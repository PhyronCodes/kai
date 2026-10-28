#!/bin/bash
# Starts KAI full screen. Used by the autostart entry (kai.desktop) at login.

cd "$(dirname "$0")"              # the kai folder, wherever it lives
source .venv/bin/activate

# Wait (up to a minute) for the internet, since KAI's brain is Gemini
for i in $(seq 1 30); do
    if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
        break
    fi
    sleep 2
done

# Run KAI. A normal goodbye exits with code 0 and stays closed;
# a crash exits with an error code, so it restarts after 3 seconds.
while true; do
    echo "--- KAI started $(date) ---" >> kai.log
    python voice.py --fullscreen >> kai.log 2>&1
    if [ $? -eq 0 ]; then
        break
    fi
    sleep 3
done
