@echo off
title AssetManager - Scan Library
cd /d "%~dp0src"
python -m asset_manager.cli scan
echo.
pause
