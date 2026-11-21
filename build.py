"""Build the release files from this repository into dist/:

  pockettube-knulli-vX.Y.zip      KNULLI / Batocera: unpack on the console and run install.sh
  pockettube-portmaster-vX.Y.zip  PortMaster port for any firmware (KNULLI, muOS, ROCKNIX, ArkOS, AmberELEC...)
  PocketTube-vX.Y.muxapp          muOS application (Applications > Archive Manager)

Usage: python build.py [out_dir] [--update-ytdlp]
The PortMaster and muOS packages bundle yt-dlp; the official release is downloaded once and kept in dist/cache.
"""
import io, os, re, subprocess, sys, time, urllib.request, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = "userdata/system/pockettube"
PM = "packaging/portmaster"
MUOS = "packaging/muos"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
DATE = (2026, 1, 1, 0, 0, 0)

args = [a for a in sys.argv[1:] if not a.startswith("--")]
out_dir = args[0] if args else os.path.join(ROOT, "dist")
version = re.search(r'APP_VERSION = "([^"]+)"', open(os.path.join(ROOT, APP, "main.py"), encoding="utf-8").read()).group(1)


def tracked(prefix):
    """Files under prefix that are in git, so local data (data.json, cache, downloads) never ships."""
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "--", prefix], capture_output=True, check=True).stdout
    return sorted(p for p in out.decode().split("\0") if p)


def read(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return f.read()


class Archive:
    def __init__(self, path, prefix="", stored=False):
        self.z = zipfile.ZipFile(path, "w", zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED)
        self.prefix, self.path, self.count = prefix, path, 0

    def add(self, name, data):
        # a script or key map with Windows line endings gives a black screen and no log on the console
        if name.endswith((".sh", ".gptk", ".ini", ".py", ".conf")) and b"\r\n" in data:
            raise SystemExit(f"{name} has CRLF line endings")
        info = zipfile.ZipInfo(self.prefix + name, date_time=DATE)
        info.compress_type = self.z.compression
        info.external_attr = (0o755 if name.endswith(".sh") else 0o644) << 16
        self.z.writestr(info, data)
        self.count += 1

    def close(self):
        self.z.close()
        print(f"{os.path.relpath(self.path, ROOT)}: {os.path.getsize(self.path) // 1024} KB, {self.count} files")


def ytdlp_files():
    cache = os.path.join(ROOT, "dist", "cache", "yt-dlp")
    if not os.path.exists(cache) or "--update-ytdlp" in sys.argv:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        for attempt in range(5):
            try:
                with urllib.request.urlopen(YTDLP_URL, timeout=60) as r:
                    data = r.read()
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(3)
        with open(cache, "wb") as f:
            f.write(data)
    z = zipfile.ZipFile(io.BytesIO(read(cache)))
    names = [n for n in z.namelist() if n != "__main__.py" and not n.endswith("/") and not n.startswith("/") and ".." not in n]
    assert any(n.startswith("yt_dlp/") for n in names), "no yt_dlp in the yt-dlp release"
    return [(n, z.read(n)) for n in names]


def port_payload(ytdlp):
    """The pockettube/ folder shared by the PortMaster port and the muOS app."""
    files = [(rel[len(APP) + 1:], read(rel)) for rel in tracked(APP)]
    files += [(name, read(f"{PM}/{name}")) for name in ("pockettube.gptk", "port.json", "README.md", "gameinfo.xml")]
    files.append(("screenshot.png", read("docs/screenshots/en-home.png")))
    files += [(rel[len(PM) + 1:], read(rel)) for rel in tracked(f"{PM}/licenses")]
    files += [(rel[len(PM) + len("/vendor/"):], read(rel)) for rel in tracked(f"{PM}/vendor")]
    files += [("ytdlp_src/" + n, data) for n, data in ytdlp]
    return files


os.makedirs(out_dir, exist_ok=True)

knulli = Archive(os.path.join(out_dir, f"pockettube-knulli-v{version}.zip"), "pockettube/")
for rel in ["install.sh", "README.md", "THIRD_PARTY.md", "LICENSE", "CHANGELOG.md"] + tracked("userdata"):
    knulli.add(rel, read(rel))
knulli.close()

payload = port_payload(ytdlp_files())

port = Archive(os.path.join(out_dir, f"pockettube-portmaster-v{version}.zip"))
port.add("PocketTube.sh", read(f"{PM}/PocketTube.sh"))
for name, data in payload:
    port.add("pockettube/" + name, data)
port.close()

# muOS unpacks the archive at the root of the SD card; Archive Manager expects plain STORE zips
mux = Archive(os.path.join(out_dir, f"PocketTube-v{version}.muxapp"), "mnt/mmc/MUOS/application/PocketTube/", stored=True)
for rel in tracked(MUOS):
    mux.add(rel[len(MUOS) + 1:], read(rel))
mux.add("PocketTube.sh", read(f"{PM}/PocketTube.sh"))
for name, data in payload:
    mux.add("pockettube/" + name, data)
mux.close()
