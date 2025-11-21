@echo off
echo Starting Self-Checkout Backend Server...
echo.

cd services

if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing/checking dependencies...
pip install -r requirements.txt -q

echo.
echo Setting production mode...
set FLASK_DEBUG=False

echo Starting Flask server...
python App.py

pause