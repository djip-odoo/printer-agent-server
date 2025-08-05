@echo off
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo Installing requirements...
pip install --upgrade pip
pip install -r requirements.txt

echo Building executable with PyInstaller...
pyinstaller --clean --onefile ^
  --add-data "ssl/cert.pem;ssl" ^
  --add-data "ssl/key.pem;ssl" ^
  --add-data "venv\Lib\site-packages\escpos\capabilities.json;escpos" ^
  main.py

echo Build complete. Output is in dist\main.exe
