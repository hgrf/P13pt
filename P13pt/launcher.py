import os
import sys
from subprocess import call
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QToolButton, QHBoxLayout)

def main():
    # CD into directory where this script is saved
    d = os.path.dirname(__file__)
    if d != '': os.chdir(d)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('icons/P13pt.png'))

    launcher = QWidget()
    btn_spectrumfitter = QToolButton()
    btn_spectrumfitter.setIcon(QIcon('spectrumfitter/audacity.png'))
    btn_spectrumfitter.setText('SpectrumFitter')
    btn_mascril = QToolButton()
    btn_mascril.setIcon(QIcon('mascril/tools-wizard.png'))
    btn_mascril.setText('Mercury Acquisition\nScript Launcher')
    btn_graphulator = QToolButton()
    btn_graphulator.setIcon(QIcon('graphulator/calculator.png'))
    btn_graphulator.setText('Graphulator')
    btn_mdb = QToolButton()
    btn_mdb.setIcon(QIcon('mdb/kmplot-2.png'))
    btn_mdb.setText('Mercury Data\nBrowser')
    layout = QHBoxLayout()
    for w in [btn_spectrumfitter, btn_mascril, btn_graphulator, btn_mdb]:
        w.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        w.setIconSize(QSize(64,64))
        w.setMinimumWidth(150)
        w.setMinimumHeight(150)
        layout.addWidget(w)
    launcher.setLayout(layout)

    btn_spectrumfitter.clicked.connect(launch_spectrumfitter)
    btn_mascril.clicked.connect(launch_mascril)
    btn_graphulator.clicked.connect(launch_graphulator)
    btn_mdb.clicked.connect(launch_mdb)

    launcher.setWindowTitle('P13pt')
    launcher.show()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)

def launch_spectrumfitter():
    call(["spectrumfitter", ""])

def launch_mascril():
    call(["mascril", ""])

def launch_graphulator():
    call(["graphulator", ""])

def launch_mdb():
    call(["mdb", ""])

if __name__ == '__main__':
    main()
