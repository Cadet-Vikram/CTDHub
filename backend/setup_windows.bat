@echo off
echo ============================================
echo  Connecting the Dots - Backend Setup
echo ============================================
echo.

echo [1/3] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo.
echo [2/3] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [3/3] Starting server...
uvicorn main:app --reload --port 8000

pause
