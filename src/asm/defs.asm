; ------------------------------------------------------------------------------
; memory address values
ENUM $0

BASE $BC
current_level:

BASE $BD
current_world:

BASE $72
current_lives:

BASE $71
game_state: ; 01 -> normal, 05 -> star-spin flying?

BASE $6F
game_state_b: ; bit 7: hard mode. bit 6: hell mode.

BASE $D0
camera_speed:

BASE $7F
item_drop_counter:

; -----------------------------------------------------------------------------

; buffer of length 0x20. First four entries are reserved for the players.
BASE $200
object_ids:

; object x:
BASE $4A
object_x: 

BASE $360
object_y: 

BASE $2E0
object_state_a:

BASE $3F0
object_state_b:

; used as a timer by skeleton
BASE $300
object_state_c:

BASE $2A0
object_yspeed_int:

BASE $2C0
object_yspeed_frac:

BASE $260
object_xspeed_int:

BASE $280
object_xspeed_frac:

BASE $440
object_hp:

; ------------------------------------------------------------------------------
; music

BASE $17
mus_tempo: ; number of frames between notes.

BASE $18
mus_tempo_timer: ; current frame mod mus_tempo.

BASE $4C4
mus_current_song:

; these are each arrays of length 6. The first 4 indices are for each channel, the second two are for sfx.

; the following two define the current "nibble" position of the track, as an offset in nibbles BASE $8000.
BASE $466
mus_pattern_l:
BASE $46C
mus_pattern_u:

; how many tempo units to wait until proceeding to next command.
BASE $472
mus_wait:

; second nibble is remaining duration this note will be held for (in frames). F means no release.
BASE $478
mus_hold_duration:

BASE $47E
mus_note_articulation: ; the style of note articulation used.

BASE $484
mus_pitch_l: ; the pitch for this note (least-significant digits)

BASE $48a
mus_pitch_h: ; the pitch for this note (most-significant digit)

BASE $490
mus_dynamics: ; the dynamics (volume) for this note

BASE $496
mus_key: ; this is transforms (adds to?) the note's pitch. Effectively, this is the "key" of the current pattern.

BASE $49C
mus_slide: ; this is a slide effect applied to the note

BASE $4A2
mus_var8:

; number of times current "repeat" section has executed.
BASE $4A8
mus_repeat_idx:

; return address for music subroutine
BASE $4AE
mus_reta_l:
BASE $4B2
mus_reta_u:

; these are each arrays of length 4
BASE $4B2
mus_var9:

; the number of times the subroutine has repeated.
BASE $4B6
mus_subrepeat_idx:

; unknown
; every note played, this resets to 0 and increments until a cap.
BASE $4BA
mus_varC:

BASE $4C6
mus_varD:

; length not known
BASE $4CA
mus_varE:

; the amount of time this note has been playing so far
; every note, this resets to 0.
BASE $4BE
mus_note_timer:

BASE $4F5
mus_varA:

BASE $4F9
mus_varB:

; ------------------------------------------------------------------------------

; points to next 4 (8 when mirrored) macro-tiles.
BASE $C0
level_data:

; when loading macro tiles, this value stores the seam (mirror) position.
; this address has other uses too.
BASE $E3
seam_accumulator:

; these contain the minitile data per medtile.
BASE $EB
medtile_data_a:

BASE $ED
medtile_data_b:

BASE $EF
medtile_data_c:

BASE $F1
medtile_data_d:

ENDE