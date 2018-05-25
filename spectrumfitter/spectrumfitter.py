#!/usr/bin/python
import sys
import os
import imp
import inspect
from glob import glob
from P13pt.rfspectrum import Network
from P13pt.params_from_filename import params_from_filename
import ConfigParser

from PyQt5.QtCore import (Qt, QSignalMapper, qInstallMessageHandler, QtInfoMsg, QtCriticalMsg, QtDebugMsg,
                          QtWarningMsg, QtFatalMsg)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                         QPushButton, QFileDialog, QMessageBox, QSlider, QSpinBox, QLabel,
                         QWidgetItem, QSplitter, QComboBox, QCheckBox, QTabWidget, QDialog)

try:
    from PyQt5.QtCore import QString
except ImportError:
    QString = str

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import matplotlib.pyplot as plt
import numpy as np
from copy import copy

def load_fitresults(filename, readfilenameparams=True, extrainfo=False):
    dummy = thru = dut = model = ra = None
    # read results file
    with open(filename, 'r') as f:
        # read the header
        column_header = None
        previous_line = None
        end_of_header = False
        data = []
        for line in f:
            line = line.strip()
            if line:
                if line[0] == '#':  # line is a comment line
                    line = line[1:].strip()
                    if line.startswith('thru:'):
                        thru = line[5:].strip()
                    elif line.startswith('dummy:'):
                        dummy = line[6:].strip()
                    elif line.startswith('dut:'):
                        dut = line[4:].strip()
                    elif line.startswith('model:'):
                        model = line[6:].strip()
                    elif line.startswith('ra:'):
                        ra = float(line[3:].strip())
                else:
                    # check if we reached the end of the header (or if we already had reached it previously)
                    # and if there is a last header line
                    if not end_of_header:
                        end_of_header = True
                        if previous_line:  # '#' was removed already
                            column_header = previous_line.split('\t')
                    data.append(line.split('\t'))
                previous_line = line
        data = zip(*data)  # transpose array

        # remove file name parameter columns if requested
        if not readfilenameparams:
            if not column_header[0] == 'filename':
                return None
            if not len(data):
                return None
            num_params = len(params_from_filename(data[0][0]))
            data = [data[0]]+data[num_params+1:]
            column_header = [column_header[0]]+column_header[num_params+1:]

        # put everything together
        if column_header and len(column_header) == len(data):
            data = dict(zip(column_header, data))
        else:
            data = None

    if not extrainfo:
        return data
    else:
        return data, dut, thru, dummy, model, ra


def clearLayout(layout):
    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)

        if isinstance(item, QWidgetItem):
            item.widget().close()
        else:
            clearLayout(item.layout())

        layout.removeItem(item)


class MainWindow(QSplitter):
    f = []
    dut_files = []
    duts = {}
    dut = None
    y = None
    thru_file = ''
    thru = None
    dummy_file = ''
    dummy = None
    dut_folder = ''
    current_index = 0
    line_r = None
    line_i = None
    model_params = {}
    fitted_param = '-Y12'
    model = None
    model_file = None
    sliders = {}
    checkboxes = {}
    dummy_toggle_status = True
    thru_toggle_status = True
    fitting_all = 0

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        browse_icon = QIcon('../icons/folder.png')
        plot_icon = QIcon('../icons/plot.png')
        self.toggleon_icon = QIcon('../icons/on.png')
        self.toggleoff_icon = QIcon('../icons/off.png')

        # set up data loading area
        self.data_loading = QWidget()
        self.txt_dut = QLineEdit('Path to DUT...')
        self.btn_browsedut = QPushButton(browse_icon, '')
        self.txt_thru = QLineEdit('Path to thru...')
        self.btn_browsethru = QPushButton(browse_icon, '')
        self.btn_togglethru = QPushButton(self.toggleon_icon, '')
        self.btn_togglethru.setEnabled(False)
        self.btn_plotthru = QPushButton(plot_icon, '')
        self.btn_plotthru.setToolTip('Plot')
        self.btn_plotthru.setEnabled(False)
        self.txt_dummy = QLineEdit('Path to dummy...')
        self.btn_browsedummy = QPushButton(browse_icon, '')
        self.btn_toggledummy = QPushButton(self.toggleon_icon, '')
        self.btn_toggledummy.setEnabled(False)
        self.btn_plotdummy = QPushButton(plot_icon, '')
        self.btn_plotdummy.setToolTip('Plot')
        self.btn_plotdummy.setEnabled(False)
        self.btn_load = QPushButton('Load')
        self.btn_prev = QPushButton(QIcon('../icons/previous.png'), '')
        self.btn_next = QPushButton(QIcon('../icons/next.png'), '')
        self.cmb_plusminus = QComboBox()
        for s in ['+', '-']:
            self.cmb_plusminus.addItem(s)
        self.cmb_parameter = QComboBox()
        for s in ['Y11', 'Y12', 'Y21', 'Y22']:
            self.cmb_parameter.addItem(s)
        self.cmb_plusminus.setCurrentText(self.fitted_param[0])
        self.cmb_parameter.setCurrentText(self.fitted_param[1:])
        self.txt_ra = QLineEdit('0')
        l = QVBoxLayout()
        for field in [[QLabel('DUT:'), self.txt_dut, self.btn_browsedut],
                      [QLabel('Thru:'), self.txt_thru, self.btn_browsethru, self.btn_togglethru, self.btn_plotthru],
                      [QLabel('Dummy:'), self.txt_dummy, self.btn_browsedummy, self.btn_toggledummy, self.btn_plotdummy]]:
            hl = QHBoxLayout()
            for w in field:
                hl.addWidget(w)
            l.addLayout(hl)
        hl = QHBoxLayout()
        for w in [QLabel('Ra:'), self.txt_ra, self.btn_load, self.btn_prev, self.btn_next,
                  QLabel('Fitted parameter:'), self.cmb_plusminus, self.cmb_parameter]:
            hl.addWidget(w)
        l.addLayout(hl)
        self.data_loading.setLayout(l)

        # set up tabbed widget for different plots
        self.plotting = QTabWidget()
        self.plotting_s = QWidget()
        self.plotting_y = QWidget()
        self.plotting_yandfit = QWidget()
        self.plotting.addTab(self.plotting_yandfit, 'Y and fit')
        self.plotting.addTab(self.plotting_y, 'All Y')
        self.plotting.addTab(self.plotting_s, 'All S')

        # set up default plotting (Y and fit)
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('f [GHz]')
        self.ax.set_ylabel(self.fitted_param+' [mS]')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotting_yandfit)
        l = QVBoxLayout()
        for w in [self.toolbar, self.canvas]:
            l.addWidget(w)
        self.plotting_yandfit.setLayout(l)

        # set up plotting of all Y parameters
        self.figure_y = plt.figure()
        self.ax_y_list = [self.figure_y.add_subplot(221+i) for i in range(4)]
        for i, ax in enumerate(self.ax_y_list):
            ax.set_xlabel(r'$f [GHz]$')
            ax.set_ylabel(r'$Y_{'+['11', '12', '21', '22'][i]+r'} [mS]$')
        self.canvas_y = FigureCanvas(self.figure_y)
        self.toolbar_y = NavigationToolbar(self.canvas_y, self.plotting_y)
        l = QVBoxLayout()
        for w in [self.toolbar_y, self.canvas_y]:
            l.addWidget(w)
        self.plotting_y.setLayout(l)
        self.figure_y.tight_layout()

        # set up plotting of all S parameters
        self.figure_s = plt.figure()
        self.ax_s_list = [self.figure_s.add_subplot(221+i) for i in range(4)]
        for i, ax in enumerate(self.ax_s_list):
            ax.set_xlabel(r'$f [GHz]$')
            ax.set_ylabel(r'$S_{'+['11', '12', '21', '22'][i]+r'}$')
        self.canvas_s = FigureCanvas(self.figure_s)
        self.toolbar_s = NavigationToolbar(self.canvas_s, self.plotting_s)
        l = QVBoxLayout()
        for w in [self.toolbar_s, self.canvas_s]:
            l.addWidget(w)
        self.plotting_s.setLayout(l)
        self.figure_s.tight_layout()

        # set up left widget of the splitter
        self.left_widget = QWidget(self)
        l = QVBoxLayout()
        l.addWidget(self.data_loading)
        l.addWidget(self.plotting)
        l.setStretchFactor(self.plotting, 1)
        self.left_widget.setLayout(l)

        # set up fitting area
        self.fitting = QWidget()
        self.txt_model = QLineEdit('Path to model...')
        self.btn_browsemodel = QPushButton(browse_icon, '')
        self.btn_loadmodel = QPushButton('Load')
        self.cmb_fitmethod = QComboBox()
        self.btn_fit = QPushButton('Fit')
        self.btn_fitall = QPushButton('Fit all')
        self.sliderwidget = QWidget()
        self.sl_layout = QVBoxLayout()
        self.sliderwidget.setLayout(self.sl_layout)
        l1 = QHBoxLayout()
        for w in [self.txt_model, self.btn_browsemodel, self.btn_loadmodel]:
            l1.addWidget(w)
        l = QVBoxLayout()
        l.addLayout(l1)
        for w in [self.cmb_fitmethod, self.btn_fit, self.btn_fitall, self.sliderwidget]:
            l.addWidget(w)
        self.fitting.setLayout(l)

        # set up picture and data saving area
        self.saving = QWidget()
        self.txt_picfolder = QLineEdit('Path to picture folder...')
        self.btn_browsepicfolder = QPushButton(browse_icon, '')
        self.btn_savepic = QPushButton(QIcon('../icons/save.png'), '')
        self.btn_saveallpics = QPushButton(QIcon('../icons/save-all.png'), '')
        self.txt_resultsfile = QLineEdit('Path to results file...')
        self.btn_browseresults = QPushButton(browse_icon, '')
        self.btn_saveresults = QPushButton(QIcon('../icons/save.png'), '')
        self.btn_loadresults = QPushButton('Load')
        l1 = QHBoxLayout()
        for w in [self.txt_picfolder, self.btn_browsepicfolder, self.btn_savepic, self.btn_saveallpics]:
            l1.addWidget(w)
        l2 = QHBoxLayout()
        for w in [self.txt_resultsfile, self.btn_browseresults, self.btn_saveresults, self.btn_loadresults]:
            l2.addWidget(w)
        l = QVBoxLayout(self.saving)
        for lx in [l1, l2]:
            l.addLayout(lx)
        l.setAlignment(Qt.AlignBottom)

        # set up right widget of the splitter
        self.right_widget = QWidget(self)
        l = QVBoxLayout()
        l.addWidget(self.fitting)
        l.addWidget(self.saving)
        self.right_widget.setLayout(l)

        # make connections
        self.map_browse = QSignalMapper(self)
        for x in ['dut', 'thru', 'dummy']:
            self.__dict__['btn_browse'+x].clicked.connect(self.map_browse.map)
            self.map_browse.setMapping(self.__dict__['btn_browse'+x], x)
        self.map_browse.mapped[str].connect(self.browse)
        self.btn_toggledummy.clicked.connect(self.toggledummy)
        self.btn_togglethru.clicked.connect(self.togglethru)
        self.btn_plotdummy.clicked.connect(self.plotdummy)
        self.btn_plotthru.clicked.connect(self.plotthru)
        self.btn_load.clicked.connect(self.load_clicked)
        self.btn_prev.clicked.connect(self.prev_spectrum)
        self.btn_next.clicked.connect(self.next_spectrum)
        self.cmb_plusminus.currentTextChanged.connect(self.parameter_modified)
        self.cmb_parameter.currentTextChanged.connect(self.parameter_modified)
        self.btn_browsemodel.clicked.connect(self.browse_model)
        self.btn_loadmodel.clicked.connect(self.load_model)
        self.btn_fit.clicked.connect(self.fit_model)
        self.btn_fitall.clicked.connect(self.fit_all)
        self.cmb_fitmethod.currentIndexChanged.connect(self.fitmethod_changed)
        self.btn_browseresults.clicked.connect(self.browse_results)
        self.btn_saveresults.clicked.connect(self.save_results)
        self.btn_loadresults.clicked.connect(self.load_results)
        self.btn_browsepicfolder.clicked.connect(self.browse_picfolder)
        self.btn_savepic.clicked.connect(self.savepic)
        self.btn_saveallpics.clicked.connect(self.saveallpics)

        # load config
        if config.has_section('main'):
            if config.has_option('main', 'dut'): self.txt_dut.setText(config.get('main', 'dut'))
            if config.has_option('main', 'thru'): self.txt_thru.setText(config.get('main', 'thru'))
            if config.has_option('main', 'dummy'): self.txt_dummy.setText(config.get('main', 'dummy'))
            if config.has_option('main', 'model'): self.txt_model.setText(config.get('main', 'model'))
            if config.has_option('main', 'ra'): self.txt_ra.setText(config.get('main', 'ra'))
        else:
            config.add_section('main')

        # set up the splitter stretch factors
        self.setStretchFactor(0,4)
        self.setStretchFactor(1,5)

        # show the splitter
        self.show()

        # make the window big
        self.resize(1200,800)

        # Set window title
        self.setWindowTitle("Spectrum Fitter")

    def browse(self, x):
        # open browser and update the text field
        folder = QFileDialog.getExistingDirectory(self, 'Choose dataset')
        if folder:
            self.__dict__['txt_'+str(x)].setText(folder)

    def load(self, reinitialise=True):
        self.clear_ax()
        if reinitialise:
            self.current_index = 0
        self.model_params = {}
        self.duts = {}
        self.dut_folder = str(self.txt_dut.text())
        self.dut_files = [os.path.basename(x) for x in sorted(glob(os.path.join(self.dut_folder, '*.txt')))]

        if len(self.dut_files) < 1:
            QMessageBox.warning(self, 'Warning', 'Please select a valid DUT folder')
            self.dut_folder = ''
            return

        dummy_files = glob(os.path.join(str(self.txt_dummy.text()), '*.txt'))
        if len(dummy_files) != 1:
            self.txt_dummy.setText('Please select a valid dummy folder')
            self.dummy_file = ''
            self.dummy = None
            self.btn_toggledummy.setEnabled(False)
            self.btn_plotdummy.setEnabled(False)
        else:
            self.dummy_file, = dummy_files
            try:
                self.dummy = Network(self.dummy_file)
            except Exception as e:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.dummy_file + ' is not a valid RF spectrum file.')
                return
            self.btn_toggledummy.setEnabled(True)
            self.btn_plotdummy.setEnabled(True)

        thru_files = glob(os.path.join(str(self.txt_thru.text()), '*.txt'))
        if len(thru_files) != 1:
            self.txt_thru.setText('Please select a valid thru folder')
            self.thru_file = ''
            self.thru = None
            self.btn_togglethru.setEnabled(False)
            self.btn_plotthru.setEnabled(False)
        else:
            self.thru_file, = thru_files
            try:
                self.thru = Network(self.thru_file)
            except Exception as e:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.thru_file + ' is not a valid RF spectrum file.')
                return
            if self.dummy and self.thru_toggle_status:
                if self.dummy.number_of_ports == self.thru.number_of_ports and np.all(self.dummy.f==self.thru.f):
                    self.dummy = self.dummy.deembed_thru(self.thru)
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed deembed thru from dummy.')
                    return
            self.btn_togglethru.setEnabled(True)
            self.btn_plotthru.setEnabled(True)

        config.set('main', 'dut', self.txt_dut.text() if self.dut_folder else None)
        config.set('main', 'thru', self.txt_thru.text() if self.thru_file else None)
        config.set('main', 'dummy', self.txt_dummy.text() if self.dummy_file else None)
        config.set('main', 'ra', self.txt_ra.text())
        self.load_spectrum(reinitialise)

    def load_clicked(self):     # workaround: if we connect button signal directly to load, we get reinitialise=False
        self.load(True)

    def clear_ax(self):
        for ax in [self.ax]+self.ax_y_list+self.ax_s_list:
            for artist in ax.lines+ax.collections:
                artist.remove()
            ax.set_prop_cycle(None)
            ax.set_title('')
        for canvas in [self.canvas, self.canvas_y, self.canvas_s]:
            canvas.draw()

    def load_spectrum(self, first_load=False):
        # clean up the axis
        self.clear_ax()
        self.line_r = None
        self.line_i = None

        params = params_from_filename(os.path.join(self.dut_folder, self.dut_files[self.current_index]))
        if not first_load and self.dut_files[self.current_index] in self.duts:
            self.dut = self.duts[self.dut_files[self.current_index]]
        else:
            # try to load spectrum and check its compatibility
            try:
                self.dut = Network(os.path.join(self.dut_folder, self.dut_files[self.current_index]))
            except Exception as e:
                QMessageBox.warning(self, 'Warning', 'File: '+self.dut_files[self.current_index]+' is not a valid RF spectrum file.')
                return
            if self.thru and self.thru_toggle_status:
                if self.thru.number_of_ports == self.dut.number_of_ports and np.all(self.thru.f==self.dut.f):
                    self.dut = self.dut.deembed_thru(self.thru)
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed thru.')
            if self.dummy and self.dummy_toggle_status:
                if self.dummy.number_of_ports == self.dut.number_of_ports and np.all(self.dummy.f==self.dut.f):
                    self.dut.y -= self.dummy.y
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed dummy.')
            try:
                ra = float(self.txt_ra.text())
            except:
                QMessageBox.warning(self, 'Warning', 'Invalid value for Ra.')
                ra = 0.
            if not ra == 0:
                y = np.zeros(self.dut.y.shape, dtype=complex)
                y[:,0,0] = 1./(1./self.dut.y[:,0,0]-ra)
                y[:,0,1] = 1./(1./self.dut.y[:,0,1]+ra)
                y[:,1,0] = 1./(1./self.dut.y[:,1,0]+ra)
                y[:,1,1] = 1./(1./self.dut.y[:,1,1]-ra)
                self.dut.y = y
            self.duts[self.dut_files[self.current_index]] = copy(self.dut)

        # plot single Y parameter
        pm = -1. if self.fitted_param[0] == '-' else +1
        i = int(self.fitted_param[2])-1
        j = int(self.fitted_param[3])-1
        self.y = pm*self.dut.y[:,i,j]
        self.ax.plot(self.dut.f/1e9, self.y.real*1e3, label='Re')
        self.ax.plot(self.dut.f/1e9, self.y.imag*1e3, label='Im')
        self.ax.legend()

        # plot all Y parameters
        for i,ax in enumerate(self.ax_y_list):
            y = self.dut.y[:,i//2,i%2]
            ax.plot(self.dut.f/1e9, y.real*1e3, label='Re')
            ax.plot(self.dut.f/1e9, y.imag*1e3, label='Im')
            if not i:
                ax.legend()

        # plot all S parameters
        for i,ax in enumerate(self.ax_s_list):
            s = self.dut.s[:,i//2,i%2]
            ax.plot(self.dut.f/1e9, s.real, label='Re')
            ax.plot(self.dut.f/1e9, s.imag, label='Im')
            if not i:
                ax.legend()

        # update titles
        title = ', '.join([key + '=' + str(params[key]) for key in params])
        self.ax.set_title(title)
        for fig in [self.figure_y, self.figure_s]:
            fig.suptitle(title)
            fig.subplots_adjust(top=0.9)

        if first_load:
            for ax in [self.ax]+self.ax_y_list+self.ax_s_list:
                ax.set_xlim([min(self.dut.f/1e9), max(self.dut.f/1e9)])
            for toolbar in [self.toolbar, self.toolbar_y, self.toolbar_s]:
                toolbar.update()
                toolbar.push_current()

        # draw model if available
        if self.model:
            if self.dut_files[self.current_index] in self.model_params:
                self.update_values(self.model_params[self.dut_files[self.current_index]])
            else:
                self.reset_values()

        # update canvas
        for canvas in [self.canvas, self.canvas_y, self.canvas_s]:
            canvas.draw()

    def toggledummy(self):
        if self.dummy_toggle_status:
            self.dummy_toggle_status = False
            self.btn_toggledummy.setIcon(self.toggleoff_icon)
        else:
            self.dummy_toggle_status = True
            self.btn_toggledummy.setIcon(self.toggleon_icon)
        self.load(reinitialise=False)

    def togglethru(self):
        if self.thru_toggle_status:
            self.thru_toggle_status = False
            self.btn_togglethru.setIcon(self.toggleoff_icon)
        else:
            self.thru_toggle_status = True
            self.btn_togglethru.setIcon(self.toggleon_icon)
        self.load(reinitialise=False)

    def plotdummy(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Dummy'+(' (deembedded thru)' if self.thru and self.thru_toggle_status else ''))
        dialog.setModal(True)
        figure = plt.figure()
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, dialog)
        l = QVBoxLayout()
        for w in [toolbar, canvas]:
            l.addWidget(w)
        dialog.setLayout(l)
        self.dummy.plot_mat('y', ylim=1e-3, fig=figure)
        figure.suptitle(self.dummy.name)
        figure.subplots_adjust(top=0.9)
        canvas.draw()
        dialog.show()

    def plotthru(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Thru')
        dialog.setModal(True)
        figure = plt.figure()
        ax = figure.add_subplot(111)
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, dialog)
        l = QVBoxLayout()
        for w in [toolbar, canvas]:
            l.addWidget(w)
        dialog.setLayout(l)
        name = self.thru.name
        self.thru.name = None       # workaround to avoid cluttering the legend
        self.thru.plot_s_deg(ax=ax)
        ax.set_title(name)
        self.thru.name = name
        canvas.draw()
        dialog.show()

    def parameter_modified(self):
        self.fitted_param = self.cmb_plusminus.currentText()+self.cmb_parameter.currentText()
        self.ax.set_ylabel(self.fitted_param+' [mS]')
        self.canvas.draw()
        if self.dut_files:
            self.load_spectrum()

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
        f = np.asarray(self.dut.f)
        try:
            y = self.model.admittance(2.*np.pi*f, **self.model.values)
        except Exception as e:
            QMessageBox.critical(self, "Error", "Could not calculate model admittance: " + str(e.message))
            return

        if self.line_r:
            self.line_r.set_ydata(y.real*1e3)
            self.line_i.set_ydata(y.imag*1e3)
        else:
            self.line_r, = self.ax.plot(f/1e9, y.real*1e3, '-.')
            self.line_i, = self.ax.plot(f/1e9, y.imag*1e3, '-.')
        self.canvas.draw()

        # store new model data
        self.model_params[self.dut_files[self.current_index]] = copy(self.model.values)

    def browse_model(self):
        model_file, filter = QFileDialog.getOpenFileName(self, 'Choose model',
                                                         directory=os.path.join(os.path.dirname(__file__), 'models'),
                                                         filter='*.py')

        if model_file:
            self.txt_model.setText(model_file)

    def load_model(self):
        # unload previous model
        clearLayout(self.sl_layout)
        self.model = None
        self.sliders = {}
        self.checkboxes = {}
        self.cmb_fitmethod.clear()

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
        except AttributeError:
            pass
        self.enable_checkboxes(self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()))
        self.plot_fit()
        try:
            self.model.update_info_widget()
        except AttributeError:
            pass

        config.set('main', 'model', filename)
        return True

    def fit_model(self):
        if not self.dut:
            QMessageBox.warning(self, 'Warning', 'Please load some data first.')
            return
        if self.model:
            fit_method = getattr(self.model, 'fit_' + str(self.cmb_fitmethod.currentText()))
            try:
                if self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex()):
                    fit_method(self.dut.f, self.y, self.checkboxes)
                else:
                    fit_method(self.dut.f, self.y)
            except Exception as e:
                QMessageBox.critical(self, "Error", "Error during fit: " + str(e.message))
                return
            for p in self.model.values:
                self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])

    def fit_all(self):
        self.fitting_all += 1
        if self.fitting_all > 1:
            return

        self.btn_fitall.setText('Stop fitting')

        widgets = [self.data_loading, self.sliderwidget, self.saving, self.btn_fit, self.txt_model, self.btn_browsemodel,
                   self.btn_loadmodel]
        for w in widgets:
            w.setEnabled(False)

        for i in range(len(self.dut_files)):
            if self.fitting_all > 1: # user requested stop
                break
            self.current_index = i
            self.load_spectrum()
            self.fit_model()
            QApplication.processEvents()

        for w in widgets:
            w.setEnabled(True)

        self.btn_fitall.setText('Fit all')
        self.fitting_all = 0

    def value_changed(self, slider):
        self.model.values[slider.id] = slider.value() * self.model.params[slider.id][3]
        self.plot_fit()
        try:
            self.model.update_info_widget()
        except AttributeError:
            pass

    def enable_checkboxes(self, b=True):
        for p in self.checkboxes:
            self.checkboxes[p].setEnabled(b)

    def fitmethod_changed(self):
        enable_checkboxes = self.cmb_fitmethod.itemData(self.cmb_fitmethod.currentIndex())
        self.enable_checkboxes(enable_checkboxes)

    def update_values(self, values):
        self.model.values.update(values)
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])
        self.plot_fit()

    def reset_values(self):
        if self.model:
            self.model.reset_values()
        for p in self.model.values:
            self.sliders[p].setValue(self.model.values[p] / self.model.params[p][3])
        self.plot_fit()

    def browse_results(self):
        results_file, filter = QFileDialog.getSaveFileName(self, 'Results file', options=QFileDialog.DontConfirmOverwrite)
        if results_file:
            self.txt_resultsfile.setText(results_file)

    def save_results(self):
        res_fname = self.txt_resultsfile.text()
        res_folder = os.path.dirname(res_fname)
        if not res_fname or res_fname == 'Path to results file...':
            QMessageBox.warning(self, 'Error', 'Please select a valid results file for saving.')
            return
        if os.path.exists(self.txt_resultsfile.text()):
            if QMessageBox.question(self, 'File exists', 'Overwrite existing file?') != QMessageBox.Yes:
                return
        with open(self.txt_resultsfile.text(), 'w') as f:
            # write the header
            f.write('# fitting results generated by P13pt spectrum fitter\r\n')
            f.write('# dut: ' + os.path.relpath(self.dut_folder, res_folder).replace('\\', '/') + '\r\n')
            if self.thru and self.thru_toggle_status:
                f.write('# thru: ' + os.path.relpath(self.thru_file, res_folder).replace('\\', '/') + '\r\n')
            if self.dummy and self.dummy_toggle_status:
                f.write('# dummy: ' + os.path.relpath(self.dummy_file, res_folder).replace('\\', '/') + '\r\n')
            f.write('# model: ' + os.path.basename(self.model_file).replace('\\', '/') + '\r\n')
            try:
                ra = float(self.txt_ra.text())
            except:
                ra = 0.
            if not ra == 0:
                f.write('# ra: ' + str(ra) + '\r\n')

            # determine columns
            f.write('# filename\t')
            for p in self.dut.params:
                f.write(p + '\t')
            f.write('\t'.join([p for p in self.model.params]))
            f.write('\r\n')

            # write data
            filelist = sorted([filename for filename in self.model_params])
            for filename in filelist:
                f.write(filename + '\t')
                # TODO: what if some filenames do not contain all parameters? should catch exceptions
                for p in self.dut.params:
                    f.write(str(params_from_filename(filename)[p]) + '\t')
                f.write('\t'.join([str(self.model_params[filename][p]) for p in self.model.params]))
                f.write('\r\n')

    def load_results(self):
        res_fname = self.txt_resultsfile.text()
        res_folder = os.path.dirname(res_fname)
        # read the data
        try:
            data, dut, thru, dummy, model, ra = load_fitresults(res_fname, readfilenameparams=False, extrainfo=True)
        except IOError:
            QMessageBox.warning(self, 'Error', 'Could not load data')
            return

        # check at least the filename field is present in the data
        if not data or 'filename' not in data:
            QMessageBox.warning(self, 'Error', 'Could not load data')
            return

        # load the dataset provided in the results file
        self.txt_dut.setText(os.path.join(res_folder, dut))
        self.txt_thru.setText(os.path.dirname(os.path.join(res_folder, thru)) if thru else '')
        self.txt_dummy.setText(os.path.dirname(os.path.join(res_folder, dummy)) if dummy else '')
        self.txt_ra.setText(str(ra) if ra else '0')
        self.load()

        # try to load the model provided in the results file
        self.txt_model.setText(os.path.join(os.path.dirname(__file__), 'models', model))
        if self.load_model():
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
                # careful, this will also add the parameters from the filename to the model params
                # TODO: repair this (i.e. let the load_fitresults function inform the user about the number of filename parameters that need to be taken into account)
                values = [float(data[p][i]) for p in params]
                self.model_params[f] = dict(zip(params, values))

        # just reload the spectrum to be sure that the model is plotted correctly
        self.load_spectrum()

    def browse_picfolder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choose folder')
        if folder:
            self.txt_picfolder.setText(folder)

    def savepic(self):
        if self.dut:
            name, ext = os.path.splitext(self.dut_files[self.current_index])
            self.figure.savefig(os.path.join(self.txt_picfolder.text(), name + '.png'))

    def saveallpics(self):
        for i in range(len(self.dut_files)):
            self.current_index = i
            self.load_spectrum()
            self.savepic()
            QApplication.processEvents()

def msghandler(type, context, message):
    if type == QtInfoMsg:
        QMessageBox.information(None, 'Info', message)
    elif type == QtDebugMsg:
        QMessageBox.information(None, 'Debug', message)
    elif type == QtCriticalMsg:
        QMessageBox.critical(None, 'Critical', message)
    elif type == QtWarningMsg:
        QMessageBox.warning(None, 'Warning', message)
    elif type == QtFatalMsg:
        QMessageBox.critical(None, 'Fatal error', message)

if __name__ == '__main__':
    qInstallMessageHandler(msghandler)

    # CD into directory where this script is saved
    d = os.path.dirname(__file__)
    if d != '': os.chdir(d)

    # Read config file
    config = ConfigParser.RawConfigParser()
    config.read('spectrumfitter.cfg')

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('audacity.png'))

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    # Writing our configuration file to 'mdb.cfg'
    with open('spectrumfitter.cfg', 'wb') as configfile:
        config.write(configfile)

    sys.exit(ret)
