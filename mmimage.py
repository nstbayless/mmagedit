# exports levels as images

import constants
from util import *
import os

available = True

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    available = False
    
def chr_to_img(data, chr_address, img, palette, offset=(0, 0), flipx=False, sprite=False, semi=False):
    for y in range(8):
        l = data.read_byte(data.chr_to_rom(chr_address + y))
        u = data.read_byte(data.chr_to_rom(chr_address + y + 8))
        for x in range(8):
            bl = (l >> (7 - x)) & 0x1
            bu = (u >> (7 - x)) & 0x1
            
            col_idx = (bl << 1) | (bu)
            col = palette[col_idx]
            colrgb = constants.palette_rgb[col]
            
            # sprite transparency
            if sprite:
                colrgb = (colrgb[0], colrgb[1], colrgb[2], 0xff)
                if col == 0xf:
                    colrgb = (0, 0, 0, 0)
                elif semi:
                    colrgb = (colrgb[0], colrgb[1], min(0xff, colrgb[2] + 0x40), 0x50)
            
            img.putpixel((7 - x + offset[0] if flipx else x + offset[0], y + offset[1]), colrgb)
    
def produce_object_images(data, semi=False):
    object_images = []
    for object_data in constants.object_data:
        if "chr" in object_data:
            chr = object_data["chr"]
            offset = object_data["offset"] if "offset" in object_data else (0, 0)
            height = 8 * len(chr)
            width = 8 * len(chr[0])
            img = Image.new('RGBA', (width, height))
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
                    
                    chr_to_img(data, chr_address, img, [0x0f, 0x0, 0x10, 0x20], (x, y), flipx, True, semi)
            
            img._mm_offset = offset
            img._mm_hard = object_data["hard"] if "hard" in object_data else False
            object_images.append(img)
        else:
            object_images.append(None)
    
    # make the list length 0xff to fit any possible object gid.        
    while len(object_images) < 0x100:
        object_images.append(None)
    
    return object_images
    
def produce_micro_tile_images(world, hard=False):
    minitile_images = []
    for palette_idx in range(4):
        minitile_images_paletted = []
        for i in range(0x100):
            palette = world.palettes[palette_idx + (4 if hard else 0)]
            img = Image.new('RGB', (8, 8), color = 'black')
            if palette is not None:
                for x in range(8):
                    for y in range(8):
                        col_idx = world.data.micro_tiles[i][x][y]
                        rgb = constants.palette_rgb[palette[col_idx]]
                        
                        # hidden block effect
                        if i in constants.hidden_micro_tiles and palette_idx == 1:
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
    
def export_images(data, path="."):
    if not os.path.exists(path):
        os.path.makedirs(path)
    for level in data.levels:
        for hard in [False, True]:
            outfile = "mm-" + str(level.world_idx + 1) + "-" + str(level.world_sublevel + 1) + ("h" if hard else "") + ".png"
            print("exporting " + outfile + " ...")
            outfile = os.path.join(path, outfile)
            
            # create tiles per-palette per-level (could be optimized to per-world)
            minitile_images = produce_micro_tile_images(level.world, hard)
            
            # create object data images
            object_images = produce_object_images(data)
                
            w = 256
            h = 32 * constants.macro_rows_per_level
            img = Image.new('RGB', (w, h), color = 'black')
            draw = ImageDraw.Draw(img)
            
            tile_rows = level.produce_med_tiles(hard)
            
            y = h
            
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
                    if not objimg._mm_hard or hard:
                        paste_image = objimg
                        if obj.flipx:
                            paste_image = ImageOps.mirror(paste_image)
                        if obj.flipy:
                            paste_image = ImageOps.flip(paste_image)
                        img.paste(paste_image, (x, y))
            
            img.save(outfile)