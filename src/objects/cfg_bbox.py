from src import constants
from src.util import *

class ConfigBBox:
    def __init__(self, data, gid):
        self.data = data
        self.gid = gid
        self.bbox = 0
    
    def read(self):
        self.bbox = self.data.read_byte(self.data.ram_to_rom(constants.ram_object_bbox_table + self.gid))
        
    def commit(self):
        self.data.write_byte(self.data.ram_to_rom(constants.ram_object_bbox_table + self.gid), self.bbox)
    
    def stat(self, out):
        out("# bounding box (hex, 0-ff), in pixels; measures distance from center to edge")
        out("bbox", f"{self.bbox:02X}")
    
    def parse(self, tokens):
        if tokens[0] == "bbox":
            self.bbox = int(tokens[1], 16) & 0xFF