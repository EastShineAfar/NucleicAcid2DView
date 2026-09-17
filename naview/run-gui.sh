#!/bin/sh
# NAView structure drawing GUI - Linux / macOS launcher.
# The whole "naview" folder is self-contained; you only need Python 3.8+
# with tkinter (Debian/Ubuntu: sudo apt install python3-tk).
cd "$(dirname "$0")" || exit 1
for py in python3 python; do
    if command -v "$py" >/dev/null 2>&1; then
        exec "$py" gui.py
    fi
done
echo "Python 3 was not found on this computer." >&2
echo "Install it, then run this script again." >&2
exit 1
