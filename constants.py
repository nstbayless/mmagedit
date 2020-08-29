from util import *

ram_object_i_gid_lookup = 0xdab1
ram_level_table = 0xDAD0
ram_med_tiles_table = 0xF883
ram_macro_tiles_table = 0xF88b
ram_world_macro_tiles_table = 0xaf10
ram_mirror_pairs_table = 0xaf00
ram_world_mirror_index_table = 0xaf0c
ram_sprite_palette_table = 0xbd5f

mirror_pairs_count = 6 # (x2).
world_count = 4
level_count = 0xd
global_macro_tiles_count = 0x24
global_med_tiles_count = 0x4c
macro_rows_per_level = 0x20
objects_start_y = macro_rows_per_level * 4

hidden_micro_tiles = range(0x78, 0x7e)

# to display hidden tiles and hardmode patches
meta_colour = (0xf0, 0x30, 0x50)
meta_colour_str = "#" + hx(meta_colour[0]) + hx(meta_colour[1]) + hx(meta_colour[2])

meta_colour_str_b = "#c020e0"

# in rgb format
palette = [
    0x484848, #00
    0x000858, #01
    0x000878, #02
    0x000870, #03
    0x380050, #04
    0x580010, #05
    0x580000, #06
    0x400000, #07
    0x100000, #08
    0x001800, #09
    0x001E00, #0A
    0x00230A, #0B
    0x001820, #0C
    0x000000, #0D
    0x080808, #0E
    0x080808, #0F

    0xA0A0A0, #10
    0x0048B8, #11
    0x0830E0, #12
    0x5818D8, #13
    0xA008A8, #14
    0xD00058, #15
    0xD01000, #16
    0xA02000, #17
    0x604000, #18
    0x085800, #19
    0x006800, #1A
    0x006810, #1B
    0x006070, #1C
    0x080808, #1D
    0x080808, #1E
    0x080808, #1F

    0xF8F8F8, #20
    0x20A0F8, #21
    0x5078F8, #22
    0x9868F8, #23
    0xF868F8, #24
    0xF870B0, #25
    0xF87068, #26
    0xF88018, #27
    0xC09800, #28
    0x70B000, #29
    0x28C020, #2A
    0x00C870, #2B
    0x00C0D0, #2C
    0x282828, #2D
    0x080808, #2E
    0x080808, #2F

    0xF8F8F8, #30
    0xA0D8F8, #31
    0xB0C0F8, #32
    0xD0B0F8, #33
    0xF8C0F8, #34
    0xF8C0E0, #35
    0xF8C0C0, #36
    0xF8C8A0, #37
    0xE8D888, #38
    0xC8E090, #39
    0xA8E8A0, #3A
    0x90E8C8, #3B
    0x90E0E8, #3C
    0xA8A8A8, #3D
    0x080808, #3E
    0x080808  #3F
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

object_data = [
    # 0
    { "chr": [[0x000]] },
    
    # 1 -- boss grim
    { "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x74, 0x75, 0x280], [0x77, 0x78, 0x76, 0x277], [0x82, 0x83, 0x84, 0x85]] },
    
    # 2 -- boss thor
    { "chr": [[0x40, 0x41, 0x241, 0x240], [0x50, 0x51, 0x251, 0x250], [0x42, 0x43, 0x243, 0x242], [0x52, 0x53, 0x253, 0x252], [0x45, 0x55, 0x255, 0x245]], "offset": (0, 16)},
    
    # 3 -- boss eye
    { "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x81, 0x281, 0x280], [0x1d9, 0x1e5, 0x1d9, 0x1c7], [0x1f2, 0x1da, 0x1db, 0x1db]] },
    
    # 4 -- flag
    { "chr": [[0xc2], [0xc0]] },
    
    # 5 -- beer
    { "chr": [[0x58, 0x59], [0x5a, 0x5b]], "offset": [4, -24] },
    
    # 6 -- glowy-eye ??
    { },
    
    # 7 -- goat
    { "chr":  [[0xa0, 0xa1], [0xb0, 0xb1]] },
    
    # 8 -- boss-knight
    { "chr":  [[0xab, 0x2ab], [0xbb, 0x2bb]] },
    
    # 9 -- wisp
    { "chr":  [[0xa7, 0xa8], [0xb7, 0xb8], [0xa9, 0xaa]] },
    
    # a -- bone
    { "chr":  [[0x1e], [0x21]] },
    
    # b -- troll
    { "chr":  [[0x87, 0x88], [0x97, 0x98]] },
    
    # c -- snake
    { "chr":  [[0x32]] },
    
    { },
    
    # e -- skeleton
    { "chr":  [[0x2b]] },
    
    { },
    { },
    { },
    
    # 12 -- resting bat
    { "chr":  [[0x23]] },
    
    # 13 -- ghost
    { "chr":  [[0x49]] },
    
    # 14 -- goblin
    { "chr":  [[0x37]] },
    
    { },
    { },
    { },
    
    # 18 -- eye
    { "chr":  [[0x3a]] },
    
    # 19 -- grinder
    { "chr":  [[0x4e, 0x21f], [0x4e, 0x21f]], "hard": True },
    
    # 1a -- fanh
    { "chr":  [[0x64], [0x65]] },
    
    # 1b -- elec
    { "chr":  [[0xaf], [0xaf], [0xaf], [0xcf]], "offset": (0, 8)},
    
    # 1c -- exit
    { "chr":  [[0xfa]] },
    
    # 1d -- trampoline
    { "chr":  [[0x68, 0x268]] },
    
    { },
    
    # 1f -- fanv
    { "chr":  [[0x60, 0x61]] },
    
    { },
    
    # 21 -- spawn
    { "chr":  [[0x16]] },
    
    { },
    { },
    
    # boss staff
    { "chr":  [[0xBE, 0x2BE], [0xc6, 0x2c4]], "offset": (4, 0) },
    
    { },
    { },
    { },
    
    # 28 -- torch
    { "chr":  [[0x6e]] },
    
    { },
    { },
    { },
    { },
    { },
    
    # 2e -- pipe-A
    { "chr":  [[0x1DD]] },
    
    # 2f -- boss-bats
    { "chr":  [[0x25, 0x24], [0x24, 0x26]] },
    
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