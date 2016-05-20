import sys

import numpy as np

from PyQt4.QtGui import (QApplication, QFileSystemModel,
                         QSplitter, QTreeView, QVBoxLayout,
                         QHBoxLayout, QListWidgetItem,
                         QListWidget, QPushButton, QWidget,
                         QSizePolicy, QMessageBox, QLabel,
                         QTextEdit, QTabWidget, QComboBox)
from PyQt4.QtCore import QDir, Qt, pyqtSlot

from plotter import Plotter
from analyser import Analyser

import os
import numpy as np
import ConfigParser
import random

def scan():
    folders = []
    for i in treev.selectedIndexes():
        folders.append(model.fileInfo(i).absoluteFilePath())

    if not len(folders):
        QMessageBox.information(splitter, "No folders selected",
            "Please select folders to scan")
        return

    for fo in folders:
        for root, dirnames, filenames in os.walk(str(fo)):
            for fi in filenames:
                if fi.endswith(('.txt', '.csv')):
                    listw.addItem(os.path.join(root, fi))

def clear():
    listw.clear()

def setroot():
    i = treev.selectedIndexes()[0]
    root = model.fileInfo(i).absoluteFilePath()
    model.setRootPath(root)
    treev.setRootIndex(i)
    config.set('main', 'root', root)

def forgetroot():
    root = None
    model.setRootPath(QDir.rootPath())
    treev.setRootIndex(model.index(QDir.rootPath()))
    config.remove_option('main', 'root')

if __name__ == '__main__':
    # CD into directory where this script is saved
    d = os.path.dirname(__file__)
    if d != '': os.chdir(d)

    # Read config file
    config = ConfigParser.RawConfigParser()
    config.read('mdb.cfg')
    try:
        root = config.get('main', 'root')
    except ConfigParser.NoSectionError:
        config.add_section('main')
        root = None
    except ConfigParser.NoOptionError:
        root = None

    app = QApplication(sys.argv)

    splitter = QSplitter()

    # Set up file system model for tree view
    model = QFileSystemModel()
    model.setRootPath(root if root else QDir.rootPath())
    model.setFilter(QDir.Dirs|QDir.Drives|QDir.NoDotAndDotDot|QDir.AllDirs)

    # Create the view in the splitter.
    browserw = QWidget(splitter)
    vl = QVBoxLayout(browserw)
    hl = QHBoxLayout()

    treev = QTreeView(browserw)
    treev.setModel(model)
    treev.setRootIndex(model.index(root if root else QDir.rootPath()))

    # Hide other columns
    treev.setColumnHidden(1, True)
    treev.setColumnHidden(2, True)
    treev.setColumnHidden(3, True)

    btnsetroot = QPushButton(browserw)
    btnsetroot.setText("Set root")
    btnsetroot.clicked.connect(setroot)

    btnforgetroot = QPushButton(browserw)
    btnforgetroot.setText("Forget root")
    btnforgetroot.clicked.connect(forgetroot)

    hl.addWidget(btnsetroot)
    hl.addWidget(btnforgetroot)

    vl.addWidget(treev)
    vl.addLayout(hl)

    # Create widget to host the scanner and add it to the splitter
    scannerw = QWidget(splitter)
    vl = QVBoxLayout(scannerw)
    hl = QHBoxLayout()

    listw = QListWidget(scannerw)

    btnscan = QPushButton(scannerw)
    btnscan.setText("Scan")
    btnscan.clicked.connect(scan)

    btnclear = QPushButton(scannerw)
    btnclear.setText("Clear")
    btnclear.clicked.connect(clear)

    hl.addWidget(btnclear)
    hl.addWidget(btnscan)

    vl.addLayout(hl)
    vl.addWidget(listw)

    # Create widget to host the information and add it to the splitter
    infow = QTabWidget(splitter)

    plotterw = Plotter()
    analyserw = Analyser(plotterw)

    infow.addTab(analyserw, "Analyser")
    infow.addTab(plotterw, "Plotter")

    listw.itemClicked.connect(analyserw.loadinfo)

    # Show the splitter.
    splitter.setStretchFactor(1, 3)        # make folder tree view small
    splitter.setStretchFactor(2, 3)        # make folder tree view small
    splitter.show()

    # Maximize the splitter.
    splitter.setWindowState(Qt.WindowMaximized)

    # Start the main loop.
    ret = app.exec_()

    # Writing our configuration file to 'example.cfg'
    with open('mdb.cfg', 'wb') as configfile:
        config.write(configfile)

    sys.exit(ret)
