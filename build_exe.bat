@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Create the venv first: py -3.12 -m venv .venv  then  pip install -r requirements.txt
  pause & exit /b 1
)
call .venv\Scripts\activate.bat
if not exist hand_landmarker.task (
  echo hand_landmarker.task is missing from this folder.
  pause & exit /b 1
)
pip install pyinstaller
pyinstaller --noconfirm --clean --onedir --name GestureControl --collect-all mediapipe --add-data "hand_landmarker.task;." run_app.py
echo.
echo Done. Copy the whole folder  dist\GestureControl  to any 64-bit Windows 10/11 PC
echo and run GestureControl.exe  (no Python or internet needed there).
pause
