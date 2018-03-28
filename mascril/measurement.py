import sys
import os
import errno
import numpy as np
from io import BytesIO as StringIO
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                             QLabel, QLineEdit, QFileDialog, QCheckBox, QDialog, QMessageBox)
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

        try:
            l = self.measure(**self.params)
        except Exception as e:
            print "Error: "+e.message

        self.tidy_up()
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


class MeasurementParameter(object):
    ''' The base class for measurement parameters.
    '''
    def __init__(self):
        self.mainwindow = None
        pass

    def get_table_widget(self):
        return QWidget()

    def get_value(self):
        return None


class Folder(MeasurementParameter):
    def __init__(self, path):
        super(Folder, self).__init__()
        self.widget = QWidget()
        self.widget.mp = self
        self.widget.setStyleSheet("QLineEdit { border: none }")
        self.txt_folder = QLineEdit(path)
        self.btn_select_folder = QPushButton(QIcon('../icons/folder.png'), '')
        self.btn_select_folder.clicked.connect(self.browse)

        # make layout
        l = QHBoxLayout(self.widget)
        l.addWidget(self.txt_folder)
        l.addWidget(self.btn_select_folder)
        l.setContentsMargins(0,0,0,0)
        self.widget.setLayout(l)

    def get_table_widget(self):
        return self.widget

    def get_value(self):
        return self.txt_folder.text()

    def browse(self):
        path = QFileDialog.getExistingDirectory(None, 'Choose directory')
        if path:
            self.txt_folder.setText(path)


class String(MeasurementParameter):
    def __init__(self, string):
        super(String, self).__init__()
        self.widget = QLineEdit(string)
        self.widget.mp = self
        self.widget.setStyleSheet("QLineEdit { border: none }")

    def get_table_widget(self):
        return self.widget

    def get_value(self):
        return self.widget.text()


class Boolean(MeasurementParameter):
    def __init__(self, b):
        super(Boolean, self).__init__()
        self.widget = QCheckBox()
        self.widget.setChecked(b)
        self.widget.mp = self

    def get_table_widget(self):
        return self.widget

    def get_value(self):
        return self.widget.isChecked()


class Sweep(MeasurementParameter):
    def __init__(self, value):
        super(Sweep, self).__init__()
        self.widget = QWidget()
        self.widget.mp = self
        self.widget.setStyleSheet("QLineEdit { border: none }")
        self.value = value
        if isinstance(value, list):
            text = '[' + ','.join(map(str, value)) + ']'
        elif isinstance(value, np.ndarray):
            text = '[' + ",".join(map(str, value.tolist())) + ']'
        else:
            text = 'could not evaluate...'
            self.value = None
        self.txt_values = QLineEdit(text)
        self.txt_values.setReadOnly(True)
        self.btn_setup_sweep = QPushButton('setup')
        self.btn_setup_sweep.clicked.connect(self.setup)

        # make layout
        l = QHBoxLayout(self.widget)
        l.addWidget(self.txt_values)
        l.addWidget(self.btn_setup_sweep)
        l.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(l)

        # set up dialog
        self.dialog = QDialog(self.mainwindow)
        self.dialog.setModal(True)
        self.txt_start, self.txt_stop, self.txt_step, self.txt_num = [QLineEdit() for i in range(4)]
        self.txt_num.setReadOnly(True)
        lbl_start, lbl_stop, lbl_step, lbl_num = [QLabel(x) for x in ['Start:', 'Stop:', 'Step:', '#:']]
        self.chk_allerretour = QCheckBox('A/R')
        self.chk_allerretour.setToolTip('Aller/Retour')
        self.chk_from0 = QCheckBox('from 0')
        self.chk_to0 = QCheckBox('to 0')

        l1 = QHBoxLayout()
        for w in [lbl_start, self.txt_start, lbl_stop, self.txt_stop, lbl_step, self.txt_step, lbl_num, self.txt_num,
                  self.chk_allerretour, self.chk_from0, self.chk_to0]:
            l1.addWidget(w)

        self.btn_apply = QPushButton('Apply')

        l = QVBoxLayout(self.dialog)
        l.addLayout(l1)
        l.addWidget(self.btn_apply)

        # make connections
        for w in [self.txt_start, self.txt_stop, self.txt_step]:
            w.textChanged.connect(self.values_changed)
        for w in [self.chk_allerretour, self.chk_from0, self.chk_to0]:
            w.stateChanged.connect(self.values_changed)
        self.btn_apply.clicked.connect(self.apply)

    def setup(self):
        if not self.mainwindow:
            return
        self.dialog.show()

    def apply(self):
        try:
            start = float(self.txt_start.text())
            stop = float(self.txt_stop.text())
            step = float(self.txt_step.text())
        except ValueError:
            QMessageBox.warning(self.dialog, 'Warning', 'Could not evaluate at least one of the numbers.')
            return

        if (stop-start)*step < 0:
            QMessageBox.warning(self.dialog, 'Warning', 'This is not going to work. Make sure the step has the correct sign.')
            return

        self.value = np.arange(start, stop, step)
        if self.chk_allerretour.isChecked():
            self.value = np.concatenate((self.value, np.flip(self.value, 0)))
        if self.chk_from0.isChecked():
            self.value = np.concatenate((np.arange(0, self.value[0], np.sign(self.value[0])*abs(step)), self.value))
        if self.chk_to0.isChecked():
            self.value = np.concatenate((self.value, np.arange(self.value[-1], 0, -np.sign(self.value[-1])*abs(step))))
        text = '[' + ",".join(map(str, self.value.tolist())) + ']'
        self.txt_values.setText(text)

        self.dialog.close()

    def values_changed(self):
        try:
            start = float(self.txt_start.text())
            stop = float(self.txt_stop.text())
            step = float(self.txt_step.text())
        except ValueError:
            return

        if (stop-start)*step < 0:
            QMessageBox.warning(self.dialog, 'Warning', 'This is not going to work. Make sure the step has the correct sign.')
            return

        if step != 0.:
            arfactor = 2 if self.chk_allerretour.isChecked() else 1
            from0steps = int(abs(start/step))+1 if self.chk_from0.isChecked() else 0
            to0steps = int(abs((start if self.chk_allerretour.isChecked() else stop)/step))+1 if self.chk_to0.isChecked() else 0
            self.txt_num.setText(str((int((stop-start)/step)+1)*arfactor+from0steps+to0steps))

    def get_table_widget(self):
        return self.widget

    def get_value(self):
        return self.value