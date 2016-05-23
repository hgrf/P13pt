from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np

from PyQt4.QtGui import (QWidget, QListWidget, QComboBox, QVBoxLayout,
                         QHBoxLayout)

from PyQt4.QtCore import pyqtSlot

class Plotter(QWidget):
    def __init__(self, parent=None):
        super(Plotter, self).__init__(parent)

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
        self.selectval.clear()
        ax = self.figure.add_subplot(111)
        ax.clear()
        self.canvas.draw()
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
