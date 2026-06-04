import time
import sys
import ctypes
import os
import logging
import win32gui
import win32con

# Add the current directory to path so we can import local modules when run from elsewhere
dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

from cpuidsdk import CPUIDSDK, CPUIDTelemetry
from layout import show1, show4, show5
from hid import HIDDevice

# Configure logging
log_file = os.path.join(dir_path, "driver.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PCMonitorDriver")

# Global state for handling Windows events and preventing garbage collection
hid_device = None
SHUTTING_DOWN = False
SUSPENDED = False

def wnd_proc(hwnd, msg, wparam, lparam):
    global SHUTTING_DOWN, SUSPENDED, hid_device
    
    if msg in (win32con.WM_QUERYENDSESSION, win32con.WM_ENDSESSION):
        logger.info(f"System shutdown/logoff detected (msg: {msg}, wparam: {wparam}). Setting shutdown flag...")
        SHUTTING_DOWN = True
        
        # Try to blank display immediately in the callback to ensure it happens before termination
        if hid_device:
            try:
                report = bytearray(64)
                report[2] = 2  # Mode ID
                hid_device.write(report)
                logger.info("Display blanked during shutdown callback.")
            except Exception as e:
                logger.error(f"Failed to blank display on shutdown in callback: {e}")
        return True
        
    elif msg == win32con.WM_POWERBROADCAST:
        if wparam == 4:  # PBT_APMSUSPEND
            logger.info("System entering sleep/suspend. Blanking display...")
            SUSPENDED = True
            if hid_device:
                try:
                    report = bytearray(64)
                    report[2] = 2  # Mode ID
                    hid_device.write(report)
                    logger.info("Display blanked during suspend callback.")
                except Exception as e:
                    logger.error(f"Failed to blank display on suspend: {e}")
            return True
            
        elif wparam in (7, 0x12):  # PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC
            logger.info("System resuming from sleep/suspend. Resuming display updates...")
            SUSPENDED = False
            return True
            
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

# ==================== CONFIGURATION ====================
# DISPLAY_MODE options:
# 0 = Celsius mode (displays CPU/GPU temperatures in Celsius)
# 1 = Fahrenheit mode (displays CPU/GPU temperatures in Fahrenheit)
# 2 = Utilization mode (displays CPU/GPU utilization percentages)
# "rotate" = Rotate through modes 0, 1, 2 every ROTATE_INTERVAL seconds
# "rotate_c_u" = Rotate between Celsius (0) and Utilization (2) only
DISPLAY_MODE = "rotate_c_u"
ROTATE_INTERVAL = 6.0  # seconds

# Update interval for fetching telemetry and updating the display
UPDATE_INTERVAL = 0.2  # seconds

# USB HID Device configuration for darkFlash L280M
VENDOR_ID = 0x5131
PRODUCT_ID = 0x2007
# =======================================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def dump_sensors(sdk, path):
    try:
        sdk.refresh()
        num_devs = sdk.get_number_of_devices()
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Number of devices: {num_devs}\n\n")
            sensor_classes = {
                "VOLTAGE": 1024,
                "TEMPERATURE": 8192,
                "FAN": 12288,
                "CLOCK": 16384,
                "CURRENT": 20480,
                "LEVEL": 24576,
                "POWER": 28672,
                "ENERGY": 40960,
                "PWM": 49152,
                "UTILIZATION": 57344,
                "UNKNOWN_F000": 61440
            }
            for dev_idx in range(num_devs):
                dev_class = sdk.get_device_class(dev_idx)
                dev_name = sdk.get_device_name(dev_idx)
                f.write(f"Device {dev_idx}: '{dev_name}' (Class: {dev_class})\n")
                for sc_name, sc_val in sensor_classes.items():
                    num_sensors = sdk.get_number_of_sensors(dev_idx, sc_val)
                    if num_sensors > 0:
                        f.write(f"  Sensor Class {sc_name} ({sc_val}): {num_sensors} sensors\n")
                        for s_idx in range(num_sensors):
                            info = sdk.get_sensor_infos(dev_idx, s_idx, sc_val)
                            if info:
                                f.write(f"    Sensor {s_idx}: ID={info['id']}, Name='{info['name']}', Type={info['type']}, Value={info['value']}, Min={info['min']}, Max={info['max']}\n")
                f.write("\n" + "="*50 + "\n\n")
        logger.info(f"Sensor dump written to {path}")
    except Exception as e:
        logger.error(f"Failed to dump sensors: {e}")

def main():
    logger.info("Starting darkFlash L280M PC Monitor Driver Daemon...")
    
    if not is_admin():
        logger.error("This script must be run as Administrator.")
        logger.error("CPUID SDK requires low-level kernel driver access (cpuid152.sys),")
        logger.error("which requires elevated privileges to load and query.")
        sys.exit(1)
        
    # 1. Initialize CPUID SDK
    logger.info("Initializing CPUID SDK...")
    try:
        sdk = CPUIDSDK()
        sdk.open()
        telemetry_reader = CPUIDTelemetry(sdk)
        logger.info("CPUID SDK initialized successfully.")
        
        # Dump sensors for diagnostics
        dump_path = os.path.join(dir_path, "sensors_dump.txt")
        dump_sensors(sdk, dump_path)
        
    except Exception as e:
        logger.error(f"Failed to initialize CPUID SDK: {e}")
        sys.exit(1)

    global hid_device
    # 2. Initialize HID Device
    logger.info(f"Scanning for HID device (VID: 0x{VENDOR_ID:04X}, PID: 0x{PRODUCT_ID:04X})...")
    hid_device = HIDDevice(VENDOR_ID, PRODUCT_ID)
    
    # Register a hidden window to listen for Windows shutdown/logoff/suspend events
    try:
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = wnd_proc
        wc.lpszClassName = "PCMonitorShutdownListener"
        try:
            class_atom = win32gui.RegisterClass(wc)
        except Exception as e:
            class_atom = "PCMonitorShutdownListener"
        hwnd = win32gui.CreateWindow(
            class_atom,
            "PCMonitorShutdownListener",
            0, 0, 0, 0, 0,
            0, 0, 0, None
        )
        logger.info(f"Shutdown/Suspend listener window created successfully (hwnd: {hwnd}).")
    except Exception as e:
        logger.warning(f"Failed to register/create shutdown listener window: {e}")
        
    # 3. Main Loop
    counter = 0
    active_mode = 0 if DISPLAY_MODE in ("rotate", "rotate_c_u") else int(DISPLAY_MODE)
    last_rotation_time = time.time()
    last_refresh_time = 0.0
    
    # Moving average histories (1-second window / 0.2-second refresh = 5 samples)
    cpu_temp_history = []
    gpu_temp_history = []
    cpu_util_history = []
    gpu_util_history = []
    fan_rpm_history = []
    
    try:
        while True:
            # Pump waiting window messages to process shutdown/suspend/resume events
            try:
                win32gui.PumpWaitingMessages()
            except Exception as e:
                pass
                
            if SHUTTING_DOWN:
                logger.info("Breaking main loop due to shutdown flag.")
                break
                
            if SUSPENDED:
                time.sleep(0.5)
                continue
                
            # Check rotation
            if DISPLAY_MODE == "rotate":
                if time.time() - last_rotation_time >= ROTATE_INTERVAL:
                    active_mode = (active_mode + 1) % 3
                    last_rotation_time = time.time()
                    logger.info(f"Display Mode rotated to: {active_mode}")
            elif DISPLAY_MODE == "rotate_c_u":
                if time.time() - last_rotation_time >= ROTATE_INTERVAL:
                    active_mode = 2 if active_mode == 0 else 0
                    last_rotation_time = time.time()
                    logger.info(f"Display Mode rotated to: {active_mode}")
            else:
                active_mode = int(DISPLAY_MODE)
                
            # Attempt to connect to HID if not connected
            if hid_device.handle == -1:
                logger.info("Connecting to display USB HID...")
                if hid_device.open():
                    logger.info(f"Connected to display at path: {hid_device.path}")
                else:
                    logger.warning("Display not found. Will retry...")
                    time.sleep(5)
                    continue
            
            # Fetch telemetry
            try:
                now = time.time()
                do_refresh = (now - last_refresh_time >= 1.0)
                if do_refresh:
                    last_refresh_time = now
                data = telemetry_reader.read_all(refresh=do_refresh)
                if do_refresh:
                    logger.info(f"Raw telemetry read: {data}")
            except Exception as e:
                logger.warning(f"Failed to read CPUID telemetry: {e}")
                data = {}
                
            # Update history and calculate moving averages
            def update_history(history, val):
                if val is not None:
                    history.append(val)
                if len(history) > 5:
                    history.pop(0)
                return int(round(sum(history) / len(history))) if history else 0

            cpu_temp = update_history(cpu_temp_history, data.get("cpu_temp"))
            gpu_temp = update_history(gpu_temp_history, data.get("gpu_temp"))
            cpu_util = update_history(cpu_util_history, data.get("cpu_util"))
            gpu_util = update_history(gpu_util_history, data.get("gpu_util"))
            fan_rpm = update_history(fan_rpm_history, data.get("fan_rpm"))
            
            # Format display values based on active mode
            if active_mode == 0:
                # Celsius: left = CPU temp, right = GPU temp
                left_val = cpu_temp
                right_val = gpu_temp
            elif active_mode == 1:
                # Fahrenheit: left = CPU temp in F, right = GPU temp in F
                left_val = cpu_temp * 9 // 5 + 32
                right_val = gpu_temp * 9 // 5 + 32
            else:
                # Utilization %: left = CPU %, right = GPU %
                left_val = cpu_util
                right_val = gpu_util
                
            # Compute segment buffers
            try:
                chip1_buf = show1(cpu_temp, gpu_temp, cpu_util, fan_rpm)
                chip2_digits_buf = show4(left_val, right_val, active_mode)
                chip2_buf = show5(cpu_util, gpu_util, chip2_digits_buf)
            except Exception as e:
                logger.warning(f"Failed to format segment buffers: {e}")
                chip1_buf = [0] * 16
                chip2_buf = [0] * 16
                
            # Formulate 64-byte payload
            report = bytearray(64)
            
            # Byte 0: Counter
            report[0] = counter & 0xFF
            counter += 1
            
            # Byte 2: Mode ID
            report[2] = 2
            
            # Bytes 4-23: BCD parameters
            report[5] = (cpu_temp // 100) % 10
            report[6] = (cpu_temp // 10) % 10
            report[7] = cpu_temp % 10
            
            report[9] = (gpu_temp // 100) % 10
            report[10] = (gpu_temp // 10) % 10
            report[11] = gpu_temp % 10
            
            report[13] = (cpu_util // 100) % 10
            report[14] = (cpu_util // 10) % 10
            report[15] = cpu_util % 10
            
            report[16] = (fan_rpm // 1000) % 10
            report[17] = (fan_rpm // 100) % 10
            report[18] = (fan_rpm // 10) % 10
            report[19] = fan_rpm % 10
            
            report[20] = 0
            report[21] = 0
            report[22] = 0
            report[23] = 0

            
            # Bytes 24-39: Chip 1 segments (16 bytes)
            report[24:40] = chip1_buf
            
            # Bytes 40-55: Chip 2 segments (16 bytes)
            report[40:56] = chip2_buf
            
            # Send payload to device
            success = False
            try:
                success = hid_device.write(report)
            except Exception as e:
                logger.error(f"Write error: {e}")
                
            if not success:
                logger.error("Failed to write to display HID. Disconnecting handle...")
                hid_device.close()
                
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Exiting daemon...")
    finally:
        logger.info("Cleaning up handles...")
        
        # Send a blank report to turn off all segments before closing the handle
        try:
            logger.info("Blanking display segments...")
            report = bytearray(64)
            report[2] = 2  # Mode ID
            hid_device.write(report)
        except Exception as e:
            logger.warning(f"Failed to blank display segments: {e}")
            
        hid_device.close()
        if 'telemetry_reader' in locals():
            try:
                telemetry_reader.close()
            except Exception as e:
                logger.error(f"Error closing telemetry reader: {e}")
        sdk.close()
        logger.info("Finished cleanup. Goodbye.")

if __name__ == "__main__":
    main()
