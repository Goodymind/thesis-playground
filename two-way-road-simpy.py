import simpy


class TrafficLight:
    def __init__(self, green_time, red_time):
        self.green_time = green_time
        self.red_time = red_time

    def is_green(self, time):
        return (time % (self.green_time + self.red_time)) in range(self.green_time)


class Road:
    # has two lanes in opposite directions, will add more soon
    def __init__(
        self,
        name,
        env,
        max_cars,
        car_time,
        traffic_light_start=None,
        traffic_light_end=None,
    ):
        self.road_res = simpy.Resource(env, max_cars)
        self.name = name
        self.car_time = car_time
        self.traffic_light_start = traffic_light_start
        self.traffic_light_end = traffic_light_end


class Car(object):
    def __init__(
        self,
        name: str,
        env: simpy.Environment,
        delay: int,
        road: Road,
        start_point="start",
    ):
        self.name = name
        self.env = env
        self.delay = delay
        self.road = road
        self.start_point = start_point
        self.action = env.process(self.run())

    def is_traffic_light_green(self):
        traffic_light = (
            self.road.traffic_light_start
            if self.start_point == "start"
            else self.road.traffic_light_end
        )
        return traffic_light is None or traffic_light.is_green(self.env.now)

    def is_end_traffic_light_green(self):
        traffic_light = (
            self.road.traffic_light_start
            if self.start_point == "end"
            else self.road.traffic_light_end
        )
        return traffic_light is None or traffic_light.is_green(self.env.now)

    def run(self):
        while True:
            if self.delay > 0:
                print(
                    f"{self.name} is parked at {self.start_point} of {self.road.name} for {self.delay} seconds. Time is {env.now}."
                )
                yield (self.env.timeout(self.delay))
            if not self.is_traffic_light_green():
                print(f"{self.name} waiting for traffic light... Time is {env.now}.")
                while not self.is_traffic_light_green():
                    yield (self.env.timeout(1))
            with self.road.road_res.request() as road_req:
                yield road_req
                print(
                    f"{self.name} is driving from {self.start_point} of {self.road.name} for {self.road.car_time} seconds. Time is {env.now}."
                )
                yield (self.env.timeout(self.road.car_time))

                if not self.is_end_traffic_light_green():
                    print(
                        f"{self.name} waiting for traffic light before leaving road... Time is {env.now}."
                    )
                    while not self.is_end_traffic_light_green():
                        yield (self.env.timeout(1))
                print(f"{self.name} reached other side of road. Time is {env.now}.")


env = simpy.Environment()
traffic_light_start = TrafficLight(3, 3)
traffic_light_end = TrafficLight(2, 5)
road = Road("Test Road", env, 2, 5, traffic_light_start, traffic_light_end)
car1 = Car("Test Car 1", env, 0, road, "start")
car2 = Car("Test Car 2", env, 2, road, "end")

env.run(until=30)
