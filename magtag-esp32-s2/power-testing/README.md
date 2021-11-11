# MagTag Power Testing

Testing the MagTag's power usage to better estimate battery life in various types of use cases.

This type of testing will also be useful for comparing different versions of CircuitPython, different hardware configurations, and different code as time moves on.

<img src=".\magtag-power-test-v1.jpg">

## Tools Required

* Adafruit [MagTag](https://www.adafruit.com/product/4800)
  * Adafruit: <https://www.adafruit.com/product/4800>
  * Digi-Key: <https://www.digikey.com/en/products/detail/adafruit-industries-llc/4800/13616787>
* Nordic [PPK2 Power Profiler Kit](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2)
  * Adafruit: <https://www.adafruit.com/product/5048>
  * Digi-Key: <https://www.digikey.com/en/products/detail/nordic-semiconductor-asa/NRF-PPK2/13557476>
* Nordic [Power Profiler software](https://github.com/NordicSemiconductor/pc-nrfconnect-ppk)
  * Included with the freely available [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-desktop) software package
* JST PH 2-Pin to female socket cable for power
  * Can't find one of these online, but can be custom crimped pretty easily
* JST PH 3-Pin (STEMMA) to female socket cable for digital IO
  * Adafruit: <https://www.adafruit.com/product/3894>
  * Can also be custom crimped pretty easily

## Setup

1. MagTag battery input 2-pin JST PH connector `VBAT`, `GND` wired to PPK2 `VOUT`, `GND` in SMU mode
2. MagTag D10 3-Pin JST PH connector `V+`, `GND`, `Signal` wired to PPK2 Logic Port `VCC`, `GND`, and `D7`
3. Nordic PPK2 USB/Data connected to an Ubuntu Linux system running Nordic's Power Profiler v3.2.0
4. Nordic PPK2 USB Power connected to a 5V 1A USB-A charger
5. Nordic Power Profiler software configuration:
  * Mode: `Source Meter`
  * Samples Per Second: `100,000`
  * Sampling Duration: `432 seconds`
  * Timestamps: `On`
  * Digital Channels: `On`, `D7` enabled, all others disabled
  * No changes to default "advanced settings" (gain/smoothing)

## Test Methodology

Start with PPK2 and MagTag devices disconnected with power switches in the off position.

1. Attach MagTag to PPK2 SMU and Digital Input headers
2. Plug in PPK2
3. Start Power Profiler software
4. Start Data Logger
5. Enable Power Output
6. Turn on MagTag
7. Wait for test to complete
8. Stop Data Logger
9. Save/Export Logged Data

### Outputs

Each test run should result in the creation of two files:

* A binary `ppk` for analysis within Nordic Power Profiler
* A plain-text `csv` for analysis using any other tools/methods

### Loading New Code

Because the PPK2's SMU can be disabled in software, we can connect the MagTag to a computer via USB-C for code updating.

Its probably a good idea to make sure the SMU is disabled when the MagTag is attached to the host system though.

Once code is updated/debugged, power off the MagTag and detach the USB-C cable before turning its power back on.

## Test Concepts and Methodology

The general idea is to import modules, execute user code, change states, use peripherals, and perform other actions with periods of `time.sleep()` between them. Performing only one one (or very few) actions before entering 1 or 10 second sleep states assists greatly in identifying the specific code being executed while analyzing things.

### PPK2 Digital IO

The PPK2's digital IO inputs can be useful for helping to pinpoint specifically where we are in the code while digging into things.

In the first test code revision this is flipped to high on a few occasions to make it easier to identify the execution a few specific chunks of code.

* While `SPEAKER_ENABLE` is set to `True`
* While blinking the board LED
* While testing the NeoPixels
* While connecting to the WiFi network

A second output pin is configured on `A1` but didn't end up being used in this testing. This is flipped to `True` when the display is refreshing.

Enabling one or more of these, regardless of whether they're connected or floating, appears to increase power consumption by around 6-7 mA while idle so this should be taken into account while doing any analysis.

### Code

#### `magtag-power-test-v1.py`

The first tests were conducted using `magtag-power-test-v1.py`. This was written in just a few minutes without a lot of debugging just to see if this would work conceptually.

There are 7 main phases of this code with 10 second sleeps between them:

1. Startup and import of `time`, `board`, `digitalio`
2. Init of peripherals
  * `indicator_pin`
  * `indicator2_pin`,
  * board LED, 
  * `SPEAKER_ENABLE`, enabled for 1 sec, disable for 1 sec
  * `NEOPIXEL_POWER_INVERTED`, enabled for 2 sec, disabled for 1 sec
  * Init of NeoPixels
3. LED/Neopixel Tests
  * Flash of board D13 LED for 1 sec
  * Single NeoPixel max/half-bright for 1 sec each
  * All NeoPixels max/half-bright for 1 sec each
  * NeoPixels `deinit()`, sleep 1 sec
  * `NEOPIXEL_ENABLE` pin to `False`, sleep 1 sec
4. Refresh of display (will contain console output from `print` statements)
5. Preparing WiFi connect with import of `secrets` and `wifi` and definition of a helper method
6. Connect to WiFi network
6. Disable WiFi
7. Loop:
  * If radio enabled and WiFi not connected, reconnect.
  * Refresh display, toggle `wifi.radio.enabled`

## Test Results

### `magtag-power-test-v1`, first run

Device: `MagTag` w/ `ESP32-S2-WROOM` module
Bootloader: `0.5.2`
CircuitPython: `7.0.0 (release)`

Data from first test run, `3.7 V`:

* **Initial boot**: `34.91 mA` avg (`870 mA` peak) over `1.329 s` for `46.41 mC` of charge
* **CircuitPython boot**: `44.03 mA` avg (`700 mA` peak) over `1.054 s` for `46.43 mC` of charge
  * Each NeoPixel blink (~`125 ms`) averages `45.23 mA` (`96.80 mA` peak) for `5.70 mC` of charge
  * Idle between blinks: `44.22 mA`
  * Idle after blinks, before first imports: `27.09 mA` (about `1.5 s`)
* **Phase 0**: 1x print statement, import `time`, `sleep(10)`: `46.30 mA` avg (peak `65.31 mA`) over `488.1 mS` for `23.63 mC` of charge
  * Idle after print, before import: `27.1 mA` avg (`31.30mA` peak) over `35.12 mS`
* **Phase 0 End, `sleep(10)`**: `29.28 mA` avg (`34.53 mA` peak) over `9.999 s` for `292.76 mC` of charge
* **Phase 1**: print statement, `import board`, `import digitalio`, print statement
  * `52.02 mA` avg (`57.48 mA` peak) over `0.596 mS` for `0.031 mC` of charge
* **Phase 1 End, `sleep(10)`**: `29.30 mA` (`34.23 mA` peak) over `9.999 s` for `292.98 mC` of charge
* **Phase 2**: Digital I/O and NeoPixel setup: `30.57 mA` avg (`720 mA` peak) over `6.035 s` for `184.52 mC` of charge
  * Pin setup: `49.54 mA` (`56.11 mA` peak) over `0.25 mS` for `0.012 mC` of charge
  * Speaker pin enable, `sleep(1)`, disable: Idle increases to `36.28 mA` (delta of `+6.98 mA`)
  * NeoPixel import and setup: `52.21 mA` avg (`720 mA` peak) over `32.49 mS` for `1.70 mC` of charge 
* **Phase 2 End, `sleep(10)`**: `30.54 mA` avg (`35.98 mA` peak) over `9.999 s` for `305.38 mC` of charge
* **Phase 3**: LED and Neopixel tests: `51.55 mA` avg (`207.53 mA` peak) over `16.01 s` for `830 mC` of charge
  * Indicator pin 1 on, on for 1 sec: `32.90 mA` avg (`59.50 mA` peak) over `1 s` for `32.91 mC` of charge
  * I1 and LED on for 1 sec: `33.07 mA` avg (`56.69 mA` peak) over `1 s` for `33.07 mC` of charge
  * `pixel[0] = (255,255,255)` @ 1.0: `68.68 mA` avg (`95.26 mA` peak) over `1 s` for `68.74 mC` of charge
  * `pixel[0] = (255,255,255)` @ 0.5: `49.99 mA` avg (`96.80 mA` peak) over `1 s` for `50.05 mC` of charge
  * `pixel[0] = (255,255,255)` @ 0.1: `35.48 mA` avg (`94.49 mA` peak) over `1 s` for `35.52 mC` of charge
  * `pixel[0] = (255,255,255)` @ 0.05: `33.35 mA` avg (`83.73 mA` peak) over `1 s` for `33.38 mC` of charge
  * `pixel[0] = (255,0,0)`@ 1.0: `45.35 mA` avg (`77.58 mA` peak) over `1 s` for `45.39 mC` of charge
  * `pixel[0] = (0,255,0)`@ 1.0: `45.48 mA` avg (`76.81 mA` peak) over `1 s` for `45.48 mC` of charge
  * `pixel[0] = (0,0,255)`@ 1.0: `43.90 mA` avg (`76.05 mA` peak) over `1 s` for `43.94 mC` of charge
  * `pixels.fill(0,0,0)`: `32.94 mA` avg (`75.28 mA` peak) over `1 s` for `32.97 mC` of charge
  * `pixels.fill(255,255,255)` @ 1.0: `163.29 mA` avg (`207.53 mA` peak) over `1 s` for `163.44 mC` of charge
  * `pixels.fill(255,255,255)` @ 0.5: `99.30 mA` avg (`191.96 mA` peak) over `1 s` for `99.40 mC` of charge
  * `pixels.fill(255,255,255)` @ 0.1: `43.84 mA` avg (`181.07 mA` peak) over `1 s` for `43.86 mC` of charge
  * `pixels.fill(255,255,255)` @ 0.05: `35.01 mA` avg (`131.01 mA` peak) over `1 s` for `35.07 mC` of charge
  * `pixels.deinit()`: `31.68 mA` avg (`99.87 mA` peak) over `1 s` for `31.71 mC` of charge
* **Phase 3 End, `sleep(10)`**: `29.28 mA` avg (`34.58 mA` peak) over `9.999 sec` for `292.83 mC`
* **Phase 4**: Display Init and Refresh: `32.8 mA` avg (`66.84 mA` peak) over `5.371 s` for `176.15 mC` of charge
  * Core display refresh process: `35.04 mA` avg (`66.84 mA` peak) over `2.371 s` for `83.11 mC` of charge
  * Note: `indicator2` pin is pulled up, probably adding 6-7 mA on top of base current
* **Phase 4 End, `sleep(10)`**: `29.30 mA` avg (`34.63 mA` peak) over `9.999 s` for `293.03 mC` of charge
* **Phase 5**: `from secrets import secrets`, `import wifi`: `109.45 mA` avg (`289.75 mA` peak) over `154.5 ms` for `16.91 mC` of charge
* **Phase 5 End, `sleep(10)`**: `79.52 mA` avg (`107.57 mA` peak) over `9.999 s` for `800 mC` of charge
  * Average current draw delta of `+50.22 mA`, more than doubling current, after importing `wifi` and before any WiFi activity
* **Phase 6**: `wifi.radio.connect()`: `92.40 mA` avg (`670 mA` peak) over `3.362 s` for `310.72 mC` of charge
* **Phase 6 End, `sleep(10)`**: `31.32 mA` avg (`307.08 mA` peak) over `9.999 s` for `313.21 mC` of charge
  * Average current draw is back down a delta of only `+2.02 mA` over previous base power draw but there are large `300 mA` spikes every `315 ms` or so lasting about `12-13 ms` before dropping back to a new, slightly lower baseline of about `27.02 mA`.
* **Phase 7**: `wifi.radio.enabled = False`: `154.51 mA` avg (`328.38 mA` peak) over `29.26 ms` for `4.52 mC` of charge
* **Phase 7 end, `sleep(10)`**: `27.04 mA` avg (`51.2 mA` peak) over `9.999 s` for `270.42 mC` of charge

### Totals: v1, first run

Run Time: `115.3 s`
Current (avg): `39.28 mA`
Current (peak): `870 mA`
Charge: `4.53 C`

## EOF
