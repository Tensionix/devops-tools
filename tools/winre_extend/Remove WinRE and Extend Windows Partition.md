# Remove WinRE Partition and Extend C: — Manual Guide + Safe PowerShell Script

## Purpose

This guide describes the exact manual steps we performed:

- checked where Windows Recovery Environment (WinRE) is stored
- confirmed that the recovery partition is the current WinRE partition
- disabled WinRE
- deleted the recovery partition
- extended the system partition `C:` into the freed space

A PowerShell script and a CMD wrapper are also included for a more reusable and safer workflow on other PCs.

---

## Included files

- `Remove-WinRE-And-Extend-System.ps1` — main PowerShell script
- `Run-Remove-WinRE-And-Extend-System.cmd` — simple launcher for people who just want to click and run
- `README_Remove_WinRE_and_Extend_C.md` — this guide

---

## Important clarification

The **Recovery** partition is **not** the same thing as:

- System Restore points
- Windows backup history
- your personal backup strategy

In this case it stores **WinRE** — the built-in Windows Recovery Environment.

WinRE is used for things like:

- advanced boot recovery options
- automatic startup repair
- some rollback scenarios after failed updates
- parts of “Reset this PC”

If you delete the WinRE partition:

- Windows will still boot and work normally
- your files stay intact
- but built-in recovery features become unavailable until WinRE is recreated

This is usually acceptable only if you are comfortable relying on:

- a Windows installation USB stick
- your own backup/image tools
- manual recovery methods

---

## Example layout from our case

The actual partition layout on the system disk was:

- Partition 1 — **System** — 100 MB
- Partition 2 — **Reserved (MSR)** — 16 MB
- Partition 3 — **Primary** — `C:`
- Partition 4 — **Recovery** — 917 MB

`reagentc /info` confirmed that WinRE was stored on:

`harddisk0\partition4`

That means the **917 MB recovery partition was the active WinRE partition**.

---

## Safety notes before doing this manually

Before removing a recovery partition manually, make sure that:

- you are running the shell **as Administrator**
- you have a **Windows installation USB stick** or another bootable rescue medium
- you understand that the built-in Windows recovery environment will be removed
- BitLocker / Device Encryption is **suspended or not in use**
- you do **not** delete the EFI/System partition
- you do **not** delete the Microsoft Reserved partition

On GPT disks, the small partitions commonly look like this:

- EFI/System — often around 100 MB
- MSR — usually 16 MB
- OS partition — your main `C:` partition
- Recovery — often several hundred MB to ~1 GB

---

## Step 1 — Check current WinRE location

Run:

```powershell
reagentc /info
```

In our case, the output showed:

```text
Windows RE location: \\?\GLOBALROOT\device\harddisk0\partition4\Recovery\WindowsRE
```

This told us exactly which partition was currently used by WinRE.

---

## Step 2 — Disable WinRE

Run:

```powershell
reagentc /disable
```

Then verify:

```powershell
reagentc /info
```

Expected result:

```text
Windows RE status: Disabled
```

This is the correct preparation step before deleting the recovery partition.

---

## Step 3 — Inspect disk and partition numbers

Run:

```text
diskpart
```

Then:

```text
list disk

select disk 0

list partition
```

In our case the result was:

```text
Partition 1  System        100 MB
Partition 2  Reserved       16 MB
Partition 3  Primary       464 GB
Partition 4  Recovery      917 MB
```

### Why this matters

This step confirms:

- which physical disk is the system disk
- which partition is `C:`
- which partition is the recovery partition
- that the recovery partition is located **to the right of `C:`**, so `C:` can be extended after deletion

---

## Step 4 — Delete only the WinRE recovery partition

Still inside `diskpart`, select the recovery partition:

```text
select partition 4
```

Delete it:

```text
delete partition override
```

### Important

Do **not** delete:

- `Partition 1` — System / EFI
- `Partition 2` — Reserved / MSR
- `Partition 3` — Primary / `C:`

Only the recovery partition should be deleted.

---

## Step 5 — Extend C:

Still inside `diskpart`, select the system partition:

```text
select partition 3
```

Then extend it:

```text
extend
```

After that, exit DiskPart:

```text
exit
```

This uses the newly freed space from the deleted recovery partition.

---

## Step 6 — Final verification

Check WinRE again:

```powershell
reagentc /info
```

Expected status:

```text
Windows RE status: Disabled
```

Then optionally open Disk Management:

```powershell
diskmgmt.msc
```

You should see that `C:` now occupies the freed space.

---

## What was achieved in this exact case

The operation was completed successfully:

- WinRE was disabled correctly
- the 917 MB recovery partition was deleted correctly
- the `C:` partition was extended successfully
- EFI and MSR partitions were left untouched

This is the correct outcome for the layout we had.

---

## Why a fully hardcoded script is a bad idea

Using a raw DiskPart script with fixed values like:

- `select disk 0`
- `select partition 4`

is unsafe for reuse because on another PC:

- the system disk may not be disk 0
- the WinRE partition may not be partition 4
- there may be another partition between `C:` and Recovery
- WinRE may already be disabled
- the recovery partition may be on a different disk
- BitLocker may still be active

That is why the PowerShell script does **auto-detection** instead of trusting fixed numbers.

---

## What the PowerShell script does

The script:

- detects the current system drive automatically
- detects the disk and partition of `C:`
- reads `reagentc /info`
- detects the current WinRE partition if WinRE is enabled
- prints the current partition list for the Windows disk
- checks that WinRE and `C:` are on the same disk
- checks that the WinRE partition is to the right of `C:`
- checks that there are no partitions between `C:` and WinRE
- checks BitLocker status if the BitLocker cmdlet is available
- asks for explicit confirmation before deleting anything
- disables WinRE
- removes the recovery partition
- extends the OS partition
- prints the final WinRE status
- prints the final partition list again

---

## Safe re-run behavior

Version 2 of the script is intentionally more friendly on repeated runs.

If you already performed the operation manually and then run the script again:

- it will show the current partition list on the Windows disk
- it will show the current `reagentc /info` result
- it will exit cleanly with a “nothing to do” style message
- it will **not** treat an already-disabled WinRE state as a hard error

This makes the script more practical for checking the current layout after the fact.

---

## CMD wrapper behavior

The `.cmd` launcher is intended as the easy entry point.

It:

- looks for the `.ps1` in the same folder
- tries portable `pwsh.exe` first if present
- then falls back to system `pwsh.exe`
- then falls back to classic Windows PowerShell
- requests UAC elevation if needed
- launches the PowerShell script with `ExecutionPolicy Bypass`

### Expected folder layout

Keep these files in the same folder:

```text
Run-Remove-WinRE-And-Extend-System.cmd
Remove-WinRE-And-Extend-System.ps1
README_Remove_WinRE_and_Extend_C.md
```

### Typical usage

Double-click:

```text
Run-Remove-WinRE-And-Extend-System.cmd
```

This is the best option for users who do not want to open PowerShell manually.

---

## Manual PowerShell launch

If you prefer to run the script directly:

```powershell
Set-ExecutionPolicy -Scope Process Bypass

.\Remove-WinRE-And-Extend-System.ps1
```

Optional switches:

```powershell
.\Remove-WinRE-And-Extend-System.ps1 -SkipBitLockerCheck

.\Remove-WinRE-And-Extend-System.ps1 -NoPause
```

---

## When you should not use this

Do **not** use this workflow when:

- you rely on built-in Windows recovery options
- you are not sure which partition is the actual WinRE partition
- BitLocker / Device Encryption is active and not suspended
- there are extra partitions between `C:` and Recovery
- the recovery partition is not on the same disk as the OS
- you do not have a bootable Windows recovery/install medium

---

## Final note

Deleting the WinRE partition is technically valid and can be done cleanly.

But the practical gain is often small — typically less than 1 GB.

So this is mostly useful when:

- you want a cleaner partition layout
- you never use built-in Windows recovery
- you already rely on your own boot media and backup workflow
