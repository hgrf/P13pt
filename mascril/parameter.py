import numpy as np
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QApplication,
                             QLabel, QLineEdit, QFileDialog, QCheckBox, QDialog, QMessageBox)
try:
    from PyQt5.QtCore import QString
except ImportError:
    QString = str

class MeasurementParameter(object):
    ''' The base class for measurement parameters.
    '''
    cli = False     # set to True if running in command line interface
    mainwindow = None
    widget = None
    value_ = None

    def __init__(self):
        if QApplication.instance() is None:
            self.cli = True

    @property
    def value(self):
        return self.value_

    @value.setter
    def value(self, val):
        self.value_ = val


class Folder(MeasurementParameter):
    def __init__(self, path):
        super(Folder, self).__init__()
        if not self.cli:
            self.widget = QWidget()
            self.widget.mp = self
            self.widget.setStyleSheet("QLineEdit { border: none }")
            self.txt_folder = QLineEdit()
            self.btn_select_folder = QPushButton(QIcon('../icons/folder.png'), '')
            self.btn_select_folder.clicked.connect(self.browse)

            # make layout
            l = QHBoxLayout(self.widget)
            l.addWidget(self.txt_folder)
            l.addWidget(self.btn_select_folder)
            l.setContentsMargins(0,0,0,0)
            self.widget.setLayout(l)
        self.value = path

    @property
    def value(self):
        return self.value_ if self.cli else self.txt_folder.text()

    @value.setter
    def value(self, val):
        self.value_ = val
        if not self.cli:
            self.txt_folder.setText(val)

    def browse(self):
        path = QFileDialog.getExistingDirectory(None, 'Choose directory')
        if path:
            self.txt_folder.setText(path)


class String(MeasurementParameter):
    def __init__(self, string):
        super(String, self).__init__()
        if not self.cli:
            self.widget = QLineEdit()
            self.widget.mp = self
            self.widget.setStyleSheet("QLineEdit { border: none }")
        self.value = string

    @property
    def value(self):
        return self.value_ if self.cli else self.widget.text()

    @value.setter
    def value(self, val):
        self.value_ = val
        if not self.cli:
            self.widget.setText(val)


class Boolean(MeasurementParameter):
    def __init__(self, b):
        super(Boolean, self).__init__()
        if not self.cli:
            self.widget = QCheckBox()
            self.widget.mp = self
        self.value = b

    @property
    def value(self):
        return self.value_ if self.cli else self.widget.isChecked()

    @value.setter
    def value(self, val):
        self.value_ = val
        if not self.cli:
            self.widget.setChecked(val)


class Sweep(MeasurementParameter):
    def __init__(self, value):
        super(Sweep, self).__init__()
        self.value = value
        if self.cli:
            return
        self.widget = QWidget()
        self.widget.mp = self
        self.widget.setStyleSheet("QLineEdit { border: none }")
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
        self.dialog.setWindowTitle('Sweep setup')
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
        if self.cli:
            return
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
        if self.chk_from0.isChecked() and self.value[0] != 0.:
            self.value = np.concatenate((np.arange(0, self.value[0], np.sign(self.value[0])*abs(step)), self.value))
        if self.chk_to0.isChecked() and self.value[-1] != 0.:
            self.value = np.concatenate((self.value, np.arange(self.value[-1], 0, -np.sign(self.value[-1])*abs(step))))
        text = '[' + ",".join(map(str, self.value.tolist())) + ']'
        self.txt_values.setText(text)

        self.dialog.close()

    def values_changed(self):
        if self.cli:
            return
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