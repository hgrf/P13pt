"""
Driver for the Keithley 2600 SourceMeter

for PyVISA 1.8

@author: Holger Graef

contains elements from an acquisition script written by Romaric Le Goff
"""

import visa
import numpy as np
from time import sleep

class K2600:
    def __init__(self, connection, channel='A', slope=0.01, initialise=True, reset=True):
        # TODO: check for error at end of init
        # TODO: implement range setting
        
        self.slope = slope
        self.time_step = 0.01     # update voltage every 10 ms when sloping
        self.channel = channel.lower()
        if self.channel not in ['a', 'b']:
            raise Exception('Invalid channel')
        
        # set up connection
        self.rm = visa.ResourceManager()
        self.k2600 = self.rm.open_resource(connection)
        self.k2600.write_termination = '\n'
        self.k2600.read_termination = '\n'   
        if reset:
            self.k2600.clear()   # if a different channel was set up previously and we execute this, the other channel is switched off
        
        if not self.query('print(localnode.model)').startswith('260'):
            raise Exception('Instrument not compatible with Keithley 2600 driver')
            
        if initialise:
            if reset:
                self.write("reset()")
            self.write("display.smu"+self.channel+".measure.func = display.MEASURE_DCAMPS")
            
            self.write("smu"+self.channel+".source.func = smu"+self.channel+".OUTPUT_DCVOLTS")
            self.write("smu"+self.channel+".source.output = smu"+self.channel+".OUTPUT_ON")
        
    def set_voltage(self, value):
        # set voltage
        time_step = self.time_step
        v_step = time_step*self.slope
        
        current_volt = self.get_voltsetpoint()
        if np.abs(value-current_volt)<=v_step:
            self.write('smu'+self.channel+'.source.levelv = '+str(value))
            return 
        slow_list = np.arange(current_volt, value, np.sign(value-current_volt)*v_step)
        for volt in slow_list:
            sleep(time_step)
            self.write('smu'+self.channel+'.source.levelv = '+str(volt))
        self.write('smu'+self.channel+'.source.levelv = '+str(value))
       
    def get_voltsetpoint(self):
        return float(self.query('print(smu'+self.channel+'.source.levelv)'))
        
    def get_voltage(self):
        return float(self.query('print(smu'+self.channel+'.measure.v())'))
        
    def get_current(self):
        return float(self.query('print(smu'+self.channel+'.measure.i())'))

    # just wrapping the main functions of self.k2600
    def query(self, q):
        return self.k2600.query(q)
    
    def ask(self, q):
        return self.k2600.query(q)
    
    def write(self, q):
        return self.k2600.write(q)


if __name__ == '__main__':
    k2600 = K2600('GPIB::26::INSTR')