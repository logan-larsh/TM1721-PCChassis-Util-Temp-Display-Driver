# Open PC Monitor Display Driver

A lightweight, offline, self-contained Python background driver for generic PC chassis front panel displays (such as the **darkFlash L280M** and other OEM chassis screens) driven by **Titan Micro TM1721** LED controllers and USB HID microcontrollers (Vendor ID `0x5131`, Product ID `0x2007`).

This driver completely replaces the official manufacturer software with a highly optimized daemon that runs silently in the background, consumes minimal CPU resources, and supports clean OS integration.

---

## Features

- **Decoupled Telemetry Refresh**: Decouples the display refresh rate (0.2s) from the heavy CPUID SDK refresh rate (1.0s). This provides a healthy time window for correct CPU/GPU utilization calculations, drastically reduces background CPU usage, and prevents stuck telemetry.
- **Power & Session Event Listeners**: Hidden Win32 event listeners intercept system events to safely shut down the display:
  - Blanks the screen immediately during **Shutdown**, **Restart**, or **Logoff** so the display doesn't stay frozen on when the PC is off.
  - Blanks the screen and pauses telemetry queries when the system enters **Sleep / Hibernate** (`PBT_APMSUSPEND`), and automatically resumes updates when the system wakes.
- **Dynamic Utilization Fallbacks**: 
  - **CPU Utilization**: Queries system times directly via `psutil` for highly responsive, 100% accurate live usage stats.
  - **GPU Utilization**: Integrates directly with the AMD display driver (`atiadlxx.dll`) Performance Metrics Log (Sensor ID 19) to fetch live GPU activity on modern architectures (such as the Radeon RX 9000 series) where generic drivers fail.
- **AMD ADL GPU Temperature Fallback**: Automatically queries AMD Performance Metrics Log (Sensor ID 8/27) to fetch Radeon core temperatures when standard SDK queries fail.

---

## Repository Files

- `main.py`: The background runner daemon script. Implements the telemetry reader, layout segment formatting, HID packet writer, and Win32 event listeners.
- `cpuidsdk.py`: Core telemetry module wrapping `cpuidsdk64.dll` and implementing the AMD ADL PMLog fallback client.
- `layout.py`: Digit segment translation and screen layout mapping for Chip 1 and Chip 2 (Titan Micro TM1721 digit representations).
- `hid.py`: Windows HID device scanner using `setupapi.dll` and `hid.dll` via `ctypes`.
- `blank.py`: A simple standalone utility to manually blank (turn off) the display panel.
- `install.ps1`: Administrative PowerShell helper script to install, uninstall, start, stop, or view logs for the background Scheduled Task.
- `cpuidsdk64.dll`: CPUID SDK 64-bit DLL (safe, local copy extracted from the OEM installer used to communicate with the low-level kernel driver).
- `parsed_segments.json`: TM1721 segment translation tables.

---

## Prerequisites

This driver is designed for **Windows (64-bit)** and requires Python 3. You must install the following dependencies:

```bash
pip install pywin32 psutil
```

---

## Installation & Setup

1. Open PowerShell as **Administrator**.
2. Navigate to the folder containing these files.
3. Run the installer script:
   ```powershell
   .\install.ps1
   ```
4. Choose **Option 1** (`Install & Start Background Task`).

This registers a Scheduled Task (`darkFlash_PCMonitor_Driver`) that runs elevated under the current logged-on user. The task has been configured with high priority, meaning it will launch **instantly** at logon without the standard Windows startup delays.

### Stopping or Uninstalling
To stop the driver or remove it from the Windows Scheduled Tasks registry, simply run `.\install.ps1` as Administrator again and choose the corresponding option, or run:
```powershell
.\install.ps1 -Action Stop
.\install.ps1 -Action Uninstall
```

---

## Diagnostics & Logs

The driver writes log statements to `driver.log` in its local directory. To view live logs, run option `5` in `install.ps1` or run:
```powershell
.\install.ps1 -Action Logs
```

---

## License

This project is open-source. Feel free to modify and share it to add support for other chassis brands and layout configs!
