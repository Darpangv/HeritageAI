@echo off
setlocal
cd /d "%~dp0"
python scripts\discover_new_sources.py %*
