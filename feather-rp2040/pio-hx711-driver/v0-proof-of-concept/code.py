import board
import rp2pio
import adafruit_pioasm
import array

pin_dout = board.D5
pin_dclk = board.D6

hx_gain = 1
hx_bits = 24
hx_init_delay = 10

hx711_init_code = """
set x, {0}       ; 0-start, 24 pulses for a read, additional pulses set gain

initloop:        ; Clock out a read pulse + gain frame to prime the sensor
    set pins, 1 [2]
    set pins, 0 [2]
    jmp x-- initloop

nop [{1}]
""".format(hx_bits + hx_gain - 1, hx_init_delay)

hx711_read_code = """
set x, {0}      ; number of cycles for post-readout gain setting
mov osr, x      ; put the gain into osr for safe keeping
set x, 7        ; number of pad bits, 0-start
set y, {1}      ; number of data bits, 0-start

padloop:        ; build front-pad bits
    in pins, 1
    jmp x-- padloop

wait 0 pin 0    ; wait for the hx711 DAC to complete a cycle

bitloop:        ; read in those bits!
    set pins, 1 [2]
    set pins, 0 [1]
    in pins, 1
    jmp y-- bitloop

mov x, osr
gainloop:       ; gain set, 1 pulse for default gain
    set pins, 1 [1]
    set pins, 0
    jmp x-- gainloop
""".format(hx_gain - 1, hx_bits - 1)

pioasm_init = adafruit_pioasm.assemble(hx711_init_code)
pioasm_asm = adafruit_pioasm.assemble(hx711_read_code)

sm = rp2pio.StateMachine(
    pioasm_asm,
    frequency=2000000,
    init=pioasm_init,
    first_in_pin=pin_dout,
    in_pin_count=1,
    first_set_pin=pin_dclk,
    set_pin_count=1,
    in_shift_right=False,
    push_threshold=32,
    auto_push=True
)

arr_buffer = array.array('I', [0])

while True:

    sm.readinto(arr_buffer)
    reading_aligned = arr_buffer[0] & 0x00FFFFFF # Drop our front-padding
    if reading_aligned > 0x7FFFFF:    # Handle negative two's compliment numbers
        reading_aligned -= 0x1000000

    if (arr_buffer[0] & 0xFF000000) == 0xFF000000:
        print("* [{0:032b}] {0} [{1:032b}] {1}".format(arr_buffer[0], reading_aligned))
    else:
        print("X [{0:032b}] {0} [{1:032b}] {1}".format(arr_buffer[0], reading_aligned))