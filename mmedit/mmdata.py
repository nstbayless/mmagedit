from bitstream import BitStream
from util import *
import constants
import json

class ObjectStream:
    def __init__(self):
        self.entries = []
        self.y = constants.objects_start_y # in microtiles (8 pixels)
        self.complete = False
    
    def length_bits(self):
        assert(self.complete)
        l = 0
        for entry in self.entries:
            l += len(entry)
        return l
        
    def length_bytes(self):
        lb = self.length_bits()
        if lb % 8 == 0:
            return lb / 8
        else:
            return int(lb / 8) + 1
        
    def as_bits(self, value, n):
        l = []
        for i in range(n):
            l.append(0 if n & (1 << (n - i - 1)) == 0 else 1)
        return l
    
    def add_object(self, obj):
        assert(not self.complete)
        assert(obj.y <= self.y)
        while obj.y < self.y:
            ydiff = max(1, min(self.y - obj.y, 8))
            self.y -= ydiff
            self.entries.append( [0, 0] + self.as_bits(ydiff - 1, 3) )
        
        if (obj.compressible()):
            self.entries.append( [1, 0] + self.as_bits(int((obj.x - 1) / 2), 4) + self.as_bits(obj.i, 4) )
        else:
            self.entries.append( [0, 1] + [1 if obj.flipx else 0] + [1 if obj.flipy else 0] + self.as_bits(obj.x, 5) + self.as_bits(obj.i, 5) )
    
    def finalize(self):
        assert(not self.complete)
        self.complete = True
        self.entries.append( [1, 1] )

class Object:
    def __init__(self):
        self.i = 0
        self.x = 0 # in microtiles
        self.y = 0 # in microtiles
        self.gid = 0 # lookup (0xdab1),i
        self.name = ""
        self.flipx = False
        self.flipy = False
        self.compressed = False
    
    def compressible(self):
        if self.flipx or self.flipy:
            return False
        if self.i >= 0x10:
            return False
        if self.x % 2 == 0:
            return False
        return True

class HardPatch:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.i = 0

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
            
    def write(self, rom):
        pass

class Level:
    def __init__(self, data, ram, idx):
        self.level_idx = idx
        if idx == 0xc:
            self.world_idx = 3
            self.world_sublevel = 3
        else:
            self.world_idx = int(idx / 3)
            self.world_sublevel = idx % 3
        self.world = data.worlds[self.world_idx]
        self.data = data
        self.ram = ram
        self.macro_rows = []
        self.objects = []
        self.hardmode_patches = []
        self.hardmode_length = None
        self.objects_length = None
                
    def read(self):
        self.macro_rows = []
        self.objects = []
        
        self.hardmode_length = self.data.read_byte(self.data.ram_to_rom(self.ram))
        
        row_count = constants.macro_rows_per_level
        for i in range(row_count):
            row = LevelMacroRow(self.data)
            row.read(self.data.ram_to_rom(self.ram + i * 4 + 1))
            self.macro_rows.append(row)
        
        # hardmode patches
        patch_y = 0
        patch_x = 0
        
        for i in range(self.hardmode_length):
            while patch_x >= 4:
                patch_x -= 4
                patch_y += 1
            
            patch_byte = self.data.read_byte(self.data.ram_to_rom(i + self.ram + row_count * 4 + 1))
            
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
        
        ram_objects_start = self.ram + self.hardmode_length + 1 + row_count * 4
        bs = BitStream(self.data.bin, self.data.ram_to_rom(ram_objects_start))
        while True:
            type = bs.read_bits(2)
            obj = Object()
            obj.type = type
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
                obj.i = bs.read_bits(5)
                obj.compressed = False
                
            elif type == 2:
                # short format
                obj.y = object_y
                obj.flipy = False
                obj.flipx = False
                obj.x = bs.read_bits(4) * 2 + 1
                obj.i = bs.read_bits(4)
                obj.compressed = True
                
            elif type == 3:
                # end-of-stream
                break
            
            obj.gid = self.data.spawnable_objects[obj.i]
            obj.name = self.data.get_object_name(obj.gid)
            if obj.y >= 0:
                self.objects.append(obj)
        
        self.objects_length = bs.offset - self.data.ram_to_rom(ram_objects_start) + (1 if bs.bitoffset > 0 else 0)
        
    def write(self):
        pass
        
    def produce_objects_stream(self):
        os = ObjectStream()
        
        # add objects to stream sorted by y position.
        for obj in sorted(self.objects, key=lambda obj : -obj.y):
            os.add_object(obj)
        
        os.finalize()
        
        return os
        
    # constructs rows of medtiles, from bottom up.
    # dimensions should be YX, 64x16
    def produce_med_tiles(self, hardmode=False):
        rows = []
        y = 0
        for lmr in self.macro_rows:
            row = [[0] * 16, [0] * 16]
            for i in range(4):
                macro_tile_idx = lmr.macro_tiles[i]
                if hardmode:
                    for patch in self.hardmode_patches:
                        if y == patch.y:
                            if i == patch.x:
                                # TODO...?
                                macro_tile_idx = 0x2f + patch.i
                macro_tile = self.world.get_macro_tile(macro_tile_idx)
                for j in range(2):
                    row[j][i * 2] = macro_tile[0 + 2 * j]
                    row[j][i * 2 + 1] = macro_tile[1 + 2 * j]
                    row[j][0x10 - i *2 - 1] = self.world.mirror_tile(row[j][i * 2])
                    row[j][0x10 - i *2 - 2] = self.world.mirror_tile(row[j][i * 2 + 1])
            
            y += 1
            
            for j in range(2):
                row[j] = rotated(row[j], (0x10 - lmr.seam) % 0x10)
            
            rows.append(row[1])
            rows.append(row[0])
            
        return rows

class World:
    def __init__(self, data, idx):
        self.data = data
        self.idx = idx
        self.macro_tiles = [] # array of [tl, tr, bl, br]
        self.med_tiles = [] # array of [tl, tr, bl, br]
        self.med_tile_palettes = []
        self.med_tile_count = None
        self.macro_tile_count = None
        self.max_symmetry_idx = 0
        self.palettes = []
        
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
        elif idx < constants.global_macro_tiles_count + self.macro_tile_count:
            return self.macro_tiles[idx - constants.global_macro_tiles_count]
        else:
            # TODO
            return [0x0, 0x0, 0x0, 0x0]
        
    def get_med_tile(self, idx):
        if idx < constants.global_med_tiles_count:
            return self.data.med_tiles[idx]
        elif idx < constants.global_med_tiles_count + self.med_tile_count:
            return self.med_tiles[idx - constants.global_med_tiles_count]
        else:
            # TODO
            return [0, 0, 0, 0]
    
    def get_med_tile_palette_idx(self, idx):
        if idx < len(self.med_tile_palettes):
            return self.med_tile_palettes[idx]
        else:
            return None
        
    def read(self):
        self.max_symmetry_idx = self.data.read_byte(self.data.ram_to_rom(constants.ram_world_mirror_index_table + self.idx))
        data_ptr = self.data.read_word(self.data.ram_to_rom(constants.ram_world_macro_tiles_table + self.idx * 2))
        self.ram = data_ptr
        self.med_tile_count = self.data.read_byte(self.data.ram_to_rom(data_ptr))
        data_ptr += 1
        self.macro_tile_count = self.data.read_byte(self.data.ram_to_rom(data_ptr))
        data_ptr += 1
        
        # dummy -- to fill in later
        self.med_tile_palettes = [0] * constants.global_med_tiles_count
        
        # med-tiles
        next_data_ptr = data_ptr
        for i in range(self.med_tile_count):
            self.med_tiles.append([
                self.data.read_byte(self.data.ram_to_rom(data_ptr + self.med_tile_count * j)) for j in range(4)
            ])
            data_ptr += 1
            next_data_ptr += 4
            
            # dummy -- to fill in later
            self.med_tile_palettes.append(0)
        data_ptr = next_data_ptr
            
        # med-tile palette data
        idx = 0
        for i in range(int((self.med_tile_count + constants.global_med_tiles_count + 3) / 4)):
            b = self.data.read_byte(self.data.ram_to_rom(data_ptr))
            for j in range(4):
                if idx < self.med_tile_count + constants.global_med_tiles_count:
                    self.med_tile_palettes[idx] = (b >> (2 * j)) % 4
                    idx += 1
            data_ptr += 1
        
        # macro-tiles
        next_data_ptr = data_ptr
        for i in range(self.macro_tile_count):
            macro_tile = []
            for j in range(4):
                byte = self.data.read_byte(self.data.ram_to_rom(data_ptr + self.macro_tile_count * j))
                macro_tile.append(byte)
            self.macro_tiles.append(macro_tile)
            data_ptr += 1
            next_data_ptr += 4
        
        data_ptr = next_data_ptr
        
        # read palette data.
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

class MMData:
    # convert ram address to rom address
    def ram_to_rom(self, address):
        return 0x10 + (address - 0x8000)
        
    def chr_to_rom(self, address):
        return 0x10 + 0x8000 + address
        
    def read_byte(self, addr):
        return int(self.bin[addr])
        
    def read_word(self, addr):
        return int(self.bin[addr]) + int(self.bin[addr + 1] * 0x100)
        
    def read(self):
        self.levels = []
        self.spawnable_objects = []
        self.micro_tiles = [] # 8x8 list of 2bits
        self.macro_tiles = [] # array of [tl, tr, bl, br]
        self.med_tiles = [] # array of [tl, tr, bl, br]
        self.worlds = []
        self.mirror_pairs = []
        
        # read spawnable objects list
        for i in range(0x20):
            self.spawnable_objects.append(self.read_byte(self.ram_to_rom(constants.ram_object_i_gid_lookup + i)))
        
        # read med-tile mirror pairs table
        for i in range(constants.mirror_pairs_count):
            pair = [self.read_byte(self.ram_to_rom(constants.ram_mirror_pairs_table) + j * constants.mirror_pairs_count + i) for j in range(2)]
            self.mirror_pairs.append(pair)
            
        # read micro-tile chr (not stored in format; only for visualization)
        for t in range(0x100):
            chr = []
            for i in range(8):
                chr.append([0] * 8)
            for y in range(8):
                l = (t << 4) | y
                u = l | (0x08)
                for x in range(8):
                    
                    a = (self.read_byte(self.chr_to_rom(u)) >> (7 - x)) & 0x1
                    b = (self.read_byte(self.chr_to_rom(l)) >> (7 - x)) & 0x1
                    
                    chr[x][y] = (a << 1) | b
            self.micro_tiles.append(chr)
            
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
                    self.read_word(self.ram_to_rom(level_idx * 2 + constants.ram_level_table)),
                    level_idx
                )
            )
            self.levels[-1].read()
    
    def __init__(self, bindata):
        self.bin = bindata
        self.read()
        # read self
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
        
    def stat(self):
        print("# Micro Mages Hack File")
        print()
        print("-- config --")
        print()
        #config
        print("{")
        print('  # objects which can be spawned using the compressed format.')
        print('  # Length must be exactly 16.')
        print('  "spawnable":    ', self.stat_spawnstr(self.spawnable_objects[:0x10]) + ",")
        print()
        print('  # objects which can be spawned using either the compressed or extended object format.')
        print('  # it is not recommended to change the last element of this list, as it may be part of other data.')
        print('  # Length must be exactly 16.')
        print('  "spawnable-ext":', self.stat_spawnstr(self.spawnable_objects[0x10:0x20]) + ",")
        print()
        print('  # these med-tiles will be replaced with the given med-tiles when mirrored, and vice versa')
        print('  "mirror-pairs":', json_list(self.mirror_pairs, lambda i : '"' + hb(i) + '"'))
        print("}")
        print()
        
        # global tile data
        
        # med-tiles
        print("-- global --")
        print()
        print("# 16x16 med-tile data, common to all worlds")
        print("# details 8x8 micro-tile composition of 16x16 med-tiles")
        print("# m idx: tl tr bl br")
        print()
        for med_idx in range(constants.global_med_tiles_count):
            med_tile = self.med_tiles[med_idx]
            print("m", hb(med_idx) + ":  ", hb(med_tile[0]), hb(med_tile[1]), hb(med_tile[2]), hb(med_tile[3]))
        print()
        
        # macro-tiles
        print("# 32x32 macro tile data common to all worlds")
        print("# details 16x16 med-tile composition of 32x32 macro tiles")
        print("# M idx: tl tr bl br")
        print()
        for macro_idx in range(constants.global_macro_tiles_count):
            macro_tile = self.macro_tiles[macro_idx]
            print("M", hb(macro_idx) + ":  ", hb(macro_tile[0]), hb(macro_tile[1]), hb(macro_tile[2]), hb(macro_tile[3]))
        print()
        
        # worlds
        for world_idx in range(constants.world_count):
            world = self.worlds[world_idx]
            print("-- world", hx(world_idx + 1), "--")
            print("# data from rom " + hex(self.ram_to_rom(world.ram)) + " / ram " + hex(world.ram))
            print()
            print("# palette data")
            for i in range(len(world.palettes)):
                if i == 4:
                    print("\n# palette data (hard)")
                s = "P" + hx(i) + ":"
                for col in world.palettes[i][1:]:
                    s += " " + hb(col)
                print(s)
            print()
            
            print("# med-tiles (16x16) specific to this world.")
            print("# \"..\" entries are shared between all worlds; only the palette is world-specific.")
            print("# m idx: tl tr bl br   :(palette 0-3)")
            print()
            for med_idx in range(constants.global_med_tiles_count + world.med_tile_count):
                palette = ":" + str(world.med_tile_palettes[med_idx])
                if (med_idx >= constants.global_med_tiles_count):
                    med_tile = world.med_tiles[med_idx - constants.global_med_tiles_count]
                    print("m", hb(med_idx) + ":  ", hb(med_tile[0]), hb(med_tile[1]), hb(med_tile[2]), hb(med_tile[3]), "  " + palette)
                else:
                    print("m", hb(med_idx) + ":  ", ".. " * 4, " " + palette)
                    
                if med_idx == world.max_symmetry_idx - 1:
                    print("~" * 24, "# tiles past this point are considered self-symmetrical")
            print()
            
            print("# macro-tiles (32x32) specific to this world.")
            print("# M idx: tl tr bl br")
            print()
            for macro_idx in range(constants.global_macro_tiles_count + world.macro_tile_count):
                if (macro_idx >= constants.global_macro_tiles_count):
                    macro_tile = world.macro_tiles[macro_idx - constants.global_macro_tiles_count]
                    print("M", hb(macro_idx) + ":  ", hb(macro_tile[0]), hb(macro_tile[1]), hb(macro_tile[2]), hb(macro_tile[3]))
            print()
        
        # levels
        for level_idx in range(constants.level_count):
            print("-- level", hx(level_idx), "--")
            level = self.levels[level_idx]
            if level.hardmode_length is not None or level.objects_length is not None:
                print("# stage " + str(level.world_idx + 1) + "-" + str(level.world_sublevel + 1))
                print("# data from rom " + hex(self.ram_to_rom(level.ram)) + " / ram " + hex(level.ram))
                print()
                print("# These fields measure (in bytes, hex) the total length of the level data.")
                print("# Each is optional, but recommended. If exceeded, an error will be thrown. If underrun, will be padded.")
                print()
                if level.hardmode_length is not None:
                    print("# Length of hardmode data.")
                    print("H" if level.hardmode_length >= 0 else "# H", hb(abs(level.hardmode_length)))
                    print()
                if level.objects_length is not None:
                    print("# Length of object data.")
                    print("O" if level.objects_length >= 0 else "# O", hb(abs(level.objects_length)))
                    print()
                
            print("# 32x32 macro-tile rows (from the top/end of the level to bottom/start).")
            print("# Each row is 256x32 pixels.")
            print("# left: seam position (0-f).")
            print("# center: the four macro-tiles (00-7f), mirrored about the seam position.")
            print("# right: optional hardmode patches (1-f or _). An underscore (_) means no patch.")
            print()
            y = len(level.macro_rows)
            for row in reversed(level.macro_rows):
                y -= 1
                hmode = "____"
                for patch in level.hardmode_patches:
                    if patch.i != 0 and y == patch.y:
                        hmode = hmode[:patch.x] + hx(patch.i) + hmode[patch.x + 1:]
                        
                print(hx(row.seam) + ":", hb(row.macro_tiles[0]), hb(row.macro_tiles[1]), hb(row.macro_tiles[2]), hb(row.macro_tiles[3]), "    " + hmode)
            print()
            print("# objects ")
            print("# x and y are in micro-tiles (8 pixels)")
            print("# optional flag -x or -y or -xy to flip the object.")
            print("# mark an object with an asterisk (*) to force it to use the compressed format.")
            print("# compressed format: x must be odd, cannot be flipped, and id must from the spawnable list (not spawnable-ext).")
            print("# The asterisk itself has no effect except that an error is thrown if the object cannot be compressed.")
            print()
            for obj in sorted(level.objects, key=lambda obj : -obj.y):
                flags = ""
                if obj.flipx or obj.flipy:
                    flags = "-" + ("x" if obj.flipx else "") + ("y" if obj.flipy else "")
                pads = " "
                if obj.compressed:
                    pads = "*"
                print("-", obj.name + " " * (10 - len(obj.name)), pads, "x" + hb(obj.x), "y" + hb(obj.y), flags)
            
            print()
            
    def parse(self, file):
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
            
            for line in f.readlines():
                if "#" in line:
                    line = line[:line.index("#")]
                if ";" in line:
                    line = line[:line.index(";")]
                tokens = line.split()
                if len(tokens) > 0:
                    directive = tokens[0]
                    if directive == "--":
                        # configuration
                        if len(tokens) >= 3 and tokens[1] == "config":
                            parsing_globals = True
                            parsing_globals_complete = False
                            globalstr = ""
                            continue
                        else:
                            parsing_globals = False
                        
                        if len(tokens) >= 3 and tokens[1] == "global":
                            world = None
                            
                        if len(tokens) >= 3 and tokens[1] == "world":
                            world = self.worlds[int(tokens[2], 16) - 1]
                        
                        # start level
                        if len(tokens) >= 3 and tokens[1] == "level":
                            level_idx = int(tokens[2], 16)
                            assert(level_idx < constants.level_count)
                            level_complete = level
                            level = self.levels[level_idx]
                            level.objects = []
                            level.hardmode_length = None
                            level.objects_length = None
                            level.hardmode_patches = []
                            row = constants.macro_rows_per_level - 1
                            obji = 0
                            
                    if directive == "H":
                        level.hardmode_length = int(tokens[1], 16)
                        
                    if directive == "O":
                        level.objects_length = int(tokens[1], 16)
                    
                    # palette data
                    if directive[0] == "P":
                        palette_idx = int(tokens[0][1], 16)
                        for i in range(1, 4):
                            col = int(tokens[i], 16)
                            palette = None
                            if world is None:
                                palette = self.palettes_sprite[palette_idx]
                            else:
                                palette = world.palettes[palette_idx]
                            palette[i] = col
                    
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
                    
                    # object
                    if directive == "-":
                        assert(len(tokens) > 3)
                        obj = Object()
                        force_compress = False
                        
                        # look up name.
                        name = tokens[1]
                        obj.name = name
                        if name.startswith("unk-"):
                            obj.gid = int(name[4:], 16)
                        else:
                            assert(name in constants.object_names_to_gid)
                            obj.gid = constants.object_names_to_gid[name]
                        
                        obj.i = self.spawnable_objects.index(obj.gid)
                        
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
                        
                        compressible = obj.compressible()
                        if force_compress and not compressible:
                            assert(False)
                        obj.compressed = compressible
                        
                        level.objects.append(obj)
                
                if level_complete is not None:
                    # length bounds
                    calculated_hardmode_patches_length = len(level_complete.hardmode_patches)
                    calculated_objects_length = level_complete.produce_objects_stream().length_bytes()
                    if level_complete.hardmode_length is not None:
                        assert(level_complete.hardmode_length >= calculated_hardmode_patches_length)
                    else:
                        level_complete.hardmode_length = -calculated_hardmode_patches_length
                    if level_complete.objects_length is not None:
                        assert(level_complete.objects_length >= calculated_objects_length)
                    else:
                        level_complete.objects_length = -calculated_objects_length
                    level_complete = None
                    
                if parsing_globals:
                    globalstr += line + "\n"
                elif not parsing_globals_complete:
                    config = json.loads(globalstr)
                    assert(len(config["spawnable"]) == 0x10)
                    assert(len(config["spawnable-ext"]) == 0x10)
                    self.spawnable_objects = [constants.object_names_to_gid[name] for name in config["spawnable"] + config["spawnable-ext"]]
                    self.mirror_pairs = []
                    for pair in config["mirror-pairs"]:
                        self.mirror_pairs.append([int(i, 16) for i in pair])
                    parsing_globals_complete = True
                        