@echo off
title 📚 LibManager - Library Management Desktop Application
cls
echo ========================================================
echo   📚 LibManager - Desktop Application Edition
echo ========================================================
echo.
echo Initializing LibManager Environment...
echo.

set "PY_CMD=python"
where %PY_CMD% >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else (
        where py >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            set "PY_CMD=py"
        )
    )
)

echo Launching LibManager Desktop Application window with %PY_CMD%...
echo.
"%PY_CMD%" main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] An error occurred while running the application.
    pause
)
