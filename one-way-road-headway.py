import simpy
import random

class traffic_data:
    def __init__(self, env):
        # input
        self.queue = 0
        self.traffic_light_state = "red"
        self.traffic_light_red_time = 20
        self.traffic_light_green_time = 20
        self.arrival_interval = 1
        self.first_car_delay = 5
        self.saturation_headway = 2
        self.sim_duration = 200
        
        # output
        self.cars_accepted = 0

        # event related stuff
        self.env = env
        self.arrival_proc = env.process(self.arrivals(env, self))
        self.signal_light_proc = env.process(self.signal_light(env, self))
        self.discharger_reactivate = env.event()
        

    def signal_light(self, env, data):
        while True:
            print(f"Signal light is green at {env.now}")
            env.process(self.discharger(env, data))
            yield env.timeout(data.traffic_light_green_time)

            print(f"Signal light is red at {env.now}")
            yield env.timeout(data.traffic_light_red_time)  

    def arrivals(self, env, data):
        """Generates cars every interval and adds them to the queue"""
        while True:
            print(f"Car arrives at {env.now}")
            data.queue += 1
            yield env.timeout(data.arrival_interval)

    def discharger(self, env, data):
        """Releases cars while the signal light is green"""
        green_end = env.now + data.traffic_light_green_time
        first = True

        while env.now < green_end and data.queue > 0:
            if first:
                # First car has extra delay (startup lost time)
                yield env.timeout(data.first_car_delay)
                first = False
            else:
                # After that, use saturation headway
                yield env.timeout(data.saturation_headway)

            # Check again in case time expired while waiting
            if env.now >= green_end:
                break

            # Discharge a car
            data.queue -= 1
            data.cars_accepted += 1
            print(f"Car departs at {env.now}, queue left: {data.queue}")



if __name__ == "__main__":
    env = simpy.Environment()
    data = traffic_data(env)
    env.run(until=data.sim_duration)