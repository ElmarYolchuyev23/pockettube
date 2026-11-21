"""Frame-time benchmark of the interface on demo data. No network or gamepad needed.

Run it on the handheld (or a PC) from a copy of this repository:
    python3 tools/perf.py              # prints a table
    python3 tools/perf.py result.json  # also saves the numbers

Every screen is drawn at rest and while navigating (an arrow key every 6 frames, so the focus
ring and lists keep animating). The app targets 30 frames per second, so a frame must stay
well under 33 ms: p95 is the frame time that 95% of frames beat, max is the slowest one.
"""
import json, os, statistics, sys, tempfile, time, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else None
src = open(os.path.join(ROOT, "tools", "screenshots.py"), encoding="utf-8").read().split("def shot(")[0]
shots_dir = tempfile.mkdtemp()  # the screenshot prelude wants an output folder; nothing is written to it
sys.argv = ["screenshots.py", "/usr/share/fonts/dejavu", shots_dir]
g = {"__file__": os.path.join(ROOT, "tools", "screenshots.py"), "__name__": "perf"}
exec(compile(src, "screenshots-prelude", "exec"), g)
app, pg, DEMO = g["app"], g["pg"], g["DEMO"]
app.sfx.play = lambda *a, **k: None

WARM, N, EVERY = 20, 300, 6


def setup(view):
    app.toasts, app.filter_open = [], False
    if view == "home":
        app.view, app.home_row, app.home_col = "home", 0, 0
    elif view == "search":
        app.view, app.lang, app.query, app.sugg, app.kx, app.ky = "search", "en", "blender", ["a", "b"], 4, 2
    elif view == "results":
        app.view, app.searched, app.results, app.sel, app.search_task = "results", "blender", [dict(v) for v in DEMO] * 3, 1, None
    elif view == "loading":
        app.view, app.searched, app.search_task = "results", "blender", types.SimpleNamespace(done=False)
    elif view == "video":
        app.video = dict(DEMO[0])
        app.details = {"id": DEMO[0]["id"], "description": "Sintel is an open movie by the Blender Foundation.",
                       "size": 120 * 1024 ** 2, "live": False}
        app.details_task, app.related_task, app.related = None, None, [dict(v) for v in DEMO[1:]]
        app.view, app.vfocus, app.vbtn = "video", "buttons", 0
    elif view == "settings":
        app.view, app.ssel = "settings", 0


KEYS = {"home": (pg.K_RIGHT, pg.K_LEFT), "search": (pg.K_RIGHT, pg.K_LEFT), "results": (pg.K_DOWN, pg.K_UP),
        "loading": None, "video": (pg.K_DOWN, pg.K_UP), "settings": (pg.K_DOWN, pg.K_UP)}


def run(view, navigate):
    setup(view)
    keys = KEYS[view] if navigate else None
    times = []
    for f in range(WARM + N):
        if keys and f % EVERY == 0:
            app.on_key(keys[0] if (f // EVERY) % 6 < 3 else keys[1])  # 3 steps forward, 3 back
            if view == "search" and app.view != "search":
                setup(view)
        t = time.perf_counter()
        app.draw()
        if f >= WARM:
            times.append((time.perf_counter() - t) * 1000)
    times.sort()
    return {"mean": round(statistics.mean(times), 2), "p95": round(times[int(len(times) * 0.95)], 2),
            "max": round(times[-1], 2)}


results = {}
print(f"{'screen':16} {'mean ms':>8} {'p95 ms':>8} {'max ms':>8}")
for view in KEYS:
    for navigate in (False, True):
        if view == "loading" and navigate:
            continue
        name = view + (" + nav" if navigate else "")
        r = results[name] = run(view, navigate)
        print(f"{name:16} {r['mean']:8.2f} {r['p95']:8.2f} {r['max']:8.2f}")
worst = max(r["p95"] for r in results.values())
print(f"\nworst p95: {worst:.1f} ms of the 33 ms frame budget at 30 fps"
      + ("  - OK" if worst < 20 else "  - tight, the interface may stutter"))
if OUT:
    json.dump(results, open(OUT, "w"), indent=1)
os.rmdir(shots_dir)
