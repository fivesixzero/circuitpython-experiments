# APDS9960: Adavanced gesture troubleshooting code, written for Adafruit Clue nRF52840
#
# Usage:
#
# Press A to de-assert `GMODE`
# Press B to dump config register states

import board
import gc

i2c = board.I2C()

mem_pre_import, mem_post_import, mem_pre_instantiate, mem_post_instantiate = (0, 0, 0, 0)

gc.collect()
mem_pre_import = gc.mem_free()
from adafruit_apds9960.apds9960 import APDS9960
gc.collect()
mem_post_import = gc.mem_free()

gc.collect()
mem_pre_instantiate = gc.mem_free()
apds = APDS9960(i2c, set_defaults=True)
gc.collect()
mem_post_instantiate = gc.mem_free()
print("MEM Pre-import       | mem_free: {:7}".format(mem_pre_import))
print("MEM Post-import      | mem_free: {:7} | change: {:7}".format(mem_post_import, mem_post_import - mem_pre_import))
print("MEM Post-instantiate | mem_free: {:7} | change: {:7}".format(mem_post_instantiate, mem_post_instantiate - mem_pre_instantiate))

import time
import keypad
import digitalio

apds_int = digitalio.DigitalInOut(board.PROXIMITY_LIGHT_INTERRUPT)
apds_int.switch_to_input(pull = digitalio.Pull.UP)

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

def wait_for_keypress(keys: keypad.Keys):
    while True:
        new_presses = get_presses(buttons)
        
        if new_presses[0] or new_presses[1]:
            break
        else:
            time.sleep(0.001)

## Dump APDS register states to console

# print("Waiting for input before starting")
# wait_for_keypress(buttons)
    
import config_regs

# config_regs.print_reg_states(apds)

## Set up APDS for proximity testing


print("APDS Init | enable: {}, enable_color: {}, enable_proximity: {}, enable_gesture: {}".format(
    apds.enable,
    apds.enable_color,
    apds.enable_proximity,
    apds.enable_gesture
))

apds.gesture_proximity_threshold = 5
apds.gesture_exit_threshold = 100
apds.gesture_exit_persistence = 2
apds.gesture_fifo_threshold = 1
apds.gesture_wait_time = 2
apds.gesture_gain = 1
apds.gesture_pulses = 8
apds.gesture_pulse_length = 1

# apds.proximity_interrupt_threshold = (0, 150, 15)
# apds.enable_proximity_interrupt = True
# apds.enable_proximity_saturation_interrupt = True

apds.enable_proximity = True
apds.enable_gesture = True

print("APDS GCNF | gpenth: {:3d}, gexth: {:3d}, gexpers: {:1d}, gfifoth: {:1d}, gwait: {:1d}".format(
    apds.gesture_proximity_threshold,
    apds.gesture_exit_threshold,
    apds.gesture_exit_persistence,
    apds.gesture_fifo_threshold,
    apds.gesture_wait_time))

# print("Waiting for input before dumping post-setup config")
# wait_for_keypress(buttons)

# config_regs.print_reg_states(apds)

# print("Waiting for input before starting loop")

# wait_for_keypress(buttons)
while True:

    new_presses = get_presses(buttons)
    
    if new_presses[0] or new_presses[1]:
        if new_presses[0]:
            apds._gesture_mode = False
        elif new_presses[1]:
            config_regs.print_reg_states(apds)

    gesture = apds.gesture()