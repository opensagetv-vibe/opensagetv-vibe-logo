@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE="
where py >nul 2>nul && set "PYTHON_EXE=py -3"
if not defined PYTHON_EXE (
  where python >nul 2>nul && set "PYTHON_EXE=python"
)
if not defined PYTHON_EXE (
  echo ERROR: Python was not found in PATH.
  exit /b 1
)

set "SVG_FILE=%~1"
if "%SVG_FILE%"=="" set "SVG_FILE=SageTV_VIBE_512_V3.svg"

if not exist "%SVG_FILE%" (
  echo ERROR: SVG file not found: "%SVG_FILE%"
  exit /b 1
)

%PYTHON_EXE% "%~dp0sagetv_logo_generator.py" "%SVG_FILE%" --config "%~dp0sagetv_logo.ini" --disable-local-fonts %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%
