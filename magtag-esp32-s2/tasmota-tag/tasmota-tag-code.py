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

#######################
### Global Settings ###
#######################

## Logging Settings
### Default log format with time.monotonic(), level, subsystem name, and logged message string
log_format_string = "[{0:<0.3f} {1:5s} {2:4}] - {3}"
### Set either log level to "None" to disable those logs
### Setting log_level to DEBUG also enables additional debug data on display
log_level = logging.DEBUG
# log_level = logging.INFO
# log_level = None
# mqtt_log_level = logging.DEBUG
mqtt_log_level = logging.INFO
# mqtt_log_level = None
### Enable to force logging to filesystem when started on battery
#### Note: Setting this to 'false' will disable logging altogether on battery
log_to_filesystem_on_battery = True

## WiFi Settings
wifi_mac = binascii.hexlify(wifi.radio.mac_address).decode("utf-8")
hostname = "tasmota-tag-{}".format(wifi_mac)

### MQTT Settings
mqtt_keepalive_timeout = 60
mqtt_client_id = hostname

### Loop Settings
loop_delay = 0.1
result_message_delay = 0.5

#####################################################
### INIT STEP 0: MagTag Devices, Logging, Secrets ###
#####################################################

### Set up MagTag battery management/voltage monitor
batt_monitor = AnalogIn(board.BATTERY)

def battery_status(battery_analog_in) -> float:
    """Return the voltage of the battery"""
    return (battery_analog_in.value / 65535.0) * 3.3 * 2

started_up_on_battery = not supervisor.runtime.usb_connected
startup_vbat = battery_status(batt_monitor)

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

## Actually do our logging setup
### Basic logging configuration
if started_up_on_battery:
    if log_to_filesystem_on_battery and log_level:
        ### If we're on battery, set up filesystem logging if we want to
        import storage
        from adafruit_logging.extensions import FileHandler

        storage.remount("/", False)

        tag_log_filepath = "/tag.log"
        mqtt_log_filepath = "/tag.log"
        log = logging.getLogger("tag")
        tag_log_handler = CustomFileHandler(
            tag_log_filepath, "a", log_format_string, log_custom_levels, "tag")
        
        if mqtt_log_level:
            mqtt_log_handler = CustomFileHandler(
                mqtt_log_filepath, "a", log_format_string, log_custom_levels, "mqtt")

        log.addHandler(tag_log_handler)
        log.setLevel(log_level)
    else:
        ### If we don't want filesystem logging or logging in general, just disable it here
        log_level = None
        mqtt_log_level = None
    
        log = logging.getLogger(None)
else:
    ### Only set up console print logging if we're starting up on USB power and if our log level is set
    if log_level:
        tag_log_handler = CustomPrintHandler(log_format_string, log_custom_levels, "tag")
        if mqtt_log_level:
            mqtt_log_handler = CustomPrintHandler(log_format_string, log_custom_levels, "mqtt")

        log = logging.getLogger("tag")
        log.addHandler(tag_log_handler)
        log.setLevel(log_level)
    else:
        log = logging.getLogger(None)

log.info("INIT STARTUP: on battery [{}], voltage [{}]".format(
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

    def set_status(self, power: str, dimmer: str, ct: str, color: str):
        self.power = power
        self.dimmer = dimmer
        self.ct = ct
        self.color = color

    def set_ip(self, ip: str):
        self.ip = ip

    def __repr__(self) -> str:
        return "Bulb [{}], power [{}], dimmer [{}], ct [{}], color [{}], ip [{}]".format(
            self.name, self.power, self.dimmer, self.ct, self.color, self.ip)


## Set up MagTag buttons using keypad
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
    
## Set up MagTag Neopixels
### Init Neopixel power pin and start with pixels enabled for init
neo_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER_INVERTED)
neo_power.switch_to_output()
neo_power.value = True
### Init pixels
neopixels = neopixel.NeoPixel(board.NEOPIXEL, 4, brightness=0.01)
pixel_wifi_status = 3
pixel_init_status = 2
pixel_mqtt_status = 1
pixel_busy_status = 0
### Blink once to confirm that we're alive
neo_power.value = False
neopixels[pixel_wifi_status] = (255,255,255)
neopixels[pixel_init_status] = (255,255,255)
neopixels[pixel_mqtt_status] = (255,255,255)
neopixels[pixel_busy_status] = (255,255,255)
time.sleep(0.25)
neopixels[pixel_wifi_status] = (0,0,0)
neopixels[pixel_init_status] = (0,0,0)
neopixels[pixel_mqtt_status] = (0,0,0)
neopixels[pixel_busy_status] = (0,0,0)
neo_power.value = True

## Load Secrets file to get wifi/MQTT broker details and bulb topic names to track
secrets_failed = False
try:
    from secrets import secrets

    ### Validate that required secrets data is present and not set to defaults
    if not secrets["ssid"] or secrets["ssid"] == "" or secrets["ssid"] == "wifi_ssid_here":
        log.critical("Valid SSID not present in secrets")
        secrets_failed = True
    if not secrets["password"] or secrets["password"] == "" or secrets["password"] == "wifi_password_here":
        log.critical("Valid network password not present in secrets")
        secrets_failed = True
    if not secrets["mqtt_broker"] or secrets["mqtt_broker"] == "" or secrets["mqtt_broker"] == "mqtt_broker_ip_here":
        log.critical("Valid broker address not present in secrets")
        secrets_failed = True
    if not secrets["mqtt_port"] or (not isinstance(secrets["mqtt_port"], int)):
        log.critical("Valid broker port not present in secrets")
        secrets_failed = True
    if not secrets["mqtt_user"] or secrets["mqtt_user"] == "" or secrets["mqtt_user"] == "mqtt_username_here":
        log.critical("Valid broker user not present in secrets")
        secrets_failed = True
    if not secrets["mqtt_password"] or secrets["mqtt_password"] == "" or secrets["mqtt_password"] == "mqtt_password_here":
        log.critical("Valid broker password not present in secrets")
        secrets_failed = True
    if not secrets["bulbs"] or len(secrets["bulbs"]) == 0:
        log.critical("Valid bulb name list not present in secrets")
        secrets_failed = True

except (NameError, ImportError) as e:
    log.critical("Error loading secrets.py: {} {}".format(type(e).__name__, e))
    secrets_failed = True

if secrets_failed:
    log.critical("WiFi secrets, broker details, and bulb topic names are kept in secrets.py, please add them there!")
    ### Refresh display with error information and halt
    exception_splash = displayio.Group()
    board.DISPLAY.show(exception_splash)
    ex_font = terminalio.FONT
    ex_bg_bitmap = displayio.Bitmap(board.DISPLAY.width, board.DISPLAY.height, 2)
    ex_bg_palette = displayio.Palette(2)
    ex_bg_palette[0] = 0xFFFFFF
    ex_bg_palette[1] = 0x000000
    ex_bg_sprite = displayio.TileGrid(ex_bg_bitmap, pixel_shader=ex_bg_palette, x=0, y=0)
    exception_splash.append(ex_bg_sprite)
    ex_title_label = label.Label(
        ex_font, text="Error loading data from secrets.py", color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, -1)
    )
    exception_splash.append(ex_title_label)
    ex_line0_label = label.Label(
        ex_font, 
        text="Secets file must contain:",
        color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 23)
    )
    exception_splash.append(ex_line0_label)
    ex_line1_label = label.Label(
        ex_font, 
        text="* network SSID/password",
        color=0x000000,
        anchor_point=(0.0, 0.0), anchored_position=(36, 47)
    )
    exception_splash.append(ex_line1_label)
    ex_line2_label = label.Label(
        ex_font, 
        text="* broker address, port, and user/pass",
        color=0x000000,
        anchor_point=(0.0, 0.0), anchored_position=(36, 59)
    )
    exception_splash.append(ex_line2_label)
    ex_line2_label = label.Label(
        ex_font, 
        text="* list of bulb device names",
        color=0x000000,
        anchor_point=(0.0, 0.0), anchored_position=(36, 71)
    )
    exception_splash.append(ex_line2_label)

    board.DISPLAY.refresh()
    while True:
        neopixels[pixel_mqtt_status] = (255,0,0)
        time.sleep(0.1)
        neopixels[pixel_mqtt_status] = (0,0,0)
        time.sleep(0.1)

############################################
### INIT STEP 1: Connect to WiFi Network ###
############################################

## WiFi Helpers
def check_network(
    secrets_data,
    neopixel_list=None, neopixel_busy_idx=None, pixel_enable_pin=None, pixel_enable_pin_inverted=None,
    start_with_init=False,
    max_network_retries=12, max_blink_cycles=50):

    if neopixel_list and not neopixel_busy_idx:
        neopixel_busy_idx = 3

    if start_with_init:
        try:
            log.info("INIT WIFI: Connecting to [{}], hostname [{}]".format(secrets_data["ssid"], wifi.radio.hostname))
            wifi.radio.connect(secrets_data["ssid"],secrets_data["password"])
            log.info("INIT WIFI: Connected to [{}] successfully, IP [{}], gateway [{}]".format(
                secrets_data["ssid"], wifi.radio.ipv4_address, wifi.radio.ipv4_gateway))
            return True
        except ConnectionError:
            log.warning("INIT WIFI: Initial connection failed, retrying [{}] times".format(max_network_retries))

    try:
        ### Ping the network's gatway to verify connected status 
        gateway_ping = wifi.radio.ping(wifi.radio.ipv4_gateway)
        log.debug("check_network: WiFi connectivity validated, gateway [{}], ping time [{}]".format(
            wifi.radio.ipv4_gateway, gateway_ping))
    except (NameError, AttributeError, ValueError) as e:
        log.warning("check_network: Network error, attempting reconnect to [{}]: {} {}".format(
            secrets_data["ssid"], type(e).__name__, e))
        no_network = True
        network_retries = 0
        while no_network:
            try:
                wifi.radio.connect(secrets_data["ssid"],secrets_data["password"])
                gateway_ping = wifi.radio.ping(wifi.radio.ipv4_gateway)
                log.info("check_network: WiFi reconnect validated, gateway [{}], ping time [{}]".format(
                    wifi.radio.ipv4_gateway, gateway_ping))
                no_network = False
            except (ConnectionError, NameError, AttributeError, ValueError) as e2:
                network_retries += 1
                log.warning("check_network: Error reconnecting to network on attempt [{}/{}]: {} {}".format(
                    network_retries, max_network_retries, type(e2).__name__, e2))

                # Blink pixels while waiting to retry, if we need to
                if neopixel_list:
                    
                    # Power on pixels, if we need to
                    if pixel_enable_pin:
                        pixel_enable_pin.value = True
                    if pixel_enable_pin_inverted:
                        pixel_enable_pin_inverted.value = False
                    
                    blink_cycles = 0
                    while blink_cycles < max_blink_cycles:
                        neopixel_list[neopixel_busy_idx] = (255,0,0)
                        time.sleep(0.1)
                        neopixel_list[neopixel_busy_idx] = (0,0,0)
                        time.sleep(0.1)
                        blink_cycles += 1
                    
                    # Power off pixels, if we need to
                    if pixel_enable_pin:
                        pixel_enable_pin.value = False
                    if pixel_enable_pin_inverted:
                        pixel_enable_pin_inverted.value = True

            # Check if we've hit our max_retries
            if network_retries >= max_network_retries:
                log.warning("check_network: Network [{}] is still inaccessible after [{}] retries".format(
                    secrets_data["ssid"], network_retries))
                raise RuntimeError("Network {} is still inaccessible after {} retries".format(
                    secrets_data["ssid"], network_retries))

## Init WIFI and connect
neo_power.value = False
neopixels[pixel_wifi_status] = (255,255,255)
wifi.radio.hostname = hostname

try:
    check_network(secrets, neopixels, start_with_init=True)
except (RuntimeError, OSError) as e:
    log.critical("Error connecting to wireless network: {} {}".format(type(e).__name__, e))
    log.critical("Check that [{}] is accessible and that credentials are correct".format(
            secrets["ssid"]))
    ### Refresh display with error information and halt
    exception_splash = displayio.Group()
    board.DISPLAY.show(exception_splash)
    ex_font = terminalio.FONT
    ex_bg_bitmap = displayio.Bitmap(board.DISPLAY.width, board.DISPLAY.height, 2)
    ex_bg_palette = displayio.Palette(2)
    ex_bg_palette[0] = 0xFFFFFF
    ex_bg_palette[1] = 0x000000
    ex_bg_sprite = displayio.TileGrid(ex_bg_bitmap, pixel_shader=ex_bg_palette, x=0, y=0)
    exception_splash.append(ex_bg_sprite)
    ex_title_label = label.Label(
        ex_font, text="Error connecting to wireless network", color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, -1)
    )
    exception_splash.append(ex_title_label)
    ex_line0_label = label.Label(
        ex_font, 
        text="network: {}".format(
            secrets["ssid"]),
        color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 23)
    )
    exception_splash.append(ex_line0_label)
    ex_line1_label = label.Label(
        ex_font, text="Check that network is accessible and", color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 47)
    )
    exception_splash.append(ex_line1_label)
    ex_line1_label = label.Label(
        ex_font, text="that the password is correct", color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 59)
    )
    exception_splash.append(ex_line1_label)
    board.DISPLAY.refresh()
    while True:
        neopixels[pixel_wifi_status] = (255,0,0)
        time.sleep(0.1)
        neopixels[pixel_wifi_status] = (0,0,0)
        time.sleep(0.1)

neopixels[pixel_wifi_status] = (0,0,0)

###########################################
### INIT Step 2: Connect to MQTT Broker ###
###########################################

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
    log.info("MQTT Subscribe: topic [{}], granted_qos [{}]".format(topic, granted_qos))

def unsubscribe(mqtt_client, userdata, topic, pid):
    log.info("MQTT Unsubscribe: topic [{}], pid [{}]".format(topic, pid))

def publish(mqtt_client, userdata, topic, pid):
    topic_data = topic_breakdown(topic)
    if topic_data['prefix'] == 'cmnd':
        log.debug("MQTT Publish: Tasmota command, device [{}], op [{}]".format(
            topic_data['device'], topic_data['op']))
    else:
        log.debug("MQTT Publish: topic [{}], pid [{}]".format(topic, pid))
        
def connect(mqtt_client, userdata, flags, rc):
    log.debug("MQTT Connect: Connected, broker [{}]".format(mqtt_client.broker))
    log.debug("MQTT Connect: flags [{}], rc [{}]".format(flags, rc))

def disconnect(mqtt_client, userdata, rc):
    log.debug("MQTT Disconnect: Disconnected, broker [{}]".format(mqtt_client.broker))
    log.debug("MQTT Disconnect: rc [{}]".format(rc))

### Init socket pool for MQTT client
pool = socketpool.SocketPool(wifi.radio)

### Init and configure client with our callbacks
mqtt_client = MQTT.MQTT(
    broker=secrets["mqtt_broker"],
    port=secrets["mqtt_port"],
    username=secrets["mqtt_user"],
    password=secrets["mqtt_password"],
    client_id=mqtt_client_id,
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
    keep_alive=mqtt_keepalive_timeout
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
log.info("INIT MQTT: Connecting to MQTT broker [{}@{}:{}], client_id [{}]".format(
    secrets["mqtt_user"], secrets["mqtt_broker"], secrets["mqtt_port"], mqtt_client_id))

try:
    mqtt_client.connect()
    log.info("INIT MQTT: Connected successfully to MQTT broker!")
except (RuntimeError, OSError) as e:
    log.critical("Error connecting to MQTT server: {}".format(e))
    log.critical("Check that server [{}@{}:{}] is running and accessible".format(
            secrets["mqtt_user"], secrets["mqtt_broker"], secrets["mqtt_port"]))
    ### Refresh display with error information and halt
    exception_splash = displayio.Group()
    board.DISPLAY.show(exception_splash)
    ex_font = terminalio.FONT
    ex_bg_bitmap = displayio.Bitmap(board.DISPLAY.width, board.DISPLAY.height, 2)
    ex_bg_palette = displayio.Palette(2)
    ex_bg_palette[0] = 0xFFFFFF
    ex_bg_palette[1] = 0x000000
    ex_bg_sprite = displayio.TileGrid(ex_bg_bitmap, pixel_shader=ex_bg_palette, x=0, y=0)
    exception_splash.append(ex_bg_sprite)
    ex_title_label = label.Label(
        ex_font, text="Error connecting to MQTT server", color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, -1)
    )
    exception_splash.append(ex_title_label)
    ex_line0_label = label.Label(
        ex_font, 
        text="network: {}".format(
            secrets["ssid"]),
        color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 23)
    )
    exception_splash.append(ex_line0_label)
    ex_line1_label = label.Label(
        ex_font, 
        text="broker: {}@{}:{}".format(
            secrets["mqtt_user"], secrets["mqtt_broker"], secrets["mqtt_port"]),
        color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 35)
    )
    exception_splash.append(ex_line1_label)
    ex_line2_label = label.Label(
        ex_font, text="[{}] {}".format(type(e).__name__, e), color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 47)
    )
    exception_splash.append(ex_line2_label)
    ex_line3_label = label.Label(
        ex_font, text="Check that broker is online and reachable".format(type(e).__name__, e), color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 71)
    )
    exception_splash.append(ex_line3_label)
    ex_line4_label = label.Label(
        ex_font, text="before reseting MagTag".format(type(e).__name__, e), color=0x000000,
        anchor_point=(0.5, 0.0), anchored_position=(board.DISPLAY.width/2, 83)
    )
    exception_splash.append(ex_line4_label)
    board.DISPLAY.refresh()
    while True:
        neopixels[pixel_mqtt_status] = (255,0,0)
        time.sleep(0.1)
        neopixels[pixel_mqtt_status] = (0,0,0)
        time.sleep(0.1)

## End MQTT Setup
neopixels[pixel_init_status] = (0,0,0)

##############################################
### INIT Step 3: Get Initial Device States ###
##############################################

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
#### Note: this needs to be set up after the bulbs list, which is why it isn't being done earlier
def message(mqtt_client, topic, message):
    topic_data = topic_breakdown(topic)
    if topic_data["prefix"] == "stat":
        bulbname = topic_data["device"]
        ## Handle 'STATUS5' (network status) message
        if topic_data["op"] == "STATUS5":
            payload = json.loads(message)["StatusNET"]
            log.debug("MQTT StatusNET payload: {}".format(payload))
            log.info("MQTT StatusNET: device [{}], ip [{}]".format(bulbname, payload['IPAddress']))
            ## Update bulb status information with new data
            bulbs[bulbname].set_ip(payload['IPAddress'])
        ## Handle 'STATUS11' (device status) message
        if topic_data["op"] == "STATUS11":
            payload = json.loads(message)["StatusSTS"]
            log.debug("MQTT StatusSTS payload: {}".format(payload))
            log.info("MQTT StatusSTS: device [{}], power [{}], dimmer [{}], ct [{}], color [{}]".format(
                bulbname, payload['POWER'], payload['Dimmer'], payload['CT'], payload['Color']))
            ## Update bulb status information with new data
            bulbs[bulbname].set_status(payload['POWER'], payload['Dimmer'], payload['CT'], payload['Color'])
        ## Handle 'RESULT' message
        if topic_data["op"] == "RESULT":
            payload = json.loads(message)
            log.debug("MQTT RESULT payload: {}".format(payload))
            if "POWER" in payload.keys():
                bulbs[bulbname].power = payload["POWER"]
            if "Dimmer" in payload.keys():
                bulbs[bulbname].dimmer = payload["Dimmer"]
            if "CT" in payload.keys():
                bulbs[bulbname].ct = payload["CT"]
            if "Color" in payload.keys():
                bulbs[bulbname].color = payload["Color"]
            log.debug("MQTT RESULT: [{}] [{}]".format(bulbname, bulbs[bulbname]))
    else:
        payload = json.loads(message)
        log.debug("MQTT Unhandled, topic [{}], payload: {}".format(topic, payload))

mqtt_client.on_message = message

### MQTT Client helpers/wrappers

def retrieve_messages(
    mqtt, 
    socket_timeout=1.0,
    neopixel_list=None, 
    mqtt_pixel_busy_idx=1,
    wifi_pixel_busy_idx=3, 
    pixel_enable_pin=None, 
    pixel_enable_pin_inverted=None,
    quiet=False
    ):
    """Returns true if any new messages were retrieved during mqtt client loop.
    
    If network or MQTT broker connectivity fails, attempts to reconnect if possible"""
    new_messages_came_in = False

    # Only enable and light up neopixels if we're in a 'quiet' state
    if neopixel_list and not quiet:
        # Enable pixels if they're not enabled already
        if pixel_enable_pin:
            pixel_enable_pin.value = True
        elif pixel_enable_pin_inverted:
            pixel_enable_pin_inverted.value = False
        
        neopixels[mqtt_pixel_busy_idx] = (255,255,255)

    try:
        rc = mqtt.loop(socket_timeout)
        while rc is not None:
            new_messages_came_in = True
            rc = mqtt.loop(socket_timeout)
    except (MMQTTException, AttributeError, RuntimeError, OSError, ValueError) as e:
        if pixel_enable_pin and not pixel_enable_pin.value:
            pixel_enable_pin.value = True
        elif pixel_enable_pin_inverted and pixel_enable_pin_inverted.value:
            pixel_enable_pin_inverted.value = False

        neopixels[mqtt_pixel_busy_idx] = (255,0,0)
        log.warning("Failed to get data, retrying: {} {}".format(type(e).__name__, e))

        ## Is our network still connected?
        check_network(
            secrets, 
            neopixels, 
            neopixel_busy_idx=wifi_pixel_busy_idx, 
            pixel_enable_pin_inverted=pixel_enable_pin_inverted)

        ## Our network looks good, but what about our MQTT server?
        try:
            mqtt.ping()
        except (OSError, MMQTTException, AttributeError, RuntimeError ) as mqtt_e:
            log.warning("MQTT server not responding: {} {}".format(type(mqtt_e).__name__, mqtt_e))
            no_mqtt = True
            mqtt_retries = 0
            while no_mqtt:
                neopixels[mqtt_pixel_busy_idx] = (255,0,0)
                check_network(secrets, neopixels)
                neopixels[mqtt_pixel_busy_idx] = (0,0,0)
                try:
                    mqtt.reconnect(resub_topics=True)
                    mqtt.ping()
                    mqtt.loop(socket_timeout)
                    no_mqtt = False
                except (ValueError, MMQTTException, AttributeError, RuntimeError) as e2:
                    mqtt_retries += 1
                    log.warning("Error reconnecting to MQTT broker on attempt {}: {} {}".format(mqtt_retries, type(e2).__name__, e2))
                    delay_cycles = 50
                    while delay_cycles > 0:
                        neopixels[mqtt_pixel_busy_idx] = (255,0,0)
                        time.sleep(0.1)
                        neopixels[mqtt_pixel_busy_idx] = (0,0,0)
                        time.sleep(0.1)
                        delay_cycles -= 1
                if mqtt_retries >= 12:
                    neopixels[mqtt_pixel_busy_idx] = (0,0,0)
                    raise RuntimeError("MQTT broker is still inaccessible after {} retries".format(mqtt_retries))
        
        neopixels[mqtt_pixel_busy_idx] = (0,0,0)

    if neopixel_list:
        ### Set all pixels to off state
        neopixels.fill((0,0,0))
        ### Disable pixels now that we're done with them
        if pixel_enable_pin and pixel_enable_pin.value:
            pixel_enable_pin.value = False
        elif pixel_enable_pin_inverted and not pixel_enable_pin_inverted.value:
            pixel_enable_pin_inverted.value = True
    
    return new_messages_came_in

## Perform initial state retrieval
log.info("INIT MQTT: Initial data retrieval starting")

## Request status info for all bulbs for initial state
for bulb in bulbs:
    mqtt_client.publish(cmnd_status.format(bulb), '5')
    mqtt_client.publish(cmnd_status.format(bulb), '11')

## Retrieve all new messages
retrieve_messages(
    mqtt_client,
    neopixel_list=neopixels,
    mqtt_pixel_busy_idx=pixel_mqtt_status,
    wifi_pixel_busy_idx=pixel_wifi_status,
    pixel_enable_pin_inverted=neo_power,
    quiet=False)

### Validate that status command replies have been received
max_status_retries = 10
max_status_retry_cycles = 25
status_retry_count = 0
status_retry_cycles = 0
refresh_not_validated = True

## Check that bulb data is fully populated
while refresh_not_validated:
    incomplete_refresh = False
    for bulbname in bulbs:
        if not bulbs[bulbname].power:
            log.warning("INIT Status: Power state not yet set for [{}]".format(bulbname))
            incomplete_refresh = True
        if not bulbs[bulbname].dimmer:
            log.warning("INIT Status: Dimmer state not yet set for [{}]".format(bulbname))
            incomplete_refresh = True
        if not bulbs[bulbname].ip:
            log.warning("INIT Status: IP not set for [{}]".format(bulbname))
            incomplete_refresh = True

    if incomplete_refresh:
        status_retry_count += 1
        log.warning("INIT Status: Status query results not yet received, retry [{}/{}]".format(
            status_retry_count, max_status_retries))

        ## Simply retry message receive, since messages may come in a bit late from some bulbs
        retrieve_messages(
            mqtt_client,
            neopixel_list=neopixels,
            mqtt_pixel_busy_idx=pixel_mqtt_status,
            wifi_pixel_busy_idx=pixel_wifi_status,
            pixel_enable_pin_inverted=neo_power,
            quiet=False)

        ## Routinely ask for statuses in case a bulb missed the last one, can happen on broker restarts
        if status_retry_count >= max_status_retries:
            status_retry_count = 0
            status_retry_cycles += 1
            log.warning("INIT Status: Max status retries hit, status commands are being re-sent, cycle [{}/{}]".format(
                status_retry_cycles, max_status_retry_cycles))
            for bulb in bulbs:
                mqtt_client.publish(cmnd_status.format(bulb), '5')
                mqtt_client.publish(cmnd_status.format(bulb), '11')

        ## Eventually we'll need to give up so that we don't hang here forever
        if status_retry_cycles >= max_status_retry_cycles:
            refresh_not_validated = False
            log.warning("INIT Status: Initial status data retrieval is incomplete but max cycles is met, proceeding anyway")

    else:
        refresh_not_validated = False
        log.info("INIT MQTT: Initial status data retrieval is completed and validated")

## End MQTT init, connect, and status update
neopixels[pixel_mqtt_status] = (0,0,0)

################################################
### INIT STEP 4: Set Up and Populate Display ###
################################################

if neo_power.value:
    neo_power.value = False
neopixels[pixel_busy_status] = (255,255,255)

## Display setup
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
        log.warning("display_refresh: Display refresh too soon, waiting before trying again")
        time.sleep(display.time_to_refresh + 0.1)
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
#### Debug Status Right: vBat Delta since Start
if log_level and log_level == logging.DEBUG:
    status_right_debug_vbat_delta = label.Label(
        font, text="vbat delta: {:0<+7.5f}v".format(0.0), color=0x000000,
        anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height-(14))
    )
    splash.append(status_right_debug_vbat_delta)
else:
    status_right_debug_vbat_delta = None
#### Debug Status Right: Startup vBat
if log_level and log_level == logging.DEBUG:
    status_right_debug_battery = label.Label(
        font, text="startup vBat:  {:0<7.5f}v".format(startup_vbat), color=0x000000,
        anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height-(14+12))
    )
    splash.append(status_right_debug_battery)
#### Debug Status Right: MQTT broker
# if log_level and log_level == logging.DEBUG:
#     status_right_debug_mqtt_broker = label.Label(
#         font, text="broker: {}:{}".format(secrets["mqtt_broker"], secrets["mqtt_port"]), color=0x000000,
#         anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height-(14+(12*2))
#     )
#     splash.append(status_right_debug_mqtt_broker)
#### Debug Status Right: MQTT user
# if log_level and log_level == logging.DEBUG:
#     status_right_debug_mqtt_id = label.Label(
#         font, text="user: {}".format(secrets["mqtt_user"]), color=0x000000,
#         anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height-(14+(12*3)))
#     )
#     splash.append(status_right_debug_mqtt_id)
#### Debug Status Right: MQTT client_id
# if log_level and log_level == logging.DEBUG:
#     status_right_debug_mqtt_id = label.Label(
#         font, text="cl_id: {}".format(mqtt_client_id), color=0x000000,
#         anchor_point=(1.0, 1.0), anchored_position=(display.width-1, display.height-(14+(12*4)))
#     )
#     splash.append(status_right_debug_mqtt_id)
#### Debug Status Left: Initial Battery
if log_level and log_level == logging.DEBUG:
    status_left_debug_ip = label.Label(
        font, text="tag ip:  {}".format(wifi.radio.ipv4_address), color=0x000000,
        anchor_point=(0.0, 1.0), anchored_position=(1, display.height-14)
    )
    splash.append(status_left_debug_ip)
#### Debug Status Left: MAC address
if log_level and log_level == logging.DEBUG:
    status_left_debug_mac = label.Label(
        font, text="tag mac: {}".format(wifi_mac), color=0x000000,
        anchor_point=(0.0, 1.0), anchored_position=(1, display.height-(14+12))
    )
    splash.append(status_left_debug_mac)

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
  if log_level and log_level == logging.DEBUG:
    device_label = label.Label(
        font, text="{} [{}]".format(name, bulbs[name].ip), color=0x000000, 
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
    
## Re-check and set a new startup_vbat if our first was > 5v, since that's not right
if log_level and log_level == logging.DEBUG:
    startup_vbat = battery_status(batt_monitor)
    status_right_debug_battery.text = "startup vBat:  {:0<7.5f}v".format(startup_vbat)

status_left.text = "Up: {:>7.2f} min".format(time.monotonic() / 60)
display_refresh()
neopixels[pixel_busy_status] = (0,0,0)

#############################################
### INIT COMPLETE: Prepare and Begin Loop ###
#############################################

## Turn off Neopixel power and set pixels to 0 before starting loop to save power
neopixels.fill((0,0,0))
neo_power.value = True

## Primary Program Loop
log.info("INIT COMPLETE: Starting loop, loop_delay [{}], result_message_delay [{}]".format(loop_delay, result_message_delay))
last_receive_time = time.monotonic()
while True:
    
    ######################################
    ### Loop Step 0: Display Busy Wait ###
    ######################################

    if display.busy or display.time_to_refresh > 0.0:
        if neo_power.value:
            neo_power.value = False
        neopixels[pixel_busy_status] = (255,255,255)

        log.info("loop DISPLAY: Display busy, waiting {} sec before starting loop".format(display.time_to_refresh))
        time.sleep(display.time_to_refresh + 0.1)

        neopixels[pixel_busy_status] = (0,0,0)
        neo_power.value = True

    #####################################
    ### Loop Step 1: Message Handling ###
    #####################################

    ## Retrieve all new messages
    try:
        new_messages_came_in = retrieve_messages(
            mqtt_client,
            neopixel_list=neopixels,
            mqtt_pixel_busy_idx=pixel_mqtt_status,
            wifi_pixel_busy_idx=pixel_wifi_status,
            pixel_enable_pin_inverted=neo_power,
            quiet=True)

        last_receive_time = time.monotonic()
    except (RuntimeError, OSError) as e:
        log.warning("loop MESSAGES: Error during message retrieval: {} {}".format(type(e).__name__, e))
        log.warning("loop MESSAGES: Last successful retrieval was {} seconds ago".format(time.monotonic() - last_receive_time))

    ## Did our newly received messages result in any state changes?
    new_messages_relevant = False
    if new_messages_came_in:
        log.debug("loop MESSAGES: New messages arrived, checking for state changes")
        ### Cycle through our bulbs list and make sure our indicators match
        for bulbname in bulbnames:
            log.debug("loop MESSAGES: bulb [{}], state [{}]/[{}], dimmer [{}]/[{}]".format(
                bulbname, bulbs[bulbname].power, device_indicators[bulbname].fill,
                 bulbs[bulbname].dimmer, device_bars[bulbname].value))

            ### Check displayed 'on/off' indicator status against up-to-date bulb state
            if bulbs[bulbname].power == 'ON' and not device_indicators[bulbname].fill:
                new_messages_relevant = True
                log.debug("loop MESSAGES:  [{}] power toggled on since last refresh".format(bulbname))
            elif bulbs[bulbname].power == 'OFF' and device_indicators[bulbname].fill:
                new_messages_relevant = True
                log.debug("loop MESSAGES:  [{}] power toggled off since last refresh".format(bulbname))
            
            ### Check displayed 'dimmer' status against up-to-date bulb state
            if bulbs[bulbname].dimmer != device_bars[bulbname].value:
                log.debug("loop MESSAGES:  [{}] dimmer changed on since last refresh".format(bulbname))
                new_messages_relevant = True
                
        if new_messages_relevant:
            log.debug("loop MESSAGES: State change found, setting up display refresh")
        else:
            log.debug("loop MESSAGES: No state changes found, ignoring")

    ###################################
    ### Loop Step 2: Input Handling ###
    ###################################

    ## Init per-loop should-do flags
    should_change_anything = False
    should_toggle = False
    should_dimmer_decrease = False
    should_dimmer_increase = False
    should_just_refresh_display = False
    
    ## Get all new key events
    new_key_events = retrieve_key_events(buttons)

    ## Determine what to do later based on key inputs
    if len(new_key_events) > 0:
        log.debug("loop INPUT: New keypad event count: {}".format(len(new_key_events)))
        for e in new_key_events:
            log.debug("loop INPUT:  Keypad event: {}".format(e))
            if e.pressed and not should_change_anything:
                if e.key_number is 0:
                    log.debug("loop INPUT EVENT:   Toggle bulb power states")
                    should_toggle = True
                elif e.key_number is 1:
                    log.debug("loop INPUT EVENT:   Just refresh display")
                    should_just_refresh_display = True
                elif e.key_number is 2:
                    log.debug("loop INPUT EVENT:   Decrease dimmers")
                    should_dimmer_decrease = True
                elif e.key_number is 3:
                    log.debug("loop INPUT EVENT:   Increase dimmers")
                    should_dimmer_increase = True
                else:
                    log.debug("loop INPUT EVENT UNHANDLED:   {}".format(e))
        should_change_anything = True
        log.debug("loop INPUT: Keypad events handled, toggle [{}], turn_on [{}], turn_off [{}], just_refresh [{}]".format(
            should_toggle,
            should_dimmer_decrease,
            should_dimmer_increase,
            should_just_refresh_display))

    ###################################################
    ### Loop Step 3: Act on Inputs or State Changes ###
    ###################################################

    ## If we have work to do, here's where we do it.
    if should_change_anything or new_messages_relevant:
        if neo_power.value:
            neo_power.value = False

        neopixels[pixel_busy_status] = (0,255,0)

        if should_toggle:
            log.info("loop INPUT: Toggling bulb on/off state")
            for bulbname in bulbnames:
                mqtt_client.publish(cmnd_power.format(bulbname), 'TOGGLE')
        if should_just_refresh_display:
            log.info("loop INPUT: Just refreshing display")
        if should_dimmer_decrease:
            log.info("loop INPUT: Decreasing bulb dimmer")
            for bulbname in bulbnames:
                new_dimmer = int(bulbs[bulbname].dimmer) - 25
                if new_dimmer <= 10:
                    new_dimmer = 10
                mqtt_client.publish(cmnd_dimmer.format(bulbname), str(new_dimmer))
        if should_dimmer_increase:
            log.info("loop INPUT: Increasing bulb dimmer")
            for bulbname in bulbnames:
                new_dimmer = int(bulbs[bulbname].dimmer) + 25
                if new_dimmer > 99:
                    new_dimmer = 99
                mqtt_client.publish(cmnd_dimmer.format(bulbname), str(new_dimmer))

        ## Retrieve all new messages (after a reasonable delay) to make sure our internal state is up to date
        if should_change_anything:
            ### Only sleep for incoming results if we've actually commanded a state change in this loop
            log.debug("loop INPUT: Waiting [{}] sec for command result messages".format(result_message_delay))
            time.sleep(result_message_delay)

        retrieve_messages(
            mqtt_client,
            neopixel_list=neopixels,
            mqtt_pixel_busy_idx=pixel_mqtt_status,
            wifi_pixel_busy_idx=pixel_wifi_status,
            pixel_enable_pin_inverted=neo_power,
            quiet=False)
        
        if neo_power.value:
            neo_power.value = False

        neopixels[pixel_busy_status] = (0,255,255)

        ### Cycle through all bulbs and update display values with fresh data
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
            if log_level and log_level == logging.DEBUG:
                status_right_debug_vbat_delta.text="vbat delta: {:0<+7.5f}v".format(
                    startup_vbat - battery_status(batt_monitor))
        else:
            status_right.text = "USB: {:0<7.5f}v".format(battery_status(batt_monitor))

        status_left.text = "Up: {:>7.2f} min".format(time.monotonic() / 60)
        
        log.info("loop INPUT: Refreshing display")
        neopixels[pixel_busy_status] = (255,255,255)
        display_refresh()
        neopixels[pixel_busy_status] = (0,0,0)
        neo_power.value = True

    ######################################
    ### Loop Step 4: End of Loop Sleep ###
    ######################################

    ## Wait a bit before starting our next loop
    time.sleep(loop_delay)