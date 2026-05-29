@echo off
setlocal

cd /d "%~dp0"

set "BUNDLED_PY=C:\Users\darpa\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if exist "%BUNDLED_PY%" (
  set "PYTHON_EXE=%BUNDLED_PY%"
) else (
  set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" scripts\validate_links.py --mode broken --limit 25 --add-replacements
"%PYTHON_EXE%" scripts\validate_links.py --mode redirect --limit 25 --add-replacements
