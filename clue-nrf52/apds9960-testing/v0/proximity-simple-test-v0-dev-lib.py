## NOTE: This code was written around a heavily modified version of the apds9960 driver that I've been using for testing.
##       Because of this it won't work with the current (or possibly future) APDS driver but the structure should be useful.

import time
import board
import keypad
import digitalio
from adafruit_apds9960.apds9960 import APDS9960

## Set up APDS9960

apds = APDS9960(board.I2C())

apds_int = digitalio.DigitalInOut(board.PROXIMITY_LIGHT_INTERRUPT)
apds_int.switch_to_input(pull = digitalio.Pull.UP)

apds.enable_proximity = True
apds.proximity_interrupt_threshold = (0, 150, 15) # This will set a sensible threshold that will cause an internal interrupt assertion (and a pin assertion, if enabled) if something is within a few centimeters of the sensor for about half a second
apds.enable_proximity_interrupt = True
apds.enable_proximity_saturation_interrupt = True # I have yet to actually see a saturation event in my testing so I'm keeping a close eye on this to see if I can figure out what kinds of events actually cause the analog saturation mentioned in the datasheet.

## Set up A/B buttons for interactivity

butts = (
    board.BUTTON_A,
    board.BUTTON_B
)

buttons = keypad.Keys(butts, value_when_pressed=False, pull=True)
event_buffer = keypad.Event()

BUTTON_A_PRESS = keypad.Event(0, True)
BUTTON_B_PRESS = keypad.Event(1, True)

presses = {
    0: False,
    1: False
}

def get_presses(keys: keypad.Keys):
    presses[0] = False
    presses[1] = False
    while keys.events.get_into(event_buffer):
        if event_buffer == BUTTON_A_PRESS:
            presses[0] = True
        elif event_buffer == BUTTON_B_PRESS:
            presses[1] = True
    return presses

## Print initial status information

print("APDS Status, enable: {}, enable_color: {}, enable_proximity: {}, enable_gesture: {}".format(
    apds.enable,
    apds.enable_color,
    apds.enable_proximity,
    apds.enable_gesture,
    apds.enable_color
))
            
while True:

    new_presses = get_presses(buttons)
    
    if new_presses[0] or new_presses[1]:
        if new_presses[0]:
            apds.clear_proximity_interrupt()
            thresh = apds.proximity_interrupt_threshold
            print("prox int thresholds, low: {}, high: {}, persistence {}".format(thresh[0], thresh[1], thresh[2]))
        elif new_presses[1]:
            apds.enable_proximity_interrupt = not apds.enable_proximity_interrupt
            if not apds.enable_proximity_interrupt:
                apds.clear_interrupt()
                print("clear_all_interrupts")
            

    print("APDS | prox {:3d} | enable_prox: {}, prox_valid: {}, enable_prox_int: {}, prox_int_state: {}, saturated: {}, int pin: {}".format(
        apds.proximity,
        apds.enable_proximity,
        apds._proximity_valid,
        apds.enable_proximity_interrupt,
        apds.proximity_interrupt_state,
        apds.sensor_saturated,
        apds_int.value
    ))

    time.sleep(0.1)