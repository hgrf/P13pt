"""
Driver for the Keithley 2400 SourceMeter

for PyVISA 1.8

@author: Holger Graef

contains elements from an acquisition script written by Romaric Le Goff
"""

import visa
import numpy as np
from time import sleep

class K2400:
    def __init__(self, connection, sourcemode='V', vrang=None, irang=None,
                 slope=0.01, initialise=True):
        self.slope = slope
        self.time_step = 0.01     # update voltage every 10 ms when sloping
        
        # set up connection
        self.rm = visa.ResourceManager()
        self.k2400 = self.rm.open_resource(connection)
        self.k2400.write_termination = '\n'
        self.k2400.read_termination = '\n'        
        self.k2400.clear()
               
        if not self.query('*IDN?').startswith('KEITHLEY INSTRUMENTS INC.,MODEL 2400'):
            raise Exception('Instrument not compatible with Keithley 2400 driver')

        if initialise:        
            self.write(":STATus:QUEue:CLEar")
            self.write(":OUTPut:STATe OFF")
           
            if sourcemode.lower() == 'v':
                self.sourcemode = 'v'
                self.write(':SOUR:FUNC VOLT')
                self.write(':SOUR:VOLT 0')
            elif sourcemode.lower() == 'i':
                self.sourcemode = 'i'
                self.write(':SOUR:FUNC CURR')
                self.write(':SOUR:CURR 0')

            if vrang is not None:
                self.write(":SOURce:VOLTage:RANGe "+str(vrang))
            if irang is not None:
                self.write(":SOURce:CURR:RANGe "+str(irang))
            
            self.write(":OUTPut:STATe ON")

        if not self.query('SYST:ERR?').startswith('0,'):
            raise Exception("Keithley 2400 signals error")
    
    def set_current(self, value):
        if not self.query(':SOUR:FUNC:MODE?') == 'CURR':
            raise Exception('The instrument is not set as current source')
        if value > float(self.query(':SOUR:CURR:RANG?')):
            raise Exception('The requested current is out of range')   
            
        # set current
        time_step = self.time_step
        i_step = time_step*self.slope
        
        current_amp = self.get_currsetpoint()
        if np.abs(value-current_amp) < i_step:
            self.write(":SOUR:CURR "+str(value))
            return 
        slow_list = np.arange(current_amp, value,
                              np.sign(value-current_amp)*i_step)
        for i in slow_list:
            sleep(time_step)
            self.write(":SOUR:CURR "+str(i))
        self.write(":SOUR:CURR "+str(value))
    
    def set_voltage(self, value):
        if not self.query(':SOUR:FUNC:MODE?') == 'VOLT':
            raise Exception('The instrument is not set as voltage source')
        if value > float(self.query(':SOUR:VOLT:RANG?')):
            raise Exception('The requested voltage is out of range')
        
        # set voltage
        time_step = self.time_step
        v_step = time_step*self.slope
        
        current_volt = self.get_voltsetpoint()
        if np.abs(value-current_volt) < v_step:
            self.write(":SOURce:VOLTage "+str(value))
            return 
        slow_list = np.arange(current_volt, value,
                              np.sign(value-current_volt)*v_step)
        for volt in slow_list:
            sleep(time_step)
            self.write(":SOURce:VOLTage "+str(volt))
        self.write(":SOURce:VOLTage "+str(value))
        
    def get_currsetpoint(self):
        return float(self.query(':SOUR:CURR?'))
    
    def get_voltsetpoint(self):
        return float(self.query(':SOUR:VOLT?'))
        
    def get_voltage(self):
        self.query(':SENS:FUNC:OFF "CURR:DC"')
        self.query(':SENS:FUNC:ON "VOLT:DC"')
        return float(self.query(':read?').split(',')[0])
        
    def get_current(self):
        self.query(':SENS:FUNC:OFF "VOLT:DC"')
        self.query(':SENS:FUNC:ON "CURR:DC"')
        return float(self.query(':read?').split(',')[1])

    # just wrapping the main functions of self.k2400
    def query(self, q):
        return self.k2400.query(q)
    
    def ask(self, q):
        return self.k2400.query(q)
    
    def write(self, q):
        return self.k2400.write(q)


if __name__ == '__main__':
    k2400 = K2400('GPIB::24::INSTR')