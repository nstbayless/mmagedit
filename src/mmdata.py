from src.bitstream import BitStream
from src.util import *
from src import constants
import json
import functools
import hashlib
import src.ips
import src.bps
import src.mappermages
import src.jsonpath
import copy
import os

breakpoint_on_byte_edit = False

# this is used for the optional single-med-tile patching mod
# represents the bit sequence for the patches
class UnitileStream:
    def __init__(self):
        self.entries = []
        self.i = 0
        self.complete = False
        self.region_starts = [-1, -1, -1, -1]
        self.prev_byte = None
    
    def length_bits(self):
        assert(self.complete)
        l = 0
        for entry in self.entries:
            l += len(entry)
        return l
        
    def length_bytes(self):
        lb = self.length_bits()
        if lb % 8 == 0:
            return int(lb / 8)
        else:
            return int(lb / 8) + 1
    
    def as_bits(self, value, n):
        l = []
        for i in range(n):
            l.append(0 if value & (1 << (n - i - 1)) == 0 else 1)
        return l
    
    def add_patch(self, patch):
        assert(not self.complete)
        assert(patch.get_i() >= self.i)
        
        # skip empty patches.
        if patch.get_flags() == 0xE0:
            return
        
        # force alignment to a region boundary
        region_boundaries = [0, 0x100, 0x200, 0x300]
        j = -1
        for region_boundary in region_boundaries:
            j += 1
            if patch.get_i() >= region_boundary and self.i < region_boundary and patch.med_tile_idx is not None:
                up = UnitilePatch()
                up.med_tile_idx = None
                up.x = region_boundary % 0x10
                up.y = region_boundary // 0x10
                self.add_patch(up)
        
            if self.i == region_boundary and self.region_starts[j] == -1:
                self.region_starts[j] = len(self.entries)
        
        # write 'advance' tokens
        while patch.get_i() > self.i:
            idiff = min(patch.get_i() - self.i, 0x41)
            assert(idiff > 0)
            if idiff >= 0x20 and idiff < 0x41:
                idiff = 0x1F
            if (idiff | 0xE0) == 0xFE and self.prev_byte == None:
                # prevent writing EOS byte, #$FE.
                idiff -= 1
            if idiff == 0x1D:
                # prevent writing 0x1D, which is code for 0x41
                idiff -= 1
            self.i += idiff
            if idiff == 0x41:
                idiff = 0x1D
            if self.prev_byte is None:
                self.entries.append([1] * 3 + self.as_bits(idiff, 5))
            else:
                self.entries[-2] = self.prev_byte[:3] + self.as_bits(idiff, 5)
                self.prev_byte = None
        
        # write patch byte
        if patch.med_tile_idx is not None:
            self.entries.append(self.as_bits(patch.get_flags(), 8))
            self.entries.append(self.as_bits(patch.med_tile_idx, 8))
            self.prev_byte = self.entries[-2]
        else:
            self.prev_byte = None
    
    def finalize(self):
        assert(not self.complete)
        self.complete = True
        self.entries.append( self.as_bits(0xFE, 8) )

# represents the bit sequence for hard mode patches in a stage
class PatchStream:
    def __init__(self, data):
        self.entries = []
        self.position = None
        self.data = data
    
    def length_bytes(self):
        return len(self.entries)

    def advance_patch(self, position):
        if self.position is None:
            self.position = 0
            self.entries = []
        if position == self.position:
            return
        if len(self.entries) == 0:
            self.entries = [0]
        assert (position > self.position)
        while True:
            assert (position >= self.position)
            if position == self.position:
                return
            diff = position - self.position - 1
            prevz = self.entries[-1] & 0xf0 == 0
            assert(diff >= 0)
            if diff < 0x0f or (diff == 0x0f and not prevz):
                assert(diff >= 0 and diff <= 0x0f)
                self.entries[-1] |= diff
                self.position = position
                break
            else:
                if (position - self.position == 0x0f) or len(self.entries) == 1:
                    # need to avoid 
                    self.entries[-1] |= 0x0e
                    self.position += 0x0f
                else:
                    self.entries[-1] |= 0x0f
                    self.position += 0x10
                
                if position > self.position:
                    self.entries.append(0)
    
    def add_patch(self, patch):
        position = patch.y * 4 + patch.x
        self.advance_patch(position)
        self.entries.append(patch.i << 4)

# represents the bit sequence for the object data in a level
class ObjectStream:
    def __init__(self, data):
        self.entries = []
        self.y = constants.objects_start_y # in microtiles (8 pixels)
        self.complete = False
        self.data = data
    
    def length_bits(self):
        assert(self.complete)
        l = 0
        for entry in self.entries:
            l += len(entry)
        return l
        
    def length_bytes(self):
        lb = self.length_bits()
        if lb % 8 == 0:
            return int(lb / 8)
        else:
            return int(lb / 8) + 1
    
    def as_bits(self, value, n):
        l = []
        for i in range(n):
            l.append(0 if value & (1 << (n - i - 1)) == 0 else 1)
        return l
    
    def add_object(self, obj):
        assert(not self.complete)
        assert(obj.y <= self.y)

        # drop objects are not part of the object stream
        if obj.drop:
            return

        while obj.y < self.y:
            ydiff = max(1, min(self.y - obj.y, 8))
            self.y -= ydiff
            self.entries.append( [0, 0] + self.as_bits(ydiff - 1, 3) )
        
        if (obj.compressible()):
            self.entries.append( [1, 0] + self.as_bits(int((obj.x - 1) / 2), 4) + self.as_bits(obj.get_i(), 4) )
        else:
            self.entries.append(
                  [0, 1]
                + [1 if obj.flipy else 0]
                + [1 if obj.flipx else 0]
                + self.as_bits(obj.x, 5)
                + (self.as_bits(obj.gid, 6) if self.data.has_mod("extended_objects") else self.as_bits(obj.get_i(), 5))
            )
    
    def finalize(self):
        assert(not self.complete)
        self.complete = True
        self.entries.append( [1, 1] )

class Object:
    def __init__(self, data):
        self.data = data
        self.x = 0 # in microtiles
        self.y = 0 # in microtiles
        self.gid = 0 # lookup (0xdab1),i
        self.flipx = False
        self.flipy = False
        self.compressed = False
        self.drop = False # only appears as a drop (requires extended objects mod)
    
    # gets placing index of object
    def get_i(self):
        if self.gid not in self.data.spawnable_objects:
            return None
        return self.data.spawnable_objects.index(self.gid)
    
    def compressible(self):
        if self.flipx or self.flipy:
            return False
        if self.get_i() is None or self.get_i() >= 0x10:
            return False
        if self.x % 2 == 0:
            return False
        return True
    
    def serialize_json(self):
        j = {
            "x": self.x,
            "y": self.y,
            "gid": self.gid,
            "flip-x": self.flipx,
            "flip-y": self.flipy,
            "compressed": self.compressed,
            ".compressible": self.compressible()
        }

        if self.data.has_mod("extended_objects"):
            j["drop"] = self.drop

        return j

    def deserialize_json(self, j):
        for key in j:
            if key == "x":
                self.x = j[key]
            elif key == "y":
                self.y = j[key]
            elif key == "gid":
                self.gid = j[key]
            elif key == "flip-x":
                self.flipx = j[key]
            elif key == "flip-y":
                self.flipy = j[key]
            elif key == "compressed":
                self.compressed = j[key]
            elif key == "drop":
                self.drop = j[key]
            else:
                self.data.errors += ["unrecognized key \"" + key + "\""]
                return False
        return True

class HardPatch:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.i = 0
    
class UnitilePatch:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.med_tile_idx = 0
        
        # which difficulties does this appear on?
        # true means it appears.
        self.flag_normal = True
        self.flag_hard   = True
        self.flag_hell   = True
    
    def get_i(self):
        return self.x + self.y * 0x10
        
    def get_flags(self):
        # produces a 1 in bits 5-7 depending on which difficulty the tile
        # does NOT appear on. A 0-valued bit means the tile does appear.
        return (0 if self.flag_normal else 0x80) | (0 if self.flag_hard else 0x40) | (0 if self.flag_hell else 0x20)
    
    def set_flags(self, flags):
        self.flag_normal = flags & 0x80 == 0
        self.flag_hard = flags & 0x40 == 0
        self.flag_hell = flags & 0x20 == 0

class LevelMacroRow:
    def __init__(self, data):
        self.data = data
        self.seam = 0
        self.macro_tiles = [0, 0, 0, 0]
        
    def read(self, rom):
        self.seam = 0
        for i in range(4):
            self.seam >>= 1
            t = self.data.read_byte(rom + 3 - i)
            self.seam |= (t & 1) << 3
            self.macro_tiles[i] = (t >> 1)
            
    def commit(self, rom):
        seam = self.seam
        for i in range(4):
            b = seam & 1
            seam >>= 1
            
            b |= (self.macro_tiles[i]) << 1
            self.data.write_byte(rom + 3 - i, b)

class Level:
    def __init__(self, data, idx):
        self.level_idx = idx
        if idx == 0xc:
            self.world_idx = 3
            self.world_sublevel = 3
        else:
            self.world_idx = int(idx / 3)
            self.world_sublevel = idx % 3
        self.world = data.worlds[self.world_idx]
        self.data = data
        self.macro_rows = []
        self.objects = []
        self.hardmode_patches = []
        self.unitile_patches = []
    
    def serialize_json(self):
        j = {
            ".world-idx": self.world_idx,
            ".world-sublevel": self.world_sublevel,
            ".name": self.get_name(),
            "macro-rows": [
                {
                    "seam": macro_row.seam,
                    "macro-tiles": macro_row.macro_tiles
                } for macro_row in self.macro_rows
            ],
            "objects": [
                obj.serialize_json() for obj in self.objects
            ],
            "hardmode-patches": [
                {
                    "x": patch.x,
                    "y": patch.y,
                    "i": patch.i
                } for patch in self.hardmode_patches
            ]
        }

        if self.data.mapper_extension:
            j["unitile-patches"] = [
                {
                    "x": patch.x,
                    "y": patch.y,
                    "med-tile": patch.med_tile_idx,
                    "flags": patch.get_flags()
                } for patch in self.unitile_patches
            ]

        return j

    def deserialize_json(self, j):
        for key in j:
            if key == "macro-rows":
                for i, macro_row in enumerate(j[key]):
                    if "seam" in macro_row:
                        self.macro_rows[i].seam = macro_row["seam"]
                    if "macro-tiles" in macro_row:
                        self.macro_rows[i].macro_tiles = macro_row["macro-tiles"]
            elif key == "objects":
                objects = []
                for obj in j[key]:
                    if obj == None or len(obj) == 0:
                        self.data.errors += ["all objects in .objects list must be fully-realized"]
                    objects.append(Object(self.data))
                    if not objects[-1].deserialize(j[key]):
                        return False
                self.objects = objects
            elif key == "unitile-patches":
                patches = []
                for patch in j[key]:
                    up = UnitilePatch()
                    up.x = patch["x"]
                    up.y = patch["y"]
                    up.med_tile_idx = patch["med-tile"]
                    up.set_flags(patch["flags"])
                self.unitile_patches = patches
            elif key == "hardmode-patches":
                patches = []
                for patch in j[key]:
                    hp = HardPatch()
                    if "x" not in patch or "y" not in patch or "i" not in patch:
                        self.data.errors += ["invalid patch format"]
                        return False
                    hp.x = patch["x"]
                    hp.y = patch["y"]
                    hp.i = patch["i"]
                    patches.append(hp)
                self.hardmode_patches = patches
            else:
                self.data.errors += ["unrecognized key \"" + key + "\""]
                return False
        return True
    
    def get_name(self, hard=False):
        s = "Tower " + str(self.world_idx + 1) + "-" + str(self.world_sublevel + 1)
        if hard:
            s += " (Hard)"
        return s
    
    def read(self):
        self.macro_rows = []
        self.objects = []
        
        # get music index
        self.music_idx = self.data.read_byte(self.data.ram_to_rom(constants.ram_music_table + self.level_idx))
        
        # get ram start address
        ram = self.data.read_word(self.data.ram_to_rom(self.level_idx * 2 + constants.ram_level_table))
        
        # read data from start address...
        hardmode_length = self.data.read_byte(self.data.ram_to_rom(ram))
        
        row_count = constants.macro_rows_per_level
        for i in range(row_count):
            row = LevelMacroRow(self.data)
            row.read(self.data.ram_to_rom(ram + i * 4 + 1))
            self.macro_rows.append(row)
        
        # hardmode patches
        patch_y = 0
        patch_x = 0
        
        for i in range(hardmode_length):
            while patch_x >= 4:
                patch_x -= 4
                patch_y += 1
            
            patch_byte = self.data.read_byte(self.data.ram_to_rom(i + ram + row_count * 4 + 1))
            
            i = (patch_byte & 0xf0) >> 4
            gap = (patch_byte & 0x0f)
            if i != 0:
                patch = HardPatch()
                patch.i = i
                patch.x = patch_x
                patch.y = patch_y
                self.hardmode_patches.append(patch)
            
            patch_x += gap + 1
            
        # read object data
        object_y = constants.objects_start_y
        
        ram_objects_start = ram + hardmode_length + 1 + row_count * 4
        bs = BitStream(self.data.bin, self.data.ram_to_rom(ram_objects_start))
        while True:
            type = bs.read_bits(2)
            obj = Object(self.data)
            obj.type = type
            i = 0
            if type == 0:
                # skip rows
                object_y -= bs.read_bits(3) + 1
                continue
                
            elif type == 1:
                # long format
                obj.y = object_y
                obj.flipy = bs.read_bit() == 1
                obj.flipx = bs.read_bit() == 1
                obj.x = bs.read_bits(5)
                i = bs.read_bits(5)
                obj.compressed = False
                
            elif type == 2:
                # short format
                obj.y = object_y
                obj.flipy = False
                obj.flipx = False
                obj.x = bs.read_bits(4) * 2 + 1
                i = bs.read_bits(4)
                obj.compressed = True
                
            elif type == 3:
                # end-of-stream
                break
                
            obj.gid = self.data.spawnable_objects[i]
            if obj.y >= 0:
                self.objects.append(obj)
        
    def length_bytes(self):
        ps = self.produce_patches_stream()
        os = self.produce_objects_stream()
        return os.length_bytes() + ps.length_bytes() + 4 * constants.macro_rows_per_level + 1
    
    def length_unitile_bytes(self):
        us = self.produce_unitile_stream()
        if len(us.entries) <= 1:
            return 0
        return us.length_bytes()
    
    def produce_unitile_rows(self):
        out = [[[None] * 3 for x in range(0x10)] for y in range(constants.macro_rows_per_level * 2)]
        
        for ut in self.unitile_patches:
            for j in range(3):
                if ut.get_flags() & (1 << (7 - j)) == 0:
                    out[ut.y][ut.x][j] = ut
        
        return out
    
    # there is some redundancy in the ways the unitiles can be expressed
    # these two functions re-express the same data in different ways
    # this simplifies other logic which operate on unitiles.
    def split_unitiles_by_difficulty(self):
        old_unitiles = self.unitile_patches
        self.unitile_patches = []
        for u in old_unitiles:
            if u.med_tile_idx is not None:
                for j in range(3):
                    flag = 1 << (7 - j)
                    if u.get_flags() & flag == 0:
                        if u.get_flags() == 0x80 or u.get_flags == 0x40 or u.get_flags == 0x20 or u.get_flags == 0:
                            # we make a copy so that we can have exactly one of the flags active.
                            uc = UnitilePatch()
                            uc.x = u.x
                            uc.y = u.y
                            uc.med_tile_idx = u.med_tile_idx
                        else:
                            # tile already has exactly one flag active, so we reuse it; no need to copy.
                            uc = u
                        uc.flag_normal = j == 0
                        uc.flag_hard = j == 1
                        uc.flag_hell = j == 2
                        assert(uc.get_flags() != 0 and uc.get_flags() != 0xE0)
                        self.unitile_patches.append(uc)

    def combine_unitiles_by_difficulty(self):
        old_unitiles = self.unitile_patches
        self.unitile_patches = []
        for u in old_unitiles:
            # don't add if the tile is vacuous (would not appear on any difficulty)
            if u.med_tile_idx is not None and u.get_flags() != 0xE0:
                # check if a compatible tile was already added
                matches = [v for v in self.unitile_patches if v.x == u.x and v.y == u.y and v.med_tile_idx == u.med_tile_idx]
                if len(matches) == 0:
                    # no luck -- add new tile instead
                    uc = UnitilePatch()
                    uc.x = u.x
                    uc.y = u.y
                    uc.med_tile_idx = u.med_tile_idx
                    uc.set_flags(u.get_flags())
                    self.unitile_patches.append(uc)
                else:
                    for v in matches:
                        # adjust the flags of the existing tile
                        v.flag_normal = v.flag_normal or u.flag_normal
                        v.flag_hard = v.flag_hard or u.flag_hard
                        v.flag_hell = v.flag_hell or u.flag_hell
    
    def length_object_drops_bytes(self):
        length = 0
        for obj in self.objects:
            if obj.drop:
                length += 4
        # ending byte
        if length > 0:
            length += 1
        return length

    # returns error, new ram output location
    def commit_drop_objects(self, ram):
        rom = self.data.ram_to_rom(ram)
        
        table_start = src.mappermages.unitile_table_range[0]
        # zero out the table
        for j in range(2):
            rom_table_location = self.data.ram_to_rom(table_start + self.level_idx + constants.level_count * j)
            self.data.write_byte(rom_table_location, 0)
        
        if self.length_object_drops_bytes() > 0:
            for j in range(2):
                rom_table_location = self.data.ram_to_rom(table_start + self.level_idx + constants.level_count * j)
                v = ram - 3
                w = (v & 0x00ff) if j == 0 else ((v & 0xff00) >> 8)
                self.data.write_byte(rom_table_location, w)
            bs = BitStream(self.data.bin, rom)
            for obj in self.objects:
                if obj.drop:
                    bs.write_bits(obj.x * 8, 8)
                    bs.write_bits((obj.y * 8) & 0xff, 8)
                    screen = (((obj.y * 8) - 0x18) // 256) + 0xFC
                    assert(screen >= 0xFB and screen < 0x100)
                    bs.write_bits(screen, 8)
                    bs.write_bits(obj.gid, 8)
            bs.write_bits(1, 8) # eof
        
        return True, ram + self.length_object_drops_bytes()

    # returns error, new ram output location
    def commit_unitile(self, ram):
        rom = self.data.ram_to_rom(ram)
        
        table_start = src.mappermages.unitile_table_range[0] + 2 * constants.level_count
        
        # zero out the table
        for j in range(4):
            rom_table_location = self.data.ram_to_rom(table_start + 8 * self.level_idx + 2 * j)
            self.data.write_word(rom_table_location, 0)
        
        # write unitile data sequence
        self.combine_unitiles_by_difficulty()
        us = self.produce_unitile_stream()
        bs = BitStream(self.data.bin, rom)
        
        if len(us.entries) > 1: # we skip if there are no unitiles at all.
            for i in range(len(us.entries)):
                if i in us.region_starts:
                    idx = us.region_starts.index(i)
                    rom_table_location = self.data.ram_to_rom(table_start + 8 * self.level_idx + 2 * idx)
                    self.data.write_word(rom_table_location, bs.offset - rom + ram)
                entry = us.entries[i]
                bs.write_bits_list(entry)
            
        return True, ram + self.length_unitile_bytes()
    
    # returns error, new ram output location
    def commit(self, ram):
        ps = self.produce_patches_stream()
        os = self.produce_objects_stream()
        
        # write music index
        self.data.write_byte(self.data.ram_to_rom(constants.ram_music_table + self.level_idx), self.music_idx)
        
        # write level ram offset
        self.data.write_word(self.data.ram_to_rom(self.level_idx * 2 + constants.ram_level_table), ram)
        
        # write hardmode data length
        rom = self.data.ram_to_rom(ram, "level")
        self.data.write_byte(rom, ps.length_bytes())
            
        # write tile data
        for i in range(constants.macro_rows_per_level):
            macro_row = self.macro_rows[i]
            macro_row.commit(rom + i * 4 + 1)
        
        # write hardmode patch data
        for i in range(len(ps.entries)):
            entry = ps.entries[i]
            self.data.write_byte(rom + 4 * constants.macro_rows_per_level + 1 + i, entry)
        
        # write objects data
        bs = BitStream(self.data.bin, rom + 4 * constants.macro_rows_per_level + 1 + ps.length_bytes())
        for entry in os.entries:
            bs.write_bits_list(entry)
        
        return True, ram + self.length_bytes()
        
    def produce_patches_stream(self):
        ps = PatchStream(self.data)
        
        # add objects to stream sorted by y and x position.
        for patch in sorted(self.hardmode_patches, key=lambda patch : patch.y * 4 + patch.x):
            ps.add_patch(patch)
        
        if ps.position is None or ps.position < 0x80:
            ps.advance_patch(0x80)
        
        return ps
        
    def produce_objects_stream(self):
        os = ObjectStream(self.data)
        
        # add objects to stream sorted by y position.
        for obj in sorted(self.objects, key=lambda obj : -obj.y):
            os.add_object(obj)
        
        os.finalize()
        
        return os
        
    def produce_unitile_stream(self):
        us = UnitileStream()
        
        # add unitiles to stream sorted by y position
        for patch in sorted(self.unitile_patches, key=lambda patch : patch.get_i()):
            us.add_patch(patch)
        
        us.finalize()
        
        return us
        
    def get_macro_patch_tile(self, patch_i):
        return 0x2f + patch_i
        
    # constructs rows of medtiles (and macrotiles) from bottom up.
    # dimensions should be YX, 64x16
    def produce_med_tiles(self, hardmode=False, orows=range(constants.macro_rows_per_level)):
        rows = []
        macro_tile_idxs = []
        if self.data.mapper_extension:
            unitile_j = (1 if hardmode else 0) # TODO: hellmode?
            unitile_rows = self.produce_unitile_rows()
        for y in orows:
            lmr = self.macro_rows[y]
            row = [[0] * 16, [0] * 16]
            for i in range(4):
                macro_tile_idx = lmr.macro_tiles[i]
                if hardmode:
                    for patch in self.hardmode_patches:
                        if y == patch.y:
                            if i == patch.x:
                                macro_tile_idx = self.get_macro_patch_tile(patch.i)
                macro_tile_idxs.append(macro_tile_idx)
                macro_tile = self.world.get_macro_tile(macro_tile_idx)
                for j in range(2):
                    row[j][i * 2] = macro_tile[0 + 2 * j]
                    row[j][i * 2 + 1] = macro_tile[1 + 2 * j]
                    row[j][0x10 - i *2 - 1] = self.world.mirror_tile(row[j][i * 2])
                    row[j][0x10 - i *2 - 2] = self.world.mirror_tile(row[j][i * 2 + 1])
            
            for j in range(2):
                # seam shift
                row[j] = rotated(row[j], (0x10 - lmr.seam) % 0x10)
                
                # apply unitile data
                if self.data.mapper_extension:
                    x = -1
                    for h in unitile_rows[2 * y + 1 - j]:
                        x += 1
                        u = h[unitile_j]
                        if u is not None:
                            row[j][x] = u.med_tile_idx
            
            rows.append(row[1])
            rows.append(row[0])
            
        return rows, macro_tile_idxs

class World:
    def __init__(self, data, idx):
        self.data = data
        self.idx = idx
        self.macro_tiles = [] # array of [tl, tr, bl, br]
        self.med_tiles = [] # array of [tl, tr, bl, br]
        self.med_tile_palettes = []
        self.total_length = None
        self.max_symmetry_idx = 0
        self.palettes = []
    
    def serialize_json(self):
        return {
            "max-symmetry-idx": self.max_symmetry_idx,
            "macro-tiles": self.macro_tiles,
            "med-tiles": self.med_tiles,
            "med-tile-palette-idxs": self.med_tile_palettes,
            "bg-palettes": self.palettes,
        }
    
    def deserialize_json(self, j):
        for key in j:
            if key == "max-symmetry-idx":
                self.max_symmetry_idx = j[key]
            elif key == "macro-tiles":
                self.macro_tiles = j[key]
            elif key == "med-tiles":
                self.med_tiles = j[key]
            elif key == "med-tile-palette-idxs":
                self.med_tile_palettes = j[key]
            elif key == "bg-palettes":
                self.palettes = j[key]
            else:
                self.data.errors += ["unrecognized key \"" + key + "\""]
                return False
        return True
        
    def mirror_tile(self, t):
        if t == 0x11:
            return 0x0
        if t < 0x1e or t >= self.max_symmetry_idx:
            for pair in self.data.mirror_pairs:
                if t == pair[0]:
                    return pair[1]
                if t == pair[1]:
                    return pair[0]
            return t
        else:
            return t ^ 0x01
            
    def get_macro_tile(self, idx):
        if idx < constants.global_macro_tiles_count:
            return self.data.macro_tiles[idx]
        elif idx < constants.global_macro_tiles_count + len(self.macro_tiles):
            return self.macro_tiles[idx - constants.global_macro_tiles_count]
        else:
            # TODO
            return [0x0, 0x0, 0x0, 0x0]
        
    def get_med_tile(self, idx):
        if idx < constants.global_med_tiles_count:
            return self.data.med_tiles[idx]
        elif idx < constants.global_med_tiles_count + len(self.med_tiles):
            return self.med_tiles[idx - constants.global_med_tiles_count]
        else:
            # TODO
            return [0, 0, 0, 0]
            
    def get_micro_tile(self, idx, hard=False):
        # world 2's special ice topping
        if self.idx == 1 and hard:
            if idx in range(0x12, 0x18):
                return 0x10
        return idx
    
    def get_med_tile_palette_idx(self, idx, hard=False):
        if idx >= len(self.med_tile_palettes):
            return None
    
        palette_idx = self.med_tile_palettes[idx]
        return self.map_palette_idx(palette_idx, hard)
    
    def get_med_tile_palette(self, med_tile_idx, hard=False):
        palette_idx = self.get_med_tile_palette_idx(med_tile_idx, hard)
        if palette_idx is None:
            return None
        return self.palettes[palette_idx]
    
    def get_palette(self, palette_idx, hard=False):
        return self.palettes[self.map_palette_idx(palette_idx, hard)]
        
    def map_palette_idx(self, palette_idx, hard=False):
        if hard:
            palette_idx += 4
        
        # hard mode uses this weird reshuffling of palette indices
        # although some palettes do not appear, all *are* loaded into ppu ram.
        if palette_idx == 6 and self.idx != 3:
            palette_idx = 4
        if palette_idx == 7 and self.idx == 0:
            palette_idx = 6
        return palette_idx
    
    def hidden_tile_palettes(self, hard=False):
        # these palettes should cause the hidden tiles to be rendered
        # specially (for the user of the editor's benefit)
        if self.idx == 3:
            return [3]
        else:
            return [1]
    
    def read(self):
        self.max_symmetry_idx = self.data.read_byte(self.data.ram_to_rom(constants.ram_world_mirror_index_table + self.idx))
        data_ptr = self.data.read_word(self.data.ram_to_rom(constants.ram_world_macro_tiles_table + self.idx * 2))
        self.ram = data_ptr
        
        # tile counts
        med_tile_count = self.data.read_byte(self.data.ram_to_rom(data_ptr))
        data_ptr += 1
        macro_tile_count = self.data.read_byte(self.data.ram_to_rom(data_ptr))
        data_ptr += 1
        
        self.total_length = med_tile_count + macro_tile_count
        
        # dummy -- to fill in later
        self.med_tile_palettes = [0] * 0x100
        
        # med-tiles
        next_data_ptr = data_ptr
        for i in range(med_tile_count):
            self.med_tiles.append([
                self.data.read_byte(self.data.ram_to_rom(data_ptr + med_tile_count * j)) for j in range(4)
            ])
            data_ptr += 1
            next_data_ptr += 4
        data_ptr = next_data_ptr
            
        # med-tile palette data
        idx = 0
        for i in range(int((med_tile_count + constants.global_med_tiles_count + 3) / 4)):
            b = self.data.read_byte(self.data.ram_to_rom(data_ptr))
            for j in range(4):
                if idx < med_tile_count + constants.global_med_tiles_count:
                    self.med_tile_palettes[idx] = (b >> (2 * j)) % 4
                    idx += 1
            data_ptr += 1
        
        # macro-tiles
        next_data_ptr = data_ptr
        for i in range(macro_tile_count):
            macro_tile = []
            for j in range(4):
                byte = self.data.read_byte(self.data.ram_to_rom(data_ptr + macro_tile_count * j))
                macro_tile.append(byte)
            self.macro_tiles.append(macro_tile)
            data_ptr += 1
            next_data_ptr += 4
        
        data_ptr = next_data_ptr
        
        # read palettes.
        bs = BitStream(self.data.bin, self.data.ram_to_rom(data_ptr))
        for i in range(8):
            a = bs.read_bits(6)
            b = bs.read_bits(6)
            c = bs.read_bits(6)
            self.palettes.append([
                0xf,
                a,
                b,
                c
            ])
            
    def commit(self):
        # assert lengths not exceeded
        if self.total_length < len(self.med_tiles) + len(self.macro_tiles):
            self.data.errors += ["size exceeded for world " + str(world_idx + 1)]
            return False
        
        # max symmetry index
        self.data.write_byte(self.data.ram_to_rom(constants.ram_world_mirror_index_table + self.idx), self.max_symmetry_idx)
        
        # ram start
        data_ptr = self.data.ram_to_rom(self.ram)
        self.data.write_word(self.data.ram_to_rom(constants.ram_world_macro_tiles_table + self.idx * 2), self.ram)
        
        # tile counts
        self.data.write_byte(data_ptr, len(self.med_tiles))
        data_ptr += 1
        
        self.data.write_byte(data_ptr, len(self.macro_tiles))
        data_ptr += 1
        
        # med-tiles
        next_data_ptr = data_ptr
        for med_tile in self.med_tiles:
            for j in range(4):
                self.data.write_byte(data_ptr + len(self.med_tiles) * j, med_tile[j])
            data_ptr += 1
            next_data_ptr += 4
        data_ptr = next_data_ptr
        
        # med-tile palette data
        palette_start = data_ptr
        for i in range(len(self.med_tiles) + constants.global_med_tiles_count):
            data_ptr = palette_start + (i // 4)
            bit = (i % 4) * 2
            bprev = self.data.read_byte(data_ptr)
            bprev &= ~(0x3 << bit)
            bprev |= self.med_tile_palettes[i] << bit
            data_ptr += 1 # if loop ends here.
        
        # macro-tiles
        next_data_ptr = data_ptr
        for macro_tile in self.macro_tiles:
            for j in range(4):
                self.data.write_byte(data_ptr + len(self.macro_tiles) * j, macro_tile[j])
            data_ptr += 1
            next_data_ptr += 4
        data_ptr = next_data_ptr
        
        # palettes
        bs = BitStream(self.data.bin, data_ptr)
        for i in range(8):
            for j in range(3):
                b = self.palettes[i][j + 1]
                bs.write_bits(b, 6)
        
        return True

class MusicLabel:
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr

class MusicOp:
    def __init__(self, op, args=None):
        self.op = op # string
        self.args = [] if args == None else args # array of strings
        self.argtypes = [None] * len(self.args)
    
    def get_duration_idx(self, music):
        assert(self.op == constants.note_opcode["name"])
        duration = int(self.args[1], 16)
        for i in range(0x8):
            if music.data.read_byte(music.data.ram_to_rom(constants.ram_music_duration_table) + i) == duration:
                return i
        assert(False)
        return 0
    
    def get_nibbles(self, music, address):
        nibbles = []
        if self.op == constants.note_opcode["name"]:
            nibbles.append(self.get_duration_idx(music))
            # duration
            type = self.args[0]
            if type == "_":
                nibbles.append(0xd)
            elif type == "*":
                nibbles.append(0xe)
            else:
                nibbles.append(int(type, 16))
            return nibbles
        else:
            for opdata in constants.music_opcodes:
                if opdata["name"] == self.op:
                    opc = constants.music_opcodes.index(opdata)
                    nibbles.append(opc)
                    
                    # opcodes in the range 0-8 must be followed by 0xF, or else
                    # they are interpreted as notes.
                    if opc < 8:
                        nibbles.append(0xF)
                    
                    # write args
                    for i in range(len(self.args)):
                        arg = self.args[i]
                        argtype = self.argtypes[i]
                        if argtype == 1:
                            nibbles.append(int(arg, 16))
                        if argtype == 2:
                            nibbles.append((int(arg, 16) & 0xf0) >> 4)
                            nibbles.append(int(arg, 16) & 0x0f)
                        if argtype == "abs":
                            if address is None:
                                nibbles += [None, None, None]
                            else:
                                addr = music.resolve_address(arg)
                                nibbles.append(addr & 0x00f)
                                nibbles.append((addr & 0x0f0) >> 4)
                                nibbles.append((addr & 0xf00) >> 8)
                        if argtype == "rels":
                            if address is None:
                                nibbles += [None, None]
                            else:
                                addr = address + len(nibbles) + 2 - music.resolve_address(arg)
                                assert(addr in range(0x100))
                                nibbles.append(addr & 0x0f)
                                nibbles.append((addr & 0xf0) >> 4)
                    
                    return nibbles
            
            # opcode not found
            assert(False)
            return []

class Music:
    def __init__(self, data):
        self.data = data
        self.songs = constants.songs
        self.song_tempos = [0] * len(self.songs)
        self.song_channel_entries = [["" for i in range(4)] for j in range(len(self.songs))]
        self.label_to_addr = dict()
        self.code = []
        self.code_start = 0x8000
        
    def resolve_address(self, arg):
        if arg in self.label_to_addr:
            return self.label_to_addr[arg].addr
        if arg[0] == "$":
            return int(arg[1:], 16)
        assert(False)
        return 0
    
    # TODO: optimize this with a datastructure..?
    def get_labels(self, addr):
        labels = []
        for labelstr, label in self.label_to_addr.items():
            if label.addr == addr:
                labels.append(label)
        return labels
    
    def read(self):
        rom_music_start = self.data.ram_to_rom(constants.ram_range_music[0])
        bs = BitStream(self.data.bin, rom_music_start)
        for idx in range(len(self.songs)):
            # tempo
            self.song_tempos[idx] = bs.read_bits(4)
            
            # track entry labels
            entry_pcs = [0] * 4
            for i in range(4):
                entry_pcs[3 - i] = 0
                for j in range(3):
                    entry_pcs[3 - i] >>= 4
                    entry_pcs[3 - i] |= bs.read_bits(4) << 8
            
            # create a label for this
            for i in range(4):
                labelstr = "entry_" + self.songs[idx] + "_" + constants.mus_vchannel_names[i]
                self.song_channel_entries[idx][i] = labelstr
                self.label_to_addr[labelstr] = MusicLabel(labelstr, entry_pcs[i])
        
        self.code = []
        self.code_start = bs.get_nibble_offset(rom_music_start)
        
        # read opcodes
        while bs.offset < self.data.ram_to_rom(constants.ram_range_music[1]):
            opc = bs.read_bits(4)
            opdata = constants.music_opcodes[opc]
            if opc < 8:
                postfix = bs.read_bits(4)
                if postfix != 0xF:
                    # play / hold a note.
                    duration = self.data.read_byte(self.data.ram_to_rom(constants.ram_music_duration_table) + opc)
                    name = constants.note_opcode["name"]
                    arg = HX(postfix)
                    if postfix == 0xd:
                        arg = "_" # tie?
                    if postfix == 0xe:
                        arg = "*"
                    self.code.append(MusicOp(constants.note_opcode["name"], [arg, HX(duration)]))
                    # process next opcode
                    continue
                else:
                    # treat opc as a standard opcode in the 0-7 inclusive range.
                    pass
            
            # standard opcode
            op = MusicOp(opdata["name"])
            if "argc" in opdata:
                for argtype in opdata["argc"]:
                    op.argtypes.append(argtype)
                    if type(argtype) == type(0):
                        # a number -- read this many nibbles
                        n = bs.read_bits(4 * argtype)
                        op.args.append(HX(n))
                        continue
                    addr = bs.get_nibble_offset(rom_music_start)
                    labelname = "label"
                    if argtype == "abs":
                        for j in range(3):
                            addr >>= 4
                            addr |= bs.read_bits(4) << 8
                        addr &= 0xffffff
                    elif argtype == "rels":
                        labelname = op.op.lower()[:3]
                        a = bs.read_bits(4)
                        a |= bs.read_bits(4) << 4
                        addr += 2 # due to the nibbles read.
                        addr -= a
                    
                    if addr / 2 + constants.ram_range_music[0] < constants.ram_range_music[1]:
                        labelname += HX(addr)
                        if labelname not in self.label_to_addr:
                            self.label_to_addr[labelname] = MusicLabel(labelname, addr)
                        op.args.append(labelname)
                    else:
                        op.args.append("$" + HW(addr)[1:])
                        
            self.code.append(op)
    
    def commit(self):
        bs = BitStream(self.data.bin, self.data.ram_to_rom(constants.ram_range_music[0]))
        
        for idx in range(len(self.songs)):
            # tempo
            bs.write_bits(self.song_tempos[idx], 4)
            
            # address of vchannel entry
            for i in reversed(range(4)):
                addr = self.resolve_address(self.song_channel_entries[idx][i])
                for j in range(3):
                    bs.write_bits(addr >> (j * 4), 4)
        
        # code
        for op in self.code:
            addr = bs.get_nibble_offset(self.data.ram_to_rom(constants.ram_range_music[0]))
            for nibble in op.get_nibbles(self, addr):
                # bounds check
                assert(bs.offset < self.data.ram_to_rom(constants.ram_range_music[1]))
                bs.write_bits(nibble, 4)
        
        return True

class TitleScreen:
    def __init__(self, data):
        self.data = data
        self.table = []
        self.palettes = []
        self.palette_idxs = []
        self.ptr_offset_z = 8
        self.ptr_count_z = 5
    
    def size(self):
        # hacky implementation
        # writes to data and then checks the bitstream.
        # FIXME: not sure why adding 4 is necessary...
        return self.write()[1] - self.data.ram_to_rom(constants.ram_range_title_screen[0]) + 4
    
    def write(self):
        bs = BitStream(self.data.bin, self.data.ram_to_rom(constants.ram_range_title_screen[0]))
        table = self.table[0] + self.palette_idxs[0] + self.table[1] + self.palette_idxs[1]
        
        # Lempel-Ziv compression, more or less
        
        # TODO: this can be optimized further.
        i = 0
        while i < len(table):
            # search for longest prefix
            best_prefix = (0, 0) # (start, length)
            for j in range(max(0, i - (1 << self.ptr_offset_z)), i):
                assert(j < i)
                l = common_prefix_length(table[i:], table[j:], min(len(table) - i, (1 << self.ptr_count_z)))
                if l > best_prefix[1]:
                    best_prefix = (j, l)
            
            # discard if too short
            # 1 is always too short, because it could be done as a new byte instead (8 bits)
            if best_prefix[1] <= 1:
                best_prefix = (0, 0)
            
            # consider discarding if enough zeros to not make it worth it...
            if best_prefix[1] <= 2 + self.ptr_count_z + self.ptr_offset_z:
                altsize = 0
                for t in table[best_prefix[0]:best_prefix[0] + best_prefix[1]]:
                    altsize += (1 if t == 0 else 8)
                if altsize <= 2 + self.ptr_count_z + self.ptr_offset_z:
                    best_prefix = (0, 0)
            
            # how long is the following chain of zeros?
            best_zeros = common_prefix_length(table[i:], [0] * 0x100, min(len(table) - i, 0x100))
            
            # which compression should we use for the following substring?
            if best_zeros <= 2 + self.ptr_count_z + self.ptr_offset_z and best_zeros >= best_prefix[1] and best_zeros > 0:
                for j in range(best_zeros):
                    bs.write_bit(0)
                    i += 1
            elif best_zeros > 2 + self.ptr_count_z + self.ptr_offset_z + 2 and best_zeros > best_prefix[1] and i > 0 and table[i - 1] != 0:
                # permits good RLE compression on next pass.
                bs.write_bit(0)
                i += 1
            elif best_prefix[1] > 1:
                # write reference
                bs.write_bit(1)
                bs.write_bit(1)
                
                # location difference
                bs.write_bits(i - best_prefix[0] - 1, self.ptr_offset_z)
                
                # length
                bs.write_bits(best_prefix[1] - 1, self.ptr_count_z)
                
                i += best_prefix[1]
            else:
                # write literal byte
                bs.write_bit(1)
                bs.write_bit(0)
                bs.write_bits(table[i], 8)
                i += 1
        
        # bounds check
        if bs.offset + (bs.bitoffset / 8) > self.data.ram_to_rom(constants.ram_range_title_screen[1]):
            self.data.errors += ["screen data exceeds range (" + HX(math.ceil(bs.offset + (bs.bitoffset / 8))) + " > " + HX(self.data.ram_to_rom(constants.ram_range_title_screen[1])) + ")" ]
            return False, math.ceil(bs.offset + (bs.bitoffset / 8))
        return True, math.ceil(bs.offset + (bs.bitoffset / 8))
    
    def get_tile(self, x, y, k=0):
        idx = x + y * 32
        if idx < 0 or idx >= len(self.table[k]):
            return 0
        else:
            return self.table[idx]
    
    def set_tile(self, x, y, t, k=0):
        idx = x + y * 32
        if idx < 0 or idx >= len(self.table[k]):
            pass
        else:
            self.table[idx] = t
            
    def get_palette_idx(self, x, y, k=0):
        #y += 1
        x *= 0x8
        y *= 0x8
        if k == 0:
            palette_i = (x // 0x20) % 8 + ((y + 0x8) // 0x20) * 8 - 0x1d
            palette_sub_i = ((x // 0x10) % 2) + 2 * (((y + 0x8) // 0x10) % 2)
        else:
            y -= 0x8 # unknown where this comes from.
            x += 0x20 # also unknown
            palette_i = (x // 0x20) % 8 + (y // 0x20) * 8
            palette_sub_i = ((x // 0x10) % 2) + 2 * (((y) // 0x10) % 2)
        return 0 if palette_i >= len(self.palette_idxs[k]) or palette_i < 0 else (self.palette_idxs[k][palette_i] >> (2 * (palette_sub_i))) & 0x3
        
    def set_palette_idx(self, x, y, palette_idx, k=0):
        #y += 1
        x *= 0x8
        y *= 0x8
        if k == 0:
            palette_i = (x // 0x20) % 8 + ((y + 0x8) // 0x20) * 8 - 0x1d
            palette_sub_i = ((x // 0x10) % 2) + 2 * (((y + 0x8) // 0x10) % 2)
        else:
            y -= 0x8 # unknown where this comes from.
            x += 0x20 # also unknown
            palette_i = (x // 0x20) % 8 + (y // 0x20) * 8
            palette_sub_i = ((x // 0x10) % 2) + 2 * (((y) // 0x10) % 2)
        if palette_i < len(self.palette_idxs[k]) and palette_i >= 0:
            mask = 0x3 << (palette_sub_i * 2)
            b = palette_idx << (palette_sub_i * 2)
            self.palette_idxs[k][palette_i] &= ~mask
            self.palette_idxs[k][palette_i] |= b & mask
    
    def read(self):
        bs = BitStream(self.data.bin, self.data.ram_to_rom(constants.ram_range_title_screen[0]))
        table = []
        
        # Lempel-Ziv decompression, more or less
        # FIXME: does this loop have the right condition?
        while bs.get_next_byte_to_read() < self.data.ram_to_rom(constants.ram_range_title_screen[1]):
            isblank = bs.read_bits(1) == 0
            if isblank:
                table.append(0)
            else:
                ispointer = bs.read_bits(1) == 1
                if ispointer:
                    sub = bs.read_bits(self.ptr_offset_z) + 1
                    count = bs.read_bits(self.ptr_count_z) + 1
                    for i in range(count):
                        if len(table) <= sub:
                            table.append(0)
                        else:
                            table.append(table[-sub])
                else:
                    b = bs.read_bits(8)
                    table.append(b)

        # interpret
        self.palette_idxs = [None] * 2
        self.table = [None] * 2
        self.palette_idxs[0] = table[constants.title_screen_tile_count[0]:constants.title_screen_tile_count[0] + constants.title_screen_palette_idx_count[0]]
        self.table[0] = table[:constants.title_screen_tile_count[0]]
        self.palette_idxs[1] = table[-constants.title_screen_palette_idx_count[1]:]
        self.table[1] = table[constants.title_screen_tile_count[0] + constants.title_screen_palette_idx_count[0]:-constants.title_screen_palette_idx_count[1]]
        
        # palettes
        self.palettes = [[], []]
        for k in range(2):
            bs = BitStream(self.data.bin, self.data.ram_to_rom(constants.ram_range_title_screen_palette[k][0]))
            for i in range(4):
                palette = [0xf]
                for j in range(3):
                    palette.append(bs.read_bits(6))
                self.palettes[k].append(palette)

class TextData:
    def __init__(self, data):
        self.data = data
        self.text = []
        self.table = constants.text_lookup
    
    def read(self):
        for i in range(29):
            bs = BitStream(self.data.bin, self.data.ram_to_rom(constants.ram_range_text[0]))
            text = ""
            # skip to marker
            for j in range(i + 1):
                while bs.read_bits(5) != 1:
                    pass
            
            # read text
            while True:
                b = bs.read_bits(5)
                if b == 0:
                    text += " "
                elif b == 1:
                    #done
                    self.text.append(text)
                    break
                elif b == 2:
                    # rare two-byte character
                    b = bs.read_bits(5)
                    text += self.table[b + 0x1a]
                elif b == 3:
                    text += "%"
                else:
                    text += self.table[b - 4]
        
    def write(self):
        bs = BitStream(self.data.bin, self.data.ram_to_rom(constants.ram_range_text[0]))
        unique_diacritics = []
        for text in self.text:
            # start-of-text marker
            bs.write_bits(1, 5)
            
            j = -1
            while True:
                j = j + 1
                if j >= len(text):
                    break
                t = text[j]
                if t == " ":
                    bs.write_bits(0, 5)
                elif t == "%" or t == "\n":
                    bs.write_bits(3, 5)
                else:
                    if t == "\\":
                        # escape characters
                        if text[j + 1] == "\\":
                            j = j + 1
                        elif text[j + 1] == "d":
                            t = text[j+1:j+4]
                            j = j + 3
                    if t in self.table:
                        i = self.table.index(t)
                        if i <= 0x1b:
                            # common character
                            assert(i + 4 < 0x20)
                            bs.write_bits(i + 4, 5)
                        else:
                            # extended character
                            bs.write_bits(2, 5)
                            assert(i - 0x1a < 0x13)
                            bs.write_bits(i - 0x1a, 5)
                    elif len(t) == 3 and t[0] == "d":
                        if self.data.mapper_extension:
                            diacritic = int(t[1:], 16)
                            if diacritic not in unique_diacritics:
                                unique_diacritics.append(diacritic)
                                if len(unique_diacritics) > src.mappermages.diacritics_table_range[1] - src.mappermages.diacritics_table_range[0]:
                                    self.data.errors += ["Too many unique diacritics. Please use fewer types of diacritics."]
                                    return False
                                addr = src.mappermages.diacritics_table_range[0] + len(unique_diacritics) - 1
                                self.data.write_byte(self.data.ram_to_rom(addr), diacritic)
                            # extended character: diacritic.
                            bs.write_bits(2, 5)
                            outb = 0x13 + unique_diacritics.index(diacritic)
                            bs.write_bits(outb, 5)
                        else:
                            self.data.errors += ["Invalid text symbol: \"" + t + "\"\nTo enable diacritics, please set the mapper_extension mod to true."]
                            return False
                    else:
                        self.data.errors += ["Invalid text symbol: \"" + t + "\"\nTo add new symbols, please export images, edit chr-rom, then reimport chr-rom."]
                        return False
            
        # bounds check
        if bs.offset + (bs.bitoffset / 8) > self.data.ram_to_rom(constants.ram_range_text[1]):
            self.data.errors += ["text section exceeds range (" + HX(math.ceil(bs.offset + (bs.bitoffset / 8))) + " > " + HX(self.data.ram_to_rom(constants.ram_range_text[1])) + ")" ]
            return False
        return True
            
class MMData:
    # convert ram address to rom address
    def ram_to_rom(self, address, chunk=""):
        if self.mapper_extension and len(self.bin) > 0xa010:
            if chunk == "" and address >= 0xc000:
                address += src.mappermages.EXTENSION_LENGTH
            if chunk == "level":
                return 0x10 + (address - 0x8000 + 0x4000)
        return 0x10 + (address - 0x8000)
        
    def chr_to_rom(self, address):
        return 0x10 + 0x8000 + address + (src.mappermages.EXTENSION_LENGTH if self.mapper_extension and len(self.bin) > 0xa010 else 0)
    
    def commit_bank_extension(self):
        # edit header
        self.bin[0x4] = (src.mappermages.EXTENSION_LENGTH // 0x4000) + 2 # prg ROM banks
        self.bin[0x5] = 0x01 # chr ROM banks (unchanged)
        self.bin[0x6] = 0x20 # mapper
        
        # inserts two banks
        self.bin[0x4010:0x4010] = bytearray(src.mappermages.EXTENSION_LENGTH)
    
    def read_nibble(self, addr, offset):
        b = self.bin[addr + (offset // 2)]
        if offset % 2 == 1:
            return self.bin[addr + (offset // 2)] & 0xf
        else:
            return self.bin[addr + (offset // 2)] >> 4
        
    def read_byte(self, addr):
        return int(self.bin[addr])
        
    def read_word(self, addr):
        return int(self.bin[addr]) + int(self.bin[addr + 1] * 0x100)    
        
    def write_nibble(self, addr, offset, val):
        val = clamp_hoi(val, 0, 0x10)
        b = self.bin[addr + (offset // 2)]
        if offset % 2 == 0:
            b = (b & 0x0f) | (val << 4)
        else:
            b = (b & 0xf0) | val
        
        self.write_byte(self, addr + (offset // 2), b)
        
    def write_byte(self, addr, b):
        if self.bin[addr] != b:
            if breakpoint_on_byte_edit:
                print("(brx) change on byte", HX(addr) + ":", HB(self.bin[addr]), "->", HB(b))
                breakpoint()
                pass
        self.bin[addr] = b
    
    def write_word(self, addr, w):
        self.write_byte(addr,     w & 0x00ff)
        self.write_byte(addr + 1, (w & 0xff00) >> 8)
    
    def write_patch(self, rom, bytes):
        for b in bytes:
            self.write_byte(rom, b)
            rom += 1

    def errors_string(self):
        errors = self.errors
        self.errors = []
        if len(errors) == 0:
            return None
        elif len(errors) == 1:
            return errors[0]
        else:
            s = "The following errors occurred:"
            for err in errors:
                s += "\n  - " + err;
            return s;

    # read chr data at offet into an array
    def chr_to_array(data, chr_ram):
        arr = [[0 for x in range(8)] for y in range(8)]
        for y in range(8):
            l = data.read_byte(data.chr_to_rom(chr_ram + y))
            u = data.read_byte(data.chr_to_rom(chr_ram + y + 8))
            for x in range(8):
                bl = (l >> (7 - x)) & 0x1
                bu = (u >> (7 - x)) & 0x1
                arr[y][x] = (bu << 1) | (bl)
        return arr

    # write chr data from array at offset
    def array_to_chr(data, chr_ram, arr):
        for k in range(2):
            for y in range(8):
                a = data.chr_to_rom(chr_ram + y + 8*k)
                v = 0
                for x in range(8):
                    b = (arr[y][x] >> k) & 1
                    v <<= 1
                    v |= b
                data.write_byte(a, v)
    
    def set_chr_from_bin(self):
        # array indices:
        # chr[page][image][y][x]
        self.chr = [
            [
                self.chr_to_array(b * 0x1000 + img * 0x10)
                for img in range(0x100)
            ] for b in range(2)
        ]
    
    def store_chr_in_bin(self):
        for b, page in enumerate(self.chr):
            for i, img in enumerate(page):
                self.array_to_chr(b * 0x1000 + i * 0x10, img)

    def chr_row_to_short(self, row):
        num = 0
        for pix in row:
            num <<= 2
            num |= pix
        return num

    def chr_short_to_row(self, short):
        row = []
        for i in range(8):
            row = [short & 3] + row
            short >>= 2
        return row
    
    def read(self, file):
        self.errors = []
        if not os.path.exists(file):
            self.errors += ["No such ROM file: " + file]
            return False
        with open(file, "rb") as f:
            self.orgbin = f.read()
            self.bin = bytearray(self.orgbin)
            
            # check length
            if len(self.bin) < 0xa010:
                self.errors += ["ROM \"" + file + "\" is too small. Is it a valid ROM?"]
                return False
            
            # check hash
            hasher = hashlib.md5()
            hasher.update(self.bin)
            hashval = str(hasher.hexdigest())
            if hashval not in constants.base_hashes:
                self.errors += ["ROM \"" + file + "\" has an unexpected hash (" + hashval + "); is this an unmodified base ROM?"]
                # don't fail; just use this as a warning.
                
            if len(self.bin) <= 0x10:
                self.errors += ["NES file " + filepath + " is empty."]
                return False
                
            if len(self.bin) != 0xa010:
                self.errors += ["NES file must be exactly 0xa010 in size. (Mapper changes can be applied by " + constants.mmname + ", but cannot be read.)"]
                return False
            
            self.levels = []
            self.spawnable_objects = []
            self.macro_tiles = [] # array of [tl, tr, bl, br]
            self.med_tiles = [] # array of [tl, tr, bl, br]
            self.worlds = []
            self.mirror_pairs = []
            self.chest_objects = []
            self.sprite_palettes = []
            
            # read special mods
            self.mods = dict()
            self.mods["no_bounce"] = self.read_byte(self.ram_to_rom(constants.ram_mod_bounce)) == constants.ram_mod_bounce_replacement[0]
            self.mods["no_auto_scroll"] = self.read_byte(self.ram_to_rom(constants.ram_mod_no_auto_scroll[0])) == constants.ram_mod_no_auto_scroll_replacement[0][0]
            self.mods["extended_objects"] = False
            self.mods["no_relic_1"] = False
            self.mods["no_relic_2"] = False
            self.mods["no_relic_3"] = False
            self.mods["no_relic_4"] = False
            self.mapper_extension = False
            
            self.pause_text = [self.read_byte(self.ram_to_rom(constants.ram_range_uncompressed_text[0] + i)) for i in range(5)]
            self.pause_text_offset = self.read_byte(self.ram_to_rom(constants.ram_pause_text_offset))
            
            self.title_screen_press_start_text_position = self.read_byte(self.ram_to_rom(constants.title_screen_press_start_text_position[0])) * 0x100 + self.read_byte(self.ram_to_rom(constants.title_screen_press_start_text_position[1]))
            self.title_screen_players_text_position = self.read_byte(self.ram_to_rom(constants.title_screen_players_text_position[0])) * 0x100 + self.read_byte(self.ram_to_rom(constants.title_screen_players_text_position[1]))
            
            # read CHR
            self.set_chr_from_bin()
            
            # read number of lives
            self.default_lives = self.read_byte(self.ram_to_rom(constants.ram_default_lives))
            
            # read palettes
            bs = BitStream(self.bin, self.ram_to_rom(constants.ram_sprite_palette_table))
            for i in range(4):
                palette = [0xf]
                for j in range(3):
                    palette.append(bs.read_bits(6))
                self.sprite_palettes.append(palette)
            
            # read spawnable objects list
            for i in range(0x1F):
                self.spawnable_objects.append(self.read_byte(self.ram_to_rom(constants.ram_object_i_gid_lookup + i)))
            
            # read med-tile mirror pairs table
            for i in range(constants.mirror_pairs_count):
                pair = [self.read_byte(self.ram_to_rom(constants.ram_mirror_pairs_table) + j * constants.mirror_pairs_count + i) for j in range(2)]
                self.mirror_pairs.append(pair)
            
            # read chest item table
            for i in range(constants.ram_chest_table_length):
                self.chest_objects.append(self.read_byte(self.ram_to_rom(constants.ram_chest_table + i)))
                
            # read object-specific data
            for cfg in self.object_config:
                if cfg is not None:
                    cfg.read()
                
            # read global med-tile types (how 16x16 tiles can be composed of 8x8 tiles)
            med_corner_ptrs = [0, 0, 0, 0]
            for i in range(4):
                med_corner_ptrs[i] = self.read_word(self.ram_to_rom(constants.ram_med_tiles_table + 2 * i))
            for i in range(constants.global_med_tiles_count):
                self.med_tiles.append([
                    self.read_byte(self.ram_to_rom(med_corner_ptrs[j] + i)) for j in range(4)
                ])
                    
            # read global macro-tile types (how 32x32 tiles can be composed of 16x16 tiles)
            macro_corner_ptrs = [0, 0, 0, 0]
            for i in range(4):
                macro_corner_ptrs[i] = self.read_word(self.ram_to_rom(constants.ram_macro_tiles_table + 2 * i))
            for i in range(constants.global_macro_tiles_count):
                self.macro_tiles.append([
                    self.read_byte(self.ram_to_rom(macro_corner_ptrs[j] + i)) for j in range(4)
                ])
            
            # read worlds
            for i in range(constants.world_count):
                world = World(self, i)
                world.read()
                self.worlds.append(world)
                
            # read levels
            for level_idx in range(constants.level_count):
                self.levels.append(
                    Level(
                        self,
                        level_idx
                    )
                )
                self.levels[-1].read()
            
            # read music data
            self.music = Music(self)
            self.music.read()
            
            # read title screen data
            self.title_screen = TitleScreen(self)
            self.title_screen.read()
            
            # read text data
            self.text = TextData(self)
            self.text.read()
                
            return True
        self.errors += ["Failed to open file \"" + file + "\" for reading."]
        return False
    
    def has_mod(self, mod):
        return mod in self.mods and self.mods[mod]
    
    # edits the binary data to be in line with everything else
    # required before writing to a binary file.
    def commit(self):
        print("committing")
        # restore bin to original.
        self.bin = bytearray(self.orgbin)

        # possibly add extra banks
        if self.mapper_extension:
            print("mapper extension...")
            self.commit_bank_extension()
        
        # write CHR
        self.store_chr_in_bin()
        
        # write number of lives
        self.write_byte(self.ram_to_rom(constants.ram_default_lives), self.default_lives)
        
        # write palettes
        bs = BitStream(self.bin, self.ram_to_rom(constants.ram_sprite_palette_table))
        for i in range(4):
            for j in range(3):
                bs.write_bits(self.sprite_palettes[i][j + 1], 6)
        
        # write spawnable objects list
        for i in range(len(self.spawnable_objects)):
            self.write_byte(self.ram_to_rom(constants.ram_object_i_gid_lookup + i), self.spawnable_objects[i])
            
        # write med-tile mirror pairs table
        for i in range(constants.mirror_pairs_count):
            for j in range(2):
                self.write_byte(self.ram_to_rom(constants.ram_mirror_pairs_table) + i + constants.mirror_pairs_count * j, self.mirror_pairs[i][j])
        
        # write chest table
        for i in range(min(constants.ram_chest_table, len(self.chest_objects))):
            self.write_byte(self.ram_to_rom(constants.ram_chest_table + i), self.chest_objects[i])
        
        # write pause text
        self.write_byte(self.ram_to_rom(constants.ram_pause_text_offset), self.pause_text_offset)
        for i in range(5):
            self.write_byte(self.ram_to_rom(constants.ram_range_uncompressed_text[0] + i), self.pause_text[i])
            
        # write title screen text position
        self.write_byte(self.ram_to_rom(constants.title_screen_press_start_text_position[0]), self.title_screen_press_start_text_position // 0x100)
        self.write_byte(self.ram_to_rom(constants.title_screen_press_start_text_position[1]), self.title_screen_press_start_text_position % 0x100)
        self.write_byte(self.ram_to_rom(constants.title_screen_players_text_position[0]), self.title_screen_players_text_position // 0x100)
        self.write_byte(self.ram_to_rom(constants.title_screen_players_text_position[1]), self.title_screen_players_text_position % 0x100)
        
        # write object-specific data
        for cfg in self.object_config:
            if cfg is not None:
                cfg.commit()
        
        # write global med-tile types (how 16x16 tiles can be composed of 8x8 tiles)
        med_corner_ptrs = [0, 0, 0, 0]
        for i in range(4):
            med_corner_ptrs[i] = self.read_word(self.ram_to_rom(constants.ram_med_tiles_table + 2 * i))
        for i in range(constants.global_med_tiles_count):
            for j in range(4):
                self.write_byte(self.ram_to_rom(med_corner_ptrs[j] + i), self.med_tiles[i][j])
        
        # write global macro-tile types (how 32x32 tiles can be composed of 16x16 tiles)
        macro_corner_ptrs = [0, 0, 0, 0]
        for i in range(4):
            macro_corner_ptrs[i] = self.read_word(self.ram_to_rom(constants.ram_macro_tiles_table + 2 * i))
        for i in range(constants.global_macro_tiles_count):
            for j in range(4):
                self.write_byte(self.ram_to_rom(macro_corner_ptrs[j] + i), self.macro_tiles[i][j])
        
        # write worlds
        for world in self.worlds:
            world.commit()
        
        # write levels
        level_ram_location = 0x8000 if self.mapper_extension else constants.ram_range_levels[0]
        unitile_location = src.mappermages.unitile_table_range[0] + 10 * constants.level_count
        for level in self.levels:
            # write level data
            result, level_ram_location = level.commit(level_ram_location)
            if not result:
                return False
            
            # optional unitile extension
            if self.mapper_extension:
                result, unitile_location = level.commit_unitile(unitile_location)
                
                if not result:
                    self.errors += ["Failed to write unitile data."]
                    return False
                
                result, unitile_location = level.commit_drop_objects(unitile_location)
                
                if not result:
                    self.errors += ["Failed to write object drop data."]
                    return False
            
        # level bounds check
        ram_level_end = 0xC000 if self.mapper_extension else constants.ram_range_levels[1]
        if level_ram_location > ram_level_end:
            self.errors += ["level space exceeded (" + HX(level_ram_location) + " > " + HX(ram_level_end) + ")"]
            return False
        
        if self.mapper_extension:
            if unitile_location > src.mappermages.unitile_table_range[1]:
                self.errors += ["unitile (med-tile patch) space exceeded (" + HX(unitile_location) + " > " + HX(src.mappermages.unitile_table_range[1]) + ")"]
                return False
        
        # write music
        if not self.music.commit():
            return False
            
        # write title screen
        if not self.title_screen.write():
            return False
        
        # write text
        if not self.text.write():
            return False
                
        # patches over
        if self.mods["no_bounce"]:
            self.write_patch(
                self.ram_to_rom(constants.ram_mod_bounce),
                constants.ram_mod_bounce_replacement
            )
        if self.mods["no_auto_scroll"]:
            for i in range(len(constants.ram_mod_no_auto_scroll)):
                self.write_patch(
                    self.ram_to_rom(constants.ram_mod_no_auto_scroll[i]),
                    constants.ram_mod_no_auto_scroll_replacement[i]
                )
        if self.mods["no_relic_1"]:
            self.write_patch(
                self.ram_to_rom(constants.ram_mod_no_relic_1[0]),
                constants.ram_mod_no_relic_1_replacement[0]
            )
        if self.mods["no_relic_2"]:
            self.write_patch(
                self.ram_to_rom(constants.ram_mod_no_relic_2[0]),
                constants.ram_mod_no_relic_2_replacement[0]
            )
        if self.mods["no_relic_3"]:
            self.write_patch(
                self.ram_to_rom(constants.ram_mod_no_relic_3[0]),
                constants.ram_mod_no_relic_3_replacement[0]
            )
        if self.mods["no_relic_4"]:
            self.write_patch(
                self.ram_to_rom(constants.ram_mod_no_relic_4[0]),
                constants.ram_mod_no_relic_4_replacement[0]
            )
        if self.mapper_extension:
            src.mappermages.patch(self.bin)
        if self.mods["extended_objects"]:
            for i in range(len(constants.ram_mod_extended_objects)):
                # requires slight modification to be compatible with mapper extension
                if not self.mapper_extension and i == 2:
                    continue
                self.write_patch(
                    self.ram_to_rom(constants.ram_mod_extended_objects[i]),
                    constants.ram_mod_extended_objects_replacement[i]
                )
        
        return True
        
    def write(self, file):
        self.errors = []
        try:
            if not self.commit():
                return False
            with open(file, "wb") as nes:
                nes.write(self.bin)
                return True
            self.errors += ["Failed to open file \"" + file + "\" for writing."]
            return False
        finally:
            # restore bin to original.
            self.bin = bytearray(self.orgbin)
        
    def write_ips(self, file):
        self.errors = []
        if self.mapper_extension:
            self.errors += ["IPS is not available when mapper-extension is enabled."]
            return False
        if not self.commit():
            return False
        rval = src.ips.create_patch(self.orgbin, self.bin, file)
        if not rval:
            self.errors += ["Failed to export IPS patch."]
        return rval

    def write_bps(self, file):
        self.errors = []
        if not self.commit():
            return False
        try:
            src.bps.create_patch(self.orgbin, self.bin, file)
        except Exception as e:
            self.errors += ["Failed to export BPS patch: " + str(e)]
            return False
        return True
    
    def __init__(self):
        self.mapper_extension = False
        self.bin = None
        self.errors = []
        self.object_config = [
            constants.object_data[gid]["config"](self, gid) if "config" in constants.object_data[gid] else None
            for gid in range(len(constants.object_data))
        ]
        pass
        
    def get_object_name(self, gid):
        str = ""
        if gid < len(constants.object_names):
            str = constants.object_names[gid][0]
        if str == "":
            str = "unk-" + hb(gid)
        return str
        
    def stat_spawnstr(self, spawnable):
        return "[" + ", ".join('"' + self.get_object_name(gid) + '"' for gid in spawnable) + "]"
        
    # write data to a human-readable hack.txt file
    def stat(self, fname=None, oall=False):
        out=print
        file = None        
        try:
            if fname is not None:
                file = open(fname, "w")
                out = functools.partial(stat_out, file)
            
            self.commit()

            out("# Micro Mages Hack File")
            out()
            out("# This file can be opened using MMagEdit, available here:")
            out("#", constants.mmrepo)
            out()
            out("format " + str(constants.mmfmt))
            out()
            out("-- config --")
            out()
            #config
            out("{")
            out('  # Default number of lives.')
            out('  "lives":    ', str(self.default_lives) + ",")
            out()
            out('  # objects which can be spawned using the compressed format.')
            out('  # Length must be exactly 16.')
            out('  "spawnable":    ', self.stat_spawnstr(self.spawnable_objects[:0x10]) + ",")
            out()
            out('  # objects which can be spawned using either the compressed or extended object format.')
            out('  # Length must be exactly 15.')
            out('  "spawnable-ext":', self.stat_spawnstr(self.spawnable_objects[0x10:0x1F]) + ",")
            out()
            out('  # objects which can be spawned from a chest (looked up randomly).')
            out('  # the final element of this list can only be spawned on multiplayer.')
            out('  # Length must be exactly 13.')
            out('  "chest-objects":', self.stat_spawnstr(self.chest_objects) + ",")
            out()
            out('  # these med-tiles will be replaced with the given med-tiles when mirrored, and vice versa')
            out('  "mirror-pairs":', json_list(self.mirror_pairs, lambda i : '"' + hb(i) + '"') + ",")
            out()
            out('  # pause text position and pause text (must be 5 characters exactly; use 00 or 01 to end it early)')
            out('  "pause-text":', "[", " ,".join(['"' + hb(i) + '"' for i in self.pause_text]), "],")
            out('  "pause-text-x": "' + hb(self.pause_text_offset) + "\",")
            out()
            out('  # position of title screen text (in ppu ram address format)')
            out('  "title-press-start-text-position":', str(self.title_screen_press_start_text_position) + ",")
            out('  "title-players-text-position":', str(self.title_screen_players_text_position) + ",")
            out()
            out('  # some special mods that can be applied')
            out('  "mods": {')
            for mod in self.mods:
                if mod != "":
                    if self.mods[mod]:
                        out('    "' + mod + '": true,')
                    else:
                        out('    "' + mod + '": false,')
            out('    "mapper-extension": ' + ("true" if self.mapper_extension else "false"))
            out('  }')
            out("}")
            out()
            
            # title screen
            for k in range(2):
                out(["-- title --", "-- ending --"][k])
                out("# data for the title screen and ending screen")
                out("# this is stored with Lempel-Ziv compression, so it's best to try to use repeating structures.")
                out()
                name = ["title screen", "ending screen"][k]
                out("# tiles for", name)
                out("# __ is equivalent to 00.")
                out()
                for i in range(0, len(self.title_screen.table[k]), 0x20):
                    row = self.title_screen.table[k][i:(i+0x20)]
                    s = "T "
                    
                    for j in row:
                        if j == 0:
                            s += "__ "
                        else:
                            s += HB(j) + " "
                    out(s)
                    
                out()
                out("# palette indices for", name)
                for i in range(0, len(self.title_screen.palette_idxs[k]), 0x8):
                    row = self.title_screen.palette_idxs[k][max(i - 0x5, 0):min(i + 0x3, len(self.title_screen.palette_idxs[k]))]
                    s = "P "
                    for j in row:
                        s += HB(j) + " "
                    out(s)
                out()
            
            # config data
            for gid in range(len(self.object_config)):
                cfg = self.object_config[gid]
                if cfg is not None:
                    out("-- object", HX(gid), "--")
                    out("#", constants.object_names[gid][0])
                    out()
                    cfg.stat(out)
            
            # global tile data
            
            out("-- global --")
            
            # text data
            out()
            out("# text data")
            out()
            out("#The letters listed here corresponds to the letters in the CHR-ROM.")
            out("#If you export the chr-rom data, you should see the image data for each")
            out("#character in the same order as they are listed here. You may edit both")
            out("#the chr-rom and the letters listed here to more conveniently edit the game text.")
            out()
            out("# \"short\" letters take 5 bits to store, and \"long\" letters take 10 bits to store.")
            out("# Space (\" \") is always a 5 bit character, and need not be listed here.")
            out()
            out("short " + self.text.table[:24])
            out("long " + self.text.table[24:])
            out()
            for text in self.text.text:
                out(">" + text + "<")
            
            # sprite palettes
            out()
            out("# sprite palettes")
            for i in range(4):
                s = "P" + str(i) + " "
                for j in range(3):
                    s += HX(self.sprite_palettes[i][j + 1]) + " "
                out(s)

            if oall or self.is_dirty("chr"):
                out()
                out("# chr-rom")
                out("# This is the graphics data. Each line is an 8x8 tile or sprite,")
                out("# Comprising 8 low-order pixel data bytes, then 8 high-order.")
                out("# Each pixel is described by two bits: one low, and one high.")
                out("# First come the background tiles (CRB), then the sprites (CRS).")
                out()
                for i in range(0x200):
                    if i == 0x100:
                        # nice and pretty and neat
                        out()
                    
                    if oall or self.is_dirty("chr", chr_idx=i):
                        s = "CRB " if i < 0x100 else "CRS "
                        s += HB(i & 0xff) + ":"
                        for j in range(0x10):
                            if j % 0x8 == 0:
                                # nice, pretty, neat.
                                s += "  "
                            s += " " + HB(self.read_byte(self.chr_to_rom(i * 0x10 + j)))
                        out(s)

            # med-tiles
            out()
            out("# 16x16 med-tile data, common to all worlds")
            out("# details 8x8 micro-tile composition of 16x16 med-tiles")
            out("# m idx: tl tr bl br")
            out()
            for med_idx in range(constants.global_med_tiles_count):
                med_tile = self.med_tiles[med_idx]
                out("m", hb(med_idx) + ":  ", hb(med_tile[0]), hb(med_tile[1]), hb(med_tile[2]), hb(med_tile[3]))
            out()
            
            # macro-tiles
            out("# 32x32 macro tile data common to all worlds")
            out("# details 16x16 med-tile composition of 32x32 macro tiles")
            out("# M idx: tl tr bl br")
            out()
            for macro_idx in range(constants.global_macro_tiles_count):
                macro_tile = self.macro_tiles[macro_idx]
                out("M", hb(macro_idx) + ":  ", hb(macro_tile[0]), hb(macro_tile[1]), hb(macro_tile[2]), hb(macro_tile[3]))
            out()
            
            # worlds
            for world_idx in range(constants.world_count):
                world = self.worlds[world_idx]
                out("-- world", hx(world_idx + 1), "--")
                out("# data from rom " + hex(self.ram_to_rom(world.ram)) + " / ram " + hex(world.ram))
                out()
                out("# palette data")
                for i in range(len(world.palettes)):
                    if i == 4:
                        out("\n# palette data (hard)")
                    s = "P" + hx(i) + ":"
                    for col in world.palettes[i][1:]:
                        s += " " + hb(col)
                    out(s)
                out()
                
                out("# med-tiles (16x16) specific to this world.")
                out("# \"..\" entries are shared between all worlds; only the palette is world-specific.")
                out("# m idx: tl tr bl br   :(palette 0-3)")
                out()
                for med_idx in range(constants.global_med_tiles_count + len(world.med_tiles)):
                    palette = ":" + str(world.med_tile_palettes[med_idx])
                    if (med_idx >= constants.global_med_tiles_count):
                        med_tile = world.med_tiles[med_idx - constants.global_med_tiles_count]
                        out("m", hb(med_idx) + ":  ", hb(med_tile[0]), hb(med_tile[1]), hb(med_tile[2]), hb(med_tile[3]), "  " + palette)
                    else:
                        out("m", hb(med_idx) + ":  ", ".. " * 4, " " + palette)
                        
                    if med_idx == world.max_symmetry_idx - 1:
                        out("~" * 24, "# tiles past this point are considered self-symmetrical")
                out()
                
                out("# macro-tiles (32x32) specific to this world.")
                out("# M idx: tl tr bl br")
                out()
                for macro_idx in range(constants.global_macro_tiles_count + len(world.macro_tiles)):
                    if (macro_idx >= constants.global_macro_tiles_count):
                        macro_tile = world.macro_tiles[macro_idx - constants.global_macro_tiles_count]
                        out("M", hb(macro_idx) + ":  ", hb(macro_tile[0]), hb(macro_tile[1]), hb(macro_tile[2]), hb(macro_tile[3]))
                out()
            
            # levels
            for level_idx in range(constants.level_count):
                out("-- level", hx(level_idx), "--")
                level = self.levels[level_idx]
                
                out("# " + level.get_name())
                
                out("# Level music")
                for i in range(len(self.music.songs)):
                    out("# " + HX(i) + " - \"" + self.music.songs[i] + "\"")
                out("song " + HB(level.music_idx))
                out()
                    
                out("# 32x32 macro-tile rows (from the top/end of the level to bottom/start).")
                out("# Each row is 256x32 pixels.")
                out("# left: seam position (0-f).")
                out("# center: the four macro-tiles (00-7f), mirrored about the seam position.")
                out("# right: optional hardmode patches (1-f or _). An underscore (_) means no patch.")
                out()
                y = len(level.macro_rows)
                for row in reversed(level.macro_rows):
                    y -= 1
                    hmode = "____"
                    for patch in level.hardmode_patches:
                        if patch.i != 0 and y == patch.y:
                            hmode = hmode[:patch.x] + hx(patch.i) + hmode[patch.x + 1:]
                            
                    out(hx(row.seam) + ":", hb(row.macro_tiles[0]), hb(row.macro_tiles[1]), hb(row.macro_tiles[2]), hb(row.macro_tiles[3]), "    " + hmode)
                out()
                
                if self.mapper_extension:
                    out("# unitile (med-tile patch) rows (from top/end of level to bottom/start).")
                    out("# Each row is 256x16 pixels.")
                    out()
                    
                    utrows = level.produce_unitile_rows()
                    for j in range(3):
                        out("# " + ["Normal", "Hard", "Hell"][j] + " mode")
                        for row in reversed(utrows):
                            s = "U" + ["N", "H", "L"][j] + " "
                            for u in row:
                                if u[j] is None:
                                    s += "__ "
                                else:
                                    s += HB(u[j].med_tile_idx) + " "
                            out(s)
                        out()
                
                out("# objects ")
                out("# x and y are in micro-tiles (8 pixels)")
                out("# optional flag -x or -y or -xy to flip the object.")
                out("# mark an object with an asterisk (*) to force it to use the compressed format.")
                out("# compressed format: x must be odd, cannot be flipped, and id must from the spawnable list (not spawnable-ext).")
                out("# The asterisk itself has no effect except that an error is thrown if the object cannot be compressed.")
                if self.mapper_extension:
                    out("# Flag -k can be used to mark the object as an item drop for a crate or chest at the same location (mapper-extension only.)")
                out()
                for obj in sorted(level.objects, key=lambda obj : -obj.y):
                    flags = ""
                    if obj.flipx or obj.flipy or obj.drop:
                        flags = "-" + ("x" if obj.flipx else "") + ("y" if obj.flipy else "") + ("k" if obj.drop else "")
                    pads = " "
                    if obj.compressed:
                        pads = "*"
                    out("-", self.get_object_name(obj.gid) + " " * (10 - len(self.get_object_name(obj.gid))), pads, "x" + hb(obj.x), "y" + hb(obj.y), flags)
                
                out()
            
            # write music headers
            music = self.music
            for song_idx in range(len(music.songs)):
                out("-- song " + HX(song_idx) + " --")
                out()
                out("name " + self.music.songs[song_idx])
                out("tempo " + HB(music.song_tempos[song_idx]))
                out()
                for i in range(4):
                    estr = "entry " + constants.mus_vchannel_names[i] + " "
                    while len(estr) < 0x13:
                        estr += " "
                    out(estr + music.song_channel_entries[song_idx][i])
                out()
            
            # music data
            out("-- music --")
            out()
            
            out("# Sound commands are encoded in an assembly-like language.")
            out("# ")
            out("# Lines ending with a ':' are a label. Labels do not do anything on their own,")
            out("# but other commands can refer to them")
            out("# commands are encoded as an opcode followed by a sequence of arguments.")
            out("# If a label starts with some number of '>' tokens, that means the label is offset")
            out("# into the folling command by the given number of nibbles (half-bytes)")
            out("# ")
            out("# ';' denotes a a comment, and is used to show how the commands are expressed in hex.")
            out("# Anything following a ';' token has no effect.")
            out("# ")
            out("# The following opcode are recognized:")
            out("# ")
            for opcode in [constants.note_opcode] + constants.music_opcodes:
                out("#   " + opcode["name"])
                out("#     " + opcode["doc"])
                out("#")
                
            out("# There are six virtual channels (v-channels): \"Lead\", \"Counterpoint\", \"Triangle\", \"Noise\", \"SFX0\", and \"SFX1\".")
            out("# The first four are musical channels, whereas the last two are for sound effects.")
            out("# Although Lead and Counterpoint are for square0 and square1 respectively, they are treated differently by some opcodes.")
            out("# ")
            out("# A song definition comprises a tempo and one entry label for each of the four musical v-channels.")
            
            addr = music.code_start # address in nibble-offset
            for op in music.code:
                # check for labels
                nl = True
                nibbles = op.get_nibbles(music, addr)
                oaddr = addr
                for nib_idx in range(len(nibbles)):
                    labels = music.get_labels(addr)
                    for label in labels:
                        if nl:
                            out()
                            nl = False
                        out(">" * nib_idx + label.name + ":")
                    addr += 1
                                
                s = "  "
                s += op.op + " "
                if op.op != constants.note_opcode["name"]:
                    while(len(s) < 0xb):
                        s += " "
                for arg in op.args:
                    s += arg + " "
                
                while len(s) < 0x20:
                    s += " "
                s += "; " + HW(oaddr)[1:] + ": " + "".join([HX(nibble) for nibble in nibbles])
                out(s)
            out()
                
            return True
        finally:
            if file is not None:
                file.close()
        return False
    
    def byte_is_dirty(self, address):
        if self.mapper_extension:
            if address > 0x4010 and address <= 0x4010 + src.mappermages.EXTENSION_LENGTH:
                return True # byte nonexistent in orgbin
            if address > 0x4010 + src.mappermages.EXTENSION_LENGTH:
                return self.orgbin[address - src.mappermages.EXTENSION_LENGTH] != self.bin[address]
        return self.orgbin[address] != self.bin[address]
        
    def is_dirty(self, *args, **kwargs):
        if "chr" in kwargs or "chr" in args:
            if "chr_idx" in kwargs:
                chr_idx = kwargs["chr_idx"]
                for i in range(0x10):
                    if self.byte_is_dirty(self.chr_to_rom(i + chr_idx * 0x10)):
                        return True
                return False
            for i in range(0x200):
                if self.is_dirty("chr", chr_idx=i):
                    return True
            return False
            
    # read data from a human-readable hack.txt file
    def parse(self, file):
        self.errors = []
        if not os.path.exists(file):
            self.errors += ["No such hack file: " + file]
            return False
        with open(file, "r") as f:
            
            level = None
            level_idx = 0
            row = 0
            obji = 0
            
            globalstr = ""
            parsing_globals = False
            parsing_globals_complete = True
            level_complete = None
            world = None
            song_idx = None
            music = None
            music_nibble = 0
            cfg = None
            title_screen = None
            
            for line in f.readlines():
                if "#" in line:
                    line = line[:line.index("#")]
                if ";" in line:
                    line = line[:line.index(";")]
                tokens = line.split()
                if len(tokens) > 0:
                    directive = tokens[0]
                    if directive == "--" and len(tokens) >= 3:
                        music = None
                        world = None
                        if level is not None:
                            # optimization.
                            level.combine_unitiles_by_difficulty()
                        level = None
                        song_idx = None
                        cfg = None
                        title_screen = None
                        
                        # configuration
                        if tokens[1] == "config":
                            parsing_globals = True
                            parsing_globals_complete = False
                            globalstr = ""
                            continue
                        else:
                            parsing_globals = False
                        
                        if tokens[1] == "object":
                            cfg = self.object_config[int(tokens[2], 16)]
                        
                        if tokens[1] == "global":
                            self.text.text = []
                            world = None
                            
                        if tokens[1] == "world":
                            world = self.worlds[int(tokens[2], 16) - 1]
                        
                        if tokens[1] == "title":
                            title_screen = self.title_screen
                            if fmt != 202010160900:
                                # (this version had a broken title screen save)
                                title_screen.table[0] = []
                                title_screen.palette_idxs[0] = []
                            screen_idx = 0

                        if tokens[1] == "ending":
                            title_screen = self.title_screen
                            title_screen.table[1] = []
                            title_screen.palette_idxs[1] = []
                            screen_idx = 1
                        
                        if tokens[1] == "song":
                            song_idx = int(tokens[2], 16)
                            
                        if tokens[1] == "music":
                            music = self.music
                            music.label_to_addr = dict()
                            music.code = []
                            music_nibble = music.code_start
                        
                        # start level
                        if tokens[1] == "level":
                            level_idx = int(tokens[2], 16)
                            assert(level_idx < constants.level_count)
                            level_complete = level
                            level = self.levels[level_idx]
                            level.objects = []
                            level.hardmode_patches = []
                            level.unitile_patches = []
                            row = constants.macro_rows_per_level - 1
                            obji = 0
                            unitile_row_idx = [constants.macro_rows_per_level * 2 - 1] * 3
                    
                    # object config is different
                    elif cfg is not None:
                        cfg.parse(tokens)
                        
                        # next line
                        continue
                        
                    # title screen is a bit different
                    elif title_screen is not None:
                        if fmt == 202010160900:
                            # (this version had a broken title screen save)
                            continue
                        if tokens[0] == "T":
                            for token in tokens[1:]:
                                if token == "__":
                                    title_screen.table[screen_idx].append(0)
                                else:
                                    title_screen.table[screen_idx].append(int(token, 16))
                        if tokens[0] == "P":
                            for token in tokens[1:]:
                                title_screen.palette_idxs[screen_idx].append(int(token, 16))
                        continue
                            
                    # music code is different
                    elif music is not None:
                        if tokens[0].endswith(":"):
                            # label
                            label = tokens[0][:-1]
                            
                            # count nibble-offsets (>)
                            offset = 0
                            while label.startswith(">"):
                                label = label[1:]
                                offset += 1
                                
                            assert(len(label) > 0)
                            music.label_to_addr[label] = MusicLabel(label, music_nibble + offset)
                        else:
                            # opcode
                            opname = tokens[0]
                            op = MusicOp(opname)
                            op.args = tokens[1:]
                            if opname != constants.note_opcode["name"]:
                                for opcode in constants.music_opcodes:
                                    if opcode["name"] == opname:
                                        if "argc" in opcode:
                                            op.argtypes = opcode["argc"] + [] # copy the list (paranoia)
                                        break
                            music_nibble += len(op.get_nibbles(music, None))
                            music.code.append(op)
                        
                        # next line
                        continue
                    
                    if directive == "ram":
                        level.ram = int(tokens[1], 16)
                        
                    if directive == "song":
                        level.music_idx = int(tokens[1], 16)
                    
                    # palette data
                    if directive[0] == "P":
                        palette_idx = int(tokens[0][1], 16)
                        for i in range(1, 4):
                            col = int(tokens[i], 16)
                            palette = None
                            if world is None:
                                palette = self.sprite_palettes[palette_idx]
                            else:
                                palette = world.palettes[palette_idx]
                            palette[i] = col

                    if directive == "CRB" or directive == "CRS":
                        idx = int(tokens[1][:2], 16) + (0x100 if directive == "CRS" else 0)
                        for j in range(0x10):
                            if j < len(tokens):
                                self.write_byte(self.chr_to_rom(idx * 0x10 + j), int(tokens[j + 2], 16))
                    
                    if directive == "m":
                        tile_idx = int(tokens[1].replace(":", ""), 16)
                        tile = []
                        palette = None
                        for t in tokens[2:]:
                            if t != ".." and t[0] != ":":
                                tile.append(int(t, 16))
                            if t[0] == ":":
                                palette = int(t[1:], 16)
                        if world == None:
                            self.med_tiles[tile_idx] = tile
                        else:
                            if tile_idx >= constants.global_med_tiles_count:
                                world.med_tiles[tile_idx - constants.global_med_tiles_count] = tile
                            world.med_tile_palettes[tile_idx] = palette
                    
                    if directive[0] == "~":
                        world.max_symmetry_idx = tile_idx + 1
                    
                    # 32x32 macro tile composition
                    if directive == "M":
                        tile_idx = int(tokens[1].replace(":", ""), 16)
                        tile = []
                        for t in tokens[2:]:
                            tile.append(int(t, 16))
                        if world == None:
                            self.macro_tiles[tile_idx] = tile
                        else:
                            world.macro_tiles[tile_idx - constants.global_macro_tiles_count] = tile
                        
                    # tile row
                    if len(directive) == 2 and directive[1] == ":":
                        # row
                        mrow = LevelMacroRow(self)
                        mrow.seam = int(directive[:1], 16)
                        for i in range(1, 5):
                            assert(i < len(tokens))
                            mrow.macro_tiles[i - 1] = int(tokens[i], 16)
                        
                        # hardmode patch
                        if len(tokens) > 5 and len(tokens[-1]) == 4:
                            for x in range(4):
                                p = tokens[-1][x]
                                if p != "_":
                                    patch = HardPatch()
                                    patch.x = x
                                    patch.y = row
                                    patch.i = int(p, 16)
                                    level.hardmode_patches.append(patch)
                                
                            
                        level.macro_rows[row] = mrow
                        row -= 1
                    
                    # unitile patch
                    if directive[0] == "U":
                        j = "NHL".index(directive[1])
                        
                        x = -1
                        for token in tokens[1:]:
                            x += 1
                            if token == "__":
                                continue
                            u = UnitilePatch()
                            u.y = unitile_row_idx[j]
                            u.x = x
                            u.flag_normal = j == 0
                            u.flag_hard = j == 1
                            u.flag_hell = j == 2
                            u.med_tile_idx = int(token, 16)
                            level.unitile_patches.append(u)
                            
                        unitile_row_idx[j] -= 1
                    
                    # object
                    if directive == "-":
                        assert(len(tokens) > 3)
                        obj = Object(self)
                        force_compress = False
                        
                        # look up name.
                        name = tokens[1]
                        if name.startswith("unk-"):
                            obj.gid = int(name[4:], 16)
                        else:
                            assert(name in constants.object_names_to_gid)
                            obj.gid = constants.object_names_to_gid[name]
                        
                        for token in tokens[2:]:
                            if token[0] == "x":
                                obj.x = int(token[1:], 16)
                            if token[0] == "y":
                                obj.y = int(token[1:], 16)
                            if token[0] == "*":
                                force_compress = True
                            if token[0] == "-":
                                if "x" in token:
                                    obj.flipx = True
                                if "y" in token:
                                    obj.flipy = True
                                if "k" in token:
                                    obj.drop = True
                        
                        if not obj.drop:
                            compressible = obj.compressible()
                            if force_compress and not compressible:
                                assert(False)
                            obj.compressed = compressible
                        
                        level.objects.append(obj)
                    
                    if directive == "format" and len(tokens) >= 2:
                        if tokens[1].isdigit():
                            fmt = int(tokens[1])
                        else:
                            # forked versions of MMagEdit should use a non-numeric character to 
                            # identify their version number. Or something.
                            self.errors += ["Hack does not appear to be created with MMagEdit. It cannot be opened with this tool."]
                            return False
                        if fmt > constants.mmfmt:
                            self.errors += ["Hack uses a more recent version of MMagEdit. An update is required."]
                            return False
                        if fmt < constants.mmfmt:
                            # this is a warning, not an error.
                            self.errors += ["Hack uses an older version of MMagEdit. Please be wary of errors or artifacts caused by updating."]
                    
                    # text        
                    if directive == "short":
                        for i in range(len(tokens[1])):
                            self.text.table = self.text.table[:i] + tokens[1][i] + self.text.table[i+1:]
                    if directive == "long":
                        for i in range(len(tokens[1])):
                            self.text.table = self.text.table[:i + 24] + tokens[1][i] + self.text.table[i+25:]
                    if directive[0] == ">":
                        text = line.split(">")[1].split("<")[0]
                        self.text.text.append(text)
                    
                    # song directives
                    if directive == "name" and song_idx is not None:
                        self.music.songs[song_idx] = tokens[1]
                        
                    if directive == "tempo" and song_idx is not None:
                        self.music.song_tempos[song_idx] = int(tokens[1], 16)
                        
                    if directive == "entry" and song_idx is not None:
                        vchannel = constants.mus_vchannel_names.index(tokens[1])
                        self.music.song_channel_entries[song_idx][vchannel] = tokens[2]
                
                if level_complete is not None:
                    level_complete = None
                    
                if parsing_globals:
                    globalstr += line + "\n"
                elif not parsing_globals_complete:
                    config = json.loads(globalstr)
                    if "spawnable" in config and "spawnable-ext" in config:
                        assert(len(config["spawnable"]) == 0x10)
                        assert(len(config["spawnable-ext"]) >= 0xF)
                        self.spawnable_objects = [constants.object_names_to_gid[name] for name in config["spawnable"] + config["spawnable-ext"]]
                        if len(self.spawnable_objects) > 0x1F:
                            self.spawnable_objects = self.spawnable_objects[:0x1F]
                    if "chest-objects" in config:
                        self.chest_objects = [constants.object_names_to_gid[name] for name in config["chest-objects"]]
                    if "lives" in config:
                        self.default_lives = int(config["lives"])
                    if "mirror-pairs" in config:
                        self.mirror_pairs = []
                        for pair in config["mirror-pairs"]:
                            self.mirror_pairs.append([int(i, 16) for i in pair])
                    if "pause-text" in config:
                        self.pause_text = []
                        for c in config["pause-text"]:
                            self.pause_text.append(int(c, 16))
                    if "pause-text-x" in config:
                        self.pause_text_offset = int(config["pause-text-x"], 16)
                    if "title-press-start-text-position" in config:
                        self.title_screen_press_start_text_position = int(config["title-press-start-text-position"])
                    if "title-players-text-position" in config:
                        self.title_screen_players_text_position = int(config["title-players-text-position"])
                    if "mods" in config:
                        for mod in config["mods"]:
                            if mod == "mapper-extension":
                                self.mapper_extension = config["mods"][mod]
                            else:
                                self.mods[mod] = config["mods"][mod]
                    parsing_globals_complete = True
            
            # integrate CHR changes
            self.set_chr_from_bin()

            # correct title screen
            for k in range(2):
                screen_name = ["title screen", "ending screen"][k]
                while len(self.title_screen.table[k]) < constants.title_screen_tile_count[k]:
                    self.title_screen.table[k].append(0)
                if len(self.title_screen.table[k]) > constants.title_screen_tile_count[k]:
                    self.errors += [screen_name + " has too many tiles."]
                    return False
                while len(self.title_screen.palette_idxs[k]) < constants.title_screen_palette_idx_count[k]:
                    self.title_screen.palette_idxs[k].append(0)
                if len(self.title_screen.palette_idxs[k]) > constants.title_screen_palette_idx_count[k]:
                    self.errors += [screen_name + " has too many palette idxs."]
                    return False
            return True
        return False
    
    def serialize_json(self, jsonpath=""):
        return src.jsonpath.extract_json({
            ".format": constants.mmfmt,
            "config": {
                "lives": self.default_lives,
                "spawnable": self.spawnable_objects[:0x10],
                "spawnable-ext": self.spawnable_objects[0x10:],
                "chest-objects": self.chest_objects,
                "mirror-pairs": self.mirror_pairs,
                "pause-text": self.pause_text,
                "pause-text-x": self.pause_text_offset,
                "mods": self.mods,
                "mapper-extension": self.mapper_extension
            },
            # TODO: "screens": self.title_screen.serialize_json(),
            # TODO: global object data
            "text-table-short": self.text.table[:24],
            "text-table-long": self.text.table[24:],
            "text": self.text.text,
            "sprite-palettes": self.sprite_palettes,
            "chr": [
                [
                    [
                        self.chr_row_to_short(row)
                        for row in img
                    ]
                    for img in page
                ]
                for page in self.chr
            ],
            "worlds-common": {
                "med-tiles": self.med_tiles[:constants.global_med_tiles_count],
                "macro-tiles": self.macro_tiles[:constants.global_macro_tiles_count]
            },
            "worlds": [
                world.serialize_json() for world in self.worlds
            ],
            "levels": [
                level.serialize_json() for level in self.levels
            ]
            # TODO: songs and music
        }, jsonpath)
        
    def deserialize_json(self, j):
        for key in j:
            if key.startswith("."):
                self.errors += ["Cannot set '.' fields"]
                return False
            elif key == "config":
                d = j[key]
                for key in d:
                    if key == "lives":
                        self.default_lives = d[key]
                    elif key == "spawnable":
                        self.spawnable_objects = d[key] + self.spawnable_objects[0x10:]
                    elif key == "spawnable-ext":
                        self.spawnable_objects[0x10:] = d[key]
                    elif key == "chest-objects":
                        self.chest_objects = d[key]
                    elif key == "mirror-pairs":
                        self.mirror_pairs = d[key]
                    elif key == "pause-text":
                        self.pause_text = key
                    elif key == "pause-text-x":
                        self.pause_text_offset = key
                    elif key == "mods":
                        self.mods = d[key]
                    elif key == "mapper-extension":
                        self.mapper_extension = d[key]
                    else:
                        self.errors += ["unrecognized key \"" + key + "\""]
                        return False
            elif key == "text-table-short":
                if len(j[key]) != 24:
                    errors += ["text-table-short length must be 24"]
                    return False
                self.text.table = j[key] + self.text.table[24:]
            elif key == "text-table-long":
                self.text.table = self.text.table[:24] + j[key]
            elif key == "text":
                self.text.text = j[key]
            elif key == "sprite-palettes":
                self.sprite_palettes = j[key]
            elif key == "chr":
                c = j[key]
                if len(c) != 2:
                    errors += ["chr must have 2 pages"]
                    return False
                if len(c[0]) != len(self.chr[0]):
                    errors += ["chr page wrong length"]
                    return False
                self.chr = c
            elif key == "worlds-common":
                d = j[key]
                for key in d:
                    if key == "med-tiles":
                        if len(d[key]) != constants.global_med_tiles_count:
                            errors += ["invalid length for common med-tiles"]
                            return False
                        self.med_tiles = d[key]
                    elif key == "macro-tiles":
                        if len(d[key]) != constants.global_macro_tiles_count:
                            errors += ["invalid length for common macro-tiles"]
                            return False
                        self.macro_tiles = d[key]
                    else:
                        self.errors += ["unrecognized key \"" + key + "\""]
                        return False
            elif key == "worlds":
                for world_idx, world in enumerate(j[key]):
                    if world is not None:
                        if not self.worlds[world_idx].deserialize_json(world):
                            return False
            elif key == "levels":
                for level_idx, level in enumerate(j[key]):
                    if level is not None:
                        if not self.levels[level_idx].deserialize_json(level):
                            return False
            else:
                self.errors += ["unrecognized key \"" + key + "\""]
                return False
        return True

    # see json_schema.txt
    def serialize_json_str(self, jsonpath=""):
        return json.dumps(self.serialize_json(jsonpath))

    # returns False if error
    def deserialize_json_str(self, jsonstr):
        return self.deserialize_json(json.loads(jsonstr))