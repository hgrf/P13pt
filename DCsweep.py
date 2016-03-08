from matplotlib import pyplot as plt
import numpy as np

# fundamental constants
e = 1.6021766208e-19 # C
eps0 = 8.854187817e-12 # As/Vm

def complex_fit(x, y_meas, function, guessed_parameters, **kwargs):
    ''' 
    Allows to fit measured data to a function. 
    
    Takes complex functions and complex y-data.
    Returns real parameters obtained by the fit.
    '''
    from scipy.optimize import leastsq
       
    residuals = lambda p,y,x,f: abs(y-f(x,p,**kwargs))
    plsq = leastsq(residuals, guessed_parameters, args=(y_meas, x, function))
    if plsq[1]>5:
        print '!!! Fit was NOT successful !!!'

    return plsq[0]

class DCsweep(object):
    """Defines the class of DCsweep
    """    
    
    def __init__(self,filename, Rg1, Rg2, Rds, L, W, d, eps):        # another variable (with a default value) in the initialisation could be used to define the table format of the input file
        self.Rg1 = Rg1
        self.Rg2 = Rg2
        self.Rds = Rds
        self.L = L
        self.W = W
        self.d = d
        self.eps = eps

        with open(filename, 'r') as current_file:
            self.raw = np.genfromtxt(current_file).T
            self.Vg1bilt = self.raw[0]
            self.Vg2bilt = self.raw[1]
            self.Vdsbilt = self.raw[2]
            self.Vg1 = self.raw[3]
            self.Vg2 = self.raw[4]
            self.Vds = self.raw[5]
            
            self.Ileak1 = (self.Vg1bilt-self.Vg1)/self.Rg1
            self.Ileak2 = (self.Vg2bilt-self.Vg2)/self.Rg2
            self.Ids = (self.Vdsbilt-self.Vds)/self.Rds
            self.Rsample = self.Vds/self.Ids
            
            self.Vg1unique = np.unique(self.Vg1bilt) # get sorted unique Vg1 values
            self.Vg2unique = np.unique(self.Vg2bilt) # get sorted unique Vg2 values        
    
    def plotTransferVg1(self, ax=None):
        if ax==None:
            ax = plt.gca()
            
        for v in self.Vg2unique:
            ax.plot(self.Vg1[self.Vg2bilt == v], self.Rsample[self.Vg2bilt == v])
            
        plt.grid(b=True)
        plt.xlabel('Vg1 [V]')
        plt.ylabel('Rsample [Ohm]')
    
    def plot2DColor(self, ax=None):
        if ax==None:
            ax = plt.gca()

        grid = self.Rsample.reshape((len(self.Vg2unique), len(self.Vg1unique)))
        grid = grid[::-1,:]
        
        plt.imshow(grid, extent=(self.Vg1unique.min(), self.Vg1unique.max(), self.Vg2unique.min(), self.Vg2unique.max()))
        plt.colorbar()
        plt.xlabel("Vg1 [V]")
        plt.ylabel("Vg2 [V]")
        
    def plotIV(self, ax=None):
        if ax==None:
            ax = plt.gca()
        
        ax.plot(self.Vds, self.Ids*1e6)
        
        plt.grid(b=True)
        plt.xlabel('Vds [V]')
        plt.ylabel('Ids [\mu A]')
    
    def diffusiveModel(self, Vg,(mu,n0,Rc)):
        return self.L/self.W/(np.sqrt(n0**2+(eps0*self.eps/self.d*Vg/e)**2)*e*mu)+Rc

    def fitModelVg1(self):
        idp = np.argmax(self.Rsample) # get index of max. resistance
        self.Vdp = self.Vg1[idp]
        self.mu, self.n0, self.Rc = complex_fit(self.Vg1[idp:]-self.Vdp, self.Rsample[idp:], self.diffusiveModel, (1., 1e15, 1e3))
        print "Fit result:"
        print "mu =", self.mu, " n0 =", self.n0, " Rc =", self.Rc
    
    def plotModelVg1(self, Vdp=None, mu=None, n0=None, Rc=None, ax=None):
        if ax==None:
            ax = plt.gca()

        if Vdp==None:
            Vdp = self.Vdp
            mu = self.mu
            n0 = self.n0
            Rc = self.Rc
        
        ax.plot(self.Vg1, self.diffusiveModel(self.Vg1-Vdp, (mu, n0, Rc)), label="model")