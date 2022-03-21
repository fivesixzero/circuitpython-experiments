import board
import ssl
import socketpool
import wifi
import time
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_minimqtt.adafruit_minimqtt import MMQTTException
import neopixel
import digitalio
import keypad
from analogio import AnalogIn
import json
import re
import terminalio
import displayio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_progressbar.progressbar import HorizontalProgressBar
import adafruit_logging as logging
import supervisor
import binascii

### Logging related variables
log_level = logging.DEBUG
mqtt_log_level = logging.DEBUG
log_to_filesystem_on_battery = True
log_format_string = "[{0:<0.3f} {1:5s} {2:4}] - {3}"
### Loop related variables
loop_delay = 0.1
result_message_delay = 0.5

### Set up MagTag battery management/voltage monitor
batt_monitor = AnalogIn(board.BATTERY)

def battery_status(battery_analog_in) -> float:
    """Return the voltage of the battery"""
    return (battery_analog_in.value / 65535.0) * 3.3 * 2

started_up_on_battery = not supervisor.runtime.usb_connected

## Set up logging

### Custom-string logging handler setup
class CustomPrintHandler():

    _levels = [
        (00, "NOTSET"),
        (10, "DEBUG"),
        (20, "INFO"),
        (30, "WARNING"),
        (40, "ERROR"),
        (50, "CRITICAL"),
    ]

    _format_string = "{0:<0.3f}: {1} - {2}"
    _system = None

    def __init__(self, format_string=_format_string, levels=_levels, system=_system):
        self._format_string = format_string
        self._levels = levels
        self._system = system

    def format(self, log_level: int, message: str) -> str:
        """Generate a timestamped message.

        :param int log_level: the logging level
        :param str message: the message to log

        """

        if self._system:
            return self._format_string.format(
                time.monotonic(), self.level_for(log_level), self._system, message
            )
        else:
            return self._format_string.format(
                time.monotonic(), self.level_for(log_level), message
            )

    def emit(self, log_level: int, message: str):
        """Send a message to the console.

        :param int log_level: the logging level
        :param str message: the message to log

        """
        print(self.format(log_level, message))
    
    def level_for(self, value: int) -> str:
        """Convert a numeric level to the most appropriate name.
        :param int value: a numeric level
        """

        for i in range(len(self._levels)):
            if value == self._levels[i][0]:
                return self._levels[i][1]
            if value < self._levels[i][0]:
                return self._levels[i - 1][1]
        return self._levels[0][1]


class CustomFileHandler(CustomPrintHandler):

    def __init__(self, filepath, mode, format_string, levels, system):
        self.logfile = open(
            filepath, mode, encoding="utf-8"
        )
        super().__init__(format_string, levels, system)

    def close(self):
        """Closes the file"""
        self.logfile.close()

    def format(self, log_level: int, message: str):
        """Generate a string to log
        :param level: The level of the message
        :param msg: The message to format
        """
        return super().format(log_level, message) + "\r\n"

    def emit(self, log_level: int, message: str):
        """Generate the message and write it to the UART.
        :param level: The level of the message
        :param msg: The message to log
        """
        self.logfile.write(self.format(log_level, message))


log_custom_levels = [
        (00, "NOTSET"),
        (10, "DEBUG"),
        (20, "INFO"),
        (30, "WARN"),
        (40, "ERROR"),
        (50, "CRIT"),
    ]

### Actually do our logging setup


## Basic logging configuration
if not started_up_on_battery:
    ## Only set up console print logging if we're starting up on USB power
    tag_log_handler = CustomPrintHandler(log_format_string, log_custom_levels, "tag")
    mqtt_log_handler = CustomPrintHandler(log_format_string, log_custom_levels, "mqtt")

    log = logging.getLogger("tag")
    log.addHandler(tag_log_handler)
    log.setLevel(log_level)
else:
    if log_to_filesystem_on_battery:
        ## If we're on battery, set up filesystem logging if we want to
        import storage
        from adafruit_logging.extensions import FileHandler

        storage.remount("/", False)

        tag_log_filepath = "/tag.log"
        mqtt_log_filepath = "/tag.log"
        log = logging.getLogger("tag")
        tag_log_handler = CustomFileHandler(
            tag_log_filepath, "a", log_format_string, log_custom_levels, "tag")
        mqtt_log_handler = CustomFileHandler(
            mqtt_log_filepath, "a", log_format_string, log_custom_levels, "mqtt")

        log.addHandler(tag_log_handler)
        log.setLevel(log_level)
    else:
        ## If we don't want filesystem logging, just disable it here
        log_level = None
        mqtt_log_level = None
    
        log = logging.getLogger(None)

log.info("INIT: Startup: on battery, [{}], voltage [{}]".format(
    started_up_on_battery, battery_status(batt_monitor)))

class Bulb:
    """Simple container for Tasmota bulb status tracking"""

    def __init__(self, name: str):

        self.name = name
        self.power = 'ON'
        self.dimmer = '0'
        self.ct = '0'
        self.color = '0'
        self.ip = ''

    def set_status(self, power: str, dimmer: str, ct: str, color: str, ip: str=''):
        self.power = power
        self.dimmer = dimmer
        self.ct = ct
        self.color = color

    def set_ip(self, ip: str):
        self.ip = ip

    def __repr__(self) -> str:
        return "Bulb: {} | Power: {}, Dimmer: {}, CT: {}, Color: {}, IP: {}".format(
            self.name, self.power, self.dimmer, self.ct, self.color, self.ip)


## Set up MagTag peripherals
### Set up MagTag buttons using keypad
button_pins = (
    board.BUTTON_A,
    board.BUTTON_B,
    board.BUTTON_C,
    board.BUTTON_D
)

buttons = keypad.Keys(button_pins, value_when_pressed=False, pull=True)

def retrieve_key_events(keys: keypad.Keys):
    """Return a list of new keypad events"""
    new_events = True
    key_events = []
    while new_events:
        event = keys.events.get()
        if event:
            key_events.append(event)
        else:
            new_events = False
    return key_events
    
### Set up MagTag Neopixels
#### Init Neopixel power pin and start with pixels enabled for init
neo_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER_INVERTED)
neo_power.switch_to_output()
neo_power.value = False
#### Init pixels
neopixels = neopixel.NeoPixel(board.NEOPIXEL, 4, brightness=0.01)
pixel_wifi_status = 3
pixel_init_status = 2
pixel_mqtt_status = 1
pixel_busy_status = 0
#### Blink once to confirm that we're alive
neopixels[pixel_wifi_status] = (255,255,255)
neopixels[pixel_init_status] = (255,255,255)
neopixels[pixel_mqtt_status] = (255,255,255)
neopixels[pixel_busy_status] = (255,255,255)
time.sleep(0.25)
neopixels[pixel_wifi_status] = (0,0,0)
neopixels[pixel_init_status] = (0,0,0)
neopixels[pixel_mqtt_status] = (0,0,0)
neopixels[pixel_busy_status] = (0,0,0)
## End MagTag peripheral setup

## Load Secrets file to get wifi/MQTT broker details and bulb topic names to track
try:
    from secrets import secrets
except ImportError:
    log.error("WiFi secrets, broker details, and bulb topic names are kept in secrets.py, please add them there!")
    raise

## Init WIFI and connect
neopixels[pixel_wifi_status] = (255,255,255)
log.info("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
log.info("Connected to %s!" % secrets["ssid"])
neopixels[pixel_wifi_status] = (0,0,0)

## Set up MQTT
neopixels[pixel_init_status] = (255,255,255)
### Tasmota MQTT Helpers
def topic_breakdown(topic_string):
    topic_expression = "([^/]*)/([^/]*)/([^/]*)"
    topic_re = re.search(topic_expression, topic_string)
    topic = {}
    topic['topic'] = topic
    topic['prefix'] = topic_re.group(1)
    topic['device'] = topic_re.group(2)
    topic['op'] = topic_re.group(3)
    return topic

### MQTT Client Callbacks
def subscribe(mqtt_client, userdata, topic, granted_qos):
    log.info("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    log.info("Unsubscribed from {0} with PID {1}".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    topic_data = topic_breakdown(topic)
    if topic_data['prefix'] == 'cmnd':
        log.debug("cmnd: {} -> Op: {}".format(topic_data['device'], topic_data['op']))
    else:
        log.debug("Published to {0} with PID {1}".format(topic, pid))
        
def connect(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    log.info("Connected to MQTT Broker!")
    log.debug("Flags: {0}, RC: {1}".format(flags, rc))

def disconnect(client, userdata, rc):
    # This method is called when the client disconnects
    # from the broker.
    log.info("Disconnected from MQTT Broker!")

### Init socket pool for MQTT client
pool = socketpool.SocketPool(wifi.radio)

### Generate client ID based on this device's WiFi MAC address
mqtt_client_id = "tasmota-tag-{}".format(binascii.hexlify(wifi.radio.mac_address).decode("utf-8"))

log.info("Connecting to MQTT broker: client-id [{}]".format(mqtt_client_id))

### Init and configure client with our callbacks
mqtt_client = MQTT.MQTT(
    broker=secrets["mqtt_broker"],
    port=secrets["mqtt_port"],
    username=secrets["mqtt_user"],
    password=secrets["mqtt_password"],
    client_id=mqtt_client_id,
    socket_pool=pool,
    # client_id=secrets["mqtt_client_id"],
    ssl_context=ssl.create_default_context(),
    keep_alive=120
)

### Set up the MQTT client callbacks we built earlier
mqtt_client.on_connect = connect
mqtt_client.on_disconnect = disconnect
mqtt_client.on_subscribe = subscribe
mqtt_client.on_unsubscribe = unsubscribe
mqtt_client.on_publish = publish

### Init MQTT system logging, only if a log level is set
if mqtt_log_level:
    mqtt_client.enable_logger(logging, mqtt_log_level)
    if mqtt_log_handler:
        mqtt_client.logger.addHandler(mqtt_log_handler)

### Connect to MQTT broker
log.info("Connecting to MQTT broker as user [{}] at [{}:{}]".format(
    secrets["mqtt_user"], secrets["mqtt_broker"], secrets["mqtt_port"]))
mqtt_client.connect()
log.info("Connected successfully to MQTT broker!")
## End MQTT Setup
neopixels[pixel_init_status] = (0,0,0)

neopixels[pixel_mqtt_status] = (255,255,255)
## Tasmota Device Control
### Define Bulb Names
bulbnames = secrets['bulbs']

### Define Topics for Bulbs
wild_tele = "tele/{}/+"
wild_cmnd = "cmnd/{}/+"
wild_stat = "stat/{}/+"

### Define Commands for Bulbs
cmnd_power = "cmnd/{}/POWER"
cmnd_dimmer = "cmnd/{}/Dimmer"
cmnd_ct = "cmnd/{}/CT"
cmnd_color = "cmnd/{}/Color"
cmnd_status = "cmnd/{}/STATUS"

### Init internal bulb objects for state tracking, set up MQTT topic list
bulbs = {}
mqtt_topics = []
for bulbname in bulbnames:
    bulbs[bulbname] = Bulb(bulbname)
    mqtt_topics.append(wild_stat.format(bulbname))

### Subscribe to MQTT topics for bulbs
for topic in mqtt_topics:
    mqtt_client.subscribe(topic)

### Set up incoming message handling
def message(mqtt_client, topic, message):
    topic_data = topic_breakdown(topic)
    if topic_data["prefix"] == "stat":
        bulbname = topic_data["device"]
        ## Handle 'STATUS11' message
        if topic_data["op"] == "STATUS11":
            payload = json.loads(message)["StatusSTS"]
            bulbs[bulbname].set_status(payload['POWER'], payload['Dimmer'], payload['CT'], payload['Color'])
            log.debug("MQTT Result: {}".format(bulbs[bulbname]))
        if topic_data["op"] == "STATUS5":
            payload = json.loads(message)["StatusNET"]
            bulbs[bulbname].set_ip(payload['IPAddress'])
        ## Handle 'RESULT' message
        if topic_data["op"] == "RESULT":
            payload = json.loads(message)
            if "POWER" in payload.keys():
                bulbs[bulbname].power = payload["POWER"]
            if "Dimmer" in payload.keys():
                bulbs[bulbname].dimmer = payload["Dimmer"]
            if "CT" in payload.keys():
                bulbs[bulbname].ct = payload["CT"]
            if "Color" in payload.keys():
                bulbs[bulbname].color = payload["Color"]
            log.debug("MQTT Result: {}".format(bulbs[bulbname]))

mqtt_client.on_message = message

### MQTT Client helpers/wrappers

def retrieve_messages(mqtt, socket_timeout=1.0, pixels=True):
    """Returns true if any new messages were retrieved during mqtt client loop"""
    new_messages_came_in = False

    if pixels:
        # Enable pixels if they're not enabled already
        if neo_power:
            neo_power.value = False
        
        neopixels[pixel_mqtt_status] = (255,255,255)

    try:
        rc = mqtt.loop(socket_timeout)
        while rc is not None:
            new_messages_came_in = True
            rc = mqtt.loop(socket_timeout)
    except (ValueError, MMQTTException, RuntimeError) as e:
        log.warning("Failed to get data, retrying", e)
        wifi.reset()
        mqtt.reconnect()

    if pixels:
        neopixels[pixel_mqtt_status] = (0,0,0)

        neo_power.value = False
    
    return new_messages_came_in

## Perform initial state retrieval
log.info("Initial data retrieval starting")

## Request status info for all bulbs for initial state
for bulb in bulbs:
    mqtt_client.publish(cmnd_status.format(bulb), '5')
    mqtt_client.publish(cmnd_status.format(bulb), '11')

## Retrieve all new messages
retrieve_messages(mqtt_client)
log.info("Initial data retrieval is complete")

## End MQTT init, connect, and status update
neopixels[pixel_mqtt_status] = (0,0,0)

## Display setup
neopixels[pixel_busy_status] = (255,255,255)
display = board.DISPLAY
font = terminalio.FONT

def display_refresh():
    """Helper for refreshing e-ink display"""
    if display.busy:
        time.sleep(display.time_to_refresh)

    try:
        display.refresh()
        while display.busy:
            pass
    except RuntimeError:
        log.warning("Display refresh too soon, waiting before trying again")
        time.sleep(2)
        display.refresh()
        while display.busy:
            pass

## Build displayio layout
### Basics
splash = displayio.Group()
display.show(splash)
### Background and Dividing Lines
bg_bitmap = displayio.Bitmap(display.width, display.height, 2)
bg_palette = displayio.Palette(2)
bg_palette[0] = 0xFFFFFF
bg_palette[1] = 0x000000
bg_sprite = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette, x=0, y=0)
### Title Bar Line
for x in range(0,display.width):
  bg_bitmap[x, 14] = 1
  bg_bitmap[x, display.height - 14] = 1
splash.append(bg_sprite)
### Title/Info Text
title_label = label.Label(
  font, text="Tasmota Bulb MQTT Controller", color=0x000000,
  anchor_point=(0.5, 0.0), anchored_position=(display.width/2, -1)
)
splash.append(title_label)
### Top Status Line
#### Top Status Text
status_center = label.Label(
  font, text=" "*20, color=0x000000,
  anchor_point=(0.5, 1.0), anchored_position=(display.width/2, display.height)
)
splash.append(status_center)
#### Status Right: Battery
status_right = label.Label(
  font, text=" "*10, color=0x000000,
  anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height)
)
splash.append(status_right)
#### Status Left: Time
status_left = label.Label(
  font, text=" "*10, color=0x000000,
  anchor_point=(0.0, 1.0), anchored_position=(1, display.height)
)
splash.append(status_left)
### Device Information
device_indicators = {}
device_labels = {}
device_bars = {}
device_line_y_start = 22
device_line_y_sep = 14
device_indicator_x = 7
device_text_x = 67
line = 0
#### Add Device Lines
for name in bulbnames:
  line += 1
  y_position = device_line_y_start
  if line > 1:
    y_position += device_line_y_sep * (line - 1)
  ## Device On/Off Indiciator
  device_indicator = Circle(device_indicator_x, y_position, 5, fill=None, outline=0x000000)
  splash.append(device_indicator)
  device_indicators[name] = device_indicator
  ## Device Text Label
  if log_level == logging.DEBUG:
    device_label = label.Label(
        font, text="{} [{}]".format(name, bulbs[bulbname].ip), color=0x000000, 
        anchor_point=(0.0, 0.5), anchored_position=(device_text_x, y_position)
    )
  else:
    device_label = label.Label(
        font, text=name, color=0x000000, 
        anchor_point=(0.0, 0.5), anchored_position=(device_text_x, y_position)
    )
  splash.append(device_label)
  device_labels[name] = device_label
  ## Device Brightness Bars
  device_bar = HorizontalProgressBar(
    (15, y_position-5),
    (50, 10),
    bar_color=0x777777,
    outline_color=0x000000,
    fill_color=0xFFFFFF,
    value=5
  )
  splash.append(device_bar)
  device_bars[name] = device_bar
#### End per-device bar setup
## End Display Setup

## Bulb state display init
### Check for new state changes
retrieve_messages(mqtt_client)

### Set initial display values based on initial device states
for bulbname in bulbnames:

    ### Set indicator for bulb power
    if bulbs[bulbname].power == 'ON':
        device_indicators[bulbname].fill = True
    elif bulbs[bulbname].power == 'OFF':
        device_indicators[bulbname].fill = None
    else:
        device_indicators[bulbname].fill = None

    ### Set indicator for bulb dimming
    dimmer = int(bulbs[bulbname].dimmer)
    if dimmer > 99:
        dimmer = 99
    device_bars[bulbname].value = dimmer

## Refresh display before loop
if started_up_on_battery:
    status_right.text = "Batt: {:0<7.5f}v".format(battery_status(batt_monitor))
else:
    status_right.text = "USB: {:0<7.5f}v".format(battery_status(batt_monitor))

status_left.text = "Up: {:>7.2f} min".format(time.monotonic() / 60)
display_refresh()
neopixels[pixel_busy_status] = (0,0,0)

## Primary Program Loop
### Turn off Neopixel power before starting loop to save power
neo_power.value = True

log.info("Starting loop: loop_delay [{}], result_message_delay [{}]".format(loop_delay, result_message_delay))
while True:
    
    ### Step 0: If our display is refreshing at loop start, wait to start the loop until the refresh is complete
    if display.busy:
        neo_power.value = False
        neopixels[pixel_busy_status] = (255,0,0)
        log.warning("loop: Display busy, waiting {} before starting loop".format(display.time_to_refresh))
        time.sleep(display.time_to_refresh + 0.1)
        neopixels[pixel_busy_status] = (0,0,0)
        neo_power.value = True

    ### Step 1: Check for and handle new messages

    ## Retrieve all new messages
    new_messages_came_in = retrieve_messages(mqtt_client, pixels=False)

    ## Did our newly received messages result in any state changes?
    new_messages_relevant = False
    if new_messages_came_in:
        ## Cycle through our bulbs list and make sure our indicators 
        for bulbname in bulbnames:
            # Check displayed 'on/off' indicator status against up-to-date bulb state
            if bulbs[bulbname].power == 'ON' and not device_indicators[bulbname]:
                new_messages_relevant = True
            elif bulbs[bulbname].power == 'OFF' and device_indicators[bulbname]:
                new_messages_relevant = True
            
            # Check displayed 'dimmer' status against up-to-date bulb state
            if bulbs[bulbname].dimmer != device_bars[bulbname].value:
                new_messages_relevant = True

    ### Step 2: Handle keypad events

    ## Init per-loop should-do flags
    should_change_anything = False
    should_toggle = False
    should_dimmer_decrease = False
    should_dimmer_increase = False
    should_just_refresh_display = False
    
    new_key_events = retrieve_key_events(buttons)

    ## Determine what to do later based on key inputs
    if len(new_key_events) > 0:
        log.debug("INPUT: New key event count: {}".format(len(new_key_events)))
        for e in new_key_events:
            log.debug("INPUT:  Key event: {}".format(e))
            if e.pressed and not should_change_anything:
                if e.key_number is 0:
                    should_toggle = True
                elif e.key_number is 1:
                    should_just_refresh_display = True
                elif e.key_number is 2:
                    should_dimmer_decrease = True
                elif e.key_number is 3:
                    should_dimmer_increase = True
        should_change_anything = True
        log.debug("INPUT: Key events handled, states: toggle [{}], turn_on [{}], turn_off [{}], just_refresh [{}]".format(
            should_toggle,
            should_dimmer_decrease,
            should_dimmer_increase,
            should_just_refresh_display))

    ## Step 3: Do the work
    ## If we have work to do, here's where we do it.
    if should_change_anything or new_messages_relevant:
        ### Set our busy status pixel to green to indicate that we're working on something 
        neo_power.value = False
        neopixels[pixel_busy_status] = (0,255,0)

        if should_toggle:
            log.info("INPUT: Toggling bulb on/off state")
            for bulbname in bulbnames:
                mqtt_client.publish(cmnd_power.format(bulbname), 'TOGGLE')
        if should_just_refresh_display:
            log.info("INPUT: Just refreshing display")
        if should_dimmer_decrease:
            log.info("INPUT: Decreasing bulb dimmer")
            for bulbname in bulbnames:
                new_dimmer = int(bulbs[bulbname].dimmer) - 25
                if new_dimmer <= 10:
                    new_dimmer = 10
                mqtt_client.publish(cmnd_dimmer.format(bulbname), str(new_dimmer))
        if should_dimmer_increase:
            log.info("INPUT: Increasing bulb dimmer")
            for bulbname in bulbnames:
                new_dimmer = int(bulbs[bulbname].dimmer) + 25
                if new_dimmer > 99:
                    new_dimmer = 99
                mqtt_client.publish(cmnd_dimmer.format(bulbname), str(new_dimmer))

        ## Retrieve all new messages (after a reasonable delay) to make sure our internal state is up to date
        neopixels[pixel_busy_status] = (255,255,0)
        time.sleep(result_message_delay)
        retrieve_messages(mqtt_client)
        neopixels[pixel_busy_status] = (0,255,255)

        ## Cycle through all bulbs and update values
        for bulbname in bulbnames:

            ## Set indicator for bulb power
            if bulbs[bulbname].power == 'ON':
                device_indicators[bulbname].fill = True
            elif bulbs[bulbname].power == 'OFF':
                device_indicators[bulbname].fill = None
            ## Set indicator for bulb dimming
            device_bars[bulbname].value = int(bulbs[bulbname].dimmer)

        if not supervisor.runtime.usb_connected:
            status_right.text = "Batt: {:0<7.5f}v".format(battery_status(batt_monitor))
        else:
            status_right.text = "USB: {:0<7.5f}v".format(battery_status(batt_monitor))

        status_left.text = "Up: {:>7.2f} min".format(time.monotonic() / 60)
        
        log.info("Refreshing display")
        neopixels[pixel_busy_status] = (255,255,255)
        display_refresh()
        
        ### Turn off our Neopixel to indicate that we're done working
        neopixels[pixel_busy_status] = (0,0,0)
        neo_power.value = True

    ## Wait a bit before starting our next loop
    time.sleep(loop_delay)