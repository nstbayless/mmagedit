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
    from tkinter import ttk
    import tkinter.filedialog, tkinter.messagebox
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
objcrosscol = {False: constants.meta_colour_str, True: constants.meta_colour_str_b}

zoom_levels = [1]

resource_dir = os.path.dirname(os.path.realpath(__file__))
icon_path = os.path.join(resource_dir, "icon.png")

# an undoable action
class GuiAction:
    def __init__(self, **kwargs):
        self.type = ""
        self.refresh = []
        self.level_idx = None
        self.hard = None
        for name, value in kwargs.items():
            setattr(self, name, value)

# 32x32 macro-tile editor
class GuiMacroEdit:
    def __init__(self, core):
        self.core = core
        self.window = tk.Toplevel(core.window)
        self.window.title("Macro-Tile Editor")
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.v_world_idx = tk.StringVar()
        self.v_world_idx.set("1")
        self.v_macro_tile_idx = tk.StringVar()
        self.v_macro_tile_idx.set("0D") # a reasonable default tile to edit
        self.v_hard = tk.BooleanVar()
        self.v_hard.set(False)
        self.world_idx = 0
        self.macro_tile_idx = 0xD
        self.closed = False
        self.select_canvas = None
        self.elts_med_select = []
        self.init()
        
        self.v_world_idx.trace("w", callback=self.on_idx_change)
        self.v_macro_tile_idx.trace("w", callback=self.on_idx_change)
        self.v_hard.trace("w", callback=self.on_idx_change)
        self.handling = False
        
    def on_close(self):
        self.closed = True
        self.window.destroy()
        self.core.subwindows.pop(type(self))
        
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
                pass
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
        
        topbar.pack(fill=tk.X)
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        self.med_tile_select_width = 4
        height=224
        
        self.select_canvas = tk.Canvas(mainframe, width = (med_width + 1) * self.med_tile_select_width, height=height, bg="black")
        self.med_micro_images = [[self.select_canvas.create_image(x * micro_width + (x // 2), y * micro_height + (y // 2), image=self.core.blank_image, anchor=tk.NW) for y in range(0x100 * macro_height // micro_height // self.med_tile_select_width)] for x in range(self.med_tile_select_width * 4)]
        self.core.attach_scrollbar(self.select_canvas, mainframe)
        self.select_canvas.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        
        self.place_canvas = tk.Canvas(mainframe, width = macro_width, height=macro_height, bg="black")
        self.place_micro_images = [[self.place_canvas.create_image(x * micro_width, y * micro_height, image=self.core.blank_image, anchor=tk.NW) for y in range(8)] for x in range(8)]
        self.place_canvas.pack()
    
    def refresh(self):
        self.core.delete_elements(self.select_canvas, self.elts_med_select)
        self.elts_med_select = []
        
        if self.select_canvas is None:
            return
        world = self.core.data.worlds[self.world_idx]
        zoom = 0
        
        # set scrollable region
        self.select_canvas.configure(
            scrollregion=(
                0, 0,
                (med_width + 1) * self.med_tile_select_width - 1,
                ((len(world.med_tiles) + constants.global_med_tiles_count + self.med_tile_select_width - 1) // self.med_tile_select_width) * (med_height + 1) - 1
            )
        )
        
        # populate
        macro_tile = world.get_macro_tile(self.macro_tile_idx)
        for i in range(4):
            med_tile_idx = macro_tile[i]
            med_tile = world.get_med_tile(med_tile_idx)
            palette_idx = world.get_med_tile_palette_idx(med_tile_idx, self.hard)
            for j in range(4):
                micro_tile_idx = med_tile[j]
                x = (i % 2) * 2 + (j % 2)
                y = (i >= 2) * 2 + (j >= 2)
                
                img = self.core.micro_images[world.idx][palette_idx][micro_tile_idx][zoom]
                self.place_canvas.itemconfig(self.place_micro_images[x][y], image=img)
        
        for med_sel_idx in range(len(world.med_tiles) + constants.global_med_tiles_count):
            med_y = (med_sel_idx // self.med_tile_select_width)
            med_x = (med_sel_idx % self.med_tile_select_width)
            line_y = med_y * (med_height + 1) + med_height
            line_x = (med_x) * (med_width + 1)
            
            rounded_sel_idx = med_sel_idx - (med_sel_idx % self.med_tile_select_width)
            divide = (rounded_sel_idx + self.med_tile_select_width == constants.global_med_tiles_count)
            # special symmetry line
            if rounded_sel_idx == 0x1c:
                divide = True
            if rounded_sel_idx == world.max_symmetry_idx:
                divide = True
            
            # add line
            self.elts_med_select.append(self.select_canvas.create_line(line_x, line_y, line_x + med_width + 1, line_y, fill=divcol if divide else linecol, width=2 if divide else 1))
            self.elts_med_select.append(self.select_canvas.create_line(line_x, line_y - med_height, line_x, line_y + 1, fill=linecol))
            
            # set images
            med_tile_idx = med_sel_idx
            med_tile = world.get_med_tile(med_tile_idx)
            palette_idx = world.get_med_tile_palette_idx(med_tile_idx, self.hard)
            for i in range(4):
                micro_tile_idx = world.get_micro_tile(med_tile[i], self.hard)
                x = i % 2 + med_x * 2
                y = i // 2 + med_y * 2
                img = self.core.micro_images[world.idx][palette_idx][micro_tile_idx][zoom]
                self.select_canvas.itemconfig(self.med_micro_images[x][y], image=img)
    
    def ctl(self, kwargs):
        if "macro_tile_idx" in kwargs:
            self.v_macro_tile_idx.set(HB(kwargs["macro_tile_idx"]))
        if "world_idx" in kwargs:
            self.v_world_idx.set(HX(kwargs["world_idx"]))
        if "hard" in kwargs:
            self.v_hard.set(kwargs["hard"])
        pass

# main window and gui data
class Gui:
    def __init__(self):
        self.data = None
        self.subwindows = dict()
        self.mouse_button_actions = ["place", "seam", "remove", "seam"] # left, middle, right, shift
        self.file = {"hack": None, "rom": None, "image": None, "ips": None}
        self.dirty = False
        self.undo_buffer = []
        self.redo_buffer = []
        self.show_lines = True
        self.show_patches = True
        self.show_objects = True
        self.show_crosshairs = True
        self.placable_objects = []
        self.placable_tiles = []
        self.menu_commands = dict()
        self.object_select_gid = None
        self.macro_tile_select_id = None
        self.level = None
        self.stage_idx = 0
        self.hard = False
        self.zoom = 0
        self.flipx = False
        self.flipy = False
        
        # preferences
        self.macro_tile_select_width = 4
        
        # clearable elts
        self.elts_macro_select = []
        self.elts_object_select = []
        self.elts_stage_horizontal_lines = []
        self.elts_row_lines = [[] for i in range(constants.macro_rows_per_level)]
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
            if type == "ips":
                promptfn = partial(promptfn, defaultextension=".ips")
        
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
    def errorbox(self, warning):
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
            
            # cannot load image
            if type == "image" and not save:
                return False
                
            # cannot load ips
            if type == "ips" and not save:
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
                
            if type == "ips" and save:
                self.file[type] = path
                rval = self.data.write_ips(path)
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
        
    def ctl(self, **kw):
        if "flipx" in kw:
            self.flipx = kw["flipx"]
            self.refresh_object_select()
        if "flipy" in kw:
            self.flipy = kw["flipy"]
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
        if "show_patches" in kw and self.hard:
            self.show_patches = kw["show_patches"]
            self.refresh_patch_rects()
        
        self.refresh_label()
    
    def clear_stage(self):
        if tkinter.messagebox.askyesno("Clear Stage", "Clearing the stage cannot be undone. Are you sure you'd like to proceed?"):
            level = self.level
            if level:
                level.hardmode_patches = []
                level.objects = []
                for macro_row in level.macro_rows:
                    macro_row.macro_tiles = [0, 0, 0, 0]
                    macro_row.seam = 0
                
                # lazy, but this is one way to refresh everything.
                self.select_stage(self.stage_idx, self.hard)
                self.clear_undo_buffers()
    
    def about(self):
        tkinter.messagebox.showinfo(constants.mmname, constants.mminfo)
    
    # handles a kepyress event
    def on_keypress(self, event):
        shift = event.state & 1
        ctrl = event.state & 4
        for acc, command in self.menu_commands.items():
            if acc is None:
                continue
            acc = acc.lower()
            if ctrl and "ctrl+" not in acc:
                continue
            if shift and "shift+" not in acc:
                continue
            if acc.startswith("ctrl+"):
                if not ctrl:
                    continue
                else:
                    acc = acc[5:]
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
        
    def apply_action(self, action, undo=False):
        if self.data is None:
            return
        
        if action.level_idx is not None:
            # switch to the stage this action was/is applied to
            # (we only do this so as not to confuse the user -- these lines could be commented out.)
            if self.level.level_idx != action.level_idx or self.hard != action.hard:
                self.select_stage(action.level_idx, action.hard)
        else:
            # record stage and hardmode so that if this is undone the user will return to here.
            action.level_idx = self.level.level_idx
            action.hard = self.hard
        
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
        
        if action.type == "tile":
            tile = action.prev_tile if undo else action.tile
            macro_row = level.macro_rows[action.macro_row_idx]
            macro_row.macro_tiles[action.macro_idx] = tile
        if action.type == "seam":
            seam = action.prev_seam if undo else action.seam
            macro_row = level.macro_rows[action.macro_row_idx]
            macro_row.seam = seam
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
            
        if "row" in action.refresh:
            self.refresh_row_tiles(action.macro_row_idx)
            self.refresh_row_lines(action.macro_row_idx)
            # needed for the weird "normal-mode grinder" effect
            self.refresh_objects()
        elif "objects" in action.refresh:
            self.refresh_objects()
        if "patches" in action.refresh:
            self.refresh_patch_rects()
            
        # we've made a change.
        self.dirty = True
        
        self.refresh_label()
        self.refresh_title()
        
    def on_stage_click(self, button, event):
        if not self.level:
            return
        
        level = self.level
        
        shift = event.state & 5 != 0 # actually checks ctrl and shift
        action = self.mouse_button_actions[3 if shift else button - 1]
        
        y = self.get_event_y(event, self.stage_canvas, level_height)
        x = event.x
        
        # object placement
        place_duplicates = False
        if self.object_select_gid is not None:
            place_duplicates = shift
            if shift: # FIXME this is kinda gross, as actions should be set by mouse+shift only...
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
                
            if action == "place":
                obj = mmdata.Object(self.data)
                obj.x = objx
                obj.y = objy
                obj.flipx = self.flipx
                obj.flipy = self.flipy
                obj.gid = self.object_select_gid
                obj.name = constants.object_names[obj.gid][0]
                
                self.apply_action(GuiAction(
                    type="object", refresh=["objects"],
                    remove=False,
                    object=obj
                ))
            
            self.refresh_objects()
        
        # tile adjustment
        if self.macro_tile_select_id is not None or (action == "seam" and not place_duplicates):
            macro_row_idx = clamp_hoi(constants.macro_rows_per_level - int(y / macro_height) - 1, 0, constants.macro_rows_per_level)
            macro_row = level.macro_rows[macro_row_idx]
            seam_x = macro_row.seam * med_width
            macro_col_x = (max(int(x - seam_x + level_width), 0) % level_width) // macro_width
            if macro_col_x >= 4:
                macro_col_x = 7 - macro_col_x
            macro_idx = clamp_hoi(macro_col_x, 0, 4)
            
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
                        type="seam", refresh=["row"],
                        macro_row_idx=macro_row_idx,
                        prev_seam=macro_row.seam,
                        seam=clamp_hoi(x / med_width, 0, level_width // med_width)
                    ))
    
    def subwindowctl(self, type, **kwargs):
        # check if subwindow has closed
        if type in self.subwindows:
            if self.subwindows[type].closed:
                self.subwindows.pop(type)
        
        # open new subwindow
        if type not in self.subwindows:
            self.subwindows[type] = type(self)
            
        # ctl it
        self.subwindows[type].ctl(kwargs)
        pass
    
    def on_macro_click(self, edit, event):
        if len(self.placable_tiles) == 0:
            return
        h = ((len(self.placable_tiles) + self.macro_tile_select_width - 1) // self.macro_tile_select_width) * (macro_height + 1)
        y = self.get_event_y(event, self.macro_canvas, h)
        x = clamp_hoi(event.x, 0, (macro_width + 1) * self.macro_tile_select_width)
        idx = clamp_hoi(int(x // (macro_width + 1)) + int(y / (macro_height + 1)) * self.macro_tile_select_width, 0, len(self.placable_tiles))
        self.macro_tile_select_id = self.placable_tiles[idx]
        self.object_select_gid = None
        if edit:
            self.subwindowctl(GuiMacroEdit, world_idx=self.level.world_idx, macro_tile_idx=self.macro_tile_select_id)
        self.refresh_selection_rect()
        self.refresh_label()
        
    def on_object_click(self, edit, event):
        if len(self.placable_objects) == 0:
            return
        y = self.get_event_y(event, self.object_canvas, len(self.placable_objects) * (macro_height + 1))
        idx = clamp_hoi(y / (objheight), 0, len(self.placable_objects))
        self.macro_tile_select_id = None
        self.object_select_gid = self.placable_objects[idx]
        self.refresh_selection_rect()
        self.refresh_label()
    
    def add_menu_command(self, menu, label, command, accelerator):
        self.menu_commands[accelerator] = command
        menu.add_command(label=label, command=command, accelerator=accelerator)
        return menu.index(label)
    
    # sets up windows and widgets
    # self.data need not be set yet.
    def init(self):
        self.window = tk.Tk()
        self.window.iconphoto(True, tk.PhotoImage(file=icon_path))
        
        self.window.bind("<Key>", self.on_keypress)
        self.blank_image = ImageTk.PhotoImage(image=Image.new('RGB', (4, 4), color='black'))
        
        # menus
        menu = tk.Menu(self.window)
        
        filemenu = tk.Menu(menu, tearoff=0)
        self.filemenu = filemenu
        self.menu_base_rom = self.add_menu_command(filemenu, "Load Base ROM...", partial(self.fio_prompt, "rom", False), "Ctrl+Shift+R")
        self.menu_fio = [self.add_menu_command(filemenu, "Open Hack...", partial(self.fio_prompt, "hack", False), "Ctrl+O")]
        filemenu.add_separator()
        self.menu_fio += [
            self.add_menu_command(filemenu, "Save Hack", partial(self.fio_prompt, "hack", True, True), "Ctrl+S"),
            self.add_menu_command(filemenu, "Save Hack As...", partial(self.fio_prompt, "hack", True), "Ctrl+Shift+S")
        ]
        filemenu.add_separator()
        self.menu_fio += [
            self.add_menu_command(filemenu, "Export Patched ROM...", partial(self.fio_prompt, "rom", True), "Ctrl+E"),
            self.add_menu_command(filemenu, "Export IPS Patch...", partial(self.fio_prompt, "ips", True), "Ctrl+P"),
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
        self.add_menu_command(editmenu, "Flip Object X", lambda: self.ctl(flipx=not self.flipx), "X")
        self.add_menu_command(editmenu, "Flip Object Y", lambda: self.ctl(flipy=not self.flipy), "Y")
        editmenu.add_separator()
        self.add_menu_command(editmenu, "Clear Stage", partial(self.clear_stage), None)
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
        
        menu.add_cascade(label="View", menu=viewmenu)
        
        windowmenu = tk.Menu(menu, tearoff=0)
        self.windowmenu = windowmenu
        self.add_menu_command(windowmenu, "Macro Tile Editor", lambda: self.subwindowctl(GuiMacroEdit, world_idx=self.level.world_idx), None)
        menu.add_cascade(label="Window", menu=windowmenu)
        
        helpmenu = tk.Menu(menu, tearoff=0)
        self.add_menu_command(helpmenu, "About", self.about, None)
        menu.add_cascade(label="Help", menu=helpmenu)
        
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
        stage_canvas = tk.Canvas(stage_frame, width=screenwidth, height=screenheight, scrollregion=(0, 0, level_width, level_height), bg="black")
        self.attach_scrollbar(stage_canvas, stage_frame)
        stage_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        stage_canvas.bind("<Button-1>", partial(self.on_stage_click, 1))
        stage_canvas.bind("<Button-2>", partial(self.on_stage_click, 2))
        stage_canvas.bind("<Button-3>", partial(self.on_stage_click, 3))
        
        macro_canvas = tk.Canvas(selector_macro_frame, width=macro_width * self.macro_tile_select_width, height=screenheight, bg="black")
        self.attach_scrollbar(macro_canvas, selector_macro_frame)
        macro_canvas.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        macro_canvas.bind("<Button-1>", partial(self.on_macro_click, False))
        macro_canvas.bind("<Button-3>", partial(self.on_macro_click, True))
        macro_canvas.bind("<Double-Button-1>", partial(self.on_macro_click, True))
        
        object_canvas = tk.Canvas(selector_objects_frame, width=objwidth, height=screenheight, bg="black")
        self.attach_scrollbar(object_canvas, selector_objects_frame)
        object_canvas.pack(side=tk.RIGHT, fill=tk.Y, expand=True)
        object_canvas.bind("<Button-1>", partial(self.on_object_click, False))
        object_canvas.bind("<Button-3>", partial(self.on_object_click, True))
        object_canvas.bind("<Double-Button-1>", partial(self.on_object_click, True))
        
        # private access
        self.stage_canvas = stage_canvas
        self.macro_canvas = macro_canvas
        self.object_canvas = object_canvas
        
        # canvas images (reused):
        self.stage_micro_dangerous = [[False for y in range(level_height // micro_height)] for x in range(level_width // micro_width)]
        self.stage_micro_images = [[stage_canvas.create_image(x * micro_width, y * micro_height, image=self.blank_image, anchor=tk.NW) for y in range(level_height // micro_height)] for x in range(level_width // micro_width)]
        self.macro_micro_images = [[macro_canvas.create_image(x * micro_width + (x // 4), y * micro_height + (y // 4), image=self.blank_image, anchor=tk.NW) for y in range(0x100 * macro_height // micro_height // self.macro_tile_select_width)] for x in range(self.macro_tile_select_width * 4)]
        self.object_select_images = [object_canvas.create_image(objwidth / 2, objheight / 2 + objheight * y, image=self.blank_image, anchor=tk.CENTER) for y in range(0x100)]
        
        # bottom label
        self.label = tk.Label(self.window)
        self.label.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.window.config(menu=menu)
        
        # we do this to refreshes menus, label, title.
        # (the undo buffer will definitely be clear at this point already regardless.)
        self.clear_undo_buffers()
    
    # this is quite expensive... progress bar? coroutine?
    def refresh_chr(self):
        assert(self.data)
        
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
                    self.object_images[j][i] = ImageTk.PhotoImage(image=img)
        
        # micro-tile images
        # list [world][palette_idx][id]
        self.micro_images = [[[[None for zoom in range(len(zoom_levels))] for id in range(0x100)] for palette_idx in range(8)] for world in self.data.worlds]
        for world_idx in range(len(self.data.worlds)):
            world = self.data.worlds[world_idx]
            images = [mmimage.produce_micro_tile_images(world, hard) for hard in [False, True]]
            for palette_idx in range(len(world.palettes)):
                for id in range(0x100):
                    img = images[palette_idx // 4][palette_idx % 4][id]
                    for zoom in range(len(zoom_levels)):
                        imgzoom = ImageOps.fit(img, (img.width * zoom_levels[zoom], img.height * zoom_levels[zoom]))
                        self.micro_images[world_idx][palette_idx][id][zoom] = ImageTk.PhotoImage(image=imgzoom)
    
    def select_stage(self, stage_idx, hard=False):
        if self.data is None:
            return
            
        self.object_select_gid = None
        self.macro_tile_select_id = 0x30 if hard else 0xd # a good default selection.
        self.stage_idx = stage_idx
        self.hard = hard
        self.level = self.data.levels[stage_idx]
        
        self.placable_objects = []
        
        self.viewmenu.entryconfig(self.menu_view_patches, state=tk.NORMAL if hard else tk.DISABLED)
        
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
        for gid in self.data.spawnable_objects:
            objdata = constants.object_data[gid]
            hard_only = objdata["hard"] if "hard" in objdata else False
            # skip objects without images, and only have grinders on hard mode.
            if (hard_only == self.hard or not self.hard) and self.object_images[0][gid] is not None:
                self.placable_objects.append(gid)
        
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
        for x in range(self.macro_tile_select_width * macro_width // micro_width):
            for y in range(0x100 * macro_height // micro_height // self.macro_tile_select_width):
                self.macro_canvas.itemconfig(self.macro_micro_images[x][y], image=self.blank_image)
                
        if self.level is None:
            return
            
        world = self.level.world
        
        # set scrollable region
        self.macro_canvas.configure(scrollregion=(0, 0, (macro_width + 1) * self.macro_tile_select_width - 1, ((len(self.placable_tiles) + self.macro_tile_select_width - 1) // self.macro_tile_select_width) * (macro_height + 1) - 1))
        
        # populate
        for macro_sel_idx in range(len(self.placable_tiles)):
            macro_idx = self.placable_tiles[macro_sel_idx]
            macro_y = (macro_sel_idx // self.macro_tile_select_width)
            macro_x = (macro_sel_idx % self.macro_tile_select_width)
            line_y = macro_y * (macro_height + 1) + macro_height
            line_x = (macro_x) * (macro_width + 1)
            
            divide = (macro_sel_idx - (macro_sel_idx % self.macro_tile_select_width) + self.macro_tile_select_width == constants.global_macro_tiles_count)
            
            # add line
            self.elts_macro_select.append(self.macro_canvas.create_line(line_x, line_y, line_x + macro_width, line_y, fill=divcol if divide else linecol, width=2 if divide else 1))
            self.elts_macro_select.append(self.macro_canvas.create_line(line_x + macro_width, line_y - macro_height, line_x + macro_width, line_y + 1, fill=linecol))
            
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
                    img = self.micro_images[world.idx][palette_idx][micro_tile_idx][self.zoom]
                    self.macro_canvas.itemconfig(self.macro_micro_images[x][y], image=img)
                    
    
    def refresh_object_select(self):
        self.delete_elements(self.object_canvas, self.elts_object_select)
        self.elts_object_select = []
        
        # clear images
        for y in range(0x100):
            self.object_canvas.itemconfig(self.object_select_images[y], image=self.blank_image)

        # set scrollable region
        self.object_canvas.configure(scrollregion=(0, 0, objwidth, len(self.placable_objects) * objheight - 1))

        flip_idx = (2 if self.flipy else 0) + (1 if self.flipx else 0)

        for i in range(len(self.placable_objects)):
            gid = self.placable_objects[i]
            line_y = i * objheight + objheight
            
            divide = i == 0xf
            
            # place line
            self.elts_object_select.append(self.object_canvas.create_line(0, line_y, objwidth, line_y, fill=divcol if divide else linecol, width=2 if divide else 1))
            
            # set object
            self.object_canvas.itemconfig(self.object_select_images[i], image=self.object_images[flip_idx][gid])
        
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
                rect_margin, y + rect_margin, objwidth - rect_margin, y + objheight - rect_margin,
                width=rect_width,
                outline=rect_colstr
             )
             
        # place the selection rect (if tile selected)
        if self.macro_tile_select_id is not None:
            i = self.placable_tiles.index(self.macro_tile_select_id)
            y = (i // self.macro_tile_select_width) * (macro_height + 1)
            x = (i % self.macro_tile_select_width) * (macro_width + 1)
            self.elt_macro_select_rect = self.macro_canvas.create_rectangle(
                x + rect_margin, y + rect_margin, x + macro_width - rect_margin, y + macro_height - rect_margin,
                width=rect_width,
                outline=rect_colstr
             )
        
    def refresh_horizontal_lines(self):
        self.delete_elements(self.stage_canvas, self.elts_stage_horizontal_lines)
        self.elts_stage_horizontal_lines = []
        
        # top and bottom dark shadow lines
        for i in [0, 1, 3, 5, 7]:
            for top in [False, True]:
                y = i if top else level_height - i - 1
                self.elts_stage_horizontal_lines.append(
                    self.stage_canvas.create_line(
                        0, y, level_width, y,
                        fill="black"
                    )
                )
        
        # horizontal grid lines
        if self.show_lines:
            for i in range(constants.macro_rows_per_level - 1):
                y = level_height - macro_height * (i + 1)
                self.elts_stage_horizontal_lines.append(
                    self.stage_canvas.create_line(
                        0, y, level_width, y,
                        fill=gridcol
                    )
                )
        
    def refresh_row_lines(self, row_idx):
        self.delete_elements(self.stage_canvas, self.elts_row_lines[row_idx])
        self.elts_row_lines[row_idx] = []
        
        if self.show_lines and self.level is not None:
            y = level_height - macro_height * row_idx - macro_height
            macro_row = self.level.macro_rows[row_idx]
            seam = macro_row.seam
            seam_x = med_width * seam
            
            # place thin vertical lines
            for i in range(level_width // macro_width):
                x = (2 * i + (seam % 2)) * med_width
                if x < level_width and x != seam_x:
                    self.elts_row_lines[row_idx].append(
                        self.stage_canvas.create_line(x, y, x, y + macro_height, fill=gridcol)
                    )
            
            # place seam
            if seam != 0:
                self.elts_row_lines[row_idx].append(
                    self.stage_canvas.create_line(seam_x, y, seam_x, y + macro_height, fill=seamcol)
                )
        
    def refresh_row_tiles(self, row_idx):
        level = self.level
        if level is not None:
            micro_y = (constants.macro_rows_per_level - row_idx - 1) * (macro_height // micro_height)
            med_tile_rows = level.produce_med_tiles(self.hard, range(row_idx, row_idx + 1))
            
            for med_tile_row_idx in range(2):
                med_tile_row = med_tile_rows[med_tile_row_idx]
                for med_tile_col_idx in range(len(med_tile_row)):
                    med_tile_idx = med_tile_row[med_tile_col_idx]
                    med_tile = level.world.get_med_tile(med_tile_idx)
                    palette_idx = level.world.get_med_tile_palette_idx(med_tile_idx, self.hard)
                    for i in range(4):
                        micro_tile_idx = level.world.get_micro_tile(med_tile[i], self.hard)
                        x = med_tile_col_idx * 2 + (i % 2)
                        y = micro_y + (1 - med_tile_row_idx) * 2 + (i // 2)
                        img = self.micro_images[level.world_idx][palette_idx][micro_tile_idx][self.zoom]
                        self.stage_micro_dangerous[x][y] = micro_tile_idx in constants.dangerous_micro_tiles
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
                semi = (hard_only and not tile_dangerous)
                
                flip_idx = (4 if semi else 0) + (2 if obj.flipy else 0) + (1 if obj.flipx else 0)
                img = self.object_images[flip_idx][obj.gid]

                offset = obj_data["offset"] if "offset" in obj_data else (0, 0)
                offset = (offset[0] - (img.width() // 2), offset[1] + 8 - (img.height()))
                
                # add image
                self.elts_objects.append(
                    self.stage_canvas.create_image(
                        obj.x * micro_width + offset[0], obj.y * micro_height + offset[1],
                        image=img,
                        anchor=tk.NW
                    )
                )
                
                if not self.show_crosshairs:
                    continue
                
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
            for patch in self.level.hardmode_patches:
                macro_row = self.level.macro_rows[patch.y]
                seam = macro_row.seam
                for mirror in [False, True]:
                    for loop in [-1, 0, 1]:
                        y = (constants.macro_rows_per_level -  patch.y - 1) * macro_height
                        x = (((7 - patch.x) if mirror else patch.x) * 2 + seam) * med_width
                        x += level_width * loop
                        self.elts_patch_rects.append(
                            self.stage_canvas.create_rectangle(
                                x + margin, y + margin, x + macro_width - margin, y + macro_height - margin,
                                outline=patchcol
                            )
                        )
    
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
                str += "Tile: " + HB(self.macro_tile_select_id)
            
            while len(str) < 0x26:
                str += " "
                
            # space remaining
            max = self.level.total_length
            ps_ = self.level.produce_patches_stream()
            os_ = self.level.produce_objects_stream()
            
            bits_used = int(ps_.length_bytes() * 8 + os_.length_bits())
            if max is None:
                bytes_used = int((bits_used) / 8)
                bits_used = int(bits_used % 8)
                str += "Used: " + HB(bytes_used) + "." + HB(bits_used * 2)[1] + " bytes"
            else:
                max = abs(max) # paranoia
                if bits_used > max * 8:
                    color="red"
                    bits_o = bits_used - max * 8
                    bytes_o = int((bits_o) / 8)
                    bits_o = int(bits_o % 8)
                    str += "OVERLIMIT: " + HB(bytes_o) + "." + HB(bits_o * 2)[1] + " past " + HB(max) + " bytes"
                else:
                    bits_r = max * 8 - bits_used
                    bytes_r = int((bits_r) / 8)
                    bits_r = int(bits_r % 8)
                    str += "Available: " + HB(bytes_r) + "." + HB(bits_r * 2)[1] + " of " + HB(max) + " bytes"
            
        self.label.configure(text=str, fg=color, anchor=tk.W, font=("TkFixedFont", 7, "normal"))
    
    def run(self):
        self.window.mainloop()