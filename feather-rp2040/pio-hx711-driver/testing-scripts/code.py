import board
from digitalio import DigitalInOut

from oled import OLED
oled = OLED()

oled.text_area.text = "Init..."

mode = "GPIO"
# mode = "PIO"

hx = None
if mode == "GPIO":
    import hx711.hx711_gpio as hx711_gpio

    dio_data = DigitalInOut(board.D5)
    dio_clk = DigitalInOut(board.D6)

    hx = hx711_gpio.HX711_GPIO(dio_data, dio_clk, gain=1, scalar=403, tare=True)
elif mode == "PIO":
    import hx711.hx711_pio as hx711_pio

    pin_data = board.D5
    pin_clk = board.D6

    hx = hx711_pio.HX711_PIO(pin_data, pin_clk, scalar=403, tare=True)

print("init, offset: {}, scalar: {}".format(hx.offset, hx.scalar))

while True:
    reading = hx.read(5)
    reading_raw = hx.read_raw()
    print("[{: 8.2f} g] [{: 8} raw] offset: {}, scalar: {}".format(reading, reading_raw, hx.offset, hx.scalar))
    oled.text_area.text = oled.text_hx.format(reading)