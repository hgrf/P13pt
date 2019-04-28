from __future__ import print_function
from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, Folder, Boolean, String
from P13pt.drivers.keithley2400 import K2400
from rohdeschwarz.instruments.vna import Vna as RohdeSchwarzVNA

import time
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
        'data_dir': Folder(r'D:\MeasurementJANIS\David M')
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
            print("Setting up DC sources...")
            self.sourceVg = sourceVg = K2400('GPIB::24::INSTR', sourcemode='v',
                vrang=200, irang=10e-6, slope=1, initialise=init)
            print("DC sources and voltmeters are set up.")
        except:
            print("There has been an error setting up DC sources and voltmeters.")
            raise
        
        if use_vna:
            try:
                print("----------------------------------------")
                print("Setting up VNA")
                self.vna = vna = RohdeSchwarzVNA()
                vna.open('TCPIP', '192.168.0.3')
                c1 = vna.channel(1)
                
                #check if we used a segmented sweep
                c1.manual_sweep = True
                c1.s_parameter_group = c1.to_logical_ports((1,2))
                vna.write("*SRE 32")
                vna.write("*ESE 1")
                
                if not c1.sweep_type == 'SEGM':
                    raise Exception('Please use segmented frequency sweep')
    
                # check if the RF power is the same on both ports and for all frequency segments
                count = int(vna.query(':SENS:SEGM:COUN?').strip())
                vna_pow = None
                for i in range(1,count+1):
                    seg_pow = float(vna.query(':SENS:SEGM{}:POW?'.format(i)))
                    if vna_pow is None:
                        vna_pow = seg_pow
                    elif vna_pow is not None and seg_pow == vna_pow:
                        continue
                    else:
                        raise Exception("Please select the same power for all ports and frequency segments")
                port1autoatt = int(vna.query(':SOUR:POW1:ATT:AUTO?').strip())
                port2autoatt = int(vna.query(':SOUR:POW2:ATT:AUTO?').strip())
                if port1autoatt or port2autoatt:
                    raise Exception("Please do not use automatic attenuators")
                port1att = float(vna.query(':SOUR:POW1:ATT?').strip())
                port2att = float(vna.query(':SOUR:POW2:ATT?').strip())
                if port1att == port2att:
                    vna_pow -= port1att
                else:
                    raise Exception("Please select the same attenuators for both ports")
                
                vna_string = '_pwr={:.0f}'.format(vna_pow)
                
                print("VNA is set up.")
                
            except:
                print("There has been an error setting up the VNA.")
                raise
                
        # define name
        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
        filename = timestamp + vna_string  + ('_'+comment if comment else '')

        # prepare saving RF data
        spectra_fol = os.path.join(data_dir, filename)
        create_path(spectra_fol)

        # prepare saving DC data
        self.prepare_saving(os.path.join(spectra_fol, filename + '.txt'))

        # save config
        if use_vna:
            try:
                with open(os.path.join(spectra_fol, 'VNAconfig'), 'w') as f:
                    f.write('# Frequency based segmented sweep setup of Rohde&Schwarz ZVA 67\n')
                    f.write('# Attenuator Port 1: {}\n'.format(port1att))
                    f.write('# Attenuator Port 2: {}\n'.format(port2att))
                    f.write('# Seg no.\tfstart\tfstop\tpoints\tbwidth\tpow\n')        
                    count = int(vna.query(':SENS:SEGM:COUN?').strip())
                    for i in range(1,count+1):
                        seg_pow = float(vna.query(':SENS:SEGM{}:POW?'.format(i)).strip())
                        bwidth = float(vna.query(':SENS:SEGM{}:BWID?'.format(i)).strip())
                        fstart = float(vna.query(':SENS:SEGM{}:FREQ:STAR?'.format(i)).strip())
                        fstop = float(vna.query(':SENS:SEGM{}:FREQ:STOP?'.format(i)).strip())
                        points = int(vna.query(':SENS:SEGM{}:SWE:POIN?'.format(i)).strip())
                        f.write('{:d}\t{:f}\t{:f}\t{:d}\t{:f}\t{:f}\n'.format(i, fstart, fstop, points, bwidth, seg_pow)) 
            
            except:
                print("There has been an error setting up the VNA.")
                raise

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
                print("Getting VNA spectra...")
                
                #save data
                timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                spectrum_file = timestamp + '_Vg=%2.4f'%(Vg)
                
                c1.save_measurement_locally(os.path.join(spectra_fol, spectrum_file), (1,2))


        print("Acquisition done.")
        
        return locals()

    def tidy_up(self):
        self.end_saving()

        print("Driving all voltages back to zero...")

        self.sourceVg.set_voltage(0.)


if __name__ == "__main__":
    m = Measurement()
    m.run()
