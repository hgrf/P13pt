#!/usr/bin/python
import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QLineEdit, QGridLayout
from P13pt.fundconst import e, vf, hbar, kB
import numpy as np

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        lbl_gate_voltage = QLabel('Gate voltage [V]:')
        self.txt_gate_voltage = QLineEdit()
        lbl_dirac_voltage = QLabel('Dirac point voltage [V]:')
        self.txt_dirac_voltage = QLineEdit('0')
        lbl_capa = QLabel('Total capacitance [fF/um^2]:')
        self.txt_capa = QLineEdit()
        lbl_doping = QLabel('Doping [10^12 cm^-2]:')
        self.txt_doping = QLineEdit('')
        lbl_temperature = QLabel('Temperature [K]:')
        self.txt_temperature = QLineEdit('0')
        lbl_fermi_level = QLabel('Fermi energy [meV]:')
        self.txt_fermi_level = QLineEdit('')
        lbl_cq = QLabel('Quantum capacitance [fF/um^2]:')
        self.txt_cq = QLineEdit('')
        lbl_lk = QLabel('Kinetic inductance [pH]:')
        self.txt_lk = QLineEdit('')
        l1 = QGridLayout()
        for row,w in enumerate(((lbl_gate_voltage, self.txt_gate_voltage),
                                (lbl_dirac_voltage, self.txt_dirac_voltage),
                                (lbl_capa, self.txt_capa),
                                (lbl_doping, self.txt_doping),
                                (lbl_temperature, self.txt_temperature),
                                (lbl_fermi_level, self.txt_fermi_level),
                                (lbl_cq, self.txt_cq),
                                (lbl_lk, self.txt_lk))):
            l1.addWidget(w[0], row, 0)
            l1.addWidget(w[1], row, 1)
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
            except ValueError:
                return
            n = C*1e-3*(Vg-Vdp)/e
            self.txt_doping.setText(str(n/1e16))

        if self.sender() == self.txt_doping or\
                self.sender() == self.txt_temperature:
            try:
                n = float(self.txt_doping.text())*1e16
                T = float(self.txt_temperature.text())
            except ValueError:
                return
            Ef = np.sign(n)*hbar*vf*np.sqrt(np.pi*np.abs(n))
            Lk = np.pi*hbar**2/e**2/Ef
            if T == 0.:
                Cq = (2*e**2)/(np.pi*(vf*hbar)**2)*Ef
            else:
                Cq = (2*e**2*kB*T)/(np.pi*(vf*hbar)**2)*(np.log(2+2*np.cosh(Ef/(kB*T))))

            self.txt_fermi_level.setText(str(Ef/e*1e3))
            self.txt_cq.setText(str(Cq*1e3))
            self.txt_lk.setText(str(Lk*1e12))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('calculator.png'))

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)