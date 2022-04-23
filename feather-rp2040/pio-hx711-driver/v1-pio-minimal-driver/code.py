# Minimal HX711 driver demo

import board
from hx711_pio import HX711_PIO

pin_data = board.D5
pin_clk = board.D6

hx711 = HX711_PIO(pin_data, pin_clk)

while True:
    print(hx711.read_raw())