#!/usr/bin/python

from __future__ import print_function
import sys
import os
import shutil
from glob import glob
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import configparser
from PIL import Image

from PyQt5.QtCore import (Qt, qInstallMessageHandler, QtInfoMsg, QtCriticalMsg, QtDebugMsg,
                          QtWarningMsg, QtFatalMsg, QSettings, pyqtSlot, QStandardPaths, QUrl)
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import (QApplication, QMessageBox, QMainWindow, QDockWidget, QAction,
                             QFileDialog, QProgressDialog, QVBoxLayout, QWidget, QGridLayout,
                             QPushButton, QHBoxLayout, QLineEdit, QLabel)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import numpy as np
from numpy.linalg import norm
import matplotlib.transforms as mtransforms


class MainWindow(QMainWindow):
    marking = None
    marks = [None]*4
    uvtexts = [None]*4
    stretch = np.asarray([1.,1.])
    translation = np.asarray([0.,0.])
    rotation = 0.

    def __init__(self, imgfile=None, parent=None):
        super(MainWindow, self).__init__(parent)

        ################### set up UI
        self.setWindowTitle('sscAlign')

        # "mark selector"
        self.controlpanel = QWidget()
        l = QGridLayout()
        # add four buttons
        for i in range(4):
            # make a button for activating marking
            btn = QPushButton(str(i+1), self.controlpanel)
            btn.clicked.connect(self.activate_marking)
            btn.markindex = i

            # make a button for removing mark
            btn2 = QPushButton('X', self.controlpanel)
            btn2.clicked.connect(self.remove_mark)
            btn2.markindex = i

            txtU = QLineEdit(self.controlpanel)
            txtV = QLineEdit(self.controlpanel)
            self.uvtexts[i] = (txtU, txtV)
            l2 = QGridLayout()
            for j,w in enumerate([QLabel('U:', self.controlpanel), txtU, btn,
                                  QLabel('V:', self.controlpanel), txtV, btn2]):
                l2.addWidget(w, j//3, j%3)            
            l.addLayout(l2, i//2, i%2)
        
        # set up button for aligning
        btn = QPushButton('Align', self.controlpanel)
        btn.clicked.connect(self.align)
        l.addWidget(btn, 3, 1)

        # set up button for resetting scale
        btn = QPushButton('Reset scale', self.controlpanel)
        btn.clicked.connect(self.autolims)
        l.addWidget(btn, 3, 0)

        # set up button for saving
        btn = QPushButton('Save', self.controlpanel)
        btn.clicked.connect(self.save)
        l.addWidget(btn, 4, 1)

        # set up text fields for stretch, translation and rotation
        self.txtStretchX = QLineEdit(self.controlpanel)
        self.txtStretchY = QLineEdit(self.controlpanel)
        self.txtTranslationX = QLineEdit(self.controlpanel)
        self.txtTranslationY = QLineEdit(self.controlpanel)
        self.txtRotation = QLineEdit(self.controlpanel)
        l2 = QGridLayout()
        for i,w in enumerate([QLabel('Stretch X:', self.controlpanel), self.txtStretchX,
                              QLabel('Stretch Y:', self.controlpanel), self.txtStretchY,
                              QLabel('Translation X:', self.controlpanel), self.txtTranslationX,
                              QLabel('Translation Y:', self.controlpanel), self.txtTranslationY,
                              QLabel('Rotation:', self.controlpanel), self.txtRotation]):
            l2.addWidget(w, i//4, i%4)

        l3 = QVBoxLayout()
        l3.addLayout(l)
        l3.addLayout(l2)
        self.controlpanel.setLayout(l3)

        # "plotting window"
        self.setCentralWidget(QWidget())
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.centralWidget())
        l = QVBoxLayout()
        for w in [self.toolbar, self.canvas]:
            l.addWidget(w)
        l2 = QHBoxLayout()
        l2.addLayout(l)
        l2.addWidget(self.controlpanel)
        self.centralWidget().setLayout(l2)

        # set up marking event
        self.canvas.mpl_connect('button_press_event', self.figure_onclick)
        self.canvas.mpl_connect('scroll_event', self.figure_onscroll)
        
        self.show()

        # choose image file
        if imgfile is None:
            imgfile, filter = QFileDialog.getOpenFileName(None, 'Pick an image file', filter='*.*')
        self.load_image(imgfile)

    def load_image(self, imgfile):
        print('Loading:', imgfile)

        # try to load image file
        try:
            self.img = mpimg.imread(imgfile)
        except Exception as e:
            print("An error occured:", e)
            return

        raw_width, raw_height = float(self.img.shape[1]), float(self.img.shape[0])

        # set up default UV coords
        lowerleftuv = [0.,0.]
        upperrightuv = [0.1,0.1]        # default in eLine is 100x100 um (this is what we will probably load if there is an automatically generated .ssc file)
        unit = 'mm'

        # figure out if there is already an associated .ssc file
        f, ext = os.path.splitext(imgfile)
        ssc_file = f+'.ssc'
        if os.path.isfile(ssc_file):
            print("Associated .ssc file detected. Loading:", ssc_file)

            # parse .ssc file
            config = configparser.ConfigParser()
            config.read(ssc_file)
            if 'SLOWSCAN' in config.sections():
                for key in config['SLOWSCAN']:
                    if key == 'lowerleftuv':
                        lowerleftuv = list(map(float, config['SLOWSCAN']['lowerleftuv'].split(',')))
                    elif key == 'upperrightuv':
                        upperrightuv = list(map(float, config['SLOWSCAN']['upperrightuv'].split(',')))
            else:
                raise Exception('Invalid .ssc file')

        # calculate stretch and translation parameters
        self.translate_stretch_twopoint((0, 0), lowerleftuv, (raw_width, raw_height), upperrightuv)

        # check if pixels are squares
        uv_aspect = self.stretch[1]*raw_height/(self.stretch[0]*raw_width)
        xy_aspect = raw_height/raw_width
        if abs(uv_aspect-xy_aspect) > 1e-3:
            reply = QMessageBox.question(self, 'Correct aspect ratio?', 
                                         'Image aspect ratio: {:.2f}\nUV aspect ratio: {:.2f}\nWould you like to correct this?'.format(xy_aspect, uv_aspect),
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stretch[1] = self.stretch[0]

        # put the origin in the lower left corner and flip the y-axis of the matrix self.img around accordingly
        # extent is not specified here, that part is taken care of by the transformations in self.show_im()
        self.im = self.ax.imshow(self.img[-1:0:-1,:,:], origin='lower')
        self.show_im()                   # apply transforms and draw image

    def show_im(self):
        # apply stretch, translation and rotation to the image
        self.transformation = mtransforms.Affine2D().scale(self.stretch[0], self.stretch[1]) + \
                              mtransforms.Affine2D().rotate(self.rotation) + \
                              mtransforms.Affine2D().translate(self.translation[0], self.translation[1])
        self.im.set_transform(self.transformation+self.ax.transData)
        
        # update text fields
        self.txtStretchX.setText(str(self.stretch[0]))
        self.txtStretchY.setText(str(self.stretch[1]))
        self.txtTranslationX.setText(str(self.translation[0]))
        self.txtTranslationY.setText(str(self.translation[1]))
        self.txtRotation.setText(str(self.rotation*180./np.pi))

        # update x and y limits
        self.autolims()

    def save(self):
        # ask user where to save
        bmpfile, filter = QFileDialog.getSaveFileName(None, 'Pick an image file', filter='*.bmp')
        if not bmpfile:
            return

        # check if correct file format was chosen and check if file
        # exists in this case (otherwise already checked by the file dialog)
        filename, ext = os.path.splitext(bmpfile)
        if ext.lower() != '.bmp':
            bmpfile += '.bmp'
            if os.path.isfile(bmpfile):
                reply = QMessageBox.question(self, 'Overwrite file?', 
                                            'File already exists: {} Overwrite?'.format(bmpfile),
                                            QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

        # figure out if there is already an associated .ssc file
        f, ext = os.path.splitext(bmpfile)
        sscfile = f+'.ssc'
        if os.path.isfile(sscfile):
            reply = QMessageBox.question(self, 'Overwrite .ssc file?', 
                                         'A corresponding .ssc file already exists. Overwrite?',
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        print('Saving to:', bmpfile, sscfile)

        # save bmp
        img = Image.fromarray(self.img)
        img = img.rotate(self.rotation*180./np.pi, expand=True)
        img.save(bmpfile)

        # calculate bounding rectangle
        u1, u2, v1, v2 = self.get_extent()
        # TODO: what are these following good for ?
        localoriginuv = [0.,0.]
        stageuv = [0.,0.]
        rotationuv = 0.

        # save ssc
        # TODO: check if 6 digits after floating point are required
        with open(sscfile, 'w') as f:
            f.write('[SLOWSCAN]\n'
                'Bitmap='+os.path.basename(bmpfile)+'\n'+
                'LowerLeftUV={:.6f},{:.6f}\n'.format(u1, v1)+
                'UpperRightUV={:.6f},{:.6f}\n'.format(u2, v2)+
                'LocalOriginUV={:.6f},{:.6f}\n'.format(*localoriginuv)+
                'StageUV={:.6f},{:.6f}\n'.format(*stageuv)+
                'RotationUV={:.6f}\n'.format(rotationuv)
            )

    def get_extent(self):
        # update x and y limits (make sure all 4 corners are included in plot)
        x1, x2, y1, y2 = self.im.get_extent()
        # bl, tr, tl, br
        corners = np.asarray([self.transformation.transform_point((x1-0.5, y1-0.5)),
                              self.transformation.transform_point((x2+0.5, y2+0.5)),
                              self.transformation.transform_point((x1-0.5, y2+0.5)),
                              self.transformation.transform_point((x2+0.5, y1-0.5))])
        
        return min(corners[:,0]), max(corners[:,0]), min(corners[:,1]), max(corners[:,1])

    def autolims(self):
        u1, u2, v1, v2 = self.get_extent()

        self.ax.set_xlim((u1, u2))
        self.ax.set_ylim((v1, v2))

        self.canvas.draw()

    def activate_marking(self):
        print('marking requested for mark #', self.sender().markindex+1)
        self.marking = self.sender().markindex

    def remove_mark(self):
        print('Removing mark #', self.sender().markindex)
        self.ax.lines.remove(self.marks[self.sender().markindex])
        self.marks[self.sender().markindex] = None
        self.uvtexts[self.sender().markindex][0].setText('')
        self.uvtexts[self.sender().markindex][1].setText('')
        self.canvas.draw()

    def set_mark(self, i, x, y):
        '''
            set mark # i to coordinates x, y
        '''
        print('Setting mark #', i, 'to X, Y =', x, ', ', y)
        if self.marks[i] is None:
            self.marks[i], = self.ax.plot(x, y, 'ro')
        else:
            self.marks[i].set_xdata([x])
            self.marks[i].set_ydata([y])
        self.canvas.draw()

    def figure_onclick(self, event):
        if self.marking is not None:
            self.set_mark(self.marking, event.xdata, event.ydata)
            self.marking = None

    def figure_onscroll(self, event):
        # adapted from https://stackoverflow.com/questions/11551049/matplotlib-plot-zooming-with-scroll-wheel
        base_scale = 1.1

        # get the current x and y limits
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata = event.xdata # get event x location
        ydata = event.ydata # get event y location
        if event.button == 'up':
            # deal with zoom in
            scale_factor = 1/base_scale
        elif event.button == 'down':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1
            print(event.button)
        # set new limits (see comment by David on stackoverflow thread mentioned above)
        self.ax.set_xlim([xdata - (xdata-cur_xlim[0]) * scale_factor,
                          xdata + (cur_xlim[1]-xdata) * scale_factor])
        self.ax.set_ylim([ydata - (ydata-cur_ylim[0]) * scale_factor,
                          ydata + (cur_ylim[1]-ydata) * scale_factor])

        self.canvas.draw() # force re-draw

    def translate_stretch_twopoint(self, xy1, uv1, xy2, uv2):
        '''
            calculate translation and stretch from two points (assume no rotation)
            translation is calculated from first point
            returns nothing, result is directly applied as shift to stored values
        '''
        # make sure arguments can be used as numpy arrays
        xy1, uv1, xy2, uv2 = map(np.asarray, (xy1, uv1, xy2, uv2))

        self.stretch = (uv2-uv1)/(xy2-xy1)
        self.translation = uv1-xy1

    def translate_onepoint(self, xy1, uv1):
        '''
            calculate translation from one point
            returns nothing, result is directly applied as shift to stored values
        '''
        # make sure arguments can be used as numpy arrays
        xy1, uv1 = map(np.asarray, (xy1, uv1))

        self.translation += uv1-xy1


    def translate_rotate_stretch_twopoint(self, xy1, uv1, xy2, uv2):
        '''
            calculate translation, stretch and rotation from two points
            translation is calculated from first point
            returns nothing, result is directly applied as shift to stored values
        '''
        # make sure arguments can be used as numpy arrays
        xy1, uv1, xy2, uv2 = map(np.asarray, (xy1, uv1, xy2, uv2))
        
        transformation = mtransforms.Affine2D().translate(-self.translation[0], -self.translation[1]) + \
                         mtransforms.Affine2D().rotate(-self.rotation) + \
                         mtransforms.Affine2D().scale(1./self.stretch[0], 1./self.stretch[1])

        # determine stretch
        stretch_correction = norm(uv2-uv1)/norm(xy2-xy1)
        self.stretch *= stretch_correction

        # determine rotation
        unit_xy = xy2-xy1
        unit_xy /= norm(unit_xy)
        unit_uv = uv2-uv1
        unit_uv /= norm(unit_uv)
        costheta = np.dot(unit_xy, unit_uv)
        sintheta = np.cross(unit_xy, unit_uv)
        self.rotation += np.arctan2(sintheta, costheta)

        print('XY1 in raw coords:', transformation.transform_point(xy1))

        transformation += mtransforms.Affine2D().scale(self.stretch[0], self.stretch[1]) + \
                          mtransforms.Affine2D().rotate(self.rotation)

        print('XY1 in new scaled and rotated system:', transformation.transform_point(xy1))

        # update translation
        self.translation = (uv1-transformation.transform_point(xy1))
 
    def align(self):
        # in the following, we use X, Y for old coordinates and U, V for new coordinates 
        # (i.e. here X, Y do NOT refer to the "raw" image coordinates)

        # count valid alignment markers
        xys = []
        uvs = []
        marks = []
        for i,line in enumerate(self.marks):
            if line is not None:
                # get coordinates from mark
                xy = (line.get_xdata()[0], line.get_ydata()[0])
                # try to get coordinates from QLineEdit's
                try:
                    u = float(self.uvtexts[i][0].text())
                except Exception:
                    self.uvtexts[i][0].setStyleSheet("QLineEdit { background: rgb(255, 0, 0); }")
                    u = None
                else:
                    self.uvtexts[i][0].setStyleSheet("QLineEdit { background: rgb(0, 255, 0); }")
                try:
                    v = float(self.uvtexts[i][1].text())
                except Exception:
                    self.uvtexts[i][1].setStyleSheet("QLineEdit { background: rgb(255, 0, 0); }")
                    v = None
                else:
                    self.uvtexts[i][1].setStyleSheet("QLineEdit { background: rgb(0, 255, 0); }")
                if u is None or v is None:
                    continue
                uv = (u,v)
                xys.append(xy)
                uvs.append(uv)
                marks.append(line)

        if len(xys) == 0:
            QMessageBox.warning(self, 'Alignment not possible', 'We need at least one valid marker for alignment')
            return
        elif len(xys) == 1:
            print('Carrying out one point alignment (translation)')
            self.translate_onepoint(xys[0], uvs[0])
        elif len(xys) == 2:
            print('Carrying out two point alignment (stretch, rotation, translation)')
            self.translate_rotate_stretch_twopoint(xys[0], uvs[0], xys[1], uvs[1])
        else:
            QMessageBox.warning(self, 'Alignment not possible', '3- and 4-point alignment is not supported yet')
            return

        # update mark coordinates
        for i,line in enumerate(marks):
            line.set_xdata([uvs[i][0]])
            line.set_ydata([uvs[i][1]])
        
        # update image
        self.show_im()
            

def main():
    app = QApplication(sys.argv)

    testing = False
    if testing:
        mainwindow = MainWindow('post development.tif')
        mainwindow.set_mark(0, 0.01577, 0.01307)
        mainwindow.set_mark(1, 0.06762, 0.01602)
        mainwindow.uvtexts[0][0].setText('-10')
        mainwindow.uvtexts[0][1].setText('-20')
        mainwindow.uvtexts[1][0].setText('0')
        mainwindow.uvtexts[1][1].setText('-20')
    else:
        mainwindow = MainWindow()

    # Start the main loop.
    ret = app.exec_()

    sys.exit(ret)

if __name__ == '__main__':
    main()
