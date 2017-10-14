from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
try:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

from PyQt4.QtGui import (QWidget, QListWidget, QVBoxLayout,
                         QHBoxLayout, QPushButton, QGridLayout, QLabel)

from PyQt4.QtCore import pyqtSlot, SIGNAL

import numpy as np

class Plotter(QWidget):
    def __init__(self, parent=None):
        super(Plotter, self).__init__(parent)

        self.header = []
        self.data = []

        self.xvar = QListWidget(self)
        self.yvar = QListWidget(self)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.btn_clear = QPushButton("Clear data", self)

        self.xvar.itemClicked.connect(self.plot)
        self.yvar.itemClicked.connect(self.plot)
        self.connect(self.btn_clear, SIGNAL('clicked()'), self.clear)

        # set the layout
        configpanelayout = QGridLayout()
        configpanelayout.addWidget(QLabel('<b>X variable:</b>'), 0, 0)
        configpanelayout.addWidget(self.xvar, 1, 0)
        configpanelayout.addWidget(QLabel('<b>Y variable:</b>'), 0, 1)
        configpanelayout.addWidget(self.yvar, 1, 1)

        toolbarlayout = QHBoxLayout()
        toolbarlayout.addWidget(self.toolbar)
        toolbarlayout.addWidget(self.btn_clear)

        layout = QVBoxLayout()
        layout.addLayout(configpanelayout)
        layout.addLayout(toolbarlayout)
        layout.addWidget(self.canvas)
        layout.setStretch(0, 1)
        layout.setStretch(2, 2)
        self.setLayout(layout)

    @pyqtSlot()
    def clear(self):
        self.data = []
        self.plot()

    @pyqtSlot()
    def plot(self):
        # clear the plotting window
        ax = self.figure.add_subplot(111)
        ax.clear()

        # check if data to plot is available
        if self.data != []:
            # check if the user chose valid variables to plot
            ix = self.xvar.currentRow()
            iy = self.yvar.currentRow()
            if ix >= 0 and iy >= 0:
                # if yes, plot stuff and update axes lables
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
