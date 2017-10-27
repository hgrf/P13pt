# -*- coding: utf-8 -*-
"""
 Interface for the scikit-rf Network class for use in P13.
 * Adding P13 spectrum file format support to the base class.
 * Adding P13 style thru deembedding support to the base class.
 
 De-embedding algorithm and original idea: Andreas Inhofer
 Code clean-up: Holger Graef
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.linalg import sqrtm
from numpy.linalg import inv
from params_from_filename import params_from_filename
from copy import deepcopy
import os
import skrf
from skrf import a2s as abcd2s
from skrf import s2a as s2abcd        

# compatible with scikit-rf version 0.14.5
class Network(skrf.Network):
    """
    Represents a n-port microwave network.
    
    This class is an interface for scikit-rf's Network class, adding support
    for the "P13 standard" of saving 2 port network data (see below), which
    is different from the touchstone format used by mwavepy.
    
    Refer to scikit-rf's documentation for more detail.
    """
    def __init__(self, file=None, params=None, z0=50.0, **kwargs):
        self.params = dict()
         
        if file:
            # update parameters dictionary from filename
            self.params.update(params_from_filename(file))       
    
            # in the following, we will check if we let skrf handle the file
            # or if we do it ourselves
            
            # check if we are dealing with a touchstone file ".sNp"
            is_skrf_compatible = False
            ext = file.split('.')[-1].lower()
            if ext[0] == 's' and ext[-1] == 'p':
                try:
                    n = int(ext[1:-1])
                    is_skrf_compatible = True
                except ValueError:
                    is_skrf_compatible = False
            
            # check if we are dealing with a pickle file
            if ext in ['.ntwk', '.p']:
                is_skrf_compatible = True
                
            if is_skrf_compatible:
                # use mwavepy constructor and pass on touchstone_file
                super(Network, self).__init__(file=file)
            else:
                # call base class constructor
                super(Network, self).__init__(z0=z0)
                # read S parameters from file
                # we will assume the file is compatible with numpy.genfromtxt,
                # that we are dealing with a 2 port network and the values
                # are stored in the order f, Real(S11), Imag(S11) and so forth
                # for S12, S21, S22 ("P13 standard")
                self.raw = np.genfromtxt(file).T
                
                if len(self.raw) != 9:
                    raise Exception('Invalid number of columnns')
                
                self.frequency.unit = 'hz'
                self.f = self.raw[0]
                self.name = os.path.basename(os.path.splitext(file)[0])                
                
                # S-matrix is created as a len(f)x2x2 matrix, see below for
                # a comment on this shape
                self.s = np.empty((len(self.f),2,2), dtype=complex)
                self.s[:,0,0] = self.raw[1] + 1j*self.raw[2]
                self.s[:,0,1] = self.raw[3] + 1j*self.raw[4]
                self.s[:,1,0] = self.raw[5] + 1j*self.raw[6]
                self.s[:,1,1] = self.raw[7] + 1j*self.raw[8]
            
        else:
            # pass all arguments to skrf constructor
            super(Network, self).__init__(z0=z0, **kwargs)
        
        # update parameters dictionary from function argument
        if params is not None:
            self.params.update(params)
    
    @property
    def w(self):
        # omega is calculated automatically in base class using Frequency class
        return self.frequency.w

    def deembed_thru(self, thru):
        """De-embed the propagation towards the active region of the DUT.
        
        Calculate the S matrix of "half a thru" by taking the matrix square
        root of the ABCD matrix of the thru network. The inverse of the result
        is multiplied on both sides of the DUT ABCD matrix, which is then
        converted back to S.
    
        Arguments
        ---------
        thru : Network object
            the thru network
        
        Returns
        -------
        dut_deembedded : Network object
            the deembedded DUT network
        """
        dut_abcd = s2abcd(self.s)
        half_thru_abcd = np.array(map(sqrtm, s2abcd(thru.s)))
        half_thru_inv = np.array(map(inv, half_thru_abcd))
        three_mat_multiplication = lambda x,y,z: np.dot(np.dot(x,y),z)
        deembedded_abcd = np.array(map(three_mat_multiplication,
                                      half_thru_inv, dut_abcd, half_thru_inv))
        dut_deembedded = deepcopy(self)
        dut_deembedded.s = abcd2s(deembedded_abcd)
        
        return dut_deembedded

    def plot_mat(self,parameter='s',fig=None,ylim=1.1):
        """Plot selected parameter (S, Y) in a 2x2 panel.
    
        Arguments
        ----------
        parameter : string
            's' or 'y'
        fig : matplotlib figure handle or None
            plots on existing figure or creates new one
        ylim : float
            The limits (positive and negative) for the y-axis.
    
        Returns
        -------
        figure handle
    
        """
        if parameter not in ['s', 'y']:
            raise Exception('Invalid parameter.')
        matrix = getattr(self, parameter)
        if fig is None:
            fig = plt.figure(figsize=(15.0, 10.0))
        for i in range(2):
            for j in range(2):
                subplotnum = 2*i+j+1 # add_subplot needs the +1 as indexing starts with 1
                ax = fig.add_subplot(2,2,subplotnum)
                ax.plot(self.f/1e9, matrix[:,i,j].real)
                ax.plot(self.f/1e9, matrix[:,i,j].imag)
                ax.set_xlabel('f [GHz]')
                ax.set_ylabel(parameter.upper()+r'$_{%d%d}$'%(i+1,j+1))
                ax.set_ylim([-ylim,ylim])    
                ax.set_xlim([min(self.f/1e9), max(self.f/1e9)])
        plt.tight_layout()                  


# for compatibility with old name
rfspectrum = Network
    

def convert_to_touchstone(filename, newfilename):
    """Convert a "P13 standard" file to a touchstone file (.s2p)

    Arguments
    ----------
    filename : string
        File name of the "P13 standard" file.
    newfilename : string
        File name of the new (.s2p) file

    Returns
    -------
    Nothing.

    """
    
    # see also http://na.support.keysight.com/plts/help/WebHelp/FilePrint/SnP_File_Format.htm    
    
    # read data
    with open(filename, 'r') as old_file: 
        # create new file with '.s2p' extension
        with open(newfilename, 'w') as new_file:
            new_file.write('# hz s ri r 50\n')
            for line in old_file.readlines():
                values = line.strip().split(' ')
                if not len(values) == 9:    # 1 for freq, 2x4 for S parameters
                    raise Exception('Invalid number of columns')
                # in old format we have f, S11, S12, S21, S22
                # in touchstone we need f, S11, S21, S12, S22
                new_order = [0, 1, 2, 5, 6, 3, 4, 7, 8]
                values = [values[i] for i in new_order]
                line = ' '.join(values)
                new_file.write(line+'\n')
        
