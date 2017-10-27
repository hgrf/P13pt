# -*- coding: utf-8 -*-
"""
Minimal script for communication with anritsu VNA

@author: Holger Graef and Andreas Inhofer
"""

# for PyVISA 1.4 !!!

import visa
import struct
import warnings

class AnritsuVNA(visa.Instrument):
    ''' Anritsu VNA driver class
    
    Parameters
    ----------
    connection : str
        The address of the VNA, e.g. 'GPIB::6::INSTR' or
        'TCPIP::192.168.0.3::5001::SOCKET'
    '''
    # Constants
    AVG_POINT_BY_POINT = 'POIN'
    AVG_SWEEP_BY_SWEEP = 'SWE'    
    
    def __init__(self, connection):
        visa.Instrument.__init__(self, connection)
        self.term_chars = '\n'
        
        # Make sure Data is communicated in the correct format.
        # do this before any other requests, so that we don't get stuck if the
        # VNA tries to speak binary
        self.write(r':FORM:DATA ASC;')         
        
        if not self.ask('*idn?').startswith('ANRITSU,MS4644B'):
            raise Exception('Unsupported device / cannot initialise')
        # Initialisation that apparently is needed.
        # ESE: Something with the Standard event status register
        # SRE: Something with the service enable register (switch to remote?)
        # CLS: Clear all status bytes
        # FORM:BORD NORM - sets the most significant byte first.
        self.write('*ESE 60;*SRE 48;*CLS;:FORM:BORD NORM;')
        # Check that everything works fine for the moment.
        if not self.ask('SYST:ERR?').startswith('No Error'):
            raise Exception('Device error')

    def ask_values_anritsu(self, query_str):
        ''' Send a query to the VNA and retrieves the returned values.
        
        Parameters
        ----------
        query_str : str
            The command string.
        
        Returns
        -------
        a : array of python doubles
            VNA data in the binary format that is specified in the
            Anritsu documentation.
        '''
        with warnings.catch_warnings():
            # because we tend to leave data in the buffer
            warnings.filterwarnings("ignore", category=visa.VisaIOWarning)
            
            # make sure Data is communicated in the correct format (binary)
            self.write(':FORM:DATA REAL;')
            # send query
            self.write(query_str)
            # receive data
            self.term_chars = ''                 # switch off termination char
            header = visa.vpp43.read(self.vi, 2) # read header-header
            assert header[0] == '#'              # check if format is OK
            count = int(header[1])               # read length of header
            header = visa.vpp43.read(self.vi, count) # read header
            count = int(header)                  # read length of binary data
            # NB: the following can crash Spyder if variable explorer is open!
            data = visa.vpp43.read(self.vi, count)
            visa.vpp43.read(self.vi, 1)          # read termination character
            assert len(data) == count            # check if all data was read
            self.term_chars = '\n'               # switch term char back on
            self.write(':FORM:DATA ASC;')        # read data in ASCII format
        # convert from big-endian binary doubles to array of python doubles
        return struct.unpack('!'+'d'*(count/8), data)

    def get_freq_list(self):
        ''' Retrieves the frequency list from the VNA.
        
        Returns
        -------
        f : array of python doubles
            The frequencies in Hz.
        '''
        return self.ask_values_anritsu(':SENS1:FREQ:DATA?;')
        
    def get_trace(self, trace_num):
        ''' Retrieves trace number trace_num from the VNA.
        
        Parameters
        ----------
        trace_num : int
            The requested trace number (1, 2, 3...)
            
        Returns
        -------
        sreal, simag : arrays of python doubles
            The real and imaginary part of the requested S parameter.
        '''
        # select desired trace
        self.write(':CALC1:PAR{}:SEL;'.format(trace_num)) 
        data = self.ask_values_anritsu(':CALC1:DATA:SDAT?')
        
        sreal = data[::2]
        simag = data[1::2]
        return sreal, simag
    
    def get_table(self, trace_nums):
        ''' Gets a table of values from the VNA
        
        The first row is frequency, the following rows are
        the real and imaginary part of the requested traces.
        
        Parameters
        ----------
        trace_nums : array of int
            The requested trace numbers (1, 2, 3...)
        
        Returns
        -------
        a : array of python doubles
            The table of values.
        '''
        table = []
        table.append(self.get_freq_list())
        for num in trace_nums:
            sreal, simag = self.get_trace(num) # get trace's real and imag part
            table.append(sreal)
            table.append(simag)
        return table
        
    def single_sweep(self):
        ''' Launch a single sweep (the VNA will hold at the end of the sweep).
        
        Waits for the sweep to be done.
        '''
        self.write(':SENS1:HOLD:FUNC SING;')       # single sweep with hold
        self.write(':TRIG:SING;')                  # trigger single sweep

        timeout = self.timeout
        self.timeout = 600.
        
        self.ask('*STB?')           # ask for status byte (or whatever)        
        
        self.timeout = timeout
    
    def _linear_sweep_only(func):
        ''' This decorator verifies that the function is only used when the
        VNA is in linear sweep mode.
        '''
        def magic(self, *args):
            if self.ask(':SENS:SWE:TYP?') == 'LIN':
                return func(self, *args)
            else:
                raise Exception('Function '+func.__name__+' can only be used'\
                    +' when VNA is in linear sweep mode)')
        return magic
    
    @_linear_sweep_only    
    def enable_averaging(self):
        ''' Switch on averaging.
        '''
        self.write(':SENS1:AVER ON;')
    
    @_linear_sweep_only
    def disable_averaging(self):
        ''' Switch off averaging.
        '''
        self.write(':SENS1:AVER OFF;')
    
    @_linear_sweep_only
    def set_average_count(self, count):
        ''' Set average count.
        
        Parameters
        ----------
        count : int
        '''
        self.write(':SENS1:AVER:COUNT {}'.format(count))
        
    @_linear_sweep_only
    def set_average_type(self, typ):
        ''' Set average type.
        
        Parameters
        ----------
        typ : str
            'POIN' for point by point averaging, 'SWE' for sweep by sweep
            averaging. The latter is pointless in this driver, because we
            only execute single sweeps.
        '''
        self.write(':SENS1:AVER:TYP {}'.format(typ))
    
    @_linear_sweep_only
    def set_average(self, count, typ):
        ''' Set all averaging parameters. For parameters, see set_average_count
        and set_average_type.
        '''
        self.enable_averaging()
        self.set_average_count(count)
        self.set_average_type(typ)
