# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 11:35:15 2021

@author: Salle-Jaune
"""
__version__='2019.9'
__author__='julien Gautier'
version=__version__

import sys
from PyQt5.QtWidgets import QApplication,QWidget,QSizePolicy,QGroupBox,QVBoxLayout
from PyQt5.QtWidgets import QGridLayout,QDockWidget
from PyQt5.QtGui import QIcon
import pathlib,os
import qdarkstyle
from princeton import ROPPER
        

class App2Cam(QWidget):
    #class 4 camera
    def __init__(self,camName0=None,camName1=None):
        
        super().__init__()
        self.left=100
        self.top=30
        self.width=1000
        self.height=1500
        self.setGeometry(self.left,self.top,self.width,self.height)
        self.setWindowTitle('Princeton 2 cameras' )
       
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        p = pathlib.Path(__file__)
        sepa=os.sep
        self.icon=str(p.parent) + sepa + 'icons' +sepa
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
        
        confpath='C:/Users/Salle-Jaune/Desktop/Python/Princeton/confCCD.ini'

        self.cam0 =ROPPER(cam='cam0',confpath=confpath)    
        self.cam1 =ROPPER(cam='cam1',confpath=confpath)
        
        self.cam=[self.cam0,self.cam1]
        self.setup()
        self.setContentsMargins(1,1,1,1)
        self.actionButton()
        
    def setup(self):

        grid_layout = QGridLayout()
        grid_layout.setVerticalSpacing(1)
        grid_layout.setHorizontalSpacing(1)
        
        
        self.dock0=QDockWidget(self)
        self.dock0.setWindowTitle(self.cam0.ccdName)
        self.dock0.setWidget(self.cam0)
        self.dock0.setFeatures(QDockWidget.DockWidgetFloatable)
#        self.dock0.setWindowState(Qt::WindowFullScreen)
        
        self.dock1=QDockWidget(self)
        self.dock1.setWindowTitle(self.cam1.ccdName)
        self.dock1.setWidget(self.cam1)
        self.dock1.setFeatures(QDockWidget.DockWidgetFloatable)
        
               
        
        grid_layout.addWidget(self.dock0, 0, 0)
        grid_layout.addWidget(self.dock1, 0, 1)
        
        
        grid_layout.setContentsMargins(1,1,1,1)
        self.horizontalGroupBox=QGroupBox()
        self.horizontalGroupBox.setLayout(grid_layout)
        self.horizontalGroupBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        windowLayout=QVBoxLayout()
        windowLayout.addWidget(self.horizontalGroupBox)
        windowLayout.setContentsMargins(1,1,1,1)
        self.setLayout(windowLayout)


    def actionButton(self):
        self.dock0.topLevelChanged.connect(self.Dock0Changed)
        self.dock1.topLevelChanged.connect(self.Dock1Changed)
        
    def Dock0Changed(self):
        self.dock0.showMaximized()
    def Dock1Changed(self):
        self.dock1.showMaximized()
    
    
        

    def closeEvent(self,event):
        exit
        event.accept()

        
if __name__ == "__main__":       
    
    appli = QApplication(sys.argv)
    appli.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    e=App2Cam()
    e.show()
    
    appli.exec_()       