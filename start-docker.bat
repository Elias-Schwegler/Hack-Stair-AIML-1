@echo off
REM =============================================================================
REM Geopard Docker Startup Script for Windows
REM =============================================================================
REM This script starts the Geopard application using Docker Compose on Windows
REM =============================================================================

echo.
echo ========================================================================
echo   Geopard - AI-Powered Geodata Assistant for Canton Luzern
echo ========================================================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop for Windows from:
    echo https://www.docker.com/products/docker-desktop
    echo.
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running
    echo.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo [OK] Docker is installed and running
echo.

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found
    echo.
    if exist .env.example (
        echo Creating .env from .env.example...
        copy .env.example .env
        echo.
        echo [IMPORTANT] Please edit .env file with your Azure credentials:
        echo   - AZURE_OPENAI_API_KEY
        echo   - AZURE_OPENAI_ENDPOINT
        echo   - AZURE_SEARCH_ENDPOINT
        echo   - AZURE_SEARCH_KEY
        echo.
        echo Then run this script again.
        pause
        exit /b 1
    ) else (
        echo [ERROR] No .env.example template found
        pause
        exit /b 1
    )
)

echo [OK] Environment file found
echo.

REM Stop any existing containers
echo Stopping any existing containers...
docker-compose down 2>nul

REM Build and start the containers
echo.
echo Building Docker image...
echo This may take a few minutes on first run...
echo.
docker-compose build

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Docker build failed
    pause
    exit /b 1
)

echo.
echo Starting Geopard application...
echo.
docker-compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start application
    pause
    exit /b 1
)

echo.
echo ========================================================================
echo   Geopard is now running!
echo ========================================================================
echo.
echo   Web Interface:  http://localhost:8000
echo   API Docs:       http://localhost:8000/docs
echo   Health Check:   http://localhost:8000/health
echo.
echo To view logs:     docker-compose logs -f
echo To stop:          docker-compose down
echo.
echo ========================================================================
echo.

REM Wait a moment for the container to start
timeout /t 3 /nobreak >nul

REM Check if container is healthy
echo Checking application health...
timeout /t 5 /nobreak >nul

docker-compose ps | findstr "Up" >nul
if %ERRORLEVEL% EQ 0 (
    echo [OK] Application is running
    echo.
    echo Opening browser...
    start http://localhost:8000
) else (
    echo [WARNING] Container may still be starting up
    echo Check logs with: docker-compose logs -f
)

echo.
pause
