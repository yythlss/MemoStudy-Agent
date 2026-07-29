@echo off
setlocal

set "DOCKER_HOME=D:\app\docker\program"
set "PATH=%DOCKER_HOME%\resources\bin;%PATH%"
cd /d "%~dp0"

echo [MemoStudy] Stopping services...
docker compose down
if errorlevel 1 (
    echo [MemoStudy] Failed to stop services.
    pause
    exit /b 1
)

echo [MemoStudy] Services stopped. Your knowledge data was preserved.
timeout /t 2 /nobreak >nul

