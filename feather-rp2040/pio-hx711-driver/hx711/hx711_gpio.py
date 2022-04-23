import time
from digitalio import DigitalInOut
from micropython import const
from . import HX711

HX_DATA_BITS = const(24)

class HX711_GPIO(HX711):

    def __init__(
            self, 
            pin_data: DigitalInOut,
            pin_clk: DigitalInOut,
            *,
            gain: int = 1, 
            offset: int = 0,
            scale: int = 1,
            tare: bool = False,
        ):


        self._pin_data = pin_data
        self._pin_data.switch_to_input()

        self._pin_clk = pin_clk
        self._pin_clk.switch_to_output()

        self.gain = gain

        self.read_raw()

        super().__init__(gain, offset, scale, tare)

    def _gain_pulse(self, gain: int) -> None:
        for i in range(gain):
            self._pin_clk.value = True
            self._pin_clk.value = False

    def read_raw(self) -> int:
        while self._pin_data.value:
            time.sleep(0.01)

        raw_reading = 0
        for i in range(HX_DATA_BITS):
            self._pin_clk.value = True
            self._pin_clk.value = False
            raw_reading = raw_reading << 1 | self._pin_data.value
        
        self._gain_pulse(self.gain)

        return raw_reading
        
