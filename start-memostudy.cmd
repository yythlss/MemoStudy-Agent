@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "DOCKER_HOME=D:\app\docker\program"
set "PATH=%DOCKER_HOME%\resources\bin;%PATH%"
set "PROJECT_DIR=%~dp0"
set "APP_URL=http://localhost:3001"

if not exist "%DOCKER_HOME%\Docker Desktop.exe" (
    echo [MemoStudy] Docker Desktop was not found at %DOCKER_HOME%.
    pause
    exit /b 1
)

docker desktop status --format json 2>nul | findstr /i "running" >nul
if not errorlevel 1 goto docker_ready

echo [MemoStudy] Starting Docker Desktop...
start "" "%DOCKER_HOME%\Docker Desktop.exe"
set /a tries=0

:wait_for_docker
timeout /t 3 /nobreak >nul
set /a tries+=1
docker desktop status --format json 2>nul | findstr /i "running" >nul
if not errorlevel 1 goto docker_ready
if !tries! geq 40 goto docker_failed
goto wait_for_docker

:docker_ready
echo [MemoStudy] Docker is ready. Starting services...
cd /d "%PROJECT_DIR%"
docker compose up -d
if errorlevel 1 goto compose_failed

echo [MemoStudy] Application is ready: %APP_URL%
start "" "%APP_URL%"
exit /b 0

:docker_failed
echo [MemoStudy] Docker Desktop did not become ready in time.
pause
exit /b 1

:compose_failed
echo [MemoStudy] Failed to start the application. Check Docker Desktop logs.
pause
exit /b 1
