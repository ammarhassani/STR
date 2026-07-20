@echo off
REM Launch the STR host on this PC (designated host workstation).
REM Put a shortcut to this file in the Startup folder (Win+R -> shell:startup)
REM so the host starts on login. Screen-lock keeps it running; after a cold
REM reboot the operator must log in once (Startup runs at login, not boot).
cd /d "%~dp0.."
python "flet_app\main.py" --host
