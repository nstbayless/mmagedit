# exports levels as images

import constants
from util import *
import os

available = True

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError as e:
    available = False
    raise e
    
def chr_to_img(data, chr_address, img, palette, offset=(0, 0), flipx=False, flipy=False, sprite=False, semi=False):
    for y in range(8):
        l = data.read_byte(data.chr_to_rom(chr_address + y))
        u = data.read_byte(data.chr_to_rom(chr_address + y + 8))
        for x in range(8):
            bl = (l >> (7 - x)) & 0x1
            bu = (u >> (7 - x)) & 0x1
            
            col_idx = (bu << 1) | (bl)
            col = palette[col_idx]
            colrgb = constants.palette_rgb[col]
            
            # sprite transparency
            if sprite:
                colrgb = (colrgb[0], colrgb[1], colrgb[2], 0xff)
                if col == 0xf:
                    colrgb = (0, 0, 0, 0)
                elif semi:
                    colrgb = (colrgb[0], colrgb[1], min(0xff, colrgb[2] + 0x40), 0x50)
            
            img.putpixel((7 - x + offset[0] if flipx else x + offset[0], (7 - y if flipy else y) + offset[1]), colrgb)

def produce_chr_sheet(data):
    img = Image.new('RGB', (256, 128))
    for b in range(2):
        palette = [constants.bg_palette, constants.sprite_palette][b]
        for y in range(16):
            for x in range(16):
                address = x * 0x10 + y * 0x100 + b * 0x1000
                chr_to_img(data, address, img, palette, (x * 0x8 + b * 0x80, y * 0x8))
    return img

def produce_object_images(data, semi=False):
    object_images = []
    for object_data in constants.object_data:
        if "chr" in object_data:
            chr = object_data["chr"]
            offset = object_data["offset"] if "offset" in object_data else (0, 0)
            height = 8 * len(chr)
            width = 8 * len(chr[0])
            img = Image.new('RGBA', (width, height))
            
            palette = constants.greyscale_palette
            if "palette" in object_data:
                palette = constants.sprite_palettes[object_data["palette"]]
            
            for i in range(len(chr)):
                for j in range(len(chr[i])):
                    chr_idx = chr[i][j]
                    x = 8 * j
                    y = 8 * i
                    
                    chr_address = 0x10 * (chr_idx & 0xff)
                    
                    is_sprite = chr_idx & 0x100 == 0
                    if is_sprite:
                        chr_address += 0x1000
                    flipx = chr_idx & 0x200 != 0
                    flipy = chr_idx & 0x400 != 0
                    
                    chr_to_img(data, chr_address, img, palette, (x, y), flipx, flipy, True, semi)
            
            img._mm_offset = offset
            img._mm_hard = object_data["hard"] if "hard" in object_data else False
            object_images.append(img)
        else:
            object_images.append(None)
    
    # make the list length 0xff to fit any possible object gid.        
    while len(object_images) < 0x100:
        object_images.append(None)
    
    return object_images
    
def produce_micro_tile_images(data, world, hard=False):
    minitile_images = []
    for palette_idx in range(4):
        minitile_images_paletted = []
        for i in range(0x100):
            palette = world.palettes[palette_idx + (4 if hard else 0)] if world is not None else constants.bg_palettes[palette_idx]
            img = Image.new('RGB', (8, 8), color = 'black')
            if palette is not None:
                for x in range(8):
                    for y in range(8):
                        col_idx = data.micro_tiles[i][x][y]
                        rgb = constants.palette_rgb[palette[col_idx]]
                        
                        # hidden block effect
                        if world is not None and i in constants.hidden_micro_tiles and palette_idx in world.hidden_tile_palettes():
                            if (x + y) % 2 == 1:
                                rgb = constants.hidden_colour
                        
                        # dangerous block effect
                        if i in constants.dangerous_micro_tiles:
                            if (x + y) % 2 == 1:
                                rgb = (0xff, 0x30, 0x38)
                                
                        img.putpixel((x, y), rgb)
            minitile_images_paletted.append(img)
        minitile_images.append(minitile_images_paletted)
    return minitile_images

def produce_title_screen(data):
    img = Image.new('RGB', (256, 224), color = 'black')
    for i in range(0x20, len(data.title_screen.table) + 0x20):
        x = (i % 0x20) * 0x8
        y = (i // 0x20) * 0x8
        tile = data.title_screen.table[i - 0x20]
        
        palette_i = (x // 0x20) % 8 + ((y + 0x8) // 0x20) * 8 - 0x1d
        palette_sub_i = ((x // 0x10) % 2) + 2 * (((y + 0x8) // 0x10) % 2)
        palette_idx = 0 if palette_i >= len(data.title_screen.palette_idxs) or palette_i < 0 else (data.title_screen.palette_idxs[palette_i] >> (2 * (palette_sub_i))) & 0x3
        
        # we remap the 0 palette because it fades in, so the initial value would be invisible.
        palette = constants.title_red_palette if palette_idx == 0 else data.title_screen.palettes[palette_idx]
        
        chr_to_img(data, tile * 0x10, img, palette, (x, y))
    return img

def export_images(data, path="."):
    if not os.path.exists(path):
        os.path.makedirs(path)
    
    # export chr
    outfile = "mm-chr.png"
    print("exporting", outfile)
    outfile = os.path.join(path, outfile)
    chr_image = produce_chr_sheet(data)
    chr_image.save(outfile)

    # export title
    outfile = "mm-title.png"
    print("exporting", outfile)
    outfile = os.path.join(path, outfile)
    produce_title_screen(data).save(outfile)

    # export levels
    for level in data.levels:
        for hard in [False, True]:
            outfile = "mm-" + str(level.world_idx + 1) + "-" + str(level.world_sublevel + 1) + ("h" if hard else "") + ".png"
            print("exporting " + outfile + " ...")
            outfile = os.path.join(path, outfile)
            
            # create tiles per-palette per-level (could be optimized to per-world)
            minitile_images = produce_micro_tile_images(data, level.world, hard)
            
            # create object data images
            object_images = produce_object_images(data)
                
            w = 256
            h = 32 * constants.macro_rows_per_level
            img = Image.new('RGB', (w, h), color = 'black')
            draw = ImageDraw.Draw(img)
            
            tile_rows, macro_tile_idxs = level.produce_med_tiles(hard)
            
            y = h
            
            dangerous_tiles = [[False for y in range(constants.macro_rows_per_level * 4)] for x in range(0x20)]
            
            for row in tile_rows:
                x = -16
                y -= 16
                for medtile_idx in row:
                    x += 16
                    offsets = [(0, 0), (8, 0), (0, 8), (8, 8)]
                    medtile = level.world.get_med_tile(medtile_idx)
                    palette_idx = level.world.get_med_tile_palette_idx(medtile_idx, hard) % 4
                    if palette_idx is None:
                        continue
                    # draw subtiles
                    for i in range(4):
                        microtile_idx = level.world.get_micro_tile(medtile[i], hard)
                        
                        offx = offsets[i][0]
                        offy = offsets[i][1]
                        _x = x + offx
                        _y = y + offy
                        
                        if (microtile_idx in constants.dangerous_micro_tiles):
                            dangerous_tiles[_x // 8][_y // 8] = True
                        else:
                            img.paste(minitile_images[palette_idx][microtile_idx], (_x, _y))
                    
            # objects
            for obj in level.objects:
                x = obj.x * 8 - 4
                y = obj.y * 8
                text = hb(obj.gid)
                objimg = object_images[obj.gid] if obj.gid < len(object_images) else None
                
                if obj.flipx and obj.flipy:
                    text += "+"
                elif obj.flipx:
                    text += "-"
                elif obj.flipy:
                    text += "|"
                if objimg is None:
                    draw.text((x, y), text, fill="white" if obj.name[0:4] != "unk-" else "red")
                else:
                    x += 4 - objimg.width//2 + objimg._mm_offset[0]
                    y += 8 - objimg.height + objimg._mm_offset[1]
                    if not objimg._mm_hard or dangerous_tiles[obj.x][obj.y]:
                        paste_image = objimg
                        if obj.flipx:
                            paste_image = ImageOps.mirror(paste_image)
                        if obj.flipy:
                            paste_image = ImageOps.flip(paste_image)
                        img.paste(paste_image, (x, y))
            
            img.save(outfile)