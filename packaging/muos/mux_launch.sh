#!/bin/sh
# HELP: Unofficial YouTube client: search, watch and download videos
# ICON: pockettube
# GRID: PocketTube

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
exec >"$APP_DIR/launch.log" 2>&1

# muOS 2601 ships func.sh; newer builds moved the helpers to retro.sh
if [ -f /opt/muos/script/var/func.sh ]; then
	. /opt/muos/script/var/func.sh
else
	. /opt/muos/script/var/retro.sh
fi

SETUP_APP "python3" ""
SET_VAR "system" "foreground_process" "python3"

# PocketTube runs on PortMaster's Python runtime; muOS ships PortMaster in MUOS/PortMaster,
# which the launcher finds through XDG_DATA_HOME
for MUOS_DIR in "$(GET_VAR "device" "storage/rom/mount")/MUOS" /mnt/mmc/MUOS /mnt/sdcard/MUOS; do
	[ -f "$MUOS_DIR/PortMaster/control.txt" ] && break
done
if [ ! -f "$MUOS_DIR/PortMaster/control.txt" ]; then
	echo "PortMaster not found: open Applications > PortMaster once to set it up"
	exit 1
fi
echo "PortMaster: $MUOS_DIR/PortMaster"

export XDG_DATA_HOME="$MUOS_DIR"
export POCKETTUBE_DIR="$APP_DIR/pockettube"
chmod +x "$APP_DIR/PocketTube.sh" 2>/dev/null

bash "$APP_DIR/PocketTube.sh"
