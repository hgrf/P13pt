#!/usr/bin/python
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QLineEdit, QGridLayout
from P13pt.fundconst import e, vf, hbar, kB
import numpy as np

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        (self.txt_gate_voltage, self.txt_capa, self.txt_width,
         self.txt_length, self.txt_doping, self.txt_fermi_level,
         self.txt_cq, self.txt_lk, self.txt_total_capa,
         self.txt_total_r, self.txt_total_lk, self.txt_total_cq,
         self.txt_rho, self.txt_mobility) = [QLineEdit() for i in range(14)]
        self.txt_dirac_voltage = QLineEdit('0')
        self.txt_temperature = QLineEdit('0')
        l1 = QGridLayout()
        for row,w in enumerate(((QLabel('Gate voltage [V]:'), self.txt_gate_voltage),
                                (QLabel('Dirac point voltage [V]:'), self.txt_dirac_voltage),
                                (QLabel('Capacitance [fF/um^2]:'), self.txt_capa),
                                (QLabel('Doping [10^12 cm^-2]:'), self.txt_doping),
                                (QLabel('Temperature [K]:'), self.txt_temperature),
                                (QLabel('Fermi energy [meV]:'), self.txt_fermi_level),
                                (QLabel('Mobility [cm^2/Vs]:'), self.txt_mobility),
                                (QLabel('Resistivity [Ohm]:'), self.txt_rho),
                                (QLabel('Quantum capacitance [fF/um^2]:'), self.txt_cq),
                                (QLabel('Kinetic inductance [pH]:'), self.txt_lk))):
            l1.addWidget(w[0], row, 0)
            l1.addWidget(w[1], row, 1)
            w[1].textChanged.connect(self.update)
        for row,w in enumerate(((QLabel('Sample width [um]:'), self.txt_width),
                                (QLabel('Sample length [um]:'), self.txt_length),
                                (QLabel('Total capacitance [fF]:'), self.txt_total_capa),
                                (QLabel('Resistivity [Ohm]:'), self.txt_total_r),
                                (QLabel('Total quantum capacitance [fF]:'), self.txt_total_cq),
                                (QLabel('Total inductance [pH]:'), self.txt_total_lk))):
            l1.addWidget(w[0], row, 2)
            l1.addWidget(w[1], row, 3)
            w[1].textChanged.connect(self.update)
        self.setLayout(l1)
        self.setWindowTitle('Graphulator')
        self.show()

    def update(self):
        if self.sender() == self.txt_gate_voltage or\
                self.sender() == self.txt_capa or\
                self.sender() == self.txt_dirac_voltage:
            try:
                Vg = float(self.txt_gate_voltage.text())
                Vdp = float(self.txt_dirac_voltage.text())
                C = float(self.txt_capa.text())
                ####
                n = C * 1e-3 * (Vg - Vdp) / e
                self.txt_doping.setText(str(n / 1e16))
            except ValueError:
                pass

        if self.sender() == self.txt_doping or\
                self.sender() == self.txt_temperature:
            try:
                n = float(self.txt_doping.text())*1e16
                T = float(self.txt_temperature.text())
                ####
                Ef = np.sign(n) * hbar * vf * np.sqrt(np.pi * np.abs(n))
                Lk = np.pi * hbar ** 2 / e ** 2 / Ef
                if T == 0.:
                    Cq = (2 * e ** 2) / (np.pi * (vf * hbar) ** 2) * Ef
                else:
                    Cq = (2 * e ** 2 * kB * T) / (np.pi * (vf * hbar) ** 2) * (np.log(2 + 2 * np.cosh(Ef / (kB * T))))
                self.txt_fermi_level.setText(str(Ef / e * 1e3))
                self.txt_cq.setText(str(np.abs(Cq * 1e3)))
                self.txt_lk.setText(str(np.abs(Lk * 1e12)))
            except ValueError:
                pass

        if self.sender() == self.txt_mobility or\
                self.sender() == self.txt_doping:
            try:
                n = float(self.txt_doping.text())*1e16
                mu = float(self.txt_mobility.text())/1e4
                ####
                rho = 1. / (n * e * mu)
                self.txt_rho.setText(str(rho))
            except ValueError:
                pass

        if self.sender() == self.txt_rho or\
                self.sender() == self.txt_width or\
                self.sender() == self.txt_length:
            try:
                rho = float(self.txt_rho.text())
                W = float(self.txt_width.text())/1e6
                L = float(self.txt_length.text())/1e6
                R = rho * L / W
                ####
                self.txt_total_r.setText(str(R))
            except ValueError:
                pass

        if self.sender() == self.txt_lk or\
                self.sender() == self.txt_width or\
                self.sender() == self.txt_length:
            try:
                Lk = float(self.txt_lk.text())
                W = float(self.txt_width.text())/1e6
                L = float(self.txt_length.text())/1e6
                self.txt_total_lk.setText(str(Lk * L / W))
            except ValueError:
                pass

        if self.sender() == self.txt_cq or\
                self.sender() == self.txt_width or\
                self.sender() == self.txt_length:
            try:
                Cq = float(self.txt_cq.text())/1e3
                W = float(self.txt_width.text())/1e6
                L = float(self.txt_length.text())/1e6
                self.txt_total_cq.setText(str(Cq*L*W*1e15))
            except ValueError:
                pass

        if self.sender() == self.txt_capa or\
                self.sender() == self.txt_width or\
                self.sender() == self.txt_length:
            try:
                C = float(self.txt_capa.text())/1e3
                W = float(self.txt_width.text())/1e6
                L = float(self.txt_length.text())/1e6
                self.txt_total_capa.setText(str(C*L*W*1e15))
            except ValueError:
                pass

        if self.sender() == self.txt_total_capa or\
                self.sender() == self.txt_width or\
                self.sender() == self.txt_length:
            try:
                C = float(self.txt_total_capa.text())/1e15
                W = float(self.txt_width.text())/1e6
                L = float(self.txt_length.text())/1e6
                self.txt_capa.setText(str(C/L/W*1e3))
            except ValueError:
                pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('calculator.png'))

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)