#!/bin/bash
# Double-click on macOS. Runs the Python host in Terminal.
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 from https://www.python.org/downloads/"
  read -r -p "Press Return to close..."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r bongo_cat_app/requirements_app.txt

echo "Serial smoke test..."
python3 tools/serial_smoke.py || true
echo
echo "Starting Bongo Cat. Grant Accessibility if asked, then relaunch."
exec python3 bongo_cat_app/main.py --no-tray
