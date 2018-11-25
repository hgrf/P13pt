class BaseModel(object):
    # dictionary of the model's parameters
    # for each parameter, we store the minimum and maximum value,
    # an initial value, a multiplier value and a unit
    params = {}
    func = None    # this is where the fitter will memorize which model function is active
    infowidget = None

    def __init__(self):
        self.values = {}            # this is where the fitter will store the values
                                    # NB: for some reason it is crucial that this is in the __init__ function,
                                    # otherwise, the SpectrumFitter might keep dictionary entries from
                                    # a previously loaded model...
        self.reset_values()

    def reset_values(self):
        for p in self.params:
            self.values[p] = self.params[p][2]*self.params[p][3]

    def update_infowidget(self):
        pass