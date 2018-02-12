import numpy as np
from lmfit import Parameters, minimize
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QLineEdit

class Model:
    # dictionary of the model's parameters
    # for each parameter, we store the minimum and maximum value,
    # an initial value, a multiplier value and a unit
#    params = {
#        'r': [1., 1000., 1000., 1, 'Ohm'],
#        'c': [0.1, 400., 200., 1e-15, 'fF'],
#        'l': [0, 2000, 0., 1e-12, 'pH'],
#        'rlo': [0, 1000, 200., 1, 'Ohm'],
#    }
    params = {
        'r': [1., 20000., 1000., 1, 'Ohm'],
        'c': [0.1, 400., 200., 1e-15, 'fF'],
        'l': [0, 10000, 0., 1e-12, 'pH'],
        'rlo': [0, 20000, 200., 1, 'Ohm'],
    }

    values = {}    # this is where the fitter will store the values

    def __init__(self):
        self.infowidget = QWidget()
        self.txt_length = QLineEdit()
        self.txt_width = QLineEdit()
        self.infolabel = QLabel()
        self.infolabel.setStyleSheet('QLabel { background: #FFFFFF; font-size: 20px; }')
        l1 = QHBoxLayout()
        for w in (QLabel('L [um]:'), self.txt_length, QLabel('W [um]:'), self.txt_width):
            l1.addWidget(w)
        l2 = QVBoxLayout()
        l2.addLayout(l1)
        l2.addWidget(self.infolabel)
        self.txt_length.textChanged.connect(self.update_info_widget)
        self.txt_width.textChanged.connect(self.update_info_widget)
        self.infowidget.setLayout(l2)
        self.reset_values()

    def reset_values(self):
        for p in self.params:
            self.values[p] = self.params[p][2]*self.params[p][3]

    def admittance(self, w, r, c, l, rlo):
        """Admittance of a Field Effect Capacitor

        Parameters
        ----------
        w : float or np.array
            Pulsation at which to compute the admitance

        r : float or np.array
            Resistance of the R-C-L line

        c : float or np.array
            Capacitance of the R-C-L line

        l : float or np.array
            Inductance of the R-C-L line

        rlo : float or np.array
            Low frequency resistance = r/3+ra

        Returns
        -------
        float : computed admittance

        """
        r = r + 1j*l*w
        k = np.sqrt(-1j*r*c*w)
        tlm = (1j*k/r) * np.tanh(1j*k)
        adm = 1./(1./tlm + rlo - r/3)
        return adm

    def objective(self, params, x_data, y_data, part=2):
        """Error function function minimized during the fitting procedure.

        We perform the optimization on both the real and imaginary part.
        
        Parameters
        ----------
        
        part : int
            0: real
            1: imaginary
            2: both
        """
        r, c, l, rlo = (params['r'].value, params['c'].value,
                        params['l'].value, params['rlo'].value) 
        computed_admittance = self.admittance(x_data, r, c, l, rlo)
        np.nan_to_num(computed_admittance)
        res = np.empty((2, len(y_data)))
        res[0] = y_data.real - computed_admittance.real
        res[1] = y_data.imag - computed_admittance.imag
        if part == 2:
            return np.ravel(res)
        else:
            return res[part]

    def update_info_widget(self):
        try:
            L = float(self.txt_length.text())/1e6
            W = float(self.txt_width.text())/1e6
        except ValueError:
            return
        #r = self.values['r']/L*W
        l = self.values['l']/L*W
        c = self.values['c']/L/W
        self.infolabel.setText('------------------------\n'+
                               'Z0 = '+str(np.sqrt(self.values['l']/self.values['c']))+' Ohm\n'+
                               'vpl/vf = '+str(1./np.sqrt(l*c)/1e6)+'\n'+
                               'fres = '+str(1./(4.*np.sqrt(self.values['l']*self.values['c']))/1e9)+' GHz')

    def fit_RCRa(self, base_f, base_y):
        # define initial values
        self.values['r'] = 200.
        self.values['c'] = 200e-15        
        self.values['l'] = 0.
        self.values['rlo'] = 230.
        
        # get crossover frequency
        # avoid detecting the crossover associated with the leak or associated to high frequency weirdness
        mask = np.logical_and(base_f > 2e8, base_f < 5e9)
        # try to detect crossover using threshold
        f_below_thresh = base_f[mask][np.abs(base_y[mask].real-base_y[mask].imag)<5e-5]
        if len(f_below_thresh):
            fc = f_below_thresh[0]
        else:
            print "Threshold detection did not work"
            fc = base_f[mask][np.argmin(np.abs(base_y[mask].real-base_y[mask].imag))]
        
        print "Detected fc:", fc/1e9, "GHz"
        #if fc < 3.1e8: fc = 1e9
        
        # define masks
        masks = [base_f < fc/5.]    # here we will only fit C
        masks += [base_f < 2.*fc]   # here we will only fit Rlo
        
        # do it again
        masks += [base_f < fc/2.]
        masks += [base_f < 2.*fc]
        
        # now fit R
        masks += [base_f < 5.*fc]
        
        # Rlo again
        masks += [base_f < 2.*fc]
        
        # L
        #masks += [np.logical_and(base_f > 2e9, base_f < 15e9)]

        # fit
        for i, mask in enumerate(masks):
            w = 2.*np.pi*base_f[mask]
            y = base_y[mask]  # minus sign because Y12 and not Y11

            # create fit parameters
            params = Parameters()
            params.add('c', value=self.values['c'], min=self.params['c'][0]*self.params['c'][3], max=self.params['c'][1]*self.params['c'][3], vary=True if i in [0, 2] else False)
            params.add('rlo', value=self.values['rlo'], min=self.params['rlo'][0]*self.params['rlo'][3], max=self.params['rlo'][1]*self.params['rlo'][3], vary=True if i in [1, 3, 5] else False)
            params.add('r', value=self.values['r'], min=self.params['r'][0]*self.params['r'][3], max=self.params['r'][1]*self.params['r'][3], vary=True if i in [4,6] else False)
            params.add('l', value=self.values['l'], min=self.params['l'][0]*self.params['l'][3], max=self.params['l'][1]*self.params['l'][3], vary=True if i in [6] else False)
        
            # execute fit
            if i in []:
                # fit only imaginary part
                res = minimize(self.objective, params, args=(w, y, 1))
            else:
                res = minimize(self.objective, params, args=(w, y))
            for p in self.values:
                self.values[p] = res.params[p].value