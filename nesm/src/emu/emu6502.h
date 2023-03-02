#ifndef _EMU6502_H_
#define _EMU6502_H_

#include "emu6502_opcodes.h"
#include <stdint.h>
#include <memory.h>
#include <unistd.h>

enum cpu_rw_mode
{
    CPU_RW_MODE_NONE    = 0,
    CPU_RW_MODE_READ    = 1,
    CPU_RW_MODE_WRITE   = 2
};

typedef struct cpu_state_
{
    uint16_t cycle; /*  0x00FF - current cycle; 0xFF00 - current instruction */
        
    uint16_t PC;             
    uint8_t  S;
    uint8_t  P; 

    uint16_t address;         
    uint8_t  rw_mode;
    uint8_t  irq    : 1;
    uint8_t  nmi    : 1;
    uint8_t  data;
    uint8_t  temp;

    uint8_t  A;
    uint8_t  X;
    uint8_t  Y;

} cpu_state;

enum cpu_status_flags
{
    CPU_STATUS_FLAG_CARRY       = 0x01,
    CPU_STATUS_FLAG_ZERO        = 0x02,
    CPU_STATUS_FLAG_IRQDISABLE  = 0x04,
    CPU_STATUS_FLAG_DECIMAL     = 0x08,
    CPU_STATUS_FLAG_BREAK       = 0x10,
    CPU_STATUS_FLAG_OVERFLOW    = 0x40,
    CPU_STATUS_FLAG_NEGATIVE    = 0x80
};

#define _CPU_SET_REG_P(cpu, v)        cpu.P = (v) | 0x20
#define _CPU_UPDATE_NZ(cpu, v)       _CPU_SET_REG_P(cpu, (cpu.P & 0x7D) | ((v & 0x80) | (v?0:0x02)))
#define _CPU_SET_REG(cpu, reg, v)    {cpu.reg = v; _CPU_UPDATE_NZ(cpu, cpu.reg);} 
#define _CPU_SET_REG_A(cpu, v)        _CPU_SET_REG(cpu, A, v)
#define _CPU_SET_REG_X(cpu, v)        _CPU_SET_REG(cpu, X, v)
#define _CPU_SET_REG_Y(cpu, v)        _CPU_SET_REG(cpu, Y, v)
#define _CPU_SET_REG_S(cpu, v)        cpu.S = v

#define _CPU_SET_INSTRUCTION(cpu, i)   (cpu.cycle = (cpu.cycle & 0x00FF) | (i << 8))
#define _CPU_GET_INSTRUCTION(cpu)      ((cpu.cycle >> 8) & 0xFF)

#define _CPU_COND_BRANCH(cpu, cond) if (cond) {\
    cpu.address = cpu.PC + (int8_t)cpu.data;\
    return cpu;\
}

#define _CPU_COND_BRANCH_TAKEN(cpu) {\
    int page_cross = ((cpu.address & 0xFF00) != (cpu.PC & 0xFF00));\
    cpu.PC = cpu.address;\
    if (page_cross) return cpu;\
}

#define _CPU_CHECK_PAGE_CROSS(cpu) \
    if (cpu.temp) {\
        cpu.rw_mode = CPU_RW_MODE_READ;\
        cpu.address += 0x0100;\
        return cpu;\
    }    


#define _CPU_BIT(cpu)               _CPU_SET_REG_P(cpu, (cpu.P & 0x3D) | (cpu.data & 0xC0) | (((cpu.A & cpu.data) == 0)?2:0))

#define _CPU_ADC(cpu) {\
    uint16_t tmp = ((uint16_t)cpu.A) + cpu.data + (cpu.P & 1);\
    uint8_t overflow = (((cpu.data ^ tmp) & (cpu.A ^ tmp)) & 0x80) >> 1;\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xBE) | ((tmp >> 8) & 1) | overflow);\
    _CPU_SET_REG_A(cpu, tmp & 0xFF);\
}

#define _CPU_SBC(cpu) {\
    uint16_t tmp = ((uint16_t)cpu.A) + ~cpu.data + (cpu.P & 1);\
    uint8_t overflow = (((~cpu.data ^ tmp) & (cpu.A ^ tmp)) & 0x80) >> 1;\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xBE) | ((~tmp >> 8) & 1) | overflow);\
    _CPU_SET_REG_A(cpu, tmp & 0xFF);\
}

#define _CPU_CMP(cpu, reg) {\
    uint16_t tmp = ((uint16_t)reg) - cpu.data;\
    _CPU_UPDATE_NZ(cpu, (tmp & 0xFF));\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xFE) | ((~tmp >> 8) & 1));\
}

#define _CPU_ROL(cpu, v) {\
    uint8_t tmp = cpu.P & 1;\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xFE) | (v >> 7));\
    v = (v << 1) | tmp;\
    _CPU_UPDATE_NZ(cpu, v);\
}

#define _CPU_ROR(cpu, v) {\
    uint8_t tmp = cpu.P & 1;\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xFE) | (v & 1));\
    v = (v >> 1) | (tmp << 7);\
    _CPU_UPDATE_NZ(cpu, v);\
}

#define _CPU_ASL(cpu, v) {\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xFE) | (v >> 7 ));\
    v = (v << 1);\
    _CPU_UPDATE_NZ(cpu, v);\
}

#define _CPU_LSR(cpu, v) {\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xFE) | (v & 1));\
    v = (v >> 1);\
    _CPU_SET_REG_P(cpu, (cpu.P & 0x7D) | (v?0:0x02));\
}

#define _CPU_LAX(cpu) {\
    cpu.A = cpu.data;\
    _CPU_SET_REG_X(cpu, cpu.data);\
}

#define _CPU_DCP(cpu) {\
    cpu.rw_mode = CPU_RW_MODE_WRITE;\
    cpu.data -= 1;\
    _CPU_CMP(cpu, cpu.A);\
}

#define _CPU_ISB(cpu) {\
    cpu.rw_mode = CPU_RW_MODE_WRITE;\
    cpu.data += 1;\
    _CPU_SBC(cpu);\
}

#define _CPU_SLO(cpu) {\
    cpu.rw_mode = CPU_RW_MODE_WRITE;\
    _CPU_SET_REG_P(cpu, (cpu.P & 0xFE) | (cpu.data >> 7 ));\
    cpu.data <<= 1;\
    _CPU_SET_REG_A(cpu, cpu.A | cpu.data);\
}

static cpu_state cpu_reset()
{
    cpu_state state;
    memset(&state, 0, sizeof(cpu_state));
    _CPU_SET_REG_P(state, CPU_STATUS_FLAG_IRQDISABLE);
    state.S = 0xFF;
    state.temp = 0xFC;
    state.cycle = 1;
    return state; 
}

static cpu_state cpu_execute(cpu_state state)
{
    uint8_t cycle = state.cycle++;
    uint_fast32_t instruction = _CPU_GET_INSTRUCTION(state);

    if (cycle == 0)
    {
        _CPU_SET_INSTRUCTION(state, state.data);
        state.rw_mode = CPU_RW_MODE_NONE;

        switch (state.data)
        {
            case IC_BRK:
                if (!(state.nmi || (state.irq && !(state.P & CPU_STATUS_FLAG_IRQDISABLE))))
                {
                    state.temp = 0xFE;
                    state.rw_mode = CPU_RW_MODE_READ;
                    state.address = state.PC++;
                }
                return state;
            case IC_PHP:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = ((uint8_t)state.S--) + 0x0100;
                state.data = state.P | CPU_STATUS_FLAG_BREAK;
                return state;
            case IC_PHA:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = ((uint8_t)state.S--) + 0x0100;
                state.data = state.A;
                return state;
            case IC_RTS: case IC_RTI: case IC_PLP: case IC_PLA:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = ((uint8_t)++state.S) + 0x0100;
                return state;
            case IC_INX: _CPU_SET_REG_X(state, state.X + 1); return state;
            case IC_INY: _CPU_SET_REG_Y(state, state.Y + 1); return state;
            case IC_DEX: _CPU_SET_REG_X(state, state.X - 1); return state;
            case IC_DEY: _CPU_SET_REG_Y(state, state.Y - 1); return state;
            case IC_ROL_ACC: _CPU_ROL(state, state.A); return state;
            case IC_ROR_ACC: _CPU_ROR(state, state.A); return state;
            case IC_ASL_ACC: _CPU_ASL(state, state.A); return state;
            case IC_LSR_ACC: _CPU_LSR(state, state.A); return state;
            case IC_TAX: _CPU_SET_REG_X(state, state.A); return state;
            case IC_TAY: _CPU_SET_REG_Y(state, state.A); return state;
            case IC_TSX: _CPU_SET_REG_X(state, state.S); return state;
            case IC_TXA: _CPU_SET_REG_A(state, state.X); return state;
            case IC_TXS: _CPU_SET_REG_S(state, state.X); return state;
            case IC_TYA: _CPU_SET_REG_A(state, state.Y); return state;
            case IC_CLC: _CPU_SET_REG_P(state, state.P & 0xFE); return state;
            case IC_SEC: _CPU_SET_REG_P(state, state.P | 1); return state;
            case IC_CLI: _CPU_SET_REG_P(state, state.P & 0xFB); return state;
            case IC_SEI: _CPU_SET_REG_P(state, state.P | 0x04); return state;
            case IC_CLV: _CPU_SET_REG_P(state, state.P & 0xBF); return state;
            case IC_CLD: _CPU_SET_REG_P(state, state.P & 0xF7); return state;
            case IC_SED: _CPU_SET_REG_P(state, state.P | 0x08); return state;
            case IC_NOP: 
            case IC_IL_NOP_IMM0: case IC_IL_NOP_IMM1: case IC_IL_NOP_IMM2: case IC_IL_NOP_IMM3: case IC_IL_NOP_IMM4: case IC_IL_NOP_IMM5:
                return state;

            case IC_BCC: case IC_BCS: case IC_BNE: case IC_BEQ: case IC_BVC: case IC_BVS: case IC_BPL: case IC_BMI:
            case IC_JMP: case IC_JMP_IND:
            case IC_BIT_ABS: case IC_BIT_ZP: 
            case IC_LDA_IMM: case IC_LDA_ABS: case IC_LDA_ABS_X: case IC_LDA_ABS_Y: case IC_LDA_ZP: case IC_LDA_ZP_X: case IC_LDA_IND_X: case IC_LDA_IND_Y:
            case IC_LDX_IMM: case IC_LDX_ABS: case IC_LDX_ABS_Y: case IC_LDX_ZP: case IC_LDX_ZP_Y: 
            case IC_LDY_IMM: case IC_LDY_ABS: case IC_LDY_ABS_X: case IC_LDY_ZP: case IC_LDY_ZP_X:
            case IC_STA_ABS: case IC_STA_ABS_X: case IC_STA_ABS_Y: case IC_STA_ZP: case IC_STA_ZP_X: case IC_STA_IND_X: case IC_STA_IND_Y:
            case IC_STX_ABS: case IC_STX_ZP: case IC_STX_ZP_Y: case IC_STY_ABS: case IC_STY_ZP: case IC_STY_ZP_X:
            case IC_ROL_ABS: case IC_ROL_ABS_X: case IC_ROL_ZP: case IC_ROL_ZP_X: 
            case IC_ROR_ABS: case IC_ROR_ABS_X: case IC_ROR_ZP: case IC_ROR_ZP_X: 
            case IC_DEC_ABS: case IC_DEC_ABS_X: case IC_DEC_ZP: case IC_DEC_ZP_X:
            case IC_INC_ABS: case IC_INC_ABS_X: case IC_INC_ZP: case IC_INC_ZP_X:
            case IC_ASL_ABS: case IC_ASL_ABS_X: case IC_ASL_ZP: case IC_ASL_ZP_X: 
            case IC_LSR_ABS: case IC_LSR_ABS_X: case IC_LSR_ZP: case IC_LSR_ZP_X: 
            case IC_AND_IMM: case IC_AND_ABS: case IC_AND_ABS_X: case IC_AND_ABS_Y: case IC_AND_ZP: case IC_AND_ZP_X: case IC_AND_IND_X: case IC_AND_IND_Y: 
            case IC_ORA_IMM: case IC_ORA_ABS: case IC_ORA_ABS_X: case IC_ORA_ABS_Y: case IC_ORA_ZP: case IC_ORA_ZP_X: case IC_ORA_IND_X: case IC_ORA_IND_Y: 
            case IC_EOR_IMM: case IC_EOR_ABS: case IC_EOR_ABS_X: case IC_EOR_ABS_Y: case IC_EOR_ZP: case IC_EOR_ZP_X: case IC_EOR_IND_X: case IC_EOR_IND_Y:
            case IC_ADC_IMM: case IC_ADC_ABS: case IC_ADC_ABS_X: case IC_ADC_ABS_Y: case IC_ADC_ZP: case IC_ADC_ZP_X: case IC_ADC_IND_X: case IC_ADC_IND_Y: 
            case IC_SBC_IMM: case IC_SBC_ABS: case IC_SBC_ABS_X: case IC_SBC_ABS_Y: case IC_SBC_ZP: case IC_SBC_ZP_X: case IC_SBC_IND_X: case IC_SBC_IND_Y:
            case IC_CMP_IMM: case IC_CMP_ABS: case IC_CMP_ABS_X: case IC_CMP_ABS_Y: case IC_CMP_ZP: case IC_CMP_ZP_X: case IC_CMP_IND_X: case IC_CMP_IND_Y:
            case IC_CPX_IMM: case IC_CPX_ABS: case IC_CPX_ZP: 
            case IC_CPY_IMM: case IC_CPY_ABS: case IC_CPY_ZP:
            case IC_JSR:    
            case IC_IL_LAX_ABS: case IC_IL_LAX_ABS_Y: case IC_IL_LAX_ZP: case IC_IL_LAX_ZP_Y: case IC_IL_LAX_IND_X: case IC_IL_LAX_IND_Y:
            case IC_IL_SAX_ABS: case IC_IL_SAX_ZP: case IC_IL_SAX_ZP_Y: case IC_IL_SAX_IND_X:
            case IC_IL_SBC_IMM:
            case IC_IL_NOP_ZP0: case IC_IL_NOP_ZP1: case IC_IL_NOP_ZP2:
            case IC_IL_NOP_ABS:
            case IC_IL_NOP_ABS_X0: case IC_IL_NOP_ABS_X1: case IC_IL_NOP_ABS_X2: case IC_IL_NOP_ABS_X3: case IC_IL_NOP_ABS_X4: case IC_IL_NOP_ABS_X5:
            case IC_IL_NOP_ZP_X0: case IC_IL_NOP_ZP_X1: case IC_IL_NOP_ZP_X2: case IC_IL_NOP_ZP_X3: case IC_IL_NOP_ZP_X4: case IC_IL_NOP_ZP_X5:
            case IC_IL_NOP_IMP0: case IC_IL_NOP_IMP1: case IC_IL_NOP_IMP2: case IC_IL_NOP_IMP3: case IC_IL_NOP_IMP4:
            case IC_IL_DCP_ABS: case IC_IL_DCP_ABS_X: case IC_IL_DCP_ABS_Y: case IC_IL_DCP_ZP: case IC_IL_DCP_ZP_X: case IC_IL_DCP_IND_X: case IC_IL_DCP_IND_Y:
            case IC_IL_ISB_ABS: case IC_IL_ISB_ABS_X: case IC_IL_ISB_ABS_Y: case IC_IL_ISB_ZP: case IC_IL_ISB_ZP_X: case IC_IL_ISB_IND_X: case IC_IL_ISB_IND_Y:
            case IC_IL_SLO_ABS: case IC_IL_SLO_ABS_X: case IC_IL_SLO_ABS_Y: case IC_IL_SLO_ZP: case IC_IL_SLO_ZP_X: case IC_IL_SLO_IND_X: case IC_IL_SLO_IND_Y:

                /* fetch first operand */
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = state.PC++;
                return state;

            default: 
                // Unknown instruction, treated as NOP
                return state;
        }
    }
    else if (cycle == 1)
    {
        state.rw_mode = CPU_RW_MODE_NONE;
        switch (instruction)
        {
            case IC_BRK:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data = state.PC >> 8;
                state.address = ((uint8_t)state.S--) + 0x0100;
                return state;
            case IC_ADC_IMM: _CPU_ADC(state); break;
            case IC_AND_IMM: _CPU_SET_REG_A(state, state.A & state.data); break;
            case IC_ORA_IMM: _CPU_SET_REG_A(state, state.A | state.data); break;
            case IC_EOR_IMM: _CPU_SET_REG_A(state, state.A ^ state.data); break;
            case IC_LDA_IMM: _CPU_SET_REG_A(state, state.data); break;
            case IC_LDX_IMM: _CPU_SET_REG_X(state, state.data); break;
            case IC_LDY_IMM: _CPU_SET_REG_Y(state, state.data); break;
            case IC_IL_SBC_IMM:
            case IC_SBC_IMM: _CPU_SBC(state); break;
            case IC_CMP_IMM: _CPU_CMP(state, state.A); break;
            case IC_CPX_IMM: _CPU_CMP(state, state.X); break;
            case IC_CPY_IMM: _CPU_CMP(state, state.Y); break;
            case IC_BCC:     _CPU_COND_BRANCH(state, (state.P & 0x01) == 0); break;
            case IC_BCS:     _CPU_COND_BRANCH(state, (state.P & 0x01)); break;
            case IC_BNE:     _CPU_COND_BRANCH(state, (state.P & 0x02) == 0); break;
            case IC_BEQ:     _CPU_COND_BRANCH(state, (state.P & 0x02)); break;
            case IC_BVC:     _CPU_COND_BRANCH(state, (state.P & 0x40) == 0); break;
            case IC_BVS:     _CPU_COND_BRANCH(state, (state.P & 0x40)); break;
            case IC_BPL:     _CPU_COND_BRANCH(state, (state.P & 0x80) == 0); break;
            case IC_BMI:     _CPU_COND_BRANCH(state, (state.P & 0x80)); break;
            case IC_LDA_ABS: case IC_LDA_ABS_X: case IC_LDA_ABS_Y:
            case IC_LDX_ABS: case IC_LDX_ABS_Y:
            case IC_LDY_ABS: case IC_LDY_ABS_X:
            case IC_STA_ABS: case IC_STA_ABS_X: case IC_STA_ABS_Y:
            case IC_STX_ABS:
            case IC_STY_ABS:
            case IC_ROL_ABS: case IC_ROL_ABS_X:
            case IC_ROR_ABS: case IC_ROR_ABS_X:
            case IC_ASL_ABS: case IC_ASL_ABS_X:
            case IC_LSR_ABS: case IC_LSR_ABS_X:
            case IC_DEC_ABS: case IC_DEC_ABS_X:
            case IC_INC_ABS: case IC_INC_ABS_X:
            case IC_AND_ABS: case IC_AND_ABS_X: case IC_AND_ABS_Y:
            case IC_ORA_ABS: case IC_ORA_ABS_X: case IC_ORA_ABS_Y:
            case IC_EOR_ABS: case IC_EOR_ABS_X: case IC_EOR_ABS_Y:
            case IC_ADC_ABS: case IC_ADC_ABS_X: case IC_ADC_ABS_Y:
            case IC_SBC_ABS: case IC_SBC_ABS_X: case IC_SBC_ABS_Y:
            case IC_CMP_ABS: case IC_CMP_ABS_X: case IC_CMP_ABS_Y:
            case IC_CPX_ABS:
            case IC_CPY_ABS:
            case IC_BIT_ABS:
            case IC_JMP: case IC_JMP_IND:
            case IC_IL_NOP_ABS:
            case IC_IL_NOP_ABS_X0: case IC_IL_NOP_ABS_X1: case IC_IL_NOP_ABS_X2: case IC_IL_NOP_ABS_X3: case IC_IL_NOP_ABS_X4: case IC_IL_NOP_ABS_X5:
            case IC_IL_LAX_ABS: case IC_IL_LAX_ABS_Y:
            case IC_IL_SAX_ABS:
            case IC_IL_DCP_ABS: case IC_IL_DCP_ABS_X: case IC_IL_DCP_ABS_Y:
            case IC_IL_ISB_ABS: case IC_IL_ISB_ABS_X: case IC_IL_ISB_ABS_Y:
            case IC_IL_SLO_ABS: case IC_IL_SLO_ABS_X: case IC_IL_SLO_ABS_Y:

                /* fetch high byte of absolute address */
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = state.PC++;
                state.temp = state.data;
                return state;

            case IC_LDA_ZP:
            case IC_LDX_ZP:
            case IC_LDY_ZP:
            case IC_BIT_ZP:
            case IC_ROL_ZP:
            case IC_ROR_ZP:
            case IC_ASL_ZP:
            case IC_LSR_ZP:
            case IC_ADC_ZP:
            case IC_SBC_ZP:
            case IC_CMP_ZP:
            case IC_CPX_ZP:
            case IC_CPY_ZP:
            case IC_DEC_ZP:
            case IC_INC_ZP:
            case IC_AND_ZP:
            case IC_ORA_ZP:
            case IC_EOR_ZP:
            case IC_IL_NOP_ZP0: case IC_IL_NOP_ZP1: case IC_IL_NOP_ZP2:
            case IC_IL_LAX_ZP:
            case IC_IL_DCP_ZP:
            case IC_IL_ISB_ZP:
            case IC_IL_SLO_ZP:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = state.data;
                return state;
            case IC_LDA_ZP_X:
            case IC_LDY_ZP_X:
            case IC_ROL_ZP_X:
            case IC_ROR_ZP_X:
            case IC_ASL_ZP_X:
            case IC_LSR_ZP_X:
            case IC_ADC_ZP_X:
            case IC_SBC_ZP_X:
            case IC_CMP_ZP_X:
            case IC_DEC_ZP_X:
            case IC_INC_ZP_X:
            case IC_AND_ZP_X:
            case IC_ORA_ZP_X:
            case IC_EOR_ZP_X:
            case IC_IL_NOP_ZP_X0: case IC_IL_NOP_ZP_X1: case IC_IL_NOP_ZP_X2: case IC_IL_NOP_ZP_X3: case IC_IL_NOP_ZP_X4: case IC_IL_NOP_ZP_X5:
            case IC_IL_DCP_ZP_X:
            case IC_IL_ISB_ZP_X:
            case IC_IL_SLO_ZP_X:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data + state.X) & 0xFF;
                return state; 
            case IC_LDX_ZP_Y:
            case IC_IL_LAX_ZP_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data + state.Y) & 0xFF;
                return state;
            case IC_STA_ZP:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = state.data;
                state.data = state.A;
                return state;
            case IC_STA_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data + state.X) & 0xFF;
                state.data = state.A;
                return state;
            case IC_STX_ZP:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = state.data;
                state.data = state.X;
                return state;
            case IC_STX_ZP_Y:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data + state.Y) & 0xFF;
                state.data = state.X;
                return state;
            case IC_STY_ZP:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = state.data;
                state.data = state.Y;
                return state;
            case IC_STY_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data + state.X) & 0xFF;
                state.data = state.Y;
                return state;
            case IC_IL_SAX_ZP:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = state.data;
                state.data = state.A & state.X;
                return state;
            case IC_IL_SAX_ZP_Y:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data + state.Y) & 0xFF;
                state.data = state.A & state.X;
                return state;
            case IC_LDA_IND_X:
            case IC_STA_IND_X:
            case IC_ADC_IND_X:
            case IC_SBC_IND_X:
            case IC_CMP_IND_X:
            case IC_AND_IND_X:
            case IC_ORA_IND_X:
            case IC_EOR_IND_X:
            case IC_IL_LAX_IND_X:
            case IC_IL_SAX_IND_X:
            case IC_IL_DCP_IND_X:
            case IC_IL_ISB_IND_X:
            case IC_IL_SLO_IND_X:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data + state.X) & 0xFF;
                return state;
            case IC_LDA_IND_Y:
            case IC_STA_IND_Y:
            case IC_ADC_IND_Y:
            case IC_SBC_IND_Y:
            case IC_CMP_IND_Y:
            case IC_AND_IND_Y:
            case IC_ORA_IND_Y:
            case IC_EOR_IND_Y:
            case IC_IL_LAX_IND_Y:
            case IC_IL_DCP_IND_Y:
            case IC_IL_ISB_IND_Y:
            case IC_IL_SLO_IND_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = state.data;
                return state;
            case IC_JSR:
                state.rw_mode = CPU_RW_MODE_NONE;
                state.temp = state.data;
                return state;
            case IC_RTI:
                state.rw_mode = CPU_RW_MODE_READ;
                _CPU_SET_REG_P(state, state.data & ~CPU_STATUS_FLAG_BREAK);
                state.address = ((uint8_t)++state.S) + 0x0100;
                return state;
            case IC_PLA:
                state.rw_mode = CPU_RW_MODE_NONE;
                _CPU_SET_REG_A(state, state.data);
                return state;
            case IC_PLP:
                state.rw_mode = CPU_RW_MODE_NONE;
                _CPU_SET_REG_P(state, state.data & ~CPU_STATUS_FLAG_BREAK);
                return state;
            case IC_PHA:
            case IC_PHP:
            case IC_RTS:
                state.rw_mode = CPU_RW_MODE_NONE;
                // empty cycle
                return state;
            default:
                break;
        }
    }
    else if (cycle == 2)
    {
        switch (instruction)
        {
            case IC_BRK:
                state.data = state.PC;
                state.address = ((uint8_t)state.S--) + 0x0100;
                return state;

            case IC_BCC: case IC_BCS: case IC_BNE: case IC_BEQ: case IC_BVC: case IC_BVS: case IC_BPL: case IC_BMI:
                _CPU_COND_BRANCH_TAKEN(state);
                break;

            case IC_LDA_ABS:
            case IC_LDX_ABS:
            case IC_LDY_ABS:
            case IC_ROL_ABS:
            case IC_ROR_ABS:
            case IC_DEC_ABS:
            case IC_INC_ABS:
            case IC_ASL_ABS:
            case IC_LSR_ABS:
            case IC_ADC_ABS:
            case IC_SBC_ABS:
            case IC_CMP_ABS:
            case IC_CPX_ABS:
            case IC_CPY_ABS:
            case IC_AND_ABS:
            case IC_ORA_ABS:
            case IC_EOR_ABS:
            case IC_BIT_ABS:
            case IC_IL_NOP_ABS:
            case IC_IL_LAX_ABS:
            case IC_IL_DCP_ABS:
            case IC_IL_ISB_ABS:
            case IC_IL_SLO_ABS:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | state.temp;
                return state;
            case IC_LDA_ABS_X:
            case IC_LDY_ABS_X:
            case IC_STA_ABS_X:
            case IC_ROL_ABS_X:
            case IC_ROR_ABS_X:
            case IC_DEC_ABS_X:
            case IC_INC_ABS_X:
            case IC_ASL_ABS_X:
            case IC_LSR_ABS_X:
            case IC_ADC_ABS_X:
            case IC_SBC_ABS_X:
            case IC_CMP_ABS_X:
            case IC_AND_ABS_X:
            case IC_ORA_ABS_X:
            case IC_EOR_ABS_X:
            case IC_IL_NOP_ABS_X0: case IC_IL_NOP_ABS_X1: case IC_IL_NOP_ABS_X2: case IC_IL_NOP_ABS_X3: case IC_IL_NOP_ABS_X4: case IC_IL_NOP_ABS_X5:
            case IC_IL_DCP_ABS_X:
            case IC_IL_ISB_ABS_X:
            case IC_IL_SLO_ABS_X:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | ((state.temp + state.X) & 0xFF);
                state.temp = ((uint16_t)state.temp + (uint16_t)state.X) >> 8;
                return state;
            case IC_LDA_ABS_Y:
            case IC_LDX_ABS_Y:
            case IC_STA_ABS_Y:
            case IC_ADC_ABS_Y:
            case IC_SBC_ABS_Y:
            case IC_CMP_ABS_Y:
            case IC_AND_ABS_Y:
            case IC_ORA_ABS_Y:
            case IC_EOR_ABS_Y:
            case IC_IL_LAX_ABS_Y:
            case IC_IL_DCP_ABS_Y:
            case IC_IL_ISB_ABS_Y:
            case IC_IL_SLO_ABS_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | ((state.temp + state.Y) & 0xFF);
                state.temp = ((uint16_t)state.temp + (uint16_t)state.Y) >> 8;
                return state;
            case IC_STA_ABS:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data << 8) | state.temp;
                state.data = state.A;
                return state;
            case IC_STX_ABS:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data << 8) | state.temp;
                state.data = state.X;
                return state;
            case IC_STY_ABS:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data << 8) | state.temp;
                state.data = state.Y;
                return state;
            case IC_IL_SAX_ABS:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data << 8) | state.temp;
                state.data = state.A & state.X;
                return state;
            case IC_LDA_IND_X:
            case IC_LDA_IND_Y:
            case IC_STA_IND_X:
            case IC_STA_IND_Y:
            case IC_ADC_IND_X:
            case IC_ADC_IND_Y:
            case IC_SBC_IND_X:
            case IC_SBC_IND_Y:
            case IC_CMP_IND_X:
            case IC_CMP_IND_Y:
            case IC_AND_IND_X:
            case IC_AND_IND_Y:
            case IC_ORA_IND_X:
            case IC_ORA_IND_Y:
            case IC_EOR_IND_X:
            case IC_EOR_IND_Y:
            case IC_IL_LAX_IND_X:
            case IC_IL_LAX_IND_Y:
            case IC_IL_SAX_IND_X:
            case IC_IL_DCP_IND_X:
            case IC_IL_DCP_IND_Y:
            case IC_IL_ISB_IND_X:
            case IC_IL_ISB_IND_Y:
            case IC_IL_SLO_IND_X:
            case IC_IL_SLO_IND_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.address + 1) & 0xFF;
                state.temp = state.data;
                return state;
            case IC_JMP:
                state.rw_mode = CPU_RW_MODE_NONE;
                state.PC = (state.data << 8) | state.temp;
                break;
            case IC_JMP_IND:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | state.temp;
                return state;
            case IC_BIT_ZP: _CPU_BIT(state); break;
            case IC_LDA_ZP: _CPU_SET_REG_A(state, state.data); break;
            case IC_LDX_ZP: _CPU_SET_REG_X(state, state.data); break;
            case IC_LDY_ZP: _CPU_SET_REG_Y(state, state.data); break;
            case IC_ADC_ZP: _CPU_ADC(state); break;
            case IC_SBC_ZP: _CPU_SBC(state); break;
            case IC_CMP_ZP: _CPU_CMP(state, state.A); break;
            case IC_CPX_ZP: _CPU_CMP(state, state.X); break;
            case IC_CPY_ZP: _CPU_CMP(state, state.Y); break;
            case IC_AND_ZP: _CPU_SET_REG_A(state, state.A & state.data); break;
            case IC_ORA_ZP: _CPU_SET_REG_A(state, state.A | state.data); break;
            case IC_EOR_ZP: _CPU_SET_REG_A(state, state.A ^ state.data); break;
            case IC_IL_LAX_ZP: _CPU_LAX(state); break;
            case IC_LDA_ZP_X:
                _CPU_SET_REG_A(state, state.data);
                return state; 
            case IC_LDY_ZP_X:
                _CPU_SET_REG_Y(state, state.data);
                return state;
            case IC_LDX_ZP_Y:
                _CPU_SET_REG_X(state, state.data);
                return state;
            case IC_IL_LAX_ZP_Y:
                _CPU_LAX(state);
                return state;
            case IC_JSR:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data = (state.PC >> 8);
                state.address = ((uint8_t)state.S--) + 0x0100;
                return state;
            case IC_RTS:
            case IC_RTI:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = ((uint8_t)++state.S) + 0x0100;
                state.temp = state.data;
                return state;
            case IC_PLA:
            case IC_PLP:
            case IC_ROL_ZP:
            case IC_ROL_ZP_X:
            case IC_ROR_ZP:
            case IC_ROR_ZP_X:
            case IC_DEC_ZP:
            case IC_DEC_ZP_X:
            case IC_INC_ZP:
            case IC_INC_ZP_X:
            case IC_ASL_ZP:
            case IC_ASL_ZP_X:
            case IC_LSR_ZP:
            case IC_LSR_ZP_X:
            case IC_STA_ZP_X:
            case IC_STX_ZP_Y:
            case IC_STY_ZP_X:
            case IC_ADC_ZP_X:
            case IC_SBC_ZP_X:
            case IC_CMP_ZP_X:
            case IC_AND_ZP_X:
            case IC_ORA_ZP_X:
            case IC_EOR_ZP_X:
            case IC_IL_NOP_ZP_X0: case IC_IL_NOP_ZP_X1: case IC_IL_NOP_ZP_X2: case IC_IL_NOP_ZP_X3: case IC_IL_NOP_ZP_X4: case IC_IL_NOP_ZP_X5:
            case IC_IL_SAX_ZP_Y:
            case IC_IL_DCP_ZP:
            case IC_IL_DCP_ZP_X:
            case IC_IL_ISB_ZP:
            case IC_IL_ISB_ZP_X:
            case IC_IL_SLO_ZP:
            case IC_IL_SLO_ZP_X:
                state.rw_mode = CPU_RW_MODE_NONE;
                // empty cycles
                return state;
            default: break;
        }
    }
    else if (cycle == 3)
    {
        switch(instruction)
        {
            case IC_BRK:
                state.data = state.P;
                if (state.nmi)
                {
                    state.nmi = 0;
                    state.temp = 0xFA;
                }
                else if (state.irq && !(state.P & CPU_STATUS_FLAG_IRQDISABLE))
                {
                    state.temp = 0xFE;
                }
                else
                {
                    state.data |= CPU_STATUS_FLAG_BREAK;
                }
                _CPU_SET_REG_P(state, state.P | CPU_STATUS_FLAG_IRQDISABLE);
                state.address = ((uint8_t)state.S--) + 0x0100;
                return state;

            case IC_LDA_ABS: _CPU_SET_REG_A(state, state.data); break;
            case IC_LDX_ABS: _CPU_SET_REG_X(state, state.data); break;
            case IC_LDY_ABS: _CPU_SET_REG_Y(state, state.data); break;
            case IC_IL_LAX_ABS: _CPU_LAX(state); break;
            case IC_ADC_ABS: case IC_ADC_ZP_X: _CPU_ADC(state); break;
            case IC_SBC_ABS: case IC_SBC_ZP_X: _CPU_SBC(state); break;
            case IC_CMP_ABS: case IC_CMP_ZP_X: _CPU_CMP(state, state.A); break;
            case IC_CPX_ABS: _CPU_CMP(state, state.X); break;
            case IC_CPY_ABS: _CPU_CMP(state, state.Y); break;
            case IC_AND_ABS: case IC_AND_ZP_X: _CPU_SET_REG_A(state, state.A & state.data); break;
            case IC_ORA_ABS: case IC_ORA_ZP_X: _CPU_SET_REG_A(state, state.A | state.data); break;
            case IC_EOR_ABS: case IC_EOR_ZP_X: _CPU_SET_REG_A(state, state.A ^ state.data); break;

            case IC_LDA_ABS_X: case IC_LDA_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SET_REG_A(state, state.data);
                break;

            case IC_LDX_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SET_REG_X(state, state.data);
                break;

            case IC_LDY_ABS_X:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SET_REG_Y(state, state.data);
                break;

            case IC_IL_LAX_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_LAX(state);
                break;

            case IC_ADC_ABS_X: case IC_ADC_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_ADC(state); 
                break;

            case IC_SBC_ABS_X: case IC_SBC_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SBC(state); 
                break;

            case IC_CMP_ABS_X: case IC_CMP_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_CMP(state, state.A);
                break;

            case IC_AND_ABS_X: case IC_AND_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SET_REG_A(state, state.A & state.data); 
                break;

            case IC_ORA_ABS_X: case IC_ORA_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SET_REG_A(state, state.A | state.data); 
                break;

            case IC_EOR_ABS_X: case IC_EOR_ABS_Y:
                _CPU_CHECK_PAGE_CROSS(state);
                _CPU_SET_REG_A(state, state.A ^ state.data); 
                break;

            case IC_STA_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address += state.temp * 0x0100;
                state.data = state.A;
                return state;

            case IC_STA_ABS_Y:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address += state.temp * 0x0100;
                state.data = state.A;
                return state;

            case IC_ROL_ABS_X:
            case IC_ROR_ABS_X:
            case IC_DEC_ABS_X:
            case IC_INC_ABS_X:
            case IC_ASL_ABS_X:
            case IC_LSR_ABS_X:
            case IC_IL_DCP_ABS_X: case IC_IL_DCP_ABS_Y: 
            case IC_IL_ISB_ABS_X: case IC_IL_ISB_ABS_Y: 
            case IC_IL_SLO_ABS_X: case IC_IL_SLO_ABS_Y: 
                state.rw_mode = CPU_RW_MODE_READ;
                state.address += state.temp * 0x0100;
                return state;

            case IC_ROL_ABS: case IC_ROL_ZP: case IC_ROL_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_ROL(state, state.data);
                return state;

            case IC_ROR_ABS: case IC_ROR_ZP: case IC_ROR_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_ROR(state, state.data);
                return state;

            case IC_DEC_ABS: case IC_DEC_ZP: case IC_DEC_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data -= 1;
                _CPU_UPDATE_NZ(state, state.data);
                return state;

            case IC_INC_ABS: case IC_INC_ZP: case IC_INC_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data += 1;
                _CPU_UPDATE_NZ(state, state.data);
                return state;

            case IC_ASL_ABS: case IC_ASL_ZP: case IC_ASL_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_ASL(state, state.data);
                return state;

            case IC_LSR_ABS: case IC_LSR_ZP: case IC_LSR_ZP_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_LSR(state, state.data);
                return state;

            case IC_IL_DCP_ABS: case IC_IL_DCP_ZP: case IC_IL_DCP_ZP_X:
                _CPU_DCP(state);
                return state;

            case IC_IL_ISB_ABS: case IC_IL_ISB_ZP: case IC_IL_ISB_ZP_X:
                _CPU_ISB(state);
                return state;

            case IC_IL_SLO_ABS: case IC_IL_SLO_ZP: case IC_IL_SLO_ZP_X:
                _CPU_SLO(state);
                return state;

            case IC_BIT_ABS:    _CPU_BIT(state); break;

            case IC_LDA_IND_X:
            case IC_ADC_IND_X:
            case IC_SBC_IND_X:
            case IC_CMP_IND_X:
            case IC_AND_IND_X:
            case IC_ORA_IND_X:
            case IC_EOR_IND_X:
            case IC_IL_LAX_IND_X:
            case IC_IL_DCP_IND_X:
            case IC_IL_ISB_IND_X:
            case IC_IL_SLO_IND_X:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | state.temp;
                return state;
            case IC_LDA_IND_Y:
            case IC_ADC_IND_Y:
            case IC_SBC_IND_Y:
            case IC_CMP_IND_Y:
            case IC_AND_IND_Y:
            case IC_ORA_IND_Y:
            case IC_EOR_IND_Y:
            case IC_IL_LAX_IND_Y:
            case IC_IL_DCP_IND_Y:
            case IC_IL_ISB_IND_Y:
            case IC_IL_SLO_IND_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | ((state.temp + state.Y) & 0xFF);
                state.temp = ((uint16_t)state.temp + (uint16_t)state.Y) >> 8;
                return state;
            case IC_STA_IND_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data << 8) | state.temp;
                state.data = state.A;
                return state;
            case IC_STA_IND_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.data << 8) | ((state.temp + state.Y) & 0xFF);
                state.temp = ((uint16_t)state.temp + (uint16_t)state.Y) >> 8;
                return state;
            case IC_IL_SAX_IND_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address = (state.data << 8) | state.temp;
                state.data = state.A & state.X;
                return state;
            case IC_JMP_IND:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = (state.address & 0xFF00) | ((state.address + 1) & 0x00FF);
                state.temp = state.data;
                return state;
            case IC_JSR:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data = state.PC & 0xFF;
                state.address = ((uint8_t)state.S--) + 0x0100;
                return state;
            case IC_RTS:
                state.rw_mode = CPU_RW_MODE_NONE;
                state.PC = ((state.data << 8) | state.temp) + 1;
                return state;
            case IC_RTI:
                state.rw_mode = CPU_RW_MODE_NONE;
                state.PC = (state.data << 8) | state.temp;
                return state;
           default: break;
        }
    }
    else if (cycle == 4)
    {
        state.rw_mode = CPU_RW_MODE_NONE;
        switch (instruction)
        {
            case IC_BRK:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = 0xFF00 | state.temp;
                return state;

             case IC_LDA_ABS_X: case IC_LDA_ABS_Y:
                _CPU_SET_REG_A(state, state.data);
                break;

            case IC_LDX_ABS_Y:
                _CPU_SET_REG_X(state, state.data);
                break;

            case IC_LDY_ABS_X:
                _CPU_SET_REG_Y(state, state.data);
                break;

            case IC_IL_LAX_ABS_Y:
                _CPU_LAX(state);
                break;

            case IC_ADC_ABS_X: case IC_ADC_ABS_Y:
                _CPU_ADC(state); 
                break;

            case IC_SBC_ABS_X: case IC_SBC_ABS_Y:
                _CPU_SBC(state); 
                break;

            case IC_CMP_ABS_X: case IC_CMP_ABS_Y:
                _CPU_CMP(state, state.A);
                break;

            case IC_AND_ABS_X: case IC_AND_ABS_Y:
                _CPU_SET_REG_A(state, state.A & state.data); 
                break;

            case IC_ORA_ABS_X: case IC_ORA_ABS_Y:
                _CPU_SET_REG_A(state, state.A | state.data); 
                break;

            case IC_EOR_ABS_X: case IC_EOR_ABS_Y:
                _CPU_SET_REG_A(state, state.A ^ state.data); 
                break;

            case IC_ROL_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_ROL(state, state.data);
                return state;

            case IC_ROR_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_ROR(state, state.data);
                return state;

            case IC_DEC_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data -= 1;
                _CPU_UPDATE_NZ(state, state.data);
                return state;

            case IC_INC_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.data += 1;
                _CPU_UPDATE_NZ(state, state.data);
                return state;

            case IC_ASL_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_ASL(state, state.data);
                return state;

            case IC_LSR_ABS_X:
                state.rw_mode = CPU_RW_MODE_WRITE;
                _CPU_LSR(state, state.data);
                return state;

            case IC_IL_DCP_ABS_X: case IC_IL_DCP_ABS_Y:
                _CPU_DCP(state);
                return state;

            case IC_IL_ISB_ABS_X: case IC_IL_ISB_ABS_Y:
                _CPU_ISB(state);
                return state;

            case IC_IL_SLO_ABS_X: case IC_IL_SLO_ABS_Y:
                _CPU_SLO(state);
                return state;
               
            case IC_LDA_IND_X: _CPU_SET_REG_A(state, state.data); return state;
            case IC_ADC_IND_X: _CPU_ADC(state); return state;
            case IC_SBC_IND_X: _CPU_SBC(state); return state;
            case IC_CMP_IND_X: _CPU_CMP(state, state.A); return state;
            case IC_AND_IND_X: _CPU_SET_REG_A(state, state.A & state.data); return state;
            case IC_ORA_IND_X: _CPU_SET_REG_A(state, state.A | state.data); return state;
            case IC_EOR_IND_X: _CPU_SET_REG_A(state, state.A ^ state.data); return state;
            case IC_IL_LAX_IND_X: _CPU_LAX(state); return state;

            case IC_LDA_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_SET_REG_A(state, state.data); break;
            case IC_ADC_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_ADC(state); break;
            case IC_SBC_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_SBC(state); break;
            case IC_CMP_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_CMP(state, state.A); break;
            case IC_AND_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_SET_REG_A(state, state.A & state.data); break;
            case IC_ORA_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_SET_REG_A(state, state.A | state.data); break;
            case IC_EOR_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_SET_REG_A(state, state.A ^ state.data); break;
            case IC_IL_LAX_IND_Y: _CPU_CHECK_PAGE_CROSS(state); _CPU_LAX(state); break;

            case IC_STA_IND_Y:
                state.rw_mode = CPU_RW_MODE_WRITE;
                state.address += state.temp * 0x0100;
                state.data = state.A;
                return state;

            case IC_JMP_IND:
                state.PC = (state.data << 8) | state.temp;
                break;
            case IC_JSR:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address = state.PC;
                return state;

            case IC_IL_DCP_IND_X: _CPU_DCP(state); return state;
            case IC_IL_ISB_IND_X: _CPU_ISB(state); return state;
            case IC_IL_SLO_IND_X: _CPU_SLO(state); return state;

            case IC_IL_DCP_IND_Y:
            case IC_IL_ISB_IND_Y:
            case IC_IL_SLO_IND_Y:
                state.rw_mode = CPU_RW_MODE_READ;
                state.address += state.temp * 0x0100;
                return state;

            case IC_ROL_ABS: case IC_ROL_ZP_X:
            case IC_ROR_ABS: case IC_ROR_ZP_X:
            case IC_DEC_ABS: case IC_DEC_ZP_X:
            case IC_INC_ABS: case IC_INC_ZP_X:
            case IC_ASL_ABS: case IC_ASL_ZP_X:
            case IC_LSR_ABS: case IC_LSR_ZP_X:
            case IC_STA_IND_X:
            case IC_IL_SAX_IND_X:
            case IC_IL_DCP_ABS: case IC_IL_DCP_ZP_X:
            case IC_IL_ISB_ABS: case IC_IL_ISB_ZP_X:
            case IC_IL_SLO_ABS: case IC_IL_SLO_ZP_X:
            case IC_RTS:
            case IC_RTI:
                state.rw_mode = CPU_RW_MODE_NONE;
                // empty cycles
                return state;
            default: break;
        }
    }
    else if (cycle == 5)
    {
        state.rw_mode = CPU_RW_MODE_NONE;
        switch (instruction)
        {
            case IC_BRK:
                state.rw_mode = CPU_RW_MODE_READ;
                state.PC = state.data;
                state.address += 1;
                return state;
            case IC_JSR:
                state.PC = (state.data << 8) | state.temp;
                break;

            case IC_IL_DCP_IND_Y: _CPU_DCP(state); return state;
            case IC_IL_ISB_IND_Y: _CPU_ISB(state); return state;
            case IC_IL_SLO_IND_Y: _CPU_SLO(state); return state;

            case IC_ROL_ABS_X:
            case IC_ROR_ABS_X:
            case IC_DEC_ABS_X:
            case IC_INC_ABS_X:
            case IC_ASL_ABS_X:
            case IC_LSR_ABS_X:
            case IC_IL_DCP_ABS_X: case IC_IL_DCP_ABS_Y: case IC_IL_DCP_IND_X:
            case IC_IL_ISB_ABS_X: case IC_IL_ISB_ABS_Y: case IC_IL_ISB_IND_X:
            case IC_IL_SLO_ABS_X: case IC_IL_SLO_ABS_Y: case IC_IL_SLO_IND_X:
                state.rw_mode = CPU_RW_MODE_NONE;
                // empty cycle
                return state;

            /* Executed if page-cross */
            case IC_LDA_IND_Y: _CPU_SET_REG_A(state, state.data); break;
            case IC_ADC_IND_Y: _CPU_ADC(state); break;
            case IC_SBC_IND_Y: _CPU_SBC(state); break;
            case IC_CMP_IND_Y: _CPU_CMP(state, state.A); break;
            case IC_AND_IND_Y: _CPU_SET_REG_A(state, state.A & state.data); break;
            case IC_ORA_IND_Y: _CPU_SET_REG_A(state, state.A | state.data); break;
            case IC_EOR_IND_Y: _CPU_SET_REG_A(state, state.A ^ state.data); break;
            case IC_IL_LAX_IND_Y: _CPU_LAX(state); break;
        }
    }
    else if (cycle == 6)
    {
        switch(instruction)
        {
            case IC_BRK:
                state.PC = (state.data << 8) | state.PC;
                break;
            case IC_IL_DCP_IND_X: case IC_IL_DCP_IND_Y:
            case IC_IL_ISB_IND_X: case IC_IL_ISB_IND_Y:
            case IC_IL_SLO_IND_X: case IC_IL_SLO_IND_Y:
                return state;
        }
    }

    if (state.nmi || (state.irq && !(state.P & CPU_STATUS_FLAG_IRQDISABLE)))
    {
        state.rw_mode = CPU_RW_MODE_NONE;
        state.cycle = 0;
        state.data = 0;
        return state;
    }

    state.cycle = 0;
    state.rw_mode = CPU_RW_MODE_READ;
    state.address = state.PC++;
    return state;
}

#endif
