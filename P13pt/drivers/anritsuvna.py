# -*- coding: utf-8 -*-
"""
Driver for the Anritsu VNA MS4644B

for PyVISA 1.8

refer to Anritsu VNA programming handbook
for VectorStar MS464xB series
PN: 10410-00322 Rev. H

@author: Holger Graef and Andreas Inhofer
"""

from __future__ import print_function
import visa
import time

class AnritsuVNA:
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
    TOTAL_PORTS = 2
    
    sweeping_port = 0
    
    def __init__(self, connection):
        self.rm = visa.ResourceManager()
        self.vna = self.rm.open_resource(connection)
        self.vna.write_termination = '\n'
        self.vna.read_termination = '\n'
        
        # Make sure Data is communicated in the correct format.
        # do this before any other requests, so that we don't get stuck if the
        # VNA tries to speak binary
        self.vna.write(r':FORM:DATA ASC;')     
        
        firstresponse = '100 Connection accepted ANRITSU,MS4644B' if connection.startswith('TCPIP') else 'ANRITSU,MS4644B'
        
        if not self.vna.query('*IDN?').startswith(firstresponse):
            raise Exception('Unsupported device / cannot initialise')
        # Initialisation (cf. manual, e.g. page 2-34)
        # ESE: set the standard event status register
        # SRE: set the service request enable register
        # CLS: clear all registers
        # FORM:BORD NORM - sets the most significant byte first.
        self.vna.write('*ESE 60;*SRE 48;*CLS;:FORM:BORD NORM;')
        
        # switch on sweep time measurement
        self.vna.write(':SENS1:SWE:TIM:TYP AUT;')
        self.vna.write(':SENS1:SWE:TIM:STAT 1;')  
        
        # Check that everything works fine for the moment.
        if not self.vna.query('SYST:ERR?').startswith('No Error'):
            raise Exception('Device error')
   
    def read_registers(self):
        print("Status byte:", self.query('*STB?'))
        print("Standard event status register:", self.query('*ESR?'))
        print("Operation status register:", self.query(':STAT:OPER:COND?'))
        #print "Data transfer at sweep end:", self.query(':TRIG:SEDT?')

    def ask_values(self, q):
        ''' Send a query to the VNA and retrieves the returned values.
        
        Parameters
        ----------
        q : str
            The command string.
        
        Returns
        -------
        a : array of python doubles
            VNA data in the binary format that is specified in the
            Anritsu documentation.
        '''
        self.vna.write(':FORM:DATA REAL;')
        data = self.vna.query_binary_values(q, datatype='d', is_big_endian=True)
        self.vna.write(':FORM:DATA ASC;')
        return data

    def get_freq_list(self):
        ''' Retrieves the frequency list from the VNA.
        
        Returns
        -------
        f : array of python doubles
            The frequencies in Hz.
        '''
        return self.ask_values(':SENS1:FREQ:DATA?')
        
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
        data = self.ask_values(':CALC1:DATA:SDAT?')
        
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
    
    def is_sweep_done(self):
        '''Checks if the sweep is done.
        
        Every time a port has finished sweeping, the corresponding bit 7 in the
        status byte register is activated, so we have to iterate over all
        ports.
        '''
        if not self.sweeping_port:
            raise Exception('No sweep is running')
        # note: I think this bugs if we use the read_stb() function, because
        # possibly it might be read this way before the VNA has cleared it
        # using the *CLS command from the previous execution of this function
        if int(self.query('*STB?')) & 128:
            #print 'Port ', self.sweeping_port, ' is done'
            if self.sweeping_port == self.TOTAL_PORTS:
                self.sweeping_port = 0
                self.write('*CLS;')
                return True
            else:
                self.sweeping_port += 1
                self.write('*CLS;')
                return self.is_sweep_done()   # check if the next port is ready
        else:
            return False
    
    def get_sweep_time(self):
        '''Asks VNA for the time the sweep will take.
        
        Returns
        -------
        t : float
            Sweep time.
        '''
        # two ports are being swept
        return 2.*float(self.query(':SENS:SWE:TIM?'))
   
    def get_source_att(self, port):
        '''Asks the VNA for the source attenuator value on the specified port.
        
        Parameters
        ----------
        port : int
            The port
        
        Returns
        -------
        p : float
            The attenuator value
        '''
        return float(self.query(':SOUR:POW:PORT{}:ATT?'.format(port)))
    
    def stop_sweep(self):
        ''' Stops the VNA sweep.
        '''
        self.write(':SENS1:HOLD:FUNC HOLD;')
    
    def single_sweep(self, wait=True):
        ''' Launch a single sweep (the VNA will hold at the end of the sweep).
        
        Parameters
        ----------
        wait : bool
            If set to True, the function waits for the sweep to be done.
        '''
        self.stop_sweep()
        # tell the VNA to let us know when the sweep is done
        # detect positive transistion for bit 1 (sweep complete) of the
        # operation status register see page 2-34
        self.write(':STAT:OPER:PTR 2')
        self.write(':STAT:OPER:ENAB 2')
        self.write('*CLS;')                        # clear the registers
        self.write(':SENS1:HOLD:FUNC SING;')       # single sweep with hold
        self.write(':TRIG:SOUR AUTO;')              # "Internal" trigger
        self.write(':TRIG;')
        self.sweeping_port = 1
        if wait:
            while not self.is_sweep_done():
                time.sleep(0.5)
    
    def get_sweep_type(self):
        '''Asks the VNA for the sweep type.
        
        Returns
        -------
        t : unicode
            The sweep type
        '''
        return self.query(':SENS:SWE:TYP?')
    
    def _fsegm_sweep_only(func):
        ''' This decorator verifies that the function is only used when the
        VNA is in FSEGM sweep mode.
        '''
        def magic(self, *args):
            if self.query(':SENS:SWE:TYP?') == 'FSEGM':
                return func(self, *args)
            else:
                raise Exception('Function '+func.__name__+' can only be used'\
                    +' when VNA is in FSEGM sweep mode)')
        return magic
    
    def _linear_sweep_only(func):
        ''' This decorator verifies that the function is only used when the
        VNA is in linear sweep mode.
        '''
        def magic(self, *args):
            if self.query(':SENS:SWE:TYP?') == 'LIN':
                return func(self, *args)
            else:
                raise Exception('Function '+func.__name__+' can only be used'\
                    +' when VNA is in linear sweep mode)')
        return magic
    
    @_fsegm_sweep_only
    def dump_freq_segments(self, f):
        ''' Dump the frequency segments to a file.
        '''
        f.write('# Frequency based segmented sweep setup of Anritsu MS4644B\n')
        f.write('# Attenuator Port 1: {}\n'.format(self.get_source_att(1)))
        f.write('# Attenuator Port 2: {}\n'.format(self.get_source_att(2)))
        f.write('# Seg no.\tfstart\tfstop\tpoints\tbwidth\tavg\tport1pow\tport2pow\n')        
        count = int(self.query(':SENS:FSEGM:COUN?'))
        for i in range(1,count+1):
            port1pow = float(self.query(':SENS:FSEGM{}:POW:PORT1?'.format(i)))
            port2pow = float(self.query(':SENS:FSEGM{}:POW:PORT2?'.format(i)))
            avg = int(self.query(':SENS:FSEGM{}:AVER:COUN?'.format(i)))
            bwidth = float(self.query(':SENS:FSEGM{}:BWID?'.format(i)))
            fstart = float(self.query(':SENS:FSEGM{}:FREQ:FSTA?'.format(i)))
            fstop = float(self.query(':SENS:FSEGM{}:FREQ:FSTO?'.format(i)))
            points = int(self.query(':SENS:FSEGM{}:SWE:POIN?'.format(i)))
            f.write('{:d}\t{:f}\t{:f}\t{:d}\t{:f}\t{:d}\t{:f}\t{:f}\n'.format(i, fstart, fstop, points, bwidth, avg, port1pow, port2pow))
       
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
    
    @_linear_sweep_only
    def get_source_power(self, port):
        '''Asks the VNA for the source power on the specified port.
        
        Parameters
        ----------
        port : int
            The port
        
        Returns
        -------
        p : float
            The power
        '''
        return float(self.query(':SOUR:POW:PORT{}?'.format(port)))
    
    @_linear_sweep_only
    def get_source_eff_pow(self, port):
        '''Asks the VNA for the effective power on the specified port.
        
        Parameters
        ----------
        port : int
            The port
        
        Returns
        -------
        p : float
            The power
        '''
        return float(self.query(':SOUR:EFF:POW:PORT{}?'.format(port)))
        
    # just wrapping the main functions of self.vna
    def query(self, q):
        return self.vna.query(q)
    
    def ask(self, q):
        return self.vna.query(q)
    
    def write(self, q):
        return self.vna.write(q)
    
    def read_stb(self):
        return self.vna.read_stb()
    

if __name__ == '__main__':
    vna = AnritsuVNA('GPIB::6::INSTR')
