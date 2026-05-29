@echo off
setlocal

cd /d "%~dp0"

set "BUNDLED_PY=C:\Users\darpa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PY%" (
  set "PYTHON_EXE=%BUNDLED_PY%"
) else (
  set "PYTHON_EXE=python"
)

if "%~1"=="" (
  echo Usage:
  echo   run_brain_test.bat "Your question"
  exit /b 1
)

"%PYTHON_EXE%" scripts\chatgpt_brain.py %*
