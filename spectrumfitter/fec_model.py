import numpy as np
from lmfit import Parameters, minimize

class Model:
    # dictionary of the model's parameters
    # for each parameter, we store the minimum and maximum value,
    # an initial value, a multiplier value and a unit
    params = {
        'r': [0.1, 10000, 1000, 1, 'Ohm'],
        'c': [0.1, 1000, 200, 1e-15, 'fF'],
        'l': [0, 100, 0, 1e-9, 'nH'],
        'gl': [0, 1000, 0, 1e-6, 'uS'],
        'ra': [0, 1000, 300, 1, 'Ohm'],
        'ca': [0, 1000, 600, 1e-15, 'fF'],
        'rasup': [0, 1000, 100, 1, 'Ohm']
    }

    values = {}    # this is where the fitter will store the values

    def __init__(self):
        self.reset_values()

    def reset_values(self):
        for p in self.params:
            self.values[p] = self.params[p][2]*self.params[p][3]

    def admittance(self, w, r, c, l, gl, ra, ca, rasup):
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

        gl : float or np.array
            Leak conductance

        ra : float or np.array
            Access resistance

        ca : float or np.array
            Access capacitance

        rasup : float or np.array
            Supplementary access resistance (e.g. ungated region)

        Returns
        -------
        float : computed admittance

        """
        r = r + 1j*l*w
        k = np.sqrt(-1j*r*c*w)
        tlm = (1j*k/r) * np.tanh(1j*k) + gl
        adm_a = 1j*w*ca + 1./ra
        adm = 1./(1./tlm + 1./adm_a + rasup)
        return adm

    def objective(self, params, x_data, y_data):
        """Error function function minimized during the fitting procedure.

        We perform the optimization on both the real and imaginary part.
        """
        r, c, l, gl, ra, ca, rasup = (params['r'].value, params['c'].value,
                                      params['l'].value, params['gl'].value,
                                      params['ra'].value, params['ca'].value,
                                      params['rasup'].value)
        computed_admittance = self.admittance(x_data, r, c, l, gl, ra, ca, rasup)
        np.nan_to_num(computed_admittance)
        res = np.empty((2, len(y_data)))
        res[0] = y_data.real - computed_admittance.real
        res[1] = y_data.imag - computed_admittance.imag
        return np.ravel(res)

    def fit_default(self, f, y, checkboxes):
        w = 2.*np.pi*f
        y = -y  # minus sign because Y12 and not Y11

        # create fit parameters
        params = Parameters()
        params.add('r', value=self.values['r'], min=1, max=120e3, vary=checkboxes['r'].isChecked())
        params.add('c', value=self.values['c'], min=1e-15, max=1e-12, vary=checkboxes['c'].isChecked())
        params.add('l', value=self.values['l'], min=0., max=1e-6, vary=checkboxes['l'].isChecked())
        params.add('ra', value=self.values['ra'], min=10, max=10e3, vary=checkboxes['ra'].isChecked())
        params.add('rasup', value=self.values['rasup'], min=0., max=10e3, vary=checkboxes['rasup'].isChecked())
        params.add('ca', value=self.values['ca'], min=10e-15, max=10e3, vary=checkboxes['ca'].isChecked())
        params.add('gl', value=self.values['gl'], min=1e-5, max=1e-3, vary=checkboxes['gl'].isChecked())

        # execute fit
        res = minimize(self.objective, params, args=(w, y))
        for p in self.values:
            self.values[p] = res.params[p].value

    def fit_stepbystep(self, base_f, base_y):
        # define masks
        masks = [base_f < 1e9]
        masks += [base_f < 40e9]

        # fit
        for i, mask in enumerate(masks):
            w = 2.*np.pi*base_f[mask]
            y = -base_y[mask]  # minus sign because Y12 and not Y11

            # create fit parameters
            params = Parameters()
            params.add('r', value=self.values['r'], min=1, max=120e3, vary=True if i in [0] else False)
            params.add('c', value=self.values['c'], min=1e-15, max=1e-12, vary=True if i in [0] else False)
            params.add('l', value=self.values['l'], min=0., max=1e-6, vary=True if i in [] else False)
            params.add('ra', value=self.values['ra'], min=10, max=10e3, vary=True if i in [] else False)
            params.add('rasup', value=self.values['rasup'], min=0., max=10e3, vary=True if i in [] else False)
            params.add('ca', value=self.values['ca'], min=10e-15, max=10e3, vary=True if i in [] else False)
            params.add('gl', value=self.values['gl'], min=1e-5, max=1e-3, vary=True if i in [] else False)

            # execute fit
            res = minimize(self.objective, params, args=(w, y))
            for p in self.values:
                self.values[p] = res.params[p].value

    def fit_firstguess(self, f, y):
        # get leak conductance from the real part of the low frequency admittance
        gl = np.mean(-y[f<2e7].real)

        # get crossover frequency
        mask = f > 3e8  # avoid detecting the crossover associated with the leak
        fc = f[mask][np.argmin(np.abs(y[mask].real - y[mask].imag))]
        if fc < 3.1e8: fc = 1e9

        # get capacitance
        mask = f < 3e8
        c = np.mean(-y[mask].imag/(2.*np.pi*f[mask]))
        r = 1./(2.*np.pi*fc*c)

        self.values['gl'] = gl
        self.values['c'] = c
        self.values['r'] = r

    def fit_RCRa(self, base_f, base_y):
        # define masks
        masks = [base_f < 1e9]
        masks += [base_f < 5e9]
        masks += [base_f < 30e9]

        # fit
        for i, mask in enumerate(masks):
            w = 2.*np.pi*base_f[mask]
            y = -base_y[mask]  # minus sign because Y12 and not Y11

            # create fit parameters
            params = Parameters()
            params.add('r', value=self.values['r'], min=100, max=100e3, vary=True if i in [0, 1] else False)
            params.add('c', value=self.values['c'], min=1e-15, max=1e-12, vary=True if i in [0, 1] else False)
            params.add('ra', value=self.values['ra'], min=1, max=10e3, vary=True if i in [1] else False)

            # don't fit the following params
            # TODO: could generate these automatically
            params.add('l', value=self.values['l'], min=0., max=1e-6, vary=False)
            params.add('gl', value=self.values['gl'], min=0., max=1e-6, vary=False)
            params.add('ca', value=self.values['ca'], min=0., max=1e-12, vary=False)
            params.add('rasup', value=self.values['rasup'], min=0., max=10e3, vary=False)

            # execute fit
            res = minimize(self.objective, params, args=(w, y))
            for p in self.values:
                self.values[p] = res.params[p].value

    def fit_RLCRa(self, base_f, base_y):
        # define masks
        masks = [base_f < 1e9]
        masks += [base_f < 5e9]
        masks += [base_f < 30e9]

        for i, mask in enumerate(masks):
            w = 2.*np.pi*base_f[mask]
            y = -base_y[mask]  # minus sign because Y12 and not Y11

            # create fit parameters
            params = Parameters()
            params.add('r', value=self.values['r'], min=100, max=100e3, vary=True if i in [0, 1, 2] else False)
            params.add('l', value=self.values['l'], min=0., max=1e-6, vary=True if i in [1, 2] else False)
            params.add('c', value=self.values['c'], min=1e-15, max=1e-12, vary=True if i in [0, 1, 2, 3] else False)
            params.add('ra', value=self.values['ra'], min=1, max=10e3, vary=True if i in [1, 2] else False)

            # don't fit the following params
            # TODO: could generate these automatically
            params.add('gl', value=self.values['gl'], min=0., max=1e-6, vary=False)
            params.add('ca', value=self.values['ca'], min=0., max=1e-12, vary=False)
            params.add('rasup', value=self.values['rasup'], min=0., max=10e3, vary=False)

            # execute fit
            res = minimize(self.objective, params, args=(w, y))
            for p in self.values:
                self.values[p] = res.params[p].value

    def fit_3params_zero(self, base_f, base_y):
        self.values['l'] = 0.
        self.values['ca'] = 0.
        self.values['rasup'] = 0.
        self.values['gl'] = 0.