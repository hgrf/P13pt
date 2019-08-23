"""
Driver for theCryoVac TIC 500 temperature controller

for PyVISA 1.8

@author: Damien FRULEUX
"""

import visa


class TIC500:
    def __init__(self, connection):
        self.rm = visa.ResourceManager()
        self.tic500 = self.rm.open_resource(connection)
        self.tic500.write_termination = '\n'
        self.tic500.read_termination = '\n'

        if self.query('*IDN?').startswith ("'CryoVac, TIC 500, 972, version 3.307'"):
            raise Exception('Controller does not respond or is incompatible with this driver')
    
    def get_temp(self, channel):
        if channel.upper() not in ['CHUCK', 'CHUCKS', 'SHIELD']:
            raise Exception('Invalid channel')
        return float(self.ask(channel.upper()+'?').strip())

    # just wrapping the main functions of self.tic500
    def query(self, q):
        return self.tic500.query(q)
    
    def ask(self, q):
        return self.tic500.query(q)
    
    def write(self, q):
        return self.tic500.write(q)
    
    def read_stb(self):
        return self.tic500.read_stb()
    
    
if __name__ == '__main__':
    tc = TIC500('ASRL5::INSTR')