@echo off
cd /d "%~dp0"
set "VENV_PY=D:\tools\venvs\screensnap\Scripts\python.exe"
if exist "%VENV_PY%" "%VENV_PY%" run.py
if not exist "%VENV_PY%" python run.py
if errorlevel 1 pause
