import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QApplication,
                             QLabel, QLineEdit, QFileDialog, QCheckBox, QDialog, QMessageBox,
                             QGroupBox, QComboBox)
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

class Select(MeasurementParameter):   
    def __init__(self, values, defaultindex=0):
        super(Select, self).__init__()
        # if command line interface
        if self.cli:
            self.value = values[defaultindex]
            return
        
        # else
        self.widget = QComboBox()
        self.widget.mp = self
        for v in values:
            if self.widget.findText(v) != -1:
                raise Exception('Duplicate item in Select()')
            self.widget.addItem(v)

    @property
    def value(self):
        return self.value_ if self.cli else self.widget.currentText()

    #TODO: should also check if element is in list if in CLI mode
    @value.setter
    def value(self, val):
        self.value_ = val
        if not self.cli:
            index = self.widget.findText(val)
            if index == -1:
                raise Exception('Item not part of list')
            else:
                self.widget.setCurrentIndex(index)

class Sweep(MeasurementParameter):
    def_value = np.asarray([0], dtype=float)
    zero = 1e-15        # for floating point error stuff

    def __init__(self, value):
        super(Sweep, self).__init__()
        self.value, text = self.parseValue(value)

        if self.cli:
            return

        # set up measurement parameter widget
        self.widget = QWidget()
        self.widget.mp = self
        self.widget.setStyleSheet("QLineEdit { border: none }")
        self.txt_values = QLineEdit(text)
        self.txt_values.setReadOnly(True)
        self.btn_setup_sweep = QPushButton('setup')
        self.btn_setup_sweep.clicked.connect(self.setup)

        l = QHBoxLayout(self.widget)
        l.addWidget(self.txt_values)
        l.addWidget(self.btn_setup_sweep)
        l.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(l)

        # set up dialog
        self.dialog = QDialog(self.mainwindow)
        self.dialog.setWindowTitle('Sweep setup')
        self.dialog.setModal(True)

        # first group (sweep parameters)
        self.group_sweep_params = QGroupBox('Sweep parameters')
        self.group_sweep_params.setCheckable(True)
        self.group_sweep_params.setChecked(False)
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
        self.group_sweep_params.setLayout(l1)

        # second group (manual sweep values)
        self.group_sweep_manual = QGroupBox('Manual sweep values')
        self.group_sweep_manual.setCheckable(True)
        lbl_manual = QLabel('Here you can manually define the values for the sweep. This can be a single value, '
                            'a python list of values/lists or a numpy array (numpy can be accessed via np.*).<br>'
                            'You can use the following shortcuts:<br>'
                            'r(start, stop, step) for '
                            '<a href="https://docs.scipy.org/doc/numpy/reference/generated/numpy.arange.html">'
                            'np.arange</a><br>'
                            'l(start, stop, num) for '
                            '<a href="https://docs.scipy.org/doc/numpy/reference/generated/numpy.linspace.html">'
                            'np.linspace</a>')
        lbl_manual.setTextFormat(Qt.RichText)
        lbl_manual.setTextInteractionFlags(Qt.TextBrowserInteraction)
        lbl_manual.setOpenExternalLinks(True)
        self.txt_sweep_manual = QLineEdit(text)

        l2 = QVBoxLayout()
        for w in [lbl_manual, self.txt_sweep_manual]:
            l2.addWidget(w)
        self.group_sweep_manual.setLayout(l2)

        self.btn_apply = QPushButton('Apply')

        # make groups mutually exclusive
        self.group_sweep_params.toggled.connect(lambda x: self.group_sweep_manual.setChecked(not x))
        self.group_sweep_manual.toggled.connect(lambda x: self.group_sweep_params.setChecked(not x))

        l = QVBoxLayout(self.dialog)
        l.addWidget(self.group_sweep_params)
        l.addWidget(self.group_sweep_manual)
        l.addWidget(self.btn_apply)

        # make connections
        for w in [self.txt_start, self.txt_stop, self.txt_step]:
            w.textChanged.connect(self.values_changed)
        for w in [self.chk_allerretour, self.chk_from0, self.chk_to0]:
            w.stateChanged.connect(self.values_changed)
        self.btn_apply.clicked.connect(self.apply)

    def parseValue(self, value):
        if isinstance(value, str) or isinstance(value, QString):
            text = str(value)
            try:
                values = eval(text, {'np': np, 'r': np.arange, 'l': np.linspace})
                value = np.asarray([])
                if isinstance(values, list) or isinstance(values, tuple):
                    for v in values:
                        value = np.append(value, np.asarray(v, dtype=float).flatten())
                else:
                    value = np.asarray(values, dtype=float).flatten()
            except Exception as e:
                value = self.def_value
                text = 'could not evaluate'
                if not self.cli:
                    QMessageBox.warning(self.dialog, 'Warning', 'Could not evaluate: '+str(e))
        elif isinstance(value, list)\
                or isinstance(value, np.ndarray)\
                or isinstance(value, float)\
                or isinstance(value, int):
            try:
                value = np.asarray(value, dtype=float).flatten()
                text = '[' + ",".join(map(str, value.tolist())) + ']'
            except:
                value = self.def_value
                text = 'could not evaluate'
        else:
            text = 'could not evaluate'
            value = self.def_value

        return value, text

    def setup(self):
        if not self.mainwindow:
            return
        self.dialog.show()

    def apply(self):
        if self.cli:
            return

        if self.group_sweep_params.isChecked():
            try:
                start = float(self.txt_start.text())
                stop = float(self.txt_stop.text())
                step = abs(float(self.txt_step.text()))
            except ValueError:
                QMessageBox.warning(self.dialog, 'Warning', 'Could not evaluate at least one of the numbers.')
                return

            value = np.arange(start, stop, np.sign(stop-start)*step)
            # make sure last item is taken into account in sweep
            if not np.abs(value[-1]-stop) < self.zero:
                value = np.concatenate((value, [stop]))

            if self.chk_allerretour.isChecked():
                value = np.concatenate((value, np.flip(value, 0)))
            if self.chk_from0.isChecked() and value[0] != 0.:
                value = np.concatenate((np.arange(0, value[0], np.sign(value[0])*step), value))
            if self.chk_to0.isChecked() and value[-1] != 0.:
                value = np.concatenate((value, np.arange(value[-1], 0, -np.sign(value[-1])*step)))
            self.value = np.round(value, 12)         # workaround to avoid floating point issues with np.arange
            self.txt_values.setText('[' + ",".join(map(str, self.value.tolist())) + ']')
            self.dialog.close()
        else:
            value, text = self.parseValue(self.txt_sweep_manual.text())
            self.value = value
            self.txt_values.setText(text)
            if not text == 'could not evaluate':
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

        if step != 0.:
            arfactor = 2 if self.chk_allerretour.isChecked() else 1
            from0steps = int(abs(start/step))+1 \
                if self.chk_from0.isChecked() and start != 0 \
                else 0
            to0steps = int(abs((start if self.chk_allerretour.isChecked() else stop)/step))+1 \
                if self.chk_to0.isChecked() and not (
                    (not self.chk_allerretour.isChecked() and stop == 0)
                    or (self.chk_allerretour.isChecked() and start == 0)) \
                else 0
            self.txt_num.setText(str((int((stop-start)/step)+1)*arfactor+from0steps+to0steps))