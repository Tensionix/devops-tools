#!/usr/bin/env bash
# Audion Fedora Desktop / WSL bootstrap (MINIMAL TUI learner)
# Messages intentionally in English (encoding-safe).
set -euo pipefail

echo "[1/5] Updating system..."
sudo dnf -y upgrade

echo "[2/5] Installing minimal CLI/Dev packages..."
sudo dnf -y install \
  git curl wget ca-certificates \
  gzip zip unzip tar xz bzip2 p7zip p7zip-plugins \
  dos2unix jq ripgrep fd-find fzf \
  htop ncdu \
  mc micro tmux \
  python3 python3-pip \
  ffmpeg

echo "[3/5] Creating venv..."
mkdir -p "$HOME/.venvs"
python3 -m venv "$HOME/.venvs/audion"
"$HOME/.venvs/audion/bin/python" -m pip install -U pip wheel setuptools

echo "[4/5] Installing Python libraries into venv..."
"$HOME/.venvs/audion/bin/pip" install -U \
  google-generativeai \
  python-docx \
  pypdf \
  pandas \
  openpyxl \
  pymorphy3 \
  tqdm

echo "[5/5] Done."
echo "Venv: $HOME/.venvs/audion"
