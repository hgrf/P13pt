import sys

import numpy as np

from PyQt4.QtGui import (QApplication, QFileSystemModel,
                         QSplitter, QTreeView, QVBoxLayout,
                         QHBoxLayout, QListWidgetItem,
                         QListWidget, QPushButton, QWidget,
                         QSizePolicy, QMessageBox, QLabel,
                         QTextEdit, QTabWidget, QComboBox)
from PyQt4.QtCore import QDir, Qt, pyqtSlot

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar

import os
import numpy as np
import matplotlib.pyplot as plt
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

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }

def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)

def loadinfo(item):
    filename = str(item.text())

    analyserw.clear()
    with open(filename) as f:
        analyserw.append('<h1>Comments</h1>')
        # search for comments
        comments = '<p>'
        lastcomment = ''
        ignorelines = 0          # number of lines that won't be considered for data import
        while True:
            line = f.readline()
            if line.startswith('#'):
                comments += html_escape(line)+'<br>'
                lastcomment = line
                ignorelines += 1
            else:
                break
        comments += '</p>'
        analyserw.append(comments)

        # now try to find header, if there is none, check last comment line
        analyserw.append('<h1>Header</h1>')
        cols = line.split('\t')         # line is the last non-comment line (s.a.)

        if not is_number(cols[0]):      # check if line does not start with a number
            header = line               # in this case this is the header line...
            dataline1 = f.readline()    # ...and the next one is the 1st data line
            ignorelines += 1
        else:
            dataline1 = line            # otherwise the line we read before is already the first data line...
            header = lastcomment[1:]    # ...and we will see if last comment qualifies as header (strip the hash)

        if len(header.split('\t')) == len(dataline1.split('\t')):       # see if "field number" is compatible with data
            analyserw.append('<p>{}</p>'.format(html_escape(header)))
            header = header.strip('\r\n').split('\t') # also removes CR and LF characters
        else:
            header = ['Col {}'.format(i) for i in range(len(dataline1))]

    plotterw.setheader(header)

    try:
        data = np.loadtxt(filename, skiprows=ignorelines).T
        plotterw.setdata(data)
    except ValueError:      # if we cannot read numbers
        analyserw.append('<h1>Data not numpy compatible!</h1>')
        plotterw.setdata(None) # TODO: need something more specific here
        return

    analyserw.append('<h1>Constants detected</h1>')
    for i, col in enumerate(data):
        if len(set(col)) == 1 and header:
            analyserw.append('{}={}<br>'.format(header[i], col[0]))

    # The algorithm below detects sweeps on "imposed" variables (e.g. voltage
    # set points) that are swept with a constant step. If the sweep step is
    # varied during the sweep, it won't work.
    analyserw.append('<h1>Sweeps detected</h1>')
    for i, col in enumerate(data):
        # get sorted unique abs diff values
        s = np.unique(np.abs(np.diff(col)))
        # remove zero
        s = s[s != 0]
        # check if there is a large jump at the end (happens for nested sweeps)
        if len(s) > 1 and (s[-1]-s[-2])/s[-2] > 1e-12:
            s = np.delete(s, -1)
        # check if we have a sweep
        if len(s) and np.mean(np.diff(s))/s[0] < 1e-12:
            analyserw.append('{}={}:{}:{}<br>'.format(header[i], np.min(col), s[0], np.max(col)))

    analyserw.append('<h1>Data</h1>')
    table = '<table border="1" width="100%"><tr>'
    if header:
        for col in header:
            table += '<td>'+col+'</td>'
        table += '</tr>'

    # max 20 data points
    for i in range(min(20, len(data[0]))):
        table += '<tr>'
        for col in data[:,i]:
            table += '<td>'+str(col)+'</td>'
        table += '</tr>'

    table += '</table>'

    analyserw.append(table)
    if len(data[0]) > 20:
        analyserw.append('<b>... more data available ...</b>')

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

class PlotterW(QWidget):
    def __init__(self, parent=None):
        super(PlotterW, self).__init__(parent)

        self.xvar = QListWidget(self)
        self.yvar = QListWidget(self)
        self.selectvar = QComboBox(self)
        self.selectval = QListWidget(self)

        self.selectval.setSelectionMode(QListWidget.MultiSelection)

        self.xvar.itemClicked.connect(self.plot)
        self.yvar.itemClicked.connect(self.plot)
        self.selectvar.activated[int].connect(self.selectedvar)
        self.selectval.itemSelectionChanged.connect(self.reducedataset)

        selectlayout = QVBoxLayout()
        selectlayout.addWidget(self.selectvar)
        selectlayout.addWidget(self.selectval)

        configpanelayout = QHBoxLayout()
        configpanelayout.addWidget(self.xvar)
        configpanelayout.addWidget(self.yvar)
        configpanelayout.addLayout(selectlayout)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # set the layout
        layout = QVBoxLayout()
        layout.addLayout(configpanelayout)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def selectedvar(self, i):
        self.selectval.clear()
        vals = np.unique(self.data[i])
        for v in vals:
            self.selectval.addItem(str(v))

    def reducedataset(self):
        if not len(self.selectval.selectedItems()):
            self.reddata = self.data
            self.plot()
            return

        selection = [False]*len(self.data[0])
        for it in self.selectval.selectedItems():
            selection = np.logical_or(selection, self.data[self.selectvar.currentIndex()]==float(it.text()))
        self.reddata = self.data[:, selection]
        self.plot(key=self.selectvar.currentIndex())

    def setheader(self, header):
        self.header = header
        self.xvar.clear()
        self.yvar.clear()
        self.selectvar.clear()
        for col in header:
            self.xvar.addItem(col)
            self.yvar.addItem(col)
            self.selectvar.addItem(col)

    def setdata(self, data):
        self.data = data
        self.reddata = data

    @pyqtSlot()         # don't accept arguments (otherwise might get some
                        # QListWidget or other stuff passed as key argument if used as slot)
    def plot(self, key=None):
        ix = self.xvar.currentRow()
        iy = self.yvar.currentRow()
        if ix < 0 or iy < 0:
            return

        ax = self.figure.add_subplot(111)
        ax.clear()
        #ax.hold(False)

        if key is None:
            ax.plot(self.reddata[ix], self.reddata[iy], '*-')
        else:
            uniquevals = np.unique(self.reddata[key])
            for v in uniquevals:
                ax.plot(self.reddata[ix, self.reddata[key]==v], self.reddata[iy, self.reddata[key]==v], '*-', label=str(v))
            ax.legend()

        ax.set_xlabel(self.header[ix])
        ax.set_ylabel(self.header[iy])

        self.canvas.draw()

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
    listw.itemClicked.connect(loadinfo)

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

    analyserw = QTextEdit(splitter)
    plotterw = PlotterW()

    infow.addTab(analyserw, "Analyser")
    infow.addTab(plotterw, "Plotter")

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
