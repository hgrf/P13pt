# -*- coding: utf-8 -*-
import numpy as np
from math import pi
import matplotlib.pyplot as plt
from glob import glob
from scipy.linalg import sqrtm
from numpy.linalg import inv

# Definition of constants:
EPSILON_0 = 8.854187e-12  # Farads per meter.

Z0 = 50.0  # Ohms


class measurement(object):
    """Defines the class of measurements.
    
    Parameters
    ----------
    from_file : path
        A file-path containing the S parameters from a VNA measurement.
    from_s : np.array
        The S parameters from which a new measurement instance should be 
        created. Requires to pass parent_meas.
    parent_meas : measurement instance
        When creating an instance using calculated S-parameters, 
        pass the original measurement instance.

    Attributes
    ----------
    s : ndarray (2x2)
        A 2x2 matrix where each element contains a vector with the corresponding
        S_11, S_12 etc. for each frequency
    """
    
    def __init__(self,from_file = None, from_s = None, parent_meas = None):
        if from_file:   
            filename = from_file
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
            elif filename.find('Vgate=')!=-1: 
                self.v_g = float(filename[filename.find('Vgate=')+6:
                                        filename.find('Vgate=')+14])
                                        
                self.v_ds = float(filename[filename.find('Vyoko=')+6:
                                        filename.find('Vyoko=')+14])
            elif filename.find('Vg1_')!=-1:
                toks = filename.split('_')
                for i, t in enumerate(toks):
                    if t=='Vg1': self.v_g = float(toks[i+1])
                    if t=='Vds': self.v_ds = float(toks[i+1].strip('.txt'))
            else:
                self.v_g = None
                self.v_ds = None                
#                raise Exception
            
                
        
        elif from_s is not None:
            # Check that a parent measurement is passed.
            assert parent_meas != None
            # Inherit frequencies from parent
            self.freq = parent_meas.freq
            self.w = parent_meas.w
            
            # Create S-matrix from passed argument
            self.s = from_s
            
            # Inherit DC data
            self.v_g = parent_meas.v_g
            self.v_ds = parent_meas.v_ds
        
        else: 
            print "Too few parameters. Cannot create measurement instance."

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
        s11, s12, s21, s22 = s[0,0], s[0,1], s[1,0], s[1,1]
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
        delta = a + b*y0 + c*z0 + d
        s[0,0] = (a + b*y0 - c*z0 - d)/delta
        s[0,1] = (2.0*(a*d - b*c))/delta
        s[1,0] = 2.0/delta
        s[1,1] = (-a + b*y0 - c*z0 + d)/delta
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
        
        Attributes
        ----------
        self.y: numpy.array
            The y-matrices as an atribute in the format "Matrix of vectors".
        """
        self.y = self.s2y(self.s)

    def mov2vom(self, mat): 
        """Transform matrix of vectors to vector of matrices.
        
        This method is useful for the deembedding procedure. 
        RF-data (S,Y,etc.) is usually stored as a matrix containing the 
        vectors Mat11, Mat22, etc. where each vector element corresponds to 
        a given frequency. This method transforms the data into a vector 
        (each element corresponds to a given frequency) whose elements are 
        the matrices.
        
        Parameters
        ----------
        mat: numpy.array
            The matrix of vectors.
        
        Returns
        -------
        vec: numpy.array
            The vector of matrices.
        """
        return np.array([mat[:,:,i] for i in range(len(mat[0,0]))])
    
    def vom2mov(self, vec):
        """Transform a vector of matrices to a matrix of vectors.
        
        Inverse method to mov2vom.
        
        Parameters
        ----------
        vec: numpy.array
            A vector of matrices.
            
        Returns
        -------
        mat: numpy.array
            A matrix of vectors.
        """
        num = len(vec)
        mat = np.empty((2,2,num), dtype= complex)
        for row in range(2):
            for column in range(2):
                mat[row, column] = np.array([vec[i, row, column] for i in range(num)])
        return mat

    def deembed_thru(self, thru):
        """Deembed the propagation along a measured thruline.
        
        Parameters
        ----------
        thru: measurement object
            The thru object that shall be used for deembedding. 
            Must be created in the main program prior to 
            execution of this function.
            
        Returns
        ----------
        deembeded_s: numpy.array
            The samples' S-parameters after thruline deembedding.
        """
        # Get the ABCD matric in Vector of matrix form for the thru.
        thru_abcd = self.mov2vom(self.s2abcd(thru.s))
        # Get the ABCD matric in Vector of matrix form for the measurement.
        sample_abcd = self.mov2vom(self.s2abcd(self.s))
        # The ABCD matrix of "half a thruline".
        half_thru = np.array(map(sqrtm,thru_abcd))
        # Invert the ABCD matrix of "half a thruline" for each frequency.
        inv_half_thru = np.array(map(inv,half_thru))
        # Multiply the inverse of the "half-thrus" on both sides to the 
        # samples' ABCD matrix and store the result in mov-format.
        three_mat_multiplication = lambda x,y,z: np.dot(np.dot(x,y),z)
        deembeded_abcd = self.vom2mov(np.array(map(three_mat_multiplication,
                                      inv_half_thru,sample_abcd, inv_half_thru)))
        # Calculate the deembedded S parameters as an attribute in mov-format.
        deembeded_s = self.abcd2s(deembeded_abcd)
        return measurement(from_s = deembeded_s, parent_meas = self)
    
    def plot_mat_spec(self,matrix,pltnum=1,ylim=1.1,legendlabel=0.0,ylabel="M"):
        """Plot selected parameter (S, Y) in a 2x2 panel.
    
        Arguments
        ----------
        matrix : matrix of vectors
            For example measurement.s or measurement.y
        pltnum : int
            The number of the plot. Defaults to 1. Choose other number if you want
            to plot in a different figure.
        ylim : float
            The limits (positive and negative) for the y-axis.
        legendlabel : float
            Define if you are plotting for different Vg.
        ylabel : string
            Define the label of the y-axes.
    
        Returns
        -------
        nothing
    
        """
        fig = plt.figure(pltnum,figsize=(15.0, 10.0))
        for i in range(2):
            for j in range(2):
                plotnum = 2*i+j+1 #add_subplot needs the +1 as indexing starts with 1
                ax = fig.add_subplot(2,2,plotnum)
                ax.plot(self.freq/1e9, matrix[i,j].real, label = 'Real, V$_g$=%.2fV'%legendlabel)
                ax.plot(self.freq/1e9, matrix[i,j].imag, label = 'Imag, V$_g$=%.2fV'%legendlabel)
                ax.set_xlabel('f [GHz]')
                ax.set_ylabel(ylabel+r'$_{%d%d}$'%(i+1,j+1))
                ax.set_ylim([-ylim,ylim])             
        plt.tight_layout()               


if __name__ == '__main__':
    """Example of how to use the measurement class.    
        Plots all spectra obtained for a sweep in Vgate.
    """
    dir_sample = r'D:\Users\inhofer\Documents\shared_for_measurements\Dresden2\Cx2\2014-07-21_18h06m00s_Dresden2_Cx2_Vgsweep_0_-0.6V'
    
    f_list = (glob(dir_sample + '/*/S-parameter/*.txt') + glob(dir_sample + '/S-parameter/*.txt'))


    # Import thru    
    dir_thru = r'D:\Users\inhofer\Documents\shared_for_measurements\Dresden2\Cx2\2014-07-21_18h06m00s_Dresden2_Cx2_Vgsweep_0_-0.6V'
    thru_list = (glob(dir_thru + '/*/S-parameter/*.txt') + glob(dir_thru + '/S-parameter/*.txt'))
    thru = measurement(thru_list[0])

    
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
    
    print f_list
    plt.close('all')
    v_g = []
    r = []
    
    # iterate over all gate voltages
    for filename in f_list[:1:]:
        print filename
        spectrum = measurement(filename)
        spectrum.create_y()
        spectrum.plot_mat_spec(spectrum.y,ylim = 1,ylabel="Y")
        spectrum.deembed_thru(thru)
        
        
        
        