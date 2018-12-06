from __future__ import print_function
from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, Folder, Boolean, String
from P13pt.drivers.keithley2400 import K2400

import time
import os

class Measurement(MeasurementBase):
    params = {
        'Vgs': Sweep([0.]),
        'stabilise_time': 0.3,
        'init': Boolean(True),
        'comment': String(''),
        'data_dir': Folder(r'D:\MeasurementJANIS\Holger\test')
    }

    observables = ['Vg', 'Ileak']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]                                                           # is applied between the two gates
    ]

    def measure(self, Vgs, stabilise_time, init, data_dir, comment, **kwargs):
        print("===================================")
        print("Starting acquisition script...")

        # initialise instruments
        try:
            print("Setting up DC sources...")
            self.sourceVg = sourceVg = K2400('GPIB::24::INSTR', sourcemode='v',
                vrang=200, irang=10e-6, slope=1, initialise=init)
            print("DC sources and voltmeters are set up.")
        except:
            print("There has been an error setting up DC sources and voltmeters.")
            raise

        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')

        # prepare saving data
        filename = timestamp + '_' + (comment if comment else '') + '.txt'
        self.prepare_saving(os.path.join(data_dir, filename))

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

        print("Acquisition done.")
        
        return locals()

    def tidy_up(self):
        self.end_saving()

        print("Driving all voltages back to zero...")

        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()
