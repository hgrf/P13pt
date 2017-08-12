import sys
from io import BytesIO as StringIO
from PyQt4.QtCore import QThread, pyqtSignal, pyqtSlot
try:
    from PyQt4.QtCore import QString
except ImportError:
    QString = str

class MeasurementBase(QThread):
    new_observables_data = pyqtSignal(list)
    new_console_data = pyqtSignal(QString)

    params = {}
    observables = []

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

        l = self.measure(**self.params)

        self.tidy_up()
        self.reset_console()

    def prepare_saving(self, filename):
        if self.data_file is None:
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
        super(MeasurementBase, self).terminate()

