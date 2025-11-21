@echo off
echo.
echo ============================================
echo   Self-Checkout System - Development Mode
echo ============================================
echo.

echo Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo Checking Node.js environment...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo.
echo Setting up environment files...
if not exist ".env" (
    echo Creating .env from template...
    copy ".env.example" ".env"
) else (
    echo .env already exists, skipping...
)

echo.
echo Setting up backend...
cd services

if not exist ".env" (
    echo Creating services/.env from template...
    copy ".env.example" ".env"
) else (
    echo services/.env already exists, skipping...
)

echo Checking virtual environment...
if not exist "venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists, skipping creation...
)

echo Testing virtual environment activation...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Recreating virtual environment...
    rmdir /s /q venv
    python -m venv venv
    call venv\Scripts\activate.bat
)

echo Checking Python dependencies...
pip show torch >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo Python dependencies already installed, skipping...
)

echo Checking YOLOv5 model...
if not exist "models\yolov5s.pt" (
    echo Downloading YOLOv5 model...
    python DownloadModel.py
    if errorlevel 1 (
        echo ERROR: Failed to download model
        pause
        exit /b 1
    )
) else (
    echo YOLOv5 model already exists, skipping download...
)

echo.
echo Starting backend server...
start cmd /k "title Backend Server && cd /d %CD% && venv\Scripts\activate.bat && python App.py"

cd ..

echo.
echo Setting up frontend...
if not exist "node_modules\next" (
    echo Installing Node.js dependencies...
    npm install
    if errorlevel 1 (
        echo ERROR: Failed to install Node.js dependencies
        pause
        exit /b 1
    )
) else (
    echo Node.js dependencies already installed, skipping...
)

echo.
echo Starting frontend development server...
start cmd /k "title Frontend Server && npm run dev:next"

echo.
echo ============================================
echo   Development servers are starting...
echo ============================================
echo.
echo Frontend: http://localhost:3002
echo Backend:  http://127.0.0.1:5002
echo Video:    http://127.0.0.1:5002/video_feed
echo.
echo Press any key to exit...
pause >nul