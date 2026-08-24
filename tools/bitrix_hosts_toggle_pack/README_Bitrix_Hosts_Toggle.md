# Bitrix Hosts Toggle Pack

This pack manages only `portal.itpgrad.ru` in Windows hosts.

Backup behavior:
- A single rotating backup is used: `backup\hosts_backup.txt`
- Each change overwrites that one backup file
- Restore is manual: copy `backup\hosts_backup.txt` back to `C:\Windows\System32\drivers\etc\hosts` as Administrator

Main actions:
- Status
- Enable with custom IP
- Disable any IP
- Enable with `192.168.0.100`
- Disable only `192.168.0.100`
