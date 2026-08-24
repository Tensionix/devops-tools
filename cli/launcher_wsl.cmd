@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - WSL Toolkit

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

:MAIN
cls
echo ======================================================================
echo   AUDION DEVOPS TOOLS - WSL TOOLKIT
echo ======================================================================
echo Root: %BASE_DIR%
echo.
echo [1] System WSL2 status
echo [2] Enable WSL2 Windows features
echo [3] Update WSL engine
echo [4] Installable distro list
echo [5] Installed distro list
echo [6] wsl --status
echo [7] Shutdown WSL
echo [8] Install online distro
echo [9] Install from .wsl/tar/vhd/vhdx image
echo [A] Package update in distro
echo [B] Install Audion Dev packages in distro
echo [C] Install micro baseline
echo [D] Install MC skin
echo [E] Install Neovim base
echo [F] Register all VHDX - dry run
echo [0] Exit
echo.
choice /C 123456789ABCDEF0 /N /M "Select: "
if errorlevel 16 exit /b 0
if errorlevel 15 goto REGISTER_ALL_DRY
if errorlevel 14 goto NVIM_BASE
if errorlevel 13 goto MC_SKIN
if errorlevel 12 goto MICRO_BASE
if errorlevel 11 goto DEV_PACKAGES
if errorlevel 10 goto PACKAGE_UPDATE
if errorlevel 9 goto INSTALL_IMAGE
if errorlevel 8 goto INSTALL_ONLINE
if errorlevel 7 goto SHUTDOWN
if errorlevel 6 goto STATUS
if errorlevel 5 goto LIST_INSTALLED
if errorlevel 4 goto LIST_ONLINE
if errorlevel 3 goto UPDATE_ENGINE
if errorlevel 2 goto ENABLE_FEATURES
if errorlevel 1 goto SYSTEM_STATUS
goto MAIN

:SYSTEM_STATUS
call :RUN_OP wsl_system_status
if not defined AUDION_NO_PAUSE pause
goto MAIN

:ENABLE_FEATURES
echo This enables Windows WSL2/VirtualMachinePlatform features and may require reboot.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP wsl_enable_features --yes-i-understand
if not defined AUDION_NO_PAUSE pause
goto MAIN

:UPDATE_ENGINE
call :RUN_OP wsl_update_engine
if not defined AUDION_NO_PAUSE pause
goto MAIN

:LIST_ONLINE
call :RUN_OP wsl_list_online
if not defined AUDION_NO_PAUSE pause
goto MAIN

:LIST_INSTALLED
call :RUN_OP wsl_list
if not defined AUDION_NO_PAUSE pause
goto MAIN

:STATUS
call :RUN_OP wsl_status
if not defined AUDION_NO_PAUSE pause
goto MAIN

:SHUTDOWN
echo This stops all running WSL distributions.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP wsl_shutdown --yes-i-understand
if not defined AUDION_NO_PAUSE pause
goto MAIN

:INSTALL_ONLINE
set "DISTRO=Ubuntu-26.04"
set "INSTANCE_NAME="
set "INSTALL_LOCATION="
echo Default distro is Ubuntu-26.04. Press Enter to keep defaults.
set /p "DISTRO=Distro [Ubuntu-26.04]: "
if not defined DISTRO set "DISTRO=Ubuntu-26.04"
set /p "INSTANCE_NAME=Instance name [same as distro]: "
set /p "INSTALL_LOCATION=Install folder [bundle WSL default]: "
echo This installs/registers a WSL distro and writes into the selected install folder.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP wsl_install_distro --yes-i-understand --param "install_distro=%DISTRO%" --param "install_name=%INSTANCE_NAME%" --param "install_location=%INSTALL_LOCATION%" --param "install_location_mode=custom" --param "no_launch=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:INSTALL_IMAGE
set "IMAGE_FILE="
set "INSTANCE_NAME=Ubuntu-26.04"
set "INSTALL_LOCATION="
set /p "IMAGE_FILE=Image file (.wsl/.tar/.vhd/.vhdx): "
if not defined IMAGE_FILE goto MAIN
set /p "INSTANCE_NAME=Distro name [Ubuntu-26.04]: "
if not defined INSTANCE_NAME set "INSTANCE_NAME=Ubuntu-26.04"
set /p "INSTALL_LOCATION=Install folder [bundle WSL default]: "
echo This imports/registers a WSL distro from the selected image.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP wsl_install_from_file --yes-i-understand --param "install_image_file=%IMAGE_FILE%" --param "install_name=%INSTANCE_NAME%" --param "install_location=%INSTALL_LOCATION%" --param "no_launch=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:PACKAGE_UPDATE
call :ASK_DISTRO
if not defined WSL_NAME goto MAIN
call :RUN_OP wsl_linux_apt_update --param "wsl_name_override=%WSL_NAME%" --param "wsl_apt_upgrade=none"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:DEV_PACKAGES
call :ASK_DISTRO
if not defined WSL_NAME goto MAIN
echo This installs the manifest default baseline packages. Heavy/Desktop groups are not selected.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP wsl_linux_dev_packages --yes-i-understand --param "wsl_name_override=%WSL_NAME%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:MICRO_BASE
call :ASK_DISTRO_AND_USER
if not defined WSL_NAME goto MAIN
call :RUN_OP wsl_micro_baseline --param "wsl_name_override=%WSL_NAME%" --param "linux_username=%LINUX_USER%"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:MC_SKIN
call :ASK_DISTRO_AND_USER
if not defined WSL_NAME goto MAIN
call :RUN_OP wsl_mc_skin --param "wsl_name_override=%WSL_NAME%" --param "linux_username=%LINUX_USER%" --param "mc_skin=electricblue256" --param "mc_apply_skin=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:NVIM_BASE
call :ASK_DISTRO_AND_USER
if not defined WSL_NAME goto MAIN
echo This writes an Audion Neovim profile in the selected WSL user's config.
choice /C YN /N /M "Continue? [Y/N]: "
if errorlevel 2 goto MAIN
call :RUN_OP wsl_neovim_base --yes-i-understand --param "wsl_name_override=%WSL_NAME%" --param "linux_username=%LINUX_USER%" --param "nvim_appname=audion-ide" --param "nvim_profile=lite"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:REGISTER_ALL_DRY
set "REGISTER_ROOT="
set /p "REGISTER_ROOT=VHDX root [bundle WSL\\VHDX]: "
call :RUN_OP wsl_register_all_vhdx --yes-i-understand --param "register_root=%REGISTER_ROOT%" --param "filter=ext4.vhdx" --param "dry_run=true"
if not defined AUDION_NO_PAUSE pause
goto MAIN

:ASK_DISTRO
set "WSL_NAME="
set /p "WSL_NAME=WSL distro name: "
exit /b 0

:ASK_DISTRO_AND_USER
call :ASK_DISTRO
set "LINUX_USER=audion"
set /p "LINUX_USER=Linux user [audion]: "
if not defined LINUX_USER set "LINUX_USER=audion"
exit /b 0

:RUN_OP
call :RESOLVE_PYTHON || exit /b 1
"%PYTHON_CMD%" %PYTHON_ARGS% "%BASE_DIR%\system_core\cli_operation.py" %*
exit /b %ERRORLEVEL%

:RESOLVE_PYTHON
set "PYTHON_CMD="
set "PYTHON_ARGS="
if exist "%BASE_DIR%\runtime\python.exe" set "PYTHON_CMD=%BASE_DIR%\runtime\python.exe" & exit /b 0
if exist "%BASE_DIR%\runtime\python\python.exe" set "PYTHON_CMD=%BASE_DIR%\runtime\python\python.exe" & exit /b 0
py -3.12 -V >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py" & set "PYTHON_ARGS=-3.12" & exit /b 0
where python.exe >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python.exe" & exit /b 0
echo [ERROR] Python runtime was not resolved.
exit /b 1
