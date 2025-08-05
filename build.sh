#!/bin/bash

set -e

echo "📦 Creating virtual environment..."
python3 -m venv venv
source ./venv/bin/activate

echo "📥 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🛠️ Building executable with PyInstaller..."
pyinstaller --clean --onefile \
  --add-data "ssl/cert.pem:ssl" \
  --add-data "ssl/key.pem:ssl" \
  main.py

echo "✅ PyInstaller build complete. Binary: dist/main"

# Optional: Make sure the binary is executable
chmod +x dist/main

# Check for missing shared libraries
echo "🔍 Checking shared library dependencies..."
if ldd dist/main | grep "not found"; then
    echo "❌ Some shared libraries are missing. Consider using staticx."
    exit 1
fi

# Optional: Build fully static binary using staticx (Linux only)
if command -v staticx &> /dev/null; then
    echo "📦 Creating static binary with staticx..."
    staticx dist/main dist/main_static
    chmod +x dist/main_static
    echo "✅ Static binary ready: dist/main_static"
else
    echo "ℹ️ staticx not found. To create a fully portable binary, run:"
    echo "    sudo apt install patchelf upx squashfs-tools"
    echo "    pip install staticx"
    echo "    staticx dist/main dist/main_static"
fi
