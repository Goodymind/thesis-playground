import simpy

class TrafficData:
    def __init__(self, env):
        self.env = env

        # inputs
        self.queue = 0
        self.traffic_light_red_time   = 60
        self.traffic_light_green_time = 60
        self.arrival_interval  = 1
        self.first_car_delay   = 5
        self.saturation_headway = 2
        self.sim_duration      = 200

        # outputs
        self.cars_accepted = 0
        self.traffic_light_state = "red"

        # start processes
        env.process(self.arrivals())
        env.process(self.signal_light())

    def signal_light(self):
        while True:
            self.traffic_light_state = "green"
            print(f"Signal light is green at {self.env.now}")

            # run discharger in parallel (NOT yield)
            self.env.process(self.discharger())

            yield self.env.timeout(self.traffic_light_green_time)

            self.traffic_light_state = "red"
            print(f"Signal light is red at {self.env.now}")

            yield self.env.timeout(self.traffic_light_red_time)

    def arrivals(self):
        while True:
            self.queue += 1
            print(f"Car arrives at {self.env.now}, queue: {self.queue}")
            yield self.env.timeout(self.arrival_interval)

    def discharger(self):
        green_end = self.env.now + self.traffic_light_green_time
        first = True

        while self.env.now < green_end and self.queue > 0:

            wait = self.first_car_delay if first else self.saturation_headway
            first = False

            yield self.env.timeout(wait)

            # re-check after waiting
            if self.env.now >= green_end:
                break

            if self.queue > 0:
                self.queue -= 1
                self.cars_accepted += 1
                print(f"Car departs at {self.env.now:.2f}, queue: {self.queue}")


if __name__ == "__main__":
    env = simpy.Environment()
    data = TrafficData(env)
    env.run(until=data.sim_duration)
    print(f"\nTotal cars accepted: {data.cars_accepted}")
    print(f"Cars still in queue: {data.queue}")