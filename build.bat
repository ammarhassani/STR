@echo off
echo ================================================
echo FIU System - Build Script
echo ================================================
echo.

echo Step 1: Installing PyInstaller...
pip install pyinstaller

echo.
echo Step 2: Building executable...
pyinstaller --onefile --windowed --name FIU_System main.py

echo.
echo ================================================
echo Build Complete!
echo ================================================
echo.
echo Executable location: dist\FIU_System.exe
echo.
echo Copy this file to your network share for deployment.
echo.
pause
