# returns a command to find an emulator, or None

import sys
import os
import subprocess

mmageditpath = "."
if getattr(sys, 'frozen', False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app 
    # path into variable _MEIPASS'.
    mmageditpath = sys._MEIPASS
else:
    mmageditpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def find_emulator():
    nesmname = "nesm.exe" if os.name == 'nt' else "nesm"
    for root, dirs, files in os.walk(mmageditpath):
        if nesmname in files:
            return os.path.join(root, nesmname)
    return None

def emulator_test():
    emu = find_emulator()
    if not emu:
        return False
    
    result = subprocess.run([emu, "--help"], capture_output=True).returncode
    
    return result == 0