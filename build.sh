#!/bin/bash

set -e

echo "📦 Creating virtual environment..."
python3 -m venv .venv
source ./.venv/bin/activate

echo "📥 Installing requirements..."
pip install --upgrade pip
pip install fastapi uvicorn pydantic pyinstaller

echo "🛠️ Building executable..."
pyinstaller --onefile \
  --add-data "ssl/cert.pem:ssl" \
  --add-data "ssl/key.pem:ssl" \
  main.py

echo "✅ Build complete. Binary: dist/main"
