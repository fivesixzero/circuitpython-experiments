# APDS-9960 Driver Dev Notes

These notes were generated during iterative development/testing of driver changes/improvements.

## Initial State and Testing Platforms

### Proximity Trinkey

#### Test 1: Baselines

* CircuitPython Version: `7.1.0-beta1`, direct download
* Driver Version: `v2.2.7`
    * `FROZEN` from `7.1.0-beta1`, at [commit `ee441d3`](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/commit/ee411d34dfa2fb70a35aa99945eca77f16456619)


| | | |
|---|---|---|
| Driver file size | `4,684` | Frozen and bundled, but this is size reduction in firmware if removed during compilation |
| Memory used by import | `5,216` |
| Memory used by instantiate | `160`
| Memory used by `gesture()` | `160`

##### Test 1: Proximity Read Only

This should be a simple control test, since reading proximity doesn't require any internal buffer allocation or expansion.

|  | `mem_free` | mem used
|---|---|---|
| only `gc` imported | `18,608` |
| `import time`<br>`import board` | `18,592` | `16` |
| `i2c = board.I2C()` | `18,592` | `0` | 
| Internal driver imports<br>`RWBits`,`RWBit`,`I2CDevice` | `15,856` | `2,736`
| Driver import<br>`APDS9960` | `13,344` | `2,512`
| _driver plus imports_ | | `[5,248]`|
| Device instantiate<br>`apds = APDS9960(i2c)` | `13,184` | `160`
| _loop start_ | | |
| `print(apds.proximity)` | `13,184` | `0`
| _no change in subsequent loops_

Raw output:

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
18608
18592
18592
15856
13344
13184
0
13184
0
13184
```

##### Test 1: Gesture Read Only

This should result in more memory usage since gesture read triggers allocation of a reusable 129-byte `bytearray` buffer.

|  | `mem_free` | newly used |
|---|---|---|
| only `gc` imported | `18,480` |
| `import time`<br>`import board` | `18,464` | `16` |
| `i2c = board.I2C()` | `18,464` | `0` | 
| Internal driver imports<br>`RWBits`,`RWBit`,`I2CDevice` | `15,760` | `2,704`
| Driver import<br>`APDS9960` | `13,232` | `2,528`
| _driver plus imports_ | | `[5,232]`|
| Device instantiate<br>`apds = APDS9960(i2c)` | `13,072` | `160`
| _loop start_ | | |
| `gc.collect()`<br>`print(apds.gesture())` | `12,912` | `160`
| _no change in subsequent loops_

Raw output:

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
18480
18464
18464
15760
13232
13072
0
12912
0
12912
```

##### Test 1: Color Read Only

Like gesture, we'd expect to see some increase when the `color` function is used due to some buffers that get allocated. After a few runs allocations should stabilize.

|  | `mem_free` | newly used |
|---|---|---|
| only `gc` imported | `18,480` |
| `import time`<br>`import board` | `18,464` | `16` |
| `i2c = board.I2C()` | `18,464` | `0` | 
| Internal driver imports<br>`RWBits`,`RWBit`,`I2CDevice` | `15,760` | `2,704`
| Driver import<br>`APDS9960` | `13,248` | `2,512`
| _driver plus imports_ | | `[5,216]`|
| Device instantiate<br>`apds = APDS9960(i2c)` | `13,088` | `160`
| _loop start_ | | |
| `gc.collect()`<br>`print(apds.color_data)` | `13,056` | `32`
| `gc.collect()`<br>`print(apds.color_data)` | `13,024` | `32`
| _no change in subsequent loops_

Raw output:

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
18480
18464
18464
15760
13248
13088
(0, 0, 0, 0)
13056
(0, 0, 0, 3273)
13024
(1604, 1135, 1046, 3273)
13024
(1604, 1136, 1046, 3272)
13024
```

##### Test 1: Import driver without pre-importing driver-internal imports

Raw Output

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
18528
18512
18512
18512
13296
13152
```

Without pre-importing the driver takes up `5,216` bytes, identical memory occupied with pre-imports.

#### Test 2: Unbundled, custom firmware build, community bundle

* CircuitPython Version: `7.1.0-beta1`, custom build
* Driver Version: `v2.2.8`
    * From community bundle `20211118`

| | | |
|---|---|---|
| Driver file size | `3,839` | Latest bundle `mpy` file |
| Memory used by import | `7,440` |
| Memory used by instantiate | `128`
| Memory used by `gesture()` | `160`

From here I'm going to look primarily at gesture read scenarios, since that's the primary item we're changing now. Also changing to a three-point logging of memory usage during init now that we know what's most interesting.

#### Test 3: Unbundled, custom build, custom compiled `mpy`

* CircuitPython Version: `7.1.0-beta1`, custom build
* Driver Version: `v2.2.8`
    * From GitHub repo

| | | |
|---|---|---|
| Driver file size | `3,854` |  |
| Memory used by import | `7,472` |
| Memory used by instantiate | `128`
| Memory used by `gesture()` | `160`

Similar results, but 32 more bytes being added after library import

#### Test 4: Unbundled, custom build, custom compiled `mpy` after constants edits

* CircuitPython Version: `7.1.0-beta1`, custom build
* Driver Version: `v2.2.8`
    * From GitHub repo [PR #37](https://github.com/adafruit/Adafruit_CircuitPython_APDS9960/pull/37)

| | | |
|---|---|---|
| Driver file size | `3,854` |  |
| Memory used by import | `6,912` |
| Memory used by instantiate | `128`
| Memory used by `gesture()` | `160`

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
19984
13072
12944
0
12784
```

#### Test 5: Adding prox/gesture engine control instance variables and "set_defaults" flag (v1)

| | | |
|---|---|---|
| Driver file size | `5,080` |  |
| Memory used by import | `11,200` |
| Memory used by instantiate | `144`
| Memory used by `gesture()` | `160`

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
19984
8784
8640
0
8480
```

#### Test 6:  Adding prox/gesture engine control instance variables and "set_defaults" flag (v2)

| | | |
|---|---|---|
| Driver file size | `5,424` |  |
| Memory used by import | `11,488` |
| Memory used by instantiate | `160`
| Memory used by `gesture()` | `160`

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
19984
8496
8336
0
8176
0
```

#### Test 8: New gesture engine, v1


| | | |
|---|---|---|
| Driver file size | `6,753` |  |
| Memory used by import | `12,784` |
| Memory used by instantiate | `144`
| Memory used by `gesture()` | `80`

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
19984
7200
7056
0
6976
```

#### Test 9: New gesture engine, v2 - committed


| | | |
|---|---|---|
| Driver file size | `6,753` |  |
| Memory used by import | `12,752` |
| Memory used by instantiate | `144`
| Memory used by zero-data `gesture()` | `80`
| Memory used by full-run `gesture()` | `784`

```
Auto-reload is on. Simply save files over USB to run them or enter REPL to disable.
code.py output:
19952
7200
7056
None
6976
Right
6192
```


## Appendix 1: Test Code

### Barebones Imports and Init

The `enable_<function>` lines are commented out for tests not requiring them.

```py
import gc
gc.collect()
print(gc.mem_free()) # 1 - start
import time
import board
gc.collect()
print(gc.mem_free()) # 2 = board/time
i2c = board.I2C()
gc.collect()
print(gc.mem_free()) # 3 - i2c setup
from adafruit_register.i2c_bits import RWBits
from adafruit_register.i2c_bit import RWBit
from adafruit_bus_device.i2c_device import I2CDevice
gc.collect()
print(gc.mem_free()) # 4 - internal driver imports
from adafruit_apds9960.apds9960 import APDS9960
gc.collect()
print(gc.mem_free()) # 5 - driver import
apds = APDS9960(i2c)
apds._gesture_mode = False # Avoid having to restart device to get new prox/gesture data
# apds.enable_proximity = True
# apds.enable_gesture = True
# apds.enable_color = True
gc.collect()
print(gc.mem_free()) # 6 - driver instantiate
```

#### Barebones Function Loops

Proximity only

```py
while True:
    gc.collect()
    print(apds.proximity)
    print(gc.mem_free()) # 7+ - looping, mid loop
    time.sleep(1)
```

#### Barebones Init, Simplified

```py
import gc
import time
import board
i2c = board.I2C()
gc.collect()
print(gc.mem_free()) # 1 - init imports
from adafruit_apds9960.apds9960 import APDS9960
gc.collect()
print(gc.mem_free()) # 2 - driver import
apds = APDS9960(i2c)
apds.enable_proximity = True
apds._gesture_mode = False # Avoid having to restart device with old driver
apds.enable_gesture = True # Avoid having to restart device with old driver
# apds.enable_color = True
gc.collect()
print(gc.mem_free()) # 3 - driver instantiate
```