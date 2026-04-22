#!/usr/bin/env bash
# install.sh — install or uninstall zo-reddot system-wide.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DST=/usr/local/bin/zo-reddot.py
UNIT_DST=/etc/systemd/system/zo-reddot.service

usage() {
  cat <<EOF
Usage: $(basename "$0") [install|uninstall]

install    Install dependencies (python3-evdev), copy script + unit,
           enable + start the service. Requires sudo. Default action.
uninstall  Stop + disable the service, remove files.
EOF
}

action="${1:-install}"

case "$action" in
  install)
    echo "=== Checking dependency: python3-evdev ==="
    if ! python3 -c "import evdev" 2>/dev/null; then
      if command -v dnf >/dev/null; then
        sudo dnf install -y python3-evdev
      elif command -v apt-get >/dev/null; then
        sudo apt-get install -y python3-evdev
      elif command -v pacman >/dev/null; then
        sudo pacman -S --noconfirm python-evdev
      else
        echo "No supported package manager found. Install python3-evdev manually." >&2
        exit 1
      fi
    else
      echo "python3-evdev already present."
    fi

    echo "=== Installing files ==="
    sudo install -m 0755 "$REPO_DIR/zo-reddot.py" "$SCRIPT_DST"
    sudo install -m 0644 "$REPO_DIR/zo-reddot.service" "$UNIT_DST"

    echo "=== Enabling service ==="
    sudo systemctl daemon-reload
    sudo systemctl enable --now zo-reddot.service
    sudo systemctl status zo-reddot.service --no-pager | head -6

    cat <<'DONE'

Installed. The TrackPoint pointer is now disabled; the three buttons below
the spacebar remain fully functional.

If your TrackPoint has a different device name than the default
"ETPS/2 Elantech TrackPoint", edit the Environment= line in
/etc/systemd/system/zo-reddot.service.

Find device names with:  cat /proc/bus/input/devices
Debug live:              journalctl -u zo-reddot -f
DONE
    ;;

  uninstall)
    echo "=== Stopping + disabling service ==="
    sudo systemctl disable --now zo-reddot.service 2>/dev/null || true
    sudo rm -f "$SCRIPT_DST" "$UNIT_DST"
    sudo systemctl daemon-reload
    echo "Removed. Original TrackPoint behavior is back."
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    echo "Unknown action: $action" >&2
    usage >&2
    exit 2
    ;;
esac
