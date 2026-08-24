OpenSSH KeyKit (Windows)

Included:
- Export-OpenSSHKeys.ps1
- Import-OpenSSHKeys.ps1
- Test-SSHAccessLinks.ps1
- wrappers\keykit.cmd (menu)
- wrappers\check-links.cmd
- wrappers\export-client.cmd
- wrappers\export-all-admin.cmd
- wrappers\import-client.cmd
- wrappers\import-all-admin.cmd

Portable PowerShell detection:
- S:\Audion\Tools\PowerShell\pwsh.exe
- E:\Audion\Tools\PowerShell\pwsh.exe
- fallback: pwsh.exe in PATH

Default RootDir:
- export: <program>\output\ssh_keykit
- import: <program>\input
- both can be overridden by the first wrapper argument or by the GUI field

Snapshot layout inside RootDir:
RootDir\<COMPUTERNAME>\users\<USERNAME>\<timestamp>\client\...
RootDir\<COMPUTERNAME>\_server\<timestamp>\...

Notes:
- Export/Import server host keys requires Administrator.
- Client keys are taken from the current user profile: %USERPROFILE%\.ssh

Access link check:
- Test-SSHAccessLinks.ps1 reads ssh config and rclone.conf and reports every
  IdentityFile, UserKnownHostsFile, ProxyCommand target, key_file and
  known_hosts_file that no longer exists.
- Nothing is copied or changed; the check only reads.
- Exit code 1 when a path is missing, unless -FailOnBroken:$false.
- Optional -ReportPath writes the same table as CSV.

Why it exists:
- Access breaks quietly. Keys and configuration files stay where they are, and
  only the paths inside them stop matching reality. Every file involved still
  exists, so nothing looks wrong until the first connection of the day fails.
