"""
Driver for the Scientific Instruments 9700 temperature controller

for PyVISA 1.8

@author: Holger Graef
"""

import visa

class SI9700:
    def __init__(self, connection):
        self.rm = visa.ResourceManager()
        self.si9700 = self.rm.open_resource(connection)
        self.si9700.write_termination = '\n'
        self.si9700.read_termination = '\n'

        if self.query('*IDN?') != 'Scientific Instruments,9700,0781,1.113':
            raise Exception('Controller does not respond or is incompatible with this driver')
    
    def get_temp(self, channel):
        if channel.upper() not in ['A', 'B']:
            raise Exception('Invalid channel')
        return float(self.ask('T'+channel.upper()+'?')[3:])
    
    def get_heater_output(self):
        return float(self.ask('HTR?')[4:])

    # just wrapping the main functions of self.si9700
    def query(self, q):
        return self.si9700.query(q)
    
    def ask(self, q):
        return self.si9700.query(q)
    
    def write(self, q):
        return self.si9700.write(q)
    
    def read_stb(self):
        return self.si9700.read_stb()
    
    
if __name__ == '__main__':
    tc = SI9700('GPIB::14::INSTR')