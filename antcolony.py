import random
import numpy as np

# Based on: https://www.geeksforgeeks.org/machine-learning/introduction-to-ant-colony-optimization/

pheromone_weight = 1
heuristic_weight = 2
evaporation = 0.5
Q = 100
n_ants = 10
n_iterations = 5

min_duration = 1
max_duration = 10

# traffic light policy (a point in the graph that ants can go to)
type TrafficLightPolicy = tuple[int, int, int]


def is_valid_step(tlp1: TrafficLightPolicy, tlp2: TrafficLightPolicy):
    if tlp1 >= tlp2:
        return False
    for i in range(3):
        if tlp2[i] - tlp1[i] == 1 and all(
            tlp2[j] == tlp1[j] for j in range(3) if i != j
        ):
            return True
    return False


nodes: list[TrafficLightPolicy] = [
    (a0, a1, a2) for a0 in range(1, 11) for a1 in range(1, 11) for a2 in range(1, 11)
]

# PLACEHOLDER BEFORE WE HAVE SUMO
node_scores: dict[TrafficLightPolicy, float] = {
    node: random.uniform(1, 100) for node in nodes
}


def node_score(tlp: TrafficLightPolicy):
    # in practice: will be the score of tlp1)
    return node_scores[tlp]


# generate pheromone values of a random number for all paths from one node/policy to another
# you can only travel to another policy if it differs by 1
pheromone_graph: dict[tuple[TrafficLightPolicy, TrafficLightPolicy], float] = {
    (i, j): 1
    for i in [
        (a0, a1, a2)
        for a0 in range(1, 11)
        for a1 in range(1, 11)
        for a2 in range(1, 11)
    ]
    for j in [
        (a0, a1, a2)
        for a0 in range(1, 11)
        for a1 in range(1, 11)
        for a2 in range(1, 11)
    ]
}


def step_numerator(fromTLP: TrafficLightPolicy, toTLP: TrafficLightPolicy):
    return (pheromone_graph[(fromTLP, toTLP)] ** pheromone_weight) * (
        node_score(toTLP) ** heuristic_weight
    )


def step_probability(fromTLP: TrafficLightPolicy, toTLP: TrafficLightPolicy):
    denom = sum([step_numerator(fromTLP, j) for j in nodes if j != toTLP])
    return step_numerator(fromTLP, toTLP) / denom


def aco():
    global_best_node: TrafficLightPolicy = (1, 1, 1)
    global_best_score = 0
    global_best_path = None

    all_paths = []
    all_scores = []
    for _ in range(n_iterations):
        for _ in range(n_ants):
            score = 0
            visited = [nodes[random.randint(0, len(nodes) - 1)]]

            while len(visited) < len(nodes):
                current = visited[-1]
                score = node_score(current)
                probabilities = []

                for node in nodes:
                    if node not in visited:
                        probabilities.append(step_probability(current, node))
                    else:
                        probabilities.append(0)

                probabilities = np.array(probabilities)
                next_node = np.random.choice(range(len(nodes)), p=probabilities)
                visited.append(next_node)

            all_paths.append(visited)
            all_scores.append(score)

            if score > global_best_score:
                global_best_node = visited[-1]
                global_best_score = score
                global_best_path = visited

        for node in pheromone_graph.keys():
            pheromone_graph[node] *= 1 - evaporation  # evaporate some pheromone

        for path, score in zip(all_paths, all_scores):
            for i in range(len(path) - 1):
                # paths will bigger resulting scores get more pheromone
                pheromone_graph[(path[i], path[i + 1])] += Q * score
                pheromone_graph[(path[i + 1], path[i])] += Q * score

            pheromone_graph[(path[-1], path[0])] += Q * score
            pheromone_graph[(path[0], path[-1])] += Q * score

    print("Best Node: ", global_best_node)
    print("Best Score: ", global_best_score)
    print("Best Path: ", global_best_path)


aco()
