import os
from glob import glob
import numpy as np
from matplotlib import pyplot as plt
from P13pt.rfspectrum import Network
from PyQt5.QtCore import QSignalMapper, pyqtSignal
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
    deembedding_changed = pyqtSignal()
    dut_folder = None
    dut_files = None
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

        browse_icon = QIcon('../icons/folder.png')
        plot_icon = QIcon('../icons/plot.png')
        self.toggleon_icon = QIcon('../icons/on.png')
        self.toggleoff_icon = QIcon('../icons/off.png')
        self.txt_dut = QLineEdit()
        self.btn_browsedut = QPushButton(browse_icon, '')
        self.txt_thru = QLineEdit()
        self.btn_browsethru = QPushButton(browse_icon, '')
        self.btn_togglethru = QPushButton(self.toggleon_icon, '')
        self.btn_togglethru.setEnabled(False)
        self.btn_plotthru = QPushButton(plot_icon, '')
        self.btn_plotthru.setToolTip('Plot')
        self.btn_plotthru.setEnabled(False)
        self.txt_dummy = QLineEdit()
        self.btn_browsedummy = QPushButton(browse_icon, '')
        self.btn_toggledummy = QPushButton(self.toggleon_icon, '')
        self.btn_toggledummy.setEnabled(False)
        self.btn_plotdummy = QPushButton(plot_icon, '')
        self.btn_plotdummy.setToolTip('Plot')
        self.btn_plotdummy.setEnabled(False)
        self.btn_load = QPushButton('Load dataset')
        self.clear()

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
        for w in [QLabel('Contact resistance:'), self.txt_ra, self.btn_load]:
            hl.addWidget(w)
        l.addLayout(hl)
        self.setLayout(l)

        # make connections
        self.map_browse = QSignalMapper(self)
        for x in ['dut', 'thru', 'dummy']:
            self.__dict__['btn_browse'+x].clicked.connect(self.map_browse.map)
            self.map_browse.setMapping(self.__dict__['btn_browse'+x], x)
        self.map_browse.mapped[str].connect(self.browse)
        self.btn_togglethru.clicked.connect(self.toggle_thru)
        self.btn_toggledummy.clicked.connect(self.toggle_dummy)
        self.btn_plotdummy.clicked.connect(self.plot_dummy)
        self.btn_plotthru.clicked.connect(self.plot_thru)
        self.btn_load.clicked.connect(self.load_dataset)

    def browse(self, x):
        # open browser and update the text field
        folder = QFileDialog.getExistingDirectory(self, 'Choose dataset')
        if folder:
            self.__dict__['txt_'+str(x)].setText(folder)

    def load_dataset(self):
        # This function inspects the provided folders and will try to load the
        # dummy and thru spectra for de-embedding.
        # It does not load the DUT spectra, since this might take a long time,
        # they can be accessed via the get_spectrum function.

        self.empty_cache()
        self.dut_folder = str(self.txt_dut.text())
        self.dut_files = [os.path.basename(x) for x in sorted(glob(os.path.join(self.dut_folder, '*.txt')))]
        self.dut_files += [os.path.basename(x) for x in sorted(glob(os.path.join(self.dut_folder, '*.s2p')))]

        if len(self.dut_files) < 1:
            QMessageBox.warning(self, 'Warning', 'Please select a valid DUT folder')
            self.dut_folder = ''
            return

        dummy_files = glob(os.path.join(str(self.txt_dummy.text()), '*.txt'))
        dummy_files += glob(os.path.join(str(self.txt_dummy.text()), '*.s2p'))
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
                # TODO: should not just return, but continue execution with dummy_file = '' etc.
                return
            self.btn_toggledummy.setEnabled(True)
            self.btn_plotdummy.setEnabled(True)

        thru_files = glob(os.path.join(str(self.txt_thru.text()), '*.txt'))
        thru_files += glob(os.path.join(str(self.txt_thru.text()), '*.s2p'))
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
            except Exception:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.thru_file + ' is not a valid RF spectrum file.')
                return
            if self.dummy and self.thru_toggle_status:
                # check for mHz deviation, since sometimes the frequency value saved is
                # not 100% equal when importing from different file formats...
                if check_deembedding_compatibility(self.dummy, self.thru):
                    self.dummy = self.dummy.deembed_thru(self.thru)
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed deembed thru from dummy.')
                    return
            self.btn_togglethru.setEnabled(True)
            self.btn_plotthru.setEnabled(True)

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
        # empty the DUT dictionary
        self.duts = {}

    def toggle_thru(self):
        self.thru_toggle_status = not self.thru_toggle_status
        self.btn_togglethru.setIcon(self.toggleon_icon if self.thru_toggle_status else self.toggleoff_icon)
        self.empty_cache()
        # TODO: deembed thru from dummy if required
        self.deembedding_changed.emit()

    def toggle_dummy(self):
        self.dummy_toggle_status = not self.dummy_toggle_status
        self.btn_toggledummy.setIcon(self.toggleon_icon if self.dummy_toggle_status else self.toggleoff_icon)
        self.empty_cache()
        # TODO: deembed thru from dummy if required
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