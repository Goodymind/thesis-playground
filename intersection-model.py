import numpy as np
from intersection_headway import generate

def find_optimal_green(arrival_ns, arrival_ew):
    best_score = 0
    best_pair = (0, 0)

    with open("results.txt", "a") as f:
        for g_ns in range(20, 161, 10):
            for g_ew in range(20, 161, 10):

                result = generate(g_ns, g_ew, arrival_ns, arrival_ew)
                # print(result, file=f)
                # Objective: maximize total accepted cars (or minimize total queue)
                score = result["cars_accepted_ns"] + result["cars_accepted_ew"] 

                if score > best_score:
                    best_score = score
                    best_pair = (g_ns, g_ew)

    return best_pair


def build_dataset():
    X = []
    y_ns = []
    y_ew = []

    arrival_ns_values = [i/5 for i in range(1, 50, 1)]
    arrival_ew_values = [i/5 for i in range(1, 50, 1)]

    for a_ns in arrival_ns_values:
        for a_ew in arrival_ew_values:
            g_ns, g_ew = find_optimal_green(a_ns, a_ew)

            X.append([a_ns, a_ew])
            y_ns.append(g_ns)
            y_ew.append(g_ew)

            print(f"Data: arrivals=({a_ns},{a_ew}) → greens=({g_ns},{g_ew})")

    return np.array(X), np.array(y_ns), np.array(y_ew)



if __name__ == "__main__":
    X, y_ns, y_ew = build_dataset()
    # print(X)
    # print(y_ns)
    # print(y_ew)