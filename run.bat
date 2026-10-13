@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m gesture_control --hand Any
pause
