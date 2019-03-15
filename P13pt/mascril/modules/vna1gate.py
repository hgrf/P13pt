from __future__ import print_function
from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, String, Folder
from P13pt.drivers.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from P13pt.drivers.anritsuvna import AnritsuVNA

import time
import numpy as np
import os
import errno

class Measurement(MeasurementBase):
    params = {
        'Vgs': Sweep([0.0]),
        'Vds': 0.01,
        'Rg': 100e3,
        'Rds': 2.2e3,
        'stabilise_time': 0.3,
        'comment': String(''),
        'data_dir': Folder(r'D:\meso\Desktop\testdata')
    }

    observables = ['Vg', 'Vgm', 'Ileak', 'Vds', 'Vdsm', 'Rs']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]
    ]

    def measure(self, data_dir, Vgs, Vds, Rg, Rds, comment, stabilise_time, **kwargs):
        print("===================================")
        print("Starting acquisition script...")

        # initialise instruments
        try:
            print("Setting up DC sources and voltmeters...")
            bilt = Bilt('TCPIP0::192.168.0.2::5025::SOCKET')
            # source (bilt, channel, range, filter, slope in V/ms, label):
            self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I2", "12", "1", 0.005, "Vg")
            self.sourceVds = sourceVds = BiltVoltageSource(bilt, "I3", "1.2", "1", 0.005, "Vds")
            # voltmeter (bilt, channel, filt, label=None)
            self.meterVg = meterVg = BiltVoltMeter(bilt, "I5;C2", "2", "Vgm")
            self.meterVds = meterVds = BiltVoltMeter(bilt, "I5;C3", "2", "Vdsm")
            print("DC sources and voltmeters are set up.")
        except:
            print("There has been an error setting up DC sources and voltmeters.")
            raise
            
        try:
            print("Setting up VNA")
            vna = AnritsuVNA('GPIB::6::INSTR')
            self.freqs = vna.get_freq_list()         # get frequency list
            print("VNA is set up.")
        except:
            print("There has been an error setting up the VNA.")
            raise

        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')

        # prepare saving DC data
        filename = timestamp + ('_'+comment if comment else '')
        self.prepare_saving(os.path.join(data_dir, filename+'.txt'))

        # prepare saving RF data
        spectra_fol = os.path.join(data_dir, filename)
        try:
            os.makedirs(spectra_fol)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        sourceVds.set_voltage(Vds)       
        for Vg in Vgs:
            if self.flags['quit_requested']:
                print("Stopping acquisition.")
                return locals()            
            
            print("Setting Vg = {}".format(Vg))
        
            # set Vg1 and 2
            sourceVg.set_voltage(Vg)
            
            # wait
            time.sleep(stabilise_time)
        
            # read voltages
            Vgm = meterVg.get_voltage()
            Vdsm = meterVds.get_voltage()
            
            # do calculations
            Ileak = (Vg-Vgm)/Rg
            Rs = Rds*Vdsm/(Vds-Vdsm)
    
            # save DC data
            self.save_row(locals())
        
            # save VNA data
            print("Getting VNA spectra...")
            vna.single_sweep()
            table = vna.get_table([1,2,3,4])
            timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')  
            spectrum_file = timestamp+'_Vg1_%2.4f'%(Vg)+'_Vds_%2.4f'%(Vds)+'.txt'
            np.savetxt(os.path.join(spectra_fol, spectrum_file), np.transpose(table))

        print("Acquisition done.")
        
        return locals()

    def tidy_up(self):
        self.end_saving()

        print("Driving all voltages back to zero...")

        self.sourceVg.set_voltage(0.)
        self.sourceVds.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()