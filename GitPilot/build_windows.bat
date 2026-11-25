@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run install.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name GitPilot main.py
if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo EXE output: dist\GitPilot\GitPilot.exe
pause
