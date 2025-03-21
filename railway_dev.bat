@echo off
REM Railway Local Development Helper Batch File
REM This script provides shortcuts for common Railway CLI commands

if "%1"=="" (
    echo Railway Local Development Helper
    echo.
    echo Usage: railway_dev.bat [command]
    echo.
    echo Available commands:
    echo   setup      - Set up Railway CLI and link to project
    echo   api        - Run the API server with Railway environment
    echo   etl        - Run the Google Ads ETL process once
    echo   db         - Check database connectivity and tables
    echo   health     - Check API health
    echo   unmapped   - Check for unmapped campaigns
    echo   all        - Run all checks
    echo.
    exit /b 1
)

REM Run the Python helper script with the provided command
python railway_local.py %*
