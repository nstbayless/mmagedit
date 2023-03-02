#ifndef _NES_CARTRIDGE_H_
#define _NES_CARTRIDGE_H_

#include <stdlib.h>
#include <stdint.h>

typedef enum nes_nametable_mirroring
{
    NES_NAMETABLE_MIRRORING_SINGLE_LOW,
    NES_NAMETABLE_MIRRORING_SINGLE_HIGH,
    NES_NAMETABLE_MIRRORING_VERTICAL,
    NES_NAMETABLE_MIRRORING_HORIZONTAL
} nes_nametable_mirroring;

typedef struct nes_mapper nes_mapper;

typedef struct nes_cartridge
{
    uint8_t*    prg_rom;
    size_t      prg_rom_size; 
    uint8_t*    chr_rom;
    size_t      chr_rom_size;
    nes_mapper* mapper;
    void*       mapper_state;
    nes_nametable_mirroring mirroring;
} nes_cartridge;

#endif
