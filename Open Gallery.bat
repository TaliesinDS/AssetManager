@echo off
title AssetManager - Generate Gallery
cd /d "%~dp0src"
echo Scanning library and building gallery...
python -m asset_manager.cli gallery
echo.
echo Opening gallery in browser...
start "" "%~dp0output\gallery.html"
