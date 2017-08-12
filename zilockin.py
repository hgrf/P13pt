import zhinst.ziPython, zhinst.utils
import pprint
import numpy as np
import os
import errno

# TODO: check version of zhinst here!

class ZILockin:
    def __init__(self, ziDAQ_address='localhost', ziDAQ_port=8005, channel=1, polltime=0.005):
        self.daq = zhinst.ziPython.ziDAQServer(ziDAQ_address, ziDAQ_port)
        self.device = device = zhinst.utils.autoDetect(self.daq)
                
        self.daq.flush()

        # read settings
        self.c = c = channel-1
        self.settings = settings = self.daq.get('*')

        self.frequency = settings[device]['oscs'][c]['freq'][0]
        LIampl = settings[device]['sigouts'][c]['amplitudes'][str(int(c)+6)][0]
        LIsigoutrange = settings[device]['sigouts'][c]['range'][0]
        self.amplitude = LIampl*LIsigoutrange
        self.rms_amp = LIampl*LIsigoutrange/np.sqrt(2)
        timeconstant = settings[device]['demods'][c]['timeconstant'][0]
        rate = settings[device]['demods'][c]['rate'][0]

        # Subscribe to scope
        self.path0 = '/' + device + '/demods/'+ c + '/sample'
        self.daq.subscribe(path0)

        self.polltime = polltime

        # filename += "_LI_%.0fHz"%LIfreq
        # filename += "_exc_%.0fmV"%(LIampl*LIsigoutrange*1e3)
        # filename += "_TC_%.1e"%LITC
        # filename += "_rate_%.1e"%LIrate

    def save_settings(self, filename):
        # make directory if necessary
        try:
            directory = os.path.dirname(filename)
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        # store all lock in settings
        with open(filename, "a") as ppf:
            pp = pprint.PrettyPrinter(stream=ppf)
            pp.pprint(self.settings)

    def poll_data(self):
        """
        This function polls the lock in for data.
        :return: [rms amplitude averaged over poll time, standard deviation of the rms amplitude over poll time]
        """
        # poll data during poll time, second parameter is poll timeout in [ms] (recomended value is 500ms)
        dataDict = self.daq.poll(self.polltime, 500)

        # recreate data
        if self.device in dataDict:
            if dataDict[self.device]['demods'][self.c]['sample']['time']['dataloss']:
                raise Exception('Sample loss detected.')
            else:
                data = dataDict[self.device]['demods'][self.c]['sample']
                rdata = np.sqrt(data['x']**2+data['y']**2)
    
        # calculate R
        r = np.mean(rdata)
        sigr = np.std(rdata)
        return [r, sigr]

    def tidy_up(self):
        # unsubscribe to scope
        self.daq.unsubscribe(self.path0)
