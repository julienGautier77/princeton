import os
import ctypes

DONT_RESOLVE_DLL_REFERENCES         = 0x00000001
LOAD_LIBRARY_AS_DATAFILE            = 0x00000002
LOAD_WITH_ALTERED_SEARCH_PATH       = 0x00000008
LOAD_IGNORE_CODE_AUTHZ_LEVEL        = 0x00000010  # NT 6.1
LOAD_LIBRARY_AS_IMAGE_RESOURCE      = 0x00000020  # NT 6.0
LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE  = 0x00000040  # NT 6.0

# These cannot be combined with LOAD_WITH_ALTERED_SEARCH_PATH.
# Install update KB2533623 for NT 6.0 & 6.1.
LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR    = 0x00000100
LOAD_LIBRARY_SEARCH_APPLICATION_DIR = 0x00000200
LOAD_LIBRARY_SEARCH_USER_DIRS       = 0x00000400
LOAD_LIBRARY_SEARCH_SYSTEM32        = 0x00000800
LOAD_LIBRARY_SEARCH_DEFAULT_DIRS    = 0x00001000


if os.name == 'nt':
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    def check_bool(result, func, args):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())
        return args

    kernel32.LoadLibraryExW.errcheck = check_bool
    kernel32.LoadLibraryExW.restype = wintypes.HMODULE
    kernel32.LoadLibraryExW.argtypes = (wintypes.LPCWSTR,
                                        wintypes.HANDLE,
                                        wintypes.DWORD)

class CDLLEx(ctypes.CDLL):
    def __init__(self, name, mode=0, handle=None, 
                 use_errno=True, use_last_error=False):
        if os.name == 'nt' and handle is None:
            handle = kernel32.LoadLibraryExW(name, None, mode)
        super(CDLLEx, self).__init__(name, mode, handle,
                                     use_errno, use_last_error)

class WinDLLEx(ctypes.WinDLL):
    def __init__(self, name, mode=0, handle=None, 
                 use_errno=False, use_last_error=True):
        if os.name == 'nt' and handle is None:
            handle = kernel32.LoadLibraryExW(name, None, mode)
        super(WinDLLEx, self).__init__(name, mode, handle,
                                       use_errno, use_last_error)

pi_path = "C:\\Program Files\\Princeton Instruments\\PICam\\Runtime"
#lib = WinDLLEx(os.path.join(pi_path, 'Picam32.dll'), 
#              LOAD_WITH_ALTERED_SEARCH_PATH)

import os
#path_dll = r"C:/Program Files/Princeton Instruments/PICam/Runtime"
#os.environ['PATH'] = path_dll + os.pathsep + os.environ['PATH']

#os.chdir(pi_path)
#lib = ctypes.windll.LoadLibrary("Piac32.dll")
lib = ctypes.windll.LoadLibrary("Picam32.dll")
#
#
#
#import win32api, win32con
#
##print(ctypes.windll.kernell32.)
#
##dll_name = os.path.join(pi_path, "Picam32.dll")
#dll_name = "Picam32.dll"
#dll_handle = win32api.LoadLibraryEx(dll_name, 0, win32con.LOAD_WITH_ALTERED_SEARCH_PATH)
#ctypes.WinDLL(dll_name, handle=dll_handle)




                        
                        
                        
                        