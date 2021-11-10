# Light-up Loupe

Bringing some (highly configurable) light to an inexpensive $8 Carson loupe with CircuitPython and a NeoPixel ring.

## Parts

### Critical Parts

* Carson LumiLoupe LL-10 10x Stand Magnifier
  * Key Specs: _10x magnification, clear plastic base, ~41mm inner diameter at top of stand_ 
  * Carson: <https://carson.com/product/ll-10-stand-magnifier/>
  * Amazon: <https://www.amazon.com/Carson-LumiLoupe-Power-Magnifier-LL-10/dp/B000CAHCQS>
* Adafruit Trinket M0
  * Key Specs: _Runs CircuitPython, 256k flash, 32k RAM, 5 GPIO pins, basic LiPo battery support, adorably tiny module_
  * Adafruit: <https://www.adafruit.com/product/3500>
* Neopixel Ring
  * Key Specs: _27mm ID, 38.6mm OD, 12x `WS2812` 5050 RGB NeoPixels_
  * AliExpress: <https://www.aliexpress.com/item/32659809231.html>
  * This Adafruit item may work but the inner diameter maybe too small: <https://www.adafruit.com/product/1643>
* LiPo Battery
  * Key Specs: _2-pin JST PH connector, ~100 mAh_
  * Adafruit: <https://www.adafruit.com/product/1570>

### Prototyping Parts

* Adafruit Half-Size Perma-Proto PCB
  * Key Specs: _a prototyper's best friend <3_
  * Adafruit: <https://www.adafruit.com/product/1609>
* Potentiomter
  * Key Specs: _10k, linear, breadboard friendly_
  * Adafruit: <https://www.adafruit.com/product/562>
* Tactile Switch x3
  * Key Specs: _12x12mm, SPST-NO, through-hole mount_
  * Digi-Key: <https://www.digikey.com/en/products/detail/e-switch/TL1100DF160Q/29468>

## Usage

### Preparation

The general-purpose CircuitPython binary for the Trinket M0 lacks the `keypad` and `pixelbuf` built-ins in the interest of saving space. So this won't run on that one-size-fits-all binary. Luckily, building a new binary with the stuff we need is easy!

Docs: <https://learn.adafruit.com/building-circuitpython/customizing-included-modules>

The important step here is to configure the CircuitPython build process to ignore some built-ins we don't need and include the build-ins we do.

The customized CircuitPython 7.0.0 Trinket M0 `uf2` binary included here was built with the `mpconfigboard.mk` in this directory and works fine with the code provided.

### Set Up

1. Flash custom firmware to Trinket M0
2. Wire up NeoPixel data line on `D4`
3. Wire up buttons on `D0`/`D1`/`D2`
4. Wire up potentiometer on `D3`
5. Sort out power/ground stuff, make sure battery is on `BAT` pin
6. Fire it up, copy the code over as `code.py`

### Prototype Functions

* Mode/Color Control
  * Press the button on `D0` to cylce through various illumination "modes", including full/partial ring illumination, primary colors and a mixed-colors-on-opposite-sides option.
* Light Position Control
  * Press `D1` and `D2` to rotate the illumination pattern around the ring.
  * Useful for partial-illumination modes, useless if all of the pixels are lit with the same color. :)
* Brigthness Control
  * Rotate the `D3` potentiometer to adjust the brightness of the lighting.

## To Do

* Create a 3D printable replacement upper ring
  * A customized upper ring could easily include slots for boards, buttons, a small trim pot, or even a custom circuit board or flex PCB
* Select some tiny parts and cook up a custom PCB
  * A custom PCB or flex PCB with the right parts could make for a seamless modification that's durable and easy to use.
