# Audion Disk Removable

Wipe a removable drive and lay one partition across it.

For flash drives and external disks whose partition table is broken: zero-sized partitions, "unallocated" across the whole device, leftovers of a previous Windows installer. Disk Management fixes that through several dialogs; this does it in one step.

## Included files

- `Run-Audion-Disk-Removable.cmd`
- `Audion-Disk-Removable.ps1`

## What the tool does

- lists every disk with number, model, bus type, size, partition style, and drive letters
- marks the system disk in red, USB drives in green
- asks which disk number to wipe
- asks that disk's size in gigabytes as confirmation
- runs `Clear-Disk`, creates one partition across the whole device, formats it
- reports the resulting drive letter, label, and free space

## Named on purpose, twice

The disk is named twice: first by number, then by size.

A disk number changes between plug-ins — today the flash drive is disk 2, tomorrow disk 3, and a typo there wipes something else. Size belongs to the device itself, so a wrong number will almost always disagree with the size you typed, and the tool stops before touching anything.

There is no model whitelist. Any disk can be wiped, including the system one — the size check is the only gate, and it is deliberate.

## Usage

Double-click `Run-Audion-Disk-Removable.cmd`. It asks for administrator rights itself, then asks the two questions.

Or pass everything up front:

```
Run-Audion-Disk-Removable.cmd -Disk 2 -SizeGb 28.48 -Label ARCHIVE -FileSystem NTFS
```

| switch | meaning |
| --- | --- |
| `-Disk` | disk number; omitted — the tool asks |
| `-SizeGb` | that disk's size in GB, for confirmation; omitted — the tool asks |
| `-FileSystem` | `exFAT` (default), `NTFS`, `FAT32` |
| `-Label` | volume label, `AUDION` by default |
| `-Style` | `MBR` (default) or `GPT`; GPT for drives above two terabytes |

## What it does not do

It does not erase data securely. `Clear-Disk` removes the partition table; the contents stay on the medium until overwritten. For a used SSD or NVMe drive that you want wiped rather than repartitioned, use `ssd_nvme_reset_wizard` next door — it has `clean all` and a discussion of what "factory state" really means.
