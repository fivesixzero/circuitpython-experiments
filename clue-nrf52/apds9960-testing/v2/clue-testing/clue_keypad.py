import board
import keypad
import time

BUTTON_A_PRESS = keypad.Event(0, True)
BUTTON_B_PRESS = keypad.Event(1, True)

class ClueKeys:

    def __init__(self):

        butts = (
            board.BUTTON_A,
            board.BUTTON_B
        )

        self.buttons = keypad.Keys(butts, value_when_pressed=False, pull=True)
        self.event_buffer = keypad.Event()

        self.presses = {
            0: False,
            1: False
        }

    def get_presses(self):
        self.presses[0] = False
        self.presses[1] = False
        while self.buttons.events.get_into(self.event_buffer):
            if self.event_buffer == BUTTON_A_PRESS:
                self.presses[0] = True
            elif self.event_buffer == BUTTON_B_PRESS:
                self.presses[1] = True
        return self.presses

    def wait_for_keypress(self):
        while True:
            new_presses = self.get_presses()
            
            if new_presses[0] or new_presses[1]:
                break
            else:
                time.sleep(0.001)