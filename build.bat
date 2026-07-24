@echo off
cd /d "%~dp0"
set "VENV_PY=D:\tools\venvs\screensnap\Scripts\python.exe"
if not exist "%VENV_PY%" set "VENV_PY=python"
"%VENV_PY%" -m PyInstaller --noconfirm --clean --windowed --onedir --name ScreenSnap --collect-all vosk --collect-all sounddevice --collect-all winsdk --add-data "models;models" run.py
echo.
echo Build done: dist\ScreenSnap\ScreenSnap.exe
pause
