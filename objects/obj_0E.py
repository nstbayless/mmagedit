from objects.cfg_hp import ConfigHP
from util import *

# skeleton

# 0xEB03: step routine

# 0xEB2F: is bone timer a thing?

# 0xEAF7: sets timer for throwing bone.

ram_interval_address = 0xEAF8

class Config0E(ConfigHP):
    def __init__(self, data, gid):
        super().__init__(data, gid)
        self.throw_interval = 0
    
    def read(self):
        super().read()
        self.throw_interval = self.data.read_byte(self.data.ram_to_rom(ram_interval_address))
        
    def commit(self):
        super().commit()
        self.data.write_byte(self.data.ram_to_rom(self.throw_interval), self.throw_interval)
    
    def stat(self, out):
        super().stat(out)
        
        out("# frames in hex, hardmode/hellmode only. Divided by two on Hell mode.")
        out("throw-interval", HB(self.throw_interval))
        out()
    
    def parse(self, tokens):
        super().parse(tokens)
        
        if tokens[0] == "throw-interval":
            self.throw_interval = int(tokens[1], 16)