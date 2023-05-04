from src.util import *

# skeleton

# 0xEB03: step routine

# 0xEB2F: is bone timer a thing?

# 0xEAF7: sets timer for throwing bone.

ram_interval_address = 0xEAF8

class Config0E:
    def __init__(self, data, gid):
        self.data = data
        self.gid = gid
        self.throw_interval = 0
    
    def read(self):
        self.throw_interval = self.data.read_byte(self.data.ram_to_rom(ram_interval_address))
        
    def commit(self):
        self.data.write_byte(self.data.ram_to_rom(ram_interval_address), self.throw_interval)
    
    def stat(self, out):
        out("# frames in hex, hardmode/hellmode only. Divided by two on Hell mode.")
        out("throw-interval", HB(self.throw_interval))
    
    def parse(self, tokens):
        if tokens[0] == "throw-interval":
            self.throw_interval = int(tokens[1], 16)