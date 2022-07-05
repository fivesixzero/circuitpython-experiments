import time
from adafruit_pyportal import PyPortal
import gc

portal = PyPortal()

# Change portal display rotation before display object init
portal.display.rotation = 0

from touch_display import TouchDisplay
display = TouchDisplay(portal)

portal = PyPortal()

portal.display.rotation = 0

from simple_display import SimpleDisplay
display = SimpleDisplay(portal)

ticks = 999
ticks_reset = 1000
while True:
    time.sleep(0.010)
    ticks += 1
    if ticks == ticks_reset:
        ticks = 0
        # print("pre-gc:  {}".format(gc.mem_free()))
        gc.collect()
        # print("post-gc: {}".format(gc.mem_free()))

    touch = display.get_touch()

    if touch:
        if 0 < touch[0] < 100:
            # print(gc.mem_free())
            pass
