from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from PyQt4.QtGui import (QWidget, QListWidget, QVBoxLayout,
                         QHBoxLayout)

from PyQt4.QtCore import pyqtSlot

import numpy as np

class Plotter(QWidget):
    def __init__(self, parent=None):
        super(Plotter, self).__init__(parent)

        self.header = []
        self.data = []

        self.xvar = QListWidget(self)
        self.yvar = QListWidget(self)

        self.xvar.itemClicked.connect(self.plot)
        self.yvar.itemClicked.connect(self.plot)

        configpanelayout = QHBoxLayout()
        configpanelayout.addWidget(self.xvar)
        configpanelayout.addWidget(self.yvar)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # set the layout
        layout = QVBoxLayout()
        layout.addLayout(configpanelayout)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.setStretch(0, 1)
        layout.setStretch(2, 2)
        self.setLayout(layout)

    @pyqtSlot()
    def plot(self):
        ix = self.xvar.currentRow()
        iy = self.yvar.currentRow()
        if ix < 0 or iy < 0:
            return

        ax = self.figure.add_subplot(111)
        ax.clear()
        #ax.hold(False)

        ax.plot(np.asarray(self.data).T[ix], np.asarray(self.data).T[iy], '*-')

        ax.set_xlabel(self.header[ix])
        ax.set_ylabel(self.header[iy])

        self.canvas.draw()

    @pyqtSlot(list)
    def set_header(self, header):
        self.header = header
        self.xvar.clear()
        self.yvar.clear()
        ax = self.figure.add_subplot(111)
        ax.clear()
        self.canvas.draw()
        for col in header:
            self.xvar.addItem(col)
            self.yvar.addItem(col)

    @pyqtSlot(list)
    def new_data_handler(self, row):
        self.data.append(row)
        self.plot()
