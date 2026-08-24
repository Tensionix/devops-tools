#!/usr/bin/env bash
set -Eeuo pipefail

export DEBIAN_FRONTEND=noninteractive

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$HOME/.venvs/audion-minimal}"

if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo"
else
  SUDO=""
fi

log() {
  printf '%s\n' "$1"
}

log "============================================================"
log "AUDION - Ubuntu Minimal Bootstrap"
log "============================================================"
log "[INFO] Script directory: $SCRIPT_DIR"
log "[INFO] Venv directory:   $VENV_DIR"
log ""

log "[1/5] Updating apt metadata..."
$SUDO apt update
log ""

log "[2/5] Installing core packages..."
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
  software-properties-common
log ""

log "[3/5] Installing minimal utilities..."
$SUDO apt install -y \
  nano \
  mc \
  tree \
  jq \
  python3 \
  python3-venv \
  python3-pip
log ""

log "[4/5] Creating Python venv..."
mkdir -p "$(dirname "$VENV_DIR")"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
log ""

log "[5/5] Final summary..."
log "[INFO] Ubuntu Minimal bootstrap completed."
log "[INFO] Activate venv with: source \"$VENV_DIR/bin/activate\""
log "[INFO] Python version: $("$VENV_DIR/bin/python" --version 2>/dev/null || true)"
log "[INFO] Pip version:    $("$VENV_DIR/bin/pip" --version 2>/dev/null || true)"
if command -v mc >/dev/null 2>&1; then
  log "[INFO] mc is available."
fi
log ""
log "Done."
