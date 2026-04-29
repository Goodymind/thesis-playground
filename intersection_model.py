import numpy as np
import sys
from concurrent.futures import ProcessPoolExecutor
from intersection_headway import generate

N_CORES = 4
N_REPS = 1


# ---------------------------------------------------------------------------
# Worker functions (must be module-level to be picklable)
# ---------------------------------------------------------------------------

def _evaluate_vehicle(args):
    g_ns, g_ew, arrival_ns, arrival_ew = args
    score = 0.0
    for _ in range(N_REPS):
        r1 = generate(g_ns, g_ew, arrival_ns, arrival_ew, ns_first=True)
        r2 = generate(g_ns, g_ew, arrival_ns, arrival_ew, ns_first=False)
        score += (
            (r1["cars_accepted_ns"] + r1["cars_accepted_ew"]  + r2["cars_accepted_ns"] + r2["cars_accepted_ew"])
        )
    return g_ns, g_ew, score / N_REPS


def _evaluate_wait(args):
    g_ns, g_ew, arrival_ns, arrival_ew = args
    score = 0.0
    for _ in range(N_REPS):
        r1 = generate(g_ns, g_ew, arrival_ns, arrival_ew, ns_first=True)
        r2 = generate(g_ns, g_ew, arrival_ns, arrival_ew, ns_first=False)

        all_waits = (r1["wait_times_ns"] + r1["wait_times_ew"] +
                     r2["wait_times_ns"] + r2["wait_times_ew"])

        s = (np.mean(all_waits) * 0.2 +
             np.median(all_waits) * 0.15 +
             np.percentile(all_waits, 95) * 0.15)

        imbalance = (abs(r1["average_wait_time_ns"] - r1["average_wait_time_ew"]) +
                     abs(r2["average_wait_time_ns"] - r2["average_wait_time_ew"]))
        s += imbalance * 0.5
        score += s
    return g_ns, g_ew, score / N_REPS


# ---------------------------------------------------------------------------
# Optimizers
# ---------------------------------------------------------------------------

def _all_pairs(arrival_ns, arrival_ew):
    return [
        (g_ns, g_ew, arrival_ns, arrival_ew)
        for g_ns in range(20, 161, 5)
        for g_ew in range(20, 161, 5)
    ]


def find_optimal_green(arrival_ns, arrival_ew):
    pairs = _all_pairs(arrival_ns, arrival_ew)
    best_score = -float('inf')
    best_pair = (0, 0)

    with ProcessPoolExecutor(max_workers=N_CORES) as executor:
        for g_ns, g_ew, score in executor.map(_evaluate_vehicle, pairs):
            # print(g_ns, g_ew, score)
            if score > best_score:
                best_score = score
                best_pair = (g_ns, g_ew)

    return best_pair


def find_optimal_green_wait(arrival_ns, arrival_ew):
    pairs = _all_pairs(arrival_ns, arrival_ew)
    best_score = float('inf')
    best_pair = (0, 0)

    with ProcessPoolExecutor(max_workers=N_CORES) as executor:
        for g_ns, g_ew, score in executor.map(_evaluate_wait, pairs):
            if score < best_score:
                best_score = score
                best_pair = (g_ns, g_ew)

    print(f"Best pair: {best_pair} with score: {best_score:.2f}")
    return best_pair


# ---------------------------------------------------------------------------
# Dataset builder
# ---------------------------------------------------------------------------

def build_dataset(param="vehicle"):
    arrival_values = [i / 3 for i in range(1, 31, 1)]

    print(f"building dataset... ({param}_data.txt)")
    with open(f"{param}_data.txt", "w") as f:
        # print("arrival_ns,arrival_ew,g_ns,g_ew", file=f)
        for a_ns in arrival_values:
            for a_ew in arrival_values:
                print(f"Testing: {a_ns}, {a_ew}")

                if param == "vehicle":
                    g_ns, g_ew = find_optimal_green(a_ns, a_ew)
                elif param == "wait":
                    g_ns, g_ew = find_optimal_green_wait(a_ns, a_ew)

                print(a_ns, a_ew, g_ns, g_ew, file=f)

    print("dataset built.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    param = sys.argv[1] if len(sys.argv) > 1 else "vehicle"
    print(f"Building dataset with parameter: {param}")
    build_dataset(param)

    # Smoke-test single queries:
    # print(find_optimal_green(2, 3))
    # print(find_optimal_green(0.2, 5))