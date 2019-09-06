# princeton

princeton camera control is an user interface lto control ropper scientifics camera (PIXIS,MTE)


It can make plot profile and data measurements  analysis

    https://github.com/julienGautier77/visu

## Requirements
*   python 3.x
*   Numpy
*   PyQt5
*   visu 21019.9
    
## Installation
install PICAM for princeton instrument
install visu 
https://github.com/julienGautier77/visu
pip install visu 

## Usage
appli = QApplication(sys.argv) 
    appli.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    e = ROPPER()  
    e.show()
    appli.exec_()       
