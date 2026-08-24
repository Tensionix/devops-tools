#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGES_DIR="${SCRIPT_DIR}/packages"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/install_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "${LOG_FILE}") 2>&1

supports_color() {
  [[ -t 1 ]] || return 1
  [[ -n "${NO_COLOR:-}" ]] && return 1
  [[ "${TERM:-}" == "dumb" ]] && return 1
  return 0
}

if supports_color; then
  C_RESET=$'\033[0m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RED=$'\033[31m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_BLUE=$'\033[34m'
  C_MAGENTA=$'\033[35m'
  C_CYAN=$'\033[36m'
else
  C_RESET=''
  C_BOLD=''
  C_DIM=''
  C_RED=''
  C_GREEN=''
  C_YELLOW=''
  C_BLUE=''
  C_MAGENTA=''
  C_CYAN=''
fi

say_info() { printf '%s[INFO]%s %s\n' "${C_CYAN}" "${C_RESET}" "$*"; }
say_warn() { printf '%s[WARN]%s %s\n' "${C_YELLOW}" "${C_RESET}" "$*"; }
say_error() { printf '%s[ERROR]%s %s\n' "${C_RED}" "${C_RESET}" "$*"; }
say_ok() { printf '%s[OK]%s %s\n' "${C_GREEN}" "${C_RESET}" "$*"; }
say_tip() { printf '%s[TIP]%s %s\n' "${C_MAGENTA}" "${C_RESET}" "$*"; }

LAYER_ORDER=(
  base
  hardware_intel
  terminal
  sync
  media_minimal
  optional_official
  media_full
  create_full
  lab
)

layer_title() {
  case "$1" in
    base) echo "Base / storage / recovery" ;;
    hardware_intel) echo "Hardware / Intel GPU / Wi-Fi / Bluetooth / color basics" ;;
    terminal) echo "Terminal / dev baseline" ;;
    sync) echo "Sync / network" ;;
    media_minimal) echo "Media Minimal" ;;
    optional_official) echo "Optional official Ubuntu extras" ;;
    media_full) echo "Media Full" ;;
    create_full) echo "Create Full" ;;
    lab) echo "Lab / containers / AI / experiments" ;;
    *) echo "$1" ;;
  esac
}

layer_desc() {
  case "$1" in
    base) echo "Core filesystem, crypto, snapshot, and recovery tools." ;;
    hardware_intel) echo "Intel graphics/media tools, firmware, Wi-Fi, Bluetooth, and color basics." ;;
    terminal) echo "CLI, editors, build tools, Python, and shell productivity tools." ;;
    sync) echo "Sync, SSH, WireGuard, and network utilities." ;;
    media_minimal) echo "Safe day-one media playback and inspection layer." ;;
    optional_official) echo "Official Ubuntu extras that may prompt or pull optional codec stacks." ;;
    media_full) echo "Heavier media conversion, tagging, and utility layer." ;;
    create_full) echo "Creator/audio/analysis tools for deeper production workflows." ;;
    lab) echo "Experimental container and AI layer." ;;
    *) echo "" ;;
  esac
}

layer_file() {
  case "$1" in
    base) echo "${PACKAGES_DIR}/packages_base.txt" ;;
    hardware_intel) echo "${PACKAGES_DIR}/packages_hardware_intel.txt" ;;
    terminal) echo "${PACKAGES_DIR}/packages_terminal.txt" ;;
    sync) echo "${PACKAGES_DIR}/packages_sync.txt" ;;
    media_minimal) echo "${PACKAGES_DIR}/packages_media_minimal.txt" ;;
    optional_official) echo "${PACKAGES_DIR}/packages_optional_official.txt" ;;
    media_full) echo "${PACKAGES_DIR}/packages_media_full.txt" ;;
    create_full) echo "${PACKAGES_DIR}/packages_create_full.txt" ;;
    lab) echo "${PACKAGES_DIR}/packages_lab.txt" ;;
    *) return 1 ;;
  esac
}

print_header() {
  echo "============================================================"
  echo "  UBUNTU DEV/CREATE INSTALLER v4"
  echo "  Colored release + conservative minimal + dry-run preview"
  echo "============================================================"
  echo "Log: ${LOG_FILE}"
  echo
}

require_apt() {
  if ! command -v apt-get >/dev/null 2>&1; then
    say_error "This installer expects Ubuntu or another APT-based system."
    exit 1
  fi
}

ensure_sudo() {
  if ! command -v sudo >/dev/null 2>&1; then
    say_error "sudo was not found."
    exit 1
  fi

  say_info "Validating sudo access..."
  sudo -v
}

prompt_ynq() {
  local prompt="$1"
  local answer

  while true; do
    read -r -p "${prompt} [Y/N/Q]: " answer
    case "${answer:-}" in
      Y|y) return 0 ;;
      N|n) return 1 ;;
      Q|q) say_info "User requested quit."; exit 0 ;;
      *) echo "Please answer Y, N, or Q." ;;
    esac
  done
}

pause_enter() {
  read -r -p "Press Enter to continue..." _
}

show_file() {
  local file="$1"
  echo "------------------------------------------------------------"
  echo "Layer file: ${file}"
  sed '/^[[:space:]]*#/d;/^[[:space:]]*$/d' "$file" || true
  echo "------------------------------------------------------------"
}

apt_update_if_needed() {
  if prompt_ynq "Run apt update now?"; then
    say_info "Running apt update."
    sudo apt-get update
  else
    say_info "Skipped apt update."
  fi
}

apt_upgrade_if_needed() {
  if prompt_ynq "Run apt upgrade now?"; then
    say_info "Running apt upgrade."
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
  else
    say_info "Skipped apt upgrade."
  fi
}

resolve_pkg() {
  local spec="$1"
  local candidate

  IFS='|' read -r -a candidates <<< "$spec"
  for candidate in "${candidates[@]}"; do
    candidate="$(echo "$candidate" | xargs)"
    if [[ -z "$candidate" ]]; then
      continue
    fi
    if apt-cache show "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  return 1
}

collect_layer_packages() {
  local file="$1"
  local line
  local resolved
  local wanted_name="$2"
  local skipped_name="$3"
  declare -n wanted_ref="$wanted_name"
  declare -n skipped_ref="$skipped_name"
  wanted_ref=()
  skipped_ref=()

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="$(echo "$line" | xargs)"
    if [[ -z "$line" ]]; then
      continue
    fi

    if resolved="$(resolve_pkg "$line")"; then
      wanted_ref+=("$resolved")
    else
      skipped_ref+=("$line")
    fi
  done < "$file"
}

preview_install_command() {
  local title="$1"
  shift
  if [[ $# -eq 0 ]]; then
    say_warn "Nothing to preview for ${title}."
    return 0
  fi

  say_info "Dry-run preview for ${title}:"
  sudo DEBIAN_FRONTEND=noninteractive apt-get -s install "$@" || true
}

install_layer() {
  local layer="$1"
  local mode="${2:-install}"
  local title file
  local -a wanted=()
  local -a skipped=()

  title="$(layer_title "$layer")"
  file="$(layer_file "$layer")"

  echo
  say_info "Preparing layer: ${title}"
  say_info "$(layer_desc "$layer")"
  show_file "$file"
  collect_layer_packages "$file" wanted skipped

  if [[ ${#wanted[@]} -eq 0 ]]; then
    say_warn "No installable packages were resolved for layer: ${title}"
  else
    say_info "Resolved packages for ${title}:"
    printf '  %s\n' "${wanted[@]}"
  fi

  if [[ ${#skipped[@]} -gt 0 ]]; then
    say_warn "Package specs not found in current APT sources:"
    printf '  %s\n' "${skipped[@]}"
  fi

  if [[ "$layer" == "optional_official" ]]; then
    say_warn "This layer may be interactive on some systems."
    say_warn "Example: ubuntu-restricted-extras may present extra prompts or EULA-related dialogs."
  fi

  if [[ ${#wanted[@]} -eq 0 ]]; then
    return 0
  fi

  if [[ "$mode" == "preview" ]]; then
    preview_install_command "$title" "${wanted[@]}"
    return 0
  fi

  if prompt_ynq "Preview install transaction for '${title}' before applying?"; then
    preview_install_command "$title" "${wanted[@]}"
  fi

  if prompt_ynq "Install layer '${title}' now?"; then
    say_info "Installing layer: ${title}"
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y install "${wanted[@]}"
    say_ok "Finished layer: ${title}"
  else
    say_info "Skipped layer: ${title}"
  fi
}

remove_layer() {
  local layer="$1"
  local title file
  local -a wanted=()
  local -a skipped=()

  title="$(layer_title "$layer")"
  file="$(layer_file "$layer")"

  echo
  say_warn "Remove mode is conservative."
  say_warn "It only removes packages listed in the layer file."
  say_warn "It does not guarantee a perfect rollback of every dependency or config change."
  show_file "$file"
  collect_layer_packages "$file" wanted skipped

  if [[ ${#wanted[@]} -eq 0 ]]; then
    say_warn "No installable package candidates were resolved for removal in ${title}."
    return 0
  fi

  say_info "Candidate packages for removal from ${title}:"
  printf '  %s\n' "${wanted[@]}"

  if prompt_ynq "Preview remove transaction for '${title}' before applying?"; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get -s remove --purge "${wanted[@]}" || true
  fi

  if prompt_ynq "Remove layer '${title}' now with apt remove --purge?"; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y remove --purge "${wanted[@]}"
    if prompt_ynq "Run apt autoremove now?"; then
      sudo DEBIAN_FRONTEND=noninteractive apt-get -y autoremove
    fi
    say_ok "Removal pass completed for ${title}."
  else
    say_info "Skipped removal for layer: ${title}"
  fi
}

run_nvidia_step() {
  echo
  say_info "NVIDIA step uses ubuntu-drivers rather than a hard-coded branch."
  say_info "This is safer on Ubuntu because the recommended branch can differ by release, kernel, Secure Boot state, and GPU."

  if ! command -v ubuntu-drivers >/dev/null 2>&1; then
    say_info "ubuntu-drivers is not installed yet. Installing ubuntu-drivers-common first."
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y install ubuntu-drivers-common
  fi

  say_info "Available desktop drivers:"
  sudo ubuntu-drivers list || true
  echo

  if prompt_ynq "Run 'sudo ubuntu-drivers install' now?"; then
    sudo ubuntu-drivers install
    say_ok "NVIDIA automatic install step finished."
  else
    say_info "Skipped NVIDIA automatic install."
  fi
}

run_snapshot_hint() {
  echo
  say_tip "This is a good checkpoint for a Timeshift snapshot."
  echo '  Example: sudo timeshift --create --comments "Post layer checkpoint"'
  echo
}

print_external_apps_note() {
  local file="${PACKAGES_DIR}/external_apps_manual.txt"
  echo
  say_info "The following apps are intentionally left for manual install or Flatpak/AppImage/upstream packages:"
  sed '/^[[:space:]]*#/d;/^[[:space:]]*$/d' "$file" || true
}

show_all_layers() {
  local layer
  for layer in "${LAYER_ORDER[@]}"; do
    echo
    printf '%s### %s%s\n' "${C_BOLD}" "$(layer_title "$layer")" "${C_RESET}"
    echo "    $(layer_desc "$layer")"
    show_file "$(layer_file "$layer")"
  done
  print_external_apps_note
}

choose_single_layer() {
  local idx=1
  local layer
  echo
  echo "Select a layer:"
  for layer in "${LAYER_ORDER[@]}"; do
    printf '  %s%d)%s %s\n' "${C_BLUE}" "${idx}" "${C_RESET}" "$(layer_title "$layer")"
    echo "     $(layer_desc "$layer")"
    idx=$((idx + 1))
  done
  echo "  Q) Quit"

  while true; do
    local choice
    read -r -p "Select action: " choice
    case "${choice:-}" in
      1) echo base; return 0 ;;
      2) echo hardware_intel; return 0 ;;
      3) echo terminal; return 0 ;;
      4) echo sync; return 0 ;;
      5) echo media_minimal; return 0 ;;
      6) echo optional_official; return 0 ;;
      7) echo media_full; return 0 ;;
      8) echo create_full; return 0 ;;
      9) echo lab; return 0 ;;
      Q|q) say_info "User requested quit."; exit 0 ;;
      *) echo "Please select a valid menu item." ;;
    esac
  done
}

run_profile() {
  local profile="$1"
  local mode="${2:-install}"
  local -a layers=()

  case "$profile" in
    minimal)
      layers=(base hardware_intel terminal sync media_minimal)
      ;;
    full)
      layers=(base hardware_intel terminal sync media_minimal optional_official media_full create_full)
      ;;
    lab)
      layers=(base hardware_intel terminal sync media_minimal optional_official media_full create_full lab)
      ;;
    *)
      say_error "Unknown profile: ${profile}"
      exit 1
      ;;
  esac

  local layer
  for layer in "${layers[@]}"; do
    install_layer "$layer" "$mode"

    if [[ "$mode" == "install" ]]; then
      run_snapshot_hint

      if [[ "$layer" == "hardware_intel" ]]; then
        if prompt_ynq "Open the NVIDIA install step now?"; then
          run_nvidia_step
          run_snapshot_hint
        else
          say_info "Skipped NVIDIA step."
        fi
      fi
    fi
  done

  print_external_apps_note
}

run_selected_layers() {
  local mode="${1:-install}"
  while true; do
    local layer
    layer="$(choose_single_layer)"
    install_layer "$layer" "$mode"
    if [[ "$mode" == "install" ]]; then
      if [[ "$layer" == "hardware_intel" ]]; then
        if prompt_ynq "Open the NVIDIA install step now?"; then
          run_nvidia_step
        fi
      fi
      run_snapshot_hint
    fi
    if ! prompt_ynq "Process another selected layer?"; then
      break
    fi
  done
  print_external_apps_note
}

show_profile_descriptions() {
  echo
  printf '%sProfiles%s\n' "${C_BOLD}" "${C_RESET}"
  echo "  Minimal: conservative Ubuntu-first day-one setup."
  echo "  Full   : Minimal + official extras + heavier media/create tools."
  echo "  Lab    : Full + experimental container/AI layer."
  echo
}

menu() {
  while true; do
    echo
    printf '%sMain menu%s\n' "${C_BOLD}" "${C_RESET}"
    show_profile_descriptions
    echo "  1) Install Minimal profile"
    echo "  2) Install Full profile"
    echo "  3) Install Lab profile"
    echo "  4) Preview Minimal profile"
    echo "  5) Preview Full profile"
    echo "  6) Preview Lab profile"
    echo "  7) Install selected layers"
    echo "  8) Preview selected layers"
    echo "  9) Remove selected layer"
    echo " 10) Show layer package lists"
    echo " 11) Run NVIDIA step only"
    echo "  Q) Quit"

    local choice
    read -r -p "Select action: " choice
    case "${choice:-}" in
      1) run_profile minimal install ;;
      2) run_profile full install ;;
      3) run_profile lab install ;;
      4) run_profile minimal preview; pause_enter ;;
      5) run_profile full preview; pause_enter ;;
      6) run_profile lab preview; pause_enter ;;
      7) run_selected_layers install ;;
      8) run_selected_layers preview ;;
      9) remove_layer "$(choose_single_layer)" ;;
      10) show_all_layers; pause_enter ;;
      11) run_nvidia_step ;;
      Q|q) say_info "User requested quit."; break ;;
      *) echo "Please select a valid menu item." ;;
    esac
  done
}

main() {
  print_header
  require_apt
  ensure_sudo
  apt_update_if_needed
  apt_upgrade_if_needed
  menu

  echo
  say_ok "Done. Review the log and keep only what you like."
}

main "$@"
