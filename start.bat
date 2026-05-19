@echo off
title ForexBot Pro
echo ============================================
echo   Starting ForexBot Pro
echo ============================================
cd /d %~dp0
call venv\Scripts\activate.bat
echo.
echo Open in browser: http://localhost:5000
echo Press CTRL+C to stop the server
echo.
python app.py
pause
