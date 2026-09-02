#!/bin/bash
# Double-click this on a Mac. First run installs what is needed; later runs
# just start Bongo Cat. Keep this file inside the unzipped project folder.
set -euo pipefail
cd "$(dirname "$0")"
chmod +x mac/setup_macos.sh 2>/dev/null || true
exec bash mac/setup_macos.sh
