# PyPortal OctoPrint Display

<img src=".\pyportal-octoprint.jpg">

Simple display for OctoPrint status and activity.

## Requirements

1. OctoPrint server set up and running
2. Use PrusaSlicer to slice GCode with thumbnails enabled
2. Modified `PrusaSlicerThumbnails` plugin installed on Octoprint server
    * Thumbnail generation only creates PNGs by default, but CircuitPython likes BMPs, so we've just gotta tweak it to create a BMP along with the PNG.
    * Commit: <https://github.com/fivesixzero/OctoPrint-PrusaSlicerThumbnails/commit/dff0451621537171d96726ecd9807f068a742cfc>
3. Readable SD card with at least 15kb free inserted in PyPortal
    * For storage of thumbnails - saves a lot of memory thanks to `OnDiskBitmap`.

## Notes

This was only my second or third project using `displayio` and includes a lot of firsts for me.

* `adafruit_touchscreen` Touch display implementation
    * Includes auto-fading touch cursor and inactivity based screen blanking
* `adafruit_displayio_layout` layout use via `TabLayout`
    * Didn't end up using the other three tabs yet, but it was a fun side experiment
* Fully operational REST API backed `displayio` display
    * Lots of labels!
* DIY `displayio` line graph for temperature history
    * This was fun, only downside is the lack of timeframe selection in the OctoPrint API
    * May look into creating a plugin to provide more controllable temperature history results
* Experimentation with loading BMP files from the filesystem
    * Thumbnail image downloaded to SD card via `PortalBase`'s `wget()` then loaded via `displayio.OnDiskBitmap()`

All of this (so far) fits into memory, although it's been fun to dodge some bullets along the way. Sometimes simply changing a variable has caused pystack exhaustion or memory errors, so regular on-hardware iteration is critical to make sure that new code doesn't cause a problem.

## TODO

1. Test and handle not-connected or no-active-job states
2. ~~Add capability for retrieval and display of current job's thumbnail~~ Done!
3. Investigate options to get broader-timeframe temperature history data points
    * Current API only gets the most recent _x_ data points, which only shows the last few minutes... This isn't really all that useful for a small 16-data-point graph.

## Links

* CircuitPython DisplayIO Layout `TabLayout` Example: <https://github.com/adafruit/Adafruit_CircuitPython_DisplayIO_Layout/blob/main/examples/displayio_layout_tab_layout_touchtest.py>
* OctoPrint API Ref: <https://docs.octoprint.org/en/master/api/index.html>