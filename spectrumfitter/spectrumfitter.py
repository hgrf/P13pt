#!/usr/bin/python
import sys
import os

from PyQt5.QtCore import (Qt, qInstallMessageHandler, QtInfoMsg, QtCriticalMsg, QtDebugMsg,
                          QtWarningMsg, QtFatalMsg, QSettings, pyqtSlot)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QMessageBox, QMainWindow, QDockWidget, QAction,
                             QFileDialog, QProgressDialog)

from dataloader import DataLoader
from navigator import Navigator
from fitter import Fitter
from plotter import Plotter
from load_fitresults import load_fitresults
from P13pt.params_from_filename import params_from_filename

class MainWindow(QMainWindow):
    session_file = None

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.settings = QSettings("Mercury", "SpectrumFitter")

        # set up data loading area
        self.dock_loader = QDockWidget('Data loading', self)
        self.dock_loader.setObjectName('loader')
        self.loader = DataLoader()
        self.dock_loader.setWidget(self.loader)

        # set up data navigator
        self.dock_navigator = QDockWidget('Data navigation', self)
        self.dock_navigator.setObjectName('navigator')
        self.navigator = Navigator()
        self.dock_navigator.setWidget(self.navigator)

        # set up plotter
        self.plotter = Plotter()
        self.setCentralWidget(self.plotter)

        # set up fitter
        self.dock_fitter = QDockWidget('Fitting', self)
        self.dock_fitter.setObjectName('fitter')
        self.fitter = Fitter()
        self.dock_fitter.setWidget(self.fitter)

        # set up the dock positions
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_loader)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_navigator)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_fitter)

        # set up menus
        fileMenu = self.menuBar().addMenu('File')
        self.act_new_session = QAction('New session', self)
        self.act_load_session = QAction('Load session', self)
        self.act_save_session = QAction('Save session', self)
        self.act_save_session_as = QAction('Save session as...', self)
        for a in [self.act_new_session, self.act_load_session, self.act_save_session, self.act_save_session_as]:
            fileMenu.addAction(a)
        self.recent_menu = fileMenu.addMenu('Recent sessions')
        self.update_recent_list()
        fileMenu.addSeparator()
        self.act_save_image = QAction('Save spectrum as image', self)
        self.act_save_allimages = QAction('Save all spectra as images', self)
        for a in [self.act_save_image, self.act_save_allimages]:
            fileMenu.addAction(a)

        for a in [self.act_save_session, self.act_save_session_as, self.act_save_image, self.act_save_allimages]:
            a.setEnabled(False)

        viewMenu = self.menuBar().addMenu('View')
        for w in [self.dock_loader, self.dock_navigator, self.dock_fitter]:
            viewMenu.addAction(w.toggleViewAction())
        self.act_restore_default_view = QAction('Restore default')
        viewMenu.addAction(self.act_restore_default_view)

        # make connections
        self.loader.dataset_changed.connect(self.dataset_changed)
        self.loader.new_file_in_dataset.connect(self.navigator.new_file_in_dataset)
        self.loader.deembedding_changed.connect(self.deembedding_changed)
        self.navigator.selection_changed.connect(self.selection_changed)
        self.fitter.fit_changed.connect(self.fit_changed)
        self.fitter.fitted_param_changed.connect(self.plotter.fitted_param_changed)
        self.fitter.btn_fitall.clicked.connect(self.fit_all)
        self.act_new_session.triggered.connect(self.new_session)
        self.act_load_session.triggered.connect(self.load_session)
        self.act_save_session.triggered.connect(self.save_session)
        self.act_save_session_as.triggered.connect(self.save_session_as)
        self.act_save_image.triggered.connect(self.save_image)
        self.act_save_allimages.triggered.connect(self.save_all_images)
        self.act_restore_default_view.triggered.connect(lambda: self.restoreState(self.default_state))

        # set up fitted parameter (this has to be done after making connections, so that fitter and plotter sync)
        self.fitter.fitted_param = '-Y12'       # default value

        # set window title and show
        self.setWindowTitle('Spectrum Fitter - New session')
        self.show()

<<<<<<< HEAD
        self.default_state = self.saveState()

        # restore layout from config (this has to be done AFTER self.show())
        if self.settings.contains('geometry'):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains('windowState'):
            self.restoreState(self.settings.value("windowState"))

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        super(MainWindow, self).closeEvent(event)

    def dataset_changed(self):
        self.fitter.empty_cache()
        self.navigator.update_file_list(self.loader.dut_files)
        for a in [self.act_save_session, self.act_save_session_as, self.act_save_image, self.act_save_allimages]:
            a.setEnabled(True)

    def deembedding_changed(self):
        # TODO: reduce redundancy with selection_changed()
        i = self.navigator.file_list.currentRow()
        spectrum = self.loader.get_spectrum(i)
        if spectrum is not None:
            #TODO: show parameters on plot
            self.plotter.plot(spectrum, {})
        else:
            self.plotter.clear()
        self.fitter.update_network(spectrum, self.loader.dut_files[i])
=======
        # make the window big
        self.resize(1200,800)

        # Set window title
        self.setWindowTitle("Spectrum Fitter")

    def browse(self, x):
        # open browser and update the text field
        folder = QFileDialog.getExistingDirectory(self, 'Choose dataset')
        if folder:
            self.__dict__['txt_'+str(x)].setText(folder)

    def load(self, reinitialise=True):
        self.clear_ax()
        if reinitialise:
            self.current_index = 0
        self.model_params = {}
        self.duts = {}
        self.dut_folder = str(self.txt_dut.text())
        self.dut_files = [os.path.basename(x) for x in sorted(glob(os.path.join(self.dut_folder, '*.txt')))]
        self.dut_files += [os.path.basename(x) for x in sorted(glob(os.path.join(self.dut_folder, '*.s2p')))]

        if len(self.dut_files) < 1:
            QMessageBox.warning(self, 'Warning', 'Please select a valid DUT folder')
            self.dut_folder = ''
            return

        dummy_files = glob(os.path.join(str(self.txt_dummy.text()), '*.txt'))
        dummy_files += glob(os.path.join(str(self.txt_dummy.text()), '*.s2p'))
        if len(dummy_files) != 1:
            self.txt_dummy.setText('Please select a valid dummy folder')
            self.dummy_file = ''
            self.dummy = None
            self.btn_toggledummy.setEnabled(False)
            self.btn_plotdummy.setEnabled(False)
        else:
            self.dummy_file, = dummy_files
            try:
                self.dummy = Network(self.dummy_file)
            except Exception as e:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.dummy_file + ' is not a valid RF spectrum file.')
                return
            self.btn_toggledummy.setEnabled(True)
            self.btn_plotdummy.setEnabled(True)

        thru_files = glob(os.path.join(str(self.txt_thru.text()), '*.txt'))
        thru_files += glob(os.path.join(str(self.txt_thru.text()), '*.s2p'))
        if len(thru_files) != 1:
            self.txt_thru.setText('Please select a valid thru folder')
            self.thru_file = ''
            self.thru = None
            self.btn_togglethru.setEnabled(False)
            self.btn_plotthru.setEnabled(False)
        else:
            self.thru_file, = thru_files
            try:
                self.thru = Network(self.thru_file)
            except Exception as e:
                QMessageBox.warning(self, 'Warning',
                                    'File: ' + self.thru_file + ' is not a valid RF spectrum file.')
                return
            if self.dummy and self.thru_toggle_status:
                if self.dummy.number_of_ports == self.thru.number_of_ports and np.max(np.abs(self.dummy.f-self.thru.f))<1e-3: # check for mHz deviation, since sometimes the frequency value saved is not 100% equal when importing from different file formats...
                    self.dummy = self.dummy.deembed_thru(self.thru)
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed deembed thru from dummy.')
                    return
            self.btn_togglethru.setEnabled(True)
            self.btn_plotthru.setEnabled(True)

        config.set('main', 'dut', self.txt_dut.text() if self.dut_folder else None)
        config.set('main', 'thru', self.txt_thru.text() if self.thru_file else None)
        config.set('main', 'dummy', self.txt_dummy.text() if self.dummy_file else None)
        config.set('main', 'ra', self.txt_ra.text())
        self.load_spectrum(reinitialise)

    def load_clicked(self):     # workaround: if we connect button signal directly to load, we get reinitialise=False
        self.load(True)

    def clear_ax(self):
        for ax in [self.ax]+self.ax_y_list+self.ax_s_list:
            for artist in ax.lines+ax.collections:
                artist.remove()
            ax.set_prop_cycle(None)
            ax.set_title('')
        for canvas in [self.canvas, self.canvas_y, self.canvas_s]:
            canvas.draw()

    def load_spectrum(self, first_load=False):
        # clean up the axis
        self.clear_ax()
        self.line_r = None
        self.line_i = None

        params = params_from_filename(os.path.join(self.dut_folder, self.dut_files[self.current_index]))
        if not first_load and self.dut_files[self.current_index] in self.duts:
            self.dut = self.duts[self.dut_files[self.current_index]]
        else:
            # try to load spectrum and check its compatibility
            try:
                self.dut = Network(os.path.join(self.dut_folder, self.dut_files[self.current_index]))
            except Exception as e:
                QMessageBox.warning(self, 'Warning', 'File: '+self.dut_files[self.current_index]+' is not a valid RF spectrum file.')
                return
            if self.thru and self.thru_toggle_status:
                if self.thru.number_of_ports == self.dut.number_of_ports and np.max(np.abs(self.dut.f-self.thru.f))<1e-3:
                    self.dut = self.dut.deembed_thru(self.thru)
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed thru.')
            if self.dummy and self.dummy_toggle_status:
                if self.dummy.number_of_ports == self.dut.number_of_ports and np.max(np.abs(self.dummy.f-self.thru.f))<1e-3:
                    self.dut.y -= self.dummy.y
                else:
                    QMessageBox.warning(self, 'Warning', 'Could not deembed dummy.')
            try:
                ra = float(self.txt_ra.text())
            except:
                QMessageBox.warning(self, 'Warning', 'Invalid value for Ra.')
                ra = 0.
            if not ra == 0:
                y = np.zeros(self.dut.y.shape, dtype=complex)
                y[:,0,0] = 1./(1./self.dut.y[:,0,0]-ra)
                y[:,0,1] = 1./(1./self.dut.y[:,0,1]+ra)
                y[:,1,0] = 1./(1./self.dut.y[:,1,0]+ra)
                y[:,1,1] = 1./(1./self.dut.y[:,1,1]-ra)
                self.dut.y = y
            self.duts[self.dut_files[self.current_index]] = copy(self.dut)

        # plot single Y parameter
        pm = -1. if self.fitted_param[0] == '-' else +1
        i = int(self.fitted_param[2])-1
        j = int(self.fitted_param[3])-1
        self.y = pm*self.dut.y[:,i,j]
        self.ax.plot(self.dut.f/1e9, self.y.real*1e3, label='Re')
        self.ax.plot(self.dut.f/1e9, self.y.imag*1e3, label='Im')
        self.ax.legend()

        # plot all Y parameters
        for i,ax in enumerate(self.ax_y_list):
            y = self.dut.y[:,i//2,i%2]
            ax.plot(self.dut.f/1e9, y.real*1e3, label='Re')
            ax.plot(self.dut.f/1e9, y.imag*1e3, label='Im')
            if not i:
                ax.legend()

        # plot all S parameters
        for i,ax in enumerate(self.ax_s_list):
            s = self.dut.s[:,i//2,i%2]
            ax.plot(self.dut.f/1e9, s.real, label='Re')
            ax.plot(self.dut.f/1e9, s.imag, label='Im')
            if not i:
                ax.legend()

        # update titles
        title = ', '.join([key + '=' + str(params[key]) for key in params])
        self.ax.set_title(title)
        for fig in [self.figure_y, self.figure_s]:
            fig.suptitle(title)
            fig.subplots_adjust(top=0.9)

        if first_load:
            for ax in [self.ax]+self.ax_y_list+self.ax_s_list:
                ax.set_xlim([min(self.dut.f/1e9), max(self.dut.f/1e9)])
            for toolbar in [self.toolbar, self.toolbar_y, self.toolbar_s]:
                toolbar.update()
                toolbar.push_current()

        # draw model if available
        if self.model:
            if self.dut_files[self.current_index] in self.model_params:
                self.update_values(self.model_params[self.dut_files[self.current_index]])
            else:
                self.reset_values()

        # update canvas
        for canvas in [self.canvas, self.canvas_y, self.canvas_s]:
            canvas.draw()

    def toggledummy(self):
        if self.dummy_toggle_status:
            self.dummy_toggle_status = False
            self.btn_toggledummy.setIcon(self.toggleoff_icon)
        else:
            self.dummy_toggle_status = True
            self.btn_toggledummy.setIcon(self.toggleon_icon)
        self.load(reinitialise=False)

    def togglethru(self):
        if self.thru_toggle_status:
            self.thru_toggle_status = False
            self.btn_togglethru.setIcon(self.toggleoff_icon)
        else:
            self.thru_toggle_status = True
            self.btn_togglethru.setIcon(self.toggleon_icon)
        self.load(reinitialise=False)

    def plotdummy(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Dummy'+(' (deembedded thru)' if self.thru and self.thru_toggle_status else ''))
        dialog.setModal(True)
        figure = plt.figure()
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, dialog)
        l = QVBoxLayout()
        for w in [toolbar, canvas]:
            l.addWidget(w)
        dialog.setLayout(l)
        self.dummy.plot_mat('y', ylim=1e-3, fig=figure)
        figure.suptitle(self.dummy.name)
        figure.subplots_adjust(top=0.9)
        canvas.draw()
        dialog.show()

    def plotthru(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('Thru')
        dialog.setModal(True)
        figure = plt.figure()
        ax = figure.add_subplot(111)
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, dialog)
        l = QVBoxLayout()
        for w in [toolbar, canvas]:
            l.addWidget(w)
        dialog.setLayout(l)
        name = self.thru.name
        self.thru.name = None       # workaround to avoid cluttering the legend
        self.thru.plot_s_deg(ax=ax)
        ax.set_title(name)
        self.thru.name = name
        canvas.draw()
        dialog.show()

    def parameter_modified(self):
        self.fitted_param = self.cmb_plusminus.currentText()+self.cmb_parameter.currentText()
        self.ax.set_ylabel(self.fitted_param+' [mS]')
        self.canvas.draw()
        if self.dut_files:
            self.load_spectrum()

    def prev_spectrum(self):
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.dut_files)-1
        self.load_spectrum()

    def next_spectrum(self):
        self.current_index += 1
        if self.current_index >= len(self.dut_files):
            self.current_index = 0
        self.load_spectrum()

    def plot_fit(self):
        if not self.dut_files:
            return
>>>>>>> master

    def selection_changed(self, i):
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # TODO: the argument here should be a filename, not the index, that way we could also put it in the
        # window title easily
        spectrum = self.loader.get_spectrum(i)
        if spectrum is not None:
            self.plotter.plot(spectrum, params_from_filename(self.loader.dut_files[i]))
        else:
            self.plotter.clear()
        self.fitter.update_network(spectrum, self.loader.dut_files[i])

        QApplication.restoreOverrideCursor()

    def fit_changed(self):
        self.plotter.plot_fit(self.fitter.model)

    def new_session(self):
        self.session_file = None
        self.setWindowTitle('Spectrum Fitter - New session')
        self.loader.clear()
        self.navigator.clear()
        self.fitter.clear()
        self.plotter.clear()

    @pyqtSlot()
    def save_session_as(self, res_file=None):
        if not res_file:
            res_file, filter = QFileDialog.getSaveFileName(self, 'Fit results file', filter='*.txt')
        if not res_file:
            return
        res_folder = os.path.dirname(res_file)

        with open(res_file, 'w') as f:
             # write the header
             f.write('# fitting results generated by P13pt spectrum fitter\n')
             if len(self.loader.dut_files) == 1:
                 f.write('# dut: ' +
                         os.path.join(
                             os.path.relpath(self.loader.dut_folder, res_folder),
                             self.loader.dut_files[0]
                         ).replace('\\', '/') + '\n')
             else:
                 f.write('# dut: ' + os.path.relpath(self.loader.dut_folder, res_folder).replace('\\', '/') + '\n')
             if self.loader.thru and self.loader.thru_toggle_status:
                 f.write('# thru: ' + os.path.relpath(self.loader.thru_file, res_folder).replace('\\', '/') + '\n')
             if self.loader.dummy and self.loader.dummy_toggle_status:
                 f.write('# dummy: ' + os.path.relpath(self.loader.dummy_file, res_folder).replace('\\', '/') + '\n')
             f.write('# fitted_param: ' + self.plotter.fitted_param + '\n')
             try:
                 ra = float(self.loader.txt_ra.text())
             except:
                 ra = 0.
             if not ra == 0:
                 f.write('# ra: ' + str(ra) + '\n')
             if self.fitter.model:
                 f.write('# model: ' + os.path.basename(self.fitter.model_file).replace('\\', '/') + '\n')
                 # determine columns
                 f.write('# filename\t')
                 for p in params_from_filename(self.loader.dut_files[0]):
                      f.write(p + '\t')
                 f.write('\t'.join([p for p in self.fitter.model.params]))
                 f.write('\n')

                 # write data
                 filelist = sorted([filename for filename in self.fitter.model_params])
                 for filename in filelist:
                     f.write(filename + '\t')
                     # TODO: what if some filenames do not contain all parameters? should catch exceptions
                     for p in params_from_filename(self.loader.dut_files[0]):
                         f.write(str(params_from_filename(filename)[p]) + '\t')
                     f.write('\t'.join([str(self.fitter.model_params[filename][p]) for p in self.fitter.model.params]))
                     f.write('\n')

        self.update_recent_list(res_file)
        self.setWindowTitle('Spectrum Fitter - '+res_file)
        self.session_file = res_file

    def save_session(self):
        self.save_session_as(self.session_file)

    @pyqtSlot()
    def load_session(self, res_file=None):
        if not res_file:
            res_file, filter = QFileDialog.getOpenFileName(self, 'Fit results file', filter='*.txt')
        if not res_file:
            return
        res_folder = os.path.dirname(res_file)

        # read the data
        try:
            data, dut, thru, dummy, model, ra, fitted_param = load_fitresults(res_file, readfilenameparams=False, extrainfo=True)
        except IOError as e:
            QMessageBox.warning(self, 'Error', 'Could not load data: '+str(e))
            return
        #TODO: put this in correct place (should at least be able to load spectra even if there are no fitresults)
        # # check at least the filename field is present in the data
        # if not data or 'filename' not in data:
        #     QMessageBox.warning(self, 'Error', 'Could not load data')
        #     return
        #
        # load the dataset provided in the results file
        # TODO: Loader should have a function for this
        self.loader.txt_ra.setText(str(ra) if ra else '0')

        # using os.path.realpath to get rid of relative path remainders ("..")
        self.loader.load_dataset(dut=os.path.realpath(os.path.join(res_folder, dut)) if dut else None,
                                 thru=os.path.realpath(os.path.join(res_folder, thru)) if thru else None,
                                 dummy=os.path.realpath(os.path.join(res_folder, dummy)) if dummy else None)
        if fitted_param:
            self.fitter.fitted_param = fitted_param

        # try to load the model provided in the results file
        #TODO: Fitter should have a function for this
        if model:
            self.fitter.txt_model.setText(os.path.join(os.path.dirname(__file__), 'models', model))
            if self.fitter.load_model():
                 # get a list of parameter names
                 params = [p for p in data]
                 unusable = []
                 # now check float conversion compatibility of the data columns, removing the ones that we cannot use
                 for p in params:
                     try:
                         data[p] = [float(x) for x in data[p]]
                     except ValueError:
                         unusable.append(p)
                 for p in unusable:
                     params.remove(p)

                 for i, f in enumerate(data['filename']):
                     values = [float(data[p][i]) for p in params]
                     self.fitter.model_params[f] = dict(zip(params, values))
            self.fitter.update_network(self.loader.get_spectrum(0), self.loader.dut_files[0])

        self.update_recent_list(res_file)
        self.setWindowTitle('Spectrum Fitter - '+res_file)
        self.session_file = res_file

    #TODO: this is not really in the right place
    @pyqtSlot()
    def fit_all(self):
         totalnum = len(self.loader.dut_files)

         progressdialog = QProgressDialog('Fitting all spectra...', 'Cancel', 0, totalnum-1, self)
         progressdialog.setWindowTitle('Progress')
         progressdialog.setModal(True)
         progressdialog.setAutoClose(True)
         progressdialog.show()

         for i in range(totalnum):
             QApplication.processEvents()
             if progressdialog.wasCanceled():
                 break
             self.navigator.file_list.setCurrentRow(i)
             self.fitter.fit_model()
             progressdialog.setValue(i)

    def save_image(self):
        # TODO: the menu action should just be deactivated when no data is loaded
        if not self.loader.dut_files:
            return
        basename, ext = os.path.splitext(self.loader.dut_files[self.navigator.file_list.currentRow()])
        filename, filter = QFileDialog.getSaveFileName(self, 'Choose file',
                                                       os.path.join(self.loader.dut_folder, basename+'.png'),
                                                       filter='*.png;;*.jpg;;*.eps')
        if filename:
            self.plotter.save_fig(filename)

    def save_all_images(self):
        foldername = QFileDialog.getExistingDirectory(self, 'Choose folder',
                                                      self.loader.dut_folder)

        totalnum = len(self.loader.dut_files)

        progressdialog = QProgressDialog('Saving all images...', 'Cancel', 0, totalnum - 1, self)
        progressdialog.setWindowTitle('Progress')
        progressdialog.setModal(True)
        progressdialog.setAutoClose(True)
        progressdialog.show()

        for i in range(totalnum):
            QApplication.processEvents()
            if progressdialog.wasCanceled():
                break
            self.navigator.file_list.setCurrentRow(i)
            basename, ext = os.path.splitext(self.loader.dut_files[self.navigator.file_list.currentRow()])
            self.plotter.save_fig(os.path.join(foldername, basename+'.png'))
            progressdialog.setValue(i)

    def load_recent(self):
        action = self.sender()
        self.load_session(action.text())

    def update_recent_list(self, filename=None):
        recentlist = list(self.settings.value('recentSessions')) if self.settings.contains('recentSessions') \
            else []
        if filename:
            if filename in recentlist:
                recentlist.remove(filename)
            recentlist.insert(0, filename)
            recentlist = recentlist[0:5]
            self.settings.setValue('recentSessions', recentlist)
        self.recent_menu.clear()
        for r in recentlist:
            a = QAction(r, self)
            self.recent_menu.addAction(a)
            a.triggered.connect(self.load_recent)


def msghandler(type, context, message):
    if type == QtInfoMsg:
        QMessageBox.information(None, 'Info', message)
    elif type == QtDebugMsg:
        QMessageBox.information(None, 'Debug', message)
    elif type == QtCriticalMsg:
        QMessageBox.critical(None, 'Critical', message)
    elif type == QtWarningMsg:
        QMessageBox.warning(None, 'Warning', message)
    elif type == QtFatalMsg:
        QMessageBox.critical(None, 'Fatal error', message)

if __name__ == '__main__':
    qInstallMessageHandler(msghandler)

    # CD into directory where this script is saved
    d = os.path.dirname(__file__)
    if d != '': os.chdir(d)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('audacity.png'))

    mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)
