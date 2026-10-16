#!/bin/bash
# One-time Pi setup (safe to re-run):  sudo Project2/pi/install.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }

DIR=$(cd "$(dirname "$0")/../.." && pwd)
OWNER=$(stat -c %U "$DIR")
as_owner() { runuser -u "$OWNER" -- "$@"; }

apt-get install -y git python3-venv python3-dev build-essential python3-gpiozero python3-lgpio

# system site packages: gpiozero + lgpio come from apt
[ -x "$DIR/.venv/bin/python" ] || as_owner python3 -m venv --system-site-packages "$DIR/.venv"
as_owner "$DIR/.venv/bin/pip" install -q -r "$DIR/Project2/requirements-pi.txt"

# GPIO18 PWM is shared with onboard audio
for cfg in /boot/firmware/config.txt /boot/config.txt; do
    if [ -f "$cfg" ]; then
        if grep -q '^dtparam=audio=on' "$cfg"; then
            sed -i 's/^dtparam=audio=on/dtparam=audio=off/' "$cfg"
            echo "install: disabled onboard audio in $cfg, reboot needed"
        fi
        break
    fi
done

for unit in obd2led.service obd2led-update.service obd2led-update.timer; do
    sed "s|@DIR@|$DIR|g" "$DIR/Project2/pi/systemd/$unit" > "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable obd2led.service obd2led-update.timer
systemctl restart obd2led.service
systemctl start obd2led-update.timer
echo "install: done, logs: journalctl -u obd2led -f"
