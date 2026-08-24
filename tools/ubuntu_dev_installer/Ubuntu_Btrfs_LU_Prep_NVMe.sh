#!/usr/bin/env bash
set -euo pipefail

# Ubuntu Btrfs Live-USB Pre-Install Prep for a target SSD/NVMe
# Purpose:
#   - select target disk interactively
#   - wipe partition table
#   - create GPT + EFI + Btrfs layout
#   - create Btrfs subvolumes @ and @home
#   - mount them under /mnt for manual Ubuntu installation
# Notes:
#   - run from a live USB session, not from the installed system
#   - destructive: this erases the selected disk
#   - keep installer step manual: choose "Something else" and reuse mounted targets

SCRIPT_NAME="Ubuntu_Btrfs_LU_Prep_NVMe"
LOG_DIR="${PWD}/logs"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="${LOG_DIR}/${SCRIPT_NAME}_${TS}.log"
mkdir -p "$LOG_DIR"

TARGET_DISK=""
ESP_SIZE_MIB="512"
BTRFS_LABEL="ubuntu-btrfs"
MOUNT_OPTS="noatime,compress=zstd,subvol=@"
HOME_MOUNT_OPTS="noatime,compress=zstd,subvol=@home"
ESP_PART=""
BTRFS_PART=""

log() {
  local msg="$1"
  echo "$msg" | tee -a "$LOG_FILE"
}

run() {
  log "[RUN] $*"
  "$@" 2>&1 | tee -a "$LOG_FILE"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this script as root: sudo bash $0" >&2
    exit 1
  fi
}

confirm_typed() {
  local required="$1"
  local entered=""
  echo
  echo "Required confirmation text: ${required}"
  read -r -p "Enter confirmation text: " entered
  [[ "$entered" == "$required" ]]
}

list_candidate_disks() {
  echo
  echo "Available block devices:"
  lsblk -d -e 7 -o NAME,PATH,MODEL,SIZE,ROTA,TYPE,TRAN | tee -a "$LOG_FILE"
  echo
  echo "Recommended targets are real SSD/NVMe disks, not USB live media."
}

choose_disk() {
  local path=""
  while true; do
    list_candidate_disks
    read -r -p "Enter target disk path (example: /dev/nvme0n1 or /dev/sda), or Q to quit: " path
    case "$path" in
      Q|q)
        echo "Cancelled."
        exit 0
        ;;
    esac

    if [[ ! -b "$path" ]]; then
      echo "Not a valid block device: $path"
      continue
    fi

    if findmnt -rn -S "$path" >/dev/null 2>&1; then
      echo "That whole device appears mounted. Choose a different disk."
      continue
    fi

    TARGET_DISK="$path"
    echo
    echo "Selected disk summary:"
    lsblk -o NAME,PATH,MODEL,SIZE,FSTYPE,MOUNTPOINTS "$TARGET_DISK"
    echo
    if confirm_typed "USE ${TARGET_DISK}"; then
      break
    fi
    echo "Selection not confirmed."
  done
}

is_nvme_disk() {
  [[ "$TARGET_DISK" == /dev/nvme* ]]
}

part_path() {
  local num="$1"
  if is_nvme_disk; then
    printf '%sp%s' "$TARGET_DISK" "$num"
  else
    printf '%s%s' "$TARGET_DISK" "$num"
  fi
}

ensure_not_mounted() {
  if lsblk -nrpo MOUNTPOINT "$TARGET_DISK" | grep -q '/'; then
    echo "Some partitions on the selected disk are mounted. Unmount them first."
    lsblk -o NAME,PATH,SIZE,FSTYPE,MOUNTPOINTS "$TARGET_DISK"
    exit 1
  fi
}

wipe_and_partition() {
  log "[INFO] Wiping and partitioning ${TARGET_DISK}"

  run wipefs -a "$TARGET_DISK"
  run sgdisk --zap-all "$TARGET_DISK"
  run parted -s "$TARGET_DISK" mklabel gpt
  run parted -s "$TARGET_DISK" mkpart ESP fat32 1MiB "${ESP_SIZE_MIB}MiB"
  run parted -s "$TARGET_DISK" set 1 esp on
  run parted -s "$TARGET_DISK" mkpart primary btrfs "${ESP_SIZE_MIB}MiB" 100%
  run partprobe "$TARGET_DISK"
  sleep 2

  ESP_PART="$(part_path 1)"
  BTRFS_PART="$(part_path 2)"

  log "[INFO] EFI partition: ${ESP_PART}"
  log "[INFO] Btrfs partition: ${BTRFS_PART}"
}

format_partitions() {
  run mkfs.vfat -F 32 -n EFI "$ESP_PART"
  run mkfs.btrfs -f -L "$BTRFS_LABEL" "$BTRFS_PART"
}

create_subvolumes() {
  run mount "$BTRFS_PART" /mnt
  run btrfs subvolume create /mnt/@
  run btrfs subvolume create /mnt/@home
  run umount /mnt
}

mount_layout() {
  run mount -o "$MOUNT_OPTS" "$BTRFS_PART" /mnt
  run mkdir -p /mnt/home
  run mkdir -p /mnt/boot/efi
  run mount -o "$HOME_MOUNT_OPTS" "$BTRFS_PART" /mnt/home
  run mount "$ESP_PART" /mnt/boot/efi
}

show_result() {
  echo
  echo "Prepared layout:"
  lsblk -o NAME,PATH,SIZE,FSTYPE,LABEL,MOUNTPOINTS "$TARGET_DISK"
  echo
  echo "Mounted targets:"
  findmnt /mnt /mnt/home /mnt/boot/efi 2>/dev/null || true
  echo
  cat <<EOF
Next step in Ubuntu installer:
  1) Start installer from live session.
  2) Choose manual partitioning / Something else.
  3) Reuse existing mounts:
     - ${BTRFS_PART} mounted as / using subvolume @
     - ${BTRFS_PART} mounted as /home using subvolume @home
     - ${ESP_PART} as /boot/efi, do not recreate if already formatted
  4) Keep format disabled in installer if the live script already formatted the partitions.
EOF
  echo
  echo "Why these mount options:"
  echo "  - subvol=@ or subvol=@home selects which Btrfs subvolume becomes the mount target"
  echo "  - compress=zstd enables modern transparent compression"
  echo "  - noatime reduces unnecessary metadata writes"
  echo
  echo "Log file: ${LOG_FILE}"
}

main() {
  require_root

  for cmd in lsblk wipefs sgdisk parted partprobe mkfs.vfat mkfs.btrfs btrfs mount umount findmnt; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Missing required command: $cmd" >&2
      exit 1
    fi
  done

  echo "====================================================================="
  echo "  Ubuntu Btrfs Live-USB Pre-Install Prep"
  echo "====================================================================="
  echo
  echo "This script will ERASE one selected disk and prepare:"
  echo "  - GPT"
  echo "  - 512 MiB EFI System Partition"
  echo "  - one Btrfs partition"
  echo "  - subvolumes @ and @home"
  echo

  choose_disk
  ensure_not_mounted

  echo
  lsblk -o NAME,PATH,MODEL,SIZE,FSTYPE,MOUNTPOINTS "$TARGET_DISK"
  echo
  if ! confirm_typed "ERASE ${TARGET_DISK}"; then
    echo "Erase confirmation failed. Aborting."
    exit 1
  fi

  wipe_and_partition
  format_partitions
  create_subvolumes
  mount_layout
  show_result
}

main "$@"
