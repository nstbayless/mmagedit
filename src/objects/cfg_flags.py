from src import constants
from src.util import *

# Note: we are only reading flags 0 and 1 for palette
# the other flags are also set, unclear what they do!

class ConfigFlags:
    def __init__(self, data, gid):
        self.data = data
        self.gid = gid
        self.flags = 0
    
    def read(self):
        self.flags = self.data.read_byte(self.data.ram_to_rom(constants.ram_object_flags_table + self.gid))
        
    def commit(self):
        self.data.write_byte(self.data.ram_to_rom(constants.ram_object_flags_table + self.gid), self.flags)
    
    def stat(self, out):
        out("# palette (0-3)")
        out("palette", f"{self.flags & 0x03:01X}")
        out()
        out("# spawn priority (hex, 0-3F). Can replace actors with lower values in order to spawn.")
        out("priority", f"{self.flags >> 2:02X}")
    
    def parse(self, tokens):
        if tokens[0] == "palette":
            self.flags &= 0xFC
            self.flags |= (0x03 & int(tokens[1], 16))
        if tokens[0] == "priority":
            self.flags &= 0x03
            self.flags |= (int(tokens[1], 16) << 2)
            self.flags &= 0xFF