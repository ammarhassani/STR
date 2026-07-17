@echo off
REM Open the STR operator control panel (status, designate host, failover, backups).
cd /d "%~dp0.."
python "flet_app\main.py" --panel
