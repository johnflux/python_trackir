""" Library to read 6 DOF (Degrees of Information) from a TrackIR camera.

    Note that this only works on Windows, since it requires the TrackIR.dll.
    The TrackIR software must be running, and use the 1:1 mapping if you want real values

    See log_to_csv.py for example usage
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from typing import Union
import winreg
import os
import sys


verbose = True

def logprint(*args, **kwargs):
    """ Function to print debug info"""
    if verbose:
        print(*args, file=sys.stderr, **kwargs)
def npResultToString(retValue: int):
    if retValue >= 0 and retValue <= 7:
        return [
            "OK",
            "DEVICE_NOT_PRESENT",
            "UNSUPPORTED_OS",
            "INVALID_ARG",
            "DLL_NOT_FOUND",
            "NO_DATA",
            "INTERNAL_DATA",
            "We didn't shutdown properly last time.  Restart TrackIR gui" # I'm guessing here - I think it means that it thinks we are already registered
        ][retValue]
    return "Unknown error"

def checkReturn(retValue: int) -> int:
    if retValue != 0:
        raise Exception("DLL function returned an error value {}: {}".format(retValue, npResultToString(retValue)))
    return retValue

class TrackIR_Signature_Data(ctypes.Structure):
    """
    This is information about the DLL returned by TrackIRDLL.NP_GetSignature()

    This struct-equivalent is to replicate the 'struct tir_signature' that is passed to the NP_GetSignature(struct tir_signature *sig) function in the DLL
    It must exactly match the C struct:
        pragma pack(1)
        struct tir_data{
            char DllSignature[200];
            char AppSignature[200];
        };
    See the python ctypes.Structure documentation for information about _pack_ and _fields_
    """
    _pack_ = 1
    _fields_ = [
        ("_DllSignature", ctypes.ARRAY(ctypes.c_char, 200)),
        ("_AppSignature", ctypes.ARRAY(ctypes.c_char, 200))
    ]

    @property
    def DllSignature(self) -> str:
        return self._DllSignature.decode('utf-8')
    @property
    def AppSignature(self) -> str:
        return self._AppSignature.decode('utf-8')

class TrackIR_6DOF_Data(ctypes.Structure):
    """
    This is the 6 DOF (Degrees of Freedom) data returned by TrackIRDLL.NP_GetData()

    This struct-equivalent is to replicate the 'struct tir_data' that is passed to the NP_GetData(struct tir_data *data) function in the DLL
    It must exactly match the C struct:
        pragma pack(1)
        struct tir_data{
            short status;
            short frame;
            unsigned int cksum;
            float roll, pitch, yaw;
            float tx, ty, tz;
            float rawx, rawy, rawz;
            float smoothx, smoothy, smoothz;
        };
    See the python ctypes.Structure documentation for information about _pack_ and _fields_
    """
    _pack_ = 1
    _fields_ = [
        ("status", ctypes.c_short),
        ("frame", ctypes.c_short),
        ("cksum", ctypes.c_uint),
        # Calculated 6 DOF, between -16383 to 16383
        # Call NP_RequestData with 119 to get only these values
        ("_roll", ctypes.c_float),
        ("_pitch", ctypes.c_float),
        ("_yaw", ctypes.c_float),
        ("_x", ctypes.c_float),
        ("_y", ctypes.c_float),
        ("_z", ctypes.c_float),
        # Raw object imager values - note that you must call NP_RequestData
        # with a value like 65535 to get these values
        # raw object position from imager
        ("_rawx", ctypes.c_float), # 0..25600
        ("_rawy", ctypes.c_float), # 0..25600
        ("_rawz", ctypes.c_float), # 0..25600
        # x, y, z deltas from raw imager position
        ("_deltax", ctypes.c_float), # 0..25600
        ("_deltay", ctypes.c_float), # 0..25600
        ("_deltaz", ctypes.c_float), # 0..25600
        # raw object position from imager
        ("_smoothx", ctypes.c_float), # 0..25600
        ("_smoothy", ctypes.c_float), # 0..25600
        ("_smoothz", ctypes.c_float), # 0..25600
    ]
    # Some helper functions to convert the values to degrees
    @property
    def roll(self):
        return -self._roll*90/16383
    @property
    def pitch(self):
        return -self._pitch*180/16383
    @property
    def yaw(self):
        return -self._yaw*180/16383
    @property            
    def x(self):
        return -self._x/64
    @property
    def y(self):
        return self._y/64
    @property
    def z(self):
        return self._z/64
    
    def __str__(self):
        return "status: {0}, frame: {1}, cksum: {2}, roll: {3}, pitch: {4}, yaw: {5}, x: {6}, y: {7}, z: {8}".format(
            self.status, self.frame, self.cksum, round(self.roll), round(self.pitch), round(self.yaw), round(self.x), round(self.y), round(self.z))


class TrackIRDLL():
    """ A class that loads the trackIR dll (NPClient64.dll) and provides functions to call them.
        The functions starting with the name 'NP_' in this class just call that function in the DLL.
    """

    def __init__(self, hWnd: Union[wintypes.HWND,int,str], trackir_profile_id: int =3750):  # Note that FreePIE uses id 13302, and 3750 is "Unity 64-bit"
        """This function expects the TrackIR software to be installed - specifically NPClient64.dll.

           It raises an Exception if the TrackIR software is not installed.

           hWnd is a Window hWND, and is used by TrackIR to detect if your program has stopped.  Called 'frame' in TKinter. e.g.

             import tkinter
             app = tkinter.Tk()
             trackir = TrackIRDll(app.wm_frame())
             while True:
                data = trackrIr.NP_GetData()
                print(data)
                time.sleep(0.01)

            NOTE: TrackR will just refuse to send information if it doesn't have a hWnd, or if the window is closed.
            An alternative is to just pass it the hwnd of some other window. (Such as the TrackIR gui itself! hah).  But if you do that, you will
            have to kill the TrackIR gui every time you want to restart this program.
        """
        # Find the DLL folder
        key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, r"Software\\NaturalPoint\\NATURALPOINT\\NPClient Location")
        path, _ = winreg.QueryValueEx(key, "Path")
        dllpath = path + "NPClient64.dll"
        logprint("Loading DLL: ", dllpath)
        trackIrDll = ctypes.WinDLL(dllpath)
        logprint("Loaded")

        # We have now loaded the DLL.  This has the following functions:
        #   int NP_RegisterWindowHandle(HWND hwnd);
        #   int NP_UnregisterWindowHandle(void);
        #   int NP_RegisterProgramProfileID(unsigned short id);
        #   int NP_QueryVersion(unsigned short *version);
        #   int NP_RequestData(unsigned short req);
        #   int NP_GetSignature(tir_signature *sig);
        #   int NP_GetData(tir_data *data);
        #   int NP_GetParameter(void);
        #   int NP_SetParameter(void);
        #   int NP_StartCursor(void);
        #   int NP_StopCursor(void);
        #   int NP_ReCenter(void);
        #   int NP_StartDataTransmission(void);
        #   int NP_StopDataTransmission(void);
    
        # Use 'ctypes' to let us call these functions

        INPUT_PARAMETER=1 # Magic numbers used by ctypes.WINFUNCTYPE
        #OUTPUT_PARAMETER=2

        # map the NP_GetSignature(tir_signature_t *sig) in the DLL
        self.NP_GetSignature_api = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.POINTER(TrackIR_Signature_Data))(("NP_GetSignature", trackIrDll), ((INPUT_PARAMETER, "signature"),))
        # map the NP_RegisterProgramProfileID(ushort id) in the DLL
        self.NP_RegisterProgramProfileID_api = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ushort)(("NP_RegisterProgramProfileID", trackIrDll), ((INPUT_PARAMETER, "id"),))
        # map the NP_RequestData(ushort dataFields) function in the DLL
        self.NP_RequestData_api = ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.c_ushort)(("NP_RequestData", trackIrDll), ((INPUT_PARAMETER, "dataFields"),))
        # map the NP_StopCursor() function in the DLL.  I'm not sure what this does, but we need to call it before calling NP_StartDataTransmission()
        self.NP_StopCursor_api = ctypes.WINFUNCTYPE(ctypes.c_int)(("NP_StopCursor", trackIrDll), ())
        # map the NP_StartCursor() function in the DLL.  I'm not sure what this does, but we presumably need to call it after calling NP_StopDataTransmission()
        self.NP_StartCursor_api = ctypes.WINFUNCTYPE(ctypes.c_int)(("NP_StartCursor", trackIrDll), ())
        # map the NP_StartDataTransmission() function in the DLL
        self.NP_StartDataTransmission_api = ctypes.WINFUNCTYPE(ctypes.c_int)(("NP_StartDataTransmission", trackIrDll), ())
        # map the NP_StopDataTransmission() function in the DLL
        self.NP_StopDataTransmission_api = ctypes.WINFUNCTYPE(ctypes.c_int)(("NP_StopDataTransmission", trackIrDll), ())
        # map the NP_GetData() function in the DLL. Note that we mark the parameter, data, as an 'OUTPUT_PARAMETER' so that ctypes will magically treat this as a return value
        self.NP_GetData_api = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.POINTER(TrackIR_6DOF_Data))(("NP_GetData", trackIrDll), ((INPUT_PARAMETER,"data"),))
        # map the NP_UnregisterWindowHandle() function in the DLL.  Do this at the very end when you stop.  I think this is just used so that TrackIR can know if your program closed down
        # without telling it.  But I'm just guessing
        self.NP_UnregisterWindowHandle_api = ctypes.WINFUNCTYPE(ctypes.c_int)(("NP_UnregisterWindowHandle", trackIrDll), ())
        # map the NP_RegisterWindowHandle(HWND wnd) function in the DLL.  Do this right after getting the signature.  I think this is just used so that TrackIR can know if your program closed down
        # without telling it.  But I'm just guessing
        self.NP_RegisterWindowHandle_api = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND)(("NP_RegisterWindowHandle", trackIrDll), ((INPUT_PARAMETER,"hWnd"),))


        self.trackir_profile_id = trackir_profile_id
        if isinstance(hWnd, str):
            # Assume it is a string in the form 0x....   because that's what tkinter gives, for example
            hWnd = int(hWnd, 16)
        self.hWnd = hWnd
        self.start()

    def start(self):
        """ Call the dll functions to lets us call NP_GetData.
          This calls the following functions in the give order:
            NP_GetSignature()
            NP_QueryVersion()
            NP_RegisterWindowHandle(windowHandle)
            NP_RequestData(data) # Where DataFields is a bitfield indicating what data we want in the NP_GetData field
            NP_RegisterProgramProfileId(profileId)
            NP_StopCursor()
            NP_StartDataTransmission()
        """
        logprint("NP_GetSignature says:")
        sig = self.NP_GetSignature()
        logprint("------------------")
        logprint(sig.AppSignature)
        logprint(sig.DllSignature)
        logprint("------------------")
        logprint()
        logprint("Calling NP_RegisterWindowHandle")
        self.NP_RegisterWindowHandle(self.hWnd)
        logprint("Calling NP_RequestData")
        self.NP_RequestData(119) # Request roll,pitch,yaw and x,y,z
        logprint("Calling NP_RegisterProgramProfileID")
        self.NP_RegisterProgramProfileID(self.trackir_profile_id)
        logprint("Calling NP_StopCursor")
        self.NP_StopCursor()
        logprint("Calling NP_StartDataTransmission")
        self.NP_StartDataTransmission()
    
    def stop(self):
        """ We no longer want to call NP_RequestData """
        logprint("Calling NP_StopDataTransmission")
        self.NP_StopDataTransmission()
        logprint("Calling NP_StartCursor")
        self.NP_StartCursor()
        logprint("Calling NP_UnregisterWindowHandle")
        self.NP_UnregisterWindowHandle()

    def NP_RegisterProgramProfileID(self, id: int) -> int:
        """Call NP_RegisterProgramProfileID in the Track IR dll to specify what program we are.
           There is a list of values that it recognizes here:

             https://github.com/ExtReMLapin/TrackIR_Research/blob/master/decrypted%20sgl.dat

           Presumably you are supposed to register with NaturalPoint and they give you can ID.

           Some interesting values:
             3750=Unity 64-bit
        """
        return self.NP_RegisterProgramProfileID_api(ctypes.c_ushort(id))

    def NP_RegisterWindowHandle(self, wnd):
        return self.NP_RegisterWindowHandle_api(wnd)

    def NP_UnregisterWindowHandle(self):
        return self.NP_UnregisterWindowHandle_api()

    def NP_RequestData(self, dataFields: int) -> int:
        """Call NP_RequestData in the Track IR dll to specify what data we want to receive.
           A useful value is 119 = x,y,z and roll,pitch,yaw
           And 65535 will return all data (i.e. with the raw, delta and smooth raw image position)

           For any other combination, add together the following combination of flags:

           Roll 1
           Pitch 2
           Yaw 4
           X 16
           Y 32
           Z 64

           // x, y, z from raw imager position
           RawX 128
           RawY 256
           RawZ 512

           // x, y, z deltas from raw imager position
           DeltaX 1024
           DeltaY 2048
           DeltaZ 4096

           // raw object position from imager
           SmoothX 8192
           SmoothY 16384
           SmoothZ 32768
        """
        return checkReturn(self.NP_RequestData_api(ctypes.c_ushort(dataFields)))
        
    def NP_StopCursor(self) -> int:
        """Call NP_StopCursor in the Track IR dll.
           I don't know what this does, but call it before calling NP_StartDataTransmission()
        """
        return checkReturn(self.NP_StopCursor_api())

    def NP_StartCursor(self) -> int:
        """Call NP_StartCursor in the Track IR dll.
           I don't know what this does, but presumably we call it after calling NP_StopDataTransmission()
        """
        return checkReturn(self.NP_StartCursor_api())
        
    def NP_StartDataTransmission(self) -> int:
        """Call NP_StartDataTransmission in the Track IR dll to actually start sending data to use with the 6dof information
        """
        return checkReturn(self.NP_StartDataTransmission_api())
    
    def NP_StopDataTransmission(self) -> int:
        """Call NP_StopDataTransmission in the Track IR dll to stop sending data to use with the 6dof information
        """
        return checkReturn(self.NP_StopDataTransmission_api())

    def NP_GetData(self) -> TrackIR_6DOF_Data:
        """Call NP_GetData in the Track IR dll to actually start sending data to use with the 6dof information
        """
        data = TrackIR_6DOF_Data()
        checkReturn(self.NP_GetData_api(ctypes.byref(data)))
        return data

    def NP_GetSignature(self) -> TrackIR_Signature_Data:
        """Call NP_GetData in the Track IR dll to get information about the DLL
        """
        sig = TrackIR_Signature_Data()
        checkReturn(self.NP_GetSignature_api(ctypes.byref(sig)))
        return sig
