@echo off
title AssetManager - Generate Gallery
cd /d "%~dp0src"

echo Stopping any existing gallery server on port 8271...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8271 " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo Scanning library and building gallery...
python -m asset_manager.cli gallery
echo.
echo Starting gallery server (Ctrl+C to stop)...
python -m asset_manager.cli serve
