# Quick HX711 demo with display
#
# Pins:
#   * D6: HX711 SCK
#   * D5: HX711 DOUT
#
# I2C:
#   * 0x37: Adafruit 0.91" OLED Display <https://www.adafruit.com/product/4440>

import time
import board
import digitalio
import displayio
import adafruit_displayio_ssd1306
from adafruit_display_text import label
import terminalio
from hx711 import HX711

hx_sck = digitalio.DigitalInOut(board.D6)
hx_sck.switch_to_output()

hx_dout = digitalio.DigitalInOut(board.D5)
hx_dout.switch_to_input()

hx = HX711(hx_dout, hx_sck)
hx.power_on()

displayio.release_displays()

i2c = board.I2C()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)

HEIGHT = 32
WIDTH = 128

display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

splash = displayio.Group()
display.show(splash)

color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x000000

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader = color_palette, x=0, y=0)
splash.append(bg_sprite)

text_hx = "HX: {:8}"
text_area = label.Label(terminalio.FONT, text=text_hx.format(0), color=0xFFFFFF, x=28, y=HEIGHT // 2 - 1)
splash.append(text_area)

while True:
    read = hx.read()
    print("HX Read: {}".format(read))
    text_area.text = text_hx.format(read)
    time.sleep(1)