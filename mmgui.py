import constants
from util import *
import os

import mmimage
import mmdata
from functools import partial

available = True

try:
    from PIL import Image, ImageDraw, ImageOps, ImageTk
    import tkinter as tk
    import tkinter.filedialog
except ImportError:
    available = False
   
if not mmimage.available:
    available = False


macro_width = 32
macro_height = 32
med_width = 16
med_height = 16
micro_width = 8
micro_height = 8

objwidth = 32
objheight = 33
screenwidth = 256
screenheight = 224
levelwidth = 256
levelheight = macro_height * constants.macro_rows_per_level
gridcol = "#333"
seamcol = "white"
selcol = constants.meta_colour_str
patchcol = constants.meta_colour_str
objcrosscol = {False: constants.meta_colour_str, True: constants.meta_colour_str_b}

resource_dir = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(resource_dir, "icon.png")

class Gui:
    def __init__(self):
        self.data = None
        self.file = {"hack": None, "rom": None, "image": None}
        self.dirty = False
        self.show_lines = True
        self.show_patches = True
        self.show_objects = True
        self.placable_objects = []
        self.placable_tiles = []
        self.object_select_gid = None
        self.macro_tile_select_id = None
        self.level = None
        self.stage_idx = 0
        self.hard = False
        
        # clearable elts
        self.elts_macro_select = []
        self.elts_object_select = []
        self.elts_stage_horizontal_lines = []
        self.elts_row_lines = [None for i in range(constants.macro_rows_per_level)]
        self.elts_objects = []
        self.elts_patch_rects = []
        self.elt_macro_select_rect = None
        self.elt_object_select_rect = None
        self.init()
        
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
                title = "select base ROM"
            else:
                title = "export to ROM"
            promptfn = partial(promptfn, filetypes=[("NES Rom", ".nes")])
        if type == "hack":
            promptfn = partial(promptfn, filetypes=[("MMagEdit Hack", ".txt")])
        if save:
            if type == "image":
                promptfn = partial(tkinter.filedialog.askdirectory, mustexist=True)
                title = "select destination directory for images"
                if type == "rom":
                    promptfn = partial(promptfn, defaultextension=".nes")
                if type == "hack":
                    promptfn = partial(promptfn, defaultextension=".txt")
        
        if path is None:
            promptfn(title=title, multiple=False)
        
        result = self.fio_direct(path, type, save)
        
        if result and not save:
            self.refresh_all()
        return result
        
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
            if type == "rom" and self.data is not None:
                return False
            
            # cannot load image
            if type == "image" and save:
                return False
            
            if type == "rom":
                if save:
                    return self.data.write(path)
                else:
                    self.data = mmdata.MMData()
                    if self.data.read(path):
                        return True
                    self.data = None # set data to none so we don't later think the data exists.
                    return False
            
            if type == "image" and save:
                return mmimage.export_images(self.data, path)
            
            if type == "hack":
                return self.data.parse(path)
            
            # note: do not refresh anything directly
            # the caller is expected to call the refresh functions
            # this allows the caller to invoke several fio_direct commands before refreshing
        except:
            # catch any save/load error, and return false if one occurs.
            pass # fallthrough
        return False
        
    def refresh_all(self):
        self.refresh_chr()
        self.select_stage(0)
        
    def soft_quit(self):
        if self.dirty and self.data is not None:
            if not self.fio_prompt("hack", True):
                # user aborted save -- don't quit.
                return
        self.window.quit()
    
    def attach_scrollbar(self, canvas, frame):
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=canvas.yview)
        canvas.config(yscrollcommand=scrollbar.set)
        
    # handles a kepyress event
    def on_keypress(self, event):
        print(event)
        pass
        
    def get_event_y(self, event, canvas)
        return event.y + canvas.yview[0] * canvas.config('scrollregion')[3]
        
    def on_stage_click(self, button, event):
        if not self.level:
            return
            
        y = get_event_y()
        x = event.x
        print("click", x, y)
        
        # object placement
        if self.object_select_gid is not None:
            x = clamp_hoi(x / micro_width, 0, levelwidth // micro_width)
            y = clamp_hoi(micro_y, 0, levelheight // micro_height)
        
        # tile placement
        if self.macro_tile_select_id is not None:
            macro_row_idx = clamp_hoi(constants.macro_rows_per_level - int(y / macro_height), 0, constants.macro_rows_per_level)
            macro_row = self.level.macro_rows[macro_row_idx]
            seam_x = macro_row.seam * med_width
            macro_col_x = (max(int(x - seam_x + levelwidth), 0) % levelwidth) // macro_width
            if macro_col_x >= 4:
                macro_col_x = 7 - macro_col_x
            macro_idx = clamp_hoi(macro_col_x, 0, 4)
            
            
            
            
        
    def on_macro_click(self, event):
        y = get_event_y()
        idx = clamp_hoi(y / (macro_height + 1), 0, len(self.placable_tiles))
        pass
        
    def on_object_click(self, event):
        y = get_event_y()
        idx = clamp_hoi(y / (objheight), 0, len(self.placable_objects))
        pass
    
    def add_menu_command(self, menu, label, command, accelerator):
        return menu.add_command(label="Load Base ROM...", command=command, accelerator=accelerator)
    
    # sets up windows and widgets
    # self.data need not be set yet.
    def init(self):
        self.window = tk.Tk()
        
        self.window.bind("<Key>", self.on_keypress)
        
        # menus
        menu = tk.Menu(self.window)
        
        filemenu = tk.Menu(menu, tearoff=0)
        self.menu_base_rom = self.add_menu_command(filemenu, "Load Base ROM...", partial(self.fio_prompt, "rom", False), "Ctrl+Shift+R")
        self.menu_fio = [self.add_menu_command(filemenu, "Open Hack...", partial(self.fio_prompt, "hack", False), "Ctrl+O")]
        filemenu.add_separator()
        self.menu_fio += [
            self.add_menu_command(filemenu, "Save Hack", partial(self.fio_prompt, "hack", True, True), "Ctrl+O"),
            self.add_menu_command(filemenu, "Save Hack As...", partial(self.fio_prompt, "hack", True), "Ctrl+Shift+S"),
            self.add_menu_command(filemenu, "Export Patched ROM...", partial(self.fio_prompt, "rom", True), "Ctrl+E"),
            self.add_menu_command(filemenu, "Export Image Sheet...", partial(self.fio_prompt, "image", True), "Ctrl+J")
        ]
        
        # start disabled
        for m in self.menu_fio:
            filemenu.entryconfig(m, state="disabled")
        
        filemenu.add_separator()
        self.add_menu_command(filemenu, "Quit", partial(self.soft_quit), "Ctrl+Q")
        menu.add_cascade(label="File", menu=filemenu)
        
        editmenu = tk.Menu(menu, tearoff=0)
        self.add_menu_command(editmenu, "Flip Object X", lambda: self.ctl(flipx=not self.flipx), "x")
        self.add_menu_command(editmenu, "Flip Object Y", lambda: self.ctl(flipy=not self.flipy), "y")
        menu.add_cascade(label="Edit", menu=editmenu)
        
        viewmenu = tk.Menu(menu, tearoff=0)
        self.menu_view_hard = self.add_menu_command(viewmenu, "Hard Mode", lambda: self.select_stage(self.level_idx, not self.hard), "p")
        stagemenu = tk.Menu(viewmenu, tearoff=0)
        
        for level_idx in range(constants.level_count):
            if level_idx in [3, 6, 9]:
                stagemenu.add_separator()
            
            level = self.data.levels[level_idx]
            accelerator = ("Shift+F" + str(23 - level_idx)) if level_idx >= 12 else "F" + str(level_idx + 1)
            self.add_menu_command(stagemenu, level.get_name(), partial(self.select_stage, level_idx), accelerator)
            
        viewmenu.add_cascade(label="Stage", menu=stagemenu)
        viewmenu.add_separator()
        
        self.add_menu_command(viewmenu, "Objects", lambda: self.ctl(show_objects=not self.show_objects), "h")
        self.add_menu_command(viewmenu, "Grid", lambda: self.ctl(show_lines=not self.show_lines), "g")
        self.menu_view_patches = self.add_menu_command(viewmenu, "Patches", lambda: self.ctl(show_patches=not self.show_patches), "p")
        
        menu.add_cascade(label="View", menu=viewmenu)
        
        # containers
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        stage_frame = tk.Frame(main_frame)
        stage_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        selectors_frame = tk.Frame(main_frame)
        selectors_frame.pack(side = tk.RIGHT, fill=tk.Y)
        
        selector_macro_frame = tk.Frame(selectors_frame)
        selector_macro_frame.pack(side = tk.LEFT, fill=tk.Y, expand=True)
        
        selector_objects_frame = tk.Frame(selectors_frame)
        selector_objects_frame.pack(side = tk.RIGHT, fill=tk.Y, expand=True)
        
        # canvases
        stage_canvas = tk.Canvas(stage_frame, width=screenwidth, height=screenheight, scrollregion=(0, 0, levelwidth, levelheight), bg="black")
        self.attach_scrollbar(stage_canvas, stage_frame)
        stage_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        stage_canvas.bind("<Button-1>", partial(self.on_stage_click, 1))
        stage_canvas.bind("<Button-2>", partial(self.on_stage_click, 2))
        stage_canvas.bind("<Button-3>", partial(self.on_stage_click, 3))
        
        macro_canvas = tk.Canvas(selector_macro_frame, width=macro_width, height=screenheight, bg="black")
        self.attach_scrollbar(macro_canvas, selector_macro_frame)
        macro_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        macro_canvas.bind("<Button-1>", partial(self.on_macro_click))
        
        object_canvas = tk.Canvas(selector_objects_frame, width=objwidth, height=screenheight, bg="black")
        self.attach_scrollbar(object_canvas, selector_objects_frame)
        object_canvas.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        object_canvas.bind("<Button-1>", partial(self.on_object_click))
        
        # canvas images (reused):
        self.stage_micro_images = [[stage_canvas.create_image(x * micro_width, y * micro_height, image=None, anchor=tk.NW) for y in range(levelheight // micro_height)] for x in range(levelwidth // micro_width)]
        self.macro_micro_images = [[macro_canvas.create_image(x * micro_width, y * micro_height + (y // 4), image=None, anchor=tk.NW) for y in range(0x100 * macro_height // micro_height)] for x in range(macro_width // micro_width)]
        self.object_images = [object_canvas.create_image(objwidth / 2, objheight / 2 + objheight * y, image=None, anchor=tk.CENTER) for y in range(0xff)]
        
        # bottom label
        self.label = tk.Label()
        
        self.window.config(menu=menu)
        self.refresh_title()
        self.refresh_label()
    
    # this is quite expensive... progress bar? coroutine?
    def refresh_chr(self):
        assert(self.data)
        
        # object images
        # list [flip][gid]
        self.object_images = [None] * 4
        for j in range(4):
            flipx = j % 2 == 1
            flipy = j >= 2
            self.object_images[j] = mmimage.produce_object_images(self.data)
            
            # flip x and/or y
            for i in len(self.object_images[j]):
                img = self.object_images[j][i]
                if img is not None:
                    if flipx:
                        img = ImageOps.mirror(img)
                    if flipy:
                        img = ImageOps.flip(img)
                    self.object_images[j][i] = ImageTk.PhotoImage(image=img)
        
        # micro-tile images
        # list [world][palette_idx][id]
        self.micro_images = [[[None for id in range(0x100)] for palette_idx in range(8)] for world in data.worlds]
        for world_idx in range(len(data.worlds)):
            world = data.worlds[world_idx]
            images = [mmimage.produce_micro_tile_images(world, hard) for hard in [False, True]]
            for palette_idx in range(len(world.palettes))
                for id in range(0x100):
                    self.micro_images[world_idx][palette_idx][id] = ImageTk.PhotoImage(image=images[palette_idx % 4][palette_idx // 4])
    
    def select_stage(self, stage_idx, hard=False):
        self.object_select_gid = None
        self.macro_tile_select_id = None
        self.stage_idx = stage_idx
        self.hard = hard
        self.level = self.data.levels[stage_idx]
        
        self.placable_objects = []
        
        filemenu.entryconfig(self.menu_view_patches, state="normal" if hard else "disabled")
        
        # decide on placable tiles
        if hard:
            self.placable_tiles = [0] + list(range(0x30, 0x3f))
        else:
            self.placable_tiles = list(range(0x100))
        
        # filter out tiles not in world
        for tile_idx in self.placable_tiles:
            if tile_idx > level.world.macro_tile_count:
                self.placable_tiles.remove(tile_idx)
        
        # decide on placable objects
        for gid in self.data.spawnable_objects:
            objdata = object_data[gid]
            hard_only = objdata["hard"] if "hard" in objdata else False
            if hard_only == self.hard and self.object_images[0][gid] is not None:
                self.placable_objects.append(gid)
                
        self.placable_tiles = []
        
        # refresh the selectors
        self.refresh_object_select()
        self.refresh_tile_select()
        self.refresh_selection_rect()
        
        # refresh the stage view
        self.refresh_horizontal_lines()
        for i in range(constants.macro_rows_per_level):
            self.refresh_row_lines(i)
            self.refresh_row_tiles(i)
        self.refresh_objects()
        self.refresh_patch_rects()
        
        # refresh related data
        self.refresh_title()
        self.refresh_label()
    
    def delete_elements(self, canvas, elements):
        for element in elements:
            if element is not None:
                canvas.delete(element)
    
    def refresh_tile_select(self):
        self.delete_elements(self.macro_canvas, self.elts_macro_select)
        self.elts_macro_select = []
        
        # clear images
        for x in range(macro_width // micro_width):
            for y in range(0x100 * macro_height // micro_height):
                self.macro_canvas.itemconfig(self.macro_micro_images[x][y], image=None)
                
        if self.level is None:
            return
        world = self.level.world
        
        # set scrollable region
        self.macro_canvas.configure(scrollregion=(0, 0, macro_width, len(self.placable_tiles) * (macro_height + 1)))
        
        # populate
        for macro_y in range(len(self.placable_tiles)):
            macro_idx = self.placable_tiles[macro_y]
            line_y = macro_y * (macro_height + 1) + macro_height
            
            # add line
            self.elts_macro_select.append(self.macro_canvas.create_line(0, line_y, macro_width, line_y, fill="#888"))
            macro_tile = world.get_macro_tile(macro_idx)
            
            # set images
            for i in range(4):
                med_tile_idx = macro_tile[i]
                med_tile = world.get_med_tile(med_tile_idx)
                for j in range(4):
                    micro_tile_idx = world.get_micro_tile(med_tile[j])
                    x = (i % 2) * 2 + (j % 2)
                    y = (i // 2) * 2 + (j // 2) + macro_y * 4
                    img = self.micro_images[world.idx][world.get_med_tile_palette_idx(med_tile_idx)][micro_tile_idx]
                    self.macro_canvas.itemconfig(self.macro_micro_images[x][y], image=img)
                    
    
    def refresh_object_select(self):
        self.delete_elements(self.object_canvas, self.elts_object_select)
        self.elts_object_select = []
        
        # clear images
        for y in range(0x100):
            self.object_canvas.itemconfig(self.object_images[y], image=None)

        # set scrollable region
        self.object_canvas.configure(scrollregion=(0, 0, macro_width, len(self.placable_tiles) * (objheight)))

        flip_idx = (2 if self.flipy else 0) + (1 if self.flipx else 0)

        for i in range(len(self.placable_objects)):
            gid = self.placable_objects[i]
            line_y = i * objheight + objheight
            
            # place line
            self.elts_macro_select.append(self.object_canvas.create_line(0, line_y, objwidth, line_y, fill="#888"))
            
            # set object
            self.object_canvas.itemconfig(self.object_images[y], image=self.object_images[flip_idx][gid])
        
    def refresh_selection_rect(self):
        # clear previous
        if self.elt_macro_select_rect is not None:
            self.macro_canvas.delete(self.elt_macro_select_rect)
        if self.elt_object_select_rect is not None:
            self.object_canvas.delete(self.elt_object_select_rect)
        self.elt_macro_select_rect = None
        self.elt_object_select_rect = None
        
        # rectangle properties
        rect_colstr = selcol
        rect_margin = 2
        rect_width = 2
        
        # place the selection rect (if object selected)
        if self.object_select_gid is not None:
            i = self.placable_objects.index(self.object_select_gid)
            y = i * objheight
            self.elt_object_select_rect = self.object_canvas.create_rectangle(
                rect_margin, y + rect_margin, objwidth - rect_margin y + objheight - rect_margin,
                width=rect_width
                outline=rect_colstr
             )
             
        # place the selection rect (if tile selected)
        if self.macro_tile_select_id is not None:
            i = self.placable_tiles.index(self.macro_tile_select_id)
            y = i * (macro_height + 1)
            self.elt_macro_select_rect = self.object_canvas.create_rectangle(
                rect_margin, y + rect_margin, macro_width - rect_margin y + macro_height - rect_margin,
                width=rect_width
                outline=rect_colstr
             )
        
    def refresh_horizontal_lines(self):
        self.delete_elements(self.stage_canvas, self.elts_stage_horizontal_lines)
        self.elts_stage_horizontal_lines = []
        
        if self.show_lines:
            for i in range(constants.macro_rows_per_level - 1):
                y = levelheight - macro_height * (i + 1)
                self.elts_stage_horizontal_lines.append(
                    self.stage_canvas.create_line(
                        0, y, levelwidth, y,
                        fill=gridcol
                    )
                )
        
    def refresh_row_lines(self, row_idx):
        self.delete_elements(self.stage_canvas, self.elts_row_lines)
        self.elts_row_lines = []
        
        if self.show_lines and self.level is not None:
            y = levelheight - macro_height * row_idx - macro_height
            macro_row = self.level.macro_rows[row_idx]
            seam = macro_row.seam
            seam_x = med_width * seam
            
            # place thin vertical lines
            for i in range(levelwidth // macro_width):
                x = (2 * (i + 1) + (seam % 2)) * med_width
                if x < levelwidth and x != seam_x:
                    self.elts_row_lines.append(
                        self.stage_canvas.create_line(x, y, x, y + macro_height),
                        fill = gridcol
                    )
            
            # place seam
            if seam_x != 0:
                self.elts_row_lines.append(
                    self.stage_canvas.create_line(x, y, x, y + macro_height),
                    fill = seamcol
                )
        
    def refresh_row_tiles(self, row_idx):
        if self.level is not None:
            micro_y = (macro_rows_per_level - row_idx - 1) * (macro_height // micro_height)
            med_tile_rows = self.level.produce_med_tiles(self.hard, range(row_idx * 2, row_idx * 2 + 2))
            
            for med_tile_row_idx in range(2):
                med_tile_row = med_tile_rows[med_tile_row_idx]
                for med_tile_col_idx in range(len(med_tile_row)):
                    med_tile_idx = med_tile_row[med_tile_col_idx]
                    med_tile = level.world.get_med_tile(med_tile_idx, self.hard)
                    palette_idx = level.world.get_med_tile_palette_idx(med_tile_idx, self.hard)
                    for i in range(4):
                        micro_tile_idx = level.world.get_micro_tile(med_tile[i], self.hard)
                        x = med_tile_col_idx * 2 + (i % 2)
                        y = micro_y + med_tile_row_idx * 2 + (i // 2)
                        img = self.micro_images[level.world_idx][palette_idx][micro_tile_idx]
                        self.macro_canvas.itemconfig(self.stage_micro_images[x][y], image=img)
        
    def refresh_objects(self):
        self.delete_elements(self.stage_canvas, self.elts_objects)
        self.elts_objects = []
        if self.show_objects and elf.level is not None:
            for obj in self.level.objects:
                obj_data = constants.object_data[obj.gid]
                offset = obj_data["offset"] if "offset" in obj_data else (0, 0)
                flip_idx = (2 if obj.flipy else 0) + (1 if obj.flipx else 0)
                
                # add image
                self.elts_objects.append(
                    self.stage_canvas.create_image(
                        obj.x * micro_width + offset[0], y * micro_height + offset[1],
                        image=self.object_images[flip_idx][obj.gid]
                        anchor=NW
                    )
                )
                
                # add crosshairs
                x = obj.x * micro_width
                y = obj.y * micro_height
                colstr = objcrosscol[obj.compressible()]
                r = 3 # radius
                
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
        
        margin = 4
        
        if self.hard and self.show_patches and self.level is not None:
            for patch in self.level.patches:
                macro_row = self.level.macro_rows[patch.y]
                seam = macro_row.seam
                for mirror in [False, True]:
                    for loop in [-1, 0, 1]
                    y = patch.y * macro_height
                    x = (((7 - patch.x) if mirror else patch.x) * 2 + seam) * med_width
                    x += levelwidth * loop
                    self.elts_patch_rects.append(
                        self.stage_canvas.create_rectangle(
                            x + margin, y + margin, x + macro_width - margin, y + macro_height - margin,
                            fill=rect_colstr, width=2
                        )
                    )
    
    def refresh_title(self):
        str = "MMagEdit"
        if self.file["hack"]:
            str += " - " + self.file["hack"]
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
            if object_select_gid is not None:
                str += "Object: "
            elif self.macro_tile_select_id is not None:
                str += "Tile: "
                
            # space remaining
            max = self.level.total_length
            ps = self.level.produce_patches_stream()
            os = self.level.produce_objects_stream()
            
            bits_used = int(ps.length_bytes() * 8 + os.length_bits())
            if max is None:
                bytes_used = int((bits_used + 7) / 8)
                bits_used = int(bits_used % 8)
                str = "Used: " + HB(bytes_used) + "." + HB(bits_used * 2) + " bytes"
            else:
                max = abs(max) # paranoia
                if bits_used > max * 8:
                    color="red"
                    bits_o = bits_used - max * 8
                    bytes_o = int((bits_o + 7) / 8)
                    bits_o = int(bits_o % 8)
                    str = "OVERLIMIT: " + HB(bytes_o) + "." + HB(bits_o * 2) + " past " + HB(max) + " bytes"
                else:
                    bits_r = max * 8 - bits_used
                    bytes_r = int((bits_r + 7) / 8)
                    bits_r = int(bits_r % 8)
                    str = "Available: " + HB(bytes_r) + "." + HB(bits_r * 2) + " of " + HB(max) + " bytes"
            
        self.label.configure(text=str, color=color, anchor=LEFT, font=("TkFixedFont", 12, "normal"))
    
    def run(self):
        self.window.mainloop()