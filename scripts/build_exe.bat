@echo off
setlocal
cd /d "%~dp0.."
if not defined IT_TOOLKIT_PYTHON (
    if exist ".venv\Scripts\python.exe" (
        set "IT_TOOLKIT_PYTHON=%CD%\.venv\Scripts\python.exe"
    ) else (
        set "IT_TOOLKIT_PYTHON=python"
    )
)
if not defined IT_TOOLKIT_BUILD_NAME set "IT_TOOLKIT_BUILD_NAME=IT-Operations-Console-%RANDOM%"
if exist "dist\%IT_TOOLKIT_BUILD_NAME%.exe" (
    echo Output already exists. Choose another IT_TOOLKIT_BUILD_NAME.
    exit /b 1
)
"%IT_TOOLKIT_PYTHON%" -m PyInstaller --distpath "%CD%\dist" --workpath "%CD%\build\%IT_TOOLKIT_BUILD_NAME%" --noconfirm --log-level WARN packaging\IT-Operations-Console.spec
if errorlevel 1 exit /b 1
echo Built: %CD%\dist\%IT_TOOLKIT_BUILD_NAME%.exe
exit /b 0
