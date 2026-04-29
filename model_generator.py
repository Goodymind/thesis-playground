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
    print(f"dataset loaded. {type}_data.txt")
    print(X[:5])
    print(y_ns[:5])
    print(y_ew[:5])
    print(f"y_ns mean: {y_ns.mean():.1f}, y_ew mean: {y_ew.mean():.1f}")

    # split
    X_train, X_test, y_ns_train, y_ns_test, y_ew_train, y_ew_test = train_test_split(
        X, y_ns, y_ew, test_size=0.2, random_state=42
    )

    # model_ns: predicts g_ns from [a_ns, a_ew]
    model_ns = XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.1)
    print(f"Training {type} model for NS green time...")
    model_ns.fit(X_train, y_ns_train)

    # model_ew: predicts g_ew from [a_ns, a_ew, g_ns]
    X_train_ew = np.column_stack([X_train, y_ns_train])
    X_test_ew  = np.column_stack([X_test,  y_ns_test])
    model_ew = XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.1)
    print(f"Training {type} model for EW green time...")
    model_ew.fit(X_train_ew, y_ew_train)

    # evaluate
    from sklearn.metrics import mean_absolute_error
    pred_ns = model_ns.predict(X_test)
    pred_ew = model_ew.predict(X_test_ew)
    print(f"NS MAE: {mean_absolute_error(y_ns_test, pred_ns):.2f}")
    print(f"EW MAE: {mean_absolute_error(y_ew_test, pred_ew):.2f}")

    # sample inference
    sample = np.array([[1.0, 3.0]])
    g_ns_pred = model_ns.predict(sample)[0]
    g_ew_pred = model_ew.predict(np.column_stack([sample, [[g_ns_pred]]]))[0]
    print(f"Predicted green times for input {sample.tolist()[0]}: NS={g_ns_pred:.2f} sec, EW={g_ew_pred:.2f} sec")

    model_ns.save_model(type + "_model_ns.json")
    model_ew.save_model(type + "_model_ew.json")
    print("models saved.")