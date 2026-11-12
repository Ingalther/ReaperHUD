"""Drawing kit for the Reaper HUD style previews: 2x supersampled Pillow canvas, palette, fonts, primitives."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts')
K = 2  # supersampling

INK = (7, 7, 9)
PANEL = (9, 9, 11)
RED = (224, 26, 46)
HOT = (255, 52, 76)
PINK = (255, 200, 206)
RED_DIM = (122, 16, 30)
RED_DEEP = (52, 6, 14)
WHITE = (236, 232, 232)
GREY = (138, 132, 138)
GREY_D = (66, 64, 70)
TEAM_RED = (255, 120, 104)
TEAM_BLU = (112, 164, 232)

_cache = {}


def F(name, px):
    key = (name, px)
    if key not in _cache:
        files = {'mich': 'Michroma-Regular.ttf', 'raj7': 'Rajdhani-Bold.ttf', 'raj6': 'Rajdhani-SemiBold.ttf',
                 'raj5': 'Rajdhani-Medium.ttf', 'bar4': 'BarlowSemiCondensed-Regular.ttf',
                 'bar5': 'BarlowSemiCondensed-Medium.ttf', 'bar6': 'BarlowSemiCondensed-SemiBold.ttf',
                 'mono': 'ShareTechMono-Regular.ttf', 'jp5': 'ReaperJPSubset-Medium.ttf',
                 'jp7': 'ReaperJPSubset-Bold.ttf', 'jp9': 'ReaperJPSubset-Black.ttf'}
        _cache[key] = ImageFont.truetype(os.path.join(FONTS, files[name]), int(round(px * K)))
    return _cache[key]


def rgba(col, a=255):
    return tuple(col[:3]) + (int(a),)


class Canvas:
    def __init__(self, base):
        """base: PIL RGB image at 1x (1920x1080)."""
        self.w, self.h = base.size
        self.im = base.resize((self.w * K, self.h * K), Image.LANCZOS).convert('RGB')
        self.d = ImageDraw.Draw(self.im, 'RGBA')

    # ---------------------------------------------------------------- geometry
    @staticmethod
    def _p(pts):
        return [(x * K, y * K) for x, y in pts]

    @staticmethod
    def chamfer_pts(x0, y0, x1, y1, tl=0, tr=0, br=0, bl=0):
        return [(x0 + tl, y0), (x1 - tr, y0), (x1, y0 + tr), (x1, y1 - br), (x1 - br, y1), (x0 + bl, y1),
                (x0, y1 - bl), (x0, y0 + tl)]

    def poly(self, pts, fill=None, outline=None, width=1):
        if fill:
            self.d.polygon(self._p(pts), fill=fill)
        if outline:
            p = self._p(pts)
            self.d.line(p + [p[0]], fill=outline, width=max(1, int(width * K)))

    def rect(self, x0, y0, x1, y1, fill):
        self.d.rectangle([x0 * K, y0 * K, x1 * K - 1, y1 * K - 1], fill=fill)

    def line(self, pts, fill, width=1):
        self.d.line(self._p(pts), fill=fill, width=max(1, int(round(width * K))))

    def chamfer(self, x0, y0, x1, y1, fill=None, outline=None, width=1, **cuts):
        self.poly(self.chamfer_pts(x0, y0, x1, y1, **cuts), fill, outline, width)

    def brackets(self, x0, y0, x1, y1, arm, fill, width=1):
        for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
            self.line([(x + dx * arm, y), (x, y), (x, y + dy * arm)], fill, width)

    def _layer(self):
        return Image.new('L', self.im.size, 0)

    def masked(self, mask_img, color, alpha=255):
        """Fill colour through an 'L' mask at canvas resolution."""
        solid = Image.new('RGB', self.im.size, color[:3])
        m = mask_img.point(lambda v: v * alpha // 255)
        self.im.paste(solid, (0, 0), m)

    def hatch(self, x0, y0, x1, y1, color, alpha=255, step=6, width=2):
        m = self._layer()
        d = ImageDraw.Draw(m)
        hgt = y1 - y0
        x = x0 - hgt
        while x < x1:
            d.line([((x) * K, y1 * K), ((x + hgt) * K, y0 * K)], fill=255, width=int(width * K))
            x += step
        clip = self._layer()
        ImageDraw.Draw(clip).rectangle([x0 * K, y0 * K, x1 * K - 1, y1 * K - 1], fill=255)
        m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(clip)))
        self.masked(m, color, alpha)

    def dots(self, x0, y0, x1, y1, color, alpha=255, step=4):
        for y in range(int(y0) + 2, int(y1) - 1, step):
            for x in range(int(x0) + 2, int(x1) - 1, step):
                self.d.rectangle([x * K, y * K, x * K + K - 1, y * K + K - 1], fill=rgba(color, alpha))

    def scan(self, x0, y0, x1, y1, color, alpha=255, step=3):
        for y in range(int(y0), int(y1), step):
            self.d.rectangle([x0 * K, y * K, x1 * K - 1, y * K + K - 1], fill=rgba(color, alpha))

    # ---------------------------------------------------------------- text
    def text(self, x, y, s, font, fill, anchor='la', spacing=0):
        if not spacing:
            self.d.text((x * K, y * K), s, font=font, fill=fill, anchor=anchor)
            return font.getlength(s) / K
        total = sum(font.getlength(ch) / K for ch in s) + spacing * (len(s) - 1)
        if anchor[0] == 'r':
            x -= total
        elif anchor[0] == 'm':
            x -= total / 2
        a = 'l' + anchor[1]
        for ch in s:
            self.d.text((x * K, y * K), ch, font=font, fill=fill, anchor=a)
            x += font.getlength(ch) / K + spacing
        return total

    def width(self, s, font, spacing=0):
        return sum(font.getlength(ch) / K for ch in s) + spacing * (len(s) - 1) if spacing else font.getlength(s) / K

    def mixed(self, x, y, parts, anchor='lm'):
        """Runs of (text, font, fill) side by side."""
        tot = sum(f.getlength(t) / K for t, f, _ in parts)
        if anchor[0] == 'r':
            x -= tot
        for t, f, col in parts:
            self.d.text((x * K, y * K), t, font=f, fill=col, anchor='l' + anchor[1])
            x += f.getlength(t) / K
        return tot

    def vtext(self, x, y, s, font, fill, step):
        for ch in s:
            self.d.text((x * K, y * K), ch, font=font, fill=fill, anchor='mt')
            y += step

    def glow_text(self, x, y, s, font, color, radius=6, strength=1.0, anchor='la', spacing=0):
        """Additive bloom behind text (what a blurred font copy does in game)."""
        m = self._layer()
        d = ImageDraw.Draw(m)
        if spacing:
            tmp = Canvas.__new__(Canvas)
            tmp.d = d
            Canvas.text(tmp, x, y, s, font, 255, anchor, spacing)
        else:
            d.text((x * K, y * K), s, font=font, fill=255, anchor=anchor)
        self.glow_mask(m, color, radius, strength)

    def glow_mask(self, m, color, radius, strength):
        g = np.asarray(m.filter(ImageFilter.GaussianBlur(radius * K)), np.float32) / 255 * strength
        a = np.asarray(self.im, np.float32)
        a += g[..., None] * np.array(color, np.float32)
        self.im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')
        self.d = ImageDraw.Draw(self.im, 'RGBA')

    def glow_poly(self, pts, color, radius, strength):
        m = self._layer()
        ImageDraw.Draw(m).polygon(self._p(pts), fill=255)
        self.glow_mask(m, color, radius, strength)

    def result(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


# -------------------------------------------------------------------- reusable pieces
# Beyond the Wall: the crimson torn by the wall's light, a red copy to the left and a cyan one to the right
SPLIT_R = (255, 20, 60)
SPLIT_C = (0, 214, 255)


def scan_in(cv, pts, color, alpha, step=3):
    """Scan lines across a convex shape, each clipped to it."""
    ys = [y for _, y in pts]
    for y in np.arange(min(ys) + 1, max(ys) - 1, step):
        xs = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            if (ay - y) * (by - y) <= 0 and ay != by:
                xs.append(ax + (bx - ax) * (y - ay) / (by - ay))
        if len(xs) >= 2:
            cv.rect(min(xs) + 1, y, max(xs) - 1, y + 1, rgba(color, alpha))


def torn(cv, pts, seed=1, col=RED, a=150, split=True, gaps=0.22, seg=46, node=2.0):
    """The HUD's hairline round a shape, bitten in places, a faint red copy left of it and a cyan one right of it,
    a node on every corner."""
    r = np.random.default_rng(seed)
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        n = max(2, int(math.hypot(bx - ax, by - ay) / seg))
        for i in range(n):
            if r.random() < gaps:
                continue
            t0, t1 = i / n, (i + r.uniform(0.6, 1.0)) / n
            p0 = (ax + (bx - ax) * t0, ay + (by - ay) * t0)
            p1 = (ax + (bx - ax) * t1, ay + (by - ay) * t1)
            if split:
                cv.line([(p0[0] - 1.5, p0[1]), (p1[0] - 1.5, p1[1])], rgba(SPLIT_R, 70), 1)
                cv.line([(p0[0] + 1.5, p0[1]), (p1[0] + 1.5, p1[1])], rgba(SPLIT_C, 45), 1)
            cv.line([p0, p1], rgba(col, a), 1)
    for (x, y) in pts:
        cv.rect(x - node, y - node, x + node, y + node, rgba(col))


def tears(cv, x0, y0, x1, y1, n=4, seed=1, col=HOT, alpha=170):
    """Glitch tears: thin bars of crimson and white, a cyan sliver under some."""
    r = np.random.default_rng(seed)
    for _ in range(n):
        y = r.uniform(y0, y1)
        h = r.choice([1, 1.5, 2, 2, 3])
        lo = min(24, (x1 - x0) * 0.3)
        xa = r.uniform(x0, x1 - lo)
        w = r.uniform(lo, max(lo + 1, (x1 - x0) * 0.5))
        cv.rect(xa, y, min(x1, xa + w), y + h, rgba(col if r.random() < 0.65 else WHITE, int(alpha * r.uniform(0.45, 1))))
        sx0, sx1 = xa + r.uniform(2, 10), min(x1, xa + w * r.uniform(0.2, 0.6))
        if r.random() < 0.6 and sx1 > sx0 + 1:
            cv.rect(sx0, y + h, sx1, y + h + 1, rgba(SPLIT_C, 110))


def panel(cv, x0, y0, x1, y1, tab=True, tab_h=None, alpha=214, cut='tr', cut_px=14, edge=150, texture=True, seed=None):
    """Black glass with faint scan lines, a cut corner, the torn hairline and a crimson tab."""
    cuts = {cut: cut_px} if cut else {}
    cv.chamfer(x0, y0, x1, y1, fill=rgba(PANEL, alpha), **cuts)
    shape = Canvas.chamfer_pts(x0, y0, x1, y1, **cuts)
    if texture:
        scan_in(cv, shape, WHITE, 12)
    torn(cv, shape, seed=int(x0 * 7 + y0 * 3) if seed is None else seed, a=edge)
    if tab:
        cv.rect(x0, y0, x0 + 3, y0 + (tab_h or (y1 - y0)), rgba(RED))


def seg_bar(cv, x0, y0, x1, y1, frac, n, on=RED, off_alpha=24, gap=2, hot_last=True):
    w = (x1 - x0 - gap * (n - 1)) / n
    k = int(round(frac * n))
    for i in range(n):
        xa = x0 + i * (w + gap)
        if i < k:
            col = HOT if (hot_last and i == k - 1) else on
            cv.rect(xa, y0, xa + w, y1, rgba(col))
        else:
            cv.rect(xa, y0, xa + w, y1, rgba(WHITE, off_alpha))


def vseg_bar(cv, x0, y0, x1, y1, frac, n, gap=2):
    """Vertical gauge filling bottom-up (what TF2's health image can do)."""
    h = (y1 - y0 - gap * (n - 1)) / n
    k = int(round(frac * n))
    for i in range(n):
        yb = y1 - i * (h + gap)
        if i < k:
            cv.rect(x0, yb - h, x1, yb, rgba(HOT if i == k - 1 else RED))
        else:
            cv.rect(x0, yb - h, x1, yb, rgba(WHITE, 22))


def label(cv, x, y, en, jp=None, color=RED, anchor='lm'):
    cv.rect(x, y - 3.5, x + 7, y + 3.5, rgba(color))
    x += 13
    parts = []
    if jp:
        parts += [(jp, F('jp5', 11), rgba(color)), ('  //  ', F('mono', 11), rgba(color, 150))]
    parts += [(en, F('mono', 12), rgba(color))]
    return cv.mixed(x, y, parts, anchor)
