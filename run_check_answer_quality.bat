@echo off
setlocal

cd /d "%~dp0"
python scripts\check_answer_quality.py %*
