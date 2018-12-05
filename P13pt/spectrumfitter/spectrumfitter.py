#!/usr/bin/python
import sys
import os
import shutil
from glob import glob

from PyQt5.QtCore import (Qt, qInstallMessageHandler, QtInfoMsg, QtCriticalMsg, QtDebugMsg,
                          QtWarningMsg, QtFatalMsg, QSettings, pyqtSlot, QStandardPaths, QUrl)
from PyQt5.QtGui import QIcon, QDesktopServices
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

        viewMenu = self.menuBar().addMenu('View')
        for w in [self.dock_loader, self.dock_navigator, self.dock_fitter]:
            viewMenu.addAction(w.toggleViewAction())
        self.act_restore_default_view = QAction('Restore default', self)
        viewMenu.addAction(self.act_restore_default_view)

        toolsMenu = self.menuBar().addMenu('Tools')
        self.act_install_builtin_models = QAction('Install built-in models', self)
        toolsMenu.addAction(self.act_install_builtin_models)
        self.act_open_model_folder = QAction('Open model folder', self)
        toolsMenu.addAction(self.act_open_model_folder)

        # make connections
        self.loader.dataset_changed.connect(self.dataset_changed)
        self.loader.new_file_in_dataset.connect(self.navigator.new_file_in_dataset)
        self.loader.deembedding_changed.connect(self.deembedding_changed)
        self.navigator.selection_changed.connect(self.selection_changed)
        self.fitter.fit_changed.connect(lambda: self.plotter.plot_fit(self.fitter.model))
        self.fitter.fitted_param_changed.connect(self.plotter.fitted_param_changed)
        self.fitter.btn_fitall.clicked.connect(self.fit_all)
        self.act_new_session.triggered.connect(self.new_session)
        self.act_load_session.triggered.connect(self.load_session)
        self.act_save_session.triggered.connect(self.save_session)
        self.act_save_session_as.triggered.connect(self.save_session_as)
        self.act_save_image.triggered.connect(self.save_image)
        self.act_save_allimages.triggered.connect(self.save_all_images)
        self.act_restore_default_view.triggered.connect(lambda: self.restoreState(self.default_state))
        self.act_install_builtin_models.triggered.connect(self.install_builtin_models)
        self.act_open_model_folder.triggered.connect(self.open_model_folder)

        # set up fitted parameter (this has to be done after making connections, so that fitter and plotter sync)
        self.fitter.fitted_param = '-Y12'       # default value

        # create new session
        self.new_session()

        # show window
        self.show()

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

    def selection_changed(self, i):
        if i < 0:       # when file_list is cleared:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # TODO: the argument here should be a filename, not the index
        spectrum = self.loader.get_spectrum(i)
        if spectrum is not None:
            self.plotter.plot(spectrum, params_from_filename(self.loader.dut_files[i]))
        else:
            self.plotter.clear()
        self.fitter.update_network(spectrum, self.loader.dut_files[i])

        QApplication.restoreOverrideCursor()

    def new_session(self):
        self.session_file = None
        self.setWindowTitle('Spectrum Fitter - New session')
        self.fitter.unload_model()
        self.loader.clear()
        self.navigator.clear()
        self.plotter.clear()
        for a in [self.act_save_session, self.act_save_session_as, self.act_save_image, self.act_save_allimages]:
            a.setEnabled(False)

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
                 f.write('# model_func: ' + self.fitter.cmb_modelfunc.currentText() + '\n')
                 # TODO: this all could clearly be done in a more elegant way
                 if self.fitter.cmb_fitmethod.currentText() != 'No fit methods found':
                     f.write('# fit_method: ' + self.fitter.cmb_fitmethod.currentText() + '\n')
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

        self.new_session()

        # read the data
        try:
            data, dut, thru, dummy, ra, fitter_info = load_fitresults(res_file, readfilenameparams=False, extrainfo=True)
        except IOError as e:
            QMessageBox.warning(self, 'Error', 'Could not load data: '+str(e))
            return

        # using os.path.realpath to get rid of relative path remainders ("..")
        self.loader.load_dataset(dut=os.path.realpath(os.path.join(res_folder, dut)) if dut else None,
                                 thru=os.path.realpath(os.path.join(res_folder, thru)) if thru else None,
                                 dummy=os.path.realpath(os.path.join(res_folder, dummy)) if dummy else None,
                                 ra=ra if ra else None)

        # if a fitted_param was provided in the session file, set it up
        if 'fitted_param' in fitter_info:
            self.fitter.fitted_param = fitter_info['fitted_param']

        # if a model was provided in the session file, load this model and the provided data
        if 'model' in fitter_info:
            self.fitter.load_model(filename=fitter_info['model'],
                                   info=fitter_info,
                                   data=data if data else None)

        # update the fitter with the first spectrum in the list
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

    def install_builtin_models(self):
        builtin_folder = os.path.join(os.path.dirname(__file__), 'models')

        for filename in sorted(glob(os.path.join(builtin_folder, '*.py'))):
            # check if the file already exists in the models folder
            if os.path.exists(os.path.join(self.fitter.models_dir, os.path.basename(filename))):
                answer = QMessageBox.question(self, 'File already exists', 'The file: '+os.path.basename(filename)+
                                              'already exists in your models folder. Would you like to replace it?')
                if answer != QMessageBox.Yes:
                    continue

            # if file does not exist or user does not mind replacing it, let's copy:
            shutil.copyfile(filename, os.path.join(self.fitter.models_dir, os.path.basename(filename)))

    def open_model_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.fitter.models_dir))

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

def main():
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

if __name__ == '__main__':
    main()
