# MACROPAD Hotkeys example: Media and most used apps
#
# This assumes that key apps are pinned at these positions on the Windows taskbar:
#
# Explorer: WIN+2
# VSCode: WIN+7
# Barrier: WIN+1
# Terminal: WIN+6
# Discord: WIN+5

from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keycode

# The "WIN key + Number" trick requires a bit of a delay if the app has multiple windows going, at
# least in Windows 11.
WIN_KEY_DELAY = 0.05

app = {              # REQUIRED dict, must be named 'app'
    'name' : 'Apps', # Application name
    'macros' : [     # List of button macros...
        # COLOR    LABEL    KEY SEQUENCE
        # 1st row ----------
        (0x101010, 'Vol-', [[ConsumerControlCode.VOLUME_INCREMENT]]),
        (0x101010, 'Mute', [[ConsumerControlCode.MUTE]]),
        (0x101010, 'Vol+', [[ConsumerControlCode.VOLUME_INCREMENT]]),
        # 2nd row ----------
        (0x000030, '<<', [[ConsumerControlCode.SCAN_PREVIOUS_TRACK]]),
        (0x000010, '> ||', [[ConsumerControlCode.PLAY_PAUSE]]),
        (0x000030, '>>', [[ConsumerControlCode.SCAN_NEXT_TRACK]]),
        # 3rd row ----------
        (0x101000, 'Explorer', [Keycode.WINDOWS, Keycode.TWO, WIN_KEY_DELAY, -Keycode.TWO, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        (0x200000, 'Stop', [[ConsumerControlCode.STOP]]),
        (0x000000, 'VSCode', [Keycode.WINDOWS, Keycode.SEVEN, WIN_KEY_DELAY, -Keycode.SEVEN, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        # 4th row ----------
        (0x101000, 'Barrier', [Keycode.WINDOWS, Keycode.ONE, WIN_KEY_DELAY, -Keycode.ONE, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        (0x101000, 'CMD', [Keycode.WINDOWS, Keycode.SIX, WIN_KEY_DELAY, -Keycode.SIX, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        (0x101000, 'Discord', [Keycode.WINDOWS, Keycode.FIVE, WIN_KEY_DELAY, -Keycode.FIVE, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        # Encoder button ---
        (0x000000, 'Mute', [[ConsumerControlCode.MUTE]])
    ]
}
