import time
import gc
import board
import displayio
import terminalio
from micropython import const
import adafruit_pyportal
from adafruit_touchscreen import Touchscreen
from adafruit_display_shapes.circle import Circle

BRIGHTNESS_DEFAULT = const(1)
COLOR_CURSOR_DEFAULT = const(0x2222CC)
SIZE_CURSOR_DEFAULT = const(20)
DIMMER_CURSOR_DELAY = const(100)  # Cursor delay in ms
DIMMER_BACKLIGHT_DELAY = const(30000)  # Backlight delay in ms

COLOR_CHANNEL_DIM = const(0x01)
COLOR_ZERO = const(0x000000)
COLOR_ONE = const(0x010101)
COLOR_THRESHOLD_GRAY = const(0x222222)
COLOR_THRESHOLD_SINGLE = const(0x22)

# Manually calibrated on PyPortal
TS_CAL_XMIN_0 = const(8150)
TS_CAL_XMAX_0 = const(58250)
TS_CAL_YMIN_0 = const(10250)
TS_CAL_YMAX_0 = const(55500)

TS_CAL_XMIN_90 = const(10850)
TS_CAL_XMAX_90 = const(54500)
TS_CAL_YMIN_90 = const(6300)
TS_CAL_YMAX_90 = const(56300)

TS_CAL_XMIN_180 = const(6200)
TS_CAL_XMAX_180 = const(56500)
TS_CAL_YMIN_180 = const(8750)
TS_CAL_YMAX_180 = const(53250)

TS_CAL_XMIN_270 = const(9000)
TS_CAL_XMAX_270 = const(52900)
TS_CAL_YMIN_270 = const(8300)
TS_CAL_YMAX_270 = const(58000)

TS_CAL_Z_THRESHOLD = const(8500)

class TouchDisplay():

    def __init__(self, portal: adafruit_pyportal.PyPortal, cursor_color: int = COLOR_CURSOR_DEFAULT):
        self._disp = board.DISPLAY

        self._WIDTH = self._disp.width
        self._HEIGHT = self._disp.height
        self._ROTATION = self._disp.rotation

        self._brightness_default = BRIGHTNESS_DEFAULT
        self._disp.brightness = self._brightness_default

        self._main_group = displayio.Group()
        self._disp.show(self._main_group)

        self._FONT = terminalio.FONT

        if cursor_color:
            self._cursor_color = cursor_color
        else:
            self._cursor_color = None

        # Set up touchscreen based on rotation
        self.init_touchscreen(portal)

        # Clean up after init with a GC for good measure
        gc.collect()

    def init_touchscreen(self, portal = None):
        rotation = portal.display.rotation

        # Set up touchscreen dimmer state vars
        self._last_touch = time.monotonic_ns()
        self._last_touch_val = (0, 0, 0)
        self._touch_time_threshold = DIMMER_CURSOR_DELAY * 1000000
        self._touch_threshold_met = True
        self._screen_blank_threshold = DIMMER_BACKLIGHT_DELAY * 1000000
        self._screen_blank_threshold_met = False
        self._channels = self.get_channels(self._cursor_color)

        if rotation == 0:
            self._ts_cal = ((TS_CAL_XMIN_0, TS_CAL_XMAX_0), (TS_CAL_YMIN_0, TS_CAL_YMAX_0))
            self._ts = Touchscreen(
                board.TOUCH_XL, board.TOUCH_XR, board.TOUCH_YD, board.TOUCH_YU,
                calibration=self._ts_cal,
                size=(self._WIDTH, self._HEIGHT),
                z_threshold=TS_CAL_Z_THRESHOLD)
        if rotation == 90:
            self._ts_cal = ((TS_CAL_XMIN_90, TS_CAL_XMAX_90), (TS_CAL_YMIN_90, TS_CAL_YMAX_90))
            self._ts = Touchscreen(
                board.TOUCH_YU, board.TOUCH_YD, board.TOUCH_XL, board.TOUCH_XR,
                calibration=self._ts_cal,
                size=(self._WIDTH, self._HEIGHT),
                z_threshold=TS_CAL_Z_THRESHOLD)
        if rotation == 180:
            self._ts_cal = ((TS_CAL_XMIN_180, TS_CAL_XMAX_180), (TS_CAL_YMIN_180, TS_CAL_YMAX_180))
            self._ts = Touchscreen(
                board.TOUCH_XR, board.TOUCH_XL, board.TOUCH_YU, board.TOUCH_YD,
                calibration=self._ts_cal,
                size=(self._WIDTH, self._HEIGHT),
                z_threshold=TS_CAL_Z_THRESHOLD)
        if rotation == 270:
            self._ts_cal = ((TS_CAL_XMIN_270, TS_CAL_XMAX_270), (TS_CAL_YMIN_270, TS_CAL_YMAX_270))
            self._ts = Touchscreen(
                board.TOUCH_YD, board.TOUCH_YU, board.TOUCH_XR, board.TOUCH_XL,
                calibration=self._ts_cal,
                size=(self._WIDTH, self._HEIGHT),
                z_threshold=TS_CAL_Z_THRESHOLD)

        if self._cursor_color:
            self._cursor = Circle(
                x0=self._HEIGHT//2, y0=self._HEIGHT//2, r=SIZE_CURSOR_DEFAULT,
                fill=COLOR_ZERO, outline=self._cursor_color, stroke=1)
            self._main_group.append(self._cursor)
        else:
            self._cursor = None
            gc.collect()

        if portal:
            portal.peripherals.touchscreen = None
            gc.collect()
            portal.peripherals.touchscreen = self._ts

    # Touch getter
    def get_touch(self):
        self._last_touch_val = self._ts.touch_point

        if self._last_touch_val:
            self._last_touch = time.monotonic_ns()

            if self._cursor:
                ### Place cursor at touch point ###
                self._cursor.x0 = self._last_touch_val[0]
                self._cursor.y0 = self._last_touch_val[1]

                ### Reset cursor color ###
                self._cursor.outline = self._cursor_color

            ### Reset Dimmer State ###
            self._touch_threshold_met = False
            self._screen_blank_threshold_met = False
            if self._disp.brightness < self._brightness_default:
                self._disp.brightness = self._brightness_default

            # print(self._last_touch_val)

        self.handle_dimmer()

        return self._last_touch_val

    # Dimmer Handler
    def handle_dimmer(self):
        time_since_touch = time.monotonic_ns() - self._last_touch

        ### Determine dimmer state ###
        if not self._touch_threshold_met and time_since_touch > self._touch_time_threshold:
            self._touch_threshold_met = True

        if not self._screen_blank_threshold_met and time_since_touch > self._screen_blank_threshold:
            self._screen_blank_threshold_met = True

        ### Handle cursor and screen dimmer ###
        if self._touch_threshold_met:

            if self._cursor.outline > COLOR_ZERO:
                if self._cursor.outline > COLOR_THRESHOLD_GRAY:
                    # dim1: Desaturate to gray
                    self._channels = self.get_channels(self._cursor.outline)
                    self._dimmer_shift = 0

                    if self._channels[0] > COLOR_THRESHOLD_SINGLE:
                        self._dimmer_shift |= COLOR_CHANNEL_DIM << 16
                    if self._channels[1] > COLOR_THRESHOLD_SINGLE:
                        self._dimmer_shift |= COLOR_CHANNEL_DIM << 8
                    if self._channels[2] > COLOR_THRESHOLD_SINGLE:
                        self._dimmer_shift |= COLOR_CHANNEL_DIM << 16

                    if self._cursor.outline - self._dimmer_shift < 0:
                        self._cursor.outline = COLOR_THRESHOLD_GRAY
                    else:
                        self._cursor.outline -= self._dimmer_shift
                elif self._cursor.outline > COLOR_ONE:
                    # dim1: Gray to black
                    self._cursor.outline -= COLOR_ONE
                elif self._cursor.outline <= COLOR_ONE:
                    # dim3: Final flip to black
                    self._cursor.outline = COLOR_ZERO
            else:
                if self._screen_blank_threshold_met and self._disp.brightness > 0.01:
                    new_brightness = float(self._disp.brightness - 0.01)
                    self._disp.brightness = new_brightness
                elif self._disp.brightness == 0.01:
                    self._disp.brightness = 0.00
                    gc.collect()

    # Dimmer status helpers
    def is_dimmed(self):
        if self._disp.brightness == 0.0:
            return True
        else:
            return False

    def is_cursor_dimmed(self):
        if self._cursor.outline == 0x000000:
            return True
        else:
            return False

    # Color helpers
    def get_channels(self, color_hex: int):
        return (
            (color_hex & 0xFF0000) >> 16,
            (color_hex & 0x00FF00) >> 8,
            color_hex & 0x0000FF
        )
