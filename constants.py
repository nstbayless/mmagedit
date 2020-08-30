from util import *

mmname = "MMagEdit V1.2"
mminfo = """
MMagEdit created by NaOH

Version 1.2: 29 August 2020

Special thanks to -7 (negativeseven) and Julius.

Please support Morphcat Games.
""".strip()

ram_object_i_gid_lookup = 0xdab1
ram_level_table = 0xDAD0
ram_med_tiles_table = 0xF883
ram_macro_tiles_table = 0xF88b
ram_world_macro_tiles_table = 0xaf10
ram_mirror_pairs_table = 0xaf00
ram_world_mirror_index_table = 0xaf0c
ram_sprite_palette_table = 0xbd5f

# ~ special mods ~
ram_mod_bounce = 0xd5d7
ram_mod_bounce_replacement = [0x00]
ram_mod_no_auto_scroll = [0x8d15, 0x8d91]
ram_mod_no_auto_scroll_replacement = [[0x00, 0x44], [0xF0, 0x09, 0xE0, 0x0F, 0x90, 0x05]]

mirror_pairs_count = 6 # (x2).
world_count = 4
level_count = 0xd
global_macro_tiles_count = 0x24
global_med_tiles_count = 0x4c
macro_rows_per_level = 0x20
objects_start_y = macro_rows_per_level * 4

hidden_micro_tiles = range(0x78, 0x7e)
dangerous_micro_tiles = [0x01]

# to display hidden tiles and hardmode patches
meta_colour = (0xf0, 0x30, 0x50)
hidden_colour = (0xa0, 0x10, 0xf0)
meta_colour_str = "#" + hx(meta_colour[0]) + hx(meta_colour[1]) + hx(meta_colour[2])

meta_colour_str_b = "#c020e0"

# hashes for base roms which will not warn on load
base_hashes = ["1062df5838a11e0e17ed590bdc1095c6"]

# palettes used by objects in the game during a level
sprite_palettes = [
    [0xf, 0x1c, 0x24, 0x20],
    [0xf, 0x15, 0x27, 0x20],
    [0xf, 0x1c, 0x2c, 0x20],
    [0xf, 0x19, 0x29, 0x20]
]

# in rgb format
palette = [
    0x7C7C7C,
    0x0000FC,
    0x0000BC,
    0x4428BC,
    0x940084,
    0xA80020,
    0xA81000,
    0x881400,
    0x503000,
    0x007800,
    0x006800,
    0x005800,
    0x004058,
    0x000000,
    0x000000,
    0x000000,
    0xBCBCBC,
    0x0078F8,
    0x0058F8,
    0x6844FC,
    0xD800CC,
    0xE40058,
    0xF83800,
    0xE45C10,
    0xAC7C00,
    0x00B800,
    0x00A800,
    0x00A844,
    0x008888,
    0x000000,
    0x000000,
    0x000000,
    0xF8F8F8,
    0x3CBCFC,
    0x6888FC,
    0x9878F8,
    0xF878F8,
    0xF85898,
    0xF87858,
    0xFCA044,
    0xF8B800,
    0xB8F818,
    0x58D854,
    0x58F898,
    0x00E8D8,
    0x787878,
    0x000000,
    0x000000,
    0xFCFCFC,
    0xA4E4FC,
    0xB8B8F8,
    0xD8B8F8,
    0xF8B8F8,
    0xF8A4C0,
    0xF0D0B0,
    0xFCE0A8,
    0xF8D878,
    0xD8F878,
    0xB8F8B8,
    0xB8F8D8,
    0x00FCFC,
    0xF8D8F8,
    0x000000,
    0x000000,
]

# the above, but as tuples.
palette_rgb = [
    (p >> 16, (p >> 8) & 0xff, p & 0xff) for p in palette
]

object_names = [
    # 0
    ["none"],
    
    ["boss-grim", "boss-grimmig", "boss-1"],
    ["boss-thor", "boss-thorrix", "boss-2"],
    ["boss-eye", "boss-4"],
    
    # 4
    ["flag"],
    
    # 5
    ["beer", "barrel-thrower", "beer-bros"],
    
    # 6
    [""], # ??
    
    # 7
    ["goat"],
    
    # 8
    ["boss-knight", "boss-3"],
    
    # 9
    ["wisp", "willowisp"],
    
    # a
    ["bone", "bone-boomer"],
    
    # b
    ["troll", "pitchfork-tosser", "fork", "demon-troll"],
    
    # c
    ["snake", "snek"],
    
    # d
    ["p-ghost"], # projectile ghost?
    
    # e
    ["skeleton", "skel"],
    
    # f
    ["i-0"], # diamond item?
    
    # 10
    ["p-barrel"], # projectile
    
    # 11
    [""], # star that disappears?
    
    # 12
    ["bat"], # resting bat
    
    # 13
    ["ghost"],
    
    # 14
    ["goblin", "gbln"],
    
    # 15
    ["i-1"], # diamond item?
    
    # 16
    ["abat", "active-bat"],
    
    # 17
    ["i-2"], # points orb?
    
    # 18
    ["eye", "ball", "eyeball"],
    
    # 19
    ["grinder"],
    
    # 1a
    ["fanh", "fan-horizontal"],
    
    # 1b
    ["elec", "electric-discharge", "electricity"],
    
    # 1c
    ["exit"],
    
    # 1d
    ["trampoline", "tramp"],
    
    # 1e
    ["p-sword"], # projectile
    
    # 1f
    ["fanv", "fan-vertical"],
    
    # 20
    ["i-feather"], # feather pickup
    
    # 21
    ["spawn", "mage", "player"],
    
    # 22
    [""],
    [""],
    
    # 24
    ["boss-staff", "boss-knight-staff", "boss-3-staff"],
    
    # 25
    [""],
    [""],
    [""],
    
    # 28
    ["torch"],
    
    # 29
    [""],
    [""],
    [""],
    [""],
    [""],
    
    # 2e
    ["pipe-A"],
    
    # 2f
    ["boss-bats"],
    
    # 30
    ["pipe-B"],
    
    # 31
    ["gate", "boss-gate"],
    
    # 32
    [""],
    
    # 33
    ["pipe-C"],
]

while len(object_names) < 0x100:
    object_names.append([""])

object_data = [
    # 0
    { "chr": [[0x000]] },
    
    # 1 -- boss grim
    { "palette": 3, "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x74, 0x75, 0x280], [0x77, 0x78, 0x76, 0x277], [0x82, 0x83, 0x84, 0x85]], "offset": (0, 8) },
    
    # 2 -- boss thor
    { "palette": 1, "chr": [[0x40, 0x41, 0x241, 0x240], [0x50, 0x51, 0x251, 0x250], [0x42, 0x43, 0x243, 0x242], [0x52, 0x53, 0x253, 0x252], [0x45, 0x55, 0x255, 0x245]], "offset": (0, 16)},
    
    # 3 -- boss eye
    { "palette": 0, "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x81, 0x281, 0x280], [0x1d9, 0x1e5, 0x1d9, 0x1c7], [0x1f2, 0x1da, 0x1db, 0x1db]] },
    
    # 4 -- flag
    { "palette": 0, "chr": [[0xc2], [0xc0]] },
    
    # 5 -- beer
    { "palette": 1, "chr": [[0x58, 0x59], [0x5a, 0x5b]], "offset": [4, -24] },
    
    # 6 -- glowy-eye ??
    { },
    
    # 7 -- goat
    { "palette": 1, "chr":  [[0xa0, 0xa1], [0xb0, 0xb1]] },
    
    # 8 -- boss-knight
    { "palette": 2, "chr":  [[0xab, 0x2ab], [0xbb, 0x2bb]] },
    
    # 9 -- wisp
    { "palette": 3, "chr":  [[0xa7, 0xa8], [0xb7, 0xb8], [0xa9, 0xaa]] },
    
    # a -- bone
    { "palette": 2, "palette": 1, "chr":  [[0x1e], [0x20]] },
    
    # b -- troll
    { "palette": 1, "chr":  [[0x87, 0x88], [0x97, 0x98]] },
    
    # c -- snake
    { "palette": 1,  "chr":  [[0x32]] },
    
    { },
    
    # e -- skeleton
    { "palette": 2, "chr":  [[0x2b]] },
    
    { },
    { },
    { },
    
    # 12 -- resting bat
    { "palette": 0, "chr":  [[0x23]] },
    
    # 13 -- ghost
    { "palette": 3, "chr":  [[0x49]] },
    
    # 14 -- goblin
    { "palette": 3, "chr":  [[0x37]] },
    
    { },
    { },
    { },
    
    # 18 -- eye
    { "palette": 0, "chr":  [[0x3a]] },
    
    # 19 -- grinder
    { "palette": 2, "chr":  [[0x4e, 0x21f], [0x4e, 0x21f]], "hard": True },
    
    # 1a -- fanh
    { "palette": 2, "chr":  [[0x64], [0x65]] },
    
    # 1b -- elec
    { "palette": 2, "chr":  [[0xaf], [0xaf], [0xaf], [0xcf]], "offset": (0, 8)},
    
    # 1c -- exit
    { "chr":  [[0xfa]] },
    
    # 1d -- trampoline
    { "palette": 2, "chr":  [[0x68, 0x268]] },
    
    { },
    
    # 1f -- fanv
    { "palette": 2, "chr":  [[0x60, 0x61]] },
    
    { },
    
    # 21 -- spawn
    { "palette": 0, "chr":  [[0x16]] },
    
    { },
    { },
    
    # boss staff
    { "palette": 2, "chr":  [[0xBE, 0x2BE], [0xc6, 0x2c4]], "offset": (4, 0) },
    
    { },
    { },
    { },
    
    # 28 -- torch
    { "palette": 1, "chr":  [[0x6e]] },
    
    { },
    { },
    { },
    { },
    { },
    
    # 2e -- pipe-A
    { "chr":  [[0x1DD]] },
    
    # 2f -- boss-bats
    { "palette": 0, "chr":  [[0x25, 0x24], [0x24, 0x26]] },
    
    # 30 -- pipe-B
    { "chr":  [[0x1F2]] },
    
    # 31 -- gate
    { "chr":  [[0x1E7, 0x1DD, 0x1DE, 0x1D9]] },
    
    { },
    
    # 30 -- pipe-C
    { "chr":  [[0x1E6]] },
]

# pad out list
while len(object_data) < 0x100:
    object_data.append({ })

object_names_to_gid = {"": -1}

i = 0
for names in object_names:
    for name in names:
        object_names_to_gid[name] = i
    i += 1
    
for i in range(0x100):
    object_names_to_gid["unk-" + hb(i)] = i