## Adafruit RP2040 all-the-things demo
##
## Product Page:  https://www.adafruit.com/product/3857
## Learn Guide:   https://learn.adafruit.com/adafruit-feather-m4-express-atsamd51
## CircuitPython: https://circuitpython.org/board/feather_m4_express/
## Bootloader:    https://github.com/adafruit/uf2-samdx1/releases/
## Pinout Image:  https://cdn-learn.adafruit.com/assets/assets/000/101/972/original/arduino_compatibles_Feather_M4_Page.png
##
## Onboard Peripherals

## Neopixel: D8
## Internal LED: Shared with pin D13
## Built-in 3v3 Regulator can be disabled by pulling EN pin to GND
##
## Interesting Options
##
## 8-bit Parallel Camera Support: Requires use of D5, D6, D10, D11, D12, D13, SCK, MOSI, MISO, SDA, SCL pins
## PWM Out: Lots of PWM out pins - D4, D5, D6, D9, D10, D11, D12, D13
##
## External Peripherals in Dev Setup
##
## Adafruit FeatherWing Tripler https://www.adafruit.com/product/3417
##
## Adafruit 128x64 OLED FeatherWing https://www.adafruit.com/product/4650
## 
## * 0x3C / 60  : OLED Display
## * Pin 9: Button A
## * Pin 6: Button B
## * Pin 5: Button C
##
## Adafruit NeoKey FeatherWing https://www.adafruit.com/product/4979
##
## Rewired the pins on my dev board so that they don't collide with the display's buttons or an additional NeoKey wing
##
## * Pin 10: NeoPixel
## * Pin 11: Switch B
## * Pin 12: Switch A
##

import board
import time
import keypad
import displayio
import terminalio
from adafruit_displayio_sh1107 import SH1107
from neopixel import NeoPixel
# from adafruit_display_text.label import Label
from adafruit_display_text.bitmap_label import Label
import bitmaptools
import microcontroller
import gc
import sys

i2c = board.I2C()

## Display

displayio.release_displays()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 62
BORDER = 2

display = SH1107(bus=display_bus, width=WIDTH, height=HEIGHT, rotation=0, auto_refresh=False)

splash = displayio.Group()
display.show(splash)

## Buttons

buttons = (
    board.D9,     # Display button A
    board.D6,     # Display button B
    board.D5,     # Display button C
    board.D12,    # Neokey A (left)
    board.D11     # Neokey B (right)
)

keys = keypad.Keys(buttons, value_when_pressed=False, pull=True)

def retrieve_key_events(keys: keypad.Keys):
    new_events = True
    key_events = []
    while new_events:
        event = keys.events.get()
        if event:
            key_events.append(event)
        else:
            new_events = False
    return key_events

## Neopixels

pixel_board = NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
pixel_board[0] = (40, 40, 40)
pixels_keys = NeoPixel(board.D10, 2, brightness=0.1)
pixels_keys[0] = (40, 40, 40)
pixels_keys[1] = (40, 40, 40)

## Display Setup

# Loop indicator
single_color_palette = displayio.Palette(1)
single_color_palette[0] = 0xFFFFFF

sm_square_bitmap = displayio.Bitmap(4, 1, 1)
sm_square = displayio.TileGrid(sm_square_bitmap, pixel_shader=single_color_palette, x=64, y=61)
splash.append(sm_square)

# Set up Page Numbers text area
page_text = "[{}/{}]"
page_label = Label(terminalio.FONT, text=page_text.format(0,0), padding_top=0, padding_bottom=0)
page_label.anchor_point = (1.0, 0.0)
page_label.anchored_position = (128, 0)
splash.append(page_label)

# Set up Page Title text area
title_text = "{:16}"
title_label = Label(terminalio.FONT, text=title_text.format(" ", 0, 0), padding_top=0, padding_bottom=0)
title_label.anchor_point = (0.0, 0.0)
title_label.anchored_position = (0, 0)
splash.append(title_label)

# Set up Internals text area
cpu_text = "CPU\nFreq: {:11.1f} MHz\nTemp: {:11.1f} C\nVolts: {:10.3} V\nMem Free: {:7d} b"
cpu_label = Label(terminalio.FONT, text=cpu_text.format(0.0, 0.0, 0.0, 0), padding_top=0, padding_bottom=0, line_spacing=0.7)
# cpu_label = Label(terminalio.FONT, text="test", padding_top=0, padding_bottom=0, line_spacing=0.7)
cpu_label.anchor_point = (0.0, 1.0)
cpu_label.anchored_position = (0, 60)

# Set up Keymap Bitmap
two_color_palette = displayio.Palette(2)
two_color_palette[0] = 0x000000
two_color_palette[1] = 0xFFFFFF

keymap_indicator_size = 3
keymap_width = 1 + ((len(buttons) + 1) * keymap_indicator_size + 1) + 1
keymap_height = 1 + keymap_indicator_size + 1
keymap_x_pos = WIDTH - keymap_width

keymap_bitmap = displayio.Bitmap(keymap_width, keymap_height, 2)
keymap_bitmap.fill(0)
keymap_tile = displayio.TileGrid(keymap_bitmap, pixel_shader=two_color_palette, x=keymap_x_pos, y=15)
splash.append(keymap_tile)

def keymap_update(keymap_bits: displayio.Bitmap, key_id: int, val: bool):
    x_position = 1 + (key_id * (keymap_indicator_size + 1))
    y_position = 1
    bitmaptools.fill_region(
        keymap_bits, 
        x_position, y_position, 
        x_position + keymap_indicator_size, y_position + keymap_indicator_size, 
        int(val)
    )

# Page Setup
page_names = [
    " ",
    "Internals",
    "Testing",
    " "
]

pause_animations = False
reverse_animations = False
should_page = True
page = 1
max_pages = 3
loop_counter = 0
max_counter = sys.maxsize - 1
start_time = time.monotonic()
time_now = 0.0
last_loop = 0.0
loop_duration = 0.0
run_time = 0.0
display_refresh_delay = 0.75
last_display_refresh = time.monotonic()
should_refresh_display = True
fast_loop_page = False
print_debug = False
did_refresh_display = True
while True:

    loop_counter += 1
    if loop_counter >= max_counter:
        loop_counter = 0
    time_now = time.monotonic()
    run_time = time_now - start_time
    if time_now > last_display_refresh + display_refresh_delay or should_refresh_display:
        should_refresh_display = True
        last_display_refresh = time_now
        # print_debug = True

    if loop_duration > 0.15:
        print_debug = True

    if print_debug or did_refresh_display:
        print("{:4d} | {:8.2f} | {:6.4f} | {:8.2f} | {:1d} | mem_free: {:8d}".format(loop_counter, time_now, loop_duration, last_display_refresh, did_refresh_display, gc.mem_free()))
        did_refresh_display = False
        print_debug = False

    # Handle control inputs
    new_events = retrieve_key_events(keys)
    if len(new_events) > 0:
        for e in new_events:
            # print(e)
            if e.pressed:
                if e.key_number is 0:   # Display A
                    new_brightness = display.brightness + 0.1
                    if new_brightness <= 1.0:
                        display.brightness = new_brightness
                    else:
                        new_brightness = 1.0
                elif e.key_number is 1: # Display B
                    gc.collect()
                elif e.key_number is 2: # Display C
                    new_brightness = display.brightness - 0.1
                    if new_brightness >= 0.0:
                        display.brightness = new_brightness
                    else:
                        new_brightness = 0.0
                elif e.key_number is 3: # Neopixel Left
                    page -= 1
                    if page < 1:
                        page = 1
                        should_page = False
                    else:
                        should_page = True
                elif e.key_number is 4: # Neopixel Right
                    page += 1
                    if page > max_pages:
                        page = max_pages
                        should_page = False
                    else:
                        should_page = True
    
    # Update pages
    if should_page:
        fast_loop_page = False
        should_page = False
        page_label.text = page_text.format(page, max_pages)
        title_label.text = title_text.format(page_names[page])
        if page == 1:
            # Show title/page if required
            if page_label not in splash:
                splash.append(page_label)
            if title_label not in splash:
                splash.append(title_label)
            # Hide other pages
            # Show this page
            splash.append(cpu_label)
            display_refresh_delay = 0.75
        if page == 2:
            # Show title/page if required
            if page_label not in splash:
                splash.append(page_label)
            if title_label not in splash:
                splash.append(title_label)
            # Hide other pages
            if cpu_label in splash:
                splash.remove(cpu_label)
            display_refresh_delay = 0.0001
        if page == 3:
            # Hide other pages
            if cpu_label in splash:
                splash.remove(cpu_label)
            # Hide the rest of the labels
            if page_label in splash:
                splash.remove(page_label)
            if title_label in splash:
                splash.remove(title_label)
            pass

    # Do per-page operations but only if we're going to refresh our display
    if should_refresh_display:
        if page == 1:
            cpu_label.text = cpu_text.format(microcontroller.cpu.frequency / 1000 / 1000, microcontroller.cpu.temperature, microcontroller.cpu.voltage, gc.mem_free())
            # cpu_label.text = 'test'
            # cpu_label.text = 'CPU\nFreq: %g MHz\nTemp: %g C\nVolts: %g V\nMem Free: %g b' % (microcontroller.cpu.frequency / 1000 / 1000, microcontroller.cpu.temperature, microcontroller.cpu.voltage, gc.mem_free())
        if page == 2:
            pass
        display.refresh()
        should_refresh_display = False
        did_refresh_display = True

        # Update our keymap_bitmap
        # if keymap_bitmap[1,1] is 1:
        #     keymap_bitmap[1,1] = 0
        #     keymap_bitmap[1,2] = 0
        #     keymap_bitmap[1,3] = 0
        #     keymap_bitmap[2,1] = 0
        #     keymap_bitmap[2,2] = 0
        #     keymap_bitmap[2,3] = 0
        #     keymap_bitmap[3,1] = 0
        #     keymap_bitmap[3,2] = 0
        #     keymap_bitmap[3,3] = 0
        # else:
        #     keymap_bitmap[1,1] = 1
        #     keymap_bitmap[1,2] = 1
        #     keymap_bitmap[1,3] = 1
        #     keymap_bitmap[2,1] = 1
        #     keymap_bitmap[2,2] = 1
        #     keymap_bitmap[2,3] = 1
        #     keymap_bitmap[3,1] = 1
        #     keymap_bitmap[3,2] = 1
        #     keymap_bitmap[3,3] = 1

        # if keymap_bitmap[5,1] is 1:
        #     bitmaptools.fill_region(keymap_bitmap, 5, 1, 8, 4, 0)
        # else:
        #     bitmaptools.fill_region(keymap_bitmap, 5, 1, 8, 4, 1)

        if keymap_bitmap[5,1] is 1:
            keymap_update(keymap_bitmap, 0, False)
        else:
            keymap_update(keymap_bitmap, 0, True)

        if keymap_bitmap[9,1] is 1:
            keymap_update(keymap_bitmap, 1, False)
        else:
            keymap_update(keymap_bitmap, 1, True)

        if keymap_bitmap[11,1] is 1:
            keymap_update(keymap_bitmap, 2, False)
        else:
            keymap_update(keymap_bitmap, 2, True)

        if keymap_bitmap[14,1] is 1:
            keymap_update(keymap_bitmap, 3, False)
        else:
            keymap_update(keymap_bitmap, 3, True)

        if keymap_bitmap[18,1] is 1:
            keymap_update(keymap_bitmap, 4, False)
        else:
            keymap_update(keymap_bitmap, 4, True)

        # Move that cute little loop indicator
        if not pause_animations:
            if reverse_animations:
                new_x = sm_square.x + 1
                sm_square.x = new_x
                if new_x > 125:
                    reverse_animations = False
            else:
                new_x = sm_square.x - 1
                sm_square.x = new_x
                if new_x < 0:
                    reverse_animations = True

    gc.collect()
    # time.sleep(0.01)
        
    loop_duration = time.monotonic() - time_now