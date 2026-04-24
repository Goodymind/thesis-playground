import sys

import simpy
from collections import deque
import random

class TrafficData:
    def __init__(self, env, ns_first = True):
        self.env = env
        self.ns_first = ns_first

        # inputs
        self.queue_ns = 0  # North-South queue
        self.queue_ew = 0  # East-West queue
        self.traffic_light_green_time_ns  = 20 # NS greed, EW red
        self.traffic_light_green_time_ew = 20 # NS red, EW green
        self.arrival_interval_ns  = 1
        self.arrival_interval_ew  = 1
        self.first_car_delay   = 3
        self.saturation_headway = 1
        self.sim_duration      = 600

        self.arrivals_timestamp_ns = deque()
        self.arrivals_timestamp_ew = deque()

        # outputs
        self.cars_accepted_ns = 0
        self.cars_accepted_ew = 0
        self.total_wait_time_ns = 0
        self.total_wait_time_ew = 0
        self.wait_times_ns = []
        self.wait_times_ew = []
        self.max_wait_time_ns = 0
        self.max_wait_time_ew = 0

        # start processes
        env.process(self.arrivals_ns())
        env.process(self.arrivals_ew())
        env.process(self.signal_light())

    def signal_light(self):
        while True:
            if self.ns_first:
                yield self.env.process(self.discharger_ns())
                yield self.env.process(self.discharger_ew())
            else:
                yield self.env.process(self.discharger_ew())
                yield self.env.process(self.discharger_ns())

    def arrivals_ns(self):
        while True:
            self.queue_ns += 1
            self.arrivals_timestamp_ns.append(self.env.now)
            yield self.env.timeout(random.expovariate(1.0 / self.arrival_interval_ns))

    def arrivals_ew(self):
        while True:
            self.queue_ew += 1
            self.arrivals_timestamp_ew.append(self.env.now)
            yield self.env.timeout(random.expovariate(1.0 / self.arrival_interval_ew))

    def discharger_ns(self):
        green_end = self.env.now + self.traffic_light_green_time_ns
        first = True

        while self.env.now < green_end:

            if self.queue_ns == 0:
                first = False
            wait = self.first_car_delay if first else self.saturation_headway
            first = False

            remaining_green = green_end - self.env.now

            if remaining_green <= 0:
                break

            wait = min(wait, remaining_green)

            yield self.env.timeout(wait)

            if self.env.now >= green_end:
                break

            if self.queue_ns > 0:
                self.queue_ns -= 1
                self.cars_accepted_ns += 1
                wait_time = self.env.now - self.arrivals_timestamp_ns.popleft()
                self.total_wait_time_ns += wait_time
                self.wait_times_ns.append(wait_time)
                self.max_wait_time_ns = max(self.max_wait_time_ns, wait_time)

    def discharger_ew(self):
        green_end = self.env.now + self.traffic_light_green_time_ew
        first = True

        while self.env.now < green_end:

            if self.queue_ew == 0:
                first = False
            wait = self.first_car_delay if first else self.saturation_headway
            first = False

            remaining_green = green_end - self.env.now

            if remaining_green <= 0:
                break

            wait = min(wait, remaining_green)

            yield self.env.timeout(wait)

            if self.env.now >= green_end:
                break

            if self.queue_ew > 0:
                self.queue_ew -= 1
                self.cars_accepted_ew += 1
                wait_time = self.env.now - self.arrivals_timestamp_ew.popleft()
                self.total_wait_time_ew += wait_time
                self.wait_times_ew.append(wait_time)
                self.max_wait_time_ew = max(self.max_wait_time_ew, wait_time)

if __name__ == "__main__":
    env = simpy.Environment()
    ns_first = sys.argv[1].lower() == "ns" if len(sys.argv) > 1 else True
    data = TrafficData(env, ns_first)
    env.run(until=data.sim_duration)
    print(f"\nTotal cars accepted (NS): {data.cars_accepted_ns}")
    print(f"Cars still in queue (NS): {data.queue_ns}")
    print(f"Total cars accepted (EW): {data.cars_accepted_ew}")
    print(f"Cars still in queue (EW): {data.queue_ew}")
    print(f"Total cars accepted: {data.cars_accepted_ns + data.cars_accepted_ew}")
    print(f"Total wait time (NS): {data.total_wait_time_ns:.2f} seconds")
    print(f"Total wait time (EW): {data.total_wait_time_ew:.2f} seconds")
    print(f"Average wait time (NS): {data.total_wait_time_ns / data.cars_accepted_ns if data.cars_accepted_ns > 0 else 0}")
    print(f"Average wait time (EW): {data.total_wait_time_ew / data.cars_accepted_ew if data.cars_accepted_ew > 0 else 0}")
    print(f"Maximum wait time: {data.max_wait_time_ns:.2f} seconds (NS), {data.max_wait_time_ew:.2f} seconds (EW)")




def generate(green_time_ns, green_time_ew, arrival_interval_ns, arrival_interval_ew, ns_first = True):
    env = simpy.Environment()
    data = TrafficData(env, ns_first)
    data.traffic_light_green_time_ns = green_time_ns
    data.traffic_light_green_time_ew = green_time_ew
    data.arrival_interval_ns = arrival_interval_ns
    data.arrival_interval_ew = arrival_interval_ew
    env.run(until=data.sim_duration)
    return {
        "green_time_ns": green_time_ns,
        "green_time_ew": green_time_ew,
        "arrival_interval_ns": arrival_interval_ns,
        "arrival_interval_ew": arrival_interval_ew,
        "cars_accepted_ns": data.cars_accepted_ns,
        "cars_accepted_ew": data.cars_accepted_ew,
        "queue_ns": data.queue_ns,
        "queue_ew": data.queue_ew,
        "total_wait_time_ns": data.total_wait_time_ns,
        "total_wait_time_ew": data.total_wait_time_ew,
        "average_wait_time_ns": data.total_wait_time_ns / data.cars_accepted_ns if data.cars_accepted_ns > 0 else 0,
        "average_wait_time_ew": data.total_wait_time_ew / data.cars_accepted_ew if data.cars_accepted_ew > 0 else 0,
        "max_wait_time_ns": data.max_wait_time_ns,
        "max_wait_time_ew": data.max_wait_time_ew,
        "wait_times_ns": data.wait_times_ns,
        "wait_times_ew": data.wait_times_ew
    }
