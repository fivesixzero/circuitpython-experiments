from adafruit_ble.advertising.standard import Advertisement

class LYWSD:

    VALID_NAMES = [
        "LYWSD03MMC",
        "LYWSD02"
    ]

    def __init__(self, advertisement: Advertisement):
        self.short_name = advertisement.short_name
        self.device_name = advertisement.complete_name
        self.address = self.get_address(advertisement)
        self.rssi = advertisement.rssi
        self.tx_power = advertisement.tx_power
        self.appearance = advertisement.appearance

    def __repr__(self):
        return "device_name [{}], short_name [{}], address [{}], rssi [{}], tx_power [{}], appearance [{}]".format(
            self.device_name,
            self.short_name,
            self.address,
            self.rssi,
            self.tx_power,
            self.appearance
        )

    @staticmethod
    def get_address(advertisement: Advertisement):
        return str(advertisement.address).split()[1].rstrip('>').lower()