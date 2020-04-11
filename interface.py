# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QIcon, QPixmap
from tmp import *

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1015, 586)
        self.gridLayoutWidget = QtWidgets.QWidget(Dialog)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(550, 210, 311, 281))
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
        self.label_18 = QtWidgets.QLabel(Dialog)
        self.label_18.setGeometry(QtCore.QRect(70, 520, 391, 31))
        self.label_18.setObjectName("label_18")
        self.image_label = QtWidgets.QLabel(Dialog)
        self.image_label.setGeometry(QtCore.QRect(0, 0, 500, 500))
        

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        result = colorz("image.jpg", 16)
        color_list=list(result)

        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.l14.setText(_translate("Dialog", "14"))
        self.l3.setText(_translate("Dialog", "3"))
        self.l1.setText(_translate("Dialog", "1"))
        self.l10.setText(_translate("Dialog", "10"))
        self.l2.setText(_translate("Dialog", "TextLabel"))
        self.l7.setText(_translate("Dialog", "TextLabel"))
        self.l13.setText(_translate("Dialog", "12"))
        self.l6.setText(_translate("Dialog", "TextLabel"))
        self.l9.setText(_translate("Dialog", "TextLabel"))
        self.l4.setText(_translate("Dialog", "TextLabel"))
        self.l5.setText(_translate("Dialog", "TextLabel"))
        self.l11.setText(_translate("Dialog", "TextLabel"))
        self.l8.setText(_translate("Dialog", "18"))
        self.l15.setText(_translate("Dialog", "15"))
        self.l12.setText(_translate("Dialog", "12"))
        self.zoom_label.setText(_translate("Dialog", "TextLabel"))
        self.zoom_color_label.setText(_translate("Dialog", "TextLabel"))
        self.label_18.setText(_translate("Dialog", "TextLabel"))
        self.image_label.setObjectName("image_label")
        self.image_label.setPixmap(QtGui.QPixmap("test.png"))
        self.image_label.show() # You were missing this.
        self.image_label.setScaledContents(True)
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
       

        


        