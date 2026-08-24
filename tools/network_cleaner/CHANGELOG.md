# Changelog

## v2 TimeMachine

- Added TimeMachine restore modes.
- Added selectable snapshot restore.
- Added pre-restore backup of current broken state.
- Added `netsh -c interface dump` capture and restore.
- Added binary `hosts` backup and SHA256 logs.
- Added firewall `.wfw` import during restore.
- Added optional sensitive Wi-Fi profile backup with clear keys.
- Added final `Godzilla Strike` mode with separate confirmations for firewall reset, Wi-Fi profile deletion, and `netcfg -d`.
