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
    def __init__(self, modifier, fsmodel, parent=None):
        super(Analyser, self).__init__(parent)
        self.modifier = modifier      # Modifier: the instance before plotting the data
        self.fsmodel = fsmodel        # QFileSystemModel (need this to get root path)

    @pyqtSlot(QListWidgetItem)
    def loadinfo(self, item):
        filename = os.path.join(str(self.fsmodel.rootPath()), str(item.text()))

        self.clear()
        with open(filename) as f:
            self.append('<h1>Comments</h1>')
            # search for comments
            comments = '<p>'
            lastcomment = None
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
            cols_tab = line.split('\t')         # line is the last non-comment line (s.a.)
            cols_space = line.split(' ')
            if len(cols_tab) > len(cols_space):
                cols = cols_tab
                delim = '\t'
            else:
                cols = cols_space
                delim = ' '

            if not is_number(cols[0]):      # check if line does not start with a number
                header = line               # in this case this is the header line...
                dataline1 = f.readline()    # ...and the next one is the 1st data line
                ignorelines += 1
            else:
                dataline1 = line            # otherwise the line we read before is already the first data line...
                if lastcomment:
                    header = lastcomment[1:]    # ...and we will see if last comment qualifies as header (strip the hash)
                else:                           # if there is no comment at all, make default header
                    header = delim.join(['Col {}'.format(i) for i in range(len(dataline1.split('\t')))])

            if len(header.split(delim)) == len(dataline1.split(delim)):       # see if "field number" is compatible with data
                self.append('<p>{}</p>'.format(html_escape(header)))
                header = header.strip('\r\n').split(delim) # also removes CR and LF characters
            else:
                header = ['Col {}'.format(i) for i in range(len(dataline1.split(delim)))]

        self.modifier.setfile(filename)
        self.modifier.setheader(header)

        try:
            data = np.loadtxt(filename, skiprows=ignorelines).T
            self.modifier.setdata(data)
        except ValueError:      # if we cannot read numbers
            self.append('<h1>Data not numpy compatible!</h1>')
            self.modifier.setdata(None) # TODO: need something more specific here
            return

        # this list stores the columns we already "understood"
        analysed_cols = []

        # The section below detects columns in the data that stay constant
        # throughout the file
        self.append('<h1>Constants detected</h1>')
        for i, col in enumerate(data):
            if len(set(col)) == 1:
                analysed_cols.append(i)
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
            if (len(s) == 1) or (len(s) > 1 and np.mean(np.diff(s))/s[0] < 1e-12):
                self.append('{}={}:{}:{}<br>'.format(header[i], np.min(col), s[0], np.max(col)))
                analysed_cols.append(i)

        # For all columns that were not successfully analysed above, show min
        # and max values
        self.append('<h1>Other variables</h1>')
        for i, col in enumerate(data):
            if i not in analysed_cols:
                self.append('{}={}:{}<br>'.format(header[i], np.min(col), np.max(col)))

        # In this section we show the data in a table (max. 20 lines)
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
