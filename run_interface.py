from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QDialog
from PyQt5.QtGui import *
import sys
import interface

class MainDialog(QDialog,interface.Ui_Dialog):
    def __init__(self,parent=None):
        super(MainDialog,self).__init__(parent)
        self.setupUi(self)

app=QApplication(sys.argv) 
form=MainDialog()
form.show()
app.exec_()