#!/usr/bin/env bash
# Audion Fedora Desktop / WSL bootstrap (POWER TUI)
# Messages intentionally in English (encoding-safe).
set -euo pipefail

echo "[1/6] Updating system..."
sudo dnf -y upgrade

echo "[2/6] Installing CLI/Dev packages (power set)..."
sudo dnf -y install \
  git curl wget ca-certificates \
  gzip zip unzip tar xz bzip2 p7zip p7zip-plugins \
  dos2unix jq ripgrep fd-find fzf \
  htop btop ncdu \
  mc micro neovim tmux \
  python3 python3-pip \
  ffmpeg

echo "[3/6] Optional: fastfetch (system summary)..."
sudo dnf -y install fastfetch || true

echo "[4/6] Creating venv..."
mkdir -p "$HOME/.venvs"
python3 -m venv "$HOME/.venvs/audion"
"$HOME/.venvs/audion/bin/python" -m pip install -U pip wheel setuptools

echo "[5/6] Installing Python libraries into venv..."
"$HOME/.venvs/audion/bin/pip" install -U \
  google-generativeai \
  python-docx \
  pypdf \
  pandas \
  openpyxl \
  pymorphy3 \
  tqdm

echo "[6/6] Done."
echo "Venv: $HOME/.venvs/audion"
