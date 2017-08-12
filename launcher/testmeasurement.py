from measurement import MeasurementBase
from testdrivers import VoltageSource, VoltMeter

import time
import numpy as np

class Measurement(MeasurementBase):
    params = {
        'Vg1s': np.linspace(-1., 1., 101),
        'Vg2s': [0.],
        'Vds': 10e-3,
        'commongate': False,
        'Rg1': 100e3,
        'Rg2': 100e3,
        'Rds': 2.2e3,
        'stabilise_time': 0.5,
        'comment': None
    }

    observables = ['Vg1', 'Vg1m', 'Ileak1', 'Vg2', 'Vg2m', 'Ileak2', 'Vds', 'Vdsm', 'Rs']

    def measure(self, Vg1s, Vg2s, Vds, commongate, Rg1, Rg2, Rds, stabilise_time, **kwargs):
        print "Starting acquisition script..."

        # initialise instruments
        try:
            self.sourceVg1 = sourceVg1 = VoltageSource() # here we should add safety limits
            self.sourceVg2 = sourceVg2 = VoltageSource()
            self.sourceVds = sourceVds = VoltageSource()
            self.meterVg1 = meterVg1 = VoltMeter()
            self.meterVg2 = meterVg2 = VoltMeter()
            self.meterVds = meterVds = VoltMeter()
        except:
            print "There has been an error setting up one of the instruments."
            raise

        # prepare saving data
        filename = time.strftime('%Y-%m-%d_%Hh%Mm%Ss') + '.txt'
        self.prepare_saving(filename)

        # loops
        sourceVds.set_voltage(Vds)
        for Vg2 in Vg2s:
            sourceVg2.set_voltage(Vg2)
            for Vg1 in Vg1s:
                if self.flags['quit_requested']:
                    return locals()

                sourceVg1.set_voltage(Vg1)

                # stabilise
                time.sleep(stabilise_time)

                # measure
                Vg1m = meterVg1.get_voltage()
                Vg2m = meterVg2.get_voltage()
                Vdsm = meterVds.get_voltage()

                # do calculations
                Ileak1 = (Vg1-Vg1m)/Rg1
                Ileak2 = (Vg2-Vg2m)/Rg2
                Rs = Rds*Vdsm/(Vds-Vdsm)

                # save data
                self.save_row(locals())

        print "Acquisition done."
        
        return locals()

    def tidy_up(self):
        self.end_saving()

        print "Driving all voltages back to zero..."

        self.sourceVg1.set_voltage(0.)
        self.sourceVg2.set_voltage(0.)
        self.sourceVds.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()