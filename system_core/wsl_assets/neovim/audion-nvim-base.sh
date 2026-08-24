#!/usr/bin/env bash
set -euo pipefail

# Audion Neovim base profile.
# No AI providers. No changes to ~/.config/nvim.

APP="${AUDION_NVIM_APPNAME:-audion-ide}"
REQUESTED_PROFILE="${AUDION_NVIM_PROFILE:-lite}"
TS="$(date +%Y%m%d-%H%M%S)"

need() { command -v "$1" >/dev/null 2>&1; }

if ! need nvim; then
  echo "[!] nvim is not installed. Run the WSL Dev packages step first."
  exit 1
fi

backup_path() {
  local path="$1"
  if [ -e "$path" ]; then
    local backup="${path}.bak.${TS}"
    mv "$path" "$backup"
    echo "[i] Backed up $path -> $backup"
  fi
}

cfg="${XDG_CONFIG_HOME:-$HOME/.config}/${APP}"
data="${XDG_DATA_HOME:-$HOME/.local/share}/${APP}"
state="${XDG_STATE_HOME:-$HOME/.local/state}/${APP}"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/${APP}"

backup_path "$cfg"
backup_path "$data"
backup_path "$state"
backup_path "$cache"

profile="lite"
if [ "$REQUESTED_PROFILE" = "lazyvim" ] && need git && timeout 60 git clone --quiet https://github.com/LazyVim/starter "$cfg" --depth=1; then
  profile="lazyvim"
  rm -rf "$cfg/.git"
  mkdir -p "$cfg/lua/plugins" "$cfg/lua/config"

  cat > "$cfg/lua/plugins/audion_lang.lua" <<'EOF'
return {
  { import = "lazyvim.plugins.extras.lang.bash" },
  { import = "lazyvim.plugins.extras.lang.python" },
  { import = "lazyvim.plugins.extras.lang.json" },
  { import = "lazyvim.plugins.extras.lang.yaml" },
  { import = "lazyvim.plugins.extras.lang.markdown" },
  {
    "nvim-treesitter/nvim-treesitter",
    opts = function(_, opts)
      opts = opts or {}
      opts.ensure_installed = {
        "bash",
        "lua",
        "python",
        "json",
        "yaml",
        "markdown",
        "markdown_inline",
        "toml",
        "gitignore",
        "vim",
        "vimdoc",
      }
      return opts
    end,
  },
}
EOF

  cat > "$cfg/lua/config/keymaps.lua" <<'EOF'
vim.keymap.set("n", "<leader>w", "<cmd>w<cr>", { desc = "Save" })
vim.keymap.set("n", "<leader>q", "<cmd>q<cr>", { desc = "Quit" })
vim.keymap.set("n", "<leader>e", "<cmd>Neotree toggle<cr>", { desc = "Explorer" })
EOF
else
  rm -rf "$cfg"
  mkdir -p "$cfg"
  if [ "$REQUESTED_PROFILE" = "lazyvim" ]; then
    echo "[warn] LazyVim starter is unavailable; creating lite Neovim profile."
  else
    echo "[i] Creating lite Neovim profile."
  fi
  cat > "$cfg/init.lua" <<'EOF'
vim.g.mapleader = " "
vim.g.maplocalleader = " "

vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.mouse = "a"
vim.opt.termguicolors = true
vim.opt.expandtab = true
vim.opt.shiftwidth = 2
vim.opt.tabstop = 2
vim.opt.smartindent = true
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.splitright = true
vim.opt.splitbelow = true
vim.opt.undofile = true

vim.keymap.set("n", "<leader>w", "<cmd>w<cr>", { desc = "Save" })
vim.keymap.set("n", "<leader>q", "<cmd>q<cr>", { desc = "Quit" })
vim.keymap.set("n", "<leader>h", "<cmd>nohlsearch<cr>", { desc = "Clear search highlight" })
vim.keymap.set("n", "<leader>pv", vim.cmd.Ex, { desc = "Open netrw explorer" })
EOF
fi

mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/audvi" <<EOF
#!/usr/bin/env bash
NVIM_APPNAME="$APP" nvim "\$@"
EOF
chmod 0755 "$HOME/.local/bin/audvi"

if ! grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.profile" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
fi
if [ -f "$HOME/.bashrc" ] && ! grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

if [ "$profile" = "lazyvim" ]; then
  lazy_log="${state}/lazy-sync-${TS}.log"
  mkdir -p "$state"
  if timeout 180 env NVIM_APPNAME="$APP" nvim --headless "+Lazy! sync" "+qa" >"$lazy_log" 2>&1; then
    echo "[i] Lazy plugin sync finished: $lazy_log"
  else
    echo "[warn] Lazy plugin sync timed out or failed; open Neovim later to continue."
    echo "[warn] Lazy plugin sync log: $lazy_log"
  fi
else
  NVIM_APPNAME="$APP" nvim --headless "+qa"
fi

echo "[OK] Audion Neovim base profile installed: $cfg"
echo "[OK] Profile mode: $profile"
echo "[OK] Launch with: audvi"
