from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QPushButton, QListWidget, QVBoxLayout, QHBoxLayout, QCheckBox

class Navigator(QWidget):
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        # set up widgets
        self.btn_prev = QPushButton(QIcon('../icons/previous.png'), '')
        self.btn_next = QPushButton(QIcon('../icons/next.png'), '')
        self.chk_auto_jump = QCheckBox('Auto jump to new spectrum')
        self.file_list = QListWidget()

        # set up layout
        l1 = QHBoxLayout()
        for w in [self.btn_prev, self.btn_next]:
            l1.addWidget(w)
        l2 = QVBoxLayout()
        l2.addLayout(l1)
        l2.addWidget(self.file_list)
        l2.addWidget(self.chk_auto_jump)
        self.setLayout(l2)

        # set up connections
        self.btn_next.clicked.connect(self.next_item)
        self.btn_prev.clicked.connect(self.prev_item)
        self.file_list.currentRowChanged.connect(self.selection_changed)

    def update_file_list(self, flist):
        self.file_list.clear()
        for f in flist:
            self.file_list.addItem(f)
        self.file_list.setCurrentRow(0)

    @pyqtSlot(str)
    def new_file_in_dataset(self, filename):
        self.file_list.addItem(filename)
        if self.chk_auto_jump.isChecked():
            self.file_list.setCurrentRow(self.file_list.count()-1)

    def next_item(self):
        i = self.file_list.currentRow()+1
        if i >= self.file_list.count():
            self.file_list.setCurrentRow(0)
        else:
            self.file_list.setCurrentRow(i)

    def prev_item(self):
        i = self.file_list.currentRow()-1
        if i < 0:
            self.file_list.setCurrentRow(self.file_list.count()-1)
        else:
            self.file_list.setCurrentRow(i)

    def clear(self):
        self.file_list.clear()