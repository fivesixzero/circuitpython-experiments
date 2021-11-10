# https://learn.adafruit.com/adafruit-trinket-m0-circuitpython-arduino/
#
# Neopixel ring data line is on D4
# Buttons are on D0, D1, D2
# 10k potentiometer is on D3

import time
import board
import digitalio
import neopixel
from keypad import Keys
from analogio import AnalogIn

# pot = None
pot = AnalogIn(board.D3)

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

# On CircuitPlayground Express, and boards with built in status NeoPixel -> board.NEOPIXEL
# Otherwise choose an open pin connected to the Data In of the NeoPixel strip, i.e. board.D1
pixel_pin = board.D4

# On a Raspberry pi, use this instead, not all pins are supported
# pixel_pin = board.D18

# The number of NeoPixels
num_pixels = 12

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=1, auto_write=False, pixel_order=ORDER
)
pixels.fill((255,255,255))
pixels.show()

button_pins = (board.D0, board.D1, board.D2)
buttons = Keys(button_pins, value_when_pressed=False, pull=True)

cycles = [
    [
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255)
    ],
    [
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255),
        (255,255,255)
    ],
    [
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (255,255,255),
        (255,255,255),
        (255,255,255)
    ],
    [
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (255,255,255)
    ],
    [
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (0,0,0)
    ],
    [
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0),
        (255,0,0)
    ],
    [
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0),
        (0,255,0)
    ],
    [
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
        (0,0,255),
    ],
    [
        (96,128,255),
        (96,128,255),
        (96,128,255),
        (0,0,0),
        (0,0,0),
        (0,0,0),
        (255,128,96),
        (255,128,96),
        (255,128,96),
        (0,0,0),
        (0,0,0),
        (0,0,0),
    ],
]

def update_pixels(rotation):
    for i in range(12):
        pix = (i + rotation) % 12
        # print("rotation: {}, pixel: {}".format(rotation, pix))
        pixels[pix] = this_cycle[i]
    pixels.show()

def get_new_presses(keypad):
    events = []
    keep_looking = True
    while keep_looking:
        e = keypad.events.get()
        if e:
            print(e)
            events.append(e)
        else:
            keep_looking = False
    return events

BRIGHTNESS_MIN = 0.01
BRIGHTNESS_MAX = 0.975
BRIGHTNESS_DIFF_MIN = 0.0025

cycle = 0
should_cycle = False
rotation = 0
button_0_held = False
while True:

    if pot:
        old_brightness = pixels.brightness
        new_brightness = pot.value / 65520
        if new_brightness > BRIGHTNESS_MAX:
            new_brightness = 1.0
        elif new_brightness < BRIGHTNESS_MIN:
            new_brightness = BRIGHTNESS_MIN
        brightness_difference = abs(old_brightness - new_brightness)
        if brightness_difference > BRIGHTNESS_DIFF_MIN:
            pixels.brightness = new_brightness
            pixels.show()
            # print("Brightness updated, old: {}, new: {}, diff: {}".format(old_brightness, new_brightness, brightness_difference))

    new_events = get_new_presses(buttons)
    if len(new_events) > 0:
        pressed = []
        released = []
        for e in new_events:
            if e.pressed:
                pressed.append(e.key_number)
            if e.released:
                released.append(e.key_number)

        if 0 in pressed:
            cycle = (cycle + 1) % len(cycles)
            this_cycle = cycles[cycle]
            update_pixels(rotation)
            # print("Changed to cycle #{}".format(cycle))
        else:
            this_cycle = cycles[cycle]
            if 1 in pressed:
                rotation = (rotation + 1) % 12
                update_pixels(rotation)
            elif 2 in pressed:
                rotation = (rotation - 1) % 12
                update_pixels(rotation)

    time.sleep(0.01)