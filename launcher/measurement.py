from PyQt4 import QtCore
from io import BytesIO as StringIO 

import sys

class MeasurementBase(QtCore.QThread):
    def __init__(self, console=None, parent=None): 
        super(MeasurementBase, self).__init__(parent)
        self.console = console
 
    def run(self):
        if self.console is not None:
            # The following has to be in the run function so that it is executed
            # in its own thread, otherwise sys is not the same.        
            self.std_sav = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = self.sio = StringIO()
            self.sio.write = self.console.tipy.write
            
            print "Measurement took over the console; you should not type anything now..."
            print "... because I have not yet disabled the console in execution mode."
        
        l = self.measure()
    
        if self.console is not None:        
            self.console.tipy.interpy.locals.update(l)
        
        self.quit()
    
    def measure(self):
        pass

    def quit(self):
        if self.console is not None:
            print "The measurement is now done, the console is yours again, but..."
            print "... the variables might have been updated."
    
            sys.stdout, sys.stderr = self.std_sav
            self.sio.close()
