# -*- coding: utf-8 -*-
"""
Convert to ng and mu.

A small programm containing functions 
that takes "calculated" data and converts to gate charge and 
chemcial potential.
"""
import numpy as np

def calc_mu(vg,ctot,cgeo,vg_ref = 0.0,use_ref_index = False, ref_index = 0):
    '''
    Calculate the surface fermi level.
    
    Parameters
    ----------
    vg: np.ndarray
        An array containing the values of gate voltages
        
    ctot: np.ndarray
        An array containing the values of measured total capa per area
    
    cgeo: float
      The geometric/oxide capacitance.
    
    vg_ref: float (optional)
        The value of gate voltage corresponding to the origin 
        of the energy scale. Default is Vg=0V.
        
    use_ref_index: bool (optional)
        If True use the index specified in the ref_index variable as reference 
        for the origin of energies. Default is False.
        
    ref_index: int
        Specified index if use_ref_index is True.
    

    Returns
    -------
    mu: ndarray
        The surface chemical potential (in eV).
    '''
    dvg = np.diff(vg)
    dvg = np.append(dvg,dvg[-1])
    if use_ref_index:
        ref_pos = ref_index
    else:
        ref_pos = np.argmin(np.abs(vg-vg_ref))
    mu_pos = [np.sum((1.-ctot[ref_pos:i]/cgeo)*dvg[ref_pos:i]) for i in range(ref_pos, len(vg))]
    mu_neg = [-np.sum((1.-ctot[i:ref_pos]/cgeo)*dvg[i:ref_pos]) for i in range(ref_pos)]
    mu = np.array(mu_neg + mu_pos)
    return mu

def calc_ng(vg,ctot,vg_ref = 0.0,use_ref_index = False, ref_index = 0):
    '''
    Calculate the fermi level and the charge carrier density on the gate.
    
    Parameters
    ----------
    vg: np.ndarray
        An array containing the values of gate voltages
        
    ctot: np.ndarray
        An array containing the values of measured total capa per area
    
    vg_ref: float (optional)
        The value of gate voltage corresponding to the origin 
        of the energy scale. Default is Vg=0V.

    use_ref_index: bool (optional)
        If True use the index specified in the ref_index variable as reference 
        for the origin of energies. Default is False.
        
    ref_index: int
        Specified index if use_ref_index is True.
        
    Returns
    -------
    ng: ndarray
        The total charge on the gate [in 10^12/cm^2].
    '''
    dvg = np.diff(vg)
    dvg = np.append(dvg,dvg[-1])
    if use_ref_index:
        ref_pos = ref_index
    else:
        ref_pos = np.argmin(np.abs(vg-vg_ref))
    
    ctimesdvg = ctot*dvg
    neg_ng = [-np.sum(ctimesdvg[i:ref_pos]) for i in range(ref_pos)]
    pos_ng = [np.sum(ctimesdvg[ref_pos:i]) for i in range(ref_pos,len(vg))]
    ng = np.array(neg_ng+pos_ng)/1.6e-19/1e16
    return ng
    
def calc_cq(ctot,cgeo):
    '''
    Calculate the quantum capacitance.
    
    Parameters:
    -----------
    ctot: np.ndarray
        The list of measured capacitance values.
    cgeo: float
        The geometrical capacitance.
    
    Returns:
    --------
    cq: np.ndarray
        The quantum capacitance.
    '''
    return 1./(1./ctot-1./cgeo)
    
def calc_cq_std(ctot,dctot,cgeo,dcgeo=0.):
    '''
    Calculate the quantum capacitance.
    
    Parameters:
    -----------
    ctot: np.ndarray
        The list of measured capacitance values.
    dctot: np.ndarray
        The list of measured capacitance uncertainties.
    cgeo: float
        The geometrical capacitance.
    dcgeo: float (optional)
        The uncertainty on the geometrical capacitance. Default is 0.
    
    Returns:
    --------
    dcq: np.ndarray
        The uncertainty of the quantum capacitance.
    '''
    d_inv_cgeo = dcgeo/cgeo**2
    d_inv_ctot = dctot/ctot**2
    d_inv_cq = np.sqrt(d_inv_cgeo**2+d_inv_ctot**2)
    d_cq = d_inv_cq*calc_cq(ctot,cgeo)**2
    return d_cq    
    
   