import numpy as np
from P13pt.fundconst import eps0, e, hbar, vf, kB

def n_from_vg(Vg, d, Vdp, include_Cq=False, T=0., eps_r=3.2):
    ''' Calculate the graphene charge carrier density using the gate voltage
    
    Parameters
    ----------
    
    Vg : float or numpy array
        gate voltage
        
    d : float or numpy array
        dielectric thickness
        
    Vdp : float or numpy array
        Dirac point voltage
        
    include_Cq : boolean
        True if you want to include the first order quantum capacitance
        correction in the calculation
    
    T : float or numpy array
        temperature in Kelvin (only makes sense if include_Cq is True)
    
    eps_r : float or numpy array
        the dielectric constant (defaults to 3.2 for hBN)
    '''
    
    Cgeo = eps0*eps_r/d
    n = Cgeo*(Vg-Vdp)/e
    if include_Cq:
        # include 1st order quantum capacitance correction
        mu = hbar*vf*np.sqrt(np.pi*np.abs(n))
        Cq = 2.*e**2*kB*T/(np.pi*(vf*hbar)**2)*np.log(2.+2.*np.cosh(mu/(kB*T)))
        C = 1./(1./Cgeo+1./Cq)
        n = C*(Vg-Vdp)/e
    return n