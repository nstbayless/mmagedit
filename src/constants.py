from src.util import *
from src import emulaunch

mmname = "MMagEdit v1.42"
mmrepo = "https://github.com/nstbayless/mmagedit"
mmfmt = 202305051312

# this function is used as a "hello world" by libmmagedit to verify library integrity
def get_version_and_date():
    sf = str(mmfmt)
    year = sf[0:4]
    month = int(sf[4:6])
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    assert len(months) == 12
    assert month in range(0, 12)
    day = sf[6:8]
    return mmname + ": " + day + " " + months[month] + " " + year

def emucredits():
    if emulaunch.find_emulator() is not None:
        return "\n\nLightweight NES Emulator \"nesm\" by gtoni."
    return ""

mminfo = ("""
MMagEdit created by NaOH, with contributions by -7 (negativeseven) and dayofni.

""" + get_version_and_date() + """.

Special thanks to Julius, Leaf_It, and Geek_Joystick.""" + emucredits() + """

Please support Morphcat Games.
""").strip()

ram_object_i_gid_lookup = 0xdab1
ram_level_table = 0xDAD0
ram_med_tiles_table = 0xF883
ram_macro_tiles_table = 0xF88b
ram_world_macro_tiles_table = 0xaf10
ram_mirror_pairs_table = 0xaf00
ram_world_mirror_index_table = 0xaf0c
ram_sprite_palette_table = 0xbd5f
ram_chest_table = 0xC45B
ram_chest_table_length = 0xD
ram_default_lives = 0xB8F1

ram_object_flags_table = 0xBE6D # first entry omitted
ram_object_flags_table_length = 0x46
ram_object_bbox_table = 0xBEF9 # first entry omitted
ram_object_bbox_table_length = 0x3B
ram_object_points_table = 0xBE56 # first entry omitted
ram_object_points_table_length = 0x19
ram_object_hp_table = 0xBD9A # first entry omitted.
ram_object_hp_table_length = 0x19 # speculative

ram_music_table = 0xdaa3 # music for each level
ram_music_duration_table = 0x8d9d # length 0x8, the amount of time a wait command waits for.
ram_music_channel_table = 0x92b3 # seems to be the audio channel (square, square, tri, noise) assigned to each of the six virtual channels

title_screen_tile_count = [0x340, 382]
title_screen_palette_idx_count = [0x1b, 0x1b]
title_screen_press_start_text_position = [0xA82A, 0xA82C]
title_screen_players_text_position = [0xE793, 0xE795]
ram_range_title_screen = [0xc5a2, 0xC737]
ram_range_title_screen_palette = [
    [0xc737, 0xc737 + 0x9],
    [0xc740, 0xc740 + 0x9]
]

# default text lookup if no table provided.
text_lookup = "EOSRATINMLDHYCGUFP-.W!V:'BKZ@X123456789"

# space available
ram_range_music = [0x8000, 0x860A]
ram_range_levels = [0xdaec, 0xe6c3+49]
ram_range_text = [0xEC67, 0xEE67]
ram_range_uncompressed_text = [0xEE67, 0xEE67+5] # pause text
ram_pause_text_offset = 0xBAD3
ram_range_passwords = [0xE824, 0xE856]

# ~ special mods ~
# the source for these hacks: https://github.com/nstbayless/mm-patches
ram_mod_bounce = 0xd5d7
ram_mod_bounce_replacement = [0x00]
ram_mod_no_auto_scroll = [0x8d81]
ram_mod_no_auto_scroll_replacement = [[0xA5, 0xD0, 0x88, 0xF0, 0x05, 0xD9, 0x15, 0x8D, 0x90, 0x0F, 0xE0, 0x0F, 0x90, 0x0D, 0xA5, 0xD0, 0xF0, 0x09, 0xC6, 0xD0, 0xF0, 0x05, 0xC6, 0xD0, 0x60, 0xE6, 0xD0, 0x60]]
ram_mod_extended_objects = [0xDAC1, 0xF800, 0xDAC1+3]
ram_mod_extended_objects_replacement = [[0xA0, 0x06, 0x20, 0xB7, 0xCA, 0x4C, 0x07, 0xF8], [0x4C, 0xC1, 0xDA], [0x0e, 0xdb]]
ram_mod_no_relic_1 = [0xCB0C]
ram_mod_no_relic_1_replacement = [[0xEA, 0xEA, 0xEA]]
ram_mod_no_relic_2 = [0xE894]
ram_mod_no_relic_2_replacement = [[0xEA, 0xEA, 0xEA]]
ram_mod_no_relic_3 = [0xCD9D]
ram_mod_no_relic_3_replacement = [[0xEA, 0xEA, 0xEA]]
ram_mod_no_relic_4 = [0xBCBE]
ram_mod_no_relic_4_replacement = [[0xEA, 0xEA, 0xEA]]
ram_mod_no_wall_cling = 0xA933
ram_mod_no_wall_cling_replacement = [0xF0]
ram_mod_no_wall_jump = [0xD3BC, 0xD3AA]
ram_mod_no_wall_jump_replacement = [[0xA9, 0x00, 0xEA], [0xA9, 0x00, 0xEA]]
ram_mod_no_relic_ui = [0xD734, 0xD7D8]
ram_mod_no_relic_ui_replacement = [[0xEA, 0xEA, 0xEA], [0x60]]

ram_intro_update = 0xA6CC
ram_gamestart = 0xB8F0
ram_ending_dispatch = 0xD61F

mirror_pairs_count = 6 # (x2).
world_count = 4
level_count = 0xE
standard_level_count = 0xD
level_idx_finale = 0xD
level_idx_44 = 0xC
global_macro_tiles_count = 0x24
global_med_tiles_count = 0x4c

standard_macro_rows = 0x20
finale_macro_rows = 0x08

hidden_micro_tiles = range(0x78, 0x7e)
dangerous_micro_tiles = [0x01]

# to display hidden tiles and hardmode patches
meta_colour = (0xf0, 0x30, 0x50)
hidden_colour = (0xa0, 0x10, 0xf0)
meta_colour_str = "#" + hx(meta_colour[0]) + hx(meta_colour[1]) + hx(meta_colour[2])

meta_colour_str_b = "#c020e0"

# hashes for base roms which will not warn on load
base_hashes = ["1062df5838a11e0e17ed590bdc1095c6", "11c3f3f8d6473d9672dd8aabb842c3a0"]

# music names
songs = ["Mysterious", "Heroic", "Spooky", "Dreamy", "Evil", "Intro", "Fanfare", "Boss", "March"]

mus_vchannel_names = ["Lead", "Counterpoint", "Triangle", "Noise", "SFX0", "SFX1"]


# note: not actually proper opcodes
note_opcode = {"name": "-", "doc": "Plays the given note with the given duration (in hex). '_' is a tie. '*' represents a portamento. Duration must be one of [1, 2, 3, 4, 6, 8, 10, 20], and the note must be _, *, or in the range 0-C inclusive"}

# dn: dump nibble
dn_opcode = {"name": "dn", "doc": "Dump nibble"}

music_opcodes = [
    # note: opcodes 0-7 inclusive are actually interpreted as WAIT codes, but will execute
    # if the wait-postfix code is 0xF.
    
    # 0
    # sets the hold duration to 0?
    {"name": "hold0", "doc": "Sets duty cycle 0."},
    
    # 1
    # sets the hold duration to 70?
    {"name": "hold1", "doc": "Sets duty cycle 1."}, 
    
    # 2
    # sets hold duration to 80?
    {"name": "hold2", "doc": "Sets duty cycle 2."}, 
    
    # sets articulation to arg, and (for music only) zeroes $4ba and $4be.
    {"name": "art", "argc": [1], "doc": "sets articulation"},
    
    # 4
    {"name": "port", "argc": [1, 1], "doc": "First argument sets portamento. Second is unknown."},
    
    # 5
    # $4Ca <- arg[0]
    {"name": "harm", "argc": [1], "doc": "sets harmony mode, inducing square1 to follow the lead"},
    
    # 6
    # jumps to the given label directly.
    {"name": "jmp", "argc": ["abs"], "doc": "jumps to the given label"},
    
    # 7
    # does nothing
    {"name": "nop", "doc": "does nothing"},
    
    #8
    # mus_dynamics <- arg[0]
    {"name": "dyn", "argc":[1], "doc": "sets dynamics"},
    
    # 9 -- modulate key
    # if arg[0:1] & 0 == 0:
    #   key += arg[0:1] >> 1 ?
    # else:
    #   key -= arg[0:1] >> 1 ?
    {"name": "mod", "argc": [2], "doc": "modulates by the given amount, causing notes played after this to be adjusted. The number of notes modulated is given by 4*(low nibble) + (bit6 + 2*bit7 + bit5)*(1 - 2*bit5). For example, 'mod 63' modulates by +10 semitones; 'mod A0' by -3. The meaning of bit4 is unknown."},
    
    # A
    # - if not in a subroutine, does nothing.
    # - returns from subroutine
    # - repeats subroutine if applicable
    {"name": "rts", "doc": "returns from subroutine. Has no effect if not in a subroutine."},
    
    #B - subroutine with key offset
    # sets $4B6 to 0 and,
    # if arg[0] < 8:
    #   key += arg[0]
    # if arg[0] >= 8:
    #   key += (arg[0] - 0x10)
    # then mus_reta <- nibble pc
    # then nibble pc -= arg[1:2]
    #
    # repeat count for subroutine is arg[3]
    {"name": "sub", "argc":[1, "rels", 1], "doc": "Executes the given subroutine, modulated by the first argument. The final argument is the number of repetitions. The subroutine must be before the current line by at most 0x100 nibbles (half-bytes)"},
    
    # C
    # if arg is 0:
    #   slide = (slide & fc)
    # otherwise:
    #   sets $4A2 to (arg >> 2), then ANDS the current slide value with 0x40, and then ORS it with (arg & 1 << 1 | arg & 2 >> 1)
    #   that is, slide = (slide & 0x40) | ((arg & 1) << 1 | (arg & 2) >> 1)
    {"name":"ctl", "argc": [1, 1], "doc": "Details are unknown. (It seems that this is causing a reading frame shift, so we are likely misinterpreting it...)"},
    
    # D -- subtract 0xC from current key.
    {"name": "doct", "doc": "modulates down by an octave"},
    
    # E -- repeat
    # if arg[0] >= mus_repeat_idx:
    #    mus_repeat_idx++
    #    nibble_pc -= arg[1:2]
    # else:
    #    mus_repeat_idx = 0
    {"name": "rep", "argc":[1, "rels"], "doc": "repeats from the given label the given number of times (plus 1). The label must be before the current line by at most 0x100 nibbles (half-bytes)"},
    
    # F - orchestrate
    # sets all $4C6 for triangle, counterpoint, and lead to the given args
    {"name": "orch", "argc":[1, 1, 1], "doc": "orchestrates triangle, counterpoint, and lead respectively. Details unknown."},
]

# wait commands (0x0-0x7 inclusive) are followed by a second "postfix" opcode byte.

# all "DONE_" postfix codes have this behaviour in common:
# if music:
#     zeroes $4ba and mus_note_timer
# slide = slide & 0xBF
# ... then a bunch more craziness depending on the channel ...
#   plays the code value as a note (0-C) added to of $496 (mus_key)
#   seems to set the music pitch ($48a, $48b) to their correct new value. 
# then returns.

mus_wait_postfix_opcodes = [
    {"name": "DONE_0"},
    {"name": "DONE_1"},
    {"name": "DONE_2"},
    {"name": "DONE_3"},
    {"name": "DONE_4"},
    {"name": "DONE_5"},
    {"name": "DONE_6"},
    {"name": "DONE_7"},
    {"name": "DONE_8"},
    {"name": "DONE_9"},
    {"name": "DONE_A"},
    {"name": "DONE_B"},
    {"name": "DONE_C"},
    
    #D
    {"name":"TIE"}, # simply finishes executing opcodes for this frame. Is this hold..?
    
    #E
    {"name":"SLIDE"}, # sets the slide value to 40 and then finishes.
    
    #F
    {"name":"EXEC_PREV"}, # executes the prior wait opcode as a standard opcode
]

greyscale_palette = [0x0f, 0x0, 0x10, 0x20] # a simple grayscale palette
bg_palette = [0x0f, 0x0c, 0x1c, 0x20]
sprite_palette = [0xf, 0x08, 0x26, 0x20]
title_red_palette = [0x0f, 0x15, 0x26, 0x20]

# bg palette used as a default by editor if no palette is in context
bg_palettes = [
    [0xf, 0x5, 0x15, 0x30], # special tiles
    [0xf, 0x08, 0x17, 0x35], # solid tiles
    [0xf, 0x0b, 0x1a, 0x20], # acid
    [0xf, 0x0c, 0x2D, 0x10]  # bg tiles
]

# this is the basic NES palette (rgb format)
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

# how to render tiles in the med-tile editor
component_micro_tile_palettes = [
    [0] * 0x10,
    [1] * 0x10,
    [1] * 0x10,
    [1] * 0x10,
    
    [1] * 0x10,
    [1] * 0x6 + [3] * 0xa,
    [3] * 0x10,
    [3] * 0x10,
    
    [3] * 0x10,
    [3] * 0x10,
    [3] * 0x10,
    [3] * 0x10,
    
    [3] * 0x10,
    [3] * 0x3 + [2] * 0x5 + [3] * 0x8,
    [3] * 0x10,
    [3] * 0x10
]

object_names = [
    # 0
    ["none"],
    
    ["boss-ghost", "boss-grim", "boss-grimmig", "boss-1"],
    ["boss-thor", "boss-thorrix", "boss-viking", "boss-2"],
    ["boss-eye", "boss-4"],
    
    # 4
    ["flag"],
    
    # 5
    ["beer", "barrel-thrower", "beer-bros"],
    
    # 6
    ["boss-final", "boss-5", "boss-finale"], # eye boss, but in space.
    
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
    ["i-gem-blue"], # blue diamond
    
    # 10
    ["p-barrel"], # projectile
    
    # 11
    ["i-warp"], # swaps player positions
    
    # 12
    ["bat"], # resting bat
    
    # 13
    ["ghost"],
    
    # 14
    ["goblin", "gbln"],
    
    # 15
    ["i-gem-green"], # green diamond item
    
    # 16
    ["abat", "active-bat"],
    
    # 17
    ["i-orb"], # points orb
    
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
    ["fx-destroyable-block-explosion"],
    
    # 23
    ["fx-explosion"],
    
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
    
    # 2A
    ["i-heart"], # 1-up
    
    # 2B
    ["i-fairy"],
    
    # 2C
    ["eye-inv"], # invincible eye
    
    # 2D
    ["dog"], # yes
    
    # 2e
    ["pipe-A"],
    
    # 2f
    ["boss-bats"],
    
    # 30
    ["pipe-B"],
    
    # 31
    ["gate", "boss-gate"],
    
    # 32
    [],
    
    # 33
    ["pipe-C"],
    
    # 34
    ["p-bone"], # bone projectile
    
    # 35
    ["p-shot-charged"],
    
    # 36
    ["relic"],
    
    # 37
    [],
    
    # 38
    ["p-fork"],
    
    # 39
    [],
    
    # 3A
    ["p-shot"],
    
    # 3B
    ["p-bubble"]
]

while len(object_names) < 0x100:
    object_names.append([])

object_data = [
    # 0
    { "chr": [[0x000]] },
    
    # 1 -- boss grim
    { "palette": 3, "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x74, 0x274, 0x280], [0x77, 0x78, 0x278, 0x277], [0x82, 0x83, 0x84, 0x85]], "offset": (0, 8) },
    
    # 2 -- boss thor
    { "palette": 1, "chr": [[0x40, 0x41, 0x241, 0x240], [0x50, 0x51, 0x251, 0x250], [0x42, 0x43, 0x243, 0x242], [0x52, 0x53, 0x253, 0x252], [0x45, 0x55, 0x255, 0x245]], "offset": (0, 16)},
    
    # 3 -- boss eye
    { "palette": 0, "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x81, 0x281, 0x280], [0x480, 0x481, 0x681, 0x680], [0x470, 0x471, 0x671, 0x670]], "offset": (0, 8) },
    
    # 4 -- flag
    { "palette": 0, "chr": [[0xc2], [0xc0]], "checkpoint": True },
    
    # 5 -- beer
    { "palette": 1, "chr": [[0x58, 0x59], [0x5a, 0x5b]], "offset": [4, -24] },
    
    # 6 -- finale boss
    { "palette": 2, "chr": [[0x70, 0x71, 0x271, 0x270], [0x80, 0x81, 0x281, 0x280], [0x480, 0x481, 0x681, 0x680], [0x470, 0x471, 0x671, 0x670]], "offset": (0, 8) },
    
    # 7 -- goat
    { "palette": 1, "chr":  [[0xa0, 0xa1], [0xb0, 0xb1]] },
    
    # 8 -- boss-knight
    { "palette": 2, "chr":  [[0xab, 0x2ab], [0xbb, 0x2bb]] },
    
    # 9 -- wisp
    { "palette": 3, "chr":  [[0xa7, 0xa8], [0xb7, 0xb8], [0xa9, 0xaa]] },
    
    # a -- bone
    { "palette": 2, "chr":  [[0x1e], [0x20]] },
    
    # b -- troll
    { "palette": 1, "chr":  [[0x87, 0x88], [0x97, 0x98]] },
    
    # c -- snake
    { "palette": 1,  "chr":  [[0x32]] },
    
    { },
    
    # e -- skeleton
    { "palette": 2, "chr":  [[0x2b]] },
    
    # f -- blue gem
    { "palette": 2, "chr":  [[0xcb]] },
    
    # 10
    { },
    
    # 11 - warp
    { "palette": 1, "chr":  [[0xc7]] },
    
    # 12 -- resting bat
    { "palette": 0, "chr":  [[0x23]] },
    
    # 13 -- ghost
    { "palette": 3, "chr":  [[0x49]] },
    
    # 14 -- goblin
    { "palette": 3, "chr":  [[0x37]] },
    
    # 15 -- green gem
    { "palette": 3, "chr":  [[0xcb]] },
    
    # 16 -- active bat
    { "palette": 0, "chr":  [[0x24]] },
    
    # 15 -- blue orb
    { "palette": 2, "chr":  [[0xc6]] },
    
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
    { "palette": 2, "chr":  [[0x460, 0x461]] },
    
    # 20 -- feather
    { "palette": 1, "chr":  [[0xCD]] },
    
    # 21 -- spawn
    { "palette": 0, "chr":  [[0x16]] },
    
    { },
    { },
    
    # boss staff
    # FIXME: the chr table seems to be wrong.
    { "palette": 2, "chr":  [[0xBE, 0x2BE], [0xc6, 0x2c4]], "offset": (4, 0) },
    
    { },
    { },
    { },
    
    # 28 -- torch
    { "palette": 1, "chr":  [[0x6e]] },
    
    { },
    
    # 2A -- 1-up
    { "palette": 1, "chr":  [[0xC9]] },
    
    # 2B -- fairy
    { "palette": 2, "chr":  [[0xD0]] },
    
    # 2C -- invincible eye
    { "palette": 3, "chr":  [[0x3a]] },
    
    # 2D -- dog
    { "palette": 1, "chr":  [[0x31]] },
    
    # 2e -- pipe-A
    { "chr":  [[0x1DD]] },
    
    # 2f -- boss-bats
    { "palette": 0, "chr":  [[0x25, 0x24], [0x24, 0x26]] },
    
    # 30 -- pipe-B
    { "chr":  [[0x1F2]] },
    
    # 31 -- gate
    { "chr":  [[0x1E7, 0x1DD, 0x1DE, 0x1D9]] },
    
    { },
    
    # 33 -- pipe-C
    { "chr":  [[0x1E6]] },
]

# pad out list
while len(object_data) < 0x100:
    object_data.append({})

object_names_to_gid = {"": -1}

for i in range(0x100):
    object_names[i] += ["obj-" + hb(i), "unk-" + hb(i)]

i = 0
for names in object_names:
    for name in names:
        if name != "":
            assert name not in object_names_to_gid, f"objects w/ name collision ({name})"
            object_names_to_gid[name] = i
    i += 1
    
# set object config
import src.objects.cfg_hp, src.objects.cfg_points, src.objects.cfg_flags, \
    src.objects.cfg_bbox, src.objects.obj_0E, src.objects.obj_shot

for i in range(0x100):
    object_data[i]["config"] = []

# first 0x19 objects have hitpoints
for i in range(1, ram_object_hp_table_length):
    object_data[i]["config"] += [src.objects.cfg_hp.ConfigHP]

for i in range(1, ram_object_points_table_length):
    object_data[i]["config"] += [src.objects.cfg_points.ConfigPoints]

for i in range(1, ram_object_flags_table_length):
    object_data[i]["config"] += [src.objects.cfg_flags.ConfigFlags]

for i in range(1, ram_object_bbox_table_length):
    object_data[i]["config"] += [src.objects.cfg_bbox.ConfigBBox]

# skeleton has special config known
object_data[0xE]["config"] += [src.objects.obj_0E.Config0E]
object_data[0x35]["config"] += [src.objects.obj_shot.ConfigShot]
object_data[0x3A]["config"] += [src.objects.obj_shot.ConfigShot]