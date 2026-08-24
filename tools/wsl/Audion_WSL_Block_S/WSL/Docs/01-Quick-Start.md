# Quick start for S:\WSL

## 1. Extract

Extract this archive so the final path is:

`S:\WSL`

## 2. Install Ubuntu to the custom location

Run in an elevated PowerShell window:

```powershell
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

After install, restart if Windows asks for it, then verify:

```powershell
wsl --status
wsl -l -v
```

## 3. Backup

Double-click:

- `Toolkit\RUN_WSL_BACKUP_PROMPT.cmd`

Choose `tar` for portable export or `vhd` for a VHDX backup.

Backups are stored under:

`S:\WSL\Backup\<DistroName>\`

## 4. Restore from a backup on a new system

Double-click:

- `Toolkit\RUN_WSL_RESTORE_FROM_BACKUP_PROMPT.cmd`

Recommended target layout:

`S:\WSL\VHDX\Ubuntu`

## 5. Register an existing ext4.vhdx in place

If you already have a live `ext4.vhdx`, use:

- `Toolkit\RUN_WSL_IMPORT_IN_PLACE_PROMPT.cmd`

Or bulk scan/register:

- `Toolkit\RUN_WSL_REGISTER_ALL_VHDX.cmd`
