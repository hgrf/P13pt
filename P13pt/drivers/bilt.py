"""
Driver for the Bilt voltage sources and voltmeters

for PyVISA 1.8

@author: Holger Graef
"""

from __future__ import print_function
import visa
from time import sleep

class BiltVoltMeter:
    def __init__(self, bilt, channel, filt, label=None):        
        self.bilt = bilt
        self.channel = channel
        
        print("Initialising Bilt voltmeter on channel "+channel+("" if label is None else " ("+label+")")+"...")
        
        # configure filter
        bilt.write(channel+";MEAS:FIL "+filt)
        
        if bilt.ask("SYST:ERROR?")[:4] != '+000':
            raise Exception("Bilt signals error")

    def get_voltage(self):
        return float(self.bilt.ask(self.channel+";MEAS?"))


class BiltVoltageSource:
    def __init__(self, bilt, channel, rang=None, filt=None, slope=None, label=None, initialise=True):
        self.bilt = bilt
        self.channel = channel
        
        print("Initialising Bilt voltage source on channel "+channel+("" if label is None else " ("+label+")")+"...")

        if initialise:        
            # switch off voltage source
            bilt.write(channel+";OUTPUT OFF")
            
            # configure range
            if rang == "auto":
                bilt.write(channel+";VOLT:RANGE:AUTO 1")
            else:
                bilt.write(channel+";VOLT:RANGE:AUTO 0")
                bilt.write(channel+";VOLT:RANGE "+rang)
            
            # configure filter
            bilt.write(channel+";VOLT:FILTER "+filt)
        
            # configure slope
            bilt.write(channel+";VOLT:SLOPE {}".format(slope))
            
            # set voltage to zero
            bilt.write(channel+";VOLT 0")
            
            # switch on source
            bilt.write(channel+";OUTPUT ON")
            
            # wait for Bilt to switch on
            sleep(0.2)
        
        if bilt.ask("SYST:ERROR?")[:4] != '+000':
            raise Exception("Bilt signals error")
    
    def set_voltage(self, value):
        value = round(value,5)          # in order to avoid bad things happening when we define linspaces like (0,1,4): basically instrument does not seem to like too many figures
        result = round(float(self.bilt.ask(self.channel+";VOLT?")), 5)
        if abs(result-value) < 1e-12:
            return
    
        # set voltage
        self.bilt.write(self.channel+";VOLT {}".format(value))
    
        # wait for voltage to stabilise
        status = self.bilt.ask(self.channel+";VOLT:STATUS?")
        while status != "1":
            status = self.bilt.ask(self.channel+";VOLT:STATUS?")
        

class Bilt:
    def __init__(self, connection):
        self.rm = visa.ResourceManager()
        self.bilt = self.rm.open_resource(connection)
        self.bilt.write_termination = '\n'
        self.bilt.read_termination = '\n'
        
        if self.ask('I0;*IDN?')[:13] != '"FRAME/BN722B': # if we just ask *IDN? we're probably talking to one of the modules, not the Bilt frame
            raise Exception("Bilt does not respond or is incompatible with this driver")
        if self.ask('SYST:ERROR?')[:4] != '+000':
            raise Exception("Bilt signals error")
            
    # just wrapping the main functions of self.bilt
    def query(self, q):
        return self.bilt.query(q)
    
    def ask(self, q):
        return self.bilt.query(q)
    
    def write(self, q):
        return self.bilt.write(q)
    
    def read_stb(self):
        return self.bilt.read_stb()


if __name__ == '__main__':
    bilt = Bilt("TCPIP0::192.168.0.2::5025::SOCKET")
    
    # range can be "1.2", "12", "auto"
    # filter can be 1=10 ms, 0=100 ms    
    biltVg1 = BiltVoltageSource(bilt, "I1", "12", "1", 0.01, "Vg1")
    biltVg2 = BiltVoltageSource(bilt, "I2", "12", "1", 0.01, "Vg2")
    biltVds = BiltVoltageSource(bilt, "I3", "1.2", "1", 0.00005, "Vds")
    
    # filter can be 1=10 rdg/s, 2=50 rdg/s
    biltVg1m = BiltVoltMeter(bilt, "I5;C1", "2", "Vg1m")
    biltVg2m = BiltVoltMeter(bilt, "I5;C2", "2", "Vg2m")
    biltVdsm = BiltVoltMeter(bilt, "I5;C3", "2", "Vdsm")
