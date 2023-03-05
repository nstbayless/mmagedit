import sys
from array import array
from src.mmdata import MMData
from src import emulaunch
import os

mmageditpath = os.path.dirname(os.path.realpath(__file__))

# as-lib
as_lib = "--as-lib" in sys.argv

gui_available=False
img_available=False
nesm_available=False
if not as_lib:
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
    nesm_available = emulaunch.find_emulator()
    
from src import constants
from src import util

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
    print("--export-images: creates image sheet for levels")
    print("--set-chr: sets chr rom (graphics data) to the data in the given image file.")
    print("--zoom n: starts editor at zoom level n (n can be 0, 1, or 2)")
    print("")
    print("debug options:")
    print("")
    print("--deps: check dependencies")
    print("--brx: breakpoint on byte edit")
    print("--json: serialize data to json")
    print("--select .field[a].field2[b:c]: (etc) select elements of json out")
    print("--apply {...}: apply json to data")
    print("--level x: exported rom jumps to level x at start (x can be 1-13)")
    print("--hard: start in hard mode (requires --level)")
    print("--hell: start in hell mode (requires --level)")

def main():
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
        elif not nesm_available:
            print("Not available: nesm")
            sys.exit(1)
        
        result, retcode = emulaunch.emulator_test()
        if not result:
            print("Warning: nesm available but cannot launch. Code:", retcode)
            sys.exit(0)
        print("All modules available.")
        sys.exit(0)

    outfile=""
    infile=""
    exportnes=""
    outpatch=""
    outbps=""
    chrin=""
    gui = True
    zoom_idx=0
    expimage = False
    dojson = "--json" in sys.argv
    jsonpath = ""
    jsonapply = None
    startlevel = 0
    starthard = 0

    if "-i" in sys.argv[2:-1]:
        infile = sys.argv[sys.argv.index("-i") + 1]
    
    if "--select" in sys.argv[2:-1]:
        jsonpath = sys.argv[sys.argv.index("--select") + 1]

    if "--zoom" in sys.argv[2:-1]:
        zoom_idx = int(sys.argv[sys.argv.index("--zoom") + 1])

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

    if "--apply" in sys.argv[2:-1]:
        jsonapply = sys.argv[sys.argv.index("--apply") + 1]
        
    if "--level" in sys.argv[2:-1]:
        startlevel = int(sys.argv[sys.argv.index("--level") + 1])
        
    if "--hard" in sys.argv[2:]:
        starthard = 1
        
    if "--hell" in sys.argv[2:]:
        starthard = 2

    if dojson:
        gui = False

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

            # set the zoom
            if zoom_idx != 0:
                gui.set_zoom(max(min(zoom_idx, 3), 0), True) # force zoom
            
            # read the rom
            if filepath != "" and filepath is not None:
                print("Opening ROM: " + filepath, flush=True)
                gui.fio_direct(filepath, "rom")
                
                # read a hack file
                if infile != "":
                    print("applying hack:", infile, flush=True)
                    gui.fio_direct(infile, "hack")
            else:
                # load whatever nes file is in the folder.
                nesfiles = []
                for file in os.listdir(mmageditpath):
                    if file.lower().endswith(".nes"):
                        nesfiles.append(file)
                if len(nesfiles) > 1:
                    gui.showinfo("Multiple .nes files found in the editor folder. Please ensure there is exactly one .nes file there to be opened by default.")
                elif len(nesfiles) == 1:
                    print("Opening ROM:", nesfiles[0], flush=True)
                    gui.fio_direct(nesfiles[0], "rom")

            # refresh the display if a rom file was successfully loaded.
            if gui.data:
                print("Initializing display...", flush=True)
                gui.refresh_all()
                
            # mainloop (blocks)
            print("Launching GUI...", flush=True)
            gui.run()
            
        # user doesn't want other things to happen after the gui is closed.
        print("Closing.", flush=True)
        sys.exit()

    # directly load data and operate on it
    elif filepath is not None:
        # data in -------------------------
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

        if jsonapply is not None:
            mmdata.deserialize_json_str(jsonapply)

        # data out ---------------------------

        if dojson:
            j = mmdata.serialize_json_str(jsonpath)
            result = result and j != "null"
            print(j)
            
        mmdata.startlevel = startlevel
        mmdata.startdifficulty = starthard

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

if not as_lib:
    main()