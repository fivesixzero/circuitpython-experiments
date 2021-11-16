# APDS9960 Notes

From the [datasheet](https://docs.broadcom.com/doc/AV02-4191EN):

>The APDS-9960 device features advanced Gesture detection, Proximity detection, Digital Ambient Light Sense (ALS) and Color Sense (RGBC). The slim modular package, L 3.94 × W 2.36 × H 1.35 mm, incorporates an IR LED and factory calibrated LED driver for drop-in compatibility with existing footprints.

## Core Functions

* Proximity detection
* Gesture detection
* Color & ambient light detection

### Features

* Configurable options enable very low power usage
    * Wait timer in main state loop and wait timers
    * Deep tuning options for LED pulses and power within proximity/gesture engines
    * Sleep-after-interrupt allows
* Internal interrupts
    * Enables the host to poll state regardless of position in the internal state machine
* Configurable interrupt pin
    * Allows configuration of asynchronous notification of the host in a variety of circumstances

The combination of these features, particularly the configurability of the interrupt pin, allow for a wide variety of use cases.

### Device Wide Flow Pseudocode

The sensor incorporates a state machine with a predictable flow to control all of its operations.

```py
def device_cycle(self):
    time.sleep(0.0057) # Initial power-up takes 5.7ms

    while self.powered_on:
        ## Sleep/wake State Handling
        while not self.awake:
            # While asleep, only i2c communication is enabled
            self.awake = self.pon & (self.pen | self.gen | self.aen)
            pass
        time.sleep(0.007) # Sleep exit takes 7 ms
        
        while self.awake:
            ## Run Engines

            ## PROXIMITY ENGINE
            if self.pen:
                self.proximity_engine()

            if self.pdata >= self.gpenth:
                self.gmode = True

            ## GESTURE ENGINE
            if self.gen and self.gmode:
                self.gesture_engine()
            
            ## WAIT TIME
            if self.wen:
                multiplier = 1
                if self.wlong:
                    multiplier = 12
                time.sleep((256 - self.wtime) * 2.78 * multiplier)

            ## COLOR/LIGHT ENGINE
            if self.aen:
                self.color_engine() # COLOR/LIGHT

            ## SLEEP-AFTER-INTERRUPT
            if self.sai and self.int_pin_asserted:
                self.awake = False
                break
```

## Proximity Engine

Proximity is measured by reflected IR energy from pulses an internal IR LED.

A cycle of the proximity engine results in an 8-bit value being placed in the `PDATA` register.

### Proximity Flow Pseudocode

```py
pen = False # default proximity engine enable set by driver
ppers = 4 # default persistence threshold set by driver
pilt = 0 # default proximity low threshold set by driver
piht = 0 # default proximity high threshold set by driver
pien = False # default proximity interrupt enable value set by driver

def proximity_engine(self) -> None:
    if pen:
        self.pdata = self.sense_prox_data()
        self.pvalid = 1
        if self.pilt <= self.pdata <= self.piht:
            self.prox_persistence = 0
        else:
            self.prox_persistence += 1
            if self.prox_persistence >= self.ppers
                self.pint = True
                if self.pien:
                    self.assert_int_pin()
                else:
                    pass
            else:
                pass
    else:
        pass
```

#### Proximity Sensing Details

`self.sense_prox_data()` was used in the pseudocode to simplify the process of analog signal acquisition, which in itself is quite complex.

This is what the process looks like, at a lower level, when the Proximity State Machine performs its proximity measurement.

1. IR LED is pulsed
    * IR LED Wavelength: `950 nm`, `+-30 nm` (not configurable)
    * IR LED Rise/Fall Time: `20 ns` (not configurable)
    * Pulse Count: 1 pulse default, `PPULSE<PPULSE>`
    * Pulse Length: `8 us` default, `PPULSE<PPLEN>`
    * Pulse Strength: `100 mA` default, `LDRIVE`*`LBOOST`
2. IR reflections are detected by phototransistors feeding an ADC
    * ADC Conversion Time: `696.6 us` (not configurable)
    * ADC Integration Steps: `1` (not configurable)
    * ADC Counts: `255`
    * Photosensor gain and selection via masking is configurable via registers
3. ADC count is stored in `PDATA` register
    * Control is returned to the Proximity Engine state machine

Detection range depends on a lot of factors, some of which can be adapted to via configuration. An example is provided in the datasheet that illustrates both the sensor's adaptability and the limitations of this approach in terms of absolute precision.

| Parameter | Min | Typ | Max | Units | Test Conditions |
|---|---|---|---|---|---|
| Proximity ADC count value, 100 mm distance object | 96 | 120 | 144 | counts | Reflecting object – 73 mm × 83 mm Kodak 90% grey card, 100 mm distance, VLEDA = 3 V, LDRIVE = 100 mA, PPULSE = 8, PGAIN = 4x, PPLEN = 8 ms, LED_BOOST = 100%, open view (no glass) above the module. |

A footnote indicates that the sensor implementation for this test has no glass or aperture above the module and that the result is an average of 5 consecutive readings. Another footnote mentions that the LED driver is calibrated to achieve this spec at the factory.

### Proximity Configuration Register Reference

| Category | R/W | Address | Name | Description | Notes |
|---|---|---|---|---|---|
| Enable/Disable | R/W | `0x80[2]` | `ENABLE<PEN>` | Proximity Enable | `0` _default_ |
| Data | R/W | `0x9C` | `PDATA` | Proximity Data | _8-bit unsigned int value (0-255)_<br>`0` = max distance, `255` = min distance |
| | RO | `0x93[1]` | `STATUS<PVALID>` | Proximity Valid | Asserted after read-in of valid sensor data to `PDATA`<br>Cleared on `PDATA` read |
| Interrupts | RO | `0x93[5]` | `STATUS<PINT>` | Proximity Interrupt | Asserted within Proximity Engine after enough valid measurements are returned within thresholds to satisfy persistence (`PPERS`) requirement |
| | RO |  `0x93[6]` | `STATUS<PGSAT>` | Analog Saturation Interrupt | Asserted if an analog saturation event occurs while reading in proximity data<br>Asserts interrupt pin if `PSIEN` is asserted<br>Cleared via `PICLEAR` or de-asserting `PEN`<br>_shared with Gesture Engine_
| Interrupt<br>Clearing | WO | `0xE5` | `PICLEAR` | Proximity-only Interrupt Clear | |
| | WO | `0xE7` | `AICLEAR` | All non-gesture Interrupt Clear | |
| Interrupt Config | R/W | `0x89` | `PILT` | Proximity Interrupt Low Threshold | Far-distance Threshold<br>_8-bit unsigned int value (0-255)_<br>`0` _default_ = max distance, `255` = min distance
| | R/W | `0x8B` | `PIHT` | Proximity Interrupt High Threshold | Close-distance Threshold<br>_8-bit unsigned int value (0-255)_<br>`0` = max distance, `255` = min distance
| | R/W | `0x8C[7:4]` | `PERS<PPERS>` | Proximity Interrupt Persistence | Number of continuous in-threshold cycles required before internal interrupt is triggered<br>_4-bit unsigned int value (0-15)_<br>`0` _default_
| Interrupt Pin<br>Config | R/W | `0x80[5]` | `ENABLE<PIEN>` | Proximity Interrupt Enable | Enables assert of interrupt pin when proximity interrupt (`PINT`) is asserted<br>`0` _default_
| | R/W | `0x90[8]` | `CONFIG2<PSIEN>` | Proximity Saturation Interrupt Enable | Enables assert of interrupt pin when proximity/gesture saturation interrupt (`PGSAT`) is asserted<br>`0` _default_
| LED<br>Config | R/W | `0x8E[7:6]` | `PPULSE<PPLEN>` | Proximity Pulse Length | Length of LED pulses for proximity measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `4 usec`, `0x1` = `8 usec` _default_, `0x02` = `16 usec`, `0x03` = `32 usec`
| | R/W | `0x8E[5:0]` | `PPULSE<PPULSE>` | Proximity Pulse Count | Number of LED pulses during each proximity measurement<br>_6-bit int value (0-63)_<br>`0` _default_ = `1`, ... `63` = `64`
| | R/W | `0x8F[7:6]` | `CONTROL<LDRIVE>` | LED Drive Strength | Output power of LEDs during proximity measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `100 mA` _default_, `0x1` = `50 mA`, `0x2` = `25 mA`, `0x3` = `12.5 mA`
| | R/W | `0x90[5:4]` | `CONFIG2<LEDBOOST>` | LED Drive Multiplier | Multiplier for output power of LEDs during proximity measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `100%` _default_, `0x1` = `150%`, `0x2` = `200%`, `0x3` = `300%`<br>Shared with Gesture Engine
| Sensor<br>Config | R/W | `0x8F[3:2]` | `CONTROL<PGAIN>` | Proximity Sensor Gain | Gain value for sensor readings during proximity measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `1x` _default_, `0x1` = `2x`, `0x2` = `4x`, `0x3` = `8x`
| | R/W | `0x9F[5]` | `CONFIG3<PCMP>` | Proximity Gain Compensation Enable | Enables gain compensation to adjust for reduced input, should be asserted in most cases where one or more photodiodes are masked<br>`0` _default_
| | R/W | `0x9F[3]` | `CONFIG3<PMSK_U>` | Proximity Mask: Up | Disables "up" photodiode output during proximity measurements<br>`0` _default_ |
| | R/W | `0x9F[2]` | `CONFIG3<PMSK_D>` | Proximity Mask: Down | Disables "down" photodiode output during proximity measurements<br>`0` _default_ |
| | R/W | `0x9F[1]` | `CONFIG3<PMSK_L>` | Proximity Mask: Left | Disables "left" photodiode output during proximity measurements<br>`0` _default_ |
| | R/W | `0x9F[0]` | `CONFIG3<PMSK_R>` | Proximity Mask: Right | Disables "right" photodiode output during proximity measurements<br>`0` _default_ |
| | R/W | `0x9D` | `POFFSET_UR` | Proximity Up/Right Sensor Offset | Offset to be applied to sensor values from the up/right sensor pair<br>_1-bit sign w/ 7-bit integer_<br>`0` default, `-127` to `127` |
| | R/W | `0x9E` | `POFFSET_DL` | Proximity Down/Left Sensor Offset | Offset to be applied to sensor values from the down/left sensor pair<br>_1-bit sign w/ 7-bit integer_<br>`0` default, `-127` to `127` |

### Proximity Driver Implementation

Fully implementing a driver would require exposing all of the relevant config options, many of which are superfluous except for a few specific use cases. For general-purpose use a subset of these would be easier to work with.

#### Proximity Data/State/Config Items Available

Because drivers in CircuitPython can be used on wide variety of platforms with very different constraints, offering a 'basic' driver that fits most use cases while occupying as little memory as possible makes sense. This is a very powerful sensor though so it also makes sense to offer more configuration for more advanced use cases, possibly in an optional subclass that can be ignored on constrained hardware.

A tiered model with 'basic', 'intermediate' and 'advanced' tiers might look something like this.

* Enable/disable, read data/state (basic)
* Interrupt configuration (intermediate)
* LED/sensor and masking/offset configuration (advanced)

## Gesture Engine

At a high level, the gesture engine uses LED pulses to detect movement across its four photosensors in one of four directions: up, down, left, or right. It shares a lot of concepts (and a few config registers) with the proximity engine but it is a much more complex system.

Results are generated from the same three factors as proximity:

* LED Emission
* IR Reception
* Environmental Factors

### Gesture Engine State Machine Pseudocode

```py
self.gesture_fifo = [] # gesture fifo starts empty on power up, is cleared as data is read out
self.gfifoth = 4 # default fifo intterupt depth set by driver
self.gexth = 0 # default gesture size exit threshold set by driver
self.gexpers = 0 # default gesture persistence set by driver
self.gwtime = 0 # default gesture-cycle wait time set by driver
self.gien = False # default gesture interrupt enable

def gesture_engine(self) -> None:
    # If gmode == 0 we shouldn't even be here
    if not self.gmode:
        return
    
    self.gesture_persistence = 0 # Internal loop persistence counter

    # LOOP START: Most of the work happens in this loop
    while True:
        # Data Acquisition (simplified)
        gesture_data = self.gesture_data_acquisition()
        
        # FIFO and Interrupt Handling
        if not (self.gflvl == 32):
            self.gesture_fifo.append(gesture_data)
            self.gflvl += 1
            if self.gflvl >= self.gfifoth:
                self.gvalid = 1
                self.gint = 1
                if self.gien:
                    self.assert_int_pin()
                else:
                    pass
            else:
                pass
        else:
            self.gfov = 1
            
        # Loop Control
        if not self.gexth == 0:
            if not self.gesture_data <= self.gexth:
                # Reset persistence if sensed values are too low
                self.gesture_persistence = 0
            else:
                self.gesture_persistence += 1
        
            if not (self.gesture_persistence >= self.gexpers):
                # Keep looping (after a wait) if we haven't hit our persistence threshold yet
                pass
            else:
                # Stop loop, skip wait, exit gesture detect loop once we've hit persistence threshold
                self.gmode = 0
                break 
        
        if not self.gmode:
            # Stop looping here if gmode gets set to 0 via I2C
        else:
            # Between-Gesture-Cycles Wait Timer
            if self.gwtime > 0:
                time.sleep(self.gwtime * 0.0028)
    # LOOP END

    if self.gvalid:
        self.gint = 1
        if self.gien:
            self.assert_int_pin()
        return #exit geture engine
    else:
        self.gesture_fifo = [] # dump orphaned data
        return # exit gesture engine            
```

### Gesture Configuration Register Reference

| Category | R/W | Address | Name | Description | Notes |
|---|---|---|---|---|---|
| Enable/Disable | R/W | `0x80[6]` | `ENABLE<GEN>` | Gesture Enable | _`0` default_ |
| Core Gesture<br>Engine Config | R/W | `0xA0` | `GPENTH` | Gesture Proximity Entry Threshold | Controls entry to the Gesture Engine by requiring a high enough `PDATA` for Gesture Engine entry<br>At a low level, this feeds a decision between Proximity Engine complete and Gesture Engine entry that sets `GMODE` if `PDATA` >= `GPENTH`<br>_8-bit unsigned int_<br>`0` _default_ |
|  | R/W | `0xA1` | `GEXTH` | Gesture Exit Threshold | Threshold for sensor input to be considered "persistent" within Gesture Engine loop handling<br>_8-bit unsigned int_<br>`0` _default_
|  | R/W | `0xA2[1:0]` | `GCONFIG1<GEXPERS>` | Gesture Exit Persistence | Number of consecutive "gesture end" occurrences required before exiting Gesture Engine<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` _default_ = `1 cycle`, `0x1` = `2 cycles`, `0x2` = `4 cycles`, `0x3` = `7 cycles`
|  | R/W | `0xA2[5:2]` | `GCONFIG1<GEXMSK>` | Gesture Exit Mask | Masks U/D/L/R photodiodes when determining if a "gesture end" event has occurred<br>_bitfield sequence of `UDLR`, where photodiode in that position is ignored if asserted_<br>`0000` (none masked) _default_
|  | R/W | `0xA2[7:6]` | `GCONFIG1<GFIFOTH>` | Gesture FIFO Threshold | Threshold for number of gesture datasets to wait for before asserting `GINT`<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` _default_ = `1 dataset`, `0x1` = `4 datasets`, `0x2` = `8 datasets`, `0x3` = `16 datasets`
|  | R/W | `0xA3[2:0]` | `GCONFIG2<GWTIME>` | Gesture Wait Time | Wait time for low-power state between repeated gesture cycles (ie, if persistence isn't yet met)<br>_3-bit int value (0-7)_<br>`0` _default_, multiply by cycle time (`2.78 ms`) for actual wait duration
| Data | RO | `0xFC` | `GFIFO_U` | Gesture FIFO Up Value | Buffer containing gesture UP data
|  | RO | `0xFD` | `GFIFO_D` | Gesture FIFO Down Value | Buffer containing gesture DOWN data
|  | RO | `0xFE` | `GFIFO_L` | Gesture FIFO Left Value | Buffer containing gesture LEFT data
|  | RO | `0xFF` | `GFIFO_R` | Gesture FIFO Right Value | Buffer containing gesture RIGHT data
|  | RO | `0xAE` | `GFLVL` | Gesture FIFO Level | Number of 4-byte gesture datasets available in FIFO for read<br>_8-bit unsigned int_ |
|  | RO | `0xAF[1]` | `GSTATUS<GFOV>` | Gesture FIFO Overflow | Asserted if FIFOs are full<br>When FIFOs are full, new gesture data is not collected |
|  | RO | `0xAF[0]` | `GSTATUS<GVALID>` | Gesture Valid | Asserted if valid gesture data is available<br>Assert can be delayed until FIFOs fill to a specific point by setting `GFIFOTH`<br>Cleared when FIFOs are clear (ie, all data has been read)
| Status | R/W | `0xAB[2]` | `GCONFIG4<GFIFO_CLR>` | Gesture FIFO Clear | Assert clears `GFIFO`, `GINT`, `GVALID`, `GFIFO_OV` and `GFIFO_LVL`
|  | R/W | `0xAB[0]` | `GCONFIG4<GMODE>` | Gesture Mode | Asserted at end of Proximity Engine run if `PDATA` >= `GPENTH` to signal that gesture engine is ready to execute<br>Will stay asserted while engine is looping, can be de-asserted to force exit of gesture engine<br>Can also be manually asserted to effectively ignore `GPENTH` and force engine enable
| Interrupts | RO | `0x93[2]`  | `STATUS<GINT>` | Gesture Interrupt | Asserted within Gesture Engine when valid gesture data is available<br>Clears only when FIFOs are completely emptied or cleared
|  | RO | `0x93[6]` | `STATUS<PGSAT>` | Analog Saturation Interrupt | Asserted if an analog saturation event occurs while reading in gesture data<br>Asserts interrupt pin if `PSIEN` is asserted<br>Cleared via `PICLEAR` or de-asserting `PEN`<br>_shared with Proximity Engine_
| Interrupt Pin<br>Config | R/W | `0xAB[1]` | `GCONFIG4<GIEN>` | Gesture Interrupt Enable | Enables assert of interrupt pin when gesture interrupt (`GINT`) is asserted<br>`0` _default_
| LED<br>Config | R/W | `0xA6[7:6]` | `GPULSE<GPLEN>` | Gesture Pulse Length | Length of LED pulses for gesture measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `4 usec`, `0x1` = `8 usec` _default_, `0x02` = `16 usec`, `0x03` = `32 usec`
|  | R/W | `0xA6[5:0]` | `GPULSE<GPULSE>` | Gesture Pulse Count | Number of LED pulses during each gesture measurement<br>_6-bit int value (0-63)_<br>`0` _default_ = `1`, ... `63` = `64`
|  | R/W | `0xA3[4:3]` | `GCONFIG2<GLDRIVE>` | Gesture LED Drive Strength | Output power of LEDs during gesture measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `100 mA` _default_, `0x1` = `50 mA`, `0x2` = `25 mA`, `0x3` = `12.5 mA`
|  | R/W | `0x90[5:4]` | `CONFIG2<LEDBOOST>` | LED Drive Multiplier | Multiplier for output power of LEDs during proximity and gesture measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `100%` _default_, `0x1` = `150%`, `0x2` = `200%`, `0x3` = `300%`<br>Shared with Proximity Engine
| Sensor Config | R/W | `0xA3[6:5]` | `GCONFIG2<GGAIN>` | Gesture Sensor Gain | Gain value for sensor readings during gesture measurements<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = `1x` _default_, `0x1` = `2x`, `0x2` = `4x`, `0x3` = `8x`
|  | R/W | `0xA4` | `GOFFSET_U` | Gesture Up Sensor Offset | Offset to be applied to sensor values from the up sensor<br>_1-bit sign w/ 7-bit integer_<br>`0` default, `-127` to `127`
|  | R/W | `0xA5` | `GOFFSET_D` | Gesture Up Sensor Offset | Offset to be applied to sensor values from the down sensor<br>_1-bit sign w/ 7-bit integer_<br>`0` default, `-127` to `127`
|  | R/W | `0xA7` | `GOFFSET_L` | Gesture Up Sensor Offset | Offset to be applied to sensor values from the left sensor<br>_1-bit sign w/ 7-bit integer_<br>`0` default, `-127` to `127`
|  | R/W | `0xA9` | `GOFFSET_R` | Gesture Up Sensor Offset | Offset to be applied to sensor values from the right sensor<br>_1-bit sign w/ 7-bit integer_<br>`0` default, `-127` to `127`
|  | R/W | `0xAA[1:0]` | `GCONFIG3<GDIMS>` | Gesture Dimension Select | Selects which gesture photodiode pairs are enabled for data acquisition during gesture cycles<br>_2-bit int (0-3), mapped to distinct values_<br>`0x0` = both pairs are active, `0x1` = only up/down, ignore left/right, `0x2` = only left/right, ignore up/down, `0x3` = both pairs are active

### Gesture Driver Implementation

TODO

### Bug Analysis/Fix: Proximity sticks 51 with gesture enabled

Issue: <https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/issues/23>

With just proximity enabled, the proximity system works fine. But once gesture is enabled, proximity values get stuck at 51 indefinitely. Although this resets to 0 after a program reset, proximity is broken until the sensor is fully power cycled.

#### Replication

This was easy to reproduce using a script built around the `gesture_simpletest` code.

I decided to capture I2C traffic during use, specifically before, during, and after the "stuck at 51" issue occurs, then capture 

A few interesting observations.

First, `GMODE` should be set to `0` when the gesture engine completes a run. Before we get a successful engine entry, it stays at `0`. For some reason, it continues to be stuck at `1` after a gesture call.

#### Gesture Operation I2C Capture/Analysis

##### Capture Data: Post stuck-at-51 state

To start, I figured I should start at the bare metal by checking on I2C bus traffic with a logic analyzer. If we're not communicating the way we think we are then, well, all bets are off.

| Register | Read | Write | Reg Name | Code Location | Note
|---|---|---|---|---|---|
| 0xAE | 0x20 |  | `GFLVL` | Driver, start of `gesture()` loop | Getting `GFLVL` before asking for gesture data
| 0xFC | _128 byte stream_ |  | `GFUFO_U` | Driver, in `gesture()` loop | Gesture FIFO page read (32 recs, 4x bytes each) |
| 0x80 | 0x45 |  | `ENABLE` | Test code | Read of enable status for `GEN` |
| 0xAF | 0x01 |  | `GSTATUS`  | Test code | Read of gesture status for `GVALID`
| 0xAB | 0x01 |  | `GCONF4` | Test code | Read of gesture config for `GMODE`
| |  | | | | _~370ms of quiet_ |
| 0x9C | 0x33 |  | `PDATA` | Test code | Read of proximity data (already stuck at 51)
| 0x80 | 0x45 |  | `ENABLE` | Test code | Read of enable status for `PEN`
| 0x80 | 0x45 |  | `ENABLE` | Test code | Read of enable status for `PIEN`
| |  | | | | _~3ms of quiet_ |
| 0xAF | 0x03 | | `GSTATUS` | Driver, pre-loop in `gesture()` | Checking `GVALID` pre-loop (note that both `GVALID` and `GFOV` are asserted)
| |  | | | | _~408ms of quiet_ |
| 0xAE | 0x20 |  | `GFLVL` | Driver, start of `gesture()` loop | Getting `GFLVL` before asking for gesture data
| 0xFC | _128 byte stream_ |  | `GFUFO_U` | Driver, in `gesture()` loop | Gesture FIFO page read (32 recs, 4x bytes each) |
| 0x80 | 0x45 |  | `ENABLE` | Test code | Read of enable status for `GEN` |
| 0xAF | 0x01 |  | `GSTATUS`  | Test code | Read of gesture status for `GVALID`
| 0xAB | 0x01 |  | `GCONF4` | Test code | Read of gesture config for `GMODE`
| |  | | | | _~370ms of quiet_ |
| 0x9C | 0x33 |  | `PDATA` | Test code | Read of proximity data (already stuck at 51)
| 0x80 | 0x45 |  | `ENABLE` | Test code | Read of enable status for `PEN`
| 0x80 | 0x45 |  | `ENABLE` | Test code | Read of enable status for `PIEN`
| |  | | | | _~3ms of quiet_ |
| 0xAF | 0x03 | | `GSTATUS` | Driver, pre-loop in `gesture()` | Checking `GVALID` pre-loop (note that both `GVALID` and `GFOV` are asserted)
| |  | | | | _~370ms of quiet_ |
| 0xAE | 0x20 |  | `GFLVL` | Driver, start of `gesture()` loop | Getting `GFLVL` before asking for gesture data
| 0xFC | _128 byte stream_ |  | `GFUFO_U` | Driver, in `gesture()` loop | Gesture FIFO page read (32 recs, 4x bytes each) |

Fortunately, it looks like we are indeed operating like we expect to be. Which is good because the analysis is pretty time-consuming work. :joy:

#### Configuration Analysis

So our bus communication is just fine, no real surprises there... Aside from some unexpected stuff in our registers. Like, why is `GMODE` (`GCONF4[0]`) true after `gesture()` runs?

Hmm. By checking and comparing config/status register states in four different cases we should be able to understand what's going on.

1. Power-on without any driver init
2. After driver init, before user code changes state
3. After user code configures state
4. After a few loops of "normal" activity that _should not trigger the gesture engine_ (ie, proximity less than the driver-configured `GPENTH` of `50`)
5. A few loops after the "bugged" activity, where we see `PDATA` stuck at `51` permanently

The important thing about this involves power cycling. Once the sensor has power, if it gets stuck in any of its engine state machines it'll just stay there forever since our driver init doesn't do any "hard reset" type stuff for us (another topic to talk about eventually, maybe)

##### Config register states after import with current driver

First we'll look at a diff between power-on-default config register state and post-init register state. 

Fresh device state after power on with all of the device-configuring lines in `__init__()`  commented out:

```
 _APDS9960_ENABLE       0x80 | 0x00 | 00000000
 _APDS9960_ATIME        0x81 | 0xFF | 11111111
 _APDS9960_WTIME        0x83 | 0xFF | 11111111
 _APDS9960_AILTIL       0x84 | 0x09 | 00001001
 _APDS9960_AILTH        0x85 | 0x45 | 01000101
 _APDS9960_AIHTL        0x86 | 0x00 | 00000000
 _APDS9960_AIHTH        0x87 | 0x00 | 00000000
 _APDS9960_PILT         0x89 | 0x00 | 00000000
 _APDS9960_PIHT         0x8B | 0x00 | 00000000
 _APDS9960_PERS         0x8C | 0x00 | 00000000
 _APDS9960_CONFIG1      0x8D | 0x60 | 01100000
 _APDS9960_PPULSE       0x8E | 0x40 | 01000000
 _APDS9960_CONTROL      0x8F | 0x00 | 00000000
 _APDS9960_CONFIG2      0x90 | 0x01 | 00000001
 _APDS9960_STATUS       0x93 | 0x00 | 00000000
 _APDS9960_POFFSET_UR   0x9D | 0x00 | 00000000
 _APDS9960_POFFSET_DL   0x9E | 0x00 | 00000000
 _APDS9960_CONFIG3      0x9F | 0x00 | 00000000
 _APDS9960_GPENTH       0xA0 | 0x00 | 00000000
 _APDS9960_GEXTH        0xA1 | 0x00 | 00000000
 _APDS9960_GCONF1       0xA2 | 0x00 | 00000000
 _APDS9960_GCONF2       0xA3 | 0x00 | 00000000
 _APDS9960_GOFFSET_U    0xA4 | 0x00 | 00000000
 _APDS9960_GOFFSET_D    0xA5 | 0x00 | 00000000
 _APDS9960_GPULSE       0xA6 | 0x40 | 01000000
 _APDS9960_GOFFSET_L    0xA7 | 0x00 | 00000000
 _APDS9960_GOFFSET_R    0xA9 | 0x00 | 00000000
 _APDS9960_GCONF3       0xAA | 0x00 | 00000000
 _APDS9960_GCONF4       0xAB | 0x00 | 00000000
 _APDS9960_GFLVL        0xAE | 0x00 | 00000000
 _APDS9960_GSTATUS      0xAF | 0x00 | 00000000
```

Fresh device state after power on with config lines present:

```
 _APDS9960_ENABLE       0x80 | 0x01 | 00000001
 _APDS9960_ATIME        0x81 | 0x01 | 00000001
 _APDS9960_WTIME        0x83 | 0xFF | 11111111
 _APDS9960_AILTIL       0x84 | 0x09 | 00001001
 _APDS9960_AILTH        0x85 | 0x45 | 01000101
 _APDS9960_AIHTL        0x86 | 0x00 | 00000000
 _APDS9960_AIHTH        0x87 | 0x00 | 00000000
 _APDS9960_PILT         0x89 | 0x00 | 00000000
 _APDS9960_PIHT         0x8B | 0x00 | 00000000
 _APDS9960_PERS         0x8C | 0x00 | 00000000
 _APDS9960_CONFIG1      0x8D | 0x60 | 01100000
 _APDS9960_PPULSE       0x8E | 0x40 | 01000000
 _APDS9960_CONTROL      0x8F | 0x01 | 00000001
 _APDS9960_CONFIG2      0x90 | 0x01 | 00000001
 _APDS9960_STATUS       0x93 | 0x00 | 00000000
 _APDS9960_POFFSET_UR   0x9D | 0x00 | 00000000
 _APDS9960_POFFSET_DL   0x9E | 0x00 | 00000000
 _APDS9960_CONFIG3      0x9F | 0x00 | 00000000
 _APDS9960_GPENTH       0xA0 | 0x32 | 00110010
 _APDS9960_GEXTH        0xA1 | 0x00 | 00000000
 _APDS9960_GCONF1       0xA2 | 0x40 | 01000000
 _APDS9960_GCONF2       0xA3 | 0x40 | 01000000
 _APDS9960_GOFFSET_U    0xA4 | 0x00 | 00000000
 _APDS9960_GOFFSET_D    0xA5 | 0x00 | 00000000
 _APDS9960_GPULSE       0xA6 | 0x83 | 10000011
 _APDS9960_GOFFSET_L    0xA7 | 0x00 | 00000000
 _APDS9960_GOFFSET_R    0xA9 | 0x00 | 00000000
 _APDS9960_GCONF3       0xAA | 0x00 | 00000000
 _APDS9960_GCONF4       0xAB | 0x00 | 00000000
 _APDS9960_GFLVL        0xAE | 0x00 | 00000000
 _APDS9960_GSTATUS      0xAF | 0x00 | 00000000
 ```

So what's different?

* `PON` bit (`ENABLE[0]`) is asserted
* `ATIME` is set to `0x01` instead of `0xFF`.
  * **Color Engine**: This extends ADC integration to `708.9 ms`, one value below its max of `712 ms`, 255 times the power-on default of `2.78 ms`.
* `AGAIN` (`CONTROL[1:0]`) is set to `0x01` instead of `0x00`
  * **Color Engine**: This sets the color/light gain to 4x (`b11`) instead of the default of 1x (`b00`)
* `GPENTH` is set to `0x32` instead of `0x0`
  * **Gesture Engine**: This prevents the gesture engine from starting unless the Proximity Engine's `PDATA` value is greater than `GPENTH`
* `GFIFOTH` (`GCONF1[7:6]`) is set to `0x01` instead of `0x00`
  * **Gesture Engine**: This delays the trigger of an internal gesture interrupt until 4 (instead of the default of 1) gesture data sets have been added to FIFO
* `GGAIN` (`GCONF[6:5]`) is set to `0x10` instead of `0x00`
  * **Gesture Engine**: This sets the gain multiplier for photosensors during gesture cycles to 4x instead of the default of 1x
* `GPLEN` (`GPULSE[7:6]`) is set to `0x10` instead of the default of `0x01`
  * **Gesture Engine**: This sets the LED pulse length during gesture operations to `16 us` instead of the default of `8 us`
* `GPULSE` (`GPULSE[5:0]`) is set to 3 (`0x000011`) instead of the default of 0 (`0x000000`)
  * **Gesture Engine**: This sets the pulse count for gesture operations to `4` instead of the default of `1`.

No surprises here. All of this is expected based on the current driver code.

##### Config register states after driver init, after enabling prox/gesture engines, but before looping

So, as another early step to make sure we're on solid ground, do our config regs change after init but before we hit our error state?

This should be simple, since we only actually told the driver to enable prox/gesture.

```
 _APDS9960_ENABLE       0x80 | 0x45 | 01000101
 _APDS9960_ATIME        0x81 | 0x01 | 00000001
 _APDS9960_WTIME        0x83 | 0xFF | 11111111
 _APDS9960_AILTIL       0x84 | 0x09 | 00001001
 _APDS9960_AILTH        0x85 | 0x45 | 01000101
 _APDS9960_AIHTL        0x86 | 0x00 | 00000000
 _APDS9960_AIHTH        0x87 | 0x00 | 00000000
 _APDS9960_PILT         0x89 | 0x00 | 00000000
 _APDS9960_PIHT         0x8B | 0x00 | 00000000
 _APDS9960_PERS         0x8C | 0x00 | 00000000
 _APDS9960_CONFIG1      0x8D | 0x60 | 01100000
 _APDS9960_PPULSE       0x8E | 0x40 | 01000000
 _APDS9960_CONTROL      0x8F | 0x01 | 00000001
 _APDS9960_CONFIG2      0x90 | 0x01 | 00000001
 _APDS9960_STATUS       0x93 | 0x22 | 00100010
 _APDS9960_POFFSET_UR   0x9D | 0x00 | 00000000
 _APDS9960_POFFSET_DL   0x9E | 0x00 | 00000000
 _APDS9960_CONFIG3      0x9F | 0x00 | 00000000
 _APDS9960_GPENTH       0xA0 | 0x32 | 00110010
 _APDS9960_GEXTH        0xA1 | 0x00 | 00000000
 _APDS9960_GCONF1       0xA2 | 0x40 | 01000000
 _APDS9960_GCONF2       0xA3 | 0x40 | 01000000
 _APDS9960_GOFFSET_U    0xA4 | 0x00 | 00000000
 _APDS9960_GOFFSET_D    0xA5 | 0x00 | 00000000
 _APDS9960_GPULSE       0xA6 | 0x83 | 10000011
 _APDS9960_GOFFSET_L    0xA7 | 0x00 | 00000000
 _APDS9960_GOFFSET_R    0xA9 | 0x00 | 00000000
 _APDS9960_GCONF3       0xAA | 0x00 | 00000000
 _APDS9960_GCONF4       0xAB | 0x00 | 00000000
 _APDS9960_GFLVL        0xAE | 0x00 | 00000000
 _APDS9960_GSTATUS      0xAF | 0x00 | 00000000
 ```

* `PEN` (`ENABLE[2]`) is asserted
* `GEN` (`ENABLE[6]`) is asserted
* `PINT` (`STATUS[5]`) is asserted
* `PVALID` (`STATUS[1]`) is asserted

The changes here all make sense.

As expected, the proximity engine is looping and generating valid data. And since our internal thresholds are all `0` our first cycle of the proximity engine should have triggered an internal interrupt.

As a side note, because we haven't enabled any external interrupts, the interrupt pin is still un-asserted, which we also expect.

##### Config register states during main loop, before error state

After 11 loops with proximity remaining at `0` a config dump was taken that should help us make sure our configs aren't getting changed during 'normal' operation.

```
 _APDS9960_ENABLE       0x80 | 0x45 | 01000101
 _APDS9960_ATIME        0x81 | 0x01 | 00000001
 _APDS9960_WTIME        0x83 | 0xFF | 11111111
 _APDS9960_AILTIL       0x84 | 0x09 | 00001001
 _APDS9960_AILTH        0x85 | 0x45 | 01000101
 _APDS9960_AIHTL        0x86 | 0x00 | 00000000
 _APDS9960_AIHTH        0x87 | 0x00 | 00000000
 _APDS9960_PILT         0x89 | 0x00 | 00000000
 _APDS9960_PIHT         0x8B | 0x00 | 00000000
 _APDS9960_PERS         0x8C | 0x00 | 00000000
 _APDS9960_CONFIG1      0x8D | 0x60 | 01100000
 _APDS9960_PPULSE       0x8E | 0x40 | 01000000
 _APDS9960_CONTROL      0x8F | 0x01 | 00000001
 _APDS9960_CONFIG2      0x90 | 0x01 | 00000001
 _APDS9960_STATUS       0x93 | 0x22 | 00100010
 _APDS9960_POFFSET_UR   0x9D | 0x00 | 00000000
 _APDS9960_POFFSET_DL   0x9E | 0x00 | 00000000
 _APDS9960_CONFIG3      0x9F | 0x00 | 00000000
 _APDS9960_GPENTH       0xA0 | 0x32 | 00110010
 _APDS9960_GEXTH        0xA1 | 0x00 | 00000000
 _APDS9960_GCONF1       0xA2 | 0x40 | 01000000
 _APDS9960_GCONF2       0xA3 | 0x40 | 01000000
 _APDS9960_GOFFSET_U    0xA4 | 0x00 | 00000000
 _APDS9960_GOFFSET_D    0xA5 | 0x00 | 00000000
 _APDS9960_GPULSE       0xA6 | 0x83 | 10000011
 _APDS9960_GOFFSET_L    0xA7 | 0x00 | 00000000
 _APDS9960_GOFFSET_R    0xA9 | 0x00 | 00000000
 _APDS9960_GCONF3       0xAA | 0x00 | 00000000
 _APDS9960_GCONF4       0xAB | 0x00 | 00000000
 _APDS9960_GFLVL        0xAE | 0x00 | 00000000
 _APDS9960_GSTATUS      0xAF | 0x00 | 00000000
 ```

 And, indeed, nothing's changed.

##### Config register states during main loop, after error state

Reg dump after hitting this state (with normal driver init).

```
 _APDS9960_ENABLE       0x80 | 0x45 | 01000101
 _APDS9960_ATIME        0x81 | 0x01 | 00000001
 _APDS9960_WTIME        0x83 | 0xFF | 11111111
 _APDS9960_AILTIL       0x84 | 0x09 | 00001001
 _APDS9960_AILTH        0x85 | 0x45 | 01000101
 _APDS9960_AIHTL        0x86 | 0x00 | 00000000
 _APDS9960_AIHTH        0x87 | 0x00 | 00000000
 _APDS9960_PILT         0x89 | 0x00 | 00000000
 _APDS9960_PIHT         0x8B | 0x00 | 00000000
 _APDS9960_PERS         0x8C | 0x00 | 00000000
 _APDS9960_CONFIG1      0x8D | 0x60 | 01100000
 _APDS9960_PPULSE       0x8E | 0x40 | 01000000
 _APDS9960_CONTROL      0x8F | 0x01 | 00000001
 _APDS9960_CONFIG2      0x90 | 0x01 | 00000001
 _APDS9960_STATUS       0x93 | 0x24 | 00100100
 _APDS9960_POFFSET_UR   0x9D | 0x00 | 00000000
 _APDS9960_POFFSET_DL   0x9E | 0x00 | 00000000
 _APDS9960_CONFIG3      0x9F | 0x00 | 00000000
 _APDS9960_GPENTH       0xA0 | 0x32 | 00110010
 _APDS9960_GEXTH        0xA1 | 0x00 | 00000000
 _APDS9960_GCONF1       0xA2 | 0x40 | 01000000
 _APDS9960_GCONF2       0xA3 | 0x40 | 01000000
 _APDS9960_GOFFSET_U    0xA4 | 0x00 | 00000000
 _APDS9960_GOFFSET_D    0xA5 | 0x00 | 00000000
 _APDS9960_GPULSE       0xA6 | 0x83 | 10000011
 _APDS9960_GOFFSET_L    0xA7 | 0x00 | 00000000
 _APDS9960_GOFFSET_R    0xA9 | 0x00 | 00000000
 _APDS9960_GCONF3       0xAA | 0x00 | 00000000
 _APDS9960_GCONF4       0xAB | 0x01 | 00000001
 _APDS9960_GFLVL        0xAE | 0x20 | 00100000
 _APDS9960_GSTATUS      0xAF | 0x03 | 00000011
```

Here we don't see any actual config changes but we do see some critical looking status changes.

* `GFLVL` is `0x20` instead of `0x0`
  * We should expect this, since the gesture FIFOs should be full if the engine is enabled (`GEN` asserted), the entry proximity threshold (`GPENTH`) has been met/exceeded, and gesture data has been successfully captured.
* `GFOV` (`GSTATUS[1]`) is asserted
  * This is expected too, since we'd expect gesture FIFOs to overflow before we get a change to read them
* `GVALID` (`GSTATUS[0]`) is asserted
  * The gesture engine is producing valid data, which is expected as well
* `GINT` (`STATUS[2]`) is asserted
  * Our internal gesture interrupt has been triggered, which will help us understand our place in the state machine
* `PVALID` (`STATUS[1]`) has de-asserted
  * This makes sense if we haven't run through the prox engine since our last proximity data read, which is a pretty important clue I think
* `GMODE` (`GCONF4[0]`) is asserted
  * This is pretty important, actually

Based on this info it looks like we're stuck in the Gesture Engine state machine indefinitely, which explains why our prox data hasn't updated.

But where the heck are we? And why?

#### Gesture Engine Perma-loop

To explain this, we'll need to dig into the basic mechanics of the gesture engine.

##### Gesture Engine State Machine Analysis

Within the broader device-wide state machine, Gesture Engine entry happens after Proximity Engine check (and entry/exit if enabled). Entry into the Gesture Engine only happens if we've got the Proximity Engine enabled (`PEN` asserted), the Gesture Engine enabled (`GEN` asserted), and `GMODE` set to 1.

`GMODE` is important here though. It gets asserted after a successful run of the Proximity Engine just before it exists and hands off to check whether to execute the Gesture Engine. But it can also get asserted via I2C by asserting the `GCONFIG4[0]` bit in the `GCONFIG` register. Once a gesture run is complete, with valid enough runs with valid data to reach the gesture persistence value `GEXTH`, `GMODE` gets flipped to `0`.

There are four main elements of the gesture engine. Between these are a few other logic checks, but for the most part, these are the big blocks.

1. Data Acquisition
2. FIFO/Interrupt Handling
3. Loop Control
4. Between-Gesture-Cycles Wait Timer

Although there's a flowchart in the datasheet, understanding the Gesture Engine's quirks is a lot easier (for Pythonic folks, at least) with some pseudocode which is detailed in an earlier section of these notes.

There's a lot going on in there, with a lot of state changes. But with this mapped out we should have a better chance of figuring this out.

##### You may tell yourself, this is not my beautiful `GMODE`! How did I get here?! What have I done?!

We know, based on the context from all those register reads, that we're stuck in the Gesture Engine. But why?

From the flowchart/pseudocode we can see that we've got two ways that we can decide to drop out of the loop.

1. Internal persistence >= `GEXPERS`
2. Host uses I2C write to de-assert `GMODE`

We're neither modifying `GEXPERS` or de-asserting `GMODE`. So of course we're never exiting.

#### Testing: Manually de-assert `GMODE` during user code loop

To test this, we can de-assert `GMODE` on a button press at the top of our main loop:

```py 
    new_presses = get_presses(buttons)

    if new_presses[0]:
        apds._gesture_mode = False
        print("APDS| GMODE = False")
```

Sure enough, that breaks us out of the infinite loop.

```
APDS | prox     0 | gesture  0 | enable_gesture: 1, gesture_valid: 0, gmode: 0
APDS | prox     2 | gesture  0 | enable_gesture: 1, gesture_valid: 0, gmode: 0
APDS | prox     8 | gesture  0 | enable_gesture: 1, gesture_valid: 0, gmode: 0
APDS | prox    10 | gesture  0 | enable_gesture: 1, gesture_valid: 0, gmode: 0
APDS | prox    34 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    44 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    45 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    51 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    51 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    51 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    51 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | prox    51 | gesture  0 | enable_gesture: 1, gesture_valid: 1, gmode: 1
APDS | GMODE = False
APDS | prox     0 | gesture  0 | enable_gesture: 1, gesture_valid: 0, gmode: 0
APDS | prox     0 | gesture  0 | enable_gesture: 1, gesture_valid: 0, gmode: 0
```

#### Fix Options: Get me out of this crazy loop!

So, knowing this, we just need to make sure we exit the gesture engine eventually, assuming we want to use other functions.

The sensor provides us with some useful registers to poke to help with this. But it'll take a bit of testing to find the best way forward.

## Color/Ambient Light Operation

TODO

## Notes

* Gesture cannot operate without proximity enabled
* `WTIME`/`WLONG` & `WEN` should be configured before `AEN` or `PEN` are asserted

### Driver Size 

|  | post-import | post-instantiate | `mpy` size |
|---|---|---|---|
| bundle `20211114` mpy | 8,416 | 144 | 3,839 |
| [previous mpy](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/blob/70f54b0a1075d4f14a1ae8e00ebae74b7b962cb7/adafruit_apds9960/apds9960.py) | 8,544 | 160 | 3,948
| [current mpy](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/blob/c55da0dee66302d2fa8ed31623d047c307f409b2/adafruit_apds9960/apds9960.py) | 8,464 | 144 | 3,794
| constant_fix mpy | 7,856 | 144 | 3,364 |
| --- | | | | 
| prox edit2 | 15,920 | 176 | 7,046 |

## Potential To Do Items

* Write class method to handle proper wait time (`WTIME`/`WLONG`) setting