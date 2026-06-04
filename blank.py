import sys
import os

# Add local path to import hid
dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

from hid import HIDDevice

def main():
    # USB HID Device configuration for darkFlash L280M
    VENDOR_ID = 0x5131
    PRODUCT_ID = 0x2007
    device = HIDDevice(VENDOR_ID, PRODUCT_ID)
    if device.open():
        report = bytearray(64)
        report[2] = 2  # Mode ID
        # Bytes 4-23 are BCD parameters, set to 0
        # Bytes 24-55 are segment outputs, set to 0
        device.write(report)
        device.close()
        print("Screen blanked successfully.")
    else:
        print("Display device not found or could not be opened.")

if __name__ == "__main__":
    main()
