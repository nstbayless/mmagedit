import sys
from array import array
from mmdata import MMData
import mmimage
import mmgui

def usage():
    print("Usage:")
    print("")
    print("  python3 mmedit.py base.nes [--gui] [-i hack.txt] [-o hack.txt] [-e modified.nes] [--export-images]")

if len(sys.argv) < 2:
    usage()
    sys.exit()

outfile=""
infile=""
exportnes=""
gui = False

expimage = False

if "-i" in sys.argv[2:-1]:
    infile = sys.argv[sys.argv.index("-i") + 1]
    
if "-o" in sys.argv[2:-1]:
    outfile = sys.argv[sys.argv.index("-o") + 1]
    
if "-e" in sys.argv[2:-1]:
    exportnes = sys.argv[sys.argv.index("-e") + 1]
    
if "--export-images" in sys.argv[2:]:
    expimage = True
    
if "--gui" in sys.argv[2:]:
    gui = True

bin = array('B')

filepath = ""
if len(sys.argv) > 1:
    filepath = sys.argv[1]

if not filepath.endswith(".nes"):
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

if outfile == "" and not expimage and not gui and exportnes == "":
    mmdata.stat()