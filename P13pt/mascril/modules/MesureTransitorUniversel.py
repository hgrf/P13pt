"""
Universal acquisition script for transistor characterization in P13

Authors: Damien Fruleux, Holger Graef, David Mele, Aurelien Schmitt

TODO:
- rs pour non bilt
- choix go to zero ou regler slope bilt ! -> slope yoko parfaite !
- peut etre tester auto slope ? auto range ?
- vna slope + dc slope
- anritsu acquisition time          
- que se passe t'il si on n'utilise pas Vds ? ou Vg ? ou Vchuck ?
- K2600 channel 1 & 2
- ajouter nouveau controleur de temperature
- sweep : use only one loop ?
- implementer algo stop auto ileak (comme pwr)
- yoko get current ? get voltage ?
"""


from __future__ import print_function

from P13pt.mascril.measurement import MeasurementBase
from P13pt.mascril.parameter import Sweep, String, Folder, Select
from P13pt.drivers.bilt import Bilt, BiltVoltageSource, BiltVoltMeter
from P13pt.drivers.yoko7651 import Yoko7651
from P13pt.drivers.anritsuvna import AnritsuVNA
from P13pt.drivers.si9700 import SI9700
from P13pt.drivers.tic500 import TIC500
from P13pt.drivers.keithley2400 import K2400
from P13pt.drivers.keithley2600 import K2600
from P13pt.mascril.progressbar import progressbar_wait

from rohdeschwarz.instruments.vna import Vna as RohdeSchwarzVNA

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
        'src_Vds': Select(['Bilt_1', 'Bilt_2', 'Bilt_3', 'Bilt_4', 'K2400', 'K2600']),
        'Vdss': Sweep([0.0]),
        'Rds_Bilt_Only': 9.86e3,
        
        'src_Vg': Select(['Bilt_3', 'Bilt_4', 'Bilt_1', 'Bilt_2', 'K2400', 'K2600']),  
        'Vgs': Sweep([0.0]),
        'Rg_Bilt_Only': 29.9e3,
        
        'src_Vchuck': Select(['None', 'Yoko', 'K2400', 'K2600']),
        'Vchucks': Sweep([0.0]),
        
        #'use_vna' : Boolean(True),
        'src_vna': Select(['None', 'zva67', 'anritsu']),
        'sweep_type' : Select(['initialise_instruments', 'give_time', 'fix_Vg_sweep_Vds', 'fix_Vds_sweep_Vg']),
        
        'mesurement_station' : Select(['None', 'JANIS', 'Cascade']),
        'comment': String(''),
        'data_dir': Folder(r''),

        'WxL': 100, #um²
        'max_pwr': 2e-3,
        'max_Ileak': 1e-7,          
    
        'stabilise_time': 1,
        'slope_vg_vd': 0.005,
        'slope_vchuck': 1
    }

    observables = ['Vg', 'Vgm', 'Ileak', 'Vds', 'Vdsm', 'Ids', 'Rs', 'pwr', 'Ta', 'Tb', 'Vchuck', 'sweeptime_min', 'remain_time_min', 'progress_percent']

    alarms = [
        ['np.abs(Ileak) > max_Ileak', MeasurementBase.ALARM_CALLCOPS],
        ['pwr > max_pwr', MeasurementBase.ALARM_CALLCOPS],
    ]

    def measure(self, sweep_type, src_Vg, src_Vds, src_Vchuck, src_vna, data_dir, comment, mesurement_station, Vdss, Vgs, Vchucks, Rg_Bilt_Only, Rds_Bilt_Only, WxL, max_pwr, max_Ileak, stabilise_time, slope_vg_vd, slope_vchuck, **kwargs):
        print("****************************************")
        print("===================================")
        print("Starting acquisition script")

        self.sourceVchuck = None

        vna_string = ''
        temp_string = ''
        
        if (mesurement_station == 'None'):
            print("Please chose a mesurement station first")
            raise
        
        #initialise instruments
        if (sweep_type =='initialise_instruments'):
            init_instruments = True
        else:
            init_instruments = False
            
#        #select correct vna
#        if (use_vna == 'True' and mesurement_station == 'JANIS'):
#            src_vna = 'anritsu'
#        elif (use_vna == 'True' and mesurement_station == 'Cascade'):
#            src_vna = 'zva67'
#        else:
#            src_vna = 'None'
        
        #------------------------------------------------------------------------#
        #------------------------------------------------------------------------#
        #set instruments
        
        if (mesurement_station == 'JANIS'):
            yoko_address = 'GPIB::3::INSTR'
            k2000_address = 'GPIB::20::INSTR'
            bilt_address = 'TCPIP0::192.168.0.2::5025::SOCKET'
            anritsu_address = 'GPIB::6::INSTR'
            temperature_address = 'GPIB::14::INSTR'
            
            position_source_bilt = "I"
            position_meter_bilt = "I5;C"
            
        if (mesurement_station == 'Cascade'):
            yoko_address = 'GPIB::10::INSTR'
            k2000_address = 'GPIB::15::INSTR'
            bilt_address = 'TCPIP0::192.168.0.5::5025::SOCKET'
            zva67_address = '192.168.0.3'
            temperature_address = 'ASRL5::INSTR'
            
            position_source_bilt = "I3;C"
            position_meter_bilt = "I1;C"
            
        k2400_address = 'GPIB::24::INSTR'
        k2600_address = 'GPIB::24::INSTR'

        #------------------------------------------------------------------------#
        #------------------------------------------------------------------------#
        
        # initialise SI9700 temperature controler
        if (mesurement_station == 'JANIS'):
            try:
                print("----------------------------------------")
                print("Setting up SI9700 temperature controller...")
                tc = SI9700(temperature_address)
                temp_string='_T={:.1f}'.format((tc.get_temp('a')+tc.get_temp('b'))/2)
                print("Temperature controller SI9700 is set up.")
                
            except:
                print("There has been an error setting up the SI9700 temperature controller.")
                raise
                
        elif (mesurement_station == 'Cascade'):
            try:
                print("----------------------------------------")
                print("Setting up TIC500 temperature controller...")
                tc = TIC500(temperature_address)
                temp_string='_T={:.1f}'.format(tc.get_temp('Chuck'))
                print("Temperature controller TIC500 is set up.")
                
            except:
                print("There has been an error setting up the TIC500 temperature controller.")
                raise
        
        # initialise K2400
        if (src_Vg == 'K2400' or src_Vds == 'K2400' or src_Vchuck == 'K2400'):
            try:
                print("----------------------------------------")
                print("Setting up K2400 DC source...")
                
                if src_Vg == 'K2400' : 
                    self.sourceVg = sourceVg = K2400(k2400_address, sourcemode='v', vrang=200, irang=100e-3, slope=slope_vg_vd, initialise=init_instruments)
                if src_Vds == 'K2400' : 
                    self.sourceVds = sourceVds = K2400(k2400_address, sourcemode='v', vrang=200, irang=100e-3, slope=slope_vg_vd, initialise=init_instruments)
                if src_Vchuck == 'K2400' : 
                    self.sourceVchuck = sourceVchuck = K2400(k2400_address, sourcemode='v', vrang=200, irang=100e-3, slope=slope_vchuck, initialise=init_instruments)
                
                print("K2400 DC source are set up.")
            except:
                print("There has been an error setting up K2400 DC sources.")
                raise
                
        # initialise K2600
        if (src_Vg == 'K2600' or src_Vds == 'K2600' or src_Vchuck == 'K2600'):
            try:
                print("----------------------------------------")
                print("Setting up K2600 DC source...")
                
                if src_Vg == 'K2600' : 
                    self.sourceVg = sourceVg = K2600(k2600_address, slope=slope_vg_vd, initialise=init_instruments)
                if src_Vds == 'K2600' : 
                    self.sourceVds = sourceVds = K2600(k2600_address, slope=slope_vg_vd, initialise=init_instruments)
                if src_Vchuck == 'K2600' : 
                    self.sourceVchuck = sourceVchuck = K2600(k2600_address, slope=slope_vchuck, initialise=init_instruments)
                
                print("K2600 DC source are set up.")
            except:
                print("There has been an error setting up K2600 DC sources.")
                raise
        
        # initialise YOKO
        if (src_Vchuck == 'Yoko'):
            try:
                print("----------------------------------------")
                print("Setting up Yokogawa DC source...")
                
                self.sourceVchuck = sourceVchuck = Yoko7651(yoko_address, initialise=init_instruments, rang=30, slope=slope_vchuck)
                
                print("Yokogawa DC source are set up.")
                
            except:
                print("There has been an error setting up the chuck voltage.")
                raise
        
        # initialise BILT
        if (src_Vg[0:4] == 'Bilt' or src_Vds[0:4] == 'Bilt'):
            try:
                print("----------------------------------------")
                print("Setting up BILT DC sources and voltmeters...")
                bilt = Bilt(bilt_address)
                
                if (src_Vg[0:4] == 'Bilt'):
                    src_Vg, port_Vg = src_Vg.split('_') 
                    self.sourceVg = sourceVg = BiltVoltageSource(bilt, position_source_bilt+port_Vg, rang = "12", filt = "1", slope = slope_vg_vd, label=None, initialise=init_instruments)
                    self.meterVg = meterVg = BiltVoltMeter(bilt, position_meter_bilt+port_Vg, filt = "2", label = "Vgm")
                    
                if (src_Vds[0:4] == 'Bilt'): 
                    src_Vds, port_Vds = src_Vds.split('_')
                    self.sourceVds = sourceVds = BiltVoltageSource(bilt, position_source_bilt+port_Vds, rang = "12", filt = "1", slope = slope_vg_vd, label=None, initialise=init_instruments)
                    self.meterVds = meterVds = BiltVoltMeter(bilt, position_meter_bilt+port_Vds, filt = "2", label = "Vdsm")
                                        
                print("BILT DC sources and voltmeters are set up.")
                
            except:
                print("There has been an error setting up BILT DC sources and voltmeters.")
                raise
        
        # initialise VNA ZVA67
        if src_vna == 'zva67':
                print("Setting up VNA")
                self.vna = vna = RohdeSchwarzVNA()
                vna.open('TCPIP', '192.168.0.3')
            
                c1 = vna.channel(1)
                sweeptime = c1.total_sweep_time_ms
                c1.init_nonblocking_sweep((1,2))

                if not c1.is_corrected():
                    raise Exception('Please calibrate or switch on correction.')
                if c1.sweep_type != 'SEGM':
                    raise Exception('Please use segmented frequency sweep')

                # check if the RF power is the same on both ports and for all
                # frequency segments
                vna_pow = np.unique(np.asarray(c1.get_frequency_segments())[:,5])
                if len(vna_pow) > 1:
                    raise Exception("Please select the same power for all ports and frequency segments")
                vna_pow = vna_pow[0]
                if c1.is_auto_attenuator(1) or c1.is_auto_attenuator(2):
                    raise Exception("Please do not use automatic attenuators")
                port1att = c1.get_attenuator(1)
                if port1att == c1.get_attenuator(2):
                    vna_pow -= port1att
                else:
                    raise Exception("Please select the same attenuators for both ports")
                vna_string = '_pwr={:.0f}'.format(vna_pow)
            
                print("VNA is set up.")
                
        # initialise VNA ANRITSU
        if (src_vna == 'anritsu'):
            try:
                print("----------------------------------------")
                print("Setting up ANRITSU VNA")
                vna = AnritsuVNA(anritsu_address)
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
                
                print("ANRITSU VNA is set up.")
                
            except:
                print("There has been an error setting up the ANRITSU VNA.")
                raise
                
        print("----------------------------------------")
        
        #------------------------------------------------------------------------#
        #------------------------------------------------------------------------#

        # define name
        timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
        filename = timestamp + vna_string  + temp_string + ('_'+comment if comment else '')

        # prepare saving DC data
        self.prepare_saving(os.path.join(data_dir, filename + '.txt'))
        
        # prepare saving RF data
        if src_vna != 'None' :
            spectra_fol = os.path.join(data_dir, filename)
            create_path(spectra_fol)
        
        # save config
        if src_vna == 'zva67':
            # prepare saving RF data
            spectra_fol = os.path.join(data_dir, filename)
            create_path(spectra_fol)
        
            c1.save_frequency_segments(os.path.join(spectra_fol, 'VNAconfig')) 
            

        sweeptime_min = len(Vgs) * len(Vdss) * len(Vchucks) * stabilise_time * (c1.total_sweep_time_ms*1e3 if src_vna == 'zva67' else 1) / 60
        remain_time_min = sweeptime_min
        progress_percent = 0
        
        if (sweep_type == 'give_time' or sweep_type == 'initialise_instruments'):
            # save data
            self.save_row(locals())
            # stop
            return locals()
        
        #------------------------------------------------------------------------#
        #------------------------------------------------------------------------#
        
        # loops
        print("........................................")
        print("Starting mesurement")
        print("++++++++++++++++++++++++++++++++++++++++")
               
        for Vchuck in Vchucks:
            if src_Vchuck != "None":
                sourceVchuck.set_voltage(Vchuck)
                
            if (sweep_type == 'fix_Vds_sweep_Vg'):
                for Vds in Vdss:
                    
                    sourceVds.set_voltage(Vds)
        
                    for Vg in Vgs:
                        
                        sourceVg.set_voltage(Vg)
                        
                        # quit request
                        if self.flags['quit_requested']:
                            return locals()
        
                        # stabilise
                        time.sleep(stabilise_time)
        
                        # measure & calculate
                        if (src_Vds == 'K2400' or src_Vds == 'K2600'):
                            #mesure current directly
                            Ids = sourceVds.get_current()
                        if (src_Vds[0:4] == 'Bilt'):
                            #mesure current and convert in tension with resistor
                            Vdsm = meterVds.get_voltage()
                            Rs = Rds_Bilt_Only*Vdsm/(Vds-Vdsm)
                            Ids = Vds/Rs
                            
                        if (src_Vg == 'K2400' or src_Vg == 'K2600'):
                            #mesure current directly
                            Ileak =  sourceVg.get_current()
                        if (src_Vg[0:4] == 'Bilt'):
                            #mesure current and convert in tension with resistor
                            Vgm = meterVg.get_voltage()
                            Ileak = (Vg-Vgm)/Rg_Bilt_Only
                            
                        pwr = (Vds*Ids)/(WxL)
        
                        # get temp
                        if (mesurement_station == 'JANIS'):
                            Ta = tc.get_temp('a')
                            Tb = tc.get_temp('b')
                            
                        elif (mesurement_station == 'Cascade'):
                            Ta = tc.get_temp('Chuck')
                            Tb = tc.get_temp('Chuck')
        
                        # save data
                        self.save_row(locals())
                        
                        #print
                        print("Getting mesurement Vg = {}".format(Vg) +" and Vds = {}".format(Vds))
        
                        # save VNA data
                        if src_vna == 'zva67':
                            # save VNA data
                            print("Getting VNA spectra...")
                
                            c1.start_nonblocking_sweep()
                            # make sure sweep is really done

                            # display sweep progress
                            progressbar_wait(sweeptime/1e3)
                            # make sure sweep is really done
                            while not c1.isdone_nonblocking_sweep():
                                time.sleep(0.5)
                
                            timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                            spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)+'_Vds=%2.4f'%(Vds)
                            spectrum_file = os.path.join(spectra_fol, spectrum_file+'.s2p')
                            c1.save_nonblocking_sweep(spectrum_file, (1,2))
                            
                        if src_vna == 'Anritsu':
                            vna.single_sweep()
                            
                            table = vna.get_table(range(1,4))
                            timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')  
                            spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)+'_Vds=%2.4f'%(Vds)+'.txt'
                            
                            np.savetxt(os.path.join(spectra_fol, spectrum_file), np.transpose(table))
                            
                        #mesure time
                        remain_time_min = remain_time_min - ( stabilise_time * (c1.total_sweep_time_ms*1e3 if src_vna == 'zva67' else 1) / 60)
                        progress_percent = (sweeptime_min - remain_time_min) / sweeptime_min * 100
    
    
            if (sweep_type == 'fix_Vg_sweep_Vds'):
                for Vg in Vgs:
                
                    sourceVg.set_voltage(Vg)
                    
                    first_pass=True
                    
                    for Vds in Vdss:
                        
                        #check power limit
                        if first_pass:
                            pwr = 0
                        else : 
                            pwr = (Vds*Ids)/(WxL)
                        if (pwr > max_pwr):
                            pwr_limit = True
                        elif (pwr < max_pwr):
                            pwr_limit = False
                        
                        if not pwr_limit:
                            
                            sourceVds.set_voltage(Vds)
                            
                            #quit request
                            if self.flags['quit_requested']:
                                return locals()
            
                            # stabilise
                            time.sleep(stabilise_time)
            
                            # measure & calculate
                            if (src_Vds == 'K2400' or src_Vds == 'K2600'):
                                #mesure current directly
                                Ids = sourceVds.get_current()
                            if (src_Vds[0:4] == 'Bilt'):
                                #mesure current and convert in tension with resistor
                                Vdsm = meterVds.get_voltage()
                                Rs = Rds_Bilt_Only*Vdsm/(Vds-Vdsm)
                                Ids = Vds/Rs
                                
                            if (src_Vg == 'K2400' or src_Vg == 'K2600'):
                                #mesure current directly
                                Ileak =  sourceVg.get_current()
                            if (src_Vg[0:4] == 'Bilt'):
                                #mesure current and convert in tension with resistor
                                Vgm = meterVg.get_voltage()
                                Ileak = (Vg-Vgm)/Rg_Bilt_Only
                                
                            pwr = (Vds*Ids)/(WxL)
        
                            # get temp
                            if (mesurement_station == 'JANIS'):
                                Ta = tc.get_temp('a')
                                Tb = tc.get_temp('b')
                                
                            elif (mesurement_station == 'Cascade'):
                                Ta = tc.get_temp('Chuck')
                                Tb = tc.get_temp('Chuck')
                
                            # do calculations
                            Ileak = (Vg-Vgm)/Rg_Bilt_Only
                            
                            # save data
                            self.save_row(locals())
                            
                            #print
                            print("Getting mesurement Vg = {}".format(Vg) +" and Vds = {}".format(Vds))
        
                        # save VNA data
                        if src_vna == 'zva67':
                            # save VNA data
                            print("Getting VNA spectra...")
                
                            c1.start_nonblocking_sweep()
                            
                            # display sweep progress
                            progressbar_wait(sweeptime/1e3)
                            # make sure sweep is really done
                            while not c1.isdone_nonblocking_sweep():
                                time.sleep(0.5)                   
                                
                            timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')
                            spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)+'_Vds=%2.4f'%(Vds)
                            spectrum_file = os.path.join(spectra_fol, spectrum_file+'.s2p')
                            c1.save_nonblocking_sweep(spectrum_file, (1,2))
                            
                        if src_vna == 'Anritsu':
                            vna.single_sweep()
                            
                            table = vna.get_table(range(1,4))
                            timestamp = time.strftime('%Y-%m-%d_%Hh%Mm%Ss')  
                            spectrum_file = timestamp+'_Vg=%2.4f'%(Vg)+'_Vds=%2.4f'%(Vds)+'.txt'
                            
                            np.savetxt(os.path.join(spectra_fol, spectrum_file), np.transpose(table))
    
                        #mesure time
                        remain_time_min = remain_time_min - ( stabilise_time * (c1.total_sweep_time_ms*1e3 if src_vna == 'zva67' else 1) / 60)
                        progress_percent = (sweeptime_min - remain_time_min) / sweeptime_min * 100
    
                        first_pass=False

        print("++++++++++++++++++++++++++++++++++++++++")
        print("Stopping measurement")
        print("........................................")
      
        return locals()

    def tidy_up(self):
        self.end_saving()
        
        print("Setting all voltages to zero")
        self.sourceVds.set_voltage(0.)
        self.sourceVg.set_voltage(0.)
        if self.sourceVchuck is not None:
            self.sourceVchuck.set_voltage(0.)    
        
        print("===================================")
        print("Ending acquisition script")
        print("****************************************")

if __name__ == "__main__":
    m = Measurement()
    m.run()