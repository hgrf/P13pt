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
         self.txt_rho, self.txt_mobility, self.txt_modes) = [QLineEdit() for i in range(15)]
        self.txt_dirac_voltage = QLineEdit('0')
        self.txt_temperature = QLineEdit('0')
        l1 = QGridLayout()
        # set up left side ("intensive")
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
        # set up right side ("extensive")
        for row,w in enumerate(((QLabel('Sample width [um]:'), self.txt_width),
                                (QLabel('Sample length [um]:'), self.txt_length),
                                (QLabel('Total capacitance [fF]:'), self.txt_total_capa),
                                (QLabel('Total resistance [Ohm]:'), self.txt_total_r),
                                (QLabel('Total quantum capacitance [fF]:'), self.txt_total_cq),
                                (QLabel('Total inductance [pH]:'), self.txt_total_lk),
                                (QLabel('Number of ballistic modes:'), self.txt_modes))):
            l1.addWidget(w[0], row, 2)
            l1.addWidget(w[1], row, 3)
        # set up read only fields
        for w in (self.txt_cq, self.txt_lk, self.txt_total_cq, self.txt_total_lk,
                  self.txt_rho, self.txt_total_r, self.txt_total_capa, self.txt_modes):
            w.setReadOnly(True)
            w.setStyleSheet('QLineEdit { background-color: #EEEEEE; }')
        # set up signals
        for w in (self.txt_capa, self.txt_doping, self.txt_mobility, self.txt_dirac_voltage,
                  self.txt_gate_voltage, self.txt_temperature, self.txt_width, self.txt_length,
                  self.txt_total_capa, self.txt_fermi_level):
            w.textEdited.connect(self.update_values)
        self.setLayout(l1)
        self.setWindowTitle('Graphulator')
        self.show()

    def update_values(self):
        ####
        # gate voltage, Dirac point voltage, Fermi level, capacitance and doping are linked,
        # so we have to treat these cases carefully
        if self.sender() == self.txt_gate_voltage\
                or self.sender() == self.txt_dirac_voltage:
            try:
                Vg = float(self.txt_gate_voltage.text())
                Vdp = float(self.txt_dirac_voltage.text())
                C = float(self.txt_capa.text())*1e-3
                n = C*(Vg-Vdp)/e
                Ef = np.sign(n)*hbar*vf*np.sqrt(np.pi*np.abs(n))
                self.txt_doping.setText(str(n/1e16))
                self.txt_fermi_level.setText(str(Ef/e*1e3))
            except ValueError:
                pass

        if self.sender() == self.txt_doping:
            try:
                n = float(self.txt_doping.text())*1e16
                Ef = np.sign(n)*hbar*vf*np.sqrt(np.pi*np.abs(n))
                self.txt_fermi_level.setText(str(Ef/e*1e3))
                try:
                    Vdp = float(self.txt_dirac_voltage.text())
                    C = float(self.txt_capa.text()) * 1e-3
                    Vg = n * e / C + Vdp
                    self.txt_gate_voltage.setText(str(Vg))
                except ValueError:
                    pass
            except ValueError:
                pass

        if self.sender() == self.txt_fermi_level:
            try:
                Ef = float(self.txt_fermi_level.text())/1e3*e
                n = np.sign(Ef)/np.pi*(Ef/hbar/vf)**2
                self.txt_doping.setText(str(n/1e16))
                try:
                    Vdp = float(self.txt_dirac_voltage.text())
                    C = float(self.txt_capa.text())*1e-3
                    Vg = n*e/C+Vdp
                    self.txt_gate_voltage.setText(str(Vg))
                except ValueError:
                    pass
            except ValueError:
                pass

        if self.sender() == self.txt_capa:
            try:
                C = float(self.txt_capa.text())/1e3
                Vg = float(self.txt_gate_voltage.text())
                Vdp = float(self.txt_dirac_voltage.text())
                n = C*(Vg-Vdp)/e
                Ef = np.sign(n)*hbar*vf*np.sqrt(np.pi*np.abs(n))
                self.txt_doping.setText(str(n/1e16))
                self.txt_fermi_level.setText(str(Ef/e*1e3))
            except ValueError:
                pass
            try:
                C = float(self.txt_capa.text())/1e3
                L = float(self.txt_length.text())/1e6
                W = float(self.txt_width.text())/1e6
                self.txt_total_capa.setText(str(C*L*W*1e15))
            except ValueError:
                pass

        ####
        # the following we can do safely in any case, because we only write to read-only fields
        #
        # calculate Cq and Lk
        try:
            Ef = float(self.txt_fermi_level.text())/1e3*e
            T = float(self.txt_temperature.text())
            Lk = np.pi*hbar**2/e**2/Ef
            if T == 0.:
                Cq = (2*e**2)/(np.pi*(vf*hbar)**2)*Ef
            else:
                Cq = (2*e**2*kB*T)/(np.pi*(vf*hbar)**2)*(np.log(2+2*np.cosh(Ef/(kB*T))))
            self.txt_cq.setText(str(np.abs(Cq*1e3)))
            self.txt_lk.setText(str(np.abs(Lk*1e12)))
        except (ValueError, ZeroDivisionError):
            pass

        # calculate total Cq and Lk
        try:
            Cq = float(self.txt_cq.text())/1e3
            Lk = float(self.txt_lk.text())/1e12
            W = float(self.txt_width.text())/1e6
            L = float(self.txt_length.text())/1e6
            self.txt_total_cq.setText(str(Cq*L*W*1e15))
            self.txt_total_lk.setText(str(Lk*L/W*1e12))
        except ValueError:
            pass

        # calculate rho
        try:
            n = float(self.txt_doping.text())*1e16
            mu = float(self.txt_mobility.text())/1e4
            rho = 1./(np.abs(n)*e*mu)
            self.txt_rho.setText(str(rho))
        except ValueError:
            pass

        # calculate R
        try:
            rho = float(self.txt_rho.text())
            W = float(self.txt_width.text())/1e6
            L = float(self.txt_length.text())/1e6
            R = rho*L/W
            self.txt_total_r.setText(str(R))
        except ValueError:
            pass

        # calculate total C
        try:
            C = float(self.txt_capa.text())/1e3
            W = float(self.txt_width.text())/1e6
            L = float(self.txt_length.text())/1e6
            C = C*L*W
            self.txt_total_capa.setText(str(C*1e15))
        except ValueError:
            pass

        # calculate number of ballistic modes
        try:
            n = float(self.txt_doping.text())*1e16
            W = float(self.txt_width.text())/1e6
            kf = np.sqrt(np.pi*np.abs(n))
            self.txt_modes.setText(str(kf*W/np.pi))
        except ValueError:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('calculator.png'))

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)