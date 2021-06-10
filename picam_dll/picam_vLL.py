#!/usr/bin/python

import ctypes
import numpy as np
from picam_types import *
import picam_types as pit
import time
import PIL
import os

# ##########################################################################################################
# helper functions
def ptr(x):
    """Shortcut to return a ctypes.pointer to object x.
    """
    return ctypes.pointer(x)


# ##########################################################################################################
# Camera Class
class picam():
    """Main class that handles all connectivity with library and cameras.
    """
    # +++++++++++ CONSTRUCTION / DESTRUCTION ++++++++++++++++++++++++++++++++++++++++++++
    def __init__(self):
        self.cam = None
        self.camIDs = None
        self.roisPtr = []
        self.pulsePtr = []
        self.modPtr = []
        self.acqThread = None
        self.w = 1300
        self.h = 1340
        self.totalFrameSize = self.w * self.h
        self.temperature = None
        self.temp_cons = 10
        self.binning = 1
       # self.reference = np.empty([2084 / self.binning, 2084 / self.binning], dtype=np.uint16)
        #self.fond = np.empty([2084 / self.binning, 2084 / self.binning], dtype=np.uint16)
        self.loadLibrary()
        self.getAvailableCameras()
        self.connect()
        #self.setROI(0, 1300, self.binning, 0, 1340, self.binning)
        #self.setParameter("Orientation", PicamOrientationMask["FlippedHorizontally"])
#        self.setParameter("ExposureTime", self.ouv)
        #self.setParameter("ShutterTimingMode", 1)
        #self.csfhc = 500
        #self.setParameter("CleanSectionFinalHeightCount", self.csfhc)
        #self.csfh = 2
        #self.setParameter("CleanSectionFinalHeight", self.csfh)
        #self.ccc = 0
        #self.setParameter("CleanCycleCount", self.ccc)
        #self.cch = 2
        #self.setParameter("CleanCycleHeight", self.cch)
        #self.cut = 1
        #self.setParameter("CleanUntilTrigger", self.cut)
        #self.scd = 0
        #self.sdr = 1000
        self.sendConfiguration()

    def __del__(self):
        self.unloadLibrary()

    # load picam.dll and initialize library
    def loadLibrary(self):
#        drive = osp.splitdrive(osp.realpath(osp.curdir))[0]
#        path_lib = osp.join('C:','\Program Files','Princeton Instruments','PICam','Runtime','Picam32.dll')
#        print(path_lib)
#        self.lib = ctypes.windll.LoadLibrary(path_lib)
        self.lib = ctypes.windll.LoadLibrary("Picam32.dll")
#        self.lib = ctypes.windll.LoadLibrary("C:/Program Files/Princeton Instruments/PICam/Runtime/Picam32.dll")
        self.lib.Picam_InitializeLibrary()

    # call this function to release any resources and free the library
    def unloadLibrary(self):
        for i in range(len(self.roisPtr)):
            self.lib.Picam_DestroyRois(self.roisPtr[i])
        for i in range(len(self.pulsePtr)):
            self.lib.Picam_DestroyPulses(self.pulsePtr[i])
        for i in range(len(self.modPtr)):
            self.lib.Picam_DestroyModulations(self.modPtr[i])
        self.disconnect()

        if isinstance(self.camIDs, list):
            for c in self.camIDs:
                self.lib.Picam_DisconnectDemoCamera(ptr(c))

        if self.camIDs is not None and not isinstance(self.camIDs, list):
            self.lib.Picam_DestroyCameraIDs(self.camIDs)
            self.camIDs = None
        self.lib.Picam_UninitializeLibrary()

    def getAvailableCameras(self):
        """Queries a list of IDs of cameras that are connected to the computer and prints some sensor information for each camera to stdout.

        If no physical camera is found, a demo camera is initialized - *for debug only*.
        """
        if self.camIDs is not None and not isinstance(self.camIDs, list):
            self.lib.Picam_DestroyCameraIDs(self.camIDs)
            self.camIDs = None

        # get connected cameras
        self.camIDs = ptr(pit.PicamCameraID())
        id_count = pit.piint()
        self.lib.Picam_GetAvailableCameraIDs(ptr(self.camIDs), ptr(id_count))

        # if none are found, create a demo camera
        print("Available Cameras:")
        if id_count.value < 1:
            self.lib.Picam_DestroyCameraIDs(self.camIDs)

            model_array = ptr(pit.piint())
            model_count = pit.piint()
            self.lib.Picam_GetAvailableDemoCameraModels(ptr(model_array), ptr(model_count))

            model_ID = pit.PicamCameraID()
            serial = ctypes.c_char_p(b"Demo Cam 1")
            self.lib.Picam_ConnectDemoCamera(model_array[67], serial, ptr(model_ID))
            self.camIDs = [model_ID]

            self.lib.Picam_DestroyModels(model_array)

            print('  Model is ', pit.PicamModelLookup[model_ID.model])
            print('  Computer interface is ', pit.PicamComputerInterfaceLookup[model_ID.computer_interface])
            print('  Sensor_name is ', model_ID.sensor_name)
            print('  Serial number is', model_ID.serial_number)
            print('\n')
        else:
            for i in range(id_count.value):
                print('  Model is ', pit.PicamModelLookup[self.camIDs[i].model])
                print('  Computer interface is ', pit.PicamComputerInterfaceLookup[self.camIDs[i].computer_interface])
                print('  Sensor_name is ', self.camIDs[i].sensor_name)
                print('  Serial number is', self.camIDs[i].serial_number)
                print('\n')

    def connect(self, camID=None):
        """ Connect to camera.

        :param int camID: Number / index of camera to connect to (optional). It is an integer index into a list of valid camera IDs that has been retrieved by :py:func:`getAvailableCameras`. If camID is None, this functions connects to the first available camera (default).
        """
        if self.cam is not None:
            self.disconnect()
        if camID is None:
            self.cam = pit.pivoid()
            self.lib.Picam_OpenFirstCamera(ptr(self.cam))
        else:
            self.cam = pit.pivoid()
            self.lib.Picam_OpenCamera(ptr(self.camIDs[camID]), ctypes.addressof(self.cam))

    def disconnect(self):
        """Disconnect current camera.
        """
        if self.cam is not None:
            self.lib.Picam_CloseCamera(self.cam)
        self.cam = None

    def getCurrentCameraID(self):
        """Returns the current camera ID (:py:class:`PicamCameraID`).
        """
        id = pit.PicamCameraID()
        self.lib.Picam_GetCameraID(self.cam, ptr(id))
        return id

    # prints a list of parameters that are available
    def printAvailableParameters(self):
        """Prints an overview over the parameters to stdout that are available for the current camera and their limits.
        """
        parameter_array = ptr(pit.piint())
        parameter_count = pit.piint()
        self.lib.Picam_GetParameters(self.cam, ptr(parameter_array), ptr(parameter_count))

        for i in range(parameter_count.value):

            # read / write access
            access = pit.piint()
            self.lib.Picam_GetParameterValueAccess(self.cam, parameter_array[i], ptr(access))
            readable = pit.PicamValueAccessLookup[access.value]

            # constraints
            contype = pit.piint()
            self.lib.Picam_GetParameterConstraintType(self.cam, parameter_array[i], ptr(contype))

            if pit.PicamConstraintTypeLookup[contype.value] == "None":
                constraint = "ALL"

            elif pit.PicamConstraintTypeLookup[contype.value] == "Range":

                c = ptr(pit.PicamRangeConstraint())
                self.lib.Picam_GetParameterRangeConstraint(self.cam, parameter_array[i], pit.PicamConstraintCategory['Capable'], ptr(c))

                constraint = "from %f to %f in steps of %f" % (c[0].minimum, c[0].maximum, c[0].increment)

                self.lib.Picam_DestroyRangeConstraints(c)

            elif pit.PicamConstraintTypeLookup[contype.value] == "Collection":

                c = ptr(pit.PicamCollectionConstraint())
                self.lib.Picam_GetParameterCollectionConstraint(self.cam, parameter_array[i], pit.PicamConstraintCategory['Capable'], ptr(c))

                constraint = ""
                for j in range(c[0].values_count):
                    if constraint != "":
                        constraint += ", "
                    constraint += str(c[0].values_array[j])

                self.lib.Picam_DestroyCollectionConstraints(c)

            elif pit.PicamConstraintTypeLookup[contype.value] == "Rois":
                constraint = "N.A."
            elif pit.PicamConstraintTypeLookup[contype.value] == "Pulse":
                constraint = "N.A."
            elif pit.PicamConstraintTypeLookup[contype.value] == "Modulations":
                constraint = "N.A."

            # print(infos
            print(pit.PicamParameterLookup[parameter_array[i]])
            print(" value access:", readable)
            print(" allowed values:", constraint)
            print("\n")

        self.lib.Picam_DestroyParameters(parameter_array)

    # get / set parameters
    # name is a string specifying the parameter
    def getParameter(self, name):
        prm = pit.PicamParameter[name]
        exists = pit.pibln()
        self.lib.Picam_DoesParameterExist(self.cam, prm, ptr(exists))

        # get type of parameter
        type = pit.piint()
        self.lib.Picam_GetParameterValueType(self.cam, prm, ptr(type))

        if pit.PicamValueTypeLookup[type.value] in ["Integer", "Boolean", "Enumeration"]:
            val = pit.piint()

            # test whether we can read the value directly from hardware
            cr = pit.pibln()
            self.lib.Picam_CanReadParameter(self.cam, prm, ptr(cr))
            if cr.value:
                if self.lib.Picam_ReadParameterIntegerValue(self.cam, prm, ptr(val)) == 0:
                    return val.value
            else:
                if self.lib.Picam_GetParameterIntegerValue(self.cam, prm, ptr(val)) == 0:
                    return val.value

        if pit.PicamValueTypeLookup[type.value] == "LargeInteger":
            val = pit.pi64s()
            if self.lib.Picam_GetParameterLargeIntegerValue(self.cam, prm, ptr(val)) == 0:
                return val.value

        if pit.PicamValueTypeLookup[type.value] == "FloatingPoint":
            val = pit.piflt()

            # NEW
            # test whether we can read the value directly from hardware
            cr = pit.pibln()
            self.lib.Picam_CanReadParameter(self.cam, prm, ptr(cr))
            if cr.value:
                if self.lib.Picam_ReadParameterFloatingPointValue(self.cam, prm, ptr(val)) == 0:
                    return val.value
            else:
                if self.lib.Picam_GetParameterFloatingPointValue(self.cam, prm, ptr(val)) == 0:
                    return val.value

        if pit.PicamValueTypeLookup[type.value] == "Rois":
            val = ptr(pit.PicamRois())
            if self.lib.Picam_GetParameterRoisValue(self.cam, prm, ptr(val)) == 0:
                self.roisPtr.append(val)
                return val.contents

        if pit.PicamValueTypeLookup[type.value] == "Pulse":
            val = ptr(pit.PicamPulse())
            if self.lib.Picam_GetParameterPulseValue(self.cam, prm, ptr(val)) == 0:
                self.pulsePtr.append(val)
                return val.contents

        if pit.PicamValueTypeLookup[type.value] == "Modulations":
            val = ptr(pit.PicamModulations())
            if self.lib.Picam_GetParameterModulationsValue(self.cam, prm, ptr(val)) == 0:
                self.modPtr.append(val)
                return val.contents

        return None

    def setParameter(self, name, value):
        """Set parameter. The value is automatically typecast to the correct data type corresponding to the type of parameter.

        .. note:: Setting a parameter with this function does not automatically change the configuration in the camera. In order to apply all changes, :py:func:`sendConfiguration` has to be called.

        :param str name: Name of the parameter exactly as stated in the PICam SDK manual.
        :param mixed value: New parameter value. If the parameter value cannot be changed, a warning is printed to stdout.
        """
        prm = pit.PicamParameter[name]

        exists = pit.pibln()
        self.lib.Picam_DoesParameterExist(self.cam, prm, ptr(exists))
        if not exists:
            print("Ignoring parameter", name)
            print("  Parameter does not exist for current camera!")
            return

        access = pit.piint()
        self.lib.Picam_GetParameterValueAccess(self.cam, prm, ptr(access))
        if pit.PicamValueAccessLookup[access.value] not in ["ReadWrite", "ReadWriteTrivial"]:
            print("Ignoring parameter", name)
            print("  Not allowed to overwrite parameter!")
            return
        if pit.PicamValueAccessLookup[access.value] == "ReadWriteTrivial":
            print("WARNING: Parameter", name, " allows only one value!")

        # get type of parameter
        type = pit.piint()
        self.lib.Picam_GetParameterValueType(self.cam, prm, ptr(type))

        if type.value not in pit.PicamValueTypeLookup:
            print("Ignoring parameter", name)
            print("  Not a valid parameter type:", type.value)
            return

        if pit.PicamValueTypeLookup[type.value] in ["Integer", "Boolean", "Enumeration"]:
            val = pit.piint(value)
            self.lib.Picam_SetParameterIntegerValue(self.cam, prm, val)

        if pit.PicamValueTypeLookup[type.value] == "LargeInteger":
            val = pit.pi64s(value)
            self.lib.Picam_SetParameterLargeIntegerValue(self.cam, prm, val)

        if pit.PicamValueTypeLookup[type.value] == "FloatingPoint":
            val = pit.piflt(value)
            self.lib.Picam_SetParameterFloatingPointValue(self.cam, prm, val)

        if pit.PicamValueTypeLookup[type.value] == "Rois":
            self.lib.Picam_SetParameterRoisValue(self.cam, prm, ptr(value))

        if pit.PicamValueTypeLookup[type.value] == "Pulse":
            self.lib.Picam_SetParameterPulseValue(self.cam, prm, ptr(value))

        if pit.PicamValueTypeLookup[type.value] == "Modulations":
            self.lib.Picam_SetParameterModulationsValue(self.cam, prm, ptr(value))

    # this function has to be called once all configurations
    # are done to apply settings to the camera
    def sendConfiguration(self):
        """This function has to be called once all configurations are done to apply settings to the camera.
        """
        failed = ptr(pit.piint())
        failedCount = pit.piint()
        self.lib.Picam_CommitParameters(self.cam, ptr(failed), ptr(failedCount))
        if failedCount.value > 0:
            for i in range(failedCount.value):
                print("Could not set parameter", pit.PicamParameterLookup[failed[i]])
        self.lib.Picam_DestroyParameters(failed)

    # set a single ROI
    def setROI(self, x0, w, xbin, y0, h, ybin):
        """Create a single region of interest (ROI).

        :param int x0: X-coordinate of upper left corner of ROI.
        :param int w: Width of ROI.
        :param int xbin: X-Binning, i.e. number of columns that are combined into one larger column (1 to w).
        :param int y0: Y-coordinate of upper left corner of ROI.
        :param int h: Height of ROI.
        :param int ybin: Y-Binning, i.e. number of rows that are combined into one larger row (1 to h).
        """
        r = pit.PicamRoi(x0, w, xbin, y0, h, ybin)
        R = pit.PicamRois(ptr(r), 1)
        self.setParameter("Rois", R)
        self.totalFrameSize = (w / xbin) * (h / ybin)
        self.w = w
        self.h = h

    def StartAcquisition(self, N=1, timeout=10000):
        self.available = pit.PicamAvailableData()
        errors = pit.piint()
        running = pit.pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        if running.value:
            print("ERROR: acquisition still running")
            return []
        t = time.time()
        self.lib.Picam_Acquire(self.cam, pit.pi64s(N), pit.piint(timeout), ptr(self.available), ptr(errors))
        print("Durée de l'acquisition : %f s" % (time.time() - t) )

    # this is a helper function that converts a readout buffer into a sequence of numpy arrays
    # it reads all available data at once into a numpy buffer and reformats data to fit to the output mask
    # size is number of readouts to read
    # returns data as floating point
    def GetAcquiredData(self):
        """This is an internally used function to convert the readout buffer into a sequence of numpy arrays.
        It reads all available data at once into a numpy buffer and reformats data to a usable format.

        :param long address: Memory address where the readout buffer is stored.
        :param int size: Number of readouts available in the readout buffer.
        :returns: List of ROIS; for each ROI, array of readouts; each readout is a NxM array.
        """
        # get number of pixels contained in a single readout and a single frame
        # parameters are bytes, a pixel in resulting array is 2 bytes
#        readoutstride = (2084 / self.binning)**2
#        framestride = (2084 / self.binning)**2

        # create a pointer to data
#        dataArrayType = pit.pi16u * 1742000 #readoutstride
        dataArrayType = pit.pi16u * int(self.totalFrameSize) #readoutstride
        dataArrayPointerType = ctypes.POINTER(dataArrayType)
        dataPointer = ctypes.cast(self.available.initial_readout, dataArrayPointerType)

        # create a numpy array from the buffer
        data = np.frombuffer(dataPointer.contents, dtype=np.uint16)
        return np.array(data).reshape((self.w, self.h))
#        return np.array(data).reshape((1300 / self.binning, 1340 / self.binning))

    def GetTemperature(self):
        self.temperature = self.getParameter("SensorTemperatureReading")
        return self.temperature

    def SetTemperature(self, temperature):
        self.setParameter("SensorTemperatureSetPoint", int(temperature))

    def GetTemperatureStatus(self):
        return self.getParameter("SensorTemperatureStatus")

    def SetExposureTime(self, time):
        """
        en ms
        """
        self.setParameter("ExposureTime", int(time))

    def SetAdcConf(self, gain="High", speed=1.0):
        # gain High, Medium ou Low; plutot High
        # speed 0.5 ou 1.0; plutot 1.0
        self.setParameter("AdcAnalogGain", pit.PicamAdcAnalogGain[gain])
        self.setParameter("AdcSpeed", speed) # 0.5 ou 1.0

    def SaveAsTxt(self, path, binning):
        file = open(path, 'w')
        for line in enumerate(self.imageArray):
            if (line[0] % int(self.width/binning) == 0) and (line[0] > 0):
                file.write("\n" + str(line[1]) + " ")
            else:
                file.write(str(line[1])+" ")
        file.close()

try:  
    from PyQt5.QtWidgets import QWidget, QDoubleSpinBox, QGridLayout
    from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QLabel
    from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QCheckBox
    from PyQt5.QtWidgets import QToolButton, QComboBox
    from PyQt5.QtGui import QIcon
    from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QThread
#    from PyQt5.QtGui import QIcon
except:
    from PyQt4.QtGui import QWidget, QDoubleSpinBox, QGridLayout
    from PyQt4.QtGui import QPushButton, QVBoxLayout, QLabel
    from PyQt4.QtGui import QHBoxLayout, QLineEdit, QCheckBox
    from PyQt4.QtGui import QToolButton, QFileDialog, QMainWindow
    from PyQt4.QtGui import QMessageBox, QComboBox
#    from PyQt4.QtGui import Q
    from PyQt4.QtGui import QIcon
    from PyQt4.QtCore import Qt, QSettings, pyqtSignal, QThread
#    from PyQt4.QtGui import QIcon

from guiqwt.plot import ImageWidget, PlotManager, ImageDialog
from guiqwt.builder import make

class MTEinterface(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.setup()
        

    def setup(self):
        self.setWindowTitle('MTE interface')
        self.setWindowIcon(QIcon('icon.svg'))
        self.setMinimumSize(250, 150)

#        self.mte = None
        self.widCON = MTEConnect(self)
        self.widACQ = MTEAcqu(self)
#        self.widSHO = ShowData(self)
        
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.widCON)
        hlayout.addWidget(self.widACQ)

        vlayout = QVBoxLayout()
        vlayout.addLayout(hlayout)
        vlayout.addStretch()

        hlayout2 = QHBoxLayout()
        hlayout2.addLayout(vlayout)
#        hlayout2.addWidget(self.widSHO)
        self.setLayout(hlayout2)

#        hlayout2.widget()
#        self.setCentralWidget(hlayout2.widget())

class MTEAcqu(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
        self.base_path = os.path.realpath(os.path.curdir)
        self.threadAcq = ThreadAcq(self)
        self.configMTE = QSettings('configMTE.ini', QSettings.IniFormat)
                
        

        self.setup()
        
        self.win = ImageDialog(edit=False, toolbar=True, wintitle="Visu Data",
                      options=dict(show_xsection=True, show_ysection=True,
                                   show_contrast=True,
                                   show_itemlist=False))
        self.win.resize(800, 1000)
        data = np.ones((1300, 1340))
        self.item_data = make.image(data, colormap='hot')
        self.plot = self.win.get_plot()
        self.plot.add_item(self.item_data)


    def setup(self):
        self.setWindowTitle('MTE acquisition')

        self.name_file = QLineEdit('filename.tif')
                
        self.showParam = QPushButton('Show Param')
        self.showParam.clicked.connect(self.show_all_param)

        self.com_conf = QComboBox()
        self.com_conf.insertItems(0, self.configMTE.childGroups())
        self.but_load_conf = QPushButton('load conf')
        self.but_load_conf.clicked.connect(self.load_conf)

        hlayout3 = QHBoxLayout()
        hlayout3.addWidget(self.but_load_conf)


        self.check_bck = QCheckBox('Substract BCK')
        self.but_tool = QToolButton()
        self.but_tool.setText('...')
        self.but_tool.clicked.connect(self.load_BCK)
        self.name_bck = QLineEdit('filename_BCK.tif')
        self.name_bck.setDisabled(True)


        hlayout = QHBoxLayout()
        hlayout.addWidget(self.check_bck)
        hlayout.addWidget(self.but_tool)

        self.lin_base_path = QLineEdit('default path')
        self.lin_base_path.setText(self.base_path)
        self.lin_base_path.setDisabled(True)
        self.but_base_path = QToolButton()
        self.but_base_path.setText('...')
        self.but_base_path.clicked.connect(self.ch_base_path)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.lin_base_path)
        hlayout2.addWidget(self.but_base_path)

        self.startAcq = QPushButton('Start Acq')
        self.startAcq.clicked.connect(self.start_acq)

        self.but_show = QPushButton('Show data')
        self.but_show.clicked.connect(self.show_data)

        
        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.showParam)
        vlayout.addSpacing(25)
        vlayout.addWidget(self.com_conf)
        vlayout.addLayout(hlayout3)
        vlayout.addSpacing(25)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.name_bck)
        vlayout.addSpacing(25)
        vlayout.addLayout(hlayout2)
        vlayout.addWidget(self.name_file)
        vlayout.addWidget(self.startAcq)
        vlayout.addSpacing(25)
        vlayout.addWidget(self.but_show)
        vlayout.addStretch()
        self.setLayout(vlayout)

    def ch_base_path(self):
        self.base_path = QFileDialog.getExistingDirectory(self)
        self.lin_base_path.setText(self.base_path)
        print('Base path is set to : %s' % self.base_path)
        
    def load_BCK(self):
        path_bck = QFileDialog.getOpenFileName(self)
        self.name_bck.setText(path_bck)
        print('Background file is set to : %s' % path_bck)

        import PIL
        img_pil = PIL.Image.open(path_bck)
        
        self.array_bck = np.array(img_pil)
        


    def start_acq(self):
        self.mte = self.parent.widCON.mte
        self.threadAcq.start()
        
    def show_all_param(self):
        self.mte.printAvailableParameters()
        param = ['ExposureTime',
                 'ShutterTimingMode']

        print('#### MTE parameters ####')
        for p in param:
            print(p, self.mte.getParameter(p) )


    def show_data(self):
        self.win.show()
        
    def load_conf(self):
        conf = self.com_conf.currentText()
        self.configMTE = QSettings('configMTE.ini', QSettings.IniFormat)
        print('Loading configuration: %s' % conf)

        x0 = int(self.configMTE.value(conf+'/x0'))
        w = int(self.configMTE.value(conf+'/w'))
        y0 = int(self.configMTE.value(conf+'/y0'))
        h = int(self.configMTE.value(conf+'/h'))
        CleanCycleCount = int(self.configMTE.value(conf+'/CleanCycleCount'))
        ExposureTime = int(self.configMTE.value(conf+'/ExposureTime'))
        TriggerResponse = int(self.configMTE.value(conf+'/TriggerResponse'))
        
        self.mte = self.parent.widCON.mte
        self.mte.setParameter("CleanCycleCount", CleanCycleCount)
        self.mte.setParameter("ExposureTime", ExposureTime)
        self.mte.setParameter("TriggerResponse", TriggerResponse)
        self.mte.setROI(x0, w, 1, y0, h, 1)
        self.mte.sendConfiguration()
        
class MTEConnect(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.parent = parent
                
        
        self.setup()
        

    def setup(self):
        self.setWindowTitle('MTE connection')
#        self.setWindowIcon(QIcon('icon.svg'))

        lab1 = QLabel('Current temperature')
        self.lab_cur_temp = QLabel(u'? °C')
        lab2 = QLabel('Set temperature')
        self.val_set_temp = self.local_spinBox(value = 15)
        self.but_set_temp = QPushButton('Set\ntemperature')

        glayout = QGridLayout()
        glayout.addWidget(lab1,              0, 0)
        glayout.addWidget(self.lab_cur_temp, 0, 1)
        glayout.addWidget(lab2,              1, 0)
        glayout.addWidget(self.val_set_temp, 1, 1)
        glayout.addWidget(self.but_set_temp, 0, 2, 2, 2)

        self.connectButton = QPushButton('Connect')
        self.disconnectButton = QPushButton('Disconnect')
#
        self.connectButton.clicked.connect(self.connect)
        self.disconnectButton.clicked.connect(self.disconnect)
        self.but_set_temp.clicked.connect(self.set_temperature)
#
        
        vlayout = QVBoxLayout(self)
        vlayout.addWidget(self.connectButton)
        vlayout.addWidget(self.disconnectButton)
        vlayout.addLayout(glayout)
        vlayout.addStretch()
        self.setLayout(vlayout)
        

    def local_spinBox(self, value = 15, unit='°C'):
        wid = QDoubleSpinBox(self)
        wid.setSuffix(" %s" % unit)
        wid.setMaximum(+20)
        wid.setMinimum(-40)
        wid.setProperty("value", value)
        return wid

    def connect(self):
        self.mte = picam()
        self.connectButton.setStyleSheet("background-color: rgb(0, 170, 0)")
        self.connectButton.setText("Connected")

        self.threadTemp = ThreadTemperature(mte=self.mte)
        self.threadTemp.TEMP.connect(self.update_lab_temp)
        self.threadTemp.start()

    def disconnect(self):
        self.mte.disconnect()
        print('MTE disconnected')
        self.connectButton.setStyleSheet("background-color: rgb(180,180,180)")
        self.connectButton.setText("Not Connected")
        self.lab_cur_temp.setText('?? °C')

    def update_lab_temp(self, temp=None):
        if temp == None:
            temp = self.mte.GetTemperature()
        self.lab_cur_temp.setText('%.2f °C' % temp)

    def set_temperature(self):
        temp = self.val_set_temp.value()
        self.mte.SetTemperature(temp)
        self.mte.sendConfiguration()
        print('Temperature set to %.2f °C' % temp)

        
 #%% Thread
class ThreadTemperature(QThread):
    # Signals
    TEMP = pyqtSignal(float)

    def __init__(self, parent=None, mte=None):
        super(ThreadTemperature,self).__init__(parent)
        self.mte    = mte

    def run(self):
        i = 0
        while self.mte.cam is not None:
            time.sleep(1)
            temp = self.mte.GetTemperature()
            self.TEMP.emit(temp)
            i += 1
            if i == 60:
                print('Temperature = %.2f °C' % temp)
                i = 0

class ThreadAcq(QThread):
    def __init__(self, parent=None):
        super(ThreadAcq,self).__init__(parent)
        self.parent = parent

    def run(self):
        self.mte = self.parent.mte
        print('-----> Start acquisition')
        self.mte.StartAcquisition()
        print('-----> Acquisition ended')

        data = self.mte.GetAcquiredData()        
        data = np.array(data, dtype=np.double)
        
        if self.parent.check_bck.checkState() == 2:
            print('Background substracetd')
            data -= self.parent.array_bck
        
        self.parent.item_data.set_data(data)
        self.parent.plot.replot()
        self.parent.win.update_cross_sections()

        f_path = self.parent.lin_base_path.text()
        f_path = os.path.join(f_path, self.parent.name_file.text())
        img_PIL = PIL.Image.fromarray(data)

        if os.path.isfile(f_path) == True:
            print('File already exist')
            war = QMessageBox(self.parent)
            war.setWindowTitle("File exist")
            war.setText("File name :\n%s\nalready exist." % f_path)
            override = war.addButton('Overwrite', QMessageBox.AcceptRole)
            nosave = war.addButton("Don't save", QMessageBox.AcceptRole)
            war.exec_()
            
            if war.clickedButton() == override:
                img_PIL.save(f_path)
                print('-----> Data saved')
            if war.clickedButton() == nosave:
                print('-----> Data NOT saved')
        else:
            img_PIL.save(f_path)
            print('-----> Data saved')

                
if __name__ == "__main__":
    # Create QApplication
    import guidata
    _app = guidata.qapplication()
    
    e = MTEinterface(None)
    e.show()

    _app.exec_()

    
#if __name__ == '__main__':
#    mte = picam()

#    binning = 2
#    kimera.setParameter("SensorTemperatureSetPoint", 15)
#    kimera.setParameter("ExposureTime", 500)
#    kimera.setParameter("ShutterTimingMode", 1)
#    #kimera.setParameter("CleanSectionFinalHeightCount", 1)
#    kimera.setParameter("CleanSectionFinalHeight", 1)
#    kimera.setParameter("CleanCycleCount", 1)
#    kimera.setParameter("CleanCycleHeight", 2000)
#    kimera.setParameter("CleanUntilTrigger", 0)
#    kimera.sendConfiguration()
#
#    print("get:")
#    print("os", kimera.getParameter("OutputSignal"))
#    print("stm", kimera.getParameter("ShutterTimingMode"))
#    print("scd", kimera.getParameter("ShutterClosingDelay"))
#    print("sdr", kimera.getParameter("ShutterDelayResolution"))
#    print("t = ", kimera.getParameter("ExposureTime"))
#    print("Tsetpoint = ", kimera.getParameter("SensorTemperatureSetPoint"))
#    print("Treading = ", kimera.getParameter("SensorTemperatureReading"))
#    print("Tstatus = ", kimera.GetTemperatureStatus())
#    print("adcspeed = ", kimera.getParameter("AdcSpeed"))
#    print("###############################################################")
#    print("Clos = ", kimera.getParameter("ShutterClosingDelay"))
#    print("Res = ", kimera.getParameter("ShutterDelayResolution"))
#    print("###############################################################")
#    print("roc = ", kimera.getParameter("ReadoutTimeCalculation"))
#    print("vsr = ", kimera.getParameter("VerticalShiftRate"))
#
#    print(kimera.getParameter("CleanSectionFinalHeightCount"))
#    print(kimera.getParameter("CleanSectionFinalHeight"))
#    #print(kimera.getParameter("CleanSerialRegister"))
#    print(kimera.getParameter("CleanCycleCount"))
#    print("cch", kimera.getParameter("CleanCycleHeight"))
#
#    print(kimera.getParameter("CleanUntilTrigger"))
#
#    
#
#    import numpy as np
#    for i in range(3):
#        t0 = time.time()
#        kimera.StartAcquisition()
#        t1 = time.time()
#        data = kimera.GetAcquiredData()
#        print(t1 - t0, "tortue")
#        print(time.time() - t1, "lievre")
#
#    kimera.unloadLibrary()
#
#    from matplotlib.pyplot import *
#    imshow(data)
#    colorbar()
#    clim([0, 2000])
#    show()
