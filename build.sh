#!/bin/bash

set -e

echo "📦 Creating virtual environment..."
python3 -m venv venv
source ./venv/bin/activate

echo "📥 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt
pip install staticx

echo "🔍 Locating escpos capabilities.json..."
CAP_JSON=$(find ./venv -name capabilities.json | head -n 1)

echo "🛠️ Building executable with PyInstaller..."
pyinstaller --clean --onefile \
  --add-data "ssl/cert.pem:ssl" \
  --add-data "ssl/key.pem:ssl" \
  --add-data "templates/index.html:templates" \
  --add-data "$CAP_JSON:escpos" \
  main.py
echo "✅ PyInstaller build complete. Binary: dist/main"

# Ensure binary is executable
chmod +x dist/main

# Check for missing shared libraries
echo "🔍 Checking shared library dependencies..."
missing_libs=$(ldd dist/main | grep "not found" || true)
if [[ -n "$missing_libs" ]]; then
    echo "❌ Some shared libraries are missing:"
    echo "$missing_libs"
    echo "➡️ Trying to build static binary using staticx..."
else
    echo "✅ No missing shared libraries detected."
fi

# Build fully static binary using staticx
if command -v staticx &> /dev/null; then
    echo "📦 Creating static binary with staticx..."
    staticx dist/main dist/main_static
    chmod +x dist/main_static
    echo "✅ Static binary ready: dist/main_static"
else
    echo "❌ staticx not found."
    echo "➡️ To install it and retry:"
    echo "   sudo apt install patchelf upx squashfs-tools"
    echo "   pip install staticx"
fi
