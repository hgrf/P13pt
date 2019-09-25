'''
This script uses the following driver for the Rohde and Schwarz VNA:
    https://github.com/Terrabits/rohdeschwarz
'''

from __future__ import print_function
from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, String, Folder, Boolean
from P13pt.drivers.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from P13pt.drivers.yoko7651 import Yoko7651
from P13pt.mascril.progressbar import progressbar_wait
from rohdeschwarz.instruments.vna import Vna as RohdeSchwarzVNA

import time
import os
import errno
import numpy as np

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
        print("===================================")
        print("Starting acquisition script...")

        chuck_string = ''
        vna_string = ''

        # initialise instruments
        print("Setting up DC sources and voltmeters...")
        bilt = Bilt('TCPIP0::192.168.0.5::5025::SOCKET')
        if init_bilt:
            # source (bilt, channel, range, filter, slope in V/ms, label):
            self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I3;C1", "12", "1", 0.005, "Vg")
        else:
            self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I3;C1", initialise=False)
        # voltmeter (bilt, channel, filt, label=None)
        self.meterVg = meterVg = BiltVoltMeter(bilt, "I1;C1", "2", "Vgm")
        print("DC sources and voltmeters are set up.")
            
        if use_chuck:
           print("Setting up Yokogawa for chuck voltage...")
           # connect to the Yoko without initialising, this will lead to
           # an exception if the Yoko is not properly configured (voltage
           # source, range 30V, output ON)
           yoko = Yoko7651('GPIB::10::INSTR', initialise=False, rang=30)
           chuck_string = '_Vchuck={:.1f}'.format(yoko.get_voltage())
           print("Yokogawa is set up.")

        if use_vna:
            print("Setting up VNA")
            self.vna = vna = RohdeSchwarzVNA()
            vna.open('TCPIP', '192.168.0.3')
            
            c1 = vna.channel(1)
            sweeptime = c1.total_sweep_time_ms
            c1.init_nonblocking_sweep((1,2))

            if not c1.is_corrected():
                raise Exception('Please calibrate or switch on correction.')
            if c1.sweep_type != 'SEGM':
                raise Exception('Please use segmented frequency sweep')

            # check if the RF power is the same on both ports and for all
            # frequency segments
            vna_pow = np.unique(np.asarray(c1.get_frequency_segments())[:,5])
            if len(vna_pow) > 1:
                raise Exception("Please select the same power for all ports and frequency segments")
            vna_pow = vna_pow[0]
            if c1.is_auto_attenuator(1) or c1.is_auto_attenuator(2):
                raise Exception("Please do not use automatic attenuators")
            port1att = c1.get_attenuator(1)
            if port1att == c1.get_attenuator(2):
                vna_pow -= port1att
            else:
                raise Exception("Please select the same attenuators for both ports")
            vna_string = '_pwr={:.0f}'.format(vna_pow)
            
            print("VNA is set up.")

        # prepare saving DC data
        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
        filename = timestamp+vna_string+chuck_string+('_'+comment if comment else '')
        self.prepare_saving(os.path.join(data_dir, filename+'.txt'))

        if use_vna:
            # prepare saving RF data
            spectra_fol = os.path.join(data_dir, filename)
            create_path(spectra_fol)
        
            c1.save_frequency_segments(os.path.join(spectra_fol, 'VNAconfig'))

        for Vg in Vgs:
            if self.flags['quit_requested']:
                print("Stopping acquisition.")
                return locals()            
            
            print("Setting Vg = {}".format(Vg))
        
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
                print("Getting VNA spectra...")
                
                c1.start_nonblocking_sweep()
                # display sweep progress
                progressbar_wait(sweeptime/1e3)
                # make sure sweep is really done
                while not c1.isdone_nonblocking_sweep():
                    time.sleep(0.5)
                
                timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)
                spectrum_file = os.path.join(spectra_fol, spectrum_file+'.s2p')
                c1.save_nonblocking_sweep(spectrum_file, (1,2))

        print("Acquisition done.")
        
        return locals()

    def tidy_up(self):
        self.vna.close()
        self.end_saving()
        print("Driving all voltages back to zero...")
        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()