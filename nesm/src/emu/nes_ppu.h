#ifndef _PPU_H_
#define _PPU_H_

#include <memory.h>
#include <stdint.h>
#include <assert.h>

#define SCANLINE_WIDTH          341
#define TOTAL_SCANLINES         262

#define VBLANK_SCANLINES        20
#define PRE_RENDER_SCANLINE     TOTAL_SCANLINES - 1
#define FIRST_RENDER_SCANLINE   0
#define LAST_RENDER_SCANLINE    TOTAL_SCANLINES - VBLANK_SCANLINES - 2
#define VBLANK_BEGIN_SCANLINE   LAST_RENDER_SCANLINE + 1

enum NES_PPU_REG_RW_MODE 
{ 
    NES_PPU_REG_RW_MODE_NONE,
    NES_PPU_REG_RW_MODE_READ,
    NES_PPU_REG_RW_MODE_WRITE
};

#define NES_PPU_CTRL_REG_ID         0
#define NES_PPU_MASK_REG_ID         1
#define NES_PPU_STATUS_REG_ID       2
#define NES_PPU_OAM_ADDR_REG_ID     3
#define NES_PPU_OAM_DATA_REG_ID     4
#define NES_PPU_SCROLL_REG_ID       5
#define NES_PPU_ADDR_REG_ID         6
#define NES_PPU_DATA_REG_ID         7

typedef union nes_ppu_ctrl_reg
{
    struct
    {
        uint8_t base_nametable_addr         : 2;
        uint8_t vram_rw_increment_step      : 1;
        uint8_t sprite_pattern_table_addr   : 1;
        uint8_t bgr_pattern_table_addr      : 1;
        uint8_t sprite_size                 : 1;
        uint8_t master_slave_select         : 1;
        uint8_t generate_nmi                : 1;
    };
    uint8_t b;
} nes_ppu_ctrl_reg;

typedef enum nes_ppu_render_mask
{
    NES_PPU_RENDER_MASK_GRAYSCALE           = 0x01,
    NES_PPU_RENDER_MASK_LEFTMOST_BACKGROUND = 0x02,
    NES_PPU_RENDER_MASK_LEFTMOST_SPRITES    = 0x04,
    NES_PPU_RENDER_MASK_BACKGROUND          = 0x08,
    NES_PPU_RENDER_MASK_SPRITES             = 0x10,
    NES_PPU_RENDER_MASK_EMPHASIZE_RED       = 0x20,
    NES_PPU_RENDER_MASK_EMPHASIZE_GREEN     = 0x40,
    NES_PPU_RENDER_MASK_EMPHASIZE_BLUE      = 0x80,

    NES_PPU_RENDER_MASK_RENDER  = NES_PPU_RENDER_MASK_BACKGROUND | NES_PPU_RENDER_MASK_SPRITES
} nes_ppu_render_mask;

typedef union nes_ppu_status_reg
{
    struct
    {
        uint8_t low : 5;
        uint8_t sprite_overflow : 1;
        uint8_t sprite_0_hit : 1;
        uint8_t vblank_started : 1; 
    };
    uint8_t b;
} nes_ppu_status_reg;

typedef struct nes_ppu_vaddr
{
    uint16_t coarse_x : 5;
    uint16_t coarse_y : 5;
    uint16_t nametable : 2;
    uint16_t fine_y : 3;
    uint16_t unused : 1;
} nes_ppu_vaddr;

typedef union nes_ppu_sprite_attrib
{
   struct
   {
       uint8_t palette : 2;
       uint8_t unused : 3;
       uint8_t priority : 1;
       uint8_t flip_x : 1;
       uint8_t flip_y : 1;
   };
   uint8_t b;
} nes_ppu_sprite_attrib;

typedef struct nes_ppu_oam_entry
{
   uint8_t                  position_y;
   uint8_t                  tile_index;
   nes_ppu_sprite_attrib    attribute;
   uint8_t                  position_x;
} nes_ppu_oam_entry;

typedef struct nes_ppu
{
    uint32_t dot;
    uint32_t scanline;

    uint8_t reg_rw_mode;
    uint8_t reg_data;
    uint8_t reg_addr : 3;
    uint8_t r : 1;
    uint8_t w : 1;

    uint8_t color_out;

    uint8_t vbl : 1;

    unsigned is_even_frame;

    union
    {
        nes_ppu_vaddr   v_addr;
        uint16_t        v_addr_reg;
    };

    union
    {
        nes_ppu_vaddr   t_addr;
        uint16_t        t_addr_reg;
    };

    int      write_toggle;
    uint8_t  fine_x;

    uint8_t  tile_value;
    uint8_t  palette_attribute;
    uint8_t  bitplane_slice_low;

    uint16_t bg_shift_low;
    uint16_t bg_shift_high;
    uint16_t attr_shift_low;
    uint16_t attr_shift_high;

    nes_ppu_sprite_attrib   sprite_attributes[8];
    uint8_t                 sprite_x_positions[8];
    uint8_t                 sprite_shift_low[8];
    uint8_t                 sprite_shift_high[8];

    uint8_t         eval_oam_free_index;
    uint8_t         eval_oam_m;
    uint8_t         eval_oam_n;
    uint8_t         eval_oam_entry[4];
    uint8_t         eval_oam_has_sprite_zero;

    uint8_t         sprite_0_test;
    uint8_t         cpu_read_buffer;
    int             update_cpu_read_buffer;

    int             pre_vblank;

    nes_ppu_ctrl_reg     ctrl;
    nes_ppu_render_mask  render_mask;
    nes_ppu_status_reg   status;
    uint8_t              oam_address;
    uint16_t             vram_address;
    uint8_t              vram_data;

    union oam_memory
    {
        nes_ppu_oam_entry   entries[64];
        uint8_t             bytes[64*4];
    } primary_oam;

    union oam_memory2
    {
        nes_ppu_oam_entry   entries[8];
        uint8_t             bytes[8*4];
    } secondary_oam;

    uint8_t         palettes[32];
} nes_ppu;

#define _NES_PPU_IS_RENDERING(ppu) ((ppu->scanline < LAST_RENDER_SCANLINE || ppu->scanline == PRE_RENDER_SCANLINE) &&\
                               (ppu->render_mask & NES_PPU_RENDER_MASK_RENDER))

#define _NES_PPU_COLOR_BLACK 15

void nes_ppu_reset(nes_ppu* ppu)
{
    uint8_t default_palette[] = {
        0x09,0x01,0x00,0x01,0x00,0x02,0x02,0x0D,0x08,0x10,0x08,0x24,0x00,0x00,0x04,0x2C,
        0x09,0x01,0x34,0x03,0x00,0x04,0x00,0x14,0x08,0x3A,0x00,0x02,0x00,0x20,0x2C,0x08
    };
    memset(ppu, 0, sizeof(nes_ppu));
    memcpy(ppu->palettes, default_palette, sizeof(default_palette));
    ppu->scanline = VBLANK_BEGIN_SCANLINE;
    ppu->color_out = _NES_PPU_COLOR_BLACK;
}

void nes_ppu_execute(nes_ppu* __restrict ppu)
{
    // Update dot and scanline
    if (++ppu->dot >= SCANLINE_WIDTH)
    {
        ppu->scanline = (ppu->scanline + 1) % TOTAL_SCANLINES;
        ppu->dot = 0;
    }

    // I/O:

    if (ppu->r | ppu->w)
    {
        if (!_NES_PPU_IS_RENDERING(ppu))
            ppu->vram_address += ppu->ctrl.vram_rw_increment_step ? 32 : 1;

        if (ppu->update_cpu_read_buffer)
        {
            ppu->cpu_read_buffer = ppu->vram_data;
            ppu->update_cpu_read_buffer = 0;
        }
        ppu->r = ppu->w = 0;
    }

    if (ppu->reg_rw_mode)
    {
        switch(ppu->reg_addr)
        {
            case NES_PPU_CTRL_REG_ID:   // write-only 
            {
                if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)
                {
                    ppu->ctrl.b = ppu->reg_data;
                    ppu->t_addr.nametable = ppu->ctrl.base_nametable_addr;
                }
            }
            break;
            case NES_PPU_MASK_REG_ID:   // write-only
            {
                if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)  ppu->render_mask = (nes_ppu_render_mask)ppu->reg_data;
            }
            break;
            case NES_PPU_STATUS_REG_ID: // read-only
            {
                if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_READ)
                {
                    ppu->reg_data = ppu->status.b;
                    ppu->status.vblank_started = 0;
                    ppu->write_toggle = 0;
                    ppu->pre_vblank = 0;
                }
            }
            break;
            case NES_PPU_OAM_ADDR_REG_ID:
            {
                if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)  ppu->oam_address = ppu->reg_data;
                else ppu->reg_data = ppu->oam_address;
            }
            break;
            case NES_PPU_OAM_DATA_REG_ID:
            {
                if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)  ppu->primary_oam.bytes[ppu->oam_address++] = ppu->reg_data;
                else ppu->reg_data = ppu->primary_oam.bytes[ppu->oam_address];
            }
            break;
            case NES_PPU_SCROLL_REG_ID: // write-only
            {
                if(ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)
                {
                    if(ppu->write_toggle)
                    {
                        ppu->t_addr.coarse_y = ppu->reg_data >> 3;
                        ppu->t_addr.fine_y = ppu->reg_data & 7;
                    }
                    else
                    {
                        ppu->t_addr.coarse_x = ppu->reg_data >> 3;
                        ppu->fine_x = ppu->reg_data & 7;
                    }
                    ppu->write_toggle = !ppu->write_toggle; 
                }
            }
            break;
            case NES_PPU_ADDR_REG_ID: // write-only
            {
                if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)
                {
                    if (ppu->write_toggle)
                    {
                        ppu->t_addr_reg = (ppu->t_addr_reg & 0xFF00) | ppu->reg_data;
                        ppu->v_addr_reg = ppu->t_addr_reg;
                        ppu->vram_address = ppu->t_addr_reg;
                    }
                    else
                    {
                        ppu->t_addr_reg = ((ppu->reg_data & 0x7F) << 8) | (ppu->vram_address & 0x00FF);
                    }
                    ppu->write_toggle = !ppu->write_toggle;
                }
            }
            break;
            case NES_PPU_DATA_REG_ID: // read-write
            {
                if (ppu->vram_address >= 0x3F00 && ppu->vram_address <= 0x3FFF)
                {
                    uint8_t palette_index = ppu->vram_address & 0x1F;
                    if ((palette_index & 0x13) == 0x10)
                        palette_index &= ~0x10;

                    if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)
                    {
                        ppu->palettes[palette_index] = ppu->reg_data;

                        if (!_NES_PPU_IS_RENDERING(ppu))
                            ppu->vram_address += ppu->ctrl.vram_rw_increment_step ? 32 : 1;
                    }
                    else
                    {
                        ppu->r = 1;
                        ppu->reg_data = ppu->palettes[palette_index];
                        ppu->update_cpu_read_buffer = 1;
                    }
                }
                else
                {
                    if (ppu->reg_rw_mode == NES_PPU_REG_RW_MODE_WRITE)
                    {
                        ppu->w = 1;
                        ppu->vram_data = ppu->reg_data;
                    }
                    else
                    {
                        ppu->r = 1;
                        ppu->reg_data = ppu->cpu_read_buffer;
                        ppu->update_cpu_read_buffer = 1;
                    }
                }

                // If rendering immediately increment X and Y scroll
                if (_NES_PPU_IS_RENDERING(ppu))
                {
                    if (ppu->v_addr.coarse_x == 31)
                    {
                        ppu->v_addr.nametable ^= 1;
                        ppu->v_addr.coarse_x = 0;
                    }
                    else
                    {
                        ppu->v_addr.coarse_x++;
                    }

                    if (ppu->v_addr.fine_y < 7)
                    {
                        ppu->v_addr.fine_y++;
                    }
                    else
                    {
                        ppu->v_addr.fine_y = 0;
                        if (ppu->v_addr.coarse_y == 29)
                        {
                            ppu->v_addr.coarse_y = 0;
                            ppu->v_addr.nametable ^= 2;
                        }
                        else if (ppu->v_addr.coarse_y == 31)
                        {
                            ppu->v_addr.coarse_y = 0;
                        }
                        else
                        {
                            ppu->v_addr.coarse_y++;
                        }
                    }
                }
            }
            break;
        }

        ppu->reg_rw_mode = NES_PPU_REG_RW_MODE_NONE;
    }

    // Rendering
  
    if (ppu->scanline == PRE_RENDER_SCANLINE && ppu->dot == 1)
    {
        // Clear VBlank, Sprite 0 Hit, Sprite overflow and toggle odd/even flag
        ppu->status.vblank_started = 0;
        ppu->status.sprite_0_hit = 0;
        ppu->status.sprite_overflow = 0;
        ppu->is_even_frame = !ppu->is_even_frame;
    }
    else if ((ppu->scanline < LAST_RENDER_SCANLINE || ppu->scanline == PRE_RENDER_SCANLINE) && (ppu->render_mask & NES_PPU_RENDER_MASK_RENDER))
    {
        const unsigned sprite_height = 8 << ppu->ctrl.sprite_size;

        // Draw pixel
        if (ppu->dot <= 257)
        {
            unsigned bg_pattern = 0;
            uint32_t palette_index = 0;
            
            if (ppu->render_mask & NES_PPU_RENDER_MASK_BACKGROUND)
            {
                unsigned bg_shift_x = 15 - ppu->fine_x;
                bg_pattern = ((ppu->bg_shift_low  >> (bg_shift_x))     & 0x01) |
                             ((ppu->bg_shift_high >> (bg_shift_x - 1)) & 0x02);

                if (bg_pattern)
                {
                    palette_index = (bg_pattern |
                                ((ppu->attr_shift_low  >> (bg_shift_x - 2)) & 0x04) | 
                                ((ppu->attr_shift_high >> (bg_shift_x - 3)) & 0x08)) & 0x0F;
                }
            }

            if ((ppu->render_mask & NES_PPU_RENDER_MASK_SPRITES))
            {
                unsigned x = ppu->dot - 2;

                for (int i = 0; i < 8; ++i)
                {
                    if (x >= ppu->sprite_x_positions[i] && (x < ppu->sprite_x_positions[i] + 8))
                    {
                        unsigned sprite_shift = 7 - (x - ppu->sprite_x_positions[i]) & 7;
                        unsigned pattern = (((ppu->sprite_shift_high[i] >> sprite_shift) << 1) & 2) |
                                           ((ppu->sprite_shift_low[i] >> sprite_shift) & 1);

                        
                        if (pattern)
                        {
                            if (i == 0 && ppu->sprite_0_test)
                                ppu->status.sprite_0_hit = ppu->primary_oam.entries[0].position_y < 240;

                            if (bg_pattern == 0 || (ppu->sprite_attributes[i].priority == 0))
                                palette_index = pattern | (ppu->sprite_attributes[i].palette << 2) | 0x10;

                            break;
                        }
                    }
                }
            }

            ppu->color_out = ppu->palettes[palette_index];
        }
        else
        {
            ppu->color_out = _NES_PPU_COLOR_BLACK;
        }

        // Shift background shift registers
        if ((ppu->dot >= 2 && ppu->dot <= 257) || (ppu->dot >= 322 && ppu->dot <= 337))
        {
            ppu->bg_shift_high <<= 1;
            ppu->bg_shift_low <<= 1;
            ppu->attr_shift_high <<= 1;
            ppu->attr_shift_low <<= 1;
       }

        if (ppu->dot && (ppu->dot <= 256 || (ppu->dot > 320 && ppu->dot <= 336)))
        {
            // Fetch background data and update shift registers
            switch(ppu->dot & 7)
            {
                case 1:
                    // Reload shift registers
                    ppu->bg_shift_high |= ppu->vram_data;
                    ppu->bg_shift_low |= ppu->bitplane_slice_low;
                    ppu->attr_shift_low |= (ppu->palette_attribute & 1) * 0xFF;
                    ppu->attr_shift_high |= ((ppu->palette_attribute >> 1) & 1) * 0xFF;

                    // Fetch tile from nametable
                    ppu->r = 1;
                    ppu->vram_address = 0x2000 | (ppu->v_addr_reg & 0x0FFF);
                    break;
                case 2:
                    ppu->tile_value = ppu->vram_data;
                    break;
                case 3:
                    // Fetch tile attributes
                    ppu->r = 1;
                    ppu->vram_address = 0x23C0 | (ppu->v_addr_reg & 0x0C00) | ((ppu->v_addr_reg >> 4) & 0x38) | ((ppu->v_addr_reg >> 2) & 0x07);
                    break;
                case 4:
                    ppu->palette_attribute = ppu->vram_data;
                    if (ppu->v_addr.coarse_y & 2) ppu->palette_attribute >>= 4;
                    if (ppu->v_addr.coarse_x & 2) ppu->palette_attribute >>= 2;
                    break;
                case 5:
                    // Fetch low bitplane
                    ppu->r = 1;
                    ppu->vram_address = (ppu->ctrl.bgr_pattern_table_addr << 12) | (ppu->tile_value << 4) | ppu->v_addr.fine_y;
                    break; 
                case 6:
                    ppu->bitplane_slice_low = ppu->vram_data;
                    break;
                case 7:
                    // Fetch high bitplane
                    ppu->r = 1;
                    ppu->vram_address = (ppu->ctrl.bgr_pattern_table_addr << 12) | (ppu->tile_value << 4) | 8 | ppu->v_addr.fine_y;
                    break;
                case 0:
                    // Increment horizontal scrolling
                    if (ppu->v_addr.coarse_x == 31)
                    {
                        ppu->v_addr.nametable ^= 1;
                        ppu->v_addr.coarse_x = 0;
                    }
                    else
                    {
                        ppu->v_addr.coarse_x++;
                    }
            
                    // Increment vertical scrolling
                    if (ppu->dot == 256)
                    {
                        if (ppu->v_addr.fine_y < 7)
                        {
                            ppu->v_addr.fine_y++;
                        }
                        else
                        {
                            ppu->v_addr.fine_y = 0;
                            if (ppu->v_addr.coarse_y == 29)
                            {
                                ppu->v_addr.coarse_y = 0;
                                ppu->v_addr.nametable ^= 2;
                            }
                            else if (ppu->v_addr.coarse_y == 31)
                            {
                                ppu->v_addr.coarse_y = 0;
                            }
                            else
                            {
                                ppu->v_addr.coarse_y++;
                            }
                        }
                    }
                    break;
            }

            // Reset OAM counters at dot 1 of each scanline
            if (ppu->dot == 1)
            {
                ppu->eval_oam_free_index = 0;
                ppu->eval_oam_m = 0;
                ppu->eval_oam_n = 0;
                ppu->eval_oam_has_sprite_zero = 0;
            }

            // Sprite evaluation
            if (ppu->scanline >= FIRST_RENDER_SCANLINE && ppu->dot < 257)
            {
                if (ppu->dot < 65)
                {
                    // clear secondary oam 
                    ppu->secondary_oam.bytes[(ppu->dot - 1) >> 1] = 0xFF;
                }
                else if (ppu->dot & 1)
                {
                    // read next entry
                    for (int i = 0; i < 4; ++i)
                        ppu->eval_oam_entry[ppu->eval_oam_m++ & 3]  = ppu->primary_oam.bytes[ppu->oam_address++];
                }
                else
                {
                    if (ppu->eval_oam_n >= ppu->eval_oam_free_index)
                    {
                        int has_free_slots = ppu->eval_oam_free_index < 8;

                        if (has_free_slots)
                            ppu->secondary_oam.entries[ppu->eval_oam_free_index].position_y = ppu->eval_oam_entry[0];

                        if (ppu->scanline >= ppu->eval_oam_entry[0] && ppu->scanline < (ppu->eval_oam_entry[0] + sprite_height))
                        {
                            if (has_free_slots)
                            {
                                if (ppu->oam_address == 4)
                                    ppu->eval_oam_has_sprite_zero = 1;

                                // add primary oam to seconday oam if it's in scanline range
                                memcpy(ppu->secondary_oam.entries + ppu->eval_oam_free_index, ppu->eval_oam_entry, sizeof(nes_ppu_oam_entry));
                                ppu->eval_oam_free_index++;
                            }
                            else
                            {
                                ppu->status.sprite_overflow = 1;
                            }
                        }
                        else if (!has_free_slots)
                        {
                            // emulate hardware bug
                            ppu->eval_oam_m++;
                        }
                    }

                    ppu->eval_oam_n = (ppu->eval_oam_n + 1) & 0x3F;
                }
            }
        }
        else
        {
            // Update horizontal scrolling component from T
            if (ppu->dot == 257)
                ppu->v_addr_reg = (ppu->v_addr_reg & ~0x041F) | (ppu->t_addr_reg & 0x041F);

            // Fetch sprite data
            if ((ppu->render_mask & NES_PPU_RENDER_MASK_SPRITES) && ppu->dot && ppu->dot <= 320)
            {
                uint32_t            current_oam_index = (ppu->dot - 257) >> 3;
                nes_ppu_oam_entry   current_oam = ppu->secondary_oam.entries[current_oam_index];

                ppu->oam_address = 0;
                ppu->sprite_0_test = ppu->eval_oam_has_sprite_zero;

                switch(ppu->dot & 7)
                {
                    case 1: 
                        ppu->sprite_attributes[current_oam_index] = current_oam.attribute;
                        break;
                    case 2:
                        ppu->sprite_x_positions[current_oam_index] = current_oam.position_x;
                        break;
                    case 3:
                        break;
                    case 4:
                        break;
                    case 5:
                        {
                            uint16_t pattern_table = ppu->ctrl.sprite_pattern_table_addr;
                            unsigned tile_index = current_oam.tile_index;
                            if (ppu->ctrl.sprite_size)
                            {
                                pattern_table = current_oam.tile_index & 1;
                                tile_index = tile_index & ~1;
                            }

                            unsigned pos_y = ppu->scanline - current_oam.position_y;

                            if (current_oam.attribute.flip_y)
                                pos_y = sprite_height - pos_y - 1;

                            pos_y += pos_y & 8;
                            
                            ppu->r = 1;
                            ppu->vram_address = (pattern_table << 12) | (tile_index << 4) | pos_y;
                        }
                        break; 
                    case 6:
                        if (current_oam.attribute.flip_x)
                            ppu->sprite_shift_low[current_oam_index] = ((ppu->vram_data * 0x80200802ULL) & 0x0884422110ULL) * 0x0101010101ULL >> 32;
                        else
                            ppu->sprite_shift_low[current_oam_index] = ppu->vram_data;
                        break;
                    case 7:
                        {
                            uint16_t pattern_table = ppu->ctrl.sprite_pattern_table_addr;
                            unsigned tile_index = current_oam.tile_index;
                            if (ppu->ctrl.sprite_size)
                            {
                                pattern_table = current_oam.tile_index & 1;
                                tile_index = tile_index & ~1;
                            }

                            unsigned pos_y = ppu->scanline - current_oam.position_y;

                            if (current_oam.attribute.flip_y)
                                pos_y = sprite_height - pos_y - 1;

                            pos_y += pos_y & 8;
                            
                            ppu->r = 1;
                            ppu->vram_address = (pattern_table << 12) | (tile_index << 4) | (pos_y + 8);
                        }
                        break;
                    case 0:
                        if (current_oam.attribute.flip_x)
                            ppu->sprite_shift_high[current_oam_index] = ((ppu->vram_data * 0x80200802ULL) & 0x0884422110ULL) * 0x0101010101ULL >> 32;
                        else
                            ppu->sprite_shift_high[current_oam_index] = ppu->vram_data;

                        // Set sprite to transparent if it's not detected on scanline.
                        if (current_oam_index >= ppu->eval_oam_free_index)
                        {
                            ppu->sprite_shift_high[current_oam_index] = 0;
                            ppu->sprite_shift_low[current_oam_index] = 0;
                        }
                        break;
                }
            }
       
            if (ppu->scanline == PRE_RENDER_SCANLINE)
            {
                if (ppu->dot >= 280 && ppu->dot <= 304)
                {
                    // Update vertical scrolling component from T during pre-render scanline
                    ppu->v_addr_reg = (ppu->v_addr_reg & ~0x7BE0) | (ppu->t_addr_reg & 0x7BE0);
                }
                else if (ppu->dot == 339 && !ppu->is_even_frame)
                {
                    // Skip one cycle if odd frame
                    ppu->dot = 340;
                }
            }
        }
    }
    else if (ppu->scanline == VBLANK_BEGIN_SCANLINE)
    {
        if (ppu->dot == 0)      ppu->pre_vblank = 1;
        else if (ppu->dot == 1) ppu->status.vblank_started = ppu->pre_vblank;
    }
 
    ppu->vbl = ppu->status.vblank_started && ppu->ctrl.generate_nmi;
}

#endif
