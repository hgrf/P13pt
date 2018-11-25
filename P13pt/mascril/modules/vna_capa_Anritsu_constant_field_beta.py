from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, String, Folder, Boolean
from P13pt.mascril.progressbar import progressbar_wait
from P13pt.drivers.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from P13pt.drivers.anritsuvna import AnritsuVNA
from P13pt.drivers.yoko7651 import Yoko7651

import time
import numpy as np
import os
import errno

class Measurement(MeasurementBase):
    params = {
        'Vgs': Sweep([0.]),
        'Vg0': 0.,
        'Vchuck0': 10.,
        'Vchuckmax': 30.,
        'CapaRatio': 10.,
        'Rg': 100e3,
        'stabilise_time': 0.3,
        'comment': String(''),
        'data_dir': Folder(r''),
        'use_vna': Boolean(True),
        'init_bilt': Boolean(False),
        'init_yoko': Boolean(False)
    }

    observables = ['Vg', 'Vgm', 'Vchuck', 'Ileak']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]
    ]

    def measure(self, data_dir, Vgs, Vg0, Vchuck0, Vchuckmax, CapaRatio, Rg,
                comment, stabilise_time, use_vna, init_bilt, init_yoko,
                **kwargs):
        print "==================================="        
        print "Starting acquisition script..."

        # initialise instruments
        try:
            print "Setting up DC sources and voltmeters..."
            bilt = Bilt('TCPIP0::192.168.0.2::5025::SOCKET')
            if init_bilt:
                # source (bilt, channel, range, filter, slope in V/ms, label):
                self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I1", "12", "1", 0.005, "Vg")
            else:
                self.sourceVg = sourceVg = BiltVoltageSource(bilt, "I1", initialise=False)
            # voltmeter (bilt, channel, filt, label=None)
            self.meterVg = meterVg = BiltVoltMeter(bilt, "I5;C1", "2", "Vgm")
            # voltage source for chuck
            self.yoko = yoko = Yoko7651("GPIB::3::INSTR", func="VOLT",
                                        rang=30., slope=1.,
                                        initialise=init_yoko, verbose=True)
            print "DC sources and voltmeters are set up."
        except:
            print "There has been an error setting up DC sources and voltmeters:"
            raise
            
        try:
            print "Setting up VNA..."
            vna = AnritsuVNA('GPIB::6::INSTR')
            sweeptime = vna.get_sweep_time()
            print "VNA is set up."
        except:
            print "There has been an error setting up the VNA:"
            raise

        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')

        # prepare saving DC data
        filename = timestamp + ('_'+comment if comment else '')
        self.prepare_saving(os.path.join(data_dir, filename+'.txt'))
        
        if use_vna:
            # prepare saving RF data
            spectra_fol = os.path.join(data_dir, filename)
            try:
                os.makedirs(spectra_fol)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            if vna.get_sweep_type() == 'FSEGM':
                with open(os.path.join(spectra_fol, 'VNAconfig'), 'w') as f:
                    vna.dump_freq_segments(f)

        for Vg in Vgs:
            if self.flags['quit_requested']:
                print "Stopping acquisition."
                return locals()            
            
            print "Setting Vg = {}".format(Vg)
        
            # calculate new chuck voltage to keep field constant
        
            # set Vg
            sourceVg.set_voltage(Vg)
            
            Vchuck = Vchuck0+CapaRatio*(Vg-Vg0)
            if np.abs(Vchuck) <= Vchuckmax:
                print "Set chuck voltage:", Vchuck
                yoko.set_voltage(Vchuck)
            else:
                print "Chuck voltage too high:", Vchuck
                print "Not changing chuck voltage."
                Vchuck = yoko.get_voltage()
            
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
                vna.single_sweep(wait=False)
                # display sweep progress
                progressbar_wait(sweeptime)
                # make sure sweep is really done
                while not vna.is_sweep_done():
                    time.sleep(0.5)
                table = vna.get_table([1,2,3,4])
                timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                spectrum_file = timestamp+'_Vg=%2.4f_Vchuck=%2.4f'%(Vg, Vchuck)+'.txt'
                np.savetxt(os.path.join(spectra_fol, spectrum_file), np.transpose(table))

        print "Acquisition done."
        
        return locals()

    def tidy_up(self):
        self.end_saving()
        print "Driving all voltages back to zero..."
        self.sourceVg.set_voltage(0.)
        self.yoko.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()