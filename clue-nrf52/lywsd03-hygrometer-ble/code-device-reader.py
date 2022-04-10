import time
import board

import adafruit_ble
from adafruit_ble.advertising.standard import Advertisement
from adafruit_ble_lywsd03mmc import LYWSD03MMCService
from _bleio import BluetoothError

import displayio
from adafruit_display_text import label
import terminalio

from lywsd import LYWSD
from addr import addr

ble = adafruit_ble.BLERadio()

connection = None

devices = {}

display = board.DISPLAY

splash = displayio.Group()
display.show(splash)
display.brightness = 0.1

color_bitmap = displayio.Bitmap(display.width, display.height, 1)
color_palate = displayio.Palette(1)
color_palate[0] = 0x000000

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palate, x=0, y=0)
splash.append(bg_sprite)

for adv in ble.start_scan(Advertisement, timeout=5):
    if adv.complete_name in LYWSD.VALID_NAMES:
        addr_str = LYWSD.get_address(adv)
        if addr_str in addr.keys() and not addr_str in devices.keys():
            devices[addr_str] = LYWSD(adv)

if len(devices) > 0:
    # Set up display labels

    lywsd03_line = "{:6}: {:5.2f}c, {:02d}%"
    text_labels = {}
    text_x = 2
    text_y_start = 2
    line_size = 19
    count = 0
    
    for address in devices.keys():
        if devices[address].device_name == "LYWSD03MMC" and address is not "":
            count += 1
            lywsd03_label = label.Label(
                terminalio.FONT, scale=2,
                text="{:6}: connecting...".format(addr[address]),
                color=0xFFFFFF,
                x=text_x,
                y=text_y_start + (count * line_size)
            )
            # print("  [{:02}] Appending label for {}".format(count, addr[address]))
            splash.append(lywsd03_label)
            text_labels[address] = lywsd03_label

    # Connect to devices and get data
    loop_delay = 60
    # print("Found [{}] listed devices to connect to".format(len(devices)))
    while True:
        for address in devices.keys():
            if devices[address].device_name == "LYWSD03MMC":
                # print("  Attempting connection to device [{}] [{}]".format(addr[address], devices[address]))
                connected = False
                connection = None
                service = None
                while not connected:
                    try:
                        connection = ble.connect(devices[address].advertisement)
                        if connection.connected:
                            connected = True
                    except BluetoothError as ex:
                        print("  Retrying in 1 second, connect error [{}]".format(ex))
                        time.sleep(1)

                service = connection[LYWSD03MMCService]
                while connection.connected:
                    temp_humidity = service.temperature_humidity
                    if temp_humidity:
                        text_labels[address].text = lywsd03_line.format(
                            addr[address], temp_humidity[0], temp_humidity[1])
                        # print("    [{} ({})]: temp/humidity [{}]".format(
                        #     addr[address],
                        #     address,
                        #     temp_humidity))
                        connection.disconnect()

            time.sleep(300)
else:
    print("Found no active devices to connect to")