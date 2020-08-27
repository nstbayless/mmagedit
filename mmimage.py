# exports levels as images

import constants
from util import *

available = True

try:
    from PIL import Image, ImageDraw
except ImportError:
    available = False
    
def export_images(data):
    for level in data.levels:
        for hard in [False, True]:
            outfile = "mm-" + str(level.world_idx + 1) + "-" + str(level.world_sublevel + 1) + ("h" if hard else "") + ".png"
            print("exporting " + outfile + " ...")
            
            # create tiles per-palette per-level (could be optimized to per-world)
            minitile_images = []
            for palette_idx in range(4):
                _palette_idx = palette_idx + (4 if hard else 0)
                
                # hard mode uses this weird reshuffling of palette indices
                # although some palettes do not appear, all *are* loaded into ppu ram.
                if _palette_idx == 6:
                    _palette_idx = 4
                if _palette_idx == 7 and level.world_idx == 0:
                    _palette_idx = 6
                    
                palette = level.world.palettes[_palette_idx]
                minitile_images_paletted = []
                for i in range(0x100):
                    img = Image.new('RGB', (8, 8), color = 'black')
                    for x in range(8):
                        for y in range(8):
                            col_idx = data.micro_tiles[i][x][y]
                            img.putpixel((x, y), constants.palette_rgb[palette[col_idx]])
                    minitile_images_paletted.append(img)
                minitile_images.append(minitile_images_paletted)
                
            w = 256
            h = 32 * constants.macro_rows_per_level
            img = Image.new('RGB', (w, h), color = 'black')
            draw = ImageDraw.Draw(img)
            
            tile_rows = level.produce_med_tiles(hard)
            
            y = h
            
            for row in tile_rows:
                x = 0
                y -= 16
                for medtile_idx in row:
                    offsets = [(0, 0), (8, 0), (0, 8), (8, 8)]
                    medtile = level.world.get_med_tile(medtile_idx)
                    palette_idx = level.world.get_med_tile_palette_idx(medtile_idx)
                    if palette_idx is None:
                        continue
                    # draw subtiles
                    for i in range(4):
                        minitile_idx = medtile[i]
                        offx = offsets[i][0]
                        offy = offsets[i][1]
                        _x = x + offx
                        _y = y + offy
                        img.paste(minitile_images[palette_idx][minitile_idx], (_x, _y))
                        
                    x += 16
                    
            # objects
            for obj in level.objects:
                x = obj.x * 8 - 4
                y = obj.y * 8
                text = hb(obj.gid)
                if obj.flipx and obj.flipy:
                    text += "+"
                elif obj.flipx:
                    text += "-"
                elif obj.flipy:
                    text += "|"
                draw.text((x, y), text, fill="white" if obj.name[0:4] != "unk-" else "red")
            
            img.save(outfile)