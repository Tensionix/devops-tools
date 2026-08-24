#!/usr/bin/env bash
set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$HOME/.venvs/audion-power}"

if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

log() {
  printf '%s\n' "$1"
}

log "============================================================"
log "AUDION - Ubuntu Power Bootstrap"
log "============================================================"
log "[INFO] Script directory: $SCRIPT_DIR"
log "[INFO] Venv directory:   $VENV_DIR"
log ""

log "[1/6] Updating apt metadata..."
$SUDO apt update
log ""

log "[2/6] Installing core packages..."
$SUDO apt install -y \
  ca-certificates \
  curl \
  wget \
  git \
  unzip \
  zip \
  tar \
  xz-utils \
  gnupg \
  lsb-release \
  software-properties-common \
  build-essential \
  pkg-config
log ""

log "[3/6] Installing power utilities..."
$SUDO apt install -y \
  btop \
  htop \
  tmux \
  mc \
  tree \
  jq \
  ripgrep \
  fd-find \
  fzf \
  bat \
  python3 \
  python3-venv \
  python3-pip \
  python3-dev \
  pipx
log ""

log "[4/6] Optional: fastfetch (system summary)..."
if apt-cache show fastfetch >/dev/null 2>&1; then
  $SUDO apt install -y fastfetch
  log "[INFO] fastfetch installed from apt."
else
  log "[INFO] fastfetch is not available in current Ubuntu apt repositories. Skipping."
fi
log ""

log "[5/6] Creating Python venv..."
mkdir -p "$(dirname "$VENV_DIR")"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
log ""

log "[6/6] Final summary..."
log "[INFO] Ubuntu Power bootstrap completed."
log "[INFO] Activate venv with: source \"$VENV_DIR/bin/activate\""
log "[INFO] Python version: $("$VENV_DIR/bin/python" --version 2>/dev/null || true)"
log "[INFO] Pip version:    $("$VENV_DIR/bin/pip" --version 2>/dev/null || true)"
if command -v btop >/dev/null 2>&1; then
  log "[INFO] btop is available."
fi
if command -v fastfetch >/dev/null 2>&1; then
  log "[INFO] fastfetch is available."
else
  log "[INFO] fastfetch was skipped or is unavailable on this Ubuntu release."
fi
log ""
log "Done."
