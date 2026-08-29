@echo off
rem ==============================================
rem  Dialogue Admin Platform launcher (conda "work" env)
rem  port 8001
rem ==============================================
cd /d "%~dp0"

where conda >nul 2>nul
if errorlevel 1 (
    echo [ERROR] conda not found.
    pause
    exit /b 1
)

conda run -n work python -c "import fastapi, sqlalchemy, pymysql, bcrypt, jwt, redis" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] conda env "work" missing dependencies. Run:
    echo   conda run -n work pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting Dialogue Admin Platform at http://127.0.0.1:8001  (Ctrl+C to stop)
echo Docs: http://127.0.0.1:8001/docs
echo.
conda run -n work --no-capture-output uvicorn admin.main:app --host 127.0.0.1 --port 8001 --reload
