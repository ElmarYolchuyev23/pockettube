import os, sys, shutil, tempfile, types

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)
work = tempfile.mkdtemp()
app_dir = os.path.join(work, "pockettube")
shutil.copytree(os.path.join(ROOT, "userdata", "system", "pockettube"), app_dir)
sys.path.insert(0, app_dir)

import i18n

yt = types.ModuleType("youtube")
yt.VERSION = "2026.10.26"
yt.thumb_url = lambda vid: "http://127.0.0.1:9/none.jpg"
yt.format_duration = lambda sec: (lambda s: f"{s // 3600}:{s // 60 % 60:02}:{s % 60:02}" if s >= 3600 else f"{s // 60}:{s % 60:02}")(int(sec or 0))
yt.format_size = lambda n: "" if not n else (i18n.T("gb", n=i18n.decimal(n / 1024 ** 3)) if n >= 1024 ** 3 else i18n.T("mb", n=round(n / 1024 ** 2)))
yt.has_rollback = lambda: False
yt.FILTERS = {
    "sort": [("relevance", 0), ("date", 2), ("views", 3)],
    "date": [("any", 0), ("hour", 1), ("today", 2), ("week", 3), ("month", 4), ("year", 5)],
    "duration": [("any", 0), ("short", 1), ("medium", 3), ("long", 2)],
    "type": [("any", 0), ("video", 1), ("live", "live"), ("playlist", 3)],
}
sys.modules["youtube"] = yt
import services

services.check_online = lambda: True
services.start_network_monitor = lambda period=15: None
services.battery_level = lambda: 80
services.free_space = lambda p: 48 * 1024 ** 3
services.Downloader = lambda *a, **k: types.SimpleNamespace(kick=lambda: None, cancel=lambda v: None)
import main

main.FONT = os.path.join(FONTS, "DejaVuSans.ttf")
main.FONT_BOLD = os.path.join(FONTS, "DejaVuSans-Bold.ttf")
main.App.show_splash = lambda self: main.load_backend()
main.time.strftime = lambda fmt, *a: "12:00"
main.Task = lambda fn, *a: types.SimpleNamespace(done=True, result=None, error=None)
pg = main.pygame

DEMO_DIR = os.path.join(ROOT, "tools", "demo")
DEMO = [
    {"id": "eRsGyueVLvQ", "title": "Sintel - Open Movie by Blender Foundation", "channel": "Blender", "duration": 888, "pos": 410},
    {"id": "R6MlUcmOul8", "title": "Tears of Steel - Blender VFX Open Movie", "channel": "Blender", "duration": 735, "pos": 300},
    {"id": "WhWc3b3KhnY", "title": "Spring - Blender Open Movie", "channel": "Blender Studio", "duration": 465, "pos": 200},
    {"id": "aqz-KE-bpKQ", "title": "Big Buck Bunny - Blender Foundation Short Film", "channel": "Blender", "duration": 635, "pos": 0},
    {"id": "Ke6XX8FHOHM", "title": "Artemis II to the Moon: Mission Animation", "channel": "NASA", "duration": 465, "pos": 0},
    {"id": "UXqq0ZvbOnk", "title": "CHARGE - Blender Open Movie", "channel": "Blender Studio", "duration": 263, "pos": 0},
    {"id": "Y-rmzh0PI3c", "title": "Cosmos Laundromat - First Cycle", "channel": "Blender", "duration": 731, "pos": 0},
]
_thumbs = {}


def demo_thumb(self, vid, w, h):
    key = (vid, w, h)
    if key not in _thumbs:
        path = os.path.join(DEMO_DIR, vid + ".jpg")
        _thumbs[key] = pg.transform.smoothscale(pg.image.load(path), (w, h)) if os.path.exists(path) else None
    return _thumbs[key]


services.Thumbs.get = demo_thumb

app = main.App()
app.store.data["history"] = [dict(v) for v in DEMO[:4]]
app.store.data["queries"] = ["blender open movie", "sintel", "space"]
app.store.data["playlists"] = [{"id": "wl", "name": "", "items": [dict(DEMO[3]), dict(DEMO[5])]},
                               {"id": "p1", "name": "Open movies", "items": [dict(v) for v in DEMO if v["channel"] != "NASA"]}]
app.store.data["downloads"] = [dict(DEMO[2], status="done", progress=1, file="x", size=7 * 1024 ** 2, quality="audio", audio=True),
                               dict(DEMO[3], status="done", progress=1, file="x", size=96 * 1024 ** 2, quality="480p"),
                               dict(DEMO[1], status="loading", progress=0.42, file="", size=0, quality="480p")]
app.store.save = lambda: None


def shot(lang, name):
    app.draw()
    pg.image.save(app.screen, os.path.join(OUT, f"{lang}-{name}.png"))


for lang in ["en", "ru"]:
    i18n.set_lang(lang)
    app.store.settings["lang"] = lang
    app.toasts = []
    app.draw_splash(0.6)
    pg.image.save(app.screen, os.path.join(OUT, f"{lang}-splash.png"))
    app.view = "home"
    shot(lang, "home")
    app.lang = lang
    app.view, app.query, app.sugg, app.kx, app.ky = "search", "blender", ["blender open movie", "blender studio"], 4, 2
    shot(lang, "search")
    app.view, app.searched, app.results, app.sel, app.search_task = "results", "blender open movie", [dict(v) for v in DEMO], 1, None
    app.filters, app.filter_open = {"duration": "long"}, False
    shot(lang, "results")
    app.filter_open, app.fsel = True, 2
    shot(lang, "filters")
    app.filter_open = False
    app.video = dict(DEMO[0])
    app.details = {"id": DEMO[0]["id"], "description": "Sintel is an open movie by the Blender Foundation, released under Creative Commons Attribution.", "size": 120 * 1024 ** 2, "live": False}
    app.details_task, app.related_task, app.related = None, None, [dict(v) for v in DEMO[1:4]]
    app.view, app.vfocus, app.vbtn = "video", "buttons", 0
    shot(lang, "video")
    app.view, app.lsel = "playlists", 0
    shot(lang, "playlists")
    app.view, app.dsel = "downloads", 0
    shot(lang, "downloads")
    app.view, app.ssel = "settings", 0
    shot(lang, "settings")
shutil.rmtree(work, ignore_errors=True)
print("screenshots written to", OUT)
