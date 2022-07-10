import adafruit_pyportal

CONNECTION_STATE_URL = "/connection"
PRINTER_STATE_URL = "/printer"
SERVER_STATE_URL = "/server"
SETTINGS_URL = "/settings"
TEMP_HISTORY_TOOL_URL = "/printer/tool"
TEMP_HISTORY_BED_URL = "/printer/bed"
JOB_URL = "/job"
FILE_URL = "/files"

FILAMENT_WEIGHT_URL = "/plugin/filament_scale?command=weight"
SPOOL_WEIGHT_URL = "/plugin/filament_scale?command=spool_weight"
SCALE_TYPE_URL = "/plugin/filament_scale?command=scale_type"

class OctoprintAPI():

    def __init__(self, portal: adafruit_pyportal.PortalBase=None, secrets=None):

        if not secrets:
            from octoprint_secrets import octoprint_secrets as secrets

        self.base_url = secrets['api_base_url']
        self.api_headers = {
            "x-api-key": secrets['api_key']
        }

        if portal:
            self._portal = portal
        else:
            self._portal = adafruit_pyportal.PyPortal()

    def ping(self):
        is_up = True
        try:
            response = self.octo_request(SERVER_STATE_URL)
        except (ConnectionRefusedError, OSError):
            is_up = False

        return is_up

    def server_status(self):
        response = self.octo_request(SERVER_STATE_URL)
        return response.json()

    def connection_status(self):
        response = self.octo_request(CONNECTION_STATE_URL)
        return response.json()

    def printer_status(self):
        response = self.octo_request(PRINTER_STATE_URL)
        return response.json()

    def current_job(self):
        response = self.octo_request(JOB_URL)
        return response.json()

    def temp(self, item="bed"):
        if item == "bed":
            request_url = self.base_url + TEMP_HISTORY_BED_URL
        elif item == "tool0":
            request_url = self.base_url + TEMP_HISTORY_TOOL_URL

        path = [item,"actual"]

        response = self._portal.network.fetch_data(request_url, headers=self.api_headers, json_path=path)

        return response[0]

    def temp_history(self, item="bed", limit=3):
        if item == "bed":
            request_url = self.base_url + TEMP_HISTORY_BED_URL + f"?history=true&limit={limit}"
        elif item == "tool0":
            request_url = self.base_url + TEMP_HISTORY_TOOL_URL + f"?history=true&limit={limit}"

        json = self._portal.network.fetch(request_url, headers=self.api_headers).json()

        temps = []
        for entry in json['history']:
            temps.append(entry[item]['actual'])

        return temps

    # No matter how its done this tends to use way, way too much memory to be useful, unfortunately
    # def temp_history_spread(self, entries, spacing, tool=False, target=False):
    #     limit = entries * spacing
    #     request_url = self.base_url + TEMP_HISTORY_TOOL_URL + f"?history=true&limit={limit}"

    #     if tool:
    #         temp_item = "tool0"
    #     else:
    #         temp_item = "bed"

    #     if target:
    #         temp_type = "target"
    #     else:
    #         temp_type = "actual"

    #     paths = (["history",0,temp_item,temp_type],)
    #     for idx in range(1, entries):
    #         append_path = (["history", idx ,temp_item, temp_type],)
    #         paths = paths + append_path

    #     return self._portal.network.fetch_data(request_url, headers=self.api_headers, json_path=paths)

    def is_printing(self) -> bool:
        ps = self.printer_status()

        if ps['state']['text'] == "printing":
            return True
        else:
            return False

    def get_file_info(self, path: str):
        response = self.octo_request(FILE_URL + "/local/" + path)
        return response.json()

    def get_settings(self):
        response = self.octo_request(SETTINGS_URL)
        return response.json()

    # DEBUG for Filament Scale development in progress
    #
    # def filament_weight(self):
    #     response = self.octo_request(FILAMENT_WEIGHT_URL, apikey=False)
    #     return response

    # def spool_weight(self):
    #     response = self.octo_request(SPOOL_WEIGHT_URL, apikey=False)
    #     return response

    # def scale_type(self):
    #     response = self.octo_request(SCALE_TYPE_URL, apikey=False)
    #     return response

    def octo_request(self, endpoint_url, apikey=True):
        request_url = self.base_url + endpoint_url
        if apikey:
            return self._portal.network.fetch(request_url, headers=self.api_headers)
        else:
            return self._portal.network.fetch(request_url)
