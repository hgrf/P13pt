'''
This script uses the following driver for the Rohde and Schwarz VNA:
    https://github.com/Terrabits/rohdeschwarz
'''

from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, String, Folder, Boolean
from P13pt.drivers.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from P13pt.drivers.yoko7651 import Yoko7651
from P13pt.mascril.progressbar import progressbar_wait
from rohdeschwarz.instruments.vna import Vna as RohdeSchwarzVNA
from rohdeschwarz.general import unique_alphanumeric_string

import time
import os
import errno

def create_path(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

class Measurement(MeasurementBase):
    params = {
        'Vgs': Sweep([0.]),
        'Rg': 100e3,
        'stabilise_time': 0.3,
        'comment': String(''),
        'data_dir': Folder(r'D:\MeasurementJANIS\Holger\test'),
        'use_vna': Boolean(True),
        'use_chuck': Boolean(True), # we are not controlling the chuck here, just recording the value of the chuck voltage
        'init_bilt': Boolean(False)
    }

    observables = ['Vg', 'Vgm', 'Ileak']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]
    ]

    def measure(self, data_dir, Vgs, Rg, comment, stabilise_time, use_vna,
                use_chuck, init_bilt, **kwargs):
        print "==================================="        
        print "Starting acquisition script..."

        chuck_string = ''
        vna_string = ''

        # initialise instruments
        print "Setting up DC sources and voltmeters..."
        bilt = Bilt('TCPIP0::192.168.0.2::5025::SOCKET')
        if init_bilt:
            # source (bilt, channel, range, filter, slope in V/ms, label):
            self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I1", "12", "1", 0.005, "Vg")
        else:
            self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I1", initialise=False)
        # voltmeter (bilt, channel, filt, label=None)
        self.meterVg = meterVg = BiltVoltMeter(bilt, "I5;C1", "2", "Vgm")
        print "DC sources and voltmeters are set up."
            
        if use_chuck:
           print "Setting up Yokogawa for chuck voltage..."
           # connect to the Yoko without initialising, this will lead to
           # an exception if the Yoko is not properly configured (voltage
           # source, range 30V, output ON)
           yoko = Yoko7651('GPIB::3::INSTR', initialise=False, rang=30)
           chuck_string = '_Vchuck={:.1f}'.format(yoko.get_voltage())
           print "Yokogawa is set up."

        if use_vna:
            print "Setting up VNA"
            self.vna = vna = RohdeSchwarzVNA()
            vna.open('GPIB', '20')
            
            c1 = vna.channel(1)
            sweeptime = c1.total_sweep_time_ms
            c1.manual_sweep = True
            c1.s_parameter_group = c1.to_logical_ports((1,2))
            # cf: https://www.rohde-schwarz.com/webhelp/webhelp_zva/program_examples/basic_tasks/typical_stages_of_a_remote_control_program.htm#Command_Synchronization
            vna.write("*SRE 32")
            vna.write("*ESE 1")
            
            if not c1.sweep_type == 'SEGM': # need to use not == because != is not implemented in Rohde Schwarz library
                raise Exception('Please use segmented frequency sweep')

            # check if the RF power is the same on both ports and for all
            # frequency segments
            count = int(vna.query(':SENS:SEGM:COUN?').strip())
            vna_pow = None
            for i in range(1,count+1):
                seg_pow = float(vna.query(':SENS:SEGM{}:POW?'.format(i)))
                if vna_pow is None:
                    vna_pow = seg_pow
                elif vna_pow is not None and seg_pow == vna_pow:
                    continue
                else:
                    raise Exception("Please select the same power for all ports and frequency segments")
            port1autoatt = int(vna.query(':SOUR:POW1:ATT:AUTO?').strip())
            port2autoatt = int(vna.query(':SOUR:POW2:ATT:AUTO?').strip())
            if port1autoatt or port2autoatt:
                raise Exception("Please do not use automatic attenuators")
            port1att = float(vna.query(':SOUR:POW1:ATT?').strip())
            port2att = float(vna.query(':SOUR:POW2:ATT?').strip())
            if port1att == port2att:
                vna_pow -= port1att
            else:
                raise Exception("Please select the same attenuators for both ports")
            vna_string = '_pwr={:.0f}'.format(vna_pow)
            
            print "VNA is set up."

        # prepare saving DC data
        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
        filename = timestamp+vna_string+chuck_string+('_'+comment if comment else '')
        self.prepare_saving(os.path.join(data_dir, filename+'.txt'))

        if use_vna:
            # prepare saving RF data
            spectra_fol = os.path.join(data_dir, filename)
            create_path(spectra_fol)
        
            with open(os.path.join(spectra_fol, 'VNAconfig'), 'w') as f:
                f.write('# Frequency based segmented sweep setup of Rohde&Schwarz ZVA 67\n')
                f.write('# Attenuator Port 1: {}\n'.format(port1att))
                f.write('# Attenuator Port 2: {}\n'.format(port2att))
                f.write('# Seg no.\tfstart\tfstop\tpoints\tbwidth\tpow\n')        
                count = int(vna.query(':SENS:SEGM:COUN?').strip())
                for i in range(1,count+1):
                    seg_pow = float(vna.query(':SENS:SEGM{}:POW?'.format(i)).strip())
                    bwidth = float(vna.query(':SENS:SEGM{}:BWID?'.format(i)).strip())
                    fstart = float(vna.query(':SENS:SEGM{}:FREQ:STAR?'.format(i)).strip())
                    fstop = float(vna.query(':SENS:SEGM{}:FREQ:STOP?'.format(i)).strip())
                    points = int(vna.query(':SENS:SEGM{}:SWE:POIN?'.format(i)).strip())
                    f.write('{:d}\t{:f}\t{:f}\t{:d}\t{:f}\t{:f}\n'.format(i, fstart, fstop, points, bwidth, seg_pow))    

        for Vg in Vgs:
            if self.flags['quit_requested']:
                print "Stopping acquisition."
                return locals()            
            
            print "Setting Vg = {}".format(Vg)
        
            # set Vg
            sourceVg.set_voltage(Vg)
            
            # wait
            time.sleep(stabilise_time)
        
            # read voltages
            Vgm = meterVg.get_voltage()
            
            # do calculations
            Ileak = (Vg-Vgm)/Rg
    
            # save DC data
            self.save_row(locals())

            if use_vna:
                # save VNA data
                print "Getting VNA spectra..."
                
                vna.write("INIT1:IMM; *OPC")
                # display sweep progress
                progressbar_wait(sweeptime/1e3)
                # make sure sweep is really done
                while not int(vna.query("*ESR?").strip()):
                    time.sleep(0.5)    
                
                timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)
                #vna.channel(1).save_measurement_locally(os.path.join(spectra_fol, spectrum_file), (1,2))
                spectrum_file = os.path.join(spectra_fol, spectrum_file+'.s2p')

                unique_filename = unique_alphanumeric_string() + '.s2p'
                
                scpi = ":MMEM:STOR:TRAC:PORT {0},'{1}',{2},{3}"
                scpi = scpi.format(1, \
                                   unique_filename, \
                                   'COMP', \
                                   '1,2')
                vna.write(scpi)
                # this saves the file on the ZVA in the folder
                # C:\Rohde&Schwarz\Nwa\
                vna.pause(5000)
            
                vna.file.download_file(unique_filename, spectrum_file)
                vna.file.delete(unique_filename)

        print "Acquisition done."
        
        return locals()

    def tidy_up(self):
        self.vna.close()
        self.end_saving()
        print "Driving all voltages back to zero..."
        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()