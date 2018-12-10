from __future__ import print_function
import sys
import os
import errno
import traceback
import numpy as np
from io import BytesIO as StringIO
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from P13pt.mascril.parameter import MeasurementParameter

try:
    from PyQt5.QtCore import QString
except ImportError:
    QString = str

class MeasurementBase(QThread):
    ALARM_SHOWVALUE = 0     # does nothing, but the user will see the result of the expression (this way we are not
                            # limited to boolean expressions, we can even use the "alarms" to do real-time calculations
                            # with the observables

    ALARM_QUIT = 1          # quit the acquisition if the alarm condition is True

    ALARM_CALLCOPS = 2      # show a colour indicator / a message if the alarm condition is True


    new_observables_data = pyqtSignal(list)
    new_console_data = pyqtSignal(QString)
    new_alarm_data = pyqtSignal(list)

    params = {}
    observables = []
    alarms = []

    def __init__(self, redirect_console=False, parent=None):
        super(MeasurementBase, self).__init__(parent)
        self.redirect_console = redirect_console
        self.flags = {'quit_requested': False}
        self.data_file = None

    def run(self):
        if self.redirect_console:
            # The following has to be in the run function so that it is executed
            # in its own thread, otherwise sys is not the same.        
            self.std_sav = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = self.sio = StringIO()
            self.sio.write = self.new_console_data.emit

        # evaluate the parameters dictionary
        params = {}
        for key in self.params:
            if isinstance(self.params[key], MeasurementParameter):
                params[key] = self.params[key].value
            else:
                params[key] = self.params[key]

        try:
            l = self.measure(**params)
        except Exception as e:
            print("An exception occured during the acquisition\n-------------------------")
            traceback.print_exc(file=sys.stdout)

        try:
            self.tidy_up()
        except Exception as e:
            print("An exception occured during the clean-up\n-------------------------")
            traceback.print_exc(file=sys.stdout)

        self.reset_console()

    def prepare_saving(self, filename):
        if self.data_file is None:
            try:
                directory = os.path.dirname(filename)
                os.makedirs(directory)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            self.data_file = open(filename, 'a')
            self.data_file.write('#' + '\t'.join(self.observables) + '\n')
        else:
            raise Exception("The last data file has not been properly closed.")

    def evaluate_alarms(self, locals):
        locals['np'] = np
        alarm_data = [0]*len(self.alarms)
        for i,alarm in enumerate(self.alarms):
            condition = alarm[0]
            action = alarm[1]
            if condition.strip() == '':
                continue
            try:
                result = eval(condition, locals)
            except Exception as e:
                if not self.redirect_console: print('Alarm could not be evaluated: '+condition+' / error: '+str(e))
                alarm_data[i] = e
            else:
                if action == self.ALARM_SHOWVALUE:
                    if not self.redirect_console: print(condition+' =', result)
                    alarm_data[i] = result
                elif action == self.ALARM_CALLCOPS:
                    if not self.redirect_console: print('Calling the cops: '+condition)
                    alarm_data[i] = True
                elif action == self.ALARM_QUIT:
                    if result:
                        if not self.redirect_console: print('Stopping the acquisition: '+condition)
                        alarm_data[i] = True
                        self.quit()
        self.new_alarm_data.emit(alarm_data)

    def save_row(self, locals):
        if self.data_file is None:
            raise Exception("No data file has been opened.")

        row = []
        for obs in self.observables:
            try:
                value = locals[obs]
            except KeyError:
                value = None
            row.append(value)
        self.data_file.write('\t'.join([str(v) for v in row]) + '\n')
        self.data_file.flush()

        self.new_observables_data.emit(row)
        self.evaluate_alarms(locals)

    def end_saving(self):
        if self.data_file is not None:
            self.data_file.close()
        self.data_file = None

    def measure(self):
        pass

    def reset_console(self):
        if self.redirect_console:
            sys.stdout, sys.stderr = self.std_sav
            self.sio.close()

    def tidy_up(self):
        pass

    @pyqtSlot()
    def quit(self):
        self.flags['quit_requested'] = True

    @pyqtSlot()
    def terminate(self):
        self.reset_console()
        if self.data_file:
            self.data_file.close()
            self.data_file = None
        super(MeasurementBase, self).terminate()