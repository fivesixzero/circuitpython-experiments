##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2022 Erik Hess <me@erikhess.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

## NOTE: This is not fully completed/tested yet!
##
## TODO: Reliably determine end of gain wait
## TODO: Reliably handle partial data reads
## TODO: Assure accuracy of ADC count 24-bit int conversion
## TODO: Rework error/exception handling

## Relevant docs:

## Datasheet: <https://cdn.sparkfun.com/datasheets/Sensors/ForceFlex/hx711_english.pdf>
## Sigrok Decoder API: <http://sigrok.org/wiki/Protocol_decoder_API>


from common.srdhelper import bitpack
import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'hx711'
    name = 'HX711'
    longname = 'HX711 load cell ADC'
    desc = 'Avia HX711 load cell ADC serial protocol.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = ['hx711']
    tags = ['IC', 'Analog/digital', 'Embedded/industrial', 'Sensor']
    channels = (
        {'id': 'hx_dout', 'name': 'DOUT', 'desc': 'HX711 serial data line'},
        {'id': 'hx_sck', 'name': 'SCK', 'desc': 'HX711 serial clock line'},
    )
    annotations = (
        ('rdy', 'Ready'),             # 0
        ('sof', 'Start of frame'),    # 1
        ('eof', 'End of frame'),      # 2
        ('bit', 'Bit'),               # 3
        ('bitlength', 'Bit Length'),  # 4
        ('pwr-dn', 'Power down'),     # 5
        ('pwr-on', 'Power on'),       # 6
        ('count', 'ADC count'),       # 7
        ('gain', 'Gain'),             # 8
        ('err', 'Error'),             # 9
    )
    annotation_rows = (
        ('bits', 'Bits', (3,)),
        ('bitlengths', 'Bit Lengths', (4,)),
        ('events', 'Events', (0,1,2,5,6)),
        ('adc', 'ADC', (7,)),
        ('gainset', 'Gain Set', (8,)),
        ('errors', 'Errors', (9,)),
    )

    def __init__(self):
        self.samplerate = None
        self.reset()

    def reset(self):
        self.ready = None  # Last ready state flip
        self.power_dn = None # Last power down state flip
        self.power_on = None # Last power on state flip
        self.reset_variables()

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def reset_variables(self):
        self.state = 'IDLE'
        self.rawbits = []  # All bits
        self.bitlengths = []  # All bit lengths
        self.sof = None  # Start of frame
        self.eof = None  # End of frame
        self.start_bit = None  # Start of bit
        self.this_bit = None  # Value of this bit
        self.end_bit = None  # End of bit
        self.gain_end = None # End of gain frame
        self.adc_count = None  # Parsed ADC count
        self.gain = None  # Parsed ADC gain

    def put_ready(self, ready):
        self.put(ready, ready, self.out_ann, [0, ['Ready', 'Rdy', 'R']])

    def put_sof(self):
        self.put(self.sof, self.sof, self.out_ann, [1, ['Start', 'SOF', 'S']])

    def put_eof(self):
        self.put(self.eof, self.eof, self.out_ann, [2, ['End', 'EOF', 'E']])

    def put_bit(self):
        self.put(self.start_bit, self.end_bit, self.out_ann, [3, [str(self.this_bit)]])

    def put_bitlength(self, bitlength):
        self.put(self.start_bit, self.end_bit, self.out_ann, [4, [str(bitlength)]])
    
    def put_power_dn(self):
        self.put(self.power_dn, self.power_dn, self.out_ann, [5, ['Power Down', 'P_DN', 'D']])
    
    def put_power_on(self):
        self.put(self.power_on, self.power_on, self.out_ann, [6, ['Power On', 'P_ON', 'O']])

    def put_adc_count(self):

        if self.adc_count > 0x7FFFFF:  # Handle two's compliment negative numbers
            self.adc_count -= 0x1000000

        self.put(self.sof, self.eof, self.out_ann, [7, [str(self.adc_count)]])

    def put_gain(self):
        self.put(self.eof, self.gain_end, self.out_ann, [8, [str(self.gain)]])

    def put_error(self, start, end, error):
        self.put(start, end, self.out_ann, [9, [str(error)]])

    def handle_bit(self):
        self.rawbits.append(self.this_bit)
        self.adc_count = self.adc_count << 1 | self.this_bit

    def get_samples_per_bit(self):
        if len(self.bitlengths) > 1:
            return sum(self.bitlengths) // len(self.bitlengths)
        elif len(self.bitlengths) == 1:
            return sum(self.bitlengths)
        else:
            raise RuntimeError("Bitlengths is empty! samplerate: {}".format(self.samplerate))

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def decode(self):
        # State machine
        while True:
            if self.state == 'IDLE':
                self.put_error(self.samplenum, self.samplenum, 'IDLE ENTER, len(rawbits) = {}'.format(
                    len(self.rawbits)))
                # Wait for ready state
                self.wait({0: 'f', 0: 'l'})
                if self.matched[0]:
                    self.power_on = self.samplenum
                    self.put_power_on()
                self.state = 'READY'
            elif self.state == 'READY':
                self.wait({1: 'r'})
                self.gain = 0
                self.sof = self.samplenum
                self.put_sof()
                self.start_bit = self.samplenum
                self.adc_count = 0
                self.rawbits = []
                self.bitlengths = []
                self.gain = 0
                self.state = 'START_READING'
            elif self.state == 'START_READING':
                (hx_rx,hx_clk,) = self.wait({1: 'f'})  # Wait for clock-fall to read in bit
                self.this_bit = hx_rx
                self.handle_bit()
                self.state = 'READING'
            elif self.state == 'READING':
                wait_max = self.get_samples_per_bit() * 2
                if (len(self.rawbits) - 1) < 27:
                    self.wait([{'skip': wait_max}, {1: 'r'}])  # Wait for clcok-rise before proceeding to next bit
                    if not self.matched[0]:
                        self.end_bit = self.samplenum
                        self.bitlengths.append(self.end_bit - self.start_bit)
                        self.put_bitlength(self.end_bit - self.start_bit)
                        self.put_bit()
                        self.start_bit = self.samplenum
                        (hx_rx,hx_clk,) = self.wait([{'skip': wait_max}, {1: 'f'}])  # Wait for clock-fall to read in bit
                        if not self.matched[0]:
                            self.this_bit = hx_rx
                            self.handle_bit()
                            if (len(self.rawbits) - 1) == 24:
                                self.eof = self.end_bit
                                self.put_eof()
                                self.put_adc_count()
                        else:
                            # TODO: Handle stuck clock
                            raise RuntimeError("DEBUG: SKIP TIME HIT, INNER READ LOOP")
                    else:
                        # raise RuntimeError("DEBUG: SKIP TIME HIT, MAIN READ STATE")
                        # Handle end of signal
                        self.put_error(self.samplenum, self.samplenum, 'END READ LOOP, len(rawbits) = {}'.format(
                            self.end_bit, len(self.rawbits)))
                        if len(self.rawbits) > 24:
                            # self.put_error(self.samplenum, self.samplenum, 'ENTER GAIN STATE')
                            self.gain = len(self.rawbits) - 24
                            self.gain_end = self.get_samples_per_bit() * self.gain
                            self.put_gain()
                            self.state = 'IDLE'
                            self.reset_variables()
                        else:
                            pass
