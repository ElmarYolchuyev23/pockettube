import os, re, sys, zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
main_py = open(os.path.join(ROOT, "userdata/system/pockettube/main.py"), encoding="utf-8").read()
version = re.search(r'APP_VERSION = "([^"]+)"', main_py).group(1)
out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f"pockettube-v{version}.zip")

files = ["install.sh", "README.md", "THIRD_PARTY.md", "LICENSE", "CHANGELOG.md"]
for base, _, names in os.walk(os.path.join(ROOT, "userdata")):
    for n in names:
        files.append(os.path.relpath(os.path.join(base, n), ROOT).replace(os.sep, "/"))

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in sorted(files):
        info = zipfile.ZipInfo(f"pockettube/{rel}", date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (0o755 if rel.endswith(".sh") else 0o644) << 16
        with open(os.path.join(ROOT, rel), "rb") as f:
            z.writestr(info, f.read())
print(out, os.path.getsize(out), "bytes,", len(files), "files")
