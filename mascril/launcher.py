import sys
import imp
import os
from PyQt5.QtCore import (pyqtSlot, Qt, QSize, qInstallMessageHandler, QtInfoMsg, QtCriticalMsg, QtDebugMsg,
                          QtWarningMsg, QtFatalMsg)
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from PyQt5.QtWidgets import (QWidget, QTextEdit, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout,
                         QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QApplication,
                         QSplitter, QComboBox, QLabel, QHeaderView)
from P13pt.mascril.measurement import MeasurementBase       # we have to import it the same way (from the same parent
                                                            # modules) as we will do it in the acquisition scripts,
                                                            # otherwise they will not be recognised as the same
                                                            # class
from P13pt.mascril.measurement import MeasurementParameter  # idem
from plotter import Plotter
try:
    from PyQt5.QtCore import QString
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
        # move cursor to end (in case user clicked somewhere else in the window)
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

        while True: # find all carriage returns
            i = data.find('\r')
            if i >= 0: # means we have to deal with a carriage return
                self.insertPlainText(QString(data[0:i]))
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.removeSelectedText()
                data = data[i+1:]
            else:
                break

        # insert remaining text
        self.insertPlainText(QString(data))
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())


class mainwindow(QSplitter):
    def __init__(self, parent=None):
        super(mainwindow, self).__init__(parent)

        self.m = None

        scriptinterfacewidget = QWidget(self)
        self.txt_acquisition_script = QLineEdit('Path to acquistion script...')
        self.btn_browse = QPushButton(QIcon('../icons/folder.png'), '')
        self.btn_browse.setToolTip('Browse')
        l1 = QHBoxLayout()
        for w in [self.txt_acquisition_script, self.btn_browse]:
            l1.addWidget(w)
        self.btn_load = QPushButton(QIcon('tools-wizard.png'), '')
        self.btn_load.setToolTip('Load module')
        self.btn_run = QPushButton(QIcon('../icons/start.png', ), '')
        self.btn_run.setToolTip('Run module')
        self.btn_stopmod = QPushButton(QIcon('../icons/stop.png'), '')
        self.btn_stopmod.setToolTip('Stop module')
        self.btn_forcestopmod = QPushButton(QIcon('../icons/kill.png'), '')
        self.btn_forcestopmod.setToolTip('Kill module')
        for btn in [self.btn_load, self.btn_run, self.btn_stopmod, self.btn_forcestopmod]:
            btn.setIconSize(QSize(32,32))
        for btn in [self.btn_run, self.btn_stopmod, self.btn_forcestopmod]:
            btn.setEnabled(False)
        l2 = QHBoxLayout()
        for w in [self.btn_load, self.btn_run, self.btn_stopmod, self.btn_forcestopmod]:
            l2.addWidget(w)
        # set up parameters table
        self.lbl_params = QLabel('<b>Module parameters:</b>')
        self.tbl_params = QTableWidget()
        self.tbl_params.setColumnCount(2)
        self.tbl_params.setHorizontalHeaderLabels(['Name', 'Value'])
        self.tbl_params.verticalHeader().hide()
        self.tbl_params.horizontalHeader().setStretchLastSection(True)
        self.lbl_readonlyconsole = QLabel('<b>Terminal output:</b>')
        self.readonlyconsole = ReadOnlyConsole()
        l_siw = QVBoxLayout(scriptinterfacewidget)
        for l in [l1, l2]:
            l_siw.addLayout(l)
        for w in [self.lbl_params, self.tbl_params,
                  self.lbl_readonlyconsole, self.readonlyconsole]:
            l_siw.addWidget(w)
        self.plotter = Plotter(self)

        observablesinterfacewidget = QWidget(self)  # this widget will contain the observables list and the alarms
        # set up observables table
        self.lbl_observables = QLabel('<b>Observables:</b>', observablesinterfacewidget)
        self.tbl_observables = QTableWidget(observablesinterfacewidget)
        self.tbl_observables.setColumnCount(2)
        self.tbl_observables.setHorizontalHeaderLabels(['Name', 'Value'])
        self.tbl_observables.verticalHeader().hide()
        self.tbl_observables.horizontalHeader().setStretchLastSection(True)
        # set up alarms table
        self.lbl_alarm = QLabel('<b>Alarms:</b>', observablesinterfacewidget)
        self.tbl_alarms = QTableWidget(observablesinterfacewidget)
        self.tbl_alarms.setColumnCount(3)
        self.tbl_alarms.setHorizontalHeaderLabels(['Condition', 'Action', 'Value'])
        self.tbl_alarms.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_alarms.verticalHeader().hide()
        self.btn_addalarm = QPushButton("Add alarm", observablesinterfacewidget)
        # put everything in a layout
        l = QVBoxLayout(observablesinterfacewidget)
        for w in [self.lbl_observables, self.tbl_observables, self.lbl_alarm, self.tbl_alarms, self.btn_addalarm]:
            l.addWidget(w)

        # make connections
        self.btn_browse.clicked.connect(self.browse_acquisition_script)
        self.btn_load.clicked.connect(self.load_module)
        self.btn_run.clicked.connect(self.run_module)
        self.btn_addalarm.clicked.connect(self.add_alarm)

        # Set window size.
        self.setWindowState(Qt.WindowMaximized)

        # Set window title
        self.setWindowTitle("MAScriL - Mercury Acquisition Script Launcher")

    @pyqtSlot()
    def browse_acquisition_script(self):
        modulespath = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   'modules')
        filename, filt = QFileDialog.getOpenFileName(self, 'Open File',
                                               directory=modulespath,
                                               filter='*.py')
        self.txt_acquisition_script.setText(filename)

    @pyqtSlot()
    def load_module(self):
        # check if there is a running module
        if isinstance(self.m, MeasurementBase) and self.m.isRunning():
            QMessageBox.critical(self, "Error", "Cannot load a new module when the previous one is not done.")
            return

        # check if we are dealing with a valid module
        filename = str(self.txt_acquisition_script.text())
        mod_name, file_ext = os.path.splitext(os.path.split(filename)[-1])
        try:
            mod = imp.load_source(mod_name, filename)
        except IOError as e:
            QMessageBox.critical(self, "Error", "Could not load file: "+str(e.args[1]))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", "Could not load module: "+str(e.args[0]))
            return
        if not hasattr(mod, 'Measurement') or not issubclass(getattr(mod, 'Measurement'), MeasurementBase):
            QMessageBox.critical(self, "Error", "Could not get correct class from file.")
            return
        self.m = getattr(mod, 'Measurement')(redirect_console=True)

        # set up parameter table
        self.tbl_params.clearContents()
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
            if isinstance(value, MeasurementParameter):
                self.tbl_params.setCellWidget(i, 1, value.get_table_widget())
                value.mainwindow = self
            else:
                self.tbl_params.setItem(i, 1, QTableWidgetItem(str(value)))

        # activate run button
        self.btn_run.setEnabled(True)

        # set up plotter
        self.plotter.clear()
        self.plotter.set_header(self.m.observables)

        # set up observables table
        self.tbl_observables.clearContents()
        self.tbl_observables.setRowCount(len(self.m.observables))
        for i, label in enumerate(self.m.observables):
            for j in [0, 1]:
                item = QTableWidgetItem(label if j==0 else '')
                item.setFlags(item.flags()^Qt.ItemIsEditable)
                self.tbl_observables.setItem(i, j, item)

        # set up alarms table
        self.tbl_alarms.clearContents()
        self.tbl_alarms.setRowCount(0)
        for i, alarm in enumerate(self.m.alarms):
            self.add_alarm() # this has the advantage of directly setting up the combobox as well
            self.tbl_alarms.item(i, 0).setText(self.m.alarms[i][0])
            self.tbl_alarms.cellWidget(i, 1).setCurrentIndex(self.m.alarms[i][1])

        # connect signals
        self.m.new_observables_data[object].connect(self.new_data_handler)
        self.m.new_console_data[QString].connect(self.readonlyconsole.write)
        self.btn_stopmod.clicked.connect(self.m.quit)
        self.btn_stopmod.clicked.connect(self.quit_requested)
        self.btn_forcestopmod.clicked.connect(self.m.terminate)
        self.m.finished.connect(self.module_done)

    @pyqtSlot()
    def run_module(self):
        # check if no other module is running and if the module we loaded is valid
        if isinstance(self.m, MeasurementBase) and self.m.isRunning():
            QMessageBox.critical(self, "Error", "Cannot run a new module when the previous one is not done.")
            return
        elif not isinstance(self.m, MeasurementBase):
            QMessageBox.critical(self, "Error", "Please load a valid module first.")
            return

        # deactivate request_quit flag in case process has been stopped previously
        # and disconnect all signals
        self.m.flags['quit_requested'] = False

        # update the parameters that do not update automatically
        # (i.e. that are not derived from MeasurementParameter)
        for i in range(self.tbl_params.rowCount()):
            key = str(self.tbl_params.item(i, 0).text())
            if not isinstance(self.m.params[key], MeasurementParameter):
                # TODO: get rid of the python interpretation and cast value to the correct type (python evaluation should be a special kind of MeasurementParameter)
                value = self.tbl_params.item(i, 1).text()
                try:
                    self.m.params[key] = eval(value, {'np': np})
                except Exception as e:
                    QMessageBox.critical(self, "Error", "Parameter '"+key+"' could not be evaluated: "+str(e.args[0]))
                    return

        # set up the alarms (this will only be necessary once the alarms will be dealt with by MeasurementBase)
        #alarms = []
        #for i in range(self.tbl_alarms.rowCount()):
        #    condition = str(self.tbl_alarms.item(i, 0).text())
        #    action = self.tbl_alarms.cellWidget(i, 1).currentIndex()
        #    alarms.append([condition, action])
        #self.m.alarms = alarms

        # disable parameter editing (here we have to distinguish between "custom" MeasurementParameter widgets and the
        # basic cell items
        for i in range(self.tbl_params.rowCount()):
            widget = self.tbl_params.cellWidget(i, 1)
            item = self.tbl_params.item(i, 1)
            if widget:
                widget.setEnabled(False)
            if item:
                item.setFlags(item.flags()^Qt.ItemIsEnabled)

        # update buttons
        self.btn_load.setEnabled(False)
        self.btn_run.setEnabled(False)
        self.btn_stopmod.setEnabled(True)

        # run the thread
        self.m.start()

    def quit_requested(self):
        self.btn_stopmod.setEnabled(False)
        self.btn_forcestopmod.setEnabled(True)

    def module_done(self):
        # enable parameter editing
        for i in range(self.tbl_params.rowCount()):
            widget = self.tbl_params.cellWidget(i, 1)
            item = self.tbl_params.item(i, 1)
            if widget:
                widget.setEnabled(True)
            if item:
                item.setFlags(item.flags()^Qt.ItemIsEnabled)

        # update buttons
        self.btn_stopmod.setEnabled(False)
        self.btn_forcestopmod.setEnabled(False)
        self.btn_run.setEnabled(True)
        self.btn_load.setEnabled(True)

    @pyqtSlot()
    def add_alarm(self):
        cmb = QComboBox()
        cmb.addItems(['show value', 'stop acquisition', 'call the cops'])
        self.tbl_alarms.setRowCount(self.tbl_alarms.rowCount()+1)
        i = self.tbl_alarms.rowCount()-1
        self.tbl_alarms.setItem(i, 0, QTableWidgetItem())
        item = QTableWidgetItem()
        item.setFlags(item.flags()^Qt.ItemIsEditable)
        self.tbl_alarms.setItem(i, 2, item)
        self.tbl_alarms.setCellWidget(i, 1, cmb)

    @pyqtSlot(list)
    def new_data_handler(self, data):
        for i,value in enumerate(data):
            self.tbl_observables.item(i, 1).setText(str(value))
        self.plotter.new_data_handler(data)

        self.evaluate_alarms(dict(zip(self.m.observables, data)))

    def evaluate_alarms(self, vars):
        vars['np'] = np
        for i in range(self.tbl_alarms.rowCount()):
            self.tbl_alarms.item(i, 2).setBackground(Qt.white)
            condition = str(self.tbl_alarms.item(i, 0).text())
            if condition.strip() == '':
                continue
            try:
                result = eval(condition, vars)
            except Exception as e:
                self.tbl_alarms.item(i, 2).setText("could not evaluate expression: "+str(e.args[0]))
            else:
                cmb_index = self.tbl_alarms.cellWidget(i, 1).currentIndex()
                if cmb_index == 0:  # just show result
                    self.tbl_alarms.item(i, 2).setText(str(result))
                elif cmb_index == 1:  # quit acquisition if result is True
                    if result:
                        self.m.quit()
                elif cmb_index == 2:  # "call the cops" if result is True (just show colour code)
                    if result:
                        self.tbl_alarms.item(i, 2).setText("calling the cops...")
                        self.tbl_alarms.item(i, 2).setBackground(Qt.red)
                    else:
                        self.tbl_alarms.item(i, 2).setText("OK...")
                        self.tbl_alarms.item(i, 2).setBackground(Qt.green)

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

if __name__ == "__main__":
    qInstallMessageHandler(msghandler)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('tools-wizard.png'))

    w = mainwindow()
    w.show()
     
    sys.exit(app.exec_())
