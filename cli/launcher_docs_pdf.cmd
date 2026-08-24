@echo off
setlocal EnableExtensions
chcp 65001 >nul

title Audion DevOps Tools - Docs PDF Export

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "PYTHON_EXE=%BASE_DIR%\runtime\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo ======================================================================
echo   AUDION DEVOPS TOOLS - DOCS PDF EXPORT
echo ======================================================================
echo Output:
echo   %BASE_DIR%\docs\PDF
echo.
echo Uses the Audion Office OCR AI Markdown PDF engine with default layout.
echo.

"%PYTHON_EXE%" "%BASE_DIR%\system_core\docs_pdf.py" %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
  echo [OK] Done.
) else (
  echo [ERROR] Docs PDF export failed with exit code %EXIT_CODE%.
)
echo.
if not defined AUDION_NO_PAUSE pause
exit /b %EXIT_CODE%
