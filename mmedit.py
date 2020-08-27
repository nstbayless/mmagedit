import sys
from array import array
from mmdata import MMData
import mmimage

def usage():
    print("Usage:")
    print("")
    print("  python3 mmedit.py base.nes [-i hack.txt] [-o hack.txt] [--export-images]")

if len(sys.argv) < 2:
    usage()
    sys.exit()

outfile=""
infile=""

expimage = False

if "-i" in sys.argv[2:-1]:
    infile = sys.argv[sys.argv.index("-i") + 1]
    
if "-o" in sys.argv[2:-1]:
    outfile = sys.argv[sys.argv.index("-o") + 1]
    
if "--export-images" in sys.argv[2:]:
    expimage = True

bin = array('B')

filepath = sys.argv[1]

if not filepath.endswith(".nes"):
    usage()
    sys.exit()

with open(filepath, 'rb') as f:
    bin = f.read()
    
if len(bin) <= 0x10:
    print("NES file", filepath , "is empty.")
    sys.exit()
    
mmdata = MMData(bin)

if infile != "":
    mmdata.parse(infile)

if expimage:
    if not mmimage.available:
        print("Image export requires PIL, which is not installed. (python3 -m pip install Pillow)")
    else:
        mmimage.export_images(mmdata)

if outfile == "" and not expimage:
    mmdata.stat()