@echo off
setlocal enabledelayedexpansion

echo ============================
echo Creating virtual environment...
echo ============================
python -m venv venv
call .\venv\Scripts\activate.bat

echo ============================
echo Installing requirements...
echo ============================
pip install --upgrade pip
pip install -r requirements.txt

:: Check if libusb DLL exists
if not exist libusb\libusb-1.0.dll (
    echo ERROR: libusb-1.0.dll is missing.
    goto end
)

:: Check if escpos capabilities.json exists
if not exist "venv\Lib\site-packages\escpos\capabilities.json" (
    echo ERROR: escpos capabilities.json not found!
    goto end
)

echo ============================
echo Building executable with PyInstaller...
echo ============================

pyinstaller --clean --onefile ^
    --add-data "ssl\cert.pem;ssl" ^
    --add-data "ssl\key.pem;ssl" ^
    --add-data "venv\Lib\site-packages\escpos\capabilities.json;escpos" ^
    --add-data "templates\index.html;templates" ^
    --add-data "libusb\libusb-1.0.dll;." ^
    main.py

echo ============================
echo ✅ Build complete. Output is in dist\main.exe
echo ============================

:end
endlocal
pause
