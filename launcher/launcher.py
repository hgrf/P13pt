# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 11:25:58 2017

@author: meso
"""

import sys
import imp
import os
from PyQt4.QtCore import pyqtSlot, SIGNAL, QThread, Qt
from PyQt4.QtGui import (QWidget, QTextEdit, QFont, QPushButton, QLineEdit, QVBoxLayout,
                         QHBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QApplication,
                         QSplitter)
#from consolewidget import ConsoleWidget
from plotter import Plotter
try:
    from PyQt4.QtCore import QString
except ImportError:
    QString = str

import numpy as np

class ReadOnlyConsole(QTextEdit):
    def __init__(self, parent=None):
        super(ReadOnlyConsole, self).__init__(parent)
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont()
        font.setFamily(u"DejaVu Sans Mono")
        font.setPointSize(10)
        self.setFont(font)

    @pyqtSlot(unicode)
    def write(self, data):
        """
            This uses insertPlainText (maybe in a later version HTML, so that we can change
            the colour of the output) and scrolls down to the bottom of the field. The problem
            with append() is that it puts the inserted text in its own paragraph, which is not
            good if we do not want the linefeed.
        :param data: a unicode string
        :return: nothing
        """
        self.insertPlainText(QString(data))
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


class mainwindow(QSplitter):
    def __init__(self, parent=None):
        super(mainwindow, self).__init__(parent)

        self.m = None

        scriptinterfacewidget = QWidget(self)
        self.txt_acquisition_script = QLineEdit('Path to acquistion script...', scriptinterfacewidget)
        self.btn_browse = QPushButton('Browse', scriptinterfacewidget)
        self.btn_load = QPushButton('Load module', scriptinterfacewidget)
        self.btn_run = QPushButton('Run module', scriptinterfacewidget)
        self.btn_stopmod = QPushButton('Stop module', scriptinterfacewidget)
        self.btn_forcestopmod = QPushButton('Force stop module', scriptinterfacewidget)
        self.tbl_params = QTableWidget(scriptinterfacewidget)
        #self.console = ConsoleWidget(self)
        self.readonlyconsole = ReadOnlyConsole(scriptinterfacewidget)
        l = QVBoxLayout(scriptinterfacewidget)
        for w in [self.txt_acquisition_script, self.btn_browse, self.btn_load, self.btn_run,
                  self.btn_stopmod, self.btn_forcestopmod, self.tbl_params, self.readonlyconsole]:
            l.addWidget(w)
        self.plotter = Plotter(self)
        self.tbl_observables = QTableWidget(self)
        
        self.connect(self.btn_browse, SIGNAL("clicked()"), self.browse_acquisition_script)
        self.connect(self.btn_load, SIGNAL("clicked()"), self.load_module)
        self.connect(self.btn_run, SIGNAL("clicked()"), self.run_module)

        # Set window size.
        self.setWindowState(Qt.WindowMaximized)

        # Set window title
        self.setWindowTitle("Acquisition script launcher")

    @pyqtSlot()
    def browse_acquisition_script(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File', directory='/', filter='*.py')
        self.txt_acquisition_script.setText(filename)

    @pyqtSlot()
    def load_module(self):
        # check if there is a running module
        if isinstance(self.m, QThread) and self.m.isRunning():
            QMessageBox.critical(self, "Error", "Cannot load a new module when the previous one is not done.")
            return

        # check if we are dealing with a valid module
        filename = str(self.txt_acquisition_script.text())
        mod_name, file_ext = os.path.splitext(os.path.split(filename)[-1])
        try:
            mod = imp.load_source(mod_name, filename)
        except IOError as e:
            QMessageBox.critical(self, "Error", "Could not load module: "+str(e.args[1]))
            return
        if not hasattr(mod, 'Measurement'):
            QMessageBox.critical(self, "Error", "Could not get correct class from file.")
            return
        self.m = getattr(mod, 'Measurement')(redirect_console=True)

        # set up parameter table
        self.tbl_params.clear()
        self.tbl_params.setColumnCount(2)
        self.tbl_params.setRowCount(len(self.m.params))
        for i,key in enumerate(self.m.params):
            item = QTableWidgetItem(key)
            item.setFlags(item.flags()^Qt.ItemIsEditable)
            self.tbl_params.setItem(i, 0, item)
            value = self.m.params[key]
            if isinstance(value, list):
                value = '['+','.join(map(str, value))+']'
            elif isinstance(value, np.ndarray):
                value = '['+",".join(map(str, value.tolist()))+']'
            self.tbl_params.setItem(i, 1, QTableWidgetItem(str(value)))

        # set up plotter
        self.plotter.set_header(self.m.observables)

        # set up observables table
        self.tbl_observables.clear()
        self.tbl_observables.setColumnCount(2)
        self.tbl_observables.setRowCount(len(self.m.observables))
        for i, label in enumerate(self.m.observables):
            for j in [0, 1]:
                item = QTableWidgetItem(label if j==0 else '')
                item.setFlags(item.flags()^Qt.ItemIsEditable)
                self.tbl_observables.setItem(i, j, item)

        # connect signals
        self.connect(self.m, SIGNAL("new_observables_data(PyQt_PyObject)"), self.new_data_handler)
        self.connect(self.m, SIGNAL("new_console_data(QString)"), self.readonlyconsole.write)
        self.connect(self.btn_stopmod, SIGNAL("clicked()"), self.m.quit)
        self.connect(self.btn_forcestopmod, SIGNAL("clicked()"), self.m.terminate)


    @pyqtSlot()
    def run_module(self):
        # check if no other module is running and if the module we loaded is valid
        if isinstance(self.m, QThread) and self.m.isRunning():
            QMessageBox.critical(self, "Error", "Cannot run a new module when the previous one is not done.")
            return
        elif not isinstance(self.m, QThread):
            QMessageBox.critical(self, "Error", "Please load a valid module first.")
            return

        # deactivate request_quit flag in case process has been stopped previously
        # and disconnect all signals
        self.m.flags['quit_requested'] = False

        # set up the parameters
        for i in range(self.tbl_params.rowCount()):
            key, value = [str(self.tbl_params.item(i, j).text()) for j in [0, 1]]
            try:
                self.m.params[key] = eval(value)
            except Exception as e:
                QMessageBox.critical(self, "Error", "Parameter '"+key+"' could not be evaluated: "+str(e.args[0]))
                return

        # run the thread
        self.m.start()

    @pyqtSlot(list)
    def new_data_handler(self, data):
        for i,value in enumerate(data):
            self.tbl_observables.item(i, 1).setText(str(value))
        self.plotter.new_data_handler(data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
     
    w = mainwindow()
    w.show()
     
    sys.exit(app.exec_())
