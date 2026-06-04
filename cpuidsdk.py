import ctypes
import os
import sys

try:
    import psutil
except ImportError:
    psutil = None

# Define constants matching CPUID SDK
HWM_CLASS_CPU = 2
HWM_CLASS_DISPLAYADAPTER = 8

SENSOR_CLASS_TEMPERATURE = 8192
SENSOR_CLASS_FAN = 12288
SENSOR_CLASS_UTILIZATION = 57344

class CPUIDSDK:
    def __init__(self, dll_path=None):
        if dll_path is None:
            # Assume DLL is in the same directory as this file
            dir_path = os.path.dirname(os.path.abspath(__file__))
            dll_path = os.path.join(dir_path, "cpuidsdk64.dll")
        else:
            dir_path = os.path.dirname(os.path.abspath(dll_path))
            
        self.driver_dir = dir_path
        self.dll_name = os.path.basename(dll_path)
        
        try:
            self.dll = ctypes.CDLL(dll_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load CPUID SDK DLL: {e}")
            
        # Define QueryInterface signature
        self.dll.QueryInterface.argtypes = [ctypes.c_uint]
        self.dll.QueryInterface.restype = ctypes.c_void_p
        
        # Mapped function pointers obtained via QueryInterface
        self.ids = {
            "CreateInstance": 0x270A4E14,
            "DestroyInstance": 0x7310E621,
            "Init": 0x404E809D,
            "Close": 0x32EC65D8,
            "RefreshInformation": 0x1436286C,
            "GetDllVersion": 0xD7B1AF63,
            "GetNumberOfDevices": 0x143C2878,
            "GetDeviceClass": 0x388A7114,
            "GetDeviceName": 0x600EC01D,
            "GetNumberOfSensors": 0xCC3F987F,
            "GetSensorInfos": 0xD88BB117
        }
        
        self.funcs = {}
        for name, fid in self.ids.items():
            addr = self.dll.QueryInterface(fid)
            if addr:
                self.funcs[name] = addr
            else:
                raise RuntimeError(f"Failed to resolve function pointer for {name}")
                
        # Setup function prototypes
        self._setup_prototypes()
        self.hSDK = None

    def _setup_prototypes(self):
        # void_p CreateInstance()
        self.proto_create = ctypes.WINFUNCTYPE(ctypes.c_void_p)
        self.func_create = self.proto_create(self.funcs["CreateInstance"])
        
        # void DestroyInstance(void_p)
        self.proto_destroy = ctypes.WINFUNCTYPE(None, ctypes.c_void_p)
        self.func_destroy = self.proto_destroy(self.funcs["DestroyInstance"])
        
        # int Init(void_p, wchar_t*, wchar_t*, int, int*, int*)
        self.proto_init = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int)
        )
        self.func_init = self.proto_init(self.funcs["Init"])
        
        # ANSI fallback for Init
        self.proto_init_ansi = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int)
        )
        self.func_init_ansi = self.proto_init_ansi(self.funcs["Init"])
        
        # void Close(void_p)
        self.proto_close = ctypes.WINFUNCTYPE(None, ctypes.c_void_p)
        self.func_close = self.proto_close(self.funcs["Close"])
        
        # void RefreshInformation(void_p)
        self.proto_refresh = ctypes.WINFUNCTYPE(None, ctypes.c_void_p)
        self.func_refresh = self.proto_refresh(self.funcs["RefreshInformation"])
        
        # int GetNumberOfDevices(void_p)
        self.proto_num_devs = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
        self.func_num_devs = self.proto_num_devs(self.funcs["GetNumberOfDevices"])
        
        # int GetDeviceClass(void_p, int)
        self.proto_dev_class = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int)
        self.func_dev_class = self.proto_dev_class(self.funcs["GetDeviceClass"])
        
        # void_p GetDeviceName(void_p, int)
        self.proto_dev_name = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)
        self.func_dev_name = self.proto_dev_name(self.funcs["GetDeviceName"])
        
        # int GetNumberOfSensors(void_p, int, int)
        self.proto_num_sensors = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
        self.func_num_sensors = self.proto_num_sensors(self.funcs["GetNumberOfSensors"])
        
        # int GetSensorInfos(void_p, int, int, int, int*, void_p*, int*, float*, float*, float*)
        self.proto_sensor_info = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float)
        )
        self.func_sensor_info = self.proto_sensor_info(self.funcs["GetSensorInfos"])

    def open(self):
        if self.hSDK is not None:
            return True
            
        self.hSDK = self.func_create()
        if not self.hSDK:
            raise RuntimeError("Failed to create CPUID SDK instance.")
            
        err = ctypes.c_int(0)
        detail = ctypes.c_int(0)
        
        # Try Unicode Init first
        res = self.func_init(
            self.hSDK,
            self.driver_dir,
            self.dll_name,
            0x7FFFFFFF,
            ctypes.byref(err),
            ctypes.byref(detail)
        )
        
        if res == 0:
            # Try ANSI fallback
            res = self.func_init_ansi(
                self.hSDK,
                self.driver_dir.encode('ansi'),
                self.dll_name.encode('ansi'),
                0x7FFFFFFF,
                ctypes.byref(err),
                ctypes.byref(detail)
            )
            
        if res == 0:
            self.hSDK = None
            raise RuntimeError(f"Failed to initialize CPUID SDK. Error code: {err.value}, detail: {detail.value}. Note: CPUID SDK requires Administrator privileges to run.")
            
        return True

    def close(self):
        if self.hSDK:
            self.func_close(self.hSDK)
            self.func_destroy(self.hSDK)
            self.hSDK = None

    def refresh(self):
        if self.hSDK:
            self.func_refresh(self.hSDK)

    def get_number_of_devices(self):
        if not self.hSDK:
            return 0
        return self.func_num_devs(self.hSDK)

    def get_device_class(self, dev_idx):
        if not self.hSDK:
            return 0
        return self.func_dev_class(self.hSDK, dev_idx)

    def get_device_name(self, dev_idx):
        if not self.hSDK:
            return ""
        ptr = self.func_dev_name(self.hSDK, dev_idx)
        if not ptr:
            return ""
        # Try to read as ANSI first, fall back to Unicode
        try:
            return ctypes.string_at(ptr).decode('ansi', errors='ignore')
        except:
            try:
                return ctypes.wstring_at(ptr)
            except:
                return ""

    def get_number_of_sensors(self, dev_idx, sensor_class):
        if not self.hSDK:
            return 0
        return self.func_num_sensors(self.hSDK, dev_idx, sensor_class)

    def get_sensor_infos(self, dev_idx, sensor_idx, sensor_class):
        if not self.hSDK:
            return None
            
        sensor_id = ctypes.c_int(0)
        name_ptr = ctypes.c_void_p(0)
        sensor_type = ctypes.c_int(0)
        value = ctypes.c_float(0.0)
        min_val = ctypes.c_float(0.0)
        max_val = ctypes.c_float(0.0)
        
        res = self.func_sensor_info(
            self.hSDK,
            dev_idx,
            sensor_idx,
            sensor_class,
            ctypes.byref(sensor_id),
            ctypes.byref(name_ptr),
            ctypes.byref(sensor_type),
            ctypes.byref(value),
            ctypes.byref(min_val),
            ctypes.byref(max_val)
        )
        
        if res == 0:
            return None
            
        # Parse name string as ANSI first
        name = ""
        if name_ptr.value:
            try:
                name = ctypes.string_at(name_ptr).decode('ansi', errors='ignore')
            except:
                try:
                    name = ctypes.wstring_at(name_ptr)
                except:
                    pass
                    
        return {
            "id": sensor_id.value,
            "name": name,
            "type": sensor_type.value,
            "value": value.value,
            "min": min_val.value,
            "max": max_val.value
        }

# ==================== AMD ADL Fallback Definitions ====================
class ADLAdapterInfo(ctypes.Structure):
    _fields_ = [
        ("iSize", ctypes.c_int),
        ("iAdapterIndex", ctypes.c_int),
        ("strUDID", ctypes.c_char * 256),
        ("iBusNumber", ctypes.c_int),
        ("iDeviceNumber", ctypes.c_int),
        ("iFunctionNumber", ctypes.c_int),
        ("iVendorID", ctypes.c_int),
        ("strAdapterName", ctypes.c_char * 256),
        ("strDisplayName", ctypes.c_char * 256),
        ("iPresent", ctypes.c_int),
        ("iExist", ctypes.c_int),
        ("strDriverPath", ctypes.c_char * 256),
        ("strDriverPathExt", ctypes.c_char * 256),
        ("strPNPID", ctypes.c_char * 256),
        ("iBusCardIndex", ctypes.c_int)
    ]

class ADLSingleSensorData(ctypes.Structure):
    _fields_ = [
        ("supported", ctypes.c_int),
        ("value", ctypes.c_int)
    ]

class ADLPMLogDataOutput(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_int),
        ("sensors", ADLSingleSensorData * 256)
    ]

ADL_MAIN_MALLOC_CALLBACK = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_int)

@ADL_MAIN_MALLOC_CALLBACK
def adl_alloc(size):
    return ctypes.windll.kernel32.LocalAlloc(0x40, size)

class AMDADLTelemetry:
    def __init__(self):
        self.adl = None
        self.context = None
        self.adapter_index = -1
        self._init_adl()

    def _init_adl(self):
        try:
            try:
                self.adl = ctypes.WinDLL("atiadlxx.dll")
            except:
                self.adl = ctypes.WinDLL("atiadlxy.dll")
                
            self.adl.ADL2_Main_Control_Create.argtypes = [ADL_MAIN_MALLOC_CALLBACK, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
            self.adl.ADL2_Main_Control_Create.restype = ctypes.c_int
            
            self.adl.ADL2_Main_Control_Destroy.argtypes = [ctypes.c_void_p]
            self.adl.ADL2_Main_Control_Destroy.restype = ctypes.c_int
            
            self.adl.ADL2_Adapter_NumberOfAdapters_Get.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
            self.adl.ADL2_Adapter_NumberOfAdapters_Get.restype = ctypes.c_int
            
            self.adl.ADL2_Adapter_AdapterInfo_Get.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
            self.adl.ADL2_Adapter_AdapterInfo_Get.restype = ctypes.c_int

            self.adl.ADL2_New_QueryPMLogData_Get.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ADLPMLogDataOutput)]
            self.adl.ADL2_New_QueryPMLogData_Get.restype = ctypes.c_int

            self.context = ctypes.c_void_p()
            res = self.adl.ADL2_Main_Control_Create(adl_alloc, 1, ctypes.byref(self.context))
            if res != 0:
                self.adl = None
                self.context = None
                return

            num_adapters = ctypes.c_int(0)
            self.adl.ADL2_Adapter_NumberOfAdapters_Get(self.context, ctypes.byref(num_adapters))
            if num_adapters.value > 0:
                adapters = (ADLAdapterInfo * num_adapters.value)()
                info_size = ctypes.sizeof(adapters)
                
                self.adl.ADL2_Adapter_AdapterInfo_Get.argtypes = [ctypes.c_void_p, ctypes.POINTER(ADLAdapterInfo * num_adapters.value), ctypes.c_int]
                res_info = self.adl.ADL2_Adapter_AdapterInfo_Get(self.context, ctypes.byref(adapters), info_size)
                if res_info == 0:
                    for idx in range(num_adapters.value):
                        adapter = adapters[idx]
                        vendor_id = adapter.iVendorID
                        present = adapter.iPresent
                        if (vendor_id in (0x1002, 1002, 0x3ea, 4098)) and present == 1:
                            self.adapter_index = adapter.iAdapterIndex
                            break
        except Exception:
            self.close()

    def get_gpu_temp(self):
        if not self.adl or not self.context or self.adapter_index == -1:
            return None
        try:
            data_output = ADLPMLogDataOutput()
            data_output.size = ctypes.sizeof(ADLPMLogDataOutput)
            res = self.adl.ADL2_New_QueryPMLogData_Get(self.context, self.adapter_index, ctypes.byref(data_output))
            if res == 0:
                # Sensor 8 is Edge temperature
                if data_output.sensors[8].supported == 1:
                    return data_output.sensors[8].value
                # Fallback to Hotspot (sensor 27) if edge isn't supported
                if data_output.sensors[27].supported == 1:
                    return data_output.sensors[27].value
        except Exception:
            pass
        return None

    def get_gpu_util(self):
        if not self.adl or not self.context or self.adapter_index == -1:
            return None
        try:
            data_output = ADLPMLogDataOutput()
            data_output.size = ctypes.sizeof(ADLPMLogDataOutput)
            res = self.adl.ADL2_New_QueryPMLogData_Get(self.context, self.adapter_index, ctypes.byref(data_output))
            if res == 0:
                # Sensor 19 is PMLOG_INFO_ACTIVITY_GFX
                if data_output.sensors[19].supported == 1:
                    return data_output.sensors[19].value
        except Exception:
            pass
        return None

    def close(self):
        if self.adl and self.context:
            try:
                self.adl.ADL2_Main_Control_Destroy(self.context)
            except Exception:
                pass
        self.adl = None
        self.context = None
        self.adapter_index = -1
# ======================================================================

class CPUIDTelemetry:
    def __init__(self, sdk):
        self.sdk = sdk
        self.adl_fallback = AMDADLTelemetry()

    def close(self):
        if hasattr(self, "adl_fallback"):
            self.adl_fallback.close()

    def read_all(self, refresh=True):
        data = {
            "cpu_temp": None,
            "gpu_temp": None,
            "cpu_util": None,
            "gpu_util": None,
            "fan_rpm": None
        }
        
        # 1. Refresh SDK
        if refresh:
            self.sdk.refresh()
        
        # 2. Loop through all devices and sensors
        num_devs = self.sdk.get_number_of_devices()
        
        # Collect candidate values
        cpu_temps = []
        gpu_temps = []
        cpu_utils = []
        gpu_utils = []
        fan_rpms = []
        
        for dev_idx in range(num_devs):
            dev_class = self.sdk.get_device_class(dev_idx)
            dev_name = self.sdk.get_device_name(dev_idx).lower()
            
            # Check if this device is CPU or GPU
            is_cpu = (dev_class in (2, 4)) or ("cpu" in dev_name) or ("ryzen" in dev_name) or ("intel" in dev_name)
            is_gpu = (dev_class in (8, 32)) or ("gpu" in dev_name) or ("radeon" in dev_name) or ("nvidia" in dev_name) or ("geforce" in dev_name)
            
            # Check temperatures (class 8192 / 0x2000)
            num_temps = self.sdk.get_number_of_sensors(dev_idx, SENSOR_CLASS_TEMPERATURE)
            for i in range(num_temps):
                info = self.sdk.get_sensor_infos(dev_idx, i, SENSOR_CLASS_TEMPERATURE)
                if info and info["value"] < 3e38: # check if defined (MAX_FLOAT check)
                    name_lower = info["name"].lower()
                    val = info["value"]
                    if is_cpu:
                        # CPU Temperature candidates
                        if "package" in name_lower or "core" in name_lower or "#" in name_lower:
                            cpu_temps.append(val)
                    elif is_gpu:
                        # GPU Temperature candidates
                        if "gpu" in name_lower or "temperature" in name_lower or "temp" in name_lower:
                            gpu_temps.append(val)
                            
            # Check utilization (class 57344 / 0xE000)
            num_utils = self.sdk.get_number_of_sensors(dev_idx, SENSOR_CLASS_UTILIZATION)
            for i in range(num_utils):
                info = self.sdk.get_sensor_infos(dev_idx, i, SENSOR_CLASS_UTILIZATION)
                if info and info["value"] < 3e38:
                    name_lower = info["name"].lower()
                    val = info["value"]
                    if is_cpu:
                        if "package" in name_lower or "total" in name_lower or "#" in name_lower or "cpu" in name_lower or "processor" in name_lower:
                            cpu_utils.append(val)
                    elif is_gpu:
                        if "gpu" in name_lower or "utilization" in name_lower or "util" in name_lower or "d3d" in name_lower:
                            gpu_utils.append(val)
                            
            # Check fans (class 12288 / 0x3000)
            num_fans = self.sdk.get_number_of_sensors(dev_idx, SENSOR_CLASS_FAN)
            for i in range(num_fans):
                info = self.sdk.get_sensor_infos(dev_idx, i, SENSOR_CLASS_FAN)
                if info and info["value"] < 3e38 and info["value"] > 0:
                    fan_rpms.append(info["value"])
                    
        # Apply select strategies
        if cpu_temps:
            data["cpu_temp"] = int(round(cpu_temps[0]))
            
        if gpu_temps and gpu_temps[0] > 0:
            data["gpu_temp"] = int(round(gpu_temps[0]))
        else:
            adl_temp = self.adl_fallback.get_gpu_temp()
            if adl_temp is not None and adl_temp > 0:
                data["gpu_temp"] = adl_temp
            
        # CPU/GPU Utilization: pick package/total utilization or the first candidate
        # CPU fallback using psutil
        if psutil is not None:
            try:
                data["cpu_util"] = int(round(psutil.cpu_percent(interval=None)))
            except:
                if cpu_utils:
                    data["cpu_util"] = int(round(cpu_utils[0]))
        else:
            if cpu_utils:
                data["cpu_util"] = int(round(cpu_utils[0]))
                
        # GPU fallback using AMD ADL
        adl_util = self.adl_fallback.get_gpu_util()
        if adl_util is not None:
            data["gpu_util"] = adl_util
        elif gpu_utils:
            data["gpu_util"] = int(round(gpu_utils[0]))
            
        # Fan RPM: pick the first candidate
        if fan_rpms:
            data["fan_rpm"] = int(round(fan_rpms[0]))
            
        return data
