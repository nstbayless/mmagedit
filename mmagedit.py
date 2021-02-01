import sys
from array import array
from src.mmdata import MMData
import os
gui_available=False
img_available=False
try:
    import src.mmimage
    img_available=True
except ImportError as e:
    pass
try:
    import src.mmgui
    gui_available=True
except ImportError as e:
    pass
    
from src import constants

def usage():
    print(constants.mmname)
    print()
    print("Usage:")
    print("  python3 mmagedit.py base.nes [-i hack.txt] [-o hack.txt] [-e modified.nes] [-p patch.ips] [--export-images]")
    print("")
    print("-i: open hack")
    print("-o: save hack")
    print("-e: export to rom")
    print("-p: export to ips patch")
    print("-b: export to bps patch")
    print("--deps: check dependencies")
    print("--export-images: creates image sheet for levels")
    print("--brx: breakpoint on byte edit")
    print("--set-chr: sets chr rom (graphics data) to the data in the given image file.")

if "--help" in sys.argv or "-h" in sys.argv:
    usage()
    sys.exit()
    
if "--deps" in sys.argv:
    if not img_available:
        print("Not available: image")
        sys.exit(1)
    elif not gui_available:
        print("Not available: gui")
        sys.exit(1)
    print("All modules available.")
    sys.exit(0)

outfile=""
infile=""
exportnes=""
outpatch=""
outbps=""
chrin=""
gui = True

expimage = False

if "-i" in sys.argv[2:-1]:
    infile = sys.argv[sys.argv.index("-i") + 1]

if "--set-chr" in sys.argv[2:-1]:
    chrin = sys.argv[sys.argv.index("--set-chr") + 1]

if "-o" in sys.argv[2:-1]:
    gui = False
    outfile = sys.argv[sys.argv.index("-o") + 1]
    
if "-e" in sys.argv[2:-1]:
    gui = False
    exportnes = sys.argv[sys.argv.index("-e") + 1]
    if not exportnes.endswith(".nes"):
        print("Error: exported ROM must have .nes extension.")
        sys.exit(1)
    
if "-p" in sys.argv[2:-1]:
    gui = False
    outpatch = sys.argv[sys.argv.index("-p") + 1]
    if not outpatch.endswith(".ips"):
        print("Error: exported IPS must have .ips extension.")
        sys.exit(1)

if "-b" in sys.argv[2:-1]:
    gui = False
    outbps = sys.argv[sys.argv.index("-b") + 1]
    if not outbps.endswith(".bps"):
        print("Error: exported BPS must have .bps extension.")
        sys.exit(1)
    
if "--export-images" in sys.argv[2:]:
    gui = False
    expimage = True

if "--brx" in sys.argv[2:]:
    src.mmdata.breakpoint_on_byte_edit = True

bin = array('B')    

filepath = None
if len(sys.argv) > 1:
    filepath = sys.argv[1]

if filepath is not None and not filepath.endswith(".nes"):
    usage()
    sys.exit()

if gui:
    if not gui_available:
        print("gui requires tkinter and PIL (Pillow) to be available, including PIL.ImageTk.")
    else:
        gui = src.mmgui.Gui()
        
        # read the rom
        if filepath != "" and filepath is not None:
            gui.fio_direct(filepath, "rom")
            
            # read a hack file
            if infile != "":
                gui.fio_direct(infile, "hack")
        else:
            # load whatever nes file is in the folder.
            nesfiles = []
            for file in os.listdir(os.path.dirname(os.path.realpath(__file__))):
                if file.lower().endswith(".nes"):
                    nesfiles.append(file)
            if len(nesfiles) > 1:
                gui.showinfo("Multiple .nes files found in the editor folder. Please ensure there is exactly one .nes file there to be opened by default.")
            elif len(nesfiles) == 1:
                gui.fio_direct(nesfiles[0], "rom")

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

    result = True

    if infile != "":
        tprev = mmdata.title_screen.table
        mmdata.parse(infile)
        tnew = mmdata.title_screen.table
    
    if chrin != "":
        if not img_available:
            print("--set-chr requires PIL (Pillow), which is not installed. (python3 -m pip install Pillow)")
        else:
            src.mmimage.set_chr_rom_from_image_path(mmdata, chrin)

    if exportnes != "":
        result = result and mmdata.write(exportnes)
        
    if outpatch != "":
        result = result and mmdata.write_ips(outpatch)
    
    if outbps != "":
        result = result and mmdata.write_bps(outbps)

    if expimage:
        if not img_available:
            print("Image export requires PIL (Pillow), which is not installed. (python3 -m pip install Pillow)")
        else:
            src.mmimage.export_images(mmdata)

    if not expimage and exportnes == "" and outfile != "":
        mmdata.stat(outfile)

    if len(mmdata.errors) > 0:
        if result:
            print("The following warning(s) occurred:")
        else:
            print("The following error(s) occurred:")
        for error in mmdata.errors:
            print("- " + error)
    sys.exit(0 if result else 1)