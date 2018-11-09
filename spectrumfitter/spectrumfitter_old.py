#!/usr/bin/python
import sys
import os
from glob import glob
from P13pt.rfspectrum import Network
from P13pt.params_from_filename import params_from_filename
import ConfigParser

from PyQt5.QtCore import (Qt, QSignalMapper, qInstallMessageHandler, QtInfoMsg, QtCriticalMsg, QtDebugMsg,
                          QtWarningMsg, QtFatalMsg)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                         QPushButton, QFileDialog, QMessageBox, QSlider, QSpinBox, QLabel,
                         QWidgetItem, QSplitter, QComboBox, QCheckBox, QTabWidget, QDialog,
                         QListWidget, QMainWindow, QDockWidget, QMenu)

try:
    from PyQt5.QtCore import QString
except ImportError:
    QString = str

from dataloader import DataLoader
from fitter import Fitter
from plotter import Plotter
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import matplotlib.pyplot as plt
import numpy as np
from copy import copy

class MainWindow(QMainWindow):
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
    model_params = {}
    fitted_param = '-Y12'
    dummy_toggle_status = True
    thru_toggle_status = True
    fitting_all = 0

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        browse_icon = QIcon('../icons/folder.png')
        self.toggleon_icon = QIcon('../icons/on.png')
        self.toggleoff_icon = QIcon('../icons/off.png')

        # set up data loading area
        self.dock_loading = QDockWidget('Data loading', self)
        self.loading = DataLoader()
        self.dock_loading.setWidget(self.loading)

        # set up list widget for file list
        self.dock_filelist = QDockWidget('File list', self)
        self.filelist = QListWidget(self.dock_filelist)
        self.dock_filelist.setWidget(self.filelist)

        # set up tabbed widget for different plots
        self.plotting = Plotter()
        self.setCentralWidget(self.plotting)

        self.fitting = Fitter()

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
        self.dock_right_widget = QDockWidget('Fitting & Saving', self)
        self.right_widget = QWidget()
        self.dock_right_widget.setWidget(self.right_widget)
        l = QVBoxLayout()
        l.addWidget(self.fitting)
        l.addWidget(self.saving)
        self.right_widget.setLayout(l)

        # make connections
        self.btn_prev.clicked.connect(self.prev_spectrum)
        self.btn_next.clicked.connect(self.next_spectrum)
        self.cmb_plusminus.currentTextChanged.connect(self.parameter_modified)
        self.cmb_parameter.currentTextChanged.connect(self.parameter_modified)
        self.cmb_fitmethod.currentIndexChanged.connect(self.fitmethod_changed)
        self.btn_browseresults.clicked.connect(self.browse_results)
        self.btn_saveresults.clicked.connect(self.save_results)
        self.btn_loadresults.clicked.connect(self.load_results)
        self.btn_browsepicfolder.clicked.connect(self.browse_picfolder)
        self.btn_savepic.clicked.connect(self.savepic)
        self.btn_saveallpics.clicked.connect(self.saveallpics)
        self.filelist.currentRowChanged.connect(self.load_index)

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
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_filelist)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_right_widget)
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_loading)

        self.viewMenu = self.menuBar().addMenu('View')
        for w in [self.dock_filelist, self.dock_right_widget, self.dock_loading]:
            self.viewMenu.addAction(w.toggleViewAction())

        # show the splitter
        self.show()

        # make the window big
        #self.resize(1200,800)

        # Set window title
        self.setWindowTitle("Spectrum Fitter")


    def parameter_modified(self):
        self.fitted_param = self.cmb_plusminus.currentText()+self.cmb_parameter.currentText()
        self.ax.set_ylabel(self.fitted_param+' [mS]')
        self.canvas.draw()
        if self.dut_files:
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
