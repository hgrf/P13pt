# -*- coding: utf-8 -*-
import numpy as np
from math import pi
import matplotlib.pyplot as plt
from glob import glob

# Definition of constants:
EPSILON_0 = 8.854187e-12  # Farads per meter.

Z0 = 50.0  # Ohms


class measurement(object):
    """Defines the class of measurements.
    
    The object is initialised with the raw S-measurement data. 
    The data filename needs to be passed as argument.

    Parameters
    ----------
    s : ndarray (2x2)
        A 2x2 matrix where each element contains a vector with the corresponding
        S_11, S_12 etc. for each frequency
    y : ndarray (2x2)
        A 2x2 matrix where each element contains a vector with the corresponding
        Y_11, Y_12 etc. for each frequency

    Methods
    -------
    s2y :
        Compute Y parameter from the S parameter data and store in attribute y.

    """
    
    def __init__(self,filename):
        with open(filename, 'r') as current_file:
            self.raw = np.genfromtxt(current_file).T

        # Frequencies
        self.freq = self.raw[0]
        self.w = 2. * pi * self.freq
        
        # S-matrix is created as a 2x2 matrix containing vectors.
        self.s = np.empty((2,2,len(self.freq)), dtype= complex)
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
    
    def s2y(self, s):
        """Compute the Y matrices from the S matrices for each frequency.
    
        Arguments
        ----------
        s: numpy.array
            An array containing complex S parameters in the format 
            defined by the __init__ method.
    
        Returns
        -------
        y: numpy.array
            An array containing complex Y parameters in the format 
            defined by the __init__ method.
        """
        y = np.empty((2,2,len(s[0,0])), dtype= complex)
        y0 = 0.02
        s11, s12, s21, s22 = s[0,0], s[0,1], s[1,0], s[1,1]
        delta_s = (1.0+s11)*(1.0+s22) - (s12*s21)
        y[0,0] = y0*((1.0-s11)*(1.0+s22) + s12*s21)/delta_s
        y[0,1] = y0*(-2.0*s12)/delta_s
        y[1,0] = y0*(-2.0*s21)/delta_s
        y[1,1] = y0*((1.0+s11)*(1.0-s22) + s12*s21)/delta_s
        return y
        
    def y2s(self,y):
        """Compute the S matrices from the Y matrices for each frequency.
    
        Arguments
        ----------
        y: numpy.array
            An array containing complex Y parameters in the format 
            defined by the __init__ method.
    
        Returns
        -------
        s: numpy.array
            An array containing complex S parameters in the format 
            defined by the __init__ method.
        """
        s = np.empty((2,2,len(y[0,0])), dtype= complex)
        y0 = 0.02
        y11, y12, y21, y22 = y[0,0], y[0,1], y[1,0], y[1,1]
        d = (y0 + y11)*(y0+y22) - (y12*y21)
        s[0,0]= ((y0-y11)*(y0+y22) + y12*y21)/d
        s[0,1]= (-2.0*y12*y0)/d
        s[1,0]= (-2.0*y21*y0)/d
        s[1,1]= ((y0+y11)*(y0-y22) + y12*y21)/d
        return s
        
    def s2abcd(self,s):
        """Compute the ABCD matrices from the S matrices for each frequency.
    
        Arguments
        ----------
        s: numpy.array
            An array containing complex Y parameters in the format 
            defined by the __init__ method.
    
        Returns
        -------
        abcd: numpy.array
            An array containing complex ABCD parameters in the format 
            defined by the __init__ method.
        """   
        abcd = np.empty((2,2,len(s[0,0])), dtype= complex)
        y0 = 0.02
        z0 = 50.0
        s11,s12,s21,s22 = s[0][0],s[0][1],s[1][0],s[1][1]
        abcd[0,0] = ((1.0+s11)*(1.0-s22) + s12*s21)/(2.0*s21)
        abcd[0,1] = z0 * ((1.0+s11)*(1.0+s22) - s12*s21)/(2.0*s21)
        abcd[1,0] = y0 * ((1.0-s11)*(1.0-s22) - s12*s21)/(2.0*s21)
        abcd[1,1] = ((1.0-s11)*(1.0+s22) + s12*s21)/(2.0*s21)
        return abcd
    
    def abcd2s(self,abcd):
        """Compute the S matrices from the ABCD matrices for each frequency.
    
        Arguments
        ----------
        abcd: numpy.array
            An array containing complex Y parameters in the format 
            defined by the __init__ method.
    
        Returns
        -------
        s: numpy.array
            An array containing complex ABCD parameters in the format 
            defined by the __init__ method.
        """    
        s = np.empty((2,2,len(abcd[0,0])), dtype= complex)
        y0 = 0.02
        z0 = 50.0
        a, b, c, d = abcd[0,0], abcd[0,1], abcd[1,0], abcd[1,1]
        d = a + b*y0 + c*z0 + d
        s[0,0] = (a + b*y0 - c*z0 - d)/d
        s[0,1] = (2.0*(a*d - b*c))/d
        s[1,0] = 2.0/d
        s[1,1] = (-a + b*y0 - c*z0 + d)/d
        return s
        
    def y2abcd(self,y):
        """Compute the ABCD matrices from the Y matrices for each frequency.
    
        Arguments
        ----------
        y: numpy.array
            An array containing complex Y parameters in the format 
            defined by the __init__ method.
    
        Returns
        -------
        abcd: numpy.array
            An array containing complex ABCD parameters in the format 
            defined by the __init__ method.
        """            
        return self.s2abcd(self.y2s(y))
        
    def abcd2y(self,abcd):
        """Compute the Y matrices from the ABCD matrices for each frequency.
    
        Arguments
        ----------
        abcd: numpy.array
            An array containing complex Y parameters in the format 
            defined by the __init__ method.
    
        Returns
        -------
        y: numpy.array
            An array containing complex ABCD parameters in the format 
            defined by the __init__ method.
        """            
        return self.s2y(self.abcd2s(abcd))
    
    def create_y(self):
        """Create the Y matrices as an attribute of the measurement object.
        """
        self.y = self.s2y(self.s)
        
    
    def plot_mat_spec(self,mat_type,pltnum=1,ylim=1.1,legendlabel=0.0):
        """Plots selected parameter (S, Y) in a 2x2 panel.
    
        Arguments
        ----------
        mat_type : string
            Select 'y' or 's' for the corresponding parameter to plot.
        pltnum : int
            The number of the plot. Defaults to 1. Choose other number if you want
            to plot in a different figure.
        ylim : float
            The limits (positive and negative) for the y-axis.
        legendlabel : float
            Define if you are plotting for different Vg.
    
        Returns
        -------
        nothing
    
        """
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
    """Example of how to use the measurement class.    
        Plots all spectra obtained for a sweep in Vgate.
    """
    dir_sample = r'C:\Users\Andreas\Documents\shared_for_measurements\Dresden2\Cx2\2014-07-21_18h06m00s_Dresden2_Cx2_Vgsweep_0_-0.6V'
    
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
        spectrum.create_y()
        spectrum.plot_mat_spec("y",ylim = 1)