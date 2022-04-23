#### `HX711` PIO Driver

Early versions and notes from development of a proper HX711 driver that makes use of RP2040 PIO, with a GPIO option for non-RP2040 boards.

## Notes

This was a fun experiment to learn how CircuitPython and the RP2040's PIO engines can work together to do some neat things! It took a bit of trial and error to nail down the most effective implementation, so here are some notes.

### HX711: Why?

This sensor IC (and its various breakouts) are ubiquitous and can be found pretty much anywhere electronics parts can be found. Its the closest thing to a jellybean load cell amp/ADC that I've been able to find so far. The cost is also very, very low, even in breakout board form, going as low as $0.40 a piece at low quantities (as of April 2022).

There are definitely more capable devices out there but the intersection of ubquitity and super-low cost make this a really fun chip for makers and people doing rapid prototyping. But there wasn't a CircuitPython Community Bundle driver for it yet! I had some time and wanted to learn RP2040 PIO, so here we are.

### HX711 Basics: Load Cells

I won't go into detail here, but load cells that will work with the `HX711` are all over the place. There are load cells on bars of metal, load cells on button-sized metal pads, and a ton of other types that'll work.

Additionally, there a bunch of different configuration options, like using multiple load cells on corners of a platform instead of a single cell.

### HX711 Basics: The Chip and Measurements

This is a very easy sensor to work with, at a low level. It's very flexible and tolerant of clock deviations/blips, making it easy to just bit-bang pins to get what we need. It's just got two pins - a data pin and a clock pin. In our use case here our microcontroller is going to use one GPIO pin as a clock output and a second as a data input.

Internally the `HX711` creates a 24-bit ADC result at a rate defined by either its internal oscillator (at 10 or 80 Hz) or an external oscillator. When a new ADC reading is available it pulls the data pin low.

When this goes low, we just need to use the clock pins to send out 24 pulses, one for each data bit. During each pulse the HX711's internal shift register will send out a single bit of the result value. After 24 clock cycles we just need to send one, two, or three more to tell the ADC what gain to use for the next ADC reading.

The data that we get back is a 24-bit two's compliment integer. This can be a bit of a headache to work with in Python, but its not impossible. For GPIO reads we can build our result one bit at a time using bit-shifts. For PIO reads we can just pad the result then shift or mask out the padding before converting to a proper, pythonic 4-byte int.

From there it's just a matter of dealing with typical 'scale' stuff - tare and scaling factor. Once that's done, you'll know what something weighs! Pretty neat for such an inexpensive little chip.

### Bit Alignment: PIO RX Buffers + CircuitPython

This sensor reads out 24 bits of data while it's clocked, with one, two, or three subsequent clock pulses dictating the gain of the next ADC reading. This was probably the most fun head-scratcher of the project, since bit-alignment between the PIO RX FIFO and CPy wasn't super easy to grok.

In the end, padding it with 8 bits up front with a loop of 8 reads before clocking for a the actual data read-in was the way to go. This way we can fit into a proper 32-bit alignment and just mask out those extra bits after we're done.

## Links:

* `HX711` Datasheet: <https://cdn.sparkfun.com/datasheets/Sensors/ForceFlex/hx711_english.pdf>
* `HX711` Breakout Datasheet: <https://community.infineon.com/gfawx74859/attachments/gfawx74859/CodeExamples/546/7/HX711_v0_0_B.pdf>
* MicroPython driver: <https://github.com/SergeyPiskunov/micropython-hx711/blob/master/hx711.py>
* MicroPython driver: <https://github.com/robert-hh/hx711>
* Arduino driver: <https://github.com/bogde/HX711>