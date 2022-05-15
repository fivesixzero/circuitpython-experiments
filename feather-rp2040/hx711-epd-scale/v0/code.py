import time
import board

i2c = board.STEMMA_I2C()

rtc_enabled = False

# i2c.try_lock()
# i2c_scan_results = i2c.scan()
# i2c.unlock()

# rtc_enabled = False
# if 0x6b in i2c_scan_results:
#     rtc_enabled = True

# import adafruit_pcf8523
# rtc = adafruit_pcf8523.PCF8523(i2c)

# months = ("", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
# months_short = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# days = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
# days_short = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")

# # default_alarm = time.struct_time((2017, 1, 1, 0, 0, 0, 6, 1, -1))

# # if rtc.alarm_status == True:
# #     rtc.alarm_status = False
# # if rtc.alarm[0] != default_alarm:
# #     rtc.alarm = (default_alarm, None)

# startup_time = rtc.datetime

# def get_status_time(
#     td: time.struct_time,
#     status_time_string: str = "{:02d}/{:02d} {:02d}:{:02d}:{:02d}"):

#     return status_time_string.format(td.tm_mon, td.tm_mday, td.tm_hour, td.tm_min, td.tm_sec)

from hx711.hx711_pio import HX711_PIO

pio_data = board.D25
pio_clk = board.D24

hx = HX711_PIO(pio_data, pio_clk, tare=False, scalar=417)

import keypad

key_a = board.D11
key_b = board.D12
key_c = board.D13

buttons = keypad.Keys((key_a, key_b, key_c), value_when_pressed=False, pull=True)

event_buffer = keypad.Event()

BUTTON_A_PRESS = keypad.Event(0, True)
BUTTON_B_PRESS = keypad.Event(1, True)
BUTTON_C_PRESS = keypad.Event(1, True)

presses = {
    0: False,
    1: False,
    2: False
}

def get_presses(keys: keypad.Keys):
    presses[0] = False
    presses[1] = False
    presses[2] = False

    while keys.events.get_into(event_buffer):
        if event_buffer == BUTTON_A_PRESS:
            presses[0] = True
        elif event_buffer == BUTTON_B_PRESS:
            presses[1] = True
        elif event_buffer == BUTTON_C_PRESS:
            presses[2] = True
    return presses

def wait_for_keypress(keys: keypad.Keys):
    while True:
        new_presses = get_presses(keys)
        
        if new_presses[0] or new_presses[1]:
            break
        else:
            time.sleep(0.001)

import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixel.brightness = 1.0

def keep_blinking(pixel, time_sec=1, delay=0.1, fill=(255, 255, 255), keys=None):

    start_time = time.monotonic()

    blink = True
    while blink:

        # Check for keypress, if we need to
        if keys:
            presses = get_presses(keys)
            if presses[0] or presses[1] or presses[2]:
                blink = False

        time.sleep(delay)
        pixel.fill(fill)
        time.sleep(delay)
        pixel.fill((0,0,0))

        now_time = time.monotonic()
        if now_time - start_time > time_sec:
            blink = False

keep_blinking(pixel, fill=(0, 255, 0))

import displayio
import terminalio
from adafruit_display_text import label
import adafruit_il0373

epd_sd_cs = board.D5
epd_sram_cs = board.D6
epd_cs = board.D9
epd_dc = board.D10
# epd_reset = board.D4 # no dedicated reset pin on FeatherWing, haven't soldered it yet

spi = board.SPI()

displayio.release_displays()
display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)

WIDTH = 296
HEIGHT = 128
ROTATION = 270
TEXT_SCALE = 4
eink_refresh_delay = 180  #  Advice is not to refresh more often than every 180 seconds, whew...

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
BUTTON_WIDTH = 44
BUTTON_WIDTH_HALF = BUTTON_WIDTH // 2

BUTTON_BORDERS = [
    (XPOS_BUTTON_A - BUTTON_WIDTH_HALF, XPOS_BUTTON_A + BUTTON_WIDTH_HALF),
    (XPOS_BUTTON_B - BUTTON_WIDTH_HALF, XPOS_BUTTON_B + BUTTON_WIDTH_HALF),
    (XPOS_BUTTON_C - BUTTON_WIDTH_HALF, XPOS_BUTTON_C + BUTTON_WIDTH_HALF),
]

font = terminalio.FONT

# Build UI
splash = displayio.Group()

# Build display background
bg_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
bg_palette = displayio.Palette(3)
bg_palette[0] = BG_COLOR
bg_palette[1] = TEXT_COLOR
bg_palette[2] = HIGHLIGHT_COLOR
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)

# Add UI lines: top/bottom title/status
for x in range(0, WIDTH):
    bg_bitmap[x, 14] = 1
    bg_bitmap[x, HEIGHT - 14] = 1

# Add UI lines: top button label markers
for y in range(0, 14):
    for x1, x2 in BUTTON_BORDERS:
        bg_bitmap[x1, y] = 1
        bg_bitmap[x2, y] = 1

splash.append(bg_sprite)

# Title on bottom line
title_text = "HX711 Filament Scale"
status_center = label.Label(
    font,
    text=title_text,
    color=HIGHLIGHT_COLOR,
    scale=1,
    anchor_point = (0.5, 1.0),
    anchored_position = (WIDTH / 2, HEIGHT)
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

if rtc_enabled:
    # Last-refresh-time on bottom left
    time_left = label.Label(
        font,
        text=get_status_time(startup_time),
        color=TEXT_COLOR,
        anchor_point=BOTTOM_LEFT,
        anchored_position=(1, HEIGHT - 15)
    )
    splash.append(time_left)

    time_left_label = label.Label(
        font,
        text="Last refresh:",
        color=TEXT_COLOR,
        anchor_point=BOTTOM_LEFT,
        anchored_position=(1, HEIGHT - 15 - 14)
    )
    splash.append(time_left_label)

# Debug data on corners
status_left = label.Label(
    font,
    text=" "*10,
    color=TEXT_COLOR,
    anchor_point=BOTTOM_LEFT,
    anchored_position=(1, HEIGHT)
)
splash.append(status_left)

status_right = label.Label(
    font,
    text=" "*10,
    color=TEXT_COLOR,
    anchor_point=BOTTOM_RIGHT,
    anchored_position=(WIDTH-1, HEIGHT)
)
splash.append(status_right)

# Center text
text_area_ypos = HEIGHT // 2

if rtc_enabled:
    text_area_ypos -= 14

text_area = label.Label(
    font,
    text="Hello World!",
    color=TEXT_COLOR,
    scale=TEXT_SCALE,
    anchor_point=CENTER_CENTER,
    anchored_position=(WIDTH // 2, (HEIGHT // 2)),
)
splash.append(text_area)

# Create the display object - the third color is red (0xff0000)
display = adafruit_il0373.IL0373(
    display_bus,
    width=WIDTH,
    height=HEIGHT,
    rotation=ROTATION,
    # busy_pin=epd_busy,
    highlight_color=HIGHLIGHT_COLOR,
)

display.show(splash)

# Display setup complete, grab our first scale read and refresh that puppy
pixel.fill((255, 255, 255))
hx.read(50)
hx.tare()
reading = hx.read(50)
reading_raw = hx.read_raw()

text_area.text = "{:.2f} g".format(reading)
pixel.fill((0, 0, 0))

display.refresh()
time.sleep(1)
print("INIT: [{: 8.2f} g] [{: 8} raw] offset: {}, scalar: {}".format(
    reading, reading_raw, hx.offset, hx.scalar))

if rtc_enabled:
    print("INIT: Startup at {}, {} {}, {}:{}:{}".format(
        days[startup_time.tm_wday],
        months[startup_time.tm_mon],
        startup_time.tm_mday,
        startup_time.tm_hour,
        startup_time.tm_min,
        startup_time.tm_sec
    ))

keep_blinking(pixel, time_sec=eink_refresh_delay, fill=(0, 0, 255))


# Final prep for loop

# wait_for_keypress(buttons)
debug = False
while True:

    new_presses = get_presses(buttons)

    tare = False
    debug = False
    weigh = False
    if new_presses[0]:
        weigh = True
    elif new_presses[1]:
        debug = True
    elif new_presses[2]:
        tare = True

    if tare:
        pixel.fill((255, 255, 255))
        print("Tare requested, current offset: [{}]".format(hx.offset))
        hx.read(50)
        hx.tare()
        print("Tare completed, new offset: [{}]".format(hx.offset))
        pixel.fill((0, 0, 0))
        weigh = True
        time.sleep(1)

    if debug:
        print("HX details, offset: [{}], scalar: [{}], gain: [{}]".format(
            hx.offset, hx.scalar, hx.gain
        ))

        debug = not debug

        if debug:
            button_b_label.color = HIGHLIGHT_COLOR
            status_left.text = "offset: {}".format(hx.offset)
            status_center.text = "scalar: {}".format(hx.scalar)
            status_right.text = "gain: {}".format(hx.gain)
        else:
            button_b_label.color = TEXT_COLOR
            status_left.text = ""
            status_right.text = ""
            status_center.text = title_text
        
        if rtc_enabled:
            time_left.text = get_status_time(startup_time)

        display.refresh()
        keep_blinking(pixel, time_sec=eink_refresh_delay, fill=(0, 0, 255))

    if weigh:
        pixel.fill((255, 255, 255))
        reading = hx.read(50)
        reading_raw = hx.read_raw()
        print(
            "[{: 8.2f} g] [{: 8} raw] offset: {}, scalar: {}".format(
                reading, reading_raw, hx.offset, hx.scalar
            )
        )
        text_area.text = "{:.2f} g".format(reading)
        if rtc_enabled:
            time_left.text = get_status_time(startup_time)
        pixel.fill((0, 0, 0))
        display.refresh()
        keep_blinking(pixel, time_sec=eink_refresh_delay, fill=(0, 0, 255))