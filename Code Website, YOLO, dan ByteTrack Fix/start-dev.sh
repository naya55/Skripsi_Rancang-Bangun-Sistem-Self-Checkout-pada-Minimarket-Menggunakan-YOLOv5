#!/bin/bash

echo ""
echo "============================================"
echo "   Self-Checkout System - Development Mode"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python3 not found! Please install Python 3.8+"
    exit 1
fi

# Check Node.js
if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js not found! Please install Node.js 18+"
    exit 1
fi

echo "Setting up environment files..."
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
fi

echo "Setting up backend..."
cd services

if [ ! -f ".env" ]; then
    echo "Creating services/.env from template..."
    cp .env.example .env
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Download model if it doesn't exist
if [ ! -f "models/yolov5s.pt" ]; then
    echo "Downloading YOLOv5 model..."
    python DownloadModel.py
fi

echo ""
echo "Starting backend server..."
gnome-terminal --title="Backend Server" -- bash -c "source venv/bin/activate; python App.py; exec bash" 2>/dev/null ||
    osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && source venv/bin/activate && python App.py"' 2>/dev/null ||
    (source venv/bin/activate && python App.py &)

cd ..

echo ""
echo "Setting up frontend..."
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi

echo ""
echo "Starting frontend development server..."
gnome-terminal --title="Frontend Server" -- bash -c "npm run dev:next; exec bash" 2>/dev/null ||
    osascript -e 'tell app "Terminal" to do script "cd '$(pwd)' && npm run dev:next"' 2>/dev/null ||
    (npm run dev:next &)

echo ""
echo "============================================"
echo "   Development servers are starting..."
echo "============================================"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend:  http://127.0.0.1:5000"
echo "Video:    http://127.0.0.1:5000/video_feed"
echo ""
echo "Press Ctrl+C to stop servers"
echo ""

# Keep script running
wait
