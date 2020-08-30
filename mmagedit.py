import sys
from array import array
from mmdata import MMData
import mmimage
import mmgui
import constants

def usage():
    print(constants.mmname)
    print()
    print("Usage:")
    print("  python3 mmagedit.py base.nes [-i hack.txt] [-o hack.txt] [-e modified.nes] [--export-images]")
    print("")
    print("-i: open hack")
    print("-o: save hack")
    print("-e: export to rom")
    print("--export-images: creates image sheet for levels")

if "--help" in sys.argv or "-h" in sys.argv:
    usage()
    sys.exit()

outfile=""
infile=""
exportnes=""
gui = True

expimage = False

if "-i" in sys.argv[2:-1]:
    infile = sys.argv[sys.argv.index("-i") + 1]
    
if "-o" in sys.argv[2:-1]:
    gui = False
    outfile = sys.argv[sys.argv.index("-o") + 1]
    
if "-e" in sys.argv[2:-1]:
    gui = False
    exportnes = sys.argv[sys.argv.index("-e") + 1]
    
if "--export-images" in sys.argv[2:]:
    gui = False
    expimage = True

bin = array('B')

filepath = None
if len(sys.argv) > 1:
    filepath = sys.argv[1]

if filepath is not None and not filepath.endswith(".nes"):
    usage()
    sys.exit()

if gui:
    if not mmgui.available:
        print("gui requires tkinter and PIL (Pillow) to be available, including PIL.ImageTk.")
    else:
        gui = mmgui.Gui()
        
        # read the rom
        if filepath != "":
            gui.fio_direct(filepath, "rom")
            
            # read a hack file
            if infile != "":
                gui.fio_direct(infile, "hack")

        # refresh the display if a rom file was successfully loaded.
        if gui.data:
            gui.refresh_all()
            
        # mainloop (blocks)
        gui.run()
        
    # user doesn't want other things to happen after the gui is closed.
    sys.exit()

# directly load data and operate on it
if filepath is not None:
    mmdata = MMData()
    
    if not mmdata.read(filepath):
        print("An error occurred while reading the rom.")
        sys.exit()

    if infile != "":
        mmdata.parse(infile)

    if exportnes != "":
        mmdata.write(exportnes)

    if expimage:
        if not mmimage.available:
            print("Image export requires PIL (Pillow), which is not installed. (python3 -m pip install Pillow)")
        else:
            mmimage.export_images(mmdata)

    if not expimage and exportnes == "" and outfile != "":
        mmdata.stat(outfile)

    if len(mmdata.errors) > 0:
        print("The following error(s) occurred:")
        for error in mmdata.errors:
            print("- " + error)