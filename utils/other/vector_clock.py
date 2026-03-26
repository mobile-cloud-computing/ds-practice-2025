from __future__ import annotations # used for type deffinitions


class VectorClock:
    def __init__(self, own_index):
        self.clocks = [0 for i in range(3)]
        self.own_index = own_index
        assert own_index < len(self.clocks)
    
    def clock(self):
        self.clocks[self.own_index] += 1
    
    def update(self, other : VectorClock | list):
        if isinstance(other, VectorClock):
            self.clocks = [max(s, o) for s, o in zip(self.clocks, other.clocks)]
        else: 
            self.clocks = [max(s, o) for s, o in zip(self.clocks, other)]