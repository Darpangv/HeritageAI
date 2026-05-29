@echo off
setlocal

cd /d "%~dp0"
python scripts\manage_conversation_memory.py %*
