#!/bin/bash
# Shared Mac setup used by "Start Bongo Cat.command".
# Average-user path: double-click the .command. This script installs Python
# deps if needed, checks USB, opens the typing-permission pane, then starts.
set -euo pipefail

bongo_repo_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$here/.." && pwd
}

bongo_find_python() {
  local c
  for c in \
    python3 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    "$HOME/Library/Frameworks/Python.framework/Versions/Current/bin/python3" \
    /Library/Frameworks/Python.framework/Versions/Current/bin/python3
  do
    if command -v "$c" >/dev/null 2>&1; then
      command -v "$c"
      return 0
    fi
    if [ -x "$c" ]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

bongo_python_ok() {
  local py="$1"
  "$py" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null
}

bongo_list_serial_ports() {
  # Cheap Yellow Display usually shows up as cu.usbserial*, cu.wchusbserial*,
  # cu.SLAB_USBtoUART, or cu.usbmodem*.
  ls /dev/cu.usbserial* /dev/cu.wchusbserial* /dev/cu.SLAB* /dev/cu.usbmodem* 2>/dev/null || true
}

bongo_has_serial() {
  [ -n "$(bongo_list_serial_ports)" ]
}

bongo_gui() {
  [ "$(uname -s)" = "Darwin" ] && command -v osascript >/dev/null 2>&1
}

bongo_dialog() {
  # usage: bongo_dialog "message" "DefaultBtn" "OtherBtn"
  local msg="$1"
  local ok="${2:-OK}"
  local extra="${3:-}"
  if ! bongo_gui; then
    echo "$msg"
    return 0
  fi
  local script
  if [ -n "$extra" ]; then
    script="display dialog \"${msg//\"/\\\"}\" buttons {\"${extra//\"/\\\"}\", \"${ok//\"/\\\"}\"} default button \"${ok//\"/\\\"}\""
  else
    script="display dialog \"${msg//\"/\\\"}\" buttons {\"${ok//\"/\\\"}\"} default button \"${ok//\"/\\\"}\""
  fi
  osascript -e "$script" >/dev/null
}

bongo_choose() {
  # Prints the button name the user clicked. Non-GUI: prints the default.
  local msg="$1"
  local default="$2"
  shift 2
  if ! bongo_gui; then
    echo "$default"
    return 0
  fi
  local buttons=""
  local b
  for b in "$@"; do
    if [ -n "$buttons" ]; then
      buttons="$buttons, "
    fi
    buttons="$buttons\"${b//\"/\\\"}\""
  done
  osascript -e "button returned of (display dialog \"${msg//\"/\\\"}\" buttons {$buttons} default button \"${default//\"/\\\"}\")"
}

bongo_open_url() {
  if command -v open >/dev/null 2>&1; then
    open "$1"
  else
    echo "Open: $1"
  fi
}

bongo_open_privacy_panes() {
  # Best-effort; URLs differ slightly across macOS versions.
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
  open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility" 2>/dev/null || true
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent" 2>/dev/null || true
}

bongo_ensure_venv() {
  local root="$1"
  local py="$2"
  local venv="$root/.venv"
  if [ ! -x "$venv/bin/python" ]; then
    echo "Setting up Bongo Cat (first run, about 30 seconds)..."
    "$py" -m venv "$venv"
  fi
  # shellcheck disable=SC1091
  source "$venv/bin/activate"
  pip install -q -r "$root/bongo_cat_app/requirements_app.txt"
}

bongo_start() {
  local root="$1"
  echo
  echo "Starting Bongo Cat."
  echo "If macOS asks, allow Accessibility + Input Monitoring, then quit and"
  echo "double-click Start Bongo Cat.command again."
  echo
  cd "$root"
  # shellcheck disable=SC1091
  source "$root/.venv/bin/activate"
  exec python3 "$root/bongo_cat_app/main.py" --no-tray
}

bongo_main() {
  export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
  local root
  root="$(bongo_repo_root)"
  cd "$root"

  local py
  if ! py="$(bongo_find_python)"; then
    local choice
    choice="$(bongo_choose "Bongo Cat needs Python 3 (free, from python.org). Install it, then double-click Start Bongo Cat again." "Get Python" "Get Python" "Quit")"
    if [ "$choice" = "Get Python" ]; then
      bongo_open_url "https://www.python.org/downloads/"
    fi
    exit 1
  fi
  if ! bongo_python_ok "$py"; then
    bongo_dialog "Python is too old. Install a current Python 3 from python.org, then try again."
    bongo_open_url "https://www.python.org/downloads/"
    exit 1
  fi

  bongo_ensure_venv "$root" "$py"

  if ! bongo_has_serial; then
    local choice
    choice="$(bongo_choose "No Bongo Cat USB device yet. Plug the cat in with a data cable (not charge-only). Charge-only cables fail. If it is plugged in and still missing, install a USB-serial driver." "Skip for now" "Try again" "Driver help" "Skip for now")"
    case "$choice" in
      "Driver help")
        local drv
        drv="$(bongo_choose "Most Cheap Yellow Display boards need a CH340 driver. CP2102 is the other common chip. Install, then unplug and replug the cat." "CH340" "CH340" "CP2102" "Cancel")"
        case "$drv" in
          CH340) bongo_open_url "https://github.com/WCHSoftGroup/ch34xser_macos" ;;
          CP2102) bongo_open_url "https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers" ;;
        esac
        ;;
      "Try again")
        if ! bongo_has_serial; then
          echo "Still no USB serial device. Starting anyway — you can replug the cable."
        fi
        ;;
    esac
  fi

  if bongo_gui; then
    bongo_open_privacy_panes
    bongo_dialog "macOS must allow Bongo Cat to see your typing.

In the Settings window that opened:
1. Privacy & Security → Accessibility → enable Terminal (or python3)
2. Privacy & Security → Input Monitoring → enable the same

Then click OK. If the cat does not react, quit and start this again."
  fi

  bongo_start "$root"
}

# Sourced by tests: do not run main.
if [ "${BONGO_SETUP_LIB:-}" = "1" ]; then
  return 0 2>/dev/null || exit 0
fi

bongo_main "$@"
