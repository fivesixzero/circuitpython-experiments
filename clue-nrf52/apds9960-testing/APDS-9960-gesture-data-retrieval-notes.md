# Gesture Data Processing: Reading it In

### Reading In Gesture FIFO Data

In gesture mode, the entire register-accessible RAM space of the device, 128 bytes in total, is dedicated to the gesture FIFOs.

The FIFO system handles internal pointer management. When a dataset is fully read in, two things happen internally. First, the Gesture FIFO Level register (`GFLVL`, `0xAE`) will decrement by one. Second, the internal FIFO pointer will shift to the next entry. Nice.

There are two ways we can read in these FIFOs. One at a time, or via a "page read".

#### FIFO Reads: One At A Time

The simplest way to read in these entries is one dataset at a time. We do this by reading each of the four `GFIFO` registers in sequence.

```py
data_tuple = (
    self._read8(_APDS9960_GFIFO_U), 
    self._read8(_APDS9960_GFIFO_D), 
    self._read8(_APDS9960_GFIFO_L), 
    self._read8(_APDS9960_GFIFO_R)
    ))
```

Although this is simple, its pretty inefficient in terms of bus traffic and memory usage. Of course, there's a better way.

#### FIFO Reads: Page Read

Alternatively we can read in an entire "page" of entries at once.

```py
record_count = self.gesture_fifo_level

if not self.buffer129:
    self.buffer129 = bytearray(129)

self.buffer129[0] = _APDS9960_GFIFO_U

with self.i2c_device as i2c:
    i2c.write_then_readinto(
        self.buffer129,
        self.buffer129,
        out_end=1,
        in_start=1,
        in_end=min(129, 1 + (record_count * 4)),
    )
```

This, coincidentally, is what Avago/Broadcom recommend in the datasheet:

>The recommended procedure for reading data stored in the FIFO begins when a gesture interrupt is generated (GFLVL >
GFIFOTH). Next, the host reads the FIFO Level register, GFLVL, to determine the amount of valid data in the FIFO.
>
>Finally, the host begins to read address 0xFC (page read), and continues to read (clock-out data) until the FIFO is empty
(Number of bytes is 4X GFLVL). For example, if GFLVL = 2, then the host should initiate a read at address 0xFC, and sequentially read all eight bytes. As the four-byte blocks are read, GFLVL register is decremented and the internal FIFO
pointers are updated.

#### FIFO Reads: When? Is the data stale? How much is there?

Pulling in a page read requires us to figure out three things.

1. When do we need to pull data?
2. Is the existing FIFO data already stale?
3. How much data do we need to pull?

I'll work through those questions in reverse order, which happens to be ascending-complexity order. :)

#### FIFO Reads: How much data is there?

By definition, a page has a size. In this case, the number of entries in our FIFO. If we don't know the size, we unlikely to have much success reading it in, yeah?

This one is easy to figure out by reading from the Gesture FIFO Level register, `GFLVL` (`0xAE`). 

When read, this register simply returns an 8-bit integer representing the number of datasets currently present in the FIFO.

#### FIFO Reads: Is the data stale?

Like that month-old pizza in the fridge, even the best datasets eventually become gross enough that it should probably just go right into trash. Or compost, if you're into that sort of thing.

Thankfully that's also pretty easy to answer, thanks to the Gesture FIFO Overflow register, `GSTATUS<GFOV>` (`0xAF[1]`). If this is asserted then the FIFO has already filled up. Since we took to long to get around to a FIFO read, that data likely needs to be disregarded since gesture events typically generate more than 32 datasets. More on that later though.

#### FIFO Reads: When do we need to read?

Theoretically, this is as easy as just checking to see if `GSTATUS<GVALID>` (`0xAF[0]`) is asserted. Once our FIFOs are cleared by full page reads, that'll get reset.

But, of course, it really isn't that easy.

The ideal method of handling this would be to set up the sensor to flip its interrupt pin when the Gesture Engine is running and has enough data in the FIFO to make it worth our time. This way the host system can start reading in right away and, once the FIFO is clear, do the math to figure out what the heck might have happened.

Setting this up will require us to make some decisions. And, of course, those decisions will lead to config registers being set.

1. How frequently should the sensor be sensing and writing datasets to the FIFO?
    * `GCONFIG2<GWTIME>` (`0xA3[2:0]`)
    * This three-bit int value (`0` to `7`) lets us decide how many `2.78 ms`cycles to wait between gesture engine loop runs
    * Each cycle takes at least `1.3 ms` (the ADC integration time for gesture cycles) but increasing `GWTIME` add on an additional `2.78 ms` (`0x01`) to `19.56 ms` (`0x07`) per cycle
2. How many datasets should we wait for before asserting an internal interrupt?
    * `GCONFIG1<GFIFOTH>` (`0xA2[7:6]`)
    * This 4-bit int value allows us to choose from four different options for FIFO thresholds
    * By default, at a value of `0x0`, `GINT` is asserted once the first dataset is added and its highest value of `0x4` `GINT` won't get asserted until our FIFOs are half full with 16 entries in them
3. Should that internal interrupt also assert the sensor's interrupt pin?
    * `GCONFIG4<GEIN>` (`0xAB[1]`)
    * With `GEIN` asserted the sensor's external interrupt pin will be asserted as soon as `GINT` is
4. What's our low-threshold to use when we're deciding whether to loop again, or how many loops are enough?
    * `GEXTH` (`0xA1`)
    * Setting `GEXTH` lets us decide how low is "too low" for gesture data to be useful for our purposes, which effectively lets us decide when to stop looping
6. Should we pay attention to all of the photodiodes while making evaluating whether to loop again? Or should we ignore one or more?
    * `GCONFIG1<GEXMSK>` (`0xA2[5:2]`)
    * This can be handy if we want to simplify the "should loop again" decision by removing one or more photodiodes from the equation
5. How many consecutive times should we persist in looping with sub-threshold data before decide to move on with our lives?
    * `GEXTH` (`0xA1`)
    * Basically, how many low-value trailing items do we want to have at the end of our data?

If this looks like its a lot, that's because it kinda is. Other critical configurations, like the gesture proximity entry threshold, IR LED power settings, and masking/gain of photosensors can make a big impact on the data collected. But that's for another discussion.

#### FIFO Reads: Living in a synchronous world

So, we'll just have the sensor assert an interrupt and we'll know exactly when to grab the latest gesture data!

Well... Not really.

We're kinda focused using this sensor with CircuitPython. As of this writing, version `7.1.0-beta1` does offer async support but "native" pin-interrupt handlers aren't part of the story. Yet.

Also, we're aiming to write a general purpose driver here. Something that can be imported and used on a SAMD21 with 256k of storage (all of 44k available for user code) and 32k of RAM (and all of ~18k free for imports/objects at run-time).

So, after all that explanation, we're going to start with a synchronous approach with user code continuously polling, either via I2C or the interrupt pin.

#### FIFO Reads: Putting it all together

Ok, so we should have answers to our three questions.

1. When do we need to pull data?
    * One of two ways: Continuous I2C polling or pin interrupt. We'll start with I2C polling.
    * As far as config goes, we'll tune things with the goal of catching the FIFOs mid-stream, before they refill
2. Is the existing FIFO data already stale?
    * We'll check `GFOV` before we retrieve data and if its asserted, we'll raise an error since being too slow here is actually a pretty bad thing
3. How much data do we need to pull?
    * In addition to pulling a full page, we'll wait at least a cycle (~`3 ms`) and check to see if new data has come in since our pull and, if so, we'll grab some more until the FIFO is clear

This code wraps all of that up

```py
    def gesture_data(self) -> List[Tuple[int, int, int, int]]:
        datasets = []

        # If we've already overflowed, clear out the stale FIFOs right away and start anew
        if self.gesture_fifo_overflow:
            self.gesture_fifo_clear = True
            while not self._gesture_valid:
                time.sleep(0.001) 

        if self._gesture_valid and self.gesture_fifo_level > 0:
            record_count = self.gesture_fifo_level

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
                low_threshold = 10
                for i in range(record_count):
                    rec = i + 1
                    idx = 1 + ((rec - 1) * 4)

                    record_tuple = (
                        self.buf129[idx],
                        self.buf129[idx + 1],
                        self.buf129[idx + 2],
                        self.buf129[idx + 3],
                    )
                    
                    # Drop fully-saturated records to conserve memory
                    if all(val == 255 for val in record_tuple):
                        pass
                    # Drop fully-zero records to conserve memory
                    elif all(val == 0 for val in record_tuple):
                        pass
                    # Low-pass filter to remove potentially spurious very-low-count entries
                    elif all(val < low_threshold for val in record_tuple):
                        pass
                    else:
                        datasets.append(record_tuple)

                # If we've managed to empty the FIFOs, lets wait to see if any movement is still in progress
                # We won't wait forever though!
                if self.gesture_fifo_level == 0:
                    time.sleep(gesture_wait * 0.001)
                    if self.gesture_fifo_level == 0 or len(datasets) >= max_gesture_datasets:
                        break

        return datasets
```

The data we get back is a list of individual dataset tuples.