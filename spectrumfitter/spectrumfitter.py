#!/usr/bin/python
import sys
import os
import imp
import inspect
from glob import glob
from P13pt.rfspectrum import Network
from P13pt.params_from_filename import params_from_filename
import ConfigParser

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QSignalMapper
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                         QPushButton, QFileDialog, QMessageBox, QSlider, QSpinBox, QLabel,
                         QWidgetItem, QSplitter, QComboBox, QCheckBox)

try:
    from PyQt5.QtCore import QString
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

        self.txt_resultsfile = QLineEdit('Path to results file...', self)
        self.btn_browseresults = QPushButton('Browse', self)
        self.btn_saveresults = QPushButton('Save', self)
        self.btn_loadresults = QPushButton('Load', self)

        # set the layout
        layout = QVBoxLayout()
        for widget in [self.txt_model, self.btn_browsemodel, self.btn_loadmodel,
                       self.cmb_fitmethod, self.btn_fit, self.sliders, self.txt_resultsfile,
                       self.btn_browseresults, self.btn_saveresults, self.btn_loadresults]:
            layout.addWidget(widget)
        self.setLayout(layout)

        # make connections
        self.btn_browsemodel.clicked.connect(self.browse_model)
        self.btn_loadmodel.clicked.connect(self.load_model)
        self.btn_fit.clicked.connect(self.fit_model)
        self.cmb_fitmethod.currentIndexChanged.connect(self.fitmethod_changed)
        self.btn_browseresults.clicked.connect(self.browse_results)
        self.btn_saveresults.clicked.connect(self.save_results)
        self.btn_loadresults.clicked.connect(self.load_results)

    def browse_model(self):
        model_file, filter = QFileDialog.getOpenFileName(self, 'Choose model', directory=os.path.dirname(__file__))
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
        self.enable_checkboxes(self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()))
        self.model_changed.emit()

    def fit_model(self):
        if self.model:
            fit_method = getattr(self.model, 'fit_'+str(self.cmb_fitmethod.currentText()))
            if self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()):
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
        enable_checkboxes = self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex())
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

    def browse_results(self):
        results_file = QFileDialog.getSaveFileName(self, 'Results file')
        self.txt_resultsfile.setText(results_file)

    def save_results(self):
        with open(self.txt_resultsfile.text(), 'w') as f:
            # write the header
            f.write('# fitting results generated by P13pt spectrum fitter\n')
            f.write('# thru: '+self.parent().thru_file+'\n')
            f.write('# dummy: ' +self.parent().dummy_file+'\n')
            f.write('# dut: '+os.path.dirname(self.parent().dut_files[0])+'\n')

            # determine columns
            f.write('# filename\t')
            for p in self.parent().dut.params:
                f.write(p+'\t')
            f.write('\t'.join([p for p in self.model.params]))
            f.write('\n')

            # write data
            for filename in self.parent().model_params:
                f.write(filename+'\t')
                for p in self.parent().dut.params:                  # TODO: what if some filenames do not contain all parameters? should catch exceptions
                    f.write(str(params_from_filename(filename)[p])+'\t')
                f.write('\t'.join([str(self.parent().model_params[filename][p]) for p in self.model.params]))
                f.write('\n')

    def load_results(self):
        QMessageBox.warning(self, 'Not implemented', 'Not implemented')


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
            self.__dict__['btn_browse'+x].clicked.connect(self.map_browse.map)
            self.map_browse.setMapping(self.__dict__['btn_browse'+x], x)
        self.map_browse.mapped[str].connect(self.browse)
        self.btn_load.clicked.connect(self.load)
        self.btn_prev.clicked.connect(self.prev_spectrum)
        self.btn_next.clicked.connect(self.next_spectrum)
        self.fitter.model_changed.connect(self.plot_fit)

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
        self.resize(1500,800)
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

        # TODO: tidy up this mess, especially the self.dut / dut weirdness (and be careful!)
        if self.dummy_file:
            dummy = Network(self.dummy_file)
        if self.thru_file:
            thru = Network(self.thru_file)
            if self.dummy_file:
                dummy = dummy.deembed_thru(thru)
            self.dut = dut = dut.deembed_thru(thru)
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
        if not self.dut_files:
            return

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
