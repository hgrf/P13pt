# -*- coding: utf-8 -*-
"""
Minimal script for communicationwith anritsu VNA

@author: Holger Graef and Andreas Inhofer
"""

# for PyVISA 1.4 !!!

import visa
import struct
import matplotlib.pyplot as plt

class AnritsuVNA(visa.Instrument):
    def __init__(self, connection):
        visa.Instrument.__init__(self, connection)
        self.term_chars = '\n'
        print self.ask('*idn?')
        # Initialisation that apparently is needed. We should check the doc what the different commands do.
        self.write('*ESE 60;*SRE 48;*CLS;:FORM:BORD NORM;')
        # Check that everything works fine for the moment.
        print self.ask('SYST:ERR?')

    def ask_values_anritsu(self, query_str):
        '''
        This function sends a query to the VNA and retrieves the returned values
        in the binary format that is specified in the Anritsu documentation.
        '''
        # make sure Data is communicated in the correct format.
        self.write(':FORM:DATA REAL;')      # switch data transmission to binary     
        # send query
        self.write(query_str)               # send query string
        # receive data
        self.term_chars = ''                # switch off termination char.
        header = visa.vpp43.read(self.vi, 2) # read header-header
        print header
        assert header[0] == '#'             # check if format is OK
        count = int(header[1])              # read length of header
        #print "Reading {} bytes header from Anritsu".format(count)
        header = visa.vpp43.read(self.vi, count) # read header
        count = int(header)                 # read length of binary data
        #print "Reading {} bytes data from Anritsu".format(count)
        self.term_chars = ''
        data = visa.vpp43.read(self.vi, count)     # this crashes Spyder if variable explorer is open !!
        visa.vpp43.read(self.vi, 1)    # read the termination character (do not do this when using GPIB)
        #print 'Successfully read {} bytes'.format(len(data))
        assert len(data) == count            # check all data was read
        self.term_chars = '\n'               # switch on term char
        self.write(':FORM:DATA ASC;')        # read data in ASCII format
        return struct.unpack('!'+'d'*(count/8), data) # convert data from big-endian binary doubles to array of python doubles

    def get_freq_list(self):
        return self.ask_values_anritsu(':SENS1:FREQ:DATA?;')
        
    def get_trace(self, trace_num):
        '''
        Gets trace number trace_num from VNA.
        '''
        # select desired trace
        self.write(':CALC1:PAR{}:SEL;'.format(trace_num)) 
        data = self.ask_values_anritsu(':CALC1:DATA:SDAT?')
        
        sreal = data[::2]
        simag = data[1::2]
        return sreal, simag
        
    def single_sweep(self):
        '''
        This function starts a single sweep (VNA will hold at the end of the
        sweep) and waits for the sweep to be done.
        '''
        self.write(':SENS:HOLD:FUNC SING;')       # single sweep with hold
        self.write(':TRIG:SING;')                 # trigger single sweep
        
        while True:
            try:
                self.ask(':STAT:OPER:COND?')
            except visa.VisaIOError:
                print 'Still sweeping or connection lost'
                continue
            break
        
        # clear buffer workaround (self.clear does not work)
        try:
            self.read_raw()
        except visa.VisaIOError:
            pass
        
        print 'Sweep is done'
        
    def enable_averaging(self):
        self.write(':SENS1:AVER ON;')
    
    def disable_averaging(self):
        self.write(':SENS1:AVER OFF;')
        
    def set_average_count(self, count):
        self.write(':SENS1:AVER:COUNT {}'.format(count))
        
    AVG_POINT_BY_POINT = 'POIN'
    AVG_SWEEP_BY_SWEEP = 'SWE'
    def set_average_type(self, typ):
        self.write(':SENS1:AVER:TYP {}'.format(typ))
    
    def set_average(self, count, typ):
        self.enable_averaging()
        self.set_average_count(count)
        self.set_average_type(typ)


vna = AnritsuVNA('TCPIP::192.168.0.3::5001::SOCKET')
freqs = vna.get_freq_list()         # get frequency list
vna.set_average(20, vna.AVG_POINT_BY_POINT)
vna.single_sweep()
sreal, simag = vna.get_trace(2)     # get real and imag part of 1st trace

plt.plot(freqs, sreal)
plt.plot(freqs, simag)
