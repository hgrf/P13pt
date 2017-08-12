from P13pt.launcher.measurement import MeasurementBase
from P13pt.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from P13pt.zilockin import ZILockin

import time
import numpy as np
import os

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
        'comment': None,
        'data_dir': '/home/holger/testdata'
    }

    observables = ['Vg1', 'Vg1m', 'Ileak1', 'Vg2', 'Vg2m', 'Ileak2', 'Vds', 'Vdsm', 'Vdsm_std', 'Rs']

    alarms = [
        ['np.abs(Ileak1) > 1e-8', MeasurementBase.ALARM_CALLCOPS],
        ['np.abs(Ileak2) > 1e-8', MeasurementBase.ALARM_CALLCOPS],
        ['np.abs(Vg1-Vg2)', MeasurementBase.ALARM_SHOWVALUE]        # useful if we just want to know how much voltage
                                                                    # is applied between the two gates
    ]

    def measure(self, data_dir, Vg1s, Vg2s, Vds, commongate, Rg1, Rg2, Rds, stabilise_time, **kwargs):
        print "Starting acquisition script..."

        # initialise instruments
        try:
            print "Setting up DC sources and voltmeters..."
            bilt = Bilt('TCPIP0::192.168.0.2::5025::SOCKET')
            self.sourceVg1 = sourceVg1 = BiltVoltageSource(bilt, "I2", "12", "1", 0.01, "Vg1")
            self.sourceVg2 = sourceVg2 = BiltVoltageSource(bilt, "I3", "12", "1", 0.01, "Vg2")
            self.meterVg1 = meterVg1 = BiltVoltMeter(bilt, "I5;C2", "2", "Vg1m")
            self.meterVg2 = meterVg2 = BiltVoltMeter(bilt, "I5;C3", "2", "Vg2m")
            print "DC sources and voltmeters are set up."

            print "Setting up lock-in amplifier"
            self.lockin = lockin = ZILockin()
            print "Lock in amplifier is set up."
        except:
            print "There has been an error setting up one of the instruments."
            raise

        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')

        # save lock in settings (in case we need to check something later)
        lockin.save_settings(os.path.join((data_dir, 'ZIsettings', timestamp+'.ZIsettings.txt')))

        # prepare saving data
        filename = timestamp + '.txt'
        self.prepare_saving(os.path.join((data_dir, filename)))

        # loops
        Vds = lockin.amplitude
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
                Vdsm, Vdsm_std = lockin.poll_data()

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

        self.lockin.tidy_up()


if __name__ == "__main__":
    m = Measurement()
    m.run()