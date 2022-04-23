"""
`HX711`
====================================================

Driver superclass for the HX711 load cell amplifier/DAC.

* Author(s): Erik Hess

Implementation Notes
--------------------

**Driver Subclasses**

* `HX711_GPIO`, works with all boards but may be subject to timing issues
* `HX711_PIO`, works with RP2040's PIO to provide more consistent pulse timing

**Hardware:**

* SparkFun `HX711 Load Cell Amplifier Breakout <https://www.sparkfun.com/products/13879>`_
"""

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/fivesixzero/CircuitPython_HX711"

class HX711():

    def __init__(
        self,
        gain: int = 1,
        offset: int = 0,
        scale: float = 1,
        tare: bool = False
    ):
        
        self.gain = gain
        self.offset = offset
        self.scale = scale

        if tare:
            self.read_raw()  # Pull a reading to avoid first-read issues
            self.tare()

    @property
    def gain(self) -> int:
        return self._gain
    
    @gain.setter
    def gain(self, gain: int) -> None:
        if gain < 1 or gain > 3:
            raise ValueError()
        else:
            self._gain = gain

    def tare(self) -> None:
        self.offset = self.read_raw()
        
    def determine_scale(self, weight: float) -> float:
        if not self.offset:
            raise ValueError()

        reading = self.read_average()
        diff = abs(reading - self.offset)
        self.scale = diff / weight
        return self.scale

    def read(self, average_count: int = 1) -> int:
        if average_count > 1:
            return (self.read_average() - self.offset) / self.scale
        else:
            return (self.read_raw() - self.offset) / self.scale

    def read_average(self, count: int = 10):
        readings = []

        for i in range(count):
            readings.append(self.read_raw(clear_fifo=False))
        
        return sum(readings) // len(readings)

    def read_raw(self) -> int:
        raise NotImplementedError()
