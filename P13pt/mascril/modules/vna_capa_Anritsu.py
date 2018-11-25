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
        'use_vna': Boolean(True), # when switched off, this script is basically just a leak test
        'use_chuck': Boolean(True), # we are not controlling the chuck here, just recording the value of the chuck voltage
        'init_bilt': Boolean(False), # when switched on, the Bilt sources will be initialised, this might be dangerous for the sample
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
            print "Setting up VNA..."
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
            
            print "VNA is set up."

        # prepare saving DC data
        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
        filename = timestamp+vna_string+chuck_string+('_'+comment if comment else '')
        self.prepare_saving(os.path.join(data_dir, filename+'.txt'))

        if use_vna:
            # prepare saving RF data
            spectra_fol = os.path.join(data_dir, filename)
            create_path(spectra_fol)
            # save segmented frequency sweep data to file
            with open(os.path.join(spectra_fol, 'VNAconfig'), 'w') as f:
                vna.dump_freq_segments(f)

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

        print "Acquisition done."
        
        return locals()

    def tidy_up(self):
        self.end_saving()
        print "Driving all voltages back to zero..."
        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()