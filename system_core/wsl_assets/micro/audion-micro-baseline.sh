#!/usr/bin/env bash
set -euo pipefail

# Audion micro baseline (settings + keybindings)
# Safe to run multiple times; existing config files are backed up with a timestamp.

TARGET_DIR="${HOME}/.config/micro"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$TARGET_DIR"

backup_if_exists() {
  local f="$1"
  if [[ -f "$f" ]]; then
    cp -a "$f" "${f}.bak.${TS}"
  fi
}

SETTINGS_FILE="${TARGET_DIR}/settings.json"
BINDINGS_FILE="${TARGET_DIR}/bindings.json"

backup_if_exists "$SETTINGS_FILE"
backup_if_exists "$BINDINGS_FILE"

cat > "$SETTINGS_FILE" <<'JSON'
{
  "colorscheme": "default",
  "tabsize": 4,
  "tabstospaces": true,
  "smartindent": true,
  "autosave": 0,
  "ruler": true,
  "linenumbers": true,
  "scrollbar": true,
  "cursorline": true,
  "statusline": true,
  "softwrap": false,
  "wrap": false,
  "eofnewline": true,
  "autoclose": true,
  "savecursor": true,
  "backup": false,
  "swapfile": false,
  "encoding": "utf-8"
}
JSON

cat > "$BINDINGS_FILE" <<'JSON'
{
  "Ctrl-Alt-w": "command-edit:toggle softwrap",
  "Ctrl-Alt-l": "command-edit:toggle linenumbers"
}
JSON

echo "Micro baseline installed:"
echo "  - ${SETTINGS_FILE}"
echo "  - ${BINDINGS_FILE}"
echo

if command -v micro >/dev/null 2>&1; then
  (micro --version 2>/dev/null || micro -version 2>/dev/null || true) | sed 's/^/micro: /' || true
else
  echo "micro: not found in PATH (install it first)."
fi

echo
echo "Done. Start micro and enjoy :)"
