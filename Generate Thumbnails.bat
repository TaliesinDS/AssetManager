@echo off
title AssetManager - Generate Blender Thumbnails
cd /d "%~dp0src"
echo This will render PBR sphere thumbnails using Blender.
echo It may take a while on the first run (~5-10s per texture).
echo.
python -m asset_manager.cli thumbnails
echo.
echo Done! Run "Open Gallery" to see the updated gallery.
pause
