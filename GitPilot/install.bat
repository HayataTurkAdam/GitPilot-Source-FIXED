@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo              GitPilot Setup
echo ==========================================
where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git was not found. Install Git for Windows first.
  echo https://git-scm.com/downloads
  pause
  exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python Launcher was not found. Install Python 3.10 or newer.
  pause
  exit /b 1
)
if not exist .venv (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Double-click run.bat to launch GitPilot.
pause
exit /b 0
:failed
echo.
echo Setup failed. Review the error above.
pause
exit /b 1
