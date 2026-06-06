# Campus Network Auto Login - Startup Setup
# Right-click this file -> Run with PowerShell
# No admin rights required.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "xyw.py"
$vbsFile = Join-Path $scriptDir "run_xyw.vbs"

# Find Python
$pythonPath = $null
try { $pythonPath = (Get-Command python -ErrorAction Stop).Source } catch {}
if (-not $pythonPath) {
    try { $pythonPath = (Get-Command python3 -ErrorAction Stop).Source } catch {}
}
if (-not $pythonPath) {
    Write-Host "[ERROR] Python not found. Install Python and add it to PATH." -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host "[INFO] Python path: $pythonPath" -ForegroundColor Green

# Create VBS launcher (runs Python silently, no console window)
$runCmd = "`"$pythonPath`" `"$pythonScript`""
$vbsContent = @"
Set ws = CreateObject("WScript.Shell")
ws.Run "$runCmd", 0, False
"@
Set-Content -Path $vbsFile -Value $vbsContent -Encoding ASCII
Write-Host "[INFO] Created VBS launcher: $vbsFile" -ForegroundColor Green

# Copy VBS shortcut to Windows Startup folder (no admin needed)
$startupDir = [Environment]::GetFolderPath("Startup")
$startupLink = Join-Path $startupDir "CampusNetworkLogin.lnk"

try {
    # Remove old shortcut if exists
    if (Test-Path $startupLink) {
        Remove-Item $startupLink -Force
        Write-Host "[INFO] Removed old startup shortcut" -ForegroundColor Yellow
    }

    # Create shortcut
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut($startupLink)
    $shortcut.TargetPath = "wscript.exe"
    $shortcut.Arguments = "`"$vbsFile`""
    $shortcut.WorkingDirectory = $scriptDir
    $shortcut.WindowStyle = 7  # Minimized
    $shortcut.Description = "Campus Network Auto Login"
    $shortcut.Save()

    Write-Host "[SUCCESS] Auto-startup configured!" -ForegroundColor Green
    Write-Host "[INFO] Shortcut created: $startupLink" -ForegroundColor Green
    Write-Host "[INFO] The script will run automatically in background after user logon." -ForegroundColor Green
    Write-Host ""
    Write-Host "Tips:" -ForegroundColor Yellow
    Write-Host "  - Double-click run_xyw.vbs to run manually now" -ForegroundColor Yellow
    Write-Host "  - To disable: delete CampusNetworkLogin.lnk from:" -ForegroundColor Yellow
    Write-Host "    $startupDir" -ForegroundColor Yellow

} catch {
    Write-Host "[ERROR] Failed: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "[FALLBACK] Do it manually:" -ForegroundColor Yellow
    Write-Host "  1. Press Win+R, type: shell:startup" -ForegroundColor Yellow
    Write-Host "  2. Copy run_xyw.vbs into the Startup folder" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
