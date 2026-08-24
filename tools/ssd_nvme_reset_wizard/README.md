# Audion SSD / NVMe Reset Wizard

Native Windows helper for used SSD and NVMe drives.

This toolkit is meant for **non-system disks** that you want to inspect, clean, repartition, and prepare for reuse with stronger guardrails than raw DiskPart typing.

## Included files

- `Run-Audion-SSD-NVMe-Reset-Wizard.cmd`
- `Audion-SSD-NVMe-Reset-Wizard.ps1`

## What the tool can do

- show all disks with size, bus type, and state
- block the current system disk by default
- show partitions on the selected disk
- delete one selected partition with `delete partition override`
- run a fast reset with `DiskPart clean`
- run a slow zero-fill wipe with `DiskPart clean all`
- rebuild the disk as **GPT + one NTFS volume**
- save a log file in `logs\`

## Important reality check

For **SSD / NVMe** media, the phrase **"factory state"** is tricky.

### What this tool really does

`clean`
removes the partition table quickly

`clean all`
writes zeros across the whole device and takes much longer

### What this tool does not guarantee

It does **not** guarantee the same result as:

- vendor **Secure Erase**
- vendor **Sanitize**
- NVMe **Format / Sanitize**
- OPAL / PSID revert on self-encrypting drives

For SSD and NVMe drives, those vendor or controller-level methods are the closest thing to a real reset-to-factory workflow.

## Practical recommendation

Use this wizard when you want one of these:

### 1. Reuse a used SSD/NVMe for your own machine
Best mode:
- `Fast reset + rebuild as GPT + one NTFS volume`

This is quick and usually enough.

### 2. Deep wipe before resale or hand-off
Possible mode:
- `Full zero-fill wipe + rebuild`

But this is slower and adds wear on flash media.

### 3. Closest possible SSD reset
Best approach:
- use the manufacturer utility
- or boot Linux and use `nvme-cli` / vendor tools
- or use Secure Erase / Sanitize / PSID revert when supported

## Safety model

The wizard uses several guardrails:

- shows the selected disk before destructive steps
- requires typed confirmations
- blocks the detected system disk by default
- logs actions to a file
- uses English-only prompts for cleaner console behavior

## Notes

- Run it **as Administrator**
- Do not use it on the active Windows disk unless you intentionally remove the block and fully understand the consequences
- `clean all` can take a very long time
- On some USB enclosures, disk identity and feature support can be limited compared to direct SATA / NVMe attachment


## v4 fix

DiskPart command construction was hardened again. The wizard now builds an explicit command array before writing the temporary DiskPart script, which avoids accidental line collapsing such as `select disk 3 clean` or `select disk 3 clean all`. The log still dumps the generated script file for verification.
