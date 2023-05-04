from src.util import *

# player projectile
ram_distance_address = 0xCCE2
charged_gid = 0x35

class ConfigShot:
    def __init__(self, data, gid):
        self.data = data
        self.gid = gid
        self.lifespan = 0
    
    def offset(self):
        return 0 if self.gid != charged_gid else 1
    
    def read(self):
        self.lifespan = self.data.read_byte(self.data.ram_to_rom(ram_distance_address + self.offset()))
        
    def commit(self):
        self.data.write_byte(self.data.ram_to_rom(ram_distance_address + self.offset()), self.lifespan)
    
    def stat(self, out):
        out("# frames in hex.")
        out("lifespan", HB(self.lifespan))
    
    def parse(self, tokens):
        if tokens[0] == "lifespan":
            self.lifespan = int(tokens[1], 16) & 0xFF