"""
GA Traffic Light Optimizer for 4-way SUMO intersection
=======================================================
Optimizes the 4 phase durations using a Genetic Algorithm.

Fitness objectives (select via --objective):
  wait_time  : minimize average waiting time per vehicle (default)
  throughput : maximize vehicles that complete their trip

Requirements:
    pip install traci
    SUMO must be installed and SUMO_HOME must be set.

Usage:
    python ga_optimizer.py                          # optimize wait time
    python ga_optimizer.py --objective throughput   # optimize throughput
    python ga_optimizer.py --once                   # single baseline run
    python ga_optimizer.py --once --phases 42 3 42 3
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
# File paths  (resolved relative to this script)
# ──────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()

NET_FILE   = str(SCRIPT_DIR / "4way.net.xml")
ROUTE_FILE = str(SCRIPT_DIR / "4way.rou.xml")
ADD_FILE   = str(SCRIPT_DIR / "4way.xml")       # original, not loaded in GA runs
SIM_END    = 600        # seconds — matches your flow end time
TL_ID      = "junction"

# Phase states from 4way.net.xml (4 chars = 4 link indices)
PHASE_STATES = ["GGGr", "yyyr", "rrrG", "rrry"]

# Duration bounds (seconds) — only green phases are evolved
MIN_GREEN    = 10
MAX_GREEN    = 90
YELLOW_FIXED = 3

# ──────────────────────────────────────────────
# Fitness objective
# "wait_time"  — minimize avg wait per vehicle
# "throughput" — maximize vehicles that finish their trip
# Set by --objective flag; overriding this constant directly also works.
# ──────────────────────────────────────────────
OBJECTIVE = "wait_time"

# ──────────────────────────────────────────────
# GA parameters
# ──────────────────────────────────────────────
POPULATION_SIZE = 20
GENERATIONS     = 30
MUTATION_RATE   = 0.2
MUTATION_STD    = 5       # Gaussian std-dev for green phase mutation (seconds)
ELITISM_COUNT   = 2
TOURNAMENT_SIZE = 3


# ══════════════════════════════════════════════
# SUMO helpers
# ══════════════════════════════════════════════

def check_sumo():
    sumo_home = os.environ.get("SUMO_HOME")
    if not sumo_home:
        print("ERROR: SUMO_HOME is not set.")
        print("  export SUMO_HOME=/path/to/sumo")
        sys.exit(1)
    return sumo_home


def make_temp_tl(phase_durations: List[int],
                 out_path: str = str(SCRIPT_DIR / "temp_tl.xml")) -> str:
    """
    Write an additional file containing our GA-evolved TL program.

    Uses programID='ga' (not '0') to avoid clashing with the tlLogic
    already embedded in 4way.net.xml. A <tlLogicController> activates
    it at t=0, overriding the default program.
    """
    root = ET.Element("additional")
    tl = ET.SubElement(root, "tlLogic",
                       id=TL_ID, type="static", programID="ga", offset="0")
    for dur, state in zip(phase_durations, PHASE_STATES):
        ET.SubElement(tl, "phase", duration=str(dur), state=state)
    ET.SubElement(root, "tlLogicController", id=TL_ID, programID="ga", begin="0")
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(out_path, encoding="unicode", xml_declaration=True)
    return out_path


def make_temp_cfg(tl_path: str,
                  tripinfo_path: str,
                  cfg_path: str = str(SCRIPT_DIR / "temp_run.sumocfg")) -> str:
    """
    Write a temporary .sumocfg.
    We do NOT include 4way.xml here — it also defines a tlLogic with
    programID='0' which would duplicate the one in the net file.
    """
    root = ET.Element("sumoConfiguration")
    inp = ET.SubElement(root, "input")
    ET.SubElement(inp, "net-file",         value=NET_FILE)
    ET.SubElement(inp, "route-files",      value=ROUTE_FILE)
    ET.SubElement(inp, "additional-files", value=tl_path)
    out = ET.SubElement(root, "output")
    ET.SubElement(out, "tripinfo-output",  value=tripinfo_path)
    time = ET.SubElement(root, "time")
    ET.SubElement(time, "end",             value=str(SIM_END))
    tree = ET.ElementTree(root)
    ET.indent(tree, space="    ")
    tree.write(cfg_path, encoding="unicode", xml_declaration=True)
    return cfg_path


def run_simulation(phase_durations: List[int]) -> dict:
    """Run SUMO headlessly and return parsed metrics."""
    tl_path       = make_temp_tl(phase_durations)
    tripinfo_path = str(SCRIPT_DIR / "temp_tripinfo.xml")
    cfg_path      = make_temp_cfg(tl_path, tripinfo_path)

    sumo_bin = os.path.join(os.environ["SUMO_HOME"], "bin", "sumo")
    result = subprocess.run(
        [sumo_bin, "-c", cfg_path, "--no-warnings", "--no-step-log"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  [SUMO ERROR] {result.stderr[:400]}")
        return _empty_metrics()

    return parse_tripinfo(tripinfo_path)


def parse_tripinfo(path: str) -> dict:
    """
    Parse tripinfo XML.

    SUMO writes one <tripinfo> per departed vehicle.
    arrival==-1 means the vehicle was still in the network at sim end.
    Throughput = number of vehicles with a valid arrival time.
    """
    if not Path(path).exists():
        return _empty_metrics()

    tree = ET.parse(path)
    root = tree.getroot()

    wait_times, travel_times = [], []
    arrived = 0

    for trip in root.findall("tripinfo"):
        wait_times.append(float(trip.get("waitingTime", 0)))
        travel_times.append(float(trip.get("duration",    0)))
        if float(trip.get("arrival", -1)) >= 0:
            arrived += 1

    n = len(wait_times)
    if n == 0:
        return _empty_metrics()

    return {
        "avg_wait":   sum(wait_times)   / n,
        "avg_travel": sum(travel_times) / n,
        "total_wait": sum(wait_times),
        "departed":   n,
        "arrived":    arrived,
        "throughput": arrived,
    }


def _empty_metrics() -> dict:
    return {
        "avg_wait": float("inf"), "avg_travel": float("inf"),
        "total_wait": float("inf"), "departed": 0,
        "arrived": 0, "throughput": 0,
    }


def fitness(metrics: dict) -> float:
    """
    Scalar fitness score — lower is always better (GA minimises).

    wait_time:
        = avg waiting time in seconds

    throughput:
        = -throughput  (negate to turn maximisation into minimisation)
          with a tiny avg_wait tie-breaker so equal-throughput solutions
          still prefer less waiting.
    """
    if metrics["departed"] == 0:
        return float("inf")

    if OBJECTIVE == "throughput":
        return -metrics["throughput"] + metrics["avg_wait"] * 1e-3

    # Default: wait_time
    return metrics["avg_wait"]


# ══════════════════════════════════════════════
# GA components
# ══════════════════════════════════════════════

@dataclass
class Individual:
    # [green_NS, yellow_NS, green_WE, yellow_WE]
    phases:  List[int]
    metrics: dict  = field(default_factory=_empty_metrics)
    score:   float = float("inf")

    def evaluate(self):
        self.metrics = run_simulation(self.phases)
        self.score   = fitness(self.metrics)

    def __repr__(self):
        m = self.metrics
        w = f"{m['avg_wait']:.1f}s" if isinstance(m.get("avg_wait"), float) else "?"
        return (f"phases={self.phases}  avg_wait={w}  "
                f"arrived={m.get('arrived','?')}/{m.get('departed','?')}")


def random_individual() -> Individual:
    return Individual(phases=[
        random.randint(MIN_GREEN, MAX_GREEN),  # green NS
        YELLOW_FIXED,                           # yellow NS (fixed)
        random.randint(MIN_GREEN, MAX_GREEN),  # green WE
        YELLOW_FIXED,                           # yellow WE (fixed)
    ])


def tournament_select(pop: List[Individual]) -> Individual:
    return min(random.sample(pop, TOURNAMENT_SIZE), key=lambda x: x.score)


def crossover(p1: Individual, p2: Individual) -> Tuple[Individual, Individual]:
    c1, c2 = copy.copy(p1.phases), copy.copy(p2.phases)
    if random.random() < 0.5: c1[0], c2[0] = c2[0], c1[0]
    if random.random() < 0.5: c1[2], c2[2] = c2[2], c1[2]
    return Individual(phases=c1), Individual(phases=c2)


def mutate(ind: Individual) -> Individual:
    phases = copy.copy(ind.phases)
    for i in [0, 2]:   # green phases only
        if random.random() < MUTATION_RATE:
            delta = int(random.gauss(0, MUTATION_STD))
            phases[i] = max(MIN_GREEN, min(MAX_GREEN, phases[i] + delta))
    return Individual(phases=phases)


# ══════════════════════════════════════════════
# Main GA loop
# ══════════════════════════════════════════════

def run_ga():
    check_sumo()
    print("=" * 62)
    print(f"  GA Traffic Light Optimizer  |  Objective: {OBJECTIVE}")
    print(f"  Pop: {POPULATION_SIZE}  Gens: {GENERATIONS}  "
          f"Mut: {MUTATION_RATE}  Elite: {ELITISM_COUNT}")
    print("=" * 62)

    # Seed with the original 42/3/42/3 timings as one individual
    print("\n[Gen 0] Initialising population...")
    population: List[Individual] = [
        Individual(phases=[42, YELLOW_FIXED, 42, YELLOW_FIXED])
    ]
    while len(population) < POPULATION_SIZE:
        population.append(random_individual())

    for i, ind in enumerate(population):
        ind.evaluate()
        print(f"  [{i+1:2d}/{POPULATION_SIZE}] {ind}")

    population.sort(key=lambda x: x.score)
    best = copy.deepcopy(population[0])
    print(f"\n  Best Gen 0: {best}")

    history = []

    for gen in range(1, GENERATIONS + 1):
        print(f"\n[Gen {gen}] Evolving...")

        next_gen: List[Individual] = [
            copy.deepcopy(ind) for ind in population[:ELITISM_COUNT]
        ]
        while len(next_gen) < POPULATION_SIZE:
            c1, c2 = crossover(tournament_select(population),
                               tournament_select(population))
            next_gen += [mutate(c1), mutate(c2)]
        next_gen = next_gen[:POPULATION_SIZE]

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
            print(f"  Best this gen : {gen_best}")
            print(f"  Overall best  : {best}")

        finite = [x.score for x in population if x.score < float("inf")]
        history.append({
            "gen":  gen,
            "best": gen_best.score,
            "avg":  sum(finite) / len(finite) if finite else float("inf"),
        })

    # ── Final report ──
    print("\n" + "=" * 62)
    print("  OPTIMISATION COMPLETE")
    print("=" * 62)
    print(f"\n  Best phase durations:")
    print(f"    Green NS  (phase 0): {best.phases[0]}s")
    print(f"    Yellow NS (phase 1): {best.phases[1]}s")
    print(f"    Green WE  (phase 2): {best.phases[2]}s")
    print(f"    Yellow WE (phase 3): {best.phases[3]}s")
    m = best.metrics
    print(f"\n  Performance metrics:")
    print(f"    Avg waiting time : {m.get('avg_wait',  0):.2f}s")
    print(f"    Avg travel time  : {m.get('avg_travel',0):.2f}s")
    print(f"    Throughput       : {m.get('arrived','?')} / {m.get('departed','?')} vehicles arrived")

    out = str(SCRIPT_DIR / "optimal_tl.xml")
    make_temp_tl(best.phases, out)
    print(f"\n  Optimal TL config saved to: {out}")

    print(f"\n  Generation history (objective: {OBJECTIVE}):")
    print(f"  {'Gen':>4}  {'Best score':>12}  {'Avg score':>12}")
    for h in history:
        print(f"  {h['gen']:>4}  {h['best']:>12.4f}  {h['avg']:>12.4f}")

    return best


# ══════════════════════════════════════════════
# Baseline single-run (for testing / --once)
# ══════════════════════════════════════════════

def run_once(phases=None):
    check_sumo()
    if phases is None:
        tree = ET.parse(ADD_FILE)
        phases = [int(p.get("duration"))
                  for p in tree.getroot().find("tlLogic").findall("phase")]

    print(f"Running single simulation with phases: {phases}")
    m = run_simulation(phases)
    print("Results:")
    print(f"  Departed          : {m.get('departed',  '?')}")
    print(f"  Arrived (thruput) : {m.get('arrived',   '?')}")
    print(f"  Avg waiting time  : {m.get('avg_wait',  0):.2f}s")
    print(f"  Avg travel time   : {m.get('avg_travel',0):.2f}s")
    print(f"  Total waiting time: {m.get('total_wait',0):.2f}s")
    return m


# ══════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GA Traffic Light Optimizer")
    parser.add_argument("--once", action="store_true",
                        help="Run a single baseline simulation and exit")
    parser.add_argument("--phases", nargs=4, type=int,
                        metavar=("GN", "YN", "GW", "YW"),
                        help="Phase durations for --once mode")
    parser.add_argument("--objective",
                        choices=["wait_time", "throughput"],
                        default="wait_time",
                        help="Fitness objective (default: wait_time)")
    args = parser.parse_args()

    # Push chosen objective into the module-level constant used by fitness()
    OBJECTIVE = args.objective

    if args.once:
        run_once(args.phases)
    else:
        run_ga()