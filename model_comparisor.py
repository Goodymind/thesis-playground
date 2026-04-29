import numpy as np
from xgboost import XGBRegressor

import intersection_headway
from webster_model import webster



if __name__ == "__main__":
    # 0.5s to 10s arrival intervals (0.1 to 2 cars/s)
    arrival_rates = [i - 0.5 for i in range(1, 10)]

    # vehicle throughput model
    vmodel_ns = XGBRegressor()
    vmodel_ew = XGBRegressor()
    vmodel_ns.load_model("vehicle_model_ns.json")
    vmodel_ew.load_model("vehicle_model_ew.json")

    # waiting model
    wmodel_ns = XGBRegressor()
    wmodel_ew = XGBRegressor()
    wmodel_ns.load_model("wait_model_ns.json")
    wmodel_ew.load_model("wait_model_ew.json")

    with open("results/comparison_results.txt", "w") as f:
        for a_ns in arrival_rates:
            for a_ew in arrival_rates:
                test_input = [[a_ns, a_ew]]
                # vmodel
                vmodel_g_ns = vmodel_ns.predict(test_input)[0]
                vmodel_g_ew = vmodel_ew.predict(np.column_stack([test_input, [vmodel_g_ns]]))[0]
                vmodel = intersection_headway.generate(vmodel_g_ns, vmodel_g_ew, a_ns, a_ew)

                # waiting
                wmodel_g_ns = wmodel_ns.predict(test_input)[0]
                wmodel_g_ew = wmodel_ew.predict(np.column_stack([test_input, [wmodel_g_ns]]))[0]
                wmodel = intersection_headway.generate(wmodel_g_ns, wmodel_g_ew, a_ns, a_ew)

                # webster
                webster_g_ns, webster_g_ew = webster(a_ns, a_ew, 1, 3)
                webstermodel = intersection_headway.generate(webster_g_ns, webster_g_ew, a_ns, a_ew)
                
                # fixed constant (no change)
                fixed_g_ns = 60
                fixed_g_ew = 60
                fixedmodel = intersection_headway.generate(fixed_g_ns, fixed_g_ew, a_ns, a_ew)

                print(f'{a_ns} {a_ew}', file=f)
                print(f"Vehicle {vmodel_g_ns} {vmodel_g_ew} {vmodel["cars_accepted_ns"]} {vmodel["cars_accepted_ew"]} {vmodel["average_wait_time_ns"]} {vmodel["average_wait_time_ew"]}", file=f)
                print(f"Waiting {wmodel_g_ns} {wmodel_g_ew} {wmodel["cars_accepted_ns"]} {wmodel["cars_accepted_ew"]} {wmodel["average_wait_time_ns"]} {wmodel["average_wait_time_ew"]}", file=f)
                print(f"Webster {webster_g_ns} {webster_g_ew} {webstermodel["cars_accepted_ns"]} {webstermodel["cars_accepted_ew"]} {webstermodel["average_wait_time_ns"]} {webstermodel["average_wait_time_ew"]}", file=f)
                print(f"Fixed   {fixed_g_ns} {fixed_g_ew} {fixedmodel["cars_accepted_ns"]} {fixedmodel["cars_accepted_ew"]} {fixedmodel["average_wait_time_ns"]} {fixedmodel["average_wait_time_ew"]}", file=f)
                



                