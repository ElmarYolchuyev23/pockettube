import os, sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
ICON_OUT = [os.path.join(ROOT, "userdata/roms/ports/images/pockettube-icon.png"),
            os.path.join(ROOT, "userdata/system/pockettube/assets/logo.png")]
MARQUEE_OUT = os.path.join(ROOT, "userdata/roms/ports/images/pockettube-marquee.png")

BODY = (124, 92, 255)
SCREEN = (25, 20, 45)
PINK = (255, 120, 160)
WHITE = (255, 255, 255)
FG = (241, 241, 241)
S = 4
RATIO = 0.80


def play(surf, cx, cy, size):
    w = size * 0.9
    pygame.draw.polygon(surf, WHITE, [(cx - w * 0.38, cy - size / 2), (cx + w * 0.62, cy), (cx - w * 0.38, cy + size / 2)])


def handheld(surf, x, y, w, h):
    pygame.draw.rect(surf, BODY, (x, y, w, h), border_radius=int(w * 0.16))
    sx, sy, sw, sh = x + w * 0.12, y + h * 0.10, w * 0.76, h * 0.48
    pygame.draw.rect(surf, SCREEN, (sx, sy, sw, sh), border_radius=int(w * 0.06))
    play(surf, sx + sw / 2, sy + sh / 2, sh * 0.5)
    cy, d, cx = y + h * 0.78, w * 0.07, x + w * 0.28
    pygame.draw.rect(surf, WHITE, (cx - d * 1.5, cy - d / 2, d * 3, d), border_radius=int(d / 3))
    pygame.draw.rect(surf, WHITE, (cx - d / 2, cy - d * 1.5, d, d * 3), border_radius=int(d / 3))
    pygame.draw.circle(surf, PINK, (int(x + w * 0.70), int(cy + d * 0.6)), int(d * 0.75))
    pygame.draw.circle(surf, WHITE, (int(x + w * 0.80), int(cy - d * 0.6)), int(d * 0.75))


def wordmark(size):
    f = pygame.font.Font(FONT, size)
    a, b = f.render("Pocket", True, FG), f.render("Tube", True, BODY)
    surf = pygame.Surface((a.get_width() + b.get_width(), max(a.get_height(), b.get_height())), pygame.SRCALPHA)
    surf.blit(a, (0, 0))
    surf.blit(b, (a.get_width(), 0))
    return surf


def main():
    pygame.init()
    big = pygame.Surface((256 * S, 256 * S), pygame.SRCALPHA)
    h = 256 * S * 0.96
    w = h * RATIO
    handheld(big, (256 * S - w) / 2, (256 * S - h) / 2, w, h)
    icon = pygame.transform.smoothscale(big, (256, 256))
    for path in ICON_OUT:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pygame.image.save(icon, path)

    big = pygame.Surface((600 * S, 200 * S), pygame.SRCALPHA)
    lh = 130 * S
    lw = lh * RATIO
    wm = wordmark(62 * S)
    x0 = (600 * S - (lw + 26 * S + wm.get_width())) / 2
    handheld(big, x0, (200 * S - lh) / 2, lw, lh)
    big.blit(wm, (x0 + lw + 26 * S, (200 * S - wm.get_height()) / 2))
    pygame.image.save(pygame.transform.smoothscale(big, (600, 200)), MARQUEE_OUT)
    print("logo written")


if __name__ == "__main__":
    main()
