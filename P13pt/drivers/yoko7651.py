"""
Driver for the Yokogawa 7651 source

for PyVISA 1.8

@author: Holger Graef

based on code by Matthieu Dartiailh
https://github.com/Exopy/exopy_hqc_legacy/blob/master/exopy_hqc_legacy
    /instruments/drivers/visa/yokogawa.py
"""

from __future__ import print_function
import visa
import numpy as np
from time import sleep

function_dict = {'F1R2': ('VOLT', 10e-3),
                 'F1R3': ('VOLT', 100e-3),
                 'F1R4': ('VOLT', 1),
                 'F1R5': ('VOLT', 10),
                 'F1R6': ('VOLT', 30),
                 'F5R4': ('CURR', 1e-3),
                 'F5R5': ('CURR', 10e-3),
                 'F5R6': ('CURR', 100e-3)}

class Yoko7651:
    def __init__(self, connection, func='VOLT', rang=1., 
                 slope=0.01, initialise=True, verbose=True):
        self.slope = slope
        self.time_step = 0.1     # update voltage every 100 ms when sloping
        self.func = func.upper()
        self.rang = rang
        
        # set up connection
        self.rm = visa.ResourceManager()
        self.yoko = self.rm.open_resource(connection)
        self.yoko.write_termination = '\n'
        self.yoko.read_termination = '\n'        
        
        if not self.query('OS').startswith('MDL7651REV1.'):
            raise Exception('Instrument not compatible with Yokogawa 7651 '+
                            'driver')
              
        # on receiving the OS command, yoko answers with 5 lines
        # 1st line: model name and software version number
        # 2nd line: function, range, output data
        # 3rd line: interval time, sweep time, program execution mode
        # 4th line: voltage limit value, current limit value
        # 5th line: END
        data = self.read()      
        curr_func = function_dict[data[0:4]][0]
        curr_rang = float(function_dict[data[0:4]][1])
        curr_valu = float(data[5:16])
        data = self.read()
        data = self.read()
        if not self.read().startswith('END'):
            raise Exception('Yokogawa 7651 error.')
        curr_outp = self.get_output()

        unit = "V" if curr_func == "VOLT" else "A"
        if verbose:
            print("Yokogawa 7651 function:", curr_func, "/ range:", curr_rang, unit)
            print("Current set point:", curr_valu, unit)
            print("Output is:", curr_outp)
            
        if not initialise and (self.func != curr_func
                               or self.rang != curr_rang
                               or curr_outp == 'OFF'):
            raise Exception('Yokogawa needs to be initialised')
            
        if initialise:
            if verbose:
                print("Initialising function:", self.func, "/ range:", self.rang, "V" if self.func == "VOLT" else "A")
            self.yoko.clear()       # this command resets the yoko
            sleep(1.)               # give the yoko some time
            self.set_output('OFF')
            self.set_function(self.func)
            self.set_range(self.rang)
            self.set_setpoint(0.)
            self.set_output('ON')
        #TODO: here it would be good to check for errors

    def determine_range(self, func, rang):
        # helper function that finds the next biggest range for the rang value
        # given the desired function (voltage or current source) and returns
        # the corresponding function string
        func = func.upper()
        # find the smallest entry in the function dict that is bigger than
        # the requested range
        min_value = np.inf
        min_key = None
        for key in function_dict:
            if function_dict[key][0] == func:
                instr_rang = function_dict[key][1]
                if instr_rang < min_value and instr_rang >= rang:
                    min_value = instr_rang
                    min_key = key
        return min_key
                    
    def get_function(self):
        self.query('OS')
        data = self.read()            
        self.read()
        self.read()
        self.read()
        return function_dict[data[0:4]][0]
    
    def set_function(self, func):
        func = func.upper()
        if func == 'VOLT':
            self.write('F1E')
        elif func == 'CURR':
            self.write('F5E')
        else:
            raise Exception('Unknown function requested')
        self.func = func
        #TODO: check that function was correctly set a la Dartiailh
    
    def get_range(self):
        self.query('OS')
        data = self.read()            
        self.read()
        self.read()
        self.read()
        return function_dict[data[0:4]][1]
    
    def set_range(self, rang):
        rang_str = self.determine_range(self.func, rang)
        if rang_str is None:
            raise Exception('No compatible range could be found')
        self.write(rang_str[2::]+'E')
        self.rang = rang
        #TODO: check that range was correctly set a Dartiailh
    
    def get_output(self):
        mess = self.query('OC')[5::]
        value = ('{0:08b}'.format(int(mess)))[3]
        if value == '0':
            return 'OFF'
        elif value == '1':
            return 'ON'
        else:
            raise Exception('Invalid output state')
            
    def set_output(self, state):
        state = state.upper()
        if state == 'ON':
            self.write('O1E')
        elif state == 'OFF':
            self.write('O0E')
        else:
            raise Exception('Invalid output state requested')
        #TODO: check if state was set correctly

    def get_setpoint(self):
        data = self.yoko.query("OD")
        if not ((self.func == 'VOLT' and data[3] == 'V')
             or (self.func == 'CURR' and data[3] == 'A')):
            raise Exception('Invalid mode selected')
        return float(data[4::])

    def set_setpoint(self, value):
        # set voltage
        v_step = self.time_step*self.slope
        
        if np.abs(value) > self.rang:
            raise Exception('Value exceeds range')
        
        current_value = self.get_setpoint()
        # check if we are already sufficiently close to the destination value
        if np.abs(value-current_value) < v_step:
            self.yoko.write("S{:+E}E".format(value))
            return 
        
        # otherwise go there slowly
        slow_list = np.arange(current_value, value,
                              np.sign(value-current_value)*v_step)
        for v in slow_list:
            sleep(self.time_step)
            self.yoko.write("S{:+E}E".format(v))
        self.yoko.write("S{:+E}E".format(value))
        #TODO: should check that instrument correctly set the value

    def get_voltage(self):
        if self.func != 'VOLT':
            raise Exception('Wrong mode selected')
        return self.get_setpoint()

    def set_voltage(self, value):
        if self.func != 'VOLT':
            raise Exception('Wrong mode selected')
        return self.set_setpoint(value)
    
    def get_current(self):
        if self.func != 'CURR':
            raise Exception('Wrong mode selected')
        return self.get_setpoint()
    
    def set_current(self, value):
        if self.func != 'CURR':
            raise Exception('Wrong mode selected')
        return self.set_setpoint(value)

    # just wrapping the main functions of self.yoko
    def query(self, q):
        return self.yoko.query(q)
    
    def ask(self, q):
        return self.yoko.query(q)
    
    def write(self, q):
        return self.yoko.write(q)
    
    def read(self):
        return self.yoko.read()


if __name__ == '__main__':
    yoko = Yoko7651('GPIB::3::INSTR')
