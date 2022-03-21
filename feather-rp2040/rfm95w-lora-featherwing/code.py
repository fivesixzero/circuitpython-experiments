## Adafruit RP2040 + RFM95W 900MHz RadioFruit Featherwing
##
## Product Page:  https://www.adafruit.com/product/3857
## Learn Guide:   https://learn.adafruit.com/adafruit-feather-m4-express-atsamd51
## CircuitPython: https://circuitpython.org/board/feather_m4_express/
## Bootloader:    https://github.com/adafruit/uf2-samdx1/releases/
## Pinout Image:  https://cdn-learn.adafruit.com/assets/assets/000/101/972/original/arduino_compatibles_Feather_M4_Page.png
##
## Onboard Peripherals
##
## Neopixel: D8
## Internal LED: Shared with pin D13
## Built-in 3v3 Regulator can be disabled by pulling EN pin to GND
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
## RFM95W LoRa Radio Featherwing Pins
##
## IRQ: D12
## CS:  D13
## RST: D11
##

import board
import time
import digitalio
import adafruit_rfm9x

irq = digitalio.DigitalInOut(board.D12)
cs = digitalio.DigitalInOut(board.D13)
rst = digitalio.DigitalInOut(board.D11)

spi = board.SPI()

rfm95 = adafruit_rfm9x.RFM9x(spi, cs, rst, 915.0)

count = 0
while True:
    packet = rfm95.receive()
    # Optionally change the receive timeout from its default of 0.5 seconds:
    # packet = rfm9x.receive(timeout=5.0)
    # If no packet was received during the timeout then None is returned.
    if packet is None:
        # Packet has not been received
        print("Received nothing! Listening again...")
    else:
        # Received a packet!
        # Print out the raw bytes of the packet:
        print("Received (raw bytes): {0}".format(packet))
        # And decode to ASCII text and print it too.  Note that you always
        # receive raw bytes and need to convert to a text format like ASCII
        # if you intend to do string processing on your data.  Make sure the
        # sending side is sending ASCII data before you try to decode!
        packet_text = str(packet, "ascii")
        print("Received (ASCII): {0}".format(packet_text))
        # Also read the RSSI (signal strength) of the last received message and
        # print it.
        rssi = rfm95.last_rssi
        print("Received signal strength: {0} dB".format(rssi))
    
    time.sleep(5)

    count += 1
    rfm95.send("Hello, other RFM95s out there! Message {}".format(count))
