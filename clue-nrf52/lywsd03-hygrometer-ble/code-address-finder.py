# Address finder for LYWSD02/03 devices
#
# Adapted from Adafruit BLE LYWSD03MMC library example:
#   https://github.com/adafruit/Adafruit_CircuitPython_BLE_LYWSD03MMC/blob/main/examples/ble_lywsd03mmc_simpletest.py
#
# Power devices on one at a time then added each new address and a simple ID note to "addr.py"
# as the devices are labeled or otherwise processed.
#
# Ideally this script will only show new devices but if many are in use nearby it may be possible
# to identify nearby devices using RSSI.

import time

import adafruit_ble
from adafruit_ble.advertising.standard import Advertisement

from lywsd import LYWSD
from addr import addr

ble = adafruit_ble.BLERadio()

connection = None

devices = {}

for adv in ble.start_scan(Advertisement, timeout=5):
    if adv.complete_name in LYWSD.VALID_NAMES:
        addr_str = LYWSD.get_address(adv)
        if not addr_str in addr.keys() and not addr_str in devices.keys():
            devices[addr_str] = LYWSD(adv)

if len(devices) > 0:
    print("Found {} new LYWSD03 or LYWSD02 devices".format(len(devices)))
    for dev in devices:
        print("  New [{}], addr [{}], all data [{}]".format(dev.device_name, dev.address, dev))
else:
    print("Found no new LYWSD03 or LYWSD02 devices")