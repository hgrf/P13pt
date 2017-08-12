import time

class VoltageSource:
    def set_voltage(self, voltage):
        print "setting voltage to ", voltage


class VoltMeter:
    def get_voltage(self):
        v = time.time()
        print "current 'voltage' is ", v
        return v