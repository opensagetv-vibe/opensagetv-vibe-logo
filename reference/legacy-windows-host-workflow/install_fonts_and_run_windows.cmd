@echo off
setlocal
cd /d "%~dp0"

call "%~dp0install_mplus_fonts_current_user.cmd"
if errorlevel 1 exit /b %errorlevel%

call "%~dp0run_sagetv_logo_generator_windows.cmd" %*
exit /b %errorlevel%
