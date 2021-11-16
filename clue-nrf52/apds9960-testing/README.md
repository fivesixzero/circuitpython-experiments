# APDS9960 Testing

Testing the APDS9960's individual functions on the Adafruit Clue nRF52840.

## Deep Notes

* [APDS-9960 Notes](./APDS-9960-notes.md)
    * Detailed notes covering state machine operations, control registers, and observations while developing, testing, and bug-fixing
* [Gesture Engine Notes](./APDS-9960-gesture-notes.md)
    * A detour into the world of APDS-9960 gesture sensor data handling, which is a bit more complicated than it seems

## Overview

The APDS9960 is a complex I2C peripheral, packing three related but distinctly different functions into a very tiny package.

* Proximity sensing
* Light intensity and RGB color sensing
* Gesture detection

This little chip has a ton of configuration options for each of the three core functions including some very useful features for 'interrupts' that can be read from a register or even picked up from signal on the chip's interrupt pin. This configurability makes it a bit more difficult to work with than your average I2C sensor. 

With this experiment I'm hoping to write some scripts to work with all of these features to both demonstrate their use and, ideally, to assist with routine testing while experimenting with potential enhancements or feature additions to the driver package.

The [current state of the driver](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/tree/c55da0dee66302d2fa8ed31623d047c307f409b2) is serviceable and works for most simple cases. But operation of the device can be [a bit wonky](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/issues/23) due to a combination of hard-coded defaults and inability to easily access some useful configuration options.

Since I've been digging in the code lately I'm planning on diving into this a bit more and this will be a home for notes and code generated along the way.

## Boards

Several dev boards have this chip built-in, making those boards handy for testing. There are also a few easy to use breakouts available.

Boards:

* [Adafruit Clue nRF52840](https://www.adafruit.com/product/4500)
  * Guide: <https://learn.adafruit.com/adafruit-clue>
* [Adafruit Feather Bluefruit Sense nRF52840](https://www.adafruit.com/product/4516)
  * Guide: <https://learn.adafruit.com/adafruit-feather-sense>
* [Adafruit Proximity Trinkey SAMD21](https://www.adafruit.com/product/5022)
  * Guide: <https://learn.adafruit.com/adafruit-proximity-trinkey>
* [Adafruit APDS-9960 Breakout (STEMMA QT/Qwiic)](https://www.adafruit.com/product/3595)
  * Guide: <https://learn.adafruit.com/adafruit-apds9960-breakout>

Projects/Guides/Example Code:

* Adafruit Learn Guide: [Motion Controlled Matrix Bed Clock](https://learn.adafruit.com/motion-controlled-matrix-bed-clock/circuit-diagram)
* Adafruit Learn Guide: [Clue Sensor Plotter](https://learn.adafruit.com/clue-sensor-plotter-circuitpython)
* Adafruit Learn Guide: [Bluefruit Playground App](https://learn.adafruit.com/bluefruit-playground-app)
* Adafruit Learn Guide: [ulab: Crunch Numbers fast in CircuitPython](https://learn.adafruit.com/ulab-crunch-numbers-fast-with-circuitpython)
* `pdx.edu`: [Programming the Adafruit Feather nRF52840 Sense: Detecting Light Intensity](https://web.cecs.pdx.edu/~gerry/class/feather_sense/on-board/ambientLight/)
  * This uses Arduino rather than CircuitPython but is still potentially relevant

## Links

* CircuitPython Driver Code: [Adafruit_CircuitPython_APDS9960](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960)
* CircuitPython Driver Docs: [Adafruit APDS9960 Library](https://circuitpython.readthedocs.io/projects/apds9960/en/latest/)
* Vendor Page: [Broadcom APDS-9960](https://www.broadcom.com/products/optical-sensors/integrated-ambient-light-and-proximity-sensors/apds-9960)
* Datasheet (2015): [APDS-9960 Datasheet (AV02-4191EN, 2015/11/13)](https://docs.broadcom.com/doc/AV02-4191EN)
* Datasheet (2013): [APDS-9960 Datasheet (AV02-3191EN, 2013/11/08)](https://cdn-learn.adafruit.com/assets/assets/000/045/848/original/Avago-APDS-9960-datasheet.pdf)
* DigiKey Product Page: [APDS-9960](https://www.digikey.com/en/products/detail/broadcom-limited/APDS-9960/5043146)
* Mouser Product Page: [APDS-9960](https://www.mouser.com/ProductDetail/Broadcom-Limited/APDS-9960?qs=sGAEpiMZZMvjAcTDbo5QTlt5OaISAUfXlP3l3KdQBnM%3D)
* Mouser New Product Page: [Broadcom APDS-9960 Proximity Light & Gesture Sensor](https://www.mouser.com/new/broadcom/broadcom-apds-9960-sensors/)
* Adafruit Breakout Product Page: [Adafruit APDS9960 Proximity, Light, RGB, and Gesture Sensor - STEMMA QT / Qwiic (3595)](https://www.adafruit.com/product/3595)
* Adafruit Breakout Board Files: [Adafruit-APDS9960-Breakout-PCB](https://github.com/adafruit/Adafruit-APDS9960-Breakout-PCB)
* SparkFun Breakout Product Page: [SEN-12787](https://www.sparkfun.com/products/12787)
* SparkFun Arduino Library and Breakout Schematics: [APDS-9960_RGB_and_Gesture_Sensor](https://github.com/sparkfun/APDS-9960_RGB_and_Gesture_Sensor)
* SparkFun Guide: [SparkFun APDS-9960 RGB Sensor Hookup Guide](https://learn.sparkfun.com/tutorials/apds-9960-rgb-and-gesture-sensor-hookup-guide/all)
* Tasmota Implementation Details: [APDS-9960 light and gesture sensor](https://tasmota.github.io/docs/APDS-9960/)