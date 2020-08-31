 # MMagEdit
*A cross-platform ROM editor for [Micro Mages](http://morphcat.de/micromages/).*
 
This utility can edit levels, worlds, and tile information for Micro Mages (by [Morphcat games](http://morphcat.de/)). Made with Python3, `Pillow`, and `tkinter`. Has both a GUI and CLI.

**Windows**: TBA.

**Linux**: See "Launching (Ubuntu)" below.

<center><img src="screenshot.png" alt="Screenshot of MMagEdit" /></center>
 
## Launching (Ubuntu)

To launch with python3 on Ubuntu Linux, first make sure the dependencies are met:

```
sudo apt-get install python-imaging-tk
sudo python3 -m pip install PIL
```

Simply run `mmagedit.py` in python:

```
python3 mmagedit.py
```

## CLI Usage

The CLI for MMagEdit allows MMagEdit to be used as a step of a romhack build process, or just for users
who prefer using the command line to a graphical editor.

The following arguments can be passed to `mmagedit.py` from the command line:

```
python3 mmagedit.py [base.nes] [args...]

--help: shows summary of options available
-i hack.txt: applies hack.txt to model
-o hack.txt: saves model to hack.txt
-e modified.nes: exports model to ROM
-p patch.ips: exports model to IPS patch
--export-images: exports model as image sheet (one for each stage normal/hard)
```

At least one of `-o`, `-e`, `-p`, or `--export-images` must
be used to suppress the GUI.

### Examples

To export a `hack.txt` file to a NES ROM (this is the most common usage):

```
python3 mmagedit.py base.nes -i hack.txt -e modified.nes
```

To create a hack.txt file to begin with:

```
python3 mmagedit.py base.nes -o hack.txt
```