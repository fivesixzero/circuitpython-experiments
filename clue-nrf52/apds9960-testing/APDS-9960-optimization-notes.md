# APDS-9960 Memory Optimization

A fully-functional APDS-9960 driver can become pretty darn huge, making it unlikely to fit into memory on more constrained devices such as the SAMD21 family. That's not cool! So lets see how small we can make this thing, yeah?

## Optimization Decisions

Before launching into this, we've got a few decisions to make that'll guide our process

### User Choice at Import/Runtime: `basic` vs `advanced`

To start, we'll use the example set by the [`BME280` CircuitPython library](https://github.com/adafruit/Adafruit_CircuitPython_BME280) to split the driver into  highly-optimized `basic` and full-featured `advanced` classes. This will give users the ability to choose which to import at runtime.

In this case though we'll maintain the current interface contract by optimizing the current driver class to be our `basic` one. Then we'll create a second class to be our `advanced` one.

### Post-optimization Constraints/Considerations

#### Optimization Results

| Commit | `mpy` size | `mpy` delta | mem `SAMD21` | mem delta | mem `RP2040` | mem delta |  Note |
|------|-----------|-------|----|---|---|---|---|
| [`2c5ee6a`](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/blob/c55da0dee66302d2fa8ed31623d047c307f409b2/adafruit_apds9960/apds9960.py) | `3,839` | baseline  | `8,944` | baseline | `9,904` | baseline | Current bundle, baseline |  |
| [`2c5ee6a`](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/blob/2c5ee6a3a6453bac2217f3db9a70bb83f022d961/adafruit_apds9960/apds9960.py) | `3,854` | `-15` | `8,960` | `-16` | `9,872` | `-32` |  `v2.2.8`, latest `mpy-cross` |
| [`064fd99`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/064fd99f6006ce146eefa74eff5944af1d716b2e/adafruit_apds9960/apds9960.py) | `6,831` | `+2,992` | OOM :( | OOM :( | `15,296` | `+5,392` | First refactor, #38 |
| [`424e72c`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/424e72cd30ae3279f82480ca599626f79fa7995e/adafruit_apds9960/apds9960.py) | `3,400` | `-439` | `8,480` | `-464` | `12,480` | `+2,576` | First optimization pass, #37 |
| [`30eeadd`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/30eeadd62628d9747e34c4623bfa29a36bd8b7da/adafruit_apds9960/apds9960.py) | `4,709` | `+870` | `6,944` | `-2,000` | `6,880` | `-3,024` | Removed `register` use |
| [`9e335a0`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/9e335a00c8ae3f8ad74990ccff6798c54e003784/adafruit_apds9960/apds9960.py) | `3,634` | `-205` | `6,000` | `-2,944` | `5,488` | `-4,416` | Removed non-essential methods/props |
| [`999945e`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/999945eaddff6cc7e220ceb26a5ef244288be0f7/adafruit_apds9960/apds9960.py) | `3,528` | `-311` | `5,792` | `-3,152` | `5,424` | `-4,480` | Refactored/tested init reset/defaults |
| [`faa7969`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/faa7969c4fd63ce818b51409e4834f95230a3ce7/adafruit_apds9960/apds9960.py) | `3,798` | `-41` | `5,568` | `-3,376` | `5,456` | `-4,448` `gesture()` rewrite |
| [`c02b1df`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/c02b1df8730b88ac06e39ee75c42ca7d6bccb267/adafruit_apds9960/apds9960.py) | `3,988` | `+149` | `5,872` | `-3,072` | `5,776` | `-4,128` | Color engine fixes |
| [`4c97c60`](https://github.com/fivesixzero/Adafruit_CircuitPython_APDS9960/blob/4c97c604b565b61333d3ff37d4f815bc8d7087e7/adafruit_apds9960/apds9960.py) | `4,053` | `+214` | `5,936` | `-3,008` | `5,840` | `-4,064` | Major docstring and docs/examples updates |

##### File Size Optimization Notes

Ideally compiled `mpy` file size should be as small as possible for both of these, using the current driver code (`2.2.8`) as a benchmark of sorts.

The main impact of this is use on boards with smaller storage, with the `Proximity Trinkey` being the most constrained case. In that case the APDS driver actually gets frozen into the firmware, so any increase in file size could destabilize the CircuitPython build process as a whole. So lets try to not do that.

The compiled file from the bundle is pretty darn small. Aside from somewhat wonky gesture detection code I think we can do a bit better than that. Unfortunately my first refactor resulted in a massive increase here, so this can be useful as "high water mark" for our `advanced` driver optimizations.

##### Memory Footprint Optimization Notes

The memory footprint is really important too, especially on constrained platforms like SAMD21. Its also critical for cases where proximity, gesture, or color/light aren't the only thing a user wants out of their device. So we should make this as small as possible too.

Memory usage varies quite a bit by platform, depending on the lower-level optimizations going on with `board`, `busio`, etc. For instance, the APDS driver import occupies about 4-5k more memory on a `QTPy RP2040` than on a `Proximity Trinkey`.

So for this testing we'll rely primarily on the `SAMD21E18` on a `Proximity Trinkey` running a custom `7.1.0-beta0` build configured with no frozen-in libraries.

Since import just isn't possible when the library gets huge on SAMD21 I'll use a `QTPy 2040` as a second target platform.


##### Memory Footprint Testing Methodology

In the example command lines I'm running on a Linux system with `mpy-cross` built from `7.1.0-beta.0` source in the path. 

`CIRCUITPY` is the `QTPy RP2040` and `CIRCUITPY1` is the `Proximity Trinkey`.

Both are set to auto-restart on filesystem changes, so their serial consoles will output the new memory usage numbers immediately after the new `mpy` files are built.

1. Check out version/tag (or edit file with prospective changes)
2. Build with `mpy-cross` directly to device
    * `mpy-cross -o /media/me/CIRCUITPY/lib/adafruit_apds9960/apds9960.mpy ./adafruit_apds9960/apds9960.py`
    * `mpy-cross -o /media/me/CIRCUITPY1/lib/adafruit_apds9960/apds9960.mpy ./adafruit_apds9960/apds9960.py`
3. Get post-compile library file size
    * `ls -al /media/me/CIRCUITPY/lib/adafruit_apds9960/`   
    * `ls -al /media/me/CIRCUITPY1/lib/adafruit_apds9960/`   
4. Observe memory usage in serial output, record results in tables above

##### Memory Footprint Test Script

Memory footprint testing is a bit frustrating due to the non-deterministic results that can come from minor or seemingly insignificant changes. Even changing the order of imports or where a global string object is declared can cause all kinds of weird changes to outcomes.

With that in mind, and after a lot of trial/error, this was the script that ended up producing the closest thing to deterministic results.

```py
# Tiny Size Test

# Free 0: Pre-startup imports
import gc
from array import array
# Pre-allocate arrays/vars
mem_frees = array('i', [0, 0, 0, 0])
mem_usages = array('i', [0, 0, 0])
gest = 0
scl1 = 'SCL1'
gc.collect()

# Free 1: Startup imports
import board

if scl1 in dir(board):
    import busio
    i2c = busio.I2C(board.SCL1, board.SDA1)
else:
    i2c = board.I2C()

str_apds_used = "USAGE: Driver Only  | {}"
str_apds_inst_used = "USAGE: Instance     | {}"
str_apds_gest_used = "USAGE: Post-gesture | {}"

str_spacer = ""
gc.collect()
mem_frees[0] = gc.mem_free()

from adafruit_apds9960.apds9960 import APDS9960
gc.collect()
mem_frees[1] = gc.mem_free()
mem_usages[0] = mem_frees[0] - mem_frees[1]

apds = APDS9960(i2c)
gc.collect()
mem_frees[2] = gc.mem_free()
mem_usages[1] = mem_frees[1] - mem_frees[2]

apds.enable_proximity = True
apds.enable_gesture = True
gest = apds.gesture()
gc.collect()
mem_frees[3] = gc.mem_free()
mem_usages[2] = mem_frees[2] - mem_frees[3]

print(str_spacer)

print(str_apds_used.format(mem_usages[0]))
print(str_apds_inst_used.format(mem_usages[1]))
print(str_apds_gest_used.format(mem_usages[2]))
```

## Optimization Ideas

The first things that came to mind fall into a few major chunks, so we'll test them out one at a time.

* Replace `adafruit_register` usage with internal methods and constants
* Remove "non-basic" functions and associated things
* Replace `__init__` default-setting with hard-coded constants via `write8`
* Refactor `gesture()` to be as simple as possible while still returning useful data

### Remove usage of `adafruit_register`

_TL;DR: Big tradeoff. Memory use went down by ~2-3k (!) but `mpy` file size increased by about 1k._

I love `adafruit_register`! But using it does appear to add some memory overhead versus relying on constants and nigh-unreadable bit-shifts.

This was tested by adding four functions for RW of bits/bytes within registers, adding constants for bit position and bit mask of each relevant item, and replacing the `RWBit`/`RWBits` assignments with properties using the constants and new functions to access the required register bits.

#### Removal of `adafruit_register` Methodology

Functions here are basically simplified subsets of functionality in `adafruit_register`.

```py
    def _get_bit(self, register: int, bitmask: int) -> int:
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        return (buf[1] & bitmask)

    def _set_bit(self, register: int, bitmask: int, value: bool) -> None:
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        if value:
            buf[1] |= bitmask
        else:
            buf[1] &= bitmask
        with self.i2c_device as i2c:
            i2c.write(buf, end=1)

    def _get_bits(self, register: int, bit_position: int, bit_mask: int) -> int:
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        return (buf[1] & bit_mask) >> bit_position

    def _set_bits(self, register: int, bit_position: int, bit_mask: int, value: int) -> None:
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        buf[1] = (buf[1] & ~bit_mask) | (value << bit_position)
        with self.i2c_device as i2c:
            i2c.write(buf, end=1)
```

Constants:

```py
_BIT_MASK_ENABLE_EN = const(0x01)
_BIT_MASK_ENABLE_PROX = const(0x04)
_BIT_MASK_ENABLE_PROX_INT = const(0x10)
_BIT_MASK_ENABLE_GESTURE = const(0x20)
_BIT_MASK_ENABLE_COLOR = const(0x02)

_BIT_MASK_GSTATUS_GVALID = const(0x01)

_BIT_MASK_GCONF4_GMODE = const(0x01)

_BIT_POSITON_PERS_PPERS = const(4)
_BIT_MASK_PERS_PPERS = const(0xF0)

_BIT_POSITON_GCONF1_GFIFOTH = const(6)
_BIT_MASK_GCONF1_GFIFOTH = const(0xC0)

_BIT_POSITON_GCONF2_GGAIN = const(5)
_BIT_MASK_GCONF2_GGAIN = const(0x60)

_BIT_POSITON_CONTROL_AGAIN = const(0)
_BIT_MASK_CONTROL_AGAIN = const(0x03)
```

Property example:

```py
    # _gesture_enable = RWBit(_APDS9960_ENABLE, 6)

    @property
    def _gesture_enable(self) -> bool:
        return self._get_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_GESTURE)

    @_gesture_enable.setter
    def _gesture_enable(self, value: bool) -> None:
        self._set_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_GESTURE, value)
```

These were replaced for 7 bit accessors and 4 bits accessors.

### Removal of Non-Basic Functions

_TL;DR: This was useful, reducing file size substantially (~1k) while also reducing memory usage quite a bit (~1k) too!_

This one's delicate, since defining what's "basic" and what isn't is pretty subjective.

#### Non-Basic Functions Methodology

Here's my initial take on what definitely needs to be present in a "basic" driver:

1. Enable/Disable for device and core functions
    * Device Enable
    * Proximity Enable
    * Gesture Enable
    * Color/Light Enable
2. Data Acquisition
    * Proximity Counts
    * Gesture (very simplified)
    * Color/Light Counts
3. Basic Tuning
    * Proximity Interrupt Enable
    * Proximity Interrupt Thresholds
    * Proximity Interrupt Clear

This means removing the following properties/functions from the current driver:

1. Tuning
    * `color_gain` (defaults will handle this)
    * `gesture_dimensions` (actually part of masking options)
    * `gesture_proximity_threshold` (defaults will handle this)
    * `integration_time` (actually color integration time)
2. Helpers
    * `rotated_gesture()` (can be done easily within `gesture()`)

It also will involve the removal of the `enable_gesture` wrapper around `_gesture_enable` since we really don't need to tinker with `GMODE` anymore, assuming that both the `gesture()` function and init defaults get improved.

Our defaults can handle all of these things, so we'll be fine there.

### Use Hard-Coded Constants via `_write8` for `__init__()` Defaults 

This is also pretty delicate, since we don't want to remove *all* of the important user tuning, but we do want to make sure that the sensor gets set up to be useful in as many use case as possible.

While we're here, we'll be implementing new defaults based on recent testing as well as a implementing a more comprehensive 'reset' of the sensor's config registers on it. And both of those on-init operations can be enabled/disabled with a pair of new `kwarg`s

#### Defaults and Reset Change Methodology

Here's the main change - a new "reset" process during init as well as new defaults.

```py
if reset:
    self._write8(_APDS9960_ENABLE, 0) # Disable sensor and all functions/interrupts

    # Reset basic config registers to power-on defaults
    self._write8(_APDS9960_ATIME, 255)
    self._write8(_APDS9960_PIHT, 0)
    self._write8(_APDS9960_PERS, 0)
    self._write8(_APDS9960_CONTROL, 1)
    self._write8(_APDS9960_GPENTH, 0)
    self._write8(_APDS9960_GEXTH, 0)
    self._write8(_APDS9960_GCONF1, 0)
    self._write8(_APDS9960_GCONF2, 0)
    self._write8(_APDS9960_GPULSE, 0)

    # Clear all interrupts
    self.clear_interrupt()

    # Enable sensor and wait 10ms for the power on delay to finish
    self.enable = True
    time.sleep(0.010)

if set_defaults:
    self.proximity_interrupt_threshold = (0, 5, 4) # Trigger PINT at >= 5, PPERS: 4 cycles
    self._write8(_APDS9960_GPENTH, 0x05) # Enter gesture engine at >= 5 counts
    self._write8(_APDS9960_GEXTH, 0x1E) # Exit gesture engine if all counts drop below 30
    self._write8(_APDS9960_GCONF1, 0x82) # GEXPERS: 1 (4 cycles), GFIFOTH: 2 (8 datasets)
    self._write8(_APDS9960_GCONF2, 0x21) # GWTIME: 1 (2.8ms), GLDRIVE: 100mA, GGAIN: 1 (2x) 
    self._write8(_APDS9960_GPULSE, 0x85) # GPULSE: 5 (6 pulses), GPLEN: 2 (16 us)
    self._write8(_APDS9960_ATIME, 0xB6) # ATIME: 182 (200ms color integration time)
    self._write8(_APDS9960_CONTROL, 0x01) # AGAIN: 1 (4x color gain), PGAIN: 0 (1x)
```

### Refactor `gesture()` for Simplicity

_TL;DR: In terms of file size and memory footprint this ended up being a bit of a wash, which itself is quite a victory compared to the comparatively massive "full-featured driver" in the first refactor attempt_

The current `gesture()` code could use some love, especially in light of the research documented in this repo. Lets streamline it.

#### Simple `gesture()` Refactor Methodology

There are tons of ways for us to handle gesture recognition, given the data this sensor can flood us with, but I think we can learn a lot from the Arduino driver here.

First off, we only need to gather the first and last frames we actually care about for later processing/analysis. We can also make some improvements to see if we actually need to pull data as well.

Second, we just need to look at the "ratio" between those first and last frames to determine what our gesture actually was.

Here's an overview of how this can be done efficiently.

Pulling In Data:

1. See if we actually have enough gesture data waiting for us
2. If we do, have we overflowed? If so, we're too late, but we can hang out for a bit before pulling
3. Start pulling in data, one 128-byte stream at a time
4. Save our first relevant looking dataset for analysis
5. Keep pulling in new streams of data until our FIFOs are totally empty, for real
6. Save our last relevant looking dataset for analysis 

Analyzing Data:

1. Determine UD/LR ratios of our first/last datasets and the deltas between those
2. Take a first guess at our gesture based on those UD/LR ratio deltas
3. Use those guesses and the deltas to arrive at a much more plausible answer
4. Rotate our answer based on `self._rotation` before we return it

Whew. A lot going on here, but `gesture()` should return more solid data after this refactor. And it might end up using less memory as well.

The whole thing, comments included, ended up fitting into around 150 lines of code, looking a bit like this:

```py
    def gesture(self) -> int:  # pylint: disable-msg=too-many-branches
        """Returns gesture code if detected.
        0 if no gesture detected
        1 if up,
        2 if down,
        3 if left,
        4 if right
        """
        # If FIFOs have overflowed we're already way too late, so clear those FIFOs and wait
        if self._get_bit(_APDS9960_GSTATUS, _BIT_MASK_GSTATUS_GFOV):
            self._set_bit(_APDS9960_GCONF4, _BIT_MASK_GCONF4_GFIFO_CLR, True)
            wait_cycles = 0
            # Don't wait forever though, just enough to see if a gesture is happening
            while (
                not self._get_bit(_APDS9960_STATUS, _BIT_MASK_STATUS_GINT)
                and wait_cycles <= 30
            ):
                time.sleep(0.003)
                wait_cycles += 1

        # Only start retrieval if there are datasets to retrieve
        frame = []
        datasets_available = self._read8(_APDS9960_GFLVL)
        if (
            self._get_bit(_APDS9960_STATUS, _BIT_MASK_STATUS_GINT)
            and datasets_available > 0
        ):
            if not self.buf129:
                self.buf129 = bytearray(129)

            buffer = self.buf129
            buffer[0] = _APDS9960_GFIFO_U

            if not self.buf4:
                self.buf4 = bytearray(4)

            buffer_dataset = self.buf4

            # Retrieve new data until our FIFOs are truly empty
            while True:
                dataset_count = self._read8(_APDS9960_GFLVL)
                if dataset_count is 0:
                    break

                with self.i2c_device as i2c:
                    i2c.write_then_readinto(
                        buffer,
                        buffer,
                        out_end=1,
                        in_start=1,
                        in_end=min(129, 1 + (dataset_count * 4)),
                    )

                # Unpack data stream into more usable U/D/L/R datasets for analysis
                idx = 0
                for i in range(dataset_count):
                    rec = i + 1
                    idx = 1 + ((rec - 1) * 4)

                    buffer_dataset[0] = buffer[idx]
                    buffer_dataset[1] = buffer[idx + 1]
                    buffer_dataset[2] = buffer[idx + 2]
                    buffer_dataset[3] = buffer[idx + 3]

                    # Drop fully-saturated and fully-zero to conserve memory
                    # Filter to remove useless (saturated, empty, low-count) datasets
                    if (
                        (not all(val == 255 for val in buffer_dataset))
                        and (not all(val == 0 for val in buffer_dataset))
                        and (all(val >= 30 for val in buffer_dataset))
                    ):
                        if len(frame) < 2:
                            frame.append(tuple(buffer_dataset))
                        else:
                            frame[1] = tuple(buffer_dataset)

                # Wait a very short time to see if new FIFO data has arrived before we drop out
                time.sleep(0.03)

        # If we only got one useful frame, that's not enough to make a solid guess
        if len(frame) < 2:
            return 0

        # We should have a dataframe with two tuples now, a "first" and "last" entry.
        # Time to process the dataframe!

        # Determine our up/down and left/right ratios along with our first/last deltas
        f_r_ud = ((frame[0][0] - frame[0][1]) * 100) // (frame[0][0] + frame[0][1])
        f_r_lr = ((frame[0][2] - frame[0][3]) * 100) // (frame[0][2] + frame[0][3])

        l_r_ud = ((frame[1][0] - frame[1][1]) * 100) // (frame[1][0] + frame[1][1])
        l_r_lr = ((frame[1][2] - frame[1][3]) * 100) // (frame[1][2] + frame[1][3])

        delta_ud = l_r_ud - f_r_ud
        delta_lr = l_r_lr - f_r_lr

        # Make our first guess at what gesture we saw, if any
        state_ud = 0
        state_lr = 0

        if delta_ud >= 30:
            state_ud = 1
        elif delta_ud <= -30:
            state_ud = -1

        if delta_lr >= 30:
            state_lr = 1
        elif delta_lr <= -30:
            state_lr = -1

        # Make our final decision based on our first guess and, if required, the delta data
        gesture_found = 0

        # Easy cases
        if state_ud == -1 and state_lr == 0:
            gesture_found = 1
        elif state_ud == 1 and state_lr == 0:
            gesture_found = 2
        elif state_ud == 0 and state_lr == -1:
            gesture_found = 3
        elif state_ud == 0 and state_lr == 1:
            gesture_found = 4

        # Not so easy cases
        if gesture_found == 0:
            if state_ud == -1 and state_lr == 1:
                if abs(delta_ud) > abs(delta_lr):
                    gesture_found = 1
                else:
                    gesture_found = 4
            elif state_ud == 1 and state_lr == -1:
                if abs(delta_ud) > abs(delta_lr):
                    gesture_found = 2
                else:
                    gesture_found = 3
            elif state_ud == -1 and state_lr == -1:
                if abs(delta_ud) > abs(delta_lr):
                    gesture_found = 1
                else:
                    gesture_found = 3
            elif state_ud == 1 and state_lr == 1:
                if abs(delta_ud) > abs(delta_lr):
                    gesture_found = 2
                else:
                    gesture_found = 3

        if gesture_found != 0:
            if self._rotation != 0:
                # If we need to rotate our gesture, lets do that before returning
                dir_lookup = [1, 4, 2, 3]
                idx = (dir_lookup.index(gesture_found) + self._rotation // 90) % 4
                return dir_lookup[idx]
            else:
                return gesture_found
        else:
            return 0
```

The biggest change from the original refactor is a streamlining of all of the code into a single function rather than having helper static methods to assist with various chunks of work. In exchange for the flagrant violation of good object-oriented coding norms we get a huge chunk of memory back. I'm okay with that.

## Conclusions

Taking a methodical approach to optimizing this code seems to have paid off! We've got a functional driver with improved gesture recognition in a smaller `mpy` file with a much lower memory footprint.

With this optimization done, all that's left to do is to update the examples and doc then set up a proper PR. Whew.

## Misc Notes

Cost, in bytes of filesize

## EOF