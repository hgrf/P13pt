# -*- coding: utf-8 -*-
import numpy as np
from math import pi
from numpy import exp
import matplotlib.pyplot as plt
from glob import glob


    

# Definition of constants:
EPSILON_0 = 8.854187e-12  # Farads per meter.

Z0 = 50.0  # Ohms

class measurement(object):
    '''Defines the class of measurements.
    
    The object is initialised the raw S-measurement data. 
    The data filename needs to be passed as argument.
    
    *********

    Methods:
    
    scattering: Extracts useful information from the data.
        
        Created attributes:
        
            freq: The frequencies from the measurement.
        
            w: The corresponding angular frequencies.
        
            s11, s12, s21, s22: The complex scattering parameters.
    
    admittance: Transforms the scattering parameters to admittance parameters.
        
        Created attributes:
        
            y11, y12, y21, y22: The complex admittance parameters.
        
    impedance: Transforms the scattering parameters to impedance parameters.
        Created attributes:
        
            z11, z12, z21, z22: The complex admittance parameters. 
        
    direct_fit: Performs a fit to the data based on a model 
        consisting of a parallel reistance, the AlOx capacitance, 
        a capacitive contribution from the BiTe and a frequency dependent 
        resistance of the BiTe. 
        (The frequency dependence is based on a Drude model.)
        
        Created attributes: 
        
            c_alox, r_par, g0, tau, c_bite
    '''
    
    def __init__(self,filename):
        with open(filename, 'r') as current_file:
            self.raw = np.genfromtxt(current_file).T

        # Frequencies
        self.freq = self.raw[0]
        self.w = 2. * pi * self.freq
        
        # S-matrix is created as a 2x2 matrix containing vectors.
        self.s = np.zeros((2,2), dtype= np.ndarray)
        self.s[0,0] = self.raw[1] + 1j*self.raw[2]
        self.s[0,1] = self.raw[3] + 1j*self.raw[4]
        self.s[1,0] = self.raw[5] + 1j*self.raw[6]
        self.s[1,1] = self.raw[7] + 1j*self.raw[8]
        
        # DC data read from filename
        if filename.find('Vg1=')!=-1:
            self.v_g = float(filename[filename.find('Vg1=')+4:
                                    filename.find('Vg1=')+12])
                                    
            self.v_ds = float(filename[filename.find('Vds=')+4:
                                    filename.find('Vds=')+12])
        else: 
            self.v_g = float(filename[filename.find('Vgate=')+6:
                                    filename.find('Vgate=')+14])
                                    
            self.v_ds = float(filename[filename.find('Vyoko=')+6:
                                    filename.find('Vyoko=')+14]) 

    def scattering(self):
        self.freq = self.raw[0]
        self.w = 2. * pi * self.freq
        self.s11 =  (self.raw[1] + 1j * self.raw[2])
        self.s12 =  (self.raw[3] + 1j * self.raw[4])
        self.s21 =  (self.raw[5] + 1j * self.raw[6])
        self.s22 =  (self.raw[7] + 1j * self.raw[8])
    
    def s2y(self):
        '''
        Creates the y matrices from s-matrices
        '''
        self.y = np.zeros((2,2), dtype= np.ndarray)
        y0 = 0.02
        s11 = self.s[0,0]
        s12 = self.s[0,1]
        s21 = self.s[1,0]
        s22 = self.s[1,1]
        d1 = (1.0+s11)*(1.0+s22) - (s12*s21)
        self.y[0,0] = y0*((1.0-s11)*(1.0+s22) + s12*s21)/d1
        self.y[0,1] = y0*(-2.0*s12)/d1
        self.y[1,0] = y0*(-2.0*s21)/d1
        self.y[1,1] = y0*((1.0+s11)*(1.0-s22) + s12*s21)/d1
        
    def admittance(self):
        self.scattering()
        delta_s = (1 + self.s11) * (1 + self.s22) - self.s12 * self.s21
        self.y11 = (((1 - self.s11) * (1 + self.s22) + self.s12 * self.s21) 
                       / (Z0 * delta_s))         
        self.y12 =  -2 * self.s12 / (Z0 * delta_s) 
        self.y21 =  -2 * self.s21 / (Z0 * delta_s)
        self.y22 = (((1 + self.s11) * (1 - self.s22) + self.s12 * self.s21) 
                       / (Z0 * delta_s))
    
    def impedance(self):
        self.scattering()    
        delta_s = (1 - self.s11) * (1 - self.s22) - self.s12 * self.s21
        self.z11 = Z0 * (((1 + self.s11) * 
            (1 - self.s22) + self.s12 * self.s21) / delta_s)
        self.z12 = 2 * Z0 * self.s12 / delta_s
        self.z21 = 2 * Z0 * self.s21 / delta_s
        self.z22 = Z0 * (((1 - self.s11) * 
            (1 + self.s22) + self.s12 * self.s21) / delta_s)
    
    def plot_mat_spec(self,mat_type,pltnum=1,matname='M',ylim=1.1,showlabel = True, 
                      legendlabel=0.0,xlabel_str='f [GHz]', ylabel_str=' ',
                        savedir=r'D:\\test.png'):
        mattype_dict = {"y" : self.y,
                        "s" : self.s,
                        }
                        
        mat = mattype_dict[mat_type]
        
        fig2 = plt.figure(pltnum,figsize=(15.0, 10.0))
        plt.suptitle(matname +'-spectrum')
        for i in range(2):
            for j in range(2):
                plotnum = 2*i+j+1 #add_subplot needs the +1 as indexing starts with 1
                ax = fig2.add_subplot(2,2,plotnum)
                ax.plot(self.freq/1e9, mat[i,j].real, label = 'Real, V$_g$=%.2fV'%legendlabel)
                ax.plot(self.freq/1e9, mat[i,j].imag, label = 'Imag, V$_g$=%.2fV'%legendlabel)
                ax.set_xlabel(xlabel_str)
                ax.set_ylabel(ylabel_str)
                ax.set_ylim([-ylim,ylim]) 
                ax.set_title(matname + '$_\mathrm{%d%d}$'%(i+1,j+1))                
        
        if showlabel == True:
            lgd = plt.gcf().get_axes()[0].legend()
        plt.tight_layout()               



              
if __name__ == '__main__':
    plt.close('all')
    dir_sample = r'D:\Measurement Andreas\HgTe CAPA wet\2016-02-01_test_before_cooldown\HfO2\2016-02-01_17h43m46s_fullS_-25dBm'
    f_list = (glob(dir_sample + '/*/S-parameter/*.txt') +
                glob(dir_sample + '/S-parameter/*.txt'))

    for filename in f_list[0:1]:
        spectrum = measurement(filename)
        spectrum.s2y()
        spectrum.plot_mat_spec("y",ylim = 0.14,ylabel_str="Y",showlabel=True)