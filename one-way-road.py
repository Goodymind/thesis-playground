'''
Events:
1. Car enters road
2. Car lines up
3. if green light, car goes through
4. if red light, car waits
'''

from collections import deque

class event:
    def __init__(self, time, action : callable, description=""):
        self.time = time
        self.action : callable = action
        self.description = description
        
    def __lt__(self, other):
        return self.time < other.time

class event_simulator:
    def __init__(self):
        self.current_time = 0
        self.events : list[event] = []
        self.running = False

    def schedule(self, delay, action : callable, description=""):
        event_time = self.current_time + delay
        new_event = event(event_time, action, description)
        self.events.append(new_event)
        self.events.sort(reverse=True)

    def run(self, until: float = -1):
        self.running = True
        while self.events and self.running:
            next_event = self.events.pop()
            if until >= 0 and next_event.time > until:
                break
            self.current_time = next_event.time
            next_event.action()
    def stop(self):
        self.running = False

class road():
    def __init__(self, name):
        self.cars_on_road = deque()
        self.name = name

class traffic_light():
    def __init__(self, name, road_start, road_end):
        self.state = "red"
        self.name = name
        self.road_start = road_start
        self.road_end = road_end

class car:
    def __init__(self, id, destination):
        self.id = id
        self.destination = destination



if __name__ == "__main__":
    sim = event_simulator()
    road_a = road("Road A")
    road_b = road("Road B")
    light_a = traffic_light("Light A", road_a, road_b)
    
    def car_generator():
        car_id = 1
        while True:
            yield car(car_id, road_b)
            car_id += 1

    # TODO: Implement the logic for car generation, traffic light changes, and car movement through the intersection.
