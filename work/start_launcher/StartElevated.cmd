@echo off
chcp 65001 >nul
setlocal EnableExtensions
set "AUDION_APP_NAME=Audion DevOps Tools"
set "AUDION_APP_ID=Audion.Tools.Audion.DevOps.Tools"
set "AUDION_GUI_ELEVATE=1"
set "AUDION_APP_ICON=E:\Audion DevOps Tools\system_core\icons\app.ico"
call "E:\Audion DevOps Tools\launcher_gui.cmd"
exit /b %ERRORLEVEL%
