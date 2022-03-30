# originally created by -7 (negativeseven)
# edited by NaOH

"""
import struct
"""

EXTENSION_LENGTH = 0x8000

from src.asmpy import patches_unitile
from src.asmpy import patches_diacritics

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

# this adds support for unitile data and text diacritics
# asm source: https://github.com/nstbayless/mm-patches
unitile_patches = patches_unitile.PATCHES + patches_diacritics.PATCHES
for i, patch in enumerate(unitile_patches):
	# change addresses to fit extended ROM
	if patch[0] >= 0x4010:
		unitile_patches[i] = (patch[0] + EXTENSION_LENGTH, patch[1])

diacritics_table_range = [0xE650, 0xE650 + 5]
# we could get as far as 0xE6C3, but we need some space for the diacritics hack.
unitile_table_range = [0xDCD1, diacritics_table_range[0]]

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
