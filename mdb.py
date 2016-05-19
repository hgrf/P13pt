import sys

import numpy as np

from PyQt4.QtGui import (QApplication, QFileSystemModel,
                         QSplitter, QTreeView, QVBoxLayout,
                         QHBoxLayout, QListWidgetItem,
                         QListWidget, QPushButton, QWidget,
                         QSizePolicy, QMessageBox, QLabel,
                         QTextEdit)
from PyQt4.QtCore import QDir, Qt

import os
import numpy as np

def scan():
    folders = []
    for i in view.selectedIndexes():
        folders.append(model.fileInfo(i).absoluteFilePath())

    if not len(folders):
        QMessageBox.information(splitter, "No folders selected",
            "Please select folders to scan")
        return

    for fo in folders:
        for root, dirnames, filenames in os.walk(str(fo)):
            for fi in filenames:
                if fi.endswith(('.txt', '.csv')):
                    listw.addItem(os.path.join(root, fi))

def clear():
    listw.clear()

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

def loadinfo(item):
    filename = str(item.text())

    infow.clear()
    with open(filename) as f:
        infow.append('<h1>Comments</h1>')
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
        infow.append(comments)

        # now try to find header, if there is none, check last comment line
        infow.append('<h1>Header</h1>')
        cols = line.split('\t')         # line is the last non-comment line (s.a.)

        if not is_number(cols[0]):      # check if line does not start with a number
            header = line               # in this case this is the header line...
            dataline1 = f.readline()    # ...and the next one is the 1st data line
            ignorelines += 1
        else:
            dataline1 = line            # otherwise the line we read before is already the first data line...
            header = lastcomment[1:]    # ...and we will see if last comment qualifies as header (strip the hash)

        if len(header.split('\t')) == len(dataline1.split('\t')):       # see if "field number" is compatible with data
            infow.append('<p>{}</p>'.format(html_escape(header)))
            header = header.split('\t')
        else:
            header = ['Col {}'.format(i) for i in range(len(dataline1))]

    try:
        data = np.loadtxt(filename, skiprows=ignorelines).T
    except ValueError:      # if we cannot read numbers
        infow.append('<h1>Data not numpy compatible!</h1>')
        return

    infow.append('<h1>Constants detected</h1>')
    for i, col in enumerate(data):
        if len(set(col)) == 1 and header:
            infow.append('{}={}<br>'.format(header[i], col[0]))

    # The algorithm below detects sweeps on "imposed" variables (e.g. voltage
    # set points) that are swept with a constant step. If the sweep step is
    # varied during the sweep, it won't work.
    infow.append('<h1>Sweeps detected</h1>')
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
            infow.append('{}={}:{}:{}<br>'.format(header[i], np.min(col), s[0], np.max(col)))

    infow.append('<h1>Data</h1>')
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

    infow.append(table)
    if len(data[0]) > 20:
        infow.append('<b>... more data available ...</b>')

if __name__ == '__main__':
    app = QApplication(sys.argv)

    splitter = QSplitter()

    # Set up file system model for tree view
    model = QFileSystemModel()
    model.setRootPath(QDir.rootPath())
    model.setFilter(QDir.Dirs|QDir.Drives|QDir.NoDotAndDotDot|QDir.AllDirs)

    # Create the view in the splitter.
    view = QTreeView(splitter)
    view.setModel(model)
    view.setRootIndex(model.index(QDir.rootPath()))

    # Hide other columns
    view.setColumnHidden(1, True)
    view.setColumnHidden(2, True)
    view.setColumnHidden(3, True)

    # Create widget to host the scanner and add it to the splitter
    scannerw = QWidget(splitter)
    vl = QVBoxLayout(scannerw)
    hl = QHBoxLayout()

    listw = QListWidget(scannerw)
    listw.itemClicked.connect(loadinfo)

    btnscan = QPushButton(scannerw)
    btnscan.setText("Scan")
    btnscan.clicked.connect(scan)

    btnclear = QPushButton(scannerw)
    btnclear.setText("Clear")
    btnclear.clicked.connect(clear)

    hl.addWidget(btnclear)
    hl.addWidget(btnscan)

    vl.addLayout(hl)
    vl.addWidget(listw)

    # Create widget to host the information and add it to the splitter
    infow = QTextEdit(splitter)

    # Show the splitter.
    splitter.setStretchFactor(1, 3)        # make folder tree view small
    splitter.setStretchFactor(2, 3)        # make folder tree view small
    splitter.show()

    # Maximize the splitter.
    splitter.setWindowState(Qt.WindowMaximized)

    # Start the main loop.
    sys.exit(app.exec_())
