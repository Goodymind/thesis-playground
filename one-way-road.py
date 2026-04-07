'''
Events:
1. Car enters road
2. Car lines up
3. if green light, car goes through
4. if red light, car waits
'''

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

class car:
    def __init__(self, id):
        self.id = id

if __name__ == "__main__":
    sim = event_simulator()
    car1 = car(1)
    car2 = car(2)
    
    def car_enters_road(car):
        print(f"Car {car.id} enters the road at time {sim.current_time}")
        sim.schedule(1, lambda: car_lines_up(car), f"Car {car.id} lines up")
    
    def car_lines_up(car):
        print(f"Car {car.id} lines up at time {sim.current_time}")
        sim.schedule(1, lambda: car_goes_through(car), f"Car {car.id} goes through")
    
    def car_goes_through(car):
        print(f"Car {car.id} goes through at time {sim.current_time}")
    
    sim.schedule(0, lambda: car_enters_road(car1), "Car 1 enters road")
    sim.schedule(0.5, lambda: car_enters_road(car2), "Car 2 enters road")
    
    sim.run()