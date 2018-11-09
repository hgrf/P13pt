from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QMessageBox)

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

class Plotter(QTabWidget):
    fitted_param = '-Y12'
    network = None
    line_r = None               # matplotlib line for real part of model plot
    line_i = None               # matplotlib line for imag part of model plot

    def __init__(self, parent=None):
        super(QTabWidget, self).__init__(parent)

        # set up different plotting tabs
        self.plotting_yandfit = QWidget()
        self.plotting_s = QWidget()
        self.plotting_y = QWidget()
        self.addTab(self.plotting_yandfit, 'Y and fit')
        self.addTab(self.plotting_y, 'All Y')
        self.addTab(self.plotting_s, 'All S')

        # set up default plotting (Y and fit)
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('f [GHz]')
        self.ax.set_ylabel(self.fitted_param+' [mS]')
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
        self.f = self.network.f[:]
        self.s = self.network.s[:,:,:]
        self.y = self.network.y[:,:,:]

        # plot single Y parameter
        pm = -1. if self.fitted_param[0] == '-' else +1
        i = int(self.fitted_param[2])-1
        j = int(self.fitted_param[3])-1
        self.ax.plot(self.f/1e9, pm*self.y[:,i,j].real*1e3, label='Re')
        self.ax.plot(self.f/1e9, pm*self.y[:,i,j].imag*1e3, label='Im')
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
        if self.network is None:
            return

        # update model lines on plot
        try:
            y = model.admittance(2.*np.pi*self.f, **model.values)
        except Exception as e:
            QMessageBox.critical(self, "Error", "Could not calculate model admittance: " + str(e.message))
            return

        if self.line_r:
            self.line_r.set_ydata(y.real*1e3)
            self.line_i.set_ydata(y.imag*1e3)
        else:
            self.line_r, = self.ax.plot(self.f/1e9, y.real*1e3, '-.')
            self.line_i, = self.ax.plot(self.f/1e9, y.imag*1e3, '-.')
        self.canvas.draw()

        # TODO: put this in a correct place
        # # store new model data
        # self.model_params[self.dut_files[self.current_index]] = copy(self.model.values)

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