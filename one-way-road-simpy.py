import simpy

MAX_CARS = 5
CAR_TIME = 2


# a car on a road
def car(env, road, delay):
    while True:
        print(f"Car parking at {env.now} for {delay} seconds")
        yield env.timeout(delay)
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
simpy.Process(env=env, generator=car_gen_delay)
env.run(until=50)
