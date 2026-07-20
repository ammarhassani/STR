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

REM PyInstaller is PINNED in requirements.txt and installed ONCE:
REM     python -m pip install -r requirements.txt
REM This used to run "pip install --upgrade pyinstaller" on every single build,
REM which needed the network and let PyPI change the bootloader and the flet
REM hook in the middle of a project. flet is pinned for exactly that reason --
REM the tool that PACKAGES it should not float either. The _MEI behaviour this
REM app has already been burned by is bootloader behaviour.

echo Step 1: Building the app from STR.spec...
python -m PyInstaller --noconfirm --clean STR.spec
if errorlevel 1 goto :failed

echo.
echo Step 2: Building the Control Panel from STR_Panel.spec...
REM A separate executable because the panel has to work when the APP does not:
REM the button on the login screen is unreachable if the app cannot start.
python -m PyInstaller --noconfirm --clean STR_Panel.spec
if errorlevel 1 goto :failed

echo.
echo Step 3: Verifying both builds...
python tools\verify_build.py
if errorlevel 1 goto :failed

echo.
echo ================================================
echo  Build OK
echo    dist\FIU_System.exe          the app
echo    dist\FIU_Control_Panel.exe   the check-up tool
echo ================================================
echo.
echo  Copy BOTH to the client PC. They create config\ and
echo  database\ NEXT TO THEMSELVES, so put them in a writable
echo  folder such as C:\STR\ -- not Program Files.
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
