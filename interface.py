# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!
from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot, QTime
from PyQt5.QtGui import QColor, QImage, QPixmap
from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QLineEdit, QHeaderView,
                             QMenu, QAction, QAbstractItemView,
                             QTableWidgetItem, QSizePolicy)
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon, QPixmap
from color_picker import *
import os

TARGET = "PROCESSING_ZONE"
color_text = ""  # R   G   B   R   G   B   R   G   B   R   G   B "
imageNumber = 0
imageList = os.listdir(TARGET)
color_list = []
selectColor="#ffffff"
img=QImage("logos/movinyl_logo_square_bold.png")
curent=0

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1020, 630)

        self.bgLabel = QtWidgets.QLabel(Dialog)
        self.bgLabel.setGeometry(QtCore.QRect(0, 0, 5000, 5000))
        self.bgLabel.setObjectName("bgLabel")

        self.gridLayoutWidget = QtWidgets.QWidget(Dialog)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(550, 180, 400, 300))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.l14 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l14.setObjectName("l14")
        self.gridLayout.addWidget(self.l14, 2, 1, 1, 1)
        self.l3 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l3.setObjectName("l3")
        self.gridLayout.addWidget(self.l3, 0, 2, 1, 1)
        self.l1 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l1.setObjectName("l1")
        self.gridLayout.addWidget(self.l1, 0, 0, 1, 1)
        self.l10 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l10.setObjectName("l10")
        self.gridLayout.addWidget(self.l10, 4, 0, 1, 1)
        self.l2 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l2.setObjectName("l2")
        self.gridLayout.addWidget(self.l2, 0, 1, 1, 1)
        self.l7 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l7.setObjectName("l7")
        self.gridLayout.addWidget(self.l7, 3, 0, 1, 1)
        self.l13 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l13.setObjectName("l13")
        self.gridLayout.addWidget(self.l13, 2, 0, 1, 1)
        self.l6 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l6.setObjectName("l6")
        self.gridLayout.addWidget(self.l6, 1, 2, 1, 1)
        self.l9 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l9.setObjectName("l9")
        self.gridLayout.addWidget(self.l9, 3, 2, 1, 1)
        self.l4 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l4.setObjectName("l4")
        self.gridLayout.addWidget(self.l4, 1, 0, 1, 1)
        self.l5 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l5.setObjectName("l5")
        self.gridLayout.addWidget(self.l5, 1, 1, 1, 1)
        self.l11 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l11.setObjectName("l11")
        self.gridLayout.addWidget(self.l11, 4, 1, 1, 1)
        self.l8 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l8.setObjectName("l8")
        self.gridLayout.addWidget(self.l8, 3, 1, 1, 1)
        self.l15 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l15.setObjectName("l15")
        self.gridLayout.addWidget(self.l15, 2, 2, 1, 1)
        self.l12 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.l12.setObjectName("l12")
        self.gridLayout.addWidget(self.l12, 4, 2, 1, 1)

        self.zoom_label = QtWidgets.QLabel(Dialog)
        self.zoom_label.setGeometry(QtCore.QRect(540, 50, 100, 100))
        self.zoom_label.setObjectName("zoom_label")

        self.zoom_color_label = QtWidgets.QLabel(Dialog)
        self.zoom_color_label.setGeometry(QtCore.QRect(700, 50, 100, 100))
        self.zoom_color_label.setObjectName("zoom_color_label")

        self.next_label = QtWidgets.QLabel(Dialog)
        self.next_label.setGeometry(QtCore.QRect(700, 520, 100, 50))
        self.next_label.setObjectName("next_label")

        self.clearLabel = QtWidgets.QLabel(Dialog)
        self.clearLabel.setGeometry(QtCore.QRect(475, 520, 30, 30))
        self.clearLabel.setObjectName("clearLabel")


        #self.prev_label = QtWidgets.QLabel(Dialog)
        #self.prev_label.setGeometry(QtCore.QRect(800, 520, 100, 50))
        #"self.prev_label.setObjectName("prev_label")

        self.fileName = QtWidgets.QLabel(Dialog)
        self.fileName.setGeometry(QtCore.QRect(70, 600, 390, 31))
        self.fileName.setObjectName("fileName")

        self.colors_label = QtWidgets.QLabel(Dialog)
        self.colors_label.setGeometry(QtCore.QRect(70, 520, 390, 31))
        self.colors_label.setObjectName("colors_label")

        self.image_label = QtWidgets.QLabel(Dialog)
        self.image_label.setGeometry(QtCore.QRect(0, 0, 500, 500))
        

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)



    def setLabelColor(self, color_list):
        self.l1.setStyleSheet("background-color: "+str(color_list[0]))
        self.l2.setStyleSheet("background-color: "+str(color_list[1]))
        self.l3.setStyleSheet("background-color: "+str(color_list[2]))
        self.l4.setStyleSheet("background-color: "+str(color_list[3]))
        self.l5.setStyleSheet("background-color: "+str(color_list[4]))
        self.l6.setStyleSheet("background-color: "+str(color_list[5]))
        self.l7.setStyleSheet("background-color: "+str(color_list[6]))
        self.l8.setStyleSheet("background-color: "+str(color_list[7]))
        self.l9.setStyleSheet("background-color: "+str(color_list[8]))
        self.l10.setStyleSheet("background-color: "+str(color_list[9]))
        self.l11.setStyleSheet("background-color: "+str(color_list[10]))
        self.l12.setStyleSheet("background-color: "+str(color_list[11]))
        self.l13.setStyleSheet("background-color: "+str(color_list[12]))
        self.l14.setStyleSheet("background-color: "+str(color_list[13]))
        self.l15.setStyleSheet("background-color: "+str(color_list[14]))
        self.bgLabel.setStyleSheet("background-color: #7F7F7F")

    def click1(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[0].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click2(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[1].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click3(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[2].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click4(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[3].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click5(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[4].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click6(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[5].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click7(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[6].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click8(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[7].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click9(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[8].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click10(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[9].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click11(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[10].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click12(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[11].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click13(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[12].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click14(self, event):
        verif="0123456789 "
        global color_text
        h=color_list[13].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    def click15(self, event):
    
        verif="0123456789 "
        global color_text
        h=color_list[14].lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)

    def clickZoom(self, event):
        verif="0123456789 "
        global color_text
        h=selectColor.lstrip('#')
        rgb=tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        srgb=str(rgb)
        for c in srgb :
            a=True
            for x in verif:
                if c==x :
                    a=False
            if a :
                srgb=srgb.replace(c,"");
        color_text = color_text + srgb + " "
        self.colors_label.setText(color_text)
    
        
    def clearFun(self, event):
        global color_text
        color_text = ""
        self.colors_label.setText(color_text)

    def funNext(self, event):
        global imageNumber
        global color_list 
        global color_text
        global img
        #self.next_label.setText("       LOADING...")

        imageNumber = imageNumber+1
        curent_image = TARGET+'/'+imageList[imageNumber]
        result = colorz(curent_image, 15)
        color_list = list(result)
        self.setLabelColor(color_list)

        img = QImage(curent_image)
        pixmap = QPixmap(QPixmap.fromImage(img))
        self.image_label.setPixmap(pixmap)
        color_text = ""
        self.colors_label.setText("")
        self.fileName.setText(imageList[imageNumber])

        #self.next_label.setText("           --->")

    def mousePressEvent(self, event):
        tmp=0

    def mouseMoveEvent(self,event):
        global selectColor
        #factor = 4000/img.height()
        x = event.pos().x()
        y = event.pos().y()
        c = img.pixel(x*8,y*8)  # color code (integer): 3235912
        c_hex = QColor(c).name()  # 8bit RGBA: (255, 23, 0, 255)
        print( x, y, str(c_hex), img.height(), img.width())
        selectColor=str(c_hex)
        self.zoom_color_label.setStyleSheet("background-color: "+str(c_hex))

    def retranslateUi(self, Dialog):
        global color_list 
        global img
        curent_image = TARGET+'/'+imageList[imageNumber]
        result = colorz(curent_image, 15)
        color_list = list(result)
        
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Movinyl Color Picker"))
        self.l14.setText(_translate("Dialog", ""))   
        self.l3.setText(_translate("Dialog", ""))
        self.l1.setText(_translate("Dialog", ""))
        self.l10.setText(_translate("Dialog", ""))
        self.l2.setText(_translate("Dialog", ""))
        self.l7.setText(_translate("Dialog", ""))
        self.l13.setText(_translate("Dialog", ""))
        self.l6.setText(_translate("Dialog", ""))
        self.l9.setText(_translate("Dialog", ""))
        self.l4.setText(_translate("Dialog", ""))
        self.l5.setText(_translate("Dialog", ""))
        self.l11.setText(_translate("Dialog", ""))
        self.l8.setText(_translate("Dialog", ""))
        self.l15.setText(_translate("Dialog", ""))
        self.l12.setText(_translate("Dialog", ""))
        self.next_label.setText(_translate("Dialog", "           --->"))
        self.clearLabel.setText(_translate("Dialog", "X"))
        #self.prev_label.setText(_translate("Dialog", "<---"))
        self.zoom_label.setText(_translate("Dialog", " "))
        self.zoom_color_label.setText(_translate("Dialog", " "))
        self.colors_label.setText(_translate("Dialog", color_text))
        self.image_label.setObjectName("image_label")
        self.colors_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.fileName.setText(_translate("Dialog", imageList[imageNumber]))
        self.fileName.setTextInteractionFlags(Qt.TextSelectableByMouse)


        
        #self.prev_label.setStyleSheet("background-color: #00B903")
        #self.next_label.setStyleSheet("background-color: #9f9f9f")

        #self.image_label.setPixmap(small_pixmap)
        img = QImage(curent_image)
        pixmap = QPixmap(QPixmap.fromImage(img))
        self.image_label.setPixmap(pixmap)
        self.next_label
        self.image_label.show() 
        self.image_label.setScaledContents(True)
        
        self.setLabelColor(color_list)

        self.l1.mousePressEvent = self.click1
        self.l2.mousePressEvent = self.click2
        self.l3.mousePressEvent = self.click3
        self.l4.mousePressEvent = self.click4
        self.l5.mousePressEvent = self.click5
        self.l6.mousePressEvent = self.click6
        self.l7.mousePressEvent = self.click7
        self.l8.mousePressEvent = self.click8
        self.l9.mousePressEvent = self.click9
        self.l10.mousePressEvent = self.click10
        self.l11.mousePressEvent = self.click11
        self.l12.mousePressEvent = self.click12
        self.l13.mousePressEvent = self.click13
        self.l14.mousePressEvent = self.click14
        self.l15.mousePressEvent = self.click15
        self.next_label.mousePressEvent = self.funNext
        self.clearLabel.mousePressEvent = self.clearFun
        self.zoom_color_label.mousePressEvent = self.clickZoom
        self.image_label.mouseMoveEvent=self.mouseMoveEvent



        