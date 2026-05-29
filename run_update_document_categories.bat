@echo off
setlocal

cd /d "%~dp0"

set "BUNDLED_PY=C:\Users\darpa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PY%" (
  set "PYTHON_EXE=%BUNDLED_PY%"
) else (
  set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" scripts\update_document_categories.py
