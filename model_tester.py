from xgboost import XGBRegressor

if __name__ == "__main__":
    model_ns = XGBRegressor()
    model_ew = XGBRegressor()

    model_ns.load_model("model_ns.json")
    model_ew.load_model("model_ew.json")

    # Example test
    test_input = [[5.0, 3.0]]  # arrival rates for NS and EW
    predicted_g_ns = model_ns.predict(test_input)[0]
    predicted_g_ew = model_ew.predict(test_input)[0]

    print(f"Predicted green times for input {test_input[0]}: NS={predicted_g_ns:.2f} sec, EW={predicted_g_ew:.2f} sec")