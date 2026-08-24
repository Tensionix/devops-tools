# Audion DevOps Tools Addon: Windows Driver and Firmware Audit

This addon contains a safe, read-only diagnostic script for Windows driver and firmware validation.

It is designed for systems like ThinkPad X1 Carbon Gen 10 on Windows 11, but it remains generic enough to run on other Windows machines.

## Files

```text
system_core\diagnostics\Invoke-WindowsDriverFirmwareAudit.ps1
launcher_snippets\Run-Windows-Driver-Firmware-Audit.cmd
```

## What it checks

- present devices with non-OK status
- BIOS / Embedded Controller version
- BIOS registry information
- Windows firmware resources
- firmware resource details
- key signed drivers for ThinkPad/Intel/Realtek/Lenovo platform components

## Safety

This module is read-only.

It does not:

- flash firmware
- install drivers
- remove drivers
- change registry
- change Windows settings
- download anything
