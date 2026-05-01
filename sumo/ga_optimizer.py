"""
GA Traffic Light Optimizer for 4-way SUMO intersection
=======================================================
Optimizes the 4 phase durations in 4way.xml using a Genetic Algorithm.
Fitness = minimize average waiting time across all vehicles.

Requirements:
    pip install sumolib traci
    SUMO must be installed and SUMO_HOME must be set.

Usage:
    python ga_optimizer.py
"""

import os
import sys
import copy
import random
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
# Resolve all file paths relative to this script's directory,
# so the script works regardless of which directory you run it from.
SCRIPT_DIR = Path(__file__).parent.resolve()

SUMO_CFG        = str(SCRIPT_DIR / "4way.sumocfg")
ADDITIONAL_FILE = str(SCRIPT_DIR / "4way.xml")
NET_FILE        = str(SCRIPT_DIR / "4way.net.xml")
ROUTE_FILE      = str(SCRIPT_DIR / "4way.rou.xml")
SIM_DURATION    = 600              # seconds (matches your flow end time)
TL_ID           = "junction"

# Phase indices in 4way.xml
# Phase 0: Green NS  (state "Gr")
# Phase 1: Yellow NS (state "yr")
# Phase 2: Green WE  (state "rG")
# Phase 3: Yellow WE (state "ry")
NUM_PHASES = 4

# Duration bounds (seconds)
MIN_GREEN    = 10
MAX_GREEN    = 90
YELLOW_FIXED = 3   # Yellow phases are kept fixed for safety

# GA parameters
POPULATION_SIZE = 20
GENERATIONS     = 30
MUTATION_RATE   = 0.2
MUTATION_STD    = 5      # stddev of gaussian mutation in seconds
ELITISM_COUNT   = 2      # top N individuals carried unchanged to next gen
TOURNAMENT_SIZE = 3

# Output
OUTPUT_FILE = "simulation_output.xml"

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def check_sumo():
    """Verify SUMO is accessible."""
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        print("ERROR: SUMO_HOME environment variable is not set.")
        print("  Set it with: export SUMO_HOME=/path/to/sumo")
        sys.exit(1)

    try:
        sys.path.append(os.path.join(sumo_home, "tools"))
        import traci
        return traci
    except ImportError:
        print("ERROR: traci not found. Install with: pip install traci")
        sys.exit(1)


def make_temp_additional(phase_durations: List[int], out_path: str = str(SCRIPT_DIR / "temp_tl.xml")):
    """
    Write a temporary additional file with the given phase durations.

    The net file already contains a tlLogic with programID="0", so we use
    programID="ga" to avoid the duplicate-ID error. A <tlLogicController>
    element then switches the junction to our new program at t=0.
    """
    root = ET.Element("additional")

    # New program with a unique programID
    tl = ET.SubElement(root, "tlLogic",
                        id=TL_ID, type="static", programID="ga", offset="0")
    states = ["GGGr", "yyyr", "rrrG", "rrry"]
    for dur, state in zip(phase_durations, states):
        ET.SubElement(tl, "phase", duration=str(dur), state=state)

    # Switch the junction to our program at simulation start
    ET.SubElement(root, "tlLogicController",
                  id=TL_ID, programID="ga", begin="0")

    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(out_path, encoding="unicode", xml_declaration=True)
    return out_path


def make_temp_cfg(additional_path: str, output_path: str,
                   cfg_out: str = str(SCRIPT_DIR / "temp_run.sumocfg")) -> str:
    """
    Write a temporary sumocfg.
    Only temp_tl.xml is loaded as additional — NOT 4way.xml.
    4way.xml contains a tlLogic that duplicates the net file's own tlLogic,
    causing SUMO to error. Our temp_tl.xml uses programID='ga' to coexist
    safely with the net's built-in programID='0'.
    """
    root = ET.Element("sumoConfiguration")
    inp = ET.SubElement(root, "input")
    ET.SubElement(inp, "net-file",         value=NET_FILE)
    ET.SubElement(inp, "route-files",      value=ROUTE_FILE)
    ET.SubElement(inp, "additional-files", value=additional_path)  # only temp_tl.xml

    out = ET.SubElement(root, "output")
    ET.SubElement(out, "tripinfo-output", value=output_path)

    time = ET.SubElement(root, "time")
    ET.SubElement(time, "end", value=str(SIM_DURATION))

    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(cfg_out, encoding="unicode", xml_declaration=True)
    return cfg_out


def run_simulation(phase_durations: List[int]) -> dict:
    """
    Run SUMO with the given phase durations.
    Returns a dict with fitness metrics.
    """
    tl_file  = make_temp_additional(phase_durations, str(SCRIPT_DIR / "temp_tl.xml"))
    out_file = str(SCRIPT_DIR / "temp_tripinfo.xml")
    cfg_file = make_temp_cfg(tl_file, out_file)

    sumo_binary = os.path.join(os.environ["SUMO_HOME"], "bin", "sumo")

    result = subprocess.run(
        [sumo_binary, "-c", cfg_file, "--no-warnings", "--no-step-log"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"  [SUMO ERROR] {result.stderr[:300]}")
        return {"avg_wait": float("inf"), "avg_travel": float("inf"), "departed": 0}

    return parse_tripinfo(out_file)


def parse_tripinfo(tripinfo_path: str) -> dict:
    """Parse SUMO tripinfo XML and extract key metrics."""
    if not Path(tripinfo_path).exists():
        return {"avg_wait": float("inf"), "avg_travel": float("inf"), "departed": 0}

    tree = ET.parse(tripinfo_path)
    root = tree.getroot()

    wait_times   = []
    travel_times = []

    for trip in root.findall("tripinfo"):
        wt = float(trip.get("waitingTime", 0))
        tt = float(trip.get("duration", 0))
        wait_times.append(wt)
        travel_times.append(tt)

    n = len(wait_times)
    if n == 0:
        return {"avg_wait": float("inf"), "avg_travel": float("inf"), "departed": 0}

    return {
        "avg_wait":   sum(wait_times)   / n,
        "avg_travel": sum(travel_times) / n,
        "departed":   n,
        "total_wait": sum(wait_times),
    }


def fitness(metrics: dict) -> float:
    """
    Lower is better.
    Primary: average waiting time
    Penalty: if very few vehicles departed (simulation may have failed)
    """
    if metrics["departed"] == 0:
        return float("inf")
    return metrics["avg_wait"]


# ──────────────────────────────────────────────
# GA Components
# ──────────────────────────────────────────────
@dataclass
class Individual:
    # [green_NS, yellow_NS, green_WE, yellow_WE]
    phases: List[int]
    metrics: dict = field(default_factory=dict)
    score: float = float("inf")

    def evaluate(self):
        self.metrics = run_simulation(self.phases)
        self.score   = fitness(self.metrics)

    def __repr__(self):
        return (f"phases={self.phases}  "
                f"avg_wait={self.metrics.get('avg_wait', '?'):.1f}s  "
                f"departed={self.metrics.get('departed', '?')}")


def random_individual() -> Individual:
    phases = [
        random.randint(MIN_GREEN, MAX_GREEN),  # green NS
        YELLOW_FIXED,                           # yellow NS (fixed)
        random.randint(MIN_GREEN, MAX_GREEN),  # green WE
        YELLOW_FIXED,                           # yellow WE (fixed)
    ]
    return Individual(phases=phases)


def tournament_select(population: List[Individual]) -> Individual:
    contestants = random.sample(population, TOURNAMENT_SIZE)
    return min(contestants, key=lambda x: x.score)


def crossover(p1: Individual, p2: Individual) -> Tuple[Individual, Individual]:
    """Single-point crossover on the mutable phase indices (0 and 2)."""
    mutable = [0, 2]
    c1 = copy.deepcopy(p1.phases)
    c2 = copy.deepcopy(p2.phases)
    if random.random() < 0.5:
        c1[0], c2[0] = c2[0], c1[0]
    if random.random() < 0.5:
        c1[2], c2[2] = c2[2], c1[2]
    return Individual(phases=c1), Individual(phases=c2)


def mutate(ind: Individual) -> Individual:
    """Gaussian mutation on green phases only."""
    phases = copy.copy(ind.phases)
    for i in [0, 2]:  # only green phases
        if random.random() < MUTATION_RATE:
            delta = int(random.gauss(0, MUTATION_STD))
            phases[i] = max(MIN_GREEN, min(MAX_GREEN, phases[i] + delta))
    return Individual(phases=phases)


# ──────────────────────────────────────────────
# Main GA Loop
# ──────────────────────────────────────────────
def run_ga():
    check_sumo()
    print("=" * 60)
    print("  GA Traffic Light Optimizer")
    print(f"  Population: {POPULATION_SIZE}  |  Generations: {GENERATIONS}")
    print(f"  Mutation rate: {MUTATION_RATE}  |  Elitism: {ELITISM_COUNT}")
    print("=" * 60)

    # --- Initial population ---
    print("\n[Gen 0] Initializing population...")
    # Seed with the original config as one individual
    population = [Individual(phases=[30, YELLOW_FIXED, 30, YELLOW_FIXED])]
    while len(population) < POPULATION_SIZE:
        population.append(random_individual())

    print(f"  Evaluating {len(population)} individuals...")
    for i, ind in enumerate(population):
        ind.evaluate()
        print(f"  [{i+1:2d}/{POPULATION_SIZE}] {ind}")

    population.sort(key=lambda x: x.score)
    best = copy.deepcopy(population[0])
    print(f"\n  Best Gen 0: {best}")

    history = []

    # --- Evolution ---
    for gen in range(1, GENERATIONS + 1):
        print(f"\n[Gen {gen}] Evolving...")

        # Elitism: carry top individuals unchanged
        next_gen = [copy.deepcopy(ind) for ind in population[:ELITISM_COUNT]]

        # Fill rest via selection, crossover, mutation
        while len(next_gen) < POPULATION_SIZE:
            p1 = tournament_select(population)
            p2 = tournament_select(population)
            c1, c2 = crossover(p1, p2)
            c1 = mutate(c1)
            c2 = mutate(c2)
            next_gen.extend([c1, c2])

        next_gen = next_gen[:POPULATION_SIZE]

        # Evaluate new individuals only (elites already have scores)
        new_inds = next_gen[ELITISM_COUNT:]
        print(f"  Evaluating {len(new_inds)} new individuals...")
        for i, ind in enumerate(new_inds):
            ind.evaluate()
            print(f"  [{i+1:2d}/{len(new_inds)}] {ind}")

        next_gen.sort(key=lambda x: x.score)
        population = next_gen

        gen_best = population[0]
        if gen_best.score < best.score:
            best = copy.deepcopy(gen_best)
            print(f"  *** New best! {best}")
        else:
            print(f"  Best this gen: {gen_best}")
            print(f"  Overall best:  {best}")

        history.append({
            "gen":      gen,
            "best":     gen_best.score,
            "avg":      sum(x.score for x in population if x.score < float("inf"))
                        / max(1, sum(1 for x in population if x.score < float("inf")))
        })

    # ── Final results ──
    print("\n" + "=" * 60)
    print("  OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"\n  Best phase durations:")
    print(f"    Green NS  (phase 0): {best.phases[0]}s")
    print(f"    Yellow NS (phase 1): {best.phases[1]}s")
    print(f"    Green WE  (phase 2): {best.phases[2]}s")
    print(f"    Yellow WE (phase 3): {best.phases[3]}s")
    print(f"\n  Performance metrics:")
    print(f"    Avg waiting time : {best.metrics.get('avg_wait',  '?'):.2f}s")
    print(f"    Avg travel time  : {best.metrics.get('avg_travel','?'):.2f}s")
    print(f"    Vehicles departed: {best.metrics.get('departed',  '?')}")

    # Write the optimal TL config
    make_temp_additional(best.phases, str(SCRIPT_DIR / "optimal_tl.xml"))
    print(f"\n  Optimal TL config saved to: optimal_tl.xml")

    # Print generation history
    print("\n  Generation history (avg waiting time):")
    print(f"  {'Gen':>4}  {'Best':>8}  {'Avg':>8}")
    for h in history:
        print(f"  {h['gen']:>4}  {h['best']:>8.2f}  {h['avg']:>8.2f}")

    return best


# ──────────────────────────────────────────────
# Standalone simulation runner (no GA)
# ──────────────────────────────────────────────
def run_once(phases=None):
    """
    Run a single simulation with the given phases (or defaults from 4way.xml)
    and print results. Use this to test your setup before running the GA.
    """
    check_sumo()
    if phases is None:
        # Read from 4way.xml
        tree = ET.parse(ADDITIONAL_FILE)
        root = tree.getroot()
        phase_els = root.find("tlLogic").findall("phase")
        phases = [int(p.get("duration")) for p in phase_els]

    print(f"Running single simulation with phases: {phases}")
    metrics = run_simulation(phases)
    print(f"Results:")
    print(f"  Vehicles departed : {metrics['departed']}")
    print(f"  Avg waiting time  : {metrics.get('avg_wait',  '?'):.2f}s")
    print(f"  Avg travel time   : {metrics.get('avg_travel','?'):.2f}s")
    print(f"  Total waiting time: {metrics.get('total_wait','?'):.2f}s")
    return metrics


# ──────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GA Traffic Light Optimizer")
    parser.add_argument("--once", action="store_true",
                        help="Run a single simulation with current 4way.xml phases and exit")
    parser.add_argument("--phases", nargs=4, type=int, metavar=("GN","YN","GW","YW"),
                        help="Manually specify 4 phase durations for --once mode")
    args = parser.parse_args()

    if args.once:
        run_once(args.phases)
    else:
        run_ga()