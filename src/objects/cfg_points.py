from src import constants
from src.util import *

class ConfigPoints:
    def __init__(self, data, gid):
        self.data = data
        self.gid = gid
        self.points = 0
    
    def read(self):
        self.points = self.data.read_byte(self.data.ram_to_rom(constants.ram_object_points_table + self.gid))
        
    def commit(self):
        self.data.write_byte(self.data.ram_to_rom(constants.ram_object_points_table + self.gid), self.points)
    
    def stat(self, out):
        out("# score gained upon defeat. 0: 0; 1: 100; 2: 200; 3: 500; 4: 1000.")
        out("points", f"{self.points:01X}")
    
    def parse(self, tokens):
        if tokens[0] == "points":
            self.points = int(tokens[1], 16) % 5