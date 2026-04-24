from typing import List
import simpy
from enum import Enum, auto


class TrafficLight:
    def __init__(self, green_time, red_time):
        self.green_time = green_time
        self.red_time = red_time

    def is_green(self, time):
        return (time % (self.green_time + self.red_time)) in range(self.green_time)


# road network is just a graph with nodes (location points) and edges (roads). Roads have 1-2 traffic lights at the end of each road with a general number of lanes. Each road connects from one location point/node to another.


class LocationPoint:
    # for ease of implementation, location points record the edges/roads connected to it
    roads = []

    def __init__(self, name):
        self.name = name

    def connect_to_road(self, road):
        self.roads.append(road)


class LaneDirections(Enum):
    FORWARD = auto()
    REVERSE = auto()


class Road:
    # TODO: Congestion factor... can increase the car time
    """
    Initialize a road.

    :param str name: Name of the road
    :param Environment env: Simpy environment of the simulation
    :param int max_cars: Maximum cars on the road
    :param int car_time: Time takes for a car to go through this whole road
    :param start_location_point: Location point at start of road/edge
    :param end_location_point: Location point at end of road/edge
    :param lanes: List of lanes specified by direction
    :param traffic_light_start: Traffic light at start point of road
    :param traffic_light_end: Traffic light at end point of road
    """

    def __init__(
        self,
        name,
        env,
        max_cars,
        car_time,
        start_location_point: LocationPoint,
        end_location_point: LocationPoint,
        lanes: List[LaneDirections],
        traffic_light_start=None,
        traffic_light_end=None,
    ):
        self.road_res = simpy.Resource(env, max_cars)
        self.name = name
        self.car_time = car_time
        self.start_location_point = start_location_point
        self.end_location_point = end_location_point
        self.lanes = lanes
        self.traffic_light_start = traffic_light_start
        self.traffic_light_end = traffic_light_end

    @property
    def start_location_point(self):
        return self._start_location_point

    @property
    def end_location_point(self):
        return self._end_location_point

    @start_location_point.setter
    def start_location_point(self, value: LocationPoint):
        self._start_location_point = value
        self._start_location_point.connect_to_road(self)

    @end_location_point.setter
    def end_location_point(self, value: LocationPoint):
        self._end_location_point = value
        self._end_location_point.connect_to_road(self)


class Car(object):
    def __init__(
        self,
        name: str,
        env: simpy.Environment,
        delay: int,
        road: Road,
        lane_id: int,
    ):
        self.name = name
        self.env = env
        self.delay = delay
        self.road = road
        # if lane_id out of bounds clamp between valid lane_ids (aka index to the lanes list)
        self.lane_id = max(0, min(lane_id, len(self.road.lanes) - 1))
        self.action = env.process(self.run())

    def is_traffic_light_green(self):
        traffic_light = (
            self.road.traffic_light_start
            if self.direction == LaneDirections.FORWARD
            else self.road.traffic_light_end
        )
        return traffic_light is None or traffic_light.is_green(self.env.now)

    def is_end_traffic_light_green(self):
        traffic_light = (
            self.road.traffic_light_start
            if self.direction == LaneDirections.REVERSE
            else self.road.traffic_light_end
        )
        return traffic_light is None or traffic_light.is_green(self.env.now)

    @property
    def direction(self):
        return self.road.lanes[self.lane_id]

    @property
    def start_point(self):
        if self.direction == LaneDirections.FORWARD:
            return self.road.start_location_point
        return self.road.end_location_point

    def run(self):
        while True:
            if self.delay > 0:
                print(
                    f"{self.name} is parked at {self.start_point.name} of {self.road.name} for {self.delay} seconds. Time is {env.now}."
                )
                yield (self.env.timeout(self.delay))
            if not self.is_traffic_light_green():
                print(f"{self.name} waiting for traffic light... Time is {env.now}.")
                while not self.is_traffic_light_green():
                    yield (self.env.timeout(1))
            with self.road.road_res.request() as road_req:
                yield road_req
                print(
                    f"{self.name} is driving from {self.start_point.name} of {self.road.name} for {self.road.car_time} seconds. Time is {env.now}."
                )
                yield (self.env.timeout(self.road.car_time))

                if not self.is_end_traffic_light_green():
                    print(
                        f"{self.name} waiting for traffic light before leaving road... Time is {env.now}."
                    )
                    while not self.is_end_traffic_light_green():
                        yield (self.env.timeout(1))
                print(f"{self.name} reached other side of road. Time is {env.now}.")


# Some examples
# here is a one way road
def run_one_way_road(duration=15):
    env = simpy.Environment()
    traffic_light_start = TrafficLight(3, 3)
    traffic_light_end = TrafficLight(2, 5)
    loc_start = LocationPoint("start")
    loc_end = LocationPoint("end")
    lanes = [LaneDirections.FORWARD]
    road = Road(
        "road",
        env,
        5,
        5,
        loc_start,
        loc_end,
        lanes,
        traffic_light_start,
        traffic_light_end,
    )
    car1 = Car("Test Car 1", env, 0, road, 0)
    car2 = Car("Test Car 2", env, 2, road, 0)

    env.run(until=duration)


# two way intersection
# all roads have two lanes and the same traffic light patterns
"""
        D
        |
A <---> C <---> B
        |
        E
"""


def run_two_way_intersection(duration=15):
    env = simpy.Environment()
    traffic_light_start = TrafficLight(3, 3)
    traffic_light_end = TrafficLight(2, 5)
    loc_points = [
        LocationPoint("A"),
        LocationPoint("B"),
        LocationPoint("C"),
        LocationPoint("D"),
        LocationPoint("E"),
    ]

    def createSimpleRoad(start_loc, end_loc):
        return Road(
            start_loc.name + end_loc.name,
            env,
            5,
            5,
            start_loc,
            end_loc,
            [LaneDirections.FORWARD, LaneDirections.REVERSE],
            traffic_light_start,
            traffic_light_end,
        )

    roads = [
        createSimpleRoad(loc_points[0], loc_points[2]),
        createSimpleRoad(loc_points[2], loc_points[1]),
        createSimpleRoad(loc_points[3], loc_points[2]),
        createSimpleRoad(loc_points[2], loc_points[4]),
    ]

    cars = [
        Car(f"Car {i}", env, 0, roads[i], j)
        for j in range(1)
        for i in range(len(roads))
    ]

    env.run(until=duration)
