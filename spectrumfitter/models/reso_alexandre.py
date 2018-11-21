import numpy as np
from P13pt.spectrumfitter.basemodel import BaseModel

class Model(BaseModel):
    params = {
        'r':      [500, 20000, 1000, 1,     'Ohm'],
        'l':      [  0,   100,   50, 1e-12, 'pH'],
        'c':      [ 70,  5000,   70, 1e-9,  'nF'],
        'tau':    [  0,  5000,    1, 1e-15, 'fs'],
        'ra':     [  0,    10,    0, 1,     'Ohm'],
        'length': [100,   600,  300, 1e-6,  'um']
    }

    Z0 = 50.

    def abcd(self, w, r, l, c, tau, ra, length):
        gamma = np.sqrt((r+1j*l*w)*1j*c*w)
        Z1 = (r+1j*l*w)/gamma

        abcd1 = np.asarray([[np.cosh(gamma*length), Z1*np.sinh(gamma*length)],
                            [1./Z1*np.sinh(gamma*length), np.cosh(gamma*length)]])
        abcd0 = np.asarray([[np.cos(w*tau), 1j*self.Z0*np.sin(w*tau)],
                            [1j/self.Z0*np.sin(w*tau), np.cos(w*tau)]])
        abcda = np.asarray([[1, ra],
                            [0, 1]])

        # TODO: this puts the frequency axis first, there might be a more elegant way to do this
        abcd0 = np.swapaxes(np.swapaxes(abcd0, 1, 2), 0, 1)
        abcd1 = np.swapaxes(np.swapaxes(abcd1, 1, 2), 0, 1)

        abcd_tot = np.matmul(np.matmul(np.matmul(np.matmul(abcd0, abcda), abcd1), abcda), abcd0)

        a = abcd_tot[:, 0, 0]
        b = abcd_tot[:, 0, 1]
        c = abcd_tot[:, 1, 0]
        d = abcd_tot[:, 1, 1]

        return a, b, c, d

    def func_s11(self, w, r, l, c, tau, ra, length):
        a, b, c, d  = self.abcd(w, r, l, c, tau, ra, length)
        return (b/self.Z0-c*self.Z0)/(2.*a+b/self.Z0+c*self.Z0)

    def func_s12(self, w, r, l, c, tau, ra, length):
        a, b, c, d  = self.abcd(w, r, l, c, tau, ra, length)
        return 2./(2.*a+b/self.Z0+c*self.Z0)