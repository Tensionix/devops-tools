# Btrfs + Timeshift For Ubuntu: Separate Storage Guide

English companion to `Btrfs_Timeshift_Ubuntu_LiveUSB_Guide_RU.md`.

This document is intentionally separate from the DevOps/package-install layer.

It covers only:

- choosing the target SSD/NVMe;
- GPT + EFI + Btrfs;
- subvolumes `@` and `@home`;
- mount option meaning;
- when to do this from Live USB and when it is already late and painful.

## 1. What Is Separate From The "All-In-One" Installer

Storage layer:

- GPT;
- EFI;
- Btrfs;
- subvolumes;
- mount options;
- Timeshift.

DevOps/install layer:

- packages;
- NVIDIA step;
- terminal/dev/media layers;
- baseline directories such as `~/Terminal`, `~/Projects`, `~/Apps`, `~/Sync`, `~/Media`, `~/Vault`, `~/Lab`.

Storage is the foundation. Packages and profiles can be rolled back or reinstalled. Disk layout and root filesystem structure are more fundamental.

## 2. Minimal Layout

For a 256 GB SSD, start simple:

- EFI System Partition - 512 MiB, FAT32;
- Btrfs partition - the rest of the disk.

Inside Btrfs:

- `@` -> `/`;
- `@home` -> `/home`.

No `@var`, `@snapshots`, `@cache`, or `@docker` on the first pass.

## 3. Why This Layout

`subvol=@` or `subvol=@home` tells Linux which Btrfs subvolume to mount.

`compress=zstd` enables transparent Btrfs compression: fast, usually space-saving, and normally fine for desktop work.

`noatime` avoids constant access-time writes on reads, reducing unnecessary SSD/NVMe write activity.

## 4. Best Time To Do It

Best moment: before installing Ubuntu, from Live USB.

After installation, the same change becomes a migration/rescue task: moving root, editing `fstab`, watching EFI/initramfs/grub, and avoiding boot confusion.

## 5. Recommended Workflow

1. Boot Ubuntu Live USB.
2. Confirm the target disk.
3. Run the prep script.
4. The script wipes the target, creates GPT, EFI, Btrfs, `@`, and `@home`, then mounts them under `/mnt`.
5. Start the Ubuntu installer.
6. Choose manual partitioning.
7. Use the prepared partitions and mount points.
8. Install Timeshift after the first boot.

## 6. What The Prep Script Does

File:

```text
Ubuntu_Btrfs_LU_Prep_NVMe.sh
```

It:

- lists disks;
- asks for the target SSD/NVMe;
- requires typed confirmation;
- removes old partitioning;
- creates EFI 512 MiB and a Btrfs data partition;
- formats EFI as FAT32 and data as Btrfs;
- creates `@` and `@home`;
- mounts `@` to `/mnt`, `@home` to `/mnt/home`, EFI to `/mnt/boot/efi`.

The script does not install Ubuntu. That boundary is intentional.

## 7. Why Installation Stays Manual

Automating partition and mount preparation is useful. Automating the entire Ubuntu install flow is riskier, especially across hardware and installer versions.

Correct boundary:

- prep script prepares disk and mount targets;
- Ubuntu installer installs the system;
- post-install kit installs packages, baseline, NVIDIA, and user tooling.

## 8. Timeshift After Install

After Ubuntu installation:

```bash
sudo apt update
sudo apt install timeshift
```

Start Timeshift and choose BTRFS mode.

## 9. Safety

This workflow is destructive for the selected disk. Confirm the target disk carefully. Do not run it against a disk that contains data you need.
