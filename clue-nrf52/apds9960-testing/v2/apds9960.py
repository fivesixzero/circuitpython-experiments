# SPDX-FileCopyrightText: 2017 Michael McWethy for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`APDS9960`
====================================================

Driver class for the APDS9960 board.  Supports gesture, proximity, and color
detection.

* Author(s): Michael McWethy, Erik Hess

Implementation Notes
--------------------

**Hardware:**

* Adafruit `APDS9960 Proximity, Light, RGB, and Gesture Sensor
  <https://www.adafruit.com/product/3595>`_ (Product ID: 3595)

* Adafruit `Adafruit CLUE
  <https://www.adafruit.com/product/4500>`_ (Product ID: 4500)

* Adafruit `Adafruit Feather nRF52840 Sense
  <https://www.adafruit.com/product/4516>`_ (Product ID: 4516)

* Adafruit `Adafruit Proximity Trinkey
  <https://www.adafruit.com/product/5022>`_ (Product ID: 5022)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""
import time
from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

try:
    # Only used for typing
    from typing import Tuple
    from busio import I2C
except ImportError:
    pass

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_APDS9960.git"

# Only one address is possible for the APDS9960, no alternates are available
_APDS9960_I2C_ADDRESS = const(0x39)
_DEVICE_ID = const(0xAB)

# APDS9960_RAM        = const(0x00)
_APDS9960_ENABLE = const(0x80)
_APDS9960_ATIME = const(0x81)
# _APDS9960_WTIME      = const(0x83)
# _APDS9960_AILTIL     = const(0x84)
# _APDS9960_AILTH      = const(0x85)
# _APDS9960_AIHTL      = const(0x86)
# _APDS9960_AIHTH      = const(0x87)
_APDS9960_PILT = const(0x89)
_APDS9960_PIHT = const(0x8B)
_APDS9960_PERS = const(0x8C)
# _APDS9960_CONFIG1    = const(0x8D)
# _APDS9960_PPULSE = const(0x8E)
_APDS9960_CONTROL = const(0x8F)
# _APDS9960_CONFIG2 = const(0x90)
_APDS9960_ID = const(0x92)
_APDS9960_STATUS = const(0x93)
_APDS9960_CDATAL = const(0x94)
# _APDS9960_CDATAH     = const(0x95)
# _APDS9960_RDATAL     = const(0x96)
# _APDS9960_RDATAH     = const(0x97)
# _APDS9960_GDATAL     = const(0x98)
# _APDS9960_GDATAH     = const(0x99)
# _APDS9960_BDATAL     = const(0x9A)
# _APDS9960_BDATAH     = const(0x9B)
_APDS9960_PDATA = const(0x9C)
# _APDS9960_POFFSET_UR = const(0x9D)
# _APDS9960_POFFSET_DL = const(0x9E)
# _APDS9960_CONFIG3    = const(0x9F)
_APDS9960_GPENTH = const(0xA0)
_APDS9960_GEXTH = const(0xA1)
_APDS9960_GCONF1 = const(0xA2)
_APDS9960_GCONF2 = const(0xA3)
# _APDS9960_GOFFSET_U  = const(0xA4)
# _APDS9960_GOFFSET_D  = const(0xA5)
# _APDS9960_GOFFSET_L  = const(0xA7)
# _APDS9960_GOFFSET_R  = const(0xA9)
_APDS9960_GPULSE = const(0xA6)
# _APDS9960_GCONF3 = const(0xAA)
_APDS9960_GCONF4 = const(0xAB)
_APDS9960_GFLVL = const(0xAE)
_APDS9960_GSTATUS = const(0xAF)
# _APDS9960_IFORCE     = const(0xE4)
# _APDS9960_PICLEAR    = const(0xE5)
# _APDS9960_CICLEAR    = const(0xE6)
_APDS9960_AICLEAR = const(0xE7)
_APDS9960_GFIFO_U = const(0xFC)
# APDS9960_GFIFO_D    = const(0xFD)
# APDS9960_GFIFO_L    = const(0xFE)
# APDS9960_GFIFO_R    = const(0xFF)

_BIT_MASK_ENABLE_EN = const(0x01)
_BIT_MASK_ENABLE_COLOR = const(0x02)
_BIT_MASK_ENABLE_PROX = const(0x04)
_BIT_MASK_ENABLE_PROX_INT = const(0x20)
_BIT_MASK_ENABLE_GESTURE = const(0x40)
_BIT_MASK_STATUS_GINT = const(0x04)
_BIT_MASK_GSTATUS_GFOV = const(0x02)
_BIT_MASK_GCONF4_GFIFO_CLR = const(0x04)

_BIT_POS_PERS_PPERS = const(4)
_BIT_MASK_PERS_PPERS = const(0xF0)

# pylint: disable-msg=too-many-instance-attributes
class APDS9960:
    """
    Provide basic driver services for the APDS9960 breakout board

    :param ~busio.I2C i2c: The I2C bus the APDS9960 is connected to
    :param int rotation: Rotation of the device. Defaults to :const:`0`
    :param bool reset: If true, reset device on init. Defaults to :const:`True`
    :param bool set_defaults: If true, set sensible defaults on init. Defaults to :const:`True`


    **Quickstart: Importing and using the APDS9960**

        Here is an example of using the :class:`APDS9960` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            from adafruit_apds9960.apds9960 import APDS9960

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            apds = APDS9960(i2c)

        Now you have access to the :attr:`apds.proximity_enable` :attr:`apds.proximity` attributes

        .. code-block:: python

            apds.proximity_enable = True
            proximity = apds.proximity

    """
    def __init__(
        self,
        i2c: I2C,
        *,
        rotation: int = 0,
        reset: bool = True,
        set_defaults: bool = True
    ):

        self.rotation = rotation

        self.buf129 = None  # Gesture FIFO buffer
        self.buf4 = None  # Gesture data processing buffer
        self.buf2 = bytearray(2)  # I2C communication buffer

        self.i2c_device = I2CDevice(i2c, _APDS9960_I2C_ADDRESS)

        if self._read8(_APDS9960_ID) != _DEVICE_ID:
            raise RuntimeError()

        if reset:
            # Disable prox, gesture, and color engines
            self.enable_proximity = False
            self.enable_gesture = False
            self.enable_color = False

            # Reset basic config registers to power-on defaults
            self.proximity_interrupt_threshold = (0, 0, 0)
            self._write8(_APDS9960_GPENTH, 0)
            self._write8(_APDS9960_GEXTH, 0)
            self._write8(_APDS9960_GCONF1, 0)
            self._write8(_APDS9960_GCONF2, 0)
            self._write8(_APDS9960_GCONF4, 0)
            self._write8(_APDS9960_GPULSE, 0)
            self._write8(_APDS9960_ATIME, 255)
            self._write8(_APDS9960_CONTROL, 1)

            # Clear all non-gesture interrupts
            self.clear_interrupt()

            # Clear gesture FIFOs and interrupt
            self._set_bit(_APDS9960_GCONF4, _BIT_MASK_GCONF4_GFIFO_CLR, True)

            # Disable sensor and all functions/interrupts and wait for sleep delay to finish
            self._write8(_APDS9960_ENABLE, 0)
            time.sleep(0.025)  # Entering sleep could take at least 25 ms if engines were active

            # Re-enable sensor and wait 10ms for the power on delay to finish
            self.enable = True
            time.sleep(0.010)  # Wake takes 5.7ms, per datasheet

        if set_defaults:
            # Trigger PINT at >= 5, PPERS: 4 cycles
            self.proximity_interrupt_threshold = (0, 5, 4)
            # Enter gesture engine at >= 5 counts
            self._write8(_APDS9960_GPENTH, 0x05)
            # Exit gesture engine if all counts drop below 30
            self._write8(_APDS9960_GEXTH, 0x1E)
            # GEXPERS: 2 (4 cycles), GEXMSK: 0 (default) GFIFOTH: 2 (8 datasets)
            self._write8(_APDS9960_GCONF1, 0x82)
            # GGAIN: 2 (4x), GLDRIVE: 100 mA (default), GGAIN: 1 (2x)
            self._write8(_APDS9960_GCONF2, 0x41)
            # GPULSE: 5 (6 pulses), GPLEN: 2 (16 us)
            self._write8(_APDS9960_GPULSE, 0x85)
            # ATIME: 182 (200ms color integration time)
            self._write8(_APDS9960_ATIME, 0xB6)
            # AGAIN: 1 (4x color gain), PGAIN: 0 (1x)
            self._write8(_APDS9960_CONTROL, 0x01)

    ## BOARD
    @property
    def enable(self) -> bool:
        """If true, the sensor is enabled
        If set to false, the sensor will enter a low-power sleep state"""
        return self._get_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_EN)

    @enable.setter
    def enable(self, value: bool) -> None:
        """If true, the sensor is enabled
        If set to false, the sensor will enter a low-power sleep state"""
        self._set_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_EN, value)

    ## Proximity Properties
    @property
    def enable_proximity(self) -> bool:
        """If true, the sensor's proximity engine is enabled"""
        return self._get_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_PROX)

    @enable_proximity.setter
    def enable_proximity(self, value: bool) -> None:
        """If true, the sensor's proximity engine is enabled"""
        self._set_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_PROX, value)

    @property
    def enable_proximity_interrupt(self) -> bool:
        """If true, internal proximity interrupts assert interrupt pin"""
        return self._get_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_PROX_INT)

    @enable_proximity_interrupt.setter
    def enable_proximity_interrupt(self, value: bool) -> None:
        """If true, internal proximity interrupts assert interrupt pin"""
        self._set_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_PROX_INT, value)

    @property
    def proximity_interrupt_threshold(self) -> Tuple[int, int, int]:
        """Tuple representing proximity engine low/high threshold (0-255) and persistence (0-15)"""
        return (
            self._read8(_APDS9960_PILT),
            self._read8(_APDS9960_PIHT),
            self._get_bits(_APDS9960_PERS, _BIT_POS_PERS_PPERS, _BIT_MASK_PERS_PPERS),
        )

    @proximity_interrupt_threshold.setter
    def proximity_interrupt_threshold(self, setting_tuple: Tuple[int, ...]) -> None:
        """Tuple representing proximity engine low/high threshold (0-255) and persistence (0-15)"""
        if setting_tuple:
            self._write8(_APDS9960_PILT, setting_tuple[0])
        if len(setting_tuple) > 1:
            self._write8(_APDS9960_PIHT, setting_tuple[1])
        persist = 4  # default 4
        if len(setting_tuple) > 2:
            persist = min(setting_tuple[2], 15)
            self._set_bits(
                _APDS9960_PERS, _BIT_POS_PERS_PPERS, _BIT_MASK_PERS_PPERS, persist
            )

    def clear_interrupt(self) -> None:
        """Clear all non-gesture interrupts"""
        self._writecmdonly(_APDS9960_AICLEAR)

    ## Gesture Properties
    @property
    def enable_gesture(self) -> bool:
        """If true, the sensor's gesture engine is enabled"""
        return self._get_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_GESTURE)

    @enable_gesture.setter
    def enable_gesture(self, value: bool) -> None:
        """If true, the sensor's gesture engine is enabled"""
        self._set_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_GESTURE, value)

    @property
    def rotation(self) -> int:
        """Gesture rotation offset. Acceptable values are 0, 90, 180, 270."""
        return self._rotation

    @rotation.setter
    def rotation(self, new_rotation: int) -> None:
        """Gesture rotation offset. Acceptable values are 0, 90, 180, 270."""
        if new_rotation in [0, 90, 180, 270]:
            self._rotation = new_rotation
        else:
            raise ValueError("Rotation value must be one of: 0, 90, 180, 270")

    ## Color/Light Properties
    @property
    def enable_color(self) -> bool:
        """If true, the sensor's color/light engine is enabled"""
        return self._get_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_COLOR)

    @enable_color.setter
    def enable_color(self, value: bool) -> None:
        """If true, the sensor's color/light engine is enabled"""
        self._set_bit(_APDS9960_ENABLE, _BIT_MASK_ENABLE_COLOR, value)

    ## PROXIMITY
    @property
    def proximity(self) -> int:
        """Proximity value: 0-255
        lower values are farther, higher values are closer"""
        return self._read8(_APDS9960_PDATA)

    ## GESTURE DETECTION
    # pylint: disable-msg=too-many-branches,too-many-locals,too-many-statements
    # Yes, that's a lot of pylint disabling, but breaking this up eats a lot of memory on import
    def gesture(self) -> int:
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
                if dataset_count == 0:
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

        return gesture_found

    ## COLOR
    @property
    def color_data_ready(self) -> int:
        """Color data ready flag.  zero if not ready, 1 is ready"""
        return self._read8(_APDS9960_STATUS) & 0x01

    @property
    def color_data(self) -> Tuple[int, int, int, int]:
        """Tuple containing r, g, b, c values"""
        return (
            self._color_data16(_APDS9960_CDATAL + 2),
            self._color_data16(_APDS9960_CDATAL + 4),
            self._color_data16(_APDS9960_CDATAL + 6),
            self._color_data16(_APDS9960_CDATAL),
        )

    # method for reading and writing to I2C
    def _write8(self, command: int, abyte: int) -> None:
        """Write a command and 1 byte of data to the I2C device"""
        buf = self.buf2
        buf[0] = command
        buf[1] = abyte
        with self.i2c_device as i2c:
            i2c.write(buf)

    def _writecmdonly(self, command: int) -> None:
        """Writes a command and 0 bytes of data to the I2C device"""
        buf = self.buf2
        buf[0] = command
        with self.i2c_device as i2c:
            i2c.write(buf, end=1)

    def _read8(self, command: int) -> int:
        """Sends a command and reads 1 byte of data from the I2C device"""
        buf = self.buf2
        buf[0] = command
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_end=1)
        return buf[0]

    def _get_bit(self, register: int, mask: int) -> bool:
        """Gets a single bit value from the I2C device's register"""
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        return bool(buf[1] & mask)

    def _set_bit(self, register: int, mask: int, value: bool) -> None:
        """Sets a single bit value in the I2C device's register"""
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        if value:
            buf[1] |= mask
        else:
            buf[1] &= ~mask
        with self.i2c_device as i2c:
            i2c.write(buf, end=2)

    def _get_bits(self, register: int, pos: int, mask: int) -> int:
        """Sets a multi-bit value in the I2C device's register"""
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        return (buf[1] & mask) >> pos

    def _set_bits(self, register: int, pos: int, mask: int, value: int) -> None:
        """Sets a multi-bit value in the I2C device's register"""
        buf = self.buf2
        buf[0] = register
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_start=1)
        buf[1] = (buf[1] & ~mask) | (value << pos)
        with self.i2c_device as i2c:
            i2c.write(buf, end=2)

    def _color_data16(self, command: int) -> int:
        """Sends a command and reads 2 bytes of data from the I2C device
        The returned data is low byte first followed by high byte"""
        buf = self.buf2
        buf[0] = command
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1)
        return buf[1] << 8 | buf[0]
