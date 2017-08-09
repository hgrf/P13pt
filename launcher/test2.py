from measurement import MeasurementBase 

from time import sleep

class Measurement(MeasurementBase):
    def __init__(self, console=None, parent=None): 
        super(Measurement, self).__init__(console, parent)

    def measure(self):
        print "running"
        
        for i in range(10):
            print i
            sleep(0.5)
        
        print "done"
        
        return locals()

if __name__ == "__main__":
    m = Measurement()
    m.run()