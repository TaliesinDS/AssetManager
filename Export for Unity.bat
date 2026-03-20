@echo off
title AssetManager - Export for Unity
cd /d "%~dp0src"
echo.
echo Type part of a texture name to export (or * for all):
set /p "NAME=>> "
if "%NAME%"=="*" (
    python -m asset_manager.cli unity-export
) else (
    python -m asset_manager.cli unity-export --name "%NAME%"
)
echo.
echo Output is in: %~dp0output\unity\
explorer "%~dp0output\unity"
pause
