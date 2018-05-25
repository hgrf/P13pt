import numpy as np
from lmfit import Parameters, minimize
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QLineEdit

class Model:
    # dictionary of the model's parameters
    # for each parameter, we store the minimum and maximum value,
    # an initial value, a multiplier value and a unit
    params = {
        'c': [1., 400., 200., 1e-15, 'fF'],
        'fres': [1., 100., 30., 1e9, 'GHz'],
        'q': [1., 1000, 600, 1e-3, 'm'],
        'rcont': [0., 100., 0., 1, 'Ohm'],
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

    def admittance(self, w, c, fres, q, rcont):
        """Admittance of a Field Effect Capacitor

        Parameters
        ----------
        w : float or np.array
            Pulsation at which to compute the admitance
            
        TODO...

        Returns
        -------
        float : computed admittance

        """
        w0 = fres*4.
        
        r = 1./(w0*c*q)
        l = 1./(w0**2*c)

        r = r + 1j*l*w
        k = np.sqrt(-1j*r*c*w)
        tlm = (1j*k/r) * np.tanh(1j*k)
        adm = 1./(1./tlm + rcont)
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
        c, fres, q, rcont = (params['c'].value, params['fres'].value,
                             params['q'].value, params['rcont'].value) 
        computed_admittance = self.admittance(x_data, c, fres, q, rcont)
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
#        r = self.values['r']
#        rlo = self.values['rlo']
#        # the following values per unit length
#        l = self.values['l']/L*W
#        c = self.values['c']/L/W
#        self.infolabel.setText('------------------------\n'+
#                               'Z0 = '+str(np.sqrt(self.values['l']/self.values['c']))+' Ohm\n'+
#                               'vpl/vf = '+str(1./np.sqrt(l*c)/1e6)+'\n'+
#                               'fres = '+str(1./(4.*np.sqrt(self.values['l']*self.values['c']))/1e9)+' GHz\n'+
#                               'rcont = '+str(rlo-r/3.)+' Ohm')

    def fit_CfresQ(self, base_f, base_y):
        # define initial values
        self.values['c'] = 200e-15
        self.values['fres'] = 40e9
        self.values['q'] = 0.5
        #self.values['rcont'] = 0.
        
        # get crossover frequency
        # avoid detecting the crossover associated with the possible leak
        mask = base_f > 2e8
        # try to detect crossover using threshold
        f_below_thresh = base_f[mask][np.abs(base_y[mask].real-base_y[mask].imag)<5e-5]
        if len(f_below_thresh):
            fc = f_below_thresh[0]
        else:
            print "Threshold detection did not work"
            fc = base_f[mask][np.argmin(np.abs(base_y[mask].real-base_y[mask].imag))]
        
        print "Detected fc:", fc/1e9, "GHz"
        
        # define masks
        masks = [base_f > 0.]    # fit everything except for Q

        # fit
        for i, mask in enumerate(masks):
            w = 2.*np.pi*base_f[mask]
            y = base_y[mask]  # minus sign because Y12 and not Y11

            # create fit parameters
            params = Parameters()
            params.add('c', value=self.values['c'], min=self.params['c'][0]*self.params['c'][3], max=self.params['c'][1]*self.params['c'][3], vary=True if i in [0] else False)
            params.add('fres', value=self.values['fres'], min=self.params['fres'][0]*self.params['fres'][3], max=self.params['fres'][1]*self.params['fres'][3], vary=True if i in [0] else False)
            params.add('q', value=self.values['q'], min=self.params['q'][0]*self.params['q'][3], max=self.params['q'][1]*self.params['q'][3], vary=True if i in [0] else False)
            params.add('rcont', value=self.values['rcont'], min=self.params['rcont'][0]*self.params['rcont'][3], max=self.params['rcont'][1]*self.params['rcont'][3], vary=True if i in [] else False)
        
            # execute fit
            if i in []:
                # fit only imaginary part
                res = minimize(self.objective, params, args=(w, y, 1))
            else:
                res = minimize(self.objective, params, args=(w, y))
            for p in self.values:
                self.values[p] = res.params[p].value
