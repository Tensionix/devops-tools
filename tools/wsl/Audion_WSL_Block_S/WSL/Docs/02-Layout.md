# Layout and conventions

## Recommended layout

```text
S:\WSL\
├─ Backup\
├─ Docs\
├─ Logs\
├─ Toolkit\
└─ VHDX\
```

## Example distro locations

```text
S:\WSL\VHDX\Ubuntu\ext4.vhdx
S:\WSL\VHDX\Fedora\ext4.vhdx
```

## Example backup locations

```text
S:\WSL\Backup\Ubuntu\Ubuntu_YYYYMMDD-HHMMSS.vhdx
S:\WSL\Backup\Ubuntu\Ubuntu_YYYYMMDD-HHMMSS.tar
```

## Notes

- Keep `Backup` separate from live `VHDX` folders.
- `Register-All-WSL-VHDX.ps1` scans `VHDX` only.
- Logs are written to `Logs`.
- The toolkit uses relative paths so it can be mirrored between drives.
