from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QMessageBox)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from fitter import parse_fitted_param_str

class Plotter(QTabWidget):
    network = None
    params = None
    line_r = None               # matplotlib line for real part of model plot
    line_i = None               # matplotlib line for imag part of model plot
    fitted_param = None

    def __init__(self, parent=None):
        super(QTabWidget, self).__init__(parent)

        # set up different plotting tabs
        self.plotting_yandfit = QWidget()
        self.plotting_s = QWidget()
        self.plotting_y = QWidget()
        self.addTab(self.plotting_yandfit, 'Fitting')
        self.addTab(self.plotting_y, 'All Y')
        self.addTab(self.plotting_s, 'All S')

        # set up default plotting (Y and fit)
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('f [GHz]')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotting_yandfit)
        l = QVBoxLayout()
        for w in [self.toolbar, self.canvas]:
            l.addWidget(w)
        self.plotting_yandfit.setLayout(l)

        # set up plotting of all Y parameters
        self.figure_y = plt.figure()
        self.ax_y_list = [self.figure_y.add_subplot(221+i) for i in range(4)]
        for i, ax in enumerate(self.ax_y_list):
            ax.set_xlabel(r'$f [GHz]$')
            ax.set_ylabel(r'$Y_{'+['11', '12', '21', '22'][i]+r'} [mS]$')
        self.canvas_y = FigureCanvas(self.figure_y)
        self.toolbar_y = NavigationToolbar(self.canvas_y, self.plotting_y)
        l = QVBoxLayout()
        for w in [self.toolbar_y, self.canvas_y]:
            l.addWidget(w)
        self.plotting_y.setLayout(l)
        self.figure_y.tight_layout()

        # set up plotting of all S parameters
        self.figure_s = plt.figure()
        self.ax_s_list = [self.figure_s.add_subplot(221+i) for i in range(4)]
        for i, ax in enumerate(self.ax_s_list):
            ax.set_xlabel(r'$f [GHz]$')
            ax.set_ylabel(r'$S_{'+['11', '12', '21', '22'][i]+r'}$')
        self.canvas_s = FigureCanvas(self.figure_s)
        self.toolbar_s = NavigationToolbar(self.canvas_s, self.plotting_s)
        l = QVBoxLayout()
        for w in [self.toolbar_s, self.canvas_s]:
            l.addWidget(w)
        self.plotting_s.setLayout(l)
        self.figure_s.tight_layout()

    def plot(self, network, params):
        self.clear()

        self.network = network
        self.params = params
        self.f = self.network.f[:]
        self.s = self.network.s[:,:,:]
        self.y = self.network.y[:,:,:]

        sign, param, i, j = parse_fitted_param_str(self.fitted_param)

        # plot parameter to be fitted
        if param == 'Y':
            self.ax.plot(self.f/1e9, sign*self.y[:,i,j].real*1e3, label='Re')
            self.ax.plot(self.f/1e9, sign*self.y[:,i,j].imag*1e3, label='Im')
        else:
            self.ax.plot(self.f/1e9, sign*self.s[:,i,j].real, label='Re')
            self.ax.plot(self.f/1e9, sign*self.s[:,i,j].imag, label='Im')
        self.ax.legend()

        # plot all Y parameters
        for i,ax in enumerate(self.ax_y_list):
            ax.plot(self.f/1e9, self.y[:,i//2,i%2].real*1e3, label='Re')
            ax.plot(self.f/1e9, self.y[:,i//2,i%2].imag*1e3, label='Im')
            if not i:
                ax.legend()

        # plot all S parameters
        for i,ax in enumerate(self.ax_s_list):
            ax.plot(self.f/1e9, self.s[:,i//2,i%2].real, label='Re')
            ax.plot(self.f/1e9, self.s[:,i//2,i%2].imag, label='Im')
            if not i:
                ax.legend()

        # update titles
        title = ', '.join([key + '=' + str(params[key]) for key in params])
        self.ax.set_title(title)
        for fig in [self.figure_y, self.figure_s]:
            fig.suptitle(title)
            fig.subplots_adjust(top=0.9)

        # TODO: check if this is still important
        # if first_load:
        #     for ax in [self.ax]+self.ax_y_list+self.ax_s_list:
        #         ax.set_xlim([min(self.dut.f/1e9), max(self.dut.f/1e9)])
        #     for toolbar in [self.toolbar, self.toolbar_y, self.toolbar_s]:
        #         toolbar.update()
        #         toolbar.push_current()

        # update canvas
        for canvas in [self.canvas, self.canvas_y, self.canvas_s]:
            canvas.draw()

    def plot_fit(self, model):
        # TODO: this should be in fitter.py
        if self.network is None:
            return

        sign, param, i, j = parse_fitted_param_str(self.fitted_param)
        mult = (1e3 if param == 'Y' else 1)

        # update model lines on plot
        try:
            y = model.func(2.*np.pi*self.f, **model.values)
        except Exception as e:
            QMessageBox.critical(self, "Error", "Could not evaluate model function: " + str(e.message))
            return

        if self.line_r:
            self.line_r.set_ydata(y.real*mult)
            self.line_i.set_ydata(y.imag*mult)
        else:
            self.line_r, = self.ax.plot(self.f/1e9, y.real*mult, '-.')
            self.line_i, = self.ax.plot(self.f/1e9, y.imag*mult, '-.')
        self.canvas.draw()

    def save_fig(self, filename):
        # determine active figure
        # TODO: could probably do this better with a dictionary or by creating subwidgets with figure property
        if self.currentIndex() == 0:     # fitting
            figure = self.figure
        elif self.currentIndex() == 1:   # all Y
            figure = self.figure_y
        elif self.currentIndex() == 2:   # all S
            figure = self.figure_s
        else:
            return
        figure.savefig(filename)

    def clear(self):
        for ax in [self.ax] + self.ax_y_list + self.ax_s_list:
            for artist in ax.lines + ax.collections:
                artist.remove()
            ax.set_prop_cycle(None)
            ax.set_title('')
        for canvas in [self.canvas, self.canvas_y, self.canvas_s]:
            canvas.draw()
        self.line_r = None
        self.line_i = None

    @pyqtSlot(str)
    def fitted_param_changed(self, s):
        self.fitted_param = s
        sign, param, i, j = parse_fitted_param_str(s)
        unit = r'\/\mathrm{[mS]}' if param == 'Y' else ''
        self.ax.set_ylabel('$' +
                           ('+' if sign > 0 else '-') +
                           param +
                           '_{' + str(i+1) + str(j+1) + '}' +
                           unit +
                           '$')
        if self.network:
            self.plot(self.network, self.params)
        self.canvas.draw()
