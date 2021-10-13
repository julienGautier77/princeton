# -*- coding: utf-8 -*-
"""
Created on Wed Jun 16 10:15:29 2021

@author: Salle-Jaune
"""

import sys

from PyQt5.QtWidgets import QApplication
from princeton import ROPPER
import qdarkstyle

if __name__ == "__main__":       
    
    appli = QApplication(sys.argv)
    confpathVisu='C:/Users/Salle-Jaune/Desktop/Python/Princeton/confCCD.ini'
    appli.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    e = ROPPER(cam='cam0',confpath=confpathVisu)  
    e.show()
    appli.exec_()       