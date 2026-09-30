@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"
echo ========================================
echo SHELL-emulator - Stage 2 error test
echo ========================================

where py >nul 2>nul
if not errorlevel 1 goto run_py
where python >nul 2>nul
if not errorlevel 1 goto run_python
echo ERROR: Python 3 not found.
set "RC=9009"
goto done

:run_py
py -3 -m src.shell_emulator2 "%ROOT_DIR%\vfs" "%ROOT_DIR%\scripts\startup_error.txt"
set "RC=%ERRORLEVEL%"
goto check

:run_python
python -m src.shell_emulator2 "%ROOT_DIR%\vfs" "%ROOT_DIR%\scripts\startup_error.txt"
set "RC=%ERRORLEVEL%"
goto check

:check
if "%RC%"=="1" (
    echo.
    echo Test passed: startup script stopped on first error.
) else (
    echo.
    echo Test FAILED: expected exit code 1, got %RC%.
)

:done
echo.
echo Code: %RC%
pause
exit /b %RC%
