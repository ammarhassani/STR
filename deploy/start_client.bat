@echo off
REM Launch the STR client with a visible window (troubleshooting). For normal
REM use prefer deploy\start_client.vbs, which runs with no console window.
cd /d "%~dp0.."
REM Self-update first (#19): pull latest code if online + clean, then launch.
python "updater.py"
python "flet_app\main.py"
