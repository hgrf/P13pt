import sys
import time

def progressbar(value=0, length=20):
    sys.stdout.write('\r[' + value*'#' + (length-value) * '.' + '] {:>3d}%'.format(value*100/length))
    if value == length:
        sys.stdout.write('\n')
    sys.stdout.flush()

def progressbar_wait(timespan, length=20):
    t0 = time.time()
    value = 0
    progressbar(value, length)
    while True:
        if (time.time()-t0)/timespan*length > value+1:
            value += 1
            progressbar(value, length)
        if value >= length:
            break
        time.sleep(0.01)    # update every 10 ms