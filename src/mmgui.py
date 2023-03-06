from src import constants
from src.util import *
import os
import copy
import math
import tempfile
from functools import partial

from src import mmimage
from src import mmdata
import src.mappermages
from src import emulaunch

try:
    from PIL import Image, ImageDraw, ImageOps, ImageTk
    import tkinter as tk
    from tkinter import ttk
    import tkinter.filedialog, tkinter.messagebox
except ImportError as e:
    available = False
    raise e

macro_width = 32
macro_height = 32
med_width = 16
med_height = 16
micro_width = 8
micro_height = 8

max_select_width = 0x4

objwidth = 32
objheight = 33
screenwidth = 256
screenheight = 224
level_width = 256
level_height = macro_height * constants.macro_rows_per_level
gridcol = "#333"
seamcol = "#ddd"
linecol = "#888"
divcol = "#cff"
selcol = constants.meta_colour_str
patchcol = constants.meta_colour_str
unipatchcol = "#cfc"
objcrosscol = {False: constants.meta_colour_str, True: constants.meta_colour_str_b, "drop": "#FFCC44"}
usagecol = {
    "overlimit": "#9c2611",
    "used": "#06368f",
    "unused": "#5d5a63"
}

zoom_levels = [2]

resource_dir = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(resource_dir, "../icon.png")

class CopyBuffer:
    def __init__(self):
        self.offset = (0, 0)
        self.source_world_idx = 0
        self.source_world_idx = 0
        self.macro_row_idx_max = 0
        self.objects = []
        self.macro_rows = []
        self.macro_patches = []
        self.unitile_patches = []

# a component to show usage data
class GuiUsageBar(tk.Canvas):
    def __init__(self, parent, core, **kwargs):
        self.max = 0
        self.usage = 0
        self.text = ""
        self.core = core
        if "max" in kwargs:
            self.max = kwargs.pop("max")
        if "usage" in kwargs:
            self.usage = kwargs.pop("usage")
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        tk.Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self.on_resize)
        self.elts = []
    
    def on_resize(self, event):
        self.refresh()

    def configure(self, **kwargs):
        if "max" in kwargs:
            self.max = kwargs.pop("max")
        if "usage" in kwargs:
            self.usage = kwargs.pop("usage")
        if "text" in kwargs:
            self.text = kwargs.pop("text")
        tk.Canvas.configure(self, **kwargs)
        self.refresh()
    
    def refresh(self):
        self.core.delete_elements(self, self.elts)
        self.elts = []

        width, height = self.winfo_width(), self.winfo_height()
        p = 1 if self.max <= 0 else float(self.usage) / float(self.max)
        overlimit = False
        if self.usage > self.max:
            overlimit = True
            p = 1
        pwidth = p * width

        # rectangles
        self.elts.append(
            self.create_rectangle(
                0, 0, width, height,
                fill=usagecol["unused"]
            )
        )
        self.elts.append(
            self.create_rectangle(
                0, 0, pwidth, height,
                fill=usagecol["overlimit" if overlimit else "used"]
            )
        )

        # text
        s = self.text + ": " if self.text != "" else ""
        if overlimit:
            s += HX(self.usage - self.max) + " OVERLIMIT past " + HX(self.max) + " bytes"
        else:
            s += HX(self.max - self.usage) + " free of " + HX(self.max) + " bytes"
        self.elts.append(
            self.create_text(
                2, height / 2.0,
                anchor=tk.W,
                text=s,
                fill="white"
            )
        )

# a component based on a grid of micro-tiles
class GuiMicroGrid(tk.Canvas):
    def __init__(self, parent, core, **kwargs):
        self.w = 0
        self.h = 0
        self.core = core
        self.data = core.data
        self.micro_images = []
        self.clear_elts = []
        self.divides = []
        self.chunkdim = None
        self.click_cb = None
        self.selection_idx = None
        self.maxh = 0
        self.copy_buffer = None
        self.linecol = linecol
        
        if "dims" in kwargs:
            dims = kwargs.pop("dims")
            self.w = dims[0]
            self.h = dims[1]
        
        if "chunkdim" in kwargs:
            self.chunkdim = kwargs.pop("chunkdim")
            
        if "cb" in kwargs:
            self.click_cb = kwargs.pop("cb")
        
        if "bg" not in kwargs:
            kwargs["bg"] = "black"
        
        scroll = True
        if "scroll" in kwargs:
            scroll = kwargs.pop("scroll")
        
        if "linecol" in kwargs:
            self.linecol = kwargs.pop("linecol")
        
        tk.Canvas.__init__(self, parent, **kwargs)
        self.calcdims()
        
        if scroll:
            self.core.attach_scrollbar(self, parent)
        
        self.bind("<Button-1>", partial(self.on_click_gui, False))
        self.bind("<Button-3>", partial(self.on_click_gui, True))
        self.bind("<Double-Button-1>", partial(self.on_click_gui, True))
        
    def refresh_zoom(self):
        self.micro_images = []
        self.refresh()
        
    def on_click_gui(self, edit, event):
        if self.click_cb is not None:
            chunkdim = (1, 1) if self.chunkdim is None else self.chunkdim
            y = int(self.core.get_event_y(event, self, self.scroll_height))
            x = clamp_hoi(event.x, 0, self.scroll_width)
            
            # convert to microtile coordinates
            if self.chunkdim is not None:
                x -= (x // (micro_width * self.core.zoom())) // self.chunkdim[0]
                y -= (y // (micro_width * self.core.zoom())) // self.chunkdim[1]
            x //= micro_width * self.core.zoom()
            y //= micro_height * self.core.zoom()
            
            # convert to chunkdim coordinates
            x //= chunkdim[0]
            y //= chunkdim[1]
            
            idx = x + y * (self.w // chunkdim[0])
            self.click_cb(int(idx), edit)
    
    def configure(self, **kwargs):
        if "dims" in kwargs:
            dims = kwargs.pop("dims")
            self.w = dims[0]
            self.h = dims[1]
        if "linecol" in kwargs:
            self.linecol = kwargs.pop("linecol")
        tk.Canvas.configure(self, **kwargs)
        self.calcdims()
        
    def calcdims(self):
        w = micro_width * self.w * self.core.zoom()
        h = micro_height * self.h * self.core.zoom()
        
        if self.chunkdim is not None:
            w += self.w // self.chunkdim[0] - 1
            h += self.h // self.chunkdim[1] - 1
        
        tk.Canvas.configure(
            self,
            width=int(w),
            scrollregion=(0, 0, int(w), int(h))
        )
        
        # add micro-images
        while len(self.micro_images) < w:
            self.micro_images.append([])
        x = 0
        for col in self.micro_images:
            while len(col) < h:
                y = len(col)
                xp = x * micro_width * self.core.zoom()
                yp = y * micro_height * self.core.zoom()
                if self.chunkdim is not None:
                    xp += x // self.chunkdim[0]
                    yp += y // self.chunkdim[1]
                col.append(self.create_image(xp, yp, image=self.core.blank_image, anchor=tk.NW))
            x += 1
        
        self.scroll_width = w
        self.scroll_height = h
    
    def set_tile_image(self, x, y, img):
        if x < self.w and y < self.h:
            self.maxh = max(self.maxh, y + 1)
            self.itemconfig(self.micro_images[x][y], image=img)
        
    def clear_from(self, index):
        chunkdim = self.chunkdim if self.chunkdim is not None else (1, 1)
        for x in range(self.w):
            for y in range(self.maxh):
                idx = (x // chunkdim[0]) + (y // chunkdim[1]) * (self.w // chunkdim[0])
                if idx < index:
                    continue
                self.itemconfig(self.micro_images[x][y], image=self.core.blank_image)
    
    def refresh(self):
        self.core.delete_elements(self, self.clear_elts)
        self.clear_elts = []
        
        self.calcdims()
        pw = self.scroll_width
        ph = self.scroll_height
        
        # lines
        if self.chunkdim is not None:
            for x in range(self.w // self.chunkdim[0]):
                px = (x + 1) * micro_width * self.chunkdim[0] * self.core.zoom() + x
                self.clear_elts.append(
                    self.create_line(px, 0, px, ph, fill=self.linecol)
                )
                for y in range(self.h // self.chunkdim[1]):
                    py = (y + 1) * micro_height * self.chunkdim[1] * self.core.zoom() + y
                    self.clear_elts.append(
                        self.create_line(0, py, pw, py, fill=self.linecol)
                    )
            
        chunkdim = self.chunkdim if self.chunkdim is not None else (1, 1)
        
        # lines
        divargs = {"width": 2, "fill": divcol}
        for divide in self.divides:
            x = chunkdim[0] * (divide % (self.w // chunkdim[0]))
            y = chunkdim[1] * (divide // (self.w // chunkdim[0]))
            
            px = x * micro_width * self.core.zoom()
            py = y * micro_height * self.core.zoom()
            
            divpy = py + micro_height * chunkdim[1] * self.core.zoom()
            if self.chunkdim is not None:
                px += x // chunkdim[0]
                py += y // chunkdim[1]
                divpy += 1 + y // chunkdim[1]
            
            if x != 0:
                # sigmoid division
                self.clear_elts.append(
                    self.create_line(0, divpy, px, divpy, **divargs)
                )
                self.clear_elts.append(
                    self.create_line(px, divpy + 1, px, py - 1, **divargs)
                )
            self.clear_elts.append(
                self.create_line(px, py, pw, py, **divargs)
            )
        
        # selection rect
        if self.selection_idx is not None:
            x = (self.selection_idx % (self.w // chunkdim[0])) * chunkdim[0]
            y = (self.selection_idx // (self.w // chunkdim[0])) * chunkdim[1]
            px = x * micro_width * self.core.zoom()
            py = y * micro_height * self.core.zoom()
            if self.chunkdim is not None:
                px += x // chunkdim[0]
                py += y // chunkdim[1]
            rect_margin = 1
            self.clear_elts.append(
                self.create_rectangle(
                    px + rect_margin,
                    py + rect_margin,
                    px + micro_width * chunkdim[0] * self.core.zoom() - rect_margin, 
                    py + micro_height * chunkdim[1] * self.core.zoom() - rect_margin,
                    width=2,
                    outline=selcol
                )
            )        

# an undoable action
class GuiAction:
    def __init__(self, **kwargs):
        self.type = ""
        self.refresh = []
        self.level_idx = None
        self.hard = None
        self.context = None
        self.children = []
        for name, value in kwargs.items():
            setattr(self, name, value)

class GuiSubWindow:
    def __init__(self, core, title):
        self.core = core
        self.window = tk.Toplevel(core.window)
        self.window.title(title)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.window.bind("<Key>", self.core.on_keypress)
        self.closed = False
    
    def on_close(self):
        self.closed = True
        self.window.destroy()
        self.core.subwindows.pop(type(self))
        
    def ctl(self, kwargs):
        pass

# screen editor
class GuiScreenEditor(GuiSubWindow):
    def __init__(self, core):
        super().__init__(core, "Screen Editor")
        self.screen = core.data.title_screen
        self.w = 256
        self.h = 224
        self.palette_idx = 0
        self.menu_commands = dict()
        self.window.bind("<Key>", self.on_keypress)
        self.init()
        self.refresh()
    
    def ctl(self, kwargs):
        if "screen" in kwargs:
            self.screen = kwargs.pop("screen")
            self.refresh()
        elif "refresh" in kwargs:
            if "refx" in kwargs and "refy" in kwargs:
                self.refresh(kwargs["refx"], kwargs["refy"], False)
            else:
                self.refresh()

    def init(self):
        self.select_canvas = GuiMicroGrid(self.window, self.core, height=8 * 16 * self.core.zoom() + 16, dims=(16, 16), chunkdim=(1, 1), cb=self.on_select_click, scroll=False, linecol="black")
        self.select_canvas.pack(side=tk.RIGHT)
        
        self.place_canvas = GuiMicroGrid(self.window, self.core, height=self.h * self.core.zoom(), dims=(self.w // micro_width, self.h // micro_height), scroll=False, cb=self.on_place_click)
        self.place_canvas.pack()
        
        self.usage_bar = GuiUsageBar(self.window, self.core, text="Screen Data", height=20)
        self.usage_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.menu = tk.Menu(self.window)
        self.cmenu = tk.Menu(self.menu, tearoff=0)
        for i in range(4):
            si = str(i+1)
            cmd = partial(self.set_palette_idx, i)
            self.cmenu.add_command(label="Palette " + si, command=cmd, accelerator=si)
            self.add_hotkey(cmd, si)
        self.menu.add_cascade(label="Palettes", menu=self.cmenu)
        self.window.config(menu=self.menu)
    
    def on_keypress(self, event):
        for acc, command in self.menu_commands.items():
            if acc is None:
                continue
            acc = acc.lower()
            if event.char is not None and acc == event.char.lower():
                command()
                return
            if event.keysym is not None and acc == event.keysym.lower():
                command()
                return
        # fall through
        self.core.on_keypress(event)
    
    def add_hotkey(self, command, accelerator):
        self.menu_commands[accelerator] = command
        
    def set_palette_idx(self, idx):
        self.palette_idx = clamp_hoi(idx, 0, 4)
        self.refresh()
    
    def get_selected_palette_idx(self):
        return self.palette_idx

    def refresh(self, fx=None, fy=None, palette=True):
        max = constants.ram_range_title_screen[1] - constants.ram_range_title_screen[0]
        usage = self.screen.size()
        self.usage_bar.configure(
            usage=usage,
            max=max 
        )
        
        # set tiles in screen
        for x in range(self.w // micro_width):
            for y in range(self.h // micro_height):
                if x == fx or fx is None:
                    if y == fy or fy is None:
                        palette_idx = self.screen.get_palette_idx(x, y)
                        img = self.core.screen_micro_images[palette_idx][self.screen.get_tile(x, y)]
                        self.place_canvas.set_tile_image(x, y, img)
        
        # set tiles in palette
        if palette:
            for x in range(16):
                for y in range(16):
                    img = self.core.screen_micro_images[self.get_selected_palette_idx()][x + 16 * y]
                    self.select_canvas.set_tile_image(x, y, img)
        
    def on_select_click(self, idx, edit):
        if idx < 256:
            self.select_canvas.selection_idx = idx
        self.select_canvas.refresh()
        
    def on_place_click(self, idx, edit):
        tile = self.select_canvas.selection_idx if not edit else 0
        if tile is None:
            return
        
        x = idx % (self.w // micro_width)
        y = idx // (self.w // micro_width)
            
        # TODO - switch to actions system (for undo)
        self.core.apply_action(GuiAction(
            type="screen", refresh=["screen"],
            context=GuiScreenEditor,
            screen=self.screen,
            x=x,
            y=y,
            palette_idx=self.get_selected_palette_idx() if not edit else None,
            prev_palette_idx=None, # fill in later
            tile=tile,
            prev_tile=None # fill in later
        ))
        
        self.refresh()
        
# select mods to enable
class GuiMod(GuiSubWindow):
    def __init__(self, core):
        super().__init__(core, "Mods")
        self.mods = []
        for mod in sorted({**core.data.mods, "mapper-extension": False}.keys()):
            if mod == "":
                continue
            enabled = core.data.mapper_extension if mod == "mapper-extension" else core.data.mods[mod]
            modl = {
                "name": mod,
                "widget": ttk.Checkbutton(self.window, text=mod, command=self.command)
            }
            modl["widget"].pack(fill=tk.X)
            modl["widget"].state(['!alternate'])
            if enabled:
                modl["widget"].state(['selected'])
            else:
                modl["widget"].state(['!selected'])
            self.mods.append(modl)
    
    def command(self):
        for mod in self.mods:
            enabled = mod["widget"].instate(['selected'])
            name = mod["name"]
            if name == "mapper-extension":
                if self.core.data.mapper_extension != enabled:
                    self.core.apply_action(GuiAction(
                        type="mod", refresh=["all"],
                        context=GuiMod,
                        mod_name=name,
                        new_value=enabled,
                        prev_value=not enabled
                    ))
            else:
                if self.core.data.mods[name] != enabled:
                    self.core.apply_action(GuiAction(
                        type="mod", refresh=["all"] if name == "extended_objects" else [],
                        context=GuiMod,
                        mod_name=name,
                        new_value=enabled,
                        prev_value=not enabled
                    ))
        
# 16x16 macro-tile editor
class GuiMedEdit(GuiSubWindow):
    palette_var_counter = 0
    def __init__(self, core):
        super().__init__(core, "Med-Tile Editor")
        self.v_world_idx = tk.StringVar()
        self.v_world_idx.set("1")
        self.v_med_tile_idx = tk.StringVar()
        self.v_med_tile_idx.set("28") # a reasonable default tile to edit
        self.v_hard = tk.BooleanVar()
        self.v_hard.set(False)
        self.v_palette_var_string = "palette_idx" + str(GuiMedEdit.palette_var_counter)
        GuiMedEdit.palette_var_counter += 1
        self.v_palette_idx = tk.IntVar(0, name=self.v_palette_var_string)
        self.world_idx = 0
        self.med_tile_idx = 0xD
        self.select_canvas = None
        self.elts_micro_select = []
        self.init()
        
        self.v_world_idx.trace("w", callback=self.on_idx_change)
        self.v_med_tile_idx.trace("w", callback=self.on_idx_change)
        self.v_hard.trace("w", callback=self.on_idx_change)
        self.v_palette_idx.trace("w", callback=self.on_idx_change)
        self.handling = False
        
    def on_idx_change(self, var, unk, mode):
        if self.handling:
            return
        self.handling = True
        if mode == 'w':
            self.hard = self.v_hard.get()
            # world index
            try:
                val = self.v_world_idx.get()
                self.world_idx = clamp_hoi(int(val, 16) - 1, 0, len(self.core.data.worlds))
                if HX(self.world_idx) != val:
                    self.v_world_idx.set(HX(self.world_idx + 1))
            except:
                self.v_world_idx.set("")
            
            # med tile idx    
            try:
                maxtile = len(self.core.data.worlds[self.world_idx].med_tiles) + constants.global_med_tiles_count
                val = self.v_med_tile_idx.get()
                self.med_tile_idx = clamp_hoi(int(val, 16), 0, maxtile)
                if HX(self.med_tile_idx) != val:
                    self.v_med_tile_idx.set(HX(self.med_tile_idx))
            except:
                self.v_med_tile_idx.set("")
            
            if var == self.v_palette_var_string:
                self.core.apply_action(GuiAction(
                    type="med-palette", refresh=["med"],
                    context=GuiMedEdit,
                    world_idx=self.world_idx,
                    med_tile_idx=self.med_tile_idx,
                    palette_idx=self.v_palette_idx.get(),
                    prev_palette_idx=self.core.data.worlds[self.world_idx].med_tile_palettes[self.med_tile_idx]
                ))
            else:
                self.v_palette_idx.set(self.core.data.worlds[self.world_idx].med_tile_palettes[self.med_tile_idx])
        self.refresh()
        self.handling = False
        
    def init(self):
        topbar = tk.Frame(self.window)
        mainframe = tk.Frame(self.window)
        
        label = ttk.Label(topbar, text="World: ")
        label.grid(column=0, row=0)
        
        entry = ttk.Entry(topbar, width=2, textvariable = self.v_world_idx)
        entry.grid(column=1, row=0)
        
        label = ttk.Label(topbar, text="Med Tile ID: ")
        label.grid(column=2, row=0)
        
        entry = ttk.Entry(topbar, width=2, textvariable = self.v_med_tile_idx)
        entry.grid(column=3, row=0)
        
        label = ttk.Label(topbar, text="Hard: ")
        label.grid(column=0, row=1)
        
        entry = ttk.Checkbutton(topbar, variable=self.v_hard)
        entry.grid(column=1, row=1)
        
        topbar.pack(fill=tk.X)
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        self.med_tile_select_width = 4
        height=224
        
        self.select_canvas = GuiMicroGrid(mainframe, self.core, height=8 * 16 * self.core.zoom() + 16, dims=(16, 16), chunkdim=(1, 1), cb=self.on_select_click, scroll=False)
        self.select_canvas.divides = [0x10, 0x56]
        self.select_canvas.pack(side=tk.RIGHT)
        
        self.place_canvas = GuiMicroGrid(mainframe, self.core, height=med_height * self.core.zoom(), dims=(med_width // micro_width, med_height // micro_height), scroll=False, cb=self.on_place_click)
        self.place_canvas.pack()
        
        self.info_label = ttk.Label(mainframe)
        self.info_label.pack()
        
        for palette_idx in range(4):
            radio = tk.Radiobutton(mainframe, text="Palette " + str(palette_idx + 1), value=palette_idx, variable=self.v_palette_idx)
            radio.pack()
        
    def refresh(self):
        self.core.delete_elements(self.select_canvas, self.elts_micro_select)
        self.elts_med_select = []
        
        if self.select_canvas is None:
            return
        world = self.core.data.worlds[self.world_idx]
        
        palette_idx = world.get_med_tile_palette_idx(self.med_tile_idx, self.hard)
        
        # populate
        med_tile = world.get_med_tile(self.med_tile_idx)
        for j in range(4):
            micro_tile_idx = med_tile[j]
            x = (j % 2)
            y = (j >= 2)
            
            # tile
            img = self.core.micro_images[world.idx][palette_idx][micro_tile_idx]
            self.place_canvas.set_tile_image(x, y, img)
        
        self.select_canvas.configure(dims=(16, 16))
        count = 16 * 16
        for micro_tile_idx in range(count):
            x = (micro_tile_idx % 16)
            y = (micro_tile_idx // 16)
            
            # set images
            
            # (please don't look at this code. This was done to fix a horrible, horrible bug.)
            palette_idx = constants.component_micro_tile_palettes[y][x] % 4
            palette_sub_idx = 1
            
            # because...
            if palette_idx == 0:
                palette_sub_idx = 0
            if palette_idx == 1:
                palette_idx = 0
            
            # ok
            img = self.core.micro_images[palette_idx][palette_sub_idx][micro_tile_idx]
            
            self.select_canvas.set_tile_image(x, y, img)
        self.select_canvas.refresh()
        
        # set label
        labelstr = ""
        if self.med_tile_idx < constants.global_med_tiles_count:
            labelstr = "Global"
        else:
            labelstr = "World " + str(self.world_idx + 1)
        if self.med_tile_idx < 0x1e:
            labelstr += "; hardcoded symmetry"
        if self.med_tile_idx >= world.max_symmetry_idx:
            labelstr += "; self-symmetric"
        self.info_label.configure(text=labelstr, anchor=tk.NW)
    
    def ctl(self, kwargs):
        if "med_tile_idx" in kwargs:
            self.v_med_tile_idx.set(HB(kwargs["med_tile_idx"]))
        if "world_idx" in kwargs:
            self.v_world_idx.set(HX(kwargs["world_idx"] + 1))
        if "hard" in kwargs:
            self.v_hard.set(kwargs["hard"])
        if "refresh" in kwargs and kwargs["refresh"]:
            self.refresh()
    
    def on_place_click(self, idx, edit):
        world = self.core.data.worlds[self.world_idx]
        if edit or self.select_canvas.selection_idx is not None:
            w = 2
            x = (idx % w)
            y = (idx // w)
            
            x = clamp_hoi(x, 0, 2)
            y = clamp_hoi(y, 0, 2)
            
            i = clamp_hoi(x + 2 * y, 0, 4)
            
            med_tile = world.get_med_tile(self.med_tile_idx)
            self.core.apply_action(GuiAction(
                type="med", refresh=["med"],
                context=GuiMedEdit,
                world_idx=self.world_idx,
                med_tile_idx=self.med_tile_idx,
                med_tile_sub=i,
                micro_tile_idx=0 if edit else self.select_canvas.selection_idx,
                prev_micro_tile_idx=med_tile[i]
            ))
    
    def on_select_click(self, idx, edit):
        if idx < 256:
            self.select_canvas.selection_idx = idx
        self.select_canvas.refresh()

# 32x32 macro-tile editor
class GuiMacroEdit(GuiSubWindow):
    def __init__(self, core):
        super().__init__(core, "Macro-Tile Editor")
        self.v_world_idx = tk.StringVar()
        self.v_world_idx.set("1")
        self.v_macro_tile_idx = tk.StringVar()
        self.v_macro_tile_idx.set("0D") # a reasonable default tile to edit
        self.v_hard = tk.BooleanVar()
        self.v_hard.set(False)
        self.world_idx = 0
        self.macro_tile_idx = 0xD
        self.select_canvas = None
        self.elts_med_select = []
        self.init()
        
        self.v_world_idx.trace("w", callback=self.on_idx_change)
        self.v_macro_tile_idx.trace("w", callback=self.on_idx_change)
        self.v_hard.trace("w", callback=self.on_idx_change)
        self.handling = False
        
    def on_idx_change(self, var, unk, mode):
        if self.handling:
            return
        self.handling = True
        if mode == 'w':
            self.hard = self.v_hard.get()
            # world index
            try:
                val = self.v_world_idx.get()
                self.world_idx = clamp_hoi(int(val, 16) - 1, 0, len(self.core.data.worlds))
                if HX(self.world_idx) != val:
                    self.v_world_idx.set(HX(self.world_idx + 1))
            except:
                self.v_world_idx.set("")
            
            # macro tile idx    
            try:
                maxtile = len(self.core.data.worlds[self.world_idx].macro_tiles) + constants.global_macro_tiles_count
                val = self.v_macro_tile_idx.get()
                self.macro_tile_idx = clamp_hoi(int(val, 16), 0, maxtile)
                if HX(self.macro_tile_idx) != val:
                    self.v_macro_tile_idx.set(HX(self.macro_tile_idx))
            except:
                self.v_macro_tile_idx.set("")
        self.refresh()
        self.handling = False
        
    def init(self):
        topbar = tk.Frame(self.window)
        mainframe = tk.Frame(self.window)
        
        label = ttk.Label(topbar, text="World: ")
        label.grid(column=0, row=0)
        
        entry = ttk.Entry(topbar, width=2, textvariable = self.v_world_idx)
        entry.grid(column=1, row=0)
        
        label = ttk.Label(topbar, text="Macro Tile ID: ")
        label.grid(column=2, row=0)
        
        entry = ttk.Entry(topbar, width=2, textvariable = self.v_macro_tile_idx)
        entry.grid(column=3, row=0)
        
        label = ttk.Label(topbar, text="Hard: ")
        label.grid(column=0, row=1)
        
        entry = ttk.Checkbutton(topbar, variable=self.v_hard)
        entry.grid(column=1, row=1)
        
        topbar.pack(fill=tk.X)
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        self.med_tile_select_width = 4
        height=224
        
        self.select_canvas = GuiMicroGrid(mainframe, self.core, height=height, chunkdim=(2, 2), cb=self.on_select_click)
        self.select_canvas.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        
        self.place_canvas = GuiMicroGrid(mainframe, self.core, height=macro_height * self.core.zoom(), dims=(macro_width // micro_width * 2, macro_height // micro_height), scroll=False, cb=self.on_place_click)
        self.place_canvas.pack()
        
        self.info_label = ttk.Label(mainframe)
        self.info_label.pack()
    
    def refresh(self):
        self.core.delete_elements(self.select_canvas, self.elts_med_select)
        self.elts_med_select = []
        
        if self.select_canvas is None:
            return
        world = self.core.data.worlds[self.world_idx]
        zoom = 0
        
        # populate
        macro_tile = world.get_macro_tile(self.macro_tile_idx)
        for i in range(4):
            med_tile_idx = macro_tile[i]
            mirror_tile_idx = world.mirror_tile(med_tile_idx)
            med_tile = world.get_med_tile(med_tile_idx)
            mirror_tile = world.get_med_tile(mirror_tile_idx)
            palette_idx = world.get_med_tile_palette_idx(med_tile_idx, self.hard)
            mirror_palette_idx = world.get_med_tile_palette_idx(mirror_tile_idx, self.hard)
            for j in range(4):
                micro_tile_idx = med_tile[j]
                mirror_micro_tile_idx = mirror_tile[j]
                x = (i % 2) * 2 + (j % 2)
                y = (i >= 2) * 2 + (j >= 2)
                
                mirrorx = 4 + ((i + 1) % 2) * 2 + (j % 2)
                
                # tile
                img = self.core.micro_images[world.idx][palette_idx][micro_tile_idx]
                self.place_canvas.set_tile_image(x, y, img)
                
                # mirror tile
                img = self.core.micro_images[world.idx][mirror_palette_idx][mirror_micro_tile_idx]
                self.place_canvas.set_tile_image(mirrorx, y, img)
        
        self.select_canvas.divides = [constants.global_med_tiles_count, 0x1e, world.max_symmetry_idx]
        count = len(world.med_tiles) + constants.global_med_tiles_count
        self.select_canvas.configure(dims=(4 * med_width // micro_width, ceil_to((count / (4)) * med_height // micro_height, med_height // micro_height)))
        for med_sel_idx in range(count):
            med_y = (med_sel_idx // self.med_tile_select_width)
            med_x = (med_sel_idx % self.med_tile_select_width)
            
            rounded_sel_idx = med_sel_idx - (med_sel_idx % self.med_tile_select_width)
            
            # set images
            med_tile_idx = med_sel_idx
            med_tile = world.get_med_tile(med_tile_idx)
            palette_idx = world.get_med_tile_palette_idx(med_tile_idx, self.hard)
            for i in range(4):
                micro_tile_idx = world.get_micro_tile(med_tile[i], self.hard)
                x = i % 2 + med_x * 2
                y = i // 2 + med_y * 2
                img = self.core.micro_images[world.idx][palette_idx][micro_tile_idx]
                self.select_canvas.set_tile_image(x, y, img)
            self.select_canvas.clear_from(count)
        self.select_canvas.refresh()
        
        # set label
        labelstr = ""
        if self.macro_tile_idx < constants.global_macro_tiles_count:
            labelstr = "Global"
        else:
            labelstr = "World " + str(self.world_idx + 1)
        self.info_label.configure(text=labelstr, anchor=tk.NW)
    
    def ctl(self, kwargs):
        if "macro_tile_idx" in kwargs:
            self.v_macro_tile_idx.set(HB(kwargs["macro_tile_idx"]))
        if "world_idx" in kwargs:
            self.v_world_idx.set(HX(kwargs["world_idx"] + 1))
        if "hard" in kwargs:
            self.v_hard.set(kwargs["hard"])
        if "refresh" in kwargs and kwargs["refresh"]:
            self.refresh()
    
    def on_place_click(self, idx, edit):
        world = self.core.data.worlds[self.world_idx]
        if edit or self.select_canvas.selection_idx is not None:
            w = macro_width // micro_width * 2
            x = (idx % w) // 2
            y = (idx // w) // 2
            
            # mirror
            if x >= macro_width // med_width:
                x = macro_width // med_width * 2 - x - 1
            
            x = clamp_hoi(x, 0, macro_width // med_width)
            y = clamp_hoi(y, 0, macro_height // med_height)
            
            i = x + 2 * y
            
            macro_tile = world.get_macro_tile(self.macro_tile_idx)
            self.core.apply_action(GuiAction(
                type="macro", refresh=["macro"],
                context=GuiMacroEdit,
                world_idx=self.world_idx,
                macro_tile_idx=self.macro_tile_idx,
                macro_tile_sub=i,
                med_tile_idx=0 if edit else self.select_canvas.selection_idx,
                prev_med_tile_idx=macro_tile[i]
            ))
    
    def on_select_click(self, idx, edit):
        world = self.core.data.worlds[self.world_idx]
        if idx < len(world.med_tiles) + constants.global_med_tiles_count:
            if edit:
                self.core.subwindowctl(GuiMedEdit, world_idx=self.world_idx, med_tile_idx=self.select_canvas.selection_idx)
            else:
                self.select_canvas.selection_idx = idx
        self.select_canvas.refresh()

# main window and gui data
class Gui:
    def __init__(self):
        self.data = None
        self.subwindows = dict()
        self.mouse_button_actions = ["place", "seam", "remove", "seam", "select", "eyedropper"] # left, middle, right, ctrl, shift, shift+right
        self.file = {"hack": None, "rom": None, "image": None, "ips": None, "bps": None, "chr": None}
        self.dirty = False
        self.undo_buffer = []
        self.redo_buffer = []
        self.show_lines = True
        self.show_patches = True
        self.show_objects = True
        self.show_crosshairs = True
        self.show_mirror = True
        self.placable_objects = []
        self.placable_tiles = []
        self.menu_commands = dict()
        self.object_select_gid = None
        self.macro_tile_select_id = None
        self.unitile_select_id = None
        self.level = None
        self.stage_idx = 0
        self.hard = False
        self.zoom_idx = 0
        self.scroll_seam_accumulator = 0
        
        # preferences
        self.macro_tile_select_width = 4
        
        # clearable elts
        self.elts_object_select = []
        self.elts_stage_horizontal_lines = []
        self.elts_row_lines = [[] for i in range(constants.macro_rows_per_level)]
        self.elts_objects = []
        self.elts_patch_rects = []
        self.elt_object_select_rect = None
        self.elts_stage_select = []
        
        self.mapper_extension_components_init = False
        
        self.select_rect = None
        self.select_rect_final = False
        self.copy_buffer = None
        
        self.init()
    
    def zoom(self):
        return int(max(0, self.zoom_idx) + 1)
        
    def play_hack(self, currentlevel=False):
        if self.data is None:
            return False
        
        path = os.path.join(tempfile.gettempdir(), "mmagedit-hack.nes")
        if currentlevel:
            self.data.startlevel = self.level.level_idx+1
            self.data.startdifficulty = 1 if self.hard else 0
        success = self.data.write(path)
        self.data.startlevel=0
        self.data.startdifficulty=0
        if not success:
            self.errorbox()
            return False
        
        if not emulaunch.find_emulator():
            tkinter.messagebox.showerror("Emulator not found", "please ensure " + emulaunch.nesmname() + " exists in the same directory as mmagedit.")
            
        return emulaunch.launch(path)
        
        
    # perform fileio, possibly ask for prompt (if auto is True, may not ask.)
    def fio_prompt(self, type, save=False, auto=False):
        path = None
        if auto:
            path = self.file[type]
        
        # prompt properties
        promptfn = partial(tkinter.filedialog.asksaveasfilename) if save else partial(tkinter.filedialog.askopenfilename)
        title = "select " + type
        if type == "rom":
            if save:
                title = "export to ROM"
            else:
                title = "select base ROM"
            promptfn = partial(promptfn, filetypes=[("NES Rom", ".nes")])
        if type == "hack":
            promptfn = partial(promptfn, filetypes=[("MMagEdit Hack", ".txt")])
        if type == "chr":
            promptfn = partial(promptfn, filetypes=[("CHR ROM image dump", ".png")])
        if save:
            if type == "image":
                promptfn = partial(tkinter.filedialog.askdirectory, mustexist=True)
                title = "select destination directory for images"
            if type == "rom":
                promptfn = partial(promptfn, defaultextension=".nes")
            if type == "hack":
                promptfn = partial(promptfn, defaultextension=".txt")
            if type == "ips":
                promptfn = partial(promptfn, defaultextension=".ips")
            if type == "bps":
                promptfn = partial(promptfn, defaultextension=".bps")
        
        if path is None:
            path = promptfn(title=title)
        if path == "" or path == ():
            path = None
        
        result = self.fio_direct(path, type, save)
        
        if result and not save:
            self.refresh_all()
        self.refresh_title()
        self.refresh_label()
        return result
        
    # display error boxes if data has errors.
    def errorbox(self, warning=False):
        if len(self.data.errors) > 0:
            title = "Warning" if warning else "Error"
            message = "" if warning else "An error occurred, preventing the file I/O operation:\n\n"
            for error in self.data.errors:
                message += ("Warning: " if len(self.data.errors) <= 1 else "- ") + error + "\n"
            if warning:
                tkinter.messagebox.showwarning(title, message)
            else:
                tkinter.messagebox.showerror(title, message)
            self.data.errors = []
        
    # loads/saves rom/hack/image
    # after loading, please call refresh_all().
    def fio_direct(self, path, type, save=False):
        try:
            if path == None:
                return False
                
            # must load rom before anything else
            if self.data is None and (save or type != "rom"):
                return False
                
            # cannot load rom twice
            if type == "rom" and not save and self.data is not None:
                return False
                
            # cannot load ips
            if type == "ips" and not save:
                return False

            # cannot load image
            if type == "image" and not save:
                return False

            # cannot save chr (save image instead)
            if type == "chr" and save:
                return False
            
            # cannot load bps
            if type == "bps" and not save:
                return False
            
            if type == "rom":
                if save:
                    rval = self.data.write(path)
                    self.errorbox(rval)
                    return rval
                else:
                    self.data = mmdata.MMData()
                    if self.data.read(path):
                        # update menu enable/disable
                        self.filemenu.entryconfig(self.menu_base_rom, state=tk.DISABLED)
                        for m in self.menu_fio:
                            self.filemenu.entryconfig(m, state=tk.NORMAL)
                        self.file[type] = path
                        self.errorbox(True)
                        return True
                    else:
                        self.errorbox(False)
                        self.data = None # set data to none so we don't later think the data exists.
                        return False
            
            if type == "image" and save:
                self.file[type] = path
                rval = mmimage.export_images(self.data, path)
                self.errorbox(rval)
                return rval

            if type == "chr" and not save:
                self.file[type] = path
                rval = mmimage.set_chr_rom_from_image_path(self.data, path)
                self.errorbox(rval)
                return rval
                
            if type == "ips" and save:
                self.file[type] = path
                rval = self.data.write_ips(path)
                self.errorbox(rval)
                return rval

            if type == "bps" and save:
                self.file[type] = path
                rval = self.data.write_bps(path)
                self.errorbox(rval)
                return rval
            
            if type == "hack" and not save:
                self.dirty = False
                self.file[type] = path
                rval = self.data.parse(path)
                self.errorbox(rval)
                return rval
            
            if type == "hack" and save:
                self.dirty = False
                self.file[type] = path
                rval = self.data.stat(path)
                self.errorbox(rval)
                return rval
            
            # note: do not refresh anything directly
            # the caller is expected to call the refresh functions
            # this allows the caller to invoke several fio_direct commands before refreshing
        except Exception as e:
            # catch any save/load error, and return false if one occurs.
            print(e)
            tkinter.messagebox.showerror("Internal Error", "An internal error occurred during the I/O process:\n\n" + str(e))
        return False
        
    def set_zoom(self, zoom_idx, force=False):
        
        if zoom_idx == self.zoom_idx:
            return
            
        if not force:
            if tkinter.messagebox.askyesno("Warning", "Magnification is currently in beta. It may take several seconds to process this request. Additionally, subwindows may take a long time to close. Continue?\n\n(Ctrl+Alt+" + str(zoom_idx + 1) + " to zoom without seeing this dialogue box.)") is False:
                return
        
        # close subwindows
        while len(self.subwindows) > 0:
            for subwindow in self.subwindows:
                self.subwindows[subwindow].on_close()
                # FIXME: weird control flow. No need for the nested loop.
                break
            
        self.zoom_idx = zoom_idx
        self.stage_micro_images = [[None for y in range(level_height // micro_height)] for x in range(level_width // micro_width)]
        self.stage_mirror_cover_images = [[None for x in range(level_width // med_width)] for y in range(level_height // macro_height)]
        self.object_select_images = [None for y in range(0x100)]
        self.stage_canvas.configure(width=screenwidth * self.zoom(), scrollregion=(0, 0, level_width * self.zoom(), level_height * self.zoom()))
        self.object_canvas.configure(width=objwidth * self.zoom())
        self.macro_canvas.refresh_zoom()
        if self.mapper_extension_components_init and self.data.mapper_extension:
            self.unitile_canvas.refresh_zoom()
        self.refresh_all()
        
    def refresh_all(self):
        self.refresh_chr()
        if self.level is None:
            self.select_stage(0)
        else:
            self.select_stage(self.level.level_idx, self.hard)
        
    def soft_quit(self):
        if self.dirty and self.data is not None:
            response = tkinter.messagebox.askyesnocancel("Save before Quitting?", "Unsaved changes have been made. Do you want to save before quitting?")
            if response is None:
                # cancel
                return
            elif response:
                if not self.fio_prompt("hack", True):
                    # user aborted save -- don't quit.
                    return
        self.window.quit()
    
    def attach_scrollbar(self, canvas, frame):
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=canvas.yview)
        canvas.config(yscrollcommand=scrollbar.set)
        # scrolling
        fn = partial(self.on_mousewheel, canvas)
        if os.name == 'nt':
            # windows
            canvas.bind("<MouseWheel>", fn)
        else:
            # linux
            canvas.bind("<Button-4>", fn)
            canvas.bind("<Button-5>", fn)
    
    def on_mousewheel(self, canvas, event):
        delta = 0
        if event.num == 5:
            delta = 2
        elif event.num == 4:
            delta = -2
        else:
            delta = -1*(event.delta/120)
        
        if delta != 0:
            if canvas == self.stage_canvas and event.state & 1:
                if not self.hard:
                    # adjust seam.
                    self.scroll_seam_accumulator += delta / 2
                    if self.scroll_seam_accumulator >= 1:
                        self.scroll_seam_accumulator = 0
                        diff = 1
                    elif self.scroll_seam_accumulator <= -1:
                        self.scroll_seam_accumulator = 0
                        diff = -1
                    else:
                        return
                    y = self.get_event_y(event, self.stage_canvas, level_height * self.zoom()) / self.zoom()
                    y = clamp_hoi(y, 0, level_height)
                    macro_y = clamp_hoi(level_height - y, 0, level_height) // macro_height
                    if self.level:
                        macro_row = self.level.macro_rows[macro_y]
                        self.apply_action(GuiAction(
                            type="seam", refresh=["row", "patches"],
                            macro_row_idx=macro_y,
                            prev_seam=macro_row.seam,
                            seam=int(macro_row.seam + 0x10 + diff) & 0xf
                        ))
            else:
                # scroll window.
                canvas.yview_scroll(delta, "units")
        
    def ctl(self, **kw):
        if "flipx" in kw:
            self.v_flipx.set(kw["flipx"])
            self.refresh_object_select()
        if "flipy" in kw:
            self.v_flipy.set(kw["flipy"])
            self.refresh_object_select()
        if "drop" in kw:
            self.v_drop.set(kw["drop"] if self.data.mapper_extension else False)
            self.refresh_object_select()
        if "show_objects" in kw:
            self.show_objects = kw["show_objects"]
            self.refresh_objects()
        if "show_crosshairs" in kw and self.show_objects:
            self.show_crosshairs = kw["show_crosshairs"]
            self.refresh_objects()
        if "show_lines" in kw:
            self.show_lines = kw["show_lines"]
            for i in range(constants.macro_rows_per_level):
                self.refresh_row_lines(i)
            self.refresh_horizontal_lines()
            if self.show_crosshairs and self.show_lines:
                self.refresh_objects() # necessary to prevent crosshairs from falling behind grid
        if "show_mirror" in kw:
            self.show_mirror = kw["show_mirror"]
            for i in range(constants.macro_rows_per_level):
                self.refresh_row_lines(i)
            if self.show_crosshairs and self.show_lines:
                self.refresh_objects() # necessary to prevent crosshairs from falling behind grid
        if "show_patches" in kw and (self.hard or self.data.mapper_extension):
            self.show_patches = kw["show_patches"]
            self.refresh_patch_rects()
        
        self.refresh_label()
    
    def clear_stage(self):
        if tkinter.messagebox.askyesno("Clear Stage", "Clearing the stage cannot be undone. All difficulties for this stage will be cleared. Are you sure you'd like to proceed?"):
            level = self.level
            if level:
                level.hardmode_patches = []
                level.objects = []
                for macro_row in level.macro_rows:
                    macro_row.macro_tiles = [0, 0, 0, 0]
                    macro_row.seam = 0
                level.unitile_patches = []
                
                # lazy, but this is one way to refresh everything.
                self.select_stage(self.stage_idx, self.hard)
                self.clear_undo_buffers()
    
    def showinfo(self, msg, title="Information"):
        tkinter.messagebox.showinfo(title, msg)
        
    def about(self):
        tkinter.messagebox.showinfo(constants.mmname, constants.mminfo)
        
    def usage(self):
        tkinter.messagebox.showinfo(constants.mmname + " - Usage", """
Mouse controls:

- Left Click: place stage element.
- Right Click: remove stage element.
- Middle Click / Ctrl Click / Shift Scroll: edit seam (mirror) position.
- Shift Click: drag to select.
- Shift Right Click: eyedropper.

Please remember to save frequently and make backups.
""".strip())
    
    # handles a kepyress event
    def on_keypress(self, event):
        shift = event.state & 0x1
        ctrl = event.state & 0x4
        alt = event.state & 0x88
        for acc, command in self.menu_commands.items():
            if acc is None:
                continue
            acc = acc.lower()
            if ctrl and "ctrl+" not in acc:
                continue
            if shift and "shift+" not in acc:
                continue
            if alt and "alt+" not in acc:
                if acc in ["ctrl+" + str(i) for i in range(10)]: # hacky zoom fix for tkinter alt modifier bug.
                    continue
            if acc.startswith("ctrl+"):
                if not ctrl:
                    continue
                else:
                    acc = acc[5:]
            if acc.startswith("alt+"):
                if not alt:
                    continue
                else:
                    acc = acc[4:]
            if acc.startswith("shift+"):
                if not shift:
                    continue
                else:
                    acc = acc[6:]
            if event.char is not None and acc == event.char.lower():
                command()
                return
            if event.keysym is not None and acc == event.keysym.lower():
                command()
                return
    
    def get_tile_dangerous(self, x, y):
        if x in range(0x20) and y in range(4 * constants.macro_rows_per_level):
            if self.stage_micro_dangerous[x][y]:
                return True
        return False
    
    def get_event_y(self, event, canvas, height):
        return event.y + canvas.yview()[0] * height
        
    def clear_undo_buffers(self):
        self.undo_buffer = []
        self.redo_buffer = []
        self.editmenu.entryconfig(self.menu_edit_undo, state=tk.DISABLED)
        self.editmenu.entryconfig(self.menu_edit_redo, state=tk.DISABLED)
        self.refresh_label()
        self.refresh_title()
    
    # applies an individual GuiAction and accumulates refresh.
    def apply_action_helper(self, action, undo, acc):
        # open context for action, if needed.
        if action.context is None:
            if action.level_idx is not None:
                # switch to the stage this action was/is applied to
                # (we only do this so as not to confuse the user -- these lines could be commented out.)
                if self.level.level_idx != action.level_idx or self.hard != action.hard:
                    self.select_stage(action.level_idx, action.hard)
            else:
                # record stage and hardmode so that if this is undone the user will return to here.
                action.level_idx = self.level.level_idx
                action.hard = self.hard
        elif action.context == GuiMacroEdit:
            self.subwindowctl(GuiMacroEdit, world_idx=action.world_idx, macro_tile_idx=action.macro_tile_idx)
        elif action.context == GuiMedEdit:
            self.subwindowctl(GuiMedEdit, world_idx=action.world_idx, med_tile_idx=action.med_tile_idx)
        elif action.context == GuiScreenEditor:
            self.subwindowctl(GuiScreenEditor, screen=action.screen)

        level = self.level

        if action.type == "tile":
            tile = action.prev_tile if undo else action.tile
            macro_row = level.macro_rows[action.macro_row_idx]
            if not undo and action.prev_tile is None:
                action.prev_tile = macro_row.macro_tiles[action.macro_idx]
            macro_row.macro_tiles[action.macro_idx] = tile
        if action.type == "seam":
            seam = action.prev_seam if undo else action.seam
            macro_row = level.macro_rows[action.macro_row_idx]
            if action.prev_seam is None and not undo:
                action.prev_seam = macro_row.seam
            macro_row.seam = seam

            # shift unitile patches accordingly.
            seam_diff = action.prev_seam - action.seam if undo else action.seam - action.prev_seam
            for u in level.unitile_patches:
                if u.y == 2 * action.macro_row_idx or u.y == 2 * action.macro_row_idx + 1:
                    u.x += seam_diff
                    u.x %= 0x10
        if action.type == "object":
            obj = action.object
            if undo != action.remove:
                level.objects.remove(obj)
            else:
                level.objects.append(obj)
                
            # when editing objects, they should become visible if they aren't already.
            self.show_objects = True
        if action.type == "patch":
            patch = action.patch
            if undo != action.remove:
                level.hardmode_patches.remove(patch)
            else:
                level.hardmode_patches.append(patch)
        if action.type == "macro":
            world = self.data.worlds[action.world_idx]
            macro_tile = world.get_macro_tile(action.macro_tile_idx)
            if action.macro_tile_sub in range(4):
                macro_tile[action.macro_tile_sub] = action.prev_med_tile_idx if undo else action.med_tile_idx
        if action.type == "med":
            world = self.data.worlds[action.world_idx]
            med_tile = world.get_med_tile(action.med_tile_idx)
            med_tile[action.med_tile_sub] = action.prev_micro_tile_idx if undo else action.micro_tile_idx
        if action.type == "med-palette":
            world = self.data.worlds[action.world_idx]
            world.med_tile_palettes[action.med_tile_idx] = action.prev_palette_idx if undo else action.palette_idx
        if action.type == "mod":
            if action.mod_name == "mapper-extension":
                self.data.mapper_extension = action.prev_value if undo else action.new_value
                # set UI to not be on object drop in case object drop is disabled.
                self.ctl(drop=False)
            else:
                self.data.mods[action.mod_name] = action.prev_value if undo else action.new_value
        if action.type == "screen":
            x = action.x
            y = action.y
            screen = action.screen
            
            # fill in undo
            if not undo and action.prev_tile is None:
                action.prev_tile = screen.get_tile(x, y)
                if action.palette_idx is not None:
                    action.prev_palette_idx = screen.get_palette_idx(x, y)
            
            palette_idx = action.prev_palette_idx if undo else action.palette_idx
            tile = action.prev_tile if undo else action.tile

            # apply tile/palette
            screen.set_tile(x, y, tile)
            if palette_idx is not None:
                screen.set_palette_idx(x, y, palette_idx)

        if action.type == "unitile":
            # unitile (med-tile patch) -- requires mapper extension
            # action.x
            # action.y
            # action.med_tile_idx [array of idxs per difficulty]
            # action.prev_med_tile_idx [array of idxs per difficulty]
            # action.difficulty_flag
            level.split_unitiles_by_difficulty()
            
            fill_in_prev = False
            if action.prev_med_tile_idx is None and not undo:
                fill_in_prev = True
                action.prev_med_tile_idx = [None] * 3

            med_tile_idx = action.prev_med_tile_idx if undo else action.med_tile_idx
            for j in range(3):
                jflag = 1 << (7 - j)
                if jflag & action.difficulty_flag:
                    continue
                if action.x < 0 or action.y < 0 or action.x >= level_width // med_width or action.y >= level_height // med_height:
                    continue
                matches = [u for u in level.unitile_patches if u.x == action.x and u.y == action.y and u.get_flags() & jflag == 0]
                if len(matches) == 0:
                    # add a new unitile
                    u = mmdata.UnitilePatch()
                    u.y = action.y
                    u.x = action.x
                    u.flag_normal = j == 0
                    u.flag_hard = j == 1
                    u.flag_hell = j == 2
                    u.med_tile_idx = None
                    matches.append(u)
                    level.unitile_patches.append(u)
                for u in matches:
                    if fill_in_prev:
                        action.prev_med_tile_idx[j] = u.med_tile_idx
                    u.med_tile_idx = med_tile_idx[j]
                
            level.combine_unitiles_by_difficulty()

        for r in action.refresh:
            acc["refresh"].add(r)

            # a couple refresh options need some additional information
            if r == "row":
                acc["macro_row_idxs"].add(action.macro_row_idx)
            if r == "macro":
                acc["macro_tile_idxs"].add(action.macro_tile_idx)
            if r == "med":
                acc["med_tile_idxs"].add(action.med_tile_idx)
            if r == "screen":
                for x in range(-1, 2):
                    for y in range(-1, 2):
                        acc["screen_coords"].add((action.x + x, action.y + y))

        # recurse:
        for a in action.children:
            self.apply_action_helper(a, undo, acc)

    def apply_action(self, action, undo=False):
        if self.data is None or self.level is None:
            return

        # for convenience
        level = self.level
        
        # add/remove action to/from undo buffer
        if undo:
            self.undo_buffer.remove(action)
            self.redo_buffer.append(action)
        else:
            if len(self.redo_buffer) > 0:
                if self.redo_buffer[-1] == action:
                    self.redo_buffer.remove(action)
                else:
                    self.redo_buffer = []
            self.undo_buffer.append(action)
        
        # update redo/undo button disabled/enabled
        self.editmenu.entryconfig(self.menu_edit_undo, state=tk.DISABLED if len(self.undo_buffer) == 0 else tk.NORMAL)
        self.editmenu.entryconfig(self.menu_edit_redo, state=tk.DISABLED if len(self.redo_buffer) == 0 else tk.NORMAL)
        
        # recursively apply actions
        acc = {
            "refresh": set(),
            "macro_row_idxs": set(),
            "macro_tile_idxs": set(),
            "med_tile_idxs": set(),
            "screen_coords": set()
        }
        
        self.apply_action_helper(action, undo, acc)

        refresh = acc["refresh"]
        if "row" in refresh:
            for macro_row_idx in acc["macro_row_idxs"]:
                self.refresh_row_tiles(macro_row_idx)
                self.refresh_row_lines(macro_row_idx)
            # needed for the weird "normal-mode grinder" effect
            self.refresh_objects()
        elif "objects" in refresh:
            self.refresh_objects()
        if "screen" in refresh:
            for coords in acc["screen_coords"]:
                self.subwindowctl(GuiScreenEditor, refresh=True, open=False, refx=coords[0], refy=coords[1], refpalette=False)
        if "patches" in refresh:
            self.refresh_patch_rects()
        if "macro" in refresh:
            self.subwindowctl(GuiMacroEdit, refresh=True, open=False)
            for macro_tile_idx in acc["macro_tile_idxs"]:
                self.refresh_on_macro_tile_update(macro_tile_idx)
            self.refresh_title()
            self.refresh_label() # just in case
        if "med" in refresh:
            self.subwindowctl(GuiMacroEdit, refresh=True, open=False)
            self.subwindowctl(GuiMedEdit, refresh=True, open=False)
            for med_tile_idx in acc["med_tile_idxs"]:
                self.refresh_on_med_tile_update(med_tile_idx)
        if "all" in refresh:
            self.refresh_all()
            
        # we've made a change.
        self.dirty = True
        
        self.refresh_label()
        self.refresh_title()

    def get_stage_placement_type(self):
        if self.object_select_gid is not None:
            return "object"
        if self.macro_tile_select_id is not None:
            if self.hard:
                return "macro-patch"
            else:
                return "macro-tile"
        if self.unitile_select_id is not None:
            return "med-tile"
        return ""
    
    def refresh_copy_menus(self):
        pass

    def paste_selection(self):
        level = self.level
        if level is None:
            return
        
        copy_buffer = self.copy_buffer    
        actions = []
        
        if copy_buffer.source_world_idx != level.world_idx:
            # we do this due to differing tilesets between worlds.
            self.showinfo("Cannot paste between worlds.")
            return
        
        if self.get_stage_placement_type() == "med-tile":
            for u in copy_buffer.unitile_patches:
                jflag = (0x80 if self.hard else 0x60)
                offset = (0, 0)
                if self.select_rect_final:
                    offset = (
                        int((self.select_rect[0]) // med_width) - copy_buffer.offset[0] // med_width,
                        int((level_height - self.select_rect[1]) // med_height) - (level_height - copy_buffer.offset[1]) // med_height
                    )
                         
                x = u.x + offset[0]
                y = u.y + offset[1]
                if x >= 0 and y >= 0 and x < level_width // med_width and y < level_height // med_height:
                    actions.append(GuiAction(
                        type="unitile", refresh=["row", "patches"],
                        macro_row_idx=y // 2,
                        x=x,
                        y=y,
                        difficulty_flag=jflag,
                        med_tile_idx=[u.med_tile_idx] * 3,
                        prev_med_tile_idx=None # fill this in on application.
                    ))
        if self.get_stage_placement_type() == "object":
            offset = (0, 0)
            if self.select_rect_final:
                offset = (
                    int((self.select_rect[0]) // micro_width) - copy_buffer.offset[0] // micro_width,
                    int((self.select_rect[1]) // micro_height) - (copy_buffer.offset[1]) // micro_height
                )
            for obj in copy_buffer.objects:                         
                x = obj.x + offset[0]
                y = obj.y + offset[1]
                obj=copy.copy(obj)
                obj.x = x
                obj.y = y
                if x >= 0 and y >= 0 and x < level_width // micro_width and y < level_height // micro_height:
                    skip=False
                    # don't place over an existing thing
                    for o in level.objects:
                        if o.x == obj.x and o.y == obj.y:
                            skip=True
                            break
                    if not skip:
                        actions.append(GuiAction(
                            type="object", refresh=["objects"],
                            object=obj,
                            remove=False
                        ))
        if self.get_stage_placement_type() in "macro-tile":
            macro_row_offset = clamp_hoi((level_height - self.select_rect[1]) // macro_height, 0, level_height // macro_height) if self.select_rect is not None and None not in self.select_rect else copy_buffer.macro_row_idx_max
            for i in range(len(copy_buffer.macro_rows)):
                macro_row = copy_buffer.macro_rows[i]
                macro_row_idx = macro_row_offset + i - len(copy_buffer.macro_rows)
                if macro_row_idx in range(level_height // macro_height):
                    actions.append(
                        GuiAction(
                            type="seam", refresh=["row", "patches"],
                            macro_row_idx=macro_row_idx,
                            prev_seam=None,
                            seam=macro_row.seam
                        )
                    )
                    for j in range(4):
                        actions.append(
                            GuiAction(
                                type="tile", refresh=["row"],
                                macro_row_idx=macro_row_idx,
                                macro_idx=j,
                                tile=macro_row.macro_tiles[j],
                                prev_tile=None # fill in later
                            )
                        )

        if len(actions) > 0:
            self.apply_action(GuiAction(
                children=actions
            ))

    def copycut_selection(self, do_copy, do_clear):
        level = self.level
        
        if not self.select_rect_final or level is None:
            return

        # create a bundle of actions so that they are all tied to the same undo buffer entry.
        if do_clear:
            actions = []

        # set copy buffer to contain the contents of the select rect.
        if do_copy:
            self.copy_buffer = CopyBuffer()
            self.copy_buffer.source_world_idx = self.level.world_idx
            self.copy_buffer.offset = (clamp_hoi(self.select_rect[0], 0, level_width), clamp_hoi(self.select_rect[1], 0, level_height))
        if self.get_stage_placement_type() in ["macro-tile", "macro-patch"]:
            macro_row_idx_min = clamp_hoi((level_height - self.select_rect[3]) / macro_height, 0, level_height / macro_height)
            macro_row_idx_max = clamp_hoi((level_height - self.select_rect[1]) / macro_height, 0, level_height / macro_height + 1)
            if do_copy:
                self.copy_buffer.macro_row_idx_max = macro_row_idx_max
            if self.get_stage_placement_type() == "macro-tile":
                for macro_row_idx in range(macro_row_idx_min, macro_row_idx_max):
                    if do_copy:
                        self.copy_buffer.macro_rows.append(
                            copy.deepcopy(
                                level.macro_rows[macro_row_idx]
                            )
                        )
                    if do_clear:
                        for j in range(4):
                            actions.append(
                                GuiAction(
                                    type="tile", refresh=["row"],
                                    macro_row_idx=macro_row_idx,
                                    macro_idx=j,
                                    tile=0,
                                    prev_tile=None # fill in later
                                )
                            )
            else:
                for patch in level.hardmode_patches:
                    if patch.y in range(macro_row_idx_min, macro_row_idx_max):
                        if do_copy:
                            self.copy_buffer.macro_patches.append(
                                copy.deepcopy(patch)
                            )
                        if do_clear:
                            actions.append(
                                GuiAction(
                                    type="patch", refresh=["row", "patches"],
                                    remove=True,
                                    macro_row_idx=patch.y,
                                    patch=patch
                                )
                            )
        elif self.get_stage_placement_type() == "object":
            for obj in level.objects:
                if obj.x * micro_width >= self.select_rect[0] and obj.x * micro_width < self.select_rect[2]:
                    if obj.y * micro_height >= self.select_rect[1] and obj.y * micro_height < self.select_rect[3]:
                        if do_copy:
                            self.copy_buffer.objects.append(
                                copy.copy(obj)
                            )
                        if do_clear:
                            actions.append(GuiAction(
                                type="object", refresh=["objects"],
                                remove=True,
                                object=obj
                            ))
        elif self.get_stage_placement_type() == "med-tile":
            for u in level.unitile_patches:
                if u.x * med_width >= self.select_rect[0] and u.x * med_width < self.select_rect[2]:
                    if level_height - (u.y + 1) * med_height >= self.select_rect[1] and level_height - (u.y + 1) * med_height < self.select_rect[3]:
                        if not u.flag_normal and not self.hard:
                            continue
                        if not u.flag_hard and self.hard:
                            continue
                        if do_copy:
                            self.copy_buffer.unitile_patches.append(
                                copy.deepcopy(u)
                            )
                        if do_clear:
                            jflag = (0x80 if self.hard else 0x60)
                            actions.append(GuiAction(
                                type="unitile", refresh=["row", "patches"],
                                macro_row_idx=u.y // 2,
                                x=u.x,
                                y=u.y,
                                difficulty_flag=jflag,
                                med_tile_idx=[None, None, None],
                                prev_med_tile_idx=None # fill this in on application.
                            ))

        # TODO: macro patches
        if do_clear and len(actions) > 0:
            self.apply_action(GuiAction(
                children=actions
            ))

        if do_copy:
            self.refresh_copy_menus()
    
    def set_selection(self, rect, final=False):
        self.select_rect = rect
        self.select_rect_final = final
        if final:
            assert(self.select_rect is not None and None not in self.select_rect)
            # swap min/max to be lower and upper bounds.
            if self.select_rect[0] > self.select_rect[2]:
                self.select_rect[2], self.select_rect[0] = self.select_rect[0], self.select_rect[2]
            if self.select_rect[1] > self.select_rect[3]:
                self.select_rect[3], self.select_rect[1] = self.select_rect[1], self.select_rect[3]
            # snap rectangle depending on selection type.
            if self.get_stage_placement_type() in ["macro-tile", "macro-patch"]:
                # macro tile selection
                self.select_rect[0] = 0
                self.select_rect[2] = level_width
                self.select_rect[1] = floor_to(self.select_rect[1], macro_height)
                self.select_rect[3] = floor_to(self.select_rect[3] + macro_height, macro_height)
            elif self.get_stage_placement_type() == "object":
                self.select_rect[0] = floor_to(self.select_rect[0] + 0x4, 0x8) - 0x4
                self.select_rect[2] = floor_to(self.select_rect[2] + 0xC, 0x8) - 0x4
                self.select_rect[1] = floor_to(self.select_rect[1] + 0x4, 0x8) - 0x4
                self.select_rect[3] = floor_to(self.select_rect[3] + 0xC, 0x8) - 0x4
            elif self.get_stage_placement_type() == "med-tile":
                self.select_rect[0] = floor_to(self.select_rect[0], med_width)
                self.select_rect[2] = floor_to(self.select_rect[2] + med_width, med_width)
                self.select_rect[1] = floor_to(self.select_rect[1] , med_height)
                self.select_rect[3] = floor_to(self.select_rect[3] + med_height, med_height)
            # bounds clamp
            for i in range(4):
                self.select_rect[i] = clamp_hoi(self.select_rect[i], 0, level_width + 1 if i % 2 == 0 else level_height + 1)

        self.refresh_selection_rect()
        self.refresh_copy_menus()
    
    def get_tiles_at(self, x, y):
        y = clamp_hoi(y, 0, level_height)
        x = clamp_hoi(x, 0, level_width)
                    
        level = self.level
        # med-tile
        macro_y = clamp_hoi(level_height - y, 0, level_height) // macro_height
        med_y = clamp_hoi(level_height - y, 0, level_height) // med_height
        med_tile_rows, macro_tile_idxs = level.produce_med_tiles(self.hard, range(macro_y, macro_y + 1))
        med_x = clamp_hoi(x, 0, level_width) // med_width
        med_tile_row = med_tile_rows[med_y % 2]
        med_tile_idx = med_tile_row[med_x]
        
        # micro-tile
        micro_x = clamp_hoi(x, 0, level_width) // micro_width
        micro_y = clamp_hoi(level_height - y, 0, level_height) // micro_height
        med_tile = level.world.get_med_tile(med_tile_idx)
        idx = 2 * (micro_y % 2) + (micro_x % 2)
        micro_tile_idx = med_tile[idx]
        
        # macro-tile
        macro_row = level.macro_rows[macro_y] if macro_y in range(len(level.macro_rows)) else None
        if macro_row is not None:
            seam_x = macro_row.seam * med_width
            macro_col_x = (max(int(x - seam_x + level_width), 0) % level_width) // macro_width
            if macro_col_x >= 4:
                macro_col_x = 7 - macro_col_x
            macro_idx = clamp_hoi(macro_col_x, 0, 4)
            macro_tile_idx = macro_tile_idxs[macro_idx]
        else:
            # not sure what causes this sometimes.
            macro_tile_idx = None
        
        return macro_tile_idx, med_tile_idx, micro_tile_idx
    
    def on_stage_motion(self, event):
        # determine what's in the element id label
        if self.level is not None:
            y = self.get_event_y(event, self.stage_canvas, level_height * self.zoom()) / self.zoom()
            x = event.x / self.zoom()
            y = clamp_hoi(y, 0, level_height)
            x = clamp_hoi(x, 0, level_width)
            
            macro_tile_idx, med_tile_idx, micro_tile_idx = self.get_tiles_at(x, y)
            
            # set label
            self.element_id_label.configure(
                text="X:" + HB(x) + ", Y:" + HX(y // 256) + HB(y % 256) +
                ", Macro:" + (".." if macro_tile_idx is None else HB(macro_tile_idx)) + ", Med:" + HB(med_tile_idx) +
                ", Micro:" + HB(micro_tile_idx)
            )
        
    def on_stage_leave(self, event):
        self.element_id_label.configure(text="")
        
    def on_stage_drag(self, event):
        y = self.get_event_y(event, self.stage_canvas, level_height * self.zoom()) / self.zoom()
        x = event.x / self.zoom()
        
        # select drag
        if self.select_rect is not None:
            self.set_selection(
            [
                self.select_rect[0],
                self.select_rect[1],
                x,
                y
            ])
    
    def on_stage_release(self, event):
        if not self.select_rect_final and self.select_rect is not None and None not in self.select_rect:
            self.set_selection(self.select_rect, True)
        else:
            self.set_selection(None)
        
    def on_stage_click(self, button, event):
        if not self.level:
            return
        
        level = self.level
        
        ctrl = event.state & 4 != 0
        shift = event.state & 1 != 0
        action_idx = button - 1
        if ctrl:
            action_idx = 3
        if shift:
            action_idx = 4
            if button == 3:
                # shift+right-click
                action_idx = 5
        action = self.mouse_button_actions[action_idx]
        
        y = self.get_event_y(event, self.stage_canvas, level_height * self.zoom()) / self.zoom()
        x = event.x / self.zoom()
        
        if action == "select":
            self.set_selection([x, y, x, y])
        else:
            self.set_selection(None)
            # (not holding shift)
            
            # object placement
            place_duplicates = False
            if self.get_stage_placement_type() == "object":
                place_duplicates = ctrl
                if ctrl: # FIXME this is kinda gross, as actions should be set by mouse+shift only...
                    action = "place"
                objx = clamp_hoi(x / micro_width, 0, level_width // micro_width)
                objy = clamp_hoi(y / micro_height, 0, level_height // micro_height)
                # remove an existing object at the given location if applicable
                if (action == "place" and not place_duplicates) or (action == "remove" and self.show_objects):
                    for obj in level.objects:
                        object_data = constants.object_data[obj.gid]
                        if obj.x == objx and obj.y == objy:
                            self.apply_action(GuiAction(
                                type="object", refresh=["objects"],
                                remove=True,
                                object=obj
                            ))
                            break
                
                if action == "eyedropper":
                    for obj in level.objects:
                        object_data = constants.object_data[obj.gid]
                        if obj.x == objx and obj.y == objy:
                            self.object_select_gid = obj.gid
                            self.refresh_object_select()
                            break
                    
                if action == "place":
                    obj = mmdata.Object(self.data)
                    obj.x = objx
                    obj.y = objy
                    obj.flipx = self.flipx()
                    obj.flipy = self.flipy()
                    obj.drop = self.drop()
                    obj.gid = self.object_select_gid
                    
                    self.apply_action(GuiAction(
                        type="object", refresh=["objects"],
                        remove=False,
                        object=obj
                    ))
                
                self.refresh_objects()
            
            # med-tile placement
            if self.get_stage_placement_type() == "med-tile":
                med_y = clamp_hoi(constants.macro_rows_per_level * 2 - int(y / med_height) - 1, 0, constants.macro_rows_per_level * 2)
                med_x = clamp_hoi(x // med_width, 0, 0x10)
                macro_row_idx = med_y // 2
                
                # place hell-hard or normal
                jflag = (0x80 if self.hard else 0x60)
                
                if action == "remove":
                    self.apply_action(GuiAction(
                        type="unitile", refresh=["row", "patches"],
                        macro_row_idx=macro_row_idx,
                        x=med_x,
                        y=med_y,
                        difficulty_flag=jflag,
                        med_tile_idx=[None, None, None],
                        prev_med_tile_idx=None # fill this in on application.
                    ))
                
                if action == "place":
                    self.apply_action(GuiAction(
                        type="unitile", refresh=["row", "patches"],
                        macro_row_idx=macro_row_idx,
                        x=med_x,
                        y=med_y,
                        difficulty_flag=jflag,
                        med_tile_idx=[self.unitile_select_id] * 3,
                        prev_med_tile_idx=None # fill this in on application.
                    ))
                
                if action == "eyedropper":
                    macro_tile_idx, med_tile_idx, micro_tile_idx = self.get_tiles_at(x, y)
                    self.unitile_select_id = med_tile_idx
                
            # tile adjustment
            if self.get_stage_placement_type() in ["macro-tile", "macro-patch"] or (action == "seam" and not place_duplicates):
                macro_row_idx = clamp_hoi(constants.macro_rows_per_level - int(y / macro_height) - 1, 0, constants.macro_rows_per_level)
                macro_row = level.macro_rows[macro_row_idx]
                seam_x = macro_row.seam * med_width
                macro_col_x = (max(int(x - seam_x + level_width), 0) % level_width) // macro_width
                if macro_col_x >= 4:
                    macro_col_x = 7 - macro_col_x
                macro_idx = clamp_hoi(macro_col_x, 0, 4)
                
                if action == "eyedropper":
                    macro_tile_idx, med_tile_idx, micro_tile_idx = self.get_tiles_at(x, y)
                    if macro_tile_idx is not None:
                        self.macro_tile_select_id = macro_tile_idx
                        
                else:
                    if self.hard:
                        # place macro tile hard-mode patch
                        
                        # remove existing patch if applicable
                        if action == "place" or action == "remove":
                            for patch in level.hardmode_patches:
                                if patch.x == macro_idx and patch.y == macro_row_idx:
                                    self.apply_action(GuiAction(
                                        type="patch", refresh=["row", "patches"],
                                        remove=True,
                                        macro_row_idx=macro_row_idx,
                                        patch=patch
                                    ))
                                    break
                        
                        # add a patch
                        if action == "place" and self.macro_tile_select_id != 0:
                            patch = mmdata.HardPatch()
                            patch.i = self.macro_tile_select_id - 0x2f
                            patch.x = macro_idx
                            patch.y = macro_row_idx
                            self.apply_action(GuiAction(
                                type="patch", refresh=["row", "patches"],
                                remove=False,
                                macro_row_idx=macro_row_idx,
                                patch=patch
                            ))
                        
                        self.refresh_patch_rects()
                    else:
                        # set macro tile
                        if action == "place":
                            self.apply_action(GuiAction(
                                type="tile", refresh=["row"],
                                macro_row_idx=macro_row_idx,
                                macro_idx=macro_idx,
                                tile=self.macro_tile_select_id,
                                prev_tile=macro_row.macro_tiles[macro_idx]
                            ))
                        elif action == "remove":
                            self.apply_action(GuiAction(
                                type="tile", refresh=["row"],
                                macro_row_idx=macro_row_idx,
                                macro_idx=macro_idx,
                                tile=0,
                                prev_tile=macro_row.macro_tiles[macro_idx]
                            ))
                        elif action == "seam":
                            self.apply_action(GuiAction(
                                type="seam", refresh=["row", "patches"],
                                macro_row_idx=macro_row_idx,
                                prev_seam=macro_row.seam,
                                seam=int(max(0, (x + micro_width - 2) / med_width)) % (level_width // med_width)
                            ))
    
    def subwindowctl(self, type, **kwargs):
        # check if subwindow has closed
        if type in self.subwindows:
            if self.subwindows[type].closed:
                self.subwindows.pop(type)
        
        # open new subwindow
        if type not in self.subwindows:
            if "open" in kwargs and not kwargs["open"]:
                # ...unless "open" is false
                return
            self.subwindows[type] = type(self)
        
        if "open" in kwargs:
            kwargs.pop("open")
        
        # ctl it
        self.subwindows[type].ctl(kwargs)
        pass
    
    def on_macro_click(self, idx, edit):
        if idx < len(self.placable_tiles):
            self.macro_tile_select_id = self.placable_tiles[idx]
            self.object_select_gid = None
            self.unitile_select_id = None
            self.set_selection(None)
            if edit:
                self.subwindowctl(GuiMacroEdit, world_idx=self.level.world_idx, macro_tile_idx=self.macro_tile_select_id)
            self.refresh_selection_rect()
            self.refresh_label()
        
    def on_object_click(self, edit, event):
        if len(self.placable_objects) == 0:
            return
        y = self.get_event_y(event, self.object_canvas, len(self.placable_objects) * (objheight * self.zoom())) / self.zoom()
        idx = clamp_hoi(y / (objheight), 0, len(self.placable_objects))
        self.macro_tile_select_id = None
        self.unitile_select_id = None
        self.object_select_gid = self.placable_objects[idx]
        self.set_selection(None)
        self.refresh_selection_rect()
        self.refresh_label()
    
    def add_hotkey(self, command, accelerator):
        self.menu_commands[accelerator] = command

    def add_menu_command(self, menu, label, command, accelerator):
        self.add_hotkey(command, accelerator)
        menu.add_command(label=label, command=command, accelerator=accelerator)
        return menu.index(label)
    
    # sets up windows and widgets
    # self.data need not be set yet.
    def init(self):
        self.window = tk.Tk()
        if os.path.exists(icon_path):
            self.window.iconphoto(True, tk.PhotoImage(file=icon_path))
        self.window.protocol("WM_DELETE_WINDOW", self.soft_quit)
        
        self.window.bind("<Key>", self.on_keypress)
        self.blank_image = ImageTk.PhotoImage(image=Image.new('RGBA', (8, 8), color=(0, 0, 0, 0)))
        
        # menus
        menu = tk.Menu(self.window)
        
        filemenu = tk.Menu(menu, tearoff=0)
        self.filemenu = filemenu
        self.menu_base_rom = self.add_menu_command(filemenu, "Load Base ROM...", partial(self.fio_prompt, "rom", False), "Ctrl+Shift+R")
        self.menu_fio = [self.add_menu_command(filemenu, "Open Hack...", partial(self.fio_prompt, "hack", False), "Ctrl+O")]
        self.menu_fio += [
            self.add_menu_command(filemenu, "Import CHR...", partial(self.fio_prompt, "chr", False), "Ctrl+R")
        ]
        filemenu.add_separator()
        self.menu_fio += [
            self.add_menu_command(filemenu, "Save Hack", partial(self.fio_prompt, "hack", True, True), "Ctrl+S"),
            self.add_menu_command(filemenu, "Save Hack As...", partial(self.fio_prompt, "hack", True), "Ctrl+Shift+S")
        ]
        filemenu.add_separator()
        self.menu_fio += [
            self.add_menu_command(filemenu, "Play", partial(self.play_hack, False), "Ctrl+Shift+G"),
            self.add_menu_command(filemenu, "Play this level", partial(self.play_hack, True), "Ctrl+G")
        ]
        filemenu.add_separator()
        self.menu_fio += [
            self.add_menu_command(filemenu, "Export Patched ROM...", partial(self.fio_prompt, "rom", True), "Ctrl+E"),
            self.add_menu_command(filemenu, "Export IPS Patch...", partial(self.fio_prompt, "ips", True), "Ctrl+P"),
            self.add_menu_command(filemenu, "Export BPS Patch...", partial(self.fio_prompt, "bps", True), "Ctrl+B"),
            self.add_menu_command(filemenu, "Export Image Sheet...", partial(self.fio_prompt, "image", True), "Ctrl+J")
        ]
        
        # start disabled
        for m in self.menu_fio:
            filemenu.entryconfig(m, state=tk.DISABLED)
        
        filemenu.add_separator()
        self.add_menu_command(filemenu, "Quit", partial(self.soft_quit), "Ctrl+Q")
        menu.add_cascade(label="File", menu=filemenu)
        
        editmenu = tk.Menu(menu, tearoff=0)
        self.editmenu = editmenu
        self.menu_edit_undo = self.add_menu_command(editmenu, "Undo", lambda: self.apply_action(self.undo_buffer[-1], True) if len(self.undo_buffer) > 0 else 0, "Ctrl+Z")
        self.menu_edit_redo = self.add_menu_command(editmenu, "Redo", lambda: self.apply_action(self.redo_buffer[-1]) if len(self.redo_buffer) > 0 else 0, "Ctrl+Y")
        editmenu.add_separator()
        self.add_menu_command(editmenu, "Select All", partial(self.set_selection, [0, 0, level_width, level_height], True), "Ctrl+A")
        self.add_menu_command(editmenu, "Select None", partial(self.set_selection, None), "Escape")
        self.add_hotkey(partial(self.set_selection, None), "Ctrl+Shift+A")
        self.add_menu_command(editmenu, "Copy Selection", partial(self.copycut_selection, True, False), "Ctrl+C")
        self.add_menu_command(editmenu, "Cut Selection", partial(self.copycut_selection, True, True), "Ctrl+X")
        self.add_menu_command(editmenu, "Paste Selection", partial(self.paste_selection), "Ctrl+V")
        self.add_menu_command(editmenu, "Clear Selection", partial(self.copycut_selection, False, True), "Delete")
        self.add_menu_command(editmenu, "Clear Stage", partial(self.clear_stage), None)
        editmenu.add_separator()
        self.add_menu_command(editmenu, "Macro Tiles...", lambda: self.subwindowctl(GuiMacroEdit, world_idx=self.level.world_idx), "Ctrl+M")
        self.add_menu_command(editmenu, "Med Tiles...", lambda: self.subwindowctl(GuiMedEdit, world_idx=self.level.world_idx), "Ctrl+Shift+M")
        self.add_menu_command(editmenu, "Mods...", lambda: self.subwindowctl(GuiMod), "Ctrl+Shift+D")
        #self.add_menu_command(editmenu, "Screen...", lambda: self.subwindowctl(GuiScreenEditor), "Ctrl+Shift+T")
        menu.add_cascade(label="Edit", menu=editmenu)
        
        viewmenu = tk.Menu(menu, tearoff=0)
        self.viewmenu = viewmenu
        stagemenu = tk.Menu(viewmenu, tearoff=0)
        
        for level_idx in range(constants.level_count):
            if level_idx in [3, 6, 9]:
                stagemenu.add_separator()
            
            sublevel = (level_idx % 3) + 1 if level_idx < 12 else 4
            world_idx = (level_idx // 3) + 1 if level_idx < 12 else 4
            name = "Tower " + str(world_idx) + "-" + str(sublevel)
            accelerator = ("Shift+F" + str(24 - level_idx)) if level_idx >= 12 else "F" + str(level_idx + 1)
            self.add_menu_command(stagemenu, name, partial(self.select_stage, level_idx), accelerator)
            
        viewmenu.add_cascade(label="Stage", menu=stagemenu)
        self.menu_view_hard = self.add_menu_command(viewmenu, "Hard Mode", lambda: self.select_stage(self.stage_idx, not self.hard), "H")
        viewmenu.add_separator()
        
        self.add_menu_command(viewmenu, "Objects", lambda: self.ctl(show_objects=not self.show_objects), "O")
        self.menu_view_crosshairs = self.add_menu_command(viewmenu, "Object Crosshairs", lambda: self.ctl(show_crosshairs=not self.show_crosshairs), "C")
        self.add_menu_command(viewmenu, "Grid", lambda: self.ctl(show_lines=not self.show_lines), "G")
        self.menu_view_patches = self.add_menu_command(viewmenu, "Patches", lambda: self.ctl(show_patches=not self.show_patches), "P")
        self.add_menu_command(viewmenu, "Mirror Shading", lambda: self.ctl(show_mirror=not self.show_mirror), "F")
        
        viewmenu.add_separator()
        self.add_menu_command(viewmenu, "Zoom 1x", lambda: self.set_zoom(0), "Ctrl+1")
        self.add_menu_command(viewmenu, "Zoom 2x", lambda: self.set_zoom(1), "Ctrl+2")
        self.add_menu_command(viewmenu, "Zoom 3x", lambda: self.set_zoom(2), "Ctrl+3")
        self.add_hotkey(lambda: self.set_zoom(0, True), "Ctrl+Alt+1")
        self.add_hotkey(lambda: self.set_zoom(1, True), "Ctrl+Alt+2")
        self.add_hotkey(lambda: self.set_zoom(2, True), "Ctrl+Alt+3")
        
        menu.add_cascade(label="View", menu=viewmenu)
        
        helpmenu = tk.Menu(menu, tearoff=0)
        self.add_menu_command(helpmenu, "About", self.about, None)
        self.add_menu_command(helpmenu, "Mouse Button Mappings", self.usage, None)
        menu.add_cascade(label="Help", menu=helpmenu)
        
        # containers
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        stage_frame = tk.Frame(main_frame)
        stage_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        stage_topbar = tk.Frame(stage_frame)
        stage_topbar.pack(side=tk.BOTTOM, fill=tk.X, expand=False)
        
        selectors_frame = tk.Frame(main_frame)
        self.selectors_frame = selectors_frame
        selectors_frame.pack(side = tk.RIGHT, fill=tk.Y)
        
        selector_macro_frame = tk.Frame(selectors_frame)
        selector_macro_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        self.selectors_subframe = tk.Frame(selectors_frame)
        self.selectors_subframe.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        
        selector_objects_frame = tk.Frame(self.selectors_subframe)
        selector_objects_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        
        # canvases
        stage_canvas = tk.Canvas(stage_frame, width=screenwidth * self.zoom(), height=screenheight, scrollregion=(0, 0, level_width * self.zoom(), level_height * self.zoom()), bg="black")
        self.attach_scrollbar(stage_canvas, stage_frame)
        stage_canvas.pack(side=tk.TOP, fill=tk.Y, expand=True)
        stage_canvas.bind("<Button-1>", partial(self.on_stage_click, 1))
        stage_canvas.bind("<Button-2>", partial(self.on_stage_click, 2))
        stage_canvas.bind("<Button-3>", partial(self.on_stage_click, 3))
        stage_canvas.bind("<B1-Motion>", partial(self.on_stage_drag))
        stage_canvas.bind("<B2-Motion>", partial(self.on_stage_drag))
        stage_canvas.bind("<B3-Motion>", partial(self.on_stage_drag))
        stage_canvas.bind("<Motion>", partial(self.on_stage_motion))
        stage_canvas.bind("<Leave>", partial(self.on_stage_leave))
        stage_canvas.bind("<ButtonRelease-1>", partial(self.on_stage_release))
        stage_canvas.bind("<ButtonRelease-2>", partial(self.on_stage_release))
        stage_canvas.bind("<ButtonRelease-3>", partial(self.on_stage_release))
        
        macro_canvas = GuiMicroGrid(selector_macro_frame, self, w=macro_width // micro_width * self.macro_tile_select_width, height=screenheight, chunkdim=(macro_width // micro_width, macro_height // micro_height), cb=self.on_macro_click)
        macro_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        object_canvas = tk.Canvas(selector_objects_frame, width=objwidth, height=screenheight, bg="black")
        self.attach_scrollbar(object_canvas, selector_objects_frame)
        object_canvas.pack(fill=tk.Y, expand=True)
        object_canvas.bind("<Button-1>", partial(self.on_object_click, False))
        object_canvas.bind("<Button-3>", partial(self.on_object_click, True))
        object_canvas.bind("<Double-Button-1>", partial(self.on_object_click, True))
        
        # private access
        self.stage_canvas = stage_canvas
        self.macro_canvas = macro_canvas
        self.object_canvas = object_canvas
        
        # canvas images (reused):
        self.stage_micro_dangerous = [[False for y in range(level_height // micro_height)] for x in range(level_width // micro_width)]
        self.stage_micro_images = [[None for y in range(level_height // micro_height)] for x in range(level_width // micro_width)]
        self.stage_mirror_cover_images = [[None for x in range(level_width // med_width)] for y in range(level_height // macro_height)]
        self.object_select_images = [None for y in range(0x100)]
        
        # object canvas checkboxes
        objects_flags_frame = tk.Frame(selector_objects_frame)
        objects_flags_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_flipx = tk.BooleanVar()
        tk.Checkbutton(objects_flags_frame, text="flip X", underline=5, variable=self.v_flipx, command=self.refresh_object_select).grid(row=0, sticky="W")
        self.v_flipy = tk.BooleanVar()
        tk.Checkbutton(objects_flags_frame, text="flip Y", underline=5, variable=self.v_flipy, command=self.refresh_object_select).grid(row=1, sticky="W")
        self.v_drop = tk.BooleanVar()
        self.objects_select_check_drop = tk.Checkbutton(objects_flags_frame, text="drop (K)", underline=6, variable=self.v_drop, command=self.refresh_object_select)
        self.objects_select_check_drop.grid_forget()

        # hotkeys for the above.
        self.add_hotkey(lambda: self.ctl(flipx=not self.flipx()), "X")
        self.add_hotkey(lambda: self.ctl(flipy=not self.flipy()), "Y")
        self.add_hotkey(lambda: self.ctl(drop=not self.drop()), "K")

        # stage topbar
        musiclabel = tk.Label(stage_topbar, text="Music: ")
        musiclabel.grid(column=0, row=0)
        
        subframe = tk.Frame(stage_topbar, width=100)
        subframe.grid(column=2, row=0)
        self.element_id_label = tk.Label(subframe, text="", width=len("X:00, Y:000, Macro:XX, Med:XX, Micro:XX"), anchor=tk.W)
        self.element_id_label.pack()
        
        self.stage_topbar = stage_topbar
        self.musicdropdown = None
        self.stage_topbar.pack_forget()
        
        # bottom bar
        bottom_frame = tk.Frame(self.window)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        bottom_alt_bar = tk.Frame(bottom_frame)
        bottom_alt_bar.pack(side=tk.TOP, fill=tk.X)

        # usage
        self.level_usage_bar = GuiUsageBar(bottom_frame, self, text="Level Data", height=20)
        self.level_usage_bar.pack(fill=tk.X)

        self.alt_usage_bar = GuiUsageBar(bottom_alt_bar, self, text="Ext. Data", height=20)
        self.alt_usage_bar.pack(fill=tk.X)
        self.alt_usage_bar.pack_forget()

        # bottom label
        self.label = tk.Label(bottom_frame, width=40)
        self.label.pack(fill=tk.X)
        
        self.window.config(menu=menu)
        
        # we do this to refreshes menus, label, title.
        # (the undo buffer will definitely be clear at this point already regardless.)
        self.clear_undo_buffers()

        self.refresh_copy_menus()
    
    def flipx(self):
        return self.v_flipx.get()

    def flipy(self):
        return self.v_flipy.get()
    
    def drop(self):
        return self.v_drop.get()

    # this is quite expensive... progress bar? coroutine?
    def refresh_chr(self):
        if self.data is None:
            return
        
        # image for covering mirrored side
        self.mirror_cover_image = Image.new('RGBA', (med_width * self.zoom(), macro_height * self.zoom()), color=(0xa0, 0xa0, 0xa0, 0xc0))
        self.mirror_cover_image = ImageTk.PhotoImage(image=self.mirror_cover_image)
        
        # object images
        # list [flip][gid]
        self.object_images = [None] * 8
        for j in range(8):
            flipx = j % 2 == 1
            flipy = (j % 4) >= 2
            semi = j >= 4
            self.object_images[j] = mmimage.produce_object_images(self.data, semi)
            
            # flip x and/or y
            for i in range(len(self.object_images[j])):
                img = self.object_images[j][i]
                if img is not None:
                    if flipx:
                        img = ImageOps.mirror(img)
                    if flipy:
                        img = ImageOps.flip(img)
                    if self.zoom() != 1:
                        img = ImageOps.fit(img, (img.width * self.zoom(), img.height * self.zoom()), method=Image.NEAREST)
                    self.object_images[j][i] = ImageTk.PhotoImage(image=img)
        
        # micro-tile images
        # list [world][palette_idx][id]
        self.micro_images = [[[None for id in range(0x100)] for palette_idx in range(8)] for world in self.data.worlds]
        self.screen_micro_images = [[None for id in range(0x100)] for palette_idx in range(4)]
        for world_idx in range(len(self.data.worlds)):
            world = self.data.worlds[world_idx]
            images = [mmimage.produce_micro_tile_images(self.data, world, hard) for hard in [False, True]]
            for palette_idx in range(8):
                for id in range(0x100):
                    img = images[palette_idx // 4][palette_idx % 4][id]
                    imgzoom = ImageOps.fit(img, (img.width * self.zoom(), img.height * self.zoom()), method=Image.NEAREST)
                    self.micro_images[world_idx][palette_idx][id] = ImageTk.PhotoImage(image=imgzoom)
    
        # screen tiles (e.g. for title screen)
        palettes = self.data.title_screen.palettes[0]
        palettes[0] = constants.title_red_palette # remap to faded-in red colour
        images = mmimage.produce_micro_tile_images(self.data, palettes)
        for palette_idx in range(4):
            for id in range(0x100):
                img = images[palette_idx][id]
                imgzoom = ImageOps.fit(img, (img.width * self.zoom(), img.height * self.zoom()), method=Image.NEAREST)
                self.screen_micro_images[palette_idx][id] = ImageTk.PhotoImage(image=imgzoom)
                    
    
    def select_stage(self, stage_idx, hard=False):
        if self.data is None:
            return
            
        self.object_select_gid = None
        self.unitile_select_id = None
        self.macro_tile_select_id = 0x30 if hard else 0xd # a good default selection.
        self.stage_idx = stage_idx
        self.hard = hard
        self.level = self.data.levels[stage_idx]
        
        self.placable_objects = []
        
        self.viewmenu.entryconfig(self.menu_view_patches, state=tk.NORMAL if (hard or self.data.mapper_extension) else tk.DISABLED)
        
        # decide on placable tiles
        if hard:
            self.placable_tiles = [0] + list(range(0x30, 0x3f))
        else:
            self.placable_tiles = list(range(0x100))
        
        # filter out tiles not in world
        for tile_idx in self.placable_tiles + []:
            if tile_idx >= len(self.level.world.macro_tiles) + constants.global_macro_tiles_count:
                self.placable_tiles.remove(tile_idx)
        
        # decide on placable objects
        for gid in self.data.spawnable_objects + (list(range(0x40)) if self.data.has_mod("extended_objects") else []):
            objdata = constants.object_data[gid]
            hard_only = objdata["hard"] if "hard" in objdata else False
            # skip objects without images, and only have grinders on hard mode.
            if (hard_only == self.hard or not self.hard) and self.object_images[0][gid] is not None:
                if gid not in self.placable_objects:
                    self.placable_objects.append(gid)
        
        # refresh the selectors
        self.refresh_object_select()
        self.refresh_tile_select()
        self.refresh_selection_rect()
        
        # refresh the stage view
        for i in range(constants.macro_rows_per_level):
            self.refresh_row_tiles(i)
            self.refresh_row_lines(i)
        self.refresh_horizontal_lines()
        self.refresh_objects()
        self.refresh_patch_rects()
        
        # refresh related data
        self.refresh_title()
        self.refresh_label()
        
        # refresh mapper extension components (only relevant if the mapper-extension mod is enabled)
        self.refresh_mapper_components()
        
        # sets the music dropdown value
        self.refresh_music_dropdown()

        # deselect all
        self.set_selection(None)
    
    def refresh_music_dropdown(self):
        # set options
        if self.musicdropdown is not None:
            self.musicdropdown.destroy()
            
        if self.level is not None:
            options = []
            for i in range(len(self.data.music.songs)):
                options.append(HB(i) + " - " + self.data.music.songs[i])        
        
            self.stage_topbar.pack(side=tk.BOTTOM, fill=tk.X, expand=False)
            
            self.musicdropdown_var = tk.StringVar(self.window)
            self.musicdropdown = tk.OptionMenu(self.stage_topbar, self.musicdropdown_var, *options)
            self.musicdropdown.grid(column=1, row=0)
            self.musicdropdown_var.set(options[self.level.music_idx])
            self.musicdropdown_var.trace("w", callback=self.on_music_idx_change)
            
            if self.hard:
                self.musicdropdown.config(state=tk.DISABLED)
            else:
                self.musicdropdown.config(state=tk.NORMAL)
    
    def on_music_idx_change(self, avr, unk, mode):
        s = self.musicdropdown_var.get()
        if s.startswith("-") or " " not in s:
            return
        else:
            n = int(s.split(" ")[0], 16)
            self.level.music_idx = n
        
    def refresh_on_macro_tile_update(self, macro_tile_idx):
        for i in range(constants.macro_rows_per_level):
            self.refresh_row_tiles(i, macro_tile_idx=macro_tile_idx)
        self.refresh_tile_select()
    
    def refresh_on_med_tile_update(self, macro_tile_idx):
        for i in range(constants.macro_rows_per_level):
            self.refresh_row_tiles(i, med_tile_idx=macro_tile_idx)
        self.refresh_tile_select()
    
    def delete_elements(self, canvas, elements):
        for element in elements:
            if element is not None:
                canvas.delete(element)
    
    def refresh_tile_select(self):
        self.macro_canvas.configure(dims=(
            self.macro_tile_select_width * macro_width // micro_width,
            ceil_to((len(self.placable_tiles) * macro_height // micro_height) / self.macro_tile_select_width, macro_height // micro_height)
        ))
        self.macro_canvas.divides = [] if self.hard else [constants.global_macro_tiles_count]
        self.macro_canvas.refresh()
                
        if self.level is None:
            return
            
        world = self.level.world
        
        clear_coords = [(x, y) for x in range(self.macro_canvas.w) for y in range(self.macro_canvas.h)]
        
        # populate
        for macro_sel_idx in range(len(self.placable_tiles)):
            macro_idx = self.placable_tiles[macro_sel_idx]
            macro_y = (macro_sel_idx // self.macro_tile_select_width)
            macro_x = (macro_sel_idx % self.macro_tile_select_width)
            
            # set images
            macro_tile = world.get_macro_tile(macro_idx)
            for i in range(4):
                med_tile_idx = macro_tile[i]
                med_tile = world.get_med_tile(med_tile_idx)
                for j in range(4):
                    micro_tile_idx = world.get_micro_tile(med_tile[j], self.hard)
                    x = (i % 2) * 2 + (j % 2) + macro_x * 4
                    y = (i // 2) * 2 + (j // 2) + macro_y * 4
                    palette_idx = world.get_med_tile_palette_idx(med_tile_idx, self.hard)
                    img = self.micro_images[world.idx][palette_idx][micro_tile_idx]
                    self.macro_canvas.set_tile_image(x, y, img)
                    if (x, y) in clear_coords:
                        clear_coords.remove((x, y))
        self.macro_canvas.clear_from(len(self.placable_tiles))
        
        for clear_coord in clear_coords:
            self.macro_canvas.set_tile_image(clear_coord[0], clear_coord[1], self.blank_image)
                    
    def refresh_object_select(self):
        self.delete_elements(self.object_canvas, self.elts_object_select)
        self.elts_object_select = []
        
        # clear images
        for y in range(0x100):
            if self.object_select_images[y] is None:
                self.object_select_images[y] = self.object_canvas.create_image(objwidth / 2 * self.zoom(), objheight / 2 * self.zoom() + objheight * y * self.zoom(), image=self.blank_image, anchor=tk.CENTER)
            else:
                self.object_canvas.itemconfig(self.object_select_images[y], image=self.blank_image)

        # set scrollable region
        self.object_canvas.configure(scrollregion=(0, 0, objwidth * self.zoom(), len(self.placable_objects) * objheight * self.zoom() - self.zoom()))

        flip_idx = (2 if self.flipy() else 0) + (1 if self.flipx() else 0) + (4 if self.drop() else 0)

        for i in range(len(self.placable_objects)):
            gid = self.placable_objects[i]
            line_y = (i * objheight + objheight) * self.zoom()
            
            divide = i == 0xf
            
            # place line
            self.elts_object_select.append(
                self.object_canvas.create_line(0, line_y, objwidth * self.zoom(), line_y,
                fill=divcol if divide else linecol, width=2 if divide else 1)
            )
            
            # set object
            img = self.object_images[flip_idx][gid]
            if img is None:
                img = self.blank_image
            self.object_canvas.itemconfig(self.object_select_images[i], image=img)
        
        # object drop
        if self.data.mapper_extension:
            self.objects_select_check_drop.grid(row=2, sticky="W")
        else:
            self.objects_select_check_drop.grid_forget()
        
    def refresh_selection_rect(self):
        # clear previous
        if self.elt_object_select_rect is not None:
            self.object_canvas.delete(self.elt_object_select_rect)
        self.elt_object_select_rect = None
        
        for elt in self.elts_stage_select:
            self.stage_canvas.delete(elt)
        self.elts_stage_select = []
        
        # macro canvas handles its own selection rect
        if self.macro_tile_select_id is not None:
            self.macro_canvas.selection_idx = self.placable_tiles.index(self.macro_tile_select_id)
        else:
            self.macro_canvas.selection_idx = None
        self.macro_canvas.refresh()
        
        # med canvas handles its own selection rect
        if self.data and self.data.mapper_extension and self.mapper_extension_components_init:
            if self.unitile_select_id is not None:
                self.unitile_canvas.selection_idx = self.placable_med_tiles.index(self.unitile_select_id)
            else:
                self.unitile_canvas.selection_idx = None
            self.unitile_canvas.refresh()
        
        # rectangle properties
        rect_colstr = selcol
        rect_margin = 2 * self.zoom()
        rect_width = 2
        
        # place the selection rect (if object selected)
        if self.object_select_gid is not None:
            i = self.placable_objects.index(self.object_select_gid)
            y = i * objheight * self.zoom()
            self.elt_object_select_rect = self.object_canvas.create_rectangle(
                rect_margin, y + rect_margin, objwidth * self.zoom() - rect_margin, y + objheight * self.zoom() - rect_margin,
                width=rect_width,
                outline=rect_colstr
             )
        
        # place the selection rect on the stage canvas
        if self.select_rect is not None and None not in self.select_rect:
            col = "white"
            if self.select_rect_final:
                if self.get_stage_placement_type() == "object":
                    col = "#77aaFF"
                if self.get_stage_placement_type() == "macro-tile":
                    col = "#FF77CC"
                if self.get_stage_placement_type() == "macro-patch":
                    col = patchcol
                if self.get_stage_placement_type() == "med-tile":
                    col = unipatchcol
            self.elts_stage_select += [
                self.stage_canvas.create_rectangle(
                    self.select_rect[0] * self.zoom(),
                    self.select_rect[1] * self.zoom(),
                    self.select_rect[2] * self.zoom(),
                    self.select_rect[3] * self.zoom(),
                    width=4,
                    outline="black"
                ),
                self.stage_canvas.create_rectangle(
                    self.select_rect[0] * self.zoom(),
                    self.select_rect[1] * self.zoom(),
                    self.select_rect[2] * self.zoom(),
                    self.select_rect[3] * self.zoom(),
                    width=2,
                    outline=col
                ),
                # duplicated for shadow
                # FIXME: make this nicer
                self.stage_canvas.create_text(
                    (max(2, min(self.select_rect[0], self.select_rect[2]) * self.zoom()) + 1, max(12, min(self.select_rect[1], self.select_rect[3])) * self.zoom() + 1),
                    text=self.get_stage_placement_type(),
                    anchor=tk.SW,
                    fill="black"
                ),
                self.stage_canvas.create_text(
                    (max(2, min(self.select_rect[0], self.select_rect[2]) * self.zoom()), max(12, min(self.select_rect[1], self.select_rect[3])) * self.zoom()),
                    text=self.get_stage_placement_type(),
                    anchor=tk.SW,
                    fill=col
                ),
            ]
        
    def refresh_horizontal_lines(self):
        self.delete_elements(self.stage_canvas, self.elts_stage_horizontal_lines)
        self.elts_stage_horizontal_lines = []
        
        # top and bottom dark shadow lines
        if self.show_lines:
            for i in [0, 1, 3, 5, 7]:
                for top in [False, True]:
                    y = i if top else level_height - i - 1
                    self.elts_stage_horizontal_lines.append(
                        self.stage_canvas.create_line(
                            0, y * self.zoom(), level_width * self.zoom(), y * self.zoom(),
                            fill="black",
                            width=self.zoom()
                        )
                    )
        
        # horizontal grid lines
        if self.show_lines:
            for i in range(constants.macro_rows_per_level - 1):
                y = (level_height - macro_height * (i + 1)) * self.zoom()
                self.elts_stage_horizontal_lines.append(
                    self.stage_canvas.create_line(
                        0, y, level_width * self.zoom(), y,
                        fill=gridcol
                    )
                )
        
    def refresh_row_lines(self, row_idx):
        self.delete_elements(self.stage_canvas, self.elts_row_lines[row_idx])
        self.elts_row_lines[row_idx] = []
        
        if self.level is not None:
            y = (level_height - macro_height * row_idx - macro_height) * self.zoom()
            macro_row = self.level.macro_rows[row_idx]
            seam = macro_row.seam
            seam_x = (med_width * seam) * self.zoom()
            
            # place mirror over-images
            mirror_cover_row = self.stage_mirror_cover_images[row_idx]
            for i in range(len(mirror_cover_row)):
                if mirror_cover_row[i] is None:
                    mirror_cover_row[i] = self.stage_canvas.create_image(
                        i * self.zoom() * med_width,
                        y,
                        image=self.blank_image,
                        anchor=tk.NW
                    )
                if (i - seam + (level_width // med_width)) % (level_width // med_width) >= (level_width // med_width // 2) and self.show_mirror:
                    self.stage_canvas.itemconfig(mirror_cover_row[i], image=self.mirror_cover_image)
                else:
                    self.stage_canvas.itemconfig(mirror_cover_row[i], image=self.blank_image)
            
            if not self.show_lines:
                return
            
            # place thin vertical lines
            for i in range(level_width // macro_width):
                x = (2 * i + (seam % 2)) * med_width * self.zoom()
                if x < level_width * self.zoom() and x != seam_x:
                    self.elts_row_lines[row_idx].append(
                        self.stage_canvas.create_line(
                            x, y, x, y + macro_height * self.zoom(), fill=gridcol
                        )
                    )
            
            # place seam
            if seam != 0:
                self.elts_row_lines[row_idx].append(
                    self.stage_canvas.create_line(seam_x, y, seam_x, y + macro_height * self.zoom(), fill=seamcol, width=self.zoom())
                )
        
    def refresh_row_tiles(self, row_idx, **kwargs):
        macro_tile_idx_filter = kwargs["macro_tile_idx"] if "macro_tile_idx" in kwargs else None
        med_tile_idx_filter = kwargs["med_tile_idx"] if "med_tile_idx" in kwargs else None
        level = self.level
        if level is not None:
            micro_y = (constants.macro_rows_per_level - row_idx - 1) * (macro_height // micro_height)
            med_tile_rows, macro_tile_idxs = level.produce_med_tiles(self.hard, range(row_idx, row_idx + 1))
            if macro_tile_idx_filter is not None and macro_tile_idx_filter not in macro_tile_idxs:
                # skip row if row does not contain the filter macro tile
                return
            for med_tile_row_idx in range(2):
                med_tile_row = med_tile_rows[med_tile_row_idx]
                for med_tile_col_idx in range(len(med_tile_row)):
                    med_tile_idx = med_tile_row[med_tile_col_idx]
                    if med_tile_idx_filter is not None and med_tile_idx != med_tile_idx_filter:
                        # skip med tile if it is not the filter med tile
                        continue
                    med_tile = level.world.get_med_tile(med_tile_idx)
                    palette_idx = level.world.get_med_tile_palette_idx(med_tile_idx, self.hard)
                    for i in range(4):
                        micro_tile_idx = level.world.get_micro_tile(med_tile[i], self.hard)
                        x = med_tile_col_idx * 2 + (i % 2)
                        y = micro_y + (1 - med_tile_row_idx) * 2 + (i // 2)
                        img = self.micro_images[level.world_idx][palette_idx][micro_tile_idx]
                        self.stage_micro_dangerous[x][y] = micro_tile_idx in constants.dangerous_micro_tiles
                        if self.stage_micro_images[x][y] is None:
                            self.stage_micro_images[x][y] = self.stage_canvas.create_image(
                                x * micro_width * self.zoom(), y * micro_height * self.zoom(), image=img, anchor=tk.NW
                            )
                        else:
                            self.stage_canvas.itemconfig(self.stage_micro_images[x][y], image=img)
        
    def refresh_objects(self):
        # clear previous
        self.delete_elements(self.stage_canvas, self.elts_objects)
        self.elts_objects = []
        
        # update menu enabled/disabled
        self.viewmenu.entryconfig(self.menu_view_crosshairs, state=tk.NORMAL if self.show_objects else tk.DISABLED)
        
        # add new objects
        if self.show_objects and self.level is not None:
            for obj in self.level.objects:
                obj_data = constants.object_data[obj.gid]
                hard_only = obj_data["hard"] if "hard" in obj_data else False
                # check if tile allows displaying hard-mode-only objects
                tile_dangerous = self.get_tile_dangerous(obj.x, obj.y)
                semi = (hard_only and not tile_dangerous) or obj.drop
                
                flip_idx = (4 if semi else 0) + (2 if obj.flipy else 0) + (1 if obj.flipx else 0)
                img = self.object_images[flip_idx][obj.gid]
                if img is None:
                    img = self.blank_image
                    offset = (0, 0)
                else:
                    offset = obj_data["offset"] if "offset" in obj_data else (0, 0)
                    offset = (offset[0] * self.zoom() - (img.width() // 2), offset[1] * self.zoom() + 8 * self.zoom() - (img.height()))

                # add image
                self.elts_objects.append(
                    self.stage_canvas.create_image(
                        obj.x * micro_width * self.zoom() + offset[0], obj.y * micro_height * self.zoom() + offset[1],
                        image=img,
                        anchor=tk.NW
                    )
                )
                
                if not self.show_crosshairs:
                    continue
                
                # add crosshairs
                x = obj.x * micro_width * self.zoom()
                y = obj.y * micro_height * self.zoom()
                # offset object slightly for drop
                # (for the benefit of crates.)
                if obj.drop:
                    x += 4 * self.zoom()
                    y += 4 * self.zoom()
                colstr = objcrosscol["drop" if obj.drop else obj.compressible()]
                r = 3 * self.zoom() # radius
                
                self.elts_objects.append(
                    self.stage_canvas.create_line(
                        x - r, y, x + r, y, fill=colstr
                    )
                )
                self.elts_objects.append(
                    self.stage_canvas.create_line(
                        x, y - r, x, y + r, fill=colstr
                    )
                )
        
    def refresh_patch_rects(self):
        self.delete_elements(self.stage_canvas, self.elts_patch_rects)
        self.elts_patch_rects = []
        
        if self.show_patches and self.level is not None:
            if self.hard:
                for patch in self.level.hardmode_patches:
                    macro_row = self.level.macro_rows[patch.y]
                    seam = macro_row.seam
                    for mirror in [False, True]:
                        for loop in [-1, 0, 1]:
                            y = (constants.macro_rows_per_level -  patch.y - 1) * macro_height
                            x = (((7 - patch.x) if mirror else patch.x) * 2 + seam) * med_width
                            x += level_width * loop
                            x *= self.zoom()
                            y *= self.zoom()
                            margin = 4 * self.zoom()
                            self.elts_patch_rects.append(
                                self.stage_canvas.create_rectangle(
                                    x + margin, y + margin, x + macro_width * self.zoom() - margin - 1, y + macro_height * self.zoom() - margin - 1,
                                    outline=patchcol
                                )
                            )
                            
            # unitile patches
            if self.data.mapper_extension:
                margin = 2 * self.zoom()
                for u in self.level.unitile_patches:
                    if (self.hard and u.flag_hard) or (not self.hard and u.flag_normal):
                        x = u.x * med_width * self.zoom()
                        y = (level_height - (u.y + 1) * med_height) * self.zoom()
                        self.elts_patch_rects.append(
                            self.stage_canvas.create_rectangle(
                                x + margin, y + margin, x + med_width * self.zoom() - margin - 1, y + med_height * self.zoom() - margin - 1,
                                outline=unipatchcol
                            )
                        )
    
    def refresh_mapper_components(self):
        world = self.data.worlds[self.level.world_idx] if self.level is not None else None
        if not self.mapper_extension_components_init and self.data.mapper_extension:
            self.mapper_extension_components_init = True
            self.unitile_select_width = 4
            self.selector_unitile_frame = tk.Frame(self.selectors_subframe)
            self.unitile_canvas = GuiMicroGrid(self.selector_unitile_frame, self, w=med_width // micro_width * self.unitile_select_width, height=screenheight, chunkdim=(med_width // micro_width, med_height // micro_height), cb=self.on_unitile_click)
            self.unitile_canvas.divides = [constants.global_med_tiles_count]
            self.unitile_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
        if self.mapper_extension_components_init:
            if not self.data.mapper_extension:
                self.selector_unitile_frame.pack_forget()
                self.unitile_select_id = None
            else:
                self.selector_unitile_frame.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        
            if self.data.mapper_extension and world is not None:
                self.placable_med_tiles = list(range(len(world.med_tiles) + constants.global_med_tiles_count))
                dims=(
                    self.unitile_select_width * med_width // micro_width,
                    ceil_to((len(self.placable_med_tiles) * med_height // micro_height) / self.unitile_select_width, med_height // micro_height)
                )
                self.unitile_canvas.configure(dims=dims)
                self.unitile_canvas.refresh()
                
                clear_coords = [(x, y) for x in range(self.unitile_canvas.w) for y in range(self.unitile_canvas.h)]
                # populate
                for med_sel_idx in range(len(self.placable_med_tiles)):
                    med_idx = self.placable_med_tiles[med_sel_idx]
                    med_y = (med_sel_idx // self.unitile_select_width)
                    med_x = (med_sel_idx % self.unitile_select_width)
                    
                    # set images
                    med_tile = world.get_med_tile(med_idx)
                    for j in range(4):
                        micro_tile_idx = world.get_micro_tile(med_tile[j], self.hard)
                        x = (j % 2) + med_x * 2
                        y = (j // 2) + med_y * 2
                        palette_idx = world.get_med_tile_palette_idx(med_idx, self.hard)
                        img = self.micro_images[world.idx][palette_idx][micro_tile_idx]
                        self.unitile_canvas.set_tile_image(x, y, img)
                        if (x, y) in clear_coords:
                            clear_coords.remove((x, y))
                self.unitile_canvas.clear_from(len(self.placable_med_tiles))
                
                for clear_coord in clear_coords:
                    self.unitile_canvas.set_tile_image(clear_coord[0], clear_coord[1], self.blank_image)
            
            self.refresh_selection_rect()
            self.refresh_label()
    
    def on_unitile_click(self, idx, edit):
        if idx < len(self.placable_med_tiles):
            self.unitile_select_id = self.placable_med_tiles[idx]
            self.object_select_gid = None
            self.macro_tile_select_id = None
            self.set_selection(None)
            if edit:
                self.subwindowctl(GuiMedEdit, world_idx=self.level.world_idx, med_tile_idx=self.unitile_select_id)
            self.refresh_selection_rect()
            self.refresh_label()
    
    def refresh_title(self):
        str = constants.mmname
        if self.file["hack"]:
            str += " - " + os.path.basename(self.file["hack"])
        if self.dirty:
            str += " *"
        self.window.title(str)
        
    def refresh_label(self):
        str = ""
        color="black"
        if self.data is None:
            str = "Load a Base ROM."
        elif self.level is None:
            str = "Select a stage."
        else:
            # level name
            str += self.level.get_name(self.hard)
            str += " "
            while len(str) < 0x10:
                str += " "
            
            # placement
            if self.object_select_gid is not None:
                object_name = constants.object_names[self.object_select_gid][0]
                str += "Object: " + object_name
            elif self.macro_tile_select_id is not None:
                str += "Macro-Tile: " + HB(self.macro_tile_select_id)
            elif self.unitile_select_id is not None:
                str += "Med-tile: " + HB(self.unitile_select_id)
            
            while len(str) < 0x26:
                str += " "
                
            # space remaining
            ps_ = self.level.produce_patches_stream()
            os_ = self.level.produce_objects_stream()
            
            bits_used = int(ps_.length_bytes() * 8 + os_.length_bits())
            bytes_used = int((bits_used) / 8)
            bits_used = int(bits_used % 8)
            str += "Level: " + HB(bytes_used) + "." + HB(bits_used * 2)[1] + " bytes"
            
            # total level space
            total_level_length = 0
            for level in self.data.levels:
                total_level_length += level.length_bytes()
            max_level_length = constants.ram_range_levels[1] - constants.ram_range_levels[0]
            if self.data.mapper_extension:
                max_level_length = 0x4000
            
            self.level_usage_bar.configure(
                usage=total_level_length,
                max=max_level_length
            )

            # unitile patch data
            if self.data.mapper_extension:
                unitile_size = 0
                unitile_max = src.mappermages.unitile_table_range[1] - src.mappermages.unitile_table_range[0]
                for level in self.data.levels:
                    # add 2 for the pointer at the start, which is not part of the stream
                    unitile_size += level.length_unitile_bytes() + 10 + level.length_object_drops_bytes()
                
                str += "; Level Ext.: " + HX(self.level.length_unitile_bytes() + 10 + self.level.length_object_drops_bytes()) + " bytes"
                self.alt_usage_bar.pack(fill=tk.X)
                self.alt_usage_bar.configure(
                    usage=unitile_size,
                    max=unitile_max
                )
            else:
                self.alt_usage_bar.pack_forget()

            
        self.label.configure(text=str, fg=color, anchor=tk.W, font=("TkFixedFont", 9, "normal"))
    
    def run(self):
        self.window.mainloop()