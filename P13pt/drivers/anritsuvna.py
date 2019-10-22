# -*- coding: utf-8 -*-
"""
Driver for the Anritsu VNA MS4644B

for PyVISA 1.8

refer to Anritsu VNA programming handbook for VectorStar MS464xB series
PN: 10410-00322 Rev. W
https://dl.cdn-anritsu.com/en-us/test-measurement/files/Manuals/Programming-Manual/10410-00322W.pdf

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
    
    is_sweeping = False
    
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
        # Initialisation (cf. manual, e.g. page 2-33)
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
    
    def get_s2p(self):
        self.write(':FORM:SNP:FREQ HZ')
        self.write(':FORM:SNP:PAR REIM')
        self.vna.read_termination = ''
        s2p = self.query('OS2P;')
        self.vna.read_termination = '\n'
        return s2p
    
    def save_s2p(self, filename):
        with open(filename, 'w') as f:
            f.write(self.get_s2p().replace('\r', ''))
    
    def is_sweep_done(self):
        '''Checks if the sweep is done.
        
        Every time a port has finished sweeping, the corresponding bit 7 in the
        status byte register is activated, so we have to iterate over all
        ports.
        '''
        if not self.is_sweeping:
            return True
        
        stb = self.read_stb()
        if stb & 16:    # message available
            res = self.read()
            assert res == '1'
            self.is_sweeping = False
            return True
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
        self.is_sweeping = False
    
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
        # operation status register see page 2-33
        # self.write(':STAT:OPER:PTR 2')
        # self.write(':STAT:OPER:ENAB 2')
        # NB: The "sweep complete" bit is set by the VNA every time a port
        # finishes sweeping, which makes it tedious to reliably distinguish
        # between an individual port finishing its sweep and all ports
        # finishing. This is why we choose to block execution instead and
        # wait for the "message available" flag instead.
        self.write('*CLS;')                        # clear the registers
        self.write(':SENS1:HOLD:FUNC SING;')       # single sweep with hold
        self.write(':TRIG:SOUR AUTO;')             # "Internal" trigger
        # trigger sweep and block command execution (as opposed to :TRIG;)
        # programming manual p. 5-838 ff.
        self.write(':TRIG:SING;')
        # when execution starts again, *OPC? will simply return 1
        self.write('*OPC?')
        
        self.is_sweeping = True
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
    
    def read(self):
        return self.vna.read()
    
    def read_stb(self):
        return self.vna.read_stb()

    def read_stb_verbose(self):
        stb = self.read_stb()
        print("Status byte:", stb)
        self.interpret_stb(stb)
        return stb

    # some functions to help interpret the different status registers
    def interpret_stb(self, stb):
        # status byte bits: (manual rev. W p. 2-29)
        # -----------------------------------------
        # 0,1 not used
        # 2 Set to indicate the Error Queue contains data. The Error Query command can then be used to read the error
        #   message(s) from the queue.
        # 3 Set to indicate the Questionable Status summary bit has been set. The Questionable Status Event register can
        #   then be read to determine the specific condition that caused the bit to be set.
        # 4 Set to indicate that the MS4640B has data ready in its output queue.
        # 5 Set to indicate that the Standard Event Status summary bit has been set. The Standard Event Status register
        #   can then be read to determine the specific event that caused the bit to be set.
        # 6 Set to indicate that the MS4640B has at least one reason to require service. This bit is also called the
        #   Master Summary Status Bit (MSS). The individual bits in the Status Byte are ANDed with their corresponding
        #   Service Request Enable Register bits, then each bit value is ORed and input to this bit.
        # 7 Set to indicate that the Operation Status summary bit has been set. The Operation Status Event register can
        #   then be read to determine the specific condition that caused the bit to be set.
        bits = {4: 'ERRQ',
                8: 'QUEST',
                16: 'MAV',
                32: 'STD',
                64: 'MSS/RQS',
                128: 'OPER'}
        for b in bits:
            if stb & b:
                print(bits[b])

    def interpret_esr(self, esr):
        # standard event status group bits:
        # ---------------------------------
        # 0 Set to indicate that all pending MS4640B operations were completed following execution of the “*OPC”
        #   command. For more information, see the descriptions of the *OPC, *OPC?, and *WAI commands in Chapter 3,
        #   “IEEE Commands”.
        # 1 Not used.
        # 2 Set to indicate that a query error has occurred.
        # 3 Set to indicate that a device-dependent error has occurred.
        # 4 Set to indicate that an execution error has occurred.
        # 5 Set to indicate that a command error (usually a syntax error) has occurred.
        # 6 Not used.
        # 7 Set to indicate that the MS4640B is powered ON and in operation.
        bits = {1: 'Operation Complete',
                4: 'Query Error',
                8: 'Device-Dependent Error',
                16: 'Execution Error',
                32: 'Command Error',
                128: 'Power ON'}
        for b in bits:
            if esr & b:
                print(bits[b])

    def interpret_osr(self, osr):
        # operation status register bits:
        # -------------------------------
        # 0 Set to indicate that a calibration is complete.
        # 1 Set to indicate that a sweep is complete. Note that the Sweep Complete Bit will not be set unless the sweep
        #   was started by an appropriate trigger commands. For examples of use, see the “TRS” command in the Lightning
        #   37xxxx Command chapter in the Programming Manual Supplement. Also see “:TRIGger[:SEQuence] Subsystem” on
        #   page 5-835 in Chapter 5, “SCPI Commands”.
        # 2-3 Not used.
        # 4 Set to indicate that the MS4640B is in an armed “wait for trigger” state.
        # 6-15 Not used.
        bits = {1: 'Calibration Complete',
                2: 'Sweep Complete',
                16: 'Waiting for Trigger'}
        for b in bits:
            if osr & b:
                print(bits[b])

    def read_registers(self):
        ''' Reads the status registers of the VNA and prints them to the console.
        '''
        # query command seems not to work when VNA is blocking command
        # execution whereas read_stb works...
        stb = int(self.query('*STB?'))
        print("Status byte:", stb)
        self.interpret_stb(stb)
        esr = int(self.query('*ESR?'))
        print("Standard event status register:", esr)
        self.interpret_esr(esr)
        osr = int(self.query(':STAT:OPER:COND?'))
        print("Operation status register:", osr)
        self.interpret_osr(osr)
    

if __name__ == '__main__':
    vna = AnritsuVNA('GPIB::6::INSTR')