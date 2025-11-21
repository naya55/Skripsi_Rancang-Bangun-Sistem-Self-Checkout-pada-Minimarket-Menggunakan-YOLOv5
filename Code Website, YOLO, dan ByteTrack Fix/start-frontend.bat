@echo off
echo Starting Self-Checkout Frontend...
echo.

echo Installing/checking dependencies...
call npm install

echo.
echo Starting Next.js production server on port 3002...
call npm run start:next

pause