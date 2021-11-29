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

# Set up I2C for STEMMA on RP2040 boards
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