@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto dependencies

py -3 -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
if errorlevel 1 goto try_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto dependencies

:try_python
python -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
if errorlevel 1 goto no_python
python -m venv .venv
if errorlevel 1 goto failed

:dependencies
".venv\Scripts\python.exe" -c "import django; assert django.get_version() == '6.1.2'" >nul 2>&1
if not errorlevel 1 goto run
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed

:run
echo Open http://127.0.0.1:8000/ in your browser after the server starts.
echo Press Ctrl+C to stop the server.
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000
if errorlevel 1 goto failed
exit /b 0

:no_python
echo Python 3.12 or newer is required. Install Python and enable Add to PATH.
pause
exit /b 1

:failed
echo Could not start the project. Read the error above and README.md.
pause
exit /b 1
