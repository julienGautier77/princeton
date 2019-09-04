# -*- coding: utf-8 -*-
"""
Created on Tue Jan 31 15:34:18 2017
Need to install PICAM in A 64 windows system

@author:  loa
"""

import ctypes,os,time
import numpy as np
#from picam_types import *


import picam_types as pit
#import syntax_coloring

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
        self.temperature = None
        self.temp_cons = 10
        self.binning = 1
        self.loadLibrary()
        self.getAvailableCameras()
        #self.connect()
        #self.w = self.getParameter("ActiveWidth")
        #self.h = self.getParameter("ActiveHeight")
        #self.totalFrameSize = self.w * self.h
    
    def __del__(self):
        self.unloadLibrary()

    # load picam.dll and initialize library
    def loadLibrary(self):
        path_lib = os.path.join('picam_dll','Picam32.dll')
        print(path_lib)
        self.lib = ctypes.windll.LoadLibrary(path_lib)
        self.lib.Picam_InitializeLibrary() #modif ju
        
        print("library loaded")

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
        print(self.camIDs,id_count)
        modele=[]
        sensorName=[]
        serialNumber=[]
        # if none are found, create a demo camera
        print("Available Cameras:")
        if id_count.value < 1:
            print ('demo')
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
           # 
        else:
            print ('mte')
#            for i in range(id_count.value): # à supprimer si la camera est une MTE
#                print('  Model is ', pit.PicamModelLookup[self.camIDs[i].model])
#                modele.append(pit.PicamModelLookup[self.camIDs[i].model])
#                print('  Computer interface is ', pit.PicamComputerInterfaceLookup[self.camIDs[i].computer_interface])
#                print('  Sensor_name is ', self.camIDs[i].sensor_name)
#                print('  Serial number is', self.camIDs[i].serial_number)
#                print('\n')
#                sensorName.append(self.camIDs[i].sensor_name)
#                serialNumber.append(self.camIDs[i].serial_number)
#        
#        return(modele,sensorName,serialNumber)
        
    def connect(self, camID=None):
        """ Connect to camera.

        :param int camID: Number / index of camera to connect to (optional). It is an integer index into a list of valid camera IDs that has been retrieved by :py:func:`getAvailableCameras`. If camID is None, this functions connects to the first available camera (default).
        """
        if self.cam is not None:
            self.disconnect()
        if camID is None:
            print('camID is none')
            self.cam = pit.pivoid()
            print('cam',self.cam)
            self.lib.Picam_OpenFirstCamera(ptr(self.cam))
            self.w = self.getParameter("ActiveWidth")
            self.h = self.getParameter("ActiveHeight")
            self.totalFrameSize = self.w * self.h
        else:
            print('cammm ID',camID)
            self.cam = pit.pivoid()
            self.lib.Picam_OpenCamera(ptr(self.camIDs[camID]), ctypes.addressof(self.cam))
            self.w = self.getParameter("ActiveWidth")
            self.h = self.getParameter("ActiveHeight")
            self.totalFrameSize = self.w * self.h

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
    def setROI(self, x0, w, xbin, y0, h, ybin, store):
        """Create a single region of interest (ROI).

        :param int x0: X-coordinate of upper left corner of ROI.
        :param int w: Width of ROI.
        :param int xbin: X-Binning, i.e. number of columns that are combined into one larger column (1 to w).
        :param int y0: Y-coordinate of upper left corner of ROI.
        :param int h: Height of ROI.
        :param int ybin: Y-Binning, i.e. number of rows that are combined into one larger row (1 to h).
        """
        r = pit.PicamRoi(x0, w, xbin, y0, h, ybin)
        R = pit.PicamRois(ptr(r), store)   # change 1 to 0 to remove a bug ?!?
        self.setParameter("Rois", R)
        self.totalFrameSize =( (w / xbin) * (h / ybin))
        self.w = (w/xbin) # modif self.w=w
        self.h = (h/ybin)

    def Acquisition(self, N=1, timeout=10000):
        print('acquire')
        self.available = pit.PicamAvailableData()
        errors = pit.piint()
        running = pit.pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        #print('running value',running.value)
        if running.value:
            print("ERROR: acquisition still running")
            return []
        t = time.time()
        self.lib.Picam_Acquire(self.cam, pit.pi64s(N), pit.piint(timeout), ptr(self.available), ptr(errors))
        #(cameraHandel,readoutcount,readouttimeout,outpoutParameter=avaible,outpouterrors)
       # print(self.getParameter("ReadoutCount"))
        print("Durée de l'acquisition : %f s" % (time.time() - t) )
        return t
        

    
    def AcquisitionAssy(self,N=int(1)):
        #asynchronously initiates data acquisition and returns immediately.
        print('start Acquisiotn asynchrone')
        running = pit.pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        print(running.value)
        #if running.value:
         #   print("ERROR: acquisition still running")
          #  return []
        t = time.time()    
        self.setParameter("ReadoutCount", N)
        self.sendConfiguration()
        #print(self.getParameter("ReadoutCount"))
        
        self.lib.Picam_StartAcquisition(self.cam)
        print("Durée de l'acquisition : %f s" % (time.time() - t) )
    
    def WaitForAcquistionUpdate(self,timeout=10000):
        self.available = pit.PicamAvailableData()
        status = ptr(pit.PicamAcquisitionStatus())
        self.lib.Picam_Acquire(self.cam, pit.piint(timeout), ptr(self.available), ptr(status))
        #return self.available.value
    def IsAcquisitionRunning(self):
        running = pit.pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        print('isRunning')
        print(running.value)
        return running.value
    
    def StopAcquisition(self):
        self.lib.Picam_StopAcquisition(self.cam)
        
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
#        return np.array(data).reshape((self.w, self.h))
        #return np.array(data).reshape((self.h, self.w))
        return np.array(data).reshape((int(self.h), int(self.w)))
#        return np.array(data).reshape((1300 / self.binning, 1340 / self.binning))

    def GetTemperature(self):
        self.temperature = self.getParameter("SensorTemperatureReading")
        return self.temperature

    def SetTemperature(self, temperature):
        self.setParameter("SensorTemperatureSetPoint", int(temperature))

    def GetTemperatureStatus(self):
        return self.getParameter("SensorTemperatureStatus")
        
    def GetShutterControl(self,shutter):
        """
        if shutter control set to true signal will available at the output
        """
        return self.getParameter("ShutterControl")
        
    
    def SetShutterControl(self,shutter):
        """
        if shutter control set to true signal will available at the output
        """
        self.setParameter("ShutterControl",int(shutter))
        
    def SetAdcConf(self, gain="High", speed=1.0):
        # gain High, Medium ou Low; plutot High
        # speed 0.5 ou 1.0; plutot 1.0
        self.setParameter("AdcAnalogGain", pit.PicamAdcAnalogGain[gain])
        self.setParameter("AdcSpeed", speed) # 0.5 ou 1.0