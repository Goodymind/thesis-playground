from xgboost import XGBRegressor
import sys
from intersection_headway import generate

def compare(predicted_g_ns, predicted_g_ew, arrival_ns, arrival_ew):
    result1 = generate(predicted_g_ns, predicted_g_ew, arrival_ns, arrival_ew, ns_first=True)
    result2 = generate(predicted_g_ns, predicted_g_ew, arrival_ns, arrival_ew, ns_first=False)

    baseline1 = generate(60, 60, arrival_ns, arrival_ew, ns_first=True)
    baseline2 = generate(60, 60, arrival_ns, arrival_ew, ns_first=False)

    print(f"Predicted: NS={predicted_g_ns:.2f} sec, EW={predicted_g_ew:.2f} sec")
    print(f"Predicted (NS first): Total accepted: {result1['cars_accepted_ns'] + result1['cars_accepted_ew']}, Average wait time: {result1['total_wait_time_ns'] / result1['cars_accepted_ns'] if result1['cars_accepted_ns'] > 0 else 0:.2f} sec (NS), {result1['total_wait_time_ew'] / result1['cars_accepted_ew'] if result1['cars_accepted_ew'] > 0 else 0:.2f} sec (EW)")
    print(f"Predicted (EW first): Total accepted: {result2['cars_accepted_ns'] + result2['cars_accepted_ew']}, Average wait time: {result2['total_wait_time_ns'] / result2['cars_accepted_ns'] if result2['cars_accepted_ns'] > 0 else 0:.2f} sec (NS), {result2['total_wait_time_ew'] / result2['cars_accepted_ew'] if result2['cars_accepted_ew'] > 0 else 0:.2f} sec (EW)")
    print(f"Baseline (60s each, NS first): Total accepted: {baseline1['cars_accepted_ns'] + baseline1['cars_accepted_ew']}, Average wait time: {baseline1['total_wait_time_ns'] / baseline1['cars_accepted_ns'] if baseline1['cars_accepted_ns'] > 0 else 0:.2f} sec (NS), {baseline1['total_wait_time_ew'] / baseline1['cars_accepted_ew'] if baseline1['cars_accepted_ew'] > 0 else 0:.2f} sec (EW)")
    print(f"Baseline (60s each, EW first): Total accepted: {baseline2['cars_accepted_ns'] + baseline2['cars_accepted_ew']}, Average wait time: {baseline2['total_wait_time_ns'] / baseline2['cars_accepted_ns'] if baseline2['cars_accepted_ns'] > 0 else 0:.2f} sec (NS), {baseline2['total_wait_time_ew'] / baseline2['cars_accepted_ew'] if baseline2['cars_accepted_ew'] > 0 else 0:.2f} sec (EW)")

if __name__ == "__main__":
    model_ns = XGBRegressor()
    model_ew = XGBRegressor()

    model_ns.load_model("wait_model_ns.json")
    model_ew.load_model("wait_model_ew.json")

    # Example test
    arrival_ns = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    arrival_ew = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    test_input = [[arrival_ns, arrival_ew]]  # arrival rates for NS and EW

    predicted_g_ns = model_ns.predict(test_input)[0]
    predicted_g_ew = model_ew.predict(test_input)[0]

    print(f"Predicted green times for input {test_input[0]}: NS={predicted_g_ns:.2f} sec, EW={predicted_g_ew:.2f} sec")
    compare(predicted_g_ns, predicted_g_ew, arrival_ns, arrival_ew)