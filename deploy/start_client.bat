@echo off
REM Run the STR client FROM SOURCE (developer machines only).
REM
REM Client PCs do NOT use this. They run the packaged FIU_System.exe, which
REM needs no Python and no source tree -- see docs/SETUP.md section C.
cd /d "%~dp0.."
REM Self-update first (#19): pull latest code if online + clean, then launch.
python "updater.py"
python "flet_app\main.py"
