# Audion WSL Block (S:\WSL target)

This archive is meant to be extracted as `S:\WSL`.

Structure:

- `Backup` — exported `.tar` / `.vhd` / `.vhdx` backups
- `Docs` — guides and notes
- `Logs` — operation logs created by the toolkit
- `Toolkit` — PowerShell and CMD host tools for WSL
- `VHDX` — live distro storage such as `Ubuntu\ext4.vhdx`

The Toolkit is path-relative:

- backups default to `..\Backup`
- VHDX scan defaults to `..\VHDX`
- logs default to `..\Logs`

So the same toolkit works when placed in either `S:\WSL\Toolkit` or `E:\WSL\Toolkit`.
