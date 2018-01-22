import sys
from PyQt5.QtGui import QFont, QFontMetrics
from PyQt5.QtWidgets import QWidget, QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLineEdit, QLabel
from PyQt5.Qt import QObject, pyqtSignal
from mdbinfo import FileInfo, Mod

class ConsoleStream(QObject):
    messageWritten = pyqtSignal(str)

    def flush( self ):
        pass

    def fileno( self ):
        return -1

    def write( self, msg ):
        if ( not self.signalsBlocked() ):
            self.messageWritten.emit(unicode(msg))

class Modifier(QWidget):
    def __init__(self, parent=None):
        super(Modifier, self).__init__(parent)

        self.plotter = parent.plotterw      # This is where the plotting takes place (need to inform this widget about changes in the data)
        self.mdbinfo = parent.mdbinfo

        self.lblselect = QLabel('Select modifier:')
        self.cmbselect = QComboBox()
        self.lblcreate = QLabel('Create modifier:')
        self.txtcreate = QLineEdit('Modifier name')
        self.btncreate = QPushButton('Create')
        self.editor = QTextEdit()
        self.console = QTextEdit()
        self.btnapply = QPushButton('Apply')
        self.btndelete = QPushButton('Delete modifier')
        self.btnmakedefault = QPushButton('Make default')
        self.btnsave = QPushButton('Save modifier')

        # disable editing console
        self.console.setReadOnly(True)

        # configure "code" font
        font = QFont()
        font.setFamily('Courier')
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(12)
        self.editor.setFont(font)

        # set up tab length to 4 spaces
        metrics = QFontMetrics(font)
        self.editor.setTabStopWidth(4*metrics.width(' '));

        self.editor.setStyleSheet('font-family: Courier;')
        self.editor.setAcceptRichText(False)

        self.cmbselect.currentIndexChanged[int].connect(self.changemod)
        self.btnapply.clicked.connect(self.apply)
        self.btnsave.clicked.connect(self.save)
        self.btndelete.clicked.connect(self.delete)
        self.btncreate.clicked.connect(self.create)
        self.btnmakedefault.clicked.connect(self.makedefault)

        h2 = QHBoxLayout()
        h2.addWidget(self.lblcreate)
        h2.addWidget(self.txtcreate)
        h2.addWidget(self.btncreate)

        h = QHBoxLayout()
        h.addWidget(self.btndelete)
        h.addWidget(self.btnsave)
        h.addWidget(self.btnmakedefault)
        h.addWidget(self.btnapply)

        l = QVBoxLayout()
        l.addWidget(self.cmbselect)
        l.addLayout(h2)
        l.addWidget(self.editor)
        l.addWidget(self.console)
        l.addLayout(h)

        self.setLayout(l)

    def setfile(self, filename):
        self.filename = filename

        # tidy up
        self.cmbselect.blockSignals(True)  # otherwise the combobox is too talkative when we modify it

        self.cmbselect.clear()
        self.editor.clear()

        self.cmbselect.addItem('None')

        # load existing modifiers
        if filename in self.mdbinfo.files:
            self.fileinfo = self.mdbinfo.files[filename]
        else:
            self.fileinfo = FileInfo()
        for mod in self.fileinfo.modifiers:
            self.cmbselect.addItem(mod.name)

        self.cmbselect.blockSignals(False)

        self.changemod(self.fileinfo.defaultmod)

    def setheader(self, header):
        self.orgheader = header             # save original header
        self.plotter.setheader(header)

    def setdata(self, data):
        self.orgdata = data                 # save original data
        self.plotter.setdata(data)

        self.apply()

    # right now the cycle is setfile, setheader, setdata (they are executed in series)
    # TODO: it would be much more logical to combine setfile, setheader and setdata in some way

    def changemod(self, i):                 # i referring to index in Combobox!
        if i:
            self.cmbselect.setCurrentIndex(i)         # (first entry is "None")
            self.editor.setText(self.fileinfo.modifiers[i-1].code)
            self.editor.setEnabled(True)
            self.btnsave.setEnabled(True)
            self.btndelete.setEnabled(True)
        else:       # no modifier to apply
            self.editor.clear()
            self.editor.setEnabled(False)
            self.btnsave.setEnabled(False)
            self.btndelete.setEnabled(False)

    def makedefault(self):
        self.fileinfo.defaultmod = self.cmbselect.currentIndex()
        self.mdbinfo.files[self.filename] = self.fileinfo
        self.mdbinfo.save()

    def apply(self):
        # restore original header and data
        header = self.orgheader
        data = self.orgdata

        # back up stdout and stderr
        oldstdout = sys.stdout
        oldstderr = sys.stderr

        s = ConsoleStream()
        s.messageWritten.connect(self.console.insertPlainText)
        sys.stdout = s
        sys.stderr = s

        # execute user code
        exec(str(self.editor.toPlainText()))

        # restore stdout and stderr
        sys.stdout = oldstdout
        sys.stderr = oldstderr

        # update plot
        self.plotter.setheader(header)
        self.plotter.setdata(data)

    def save(self):
        mod = Mod()
        mod.name = str(self.cmbselect.currentText())
        mod.code = self.editor.toPlainText()
        self.fileinfo.modifiers[self.cmbselect.currentIndex()-1] = mod
        self.mdbinfo.files[self.filename] = self.fileinfo
        self.mdbinfo.save()

    def delete(self):
        i = self.cmbselect.currentIndex()
        del self.fileinfo.modifiers[i-1]
        if self.fileinfo.defaultmod == i:     # check if we're deleting the default modifier
            self.fileinfo.defaultmod = 0      # if true, set default modifier to "None"
        self.mdbinfo.files[self.filename] = self.fileinfo
        self.setfile(self.filename)     # re-initialise

    def create(self):
        mod = Mod()
        mod.name = str(self.txtcreate.text())
        mod.code = ''
        self.fileinfo.modifiers.append(mod)
        self.mdbinfo.files[self.filename] = self.fileinfo
        self.mdbinfo.save()
        self.cmbselect.addItem(self.txtcreate.text())
        self.changemod(self.cmbselect.count()-1)
