import os
import imp
import inspect
from copy import copy

from PyQt5.QtCore import Qt, QSignalMapper, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                             QLineEdit, QFileDialog, QWidgetItem, QMessageBox, QCheckBox,
                             QSlider, QSpinBox, QLabel, QApplication)

def clearLayout(layout):
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if isinstance(item, QWidgetItem):
            item.widget().close()
        else:
            clearLayout(item.layout())
        layout.removeItem(item)

def parse_fitted_param_str(s):
    sign = -1. if s[0] == '-' else +1
    param = s[1]
    i = int(s[2]) - 1
    j = int(s[3]) - 1
    return sign, param, i, j

def create_fitted_param_str(sign, param, i, j, unit=False):
    unit_string = ' [mS]' if param.lower() == 'y' else ''
    return ('+' if sign > 0 else '-') + \
        param + \
        str(i + 1) + \
        str(j + 1) + \
        (unit_string if unit else '')

class Fitter(QWidget):
    filename = None
    network = None
    model = None
    model_file = None
    sliders = {}
    checkboxes = {}
    fit_changed = pyqtSignal()
    fitted_param_changed = pyqtSignal(str)
    fitted_param = None       # default value
    model_params = {}

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        # set up fitting area
        browse_icon = QIcon('../icons/folder.png')
        self.cmb_sign = QComboBox()
        self.cmb_paramtofit = QComboBox()
        self.cmb_elemtofit = QComboBox()
        for s in ['+', '-']:
            self.cmb_sign.addItem(s)
        for p in ['Y', 'S']:
            self.cmb_paramtofit.addItem(p)
        for e in range(4):
            self.cmb_elemtofit.addItem(str(e//2+1)+str(e%2+1))
        self.txt_model = QLineEdit('Path to model...')
        self.btn_browsemodel = QPushButton(browse_icon, '')
        self.btn_loadmodel = QPushButton('Load')
        self.cmb_fitmethod = QComboBox()
        self.btn_fit = QPushButton('Fit')
        self.btn_fitall = QPushButton('Fit all')
        self.sliderwidget = QWidget()

        # layouts
        self.sl_layout = QVBoxLayout()
        self.sliderwidget.setLayout(self.sl_layout)
        l1 = QHBoxLayout()
        for w in [QLabel('Parameter:'), self.cmb_sign, self.cmb_paramtofit, self.cmb_elemtofit]:
            l1.addWidget(w)
        l2 = QHBoxLayout()
        for w in [self.txt_model, self.btn_browsemodel, self.btn_loadmodel]:
            l2.addWidget(w)
        l = QVBoxLayout()
        l.addLayout(l1)
        l.addLayout(l2)
        for w in [self.cmb_fitmethod, self.btn_fit, self.btn_fitall, self.sliderwidget]:
            l.addWidget(w)
        self.setLayout(l)

        # make connections
        self.btn_browsemodel.clicked.connect(self.browse_model)
        self.btn_loadmodel.clicked.connect(self.load_model)
        self.btn_fit.clicked.connect(self.fit_model)
        for w in [self.cmb_sign, self.cmb_paramtofit, self.cmb_elemtofit]:
            w.currentIndexChanged.connect(self.cmb_fitted_param_changed)

    def cmb_fitted_param_setup(self):
        sign, param, i, j = parse_fitted_param_str(self.fitted_param)
        self.cmb_sign.setCurrentText('+' if sign > 0 else '-')
        self.cmb_paramtofit.setCurrentText(param)
        self.cmb_elemtofit.setCurrentText(str(i+1)+str(j+1))

    def cmb_fitted_param_changed(self):
        self.fitted_param = create_fitted_param_str(
            +1 if self.cmb_sign.currentText() == '+' else -1,
            self.cmb_paramtofit.currentText(),
            int(self.cmb_elemtofit.currentText()[0])-1,
            int(self.cmb_elemtofit.currentText()[1])-1
        )
        self.fitted_param_changed.emit(self.fitted_param)

    def browse_model(self):
        model_file, filter = QFileDialog.getOpenFileName(self, 'Choose model',
                                                         directory=os.path.join(os.path.dirname(__file__), 'models'),
                                                         filter='*.py')

        if model_file:
            self.txt_model.setText(model_file)

    def unload_model(self):
        clearLayout(self.sl_layout)
        self.empty_cache()
        self.model = None
        self.sliders = {}
        self.checkboxes = {}
        self.cmb_fitmethod.clear()

    def update_network(self, network, filename):
        self.network = network
        self.filename = filename
        if filename in self.model_params:
            self.update_values(self.model_params[filename])
        elif self.model:        # only try to reset values if a model is defined
            self.reset_values()

    def empty_cache(self):
        self.model_params = {}

    def load_model(self):
        # unload previous model
        self.unload_model()

        # check if we are dealing with a valid module
        filename = str(self.txt_model.text())
        mod_name, file_ext = os.path.splitext(os.path.split(filename)[-1])
        try:
            mod = imp.load_source(mod_name, filename)
            if not hasattr(mod, 'Model'):
                QMessageBox.critical(self, "Error", "Could not get correct class from file.")
                return False
            self.model = getattr(mod, 'Model')()
        except Exception as e:
            QMessageBox.critical(self, "Error", "Could not load module: " + str(e.message))
            return False
        self.model_file = filename
        for member in inspect.getmembers(self.model, predicate=inspect.ismethod):
            if member[0].startswith('fit_'):
                # check if for this function we want to show checkboxes or not
                if len(inspect.getargspec(member[1]).args) == 4:
                    enable_checkboxes = True
                else:
                    enable_checkboxes = False
                self.cmb_fitmethod.addItem(member[0][4:], enable_checkboxes)
        for p in self.model.params:
            label = QLabel(p + ' [' + str(self.model.params[p][4]) + ']')
            sl = QSlider(Qt.Horizontal)
            self.sliders[p] = sl
            sl.id = p
            sl.setMinimum(self.model.params[p][0])
            sl.setMaximum(self.model.params[p][1])
            sb = QSpinBox()
            sb.setMinimum(self.model.params[p][0])
            sb.setMaximum(self.model.params[p][1])
            cb = QCheckBox()
            self.checkboxes[p] = cb
            map = QSignalMapper(self)
            sl.valueChanged[int].connect(sb.setValue)
            sb.valueChanged[int].connect(sl.setValue)
            sl.valueChanged[int].connect(map.map)
            sl.setValue(self.model.params[p][2])
            map.mapped[QWidget].connect(self.value_changed)
            map.setMapping(sl, sl)
            l = QHBoxLayout()
            l.addWidget(label)
            l.addWidget(sl)
            l.addWidget(sb)
            l.addWidget(cb)
            self.sl_layout.addLayout(l)

        try:        # for backwards compatibility
            self.sl_layout.addWidget(self.model.infowidget)
            self.model.update_info_widget()
        except AttributeError:
            pass
        self.enable_checkboxes(self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()))

        #TODO: fix this
        #config.set('main', 'model', filename)
        return True

    def value_changed(self, slider):
        self.model.values[slider.id] = slider.value() * self.model.params[slider.id][3]
        self.model_params[self.filename] = copy(self.model.values)
        try:
            self.model.update_info_widget()
        except AttributeError:
            pass
        self.fit_changed.emit()

    def enable_checkboxes(self, b=True):
        for p in self.checkboxes:
            self.checkboxes[p].setEnabled(b)

    def fitmethod_changed(self):
        enable_checkboxes = self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex())
        self.enable_checkboxes(enable_checkboxes)

    def reset_values(self):
        # TODO: remove redundancy with update_values
        if self.model:
            self.model.reset_values()
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])
        self.fit_changed.emit()

    def update_values(self, values):
        self.model.values.update(values)
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])
        self.fit_changed.emit()

    def fit_model(self):
        if not self.network:
            QMessageBox.warning(self, 'Warning', 'Please load some data first.')
            return

        sign, param, i, j = parse_fitted_param_str(self.fitted_param)

        param = self.network.y[:,i,j] if param == 'Y' \
            else self.network.s[:,i,j]

        # TODO: instead disable fit buttons when no model is loaded
        if self.model:
            fit_method = getattr(self.model, 'fit_' + str(self.cmb_fitmethod.currentText()))
            try:
                if self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()):
                    fit_method(self.network.f, sign*param, self.checkboxes)
                else:
                    fit_method(self.network.f, sign*param)
            except Exception as e:
                QMessageBox.critical(self, "Error", "Error during fit: " + str(e))
                return
            for p in self.model.values:
                self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])