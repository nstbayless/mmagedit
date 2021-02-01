 # MMagEdit
 
[![AppVeyor Build Status](https://ci.appveyor.com/api/projects/status/github/nstbayless/mmagedit?svg=true)](https://ci.appveyor.com/project/nstbayless/mmagedit)
 
*A cross-platform ROM editor for [Micro Mages](http://morphcat.de/micromages/).*
 
This utility can edit levels, worlds, and tile information for Micro Mages (by [Morphcat games](http://morphcat.de/)). Made with Python3, `Pillow`, and `tkinter`. Has both a GUI and CLI.

**Windows**: [Download](https://ci.appveyor.com/api/projects/nstbayless/mmagedit/artifacts/mmagedit.zip).

**Linux**: See "Launching (Ubuntu)" below.

<center><img src="screenshot.png" alt="Screenshot of MMagEdit" /></center>

## GUI Usage

### Lag

Please be aware that some functionality is a bit laggy in the GUI. Most prominently, **changing the zoom level**
and **closing a subwindow** are likely to incur quite a lot of lag. Optimizations for this may be figured out in the future,
but in the meantime please bear with it.

Users have also reported that some lag may occur for a few minutes while the program first loads, but will go away afterward.

### Placing Stage Elements

Left-clicking, middle-clicking (or ctrl-clicking), shift-clicking, and right-clicking all achieve different effects:

- Left Click: places a tile, tile patch, or object
- Right Click: removes a tile, tile patch, or object
- Middle Click / Ctrl Click: edits the mirror position (seam position). Not available on hard mode.
- Shift Click: drag to select a rectangle (for copying/cutting/deleting/pasting)

## Launching (Ubuntu)

To launch with python3 on Ubuntu Linux, first make sure the dependencies are met:

```
sudo apt-get install python3-tk python3-pil.imagetk
sudo python3 -m pip install pillow
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

### CLI-Only features

Some capabilities of MMagEdit are limited to the CLI simply because they have not yet been added to the GUI. This is a non-exhaustive list.

- Editing text
- Editing music
- Adjusting object stats (hp, etc.)
- Editing chest loot drop rates
- Editing the title screen
- Adjusting world palette colours
- Adjusting the world med-tile self-symmetry index

## TODO

- selection:
    - checkboxes to select what layers to copy/paste to/from
    - macro-patch copy/pasting
- export single image
- mod to make game over respawn from start of level instead of world
- GUI string editor
- objects with normal/hard/hell flags
- adjust level size?
- adjust level direction/orientation?