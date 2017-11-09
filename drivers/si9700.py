"""
Driver for the Scientific Instruments 9700 temperature controller

Uses PyVISA 1.4

@author: Holger Graef
"""

import visa

class SI9700(visa.Instrument):
    def __init__(self, connection):
        visa.Instrument.__init__(self, connection)
        self.term_chars = '\n'
        if self.ask('*IDN?') != 'Scientific Instruments,9700,0781,1.113':
            raise Exception('Controller does not respond or is incompatible with this driver')
    
    def get_temp(self, channel):
        if channel.upper() not in ['A', 'B']:
            raise Exception('Invalid channel')
        return float(self.ask('T'+channel.upper()+'?')[3:])
    
    def get_heater_output(self):
        return float(self.ask('HTR?')[4:])
