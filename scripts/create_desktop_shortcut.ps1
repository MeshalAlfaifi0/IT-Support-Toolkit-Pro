#Requires -Version 5.1
<#
.SYNOPSIS
    Creates a desktop shortcut for IT Operations Console.

.DESCRIPTION
    ينشئ اختصاراً لـ IT Operations Console على سطح المكتب.
    يُستخدَم بعد بناء ملف EXE بواسطة scripts\build_exe.bat.

.PARAMETER ExePath
    المسار الكامل لملف EXE. اختياري — يُحدَّد تلقائياً من مجلد dist.

.PARAMETER Scope
    CurrentUser (الافتراضي) أو AllUsers (يتطلب مسؤول).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1
    powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1 -Scope AllUsers
#>

param(
    [string]$ExePath = "",
    [ValidateSet("CurrentUser", "AllUsers")]
    [string]$Scope = "CurrentUser"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  IT Operations Console — Create Desktop Shortcut" -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host ""

# ── تحديد مسار EXE ────────────────────────────────────────────────────────
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

if ($ExePath -eq "") {
    $LatestBuild = Get-ChildItem -LiteralPath (Join-Path $ProjectDir "dist") -Filter "IT-Operations-Console*.exe" -File |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($LatestBuild) {
        $ExePath = $LatestBuild.FullName
    } else {
        $ExePath = Join-Path $ProjectDir "dist\IT-Operations-Console.exe"
    }
}

if (-not (Test-Path $ExePath)) {
    Write-Host "[خطأ] لم يتم العثور على ملف EXE:" -ForegroundColor Red
    Write-Host "       $ExePath" -ForegroundColor Red
    Write-Host ""
    Write-Host "  قم ببناء التطبيق أولاً باستخدام:" -ForegroundColor Yellow
    Write-Host "      scripts\build_exe.bat" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "اضغط Enter للخروج"
    exit 1
}

# ── تحديد مسار سطح المكتب ───────────────────────────────────────────────
if ($Scope -eq "AllUsers") {
    # يتطلب تشغيل كمسؤول
    $currentPrincipal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "[خطأ] يتطلب AllUsers تشغيل PowerShell كمسؤول." -ForegroundColor Red
        exit 1
    }
    $DesktopPath = [Environment]::GetFolderPath("CommonDesktopDirectory")
} else {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
}

$ShortcutPath = Join-Path $DesktopPath "IT Operations Console.lnk"

# ── إنشاء الاختصار ────────────────────────────────────────────────────────
Write-Host "  مسار EXE      : $ExePath" -ForegroundColor Gray
Write-Host "  سطح المكتب    : $DesktopPath" -ForegroundColor Gray
Write-Host "  ملف الاختصار  : $ShortcutPath" -ForegroundColor Gray
Write-Host ""

try {
    $WshShell  = New-Object -ComObject WScript.Shell
    $Shortcut  = $WshShell.CreateShortcut($ShortcutPath)

    $Shortcut.TargetPath       = $ExePath
    $Shortcut.WorkingDirectory = Split-Path -Parent $ExePath
    $Shortcut.Description      = "IT Operations Console — أدوات دعم تقنية المعلومات"
    $Shortcut.WindowStyle      = 1   # SW_SHOWNORMAL

    # استخدام أيقونة EXE نفسه (تضمَّنت داخله عبر PyInstaller)
    $Shortcut.IconLocation     = "$ExePath,0"

    $Shortcut.Save()

    Write-Host "[نجح] تم إنشاء الاختصار بنجاح:" -ForegroundColor Green
    Write-Host "       $ShortcutPath" -ForegroundColor Green

} catch {
    Write-Host "[خطأ] فشل إنشاء الاختصار:" -ForegroundColor Red
    Write-Host "       $_" -ForegroundColor Red
    exit 1
}

# ── إنشاء اختصار في قائمة Start (اختياري) ────────────────────────────────
$CreateStartMenu = Read-Host "`nهل تريد إنشاء اختصار في قائمة Start أيضاً؟ [Y/N]"

if ($CreateStartMenu -match "^[Yy]$") {
    try {
        if ($Scope -eq "AllUsers") {
            $StartMenuDir = [Environment]::GetFolderPath("CommonPrograms")
        } else {
            $StartMenuDir = [Environment]::GetFolderPath("Programs")
        }

        $AppFolder = Join-Path $StartMenuDir "IT Operations Console"
        if (-not (Test-Path $AppFolder)) {
            New-Item -ItemType Directory -Path $AppFolder | Out-Null
        }

        $StartShortcut = $WshShell.CreateShortcut(
            (Join-Path $AppFolder "IT Operations Console.lnk")
        )
        $StartShortcut.TargetPath       = $ExePath
        $StartShortcut.WorkingDirectory = Split-Path -Parent $ExePath
        $StartShortcut.Description      = "IT Operations Console — أدوات دعم تقنية المعلومات"
        $StartShortcut.WindowStyle      = 1
        $StartShortcut.IconLocation     = "$ExePath,0"
        $StartShortcut.Save()

        Write-Host "[نجح] تم إنشاء اختصار قائمة Start:" -ForegroundColor Green
        Write-Host "       $(Join-Path $AppFolder 'IT Operations Console.lnk')" -ForegroundColor Green

    } catch {
        Write-Host "[تحذير] فشل إنشاء اختصار قائمة Start: $_" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  اكتملت العملية. ابحث عن الاختصار على سطح المكتب." -ForegroundColor Cyan
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host ""
