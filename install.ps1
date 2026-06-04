param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("Install", "Uninstall", "Start", "Stop", "Logs")]
    [string]$Action
)

# Windows Task Scheduler Installer for darkFlash L280M PC Monitor Driver
# This script must be run as Administrator to register scheduled tasks.

# 1. Check for Admin privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This script must be run as Administrator."
    Write-Host "Please re-open PowerShell as Administrator and run this script again." -ForegroundColor Red
    Exit
}

$driverDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $driverDir "main.py"
$logPath = Join-Path $driverDir "driver.log"
$taskName = "darkFlash_PCMonitor_Driver"

# 2. Find pythonw.exe or python.exe
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    $pythonPath = "python.exe"
}
$pythonwPath = $pythonPath -replace "python.exe", "pythonw.exe"
if (-not (Test-Path $pythonwPath)) {
    $pythonwPath = $pythonPath
}

function Install-Task {
    Write-Host "Registering Scheduled Task '$taskName'..." -ForegroundColor Yellow
    
    $action = New-ScheduledTaskAction -Execute $pythonwPath -Argument "`"$scriptPath`"" -WorkingDirectory $driverDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    
    $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $currentUser -RunLevel Highest
    
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Priority 4
    
    $task = Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
    
    if ($task) {
        Write-Host "[+] Scheduled task registered successfully!" -ForegroundColor Green
        Write-Host "[*] Starting the task now..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $taskName
        Write-Host "[+] Task started in background. Checking log file..." -ForegroundColor Green
        Start-Sleep -Seconds 2
        Show-Logs -NumLines 10
    } else {
        Write-Error "Failed to register scheduled task."
    }
}

function Uninstall-Task {
    Write-Host "Stopping and removing Scheduled Task '$taskName'..." -ForegroundColor Yellow
    
    # Check if task exists
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($task) {
        # Stop task if running
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        # Unregister task
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "[+] Scheduled task removed successfully." -ForegroundColor Green
    } else {
        Write-Host "[*] Task '$taskName' does not exist." -ForegroundColor Yellow
    }
}

function Start-Task {
    Write-Host "Starting Scheduled Task '$taskName'..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $taskName
    Write-Host "[+] Task start command issued." -ForegroundColor Green
}

function Stop-Task {
    Write-Host "Stopping Scheduled Task '$taskName'..." -ForegroundColor Yellow
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    # Kill any stray pythonw instances running main.py
    $processes = Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -like "*main.py*" }
    if ($processes) {
        $processes | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
        Write-Host "[+] Terminated stray background driver processes." -ForegroundColor Green
    }
    Write-Host "[+] Task stopped." -ForegroundColor Green
}

function Show-Logs {
    param(
        [int]$NumLines = 30
    )
    if (Test-Path $logPath) {
        Write-Host "--- Last $NumLines lines of $logPath ---" -ForegroundColor Cyan
        Get-Content $logPath -Tail $NumLines
    } else {
        Write-Host "Log file does not exist yet: $logPath" -ForegroundColor Yellow
    }
}

# If Action argument was provided, run it directly
if ($Action) {
    switch ($Action) {
        "Install"   { Install-Task; Break }
        "Uninstall" { Uninstall-Task; Break }
        "Start"     { Start-Task; Break }
        "Stop"      { Stop-Task; Break }
        "Logs"      { Show-Logs; Break }
    }
    Exit
}

# Interactive Menu fallback
Write-Host "Driver Directory: $driverDir" -ForegroundColor Cyan
Write-Host "Python Path:      $pythonwPath" -ForegroundColor Cyan
Write-Host "Script Path:      $scriptPath" -ForegroundColor Cyan

Write-Host "`nOptions:" -ForegroundColor White
Write-Host "1) Install & Start Background Task (Run on Login)"
Write-Host "2) Uninstall/Remove Task"
Write-Host "3) Start Task"
Write-Host "4) Stop Task"
Write-Host "5) View Logs"
Write-Host "q) Quit`n"

$choice = Read-Host "Choose an option"

switch ($choice) {
    "1" { Install-Task }
    "2" { Uninstall-Task }
    "3" { Start-Task }
    "4" { Stop-Task }
    "5" { Show-Logs }
    "q" { Exit }
    default { Write-Host "Invalid choice." -ForegroundColor Red }
}
