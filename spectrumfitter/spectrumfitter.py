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

        # make connections
        self.loader.dataset_changed.connect(self.dataset_changed)
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

        # set up fitted parameter (this has to be done after making connections, so that fitter and plotter sync)
        self.fitter.fitted_param = '-Y12'       # default value

        # set window title and show
        self.setWindowTitle('Spectrum Fitter - New session')
        self.show()

        # restore layout from config (this has to be done AFTER self.show())
        if self.settings.contains('geometry'):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains('windowState'):
            self.restoreState(self.settings.value("windowState"))

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

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        super(MainWindow, self).closeEvent(event)


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
