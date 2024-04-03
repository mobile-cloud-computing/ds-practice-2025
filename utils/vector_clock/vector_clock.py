class VectorClock:
    def __init__(self, process_id, num_processes, order_id, clocks = []):
        self.process_id = process_id
        self.num_processes = num_processes

        if len(clocks)>0:
            self.clock = clocks 
        else:
            self.clock = [0] * num_processes
        self.order_id = order_id

    def update(self):
        self.clock[self.process_id] += 1

    def merge(self, other_clock):
        for i in range(self.num_processes):
            self.clock[i] = max(self.clock[i], other_clock.clock[i])

    def __str__(self):
        return f"Process {self.process_id}: {self.clock} : Order {self.order_id} Number of Processes: {self.num_processes}"
    
