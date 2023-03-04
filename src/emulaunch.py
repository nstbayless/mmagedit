# returns a command to find an emulator, or None

import sys
import os

mmageditpath = "."
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    mmageditpath = sys._MEIPASS
else:
    mmageditpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("emulaunch path: ", mmageditpath)

def find_emulator():
    return None
    