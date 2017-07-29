# -*- coding: utf-8 -*-
# rfspectrum class written by Andreas Inhofer and Holger Graef

import numpy as np
from math import pi
import matplotlib.pyplot as plt
from glob import glob
from scipy.linalg import sqrtm
from numpy.linalg import inv
from params_from_filename import params_from_filename


# Definition of constants:
EPSILON_0 = 8.854187e-12  # Farads per meter.

Z0 = 50.0  # Ohms


class rfspectrum(object):
    """Defines the class of RF spectra.
    
    Parameters
    ----------
    from_file : path
        A file-path containing the S parameters from a VNA measurement.
    from_s : np.array
        The S parameters from which a new rfspectrum instance should be 
        created. Requires to pass a frequency list and optionally a parameter
        dictionary.
    f : np.array
        The frequency list to be passed along if S parameters are read from
        an array.
    params : dict
        To be passed along optionally.


    Attributes
    ----------
    s : ndarray (2x2)
        A 2x2 matrix where each element contains a vector with the corresponding
        S_11, S_12 etc. for each frequency
    """
    
    def __init__(self,from_file = None, from_s = None, f = None, params = None):
        self.params = dict()        
        
        if from_file is not None:   
            filename = from_file
            with open(filename, 'r') as current_file:
                self.raw = np.genfromtxt(current_file).T
    
            # Frequencies
            self.f = self.raw[0]
            self.w = 2.*pi*self.f
            
            # S-matrix is created as a 2x2 matrix containing vectors.
            self.s = np.empty((2,2,len(self.f)), dtype= complex)
            self.s[0,0] = self.raw[1] + 1j*self.raw[2]
            self.s[0,1] = self.raw[3] + 1j*self.raw[4]
            self.s[1,0] = self.raw[5] + 1j*self.raw[6]
            self.s[1,1] = self.raw[7] + 1j*self.raw[8]
            
            self.params.update(params_from_filename(filename))
            
        
        elif from_s is not None:
            # Check that a frequency list is passed.
            assert f is not None
            # Inherit frequencies from parent
            self.f = f
            self.w = 2.*pi*f
            
            # Create S-matrix from passed argument
            self.s = from_s
        
        else: 
            print "Too few parameters. Cannot create rfspectrum instance."
            
        if params is not None:
            self.params.update(params)

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
        """Create the Y matrices as an attribute of the rfspectrum object.
        
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
        thru: rfspectrum object
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
                                      inv_half_thru, sample_abcd, inv_half_thru)))
        # Calculate the deembedded S parameters as an attribute in mov-format.
        deembeded_s = self.abcd2s(deembeded_abcd)
        return rfspectrum(from_s = deembeded_s, f = self.f, params = self.params)
    
    def plot_mat(self,matrix,pltnum=1,ylim=1.1,ylabel="M"):
        """Plot selected parameter (S, Y) in a 2x2 panel.
    
        Arguments
        ----------
        matrix : matrix of vectors
            For example rfspectrum.s or rfspectrum.y
        pltnum : int
            The number of the plot. Defaults to 1. Choose other number if you want
            to plot in a different figure.
        ylim : float
            The limits (positive and negative) for the y-axis.
        ylabel : string
            Define the label of the y-axes.
    
        Returns
        -------
        nothing
    
        """
        fig = plt.figure(pltnum,figsize=(15.0, 10.0))
        for i in range(2):
            for j in range(2):
                subplotnum = 2*i+j+1 #add_subplot needs the +1 as indexing starts with 1
                ax = fig.add_subplot(2,2,subplotnum)
                ax.plot(self.f/1e9, matrix[i,j].real)
                ax.plot(self.f/1e9, matrix[i,j].imag)
                ax.set_xlabel('f [GHz]')
                ax.set_ylabel(ylabel+r'$_{%d%d}$'%(i+1,j+1))
                ax.set_ylim([-ylim,ylim])             
        plt.tight_layout()               


if __name__ == '__main__':
    """Example of how to use the rfspectrum class.    
        Plots all spectra obtained for a sweep in Vgate.
    """
    f_list = glob('testdata/*.txt')

    # Import thru    
    #dir_thru = r'D:\Users\inhofer\Documents\shared_for_measurements\Dresden2\Cx2\2014-07-21_18h06m00s_Dresden2_Cx2_Vgsweep_0_-0.6V'
    #thru_list = (glob(dir_thru + '/*/S-parameter/*.txt') + glob(dir_thru + '/S-parameter/*.txt'))
    #thru = rfspectrum(thru_list[0])  
    
    # use helper function to sort file list
    sorting = lambda filename: float(params_from_filename(filename)['Vg1'])
    f_list = sorted(f_list, key=sorting)
    
    plt.close('all')
    v_g = []
    r = []
    
    # iterate over all gate voltages
    for filename in f_list:
        print filename
        spectrum = rfspectrum(filename)
        spectrum.create_y()
        spectrum.plot_mat(spectrum.y,ylim=1e-4,ylabel="Y")
        #spectrum.deembed_thru(thru)
        
        
        
        