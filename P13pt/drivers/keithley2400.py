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
                 slope=0.01, initialise=True, average=None, average_mode='REP',
                 speed=10.):
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

        if average is None:
            self.set_average_state(False)
        else:
            self.set_average_state(True)
            self.set_average_count(average)
            self.set_filter(average_mode)
        
        self.set_speed(speed)       # default value (10) is HI ACCURACY MODE
        

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
    
    def get_speed(self):
        """
        returns the integration time in terms of power line cycles
        NB this is a global value for voltage, current and resistance
        measurements
        
        on the instrument you can configure the following values:
        FAST          0.01
        MED           0.1
        NORMAL        1
        HI ACCURACY   10
        """
        return float(self.query(':SENS:VOLT:NPLC?'))
        
    
    def get_filter(self):
        """
        returns REP for repeating average and MOV for moving average
        """
        return self.query(':SENS:AVER:TCON?')
    
    def get_average_count(self):
        return int(self.query(':SENS:AVER:COUN?'))
    
    def get_average_state(self):
        return bool(int(self.query(':SENS:AVER:STAT?')))
    
    def set_speed(self, value):
        if value < 0.01 or value > 10.:
            raise Exception('Speed has to be 0.01-10')
        self.write(':SENS:VOLT:NPLC '+str(value))
        
    def set_filter(self, value):
        value = value.upper()
        if value not in ['MOV', 'REP']:
            raise Exception('Filter has to be MOV or REP')
        self.write(':SENS:AVER:TCON '+value)
        
    def set_average_count(self, value):
        value = int(value)
        if value < 1 or value > 100:
            raise Exception('Average count has to be 1-100')
        self.write(':SENS:AVER:COUN '+str(value))
        
    def set_average_state(self, value):
        value = '1' if value else '0'
        self.write(':SENS:AVER:STAT '+value)

    # just wrapping the main functions of self.k2400
    def query(self, q):
        return self.k2400.query(q)
    
    def ask(self, q):
        return self.k2400.query(q)
    
    def write(self, q):
        return self.k2400.write(q)


if __name__ == '__main__':
    k2400 = K2400('GPIB::24::INSTR')