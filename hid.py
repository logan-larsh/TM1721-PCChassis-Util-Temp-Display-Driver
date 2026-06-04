import ctypes
from ctypes import wintypes
import struct

# GUID structure
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8)
    ]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p)
    ]

class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]

# Win32 Constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1

# DLLs
setupapi = ctypes.WinDLL("setupapi.dll")
hid = ctypes.WinDLL("hid.dll")
kernel32 = ctypes.WinDLL("kernel32.dll")

# Setup Win32 function signatures for 64-bit safety
setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_ulong]

setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]

setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]

setupapi.SetupDiDestroyDeviceInfoList.restype = wintypes.BOOL
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]

hid.HidD_GetHidGuid.restype = None
hid.HidD_GetHidGuid.argtypes = [ctypes.c_void_p]

hid.HidD_GetAttributes.restype = wintypes.BOOL
hid.HidD_GetAttributes.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

kernel32.CreateFileW.restype = ctypes.c_void_p
kernel32.CreateFileW.argtypes = [ctypes.c_wchar_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

kernel32.WriteFile.restype = wintypes.BOOL
kernel32.WriteFile.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p, ctypes.c_void_p]

def find_device_path(vendor_id, product_id):
    """
    Scans Windows setup API for HID devices matching vendor_id and product_id.
    Returns the device path as a string, or None if not found.
    """
    guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(guid))
    
    # Get all device interfaces for HID class
    # DIGCF_PRESENT = 2, DIGCF_DEVICEINTERFACE = 0x10
    h_dev_info = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(guid),
        None,
        None,
        0x00000002 | 0x00000010
    )
    if h_dev_info == INVALID_HANDLE_VALUE or h_dev_info == 0xFFFFFFFFFFFFFFFF or not h_dev_info:
        return None
        
    try:
        interface_data = SP_DEVICE_INTERFACE_DATA()
        interface_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
        
        index = 0
        while setupapi.SetupDiEnumDeviceInterfaces(
            h_dev_info,
            None,
            ctypes.byref(guid),
            index,
            ctypes.byref(interface_data)
        ):
            index += 1
            
            # Query size first
            req_size = wintypes.DWORD(0)
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                h_dev_info,
                ctypes.byref(interface_data),
                None,
                0,
                ctypes.byref(req_size),
                None
            )
            
            if req_size.value == 0:
                continue
                
            # Allocate detail buffer
            # cbSize must be 8 on 64-bit systems, 6 on 32-bit systems (due to packing)
            cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
            buf = ctypes.create_string_buffer(req_size.value)
            struct.pack_into("I", buf, 0, cb_size)
            
            if setupapi.SetupDiGetDeviceInterfaceDetailW(
                h_dev_info,
                ctypes.byref(interface_data),
                buf,
                req_size.value, # pass value!
                None,
                None
            ):
                # DevicePath is a null-terminated wchar string starting at offset 4
                device_path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
                
                # Check attributes without write/read access to prevent locking active devices
                h_dev = kernel32.CreateFileW(
                    device_path,
                    0,  # 0 desired access allows querying info without locking
                    FILE_SHARE_READ | FILE_SHARE_WRITE,
                    None,
                    OPEN_EXISTING,
                    0,
                    None
                )
                if h_dev and h_dev != INVALID_HANDLE_VALUE and h_dev != 0xFFFFFFFFFFFFFFFF:
                    try:
                        attrs = HIDD_ATTRIBUTES()
                        attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
                        if hid.HidD_GetAttributes(h_dev, ctypes.byref(attrs)):
                            if attrs.VendorID == vendor_id and attrs.ProductID == product_id:
                                return device_path
                    finally:
                        kernel32.CloseHandle(h_dev)
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(h_dev_info)
        
    return None


class HIDDevice:
    def __init__(self, vendor_id, product_id):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.handle = INVALID_HANDLE_VALUE
        self.path = None

    def open(self):
        self.close()
        self.path = find_device_path(self.vendor_id, self.product_id)
        if not self.path:
            return False
            
        self.handle = kernel32.CreateFileW(
            self.path,
            GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )
        return self.handle and self.handle != INVALID_HANDLE_VALUE and self.handle != 0xFFFFFFFFFFFFFFFF

    def close(self):
        if self.handle and self.handle != INVALID_HANDLE_VALUE and self.handle != 0xFFFFFFFFFFFFFFFF:
            kernel32.CloseHandle(self.handle)
        self.handle = INVALID_HANDLE_VALUE
        self.path = None

    def write(self, data):
        """
        Writes a 64-byte payload. Prepends Report ID 0.
        Returns True if successful, False otherwise.
        """
        if not self.handle or self.handle == INVALID_HANDLE_VALUE or self.handle == 0xFFFFFFFFFFFFFFFF:
            return False
            
        if len(data) != 64:
            raise ValueError("Payload must be exactly 64 bytes.")
            
        # Prepends Report ID 0. Windows HID expects the first byte to be the Report ID.
        report_buf = bytearray([0]) + bytearray(data)
        bytes_written = wintypes.DWORD(0)
        
        # WriteFile signature:
        # BOOL WriteFile(HANDLE hFile, LPCVOID lpBuffer, DWORD nNumberOfBytesToWrite, LPDWORD lpNumberOfBytesWritten, LPOVERLAPPED lpOverlapped)
        res = kernel32.WriteFile(
            self.handle,
            (ctypes.c_char * len(report_buf)).from_buffer(report_buf),
            len(report_buf),
            ctypes.byref(bytes_written),
            None
        )
        return bool(res) and bytes_written.value == len(report_buf)
