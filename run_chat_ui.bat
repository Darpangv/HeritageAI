@echo off
setlocal

cd /d "%~dp0"

set "BUNDLED_PY=C:\Users\darpa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PY%" (
  set "PYTHON_EXE=%BUNDLED_PY%"
) else (
  set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m streamlit run app_chat.py --server.port 8502 --server.headless true
