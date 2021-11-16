# APDS-9960 Gesture Notes

The Gesture Engine on the APDS-9960 is interesting. You can't just ask it "Was there a gesture? If so, what was it?". Instead, you have to do all that work in your driver or userland implementation.

Unlike some more integrated sensors, this device doesn't do the work of determining a gesture. It simply stores sequential data in a buffer of up to 32 entries for four photodiodes with different view cones.

Its up to the implementer to choose how to crunch those numbers to answer the important questions. For a CircuitPython driver, at minimum, we should hopefully be able to provide a user the ability to detect "up", "down", "left", and "right" movements.

## Capturing Gesture Data

Gathering data from the sensor is a bit tricky. The FIFO holds 32 entries and it can fill up very quickly. Once its full data gets stale very, very fast. Even as it empties we could see several new entries show up in the time it takes to read data over the I2C bus.

A few things come to mind to help manage this.

First, we can increase `GWTIME` to give us more breathing room between cycles. We'll get less granularity in our results but if we're only looking at the first few and the last few this probably isn't a big deal at all.

Second, we can use `GFIFOTH` and the internal `GINT` flag to give us a better idea of when we should start reading in new data. For our use case though these may end up being a bit too narrowly-focused.

Third, we can adapt our read-in process to repeat reads until our FIFOs are empty for a few cycles. This is important to avoid cases where a single gesture creates data that exceeds our entire FIFO-full time window.

What is that time window anyway? With `GWTIME` at `0` we get no additional delay added to each cycle. The ADC conversion time is `1.39 ms` and that should be the longest delay. That means we'll have a full buffer in as little as `44.48 ms`! Whew. Even just bumping `GWTIME` to `1` takes that up to `133.44 ms`.

These settings and this code are working alright for now but both definitely need more tuning/testing.

### Gesture Engine Configuration

These still need some tuning/testing but are getting us a lot closer to sensible defaults.

```py
apds.gesture_proximity_threshold = 5
apds.gesture_exit_threshold = 100
apds.gesture_exit_persistence = 2
apds.gesture_fifo_threshold = 1
apds.gesture_wait_time = 3
apds.gesture_gain = 1
apds.gesture_pulses = 8
apds.gesture_pulse_length = 1
```

### Gesture Data Acquisition Code

```py
    def gesture_data(self) -> List[Tuple[int, int, int, int]]:
        datasets = []

        # If we've already overflowed, clear out the stale FIFOs right away and start anew
        # TODO: Figure out a better way to handle premature overflows, maybe
        if self.gesture_fifo_overflow:
            self.gesture_fifo_clear = True
            # DEBUG
            print("GESTURE PRE   | already overflowed, clearing FIFOs now and waiting")
            while not self._gesture_valid:
                time.sleep(0.001) 

        if self._gesture_valid and self.gesture_fifo_level > 0:
            record_count = self.gesture_fifo_level

            # DEBUG
            print("GESTURE BEGIN | gint: {:1} | gvalid: {:1} | gfifolvl: {:3} | status: {:08b}".format(
                self.gesture_interrupt,
                self._gesture_valid,
                self.gesture_fifo_level,
                self._read8(_APDS9960_STATUS)
            ))

            if self.buf129 is None:
                self.buf129 = bytearray(129)

            # Acquire gesture data
            # Also, keep stacking new datasets if they show up while we're reading in FIFO data
            # Or, like, if we hit max_gesture_datasets
            max_gesture_datasets = 255
            while True:
                gesture_wait = self.gesture_wait_time * 3

                # Acquire all available data
                record_count = self.gesture_fifo_level
                self.buf129[0] = _APDS9960_GFIFO_U
                with self.i2c_device as i2c:
                    i2c.write_then_readinto(
                        self.buf129,
                        self.buf129,
                        out_end=1,
                        in_start=1,
                        in_end=min(129, 1 + (record_count * 4)),
                    )

                # Unpack data stream into more usable U/D/L/R datasets
                idx = 0
                for i in range(record_count):
                    rec = i + 1

                    idx = 1 + ((rec - 1) * 4)
                    datasets.append((
                        self.buf129[idx],
                        self.buf129[idx + 1],
                        self.buf129[idx + 2],
                        self.buf129[idx + 3],
                    ))

                # If we've cleared the FIFOs, lets wait to see if any movement is still in progress
                # We won't wait forever though!
                if self.gesture_fifo_level == 0:
                    time.sleep(gesture_wait * 0.001)
                    if self.gesture_fifo_level == 0 or len(datasets) >= max_gesture_datasets:
                        break

            # DEBUG
            for i in range(len(datasets)):
                print("GESTURE DATA  | set #{:02}/{:02}: {}".format(
                    i + 1,
                    len(datasets),
                    datasets[i]
                ))

            # DEBUG
            print("GESTURE END   | gint: {:1} | gvalid: {:1} | gfifolvl: {:3}".format(
                self.gesture_interrupt,
                self._gesture_valid,
                self.gesture_fifo_level
            ))
            
            return datasets
```

## Determining a Gesture

We'll have a lot of work to do if we want to properly detect incoming gestures. The datasheet gives us a general pattern to expect with various movements but getting this right will take a lot of testing with real-life behavior.

Thankfully, we have a pretty decent starting point in the form of [SparkFun's APDS-9960 Arduino library](https://github.com/sparkfun/SparkFun_APDS-9960_Sensor_Arduino_Library/blob/master/src/SparkFun_APDS9960.cpp).

In this library, they chose to "process" gesture data in a function called `processGestureData()` then "decode" gesture data in another function called `decodeGesture()`.

With a bit of elbow grease we can translate this into something more snakey.

### Gesture Data Processing/Decoding

Like the acquisition code above this is rough and definitely not perfect in practice.

Even in this rough shape though its producing largely deterministic results from hand-swipe events within a few centimeters of the sensor! Pretty exciting to see that we' may be on the right track.

```py
    def gesture(self) -> int:
        gesture_data = self.gesture_data()
        
        if not gesture_data:
            return 0

        # if (0, 0, 0, 0) in (gesture_data):
        #     print("GEST ANALYSIS | Junk data, all zeroes present")
        #     return 0

        if len(gesture_data) > 0:
            print("GEST ANALYSIS | Start Gesture Analysis")

            zeroes = (0, 0, 0, 0)
            first_data = (0, 0, 0, 0)
            last_data = (0, 0, 0, 0)
            GESTURE_THRESHOLD_OUT = 30

            # Find first/last values
            for early_gesture_tuple in gesture_data:
                # if [(gv > thr) for gv, thr in zip(early_gesture_tuple, GESTURE_THRESHOLD_OUT)]
                if (early_gesture_tuple[0] > GESTURE_THRESHOLD_OUT and
                    early_gesture_tuple[1] > GESTURE_THRESHOLD_OUT and
                    early_gesture_tuple[2] > GESTURE_THRESHOLD_OUT and
                    early_gesture_tuple[3] > GESTURE_THRESHOLD_OUT):
                        first_data = early_gesture_tuple
                        break # Stop iterating on our first hit

            print("GEST ANALYSIS | First: {}".format(first_data))

            for reverse_gesture_tuple in reversed(gesture_data):
                if (reverse_gesture_tuple[0] > GESTURE_THRESHOLD_OUT and
                    reverse_gesture_tuple[1] > GESTURE_THRESHOLD_OUT and
                    reverse_gesture_tuple[2] > GESTURE_THRESHOLD_OUT and
                    reverse_gesture_tuple[3] > GESTURE_THRESHOLD_OUT):
                        last_data = reverse_gesture_tuple
                        break # Stop iterating on our first hit

            print("GEST ANALYSIS | Last:  {}".format(last_data))

            if first_data == zeroes or last_data == zeroes:
                print("GEST ANALYSIS | Junk data, all under useful thresholds")
                return 0

            # Ratios and Deltas
            ud_ratio_first = ((first_data[0] - first_data[1]) * 100) / (first_data[0] + first_data[1])
            lr_ratio_first = ((first_data[2] - first_data[3]) * 100) / (first_data[2] + first_data[3])
            ud_ratio_last = ((last_data[0] - last_data[1]) * 100) / (last_data[0] + last_data[1])
            lr_ratio_last = ((last_data[2] - last_data[3]) * 100) / (last_data[2] + last_data[3])


            # Calculate delta betwen first and last ratios
            ud_delta = ud_ratio_last - ud_ratio_first
            lr_delta = lr_ratio_last - lr_ratio_first

            print("GEST ANALYSIS | UD Ratio | First: {}, Last: {}, Delta: {}".format(ud_ratio_first, ud_ratio_last, ud_delta))
            print("GEST ANALYSIS | LR Ratio | First: {}, Last: {}, Delta: {}".format(lr_ratio_first, lr_ratio_last, lr_delta))

            # Accumulate UD/LR deltas
            self.gesture_ud_delta += ud_delta
            self.gesture_lr_delta += lr_delta

            GESTURE_SENSITIVITY_1 = 50
            GESTURE_SENSITIVITY_2 = 20

            # Basic Gesture Determination
            # Determine U/D Gesture
            if self.gesture_ud_delta >= GESTURE_SENSITIVITY_1:
                self.gesture_ud_count = 1
            elif self.gesture_ud_delta <= -GESTURE_SENSITIVITY_1:
                self.gesture_ud_count = -1
            else:
                self.gesture_ud_count = 0

            # Determine L/R Gesture
            if self.gesture_lr_delta >= GESTURE_SENSITIVITY_1:
                self.gesture_lr_count = 1
            elif self.gesture_lr_delta <= -GESTURE_SENSITIVITY_1:
                self.gesture_lr_count = -1
            else:
                self.gesture_lr_count = 0
            
            # Determine Near/Far Gesture
            if self.gesture_ud_count == 0 and self.gesture_lr_count == 0:
                if abs(ud_delta) < GESTURE_SENSITIVITY_2 and \
                   abs(lr_delta) < GESTURE_SENSITIVITY_2:

                    if ud_delta == 0 and lr_delta == 0:
                        self.gesture_near_count += 1
                    elif ud_delta != 0 and lr_delta != 0:
                        self.gesture_far_count += 1

                    if self.gesture_near_count >= 10 and self.gesture_far_count >= 2:
                        if ud_delta == 0 and lr_delta == 0:
                            self.gesture_state = "near"
                        elif ud_delta != 0 and lr_delta != 0:
                            self.gesture_state = "far"
            else:
                if abs(ud_delta) < GESTURE_SENSITIVITY_2 and \
                   abs(lr_delta) < GESTURE_SENSITIVITY_2:
                    if ud_delta == 0 and lr_delta == 0:
                        self.gesture_near_count += 1
                    
                    if self.gesture_near_count >= 10:
                        self.gesture_ud_count = 0
                        self.gesture_lr_count = 0
                        self.gesture_ud_delta = 0
                        self.gesture_lr_delta = 0
            
            print("GEST ANALYSIS | Globals | UD Count: {}, LR Count: {}, Near Count: {}, Far Count: {}".format(
                self.gesture_ud_count, self.gesture_lr_count, self.gesture_near_count, self.gesture_far_count))
            print("GEST ANALYSIS | Globals | UD Delta: {}, LR Delta: {}".format(self.gesture_ud_delta, self.gesture_lr_delta))
            print("GEST ANALYSIS | Globals | state: {}, motion: {}".format(self.gesture_state, self.gesture_motion))

            # ## DECODE GESTURE
            # print("GEST DECODE   | Start Gesture Decode")

            # Return if near or far event is detected
            if self.gesture_state == "near":
                self.gest_motion = "near"
                print("GEST DECODE   | Gesture Decuded: NEAR")
                return 0
            elif self.gesture_state == "far":
                self.gesture_motion = "far"
                print("GEST DECODE   | Gesture Decuded: FAR")
                return 0

            # Determine swipe direction
            if self.gesture_ud_count == -1 and self.gesture_lr_count == 0:
                self.gesture_motion = "up"
            elif self.gesture_ud_count == 1 and self.gesture_lr_count == 0:
                self.gesture_motion = "down"
            elif self.gesture_ud_count == 0 and self.gesture_lr_count == 1:
                self.gesture_motion = "right"
            elif self.gesture_ud_count == 0 and self.gesture_lr_count == -1:
                self.gesture_motion = "left"
            elif self.gesture_ud_count == -1 and self.gesture_lr_count == 1:
                if abs(self.gesture_ud_delta) > abs(self.gesture_lr_delta):
                    self.gesture_motion = "up"
                else:
                    self.gesture_motion = "down"
            elif self.gesture_ud_count == 1 and self.gesture_lr_count == -1:
                if abs(self.gesture_ud_delta) > abs(self.gesture_lr_delta):
                    self.gesture_motion = "down"
                else:
                    self.gesture_motion = "left"
            elif self.gesture_ud_count == -1 and self.gesture_lr_count == -1:
                if abs(self.gesture_ud_delta) > abs(self.gesture_lr_delta):
                    self.gesture_motion = "up"
                else:
                    self.gesture_motion = "left"
            elif self.gesture_ud_count == 1 and self.gesture_lr_count == 1:
                if abs(self.gesture_ud_delta) > abs(self.gesture_lr_delta):
                    self.gesture_motion = "down"
                else:
                    self.gesture_motion = "right"
            else:
                # return 0
                pass            
            
            print("GEST DECODE   | Globals | state: {}, motion: {}".format(self.gesture_state, self.gesture_motion))
            
            if self.gesture_motion != "":
                print("GEST DECODE   | Successful decode, resetting counts!")
                self._reset_counts()
            
            # return 1

        return 0
```

Test results from a first run with the acquisition and decode stuff is looking pretty good.

```
GESTURE BEGIN | gint: 1 | gvalid: 1 | gfifolvl:   4 | status: 00100110
GESTURE DATA  | set #01/32: (31, 83, 54, 64)
GESTURE DATA  | set #02/32: (44, 107, 73, 81)
GESTURE DATA  | set #03/32: (65, 134, 99, 101)
GESTURE DATA  | set #04/32: (89, 168, 129, 126)
GESTURE DATA  | set #05/32: (119, 201, 164, 152)
GESTURE DATA  | set #06/32: (160, 240, 204, 185)
GESTURE DATA  | set #07/32: (204, 255, 249, 219)
GESTURE DATA  | set #08/32: (254, 255, 255, 251)
GESTURE DATA  | set #09/32: (255, 255, 255, 255)
GESTURE DATA  | set #10/32: (255, 255, 255, 255)
GESTURE DATA  | set #11/32: (255, 255, 255, 255)
GESTURE DATA  | set #12/32: (255, 255, 255, 255)
GESTURE DATA  | set #13/32: (255, 255, 255, 255)
GESTURE DATA  | set #14/32: (255, 255, 255, 255)
GESTURE DATA  | set #15/32: (255, 255, 255, 255)
GESTURE DATA  | set #16/32: (255, 255, 255, 255)
GESTURE DATA  | set #17/32: (255, 255, 255, 255)
GESTURE DATA  | set #18/32: (255, 255, 255, 255)
GESTURE DATA  | set #19/32: (255, 255, 255, 255)
GESTURE DATA  | set #20/32: (255, 255, 255, 255)
GESTURE DATA  | set #21/32: (255, 255, 255, 255)
GESTURE DATA  | set #22/32: (255, 255, 255, 255)
GESTURE DATA  | set #23/32: (255, 255, 255, 255)
GESTURE DATA  | set #24/32: (255, 255, 255, 255)
GESTURE DATA  | set #25/32: (255, 161, 255, 255)
GESTURE DATA  | set #26/32: (255, 67, 255, 255)
GESTURE DATA  | set #27/32: (255, 25, 132, 156)
GESTURE DATA  | set #28/32: (144, 7, 50, 85)
GESTURE DATA  | set #29/32: (62, 0, 11, 39)
GESTURE DATA  | set #30/32: (25, 0, 0, 15)
GESTURE DATA  | set #31/32: (12, 0, 0, 4)
GESTURE DATA  | set #32/32: (4, 0, 0, 0)
GESTURE END   | gint: 0 | gvalid: 0 | gfifolvl:   0
GEST ANALYSIS | Start Gesture Analysis
GEST ANALYSIS | First: (31, 83, 54, 64)
GEST ANALYSIS | Last:  (255, 67, 255, 255)
GEST ANALYSIS | UD Ratio | First: -45.614, Last: 58.3851, Delta: 103.999
GEST ANALYSIS | LR Ratio | First: -8.47458, Last: 0.0, Delta: 8.47458
GEST ANALYSIS | Globals | UD Count: 1, LR Count: 0, Near Count: 0, Far Count: 0
GEST ANALYSIS | Globals | UD Delta: 103.999, LR Delta: 8.47458
GEST ANALYSIS | Globals | state: , motion: 
GEST DECODE   | Globals | state: , motion: down
GEST DECODE   | Successful decode, resetting counts!
```

The biggest downside is fact that any implementation of this algorithm is likely increase the library size substantially. For now though I'm inclined to get it working reliably, see how big it gets, and decide what to do after that.

## Ref Links

* SparkFun Arduino Driver: <https://github.com/sparkfun/SparkFun_APDS-9960_Sensor_Arduino_Library/blob/master/src/SparkFun_APDS9960.cpp>
* Linux Driver Source: <https://elixir.bootlin.com/linux/v5.16-rc1/source/drivers/iio/light/apds9960.c>
    * **Fun Fact**: Contains a neat comment: `Disable gesture sensor, since polling is useless from user-space`. Ha!
* Rust Driver Source: <https://docs.rs/apds9960/0.1.0/apds9960/>