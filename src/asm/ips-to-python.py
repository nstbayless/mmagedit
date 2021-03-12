# modified from pyton-ips.
# https://pypi.org/project/python-ips

import struct
import sys

import os

def hb(a):
    str = hex(a)[2:]
    if (len(str) < 2):
         str = "0" + str
    return str.upper()

def unpack_int(string):
    """Read an n-byte big-endian integer from a byte string."""
    (ret,) = struct.unpack_from('>I', b'\x00' * (4 - len(string)) + string)
    return ret

def apply(patchpath, filepath):
    patchfile = open(patchpath, 'rb')
    ofile = open(filepath, "w")
    ofile.write("""# This file was auto-generated. Please run :/src/asm/build.sh

PATCHES = [\n"""
    )
    patch_size = os.path.getsize(patchpath)

    if patchfile.read(5) != b'PATCH':
        raise Exception('Invalid patch header.')

    # Read First Record
    r = patchfile.read(3)
    while patchfile.tell() not in [patch_size, patch_size - 3]:
        # Unpack 3-byte pointers.
        offset = unpack_int(r)
        # Read size of data chunk
        r = patchfile.read(2)
        size = unpack_int(r)

        if not size:  # RLE Record
            r = patchfile.read(2)
            rle_size = unpack_int(r)
            data = patchfile.read(1) * rle_size
        else:
            data = patchfile.read(size)

        # Write to file
        ofile.write("    (")
        ofile.write(hex(offset))
        ofile.write(", bytearray.fromhex(\"")
        first = True
        if len(data) > 10:
            ofile.write("\"\"")
            for i, d in enumerate(data):
                if i % 16 == 0:
                    ofile.write("\n        ")
                else:
                    ofile.write(" ")
                first = False
                ofile.write(hb(d))
            ofile.write("\n    \"\"\".strip().replace(\"\\n\",\"  \")+\"")
        else:
            for d in data:
                if not first:
                    ofile.write(" ")
                first = False
                ofile.write(hb(d))

        ofile.write("\")),\n\n")
        
        # Read Next Record
        r = patchfile.read(3)

    if patch_size - 3 == patchfile.tell():
        trim_size = unpack_int(patchfile.read(3))
        print("trim size:", trim_size)

    # Cleanup
    ofile.write("]\n")
    ofile.close()
    patchfile.close()
    print("Written successfully.")

if len(sys.argv) != 3:
    print("Usage: ips-to-python.py PATCH.ips OUT.py")
else:
    apply(sys.argv[1], sys.argv[2])