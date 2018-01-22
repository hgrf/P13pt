#!/usr/bin/python
import sys
import os
import imp
import inspect
from glob import glob
from P13pt.rfspectrum import Network
from P13pt.params_from_filename import params_from_filename
import ConfigParser

from PyQt4.QtCore import pyqtSignal, pyqtSlot, SIGNAL, SLOT, Qt, QSignalMapper
from PyQt4.QtGui import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                         QPushButton, QFileDialog, QMessageBox, QSlider, QSpinBox, QLabel,
                         QWidgetItem, QSplitter, QComboBox, QCheckBox)

try:
    from PyQt4.QtCore import QString
except ImportError:
    QString = str

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np
import copy

def clearLayout(layout):
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)

        if isinstance(item, QWidgetItem):
            item.widget().close()
        else:
            clearLayout(item.layout())

        layout.removeItem(item)

class Fitter(QWidget):
    model_changed = pyqtSignal()
    model = None
    sliders = {}
    checkboxes = {}

    def __init__(self, parent=None):
        super(Fitter, self).__init__(parent)

        self.txt_model = QLineEdit('Path to model...', self)
        self.btn_browsemodel = QPushButton('Browse', self)
        self.btn_loadmodel = QPushButton('Load', self)
        self.cmb_fitmethod = QComboBox(self)
        self.btn_fit = QPushButton('Fit', self)

        self.sliders = QWidget(self)
        self.sl_layout = QVBoxLayout()
        self.sliders.setLayout(self.sl_layout)

        # set the layout
        layout = QVBoxLayout()
        for widget in [self.txt_model, self.btn_browsemodel, self.btn_loadmodel,
                       self.cmb_fitmethod, self.btn_fit, self.sliders]:
            layout.addWidget(widget)
        self.setLayout(layout)

        # make connections
        self.connect(self.btn_browsemodel, SIGNAL('clicked()'), self.browse_model)
        self.connect(self.btn_loadmodel, SIGNAL('clicked()'), self.load_model)
        self.connect(self.btn_fit, SIGNAL('clicked()'), self.fit_model)
        self.connect(self.cmb_fitmethod, SIGNAL('currentIndexChanged(int)'), self.fitmethod_changed)

    def browse_model(self):
        model_file = QFileDialog.getOpenFileName(self, 'Choose model', directory=os.path.dirname(__file__))
        self.txt_model.setText(model_file)
        config.set('main', 'model', model_file)

    def load_model(self):
        # unload previous model
        clearLayout(self.sl_layout)
        self.cmb_fitmethod.clear()
        self.sliders = {}
        self.checkboxes = {}

        # check if we are dealing with a valid module
        filename = str(self.txt_model.text())
        mod_name, file_ext = os.path.splitext(os.path.split(filename)[-1])
        try:
            mod = imp.load_source(mod_name, filename)
        except IOError as e:
            QMessageBox.critical(self, "Error", "Could not load module: "+str(e.args[1]))
            return
        if not hasattr(mod, 'Model'):
            QMessageBox.critical(self, "Error", "Could not get correct class from file.")
            return
        self.model = getattr(mod, 'Model')()
        for member in inspect.getmembers(self.model, predicate=inspect.ismethod):
            if member[0].startswith('fit_'):
                # check if for this function we want to show checkboxes or not
                if len(inspect.getargspec(member[1]).args) == 4:
                    enable_checkboxes = True
                else:
                    enable_checkboxes = False
                self.cmb_fitmethod.addItem(member[0][4:], enable_checkboxes)
        for p in self.model.params:
            label = QLabel(p+' ['+str(self.model.params[p][4])+']')
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
            self.connect(sl, SIGNAL('valueChanged(int)'), sb, SLOT('setValue(int)'))
            self.connect(sb, SIGNAL('valueChanged(int)'), sl, SLOT('setValue(int)'))
            self.connect(sl, SIGNAL('valueChanged(int)'), map, SLOT('map()'))
            sl.setValue(self.model.params[p][2])
            self.connect(map, SIGNAL('mapped(QWidget *)'), self.value_changed)
            map.setMapping(sl, sl)
            l = QHBoxLayout()
            l.addWidget(label)
            l.addWidget(sl)
            l.addWidget(sb)
            l.addWidget(cb)
            self.sl_layout.addLayout(l)
        self.enable_checkboxes(self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()).toBool())
        self.model_changed.emit()

    def fit_model(self):
        if self.model:
            fit_method = getattr(self.model, 'fit_'+str(self.cmb_fitmethod.currentText()))
            if self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()).toBool():
                fit_method(self.parent().get_f(), self.parent().get_y(), self.checkboxes)
            else:
                fit_method(self.parent().get_f(), self.parent().get_y())
            for p in self.model.values:
                self.sliders[p].setValue(self.model.values[p]/self.model.params[p][3])

    def value_changed(self, slider):
        self.model.values[slider.id] = slider.value()*self.model.params[slider.id][3]
        self.model_changed.emit()

    def enable_checkboxes(self, b=True):
        for p in self.checkboxes:
            self.checkboxes[p].setEnabled(b)

    def fitmethod_changed(self):
        enable_checkboxes = self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()).toBool()
        self.enable_checkboxes(enable_checkboxes)

    def update_values(self, values):
        self.model.values.update(values)
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p]/self.model.params[p][3])
        self.model_changed.emit()

    def reset_values(self):
        if self.model:
            self.model.reset_values()
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p]/self.model.params[p][3])
        self.model_changed.emit()


class MainWindow(QSplitter):
    f = []
    dut_files = []
    thru_file = ''
    dummy_file = ''
    current_index = 0
    line_r = None
    line_i = None
    model_params = {}

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # set up data loading area
        self.data_loading = QWidget(self)
        self.txt_dut = QLineEdit('Path to DUT...', self.data_loading)
        self.btn_browsedut = QPushButton('Browse', self.data_loading)
        self.txt_thru = QLineEdit('Path to thru...', self.data_loading)
        self.btn_browsethru = QPushButton('Browse', self.data_loading)
        self.txt_dummy = QLineEdit('Path to dummy...', self.data_loading)
        self.btn_browsedummy = QPushButton('Browse', self.data_loading)
        self.btn_load = QPushButton('Load', self.data_loading)
        self.btn_prev = QPushButton('Previous spectrum', self.data_loading)
        self.btn_next = QPushButton('Next spectrum', self.data_loading)
        l = QVBoxLayout()
        for w in [self.txt_dut, self.btn_browsedut, self.txt_thru, self.btn_browsethru,
                       self.txt_dummy, self.btn_browsedummy, self.btn_load, self.btn_prev, self.btn_next]:
            l.addWidget(w)
        self.data_loading.setLayout(l)

        # set up plotting area
        self.plotting = QWidget(self)
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('f [GHz]')
        self.ax.set_ylabel('Y12 [mS]')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotting)
        l = QVBoxLayout()
        for w in [self.toolbar, self.canvas]:
            l.addWidget(w)
        self.plotting.setLayout(l)

        # set up fitting area
        self.fitter = Fitter(self)

        # make connections
        self.map_browse = QSignalMapper(self)
        for x in ['dut', 'thru', 'dummy']:
            self.connect(self.__dict__['btn_browse'+x], SIGNAL('clicked()'), self.map_browse, SLOT('map()'))
            self.map_browse.setMapping(self.__dict__['btn_browse'+x], x)
        self.connect(self.map_browse, SIGNAL('mapped(const QString &)'), self.browse)
        self.connect(self.btn_load, SIGNAL('clicked()'), self.load)
        self.connect(self.btn_prev, SIGNAL('clicked()'), self.prev_spectrum)
        self.connect(self.btn_next, SIGNAL('clicked()'), self.next_spectrum)
        self.connect(self.fitter, SIGNAL('model_changed()'), self.plot_fit)

        # load config
        if config.has_section('main'):
            if config.has_option('main', 'dut'): self.txt_dut.setText(config.get('main', 'dut'))
            if config.has_option('main', 'thru'): self.txt_thru.setText(config.get('main', 'thru'))
            if config.has_option('main', 'dummy'): self.txt_dummy.setText(config.get('main', 'dummy'))
            if config.has_option('main', 'model'): self.fitter.txt_model.setText(config.get('main', 'model'))
        else:
            config.add_section('main')

        # Show the splitter.
        self.setStretchFactor(0,1)
        self.setStretchFactor(1,1)
        self.setStretchFactor(2,2)
        self.show()

        # Maximize the splitter.
        #self.resize(1500,800)
        #self.setWindowState(Qt.WindowMaximized)

    def get_f(self):
        return self.dut.f

    def get_y(self):
        return self.dut.y[:,0,1]

    def browse(self, x):
        # open browser and update the text field
        folder = QFileDialog.getExistingDirectory(self, 'Choose dataset')
        self.__dict__['txt_'+str(x)].setText(folder)

        # save in config file
        config.set('main', str(x), folder)

    def load(self):
        self.clear_ax()
        self.current_index = 0
        self.dut_files = sorted(glob(os.path.join(str(self.txt_dut.text()), '*.txt')),
                                key=lambda x: params_from_filename(x)['timestamp'])

        if len(self.dut_files) < 1:
            QMessageBox.warning(self, 'Warning', 'Please select a valid DUT folder')
            return

        dummy_files = glob(os.path.join(str(self.txt_dummy.text()), '*.txt'))
        if len(dummy_files) != 1:
            self.txt_dummy.setText('Please select a valid dummy folder')
            self.dummy_file = ''
        else:
            self.dummy_file, = dummy_files

        thru_files = glob(os.path.join(str(self.txt_thru.text()), '*.txt'))
        if len(thru_files) != 1:
            self.txt_thru.setText('Please select a valid thru folder')
            self.thru_file = ''
        else:
            self.thru_file, = thru_files

        self.load_spectrum(True)

    def clear_ax(self):
        for artist in self.ax.lines + self.ax.collections:
            artist.remove()
        self.ax.set_prop_cycle(None)
        self.ax.set_title('')
        self.canvas.draw()

    def load_spectrum(self, first_load=False):
        # clean up the axis
        self.clear_ax()
        self.line_r = None
        self.line_i = None

        # load spectra
        self.dut = dut = Network(self.dut_files[self.current_index])
        params = params_from_filename(self.dut_files[self.current_index])

        if self.dummy_file:
            dummy = Network(self.dummy_file)
        if self.thru_file:
            thru = Network(self.thru_file)
            dummy = dummy.deembed_thru(thru)
            dut = dut.deembed_thru(thru)
        if self.dummy_file:
            dut.y -= dummy.y

        self.ax.plot(dut.f/1e9, dut.y[:,0,1].real*1e3, label='Real')
        self.ax.plot(dut.f/1e9, dut.y[:,0,1].imag*1e3, label='Imag')
        if first_load:
            self.ax.set_xlim([min(dut.f/1e9), max(dut.f/1e9)])
        self.ax.set_title(', '.join([key+'='+str(params[key]) for key in params]))

        # draw model if available
        self.f = dut.f
        if self.fitter.model:
            if self.dut_files[self.current_index] in self.model_params:
                self.fitter.update_values(self.model_params[self.dut_files[self.current_index]])
            else:
                self.fitter.reset_values()

        # update canvas
        self.canvas.draw()

    def prev_spectrum(self):
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.dut_files)-1
        self.load_spectrum()

    def next_spectrum(self):
        self.current_index += 1
        if self.current_index >= len(self.dut_files):
            self.current_index = 0
        self.load_spectrum()

    def plot_fit(self):
        # update model lines on plot
        f = np.asarray(self.f)
        y = -self.fitter.model.admittance(2.*np.pi*f, **self.fitter.model.values)  # - (minus) as a convention because we are looking at Y12

        if self.line_r:
            self.line_r.set_ydata(y.real*1e3)
            self.line_i.set_ydata(y.imag*1e3)
        else:
            self.line_r, = self.ax.plot(f/1e9, y.real*1e3, '-.')
            self.line_i, = self.ax.plot(f/1e9, y.imag*1e3, '-.')
        self.canvas.draw()

        # store new model data
        self.model_params[self.dut_files[self.current_index]] = copy.copy(self.fitter.model.values)


if __name__ == '__main__':
    # CD into directory where this script is saved
    d = os.path.dirname(__file__)
    if d != '': os.chdir(d)

    # Read config file
    config = ConfigParser.RawConfigParser()
    config.read('spectrumfitter.cfg')

    app = QApplication(sys.argv)

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    # Writing our configuration file to 'mdb.cfg'
    with open('spectrumfitter.cfg', 'wb') as configfile:
        config.write(configfile)

    sys.exit(ret)