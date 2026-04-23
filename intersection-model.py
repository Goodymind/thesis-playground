import numpy as np
from intersection_headway import generate
import sys

def find_optimal_green(arrival_ns, arrival_ew):
    best_score = 0
    best_pair = (0, 0)

    # with open("results.txt", "a") as f:
    for g_ns in range(20, 161, 5):
        for g_ew in range(20, 161, 5):

            result = generate(g_ns, g_ew, arrival_ns, arrival_ew)
            # print(result, file=f)
            # Objective: maximize total accepted cars (or minimize total queue)
            score = result["cars_accepted_ns"] + result["cars_accepted_ew"] 

            if score > best_score:
                best_score = score
                best_pair = (g_ns, g_ew)

    return best_pair

def find_optimal_green_wait(arrival_ns, arrival_ew):
    best_score = float('inf')
    best_pair = (0, 0)

    for g_ns in range(20, 161, 5):
        for g_ew in range(20, 161, 5):

            result = generate(g_ns, g_ew, arrival_ns, arrival_ew)
            # Objective: minimize average wait time
            score = result["average_wait_time_ns"] + result["average_wait_time_ew"]
            print(g_ns, g_ew, score, result["average_wait_time_ns"], result["average_wait_time_ew"])

            if score < best_score:
                best_score = score
                best_pair = (g_ns, g_ew)

    return best_pair

def build_dataset(param="vehicle"):
    X = []
    y_ns = []
    y_ew = []

    arrival_ns_values = [i/5 for i in range(1, 50, 1)]
    arrival_ew_values = [i/5 for i in range(1, 50, 1)]
    print(f'building dataset... ({param}.txt)')
    with open(f"{param}_data.txt", "w") as f:
        print("arrival_ns,arrival_ew,g_ns,g_ew")
        for a_ns in arrival_ns_values:
            for a_ew in arrival_ew_values:
                print("Testing: ", a_ns, a_ew)

                if param == "vehicle":
                    g_ns, g_ew = find_optimal_green(a_ns, a_ew)
                elif param == "wait":
                    g_ns, g_ew = find_optimal_green_wait(a_ns, a_ew)

                X.append([a_ns, a_ew])
                y_ns.append(g_ns)
                y_ew.append(g_ew)

                # print(f"Data: arrivals=({a_ns},{a_ew}) → greens=({g_ns},{g_ew})", file=f)
                print(a_ns, a_ew, g_ns, g_ew, file=f)
    print('dataset built.')
    return np.array(X), np.array(y_ns), np.array(y_ew)



if __name__ == "__main__":

    # param = sys.argv[1] if len(sys.argv) > 1 else "vehicle"
    # print(f"Building dataset with parameter: {param}")
    # X, y_ns, y_ew = build_dataset(param)
    print(find_optimal_green_wait(1, 1))