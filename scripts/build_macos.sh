#!/usr/bin/env bash
set -euo pipefail

PYTHON_CMD="${PYTHON_CMD:-python3}"

echo "[1/3] Preparing build tools..."
"${PYTHON_CMD}" -m pip install --upgrade pip
"${PYTHON_CMD}" -m pip install -e ".[build]"

echo "[2/3] Running tests..."
"${PYTHON_CMD}" -m unittest discover -s tests -v

echo "[3/3] Building AutoIO.app..."
"${PYTHON_CMD}" -m PyInstaller \
  --clean \
  --noconfirm \
  --windowed \
  --collect-all customtkinter \
  --osx-bundle-identifier "io.github.rootseyo.autoio" \
  --name "AutoIO" \
  auto_kb_mouse.py

APP_VERSION="$("${PYTHON_CMD}" -c 'from auto_io import __version__; print(__version__)')"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString ${APP_VERSION}" dist/AutoIO.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c "Add :CFBundleVersion string ${APP_VERSION}" dist/AutoIO.app/Contents/Info.plist
codesign --force --deep --sign - dist/AutoIO.app

echo "Build complete: dist/AutoIO.app"
