#ifndef _NES_APU_H_
#define _NES_APU_H_

#include <stdint.h>
#include <memory.h>
#include <assert.h>

#define NES_APU_PULSE1_REG0_ID          0x4000
#define NES_APU_PULSE1_REG1_ID          0x4001
#define NES_APU_PULSE1_REG2_ID          0x4002
#define NES_APU_PULSE1_REG3_ID          0x4003

#define NES_APU_PULSE2_REG0_ID          0x4004
#define NES_APU_PULSE2_REG1_ID          0x4005
#define NES_APU_PULSE2_REG2_ID          0x4006
#define NES_APU_PULSE2_REG3_ID          0x4007

#define NES_APU_TRIANGLE_REG0_ID        0x4008
#define NES_APU_TRIANGLE_REG1_ID        0x400A
#define NES_APU_TRIANGLE_REG2_ID        0x400B

#define NES_APU_NOISE_REG0_ID           0x400C
#define NES_APU_NOISE_REG1_ID           0x400E
#define NES_APU_NOISE_REG2_ID           0x400F

#define NES_APU_STATUS_REG_ID           0x4015
#define NES_APU_FRAME_COUNTER_REG_ID    0x4017

enum NES_APU_REG_RW_MODE
{
    NES_APU_REG_RW_MODE_NONE,
    NES_APU_REG_RW_MODE_READ,
    NES_APU_REG_RW_MODE_WRITE
};

typedef struct nes_apu_pulse
{
    uint8_t     duty : 2;
    uint8_t     sequence_output : 1;
    union
    {
        uint8_t     length_counter_halt : 1;
        uint8_t     env_loop : 1;
    };
    uint8_t     env_start : 1;
    uint8_t     constant_volume : 1;
    uint8_t     sweep_enable : 1;
    uint8_t     sweep_negate : 1;
    uint8_t     sweep_reload : 1;
    uint16_t    timer;
    uint16_t    t;
    uint8_t     sequencer;
    uint8_t     length_counter;
    uint8_t     sweep_divider;
    uint8_t     sweep_divider_period;
    uint8_t     sweep_shift_count;
    uint16_t    sweep_target_period;
    uint8_t     env_divider;
    uint8_t     env_counter;
    uint8_t     volume;
    uint16_t    output;
} nes_apu_pulse;

typedef struct nes_apu_triangle
{
    union
    {
        uint8_t     control_flag : 1;
        uint8_t     length_counter_halt : 1;
    };
    uint8_t     linear_counter_reload : 1;
    uint16_t    timer;
    uint16_t    t;
    uint8_t     linear_counter;
    uint8_t     linear_counter_reload_value;
    uint8_t     length_counter;
    uint8_t     sequencer;
    uint16_t    output;
} nes_apu_triangle;

typedef struct nes_apu_noise
{
    uint8_t     mode : 1;
    union
    {
        uint8_t     length_counter_halt : 1;
        uint8_t     env_loop : 1;
    };
    uint8_t     env_start : 1;
    uint8_t     constant_volume : 1;
    uint16_t    shift_register;
    uint16_t    timer;
    uint16_t    t;
    uint8_t     length_counter;
    uint8_t     env_divider;
    uint8_t     env_counter;
    uint8_t     volume;
    uint16_t    output;
} nes_apu_noise;

typedef struct nes_apu
{
    uint8_t     reg_rw_mode : 2;
    uint16_t    reg_addr;
    uint8_t     reg_data;

    uint8_t     sequencer_mode : 1;
    uint8_t     sequencer_reset_req : 3;
    uint8_t     inhibit_interrupt : 1;
    uint8_t     frame_interrupt : 1;

    union
    {
        struct
        {
            uint8_t pulse1   : 1;
            uint8_t pulse2   : 1;
            uint8_t triangle : 1;
            uint8_t noise    : 1;
            uint8_t dmc      : 1;
        };
        uint8_t b;
    } channel_enable;

    nes_apu_pulse       pulse[2];
    nes_apu_triangle    triangle;
    nes_apu_noise       noise;

    int16_t     samples[44100];
    uint32_t    sample_count;

    uint32_t    cycle;
} nes_apu;

void nes_apu_reset(nes_apu* apu)
{
    memset(apu, 0, sizeof(nes_apu));
    apu->noise.shift_register = 1;
}

void update_sweep_target_period(nes_apu* apu, int i)
{
    const uint16_t change_amount = apu->pulse[i].timer >> apu->pulse[i].sweep_shift_count;
    apu->pulse[i].sweep_target_period = apu->pulse[i].timer + (change_amount ^ (0xFFFF * apu->pulse[i].sweep_negate)) + apu->pulse[i].sweep_negate * i;
}

void nes_apu_execute(nes_apu* apu)
{
    const uint8_t lengths[] = { 10, 254, 20, 2, 40, 4, 80, 6, 160, 8, 60, 10, 14, 12, 26, 14, 12, 16, 24, 18, 48, 20, 96, 22, 192, 24, 72, 26, 16, 28, 32, 30 };

    // I/O
    if (apu->reg_rw_mode)
    {
        switch (apu->reg_addr)
        {
            case NES_APU_STATUS_REG_ID:
            {
                if (apu->reg_rw_mode == NES_APU_REG_RW_MODE_WRITE)
                {
                    apu->channel_enable.b = apu->reg_data & 0x1F;
                    if (apu->channel_enable.pulse1 == 0)
                        apu->pulse[0].length_counter = 0;

                    if (apu->channel_enable.pulse2 == 0)
                        apu->pulse[1].length_counter = 0;

                    if (apu->channel_enable.triangle == 0)
                        apu->triangle.length_counter = 0;

                    if (apu->channel_enable.noise == 0)
                        apu->noise.length_counter = 0;
                }
                else
                {
                    apu->reg_data = (apu->pulse[0].length_counter > 0) |
                                   ((apu->pulse[1].length_counter > 0) << 1) |
                                   ((apu->triangle.length_counter > 0) << 2) |
                                   ((apu->noise.length_counter > 0) << 3) |
                                   (apu->frame_interrupt << 6);

                    apu->frame_interrupt = apu->sequencer_mode == 0 && (apu->cycle >= 29828 && apu->cycle <= 29830);
                }
            }
            break;
            case NES_APU_FRAME_COUNTER_REG_ID:
            {
                apu->sequencer_mode = apu->reg_data >> 7;
                apu->inhibit_interrupt = (apu->reg_data >> 6) & 1;
                if (apu->inhibit_interrupt)
                    apu->frame_interrupt = 0;
                apu->sequencer_reset_req = 4 - ((~apu->cycle) & 1);
            }
            break;
            case NES_APU_PULSE1_REG0_ID:
            case NES_APU_PULSE2_REG0_ID:
            {
                unsigned i = (apu->reg_addr >> 2) & 1;
                apu->pulse[i].duty = apu->reg_data >> 6;
                apu->pulse[i].length_counter_halt = (apu->reg_data >> 5) & 1; // alias env_loop
                apu->pulse[i].constant_volume = (apu->reg_data >> 4) & 1;
                apu->pulse[i].volume = apu->reg_data & 0x0F;
            }
            break;
            case NES_APU_PULSE1_REG1_ID:
            case NES_APU_PULSE2_REG1_ID:
            {
                unsigned i = (apu->reg_addr >> 2) & 1;
                apu->pulse[i].sweep_enable = (apu->reg_data >> 7);
                apu->pulse[i].sweep_divider_period = (apu->reg_data >> 4) & 7;
                apu->pulse[i].sweep_negate = (apu->reg_data >> 3) & 1;
                apu->pulse[i].sweep_shift_count = apu->reg_data & 7;
                apu->pulse[i].sweep_reload = 1;
                update_sweep_target_period(apu, i);
            }
            break;
            case NES_APU_PULSE1_REG2_ID:
            case NES_APU_PULSE2_REG2_ID:
            {
                unsigned i = (apu->reg_addr >> 2) & 1;
                apu->pulse[i].timer = (apu->pulse[i].timer & 0xFF00) | apu->reg_data;
                update_sweep_target_period(apu, i);
            }
            break;
            case NES_APU_PULSE1_REG3_ID:
            case NES_APU_PULSE2_REG3_ID:
            {
                unsigned i = (apu->reg_addr >> 2) & 1;
                if (apu->channel_enable.b & (i + 1))
                    apu->pulse[i].length_counter = lengths[apu->reg_data >> 3];

                apu->pulse[i].timer = (((uint16_t)apu->reg_data & 7) << 8) | (apu->pulse[i].timer & 0xFF);
                apu->pulse[i].sequencer = 0;
                apu->pulse[i].env_start = 1;
                update_sweep_target_period(apu, i);
            }
            break;
            case NES_APU_TRIANGLE_REG0_ID:
            {
                apu->triangle.control_flag = (apu->reg_data >> 7);
                apu->triangle.linear_counter_reload_value = (apu->reg_data & 0x7F);
            }
            break;
            case NES_APU_TRIANGLE_REG1_ID:
            {
                apu->triangle.timer = (apu->triangle.timer & 0xFF00) | apu->reg_data;
            }
            break;
            case NES_APU_TRIANGLE_REG2_ID:
            {
                if (apu->channel_enable.triangle)
                    apu->triangle.length_counter = lengths[apu->reg_data >> 3];

                apu->triangle.timer = (((uint16_t)apu->reg_data & 7) << 8) | (apu->triangle.timer & 0xFF);
                apu->triangle.linear_counter_reload = 1;
            }
            break;
            case NES_APU_NOISE_REG0_ID:
            {
                apu->noise.length_counter_halt = (apu->reg_data >> 5) & 1; // alias env_loop
                apu->noise.constant_volume = (apu->reg_data >> 4) & 1;
                apu->noise.volume = apu->reg_data & 0x0F;
            }
            break;
            case NES_APU_NOISE_REG1_ID:
            {
                const uint16_t noise_periods[] = {4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068 };
                apu->noise.mode = (apu->reg_data >> 7);
                apu->noise.timer = noise_periods[apu->reg_data & 0x0F];
            }
            break;
            case NES_APU_NOISE_REG2_ID:
            {
                if (apu->channel_enable.noise)
                    apu->noise.length_counter = lengths[apu->reg_data >> 3];

                apu->noise.env_start = 1;
            }
            break;
        }
        apu->reg_rw_mode = NES_APU_REG_RW_MODE_NONE;
    }

    // Update frame sequencer
    {
        unsigned update_quarter = 0;
        unsigned update_half = 0;

        if (apu->sequencer_reset_req)
        {
            if (--apu->sequencer_reset_req == 0)
            {
                apu->cycle = 0;
                update_half = update_quarter = apu->sequencer_mode;
            }
        }

        if (apu->sequencer_mode == 0)
        {
            switch(apu->cycle)
            {
                case 7457:  update_quarter = 1; break;
                case 14913: update_quarter = 1; update_half = 1; break;
                case 22371: update_quarter = 1; break;
                case 29828:
                    apu->frame_interrupt = (apu->inhibit_interrupt == 0);
                    break;
                case 29829:
                    update_quarter = 1; update_half = 1;
                    apu->frame_interrupt = (apu->inhibit_interrupt == 0);
                    break;
                case 29830:
                    apu->cycle = 0;
                    apu->frame_interrupt = (apu->inhibit_interrupt == 0);
                    break;
            }
        }
        else
        {
            switch(apu->cycle)
            {
                case 7457:  update_quarter = 1; break;
                case 14913: update_quarter = 1; update_half = 1; break;
                case 22371: update_quarter = 1; break;
                case 37281: update_quarter = 1; update_half = 1; break;
                case 37282: apu->cycle = 0; break;
            }
        }

        if (update_quarter)
        {
            // pulse envelopes
            for (int i = 0; i < 2; ++i)
            {
                if ((apu->channel_enable.b & (i + 1)) && apu->pulse[i].length_counter)
                {
                    if (apu->pulse[i].env_start)
                    {
                        apu->pulse[i].env_start = 0;
                        apu->pulse[i].env_counter = 15;
                        apu->pulse[i].env_divider = apu->pulse[i].volume + 1;
                    }
                    else if (apu->pulse[i].env_divider-- == 0)
                    {
                        apu->pulse[i].env_divider = apu->pulse[i].volume;
                        if (apu->pulse[i].env_counter-- == 0)
                            apu->pulse[i].env_counter = 15 * apu->pulse[i].env_loop;
                    }
                }
            }

            // triangle linear counter
            if (apu->channel_enable.triangle)
            {
                if (apu->triangle.linear_counter_reload) apu->triangle.linear_counter = apu->triangle.linear_counter_reload_value;
                else if (apu->triangle.linear_counter) apu->triangle.linear_counter--;

                apu->triangle.linear_counter_reload &= apu->triangle.control_flag;
            }

            // noise envelope
            if (apu->channel_enable.noise && apu->noise.length_counter)
            {
                if (apu->noise.env_start)
                {
                    apu->noise.env_start = 0;
                    apu->noise.env_counter = 15;
                    apu->noise.env_divider = apu->noise.volume + 1;
                }
                else if (apu->noise.env_divider-- == 0)
                {
                    apu->noise.env_divider = apu->noise.volume;
                    if (apu->noise.env_counter-- == 0)
                        apu->noise.env_counter = 15 * apu->noise.env_loop;
                }
            }
        }

        if (update_half)
        {
            // pulse sweep and length counters
            for (int i = 0; i < 2; ++i)
            {
                if ((apu->channel_enable.b & (i + 1)) && apu->pulse[i].length_counter)
                {
                    apu->pulse[i].length_counter -= apu->pulse[i].length_counter_halt ^ 1;

                    if (apu->pulse[i].sweep_divider == 0 && apu->pulse[i].sweep_enable && apu->pulse[i].sweep_target_period < 0x800)
                    {
                        apu->pulse[i].timer = apu->pulse[i].sweep_target_period;
                        update_sweep_target_period(apu, i);
                    }

                    if (apu->pulse[i].sweep_divider-- == 0 || apu->pulse[i].sweep_reload)
                    {
                        apu->pulse[i].sweep_divider = apu->pulse[i].sweep_divider_period;
                        apu->pulse[i].sweep_reload = 0;
                    }
                }
            }

            // triangle length counter
            if (apu->channel_enable.triangle && apu->triangle.length_counter)
                apu->triangle.length_counter -= apu->triangle.length_counter_halt ^ 1;

            // noise length counter
            if (apu->channel_enable.noise && apu->noise.length_counter)
                apu->noise.length_counter -= apu->noise.length_counter_halt ^ 1;
        }
    }

    // Update pulse and noise channels
    if (apu->cycle & 1)
    {
        // Update pulse channels
        for (int i = 0; i < 2; ++i)
        {
            if ((apu->channel_enable.b & (i + 1)) && apu->pulse[i].length_counter)
            {
                if (apu->pulse[i].t-- == 0)
                {
                    apu->pulse[i].t = apu->pulse[i].timer;
                    switch (apu->pulse[i].duty)
                    {
                        case 0: apu->pulse[i].sequence_output = (0x80 >> apu->pulse[i].sequencer) & 1; break;
                        case 1: apu->pulse[i].sequence_output = (0xC0 >> apu->pulse[i].sequencer) & 1; break;
                        case 2: apu->pulse[i].sequence_output = (0xF0 >> apu->pulse[i].sequencer) & 1; break;
                        case 3: apu->pulse[i].sequence_output = ((~0xC0) >> apu->pulse[i].sequencer) & 1; break;
                    }
                    apu->pulse[i].sequencer = (apu->pulse[i].sequencer - 1) & 7;
                }

                if (apu->pulse[i].timer >= 8)
                {
                    if (apu->pulse[i].constant_volume)
                        apu->pulse[i].output = (apu->pulse[i].sequence_output & (apu->pulse[i].sweep_target_period < 0x800)) * apu->pulse[i].volume;
                    else
                        apu->pulse[i].output = (apu->pulse[i].sequence_output & (apu->pulse[i].sweep_target_period < 0x800)) * apu->pulse[i].env_counter;
                }
                else
                {
                    apu->pulse[i].output = 0;
                }
            }
            else
            {
                apu->pulse[i].output= 0;
            }
        }

        // Update noise channel
        if (apu->channel_enable.noise && apu->noise.length_counter)
        {
            if (apu->noise.t-- == 0)
            {
                apu->noise.t = apu->noise.timer;
                apu->noise.shift_register = (apu->noise.shift_register >> 1) | 
                    ((apu->noise.shift_register ^ (apu->noise.shift_register >> (apu->noise.mode * 5 + 1))) << 14);
            }

            apu->noise.output = (apu->noise.shift_register & 1) * (apu->noise.constant_volume ? apu->noise.volume : apu->noise.env_counter);
        }
        else
        {
            apu->noise.output = 0;
        }
    }

    // Update triangle channel
    if (apu->channel_enable.triangle)
    {
        if (apu->triangle.t-- == 0)
        {
            apu->triangle.t = apu->triangle.timer;

            if (apu->triangle.length_counter && apu->triangle.linear_counter)
            {
                apu->triangle.output = (apu->triangle.timer > 1) * 
                    ((apu->triangle.sequencer < 16) ? -(apu->triangle.sequencer - 15) : apu->triangle.sequencer - 16);
                apu->triangle.sequencer = (apu->triangle.sequencer + 1) % 32;
            }
        }
    }

    // Mixing
    {
        uint64_t pulse_out = (apu->pulse[0].output + apu->pulse[1].output) * 32298154ULL; 
        uint64_t tnd_out = apu->triangle.output * 36550171ULL + apu->noise.output * 21217138ULL;

        // dividing by 42949672ULL results in output in rage 0-100
        apu->samples[apu->sample_count++] = ((pulse_out + tnd_out)/42949672ULL) * 500;
    }

    apu->cycle++;
}

#endif
