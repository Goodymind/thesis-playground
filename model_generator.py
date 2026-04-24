from xgboost import XGBRegressor
import numpy as np
import sys
from sklearn.model_selection import train_test_split

# build dataset
def get_dataset(path="data.txt"):
    X = []
    y_ns = []
    y_ew = []

    with open(path, "r") as f:
        for line in f:
            a_ns, a_ew, g_ns, g_ew = map(float, line.strip().split())
            X.append([a_ns, a_ew])
            y_ns.append(g_ns)
            y_ew.append(g_ew)

    return np.array(X), np.array(y_ns), np.array(y_ew)

if __name__ == "__main__":
    type = sys.argv[1] if len(sys.argv) > 1 else "vehicle"
    print("loading dataset...")
    X, y_ns, y_ew = get_dataset(type + "_data.txt")
    print("dataset loaded.") 
    # split
    X_train, X_test, y_ns_train, y_ns_test, y_ew_train, y_ew_test = train_test_split(X, y_ns, y_ew, test_size=0.2)

    # models
    model_ns = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1
    )

    model_ew = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1
    )

    # train
    print(f"Training {type} model for NS green time...")
    model_ns.fit(X_train, y_ns_train)
    print(f"Training {type} model for EW green time...")
    model_ew.fit(X_train, y_ew_train)

    model_ns.save_model(type + "_model_ns.json")
    model_ew.save_model(type + "_model_ew.json")
    print("models saved.")