# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 11:25:58 2017

@author: meso
"""

import sys
import imp
import os
from PyQt4.Qt import *
from consolewidget import ConsoleWidget

class mainwindow(QWidget):
    def __init__(self, parent=None):
        super(mainwindow, self).__init__(parent)
        
        self.txt_acquisition_script = QLineEdit('Path to acquistion script...', self)
        self.btn_browse = QPushButton('Browse', self)
        self.btn_load = QPushButton('Load Module', self)
        self.btn_runmod = QPushButton('Run Module', self)
        self.btn_stopmod = QPushButton('Stop Module', self)
        self.btn_run = QPushButton('Run', self)
        self.btn_stop = QPushButton('Stop', self)
        self.console = ConsoleWidget(self)
        self.interface = QTextEdit(self)
        
        # Layout stuff
        layout = QVBoxLayout()
        layout.addWidget(self.txt_acquisition_script)
        layout.addWidget(self.btn_browse)
        layout.addWidget(self.btn_load)
        layout.addWidget(self.btn_runmod)
        layout.addWidget(self.btn_stopmod)
        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.console)
        layout.addWidget(self.interface)
        self.setLayout(layout)
        
        self.connect(self.btn_browse, SIGNAL("clicked()"), self.browse_acquisition_script)
        self.connect(self.btn_load, SIGNAL("clicked()"), self.load_measurement)
        self.connect(self.btn_stopmod, SIGNAL("clicked()"), self.stop_measurement)
        self.connect(self.btn_run, SIGNAL("clicked()"), self.execute_acquisition_script)
        self.connect(self.btn_stop, SIGNAL("clicked()"), self.stop_acquisition_script)
        
        # Set window size.
        self.resize(800, 600)
         
        # Set window title
        self.setWindowTitle("Acquisition script launcher")
         
    def browse_acquisition_script(self):
        filename = QFileDialog.getOpenFileName(self, 'Open File', directory='/', filter='*.py')
        self.txt_acquisition_script.setText(filename)
        
    def execute_acquisition_script(self):
        filename = self.txt_acquisition_script.text()
        # the execution has to be done asynchronously, we cannot just run a function in the console
        self.console.tipy.instruction.put('runfile:'+filename)
        
    def load_measurement(self):
        filename = self.txt_acquisition_script.text()
        mod_name, file_ext = os.path.splitext(os.path.split(filename)[-1])
        mod = imp.load_source(mod_name, filename)
        if hasattr(mod, 'Measurement'):
            self.m = getattr(mod, 'Measurement')(self.console)            
            
            self.m.start()
        else:
            print "Could not get correct class from file"
            
    def stop_measurement(self):
        self.m.terminate()
    
    def stop_acquisition_script(self):
        self.console.tipy.stop()



if __name__ == "__main__":
    app = QApplication(sys.argv)
     
    w = mainwindow()
    w.show()
     
    sys.exit(app.exec_())