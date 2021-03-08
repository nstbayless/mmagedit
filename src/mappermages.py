# originally created by -7 (negativeseven)
# edited by NaOH

"""
import struct
"""

EXTENSION_LENGTH = 0x8000

PATCHES = [

	# new reset vector
	(0x1000c, bytearray.fromhex("ec da")),

	#	$daec:
	#		lda #0
	#		sta $fff8 ; has to be a value #0
	#		jmp $9557 ; jump to old entry point
	(0xdafc, bytearray.fromhex("a9 00 8d f8 ff 4c 57 95")),

	#	$daf4:
	#		lda #1
	#		sta $ffe8
	#		ldy #0
	#		lda ($c0),y
	#		sty $fff8
	#		rts
	(0xdb04, bytearray.fromhex("a9 01 8d e8 ff a0 00 b1 c0 8c f8 ff 60")),

	#	$db01:
	#		lda #1
	#		sta $ffe8
	#		ldy #0
	#		lda ($84),y
	#		sty $fff8
	#		rts
	(0xdb11, bytearray.fromhex("a9 01 8d e8 ff a0 00 b1 84 8c f8 ff 60")),

	# 	$db0e:
	#		lda #1
	#		sta $ffe8
	#		jsr $cab7
	#		sty $fff8
	#		rts
	(0xdb1e, bytearray.fromhex("a9 01 8d e8 ff 20 b7 ca 8c f8 ff 60")),

	#	$db1a:
	#		ldy #4
	#		jmp $db0e
	(0xdb2a, bytearray.fromhex("a0 04 4c 0e db")),

	#	$db1f:
	#		ldy #5
	#		jmp $db0e
	(0xdb2f, bytearray.fromhex("a0 05 4c 0e db")),

	#	$db24:
	#		ldy #1
	#		sty $ffe8
	#		dey
	#		lda ($ca),y
	#		sty $fff8
	#		rts
	(0xdb34, bytearray.fromhex("a0 01 8c e8 ff 88 b1 ca 8c f8 ff 60 ")),

	#	$db30:
	#		sta $5d3
	#		jmp $db24
	(0xdb40, bytearray.fromhex("8d d3 05 4c 24 db")),

	#	$f5b6:
	#		jsr $daf4
	#		nop
	(0xf5c6, bytearray.fromhex("20 f4 da ea")),

	#	$f3b3:
	#		jsr $daf4
	#		nop
	(0xf3c3, bytearray.fromhex("20 f4 da ea")),

	#	$f590:
	#		jsr $db24
	#		nop
	(0xf5a0, bytearray.fromhex("20 24 db ea")),

	#	$f596:
	#		jsr $db30
	#		nop
	#		nop
	(0xf5a6, bytearray.fromhex("20 30 db ea ea")),

	#	$f7d5:
	#		jsr $db0e
	(0xf7e5, bytearray.fromhex("20 0e db")),

	#	$f7e7
	#		jsr $db0e
	(0xf7f7, bytearray.fromhex("20 0e db")),

	#	$f7f0
	#		jsr $db0e
	(0xf800, bytearray.fromhex("20 0e db")),

	#	$f7f8
	#		jsr $db1f
	(0xf808, bytearray.fromhex("20 1f db")),

	#	$f800
	#		jsr $db1f
	(0xf810, bytearray.fromhex("20 1f db")),

	#	$f833
	#		jsr $db1a
	(0xf843, bytearray.fromhex("20 1a db")),

	#	$f83f
	#		jsr $db1a
	(0xf84f, bytearray.fromhex("20 1a db")),
]

# this adds support for unitile data
# asm source: https://github.com/nstbayless/mm-patches
unitile_patches = [
	(0x7630+0x8000, bytearray.fromhex("20 D1 DB EA")),
	
	(0x004481+0x8000, bytearray.fromhex("4C 64 DB")),
	
	(0x0044A7+0x8000, bytearray.fromhex("4C 50 DB EA")),
	
	(0xdB46, bytearray.fromhex("""
25 30 85 30 A5 CE 85 0B A5 31 38 E5 18 C5 CD B0
02 E6 0B A9 F8 25 31 85 31 60 A9 F0 20 36 DB 20
86 DB 90 03 4C A1 C4 A5 7F 29 0F 4C 9B C4 A9 F8
20 36 DB 20 86 DB 90 03 4C 91 C4 A5 7F 4A 4C 74
C4 B1 08 48 E6 08 D0 02 E6 09 68 60 A4 0A 18 60
84 0A A4 BC B9 D1 DC 85 08 B9 DE DC 85 09 F0 EC
A0 00 20 77 DB 20 77 DB 20 77 DB 20 77 DB C9 01
F0 DA C5 30 D0 EC 20 77 DB C5 31 D0 E8 20 77 DB
C5 0B D0 E4 20 77 DB A4 0A 20 4D 8B 38 60 A0 00
B1 00 A8 E6 00 D0 02 E6 01 98 60 8A 48 98 48 A5
00 48 A5 01 48 A5 02 48 A5 03 48 A5 04 48 A5 05
48 A5 BC 0A A8 B9 D0 DA 85 00 38 A5 C0 E5 00 4A
4A 0A 85 00 C6 00 C6 00 AD C9 05 4A 4A 4A 4A 29
01 05 00 85 02 A9 00 85 03 85 04 A5 BC 0A 0A 85
00 A5 02 4A 4A 4A 4A 29 03 85 04 05 00 0A A8 B9
EB DC 85 00 B9 EC DC 85 01 05 00 F0 22 20 C4 DB
C9 FE F0 7C 48 29 E0 AA A5 03 4A 4A 4A 4A 85 05
A5 04 0A 0A 0A 0A 05 05 C5 02 90 47 F0 04 68 4C
B6 DC 8A F0 1A C9 E0 F0 42 24 6F 50 06 29 20 D0
37 F0 0C 10 06 29 40 D0 2F F0 04 29 80 D0 29 A5
02 48 0A 0A 0A 0A 85 02 38 A9 F0 E5 02 85 02 A5
03 29 0F 18 65 02 AA 68 85 02 20 C4 DB 9D 00 06
4C A1 DC 8A C9 E0 F0 03 20 C4 DB 68 29 1F C9 1D
D0 02 A9 41 18 65 03 85 03 90 82 E6 04 4C 33 DC
68 85 05 68 85 04 68 85 03 68 85 02 68 85 01 68
85 00 68 A8 68 AA A5 D2 29 03 60

	""".strip().replace("\n","  "))),
	
	# after this point come the unitile replacement patches
]

unitile_table_range = [0xDCD1, 0xe6c3]

"""
# add PRG banks 1-2, pushing the old bank 1 to bank 3
rom_bytes[0x4010:0x4010] = bytearray(0x8000)

# place levels in bank 1
new_level_data_location = 0x4010
for level_id in range(13):
	level_data_pointer = struct.unpack("<H", rom_bytes[0xdae0 + level_id * 0x2:][:2])[0] + 0x10
	level_data_size = 1 + 0x80 + int(rom_bytes[level_data_pointer])
	current_bit_index = 0

	while True:
		command = 0
		for bit_index in range(2):
			while current_bit_index >= 8:
				current_bit_index -= 8
				level_data_size += 1
			bit = rom_bytes[level_data_pointer + level_data_size] & (1 << (7 - current_bit_index)) > 0
			current_bit_index += 1
			command <<= 1
			command |= bit

		if command == 0:
			current_bit_index += 3
		elif command == 1:
			current_bit_index += 12
		elif command == 2:
			current_bit_index += 8
		elif command == 3:
			level_data_size += 1
			break

	# move level data to new location
	rom_bytes[new_level_data_location:new_level_data_location + level_data_size] = rom_bytes[level_data_pointer:level_data_pointer + level_data_size]
	
	# set level data pointer
	rom_bytes[0xdae0 + level_id * 0x2 : 0xdae0 + level_id * 0x2 + 2] = struct.pack("<H", new_level_data_location + 0x4000 - 0x10)
	new_level_data_location += level_data_size
"""

def patch(rom_bytes):
	# replace bytearrays
	for patch in PATCHES + unitile_patches:
		address = patch[0]
		for new_byte in patch[1]:
			rom_bytes[address] = new_byte
			address += 1
