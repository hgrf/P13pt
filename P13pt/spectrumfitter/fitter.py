import os
import imp
import inspect
from copy import copy

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QStandardPaths
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
                             QLineEdit, QFileDialog, QWidgetItem, QMessageBox, QCheckBox,
                             QSlider, QSpinBox, QLabel)

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
    _fitted_param = None       # default value
    model_params = {}
    manual_mode = True         # in manual mode, we emit the fit_changed signal when sliders are modified

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        # set up models folder
        home_dir = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        self.models_dir = os.path.join(home_dir, 'SpectrumFitterModels')
        # check if models folder exists
        if os.path.exists(self.models_dir):
            # check if this path is a folder
            if not os.path.isdir(self.models_dir):
                raise Exception('~/SpectrumFitterModels exists, but is not a folder')
        else:
            # create the models folder
            os.mkdir(self.models_dir)

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
        self.txt_model.setReadOnly(True)
        self.btn_browsemodel = QPushButton(browse_icon, '')
        self.cmb_modelfunc = QComboBox()
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
        for w in [self.txt_model, self.btn_browsemodel]:
            l2.addWidget(w)
        l3 = QHBoxLayout()
        for w in [QLabel('Model function:'), self.cmb_modelfunc]:
            l3.addWidget(w)
        l4 = QHBoxLayout()
        for w in [QLabel('Fit method:'), self.cmb_fitmethod]:
            l4.addWidget(w)
        l = QVBoxLayout()
        l.addLayout(l1)
        l.addLayout(l2)
        l.addLayout(l3)
        l.addLayout(l4)
        for w in [self.btn_fit, self.btn_fitall, self.sliderwidget]:
            l.addWidget(w)
        self.setLayout(l)

        # make connections
        self.btn_browsemodel.clicked.connect(self.browse_model)
        self.btn_fit.clicked.connect(self.fit_model)
        for w in [self.cmb_sign, self.cmb_paramtofit, self.cmb_elemtofit]:
            w.currentIndexChanged.connect(self.cmb_fitted_param_changed)
        self.cmb_modelfunc.currentTextChanged.connect(self.cmb_modelfunc_changed)

        # disable buttons while no model is loaded
        self.btn_fit.setEnabled(False)
        self.btn_fitall.setEnabled(False)

    @property
    def fitted_param(self):
        return self._fitted_param

    @fitted_param.setter
    def fitted_param(self, value):
        self._fitted_param = value
        sign, param, i, j = parse_fitted_param_str(value)
        # TODO: check if this one calls itsself by setting the combo boxes
        self.cmb_sign.setCurrentText('+' if sign > 0 else '-')
        self.cmb_paramtofit.setCurrentText(param)
        self.cmb_elemtofit.setCurrentText(str(i+1)+str(j+1))
        self.fitted_param_changed.emit(self._fitted_param)
        if self.model:
            self.fit_changed.emit()     # force plotter to plot fit again

    def cmb_fitted_param_changed(self):
        self.fitted_param = create_fitted_param_str(
            +1 if self.cmb_sign.currentText() == '+' else -1,
            self.cmb_paramtofit.currentText(),
            int(self.cmb_elemtofit.currentText()[0])-1,
            int(self.cmb_elemtofit.currentText()[1])-1
        )

    @pyqtSlot(str)
    def cmb_modelfunc_changed(self, txt):
        if self.model and self.model.values:
            self.model.func = getattr(self.model, 'func_' + txt)
            self.fit_changed.emit()

    def browse_model(self):
        model_file, filter = QFileDialog.getOpenFileName(self, 'Choose model', directory=self.models_dir, filter='*.py')

        if model_file:
            self.txt_model.setText(model_file)
            self.load_model()

    def unload_model(self):
        # unload model first, then empty cache and clear the UI
        self.model = None
        self.empty_cache()
        self.sliders = {}
        self.checkboxes = {}
        clearLayout(self.sl_layout)
        self.cmb_fitmethod.clear()
        self.cmb_modelfunc.clear()
        self.btn_fit.setEnabled(False)
        self.btn_fitall.setEnabled(False)

    def update_network(self, network, filename):
        self.network = network
        self.filename = filename
        if self.model:
            # if a model is loaded, try to find the model parameters in the model_params dictionary,
            # if there is no entry, reset the model values
            self.update_values(self.model_params[filename] if filename in self.model_params else None)

    def empty_cache(self):
        self.model_params = {}

    @pyqtSlot()
    def load_model(self, filename=None, info={}, data=None):
        # unload previous model
        self.unload_model()

        if filename:
            self.txt_model.setText(os.path.join(self.models_dir, filename))

        # check if we are dealing with a valid module and load it
        filename = str(self.txt_model.text())
        if not os.path.exists(filename) or not os.path.isfile(filename):
            QMessageBox.critical(self, "Error", "The file "+filename+" does not exist.")
            return False

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

        # check for model functions
        for member in inspect.getmembers(self.model, predicate=inspect.ismethod):
            if member[0].startswith('func_'):
                if not self.model.func:
                    self.model.func = getattr(self.model, member[0])
                self.cmb_modelfunc.addItem(member[0][5:])

        # check that there ARE model functions
        if not self.cmb_modelfunc.count():
            QMessageBox.critical(self, "Error", "Invalid model, please define at least one function func_*")
            self.model = None
            self.model_file = None
            return False

        # if a function was provided in the info, load it
        if 'model_func' in info:
            self.cmb_modelfunc.setCurrentText(info['model_func'])

        # check for fitting methods and if they support checkboxes
        for member in inspect.getmembers(self.model, predicate=inspect.ismethod):
            if member[0].startswith('fit_'):
                # check if for this function we want to show checkboxes or not
                if len(inspect.getargspec(member[1]).args) == 4:
                    enable_checkboxes = True
                else:
                    enable_checkboxes = False
                # add fit method to drop down list and put the enable_checkboxes value in the item data
                self.cmb_fitmethod.addItem(member[0][4:], enable_checkboxes)

        # if a method was provided in the info, load it
        if 'fit_method' in info:
            self.cmb_fitmethod.setCurrentText(info['fit_method'])

        # set up the sliders for the model parameters
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
            sl.valueChanged[int].connect(sb.setValue)
            sb.valueChanged[int].connect(sl.setValue)
            sl.setValue(self.model.params[p][2])
            sl.valueChanged.connect(self.slider_value_changed)
            l = QHBoxLayout()
            l.addWidget(label)
            l.addWidget(sl)
            l.addWidget(sb)
            l.addWidget(cb)
            self.sl_layout.addLayout(l)

        # set up the info widget if it exists
        if self.model.infowidget:
            self.sl_layout.addWidget(self.model.infowidget)
            self.model.update_infowidget()

        # set up the fit method list if a any fit methods could be detected
        if self.cmb_fitmethod.count():
            self.enable_checkboxes(self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()))
            self.btn_fit.setEnabled(True)
            self.btn_fitall.setEnabled(True)
        else:
            self.cmb_fitmethod.addItem('No fit methods found')

        # if data was provided, evaluate it
        if data:
            # get a list of parameter names
            params = [p for p in data]
            unusable = []
            # now check float conversion compatibility of the data columns, removing the ones that we cannot use
            for p in params:
                try:
                    data[p] = [float(x) for x in data[p]]
                except ValueError:
                    unusable.append(p)
            for p in unusable:
                params.remove(p)

            for i, f in enumerate(data['filename']):
                values = [float(data[p][i]) for p in params]
                self.model_params[f] = dict(zip(params, values))

        return True

    def slider_value_changed(self):
        slider = self.sender()
        self.model.values[slider.id] = slider.value() * self.model.params[slider.id][3]
        self.model_params[self.filename] = copy(self.model.values)
        self.model.update_infowidget()
        if self.manual_mode:
            self.fit_changed.emit()

    def enable_checkboxes(self, b=True):
        for p in self.checkboxes:
            self.checkboxes[p].setEnabled(b)

    def fitmethod_changed(self):
        enable_checkboxes = self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex())
        self.enable_checkboxes(enable_checkboxes)

    def update_values(self, values=None):
        self.manual_mode = False
        if values is None:
            self.model.reset_values()
        else:
            self.model.values.update(values)
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])
        self.manual_mode = True
        self.fit_changed.emit()

    def fit_model(self):
        if not self.network:
            QMessageBox.warning(self, 'Warning', 'Please load some data first.')
            return

        sign, param, i, j = parse_fitted_param_str(self.fitted_param)

        param = self.network.y[:,i,j] if param == 'Y' \
            else self.network.s[:,i,j]

        fit_method = getattr(self.model, 'fit_' + str(self.cmb_fitmethod.currentText()))
        try:
            if self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()):
                fit_method(self.network.f, sign*param, self.checkboxes)
            else:
                fit_method(self.network.f, sign*param)
        except Exception as e:
            QMessageBox.critical(self, "Error", "Error during fit: " + str(e))
            return

        self.update_values(self.model.values)