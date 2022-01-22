# MACROPAD Hotkeys base: Media and Most Used Sites
#
# This assumes that key apps are pinned at these positions on the Windows taskbar:
#
# Chrome: WIN+3
# Spotify: WIN+4

from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keycode

# The "WIN key + Number" trick requires a bit of a delay if the app has multiple windows going, at
# least in Windows 11.
WIN_KEY_DELAY = 0.05

app = {               # REQUIRED dict, must be named 'app'
    'name' : 'Media', # Application name
    'macros' : [      # List of button macros...
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
        (0x500050, 'Chrome', [Keycode.WINDOWS, Keycode.THREE, WIN_KEY_DELAY, -Keycode.THREE, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        (0x200000, 'Stop', [[ConsumerControlCode.STOP]]),
        (0x004000, 'Spotify', [Keycode.WINDOWS, Keycode.FOUR, WIN_KEY_DELAY, -Keycode.FOUR, WIN_KEY_DELAY, -Keycode.WINDOWS]),
        # 4th row ----------
        (0x100010, 'GH', [Keycode.WINDOWS, Keycode.THREE, WIN_KEY_DELAY, -Keycode.THREE, WIN_KEY_DELAY, -Keycode.WINDOWS, Keycode.CONTROL, Keycode.N, -Keycode.CONTROL, 0.2, 'github.com', Keycode.DELETE, '\n']),
        (0x100010, 'Adafruit', [Keycode.WINDOWS, Keycode.THREE, WIN_KEY_DELAY, -Keycode.THREE, WIN_KEY_DELAY, -Keycode.WINDOWS, Keycode.CONTROL, Keycode.N, -Keycode.CONTROL, 0.2, 'adafruit.com', Keycode.DELETE, '\n']),
        (0x100010, 'DK', [Keycode.WINDOWS, Keycode.THREE, WIN_KEY_DELAY, -Keycode.THREE, WIN_KEY_DELAY, -Keycode.WINDOWS, Keycode.CONTROL, Keycode.N, -Keycode.CONTROL, 0.2, 'digikey.com', Keycode.DELETE, '\n']),
        # Encoder button ---
        (0x000000, 'Mute', [[ConsumerControlCode.MUTE]])
    ]
}
