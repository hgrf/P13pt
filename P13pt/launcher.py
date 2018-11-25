import sys
from subprocess import call
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QHBoxLayout)

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('spectrumfitter/audacity.png'))

    launcher = QWidget()
    btn_spectrumfitter = QPushButton(QIcon('spectrumfitter/audacity.png'), 'SpectrumFitter')
    btn_mascril = QPushButton(QIcon('mascril/tools-wizard.png'), 'Mercury Acquisition Script Launcher')
    layout = QHBoxLayout()
    for w in [btn_spectrumfitter, btn_mascril]:
        layout.addWidget(w)
    launcher.setLayout(layout)

    btn_spectrumfitter.clicked.connect(launch_spectrumfitter)
    btn_mascril.clicked.connect(launch_mascril)

    launcher.setWindowTitle('P13pt')
    launcher.show()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)

def launch_spectrumfitter():
    call(["spectrumfitter", ""])

def launch_mascril():
    call(["mascril", ""])

if __name__ == '__main__':
    main()
