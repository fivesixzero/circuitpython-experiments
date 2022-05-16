# HX711 EPD Scale

Scratchpad for code written while building a simple HX711-based scale with an e-paper display, specifically the [Adafruit 2.9" E-Ink Tri-Color FeatherWing](https://www.adafruit.com/product/4778).

# Setup

* [Adafruit 2.9" E-Ink Tri-Color FeatherWing](https://www.adafruit.com/product/4778)
    * Mounted to a custom-designed 3D-printed chassis 
* [`RP2040 Feather`](https://www.adafruit.com/product/4884)
    * Mounted on FeatherWing
* [`HX711`](https://www.google.com/search?q=hx711+breakout+board) ADC
    * DOUT to `D25`, SCK to `D24`
* [`5 Kg 4-wire Strain Gauge Load Cell](https://www.adafruit.com/product/4541)
    * Directly connected to HX711
    * Crimped a 4-pin JST-PH header on to the load cell wires
    * Soldered a 4-pin JST-PH socket on to the HX711
    * Mounted to a custom 3D-printed baseplate and "adapter" plate for attaching a [Prusa MINI+ Spoolholder](https://help.prusa3d.com/guide/6-spool-holder-assembly_204973).
* [`PCF8523`](https://www.adafruit.com/product/5189) RTC  (Optional)
    * Via STEMMA-QT
* [`Adafruit Push-Button Power Switch Breakout`](https://www.adafruit.com/product/1400) between a LiPo 400mA battery and the Feather RP2040's battery input

FeatherWing `BUSY` pad can be soldered to an unused pin (like `D4`, maybe) to make display refreshes more useful

# References

## 2.9" E-Ink FeatherWing Pinouts

```python
hx_pio_data = board.D25
hx_pio_clk = board.D24

key_a = board.D11
key_b = board.D12
key_c = board.D13

epd_sd_cs = board.D5
epd_sram_cs = board.D6
epd_cs = board.D9
epd_dc = board.D10

# epd_busy = board.D4  # Optional, requires manual connection on FeatherWing
```

[<img src="https://cdn-learn.adafruit.com/assets/assets/000/104/601/medium640/eink___epaper_Pinouts_2.9.jpg?1631640290" width="450">](https://cdn-learn.adafruit.com/assets/assets/000/104/601/original/eink___epaper_Pinouts_2.9.jpg?1631640290)

[<img src="https://cdn-learn.adafruit.com/assets/assets/000/107/203/medium640/adafruit_products_feather-rp2040-pins.png?1639162603" width="450">](https://cdn-learn.adafruit.com/assets/assets/000/107/203/original/adafruit_products_feather-rp2040-pins.png?1639162603)

## 2.9" E-Ink Links

* [Learn Guide](https://learn.adafruit.com/adafruit-2-9-eink-display-breakouts-and-featherwings)
* [PCB Files](https://github.com/adafruit/Adafruit-E-Paper-Display-Breakout-PCBs)
* [`IL0376F` Datasheet](https://cdn-learn.adafruit.com/assets/assets/000/057/648/original/IL0376F.pdf)
* [`IL0373` CircuitPython Driver]()

<https://github.com/adafruit/Adafruit_CircuitPython_IL0373>

## CircuitPython `EPaperDisplay` class definition

<https://github.com/adafruit/circuitpython/blob/main/shared-bindings/displayio/EPaperDisplay.c>

## HX711 CircuitPython Community Bundle Driver

<https://github.com/fivesixzero/CircuitPython_HX711/>

## UI Layout

```python
# Basic init
spi = board.SPI()

displayio.release_displays()
display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)

# Display properties
WIDTH = 296
HEIGHT = 128
ROTATION = 270
TEXT_SCALE = 4

BG_COLOR = 0xFFFFFF  # white background
TEXT_COLOR = 0x000000  # black text
HIGHLIGHT_COLOR = 0xFF0000

# Positioning typo eliminators :joy:
TOP_LEFT = (0.0, 0.0)
TOP_CENTER = (0.5, 0.0)
TOP_RIGHT = (1.0, 0.0)

BOTTOM_LEFT = (0.0, 1.0)
BOTTOM_CENTER = (0.5, 1.0)
BOTTOM_RIGHT = (1.0, 1.0)

CENTER_CENTER = (0.5, 0.5)

# X positions of buttons along the top of the display for labels
XPOS_BUTTON_A = 47
XPOS_BUTTON_B = (WIDTH // 2) - 12
XPOS_BUTTON_C = (WIDTH - XPOS_BUTTON_A) - 25

# Init display

# Create the display object - the third color is red (0xff0000)
display = adafruit_il0373.IL0373(
    display_bus,
    width=WIDTH,
    height=HEIGHT,
    rotation=ROTATION,
    # busy_pin=epd_busy,
    highlight_color=HIGHLIGHT_COLOR,
)

font = terminalio.FONT

splash = displayio.Group()
display.show(splash)

# Build display background
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
bg_palette = displayio.Palette(3)
bg_palette[0] = BG_COLOR
bg_palette[1] = TEXT_COLOR
bg_palette[2] = HIGHLIGHT_COLOR
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)

# Add UI lines: top/bottom title/status
for x in range(0, display.width):
    bg_bitmap[x, 14] = 1
    bg_bitmap[x, display.height - 14] = 1

splash.append(bg_sprite)

# Title on bottom line
title_text = "HX711 Filament Scale"
status_center = label.Label(
    font,
    text=title_text,
    color=HIGHLIGHT_COLOR,
    scale=1,
    anchor_point = (0.5, 1.0),
    anchored_position = (display.width / 2, display.height)
)
splash.append(status_center)

# Buttons on top row
button_a_label = label.Label(
    font,
    text="WEIGH",
    color=TEXT_COLOR,
    anchor_point=TOP_CENTER,
    anchored_position=(XPOS_BUTTON_A, -1)
)
splash.append(button_a_label)

button_b_label = label.Label(
    font,
    text="DEBUG",
    color=TEXT_COLOR,
    anchor_point=TOP_CENTER,
    anchored_position=(XPOS_BUTTON_B, -1)
)
splash.append(button_b_label)

button_c_label = label.Label(
    font,
    text="TARE",
    color=TEXT_COLOR,
    anchor_point=TOP_CENTER,
    anchored_position=(XPOS_BUTTON_C, -1)
)
splash.append(button_c_label)

# Debug data on corners
status_left = label.Label(
    font,
    text=" "*10,
    color=TEXT_COLOR,
    anchor_point=BOTTOM_LEFT,
    anchored_position=(1, display.height)
)
splash.append(status_left)

status_right = label.Label(
    font,
    text=" "*10,
    color=TEXT_COLOR,
    anchor_point=BOTTOM_RIGHT,
    anchored_position=(display.width-1, display.height)
)
splash.append(status_right)

# Center text (TEST)
text_area = label.Label(
    font,
    text="Hello World!",
    color=TEXT_COLOR,
    scale=TEXT_SCALE,
    anchor_point=CENTER_CENTER,
    anchored_position=(display.width // 2, display.height // 2),
)
splash.append(text_area)
```

## `PCF8523` RTC

This is basically a thin wrapper around `adafruit_register` I2C register implementations, which is pretty neat actually.

The alarm uses `i2c_bcd_alarm`.

<https://github.com/adafruit/Adafruit_CircuitPython_Register/blob/main/adafruit_register/i2c_bcd_alarm.py>

Configuring an alarm requires both a time/date and a frequency.

```python
rtc.alarm = (alarm_datetime, "Hourly")
```

TODO: Set up RTC to auto-refresh EPD regularly

## Prusa MINI+ Spoolholder

<img src="https://cdn.help.prusa3d.com/wp-content/uploads/2021/01/87a0a1e15b2ccd39-1536x1152.jpg" width="450">

This is a pretty nice, simple vertical spoolholder design that keeps the spool in place while offering very little friction during use.

Parts:

* 2x [`MINI-rail-spoolholder.stp`](https://raw.githubusercontent.com/prusa3d/Original-Prusa-MINI/master/STEP/PRINTED%20PARTS/MINI-rail-spoolholder.stp)
* 4x [`MINI-base-spoolholder.stp`](https://raw.githubusercontent.com/prusa3d/Original-Prusa-MINI/master/STEP/PRINTED%20PARTS/MINI-base-spoolholder.stp)
* 4x [608Z]() (or any [`608`]()) Bearings
    * Measurements: 8mm x 22mm x 7mm
    * Digikey: [`608-2RS-W` ($1.00 each)](https://www.digikey.com/en/products/detail/mechatronics-bearing-group/608-2RS-W-CHEVRONSRI2/9608369)
    * Lots of compatible bearings are listed on Amazon or other places as "skateboard bearings".
    * These are roughly $1 each and can often be found cheaper. Quality of the bearing isn't a huge issue here, so don't spend too much.
* 4x `M3x12` Screw
    * McMaster [`92000A122` ($6.65 for 100)](https://www.mcmaster.com/92000A122) or [`92005A122` ($4.32 for 100)](https://www.mcmaster.com/92005A122)
* 4x `M3x8` Screw
    * McMaster [`92000A118` ($5.51 for 100)](https://www.mcmaster.com/92000A118) or [`92005A118` ($4.32 for 100)](https://www.mcmaster.com/92005A118)
* 4x `M3n` Nut
    * McMaster [`90592A085` ($1.44 for 100)](https://www.mcmaster.com/90592A085/)

Assembly:

<https://help.prusa3d.com/guide/6-spool-holder-assembly_204973>

## Prusa MINI+ Spoolholder Scale Base/Adapter

_TODO: Share scale models on Printables and link here_