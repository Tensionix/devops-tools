# Ubuntu Dev/Create Installer Kit v4

This release keeps the same layered installer idea, but makes the day-one path more conservative and easier to reason about.

What changed in v4:

- colored menu output for faster reading in a real terminal;
- dry-run preview profiles and dry-run preview for individual layers;
- `Minimal` is stricter and no longer pulls optional extras automatically;
- `ubuntu-restricted-extras` was moved out of the base layer into a separate optional official layer;
- the README now treats the kit as a portable NVMe-Linux starter architecture, not just a shell wrapper.

---

## 1. Core idea

The goal is not to blast the machine with one giant `apt install ...` command.

The goal is to:

- install in layers;
- validate hardware between layers;
- snapshot between meaningful checkpoints;
- keep paths short and neutral inside the real system;
- leave riskier or more opinionated pieces for later.

This is especially useful when you are still building Linux muscle memory and want a low-drama first system.

---

## 2. Portable NVMe-Linux philosophy

This is not a magical "plug SSD into anything and everything is perfect" promise.

It is a practical system layout and package workflow designed to make a laptop Linux install easier to:

- understand;
- maintain;
- roll back;
- migrate conceptually between machines.

Recommended base layout for a 256 GB SSD:

- EFI: 512 MB, FAT32
- one main Btrfs partition for the system
- subvolumes:
  - `@` mounted at `/`
  - `@home` mounted at `/home`

If hibernation is not required, keep the initial layout simple and decide on swap later.

---

## 3. Keep the paths short

Use branding in docs, release names, and project bundles.

Inside the live system, keep the paths neutral and short.

Recommended folders:

- `~/Terminal`
- `~/Projects`
- `~/Apps`
- `~/Sync`
- `~/Media`
- `~/Vault`
- `~/Lab`

This keeps the system cleaner and easier to carry from one machine to another.

---

## 4. Profile model

### Minimal

Conservative Ubuntu-first setup.

Includes:

- Base
- Hardware / Intel / Wi-Fi / Bluetooth / color basics
- Terminal
- Sync
- Media Minimal
- optional NVIDIA step after hardware

Use this first.

### Full

Everything from Minimal, plus:

- Optional official Ubuntu extras
- Media Full
- Create Full

This is the "comfortable workstation" profile.

### Lab

Everything from Full, plus:

- Lab / experimental layer

Use this when you intentionally want to test containers, AI tools, or other not-quite-core pieces.

---

## 5. Layer intent

### Base

Core storage, crypto, recovery, and rollback tools.

Packages include:

- Btrfs tools
- cryptsetup
- GPT / EFI utilities
- zstd
- Timeshift
- rsync / curl / wget

Deliberately not included anymore:

- `ubuntu-restricted-extras`
- optional desktop extras that may create friction during a clean first run

### Hardware / Intel

This layer is where you stabilize:

- Intel graphics / VA-API basics
- Wi-Fi and Bluetooth support
- firmware and inspection tools
- basic color management packages

Important note:

- AX200 / AX211 support on Linux is normally about `iwlwifi` + `linux-firmware`, not about downloading a vendor `.run` driver.
- LUT / ICC workflow should come **after** the system is already stable with graphics, sleep, wake, and networking.

### NVIDIA step

This is intentionally separate.

The script uses:

```bash
sudo ubuntu-drivers install
```

Why:

- Ubuntu can pick the recommended branch more safely than a hard-coded package number in a generic script;
- Secure Boot, kernel state, and release differences matter.

### Terminal

Day-one CLI and dev baseline:

- `micro`
- `mc`
- `neovim`
- `git`
- `ripgrep`
- `fd-find`
- compilers
- Python
- `tmux`
- `fzf`
- `shellcheck`

### Sync

Infrastructure layer:

- Syncthing
- rclone
- SSH
- WireGuard
- network utilities

### Media Minimal

Day-one playback and inspection:

- `ffmpeg`
- `mpv`
- `vlc`
- `smplayer`
- `mediainfo`
- music players

### Optional official Ubuntu extras

This layer exists because some things are still useful, but they should not surprise the first run.

Examples:

- `flatpak`
- `ubuntu-restricted-extras`

Important:

- `ubuntu-restricted-extras` can be interactive depending on release and package state.
- That is exactly why it is no longer hidden in the base layer.

### Media Full

Heavier media tooling such as:

- HandBrake
- MKVToolNix
- ImageMagick
- SoX
- tagging / audio tools

### Create Full

Broader creator and analysis tooling:

- Audacity
- OBS Studio
- VapourSynth
- Gifski
- metadata helpers
- routing utilities

### Lab

This is where experimentation belongs:

- Podman
- Distrobox
- Ollama

Treat this as optional and reversible, not as part of the sacred base system.

---

## 6. Dry-run mode

v4 adds preview modes.

You can now preview:

- Minimal profile
- Full profile
- Lab profile
- selected layers
- remove transactions

This is useful when you want to see what Ubuntu would do before you commit to the install.

The script uses `apt-get -s` for previews.

---

## 7. External / manual installs

Some apps are intentionally not forced through the installer.

Why:

- they may be better as Flatpak/AppImage/upstream binaries;
- they may be personal preference tools;
- they may change fast or depend on one external maintainer.

See:

- `packages/external_apps_manual.txt`

Typical examples include:

- Shutter Encoder
- LosslessCut
- DisplayCAL
- other upstream-only or manually managed tools

---

## 8. Suggested first-pass workflow

Recommended order for a fresh system:

1. Install Minimal profile
2. Verify:
   - display
   - audio
   - sleep / wake
   - Wi-Fi / Bluetooth
   - touchpad / keyboard
3. Run NVIDIA step
4. Create a Timeshift snapshot
5. Install Full profile pieces selectively
6. Only then start touching Lab

This keeps the learning curve under control.

---

## 9. Smoke-test status

The shell logic was smoke-tested in sandbox with mocked `sudo`, `apt-get`, `apt-cache`, and `ubuntu-drivers` commands.

Validated:

- `bash -n` syntax
- menu flow
- dry-run flow
- layer resolution
- Y / N / Q branching
- NVIDIA step entry
- package skip behavior when a package is not available

Not fully validated in sandbox:

- real package installs on a live Ubuntu desktop;
- Secure Boot interactions;
- actual NVIDIA branch selection;
- real sleep / wake / ICC / LUT behavior on physical hardware.

---

## 10. Files in this kit

- `Run-Ubuntu-Dev-Create-Installer.sh`
- `packages/`
- `logs/`
- `README.md`

---

## 11. Practical rule

Use the branding for the release.

Keep the live system itself clean.

That means:

- bundle name can be branded;
- docs can be branded;
- real filesystem paths should stay short and neutral.
