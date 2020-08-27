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
    
    [""],
    [""],
    [""],
    
    # 4
    ["flag"],
    
    # 5
    ["beer", "barrel-thrower", "beer-bros"],
    
    # 6
    ["glowy-eye"], # ??
    
    # 7
    ["goat"],
    
    # 8
    [""],
    
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
    ["abat", "active-bat"], # diamond item?
    
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
    [""],
    [""],
    [""],
    [""],
    
    # 28
    ["torch"],
]

object_names_to_gid = {"": -1}

i = 0
for names in object_names:
    for name in names:
        object_names_to_gid[name] = i
    i += 1
    
for i in range(0x100):
    object_names_to_gid["unk-" + hb(i)] = i