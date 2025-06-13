@echo off
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo Installing requirements...
pip install --upgrade pip
pip install fastapi uvicorn pydantic pyinstaller

echo Building executable...
pyinstaller --onefile ^
  --add-data "ssl/cert.pem:ssl" ^
  --add-data "ssl/key.pem:ssl" ^
  main.py

echo Build complete. Output is in dist\main.exe
