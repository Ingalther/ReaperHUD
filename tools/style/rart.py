"""Float-image helpers for the Reaper HUD artwork (numpy + Pillow only, no scipy)."""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts')

# ---------------------------------------------------------------- palette (0..1 floats)
def c(r, g, b):
    return np.array([r, g, b], np.float32) / 255


VOID = c(5, 5, 7)
INK = c(12, 11, 14)
BLOOD = c(120, 8, 22)
RED = c(228, 26, 46)
NEON = c(255, 46, 66)
HOT = c(255, 196, 200)
SOUL = c(255, 226, 230)
WHITE = c(238, 234, 234)
STEEL = c(128, 124, 130)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


# ---------------------------------------------------------------- blur without scipy
def _box(a, r, axis):
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    p = np.pad(a, pad, mode='edge')
    cs = np.cumsum(p, axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(cs, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(cs, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def blur(a, sigma, axes=(0, 1)):
    """Gaussian blur approximated by three box passes per axis."""
    if sigma <= 0.3:
        return a.astype(np.float32)
    r = max(1, int(round((math.sqrt(4 * sigma * sigma + 1) - 1) / 2)))
    out = a.astype(np.float32)
    for _ in range(3):
        for ax in axes:
            out = _box(out, r, ax)
    return out


def blur_dir(a, sigma, axis):
    return blur(a, sigma, axes=(axis,))


# ---------------------------------------------------------------- shapes
def catmull(points, closed=True, n=14):
    """Smooth curve through the points (centripetal-free uniform Catmull-Rom)."""
    pts = [np.array(p, np.float64) for p in points]
    if closed:
        ext = [pts[-1]] + pts + [pts[0], pts[1]]
    else:
        ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(pts[-1])
    return np.array(out)


class Mask:
    """Supersampled 'L' drawing surface that comes back as a float mask."""

    def __init__(self, w, h, ss=4):
        self.w, self.h, self.ss = w, h, ss
        self.im = Image.new('L', (w * ss, h * ss), 0)
        self.d = ImageDraw.Draw(self.im)

    def _p(self, pts):
        s = self.ss
        return [(float(x) * s, float(y) * s) for x, y in pts]

    def poly(self, pts, fill=255):
        self.d.polygon(self._p(pts), fill=fill)
        return self

    def line(self, pts, width, fill=255):
        self.d.line(self._p(pts), fill=fill, width=max(1, int(round(width * self.ss))), joint='curve')
        return self

    def ellipse(self, cx, cy, rx, ry, fill=255, width=0):
        s = self.ss
        box = [(cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s]
        if width:
            self.d.ellipse(box, outline=fill, width=max(1, int(round(width * s))))
        else:
            self.d.ellipse(box, fill=fill)
        return self

    def rect(self, x0, y0, x1, y1, fill=255):
        s = self.ss
        self.d.rectangle([x0 * s, y0 * s, x1 * s - 1, y1 * s - 1], fill=fill)
        return self

    def text(self, xy, txt, fnt, fill=255, anchor='la', spacing=0):
        s = self.ss
        if spacing:
            x, y = xy
            for ch in txt:
                self.d.text((x * s, y * s), ch, font=fnt, fill=fill, anchor=anchor)
                x += (fnt.getlength(ch) / s) + spacing
        else:
            self.d.text((xy[0] * s, xy[1] * s), txt, font=fnt, fill=fill, anchor=anchor)
        return self

    def get(self):
        im = self.im.resize((self.w, self.h), Image.BOX)
        return np.asarray(im, np.float32) / 255


# ---------------------------------------------------------------- compositing (float RGB 0..1)
def over(dst, color, alpha):
    a = np.clip(alpha, 0, 1)[..., None]
    col = color if np.ndim(color) == 1 else color
    dst *= (1 - a)
    dst += a * col
    return dst


def add(dst, color, amount):
    dst += np.clip(amount, 0, None)[..., None] * color
    return dst


def screen(dst, color, amount):
    a = np.clip(amount, 0, 1)[..., None] * color
    dst[:] = 1 - (1 - dst) * (1 - a)
    return dst


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def noise2d(w, h, seed, scale=64, octaves=4):
    r = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, s, tot = 1.0, scale, 0
    for _ in range(octaves):
        gw, gh = max(2, w // s + 2), max(2, h // s + 2)
        g = Image.fromarray(r.uniform(0, 255, (gh, gw)).astype(np.uint8))
        g = np.asarray(g.resize((w, h), Image.BICUBIC), np.float32) / 255 - 0.5
        out += amp * g
        tot += amp
        amp *= 0.5
        s = max(1, s // 2)
    return out / tot


def to_image(rgb):
    return Image.fromarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def to_rgba(rgb, alpha):
    a = (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)
    return Image.fromarray(np.dstack([(np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8), a]), 'RGBA')
