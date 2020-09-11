from bitstream import BitStream
from util import *
import constants
import json
import functools
import hashlib
import ips

class PatchStream:
    def __init__(self):
        self.entries = []
        self.position = None
    
    def length_bytes(self):
        return len(self.entries)
    
    def add_patch(self, patch):
        position = patch.y * 4 + patch.x
        if self.position is None:
            # start of stream
            self.position = 0
            if position != 0:
                self.entries = [0]
            else:
                self.entries = [patch.i << 4]
                return
        
        assert(position > self.position)
        while True:
            diff = position - self.position - 1
            if diff < 0x10:
                self.entries[-1] |= diff
                self.entries.append(patch.i << 4)
                self.position = position
                break
            else:
                self.position += 0x10
                self.entries[-1] |= 0x0f
                self.entries.append(0)
            
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
        while obj.y < self.y:
            ydiff = max(1, min(self.y - obj.y, 8))
            self.y -= ydiff
            self.entries.append( [0, 0] + self.as_bits(ydiff - 1, 3) )
        
        if (obj.compressible()):
            self.entries.append( [1, 0] + self.as_bits(int((obj.x - 1) / 2), 4) + self.as_bits(obj.get_i(), 4) )
        else:
            self.entries.append( [0, 1] + [1 if obj.flipy else 0] + [1 if obj.flipx else 0] + self.as_bits(obj.x, 5) + self.as_bits(obj.get_i(), 5) )
    
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
        self.name = ""
        self.flipx = False
        self.flipy = False
        self.compressed = False
    
    # gets placing index of object
    def get_i(self):
        return self.data.spawnable_objects.index(self.gid)
    
    def compressible(self):
        if self.flipx or self.flipy:
            return False
        if self.get_i() >= 0x10:
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
        self.total_length = None
    
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
        self.ram = self.data.read_word(self.data.ram_to_rom(self.level_idx * 2 + constants.ram_level_table))
        
        # read data from start address...
        hardmode_length = self.data.read_byte(self.data.ram_to_rom(self.ram))
        
        row_count = constants.macro_rows_per_level
        for i in range(row_count):
            row = LevelMacroRow(self.data)
            row.read(self.data.ram_to_rom(self.ram + i * 4 + 1))
            self.macro_rows.append(row)
        
        # hardmode patches
        patch_y = 0
        patch_x = 0
        
        for i in range(hardmode_length):
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
        
        ram_objects_start = self.ram + hardmode_length + 1 + row_count * 4
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
            obj.name = self.data.get_object_name(obj.gid)
            if obj.y >= 0:
                self.objects.append(obj)
        
        objects_length = bs.offset - self.data.ram_to_rom(ram_objects_start) + (1 if bs.bitoffset > 0 else 0)
        self.total_length = objects_length + hardmode_length
        
    def commit(self):
        ps = self.produce_patches_stream()
        os = self.produce_objects_stream()
        
        # check length (sanity)
        if self.total_length is not None:
            if ps.length_bytes() + os.length_bytes() > self.total_length:
                self.data.errors += ["Size limit exceeded: " + self.get_name()]
                return False
        
        # write music index
        #self.data.write_byte(self.data.ram_to_rom(constants.ram_music_table + self.level_idx), self.music_idx)
        
        # write level ram offset
        self.data.write_word(self.data.ram_to_rom(self.level_idx * 2 + constants.ram_level_table), self.ram)
        
        # write hardmode data length
        rom = self.data.ram_to_rom(self.ram)
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
        
        return True
        
    def produce_patches_stream(self):
        ps = PatchStream()
        
        # add objects to stream sorted by y position.
        for patch in sorted(self.hardmode_patches, key=lambda patch : patch.y * 4 + patch.x):
            ps.add_patch(patch)
        
        return ps
        
    def produce_objects_stream(self):
        os = ObjectStream()
        
        # add objects to stream sorted by y position.
        for obj in sorted(self.objects, key=lambda obj : -obj.y):
            os.add_object(obj)
        
        os.finalize()
        
        return os
        
    def get_macro_patch_tile(self, patch_i):
        return 0x2f + patch_i
        
    # constructs rows of medtiles (and macrotiles) from bottom up.
    # dimensions should be YX, 64x16
    def produce_med_tiles(self, hardmode=False, orows=range(constants.macro_rows_per_level)):
        rows = []
        macro_tile_idxs = []
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
                row[j] = rotated(row[j], (0x10 - lmr.seam) % 0x10)
            
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

class MMData:
    # convert ram address to rom address
    def ram_to_rom(self, address):
        return 0x10 + (address - 0x8000)
        
    def chr_to_rom(self, address):
        return 0x10 + 0x8000 + address
        
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
            self.bin[addr + (offset // 2)] = (b & 0x0f) | (val << 4)
        else:
            self.bin[addr + (offset // 2)] = (b & 0xf0) | val
        
    def write_byte(self, addr, b):
        self.bin[addr] = b
    
    def write_word(self, addr, w):
        self.write_byte(addr,     w & 0x00ff)
        self.write_byte(addr + 1, (w & 0xff00) >> 8)
    
    def write_patch(self, rom, bytes):
        for b in bytes:
            self.write_byte(rom, b)
            rom += 1
    
    def read(self, file):
        self.errors = []
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
            
            self.levels = []
            self.spawnable_objects = []
            self.micro_tiles = [] # 8x8 list of 2bits
            self.macro_tiles = [] # array of [tl, tr, bl, br]
            self.med_tiles = [] # array of [tl, tr, bl, br]
            self.worlds = []
            self.mirror_pairs = []
            self.chest_objects = []
            
            # read special mods
            self.mods = dict()
            self.mods["no_bounce"] = self.read_byte(self.ram_to_rom(constants.ram_mod_bounce)) == constants.ram_mod_bounce_replacement[0]
            self.mods["no_auto_scroll"] = self.read_byte(self.ram_to_rom(constants.ram_mod_no_auto_scroll[0])) == constants.ram_mod_no_auto_scroll_replacement[0][0]
            
            # read spawnable objects list
            for i in range(0x20):
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
                
            # read micro-tile chr (not stored in format; only for visualization)
            # FIXME: don't do this; mmimage should read from chr rom directly. It has a function for that already.
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
                        level_idx
                    )
                )
                self.levels[-1].read()
            
            # read music data
            self.music = Music(self)
            self.music.read()
                
            return True
        self.errors += ["Failed to open file \"" + file + "\" for reading."]
        return False
    
    # edits the binary data to be in line with everything else
    # required before writing to a binary file.
    def commit(self):
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
        for level in self.levels:
            # write level data
            if not level.commit():
                return False
                
        # write music
        if not self.music.commit():
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
        
        return True
        
    def write(self, file):
        self.errors = []
        if not self.commit():
            return False
        with open(file, "wb") as nes:
            nes.write(self.bin)
            return True
        self.errors += ["Failed to open file \"" + file + "\" for writing."]
        return False
        
    def write_ips(self, file):
        self.errors = []
        if not self.commit():
            return False
        rval = ips.create_patch(self.orgbin, self.bin, file)
        if not rval:
            self.errors += ["Failed to export patch."]
        return rval
    
    def __init__(self):
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
    def stat(self, fname=None):
        out=print
        file = None        
        try:
            if fname is not None:
                file = open(fname, "w")
                out = functools.partial(stat_out, file)
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
            out('  # objects which can be spawned using the compressed format.')
            out('  # Length must be exactly 16.')
            out('  "spawnable":    ', self.stat_spawnstr(self.spawnable_objects[:0x10]) + ",")
            out()
            out('  # objects which can be spawned using either the compressed or extended object format.')
            out('  # it is not recommended to change the last element of this list, as it might be part of other data.')
            out('  # Length must be exactly 16.')
            out('  "spawnable-ext":', self.stat_spawnstr(self.spawnable_objects[0x10:0x20]) + ",")
            out()
            out('  # objects which can be spawned from a chest (looked up randomly).')
            out('  # the final element of this list can only be spawned on multiplayer.')
            out('  # Length must be exactly 13.')
            out('  "chest-objects":', self.stat_spawnstr(self.chest_objects) + ",")
            out()
            out('  # these med-tiles will be replaced with the given med-tiles when mirrored, and vice versa')
            out('  "mirror-pairs":', json_list(self.mirror_pairs, lambda i : '"' + hb(i) + '"') + ",")
            out()
            out('  # some special mods that can be applied')
            out('  "mods": {')
            for mod in self.mods:
                if mod != "":
                    if self.mods[mod]:
                        out('    "' + mod + '": true,')
                    else:
                        out('    "' + mod + '": false,')
            out('  "":""}') # FIXME: a nasty hack to make the comma logic easier...
            out("}")
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
            
            # med-tiles
            out("-- global --")
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
                out("# data from rom " + hex(self.ram_to_rom(level.ram)) + " / ram " + hex(level.ram))
                out("ram", HW(level.ram))
                out()
                out("# This field measures (in bytes, hex) the total length of the level data.")
                out("# Optional, but recommended. If exceeded, an error will be thrown. If underrun, will be padded.")
                calculated_length = level.produce_objects_stream().length_bytes() + level.produce_patches_stream().length_bytes()
                if level.total_length is not None:
                    out("size", HB(level.total_length))
                else:
                    out("# size", HB(calculated_length))
                out()
                
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
                out("# objects ")
                out("# x and y are in micro-tiles (8 pixels)")
                out("# optional flag -x or -y or -xy to flip the object.")
                out("# mark an object with an asterisk (*) to force it to use the compressed format.")
                out("# compressed format: x must be odd, cannot be flipped, and id must from the spawnable list (not spawnable-ext).")
                out("# The asterisk itself has no effect except that an error is thrown if the object cannot be compressed.")
                out()
                for obj in sorted(level.objects, key=lambda obj : -obj.y):
                    flags = ""
                    if obj.flipx or obj.flipy:
                        flags = "-" + ("x" if obj.flipx else "") + ("y" if obj.flipy else "")
                    pads = " "
                    if obj.compressed:
                        pads = "*"
                    out("-", obj.name + " " * (10 - len(obj.name)), pads, "x" + hb(obj.x), "y" + hb(obj.y), flags)
                
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
            
    # read data from a human-readable hack.txt file
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
            song_idx = None
            music = None
            music_nibble = 0
            cfg = None
            
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
                        level = None
                        song_idx = None
                        cfg = None
                        
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
                            world = None
                            
                        if tokens[1] == "world":
                            world = self.worlds[int(tokens[2], 16) - 1]
                        
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
                            level.total_length = None
                            level.hardmode_patches = []
                            row = constants.macro_rows_per_level - 1
                            obji = 0
                    
                    # object config is different
                    elif cfg is not None:
                        cfg.parse(tokens)
                        
                        # next line
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
                    
                    if directive == "size":
                        level.total_length = int(tokens[1], 16)
                        
                    if directive == "song":
                        level.music_idx = int(tokens[1], 16)
                    
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
                        obj = Object(self)
                        force_compress = False
                        
                        # look up name.
                        name = tokens[1]
                        obj.name = name
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
                    assert(len(config["spawnable"]) == 0x10)
                    assert(len(config["spawnable-ext"]) == 0x10)
                    self.spawnable_objects = [constants.object_names_to_gid[name] for name in config["spawnable"] + config["spawnable-ext"]]
                    self.chest_objects = [constants.object_names_to_gid[name] for name in config["chest-objects"]]
                    self.mirror_pairs = []
                    for pair in config["mirror-pairs"]:
                        self.mirror_pairs.append([int(i, 16) for i in pair])
                    if "mods" in config:
                        for mod in config["mods"]:
                            self.mods[mod] = config["mods"][mod]
                    parsing_globals_complete = True
            return True
        return False
                        