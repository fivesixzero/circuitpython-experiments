## Adafruit Feather nRF52840 Sense all-the-devices demo
##
## https://www.adafruit.com/product/4516
## https://learn.adafruit.com/adafruit-feather-sense/
## https://circuitpython.org/board/feather_bluefruit_sense/
##
## Board has 6 i2c addresses in use:
##
## * 0x1C / 28  : LIS3MDL Magnetometer https://github.com/adafruit/Adafruit_CircuitPython_LIS3MDL
## * 0x39 / 57  : APDS9960 Light/Gesture/Proximity (IRQ on D36) https://github.com/adafruit/Adafruit_CircuitPython_APDS9960
## * 0x44 / 68  : SHT30 Humidity https://learn.adafruit.com/adafruit-sht31-d-temperature-and-humidity-sensor-breakout
## * 0x6A / 106 : LSM6DS33 Gyro + Accel (IRQ on D3) https://github.com/adafruit/Adafruit_CircuitPython_LSM6DS
## * 0x77 / 119 : BMP280 Temp/Pressure https://github.com/adafruit/Adafruit_CircuitPython_BMP280
##
## Other Peripherals
##
## Sound Sensor (PDM): MP34DT01-M: board.MICROPHONE_DATA (D34) is PDM Data, board.MICROPHONE_CLOCK (D35) is PDM clock
##
##
## External Peripherals in Dev Setup
##
## Adafruit FeatherWing Tripler https://www.adafruit.com/product/3417
##
## Adafruit 128x64 OLED FeatherWing https://www.adafruit.com/product/4650
## 
## * 0x3C / 60  : OLED Display
## * Pin 9: Button A
## * Pin 6: Button B
## * Pin 5: Button C
##
## Adafruit NeoKey FeatherWing https://www.adafruit.com/product/4979
##
## Rewired the pins on my dev board so that they don't collide with the display's buttons or an additional NeoKey wing
##
## * Pin 10: NeoPixel
## * Pin 11: Switch B
## * Pin 12: Switch A
##

import board
import displayio
import time
from neopixel import NeoPixel
import countio
from adafruit_lis3mdl import LIS3MDL
from adafruit_lsm6ds.lsm6ds33 import LSM6DS33
from adafruit_apds9960.apds9960 import APDS9960
import adafruit_bmp280
from adafruit_sht31d import SHT31D
from adafruit_displayio_sh1107 import SH1107
import audiobusio
import array
import math
import microcontroller
import terminalio
from adafruit_display_text.label import Label
from adafruit_display_shapes.sparkline import Sparkline
import keypad
import gc

i2c = board.I2C()

## Mag

mag = LIS3MDL(i2c)

## Gyro/Accel

acc = LSM6DS33(i2c)
acc_irq_counter = countio.Counter(board.ACCELEROMETER_GYRO_INTERRUPT)

## Light/Gesture/Color

apds = APDS9960(i2c)
apds.proximity_interrupt_threshold = (0, 100, 4)
apds_irq_counter = countio.Counter(board.PROXIMITY_LIGHT_INTERRUPT)

## Temperature/Pressure/Altitude BMP280

bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
bmp280.mode = adafruit_bmp280.MODE_SLEEP  # Start up in sleep mode

## Humidity/Temperature

sht30 = SHT31D(i2c)

## Microphone

mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA, bit_depth=16)
mic_samples = array.array('H', [0] * 160)

def mean(values):
    return sum(values) / len(values)

def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))

## Helper: IRQ pulse count checker

def count_checker(pulse_counter: countio.Counter) -> int:
    if pulse_counter.count > 0:
        current_count = pulse_counter.count
        pulse_counter.reset
        return current_count
    else:
        return 0

## Buttons

buttons = (
    board.SWITCH, # Built-in user button
    board.D9,     # Display button A
    board.D6,     # Display button B
    board.D5,     # Display button C
    board.D12,    # Neokey A (left)
    board.D11     # Neokey B (right)
)

keys = keypad.Keys(buttons, value_when_pressed=False, pull=True)

def retrieve_key_events(keys: keypad.Keys):
    new_events = True
    key_events = []
    while new_events:
        event = keys.events.get()
        if event:
            key_events.append(event)
        else:
            new_events = False
    return key_events

## Neopixels

pixel_board = NeoPixel(board.NEOPIXEL, 1, brightness=0.1)
pixel_board[0] = (0, 0, 50)
pixels_keys = NeoPixel(board.D10, 2, brightness=0.1)
pixels_keys[0] = (50, 50, 50)
pixels_keys[1] = (50, 50, 50)

## Display

displayio.release_displays()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)

WIDTH = 128
HEIGHT = 62
BORDER = 2

display = SH1107(display_bus, width=WIDTH, height=HEIGHT, rotation=0)

font = terminalio.FONT

splash = displayio.Group()
display.show(splash)

# Background Sprite
bg_palette = displayio.Palette(1)
bg_palette[0] = 0x000000 # Black
fg_palette = displayio.Palette(1)
fg_palette[0] = 0xFFFFFF # White

inner_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 2)
inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=bg_palette, x=BORDER, y=BORDER)
splash.append(inner_sprite)

# Draw some white squares
sm_square_bitmap = displayio.Bitmap(2, 2, 1)
sm_square = displayio.TileGrid(sm_square_bitmap, pixel_shader=fg_palette, x=64, y=60)
splash.append(sm_square)

# Set up Page Numbers text area
page_text = "[{}/{}]"

page_label = Label(font, text=page_text.format(0,0), padding_top=0, padding_bottom=0)
page_label.anchor_point = (1.0, 0.0)
page_label.anchored_position = (128, 0)
splash.append(page_label)

# Set up Page Title text area
title_text = " "*16
title_label = Label(font, text=title_text, padding_top=0, padding_bottom=0)
title_label.anchor_point = (0.0, 0.0)
title_label.anchored_position = (0, 0)
splash.append(title_label)

# Set up Mag Data text area
mag_text = "Magnetometer\nX: {:>+9.4f}\nY: {:>+9.4f}\nZ: {:>+9.4f}"
mag_label = Label(font, text=mag_text.format(0.0, 0.0, 0.0), padding_top=0, padding_bottom=0, line_spacing=0.7)
mag_label.anchor_point = (0.0, 1.0)
mag_label.anchored_position = (0, 60)
mag_label.hidden = True
splash.append(mag_label)

# Set up Gyro Data text area
gyro_text = "Gyro\nX: {:>+6.2f}\nY: {:>+6.2f}\nZ: {:>+6.2f}"
gyro_label = Label(font, text=gyro_text.format(0.0, 0.0, 0.0), padding_top=0, padding_bottom=0, line_spacing=0.7)
gyro_label.anchor_point = (1.0, 1.0)
gyro_label.anchored_position = (128, 60)
gyro_label.hidden = True
splash.append(gyro_label)

# Set up Accel
acc_text = "Accel\nX: {:>+7.2f}\nY: {:>+7.2f}\nZ: {:>+7.2f}"
acc_label = Label(font, text=acc_text.format(0.0, 0.0, 0.0), padding_top=0, padding_bottom=0, line_spacing=0.7)
acc_label.anchor_point = (0.0, 1.0)
acc_label.anchored_position = (0, 60)
acc_label.hidden = True
splash.append(acc_label)

# Set up color/prox/gesture
color_text = "Color\nR: {:4d}\nG: {:4d}\nB: {:4d}\nC: {:4d}"
color_label = Label(font, text=color_text.format(0, 0, 0, 0), padding_top=0, padding_bottom=0, line_spacing=0.7)
color_label.anchor_point = (0.0, 1.0)
color_label.anchored_position = (0, 60)
color_label.hidden = True
splash.append(color_label)

prox_text = "Prox: {:6d}"
prox_label = Label(font, text=prox_text.format(0, 0, 0, 0), padding_top=0, padding_bottom=0, line_spacing=0.7)
prox_label.anchor_point = (0.0, 1.0)
prox_label.anchored_position = (55, 50)
prox_label.hidden = True
splash.append(prox_label)

gesture_text = "Gesture:   {:1d}"
gesture_label = Label(font, text=gesture_text.format(0), padding_top=0, padding_bottom=0, line_spacing=0.7)
gesture_label.anchor_point = (0.0, 1.0)
gesture_label.anchored_position = (55, 60)
gesture_label.hidden = True
splash.append(gesture_label)

# Set up temp/pressure/altitude
temp_text = "Temp:      {:6.2f} C\nPressure: {:7.2f} hPa\nAltitude: {:7.2f} m\nHumidity: {:7.2f} %"
temp_label = Label(font, text=temp_text.format(0.0, 0.0, 0.0, 0.0), padding_top=0, padding_bottom=0, line_spacing=0.7)
temp_label.anchor_point = (0.0, 1.0)
temp_label.anchored_position = (0, 60)
temp_label.hidden = True
splash.append(temp_label)

# Set up PDM microphone label
mic_text = "Audio Level: {:7.2f}"
mic_label = Label(font, text=mic_text.format(0.0, 0.0, 0.0, 0.0), padding_top=0, padding_bottom=0, line_spacing=0.7)
mic_label.anchor_point = (0.0, 1.0)
mic_label.anchored_position = (0, 60)
mic_label.hidden = True
splash.append(mic_label)

mic_sparkline_max_entries = 16
mic_sparkline = Sparkline(
    width=126, height=30,
    max_items=mic_sparkline_max_entries, 
    y_min=0, y_max=400,
    x=1, 
    y=16)
mic_sparkline.hidden = True
mic_sparkline.clear_values()
sparklist = [1] * mic_sparkline_max_entries
mic_sparkline._spark_list = sparklist
splash.append(mic_sparkline)
mic_cycle_count = 0

# Set up internals label
cpu_text = "CPU\nFreq: {:9.1f} MHz\nTemp: {:9.1f} C\nVolts: {:8.3} V\nMem Free: {:5d} bytes"
cpu_label = Label(font, text=cpu_text.format(0.0, 0.0, 0.0, 0), padding_top=0, padding_bottom=0, line_spacing=0.7)
cpu_label.anchor_point = (0.0, 1.0)
cpu_label.anchored_position = (0, 60)
cpu_label.hidden = True
splash.append(cpu_label)


# Prep for Loop and Loop
reverse = False
pause = False
page = 6
page_max = 6
pagechange = True
page_label.text = page_text.format(page, page_max)
gc.collect()
while True:

    ## Handle IRQ events
    acc_irq_events = count_checker(acc_irq_counter)
    apds_irq_events = count_checker(apds_irq_counter)

    if acc_irq_events:
        print("{} accelerometer IRQ events detected".format(acc_irq_events))
    if apds_irq_events:
        print("{} APDS9960 IRQ events detected, threshold: {}, prox: {}".format(apds_irq_events, apds.proximity_interrupt_threshold, apds.proximity))

    ## Handle button/key inputs for page changes and animation pauses
    should_pause = False
    should_page = False
    should_page_to = 0
    new_events = retrieve_key_events(keys)
    if len(new_events) > 0:
        for e in new_events:
            # print(e)
            if e.pressed:  # We only care about pressed keys, not released ones
                # Pause animations
                if e.key_number is 0:
                    if not should_pause:  # Only act on the first event
                        should_pause = True
                        pixel_board[0] = (40, 40, 40)
                # Increment page
                elif e.key_number is 1 or e.key_number is 4:
                    if not should_page:  # Only act on the first event
                        should_page = True
                        should_page_to = page + 1
                        if should_page_to > page_max:
                            should_page_to = page_max
                            pagechange = False
                        else:
                            pagechange = True
                        pixel_board[0] = (0, 0, 50)
                # Decrement page
                elif e.key_number is 3 or e.key_number is 5:
                    if not should_page:  # Only act on the first event
                        should_page = True
                        should_page_to = page - 1
                        if should_page_to <= 0:
                            should_page_to = 1
                            pagechange = False
                        else:
                            pagechange = True
                        pixel_board[0] = (0, 0, 50)

    if should_pause:
        pause = not pause

    if should_page and pagechange:
        if page != should_page_to:
            page = should_page_to
        else:
            pagechange = False

    ## Handle page changes
    if pagechange:
        print("Page changed to page #{}".format(page))
        page_label.text = page_text.format(page, page_max)
        if page == 1:
            title_label.text = "LIS3MDL"
            # Show page 1
            mag_label.hidden = False
            # Hide page 2
            gyro_label.hidden = True
            acc_label.hidden = True
            color_label.hidden = True
            # Hide page 3
            color_label.hidden = True
            prox_label.hidden = True
            gesture_label.hidden = True
            # Hide page 4
            temp_label.hidden = True
            # Hide page 5
            mic_label.hidden = True
            mic_sparkline.hidden = True
            # Hide page 6
            cpu_label.hidden = True
            # Disable page 3 unused sensors/features
            apds.enable_color = False
            apds.enable_proximity = False
            apds.enable_proximity_interrupt = False
            apds.enable_gesture = False
            # Disable page 4 unused sensors/features
            bmp280.mode = adafruit_bmp280.MODE_SLEEP
        elif page == 2:
            title_label.text = "LSM6DS33"
            # Hide page 1
            mag_label.hidden = True
            # Show page 2
            gyro_label.hidden = False
            acc_label.hidden = False
            # Hide page 3
            color_label.hidden = True
            prox_label.hidden = True
            gesture_label.hidden = True
            # Hide page 4
            temp_label.hidden = True
            # Hide page 5
            mic_label.hidden = True
            mic_sparkline.hidden = True
            # Hide page 6
            cpu_label.hidden = True
            # Disable page 3 unused sensors/features
            apds.enable_color = False
            apds.enable_proximity = False
            apds.enable_proximity_interrupt = False
            apds.enable_gesture = False
            # Disable page 4 unused sensors/features
            bmp280.mode = adafruit_bmp280.MODE_SLEEP
        elif page == 3:
            title_label.text = "APDS9960"
            # Hide page 1
            mag_label.hidden = True
            # Hide page 2
            gyro_label.hidden = True
            acc_label.hidden = True
            # Show page 3
            color_label.hidden = False
            prox_label.hidden = False
            gesture_label.hidden = False
            # Hide page 4
            temp_label.hidden = True
            # Hide page 5
            mic_label.hidden = True
            mic_sparkline.hidden = True
            # Hide page 6
            cpu_label.hidden = True
            # Enable Page 3 sensors/features
            apds.enable_color = True
            apds.enable_proximity = True
            apds.enable_proximity_interrupt = True
            apds.enable_gesture = True
            # Disable page 4 unused sensors/features
            bmp280.mode = adafruit_bmp280.MODE_SLEEP
        elif page == 4:
            title_label.text = "BMP280/SHT30"
            # Hide page 1
            mag_label.hidden = True
            # Hide page 2
            gyro_label.hidden = True
            acc_label.hidden = True
            # Hide page 3
            color_label.hidden = True
            prox_label.hidden = True
            gesture_label.hidden = True
            # Show page 4
            temp_label.hidden = False
            # Hide page 5
            mic_label.hidden = True
            mic_sparkline.hidden = True
            # Hide page 6
            cpu_label.hidden = True
            # Disable page 3 unused sensors/features
            apds.enable_color = False
            apds.enable_proximity = False
            apds.enable_proximity_interrupt = False
            apds.enable_gesture = False
            # Enable page 4 unused sensors/features
            bmp280.mode = adafruit_bmp280.MODE_NORMAL
        elif page == 5:
            title_label.text = "PDM Microphone"
            # Hide page 1
            mag_label.hidden = True
            # Hide page 2
            gyro_label.hidden = True
            acc_label.hidden = True
            # Hide page 3
            color_label.hidden = True
            prox_label.hidden = True
            gesture_label.hidden = True
            # Hide page 4
            temp_label.hidden = True
            # Show page 5
            mic_label.hidden = False
            mic_sparkline.hidden = False
            # Hide page 6
            cpu_label.hidden = True
            # Disable page 3 unused sensors/features
            apds.enable_color = False
            apds.enable_proximity = False
            apds.enable_proximity_interrupt = False
            apds.enable_gesture = False
            # Enable page 4 unused sensors/features
            bmp280.mode = adafruit_bmp280.MODE_SLEEP
        elif page == 6:
            title_label.text = "Internals"
            # Hide page 1
            mag_label.hidden = True
            # Hide page 2
            gyro_label.hidden = True
            acc_label.hidden = True
            # Hide page 3
            color_label.hidden = True
            prox_label.hidden = True
            gesture_label.hidden = True
            # Hide page 4
            temp_label.hidden = True
            # Hide page 5
            mic_label.hidden = True
            mic_sparkline.hidden = True
            # Show page 6
            cpu_label.hidden = False
            # Disable page 3 unused sensors/features
            apds.enable_color = False
            apds.enable_proximity = False
            apds.enable_proximity_interrupt = False
            apds.enable_gesture = False
            # Enable page 4 unused sensors/features
            bmp280.mode = adafruit_bmp280.MODE_SLEEP

        pagechange = False

    # Update sensor data and display only if sensors are on the page
    if page == 1:
        # Mag Update
        mag_x, mag_y, mag_z = mag.magnetic
        # print(mag_text.format(mag_x, mag_y, mag_z))
        mag_label.text = mag_text.format(mag_x, mag_y, mag_z)
    elif page == 2:
        # Gyro/Accel Update
        gyro_x, gyro_y, gyro_z = acc.gyro
        # print(gyro_text.format(gyro_x, gyro_y, gyro_z))
        gyro_label.text = gyro_text.format(gyro_x, gyro_y, gyro_z)

        acc_x, acc_y, acc_z = acc.acceleration
        # print(acc_text.format(acc_x, acc_y, acc_z))
        acc_label.text = acc_text.format(acc_x, acc_y, acc_z)

        # Test Gyro/Accel Interrupt Status
        # print("Acc IRQ: Value: {}, Rose: {}, Fell: {}".format(acc_irq_sw.value, acc_irq_sw.rose, acc_irq_sw.fell))
    elif page == 3:
        # Color Update
        color_r, color_g, color_b, color_c = apds.color_data
        color_label.text = color_text.format(color_r, color_g, color_b, color_c)
        # Prox update
        prox_label.text = prox_text.format(apds.proximity)
        # Gesture update
        gesture_label.text = gesture_text.format(apds.gesture())

        # Test APDS Interrupt Status
        # print("APDS IRQ: Value: {}, Rose: {}, Fell: {}".format(apds_irq_sw.value, apds_irq_sw.rose, apds_irq_sw.fell))
    elif page == 4:
        # Temp/Pressure/Altitude Update
        temp_label.text = temp_text.format(bmp280.temperature, bmp280.pressure, bmp280.altitude, sht30.relative_humidity)
    elif page == 5:
        mic_cycle_count += 1
        if mic_cycle_count > 3:
            mic_cycle_count = 0
        # PDM Microphone updates
        mic.record(mic_samples, len(mic_samples))
        magnitude = normalized_rms(mic_samples)
        # print("Mic RMS: {}".format(magnitude))
        mic_label.text = mic_text.format(magnitude)
        # Handle sparklist with care, only updating every x cycles to avoid display issues
        if len(mic_sparkline._spark_list) > mic_sparkline_max_entries:
            mic_sparkline._spark_list.pop(0)
        mic_sparkline._spark_list.append(magnitude)
        if mic_cycle_count is 3:
            mic_sparkline.update()
    elif page == 6:
        cpu_label.text = cpu_text.format(microcontroller.cpu.frequency / 1000 / 1000, microcontroller.cpu.temperature, microcontroller.cpu.voltage, gc.mem_free())

    ## Handle scrolling loop indicator
    ### Move that little box
    if not pause:
        if reverse:
            new_x_2 = sm_square.x + 1
            sm_square.x = new_x_2
            if new_x_2 > 125:
                reverse = False
        else:
            new_x_2 = sm_square.x - 1
            sm_square.x = new_x_2
            if new_x_2 < 0:
                reverse = True
      
    time.sleep(0.005)
    # time.sleep(0.2)