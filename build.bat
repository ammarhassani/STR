@echo off
REM ============================================================
REM  STR - build the distributable client/host executable
REM ============================================================
REM  The build is defined in STR.spec, NOT on this command line.
REM  The old one-liner omitted pathex and every data file, which
REM  produced an .exe that died on a fresh PC with
REM  "No module named components". See STR.spec for the details.
REM ============================================================
cd /d "%~dp0"

echo Step 1: Installing PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :failed

echo.
echo Step 2: Building executable from STR.spec...
python -m PyInstaller --noconfirm --clean STR.spec
if errorlevel 1 goto :failed

echo.
echo Step 3: Verifying the build...
python tools\verify_build.py
if errorlevel 1 goto :failed

echo.
echo ================================================
echo  Build OK:  dist\FIU_System.exe
echo ================================================
echo.
echo  Copy the .exe to the client PC and run it. It creates
echo  config\ and database\ NEXT TO ITSELF, so put it in a
echo  writable folder such as C:\STR\ -- not Program Files.
echo.
pause
exit /b 0

:failed
echo.
echo ================================================
echo  BUILD FAILED - see the messages above.
echo ================================================
pause
exit /b 1
