@echo off
REM Run the STR client FROM SOURCE (developer machines only).
REM
REM Client PCs do NOT use this. They run the packaged FIU_System.exe, which
REM needs no Python and no source tree -- see docs/SETUP.md section C.
cd /d "%~dp0.."
python "flet_app\main.py"
