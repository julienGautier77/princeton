# princeton

princeton camera control is an user interface lto control ropper scientifics camera (PIXIS,MTE)
it use picam library inspired from :
https://github.com/ddietze/Py-Hardware-Support.git

It can make plot profile and data measurements analysis by using :

    https://github.com/julienGautier77/visu

## Requirements
*   python 3.x
*   Numpy
*   PyQt5
*   visu 2019.9
    
## Installation
install PICAM for princeton instrument

install visu :

https://github.com/julienGautier77/visu

or 

pip install visu 

## Usage
    appli = QApplication(sys.argv) 
    appli.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    e = ROPPER()  
    e.show()
    appli.exec_()       
