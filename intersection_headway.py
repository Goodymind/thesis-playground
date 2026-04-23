import simpy
from collections import deque

class TrafficData:
    def __init__(self, env):
        self.env = env

        # inputs
        self.queue_ns = 0  # North-South queue
        self.queue_ew = 0  # East-West queue
        self.traffic_light_green_time_ns  = 20 # NS red, EW green
        self.traffic_light_green_time_ew = 20 # NS green, EW red
        self.arrival_interval_ns  = 2
        self.arrival_interval_ew  = 2
        self.first_car_delay   = 3
        self.saturation_headway = 1
        self.sim_duration      = 200

        self.arrivals_timestamp_ns = deque()
        self.arrivals_timestamp_ew = deque()

        # outputs
        self.cars_accepted_ns = 0
        self.cars_accepted_ew = 0
        self.total_wait_time_ns = 0
        self.total_wait_time_ew = 0

        # start processes
        env.process(self.arrivals_ns())
        env.process(self.arrivals_ew())
        env.process(self.signal_light())

    def signal_light(self):
        while True:
            # NS green, EW red
            # print(f"Signal: NS green, EW red at {self.env.now}")

            self.env.process(self.discharger_ns())

            yield self.env.timeout(self.traffic_light_green_time_ns)

            # NS red, EW green
            # print(f"Signal: NS red, EW green at {self.env.now}")

            self.env.process(self.discharger_ew())

            yield self.env.timeout(self.traffic_light_green_time_ew)

    def arrivals_ns(self):
        while True:
            self.queue_ns += 1
            # print(f"Car arrives (NS) at {self.env.now}, queue: {self.queue_ns}")
            self.arrivals_timestamp_ns.append(self.env.now)
            yield self.env.timeout(self.arrival_interval_ns)

    def arrivals_ew(self):
        while True:
            self.queue_ew += 1
            # print(f"Car arrives (EW) at {self.env.now}, queue: {self.queue_ew}")
            self.arrivals_timestamp_ew.append(self.env.now)
            yield self.env.timeout(self.arrival_interval_ew)

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
                # print(f"Car departs (NS) at {self.env.now:.2f}, queue: {self.queue_ns}, waited for {wait_time:.2f} seconds")

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
                self.total_wait_time_ew += self.env.now - self.arrivals_timestamp_ew.popleft()
                # print(f"Car departs (EW) at {self.env.now:.2f}, queue: {self.queue_ew}")


if __name__ == "__main__":
    env = simpy.Environment()
    data = TrafficData(env)
    env.run(until=data.sim_duration)
    print(f"\nTotal cars accepted (NS): {data.cars_accepted_ns}")
    print(f"Cars still in queue (NS): {data.queue_ns}")
    print(f"Total cars accepted (EW): {data.cars_accepted_ew}")
    print(f"Cars still in queue (EW): {data.queue_ew}")
    print(f"Total cars accepted: {data.cars_accepted_ns + data.cars_accepted_ew}")
    print(f"Average wait time (NS): {data.total_wait_time_ns / data.cars_accepted_ns if data.cars_accepted_ns > 0 else 0}")
    print(f"Average wait time (EW): {data.total_wait_time_ew / data.cars_accepted_ew if data.cars_accepted_ew > 0 else 0}")

def generate(green_time_ns, green_time_ew, arrival_interval_ns, arrival_interval_ew):
    env = simpy.Environment()
    data = TrafficData(env)
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
        "average_wait_time_ns": data.total_wait_time_ns / data.cars_accepted_ns if data.cars_accepted_ns > 0 else 0,
        "average_wait_time_ew": data.total_wait_time_ew / data.cars_accepted_ew if data.cars_accepted_ew > 0 else 0
    }
