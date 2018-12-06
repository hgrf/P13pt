from __future__ import print_function
import sys
import os
import errno
import traceback
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

    params = {}
    observables = []
    alarms = []
    """ As of now, alarms can be defined in the measurement class (as a list of lists, where the nested lists contain
    pairs of condition (string) and action (integer ALARM_*), but they will be handled by the launcher, not in the
    detached execution mode (i.e. running the script directly from the console). The reason is primarily that it is
    much easier to dynamically modify the alarms if they are checked on the GUI side. If we want to evaluate the alarms
    in the MeasurementBase class, then we have to (a) find a thread-safe way to send modifications of the alarms to the
    running acquisition thread and (b) find a way to inform the GUI that an alarm is activated / re-evaluate the alarm
    conditions in the GUI.
    """

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