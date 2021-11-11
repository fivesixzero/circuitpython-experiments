print("00: Boot complete, running code.py")

import time
time.sleep(10)
print("01: Starting up, importing time, board, and digitalio")
import board
import digitalio

print("01: Started up, sleeping 10 seconds")
time.sleep(10)
print("02: Init LED, Neopixels, peripheral pins")

time.sleep(1)
indicator_pin = digitalio.DigitalInOut(board.D10)
indicator_pin.switch_to_output()
indicator_pin.value = False

time.sleep(1)
indicator2_pin = digitalio.DigitalInOut(board.A1)
indicator2_pin.switch_to_output()
indicator2_pin.value = False

time.sleep(1)
led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()
led.value = False

time.sleep(1)
indicator_pin.value = True
speaker_enable_pin = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable_pin.switch_to_output()
speaker_enable_pin.value = True

time.sleep(1)
speaker_enable_pin.value = False
indicator_pin.value = False

time.sleep(1)
import neopixel
pixels = neopixel.NeoPixel(board.NEOPIXEL, 4, brightness=1.0, auto_write=False)
pixels.brightness = 1.0
pixels.fill((0,0,0))
pixels.show()

print("02: Peripherals set up, sleeping 10 seconds")

time.sleep(10)
print("03: Running LED/Neopixel Tests")
indicator_pin.value = True
time.sleep(1)
led.value = True
time.sleep(1)
led.value = False
indicator_pin.value = False

time.sleep(1)
indicator_pin.value = True
pixels[0] = (255,255,255)
pixels.brightness = 1.0
pixels.show()
time.sleep(1)
pixels.brightness = 0.5
pixels.show()
time.sleep(1)
pixels.brightness = 0.1
pixels.show()
time.sleep(1)
pixels.brightness = 0.05
pixels.show()
time.sleep(1)
pixels[0] = (255,0,0)
pixels.brightness = 1.0
pixels.show()
time.sleep(1)
pixels[0] = (0,255,0)
pixels.show()
time.sleep(1)
pixels[0] = (0,0,255)
pixels.show()
time.sleep(1)
pixels.fill((0,0,0))
pixels.show()
time.sleep(1)
pixels.fill((255,255,255))
pixels.show()
time.sleep(1)
pixels.brightness = 0.5
pixels.show()
time.sleep(1)
pixels.brightness = 0.1
pixels.show()
time.sleep(1)
pixels.brightness = 0.05
pixels.show()
time.sleep(1)
pixels.deinit()
time.sleep(1)
# neopixel_power_pin.value = False
indicator_pin.value = False
print("03: LED/NeoPixel tests complete")
time.sleep(10)

print("04: Initializing and refreshing display")
def display_refresh():
    indicator2_pin.value = True
    while board.DISPLAY.time_to_refresh > 0.0:
        time.sleep(board.DISPLAY.time_to_refresh)
    board.DISPLAY.refresh()
    while board.DISPLAY.time_to_refresh > 0.0:
        time.sleep(board.DISPLAY.time_to_refresh)
    indicator2_pin.value = False

display_refresh()
print("04: Sleeping 10 seconds")
time.sleep(10)

print("05: Preparing to connect to Wifi network")
from secrets import secrets
import wifi

def wifi_connect(ssid: str, password: str) -> None:
    indicator_pin.value = True
    print("WIFI: wifi_connect called")
    wifi.radio.connect(ssid, password)
    print("WIFI: wifi_connect complete")
    indicator_pin.value = False

print("05: Sleeping for 10 seconds")
time.sleep(10)

print("06: Connecting to Wifi network")
wifi_connect(secrets["ssid"], secrets["password"])
print("06: Sleeping for 10 seconds")
time.sleep(10)

print("07: Disabling WiFi Networking")
wifi.radio.enabled = False
time.sleep(10)
print("07: Sleeping for 10 seconds")


while True:
    if not wifi.radio.ap_info and wifi.radio.enabled:
        print("Loop: Wifi not connected, reconnecting")
        wifi_connect(secrets["ssid"], secrets["password"])
        print("Loop: Wifi reconnected, sleeping 10 sec")
        time.sleep(10)
    
    print("Loop Time: {}, sleeping 10 seconds".format(time.monotonic()))
    display_refresh()
    time.sleep(10)
    wifi.radio.enabled = not wifi.radio.enabled
