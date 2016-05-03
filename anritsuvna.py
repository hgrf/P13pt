# -*- coding: utf-8 -*-
"""
Minimal script for communication with anritsu VNA

@author: Holger Graef and Andreas Inhofer
"""

# for PyVISA 1.4 !!!

import visa
import struct

class AnritsuVNA(visa.Instrument):
    def __init__(self, connection):
        visa.Instrument.__init__(self, connection)
        self.term_chars = '\n'
        print self.ask('*idn?')
        # Initialisation that apparently is needed.
        # ESE: Something with the Standard event status register
        # SRE: Something with the service enable register (switch to remote?)
        # CLS: Clear all status bytes
        # FORM:BORD NORM - sets the most significant byte first.
        self.write('*ESE 60;*SRE 48;*CLS;:FORM:BORD NORM;')
        # Make sure Data is communicated in the correct format.
        self.write(r':FORM:DATA ASC;') 
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
        
        n = 0       # number of times we ask for status
        while True:
            try:
                n = n+1
                self.ask(':STAT:OPER:COND?')
            except visa.VisaIOError:
                print 'Still sweeping or connection lost'
                continue
            break
        
        for i in range(n-1): self.read()  # workaround that empties the read buffer
        
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

if __name__ == '__main__':
    """Example of how to use this driver
    """
    import numpy as np    
    from measurement import measurement
    vna = AnritsuVNA('GPIB::6::INSTR') #for GPIB
#    vna = AnritsuVNA('TCPIP::192.168.0.3::5001::SOCKET')#for TCPIP
    freqs = vna.get_freq_list()         # get frequency list
    vna.set_average(1, vna.AVG_POINT_BY_POINT)
    vna.single_sweep()
    
    table = []
    table.append(freqs)
    for i in range(4):
        sreal, simag = vna.get_trace(i+1)     # get real and imag part of i-th trace
        table.append(sreal)
        table.append(simag)
    
    datafile = '2016-01-21_14h57m22s_test_Vds=-0.000029_Vg1=0.003376.txt'
    np.savetxt(datafile, np.transpose(table))
    
    spectrum = measurement(datafile)
    spectrum.create_y()
    spectrum.plot_mat_spec("s",ylim = 1)
