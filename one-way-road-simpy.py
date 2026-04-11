import simpy

MAX_CARS = 5
CAR_TIME = 2
TRAFFIC_LIGHT_RED_TIME = 3
# 0-2,6-8
TRAFFIC_LIGHT_GREEN_TIME = 3


def is_green(time):
    return (time % (TRAFFIC_LIGHT_GREEN_TIME + TRAFFIC_LIGHT_RED_TIME)) in range(
        TRAFFIC_LIGHT_GREEN_TIME
    )


# a car on a road
def car(env, road, delay):
    while True:
        if delay > 0:
            print(f"Car parking at {env.now} for {delay} seconds")
            yield env.timeout(delay)

        if not is_green(env.now):
            print("Waiting for traffic light to turn green...")
        while not is_green(env.now):
            yield env.timeout(1)

        print("Traffic light is green, moving forward")

        with road.request() as req:
            yield req
            print(f"Car driving at start of intersection at {env.now}")
            print(f"Road has {road.count} out of {road.capacity} cars now")
            yield env.timeout(CAR_TIME)


env = simpy.Environment()
road = simpy.Resource(env, capacity=MAX_CARS)
car_gen = car(env, road, 0)
car_gen_delay = car(env, road, 1)
simpy.Process(env=env, generator=car_gen)
# simpy.Process(env=env, generator=car_gen_delay)
env.run(until=15)
