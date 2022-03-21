# `circuitpython-experiments`

A collection of demos and experiments built with CircuitPython

## Experiments

### [Clue nRF52840 Express](https://www.adafruit.com/product/4500)

* [`apds-9960-testing`](./clue-nrf52/apds9960-testing)
    * A trip deep, deep down the rabbit-hole with the complex APDS-9960 proximity, gesture, and color/light sensor including copious test code, notes (and even a fancy Jupyter Notebook!) on gesture recognition via CircuitPython

### [Feather Bluefruit Sense](https://www.adafruit.com/product/4516)

* [`all-devices-demo`](./feather-bluefruit-sense/all-devices-demo)
    * Demo: Illustrating use of ALL THE THINGS on this fancy board with CircuitPython 7.0.0.

### [Feather RP2040](https://www.adafruit.com/product/4884)

* [`all-the-things-demo`](./feather-rp2040/all-the-things-demo/)
    * Demo: Illustrating use of ALL THE THINGS on this fancy board with CircuitPython 7.0.0.
* [`rfm95w-lora-featherwing`](./feather-rp2040/rfm95w-lora-featherwing/)
    * Demo: Illustrating basic usage of the [RFM95W LoRa FeatherWing](https://www.adafruit.com/product/3231) for transmitting and receiving messages

### [MacroPad RP2040](https://www.adafruit.com/product/5128)

* [`learn-guide-macros`](./macropad-rp2040/learn-guide-macros)
    * Macro examples for use with the excellent ["Learn Guide" code](https://github.com/adafruit/Adafruit_Learning_System_Guides/tree/main/Macropad_Hotkeys) for the Macropad RP2040

### [MagTag](https://www.adafruit.com/product/4800)

* [`power-testing`](./magtag-esp32-s2/power-testing)
    * Testing the MagTag's power usage to better estimate battery life in various types of use cases.
* [`tasmota-tag`](./magtag-esp32-s2/tasmota-tag)
    * Functional proof of concept for control of Tasmota-flashed, MQTT-enabled LED lightbulbs using a MagTag running CircuitPython with the `adafruit_minimqtt` library.

### [Trinket M0](https://www.adafruit.com/product/3500)

* [`light-up-loupe`](./trinket-m0/light-up-loupe)
    * Prototype: Turning an inexpensive Carson loupe into a fancy ring-lit loupe.

### Notes

* [`python-re-commit-notes.md`](./notes/python-pre-commit-notes.md)
    * Cheat sheet for using `pre-commit`, `black`, `mypy`, and `sphynx` to validate code when preparing contributions to Adafruit's CircuitPython projects