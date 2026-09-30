@echo off

cd /d "%~dp0.."

echo ========================================
echo SHELL-emulator - Stage 2
echo ========================================
echo VFS: %CD%\vfs
echo Startup: %CD%\scripts\startup_success.txt
echo.

py -3 -m src.shell_emulator2 "%CD%\vfs" "%CD%\scripts\startup_success.txt"

echo.
echo Exit code: %ERRORLEVEL%
echo.
pause