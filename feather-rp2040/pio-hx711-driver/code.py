
import board
import hx711.hx711_pio as hx711_pio
import hx711.hx711_gpio as hx711_gpio
from digitalio import DigitalInOut

# pin_data = board.D5
# pin_clk = board.D6

# hx = hx711_pio.HX711_PIO(pin_data, pin_clk, scale=416, tare=True)

dio_data = DigitalInOut(board.D5)
dio_clk = DigitalInOut(board.D6)

hx = hx711_gpio.HX711_GPIO(dio_data, dio_clk, scale=416, tare=True)

print("init, offset: {}, scale: {}".format(hx.offset, hx.scale))

while True:
    print("[{: 8.2f}] offset: {}, scale: {}".format(hx.read(1), hx.offset, hx.scale))