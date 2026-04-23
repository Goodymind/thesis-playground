from xgboost import XGBRegressor
import numpy as np
from sklearn.model_selection import train_test_split

# build dataset
def get_dataset():
    X = []
    y_ns = []
    y_ew = []

    with open("data.txt", "r") as f:
        for line in f:
            a_ns, a_ew, g_ns, g_ew = map(float, line.strip().split())
            X.append([a_ns, a_ew])
            y_ns.append(g_ns)
            y_ew.append(g_ew)

    return np.array(X), np.array(y_ns), np.array(y_ew)

if __name__ == "__main__":
    print("loading dataset...")
    X, y_ns, y_ew = get_dataset()
    print("dataset loaded.") 
    # split
    X_train, X_test, y_ns_train, y_ns_test = train_test_split(X, y_ns, test_size=0.2)
    _, _, y_ew_train, y_ew_test = train_test_split(X, y_ew, test_size=0.2)

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
    print("Training model for NS green time...")
    model_ns.fit(X_train, y_ns_train)
    print("Training model for EW green time...")
    model_ew.fit(X_train, y_ew_train)

    model_ns.save_model("model_ns.json")
    model_ew.save_model("model_ew.json")
    print("models saved.")