#!/usr/bin/python

import ctypes
import numpy as np
from picam_types import *
import time

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
        self.totalFrameSize = 0
        self.temperature = None
        self.temp_cons = 10
        self.binning = 1
        self.ouv = 100
        self.reference = np.empty([2084 / self.binning, 2084 / self.binning], dtype=np.uint16)
        self.fond = np.empty([2084 / self.binning, 2084 / self.binning], dtype=np.uint16)
        self.loadLibrary()
        self.getAvailableCameras()
        self.connect()
        self.setROI(0, 2084, self.binning, 0, 2084, self.binning)
        #self.setParameter("Orientation", PicamOrientationMask["FlippedHorizontally"])
        self.setParameter("ExposureTime", self.ouv)
        self.setParameter("ShutterTimingMode", 1)
        self.csfhc = 500
        self.setParameter("CleanSectionFinalHeightCount", self.csfhc)
        self.csfh = 2
        self.setParameter("CleanSectionFinalHeight", self.csfh)
        self.ccc = 0
        self.setParameter("CleanCycleCount", self.ccc)
        self.cch = 2
        self.setParameter("CleanCycleHeight", self.cch)
        self.cut = 1
        self.setParameter("CleanUntilTrigger", self.cut)
        self.scd = 0
        self.sdr = 1000
        self.sendConfiguration()

    def __del__(self):
        self.unloadLibrary()

    # load picam.dll and initialize library
    def loadLibrary(self):
        self.lib = ctypes.windll.LoadLibrary("C:\Program Files\Princeton Instruments\PICam\Runtime\Picam32.dll")
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
        self.camIDs = ptr(PicamCameraID())
        id_count = piint()
        self.lib.Picam_GetAvailableCameraIDs(ptr(self.camIDs), ptr(id_count))

        # if none are found, create a demo camera
        print("Available Cameras:")
        if id_count.value < 1:
            self.lib.Picam_DestroyCameraIDs(self.camIDs)

            model_array = ptr(piint())
            model_count = piint()
            self.lib.Picam_GetAvailableDemoCameraModels(ptr(model_array), ptr(model_count))

            model_ID = PicamCameraID()
            serial = ctypes.c_char_p("Demo Cam 1")
            self.lib.Picam_ConnectDemoCamera(model_array[67], serial, ptr(model_ID))
            self.camIDs = [model_ID]

            self.lib.Picam_DestroyModels(model_array)

            print('  Model is ', PicamModelLookup[model_ID.model])
            print('  Computer interface is ', PicamComputerInterfaceLookup[model_ID.computer_interface])
            print('  Sensor_name is ', model_ID.sensor_name)
            print('  Serial number is', model_ID.serial_number)
            print('\n')
        else:
            for i in range(id_count.value):
                print('  Model is ', PicamModelLookup[self.camIDs[i].model])
                print('  Computer interface is ', PicamComputerInterfaceLookup[self.camIDs[i].computer_interface])
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
            self.cam = pivoid()
            self.lib.Picam_OpenFirstCamera(ptr(self.cam))
        else:
            self.cam = pivoid()
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
        id = PicamCameraID()
        self.lib.Picam_GetCameraID(self.cam, ptr(id))
        return id

    # prints a list of parameters that are available
    def printAvailableParameters(self):
        """Prints an overview over the parameters to stdout that are available for the current camera and their limits.
        """
        parameter_array = ptr(piint())
        parameter_count = piint()
        self.lib.Picam_GetParameters(self.cam, ptr(parameter_array), ptr(parameter_count))

        for i in range(parameter_count.value):

            # read / write access
            access = piint()
            self.lib.Picam_GetParameterValueAccess(self.cam, parameter_array[i], ptr(access))
            readable = PicamValueAccessLookup[access.value]

            # constraints
            contype = piint()
            self.lib.Picam_GetParameterConstraintType(self.cam, parameter_array[i], ptr(contype))

            if PicamConstraintTypeLookup[contype.value] == "None":
                constraint = "ALL"

            elif PicamConstraintTypeLookup[contype.value] == "Range":

                c = ptr(PicamRangeConstraint())
                self.lib.Picam_GetParameterRangeConstraint(self.cam, parameter_array[i], PicamConstraintCategory['Capable'], ptr(c))

                constraint = "from %f to %f in steps of %f" % (c[0].minimum, c[0].maximum, c[0].increment)

                self.lib.Picam_DestroyRangeConstraints(c)

            elif PicamConstraintTypeLookup[contype.value] == "Collection":

                c = ptr(PicamCollectionConstraint())
                self.lib.Picam_GetParameterCollectionConstraint(self.cam, parameter_array[i], PicamConstraintCategory['Capable'], ptr(c))

                constraint = ""
                for j in range(c[0].values_count):
                    if constraint != "":
                        constraint += ", "
                    constraint += str(c[0].values_array[j])

                self.lib.Picam_DestroyCollectionConstraints(c)

            elif PicamConstraintTypeLookup[contype.value] == "Rois":
                constraint = "N.A."
            elif PicamConstraintTypeLookup[contype.value] == "Pulse":
                constraint = "N.A."
            elif PicamConstraintTypeLookup[contype.value] == "Modulations":
                constraint = "N.A."

            # print(infos
            print(PicamParameterLookup[parameter_array[i]])
            print(" value access:", readable)
            print(" allowed values:", constraint)
            print("\n")

        self.lib.Picam_DestroyParameters(parameter_array)

    # get / set parameters
    # name is a string specifying the parameter
    def getParameter(self, name):
        prm = PicamParameter[name]
        exists = pibln()
        self.lib.Picam_DoesParameterExist(self.cam, prm, ptr(exists))

        # get type of parameter
        type = piint()
        self.lib.Picam_GetParameterValueType(self.cam, prm, ptr(type))

        if PicamValueTypeLookup[type.value] in ["Integer", "Boolean", "Enumeration"]:
            val = piint()

            # test whether we can read the value directly from hardware
            cr = pibln()
            self.lib.Picam_CanReadParameter(self.cam, prm, ptr(cr))
            if cr.value:
                if self.lib.Picam_ReadParameterIntegerValue(self.cam, prm, ptr(val)) == 0:
                    return val.value
            else:
                if self.lib.Picam_GetParameterIntegerValue(self.cam, prm, ptr(val)) == 0:
                    return val.value

        if PicamValueTypeLookup[type.value] == "LargeInteger":
            val = pi64s()
            if self.lib.Picam_GetParameterLargeIntegerValue(self.cam, prm, ptr(val)) == 0:
                return val.value

        if PicamValueTypeLookup[type.value] == "FloatingPoint":
            val = piflt()

            # NEW
            # test whether we can read the value directly from hardware
            cr = pibln()
            self.lib.Picam_CanReadParameter(self.cam, prm, ptr(cr))
            if cr.value:
                if self.lib.Picam_ReadParameterFloatingPointValue(self.cam, prm, ptr(val)) == 0:
                    return val.value
            else:
                if self.lib.Picam_GetParameterFloatingPointValue(self.cam, prm, ptr(val)) == 0:
                    return val.value

        if PicamValueTypeLookup[type.value] == "Rois":
            val = ptr(PicamRois())
            if self.lib.Picam_GetParameterRoisValue(self.cam, prm, ptr(val)) == 0:
                self.roisPtr.append(val)
                return val.contents

        if PicamValueTypeLookup[type.value] == "Pulse":
            val = ptr(PicamPulse())
            if self.lib.Picam_GetParameterPulseValue(self.cam, prm, ptr(val)) == 0:
                self.pulsePtr.append(val)
                return val.contents

        if PicamValueTypeLookup[type.value] == "Modulations":
            val = ptr(PicamModulations())
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
        prm = PicamParameter[name]

        exists = pibln()
        self.lib.Picam_DoesParameterExist(self.cam, prm, ptr(exists))
        if not exists:
            print("Ignoring parameter", name)
            print("  Parameter does not exist for current camera!")
            return

        access = piint()
        self.lib.Picam_GetParameterValueAccess(self.cam, prm, ptr(access))
        if PicamValueAccessLookup[access.value] not in ["ReadWrite", "ReadWriteTrivial"]:
            print("Ignoring parameter", name)
            print("  Not allowed to overwrite parameter!")
            return
        if PicamValueAccessLookup[access.value] == "ReadWriteTrivial":
            print("WARNING: Parameter", name, " allows only one value!")

        # get type of parameter
        type = piint()
        self.lib.Picam_GetParameterValueType(self.cam, prm, ptr(type))

        if type.value not in PicamValueTypeLookup:
            print("Ignoring parameter", name)
            print("  Not a valid parameter type:", type.value)
            return

        if PicamValueTypeLookup[type.value] in ["Integer", "Boolean", "Enumeration"]:
            val = piint(value)
            self.lib.Picam_SetParameterIntegerValue(self.cam, prm, val)

        if PicamValueTypeLookup[type.value] == "LargeInteger":
            val = pi64s(value)
            self.lib.Picam_SetParameterLargeIntegerValue(self.cam, prm, val)

        if PicamValueTypeLookup[type.value] == "FloatingPoint":
            val = piflt(value)
            self.lib.Picam_SetParameterFloatingPointValue(self.cam, prm, val)

        if PicamValueTypeLookup[type.value] == "Rois":
            self.lib.Picam_SetParameterRoisValue(self.cam, prm, ptr(value))

        if PicamValueTypeLookup[type.value] == "Pulse":
            self.lib.Picam_SetParameterPulseValue(self.cam, prm, ptr(value))

        if PicamValueTypeLookup[type.value] == "Modulations":
            self.lib.Picam_SetParameterModulationsValue(self.cam, prm, ptr(value))

    # this function has to be called once all configurations
    # are done to apply settings to the camera
    def sendConfiguration(self):
        """This function has to be called once all configurations are done to apply settings to the camera.
        """
        print("sendconf")
        failed = ptr(piint())
        failedCount = piint()
        self.lib.Picam_CommitParameters(self.cam, ptr(failed), ptr(failedCount))
        if failedCount.value > 0:
            for i in range(failedCount.value):
                print("Could not set parameter", PicamParameterLookup[failed[i]])
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
        r = PicamRoi(x0, w, xbin, y0, h, ybin)
        R = PicamRois(ptr(r), 1)
        self.setParameter("Rois", R)
        self.totalFrameSize = (w / xbin) * (h / ybin)

    def StartAcquisition(self, N=1, timeout=10000):
        self.available = PicamAvailableData()
        errors = piint()
        running = pibln()
        self.lib.Picam_IsAcquisitionRunning(self.cam, ptr(running))
        if running.value:
            print("ERROR: acquisition still running")
            return []
        t = time.time()
        self.lib.Picam_Acquire(self.cam, pi64s(N), piint(timeout), ptr(self.available), ptr(errors))
        print(time.time() - t, "StartAcquisition")

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
        readoutstride = (2084 / self.binning)**2
        framestride = (2084 / self.binning)**2

        # create a pointer to data
        dataArrayType = pi16u * readoutstride
        dataArrayPointerType = ctypes.POINTER(dataArrayType)
        dataPointer = ctypes.cast(self.available.initial_readout, dataArrayPointerType)

        # create a numpy array from the buffer
        data = np.frombuffer(dataPointer.contents, dtype=np.uint16)
        return np.array(data).reshape((2084 / self.binning, 2084 / self.binning))

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
        self.setParameter("AdcAnalogGain", PicamAdcAnalogGain[gain])
        self.setParameter("AdcSpeed", speed) # 0.5 ou 1.0

    def SaveAsTxt(self, path, binning):
        file = open(path, 'w')
        for line in enumerate(self.imageArray):
            if (line[0] % int(self.width/binning) == 0) and (line[0] > 0):
                file.write("\n" + str(line[1]) + " ")
            else:
                file.write(str(line[1])+" ")
        file.close()

if __name__ == '__main__':
    kimera = picam()
    binning = 2
    kimera.setParameter("SensorTemperatureSetPoint", 15)
    kimera.setParameter("ExposureTime", 500)
    kimera.setParameter("ShutterTimingMode", 1)
    #kimera.setParameter("CleanSectionFinalHeightCount", 1)
    kimera.setParameter("CleanSectionFinalHeight", 1)
    kimera.setParameter("CleanCycleCount", 1)
    kimera.setParameter("CleanCycleHeight", 2000)
    kimera.setParameter("CleanUntilTrigger", 0)
    kimera.sendConfiguration()

    print("get:")
    print("os", kimera.getParameter("OutputSignal"))
    print("stm", kimera.getParameter("ShutterTimingMode"))
    print("scd", kimera.getParameter("ShutterClosingDelay"))
    print("sdr", kimera.getParameter("ShutterDelayResolution"))
    print("t = ", kimera.getParameter("ExposureTime"))
    print("Tsetpoint = ", kimera.getParameter("SensorTemperatureSetPoint"))
    print("Treading = ", kimera.getParameter("SensorTemperatureReading"))
    print("Tstatus = ", kimera.GetTemperatureStatus())
    print("adcspeed = ", kimera.getParameter("AdcSpeed"))
    print("###############################################################")
    print("Clos = ", kimera.getParameter("ShutterClosingDelay"))
    print("Res = ", kimera.getParameter("ShutterDelayResolution"))
    print("###############################################################")
    print("roc = ", kimera.getParameter("ReadoutTimeCalculation"))
    print("vsr = ", kimera.getParameter("VerticalShiftRate"))

    print(kimera.getParameter("CleanSectionFinalHeightCount"))
    print(kimera.getParameter("CleanSectionFinalHeight"))
    #print(kimera.getParameter("CleanSerialRegister"))
    print(kimera.getParameter("CleanCycleCount"))
    print("cch", kimera.getParameter("CleanCycleHeight"))

    print(kimera.getParameter("CleanUntilTrigger"))

    

    import numpy as np
    for i in range(3):
        t0 = time.time()
        kimera.StartAcquisition()
        t1 = time.time()
        data = kimera.GetAcquiredData()
        print(t1 - t0, "tortue")
        print(time.time() - t1, "lievre")

    kimera.unloadLibrary()

    from matplotlib.pyplot import *
    imshow(data)
    colorbar()
    clim([0, 2000])
    show()
