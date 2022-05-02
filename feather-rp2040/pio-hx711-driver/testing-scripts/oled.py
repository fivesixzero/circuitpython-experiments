import displayio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import terminalio
import board


class OLED():

    def __init__(self, i2c = None):

        displayio.release_displays()

        if not i2c:
            i2c = board.I2C()

        self.display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)

        HEIGHT = 32
        WIDTH = 128

        self.display = adafruit_displayio_ssd1306.SSD1306(self.display_bus, width=WIDTH, height=HEIGHT)
        self.display.brightness = 0.1

        self.splash = displayio.Group()
        self.display.show(self.splash)

        self.color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
        self.color_palette = displayio.Palette(1)
        self.color_palette[0] = 0x000000

        self.bg_sprite = displayio.TileGrid(self.color_bitmap, pixel_shader = self.color_palette, x=0, y=0)
        self.splash.append(self.bg_sprite)

        self.text_hx = "{: 8.2f} g"
        self.text_area = label.Label(terminalio.FONT, scale=2, text=self.text_hx.format(0), color=0xFFFFFF, x=WIDTH // 2 - 1, y=HEIGHT // 2 - 1)
        self.text_area.anchor_point = (0.5, 0.5)
        self.text_area.anchored_position = (WIDTH // 2 - 1, HEIGHT // 2 - 1)
        self.splash.append(self.text_area)