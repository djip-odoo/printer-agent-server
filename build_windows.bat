@echo off
setlocal

echo ============================
echo Creating virtual environment...
echo ============================
python -m venv venv
call venv\Scripts\activate

echo ============================
echo Installing requirements...
echo ============================
pip install --upgrade pip
pip install -r requirements.txt

echo ============================
echo Building executable with PyInstaller...
echo ============================

REM Use semicolon (;) on Windows in --add-data
REM Format: "<source_path>;<destination_subfolder>"
REM Escape all backslashes properly

pyinstaller --clean --onefile ^
  --add-data "ssl\\cert.pem;ssl" ^
  --add-data "ssl\\key.pem;ssl" ^
  --add-data "venv\\Lib\\site-packages\\escpos\\capabilities.json;escpos" ^
  --add-data "libusb\\libusb-1.0.dll;." ^
  main.py

echo ============================
echo ✅ Build complete. Output is in dist\main.exe
echo ============================

endlocal
pause
