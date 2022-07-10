import board
# import gc
import displayio
# import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_pyportal import PyPortal
# from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle
# from adafruit_display_shapes.triangle import Triangle
from adafruit_display_shapes.line import Line
from adafruit_displayio_layout.layouts.tab_layout import TabLayout
from adafruit_display_text.label import Label
from adafruit_progressbar.horizontalprogressbar import HorizontalProgressBar
import adafruit_imageload
# import adafruit_datetime  # Takes a ton of memory - from 53,120 free to ~26,000 free just adding this import :(
# from adafruit_datetime import timedelta
from octoprint_api import OctoprintAPI
import touch_display

TABS_FONT_PATH = "/fonts/Helvetica-Bold-24.bdf"
TITLE_FONT_PATH = "/fonts/Helvetica-Bold-16.bdf"
INFO_FONT_PATH = "/fonts/Arial-Italic-12.bdf"
FIXED_NUMBERS_FONT_PATH = "/fonts/Consolas-20.bdf"
FIXED_NUMBERS_SMALL_FONT_PATH = "/fonts/Consolas-numbers-only-12.bdf"

FONT_TABS = bitmap_font.load_font(TABS_FONT_PATH)
FONT_TITLES = bitmap_font.load_font(TITLE_FONT_PATH)
FONT_INFO = bitmap_font.load_font(INFO_FONT_PATH)
FONT_FIXED_NUMBERS = bitmap_font.load_font(FIXED_NUMBERS_FONT_PATH)
FONT_FIXED_NUMBERS_SMALL = bitmap_font.load_font(FIXED_NUMBERS_SMALL_FONT_PATH)

class OctoDisplay(touch_display.TouchDisplay):

    def __init__(self, portal: PyPortal = None, cursor_color: int = touch_display.COLOR_CURSOR_DEFAULT):

        if not portal:
            portal = PyPortal()

        super().__init__(portal, cursor_color)

        self._api = OctoprintAPI(portal)
        portal.network.connect()

        self._font_tabs = FONT_TABS

        self._tab_active_bmp = "bmps/active_tab_sprite_desaturated_30.bmp"
        self._tab_active_color = 0x228847
        self._tab_inactive_bmp = "bmps/inactive_tab_sprite_desaturated_30.bmp"
        self._tab_inactive_color = 0x14512A

        self._page_names = [
            ("Octo", "Octoprint Status"),
            ("Env", "Environment Status"),
            ("Net", "Net Status"),
            ("Misc", "Misc Details")
        ]

        self._set_up_tab_layout()

    def get_touch(self):
        touch_event = super().get_touch()

        if touch_event:
            # Handle paging changes on touch
            current_page = self._layout.showing_page_index
            self._layout.handle_touch_events(touch_event)
            if current_page != self._layout.showing_page_index:
                print(f"Page changed, old: [{current_page}], new: [{self._layout.showing_page_index}]")
                print(f"Page changed, tab height: [{self._layout.tab_height}]")

            # Handle in-tab touch events
            if self._first_touch and not self._wakeup_touch and touch_event[1] > self._layout.tab_height:
                # TODO: Implement per page touch events

                # Update page if our cursor is hidden and we're on page 0
                self._layout.showing_page_content.update_all()

        return touch_event

    def _set_up_tab_layout(self):
        self._layout = TabLayout(
            x=0,
            y=0,
            display=self._disp,
            tab_text_scale=1,
            custom_font=self._font_tabs,
            showing_tab_spritesheet=self._tab_active_bmp,
            showing_tab_text_color=self._tab_active_color,
            inactive_tab_spritesheet=self._tab_inactive_bmp,
            inactive_tab_text_color=self._tab_inactive_color,
            inactive_tab_transparent_indexes=(0, 1),
            showing_tab_transparent_indexes=(0, 1),
            tab_count=4
        )

        for page in self._page_names:
            # page_group = self._set_up_page(page[1])
            if page[0] == "Octo":
                page_group = OctoprintGroup(page[1], self._api)
                self._octo_page = page_group
            else:
                page_group = BaseGroup(page[1])

            self._layout.add_content(page_group, page[0])

        # add it to the group that is showing on the display
        if self._cursor:
            cursor = self._main_group.pop()

        self._main_group.append(self._layout)

        # If we have a cursor, pop it off the bottom of the stack and drop it on top
        if self._cursor:
            self._main_group.append(cursor)

class BaseGroup(displayio.Group):

    def __init__(self, title_text: str):
        super().__init__()

        self._font_titles = FONT_TITLES

        self._WIDTH = board.DISPLAY.width
        self._HEIGHT = board.DISPLAY.height

        # Add divider line at top of page
        self.line_tabs = Line(x0=0, y0=0, x1=self._WIDTH, y1=0, color=0xAAAAAA)
        self.append(self.line_tabs)

        # Add divider line at bottom of title
        title_bottom_y = 21
        self.line_title = Line(x0=0, y0=title_bottom_y, x1=self._WIDTH, y1=title_bottom_y, color=0xAAAAAA)
        self.append(self.line_title)

        # Add title text
        self.page_title = Label(
            font=self._font_titles,
            scale=1,
            text=title_text,
            anchor_point=(0.5, 0),  #  Cetered
            anchored_position=(self._WIDTH//2, 5),  #  Cetered and down a bit
        )
        self.append(self.page_title)

    def update_all():
        pass

class OctoprintGroup(BaseGroup):

    def __init__(self, title_text: str, api: OctoprintAPI):
        super().__init__(title_text)
        self._api = api

        self._font_titles = FONT_TITLES
        self._font_info = FONT_INFO
        self._font_fixed_numbers = FONT_FIXED_NUMBERS
        self._font_fixed_numbers_small = FONT_FIXED_NUMBERS_SMALL

        self._init_content()
        self.update_all()

    def _init_content(self):

        image, palette = adafruit_imageload.load("bmps/prusaslicer-8-color-4-bit_159x90.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette)
        prusaslicer_thumbnail = displayio.TileGrid(image, pixel_shader=palette, x=160, y=120)
        self.append(prusaslicer_thumbnail)

        # TODO: Implement status text and indicator shapes/labels
        ## Connection status
        # connection_status_indicator = None  # api/connection current/state
        # connection_status_text_label = None  # api/connection current/state

        ## Page divider lines
        page_centerline = Line(x0=160, y0=22, x1=self._WIDTH//2, y1=self._HEIGHT, color=0xFFFFFF)
        self.append(page_centerline)
        status_title_line = Line(x0=0, y0=69, x1=self._WIDTH, y1=69, color=0xFFFFFF)
        self.append(status_title_line)
        status_temps_line = Line(x0=0, y0=120, x1=self._WIDTH, y1=120, color=0xFFFFFF)
        self.append(status_temps_line)

        # Printer Status Title
        self.printer_status_title = Label(  # api/printer state/text
            font=self._font_titles, text="Printer Status")
        self.printer_status_title.anchor_point=(0.5, 0.5)
        self.printer_status_title.anchored_position=((self._WIDTH//2)//2, 34)
        self.append(self.printer_status_title)

        ## Printer Status
        self.printer_status_indicator = Circle(  # api/printer state/flags/??? (printing, ready, etc)
            x0=12, y0=53, r=7, fill=0x222222, stroke=0)
        self.append(self.printer_status_indicator)

        self.printer_status_text_label = Label(  # api/printer state/text
            font=self._font_info, text="unknown")
        self.printer_status_text_label.anchor_point=(0.0, 0.5)
        self.printer_status_text_label.anchored_position=(24, 56)
        self.append(self.printer_status_text_label)

        # Printer Temperatures

        printer_status_temp_bed_title = Label(  # api/printer temperature/bed/actual
            font=self._font_titles, scale=1, text="Bed")
        printer_status_temp_bed_title.anchor_point=(0.5, 0.5)
        printer_status_temp_bed_title.anchored_position=((self._WIDTH//2)//4, 83)
        self.append(printer_status_temp_bed_title)

        printer_status_temp_tool_title = Label(  # api/printer temperature/bed/actual
            font=self._font_titles, scale=1, text="Tool")
        printer_status_temp_tool_title.anchor_point=(0.5, 0.5)
        printer_status_temp_tool_title.anchored_position=(((self._WIDTH//2)//4) * 3, 83)
        self.append(printer_status_temp_tool_title)

        self.printer_status_temp_bed = Label(  # api/printer temperature/bed/actual
            font=self._font_fixed_numbers, scale=1, text="000.0", color=0xFF9811)
        self.printer_status_temp_bed.anchor_point=(0.5, 0.5)
        self.printer_status_temp_bed.anchored_position=((self._WIDTH//2)//4, 105)
        self.append(self.printer_status_temp_bed)
        # printer_status_temp_bed_target = None  # api/printer temperature/bed/target

        self.printer_status_temp_tool = Label(  # api/printer temperature/tool/actual
            font=self._font_fixed_numbers, scale=1, text="000.0", color=0xFF1111)
        self.printer_status_temp_tool.anchor_point=(0.5, 0.5)
        self.printer_status_temp_tool.anchored_position=(((self._WIDTH//2)//4) * 3, 105)
        self.append(self.printer_status_temp_tool)
        # printer_status_temp_tool_target = None  # api/printer temperature/tool/target

        # # Printer Temperatures Graph
        self.temp_graph_x = 0
        self.temp_graph_y = 121
        self.temp_graph_width = 160
        self.temp_graph_height = 89

        self.tool_line_color = 0xFF1111
        self.bed_line_color = 0xFF9811

        self.temp_graph = displayio.Group()

        temp_tool_init_data = [20,30,50,50,100,190,260,260]
        temp_bed_init_data = [20,23,25,30,40,70,90,90]

        temp_tool_graph = self.build_temp_graph(
            self.temp_graph_x, self.temp_graph_y,
            self.temp_graph_width, self.temp_graph_height,
            self.tool_line_color, temp_tool_init_data, 20, 260)

        self.temp_graph.append(temp_tool_graph)

        temp_bed_graph = self.build_temp_graph(
            self.temp_graph_x, self.temp_graph_y,
            self.temp_graph_width, self.temp_graph_height,
            self.bed_line_color, temp_bed_init_data, 20, 260)

        self.temp_graph.append(temp_bed_graph)

        self.append(self.temp_graph)

        # Job Status Title
        self.job_status_title = Label(  # api/printer state/text
            font=self._font_titles, text="Job Status")
        self.job_status_title.anchor_point=(0.5, 0.5)
        self.job_status_title.anchored_position=(((self._WIDTH//2)//2) * 3, 34)
        self.append(self.job_status_title)

        ## Job Status
        progress_bar_y = 48
        progress_bar_height = 16
        self.job_progress_bar = HorizontalProgressBar(
            position=(165, progress_bar_y),
            size=(99, progress_bar_height),
            min_value=0, max_value=100, value=1,
            bar_color=0x229922, outline_color=0x999999, fill_color=0x111111,
            border_thickness=1, margin_size = 1)
        self.append(self.job_progress_bar)

        self.job_progress_percent_string = "{:.1f} %"
        self.job_progress_percent_label = Label(  # api/job progress/completion
            font=self._font_fixed_numbers_small, text=self.job_progress_percent_string.format(100.0))
        self.job_progress_percent_label.anchor_point=(0.5, 0.5)
        self.job_progress_percent_label.anchored_position=(267 + 26, (progress_bar_y + (progress_bar_height // 2)))
        self.append(self.job_progress_percent_label)

        # Job Time Remaining/Total Status

        self.job_time_string = "{:.1f} hr"

        job_time_total_title = Label(
            font=self._font_titles, scale=1, text="Total")
        job_time_total_title.anchor_point=(0.5, 0.5)
        job_time_total_title.anchored_position=((((self._WIDTH//2)//4) * 5) + 3, 83)
        self.append(job_time_total_title)

        self.job_time_total_label = Label(  # api/job progress/printTime  (in seconds)
            font=self._font_fixed_numbers, text=self.job_time_string.format(0.0))
        self.job_time_total_label.anchor_point=(0.5, 0.5)
        self.job_time_total_label.anchored_position=((((self._WIDTH//2)//4) * 5) + 3, 105)
        self.append(self.job_time_total_label)

        job_time_remaining_title = Label(
            font=self._font_titles, scale=1, text="Left")
        job_time_remaining_title.anchor_point=(0.5, 0.5)
        job_time_remaining_title.anchored_position=((((self._WIDTH//2)//4) * 7) - 3, 83)
        self.append(job_time_remaining_title)

        self.job_time_remaining_label = Label(  # api/job progress/printTime  (in seconds)
            font=self._font_fixed_numbers, text=self.job_time_string.format(0.0))
        self.job_time_remaining_label.anchor_point=(0.5, 0.5)
        self.job_time_remaining_label.anchored_position=((((self._WIDTH//2)//4) * 7) - 3, 105)
        self.append(self.job_time_remaining_label)

        # file_estimated_filament_volume = None # api/file/<job_file> gcodeAnalysis/filament/tool0/volume
        # file_estimated_filament_mass = None # api/file/<job_file> gcodeAnalysis/filament/tool0/length

    def update_status(self):
        status_data = self._api.connection_status()

        printer_name = status_data["options"]["printerProfiles"][0]["name"]
        connection_state = status_data["current"]["state"]

        self.printer_status_title.text = printer_name

        # Handle new connection state data
        if connection_state == "Closed":
            self.printer_status_indicator.fill = 0xFF2222
        elif connection_state == "Printing":
            self.printer_status_indicator.fill = 0x22FF22
        elif connection_state == "Ready" or connection_state == "Operational":
            self.printer_status_indicator.fill = 0x22FFFF
            connection_state = "Idle"
        else:
            self.printer_status_indicator.fill = 0xFFFF22

        self.printer_status_text_label.text = connection_state

    def update_temp(self):
        temp_tool = self._api.temp(item="tool0")
        temp_bed = self._api.temp(item="bed")

        current_temp_tool = float(temp_tool)
        current_temp_bed = float(temp_bed)

        # self.printer_status_temp_tool.text = "{:5.2f}°".format(current_temp_tool)
        # self.printer_status_temp_bed.text = "{:4.2f}°".format(current_temp_bed)

        self.printer_status_temp_tool.text = "{:5.2f}".format(current_temp_tool)
        self.printer_status_temp_bed.text = "{:4.2f}".format(current_temp_bed)

    def update_temp_graphs(self):
        for idx in range(0, len(self.temp_graph)):
            self.temp_graph.pop()

        temp_tool_history = self._api.temp_history(item="tool0", limit=17)
        temp_bed_history = self._api.temp_history(item="bed", limit=17)

        temp_tool_graph = self.build_temp_graph(
            self.temp_graph_x, self.temp_graph_y,
            self.temp_graph_width, self.temp_graph_height,
            self.tool_line_color, temp_tool_history, 20, 260)

        temp_bed_graph = self.build_temp_graph(
            self.temp_graph_x, self.temp_graph_y,
            self.temp_graph_width, self.temp_graph_height,
            self.bed_line_color, temp_bed_history, 20, 260)

        self.temp_graph.append(temp_tool_graph)
        self.temp_graph.append(temp_bed_graph)

    def update_job(self):
        job_json = self._api.current_job()
        # job_state_string = job_json['state']
        job_progress_percent = job_json['progress']['completion']
        job_elapsed_sec = job_json['progress']['printTime']
        job_remaining_sec = job_json['progress']['printTimeLeft']

        # job_start_epoch = job_json['job']['date']
        # job_file_display_name = job_json['job']['file']['display']
        # job_file_path = job_json['job']['file']['path']

        # file_data_required = False
        # if file_data_required:
        #     file_json = self._api.get_file_info(job_file_path)

        #     file_date_epoch = file_json['date']

        #     ## Analysis sometimes isn't available on newly uploaded gcode files
        #     try:
        #         gcode_analysis = file_json['gcodeAnalysis']
        #     except:
        #         gcode_analysis = None

        #     if gcode_analysis:
        #         file_filament_volume_total = 0.0
        #         file_filament_length_total = 0.0
        #         for tool in gcode_analysis['filament']:
        #             file_filament_volume_total += float(tool['volume'])
        #             file_filament_length_total += float(tool['length'])

        #         file_dimensions = gcode_analysis['dimensions']
        #         file_printing_area = gcode_analysis['printingArea']
        #         file_estimated_print_time = gcode_analysis['estimatedPrintTime']
        #     else:
        #         file_filament_volume_total = None
        #         file_filament_length_total = None
        #         file_dimensions = None
        #         file_printing_area = None
        #         file_estimated_print_time = None

        #     ## Thumbnails won't be available if a thumbnail generating plugin hasn't been installed
        #     try:
        #         file_thumbnail_path = file_json['thumbnail']
        #     except:
        #         file_thumbnail_path = None

        self.job_progress_bar.value = float(job_progress_percent)
        self.job_progress_percent_label.text = self.job_progress_percent_string.format(job_progress_percent)

        self.job_time_remaining_label.text = self.job_time_string.format(job_remaining_sec / 3600)
        self.job_time_total_label.text = self.job_time_string.format((job_elapsed_sec + job_remaining_sec) / 3600)

    def update_all(self):
        self.update_status()
        self.update_temp()
        self.update_temp_graphs()
        self.update_job()

    def build_temp_graph(self, graph_x, graph_y, graph_width, graph_height, line_color, temp_vals, temp_min, temp_max):
        graph = displayio.Group(x=0, y=0)

        line_count = len(temp_vals) - 1
        line_spacing = round(graph_width / line_count)

        x_vals = list(range(graph_x, line_spacing * line_count, line_spacing))
        x_vals.append(graph_width - 1)

        y_margin = 5

        y_vals = []
        for idx in range(0, len(temp_vals)):
            pct = (temp_vals[idx] - temp_min) / (temp_max - temp_min)
            if pct > 1:
                pct = 1

            y_height = round((graph_height - (y_margin * 2)) * pct)
            y_pos = (graph_height - y_height) + graph_y - y_margin

            y_vals.append(y_pos)

        for idx in range(0, line_count):
            temp_line = Line(
                    x0=x_vals[idx], y0=y_vals[idx],
                    x1=x_vals[idx+1], y1=y_vals[idx+1],
                    color=line_color,
                )

            graph.append(temp_line)

        return graph