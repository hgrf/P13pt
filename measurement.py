# -*- coding: utf-8 -*-
import numpy as np
from math import pi
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
    
    s2y: Extracts Y parameter from the data.
        
        Created attributes:
        
            y: A 2x2 matrix where each element contains a vector with the corresponding
               Y_11, Y_12 etc. for each frequency
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
        delta_s = (1.0+s11)*(1.0+s22) - (s12*s21)
        self.y[0,0] = y0*((1.0-s11)*(1.0+s22) + s12*s21)/delta_s
        self.y[0,1] = y0*(-2.0*s12)/delta_s
        self.y[1,0] = y0*(-2.0*s21)/delta_s
        self.y[1,1] = y0*((1.0+s11)*(1.0-s22) + s12*s21)/delta_s
    
    def plot_mat_spec(self,mat_type,pltnum=1,ylim=1.1,legendlabel=0.0):
        mattype_dict = {"y" : self.y,
                        "s" : self.s}
                        
        mat = mattype_dict[mat_type]
        
        fig = plt.figure(pltnum,figsize=(15.0, 10.0))
        for i in range(2):
            for j in range(2):
                plotnum = 2*i+j+1 #add_subplot needs the +1 as indexing starts with 1
                ax = fig.add_subplot(2,2,plotnum)
                ax.plot(self.freq/1e9, mat[i,j].real, label = 'Real, V$_g$=%.2fV'%legendlabel)
                ax.plot(self.freq/1e9, mat[i,j].imag, label = 'Imag, V$_g$=%.2fV'%legendlabel)
                ax.set_xlabel('f [GHz]')
                ax.set_ylabel(mat_type.upper() + '$_\mathrm{%d%d}$'%(i+1,j+1))
                ax.set_ylim([-ylim,ylim])             
                
        plt.tight_layout()               


if __name__ == '__main__':
    dir_sample = r'../TR10/Janis 11K 2016-01-21/RF/recalibre/2016-01-21_21h11m21s_Vg_sweep'
    
    f_list = (glob(dir_sample + '/*/S-parameter/*.txt') + glob(dir_sample + '/S-parameter/*.txt'))
    
    # helper function to enable sorting by Vg in filename
    def sorting(name):
        if name.find('Vg1=')!=-1:
            vg = float(name[name.find('Vg1=')+4:
                                    name.find('Vg1=')+12])
        else: 
            vg = float(name[name.find('Vgate=')+6:
                                    name.find('Vgate=')+14])
        if 'return' in name: vg += 1000         # shift up return sweep
        return vg    
    
    # use helper function to sort file list
    f_list = sorted(f_list, key=sorting)
    
    plt.close('all')
    v_g = []
    r = []
    
    # iterate over all gate voltages
    for filename in f_list:
        spectrum = measurement(filename)
        spectrum.s2y()
        spectrum.plot_mat_spec("y",ylim = 1)
