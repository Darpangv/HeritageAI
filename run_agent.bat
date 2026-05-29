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
  echo   run_agent.bat "Your heritage question here"
  echo.
  echo Example:
  echo   run_agent.bat "What does the UNESCO Hampi document say about Hampi heritage?"
  exit /b 1
)

"%PYTHON_EXE%" scripts\heritage_agent.py %*
