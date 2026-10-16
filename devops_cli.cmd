@echo off
setlocal EnableExtensions
chcp 65001 >nul

rem Audion DevOps Tools: the console command. A button of the window and this command run the
rem same thing - an operation of the manifest, with the parameters the window gives it.
rem
rem   devops_cli.cmd describe
rem   devops_cli.cmd run --operation dns_status
rem   devops_cli.cmd run --operation network_wifi_connect --set wifi_profile=Home
rem   devops_cli.cmd check --operation network_standard_repair
rem   devops_cli.cmd options --operation network_wifi_connect --field wifi_adapter
rem   devops_cli.cmd state --page link
rem
rem Exit codes: 0 done, 1 the operation failed, 2 wrong call, 130 stopped.
rem
rem The folder of the caller stays the current one: a relative --params, --result or
rem --cancel-file is counted from it. A relative --source or --target is counted from
rem the program folder - the command does that itself.

set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

set "PYTHON_CMD="
if exist "%BASE_DIR%\runtime\python.exe" set "PYTHON_CMD=%BASE_DIR%\runtime\python.exe"
if not defined PYTHON_CMD if exist "%BASE_DIR%\runtime\python\python.exe" set "PYTHON_CMD=%BASE_DIR%\runtime\python\python.exe"
rem Not a block in brackets: a path with a bracket in it - "Program Files (x86)" - would close it.
if not defined PYTHON_CMD goto NO_PYTHON

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
"%PYTHON_CMD%" -u "%BASE_DIR%\system_core\cli.py" %*
exit /b %ERRORLEVEL%

:NO_PYTHON
echo [ERR] Python of the project was not found: "%BASE_DIR%\runtime\python.exe"
echo       Build the environment first: builder_main.cmd
exit /b 2
