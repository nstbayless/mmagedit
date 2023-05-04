from src import constants
from src.util import *

class ConfigHP:
    def __init__(self, data, gid):
        self.data = data
        self.gid = gid
        self.hp = 0
    
    def read(self):
        self.hp = self.data.read_byte(self.data.ram_to_rom(constants.ram_object_hp_table + self.gid))
        
    def commit(self):
        self.data.write_byte(self.data.ram_to_rom(constants.ram_object_hp_table + self.gid), self.hp)
    
    def stat(self, out):
        out("# hp in hex, FF maximum")
        out("hp", HB(self.hp))
    
    def parse(self, tokens):
        if tokens[0] == "hp":
            self.hp = int(tokens[1], 16) & 0xFF