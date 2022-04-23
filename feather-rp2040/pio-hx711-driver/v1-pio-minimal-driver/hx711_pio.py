import rp2pio
import adafruit_pioasm
import array
from digitalio import DigitalInOut
from micropython import const

hx711_read_code = """
set x, {0}      ; number of cycles for post-readout gain setting
mov osr, x      ; put the gain into osr for safe keeping
set x, 7        ; number of pad bits, 0-start
set y, {1}      ; number of data bits, 0-start

padloop:        ; build front-pad bits for 32-bit Pythonic int alignment
    in pins, 1
    jmp x-- padloop

wait 0 pin 0    ; wait for the hx711 DAC's cycle-complete signal

mov x, osr      ; set up our gain loop counter, also delays first clock edge by a full cycle

bitloop:        ; read in those bits!
    set pins, 1 [3]
    set pins, 0 [1]
    in pins, 1
    jmp y-- bitloop

gainloop:       ; gain set, 1 pulse for default gain
    set pins, 1 [3]
    set pins, 0
    jmp x-- gainloop
"""

HX_DATA_BITS = const(24)
HX_INIT_DELAY = const(10)

HX_MAX_VALUE = const(0x7FFFFF)
PAD_MASK = const(0x00FFFFFF)
COMPLMENT_MASK = const(0x1000000)

class HX711_PIO():

    def __init__(
            self, 
            pin_data: DigitalInOut,
            pin_clk: DigitalInOut,
            gain: int = 1, 
            offset: int = 0,
            avg_reads: int = 8,
            pio_freq: int = 4000000
        ):

        self._buffer = array.array('I', [0])

        self._pin_data = pin_data
        self._pin_clk = pin_clk
        self.gain = gain
        self.offset = offset
        self.avg_reads = avg_reads
        self._pio_freq = pio_freq

        self._pioasm_read = adafruit_pioasm.assemble(
            hx711_read_code.format(self.gain - 1, HX_DATA_BITS - 1))

        self._sm = rp2pio.StateMachine(
            self._pioasm_read,
            frequency=self._pio_freq,
            first_in_pin=self._pin_data,
            in_pin_count=1,
            first_set_pin=self._pin_clk,
            set_pin_count=1,
            in_shift_right=False,
            push_threshold=32,
            auto_push=True
        )

    def read_raw(self):
        self._sm.readinto(self._buffer)
        reading_aligned = self._buffer[0] & PAD_MASK   # Mask out our pad bits
        
        if reading_aligned > HX_MAX_VALUE:             # Handle two's compliment negative numbers
            reading_aligned -= COMPLMENT_MASK

        return reading_aligned