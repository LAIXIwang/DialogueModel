@echo off
rem ==============================================
rem  Dialogue BFF launcher (conda "work" env)
rem ==============================================
cd /d "%~dp0"

where conda >nul 2>nul
if errorlevel 1 (
    echo [ERROR] conda not found. Install Anaconda/Miniconda and add it to PATH.
    pause
    exit /b 1
)

conda run -n work python -c "import fastapi, uvicorn, httpx" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] conda env "work" is missing or lacks dependencies.
    echo   Fix it first:
    echo     conda env create -f environment.yml
    echo   or for an existing env:
    echo     conda run -n work pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting Dialogue BFF at http://127.0.0.1:8000  (Ctrl+C to stop)
echo Health check: http://127.0.0.1:8000/health
echo.
conda run -n work --no-capture-output uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
