@echo off
setlocal

cd /d "%~dp0"
call "%~dp0load_project_env.bat"

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
set "BUNDLED_PY=C:\Users\darpa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%VENV_PY%" (
  set "PYTHON_EXE=%VENV_PY%"
) else if exist "%BUNDLED_PY%" (
  set "PYTHON_EXE=%BUNDLED_PY%"
) else (
  set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m streamlit run app.py --server.port 8501 --server.headless true
