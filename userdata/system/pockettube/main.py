import os, sys, threading, time
import pygame

import i18n
import player
import services
from i18n import T
import sounds as sounds_mod
import store as store_mod

youtube = None
load_error = None

APP_VERSION = "1.0"
APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = "PocketTube"
W, H = 640, 480
FONT = os.path.join(APP_DIR, "assets", "fonts", "Inter-Regular.ttf")
FONT_BOLD = os.path.join(APP_DIR, "assets", "fonts", "Inter-SemiBold.ttf")
FALLBACK_FONT = "/usr/share/fonts/dejavu/DejaVuSans.ttf"
FALLBACK_FONT_BOLD = "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"

# Palette, darkest to lightest
BG = (15, 15, 15)
FIELD = (18, 18, 18)
SURF_DARK = (24, 24, 24)
SKEL = (28, 28, 28)
SURF_LOW = (30, 30, 30)
LINE = (34, 34, 34)
SURF = (39, 39, 39)
SURF_HI = (58, 58, 58)
TRACK = (77, 77, 77)
MUTED = (138, 138, 138)
DIM = (170, 170, 170)
SOFT = (204, 204, 204)
FG = (241, 241, 241)
INK = (15, 15, 15)
VEIL = (0, 0, 0, 170)
ACC = (124, 92, 255)
LIVE_RED = (230, 33, 60)
ERR_RED = (255, 90, 110)
ERR_SOFT = (255, 138, 155)
FOCUS_W = 2  # width of the accent focus ring
ERR_BG, ERR_FG = (58, 20, 24), (255, 218, 223)
TINTS = [(59, 47, 74), (47, 74, 68), (74, 59, 47), (47, 61, 74), (74, 47, 59), (59, 74, 47)]

TABS = ["home", "search", "history", "downloads", "playlists"]
FILTER_KEYS = ["sort", "date", "duration", "type"]
KB = {
    "en": ["1234567890", "qwertyuiop", "asdfghjkl'", "zxcvbnm,.-"],
    "ru": ["1234567890", "йцукенгшщзхъ", "фывапролджэ", "ячсмитьбюё.-"],
}
SPECIAL = ["lang", "space", "erase", "find"]

K_A, K_B, K_X, K_Y = pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_SPACE
K_START, K_SELECT, K_L1, K_R1 = pygame.K_q, pygame.K_TAB, pygame.K_PAGEUP, pygame.K_PAGEDOWN


def load_backend():
    global youtube, load_error
    try:
        import youtube as yt
        youtube = yt
        services.check_online()
    except Exception as e:
        load_error = e


_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        try:
            _fonts[key] = pygame.font.Font(FONT_BOLD if bold else FONT, size)
        except (pygame.error, OSError):
            _fonts[key] = pygame.font.Font(FALLBACK_FONT_BOLD if bold else FALLBACK_FONT, size)
    return _fonts[key]


def clean(s):
    return "".join(ch for ch in str(s)
                   if ord(ch) < 0x2000 or 0x2010 <= ord(ch) <= 0x2026 or 0x25A0 <= ord(ch) <= 0x25FF)


def ellipsize(s, f, max_w):
    s = clean(s)
    if f.size(s)[0] <= max_w:
        return s
    while s and f.size(s + "…")[0] > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def wrap(s, f, max_w, max_lines):
    words, lines, cur = clean(s).replace("\n", " ").split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.size(test)[0] <= max_w:
            cur = test
            continue
        if cur:
            lines.append(cur)
        cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and " ".join(lines) != " ".join(words):
        lines[-1] = ellipsize(lines[-1] + " …", f, max_w)
    return lines


def text(surf, s, pos, size=14, color=FG, bold=False, max_w=None, center=False, right=False):
    f = font(size, bold)
    s = ellipsize(s, f, max_w) if max_w else clean(s)
    img = f.render(s, True, color)
    x, y = pos
    if center:
        x -= img.get_width() // 2
    elif right:
        x -= img.get_width()
    surf.blit(img, (x, y))
    return img.get_width()


class Task:

    def __init__(self, fn, *args):
        self.done, self.result, self.error = False, None, None
        threading.Thread(target=self._run, args=(fn, args), daemon=True).start()

    def _run(self, fn, args):
        try:
            self.result = fn(*args)
        except Exception as e:
            self.error = e
        self.done = True


class App:
    def __init__(self):
        sounds_mod.prepare_env()
        pygame.init()
        pygame.mouse.set_visible(False)
        pygame.key.set_repeat(350, 90)
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(APP_NAME)
        self.logo_src = None
        try:
            self.logo_src = pygame.image.load(os.path.join(APP_DIR, "assets", "logo.png"))
        except (pygame.error, FileNotFoundError):
            pass
        self.logo_cache = {}
        self.toasts = []
        self.anims, self.anim_prev, self.anim_now, self.focus_ring, self.list_off = {}, set(), set(), None, 0
        self.store = store_mod.Store()
        i18n.set_lang(self.store.settings["lang"])
        self.show_splash()

        self.sfx = sounds_mod.Sounds(self.store.settings.get("sounds", True))
        self.thumbs = services.Thumbs(youtube.thumb_url)
        self.downloader = services.Downloader(self.store, youtube, self.thumbs, self.notify)
        services.start_network_monitor()

        self.view = "home" if services.is_online() else "offline"
        self.back_view = "home"
        self.home_row, self.home_col = 0, 0
        self.query, self.lang = "", self.store.settings.get("kb_layout", "en")
        self.kx, self.ky = 0, 1
        self.sugg, self.sugg_i, self.sugg_for, self.sugg_due, self.sugg_task = [], 0, "", 0, None
        self.results, self.sel, self.search_task, self.searched = [], 0, None, ""
        self.hsel, self.dsel, self.ssel, self.obtn = 0, 0, 0, 0
        self.retry_task = None
        self.video, self.details, self.details_task, self.vbtn = None, None, None, 0
        self.yt_task, self.yt_progress, self.yt_action, self.restart_at = None, 0.0, 0, 0
        self.filters = dict(self.store.settings.get("filters") or {})
        self.filter_open, self.fsel, self.filters_backup = False, 0, {}
        self.related, self.related_task, self.rsel, self.vfocus = [], None, 0, "buttons"
        self.lsel, self.plist, self.pisel, self.plist_task = 0, None, 0, None
        self.pick_sel, self.pick_back = 0, "video"
        self.kb_target, self.saved_query, self.name_back = "search", "", "playlists"
        self.del_confirm = (None, 0)

    # --- motion -------------------------------------------------------------

    def anim(self, key, target, k=0.45):
        """Ease a tuple of numbers towards target; snaps when the key wasn't drawn last frame."""
        cur = self.anims.get(key)
        if cur is None or key not in self.anim_prev or len(cur) != len(target):
            cur = list(target)
        else:
            cur = [t if abs(t - c) < 0.5 else c + (t - c) * k for c, t in zip(cur, target)]
        self.anims[key] = cur
        self.anim_now.add(key)
        return cur

    def hl(self, rect, radius=10, fill=None, grow=0, key=None):
        """Focus highlight: optional fill under the item now, accent ring on top at the end of the frame."""
        # animate in content coordinates so the ring stays put while its list scrolls
        target = pygame.Rect(rect).inflate(grow, grow).move(0, round(self.list_off))
        x, y, w, h = self.anim("focus:" + (key or self.view), tuple(target))
        r = pygame.Rect(round(x), round(y - self.list_off), round(w), round(h))
        if fill:
            pygame.draw.rect(self.screen, fill, r.inflate(-grow, -grow), border_radius=radius)
        self.focus_ring = (r, radius + grow // 2, self.screen.get_clip())

    def scroller(self, key, first, count, per, row_h, top_y, bar=True):
        """Smoothly scrolled list window: returns (offset, visible indexes, clip) and draws the scrollbar.
        Clips drawing to the list until end_list()."""
        off = self.anim("scroll:" + key, (first * row_h,))[0]
        start = int(off // row_h)
        end = min(count, start + per + (1 if off != start * row_h else 0))
        if bar and count > per:
            track = pygame.Rect(W - 12, top_y + 4, 4, per * row_h - 8)
            pygame.draw.rect(self.screen, SURF, track, border_radius=2)
            hgt = max(20, track.h * per // count)
            pos = track.y + int((track.h - hgt) * off / ((count - per) * row_h))
            pygame.draw.rect(self.screen, DIM, (track.x, pos, 4, hgt), border_radius=2)
        self.list_off = off
        self.screen.set_clip(pygame.Rect(0, top_y - 3, W, per * row_h + 3))
        return off, range(start, end)

    def end_list(self):
        self.list_off = 0
        self.screen.set_clip(None)

    def show_splash(self):
        thread = threading.Thread(target=load_backend, daemon=True)
        thread.start()
        clock, progress = pygame.time.Clock(), 0.0
        while thread.is_alive() or progress < 1.0:
            pygame.event.pump()
            if thread.is_alive():
                progress += (0.9 - progress) * 0.05
            else:
                progress = min(1.0, progress + 0.08)
            self.draw_splash(progress)
            clock.tick(30)
        if load_error:
            self.screen.fill(BG)
            text(self.screen, T("start_error", err=load_error), (20, H // 2), 13, ERR_RED, max_w=W - 40)
            pygame.display.flip()
            pygame.time.wait(5000)
            raise SystemExit(1)

    def draw_splash(self, progress):
        s = self.screen
        s.fill(BG)
        size, gap = 96, 14
        a = font(44, True).render("Pocket", True, FG)
        b = font(44, True).render("Tube", True, ACC)
        total = int(size * 0.78) + gap + a.get_width() + b.get_width()
        x, y = (W - total) // 2, 150
        self.draw_logo(x - int(size * 0.11), y, size)
        tx = x + int(size * 0.78) + gap
        s.blit(a, (tx, y + size // 2 - a.get_height() // 2))
        s.blit(b, (tx + a.get_width(), y + size // 2 - b.get_height() // 2))
        lh = size
        bw = 275
        bar = pygame.Rect((W - bw) // 2, y + lh + 35, bw, 5)
        pygame.draw.rect(s, SURF, bar, border_radius=3)
        pygame.draw.rect(s, ACC, (bar.x, bar.y, int(bw * progress), 5), border_radius=3)
        text(s, T("starting"), (W // 2, bar.bottom + 12), 16, DIM, center=True)
        pygame.display.flip()

    def draw_logo(self, x, y, size):
        if self.logo_src is None:
            pygame.draw.rect(self.screen, ACC, (x + size * 0.11, y, size * 0.78, size), border_radius=size // 6)
            return
        if size not in self.logo_cache:
            self.logo_cache[size] = pygame.transform.smoothscale(self.logo_src, (size, size))
        self.screen.blit(self.logo_cache[size], (x, y))

    def draw_wifi(self, cx, cy, color, scale=1.0, slash=False):
        for i, r in enumerate((4, 8, 12)):
            r = int(r * scale)
            rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
            pygame.draw.arc(self.screen, color, rect, 0.8, 2.35, max(2, int(2 * scale)))
        pygame.draw.circle(self.screen, color, (cx, cy), max(2, int(1.5 * scale)))
        if slash:
            d = int(13 * scale)
            pygame.draw.line(self.screen, color, (cx - d, cy - d - 2), (cx + d, cy + d // 2), max(2, int(2 * scale)))

    def draw_status(self, right_x, cy):
        s = self.screen
        clock = time.strftime("%H:%M")
        x = right_x - text(s, clock, (right_x, cy - 8), 12, SOFT, True, right=True) - 10
        lvl = services.battery_level()
        if lvl is not None:
            x -= 22
            pygame.draw.rect(s, SOFT, (x, cy - 6, 19, 11), 2, border_radius=3)
            pygame.draw.rect(s, SOFT, (x + 19, cy - 2, 2, 4))
            pygame.draw.rect(s, SOFT if lvl > 15 else ERR_RED, (x + 3, cy - 3, max(1, int(13 * lvl / 100)), 5))
            x -= 8
        self.draw_wifi(x - 8, cy + 5, SOFT, 0.8, slash=not services.is_online())

    def draw_header(self, active=None, title=None):
        s = self.screen
        pygame.draw.line(s, LINE, (0, 47), (W, 47))
        self.draw_logo(12, 9, 30)
        if title:
            w = text(s, "Pocket", (46, 14), 16, FG, True)
            text(s, "Tube", (46 + w, 14), 16, ACC, True)
            text(s, title, (W // 2, 14), 16, FG, True, center=True, max_w=300)
        else:
            f = font(12)
            labels = [T("tab_" + n) for n in TABS]
            widths = [f.size(label)[0] + 14 for label in labels]
            total = sum(widths) + 4 * (len(TABS) - 1) + 2 * (26 + 5)
            x = 54 + max(0, (468 - total) // 2)
            x += self.draw_key("L1", x, 14, small=True) + 5
            for name, label, w in zip(TABS, labels, widths):
                on = name == active
                pygame.draw.rect(s, FG if on else SURF, (x, 11, w, 26), border_radius=8)
                text(s, label, (x + w // 2, 16), 12, INK if on else FG, on, center=True)
                x += w + 4
            self.draw_key("R1", x, 14, small=True)
        self.draw_status(W - 16, 24)

    def draw_key(self, label, x, y, small=False, light=True):
        f = font(9 if small else 10, True)
        w = max(18, f.size(label)[0] + 8)
        color = FG if light and len(label) == 1 else DIM
        pygame.draw.rect(self.screen, color, (x, y, w, 18), border_radius=9 if len(label) == 1 else 5)
        img = f.render(label, True, INK)
        self.screen.blit(img, (x + (w - img.get_width()) // 2, y + (18 - img.get_height()) // 2))
        return w

    def draw_footer(self, hints):
        s = self.screen
        pygame.draw.rect(s, SURF_DARK, (0, H - 36, W, 36))
        pygame.draw.line(s, LINE, (0, H - 36), (W, H - 36))
        f = font(12)
        widths = [max(18, font(10, True).size(k)[0] + 8) + 6 + f.size(l)[0] for k, l in hints]
        x = (W - (sum(widths) + 16 * (len(hints) - 1))) // 2
        for (k, l), w in zip(hints, widths):
            kw = self.draw_key(k, x, H - 27)
            text(s, l, (x + kw + 6, H - 27), 12, DIM)
            x += w + 16

    def draw_thumb(self, vid, x, y, w, h, idx=0):
        img = self.thumbs.get(vid, w, h) if vid else None
        if img:
            self.screen.blit(img, (x, y))
        else:
            pygame.draw.rect(self.screen, TINTS[idx % len(TINTS)], (x, y, w, h), border_radius=8)

    def draw_badge(self, label, right, bottom, red=False):
        f = font(11, True)
        img = f.render(label, True, FG)
        r = pygame.Rect(right - img.get_width() - 8, bottom - 17, img.get_width() + 8, 16)
        pygame.draw.rect(self.screen, LIVE_RED if red else (0, 0, 0), r, border_radius=4)
        self.screen.blit(img, (r.x + 4, r.y + 1))

    def draw_video_row(self, y, v, idx, selected, status=None, progress=None):
        s = self.screen
        if selected:
            self.hl((10, y, W - 30, 82), 10, fill=SURF)
        self.draw_thumb(v["id"], 16, y + 5, 128, 72, idx)
        live = v.get("live")
        if v.get("kind") == "playlist":
            self.draw_badge(T("badge_playlist"), 140, y + 73)
        else:
            self.draw_badge("LIVE" if live else youtube.format_duration(v.get("duration")), 140, y + 73, red=live)
        lines = wrap(v.get("title", ""), font(14), W - 200, 2)
        for i, line in enumerate(lines):
            text(s, line, (156, y + 8 + i * 18), 14, FG)
        cy = y + 10 + len(lines) * 18
        text(s, v.get("channel", ""), (156, cy), 12, DIM, max_w=W - 200)
        if progress is not None:
            pygame.draw.rect(s, SURF_HI, (156, cy + 22, 160, 4), border_radius=2)
            pygame.draw.rect(s, ACC, (156, cy + 22, int(160 * progress), 4), border_radius=2)
            text(s, status, (324, cy + 16), 12, DIM)
        elif status:
            text(s, status, (156, cy + 17), 12, DIM)

    def draw_list(self, items, sel, top_y, row_fn, empty_text):
        s = self.screen
        if not items:
            text(s, empty_text, (W // 2, top_y + 120), 14, DIM, center=True)
            return
        per = max(1, (H - 36 - top_y) // 84)
        first = max(0, min(sel - 1, len(items) - per))
        off, rows = self.scroller(self.view, first, len(items), per, 84, top_y)
        for i in rows:
            row_fn(top_y + i * 84 - round(off), items[i], i, i == sel)
        self.end_list()

    def draw_skeleton(self, top_y):
        s = self.screen
        for i, (a, b) in enumerate([(88, 54), (76, 62), (92, 40), (70, 58)]):
            y = top_y + i * 84
            pygame.draw.rect(s, LINE, (16, y + 5, 128, 72), border_radius=8)
            pygame.draw.rect(s, SURF, (156, y + 10, int(4.4 * a), 14), border_radius=7)
            pygame.draw.rect(s, LINE, (156, y + 32, int(4.4 * b), 14), border_radius=7)
            pygame.draw.rect(s, SKEL, (156, y + 54, 130, 10), border_radius=5)

    def draw_button(self, label, key, x, y, w, focused, primary=None, focus_key=None):
        s = self.screen
        primary = focused if primary is None else primary
        r = pygame.Rect(x, y, w, 42)
        if focused:
            self.hl(r, 21, grow=10, key=focus_key)
        pygame.draw.rect(s, FG if primary else SURF, r, border_radius=21)
        kx = x + 14
        pygame.draw.circle(s, INK if primary else FG, (kx + 10, y + 21), 10)
        img = font(11, True).render(key, True, FG if primary else INK)
        s.blit(img, (kx + 10 - img.get_width() // 2, y + 21 - img.get_height() // 2))
        text(s, label, (kx + 30, y + 12), 15, INK if primary else FG, max_w=w - 60)

    def draw_toasts(self):
        now = time.time()
        self.toasts = [t for t in self.toasts if t[2] > now]
        y = H - 52
        for msg, kind, _ in reversed(self.toasts[-2:]):
            f = font(13)
            msg = ellipsize(msg, f, W - 80)
            w = f.size(msg)[0] + 32
            r = pygame.Rect((W - w) // 2, y - 40, w, 40)
            if kind == "error":
                pygame.draw.rect(self.screen, ERR_BG, r, border_radius=10)
                pygame.draw.rect(self.screen, ERR_RED, r, 1, border_radius=10)
                text(self.screen, msg, (r.x + 16, r.y + 11), 13, ERR_FG)
            else:
                pygame.draw.rect(self.screen, FG, r, border_radius=10)
                text(self.screen, msg, (r.x + 16, r.y + 11), 13, INK)
            y -= 48

    def notify(self, msg, kind="ok"):
        if kind == "error":
            self.sfx.play("error")
        self.toasts.append((msg, kind, time.time() + 3.5))

    def draw(self):
        self.anim_prev, self.anim_now, self.focus_ring, self.list_off = self.anim_now, set(), None, 0
        self.screen.fill(BG)
        getattr(self, "draw_" + self.view)()
        if self.focus_ring:
            r, radius, clip = self.focus_ring
            self.screen.set_clip(clip)
            pygame.draw.rect(self.screen, ACC, r, FOCUS_W, border_radius=radius)
            self.screen.set_clip(None)
        self.draw_toasts()
        pygame.display.flip()

    def draw_home(self):
        s = self.screen
        self.draw_header("home")
        text(s, T("continue_watching"), (16, 60), 15, FG, True)
        cards = self.home_cards()
        if not cards:
            text(s, T("home_empty"), (16, 92), 13, DIM)
        for i, v in enumerate(cards):
            x, y = 16 + i * 200, 88
            if self.home_row == 0 and self.home_col == i:
                self.hl((x, y, 188, 106), 8, grow=10)
            self.draw_thumb(v["id"], x, y, 188, 106, i)
            dur = v.get("duration") or 0
            pygame.draw.rect(s, TRACK, (x, y + 103, 188, 3))
            if dur:
                pygame.draw.rect(s, ACC, (x, y + 103, int(188 * min(1, (v.get("pos") or 0) / dur)), 3))
            live = v.get("live")
            self.draw_badge("LIVE" if live else youtube.format_duration(dur), x + 183, y + 98, red=live)
            for j, line in enumerate(wrap(v["title"], font(12), 188, 2)):
                text(s, line, (x, y + 112 + j * 15), 12, FG)
            text(s, v.get("channel", ""), (x, y + 144), 11, DIM, max_w=188)
        text(s, T("recent_searches"), (16, 262), 15, FG, True)
        if not self.store.queries:
            text(s, T("searches_empty"), (16, 292), 13, DIM)
        x, y = 16, 290
        for i, q in enumerate(self.store.queries[:6]):
            w = font(13).size(clean(q))[0] + 46
            if x + w > W - 16:
                x, y = 16, y + 42
            on = self.home_row == 1 and self.home_col == i
            if on:
                self.hl((x, y, w, 32), 16, grow=8)
            pygame.draw.rect(s, FG if on else SURF, (x, y, w, 32), border_radius=16)
            pygame.draw.circle(s, INK if on else DIM, (x + 19, y + 16), 6, 2)
            pygame.draw.line(s, INK if on else DIM, (x + 19, y + 16), (x + 19, y + 12), 2)
            text(s, q, (x + 32, y + 8), 13, INK if on else FG)
            x += w + 8
        self.draw_footer([("A", T("hint_open")), ("Y", T("hint_search")), ("L1 R1", T("hint_sections")), ("SELECT", T("settings")), ("B", T("hint_exit"))])

    def home_cards(self):
        hist = self.store.history
        unfinished = [h for h in hist if not h.get("live") and (h.get("pos") or 0) > 30
                      and (h.get("duration") or 0) - (h.get("pos") or 0) > 30]
        return (unfinished or hist)[:3]

    def draw_search(self):
        s = self.screen
        naming = self.kb_target == "name"
        if naming:
            self.draw_header(title=T("new_playlist"))
        else:
            self.draw_header("search")
        field = pygame.Rect(16, 58, W - 80, 36)
        pygame.draw.rect(s, FIELD, field, border_radius=18)
        pygame.draw.rect(s, SURF_HI, field, 1, border_radius=18)
        pygame.draw.circle(s, DIM, (field.x + 20, field.y + 16), 6, 2)
        pygame.draw.line(s, DIM, (field.x + 24, field.y + 20), (field.x + 29, field.y + 25), 2)
        w = text(s, self.query or "", (field.x + 38, field.y + 8), 15, FG, max_w=field.w - 60)
        if not self.query:
            text(s, T("playlist_name_placeholder") if naming else T("search_placeholder"), (field.x + 38, field.y + 8), 15, MUTED)
            w = 0
        pygame.draw.rect(s, ACC, (field.x + 40 + w, field.y + 9, 2, 18))
        pygame.draw.rect(s, FG, (W - 56, 63, 40, 26), border_radius=6)
        text(s, self.lang.upper(), (W - 36, 67), 12, INK, True, center=True)
        for i, sg in enumerate(self.sugg):
            y = 102 + i * 26
            on = self.ky == -1 and self.sugg_i == i
            if on:
                self.hl((12, y - 2, W - 24, 24), 6, fill=SURF)
            pygame.draw.circle(s, DIM, (26, y + 10), 5, 2)
            text(s, sg, (40, y + 2), 13, FG if on else SOFT, max_w=W - 60)
        rows = KB[self.lang]
        top, kh, gap = 210, 40, 6
        cols = max(len(r) for r in rows)
        kw = (W - 32 - (cols - 1) * gap) // cols
        for y, row in enumerate(rows):
            x0 = (W - (len(row) * kw + (len(row) - 1) * gap)) // 2
            for x, ch in enumerate(row):
                r = pygame.Rect(x0 + x * (kw + gap), top + y * (kh + gap), kw, kh)
                on = (x, y) == (self.kx, self.ky)
                if on:
                    self.hl(r, 8, grow=6)
                pygame.draw.rect(s, FG if on else SURF, r, border_radius=8)
                text(s, ch, r.center[:1] + (r.y + 10,), 16, INK if on else FG, center=True)
        y = len(rows)
        sw = (W - 32 - 3 * gap) // 4
        for x, kid in enumerate(SPECIAL):
            label = T("key_save") if kid == "find" and naming else T("key_" + kid)
            r = pygame.Rect(16 + x * (sw + gap), top + y * (kh + gap), sw, kh)
            on = (x, y) == (self.kx, self.ky)
            find = kid == "find"
            if on:
                self.hl(r, 8, grow=6)
            pygame.draw.rect(s, FG if on else (ACC if find else SURF), r, border_radius=8)
            text(s, label, (r.centerx, r.y + 12), 13, INK if on else FG, find, center=True)
        self.draw_footer([("A", T("hint_enter")), ("X", T("hint_erase")), ("Y", T("hint_space")),
                          ("START", T("key_save") if naming else T("hint_find")), ("B", T("hint_back"))])

    def draw_results(self):
        s = self.screen
        self.draw_header("search")
        pygame.draw.rect(s, SURF, (16, 56, W - 110, 34), border_radius=17)
        text(s, self.searched, (40, 63), 15, FG, max_w=W - 260)
        n = sum(1 for k in FILTER_KEYS if self.filters.get(k, "any" if k != "sort" else "relevance") not in ("any", "relevance"))
        label = T("filters_n", n=n) if n else T("filters")
        fw = font(12).size(label)[0] + 46
        fx = W - 110 - fw
        pygame.draw.rect(s, ACC if n else SURF_HI, (fx, 61, fw, 24), border_radius=12)
        kw = self.draw_key("X", fx + 4, 64)
        text(s, label, (fx + kw + 10, 66), 12, FG)
        loading = self.search_task and not self.search_task.done
        text(s, T("searching") if loading else (f"{self.sel + 1} / {len(self.results)}" if self.results else ""),
             (W - 18, 64), 12, DIM, right=True)
        if loading:
            self.draw_skeleton(100)
        else:
            self.draw_list(self.results, self.sel, 100,
                           lambda y, v, i, on: self.draw_video_row(y, v, i, on), T("nothing_found"))
        self.draw_footer([("A", T("hint_open")), ("X", T("filters")), ("Y", T("hint_new_search")), ("L1 R1", T("hint_sections")), ("B", T("hint_back"))])
        if self.filter_open:
            self.draw_filters()

    def draw_filters(self):
        s = self.screen
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill(VEIL)
        s.blit(veil, (0, 0))
        pw, ph = 460, 290
        px, py = (W - pw) // 2, 70
        pygame.draw.rect(s, SURF_DARK, (px, py, pw, ph), border_radius=14)
        text(s, T("filters"), (px + 20, py + 16), 17, FG, True)
        for i, k in enumerate(FILTER_KEYS):
            y = py + 54 + i * 46
            on = i == self.fsel
            if on:
                self.hl((px + 10, y, pw - 20, 40), 8, fill=SURF, key="filters")
            text(s, T("f_" + k), (px + 24, y + 11), 14, FG)
            val = self.filters.get(k, youtube.FILTERS[k][0][0])
            shown = f"◀  {T('fv_' + k + '_' + val)}  ▶"
            text(s, shown, (px + pw - 24, y + 11), 14, FG if on else DIM, right=True)
        text(s, T("filters_hint"), (W // 2, py + ph - 34), 12, DIM, center=True)

    def draw_history(self):
        self.draw_header("history")
        items = self.store.history
        self.draw_list(items, self.hsel, 58, self.history_row, T("history_empty"))
        self.draw_footer([("A", T("hint_open")), ("X", T("hint_remove")), ("L1 R1", T("hint_sections")), ("B", T("hint_back"))])

    def history_row(self, y, v, i, on):
        dur, pos = v.get("duration") or 0, v.get("pos") or 0
        status = T("stopped_at", time=youtube.format_duration(pos)) if pos > 30 and dur - pos > 30 else T("watched")
        self.draw_video_row(y, v, i, on, status)

    def draw_downloads(self):
        s = self.screen
        self.draw_header("downloads")
        top = 56
        free = services.free_space(self.store.settings["dl_dir"])
        text(s, T("downloads_summary", count=len(self.store.downloads), free=youtube.format_size(free)), (16, top + 2), 12, DIM)
        top += 24
        if not services.is_online():
            pygame.draw.rect(s, SURF_LOW, (0, top, W, 28))
            self.draw_wifi(W // 2 - 150, top + 19, SOFT, 0.6, slash=True)
            text(s, T("offline_banner"), (W // 2 - 132, top + 6), 12, SOFT)
            top += 34
        self.draw_list(self.store.downloads, self.dsel, top, self.download_row,
                       T("downloads_empty"))
        self.draw_footer([("A", T("hint_watch")), ("X", T("hint_delete_cancel")), ("L1 R1", T("hint_sections")), ("B", T("hint_back"))])

    def download_row(self, y, d, i, on):
        st = d["status"]
        if st == "done":
            q = T("q_audio") if d.get("audio") else d.get('quality', '')
            self.draw_video_row(y, d, i, on, f"{q} · {youtube.format_size(d.get('size'))}")
        elif st == "loading":
            self.draw_video_row(y, d, i, on, T("dl_progress", pct=int(d.get('progress', 0) * 100)), d.get("progress", 0))
        elif st == "queued":
            self.draw_video_row(y, d, i, on, T("dl_queued") if services.is_online() else T("dl_waiting_net"))
        else:
            self.draw_video_row(y, d, i, on, d.get("error") or T("dl_error"))

    def draw_video(self):
        s, v = self.screen, self.video
        det = self.details
        self.draw_thumb(v["id"], 20, 20, 320, 180, 2)
        if v.get("live") or (det and det.get("live")):
            self.draw_badge("LIVE", 334, 194, red=True)
        else:
            self.draw_badge(youtube.format_duration(v.get("duration")), 334, 194)
        live = v.get("live") or (det and det.get("live"))
        chips = [T("live")] if live else []
        chips.append(self.store.settings["quality"])
        dl = self.store.find_download(v["id"])
        if live:
            pass
        elif dl and dl["status"] == "done":
            chips.append(T("downloaded_size", size=youtube.format_size(dl.get("size"))))
        elif det and det.get("size"):
            chips.append(T("approx_size", size=youtube.format_size(det["size"])))
        x = 20
        for c in chips:
            w = font(12).size(c)[0] + 16
            pygame.draw.rect(s, LIVE_RED if c == T("live") else SURF, (x, 212, w, 24), border_radius=6)
            text(s, c, (x + 8, 216), 12, FG)
            x += w + 8
        y = 20
        for line in wrap(v.get("title", ""), font(18), 260, 3):
            text(s, line, (360, y), 18, FG)
            y += 24
        y += 6
        pygame.draw.circle(s, TINTS[5], (374, y + 14), 14)
        text(s, v.get("channel", ""), (396, y + 5), 14, FG, max_w=224)
        y += 38
        if self.details_task and not self.details_task.done:
            for i in range(3):
                pygame.draw.rect(s, SURF, (360, y + i * 18, 240 - i * 50, 10), border_radius=5)
        elif det:
            for line in wrap(det.get("description") or T("no_description"), font(12), 260, 3):
                text(s, line, (360, y), 12, DIM)
                y += 17
        dl_label = T("btn_download")
        if live:
            dl_label = T("btn_live_no_download")
        elif dl:
            dl_label = {"done": T("btn_downloaded"), "queued": T("btn_unqueue"), "error": T("btn_retry_download"),
                        "loading": T("btn_cancel_pct", pct=int(dl.get('progress', 0) * 100))}[dl["status"]]
        pos = self.store.history_pos(v["id"])
        if live:
            watch = T("btn_watch_live")
        else:
            watch = T("btn_resume", time=youtube.format_duration(pos)) if pos > 30 else T("btn_watch")
        saved = any(self.store.in_playlist(p["id"], v["id"]) for p in self.store.playlists)
        labels = [(watch, "A"), (dl_label, "X"), (T("btn_saved") if saved else T("btn_save"), "Y")]
        bfocus = self.vfocus == "buttons"
        for i, (label, key) in enumerate(labels):
            by = 278 + i * 52
            self.draw_button(label, key, 360, by, 260, bfocus and self.vbtn == i, primary=(i == 0), focus_key="video")
        self.draw_related()
        hints = [("A", T("hint_select"))]
        if not live:
            hints.append(("X", T("hint_download")))
        hints += [("Y", T("btn_save")), ("START", T("hint_listen")), ("B", T("hint_back"))]
        self.draw_footer(hints)

    def draw_related(self):
        s = self.screen
        text(s, T("related"), (20, 246), 13, FG, True)
        if self.related_task and not self.related_task.done:
            for i in range(3):
                pygame.draw.rect(s, LINE, (20, 268 + i * 58, 92, 52), border_radius=6)
                pygame.draw.rect(s, SURF, (120, 274 + i * 58, 180 - i * 30, 10), border_radius=5)
            return
        if not self.related:
            text(s, T("related_none"), (20, 272), 12, DIM)
            return
        first = max(0, min(self.rsel - 1, len(self.related) - 3))
        off, rows = self.scroller("related", first, len(self.related), 3, 58, 266, bar=False)
        for idx in rows:
            r = self.related[idx]
            y = 266 + idx * 58 - round(off)
            on = self.vfocus == "related" and idx == self.rsel
            if on:
                self.hl((14, y - 3, 330, 58), 8, fill=SURF, key="video")
            self.draw_thumb(r["id"], 20, y, 92, 52, idx)
            self.draw_badge(youtube.format_duration(r.get("duration")) if r.get("duration") else "LIVE", 110, y + 50, red=not r.get("duration"))
            for j, line in enumerate(wrap(r.get("title", ""), font(12), 216, 2)):
                text(s, line, (120, y + 2 + j * 15), 12, FG)
            text(s, r.get("channel", ""), (120, y + 34), 11, DIM, max_w=216)
        self.end_list()

    def draw_offline(self):
        s = self.screen
        self.draw_header(title=" ")
        pygame.draw.circle(s, SURF_LOW, (W // 2, 150), 56)
        self.draw_wifi(W // 2, 172, DIM, 2.4, slash=True)
        text(s, T("offline_title"), (W // 2, 222), 20, FG, center=True)
        for i, line in enumerate([T("offline_line1"),
                                  T("offline_line2")]):
            text(s, line, (W // 2, 258 + i * 20), 13, DIM, center=True)
        busy = self.retry_task and not self.retry_task.done
        self.draw_button(T("checking") if busy else T("retry"), "A", 110, 320, 200, self.obtn == 0, primary=True)
        self.draw_button(T("tab_downloads"), "Y", 330, 320, 200, self.obtn == 1, primary=False)
        self.draw_footer([("A", T("hint_select")), ("Y", T("tab_downloads")), ("B", T("hint_exit"))])

    def settings_rows(self):
        st = self.store.settings
        return [
            (T("set_quality"), T("set_quality_hint"), st["quality"]),
            (T("set_dl_quality"), T("set_dl_quality_hint"), T("q_audio") if st["dl_quality"] == "audio" else st["dl_quality"]),
            (T("set_dl_dir"), st["dl_dir"], T("set_change")),
            (T("set_clear"), T("set_clear_hint"), T("set_clear_btn")),
            ("yt-dlp " + youtube.VERSION, T("set_ytdlp_hint"), self.yt_value()),
            (T("set_sounds"), T("set_sounds_hint"), T("on") if st.get("sounds", True) else T("off")),
            (T("set_language"), T("set_language_hint"), i18n.LANG_NAMES[i18n.LANG]),
            (T("set_kb"), T("set_kb_hint"), T("kb_" + st.get("kb_layout", "en"))),
            (T("set_about"), f"{APP_NAME} {APP_VERSION}", ""),
        ]

    def yt_actions(self):
        return ["update", "rollback"] if youtube.has_rollback() else ["update"]

    def yt_value(self):
        if self.restart_at:
            return T("restarting")
        if self.yt_task and not self.yt_task.done:
            return T("yt_updating", pct=int(self.yt_progress * 100))
        acts = self.yt_actions()
        return T("yt_" + acts[self.yt_action % len(acts)])

    def draw_settings(self):
        s = self.screen
        self.draw_header(title=T("settings"))
        rows = self.settings_rows()
        vis = 8
        first = max(0, min(self.ssel - vis + 2, len(rows) - vis))
        off, visible = self.scroller("settings", first, len(rows), vis, 48, 55)
        for i in visible:
            label, hint, value = rows[i]
            y = 55 + i * 48 - round(off)
            if i == self.ssel:
                self.hl((20, y, W - 40, 44), 10, fill=SURF)
            text(s, label, (34, y + 4), 15, FG)
            text(s, hint, (34, y + 24), 12, DIM, max_w=360)
            if value:
                arrows = i < 2 or i in (5, 6, 7) or (i == 4 and len(self.yt_actions()) > 1 and not self.yt_task)
                shown = f"◀  {value}  ▶" if arrows else value
                f = font(13)
                w = f.size(shown)[0] + 20
                pygame.draw.rect(s, SURF_HI if i == self.ssel else SURF, (W - 34 - w, y + 8, w, 28), border_radius=8)
                text(s, shown, (W - 24 - w, y + 13), 13, ERR_SOFT if i == 3 else FG)
        self.end_list()
        self.draw_footer([("◀▶", T("hint_change")), ("A", T("hint_select")), ("B", T("hint_back"))])

    def switch_tab(self, step):
        names = list(TABS)
        cur = "search" if self.view == "results" else self.view
        i = names.index(cur) if cur in names else 0
        nxt = names[(i + step) % len(names)]
        if nxt == "search" and self.results:
            nxt = "results"
        self.view = nxt

    def do_search(self, q):
        q = q.strip()
        if not q:
            return
        self.store.add_query(q)
        self.query, self.searched = q, q
        self.results, self.sel = [], 0
        self.search_task = Task(youtube.search, q, 20, dict(self.filters))
        self.view = "results"

    def details_for(self, v):
        return Task(youtube.get_details, v["id"], self.store.settings["quality"], bool(v.get("live")))

    def open_video(self, v):
        if self.view != "video":
            self.back_view = self.view
        self.video, self.details, self.vbtn = dict(v), None, 0
        self.related, self.rsel, self.vfocus = [], 0, "buttons"
        self.related_task = Task(youtube.related, v["id"]) if services.is_online() else None
        dl = self.store.find_download(v["id"])
        if dl and dl["status"] == "done" and not services.is_online():
            self.details_task = None
        else:
            self.details_task = self.details_for(v)
        self.view = "video"

    def wait_details(self, message):
        while not self.details_task.done:
            pygame.event.pump()
            self.toasts = [t for t in self.toasts if t[1] != "wait"]
            self.toasts.append((message, "wait", time.time() + 1))
            self.draw()
            pygame.time.wait(50)
        self.toasts = [t for t in self.toasts if t[1] != "wait"]
        if self.details_task.error:
            if not services.check_online():
                self.view = "offline"
            else:
                self.notify(T("unavailable", err=str(self.details_task.error)[:50]), "error")
                self.details_task = self.details_for(self.video)
            return False
        self.details = self.details_task.result
        return True

    def play_current(self, audio_only=False):
        v = self.video
        dl = self.store.find_download(v["id"])
        if dl and dl["status"] == "done":
            if os.path.exists(dl.get("file", "")):
                self.play_download(dl, audio_only)
                return
            self.mark_missing(dl)
        if not self.details_task:
            self.notify(T("offline_not_downloaded"), "error")
            return
        res = self.details_task.result if self.details_task.done else None
        if res and time.time() - res.get("fetched", 0) > 3 * 3600:
            self.details_task = self.details_for(v)
        if not self.wait_details(T("getting_link")):
            return
        for attempt in range(2):
            d = self.details
            if audio_only and d.get("audio_url") and not d.get("live"):
                failed = self.run_player(v, d["audio_url"], None, False, chapters=d.get("chapters"),
                                         audio_only=True, can_video=False)
            else:
                failed = self.run_player(v, d["video_url"], d["audio_url"], d.get("live"),
                                         chapters=d.get("chapters"), subs=d.get("subs"), audio_only=audio_only)
            if not failed:
                return
            if attempt == 0:
                self.details_task = self.details_for(v)
                if not self.wait_details(T("link_expired")):
                    return
        self.notify(T("play_failed"), "error")

    def play_download(self, d, audio_only=False):
        self.video = dict(d)
        audio_file = bool(d.get("audio"))
        return self.run_player(d, d["file"], None, chapters=d.get("chapters"), subs=self.local_subs(d),
                               audio_only=audio_only or audio_file, can_video=not audio_file)

    def local_subs(self, dl):
        return [t for t in dl.get("subs") or [] if t.get("path") and os.path.exists(t["path"])]

    def run_player(self, v, video_url, audio_url, live=False, chapters=None, subs=None, audio_only=False, can_video=True):
        pos = self.store.history_pos(v["id"])
        dur = v.get("duration") or 0
        start = 0 if live else (pos if 30 < pos and (not dur or dur - pos > 30) else 0)
        self.sfx.stop()
        pygame.display.quit()
        try:
            p = player.Player(video_url, audio_url, start, v.get("title", ""), live,
                              v.get("duration") or 0, chapters, subs,
                              self.store.settings, self.store.save, audio_only, can_video)
            pos, failed = p.play()
            self.last_end = p.end_reason
        finally:
            pygame.display.init()
            pygame.mouse.set_visible(False)
            self.screen = pygame.display.set_mode((W, H))
            pygame.event.clear()
            self.sfx.start()
        if failed:
            return True
        entry = dict(v, live=bool(live))
        self.store.add_history(entry, 0 if live else pos)
        return False

    def mark_missing(self, dl):
        dl["status"], dl["progress"], dl["file"] = "error", 0, ""
        dl["error"] = T("dl_missing")
        self.store.save()
        self.notify(T("file_missing"), "error")

    def request_download(self, v):
        if v.get("live") or (self.details and self.details.get("id") == v["id"] and self.details.get("live")):
            self.notify(T("live_no_download"), "error")
            return
        dl = self.store.find_download(v["id"])
        if dl and dl["status"] in ("loading", "queued"):
            self.downloader.cancel(v["id"])
            self.notify(T("cancelling") if dl["status"] == "loading" else T("unqueued"))
            return
        if dl and dl["status"] == "error":
            dl["status"], dl["progress"] = "queued", 0
            dl.pop("error", None)
            self.store.save()
        elif dl:
            self.notify(T("already_downloaded"))
            return
        else:
            self.store.add_download(v)
        self.downloader.kick()
        self.notify(T("added_download"))

    def start_yt_action(self):
        acts = self.yt_actions()
        act = acts[self.yt_action % len(acts)]
        if act == "rollback":
            self.yt_task = Task(self.rollback_ytdlp)
            return
        if not services.is_online():
            self.notify(T("no_network"), "error")
            return
        self.yt_progress = 0.0
        self.yt_task = Task(youtube.update_ytdlp, lambda p: setattr(self, "yt_progress", p))

    @staticmethod
    def rollback_ytdlp():
        if not youtube.rollback_ytdlp():
            raise RuntimeError(T("no_previous"))
        return "rollback", True

    def restart(self):
        self.sfx.stop()
        pygame.quit()
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)])

    def press_key(self):
        rows = KB[self.lang]
        if self.ky < len(rows):
            self.query += rows[self.ky][self.kx]
            return
        label = SPECIAL[self.kx]
        if label == "lang":
            self.lang = "ru" if self.lang == "en" else "en"
        elif label == "space":
            self.query += " "
        elif label == "erase":
            self.query = self.query[:-1]
        else:
            self.submit_keyboard()

    def submit_keyboard(self):
        if self.kb_target != "name":
            self.do_search(self.query)
            return
        name = self.query.strip()
        if not name:
            return
        pid = self.store.playlist_create(name)
        if self.name_back == "pick" and self.video:
            self.store.playlist_toggle(pid, self.video)
            self.notify(T("added_to", name=name))
        else:
            self.notify(T("playlist_created", name=name))
        self.close_keyboard()

    def close_keyboard(self):
        back = self.name_back
        self.kb_target, self.query = "search", self.saved_query
        self.view = "video" if back == "pick" else back

    def on_key(self, key):
        if key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, K_L1, K_R1, K_X, K_Y):
            self.sfx.play("move")
        elif key in (K_A, K_START, K_SELECT):
            self.sfx.play("confirm")
        elif key == K_B:
            self.sfx.play("back")
        if key == K_SELECT and self.view != "settings":
            self.back_view, self.view, self.ssel = self.view, "settings", 0
            return True
        if key in (K_L1, K_R1) and self.view in ("home", "search", "results", "history", "downloads", "playlists") and self.kb_target == "search":
            self.switch_tab(-1 if key == K_L1 else 1)
            return True
        return getattr(self, "key_" + self.view)(key)

    def key_home(self, key):
        cards, chips = self.home_cards(), self.store.queries[:6]
        if key in (pygame.K_UP, pygame.K_DOWN):
            self.home_row = 0 if key == pygame.K_UP else 1
            self.home_col = 0
        elif key == pygame.K_LEFT:
            self.home_col = max(0, self.home_col - 1)
        elif key == pygame.K_RIGHT:
            limit = len(cards) if self.home_row == 0 else len(chips)
            self.home_col = min(max(0, limit - 1), self.home_col + 1)
        elif key == K_A:
            if self.home_row == 0 and self.home_col < len(cards):
                self.open_video(cards[self.home_col])
            elif self.home_row == 1 and self.home_col < len(chips):
                self.do_search(chips[self.home_col])
        elif key == K_Y:
            self.view = "search"
        elif key == K_B:
            return False
        return True

    def row_len(self, ky):
        rows = KB[self.lang]
        if ky < 0:
            return 1
        return len(SPECIAL) if ky >= len(rows) else len(rows[ky])

    def key_search(self, key):
        rows = len(KB[self.lang])
        width = self.row_len(self.ky)
        before = self.query
        old_ky, old_width = self.ky, width
        if self.ky == -1:
            if key == pygame.K_UP:
                self.sugg_i = max(0, self.sugg_i - 1)
            elif key == pygame.K_DOWN:
                if self.sugg_i + 1 < len(self.sugg):
                    self.sugg_i += 1
                else:
                    self.ky = 0
            elif key == K_A and self.sugg:
                self.do_search(self.sugg[self.sugg_i])
                return True
        elif key == pygame.K_LEFT:
            self.kx = (self.kx - 1) % width
        elif key == pygame.K_RIGHT:
            self.kx = (self.kx + 1) % width
        elif key == pygame.K_UP:
            if self.ky == 0 and self.sugg:
                self.ky, self.sugg_i = -1, len(self.sugg) - 1
            else:
                self.ky = (self.ky - 1) % (rows + 1)
        elif key == pygame.K_DOWN:
            self.ky = (self.ky + 1) % (rows + 1)
        elif key == K_A:
            self.press_key()
        if self.ky >= 0 and old_ky >= 0 and key in (pygame.K_UP, pygame.K_DOWN):
            new_width = self.row_len(self.ky)
            if new_width != old_width:
                self.kx = round((self.kx + 0.5) * new_width / old_width - 0.5)
            self.kx = max(0, min(self.kx, new_width - 1))
        if key == K_X:
            self.query = self.query[:-1]
        elif key == K_Y:
            self.query += " "
        elif key == K_START:
            self.submit_keyboard()
        elif key == K_B:
            if self.kb_target == "name":
                self.close_keyboard()
            else:
                self.view = "results" if self.results else "home"
        if self.query != before and self.kb_target == "search":
            self.sugg_due = time.time() + 0.6
        return True

    def key_results(self, key):
        if self.filter_open:
            return self.key_filters(key)
        if key == K_X:
            self.filter_open, self.fsel, self.filters_backup = True, 0, dict(self.filters)
            return True
        if key == K_A and self.results and self.results[self.sel].get("kind") == "playlist":
            self.open_remote_playlist(self.results[self.sel])
            return True
        if key == pygame.K_UP:
            self.sel = max(0, self.sel - 1)
        elif key == pygame.K_DOWN:
            self.sel = min(len(self.results) - 1, self.sel + 1)
        elif key == K_A and self.results:
            self.open_video(self.results[self.sel])
        elif key in (K_Y, K_B):
            self.view = "search"
        return True

    def key_filters(self, key):
        if key == pygame.K_UP:
            self.fsel = (self.fsel - 1) % len(FILTER_KEYS)
        elif key == pygame.K_DOWN:
            self.fsel = (self.fsel + 1) % len(FILTER_KEYS)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            k = FILTER_KEYS[self.fsel]
            opts = [o for o, _ in youtube.FILTERS[k]]
            cur = self.filters.get(k, opts[0])
            self.filters[k] = opts[(opts.index(cur) + (1 if key == pygame.K_RIGHT else -1)) % len(opts)]
        elif key == K_Y:
            self.filters = {}
        elif key in (K_A, K_START, K_X):
            self.filter_open = False
            self.store.settings["filters"] = dict(self.filters)
            self.store.save()
            if self.filters != self.filters_backup and self.searched:
                self.do_search(self.searched)
        elif key == K_B:
            self.filter_open, self.filters = False, self.filters_backup
        return True

    def open_remote_playlist(self, item):
        self.plist = {"pid": None, "remote": item["id"], "title": item.get("title", ""), "items": []}
        self.pisel, self.plist_back = 0, self.view
        self.plist_task = Task(youtube.playlist_items, item["id"])
        self.view = "playlist"

    def key_history(self, key):
        items = self.store.history
        if key == pygame.K_UP:
            self.hsel = max(0, self.hsel - 1)
        elif key == pygame.K_DOWN:
            self.hsel = min(len(items) - 1, self.hsel + 1)
        elif key == K_A and items:
            self.open_video(items[self.hsel])
        elif key == K_X and items:
            del items[self.hsel]
            self.store.save()
            self.hsel = max(0, min(self.hsel, len(items) - 1))
        elif key == K_B:
            self.view = "home"
        return True

    def key_downloads(self, key):
        items = self.store.downloads
        if key == pygame.K_UP:
            self.dsel = max(0, self.dsel - 1)
        elif key == pygame.K_DOWN:
            self.dsel = min(len(items) - 1, self.dsel + 1)
        elif key == K_A and items:
            d = items[self.dsel]
            if d["status"] == "done" and not os.path.exists(d.get("file", "")):
                self.mark_missing(d)
            elif d["status"] == "done":
                self.play_download(d)
            elif d["status"] == "error":
                self.request_download(d)
            else:
                self.open_video(d)
        elif key == K_X and items:
            d = items[self.dsel]
            if d["status"] in ("loading", "queued"):
                self.downloader.cancel(d["id"])
                self.notify(T("cancelling") if d["status"] == "loading" else T("unqueued"))
                self.dsel = max(0, min(self.dsel, len(self.store.downloads) - 1))
            else:
                self.store.remove_download(d["id"])
                self.dsel = max(0, min(self.dsel, len(self.store.downloads) - 1))
                self.notify(T("video_deleted"))
        elif key == K_B:
            self.view = "home" if services.is_online() else "offline"
        return True

    def key_video(self, key):
        if key == pygame.K_LEFT and self.related:
            self.vfocus = "related"
        elif key == pygame.K_RIGHT:
            self.vfocus = "buttons"
        elif key in (pygame.K_UP, pygame.K_DOWN):
            step = -1 if key == pygame.K_UP else 1
            if self.vfocus == "related":
                self.rsel = max(0, min(len(self.related) - 1, self.rsel + step))
            else:
                self.vbtn = max(0, min(2, self.vbtn + step))
        elif key == K_A and self.vfocus == "related" and self.related:
            self.open_video(self.related[self.rsel])
        elif key == K_A:
            if self.vbtn == 0:
                self.play_current()
            elif self.vbtn == 1:
                self.request_download(self.video)
            else:
                self.open_picker()
        elif key == K_Y:
            self.open_picker()
        elif key == K_START:
            self.play_current(audio_only=True)
        elif key == K_X:
            self.request_download(self.video)
        elif key == K_B:
            self.view = self.back_view
        return True

    def n_videos(self, n):
        return T("n_videos_1") if n == 1 else T("n_videos", n=n)

    def playlist_name(self, p):
        return T("watch_later") if p["id"] == store_mod.WATCH_LATER else p["name"]

    def draw_playlists(self):
        s = self.screen
        self.draw_header("playlists")
        rows = self.store.playlists + [None]
        self.lsel = max(0, min(self.lsel, len(rows) - 1))
        per = (H - 36 - 58) // 64
        first = max(0, min(self.lsel - per + 2, len(rows) - per))
        off, visible = self.scroller("playlists", first, len(rows), per, 64, 58)
        for idx in visible:
            p = rows[idx]
            y = 58 + idx * 64 - round(off)
            if idx == self.lsel:
                self.hl((10, y, W - 30, 58), 10, fill=SURF)
            if p is None:
                pygame.draw.rect(s, SURF_HI, (18, y + 7, 78, 44), border_radius=8)
                text(s, "+", (57, y + 13), 22, FG, True, center=True)
                text(s, T("new_playlist"), (110, y + 19), 15, FG)
                continue
            items = p["items"]
            if items:
                self.draw_thumb(items[0]["id"], 18, y + 7, 78, 44, idx)
            else:
                pygame.draw.rect(s, TINTS[idx % len(TINTS)], (18, y + 7, 78, 44), border_radius=8)
            self.draw_badge(str(len(items)), 92, y + 47)
            text(s, self.playlist_name(p), (110, y + 10), 15, FG, max_w=W - 150)
            text(s, self.n_videos(len(items)), (110, y + 32), 12, DIM)
        self.end_list()
        self.draw_footer([("A", T("hint_open")), ("X", T("hint_delete")), ("L1 R1", T("hint_sections")), ("B", T("hint_back"))])

    def key_playlists(self, key):
        rows = self.store.playlists + [None]
        if key == pygame.K_UP:
            self.lsel = max(0, self.lsel - 1)
        elif key == pygame.K_DOWN:
            self.lsel = min(len(rows) - 1, self.lsel + 1)
        elif key == K_A:
            p = rows[self.lsel]
            if p is None:
                self.open_keyboard_for_name("playlists")
            else:
                self.plist = {"pid": p["id"], "remote": None, "title": self.playlist_name(p), "items": p["items"]}
                self.pisel, self.plist_back = 0, "playlists"
                self.view = "playlist"
        elif key == K_X:
            p = rows[self.lsel]
            if p is None or p["id"] == store_mod.WATCH_LATER:
                return True
            if self.confirm_delete(p["id"]):
                self.store.playlist_delete(p["id"])
                self.notify(T("playlist_deleted"))
                self.lsel = max(0, self.lsel - 1)
        elif key == K_B:
            self.view = "home"
        return True

    def confirm_delete(self, key):
        last, when = self.del_confirm
        if last == key and time.time() - when < 3:
            self.del_confirm = (None, 0)
            return True
        self.del_confirm = (key, time.time())
        self.notify(T("press_again_delete"))
        return False

    def draw_playlist(self):
        s = self.screen
        pl = self.plist
        self.draw_header(title=pl["title"] or T("tab_playlists"))
        loading = self.plist_task is not None
        text(s, T("searching") if loading else self.n_videos(len(pl["items"])), (16, 58), 12, DIM)
        if loading:
            self.draw_skeleton(80)
        else:
            self.draw_list(pl["items"], self.pisel, 80, lambda y, v, i, on: self.draw_video_row(y, v, i, on), T("playlist_empty"))
        hints = [("A", T("hint_open")), ("START", T("hint_play_all"))]
        hints.append(("Y", T("hint_save_playlist")) if pl["remote"] else ("X", T("hint_remove")))
        hints.append(("B", T("hint_back")))
        self.draw_footer(hints)

    def key_playlist(self, key):
        pl = self.plist
        items = pl["items"]
        if key == pygame.K_UP:
            self.pisel = max(0, self.pisel - 1)
        elif key == pygame.K_DOWN:
            self.pisel = min(max(0, len(items) - 1), self.pisel + 1)
        elif key == K_A and items:
            self.open_video(items[self.pisel])
        elif key == K_START and items:
            self.play_queue(items[self.pisel:])
        elif key == K_X and items and pl["pid"]:
            self.store.playlist_remove(pl["pid"], items[self.pisel]["id"])
            pl["items"] = self.store.playlist(pl["pid"])["items"]
            self.pisel = max(0, min(self.pisel, len(pl["items"]) - 1))
            self.notify(T("removed_from_playlist"))
        elif key == K_Y and items and pl["remote"]:
            self.store.playlist_create(pl["title"] or T("tab_playlists"), [
                {k: v.get(k) for k in ("id", "title", "channel", "duration", "live")} for v in items])
            self.notify(T("playlist_created", name=pl["title"]))
        elif key == K_B:
            self.view = getattr(self, "plist_back", "playlists")
        return True

    def play_queue(self, items):
        for i, v in enumerate(items):
            self.video = dict(v)
            dl = self.store.find_download(v["id"])
            if dl and dl["status"] == "done" and os.path.exists(dl.get("file", "")):
                self.play_download(dl)
            else:
                self.details_task = self.details_for(v)
                if not self.wait_details(T("queue_next", n=i + 1, total=len(items))):
                    break
                d = self.details
                if self.run_player(v, d["video_url"], d["audio_url"], d.get("live"),
                                   chapters=d.get("chapters"), subs=d.get("subs")):
                    self.notify(T("play_failed"), "error")
                    break
            if getattr(self, "last_end", "") != "eof":
                break

    def open_picker(self):
        self.pick_sel = 0
        self.view = "pick"

    def draw_pick(self):
        self.draw_video()
        s = self.screen
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill(VEIL)
        s.blit(veil, (0, 0))
        rows = self.store.playlists + [None]
        vis = min(len(rows), 6)
        first = max(0, min(self.pick_sel - vis + 2, len(rows) - vis))
        pw, ph = 420, 70 + vis * 46
        px, py = (W - pw) // 2, max(30, (H - 36 - ph) // 2)
        pygame.draw.rect(s, SURF_DARK, (px, py, pw, ph), border_radius=14)
        text(s, T("save_to"), (px + 20, py + 16), 17, FG, True)
        off, visible = self.scroller("pick", first, len(rows), vis, 46, py + 54, bar=False)
        for idx in visible:
            p = rows[idx]
            y = py + 54 + idx * 46 - round(off)
            on = idx == self.pick_sel
            if on:
                self.hl((px + 10, y, pw - 20, 40), 8, fill=SURF, key="pick")
            col = FG
            if p is None:
                text(s, "+  " + T("new_playlist"), (px + 24, y + 11), 14, col)
                continue
            box = pygame.Rect(px + 24, y + 11, 18, 18)
            pygame.draw.rect(s, col, box, 2, border_radius=4)
            if self.store.in_playlist(p["id"], self.video["id"]):
                pygame.draw.rect(s, ACC, box.inflate(-6, -6), border_radius=2)
            text(s, self.playlist_name(p), (px + 54, y + 11), 14, col, max_w=pw - 120)
            text(s, str(len(p["items"])), (px + pw - 24, y + 11), 13, FG if on else DIM, right=True)
        self.end_list()
        self.draw_footer([("A", T("hint_toggle")), ("B", T("hint_done"))])

    def key_pick(self, key):
        rows = self.store.playlists + [None]
        if key == pygame.K_UP:
            self.pick_sel = max(0, self.pick_sel - 1)
        elif key == pygame.K_DOWN:
            self.pick_sel = min(len(rows) - 1, self.pick_sel + 1)
        elif key == K_A:
            p = rows[self.pick_sel]
            if p is None:
                self.open_keyboard_for_name("pick")
            else:
                added = self.store.playlist_toggle(p["id"], self.video)
                self.notify(T("added_to", name=self.playlist_name(p)) if added else T("removed_from", name=self.playlist_name(p)))
        elif key in (K_B, K_Y):
            self.view = "video"
        return True

    def open_keyboard_for_name(self, back):
        self.saved_query, self.query = self.query, ""
        self.kb_target, self.name_back = "name", back
        self.kx, self.ky, self.sugg = 0, 1, []
        self.view = "search"

    def key_offline(self, key):
        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.obtn = 0 if key == pygame.K_LEFT else 1
        elif key == K_Y or (key == K_A and self.obtn == 1):
            self.view = "downloads"
        elif key == K_A and (self.retry_task is None or self.retry_task.done):
            self.retry_task = Task(services.check_online)
        elif key == K_B:
            return False
        return True

    def key_settings(self, key):
        st = self.store.settings
        if key == pygame.K_UP:
            self.ssel = max(0, self.ssel - 1)
        elif key == pygame.K_DOWN:
            self.ssel = min(len(self.settings_rows()) - 1, self.ssel + 1)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT, K_A):
            step = -1 if key == pygame.K_LEFT else 1
            if self.ssel in (0, 1):
                name = "quality" if self.ssel == 0 else "dl_quality"
                qs = store_mod.QUALITIES if self.ssel == 0 else store_mod.DL_QUALITIES
                st[name] = qs[(qs.index(st[name]) + step) % len(qs)]
                self.store.save()
            elif self.ssel == 2:
                dirs = store_mod.DOWNLOAD_DIRS
                i = dirs.index(st["dl_dir"]) if st["dl_dir"] in dirs else 0
                st["dl_dir"] = dirs[(i + step) % len(dirs)]
                self.store.save()
            elif self.ssel == 3 and key == K_A:
                self.store.clear_history()
                self.home_row = self.home_col = self.hsel = 0
                self.notify(T("history_cleared"))
            elif self.ssel == 6:
                langs = i18n.LANGS
                st["lang"] = langs[(langs.index(i18n.LANG) + step) % len(langs)]
                i18n.set_lang(st["lang"])
                self.store.save()
            elif self.ssel == 7:
                st["kb_layout"] = "ru" if st.get("kb_layout", "en") == "en" else "en"
                self.lang = st["kb_layout"]
                self.store.save()
            elif self.ssel == 5:
                st["sounds"] = not st.get("sounds", True)
                self.sfx.enabled = st["sounds"]
                self.store.save()
                self.sfx.play("confirm")
            elif self.ssel == 4 and not (self.yt_task or self.restart_at):
                if key == K_A:
                    self.start_yt_action()
                else:
                    self.yt_action += step
        elif key == K_B:
            self.view = self.back_view
        return True

    def update(self):
        if self.related_task and self.related_task.done:
            task, self.related_task = self.related_task, None
            self.related = task.result or []
        if self.plist_task and self.plist_task.done:
            task, self.plist_task = self.plist_task, None
            if task.error:
                self.notify(T("unavailable", err=str(task.error)[:50]), "error")
                self.view = "results"
            elif self.plist is not None:
                self.plist["items"] = task.result["items"]
                self.plist["title"] = self.plist["title"] or task.result["title"]
        if self.view == "search" and self.kb_target == "search":
            if self.sugg_due and time.time() > self.sugg_due:
                self.sugg_due = 0
                if self.query.strip() and services.is_online():
                    self.sugg_for = self.query
                    self.sugg_task = Task(youtube.suggestions, self.query)
                else:
                    self.sugg = []
            if self.sugg_task and self.sugg_task.done:
                if self.sugg_for == self.query:
                    self.sugg = self.sugg_task.result or []
                    if self.ky == -1 and not self.sugg:
                        self.ky = 0
                self.sugg_task = None
        if self.search_task and self.search_task.done:
            task, self.search_task = self.search_task, None
            if task.error:
                if not services.check_online():
                    self.view = "offline"
                else:
                    self.notify(T("search_error", err=str(task.error)[:60]), "error")
            else:
                self.results = task.result or []
        if self.details_task and self.details_task.done and not self.details_task.error:
            self.details = self.details_task.result
        if self.yt_task and self.yt_task.done:
            task, self.yt_task = self.yt_task, None
            if task.error:
                self.notify(T("failed", err=str(task.error)[:60]), "error")
            else:
                ver, changed = task.result
                if not changed:
                    self.notify(T("yt_latest", ver=ver))
                else:
                    self.notify(T("yt_rolled_back") if ver == "rollback" else T("yt_updated", ver=ver))
                    self.restart_at = time.time() + 2
        if self.restart_at and time.time() > self.restart_at:
            self.restart()
        if self.retry_task and self.retry_task.done:
            ok, self.retry_task = self.retry_task.result, None
            if ok:
                self.view = "home"
                self.downloader.kick()
            else:
                self.notify(T("still_offline"), "error")

    def run(self):
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.on_key(event.key) is not False
                    if not running:
                        break
            self.update()
            self.draw()
            clock.tick(30)
        pygame.quit()


if __name__ == "__main__":
    App().run()
