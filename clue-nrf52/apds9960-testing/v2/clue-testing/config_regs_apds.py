from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_apds9960.apds9960 import APDS9960

try:
    # Only used for typing
    from typing import Dict
except ImportError:
    pass

class ConfigRegsAPDS:

    def __init__(self, *, apds: APDS9960=None, i2c_bus=None):
        if not apds:
            if not i2c_bus:
                import board
                i2c = board.I2C()
            self.i2c_device = I2CDevice(i2c, 0x39)
        else:
            self.i2c_device = apds.i2c_device

    config_regs = { 
        "_APDS9960_ENABLE": 0x80,
        "_APDS9960_ATIME": 0x81,
        "_APDS9960_WTIME": 0x83,
        "_APDS9960_AILTIL": 0x84,
        "_APDS9960_AILTH": 0x85,
        "_APDS9960_AIHTL": 0x86,
        "_APDS9960_AIHTH": 0x87,
        "_APDS9960_PILT": 0x89,
        "_APDS9960_PIHT": 0x8B,
        "_APDS9960_PERS": 0x8C,
        "_APDS9960_CONFIG1": 0x8D,
        "_APDS9960_PPULSE": 0x8E,
        "_APDS9960_CONTROL": 0x8F,
        "_APDS9960_CONFIG2": 0x90,
        "_APDS9960_STATUS": 0x93,
        "_APDS9960_POFFSET_UR": 0x9D,
        "_APDS9960_POFFSET_DL": 0x9E,
        "_APDS9960_CONFIG3": 0x9F,
        "_APDS9960_GPENTH": 0xA0,
        "_APDS9960_GEXTH": 0xA1,
        "_APDS9960_GCONF1": 0xA2,
        "_APDS9960_GCONF2": 0xA3,
        "_APDS9960_GOFFSET_U": 0xA4,
        "_APDS9960_GOFFSET_D": 0xA5,
        "_APDS9960_GOFFSET_L": 0xA7,
        "_APDS9960_GOFFSET_R": 0xA9,
        "_APDS9960_GPULSE": 0xA6,
        "_APDS9960_GCONF3": 0xAA,
        "_APDS9960_GCONF4": 0xAB,
        "_APDS9960_GFLVL": 0xAE,
        "_APDS9960_GSTATUS": 0xAF,
    }

    def sorted_reg_dict(self) -> Dict[str, int]:
        return sorted(self.config_regs, key=self.config_regs.get)

    def print_reg_states(self) -> None:
        buf2 = bytearray(2)
        for key in self.sorted_reg_dict():
            reg_val = self._read8(buf2, self.config_regs[key])
            print(" {0:22} 0x{1:02X} | 0x{2:02X} | b{2:08b} | {2:3d}".format(key, self.config_regs[key], reg_val))

    def _read8(self, buf: bytearray, addr: int) -> int:
        buf[0] = addr
        with self.i2c_device as i2c:
            i2c.write_then_readinto(buf, buf, out_end=1, in_end=1)
        return buf[0]