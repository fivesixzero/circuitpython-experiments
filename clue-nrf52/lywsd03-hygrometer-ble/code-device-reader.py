# Device reader for LYWSD02/03 devices
#
# Adapted from Adafruit BLE LYWSD03MMC library example:
#   https://github.com/adafruit/Adafruit_CircuitPython_BLE_LYWSD03MMC/blob/main/examples/ble_lywsd03mmc_simpletest.py
#
# Once the address list in addr.py is populated, this script will poll all active devices on that
# list to retrieve their humidity/temperature readings.

import time

import adafruit_ble
from adafruit_ble.advertising.standard import Advertisement
from adafruit_ble_lywsd03mmc import LYWSD03MMCService
from _bleio import BluetoothError

from lywsd import LYWSD
from addr import addr

ble = adafruit_ble.BLERadio()

connection = None

devices = {}

for adv in ble.start_scan(Advertisement, timeout=5):
    if adv.complete_name in LYWSD.VALID_NAMES:
        addr_str = LYWSD.get_address(adv)
        if addr_str in addr.keys() and not addr_str in devices.keys():
            devices[addr_str] = LYWSD(adv)

if len(devices) > 0:
    print("Found [{}] listed devices to connect to".format(len(devices)))
    for address in devices.keys():
        if devices[address].device_name == "LYWSD03MMC":
            print("  Attempting connection to device [{}] [{}]".format(addr[address], devices[address]))
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
                    print("    [{} ({})]: temp/humidity [{}]".format(
                        addr[address],
                        address,
                        temp_humidity))
                    connection.disconnect()
else:
    print("Found no active devices to connect to")