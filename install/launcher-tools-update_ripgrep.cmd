@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Update ripgrep

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%A in ("%SCRIPT_DIR%\..") do set "ROOT=%%~fA"

set "DL=%ROOT%\install\download"
set "RG_DIR=%ROOT%\ripgrep"
set "TMP=%DL%\_ripgrep_tmp"
set "ZIP=%DL%\ripgrep_windows_x64.zip"
set "PS_EXE="

if exist "%ROOT%\system_core\powershell\pwsh.exe" set "PS_EXE=%ROOT%\system_core\powershell\pwsh.exe"
if not defined PS_EXE where pwsh.exe >nul 2>nul && set "PS_EXE=pwsh.exe"
if not defined PS_EXE where powershell.exe >nul 2>nul && set "PS_EXE=powershell.exe"

if not exist "%DL%\" mkdir "%DL%" >nul 2>nul
if not exist "%RG_DIR%\" mkdir "%RG_DIR%" >nul 2>nul

echo ======================================================================
echo   AUDION DEVOPS TOOLS - UPDATE RIPGREP
echo ======================================================================
echo Root:    %ROOT%
echo Install: %SCRIPT_DIR%
echo DL:      %DL%
echo ripgrep: %RG_DIR%
echo.

if not defined PS_EXE goto ERR_POWERSHELL

echo [1/4] Resolving URL and downloading ZIP...
"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$zip='%ZIP%';" ^
  "$headers=@{'User-Agent'='Audion-DevOps-Tools'}; if($env:GITHUB_TOKEN){$headers['Authorization']='Bearer '+$env:GITHUB_TOKEN};" ^
  "$repo='https://github.com/BurntSushi/ripgrep'; $api='https://api.github.com/repos/BurntSushi/ripgrep/releases/latest'; $url=$null; $tag=$null; $downloaded=$false;" ^
  "try { $resp=$null; try { $resp=Invoke-WebRequest -Uri ($repo + '/releases/latest') -Headers $headers -MaximumRedirection 0 -ErrorAction Stop } catch { $resp=$_.Exception.Response }; $loc=$null; if($resp){ if($resp.Headers.Location){ $loc=[string]$resp.Headers.Location } elseif($resp.Headers['Location']){ $loc=[string]$resp.Headers['Location'] } }; if(-not $loc -or $loc -notmatch '/tag/(?<tag>v?[0-9][^/]+)$'){ throw 'Could not resolve latest ripgrep release tag without API.' }; $tag=$Matches.tag; $version=$tag.TrimStart('v'); $url=($repo + '/releases/download/' + $tag + '/ripgrep-' + $version + '-x86_64-pc-windows-msvc.zip'); Write-Host ('[INFO] Resolved through releases/latest redirect: ' + $tag) } catch { Write-Host ('[WARN] releases/latest resolver unavailable, using GitHub API: ' + $_.Exception.Message) };" ^
  "if($url){ try { Write-Host ('[URL] ' + $url); Invoke-WebRequest -Uri $url -Headers $headers -OutFile $zip; $downloaded=$true; Write-Host '[INFO] Direct release download succeeded.' } catch { Write-Host ('[WARN] Direct asset URL failed, using GitHub API: ' + $_.Exception.Message); $url=$null; Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue } };" ^
  "if(-not $url){ $r=Invoke-RestMethod -Headers $headers $api; $tag=$r.tag_name; $a=$null; foreach($item in $r.assets){ if($item.name -match '^ripgrep-.+-x86_64-pc-windows-msvc\.zip$'){ $a=$item; break } }; if(-not $a){ throw 'Asset not found: ripgrep x86_64-pc-windows-msvc.zip' }; $url=($a.browser_download_url).Trim(); Write-Host '[INFO] Resolved through GitHub API fallback.' };" ^
  "Write-Host ('[URL] ' + $url);" ^
  "Write-Host ('[VER] ' + $tag);" ^
  "if(-not $downloaded){ Invoke-WebRequest -Uri $url -Headers $headers -OutFile $zip }"
if errorlevel 1 goto ERR_DOWNLOAD

if not exist "%ZIP%" goto ERR_DOWNLOAD
for %%F in ("%ZIP%") do echo [OK] Downloaded: %%~zF bytes
echo.

echo [2/4] Extracting archive...
if exist "%TMP%" rd /s /q "%TMP%" >nul 2>nul
mkdir "%TMP%" >nul 2>nul

"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "Expand-Archive -Path '%ZIP%' -DestinationPath '%TMP%' -Force"
if errorlevel 1 goto ERR_EXTRACT

echo [3/4] Installing into project ripgrep folder...
"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$tmp='%TMP%'; $dest='%RG_DIR%';" ^
  "$rg=Get-ChildItem -LiteralPath $tmp -Filter 'rg.exe' -Recurse -File | Select-Object -First 1;" ^
  "if(-not $rg){ throw 'rg.exe was not found after extract.' }" ^
  "$src=$rg.Directory.FullName;" ^
  "New-Item -ItemType Directory -Force -Path $dest | Out-Null;" ^
  "Get-ChildItem -LiteralPath $dest -Force | Remove-Item -Force -Recurse;" ^
  "Copy-Item -Path (Join-Path $src '*') -Destination $dest -Recurse -Force"
if errorlevel 1 goto ERR_COPY
rem No .gitkeep here: the folder is filled by this step, so it is never empty,
rem and install\init_folders.cmd owns the empty structure.

echo [4/4] Verifying rg.exe...
"%RG_DIR%\rg.exe" --version > "%TMP%\rg_version.txt" 2>nul
if errorlevel 1 goto ERR_VERIFY
set "RG_VERSION="
set /p RG_VERSION=<"%TMP%\rg_version.txt"
if not defined RG_VERSION goto ERR_VERIFY
echo %RG_VERSION% | findstr /B /I /C:"ripgrep " >nul
if errorlevel 1 goto ERR_VERIFY

rd /s /q "%TMP%" >nul 2>nul

echo.
echo [SUCCESS] ripgrep updated: %RG_DIR%\rg.exe
echo [VERSION] %RG_VERSION%
if not defined AUDION_NO_PAUSE pause
exit /b 0

:ERR_POWERSHELL
echo [ERROR] PowerShell was not found.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:ERR_DOWNLOAD
echo [ERROR] Download failed.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:ERR_EXTRACT
echo [ERROR] Extract failed.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:ERR_COPY
echo [ERROR] Install/copy failed.
if not defined AUDION_NO_PAUSE pause
exit /b 1

:ERR_VERIFY
echo [ERROR] rg.exe verification failed.
if not defined AUDION_NO_PAUSE pause
exit /b 1
