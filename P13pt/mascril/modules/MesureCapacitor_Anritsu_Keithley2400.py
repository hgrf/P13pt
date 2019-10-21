from __future__ import print_function
from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, Folder, Boolean, String
from P13pt.mascril.progressbar import progressbar_wait
from P13pt.drivers.keithley2400 import K2400
from P13pt.drivers.anritsuvna import AnritsuVNA

import time
import numpy as np
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
        'stabilise_time': 0.3,
        'init': Boolean(True),
        'use_vna': Boolean(True),
        'comment': String(''),
        'data_dir': Folder(r'D:\MeasurementJANIS\Holger\test')
    }

    observables = ['Vg', 'Ileak']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]                                                           # is applied between the two gates
    ]

    def measure(self, Vgs, stabilise_time, init, use_vna, data_dir, comment, **kwargs):
        print("===================================")
        print("Starting acquisition script...")
        
        vna_string = ''

        # initialise instruments
        try:
            print("----------------------------------------")
            print("Setting up Keithley DC sources...")
            self.sourceVg = sourceVg = K2400('GPIB::24::INSTR', sourcemode='v', vrang=200, irang=10e-6, slope=1, initialise=init)
            print("DC sources are set up.")
        except:
            print("There has been an error setting up DC sources.")
            raise
        
        if use_vna:
            print("Setting up VNA...")
            vna = AnritsuVNA('GPIB::6::INSTR')
            sweeptime = vna.get_sweep_time()
            
            if vna.get_sweep_type() != 'FSEGM':
                raise Exception('Please use segmented frequency sweep')

            # check if the RF power is the same on both ports and for all
            # frequency segments
            count = int(vna.query(':SENS:FSEGM:COUN?'))
            vna_pow = None
            for i in range(1,count+1):
                port1pow = float(vna.query(':SENS:FSEGM{}:POW:PORT1?'.format(i)))
                port2pow = float(vna.query(':SENS:FSEGM{}:POW:PORT2?'.format(i)))
                if vna_pow is None and port1pow == port2pow:
                    vna_pow = port1pow
                elif vna_pow is not None and port1pow == port2pow and port1pow == vna_pow:
                    continue
                else:
                    raise Exception("Please select the same power for all ports and frequency segments")
            port1att = vna.get_source_att(1)
            port2att = vna.get_source_att(2)
            if port1att == port2att:
                vna_pow -= port1att
            else:
                raise Exception("Please select the same attenuators for both ports")
            vna_string = '_pwr={:.0f}'.format(vna_pow)
            
            print("VNA is set up.")
                
        # define name
        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
        filename = timestamp + vna_string  + ('_'+comment if comment else '')

        # prepare saving RF data
        spectra_fol = os.path.join(data_dir, filename)
        create_path(spectra_fol)

        # prepare saving DC data
        self.prepare_saving(os.path.join(data_dir, filename + '.txt'))

        if use_vna:
            # prepare saving RF data
            spectra_fol = os.path.join(data_dir, filename)
            create_path(spectra_fol)
            # save segmented frequency sweep data to file
            with open(os.path.join(spectra_fol, 'VNAconfig'), 'w') as f:
                vna.dump_freq_segments(f)

        # loop
        for Vg in Vgs:
            if self.flags['quit_requested']:
                return locals()

            print('Setting Vg='+str(Vg)+' V...')
            sourceVg.set_voltage(Vg)
            time.sleep(stabilise_time)

            # measure
            Vgm = sourceVg.get_voltage()
            Ileak = sourceVg.get_current()

            # save data
            self.save_row(locals())
            
            # save VNA data
            if use_vna:
                # save VNA data
                print("Getting VNA spectra...")
                vna.single_sweep(wait=False)
                # display sweep progress
                progressbar_wait(sweeptime)
                # make sure sweep is really done
                while not vna.is_sweep_done():
                    time.sleep(0.5)
                table = vna.get_table([1,2,3,4])
                timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                spectrum_file = timestamp+'_Vg={:.3f}.txt'.format(Vg)
                np.savetxt(os.path.join(spectra_fol, spectrum_file), np.transpose(table))


        print("Acquisition done.")
        
        return locals()

    def tidy_up(self):
        self.end_saving()

        print("Driving all voltages back to zero...")

        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()
