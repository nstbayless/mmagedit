#ifndef _EMU6502_OPCODES_H_
#define _EMU6502_OPCODES_H_

#define IC_BRK      0x00

#define IC_PHP      0x08
#define IC_PHA      0x48
#define IC_PLP      0x28
#define IC_PLA      0x68

#define IC_INX      0xE8
#define IC_INY      0xC8
#define IC_DEX      0xCA
#define IC_DEY      0x88

#define IC_TAX      0xAA
#define IC_TAY      0xA8
#define IC_TSX      0xBA
#define IC_TXA      0x8A
#define IC_TXS      0x9A
#define IC_TYA      0x98

#define IC_CLC      0x18
#define IC_SEC      0x38
#define IC_CLI      0x58
#define IC_SEI      0x78
#define IC_CLV      0xB8
#define IC_CLD      0xD8
#define IC_SED      0xF8

#define IC_NOP      0xEA

#define IC_BCC      0x90
#define IC_BCS      0xB0
#define IC_BNE      0xD0
#define IC_BEQ      0xF0
#define IC_BVC      0x50
#define IC_BVS      0x70
#define IC_BPL      0x10
#define IC_BMI      0x30

#define IC_JMP      0x4C
#define IC_JMP_IND  0x6C

#define IC_BIT_ABS  0x2C
#define IC_BIT_ZP   0x24
#define IC_LDA_IMM      0xA9
#define IC_LDA_ABS      0xAD
#define IC_LDA_ABS_X    0xBD
#define IC_LDA_ABS_Y    0xB9
#define IC_LDA_ZP       0xA5
#define IC_LDA_ZP_X     0xB5
#define IC_LDA_IND_X    0xA1
#define IC_LDA_IND_Y    0xB1

#define IC_LDX_IMM      0xA2
#define IC_LDX_ABS      0xAE
#define IC_LDX_ABS_Y    0xBE
#define IC_LDX_ZP       0xA6
#define IC_LDX_ZP_Y     0xB6
#define IC_LDY_IMM      0xA0
#define IC_LDY_ABS      0xAC
#define IC_LDY_ABS_X    0xBC
#define IC_LDY_ZP       0xA4
#define IC_LDY_ZP_X     0xB4

#define IC_STA_ABS      0x8D
#define IC_STA_ABS_X    0x9D
#define IC_STA_ABS_Y    0x99
#define IC_STA_ZP       0x85
#define IC_STA_ZP_X     0x95
#define IC_STA_IND_X    0x81
#define IC_STA_IND_Y    0x91

#define IC_STX_ABS      0x8E
#define IC_STX_ZP       0x86
#define IC_STX_ZP_Y     0x96

#define IC_STY_ABS      0x8C
#define IC_STY_ZP       0x84
#define IC_STY_ZP_X     0x94

#define IC_ROL_ABS      0x2E
#define IC_ROL_ABS_X    0x3E
#define IC_ROL_ZP       0x26
#define IC_ROL_ZP_X     0x36
#define IC_ROL_ACC      0x2A

#define IC_ROR_ABS      0x6E
#define IC_ROR_ABS_X    0x7E
#define IC_ROR_ZP       0x66
#define IC_ROR_ZP_X     0x76
#define IC_ROR_ACC      0x6A

#define IC_DEC_ABS      0xCE
#define IC_DEC_ABS_X    0xDE
#define IC_DEC_ZP       0xC6
#define IC_DEC_ZP_X     0xD6

#define IC_INC_ABS      0xEE
#define IC_INC_ABS_X    0xFE
#define IC_INC_ZP       0xE6
#define IC_INC_ZP_X     0xF6

#define IC_ASL_ABS      0x0E
#define IC_ASL_ABS_X    0x1E
#define IC_ASL_ZP       0x06
#define IC_ASL_ZP_X     0x16
#define IC_ASL_ACC      0x0A

#define IC_LSR_ABS      0x4E
#define IC_LSR_ABS_X    0x5E
#define IC_LSR_ZP       0x46
#define IC_LSR_ZP_X     0x56
#define IC_LSR_ACC      0x4A

#define IC_AND_IMM      0x29
#define IC_AND_ABS      0x2D
#define IC_AND_ABS_X    0x3D
#define IC_AND_ABS_Y    0x39
#define IC_AND_ZP       0x25
#define IC_AND_ZP_X     0x35
#define IC_AND_IND_X    0x21
#define IC_AND_IND_Y    0x31
#define IC_ORA_IMM      0x09
#define IC_ORA_ABS      0x0D
#define IC_ORA_ABS_X    0x1D
#define IC_ORA_ABS_Y    0x19
#define IC_ORA_ZP       0x05
#define IC_ORA_ZP_X     0x15
#define IC_ORA_IND_X    0x01
#define IC_ORA_IND_Y    0x11
#define IC_EOR_IMM      0x49
#define IC_EOR_ABS      0x4D
#define IC_EOR_ABS_X    0x5D
#define IC_EOR_ABS_Y    0x59
#define IC_EOR_ZP       0x45
#define IC_EOR_ZP_X     0x55
#define IC_EOR_IND_X    0x41
#define IC_EOR_IND_Y    0x51

#define IC_ADC_IMM      0x69
#define IC_ADC_ABS      0x6D
#define IC_ADC_ABS_X    0x7D
#define IC_ADC_ABS_Y    0x79
#define IC_ADC_ZP       0x65
#define IC_ADC_ZP_X     0x75
#define IC_ADC_IND_X    0x61
#define IC_ADC_IND_Y    0x71
#define IC_SBC_IMM      0xE9
#define IC_SBC_ABS      0xED
#define IC_SBC_ABS_X    0xFD
#define IC_SBC_ABS_Y    0xF9
#define IC_SBC_ZP       0xE5
#define IC_SBC_ZP_X     0xF5
#define IC_SBC_IND_X    0xE1
#define IC_SBC_IND_Y    0xF1

#define IC_CMP_IMM      0xC9
#define IC_CMP_ABS      0xCD
#define IC_CMP_ABS_X    0xDD
#define IC_CMP_ABS_Y    0xD9
#define IC_CMP_ZP       0xC5
#define IC_CMP_ZP_X     0xD5
#define IC_CMP_IND_X    0xC1
#define IC_CMP_IND_Y    0xD1
#define IC_CPX_IMM      0xE0
#define IC_CPX_ABS      0xEC
#define IC_CPX_ZP       0xE4
#define IC_CPY_IMM      0xC0
#define IC_CPY_ABS      0xCC
#define IC_CPY_ZP       0xC4

#define IC_JSR      0x20

#define IC_RTS      0x60
#define IC_RTI      0x40

// Illegal codes
#define IC_IL_NOP_ZP0        0x04
#define IC_IL_NOP_ZP1        0x44
#define IC_IL_NOP_ZP2        0x64
#define IC_IL_NOP_ABS        0x0C
#define IC_IL_NOP_ABS_X0     0x1C
#define IC_IL_NOP_ABS_X1     0x3C
#define IC_IL_NOP_ABS_X2     0x5C
#define IC_IL_NOP_ABS_X3     0x7C
#define IC_IL_NOP_ABS_X4     0xDC
#define IC_IL_NOP_ABS_X5     0xFC
#define IC_IL_NOP_ZP_X0      0x14
#define IC_IL_NOP_ZP_X1      0x34
#define IC_IL_NOP_ZP_X2      0x54
#define IC_IL_NOP_ZP_X3      0x74
#define IC_IL_NOP_ZP_X4      0xD4
#define IC_IL_NOP_ZP_X5      0xF4
#define IC_IL_NOP_IMM0       0x1A
#define IC_IL_NOP_IMM1       0x3A
#define IC_IL_NOP_IMM2       0x5A
#define IC_IL_NOP_IMM3       0x7A
#define IC_IL_NOP_IMM4       0xDA
#define IC_IL_NOP_IMM5       0xFA
#define IC_IL_NOP_IMP0       0x80
#define IC_IL_NOP_IMP1       0x82
#define IC_IL_NOP_IMP2       0x89
#define IC_IL_NOP_IMP3       0xC2
#define IC_IL_NOP_IMP4       0xE2

#define IC_IL_LAX_ABS        0xAF
#define IC_IL_LAX_ABS_Y      0xBF
#define IC_IL_LAX_ZP         0xA7
#define IC_IL_LAX_ZP_Y       0xB7
#define IC_IL_LAX_IND_X      0xA3
#define IC_IL_LAX_IND_Y      0xB3

#define IC_IL_SAX_ABS        0x8F
#define IC_IL_SAX_ZP         0x87
#define IC_IL_SAX_ZP_Y       0x97
#define IC_IL_SAX_IND_X      0x83

#define IC_IL_SBC_IMM        0xEB

#define IC_IL_DCP_ABS        0xCF
#define IC_IL_DCP_ABS_X      0xDF
#define IC_IL_DCP_ABS_Y      0xDB
#define IC_IL_DCP_ZP         0xC7
#define IC_IL_DCP_ZP_X       0xD7
#define IC_IL_DCP_IND_X      0xC3
#define IC_IL_DCP_IND_Y      0xD3

#define IC_IL_ISB_ABS        0xEF 
#define IC_IL_ISB_ABS_X      0xFF
#define IC_IL_ISB_ABS_Y      0xFB
#define IC_IL_ISB_ZP         0xE7
#define IC_IL_ISB_ZP_X       0xF7
#define IC_IL_ISB_IND_X      0xE3
#define IC_IL_ISB_IND_Y      0xF3

#define IC_IL_SLO_ABS        0x0F
#define IC_IL_SLO_ABS_X      0x1F
#define IC_IL_SLO_ABS_Y      0x1B
#define IC_IL_SLO_ZP         0x07
#define IC_IL_SLO_ZP_X       0x17
#define IC_IL_SLO_IND_X      0x03
#define IC_IL_SLO_IND_Y      0x13


#endif
