# Touch Cursor with Display Dimming

<img src=".\pyportal-touch.gif">

Simple demonstration of touch screen impementation and touch activity based screen dimming.

Could be used as a base for building out proper displays, maybe.

## Notes

This is a simple demo implementing a touch cursor and display dimmer on a shared timer.

On touch, the display powers on and a cusror is placed at the touch point. Subsequent touches cause the cursor to move.

After a short delay (`DIMMER_CURSOR_DELAY`) since the most recent touch, the cursor begins dimming, first by desaturating to gray then reducing to black.

After a longer delay (`DIMMER_BACKLIGHT_DELAY`) the display backlight fades to 0.

The timers reset on a touch event.

Calibrations tested on a PyPortal are set up as constants in `simple_display.py`.