import visa
from time import sleep

class BiltVoltMeter:
    def __init__(self, bilt, channel, filt, label=None):        
        self.bilt = bilt
        self.channel = channel
        
        print "Initialising Bilt voltmeter on channel "+channel+("" if label is None else " ("+label+")")+"..."
        
        # configure filter
        bilt.write(channel+";MEAS:FIL "+filt)
        
        print bilt.ask("SYST:ERROR?")

    def get_voltage(self):
        return float(self.bilt.ask(self.channel+";MEAS?"))


class BiltVoltageSource:
    def __init__(self, bilt, channel, rang, filt, slope, label=None):
        self.bilt = bilt
        self.channel = channel
        
        print "Initialising Bilt voltage source on channel "+channel+("" if label is None else " ("+label+")")+"..."
        
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
        
        print bilt.ask("SYST:ERROR?")
    
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
        

class Bilt(visa.Instrument):
    def __init__(self, connection):
        visa.Instrument.__init__(self, connection)
        self.term_chars = '\n'
        print self.ask('*IDN?')
        print self.ask('SYST:ERROR?')


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