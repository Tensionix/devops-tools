# WSL On Windows - Practical Guide

English companion to `wsl_installation_guide_for_windows.md`.

## 1. What WSL Is

WSL is not Ubuntu and not a Linux distribution. WSL is the Windows compatibility/virtualization layer that lets Windows run Linux distributions.

Ubuntu, Debian, and other systems inside WSL are separate distributions installed on top of the WSL platform.

This is why `wsl --install` can mean two things:

- installing the WSL platform;
- installing WSL plus the default Ubuntu distribution.

In practice, the command can do both.

## 2. Platform And Distribution Are Separate

There are two layers:

- WSL platform - Windows components that enable WSL.
- Linux distribution - Ubuntu, Debian, openSUSE, and so on.

Keep four actions separate:

1. install WSL itself;
2. install a specific distribution;
3. update the WSL platform;
4. update packages inside the Linux distribution.

## 3. What `wsl --install` Does

Without parameters:

```powershell
wsl --install
```

Usually this enables required Windows components, installs WSL, and installs default Ubuntu.

With a specific distro:

```powershell
wsl --install -d Ubuntu-24.04
wsl --install -d Debian
```

This installs WSL if needed and installs the selected distribution.

## 4. Install A Specific Distro On A Clean System

This is valid:

```powershell
wsl --install -d Ubuntu
wsl --install -d Ubuntu-24.04
```

You do not have to install an "empty WSL" first.

## 5. Custom Install Location

Use `--location` when you do not want the distro on `C:`.

```powershell
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
wsl --install -d Ubuntu-24.04 --location "S:\WSL\VHDX\Ubuntu-24.04"
```

If WSL is not installed yet, it will be prepared first.

## 6. Platform Only

To install only the platform:

```powershell
wsl --install --no-distribution
```

Then list and install distributions manually:

```powershell
wsl --list --online
wsl --install -d Ubuntu --location "S:\WSL\VHDX\Ubuntu"
```

This is the most controlled route.

## 7. When To Use `wsl --import`

Use import for a prepared tar/rootfs/VHD workflow:

```powershell
wsl --import MyUbuntu "S:\WSL\VHDX\MyUbuntu" .\ubuntu.tar
```

Good cases:

- you already have a prepared rootfs archive;
- you are moving a distro between machines;
- you need a custom image rather than the online Microsoft catalog.

## 8. Update Boundaries

Update WSL platform:

```powershell
wsl --update
```

Update packages inside Ubuntu:

```bash
sudo apt update
sudo apt upgrade
```

These are different layers.

## 9. Recommended Controlled Route

1. Run `wsl --install --no-distribution`.
2. Reboot if Windows asks.
3. Run `wsl --list --online`.
4. Install the selected distro with `--location`.
5. Launch the distro and create the Linux user.
6. Update packages inside Linux.

## 10. Practical Rule

Decide first whether you are managing the Windows WSL platform, a Linux distribution, or Linux packages inside that distribution. Most WSL confusion comes from mixing those layers.
