# Default Apps Guard

Default Apps Guard protects Windows default app associations without editing
`UserChoice` registry values directly.

## Layers

- `Snapshot current defaults` exports the current DISM associations to
  `backup\default_apps\` without touching the profile XML.
- `Rescan / update profile` exports the current DISM associations to
  `profiles\default_apps\AppAssociations.xml` and keeps a timestamped backup.
- `Import profile XML` copies an external `AppAssociations.xml` into the managed
  profile path after backing up the previous profile.
- `Apply / repair policy` copies the profile XML to ProgramData, sets
  `HKLM\SOFTWARE\Policies\Microsoft\Windows\System\DefaultAssociationsConfiguration`
  and runs `gpupdate /force`.
- `Remove policy` removes the HKLM policy value and can optionally delete the
  inactive policy XML after backing it up.

## Rule

Do not hand-edit protected `UserChoice` hashes. Build or rescan a reference XML,
apply it as policy, then sign out/sign in or reboot.

Short user-facing guide with the exact fresh-Windows ritual and gotchas:
`docs\DEFAULT_APPS_GUARD_RU.md`.

## Official Boundary

The primary layer is documented Microsoft administrator/deployment behavior:

- DISM exports, lists, imports and removes default app associations.
- `DefaultAssociationsConfiguration` is the documented device policy for default
  file type and protocol associations.
- The policy registry path is
  `HKLM\SOFTWARE\Policies\Microsoft\Windows\System`.
- Microsoft documents this policy for Pro, Enterprise, Education and IoT
  Enterprise. Home/Core editions are treated as unsupported unless the explicit
  expert override is enabled.
- On Windows 11 22H2+, `Suggested="true"` means a suggested association is
  applied once for a policy version. Without it, the association is applied on
  every sign-in.

Current-user association snapshots are not part of this module. They live in
Association Defense, read `UserChoice\ProgId` straight from the registry, and
record state only - nothing writes the protected per-user hash.

References:

- <https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-applicationdefaults>
- <https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-default-application-association-servicing-command-line-options?view=windows-11>
- <https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/export-or-import-default-application-associations?view=windows-11>
