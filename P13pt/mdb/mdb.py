#!/usr/bin/python
import sys

from PyQt5.QtGui import QPen, QColor, QFont, QBrush, QPalette

from PyQt5.QtWidgets import (QApplication, QFileSystemModel, QSplitter, QTreeView, QVBoxLayout, QHBoxLayout,
                             QListWidgetItem, QListWidget, QPushButton, QWidget, QTabWidget,
                             QTextEdit, QAbstractItemDelegate, QStyle)
from PyQt5.QtCore import QDir, Qt, QSize

from plotter import Plotter
from analyser import Analyser
from modifier import Modifier

import os
import ConfigParser
from glob import glob

from mdbinfo import FolderInfo

config = None
root = None

class FileListDelegate(QAbstractItemDelegate):
    def __init__(self):
        super(FileListDelegate, self).__init__()

    def paint(self, painter, option, index):
        r = option.rect
        fontPen = QPen(QColor.fromRgb(0, 0, 0), 1, Qt.SolidLine)
        selectedBrush = QBrush(QApplication.palette().color(QPalette.Highlight))
        selectedFontPen = QPen(QApplication.palette().color(QPalette.HighlightedText))

        # alternating background
        painter.setBrush(Qt.white if (index.row() % 2) else QColor(240, 240, 240))
        painter.drawRect(r)

        if(option.state & QStyle.State_Selected):
            painter.setBrush(selectedBrush)
            painter.drawRect(r)
            fontPen = selectedFontPen

        flag = '!' if index.data(Qt.UserRole+1) else '?'
        filename = index.data(Qt.DisplayRole)+' ('+flag+')'
        #description = index.data(Qt::UserRole + 1).toString();

        painter.setPen(fontPen)
        painter.setFont(QFont(QFont.defaultFamily(QFont()), 10, QFont.Normal))
        # returns bounding rect br
        br = painter.drawText(r.left(), r.top(), r.width(), r.height(), Qt.AlignTop | Qt.AlignLeft | Qt.TextWrapAnywhere, filename)

    def sizeHint(self, option, index):
        return QSize(200, 40);  #  very dumb value


class MainWindow(QSplitter):
    def scan(self, index):
        # empty list view
        self.listw.clear()

        # determine chosen folder from active tree view item
        folder = str(self.model.fileInfo(index).absoluteFilePath())

        # initialise folder info
        self.mdbinfo.load(folder)
        self.descriptionw.setText(self.mdbinfo.description)

        # look for data files
        extensions = ["txt", "csv"]
        files = []
        for e in extensions:
            files.extend(glob(os.path.join(folder, "*." + e)))

        for f in sorted(files):
            item = QListWidgetItem()
            item.setText(os.path.basename(f))
            if f in self.mdbinfo.files:
                item.setData(Qt.UserRole+1, True)
            self.listw.addItem(item)

    def setroot(self):
        i = self.treev.selectedIndexes()[0]
        root = self.model.fileInfo(i).absoluteFilePath()
        self.model.setRootPath(root)
        self.treev.setRootIndex(i)
        config.set('main', 'root', root)

    def forgetroot(self):
        rPath = self.model.myComputer().toString()
        config.remove_option('main', 'root')
        self.model.setRootPath(rPath)
        self.treev.setRootIndex(self.model.index(rPath))

    def initfolderview(self):
        # Set up file system model for tree view
        self.model = QFileSystemModel()
        model = self.model
        rPath = model.myComputer() #.toString()
        model.setRootPath(root if root else rPath)
        model.setFilter(QDir.Dirs | QDir.Drives | QDir.NoDotAndDotDot | QDir.AllDirs)

        # Create the tree view in the splitter.
        browserw = QWidget(self)
        vl = QVBoxLayout(browserw)
        hl = QHBoxLayout()

        self.treev = QTreeView(browserw)
        treev = self.treev
        treev.setModel(model)
        treev.setRootIndex(model.index(root if root else rPath))

        treev.clicked.connect(self.scan)

        # Hide other columns
        treev.setColumnHidden(1, True)
        treev.setColumnHidden(2, True)
        treev.setColumnHidden(3, True)

        btnsetroot = QPushButton(browserw)
        btnsetroot.setText("Set root")
        btnsetroot.clicked.connect(self.setroot)

        btnforgetroot = QPushButton(browserw)
        btnforgetroot.setText("Forget root")
        btnforgetroot.clicked.connect(self.forgetroot)

        hl.addWidget(btnsetroot)
        hl.addWidget(btnforgetroot)

        vl.addWidget(treev)
        vl.addLayout(hl)

    def savedescription(self):
        self.mdbinfo.description = self.descriptionw.toPlainText()
        self.mdbinfo.save()

    def initfilesview(self):
        # Create widget to host the scanner and add it to the splitter
        scannerw = QWidget(self)
        vl = QVBoxLayout(scannerw)

        self.descriptionw = QTextEdit(scannerw)
        btnsave = QPushButton("Save description")
        self.listw = QListWidget(scannerw)

        self.listw.setItemDelegate(FileListDelegate())

        btnsave.clicked.connect(self.savedescription)

        vl.addWidget(self.descriptionw)
        vl.addWidget(btnsave)
        vl.addWidget(self.listw)

        vl.setStretchFactor(self.listw, 10)

    def initinfoview(self):
        # Create widget to host the information and add it to the splitter
        infow = QTabWidget(self)

        self.plotterw = Plotter()
        self.modifierw = Modifier(self)
        self.analyserw = Analyser(self)

        infow.addTab(self.analyserw, "Analyser")
        infow.addTab(self.modifierw, "Modifier")
        infow.addTab(self.plotterw, "Plotter")

        self.listw.currentItemChanged.connect(self.analyserw.loadinfo)
        #self.listw.itemClicked.connect(self.analyserw.loadinfo)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.mdbinfo = FolderInfo()

        self.initfolderview()
        self.initfilesview()
        self.initinfoview()

        # Show the splitter.
        self.setStretchFactor(1, 3)        # make folder tree view small
        self.setStretchFactor(2, 3)        # make folder tree view small
        self.show()

        # Maximize the splitter.
        self.setWindowState(Qt.WindowMaximized)

def main():
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

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    # Writing our configuration file to 'mdb.cfg'
    with open('mdb.cfg', 'wb') as configfile:
        config.write(configfile)

    sys.exit(ret)

if __name__ == '__main__':
    main()