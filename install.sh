#!/bin/bash
set -euo pipefail

usage() {
    cat <<'EOF'
PocketTube installer: an unofficial YouTube client for Linux handhelds with EmulationStation.
Safe to re-run: settings, history, playlists, downloads and cache are kept.
An older install (ytclient / YouTube.sh) is backed up and moved over automatically.

  bash install.sh                  install into /userdata
  bash install.sh --no-deno        skip deno (some videos won't get 720p)
  bash install.sh --update-ytdlp   install the latest yt-dlp even if one is present
  bash install.sh --prefix DIR     install into another folder (for testing), no carousel
  bash install.sh --no-es          don't touch the EmulationStation carousel
EOF
}

SRC="$(cd "$(dirname "$0")" && pwd)"
PREFIX=/userdata
WITH_DENO=1
UPDATE_YTDLP=0
WITH_ES=1
while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; WITH_ES=0; shift ;;
        --no-deno) WITH_DENO=0 ;;
        --update-ytdlp) UPDATE_YTDLP=1 ;;
        --no-es) WITH_ES=0 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
    shift
done

NAME=PocketTube
APP="$PREFIX/system/pockettube"
OLD_APP="$PREFIX/system/ytclient"
PORTS="$PREFIX/roms/ports"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$APP/backup-$STAMP"
ES=http://127.0.0.1:1234
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

say() { echo "==> $*"; }

mkdir -p "$PREFIX/system" "$PORTS/images"

if [ -d "$OLD_APP" ] && [ ! -d "$APP" ]; then
    MIG="$PREFIX/system/pockettube-migration-backup-$STAMP"
    say "Found an older install in $OLD_APP, backing it up to $MIG"
    mkdir -p "$MIG/ports/images"
    cp -a "$OLD_APP" "$MIG/ytclient"
    for f in YouTube.sh YouTube.sh.keys gamelist.xml; do
        if [ -e "$PORTS/$f" ]; then cp -a "$PORTS/$f" "$MIG/ports/"; fi
    done
    for f in "$PORTS"/images/youtube-*.png "$PORTS"/images/YouTube-*.png; do
        if [ -e "$f" ]; then cp -a "$f" "$MIG/ports/images/"; fi
    done
    mv "$OLD_APP" "$APP"
    if [ -f "$APP/data.json" ]; then
        python3 - "$APP/data.json" "$OLD_APP/" "$APP/" <<'PY'
import json, os, sys
path, old, new = sys.argv[1:4]
with open(path, encoding="utf-8") as f:
    data = json.load(f)


def fix(v):
    if isinstance(v, str):
        return v.replace(old, new)
    if isinstance(v, list):
        return [fix(x) for x in v]
    if isinstance(v, dict):
        return {k: fix(x) for k, x in v.items()}
    return v


with open(path + ".tmp", "w", encoding="utf-8") as f:
    json.dump(fix(data), f, ensure_ascii=False, indent=1)
os.replace(path + ".tmp", path)
PY
    fi
    rm -f "$PORTS/YouTube.sh" "$PORTS/YouTube.sh.keys" "$PORTS"/images/youtube-*.png "$PORTS"/images/YouTube-*.png
    rm -rf "$APP"/backup-* "$APP"/*.v[0-9] "$APP/input.conf" "$APP/yt-dlp"
    say "Moved the older install to $APP (backup kept in $MIG)"
elif [ -d "$OLD_APP" ]; then
    say "An older install is still in $OLD_APP; leaving it untouched"
fi

say "Installing into $PREFIX"
mkdir -p "$APP/assets"
copy() {
    local from="$SRC/userdata/$1" to="$2"
    if [ -f "$to" ] && ! cmp -s "$from" "$to"; then
        mkdir -p "$BACKUP"
        cp -a "$to" "$BACKUP/"
    fi
    cp "$from" "$to"
}
for f in main.py youtube.py store.py services.py sounds.py i18n.py player.py player-input.conf; do
    copy "system/pockettube/$f" "$APP/$f"
done
copy system/pockettube/assets/logo.png "$APP/assets/logo.png"
mkdir -p "$APP/assets/fonts"
for f in Inter-Regular.ttf Inter-SemiBold.ttf Inter-LICENSE.txt; do
    copy "system/pockettube/assets/fonts/$f" "$APP/assets/fonts/$f"
done
copy "roms/ports/$NAME.sh" "$PORTS/$NAME.sh"
copy "roms/ports/$NAME.sh.keys" "$PORTS/$NAME.sh.keys"
for f in pockettube-icon.png pockettube-marquee.png pockettube-screenshot.png; do
    copy "roms/ports/images/$f" "$PORTS/images/$f"
done
chmod +x "$PORTS/$NAME.sh"
if [ -d "$BACKUP" ]; then
    say "Previous versions of changed files: $BACKUP"
fi

if [ ! -d "$APP/ytdlp_src/yt_dlp" ] || [ "$UPDATE_YTDLP" = 1 ]; then
    say "Downloading yt-dlp"
    curl -fsSL -o "$TMP/yt-dlp" https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp
    rm -rf "$APP/ytdlp_src.new"
    python3 - "$TMP/yt-dlp" "$APP/ytdlp_src.new" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
names = [n for n in z.namelist() if n != "__main__.py" and not n.startswith("/") and ".." not in n]
assert any(n.startswith("yt_dlp/") for n in names), "no yt_dlp in the archive"
z.extractall(sys.argv[2], names)
PY
    VER="$(python3 -c 'import sys;sys.path.insert(0,sys.argv[1]);import yt_dlp;print(yt_dlp.version.__version__)' "$APP/ytdlp_src.new")"
    python3 -m compileall -q "$APP/ytdlp_src.new" >/dev/null || true
    if [ -d "$APP/ytdlp_src" ]; then
        rm -rf "$APP/ytdlp_src.old"
        mv "$APP/ytdlp_src" "$APP/ytdlp_src.old"
    fi
    mv "$APP/ytdlp_src.new" "$APP/ytdlp_src"
    say "yt-dlp $VER installed"
else
    say "yt-dlp already present, keeping it (update with --update-ytdlp or from the app settings)"
fi

if [ "$WITH_DENO" = 1 ]; then
    if [ -x "$APP/bin/deno" ] && "$APP/bin/deno" --version >/dev/null 2>&1; then
        say "deno already present: $("$APP/bin/deno" --version | head -1)"
    else
        case "$(uname -m)" in
            aarch64) ARCH=aarch64 ;;
            x86_64) ARCH=x86_64 ;;
            *) ARCH="" ;;
        esac
        if [ -z "$ARCH" ]; then
            say "No deno build for $(uname -m), skipping"
        else
            say "Downloading deno ($ARCH, ~40 MB)"
            curl -fsSL -o "$TMP/deno.zip" "https://github.com/denoland/deno/releases/latest/download/deno-$ARCH-unknown-linux-gnu.zip"
            mkdir -p "$APP/bin"
            python3 -c 'import sys,zipfile;zipfile.ZipFile(sys.argv[1]).extract("deno",sys.argv[2])' "$TMP/deno.zip" "$TMP"
            chmod +x "$TMP/deno"
            if "$TMP/deno" --version >/dev/null 2>&1; then
                mv "$TMP/deno" "$APP/bin/deno"
                say "$("$APP/bin/deno" --version | head -1) installed"
            else
                say "deno doesn't run on this system, continuing without it"
            fi
        fi
    fi
fi

if [ "$WITH_ES" = 1 ] && curl -fs -o /dev/null "$ES/systems/ports/games"; then
    say "Updating the Ports carousel"
    find_gid() {
        curl -fs "$ES/systems/ports/games" | python3 -c '
import sys, json
for g in json.load(sys.stdin):
    if g.get("path", "").endswith("/PocketTube.sh"):
        print(g["id"]); break' || true
    }
    is_done() {
        curl -fs "$ES/systems/ports/games/$1" | python3 -c '
import sys, json
g = json.load(sys.stdin)
sys.exit(0 if g.get("name") == "PocketTube" and g.get("image") else 1)' 2>/dev/null
    }
    GID="$(find_gid)"
    if [ -z "$GID" ]; then
        curl -fs -o /dev/null "$ES/reloadgames" || true
        sleep 8
        GID="$(find_gid)"
    fi
    if [ -n "$GID" ]; then
        cat > "$TMP/meta.json" <<'JSON'
{"name": "PocketTube",
 "desc": "Unofficial YouTube client for handhelds: search and watch videos, live streams, playlists, subtitles and chapters, downloads for offline viewing, audio-only mode. Gamepad controls.",
 "genre": "Video", "players": "1", "developer": "PocketTube"}
JSON
        curl -fs -o /dev/null -X POST -H 'Content-Type: application/json' \
            --data-binary @"$TMP/meta.json" "$ES/systems/ports/games/$GID" || true
        for pair in image:pockettube-screenshot.png marquee:pockettube-marquee.png thumbnail:pockettube-icon.png; do
            curl -fs -o /dev/null -X POST -H 'Content-Type: image/png' \
                --data-binary @"$PORTS/images/${pair#*:}" "$ES/systems/ports/games/$GID/media/${pair%%:*}" || true
        done
        if is_done "$GID"; then
            say "PocketTube is in Ports with its description and artwork"
        else
            say "EmulationStation didn't accept the metadata: restart EmulationStation and run the installer again"
        fi
    else
        say "PocketTube.sh not found in Ports: restart EmulationStation and run the installer again"
    fi
else
    say "Carousel skipped (EmulationStation not responding, or --no-es/--prefix)"
fi

cd "$APP"
python3 -c 'import ast,sys;[ast.parse(open(f).read()) for f in sys.argv[1:]]' main.py youtube.py store.py services.py sounds.py i18n.py player.py
if python3 -c 'import sys;sys.path.insert(0,"ytdlp_src");import yt_dlp' 2>/dev/null; then
    say "Done. Launch it from Ports → PocketTube"
else
    echo "!! yt-dlp can't be imported, run again with --update-ytdlp"
    exit 1
fi
