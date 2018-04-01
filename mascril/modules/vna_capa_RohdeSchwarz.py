'''
This script uses the following driver for the Rohde and Schwarz VNA:
    https://github.com/Terrabits/rohdeschwarz
'''

from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, String, Folder, Boolean
from P13pt.drivers.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from rohdeschwarz.instruments.vna import Vna as RohdeSchwarzVNA

import time
import os
import errno

class Measurement(MeasurementBase):
    params = {
        'Vgs': Sweep([0.]),
        'Rg': 100e3,
        'stabilise_time': 0.3,
        'comment': String(''),
        'data_dir': Folder(r'D:\MeasurementJANIS\Holger\test'),
        'use_vna': Boolean(True),
        'init_bilt': Boolean(False)
    }

    observables = ['Vg', 'Vgm', 'Ileak']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]
    ]

    def measure(self, data_dir, Vgs, Rg, comment, stabilise_time, use_vna, init_bilt, **kwargs):
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
            print "DC sources and voltmeters are set up."
        except:
            print "There has been an error setting up DC sources and voltmeters."
            raise
            
        try:
            print "Setting up VNA"
            self.vna = vna = RohdeSchwarzVNA()
            vna.open('GPIB', '7')
            print "VNA is set up."
        except:
            print "There has been an error setting up the VNA."
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
                print "Getting VNA spectra|"
                timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)
                vna.channel(1).save_measurement_locally(os.path.join(spectra_fol, spectrum_file), (1,2))

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