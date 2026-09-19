# Audion Startup Kit

What starts by itself: show it, add to it, remove the overlaps.

Windows can bring a program up at start in four different ways, and each lives its own life: a scheduled task, a shortcut in the Startup folder, a `Run` registry value, a `RunOnce` value. They get created at different times by different hands, and then the same program starts twice and gets in its own way.

This tool gathers all four into one list, adds a new entry, and — before adding — shows what already launches that same program and offers to remove it.

## Included files

- `Run-Audion-Startup-Kit.cmd`
- `Audion-Startup-Kit.ps1`

## What it does

- lists scheduled tasks with logon/boot triggers, both Startup folders, `Run` and `RunOnce` in HKCU and HKLM
- shows the delay of every entry that has one
- unwraps its own delay wrapper, so a shortcut shows the real program rather than `cmd.exe`
- finds overlaps by executable name, not by full command line — the same program gets registered with a path, through a wrapper, with arguments, and the strings never match
- adds an entry: choice of moment (logon or boot), delay in minutes, method (task or shortcut)
- verifies by fact: after adding, the entry has to appear in the list under its own name
- removes any entry from any of the four places

## The delay

Right after boot half the things do not work: the network is not up, services are not ready, the profile is not unrolled. The delay is what makes autostart usable at all.

The two methods differ:

| method | how the delay is done |
| --- | --- |
| scheduled task | native: the trigger carries `Delay`, written as `PT2M` |
| Startup shortcut | none of its own — the tool writes a small wrapper into `%LOCALAPPDATA%\Audion\Startup` that waits, then launches |

## Wi-Fi hotspot

Sharing Wi-Fi does not come up "at boot" under any settings. `NetworkOperatorTetheringManager` needs the context of a logged-in user: before logon nobody owns the radio. The tool knows this and moves such an entry to logon.

The password and the internet source are set in Windows' own hotspot settings — this tool only brings the sharing up.

## Usage

Double-click `Run-Audion-Startup-Kit.cmd` to see the list. It asks for administrator rights itself; they are needed for entries that are common to all users and for boot-time tasks.

Or pass everything up front:

```
Run-Audion-Startup-Kit.cmd -Action add -Path "C:\Tools\hotspot.ps1" -When logon -DelayMinutes 2
```

| switch | meaning |
| --- | --- |
| `-Action` | `list` (default), `add`, `remove` |
| `-Path` | what to launch; omitted — the tool asks |
| `-Arguments` | arguments for that program |
| `-When` | `logon` (default) or `boot` |
| `-DelayMinutes` | delay after the event, `0` for none |
| `-How` | `task` (default) or `startup` |
| `-Name` | entry name; omitted — taken from the program name |

`.ps1` and `.cmd` files are wrapped into their own engine automatically: the scheduler can only launch programs.

## What it does not do

It does not touch services, group policy, or the `RunServices` keys. It does not decide what should start — it shows what already does and keeps that list from contradicting itself.
