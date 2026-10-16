#!/bin/bash
# Run by obd2led-update.timer: pull from GitHub, check, restart. Offline is not an error.
set -u

DIR=$(cd "$(dirname "$0")/../.." && pwd)
OWNER=$(stat -c %U "$DIR")
as_owner() { runuser -u "$OWNER" -- "$@"; }
cd "$DIR"

old=$(as_owner git rev-parse HEAD)
if ! as_owner timeout 60 git pull --ff-only -q; then
    echo "update: pull failed (offline?), staying on $old"
    exit 0
fi
new=$(as_owner git rev-parse HEAD)
[ "$old" = "$new" ] && exit 0

if ! as_owner .venv/bin/python -m Project2.pi.check; then
    echo "update: $new fails the check, rolling back to $old"
    as_owner git reset -q --hard "$old"
    exit 1
fi

if ! git diff --quiet "$old" "$new" -- Project2/requirements-pi.txt Project2/pi/systemd Project2/pi/install.sh; then
    echo "update: dependencies or services changed, re-running install.sh"
    Project2/pi/install.sh   # restarts obd2led itself
else
    systemctl restart obd2led.service
fi
echo "update: $old -> $new"
