param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"

$installDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $installDir
$downloadDir = Join-Path $installDir "download"
$runtimeDir = Join-Path $rootDir "runtime"
$wheelhouseDir = Join-Path $rootDir "wheelhouse"
$requirementsFile = Join-Path $installDir "requirements_full.in"
$doctorScript = Join-Path $rootDir "system_core\doctor.py"
$guiSmokeScript = Join-Path $rootDir "system_core\ui_nicegui\app.py"
$cmdEncodingScript = Join-Path $installDir "Repair-CmdEncoding.ps1"

$pythonMinor = 12
$headers = @{ 'User-Agent' = 'Audion-Portable-Installer' }
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$getPipPath = Join-Path $downloadDir "get-pip.py"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

function Get-NormalizedPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}

function Assert-OutsideBackup {
    param(
        [Parameter(Mandatory = $true)][string]$RootDir,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    $backupPath = Get-NormalizedPath (Join-Path $RootDir "backup")
    $target = Get-NormalizedPath $TargetPath
    $backupPrefix = $backupPath + [System.IO.Path]::DirectorySeparatorChar
    if ($target -eq $backupPath -or $target.StartsWith($backupPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label points inside protected backup folder: $target"
    }
}

function Confirm-PortableRebuild {
    param(
        [Parameter(Mandatory = $true)][string]$RootDir,
        [Parameter(Mandatory = $true)][string]$RuntimeDir,
        [Parameter(Mandatory = $true)][string]$WheelhouseDir,
        [Parameter(Mandatory = $true)][string]$DownloadDir
    )

    Assert-OutsideBackup -RootDir $RootDir -TargetPath $RuntimeDir -Label "Runtime"
    Assert-OutsideBackup -RootDir $RootDir -TargetPath $WheelhouseDir -Label "Wheelhouse"
    Assert-OutsideBackup -RootDir $RootDir -TargetPath $DownloadDir -Label "Download cache"

    if ($Yes) {
        Write-Host "[SAFETY] /Y supplied: runtime and wheelhouse rebuild confirmed."
        return
    }

    Write-Host "[SAFETY] Project backup is protected and will not be cleaned by this build:"
    Write-Host "         $(Join-Path $RootDir 'backup')"
    Write-Host "[SAFETY] This rebuild overwrites generated install areas:"
    Write-Host "         $RuntimeDir"
    Write-Host "         $WheelhouseDir"
    Write-Host "         $DownloadDir"
    while ($true) {
        $rawAnswer = Read-Host "Proceed with portable environment rebuild? [Y/N/Q]"
        if ($null -eq $rawAnswer) {
            Write-Host "[CANCELLED] No answer was provided. Nothing was changed."
            exit 0
        }
        $answer = $rawAnswer.Trim().ToUpperInvariant()
        switch ($answer) {
            "Y" { return }
            "N" {
                Write-Host "[CANCELLED] Nothing was changed."
                exit 0
            }
            "Q" {
                Write-Host "[QUIT] Nothing was changed."
                exit 0
            }
            default { Write-Host "Please answer Y, N or Q." }
        }
    }
}

Write-Host "======================================================================"
Write-Host "AUDION DEVOPS TOOLS - BUILD PORTABLE ENV (PS)"
Write-Host "======================================================================"
Write-Host "Root:        $rootDir"
Write-Host "Install:     $installDir"
Write-Host "Download:    $downloadDir"
Write-Host "Runtime:     $runtimeDir"
Write-Host "Wheelhouse:  $wheelhouseDir"
Write-Host ""

Confirm-PortableRebuild -RootDir $rootDir -RuntimeDir $runtimeDir -WheelhouseDir $wheelhouseDir -DownloadDir $downloadDir

New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
New-Item -ItemType Directory -Force -Path $wheelhouseDir | Out-Null

Write-Host "[0/7] Normalizing project CMD files..."
if (-not (Test-Path $cmdEncodingScript)) {
    throw "Missing file: $cmdEncodingScript"
}
& $cmdEncodingScript -Root $rootDir -Fix

$pyPatch = -1
for ($i = 0; $i -le 40; $i++) {
    $uri = "https://www.python.org/ftp/python/3.$pythonMinor.$i/python-3.$pythonMinor.$i-embed-amd64.zip"
    try {
        Invoke-WebRequest -Headers $headers -Uri $uri -Method Head -TimeoutSec 10 | Out-Null
        $pyPatch = $i
    } catch {
        if ($pyPatch -ge 0) { break }
    }
}
if ($pyPatch -lt 0) { throw "Could not resolve any Python 3.$pythonMinor.x embed-amd64 build" }
$pythonVersion = "3.$pythonMinor.$pyPatch"
$pythonZipName = "python-$pythonVersion-embed-amd64.zip"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/$pythonZipName"
$pythonZipPath = Join-Path $downloadDir $pythonZipName

Write-Host "[1/7] Downloading Python Embedded..."
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZipPath

Write-Host "[2/7] Extracting runtime..."
if (Test-Path $runtimeDir) {
    Get-ChildItem -Force $runtimeDir | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
}
Expand-Archive -Path $pythonZipPath -DestinationPath $runtimeDir -Force

Write-Host "[3/7] Enabling import site..."
$pthFile = Join-Path $runtimeDir "python3$pythonMinor._pth"
if (-not (Test-Path $pthFile)) {
    throw "Missing file: $pthFile"
}
(Get-Content $pthFile) -replace '^#import site$', 'import site' | Set-Content $pthFile -Encoding ASCII

Write-Host "[4/7] Downloading get-pip.py..."
# A dropped connection here used to kill the whole project build.
$getPipOk = $false
foreach ($getPipTry in 1..5) {
    $getPipTmp = "$($getPipPath).part"
    try {
        Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipTmp -TimeoutSec 120 -UseBasicParsing
        $getPipSize = (Get-Item -LiteralPath $getPipTmp).Length
        if ($getPipSize -lt 1000000) { throw "truncated body: $getPipSize bytes" }
        Move-Item -LiteralPath $getPipTmp -Destination $getPipPath -Force
        $getPipOk = $true
        break
    } catch {
        Write-Host "  get-pip.py attempt $getPipTry failed: $($_.Exception.Message)"
        Remove-Item -LiteralPath $getPipTmp -Force -ErrorAction SilentlyContinue
        if ($getPipTry -lt 5) { Start-Sleep -Seconds (3 * $getPipTry) }
    }
}
if (-not $getPipOk) { throw "Could not download get-pip.py after 5 attempts - the network dropped every time." }
$pythonExe = Join-Path $runtimeDir "python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Missing file: $pythonExe"
}

Write-Host "[5/7] Installing pip..."
Invoke-Checked -Label "Installing pip" -Command { & $pythonExe $getPipPath }

Write-Host "[6/7] Building wheelhouse and installing packages..."
Get-ChildItem -Force $wheelhouseDir |
    Where-Object { $_.Name -ne ".gitkeep" } |
    Remove-Item -Force -Recurse
Invoke-Checked -Label "Installing build bootstrap" -Command {
    & $pythonExe -m pip install --disable-pip-version-check --upgrade setuptools wheel packaging
}
Invoke-Checked -Label "Building wheelhouse" -Command {
    & $pythonExe -m pip wheel --disable-pip-version-check --prefer-binary --no-build-isolation --timeout 120 --retries 12 -r $requirementsFile -w $wheelhouseDir
}
Invoke-Checked -Label "Installing packages" -Command {
    & $pythonExe -m pip install --disable-pip-version-check --no-build-isolation --no-index --find-links=$wheelhouseDir -r $requirementsFile
}

Write-Host "[7/7] Verifying environment..."
Invoke-Checked -Label "Verifying environment" -Command { & $pythonExe $doctorScript --project-root $rootDir }
if (Test-Path $guiSmokeScript) {
    Invoke-Checked -Label "Verifying NiceGUI smoke" -Command { & $pythonExe $guiSmokeScript --smoke }
}

Write-Host ""
Write-Host "[SUCCESS] Portable environment is ready."
Write-Host "[INFO] Release licensing is generated later from the finalized release contents."
