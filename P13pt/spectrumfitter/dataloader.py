import os
from glob import glob
import numpy as np
from matplotlib import pyplot as plt
from P13pt.rfspectrum import Network
from PyQt5.QtCore import QSignalMapper, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
                             QFileDialog, QMessageBox, QDialog)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

def check_deembedding_compatibility(ntwk1, ntwk2):
    # TODO: careful when de-embedding thru from thru
    return ntwk1.number_of_ports == ntwk2.number_of_ports and np.max(np.abs(ntwk1.f - ntwk2.f)) < 1e-3

class DataLoader(QWidget):
    dataset_changed = pyqtSignal()
    new_file_in_dataset = pyqtSignal(str)
    deembedding_changed = pyqtSignal()
    dut_folder = None
    dut_files = None
    dummy_raw = None
    dummy_deem = None
    dummy = None
    dummy_file = None
    dummy_toggle_status = True
    thru = None
    thru_file = None
    thru_toggle_status = True
    ra = None
    duts = {}

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        file_icon = QIcon('../icons/file.png')
        folder_icon = QIcon('../icons/folder.png')
        plot_icon = QIcon('../icons/plot.png')
        self.toggleon_icon = QIcon('../icons/on.png')
        self.toggleoff_icon = QIcon('../icons/off.png')

        self.txt_dut = QLineEdit()
        self.btn_browsedut_file = QPushButton(file_icon, '')
        self.btn_browsedut_folder = QPushButton(folder_icon, '')

        self.txt_thru = QLineEdit()
        self.btn_browsethru_file = QPushButton(file_icon, '')
        self.btn_browsethru_folder = QPushButton(folder_icon, '')
        self.btn_togglethru = QPushButton(self.toggleon_icon, '')
        self.btn_plotthru = QPushButton(plot_icon, '')

        self.txt_dummy = QLineEdit()
        self.btn_browsedummy_file = QPushButton(file_icon, '')
        self.btn_browsedummy_folder = QPushButton(folder_icon, '')
        self.btn_toggledummy = QPushButton(self.toggleon_icon, '')
        self.btn_plotdummy = QPushButton(plot_icon, '')

        for w in [self.btn_browsedut_file, self.btn_browsethru_file, self.btn_browsedummy_file]:
            w.setToolTip('Browse file')
        for w in [self.btn_browsedut_folder, self.btn_browsethru_folder, self.btn_browsedummy_folder]:
            w.setToolTip('Browse folder')
        for w in [self.btn_togglethru, self.btn_toggledummy]:
            w.setEnabled(False)
        for w in [self.btn_plotthru, self.btn_plotdummy]:
            w.setToolTip('Plot')
            w.setEnabled(False)

        self.btn_load = QPushButton('Load dataset')
        self.txt_ra = QLineEdit()

        l = QVBoxLayout()
        for field in [[QLabel('DUT:'), self.txt_dut, self.btn_browsedut_file, self.btn_browsedut_folder],
                      [QLabel('Thru:'), self.txt_thru, self.btn_browsethru_file, self.btn_browsethru_folder,
                       self.btn_togglethru, self.btn_plotthru],
                      [QLabel('Dummy:'), self.txt_dummy, self.btn_browsedummy_file, self.btn_browsedummy_folder,
                       self.btn_toggledummy, self.btn_plotdummy]]:
            hl = QHBoxLayout()
            for w in field:
                hl.addWidget(w)
            l.addLayout(hl)
        hl = QHBoxLayout()
        for w in [QLabel('Contact resistance:'), self.txt_ra, self.btn_load]:
            hl.addWidget(w)
        l.addLayout(hl)
        self.setLayout(l)

        # initialise data loader
        self.clear()

        # set up folder watcher
        self.timer = QTimer()
        self.timer.setInterval(1000)       # check for changes every second
        self.timer.timeout.connect(self.watch_folder)

        # make connections
        self.map_browse = QSignalMapper(self)
        for x in ['dut', 'thru', 'dummy']:
            self.__dict__['btn_browse'+x+'_folder'].clicked.connect(self.map_browse.map)
            self.__dict__['btn_browse'+x+'_file'].clicked.connect(self.map_browse.map)
            self.map_browse.setMapping(self.__dict__['btn_browse'+x+'_folder'], x+'_folder')
            self.map_browse.setMapping(self.__dict__['btn_browse' + x + '_file'], x + '_file')
        self.map_browse.mapped[str].connect(self.browse)
        self.btn_togglethru.clicked.connect(self.toggle_thru)
        self.btn_toggledummy.clicked.connect(self.toggle_dummy)
        self.btn_plotdummy.clicked.connect(self.plot_dummy)
        self.btn_plotthru.clicked.connect(self.plot_thru)
        self.btn_load.clicked.connect(self.load_dataset)

    def browse(self, x):
        # open browser and update the text field
        field, type = x.split('_')
        if type == 'folder':
            folder = QFileDialog.getExistingDirectory(self, 'Choose folder')
            if folder:
                self.__dict__['txt_'+field].setText(folder)
        elif type == 'file':
            filename, filter = QFileDialog.getOpenFileName(self, 'Choose file', filter='*.txt *.s2p *.dat')
            if filename:
                self.__dict__['txt_'+field].setText(filename)

    def get_spectra_files(self, path, tellmeifitsafolder=False):
        supported_exts = ['.txt', '.s2p', '.dat']
        folder = None
        files = []
        itsafolder = False

        if os.path.isdir(path):
            folder = path
            for ext in supported_exts:
                files += [os.path.basename(x) for x in sorted(glob(os.path.join(folder, '*'+ext)))]
            itsafolder = True
        elif os.path.isfile(path):
            basename, ext = os.path.splitext(path)
            if ext.lower() in supported_exts:
                folder = os.path.dirname(path)
                files += [path]
        else:
            pass

        if tellmeifitsafolder:
            return folder, files, itsafolder
        else:
            return folder, files

    @pyqtSlot()
    def load_dataset(self, dut=None, thru=None, dummy=None, ra=None):
        # This function inspects the provided folders and will try to load the dummy and thru spectra for de-embedding.
        # It does not load the DUT spectra, since this might take a long time, they can be accessed via the get_spectrum
        # function.

        # tidy up first
        self.empty_cache()
        self.dut_folder = None
        self.dut_files = None
        self.thru_file = None
        self.thru = None
        self.dummy_file = None
        self.dummy_raw = None
        self.dummy_deem = None
        self.dummy = None
        self.btn_toggledummy.setEnabled(False)
        self.btn_togglethru.setEnabled(False)
        self.btn_plotdummy.setEnabled(False)
        self.btn_plotthru.setEnabled(False)

        # take what you can from the function parameters, the rest from the text fields
        dut = str(self.txt_dut.text()) if not dut else dut
        thru = str(self.txt_thru.text()) if not thru else thru
        dummy = str(self.txt_dummy.text()) if not dummy else dummy
        ra = str(self.txt_ra.text()) if not ra else ra

        # update the text fields
        self.txt_dut.setText(dut)
        self.txt_thru.setText(thru)
        self.txt_dummy.setText(dummy)
        self.txt_ra.setText(str(ra) if ra else '0')

        # check provided files
        self.dut_folder, self.dut_files, itsafolder = self.get_spectra_files(dut, tellmeifitsafolder=True)
        if not self.dut_files:
            QMessageBox.warning(self, 'Warning', 'Please select a valid DUT folder or file')

        # if the user loaded a folder, switch on the folder watcher
        if itsafolder:
            self.timer.start()
        else:
            self.timer.stop()

        thru_folder, thru_files = self.get_spectra_files(thru)
        if len(thru_files) != 1:
            self.txt_thru.setText('Please select a valid thru folder or file')
        else:
            self.thru_file = os.path.join(thru_folder, thru_files[0])

        dummy_folder, dummy_files = self.get_spectra_files(dummy)
        if len(dummy_files) != 1:
            self.txt_dummy.setText('Please select a valid dummy folder or file')
        else:
            self.dummy_file = os.path.join(dummy_folder, dummy_files[0])

        # load the provided files
        if self.dummy_file:
            try:
                self.dummy_raw = Network(self.dummy_file)
                assert self.dummy_raw.number_of_ports == 2
                self.btn_toggledummy.setEnabled(True)
                self.btn_plotdummy.setEnabled(True)
            except Exception as e:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.dummy_file + ' is not a valid 2-port RF spectrum file.')
                self.dummy_raw = None

        if self.thru_file:
            try:
                self.thru = Network(self.thru_file)
                assert self.thru.number_of_ports == 2
                self.btn_togglethru.setEnabled(True)
                self.btn_plotthru.setEnabled(True)
            except Exception as e:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.thru_file + ' is not a valid 2-port RF spectrum file.')
                self.thru = None

        self.dummy_deem = None
        if self.dummy_raw and self.thru:
            # check for mHz deviation, since sometimes the frequency value saved is
            # not 100% equal when importing from different file formats...
            if not check_deembedding_compatibility(self.dummy_raw, self.thru):
                QMessageBox.warning(self, 'Warning', 'Dummy and thru are not compatible')
                self.dummy_raw = None
                self.thru = None
            else:
                self.dummy_deem = self.dummy_raw.deembed_thru(self.thru)

        self.dummy = self.dummy_deem if (self.thru_toggle_status and self.thru) else self.dummy_raw

        self.dataset_changed.emit()

    def get_spectrum(self, index):
        # check if the spectrum is already prepared
        filename = self.dut_files[index]
        if filename in self.duts:
            return self.duts[filename]
        else:
            # try to load spectrum and check its compatibility
            try:
                dut = Network(os.path.join(self.dut_folder, filename))
            except Exception:
                QMessageBox.warning(self, 'Warning', 'File: ' + filename + ' is not a valid RF spectrum file.')
                return None
            if self.thru and self.thru_toggle_status:
                if check_deembedding_compatibility(dut, self.thru):
                    dut = dut.deembed_thru(self.thru)
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed thru.')
            if self.dummy and self.dummy_toggle_status:
                if check_deembedding_compatibility(dut, self.dummy):
                    dut.y -= self.dummy.y
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed dummy.')
            try:
                ra = float(self.txt_ra.text())
            except:
                QMessageBox.warning(self, 'Warning', 'Invalid value for contact resistance. Using zero.')
                ra = 0.
            if not ra == 0:
                y = np.zeros(dut.y.shape, dtype=complex)
                y[:, 0, 0] = 1. / (1. / dut.y[:, 0, 0] - ra)
                y[:, 0, 1] = 1. / (1. / dut.y[:, 0, 1] + ra)
                y[:, 1, 0] = 1. / (1. / dut.y[:, 1, 0] + ra)
                y[:, 1, 1] = 1. / (1. / dut.y[:, 1, 1] - ra)
                dut.y = y
            self.duts[filename] = dut
            return dut

    def empty_cache(self):
        self.duts = {}          # empty the DUT dictionary

    def toggle_thru(self):
        self.empty_cache()
        self.thru_toggle_status = not self.thru_toggle_status
        self.btn_togglethru.setIcon(self.toggleon_icon if self.thru_toggle_status else self.toggleoff_icon)
        self.dummy = self.dummy_deem if (self.thru_toggle_status and self.thru) else self.dummy_raw
        self.deembedding_changed.emit()

    def toggle_dummy(self):
        self.empty_cache()
        self.dummy_toggle_status = not self.dummy_toggle_status
        self.btn_toggledummy.setIcon(self.toggleon_icon if self.dummy_toggle_status else self.toggleoff_icon)
        self.deembedding_changed.emit()

    def plot_dummy(self):
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

    def plot_thru(self):
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

    def clear(self):
        self.txt_dut.setText('Path to DUT...')
        self.txt_thru.setText('Path to thru...')
        self.txt_dummy.setText('Path to dummy...')
        self.txt_ra.setText('0')

    def watch_folder(self):
        folder, files = self.get_spectra_files(self.dut_folder)
        for f in files:
            if f not in self.dut_files:
                self.dut_files.append(f)
                self.new_file_in_dataset.emit(f)