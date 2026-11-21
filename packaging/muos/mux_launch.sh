#!/bin/sh
# HELP: Unofficial YouTube client: search, watch and download videos
# ICON: pockettube
# GRID: PocketTube

. /opt/muos/script/var/func.sh

SETUP_APP "python3" ""
SET_VAR "system" "foreground_process" "python3"

# PocketTube runs on PortMaster's Python runtime; muOS ships PortMaster in MUOS/PortMaster,
# which the launcher finds through XDG_DATA_HOME
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
export XDG_DATA_HOME="$(GET_VAR "device" "storage/rom/mount")/MUOS"
export POCKETTUBE_DIR="$APP_DIR/pockettube"

bash "$APP_DIR/PocketTube.sh"
