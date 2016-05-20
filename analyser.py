from PyQt4.QtGui import (QTextEdit, QListWidgetItem)

from PyQt4.QtCore import pyqtSlot

import numpy as np

import os

#### helper functions
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
    }

def html_escape(text):
    """Produce entities within text."""
    return "".join(html_escape_table.get(c,c) for c in text)

class Analyser(QTextEdit):
    def __init__(self, plotter, fsmodel, parent=None):
        super(Analyser, self).__init__(parent)
        self.plotter = plotter      # Plotter (so we can send the header and the data to the plotting widget)
        self.fsmodel = fsmodel      # QFileSystemModel (need this to get root path)

    @pyqtSlot(QListWidgetItem)
    def loadinfo(self, item):
        filename = os.path.join(str(self.fsmodel.rootPath()), str(item.text()))

        self.clear()
        with open(filename) as f:
            self.append('<h1>Comments</h1>')
            # search for comments
            comments = '<p>'
            lastcomment = ''
            ignorelines = 0          # number of lines that won't be considered for data import
            while True:
                line = f.readline()
                if line.startswith('#'):
                    comments += html_escape(line)+'<br>'
                    lastcomment = line
                    ignorelines += 1
                else:
                    break
            comments += '</p>'
            self.append(comments)

            # now try to find header, if there is none, check last comment line
            self.append('<h1>Header</h1>')
            cols = line.split('\t')         # line is the last non-comment line (s.a.)

            if not is_number(cols[0]):      # check if line does not start with a number
                header = line               # in this case this is the header line...
                dataline1 = f.readline()    # ...and the next one is the 1st data line
                ignorelines += 1
            else:
                dataline1 = line            # otherwise the line we read before is already the first data line...
                header = lastcomment[1:]    # ...and we will see if last comment qualifies as header (strip the hash)

            if len(header.split('\t')) == len(dataline1.split('\t')):       # see if "field number" is compatible with data
                self.append('<p>{}</p>'.format(html_escape(header)))
                header = header.strip('\r\n').split('\t') # also removes CR and LF characters
            else:
                header = ['Col {}'.format(i) for i in range(len(dataline1))]

        self.plotter.setheader(header)

        try:
            data = np.loadtxt(filename, skiprows=ignorelines).T
            self.plotter.setdata(data)
        except ValueError:      # if we cannot read numbers
            self.append('<h1>Data not numpy compatible!</h1>')
            self.plotter.setdata(None) # TODO: need something more specific here
            return

        self.append('<h1>Constants detected</h1>')
        for i, col in enumerate(data):
            if len(set(col)) == 1 and header:
                self.append('{}={}<br>'.format(header[i], col[0]))

        # The algorithm below detects sweeps on "imposed" variables (e.g. voltage
        # set points) that are swept with a constant step. If the sweep step is
        # varied during the sweep, it won't work.
        self.append('<h1>Sweeps detected</h1>')
        for i, col in enumerate(data):
            # get sorted unique abs diff values
            s = np.unique(np.abs(np.diff(col)))
            # remove zero
            s = s[s != 0]
            # check if there is a large jump at the end (happens for nested sweeps)
            if len(s) > 1 and (s[-1]-s[-2])/s[-2] > 1e-12:
                s = np.delete(s, -1)
            # check if we have a sweep
            if len(s) and np.mean(np.diff(s))/s[0] < 1e-12:
                self.append('{}={}:{}:{}<br>'.format(header[i], np.min(col), s[0], np.max(col)))

        self.append('<h1>Data</h1>')
        table = '<table border="1" width="100%"><tr>'
        if header:
            for col in header:
                table += '<td>'+col+'</td>'
            table += '</tr>'

        # max 20 data points
        for i in range(min(20, len(data[0]))):
            table += '<tr>'
            for col in data[:,i]:
                table += '<td>'+str(col)+'</td>'
            table += '</tr>'

        table += '</table>'

        self.append(table)
        if len(data[0]) > 20:
            self.append('<b>... more data available ...</b>')
