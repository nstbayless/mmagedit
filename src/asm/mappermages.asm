# UxROM mapper patch
# (WIP)

BANK 3
BASE $C000

FROM $DAEC
new_reset_vector:
    lda #$0
    sta $fff8
    jmp $9957 # jump to old entry point

FROM $DAF4
# bank swap?
unknown_a:
    lda #$1
    sta $ffe8
    ldy #$0
    lda ($c0), y
    sty $fff8
    rts

# TODO...

# reset vector
FROM $FFFC
    dw new_reset_vector