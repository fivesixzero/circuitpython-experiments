import board
import time
from adafruit_pyportal import PyPortal
import gc

portal = PyPortal()
portal.display.rotation = 0

from octoprint_display import OctoDisplay
display = OctoDisplay(portal)

ticks_reset = 5 * 60 * 100
ticks = 0
while True:
    time.sleep(0.010)
    ticks += 1

    if ticks == ticks_reset:
        ticks = 0
        print("pre-gc:  {}".format(gc.mem_free()))
        gc.collect()
        print("post-gc: {}".format(gc.mem_free()))

        if display._api.is_printing():
            display._layout.showing_page_content.update_all()
            display._last_touch = display._touch_time_threshold + 1

    touch = display.get_touch()

    if touch:
        if 0 < touch[0] < 100:
            # print(gc.mem_free())
            pass
