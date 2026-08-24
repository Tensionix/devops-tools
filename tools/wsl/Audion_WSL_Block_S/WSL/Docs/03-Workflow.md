# Typical workflow

## Fresh Windows 11 Pro 25H2 setup

```powershell
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

## Create a VHD backup

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "S:\WSL\Toolkit\Audion-WSL-Toolkit.ps1" -Action backup -Name Ubuntu -Format vhd
```

## Restore from a VHD backup

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "S:\WSL\Toolkit\Audion-WSL-Toolkit.ps1" -Action restorefrombackup -Name Ubuntu -Location "S:\WSL\VHDX\Ubuntu" -BackupFile "S:\WSL\Backup\Ubuntu\Ubuntu_YYYYMMDD-HHMMSS.vhdx"
```

## Register a live ext4.vhdx in place

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "S:\WSL\Toolkit\Audion-WSL-Toolkit.ps1" -Action importinplace -Name Ubuntu -VhdxPath "S:\WSL\VHDX\Ubuntu\ext4.vhdx"
```
