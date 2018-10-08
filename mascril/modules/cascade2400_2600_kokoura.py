from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, Folder, Boolean, String
from P13pt.drivers.keithley2400 import K2400
from P13pt.drivers.keithley2600 import K2600

import time
import os

class Measurement(MeasurementBase):
    params = {
        'Vds': 10e-3,
        'Vgs': Sweep([0.]),
	'Vg_speed': 5,
        'Rg': 100e3,
        'stabilise_time': 0.05,
        'init': Boolean(True),
        'comment': String(''),
        'data_dir': Folder('D:\Manip13\Desktop\Holger')
    }

    observables = ['Vg', 'Vgm', 'Ileak', 'Vds', 'Vdsm', 'Ids', 'Rds']

    alarms = [
        ['np.abs(Ileak) > 1e-8', MeasurementBase.ALARM_CALLCOPS]                                                           # is applied between the two gates
    ]

    def measure(self, Vds, Vgs, Vg_speed, Rg, stabilise_time, init, data_dir, comment, **kwargs):
        print "==================================="        
        print "Starting acquisition script..."

        # initialise instruments
        try:
            print "Setting up DC sources..."
            self.sourceVg = sourceVg = K2400('GPIB::24::INSTR', sourcemode='v',
                vrang=200, irang=10e-6, slope=Vg_speed, initialise=init)
            self.sourceVds = sourceVds = K2600('GPIB::26::INSTR', slope=0.005,
                initialise=init)
            print "DC sources and voltmeters are set up."
        except:
            print "There has been an error setting up DC sources and voltmeters."
            raise

        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')

        # prepare saving data
        filename = timestamp + '_' + (comment if comment else '') + '.txt'
        self.prepare_saving(os.path.join(data_dir, filename))

        # loop
        sourceVds.set_voltage(Vds)
        for Vg in Vgs:
            if self.flags['quit_requested']:
                return locals()

            #t0 = time.time()
            print 'Setting Vg='+str(Vg)+' V...'
            sourceVg.set_voltage(Vg)
            #print 'Voltage setting time', time.time()-t0

            #t0 = time.time()
            time.sleep(stabilise_time)
            #print 'Stabilising time', time.time()-t0

            # measure
            #t0 = time.time()
            Vgm = sourceVg.get_voltage()
            #print 'Acquisition time Vgm', time.time()-t0
            #t0 = time.time()
            Ileak = sourceVg.get_current()
            #print 'Acquisition time Ileak', time.time()-t0
            #t0 = time.time()
            Vdsm = sourceVds.get_voltage()
            #print 'Acquisition time Vdsm', time.time()-t0
            #t0 = time.time()
            Ids = sourceVds.get_current()
            #print 'Acquisition time Ids', time.time()-t0


            # do calculations
            Rds = Vds/Ids

            #t0 = time.time()
            # save data
            self.save_row(locals())
            #print 'Data saving time', time.time()-t0

        print "Acquisition done."
        
        return locals()

    def tidy_up(self):
        self.end_saving()

        print "Driving all voltages back to zero..."

        self.sourceVds.set_voltage(0.)
        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()
