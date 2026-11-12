"""Generates every texture of the Reaper HUD into <out>/materials (numpy + Pillow only).

The look: black glass panels with a crimson hairline and cut corners, red seals with white kanji, labels that pair a
red square, a Japanese word and an English one in a terminal face, portraits and icons in a crimson-to-white hologram
duotone behind scan lines. Fonts come from tools/fonts and icons from tools/logos, so every machine draws the same.
"""
import glob
import os

import numpy as np
from PIL import ImageChops
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from vtf import write_vtf

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
ART = os.path.join(HERE, 'art')
LOGOS = os.path.join(HERE, 'logos')
THUMB = 'materials/vgui/replay/thumbnails/rk'

# ---------------------------------------------------------------- palette
INK = (7, 7, 9)
PANEL = (9, 9, 11)
RED = (224, 26, 46)
HOT = (255, 52, 76)
RED_DIM = (122, 16, 30)
RED_DEEP = (52, 6, 14)
WHITE = (236, 232, 232)
PINK = (255, 200, 206)
GREY = (138, 132, 138)
GREY_D = (66, 64, 70)
TEAM = {'red': (255, 120, 104), 'blue': (112, 164, 232), 'ink': (138, 132, 138)}
TEAM_DEEP = {'red': (60, 12, 14), 'blue': (12, 22, 40), 'ink': (22, 22, 24)}

CLASSES = [  # (button name, portrait name, sel name, number, label, katakana)
    ('scout', 'scout', 'scout', 1, 'SCOUT', 'スカウト'),
    ('soldier', 'soldier', 'soldier', 2, 'SOLDIER', 'ソルジャー'),
    ('pyro', 'pyro', 'pyro', 3, 'PYRO', 'パイロ'),
    ('demoman', 'demoman', 'demo', 4, 'DEMOMAN', 'デモマン'),
    ('heavyweapons', 'heavy', 'heavy', 5, 'HEAVY', 'ヘビー'),
    ('engineer', 'engineer', 'engineer', 6, 'ENGINEER', 'エンジニア'),
    ('medic', 'medic', 'medic', 7, 'MEDIC', 'メディック'),
    ('sniper', 'sniper', 'sniper', 8, 'SNIPER', 'スナイパー'),
    ('spy', 'spy', 'spy', 9, 'SPY', 'スパイ'),
]
BUILDING_KANJI = {'sentry': '砲', 'dispenser': '補', 'tele_entrance': '入', 'tele_exit': '出', 'sapper': '破'}

_fonts = {}


def font(name, px):
    files = {'mich': 'Michroma-Regular.ttf', 'raj7': 'Rajdhani-Bold.ttf', 'raj6': 'Rajdhani-SemiBold.ttf',
             'mono': 'ShareTechMono-Regular.ttf', 'jp5': 'ReaperJPSubset-Medium.ttf', 'jp7': 'ReaperJPSubset-Bold.ttf',
             'jp9': 'ReaperJPSubset-Black.ttf', 'bar6': 'BarlowSemiCondensed-SemiBold.ttf'}
    key = (name, int(px))
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONTS, files[name]), max(1, int(px)))
    return _fonts[key]


def c(col, a=255):
    return tuple(col[:3]) + (int(a),)


class Tex:
    """RGBA texture drawn at ss x its size; every primitive is composited (source-over) onto what is there."""

    def __init__(self, w, h, ss=2):
        self.w, self.h, self.ss = int(w), int(h), ss
        self.im = Image.new('RGBA', (self.w * ss, self.h * ss), (0, 0, 0, 0))

    def _p(self, pts):
        s = self.ss
        return [(x * s, y * s) for x, y in pts]

    def _layer(self):
        layer = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        return layer, ImageDraw.Draw(layer)

    def poly(self, pts, fill):
        layer, d = self._layer()
        d.polygon(self._p(pts), fill=fill)
        self.im.alpha_composite(layer)

    def outline(self, pts, fill, width=1.0):
        layer, d = self._layer()
        p = self._p(pts)
        d.line(p + [p[0]], fill=fill, width=max(1, round(width * self.ss)))
        self.im.alpha_composite(layer)

    def line(self, pts, fill, width=1.0):
        layer, d = self._layer()
        d.line(self._p(pts), fill=fill, width=max(1, round(width * self.ss)))
        self.im.alpha_composite(layer)

    def rect(self, x0, y0, x1, y1, fill):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill)

    def rects(self, boxes, fill):
        layer, d = self._layer()
        s = self.ss
        for x0, y0, x1, y1 in boxes:
            d.rectangle([x0 * s, y0 * s, max(x0 * s, x1 * s - 1), max(y0 * s, y1 * s - 1)], fill=fill)
        self.im.alpha_composite(layer)

    def ellipse(self, cx, cy, rx, ry, fill=None, outline=None, width=1.0):
        layer, d = self._layer()
        s = self.ss
        d.ellipse([(cx - rx) * s, (cy - ry) * s, (cx + rx) * s, (cy + ry) * s], fill=fill, outline=outline,
                  width=max(1, round(width * s)) if outline else 0)
        self.im.alpha_composite(layer)

    def text(self, x, y, s, fnt, fill, anchor='la', spacing=0.0):
        layer, d = self._layer()
        ss = self.ss
        f = font(fnt[0], fnt[1] * ss)
        if spacing:
            total = sum(f.getlength(ch) for ch in s) / ss + spacing * (len(s) - 1)
            if anchor[0] == 'r':
                x -= total
            elif anchor[0] == 'm':
                x -= total / 2
            for ch in s:
                d.text((x * ss, y * ss), ch, font=f, fill=fill, anchor='l' + anchor[1])
                x += f.getlength(ch) / ss + spacing
        else:
            d.text((x * ss, y * ss), s, font=f, fill=fill, anchor=anchor)
        self.im.alpha_composite(layer)
        return f.getlength(s) / ss

    def vtext(self, x, y, s, fnt, fill, step):
        for ch in s:
            self.text(x, y, ch, fnt, fill, 'mt')
            y += step

    def width(self, s, fnt):
        return font(fnt[0], fnt[1] * self.ss).getlength(s) / self.ss

    def mixed(self, x, y, runs, anchor='lm'):
        """Runs of (text, font, fill) side by side."""
        if anchor[0] == 'r':
            x -= sum(self.width(t, f) for t, f, _ in runs)
        for t, f, col in runs:
            x += self.text(x, y, t, f, col, 'l' + anchor[1])
        return x

    def paste(self, img, x, y, w=None, h=None):
        """Composite an RGBA image with its top-left at (x, y), scaled to w x h (texture units)."""
        s = self.ss
        w = w or img.width / s
        h = h or img.height / s
        self.im.alpha_composite(img.convert('RGBA').resize((max(1, round(w * s)), max(1, round(h * s))),
                                                          Image.LANCZOS), (round(x * s), round(y * s)))

    def dots(self, x0, y0, x1, y1, color, alpha, step=4):
        boxes = [(x, y, x + 1, y + 1) for y in range(int(y0) + 2, int(y1) - 1, step)
                 for x in range(int(x0) + 2, int(x1) - 1, step)]
        self.rects(boxes, c(color, alpha))

    def scan(self, x0, y0, x1, y1, color, alpha, step=3):
        self.rects([(x0, y, x1, y + 1) for y in range(int(y0), int(y1), step)], c(color, alpha))

    def hatch(self, x0, y0, x1, y1, color, alpha, step=6, width=2.0):
        layer, d = self._layer()
        s = self.ss
        hgt = y1 - y0
        x = x0 - hgt
        while x < x1:
            d.line([(x * s, y1 * s), ((x + hgt) * s, y0 * s)], fill=c(color, alpha), width=max(1, round(width * s)))
            x += step
        clip = Image.new('L', self.im.size, 0)
        ImageDraw.Draw(clip).rectangle([x0 * s, y0 * s, x1 * s - 1, y1 * s - 1], fill=255)
        layer.putalpha(Image.fromarray(np.minimum(np.asarray(layer.getchannel('A')), np.asarray(clip))))
        self.im.alpha_composite(layer)

    def brackets(self, x0, y0, x1, y1, arm, color, width=1.0):
        for (x, y, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x1, y1, -1, -1), (x0, y1, 1, -1)):
            self.line([(x + dx * arm, y), (x, y), (x, y + dy * arm)], color, width)

    def glow(self, radius, color, strength=1.0):
        """Soft halo of everything drawn so far, laid under it."""
        a = self.im.getchannel('A').filter(ImageFilter.GaussianBlur(radius * self.ss))
        g = Image.new('RGBA', self.im.size, c(color, 0))
        g.putalpha(a.point(lambda v: min(255, int(v * strength))))
        g.alpha_composite(self.im)
        self.im = g

    def result(self):
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def chamfer(x0, y0, x1, y1, tl=0, tr=0, br=0, bl=0):
    return [(x0 + tl, y0), (x1 - tr, y0), (x1, y0 + tr), (x1, y1 - br), (x1 - br, y1), (x0 + bl, y1), (x0, y1 - bl),
            (x0, y0 + tl)]


_WALL = []


def wall_texture():
    """The Blackwall's own pattern (Cyberpunk 2077's blackwall_atlas, tools/art/cp2077/blackwall_wall.png)."""
    if not _WALL:
        src = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art', 'cp2077',
                                      'blackwall_wall.png')).convert('RGBA')
        # in the HUD's one crimson (the game's runs from crimson to magenta, which the BLU twin would leave pink):
        # its brightness as the crimson's strength, its own alpha kept
        lum = np.asarray(src.convert('L'), np.float32) / 255.0
        out = np.zeros(lum.shape + (4,), np.uint8)
        for i, v in enumerate(HOT):
            out[..., i] = np.clip(lum * 1.25 * v, 0, 255)
        out[..., 3] = (np.asarray(src.split()[3], np.float32) * np.clip(lum * 1.6, 0, 1)).astype(np.uint8)
        _WALL.append(Image.fromarray(out, 'RGBA'))
    return _WALL[0]


def wall_over(img, side='right', strength=0.26):
    """The Wall's pattern over a finished picture, where the picture is solid (its own alpha), fading in from one
    side: for the cards that are not drawn with glass()."""
    img = img.convert('RGBA')
    w, h = img.size
    pat = wall_texture().resize((w, h), Image.BICUBIC)
    ramp = Image.new('L', (w, 1))
    px = ramp.load()
    for x in range(w):
        f = x / max(1, w - 1)
        px[x, 0] = int(255 * strength * (f if side == 'right' else 1 - f) ** 1.3)
    solid = img.split()[3].point(lambda v: 255 if v > 200 else 0)
    pat.putalpha(ImageChops.multiply(ImageChops.multiply(pat.split()[3], ramp.resize((w, h))), solid))
    out = img.copy()
    out.alpha_composite(pat)
    return out


def glass(w, h, cuts=None, tab=None, tab_w=0.0, fill=PANEL, fill_a=236, edge=RED, edge_a=100, dots=True, ss=2,
          line=1.2, wall='right', wall_a=0.34):
    """Black glass panel: cut corners (cuts: dict tl / tr / br / bl in px), a hairline, a team / accent tab on the
    left, a faint dot grid. Since 0.9 the Wall is in it: its pattern fading in from one side (wall: 'right',
    'left' or None; panels too small to carry it stay plain), the hairline brighter, the cut corners hot. Returns
    the Tex for more drawing."""
    t = Tex(w, h, ss)
    cuts = cuts or {}
    shape = chamfer(0, 0, w, h, **cuts)
    t.poly(shape, c(fill, fill_a))
    if dots:
        t.dots(3, 3, w - 3, h - 3, WHITE, 9, step=4)
    if wall and w >= 150 and h >= 40:
        W_, H_ = t.im.size
        pat = wall_texture().resize((W_, H_), Image.BICUBIC)
        ramp = Image.new('L', (W_, 1))
        px = ramp.load()
        for x in range(W_):
            f = x / max(1, W_ - 1)
            px[x, 0] = int(255 * wall_a * (f if wall == 'right' else 1 - f) ** 1.3)
        clip = Image.new('L', (W_, H_), 0)
        ImageDraw.Draw(clip).polygon(t._p(shape), fill=255)
        pat.putalpha(ImageChops.multiply(ImageChops.multiply(pat.split()[3], ramp.resize((W_, H_))), clip))
        t.im.alpha_composite(pat)
    if edge:
        inner = {k: max(0, v - 1) for k, v in cuts.items()}
        t.outline(chamfer(0.5, 0.5, w - 0.5, h - 0.5, **inner), c(edge, min(255, edge_a + 60)), line)
        arm = max(8, min(w, h) * 0.16)
        hot = c(HOT if edge == RED else edge, 255)
        for key, (cx, cy, dx, dy) in (('tl', (0, 0, 1, 1)), ('tr', (w, 0, -1, 1)), ('br', (w, h, -1, -1)),
                                      ('bl', (0, h, 1, -1))):
            k = cuts.get(key, 0)
            if k:   # the cut corner and a little of the edges either side of it, hot
                t.line([(cx + dx * (k + arm), cy + dy * 0.6), (cx + dx * k, cy + dy * 0.6), (cx + dx * 0.6, cy + dy * k),
                        (cx + dx * 0.6, cy + dy * (k + arm))], hot, line * 1.5)
    if tab:
        t.rect(0, cuts.get('tl', 0), tab_w, h - cuts.get('bl', 0), c(tab))
    return t


def label(t, x, y, en, jp=None, size=11.0, color=RED):
    """The HUD's label: red square, Japanese word, // , English word (terminal face)."""
    sq = size * 0.62
    t.rect(x, y - sq / 2, x + sq, y + sq / 2, c(color))
    runs = []
    if jp:
        runs += [(jp, ('jp5', size), c(color)), ('  //  ', ('mono', size), c(color, 150))]
    runs.append((en, ('mono', size * 1.08), c(color)))
    return t.mixed(x + sq + size * 0.55, y, runs)


def seal(chars, w, h, fill=RED, ink=WHITE):
    """Red seal with white kanji stacked down its middle."""
    t = Tex(w, h, 4)
    t.rect(0, 0, w, h, c(fill))
    t.outline([(w * 0.06, h * 0.06), (w * 0.94, h * 0.06), (w * 0.94, h * 0.94), (w * 0.06, h * 0.94)],
              c(INK, 110), max(1.0, w * 0.02))
    n = len(chars)
    size = min(w * 0.72, h * 0.84 / n)
    y = (h - size * n * 1.04) / 2
    for ch in chars:
        t.text(w / 2, y, ch, ('jp9', size), c(ink), 'mt')
        y += size * 1.04
    return t.result()


def duotone(img, dark=RED_DEEP, mid=RED, light=WHITE, gamma=0.9, keep_alpha=True):
    """Luminance -> crimson hologram: black to deep red to red to white."""
    im = img.convert('RGBA')
    a = np.asarray(im, np.float32) / 255
    lum = np.clip(a[..., :3] @ np.array([0.3, 0.55, 0.15], np.float32), 0, 1) ** gamma
    stops = np.array([0.0, 0.42, 0.78, 1.0], np.float32)
    cols = np.array([(4, 2, 3), dark, mid, light], np.float32) / 255
    out = np.stack([np.interp(lum, stops, cols[:, i]) for i in range(3)], -1)
    alpha = a[..., 3:4] if keep_alpha else np.ones_like(a[..., :1])
    return Image.fromarray((np.concatenate([out, alpha], -1) * 255).astype(np.uint8), 'RGBA')


def scanlines(img, step=3, depth=0.35):
    a = np.asarray(img.convert('RGBA'), np.float32)
    rows = (np.arange(a.shape[0]) % step) == 0
    a[rows, :, :3] *= 1 - depth
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def logo_icon(name, size=256, tint=None):
    """An item icon from tools/logos (the HUD's own drawings) in the hologram duotone; tint: a team colour for
    the brightest parts instead of white."""
    p = os.path.join(LOGOS, name + '.png')
    if not os.path.exists(p):
        return generic_icon(size)
    im = Image.open(p).convert('RGBA').resize((size, size), Image.LANCZOS)
    return duotone(im, light=tint or WHITE, gamma=0.8)


def generic_icon(size=256):
    """An item without a drawing of its own: a crimson diamond with a white core."""
    t = Tex(size, size, 2)
    m = size / 2
    t.poly([(m, size * 0.1), (size * 0.9, m), (m, size * 0.9), (size * 0.1, m)], c(RED))
    t.poly([(m, size * 0.3), (size * 0.7, m), (m, size * 0.7), (size * 0.3, m)], c(WHITE))
    return t.result()


def gradient(w, h, stops, axis='x', color=INK):
    """Alpha gradient along one axis; stops = [(pos 0..1, alpha 0..1), ...]."""
    n = w if axis == 'x' else h
    t = np.linspace(0, 1, n)
    a = np.interp(t, [p for p, _ in stops], [v for _, v in stops])
    arr = np.tile(a[None, :], (h, 1)) if axis == 'x' else np.tile(a[:, None], (1, w))
    img = np.dstack([np.full((h, w), color[0]), np.full((h, w), color[1]), np.full((h, w), color[2]),
                     arr * 255]).astype(np.uint8)
    return Image.fromarray(img, 'RGBA')


def soft_frame(w, h, color, inset=0.12):
    """A glow hugging the inside of a card, for the overheal / low-ammo pulses."""
    W, H = w * 4, h * 4
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)) / (min(W, H) * inset)
    a = np.clip(1 - d, 0, 1) ** 1.6
    img = np.dstack([np.full((H, W), color[0]), np.full((H, W), color[1]), np.full((H, W), color[2]),
                     a * 255]).astype(np.uint8)
    return Image.fromarray(img, 'RGBA')


def fill(color, a=255, size=32):
    return Image.new('RGBA', (size, size), c(color, a))


# ---------------------------------------------------------------- output
def vmt(path, basetexture):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('"UnlitGeneric"\n{\n'
                f'\t"$basetexture"\t"{basetexture}"\n'
                '\t"$translucent"\t"1"\n\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n'
                '\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n}\n')


BLU_HUE = 213.0   # the BLU accent: crimson's hue (354) turned to an electric azure, its depth and brightness kept


def to_blue(img):
    """The BLU twin of a texture drawn in the HUD's crimson: every pixel of the red family (hue within 35 degrees of
    red, not grey; amber stays) takes the BLU accent's hue with its own saturation, brightness and alpha, so crimson turns azure,
    deep red deep blue, pink pale blue; greys, white and ink stay as they are. The game shows the twin on BLU
    (CTFImagePanel teambg_3, Out.thumb team=True)."""
    a = np.asarray(img.convert('RGBA'), np.float32) / 255
    rgb = a[..., :3]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    safe = np.where(d > 1e-6, d, 1)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / safe) % 6, np.where(mx == g, (b - r) / safe + 2, (r - g) / safe + 4)) * 60
    hs = np.where(h > 180, h - 360, h)                         # signed: red at 0
    s = np.where(mx > 1e-6, d / np.where(mx > 1e-6, mx, 1), 0)
    w = np.clip((35 - np.abs(hs)) / 10, 0, 1) * np.clip((s - 0.06) / 0.08, 0, 1)
    nh = ((BLU_HUE + hs) % 360) / 60
    k = lambda n: (n + nh) % 6
    f = lambda n: mx - mx * s * np.clip(np.minimum(k(n), 4 - k(n)), 0, 1)
    blue = np.stack([f(5), f(3), f(1)], -1)
    a[..., :3] = blue * w[..., None] + rgb * (1 - w[..., None])
    return Image.fromarray((a * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA')


class Out:
    def __init__(self, root, preview=None):
        self.root = root
        self.preview = preview
        os.makedirs(os.path.join(root, THUMB), exist_ok=True)
        os.makedirs(os.path.join(root, 'materials/console'), exist_ok=True)

    def thumb(self, name, img, mips=True, team=False):
        """team: also its BLU twin (to_blue) as b/<name>, for a CTFImagePanel's teambg_3 (ingame.team)."""
        if team:
            self.thumb('b/' + name, to_blue(img), mips)
        p = os.path.join(self.root, THUMB, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if self.preview:
            img.save(os.path.join(self.preview, name.replace('/', '_') + '.png'))
        if not name.endswith(('_mul', '_add')):  # multiplied / added to what is under them: alpha plays no part
            img = linear_alpha(img)
        w, h = img.size
        pw, ph = 1 << (w - 1).bit_length(), 1 << (h - 1).bit_length()
        if (pw, ph) != (w, h):
            # textures must be power-of-two; the panel draws it at the art's own aspect, so a stretch round-trips
            img = img.resize((pw, ph), Image.LANCZOS)
        write_vtf(p + '.vtf', img, alpha=True, mips=mips)
        vmt(p + '.vmt', f'vgui/replay/thumbnails/rk/{name}')

    def anim(self, name, frames, fps):
        """A flipbook: the frames in one VTF, played on a loop by the material's AnimatedTexture proxy."""
        p = os.path.join(self.root, THUMB, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        write_vtf(p + '.vtf', [linear_alpha(f) for f in frames], alpha=True, mips=False)
        with open(p + '.vmt', 'w', encoding='utf-8') as f:
            f.write('"UnlitGeneric"\n{\n'
                    f'\t"$basetexture"\t"vgui/replay/thumbnails/rk/{name}"\n'
                    '\t"$translucent"\t"1"\n\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n'
                    '\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n'
                    '\t"Proxies"\n\t{\n\t\t"AnimatedTexture"\n\t\t{\n'
                    '\t\t\t"animatedtexturevar"\t"$basetexture"\n'
                    '\t\t\t"animatedtextureframenumvar"\t"$frame"\n'
                    f'\t\t\t"animatedtextureframerate"\t"{fps}"\n'
                    '\t\t}\n\t}\n}\n')
        if self.preview:
            frames[0].save(os.path.join(self.preview, name + '.png'))

    def console(self, name, img):
        p = os.path.join(self.root, 'materials/console', name)
        write_vtf(p + '.vtf', img.convert('RGBA'), alpha=False, mips=False)
        with open(p + '.vmt', 'w', encoding='utf-8') as f:
            f.write('"UnlitGeneric"\n{\n\t"$basetexture"\t"console/%s"\n\t"$vertexcolor"\t"1"\n'
                    '\t"$vertexalpha"\t"1"\n\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n}\n' % name)
        if self.preview:
            img.convert('RGB').save(os.path.join(self.preview, name + '.jpg'), quality=88)


def linear_alpha(img):
    """The game blends in linear light: black glass at alpha a keeps (1 - a) of the light under it, which on screen
    is (1 - a) ** (1 / 2.2) of the brightness, so a 60 % pane takes only a third of the scene away instead of the
    designed 60 %. Dark pixels get the alpha that darkens the scene as designed, 1 - (1 - a) ** 2.2; the brighter
    a pixel, the less of that it gets (white lettering and crimson keep theirs)."""
    a = np.asarray(img.convert('RGBA'), np.float32) / 255
    alpha = a[..., 3]
    dark = 1 - a[..., :3].max(axis=2)
    a[..., 3] = alpha + (1 - (1 - alpha) ** 2.2 - alpha) * dark
    return Image.fromarray((a * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- generic skin (9-slice borders, 8 px corners)
def slice_panel(fill_col, edge=None, edge_a=90, cut=True, fill_a=220, tab=None, size=64, border_px=1.0):
    """A 9-slice tile: the game keeps its 8 px corners and stretches the rest, so the cut corner and the hairline
    survive any panel size."""
    t = Tex(size, size, ss=4)
    t.poly(chamfer(0, 0, size, size, tr=6 if cut else 0), c(fill_col, fill_a))
    if edge:
        t.outline(chamfer(0.5, 0.5, size - 0.5, size - 0.5, tr=5.5 if cut else 0), c(edge, edge_a), border_px)
    if tab:
        t.rect(0, 0, 2, size, c(tab))
    return t.result()


def generic(out):
    out.thumb('blank', Image.new('RGBA', (16, 16), (0, 0, 0, 0)), mips=False)
    out.thumb('panel', slice_panel(PANEL, RED, fill_a=236), mips=False)
    out.thumb('panel_opaque', slice_panel(PANEL, RED, fill_a=255), mips=False)
    out.thumb('panel_thin', slice_panel(PANEL, GREY_D, edge_a=200, fill_a=170, cut=False), mips=False)
    out.thumb('panel_clear', slice_panel(INK, None, fill_a=140, cut=False), mips=False)
    out.thumb('panel_accent', slice_panel(PANEL, HOT, edge_a=255, tab=RED, fill_a=236), mips=False)
    out.thumb('panel_red', slice_panel((38, 8, 12), TEAM['red'], edge_a=120, fill_a=230), mips=False)
    out.thumb('panel_red_opaque', slice_panel((38, 8, 12), TEAM['red'], edge_a=120, fill_a=255), mips=False)
    out.thumb('panel_blue', slice_panel((10, 16, 30), TEAM['blue'], edge_a=120, fill_a=230), mips=False)
    out.thumb('panel_blue_opaque', slice_panel((10, 16, 30), TEAM['blue'], edge_a=120, fill_a=255), mips=False)
    out.thumb('btn', slice_panel((18, 18, 20), RED_DIM, edge_a=160, fill_a=236, cut=False, tab=RED_DIM), mips=False)
    out.thumb('btn_hover', slice_panel(RED, HOT, edge_a=255, fill_a=255, cut=False), mips=False)
    out.thumb('btn_down', slice_panel(HOT, WHITE, edge_a=160, fill_a=255, cut=False), mips=False)
    out.thumb('btn_off', slice_panel((22, 22, 24), GREY_D, edge_a=120, fill_a=160, cut=False), mips=False)
    out.thumb('item', slice_panel((16, 16, 18), (170, 170, 170), edge_a=255, fill_a=236, cut=False), mips=False)
    out.thumb('item_plain', slice_panel((12, 12, 14), GREY_D, edge_a=200, fill_a=230, cut=False), mips=False)
    out.thumb('item_hover', slice_panel((24, 16, 18), WHITE, edge_a=255, fill_a=240, cut=False, border_px=3),
              mips=False)
    out.thumb('item_sel', slice_panel((48, 8, 16), RED, edge_a=255, fill_a=240, cut=False, border_px=3), mips=False)
    # rows (crafting recipes): a hairline at rest, a crimson wash with a crimson edge on hover
    t = Tex(64, 32)
    t.line([(0, 31.5), (64, 31.5)], c(WHITE, 60), 1)
    out.thumb('nav', t.result(), mips=False)
    nav_h = gradient(64, 32, [(0, 0.6), (1, 0.0)], color=(120, 12, 26))
    bar = Tex(64, 32)
    bar.rect(0, 0, 3, 32, c(RED))
    nav_h.alpha_composite(bar.result())
    out.thumb('nav_hover', nav_h, mips=False)
    a = np.zeros((256, 256, 4), np.float32)
    a[..., :3] = PANEL
    yy = np.linspace(0, 1, 256)[:, None]
    a[..., 0] += 70 * np.exp(-((yy - 1.0) / 0.35) ** 2)
    a[..., 3] = 240
    out.thumb('inspect_bg', Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA'))
    out.thumb('shade_full', gradient(32, 32, [(0, 0.6), (1, 0.6)]), mips=False)
    out.thumb('header', gradient(32, 128, [(0, 0.96), (0.55, 0.8), (1, 0)], axis='y'))
    out.thumb('footer', gradient(32, 128, [(0, 0), (0.35, 0.8), (1, 0.96)], axis='y'))


# ---------------------------------------------------------------- in-game: the ID card, the ammo card, meters
U = 6  # texture pixels per HUD unit for the in-game cards (2.25 px per unit at 1080p, 4.5 at 4K)


def id_card(w, h, gauge):
    """Vitals card (w x h HUD units): cut top-right corner, the HEALTH label, the slot of the vertical gauge at its
    right end, a hairline over the killstreak row."""
    t = glass(w * U, h * U, cuts={'tr': 7 * U}, fill_a=240, edge_a=110)
    label(t, 5 * U, 6 * U, 'HEALTH', '体力', size=5.6 * U)
    gx, gy, gw, gh = gauge
    t.rect((gx - 1.2) * U, (gy - 1.2) * U, (gx + gw + 1.2) * U, (gy + gh + 1.2) * U, c(INK, 255))
    t.text((gx + gw / 2) * U, (gy + gh + 2.4) * U, 'HP', ('mono', 3.2 * U), c(GREY), 'mt')
    t.line([(5 * U, (h - 14.5) * U), ((gx - 4) * U, (h - 14.5) * U)], c(RED, 70), 1)
    return t.result()


def id_photo_bg(w, h):
    t = Tex(w * U, h * U)
    W, H = w * U, h * U
    t.poly(chamfer(0, 0, W, H, bl=5 * U), c(RED_DEEP, 235))
    t.dots(4, 4, W - 4, H - 4, RED, 24, step=6)
    yy = np.linspace(0, 1, t.im.height)[:, None]
    glow = np.clip(np.exp(-((yy - 0.8) / 0.35) ** 2) * 80, 0, 255) * np.ones((1, t.im.width))
    g = Image.new('RGBA', t.im.size, c(RED, 0))
    g.putalpha(Image.fromarray(glow.astype(np.uint8)))
    t.im.alpha_composite(g)
    return t.result()


def id_photo_fx(w, h):
    """Drawn over the 3D model: scan lines, a faint crimson wash, ID brackets and the badge number."""
    t = Tex(w * U, h * U)
    W, H = w * U, h * U
    t.rect(0, 0, W, H, c(RED, 20))
    t.scan(0, 0, W, H, INK, 70, step=3)
    t.brackets(2 * U, 2 * U, W - 2 * U, H - 2 * U, 6 * U, c(WHITE, 220), 0.5 * U)
    t.text(3.5 * U, H - 4.5 * U, 'ID-0451', ('mono', 3.6 * U), c(WHITE, 210), 'lm')
    t.outline(chamfer(1, 1, W - 1, H - 1, bl=5 * U - 1), c(RED, 150), 1.2)
    return t.result()


def gauge_mask(w, h, n=12):
    """Over the game's health fill: card-black bars between n slots, so the fill reads as segments."""
    t = Tex(w * U, h * U)
    W, H = w * U, h * U
    gap = 1.0 * U
    seg = (H - gap * (n - 1)) / n
    t.rects([(0, H - (i + 1) * seg - i * gap - gap, W, H - (i + 1) * seg - i * gap) for i in range(n - 1)],
            c(PANEL, 255))
    return t.result()


def ammo_card(w, h, split):
    t = glass(w * U, h * U, cuts={'tl': 7 * U}, fill_a=240, edge_a=110)
    W, H = w * U, h * U
    t.rect(W - 1.4 * U, 0, W, H, c(RED))
    label(t, 9 * U, 6 * U, 'AMMO', '弾薬', size=5.6 * U)
    t.line([(split * U, 13 * U), (split * U, H - 7 * U)], c(RED, 140), 0.4 * U)
    t.hatch(9 * U, H - 5.5 * U, 46 * U, H - 3.5 * U, RED_DIM, 255, step=1.6 * U, width=0.5 * U)
    return t.result()


def streak_tag(w, h):
    """The killstreak row inside the vitals card: 撃破 (kills) in crimson; the game writes the count and its word."""
    t = Tex(w * U, h * U)
    t.text(1 * U, h * U / 2, '撃破', ('jp7', 7.4 * U), c(RED), 'lm')
    return t.result()


def tag(w=58, h=26, s=8.0):
    """The small black glass tag behind every counter (sticky, metal, item meters...)."""
    t = glass(w * s, h * s, cuts={'tr': 4 * s}, fill_a=242, edge_a=120)
    t.rect(0, 0, 1 * s, h * s, c(RED))
    return t


def tag_with_icon(icon, w=58, h=26, s=8.0):
    """A counter tag with the item's icon on its left: the game draws its bar or count on the right."""
    t = tag(w, h, s)
    t.paste(icon, 2.5 * s, 1 * s, 24 * s, 24 * s)
    return t.result()


def sticky_icon(team, size=256):
    """A stickybomb: a dark sphere with eight spikes, a team-coloured ring and a hot core."""
    t = Tex(size, size, 2)
    m = size / 2
    col = TEAM[team]
    for i in range(8):
        a = i * np.pi / 4
        x1, y1 = m + np.cos(a) * size * 0.46, m + np.sin(a) * size * 0.46
        x0, y0 = m + np.cos(a + 0.22) * size * 0.3, m + np.sin(a + 0.22) * size * 0.3
        x2, y2 = m + np.cos(a - 0.22) * size * 0.3, m + np.sin(a - 0.22) * size * 0.3
        t.poly([(x0, y0), (x1, y1), (x2, y2)], c(GREY_D))
    t.ellipse(m, m, size * 0.33, size * 0.33, fill=c((24, 22, 26)), outline=c(col), width=size * 0.05)
    t.ellipse(m, m, size * 0.11, size * 0.11, fill=c(HOT))
    t.glow(size * 0.03, RED, 0.6)
    return t.result()


def streak_card():
    """Killstreak splash ("... is GODLIKE!"): nine-slice border (40 px corners), black glass, crimson tab."""
    t = glass(512, 128, cuts={'tr': 26}, fill_a=232, edge_a=140, ss=2)
    t.rect(0, 0, 6, 128, c(RED))
    return t.result()


def notice_card(team, w=1024, h=262):
    """Team goal / team switch / alert notice: black glass, the team colour down its left end behind the seal."""
    t = glass(w, h, cuts={'tr': h * 0.16, 'bl': h * 0.16}, fill_a=238, edge_a=110)
    t.poly(chamfer(0, 0, h * 0.86, h, bl=h * 0.16), c(TEAM_DEEP[team], 255))
    t.rect(0, 0, 8, h - h * 0.16, c(TEAM[team]))
    return t.result()


def notif_card(team, w=1024, h=176):
    t = glass(w, h, cuts={'tr': h * 0.2}, fill_a=238, edge_a=110)
    t.rect(0, 0, 10, h, c(TEAM[team]))
    return t.result()


def tid_card(team):
    t = glass(512, 96, cuts={'br': 22}, fill_a=232, edge_a=90)
    t.rect(0, 0, 7, 96, c(TEAM[team]))
    return t.result()


def freeze_card(team, w=1024, h=168):
    """Death screen 'You were killed by': the killer's team colour on the end where their health tile sits."""
    t = glass(w, h, cuts={'tr': h * 0.22}, fill_a=240, edge_a=120)
    t.rect(0, 0, h * 0.9, h, c(TEAM_DEEP[team], 255))
    t.rect(0, 0, 8, h, c(TEAM[team]))
    t.text(w - 14, h - 14, 'TERMINATED', ('mono', h * 0.13), c(RED, 170), 'rs', spacing=2)
    return t.result()


def stat_card(team, w=1024, h=354):
    t = glass(w, h, cuts={'tr': h * 0.1}, fill_a=240, edge_a=120)
    t.rect(0, 0, h * 0.84, h, c(TEAM_DEEP[team], 255))
    t.rect(0, 0, 8, h, c(TEAM[team]))
    return t.result()


def countdown_card(size=256):
    """The match-start countdown's card. The game makes its panel itself (a plain scalable image), so it cannot follow
    the team: a white hairline, no team's colour."""
    t = glass(size, size, cuts={'tr': 40, 'bl': 40}, fill_a=236, edge=WHITE, edge_a=110, ss=2, line=2)
    t.brackets(10, 10, size - 10, size - 10, 30, c(WHITE, 200), 3)
    return t.result()


def rule(w=512, h=32, thick=4):
    a = np.zeros((h, w), np.float32)
    y0 = (h - thick) // 2
    a[y0:y0 + thick, :] = np.clip(np.linspace(1.4, 0, w), 0, 1) ** 0.7
    img = np.dstack([np.full((h, w), RED[0]), np.full((h, w), RED[1]), np.full((h, w), RED[2]), a * 255])
    return Image.fromarray(img.astype(np.uint8), 'RGBA')


def rule_v(w=32, h=512):
    """The hairline between the scoreboard's teams, fading out at both ends."""
    a = np.zeros((h, w), np.float32)
    x0 = w // 2
    prof = np.clip(1 - np.abs(np.linspace(-1, 1, h)) ** 4, 0, 1) * 0.6
    a[:, x0:x0 + 2] = prof[:, None]
    img = np.dstack([np.full((h, w), RED[0]), np.full((h, w), RED[1]), np.full((h, w), RED[2]), a * 255])
    return Image.fromarray(img.astype(np.uint8), 'RGBA')


def building_card(team, w=512, h=192):
    """The engineer's building status card in its owner's team (the game picks bld_red / bld_blue): the glass's
    crimson edges, cut corner and Wall turn azure on the BLU one."""
    t = glass(w, h, cuts={'tr': h * 0.18}, fill_a=236, edge_a=110)
    t.rect(0, 0, 8, h, c(TEAM[team]))
    return to_blue(t.result()) if team == 'blue' else t.result()


def building_kanji(ch, size=256):
    t = Tex(size, size, 2)
    t.text(size / 2, size / 2, ch, ('jp9', size * 0.9), c(WHITE), 'mm')
    return t.result()


def hitmarker(size=128):
    """The X your hits flash: white, torn into a red copy to the left and a cyan one to the right."""
    t = Tex(size, size, 2)
    m, a, b = size / 2, size * 0.16, size * 0.42
    for off, col, alpha in ((-size * 0.035, (255, 20, 60), 170), (size * 0.035, (0, 214, 255), 130), (0, WHITE, 255)):
        for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            t.line([(m + dx * a + off, m + dy * a), (m + dx * b + off, m + dy * b)], c(col, alpha), size * 0.06)
    t.glow(size * 0.04, RED, 1.2)
    return t.result()


def respawn_card(w=1024, h=93):
    """"Respawn in X seconds": the label's own border (a border cannot follow the team), so white marks, no team's
    colour."""
    t = glass(w, h, cuts={'tl': h * 0.3, 'br': h * 0.3}, fill_a=232, edge=WHITE, edge_a=90)
    t.rect(h * 0.3, 0, h * 0.3 + 10, h, c(WHITE, 200))
    t.rect(w - h * 0.3 - 10, 0, w - h * 0.3, h, c(WHITE, 200))
    return t.result()


def spec_bar(edge='bottom', w=2048, h=96):
    """0.9 spectator / death screen: the letterbox bars back as the HUD's ink strips, the Wall fading in from the
    right, a crimson rule on the side that faces the picture with a hot stub at its left end. Borders cannot follow
    the team, so crimson."""
    im = Image.new('RGBA', (w, h), INK + (238,))
    im = wall_over(im, 'right', 0.30)
    d = ImageDraw.Draw(im)
    y = h - 3 if edge == 'bottom' else 0
    d.rectangle([0, y, w, y + 2], fill=RED + (230,))
    d.rectangle([0, y - 3 if edge == 'bottom' else y, w * 0.06, (y + 5) if edge == 'top' else y + 2], fill=HOT + (255,))
    return im


def flatline_text(team, w=1024, h=64):
    """The freezecam's "// FLATLINED BY" in the killer's team colour (a picture, so it can follow the team like the
    card under it; a label cannot)."""
    t = Tex(w, h, 2)
    col = TEAM[team]
    t.mixed(4, h / 2, [('//  ', ('raj7', 50), c(col)), ('FLATLINED BY', ('raj7', 50), c(col))], 'lm')
    return t.result()


def popup_head(w=2048, h=80):
    """0.9 (preview 28): the HUD Settings window's title strip, crimson filled, the Wall bright in it from the right,
    a dark rule under it."""
    im = Image.new('RGBA', (w, h), (200, 22, 42, 250))
    pat = wall_texture().convert('L').resize((w, h), Image.BICUBIC)
    ramp = Image.new('L', (w, 1))
    px = ramp.load()
    for x in range(w):
        px[x, 0] = int(255 * max(0.0, (x / (w - 1) - 0.35) / 0.65) ** 1.1)
    light = Image.new('RGBA', (w, h), HOT + (0,))
    light.putalpha(ImageChops.multiply(pat, ramp.resize((w, h))))
    im.alpha_composite(light)
    ImageDraw.Draw(im).rectangle([0, h - 4, w, h], fill=INK + (255,))
    return im


def menu_bg(w=1024, h=384, header=0.27):
    t = glass(w, h, cuts={'tr': h * 0.08}, fill_a=236, edge_a=120)
    t.rect(0, 0, w, h * header, c(RED_DEEP, 200))
    t.line([(0, h * header), (w, h * header)], c(RED, 160), 2)
    return t.result()


MENU_TONES = {'on': (RED, WHITE), 'dim': (GREY_D, GREY), 'red': (RED_DEEP, (200, 150, 150))}


def menu_item(state, w=256, h=272):
    """One building / class slot of the build and disguise menus, toned by its state (crimson = ready, grey = built
    or unavailable, deep red = not enough metal)."""
    tone, edge = MENU_TONES[state]
    t = glass(w, h, cuts={'tr': 22}, fill_a=236, edge=edge, edge_a=150)
    yy = np.linspace(0, 1, t.im.height)[:, None]
    a = np.clip((yy - 0.45) / 0.55, 0, 1) ** 1.5 * (150 if state == 'on' else 110)
    g = Image.new('RGBA', t.im.size, c(tone, 0))
    g.putalpha(Image.fromarray((a * np.ones((1, t.im.width))).astype(np.uint8)))
    t.im.alpha_composite(g)
    return t.result()


def menu_key(size=128):
    """The key chip behind a build / disguise menu number (the number label's own border, so no team): a white
    keycap, the number on it in black."""
    t = Tex(size, size, 2)
    t.poly(chamfer(4, 4, size - 4, size - 4, tr=size * 0.22), c(WHITE))
    return t.result()


def escort_strip(w=1024, h=128):
    """0.9 (preview 11): the payload track as a slim ink rail through the middle of the strip, crimson hairlines on
    its edges and hot square ends; the rest is clear, so the game's track, cart and checkpoints sit on the map."""
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y0, y1 = int(h * 0.62), int(h * 0.80)
    d.rectangle([0, y0, w, y1], fill=INK + (225,))
    d.rectangle([0, y0, w, y0 + 1], fill=RED + (200,))
    d.rectangle([0, y1 - 1, w, y1], fill=RED + (120,))
    for x in (0, w - 10):
        d.rectangle([x, y0 - 6, x + 10, y1 + 6], fill=HOT + (255,))
    return im


def cp_rim(size=256):
    t = Tex(size, size, 2)
    m = size / 2
    t.ellipse(m, m, size * 0.46, size * 0.46, outline=c(INK, 230), width=size * 0.06)
    t.ellipse(m, m, size * 0.44, size * 0.44, outline=c(RED), width=size * 0.015)
    for i in range(24):
        a = i * np.pi / 12
        r0, r1 = size * 0.47, size * (0.5 if i % 6 == 0 else 0.49)
        t.line([(m + np.cos(a) * r0, m + np.sin(a) * r0), (m + np.cos(a) * r1, m + np.sin(a) * r1)], c(RED, 200),
               size * 0.01)
    return t.result()


def intel_card(size=128):
    """The carried intel: a white briefcase with a crimson edge."""
    t = Tex(size, size, 2)
    w, h = size * 0.74, size * 0.5
    x0, y0 = (size - w) / 2, size * 0.32
    t.outline([(size * 0.39, size * 0.33), (size * 0.39, size * 0.2), (size * 0.61, size * 0.2),
               (size * 0.61, size * 0.33)], c(WHITE), size * 0.05)
    t.poly(chamfer(x0, y0, x0 + w, y0 + h, tr=size * 0.06, bl=size * 0.06), c(WHITE))
    t.rect(x0, y0 + h * 0.38, x0 + w, y0 + h * 0.46, c(RED))
    t.glow(size * 0.03, RED, 1.2)
    return t.result()


def ctf_bar(w=1024, h=222):
    t = glass(w, h, cuts={'tl': h * 0.25, 'tr': h * 0.25}, fill_a=236, edge_a=110)
    t.rect(10, 10, w / 2 - 6, h - 10, c(TEAM_DEEP['blue'], 255))
    t.rect(w / 2 + 6, 10, w - 10, h - 10, c(TEAM_DEEP['red'], 255))
    t.rect(10, h - 16, w / 2 - 6, h - 10, c(TEAM['blue']))
    t.rect(w / 2 + 6, h - 16, w - 10, h - 10, c(TEAM['red']))
    t.line([(w / 2, 14), (w / 2, h - 14)], c(RED), 3)
    return t.result()


def ring(team, pointer=False, size=256):
    """CTF compass ring (the game turns it toward the flag): a dark disc in a bright ring of the team colour that
    glows into the floor around it, a pointer at the top. Kept inside the texture's circle, so it turns cleanly."""
    t = Tex(size, size, 2)
    m = size / 2
    col = TEAM[team] if team in TEAM else (180, 90, 92)
    lit = tuple(round(v + (255 - v) * 0.22) for v in col)
    r, w = size * 0.385, size * 0.055
    t.ellipse(m, m, r, r, outline=c(col), width=w)
    if pointer:
        t.poly([(m, size * 0.045), (m + size * 0.075, size * 0.15), (m - size * 0.075, size * 0.15)], c(col))
    t.glow(size * 0.028, col, 1.5)
    t.ellipse(m, m, r - w / 2, r - w / 2, fill=c(INK, 225))
    t.ellipse(m, m, r, r, outline=c(lit), width=w)
    t.ellipse(m, m, size * 0.305, size * 0.305, outline=c(WHITE, 70), width=size * 0.008)
    if pointer:
        t.poly([(m, size * 0.045), (m + size * 0.075, size * 0.15), (m - size * 0.075, size * 0.15)], c(lit))
    return t.result()


def glyph(stock, size=256):
    """A flag state glyph (home, dropped, carried) in deep ink: the game lays it on the briefcase, so dark on light
    reads best, as in the stock HUD."""
    im = stock.convert('RGBA').resize((size, size), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    out = np.concatenate([np.broadcast_to(np.array(INK, np.float32) + 4, a[..., :3].shape), a[..., 3:4]], -1)
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


def briefcase(stock, size=256):
    """The intel briefcase under the glyph, lifted from the stock tan to near white so the ring reads at a glance."""
    im = stock.convert('RGBA').resize((size, size), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    rgb = a[..., :3] + (np.array((252, 250, 246), np.float32) - a[..., :3]) * 0.62
    return Image.fromarray(np.concatenate([rgb, a[..., 3:4]], -1).astype(np.uint8), 'RGBA')


# ---------------------------------------------------------------- payload (hud/cart_*, redirected by build.py)
def _team_col(team):
    return TEAM[team] if team in TEAM else GREY


def cart_point(team, opaque=False, size=128):
    """A checkpoint on the payload track: the CTF ring's language, a dark disc in a ring of the owning team's colour
    with a bright dot in the middle (grey while nobody holds it)."""
    t = Tex(size, size, 2)
    m = size / 2
    col = _team_col(team)
    t.ellipse(m, m, size * 0.4, size * 0.4, outline=c(col), width=size * 0.07)
    t.glow(size * 0.025, col, 1.2)
    t.ellipse(m, m, size * 0.37, size * 0.37, fill=c(INK, 255 if opaque else 228))
    lit = tuple(round(v + (255 - v) * 0.2) for v in col)
    t.ellipse(m, m, size * 0.4, size * 0.4, outline=c(lit), width=size * 0.07)
    t.ellipse(m, m, size * 0.3, size * 0.3, outline=c(WHITE, 60), width=size * 0.012)
    t.ellipse(m, m, size * 0.11, size * 0.11, fill=c(WHITE))
    return t.result()


def cart_home(team, square=False, opaque=False, size=128):
    """Where the cart starts: the checkpoint disc (a square for payload race) with a white house in it."""
    t = Tex(size, size, 2)
    m = size / 2
    col = _team_col(team)
    lit = tuple(round(v + (255 - v) * 0.2) for v in col)
    if square:
        r = size * 0.4
        t.poly(chamfer(m - r, m - r, m + r, m + r, tl=size * 0.08, br=size * 0.08), c(col))
        t.glow(size * 0.025, col, 1.2)
        r2 = r - size * 0.07
        t.poly(chamfer(m - r2, m - r2, m + r2, m + r2, tl=size * 0.05, br=size * 0.05), c(INK, 255 if opaque else 228))
    else:
        t.ellipse(m, m, size * 0.4, size * 0.4, outline=c(col), width=size * 0.07)
        t.glow(size * 0.025, col, 1.2)
        t.ellipse(m, m, size * 0.37, size * 0.37, fill=c(INK, 255 if opaque else 228))
        t.ellipse(m, m, size * 0.4, size * 0.4, outline=c(lit), width=size * 0.07)
    hw, top, eave, foot = size * 0.17, size * 0.3, size * 0.47, size * 0.68
    t.poly([(m, top), (m + hw + size * 0.05, eave), (m - hw - size * 0.05, eave)], c(WHITE))
    t.rect(m - hw, eave - 1, m + hw, foot, c(WHITE))
    t.rect(m - size * 0.05, size * 0.55, m + size * 0.05, foot, c(INK))
    return t.result()


def cart_badge(team, bottom=False, size=128):
    """The cart on the track: a pin in the team's colour, its point on the track, the cart drawn in its lower half
    (the game lays its arrows, the pushers' count and the recede timer over the upper half). The bottom variant
    (payload race's lower track) points up."""
    t = Tex(size, size, 2)
    col = _team_col(team)
    dark = tuple(round(i * 0.78 + v * 0.22) for i, v in zip(INK, col))
    x0, x1, y0, y1 = size * 0.12, size * 0.88, size * 0.04, size * 0.7
    cut = size * 0.1
    body = [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1), (size * 0.6, y1), (size * 0.5, size * 0.97),
            (size * 0.4, y1), (x0, y1), (x0, y0 + cut)]
    t.poly(body, c(col))
    t.glow(size * 0.03, col, 1.3)
    e, f = size * 0.05, size * 0.13   # the dark inside, the edge's width in from the outline
    inset = [(x0 + e, y0 + f), (x0 + f, y0 + e), (x1 - f, y0 + e), (x1 - e, y0 + f), (x1 - e, y1 - e),
             (size * 0.57, y1 - e), (size * 0.5, size * 0.84), (size * 0.43, y1 - e), (x0 + e, y1 - e)]
    t.poly(inset, c(dark, 240))
    # the cart: a tub on two wheels
    cy = size * 0.5
    t.poly([(size * 0.3, cy - size * 0.07), (size * 0.7, cy - size * 0.07), (size * 0.65, cy + size * 0.06),
            (size * 0.35, cy + size * 0.06)], c(WHITE))
    for wx in (size * 0.4, size * 0.6):
        t.ellipse(wx, cy + size * 0.1, size * 0.045, size * 0.045, fill=c(WHITE))
    im = t.result()
    return im.transpose(Image.FLIP_TOP_BOTTOM) if bottom else im


def cart_alert(w=256, h=128):
    """Over the cart when it is about to roll back: a hot crimson warning sign with a soft glow."""
    t = Tex(w, h, 2)
    m = w / 2
    t.poly([(m, h * 0.08), (m + h * 0.48, h * 0.9), (m - h * 0.48, h * 0.9)], c(HOT))
    t.glow(h * 0.06, HOT, 1.4)
    t.poly([(m, h * 0.22), (m + h * 0.34, h * 0.82), (m - h * 0.34, h * 0.82)], c(INK, 235))
    t.rect(m - h * 0.035, h * 0.38, m + h * 0.035, h * 0.64, c(WHITE))
    t.rect(m - h * 0.035, h * 0.7, m + h * 0.035, h * 0.76, c(WHITE))
    return t.result()


def cart_arrow(right=True, size=64):
    """The cart's direction (rolling back, or the pushers' capping arrow): a white double chevron."""
    t = Tex(size, size, 2)
    for k in (0.0, 0.26):
        x = size * (0.22 + k)
        pts = [(x, size * 0.2), (x + size * 0.28, size * 0.5), (x, size * 0.8)]
        t.line(pts, c(WHITE), size * 0.11)
    t.glow(size * 0.04, RED, 1.0)
    im = t.result()
    return im if right else im.transpose(Image.FLIP_LEFT_RIGHT)


def cart_blocked(size=64):
    """The cart is blocked: a crimson no-entry ring."""
    t = Tex(size, size, 2)
    m = size / 2
    t.ellipse(m, m, size * 0.38, size * 0.38, outline=c(HOT), width=size * 0.1)
    t.line([(m - size * 0.26, m + size * 0.26), (m + size * 0.26, m - size * 0.26)], c(HOT), size * 0.1)
    t.glow(size * 0.04, HOT, 1.2)
    return t.result()


def cart_track(w=512, h=16, opaque=False):
    """The track the cart runs on: a dark rail between two light hairlines."""
    t = Tex(w, h, 2)
    t.rect(0, 0, w, h, c(INK, 255 if opaque else 215))
    t.rect(0, 0, w, max(1.5, h * 0.12), c(WHITE, 130))
    t.rect(0, h - max(1.5, h * 0.12), w, h, c(WHITE, 130))
    return t.result()


def cart_track_fill(team, opaque=False, w=64, h=16):
    """How far the cart has come (payload race, hills): the team's colour, a lighter line along its top."""
    t = Tex(w, h, 2)
    col = _team_col(team)
    t.rect(0, 0, w, h, c(col, 255 if opaque else 225))
    t.rect(0, 0, w, h * 0.25, c(tuple(round(v + (255 - v) * 0.45) for v in col), 255 if opaque else 235))
    return t.result()


def cart_track_arrow(w=256, h=32):
    """A hill on the track: white chevrons along it."""
    t = Tex(w, h, 2)
    for i in range(8):
        x = w * (i + 0.3) / 8
        t.line([(x, h * 0.2), (x + h * 0.3, h * 0.5), (x, h * 0.8)], c(WHITE, 170), h * 0.12)
    return t.result()


def payload_icons(out):
    """The payload HUD's pictures, under the stock names (hud/cart_*); build.py points the stock materials here."""
    for team in ('blue', 'red', 'neutral'):
        for opaque in (False, True):
            out.thumb(f'obj/cart_point_{team}' + ('_opaque' if opaque else ''), cart_point(team, opaque))
        out.thumb(f'obj/cart_{team}', cart_badge(team))
        out.thumb(f'obj/cart_{team}_bottom', cart_badge(team, bottom=True))
    for team in ('blue', 'red'):
        out.thumb(f'obj/cart_home_{team}', cart_home(team))
        out.thumb(f'obj/cart_home_{team}_opaque', cart_home(team, opaque=True))
        out.thumb(f'obj/cart_home_{team}_square', cart_home(team, square=True))
        out.thumb(f'obj/cart_track_{team}', cart_track_fill(team))
        out.thumb(f'obj/cart_track_{team}_opaque', cart_track_fill(team, opaque=True))
    out.thumb('obj/cart_alert', cart_alert())
    out.thumb('obj/cart_arrow_left', cart_arrow(right=False))
    out.thumb('obj/cart_arrow_right', cart_arrow(right=True))
    out.thumb('obj/cart_blocked', cart_blocked())
    out.thumb('obj/cart_track', cart_track())
    out.thumb('obj/cart_track_neutral_opaque', cart_track(h=32, opaque=True))
    out.thumb('obj/cart_track_arrow', cart_track_arrow())


def cp_icon(stock, team, size=128):
    """Control point icon: the stock icon in the hologram duotone (the team's colour on top) inside a thin ring."""
    t = Tex(size, size, 2)
    m = size / 2
    col = TEAM.get(team, GREY)
    t.ellipse(m, m, size * 0.47, size * 0.47, fill=c(INK, 220), outline=c(col), width=size * 0.04)
    icon = duotone(stock.convert('RGBA').resize((size, size), Image.LANCZOS), mid=col, light=WHITE)
    t.paste(icon, size * 0.14, size * 0.14, size * 0.72, size * 0.72)
    return t.result()


def top_band(w=1024, h=80):
    """Behind the casual team strip at the top: black glass, a crimson hairline along its foot."""
    t = glass(w, h, cuts={'bl': h * 0.4, 'br': h * 0.4}, fill_a=228, edge_a=90)
    t.line([(h * 0.4, h - 2), (w - h * 0.4, h - 2)], c(RED), 2)
    return t.result()


def portrait_frame(w=128, h=100):
    t = Tex(w, h, 2)
    t.outline([(1, 1), (w - 1, 1), (w - 1, h - 1), (1, h - 1)], c(WHITE, 150), 1.5)
    t.brackets(3, 3, w - 3, h - 3, 14, c(RED), 2)
    return t.result()


def banner(team, mirror=False, w=1024, h=256):
    """Scoreboard / win panel team head, the friends panel's header in the team's colour: black glass, the team tab
    on the outer end, ■ 青 // BLU in mono and a hatch toward the middle."""
    col = TEAM[team]
    t = glass(w, h, cuts={'tr' if mirror else 'tl': h * 0.16}, fill_a=232, edge=col, edge_a=150)
    jp, en = ('青', 'BLU') if team == 'blue' else ('赤', 'RED')
    if mirror:
        t.rect(w - 10, 0, w, h, c(col))
        t.mixed(w - 34, h * 0.15, [(jp, ('jp5', 34), c(col)), ('  //  ', ('mono', 34), c(col, 150)),
                                  (en, ('mono', 38), c(col))], 'rm')
        t.rect(w - 34 - t.width('  //  ', ('mono', 34)) - t.width(jp, ('jp5', 34)) - t.width(en, ('mono', 38)) - 30,
               h * 0.15 - 10, w - 34 - t.width('  //  ', ('mono', 34)) - t.width(jp, ('jp5', 34))
               - t.width(en, ('mono', 38)) - 10, h * 0.15 + 10, c(col))
        t.hatch(w * 0.06, h * 0.12, w * 0.26, h * 0.26, RED_DIM, 255, step=14, width=4)
    else:
        t.rect(0, 0, 10, h, c(col))
        t.rect(34, h * 0.15 - 10, 54, h * 0.15 + 10, c(col))
        t.mixed(64, h * 0.15, [(jp, ('jp5', 34), c(col)), ('  //  ', ('mono', 34), c(col, 150)),
                              (en, ('mono', 38), c(col))], 'lm')
        t.hatch(w * 0.74, h * 0.12, w * 0.94, h * 0.26, RED_DIM, 255, step=14, width=4)
    t.line([(0, h - 3), (w, h - 3)], c(col, 120), 3)
    return t.result()


def score_main(w=1024, h=656):
    """The scoreboard's page: black glass with two cut corners and the crimson hairline."""
    t = glass(w, h, cuts={'tl': 24, 'br': 24}, fill_a=232, edge_a=120)
    return t.result()


def win_page(w=1024, h=672):
    """End-of-round page: black glass, ■ 勝負 // ROUND OVER in the top right corner. Near solid: the centre strip
    (stickies, ÜberCharge, metal) sits under its list of top players."""
    t = glass(w, h, cuts={'tr': 40, 'bl': 40}, fill_a=246, edge_a=150)
    t.mixed(w - 64, 30, [('勝負', ('jp5', 26), c(RED)), ('  //  ', ('mono', 26), c(RED, 150)),
                         ('ROUND OVER', ('mono', 28), c(RED))], 'rm')
    return t.result()


def search_bar(chip=True, w=512, h=80):
    """Backpack / item selection search strip: black glass with a crimson hairline under the typed text; at the left
    the ■ 検索 tag (the game draws the typed text right of it). chip=False: the plain strip behind drop-downs."""
    t = glass(w, h, cuts={'tr': 14}, fill_a=240, edge_a=110)
    x0 = 0
    if chip:
        cw = h * 1.08
        t.rect(0, 0, 6, h, c(RED))
        t.rect(20, h / 2 - 9, 38, h / 2 + 9, c(RED))
        t.text(46, h / 2, '検索', ('jp5', 26), c(RED), 'lm')
        x0 = cw + 6
    t.line([(x0 + 6, h - 8), (w - 18, h - 8)], c(RED, 160), 2)
    return t.result()


def craft_card(w, h, band=0.17):
    """Crafting cards: black glass, a crimson tab down the heading and a hairline under it."""
    t = glass(w, h, cuts={'tr': 30}, fill_a=236, edge_a=120)
    t.rect(0, 0, 8, h * band, c(RED))
    t.line([(0, h * band), (w, h * band)], c(RED, 120), 2)
    return t.result()


def craft_chip(size=128):
    t = glass(size, size, cuts={'tr': 22}, fill_a=236, edge_a=150)
    return t.result()


def chip(hover=False, size=128):
    t = Tex(size, size, 4)
    if hover:
        t.poly(chamfer(0, 0, size, size, tr=size * 0.2), c(RED))
    else:
        t.poly(chamfer(0, 0, size, size, tr=size * 0.2), c(PANEL, 220))
        t.outline(chamfer(1, 1, size - 1, size - 1, tr=size * 0.2 - 1), c(RED, 130), 2)
    return t.result()


# ---------------------------------------------------------------- portraits: class / team cards
def class_card(portrait, num, label_txt, kana, hover=False, w=512, h=192):
    """Class select card (178 x 67 units): the class portrait in the hologram duotone on the left behind scan
    lines, the number, the class and its katakana on the right; hover lights it crimson."""
    t = glass(w, h, cuts={'tr': 22, 'bl': 22}, fill=RED_DEEP if hover else PANEL, fill_a=240,
              edge=HOT if hover else RED, edge_a=255 if hover else 110, line=2 if hover else 1.2)
    pw = h * 1.05
    p = portrait.convert('RGBA')
    side = min(p.width, p.height)
    p = p.crop(((p.width - side) // 2, 0, (p.width + side) // 2, side))
    p = scanlines(duotone(p, light=WHITE if hover else PINK, gamma=0.85 if hover else 1.0), step=4, depth=0.3)
    t.paste(p, 6, 6, pw - 12, h - 12)
    t.line([(pw, 14), (pw, h - 14)], c(RED, 160), 2)
    t.text(pw + 18, h * 0.3, '%02d' % num if isinstance(num, int) else num, ('mono', h * 0.2),
           c(INK if hover else RED), 'lm')
    if hover:
        t.rect(pw + 12, h * 0.3 - h * 0.12, pw + 12 + t.width('%02d' % num if isinstance(num, int) else num,
                                                               ('mono', h * 0.2)) + 12, h * 0.3 + h * 0.12, c(RED))
        t.text(pw + 18, h * 0.3, '%02d' % num if isinstance(num, int) else num, ('mono', h * 0.2), c(INK), 'lm')
    t.text(pw + 16, h * 0.62, label_txt, ('raj7', h * 0.3), c(WHITE), 'lm', spacing=2)
    t.text(w - 18, h * 0.86, kana, ('jp5', h * 0.13), c(PINK if hover else GREY), 'rm')
    return t.result()


def tall_card(figure, num, kana, active=False, w=256, h=512, label_txt='', id_tag=True):
    """Loadout class card (68 x 136 units) in the in-game ID photo's language: black glass, the class figure in the
    crimson duotone behind scan lines and ID brackets, the number in mono over it, the class and its katakana under
    it; the active class is lit crimson."""
    t = glass(w, h, cuts={'br': 24}, fill=PANEL, fill_a=236, edge=HOT if active else RED, edge_a=255 if active else 100,
              line=2.4 if active else 1.2)
    x0, y0, x1, y1 = 10, 44, w - 10, h - 78
    t.rect(x0, y0, x1, y1, c((26, 5, 10), 255))
    fig = duotone(figure.convert('RGBA'), dark=(26, 5, 10), mid=RED if active else (150, 18, 34),
                  light=WHITE if active else PINK)
    fig = scanlines(fig, step=4, depth=0.45)
    fh = (y1 - y0) * 0.98
    fw = fh * fig.width / fig.height
    if fw > (x1 - x0):
        fw = x1 - x0
        fh = fw * fig.height / fig.width
    t.paste(fig, (x0 + x1 - fw) / 2, y1 - fh, fw, fh)
    t.brackets(x0 + 6, y0 + 6, x1 - 6, y1 - 6, 22, c(WHITE, 200), 2)
    t.rect(10, 16, 22, 28, c(HOT if active else RED))
    t.text(30, 22, num if isinstance(num, str) else '%02d' % num, ('mono', 28), c(WHITE if active else RED), 'lm')
    if id_tag:  # the class select puts how many teammates play the class there instead
        t.text(w - 12, 22, 'ID', ('mono', 22), c(GREY), 'rm')
    if label_txt:
        t.text(12, h - 52, label_txt, ('raj7', 38 if len(label_txt) <= 7 else 30), c(WHITE), 'lm')
    t.text(12, h - 22, kana, ('jp5', 22), c(RED if active else GREY), 'lm')
    if active:
        t.rect(0, 0, w, 5, c(RED))
    return t.result()


CELL = (190, 132)            # px: a class's cell in the class select's code matrix (menu.matrix_cells)
RANDOM_CELL = (594, 52)      # px: the wide RANDOM cell under them
CELL_CODES = {'scout': '1C', 'soldier': 'BD', 'pyro': '55', 'demoman': 'E9', 'heavyweapons': '7A',
              'engineer': 'FF', 'medic': 'C3', 'sniper': '9B', 'spy': '0X', 'random': '??'}


def matrix_cell(figure, code, key, label_txt, kana, lit=False, w=190, h=132):
    """A class in the class select's code matrix (0.9, preview 24): a plain ink card, the hex code large and bold over
    the class name, its number key in the corner (the teammate count goes in the other). Lit (under the pointer): the
    Wall floods the card in crimson, the edge burns hot, the code splits red. The RANDOM cell is a wide strip."""
    wide = w > 2 * h
    t = glass(w, h, cuts={'br': 12} if not lit else {'tr': 12, 'br': 12}, fill=PANEL, fill_a=240,
              edge=HOT if lit else RED, edge_a=255 if lit else 110, dots=False, line=2.0 if lit else 1.0,
              wall=None)
    if lit:
        W_, H_ = t.im.size
        flood = Image.new('RGBA', (W_, H_), (104, 12, 26, 220))
        flood = wall_over(flood, 'left', 0.95)
        flood = wall_over(flood, 'right', 0.6)
        mask = t.im.split()[3].point(lambda v: 255 if v > 128 else 0)
        flood.putalpha(ImageChops.multiply(flood.split()[3], mask))
        t.im.alpha_composite(flood)
        t.rect(0, 0, 4, h, c(HOT))
    # the class behind the code, on the right (back by the user's call): the game's large class portrait (256 px,
    # the bust) in the hologram duotone with scan lines and a red / cyan split, fading out towards the code
    from PIL import ImageOps
    src = figure.convert('RGBA')
    lifted = ImageOps.autocontrast(src.convert('RGB'), cutoff=1).convert('RGBA')   # dark portraits (soldier) read
    lifted.putalpha(src.split()[3])
    fig = duotone(lifted, dark=(20, 4, 8), mid=RED if lit else (150, 22, 38),
                  light=PINK if lit else (236, 150, 160))
    fig = scanlines(fig, step=3, depth=0.45)
    a = np.asarray(fig, np.float32)
    fw_px = a.shape[1]
    ramp = np.clip(np.linspace(-0.15, 1.6, fw_px), 0, 1) ** 1.4
    a[..., 3] *= ramp[None, :] * (0.95 if lit else 0.75)
    fig = Image.fromarray(a.astype(np.uint8), 'RGBA')
    fh = h
    fw = fh * fig.width / fig.height
    fx, fy = w - fw - (30 if wide else 3), 0
    for dx, col, al in ((-3, (255, 20, 60), 90), (3, (0, 214, 255), 70)):
        ghost = Image.new('RGBA', fig.size, col + (0,))
        ghost.putalpha(fig.split()[3].point(lambda v, al=al: v * al // 255))
        t.paste(ghost, fx + dx, fy, fw, fh)
    t.paste(fig, fx, fy, fw, fh)
    if not wide:  # the code and name stay readable over the bust
        t.paste(Image.fromarray(np.dstack([np.full((8, 64), v, np.uint8) for v in PANEL] + [
            np.tile(np.linspace(150, 0, 64).astype(np.uint8), (8, 1))]), 'RGBA'), 0, 0, w * 0.6, h)
    if wide:
        t.text(16, h / 2, '??', ('raj7', 26), c(WHITE), 'lm')
        t.mixed(60, h / 2, [(label_txt, ('raj7', 26), c(WHITE)), ('  //  ', ('mono', 13), c(RED)),
                            (kana, ('jp5', 13), c(PINK if lit else GREY))], 'lm')
        if lit:
            t.text(w - 16, h / 2, '>> LINK', ('mono', 13), c(HOT), 'rm')
        return t.result()
    t.text(12, 13, f'KEY {key}', ('mono', 11), c(PINK if lit else GREY), 'lm')
    if lit:
        t.text(12 + 3, 22, code, ('raj7', 58), c(RED), 'lt')
    t.text(12, 22, code, ('raj7', 58), c(WHITE), 'lt')
    t.text(12, 104, label_txt, ('raj7', 24 if len(label_txt) <= 7 else 20), c(WHITE), 'lm')
    if lit:
        t.text(w - 10, h - 11, '>> LINK', ('mono', 11), c(HOT), 'rm')
    return t.result()


def team_card(portraits, label_txt, kanji, team, hover=False, w=512, h=1024):
    """Team select card (176 x 352): two class portraits stacked in the team's duotone, the team name and its kanji
    seal; hover lights the edge."""
    col = TEAM[team]
    t = glass(w, h, cuts={'tr': 40, 'bl': 40}, fill=TEAM_DEEP[team], fill_a=245,
              edge=WHITE if hover else col, edge_a=255 if hover else 170, line=3 if hover else 1.6)
    ph = h * 0.33
    for i, p in enumerate(portraits):
        p = p.convert('RGBA')
        side = min(p.width, p.height)
        p = p.crop(((p.width - side) // 2, 0, (p.width + side) // 2, side))
        p = scanlines(duotone(p, dark=TEAM_DEEP[team], mid=col, light=WHITE), step=4, depth=0.3)
        t.paste(p, 24, 40 + i * (ph + 16), w - 48, ph)
    y = 40 + 2 * (ph + 16) + 20
    t.text(w / 2, y + 40, label_txt, ('raj7', 140), c(WHITE), 'mm', spacing=8)
    t.paste(seal(kanji, 120, 120, fill=col if team == 'red' else (60, 100, 170)), w / 2 - 60, y + 110, 120, 120)
    if hover:
        t.glow(10, col, 0.8)
    return t.result()


def small_card(label_txt, kanji, hover=False, w=512, h=192):
    t = glass(w, h, cuts={'tr': 26, 'bl': 26}, fill=RED_DEEP if hover else PANEL, fill_a=240,
              edge=HOT if hover else RED, edge_a=255 if hover else 120, line=2 if hover else 1.2)
    t.paste(seal(kanji, 120, 120), 24, (h - 120) / 2, 120, 120)
    t.text(170, h / 2, label_txt, ('raj7', 66), c(WHITE), 'lm', spacing=3)
    return t.result()


def team_tag(team, hover=False, w=256, h=128):
    col = TEAM[team]
    t = glass(w, h, cuts={'tr': 22}, fill=TEAM_DEEP[team], fill_a=245, edge=WHITE if hover else col,
              edge_a=255 if hover else 180, line=3 if hover else 1.6)
    t.rect(0, 0, 10, h, c(col))
    return t.result()


# ---------------------------------------------------------------- main menu
def logo(compact=False):
    """Seal + (DON'T FEAR) THE REAPER, the last letter breaking into pixel dust, the rule and the division line."""
    W, H = 1240, 248
    t = Tex(W, H)
    t.rect(0, 26, 116, 142, c(RED))
    t.outline([(6, 32), (110, 32), (110, 136), (6, 136)], c(INK, 110), 2)
    t.text(58, 36, '死', ('jp9', 44), c(WHITE), 'mt')
    t.text(58, 84, '神', ('jp9', 44), c(WHITE), 'mt')
    x0 = 152
    t.text(x0 + 4, 14, "(DON'T FEAR)", ('mich', 30), c(RED), 'lt', spacing=10)
    ss = t.ss
    m = Image.new('L', t.im.size, 0)
    d = ImageDraw.Draw(m)
    wf = font('mich', 98 * ss)
    x = x0
    for ch in 'THE REAPER':
        d.text((x * ss, 56 * ss), ch, font=wf, fill=255, anchor='lt')
        x += wf.getlength(ch) / ss + 4
    end = x - 4
    a = np.asarray(m, np.uint8).copy()
    r = np.random.default_rng(8)
    blk = 6 * ss
    xs0 = (x0 + (end - x0) * 0.9) * ss
    ys, _ = np.nonzero(a)
    dust = np.zeros_like(a)
    for by in range(ys.min() - ys.min() % blk, ys.max() + 1, blk):
        for bx in range(int(xs0) - int(xs0) % blk, int(end * ss) + blk, blk):
            if not a[by:by + blk, bx:bx + blk].any():
                continue
            tt = min(1.0, max(0.0, (bx - xs0) / (end * ss - xs0)))
            if r.random() < 0.62 * tt ** 1.2:
                a[by:by + blk, bx:bx + blk] = 0
                if r.random() < 0.6:
                    dx = int(r.exponential(30) * ss) + blk
                    dy = int(r.normal(-8, 10) * ss)
                    ty, tx = by + dy, bx + dx
                    if 0 <= ty < a.shape[0] - blk and 0 <= tx < a.shape[1] - blk:
                        dust[ty:ty + blk, tx:tx + blk] = int(r.uniform(90, 255))
    for mask, col, dx, k in ((a, RED, -4 * ss, 0.55), (a, WHITE, 0, 1.0), (dust, RED, 0, 1.0)):
        layer = Image.new('RGBA', t.im.size, c(col, 0))
        mm = np.roll(mask, dx, axis=1) if dx else mask
        layer.putalpha(Image.fromarray((mm * k).astype(np.uint8)))
        t.im.alpha_composite(layer)
    t.rect(0, 172, 66, 178, c(RED))
    t.rect(66, 174, W - 40, 176, c(RED, 140))
    t.mixed(0, 206, [('SOUL HARVEST DIVISION', ('mono', 24), c(GREY)), ('  //  ', ('mono', 24), c(RED)),
                     ('死神部門', ('jp5', 22), c(GREY)), ('  //  ', ('mono', 24), c(RED)),
                     ('HUD BY INGALTHER', ('mono', 24), c(GREY))])
    img = t.result()
    return img.crop((0, 0, W, 186)) if compact else img


def nav_button(i, en, jp, armed, nav_w, nav_h):
    """One main menu button with its number, name and Japanese name baked in (the button itself has no text)."""
    s = 4.3  # texture px per unit: 1015 x 90 for the 236 x 21 button, one 1024-wide texture
    W, H = round(nav_w * s), round(nav_h * s)
    t = Tex(W, H)
    cut = 5.5 * s
    if armed:
        t.poly(chamfer(0, 0, W, H, br=cut), c(RED))
        r = np.random.default_rng(4 + i)
        boxes = []
        for _ in range(16):  # the armed button sheds pixel dust off its cut corner
            q = r.choice([2, 3, 3, 4]) * s / 2.2
            yy = r.uniform(H * 0.45, H - q)
            xx = W - cut * (1 - (yy - (H - cut)) / cut) if yy > H - cut else W
            xx -= r.exponential(10) * s / 2.2 + q
            boxes.append((xx, yy, xx + q, yy + q))
        t.rects(boxes, c(INK, 150))
        fg, num, sub = c(INK), c(INK), c(INK, 170)
    else:
        t.poly(chamfer(0, 0, W, H, br=cut), c(PANEL, 210))
        t.rect(0, 0, 0.45 * s, H, c(RED_DIM))
        t.line([(0, H - 1), (W - cut, H - 1)], c(RED, 50), 1)
        fg, num, sub = c(WHITE), c(RED), c(GREY)
    cy = H / 2
    t.text(8 * s, cy, '%02d' % (i + 1), ('mono', 6.2 * s), num, 'lm')
    t.text(24 * s, cy + 0.4 * s, en, ('raj7', 10.6 * s), fg, 'lm', spacing=0.45 * s)
    t.text(W - 10 * s, cy, jp, ('jp5', 5.3 * s), sub, 'rm')
    return t.result()


def profile_card(w, h):
    s = 3.9  # 1014 x 234: one 1024 x 256 texture
    t = glass(round(w * s), round(h * s), cuts={'tr': 6 * s}, fill_a=222, edge_a=100)
    t.rect(0, 0, 1.4 * s, h * s * 0.42, c(RED))
    return t.result()


def friends_panel(w, h, head):
    s = 3.6  # 778 x 504: one 1024 x 512 texture
    W, H = round(w * s), round(h * s)
    t = glass(W, H, cuts={'tl': 6 * s}, fill_a=222, edge_a=100)
    t.rect(0, 6 * s, 1.4 * s, head * s, c(RED))
    t.line([(1, head * s), (W - 1, head * s)], c(RED, 70), 1)
    t.hatch(W - 64 * s, head * s * 0.42, W - 34 * s, head * s * 0.58, RED_DIM, 255, step=2.2 * s, width=0.7 * s)
    t.text(W - 8 * s, head * s / 2, 'フレンド', ('jp5', 5.4 * s), c(RED), 'rm')
    return t.result()


def popup_bg(w, h):
    s = 1.6  # 1024 x 422: one 1024 x 512 texture
    W, H = round(w * s), round(h * s)
    # as before 0.9 (the user's call): no Wall in the HUD Settings window
    t = glass(W, H, cuts={'tr': 10 * s, 'bl': 10 * s}, fill_a=246, edge_a=150, line=1.5, wall=None)
    t.rect(0, 10 * s, 1.4 * s, 34 * s, c(RED))
    return t.result()


def tagline(w=12, h=170):
    """Right edge of the main menu: 死神を恐れるな (don't fear the reaper) down the side, a hairline, the English."""
    s = 8
    t = Tex(w * s, h * s)
    W = w * s
    y = 2 * s
    for ch in '死神を恐れるな':
        t.text(W / 2, y, ch, ('jp7', 8.2 * s), c(RED, 220), 'mt')
        y += 10 * s
    t.line([(W / 2, y + 2 * s), (W / 2, y + 12 * s)], c(RED, 130), 0.25 * s)
    tw, th = int((h * s - y - 16 * s)), int(W)
    layer = Image.new('RGBA', (tw * 2, th * 2), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((0, layer.height / 2), "DON'T FEAR THE REAPER", font=font('mono', 4.2 * s * 2),
                               fill=c(GREY, 190), anchor='lm')
    layer = layer.rotate(-90, expand=True).resize((th * t.ss, tw * t.ss), Image.LANCZOS)
    t.im.alpha_composite(layer, (0, int((y + 16 * s) * t.ss)))
    return t.result()


def kanji_mark(txt='死神', w=64, h=128):
    t = Tex(w, h, 4)
    t.vtext(w / 2, 4, txt, ('jp9', w * 0.86), c(WHITE), w * 0.94)
    return t.result()


def speed_lines(w=1024, h=512, n=160, seed=3):
    """Behind the full-screen menus: thin vertical data streaks, white and crimson."""
    r = np.random.default_rng(seed)
    t = Tex(w, h, 1)
    for _ in range(n):
        x = r.uniform(0, w)
        y0 = r.uniform(-50, h)
        ln = r.uniform(20, 220)
        col = RED if r.random() < 0.6 else WHITE
        t.line([(x, y0), (x, y0 + ln)], c(col, int(r.uniform(40, 200))), r.choice([1, 1, 2]))
    return t.result()


def tone_tile(size=64, step=8):
    t = Tex(size, size, 1)
    t.rects([(x, y, x + 2, y + 2) for y in range(0, size, step) for x in range(0, size, step)], c(WHITE, 255))
    return t.result()


def scan_bar(w=1024, h=256):
    """A crimson scan bar across the menus (where Hueco Mundo had a spear of light)."""
    yy = np.linspace(-1, 1, h)[:, None]
    xx = np.linspace(0, 1, w)[None, :]
    a = np.exp(-(yy / 0.05) ** 2) * (0.25 + 0.75 * np.sin(xx * np.pi) ** 0.5) + np.exp(-(yy / 0.3) ** 2) * 0.18
    img = np.dstack([np.full((h, w), RED[0]), np.full((h, w), RED[1]), np.full((h, w), RED[2]),
                     np.clip(a, 0, 1) * 255])
    return Image.fromarray(img.astype(np.uint8), 'RGBA')


def layout_preview(scene, alt, cards, hover=False, w=512, h=288):
    """HUD Settings: one layout drawn small, the health card and the ammo card where they would be."""
    import ingame as G
    t = Tex(w, h, 1)
    t.paste(scene.resize((w, h), Image.LANCZOS), 0, 0, w, h)
    t.rect(0, 0, w, h, c(INK, 120))
    k = h / 480
    uw = w / k

    def ux(x):  # a corner-layout x resolved for this preview's layout (alt: the corners)
        v = x if alt else G.centred(x)
        if isinstance(v, int):
            return v
        return uw / 2 + int(v[1:]) if v.startswith('c') else uw - int(v[1:])
    if alt:  # MINMODE (minmode.py): the bare numbers on their fading plates, out either side of the crosshair
        import minmode as M
        mid = uw / 2
        hx, ax, y = mid + M.H_X, mid + M.A_X, M.MM_Y
        t.paste(M.plate('l', 'HP', '完全性'), hx * k, y * k, M.PLATE[0] * k, M.PLATE[1] * k)
        t.paste(M.plate('r', 'RDS', '弾薬'), ax * k, y * k, M.PLATE[0] * k, M.PLATE[1] * k)
        t.text((hx + M.PLATE[0] - 8) * k, (y + 24) * k, '142', ('raj7', 30 * k), c(WHITE), 'rm')
        t.text((ax + 52) * k, (y + 24) * k, '4', ('raj7', 30 * k), c(WHITE), 'rm')
        t.text((ax + 56) * k, (y + 28) * k, '/ 20', ('raj6', 11 * k), c(GREY), 'lm')
        if hover:
            t.outline([(1, 1), (w - 1, 1), (w - 1, h - 1), (1, h - 1)], c(RED), 4)
        return t.result()
    cx, cy, cw, ch = G.CARD
    cx = ux(cx)
    t.paste(cards['card'], cx * k, cy * k, cw * k, ch * k)
    px, py, pw, ph = G.at(G.PHOTO, (cx, cy))
    t.paste(cards['photo'], px * k, py * k, pw * k, ph * k)
    t.text((cx + G.LX) * k, (cy + 33) * k, '142', ('raj7', 40 * k), c(WHITE), 'lm')
    ax, ay, aw, ah = G.AMMO
    ax = ux('r%d' % ax)
    t.paste(cards['ammo'], ax * k, ay * k, aw * k, ah * k)
    t.text((ax + G.AMMO_DIGITS[2]) * k, (ay + 28) * k, '4', ('raj7', 40 * k), c(WHITE), 'rm')
    if hover:
        t.outline([(1, 1), (w - 1, 1), (w - 1, h - 1), (1, h - 1)], c(RED), 4)
    else:
        t.outline([(1, 1), (w - 1, 1), (w - 1, h - 1), (1, h - 1)], c(GREY_D), 2)
    return t.result()


def menu_background():
    """The menu scene (tools/art/menu_background.png), fitted to 16:9."""
    src = Image.open(os.path.join(ART, 'menu_background.png')).convert('RGB')
    w, h = src.size
    if abs(w / h - 16 / 9) > 0.01:
        if w / h > 16 / 9:
            nw = round(h * 16 / 9)
            src = src.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:
            nh = round(w * 9 / 16)
            src = src.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return src


def tf_emblem_mask(size, ss=4, tilt=6.7):
    """TF2's round emblem as an alpha mask, drawn the way the game's own logo panel draws it (CTFLogoPanel): four
    quarters of a ring, the hub 0.35 of its radius, the gaps 6 degrees either side at the rim (17 at the hub, so
    they run parallel), the whole turned 6.7 degrees."""
    S = size * ss
    m, R = S / 2, S * 0.4
    r = R * 0.35
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    for q in range(4):
        a0 = tilt + q * 90
        outer = [(m + R * np.cos(np.radians(a)), m - R * np.sin(np.radians(a)))
                 for a in np.linspace(a0 + 6, a0 + 84, 48)]
        inner = [(m + r * np.cos(np.radians(a)), m - r * np.sin(np.radians(a)))
                 for a in np.linspace(a0 + 90 - 6 / 0.35, a0 + 6 / 0.35, 24)]
        d.polygon(outer + inner, fill=255)
    return im.resize((size, size), Image.LANCZOS)


def cyber_emblem(size=256):
    """The game icon: TF2's emblem, so the game still reads as TF2 in the taskbar and on the desktop shortcut, in the
    HUD's cyberpunk look: crimson quarters lit from the top with scanlines and a bright rim, a neon glow, a cyan
    ghost knocked out of register, two glitch slices and targeting brackets in the corners."""
    S = size
    mask = np.asarray(tf_emblem_mask(S), np.float32) / 255
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S
    # crimson, hot at the top, deep at the foot; every third row a little darker
    t = np.clip((yy - 0.12) / 0.76, 0, 1)[..., None]
    col = np.array(HOT, np.float32) * (1 - t) + np.array(RED_DIM, np.float32) * t
    col *= np.where((np.arange(S) % 3 == 0)[:, None, None], 0.72, 1.0)
    # a bright rim: where the mask fades out, toward the light
    edge = np.clip(mask - np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(
        ImageFilter.MinFilter(max(3, S // 64 * 2 + 1))), np.float32) / 255, 0, 1)
    col = col * (1 - edge[..., None] * 0.8) + np.array((255, 214, 220), np.float32) * edge[..., None] * 0.8
    body = np.concatenate([col, mask[..., None] * 255], -1)
    body = Image.fromarray(np.clip(body, 0, 255).astype(np.uint8), 'RGBA')
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    # the glow
    glow = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(S * 0.035))
    g = Image.new('RGBA', (S, S), c(RED, 0))
    g.putalpha(glow.point(lambda v: min(255, int(v * 1.3))))
    out.alpha_composite(g)
    # the cyan ghost, a little to the left
    ghost = np.zeros((S, S, 4), np.float32)
    ghost[..., :3] = (40, 220, 255)
    ghost[..., 3] = mask * 150
    ghost = Image.fromarray(ghost.astype(np.uint8), 'RGBA')
    out.alpha_composite(ghost, (-round(S * 0.022), 0))
    # an ink outline, so it holds on a light desktop too
    ink = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(max(3, S // 85 * 2 + 1)))
    k = Image.new('RGBA', (S, S), c(INK, 0))
    k.putalpha(ink.point(lambda v: int(v * 0.9)))
    out.alpha_composite(k)
    out.alpha_composite(body)
    # two glitch slices, knocked sideways
    for y0, h, dx in ((0.34, 0.035, 0.035), (0.63, 0.022, -0.028)):
        box = (0, round(S * y0), S, round(S * (y0 + h)))
        sl = out.crop(box)
        clear = Image.new('RGBA', sl.size, (0, 0, 0, 0))
        out.paste(clear, box[:2])
        out.alpha_composite(sl, (round(S * dx), box[1]))
    # targeting brackets in the corners
    tb = Tex(S, S, 2)
    arm, w, p = S * 0.16, max(2.0, S * 0.022), S * 0.04
    tb.brackets(p, p, S - p, S - p, arm, c(RED, 235), w)
    out.alpha_composite(tb.result())
    return out


def app_icon(path):
    """The game's taskbar / desktop icon: TF2's emblem in the HUD's cyberpunk look (cyber_emblem). One 256x256
    entry: the engine takes the first image of resource/game.ico."""
    cyber_emblem(256).save(path, format='ICO', sizes=[(256, 256)])


# ---------------------------------------------------------------- the build
def hud_cards(out):
    import ingame
    ingame.textures(out)
    out.thumb('hp_fill', fill(RED), mips=False)
    out.thumb('hp_dead', fill(GREY_D), mips=False)
    for team in ('red', 'blue'):
        out.thumb(f'notice_{team}', notice_card(team))
        out.thumb(f'notif_{team}', notif_card(team))
        out.thumb(f'freeze_{team}', freeze_card(team))
        out.thumb(f'flatline_{team}', flatline_text(team), mips=False)
        out.thumb(f'stat_{team}', stat_card(team))
        out.thumb(f'bld_{team}', building_card(team))
    out.thumb('notif_ink', notif_card('ink'))
    out.thumb('streak_card', streak_card(), mips=False)
    out.thumb('countdown_card', countdown_card())
    # team=True: a BLU twin as well, for the pictures that follow the local player's team (ingame.timg)
    out.thumb('notice_rule', rule(512, 32, thick=6), team=True)
    for name, txt in (('goal', '任務'), ('switch', '移籍'), ('alert', '警告')):
        out.thumb('seal_' + name, seal(txt, 224, 256), team=True)
    for kind, ch in BUILDING_KANJI.items():
        out.thumb('bld_k_' + kind, building_kanji(ch))
    out.thumb('hitmarker', hitmarker(), team=True)
    out.thumb('respawn_card', respawn_card())
    out.thumb('spec_bar_top', spec_bar('bottom'))
    out.thumb('popup_head', popup_head())
    out.thumb('spec_bar_bot', spec_bar('top'))
    out.thumb('menu_bg', menu_bg(), team=True)
    for state in MENU_TONES:
        out.thumb('menu_item_' + state, menu_item(state), team=True)
    out.thumb('menu_key', menu_key())
    out.thumb('disguise_card', notif_card('ink'))
    out.thumb('escort_strip', escort_strip(), team=True)
    out.thumb('cp_rim', cp_rim(), team=True)
    out.thumb('intel_card', intel_card())
    out.thumb('ctf_bar', ctf_bar())
    out.thumb('top_band', top_band())
    out.thumb('portrait_frame', portrait_frame(), mips=False)


def objective_icons(out, pdir):
    """Control point and CTF flag art; the stock materials are redirected here by vmt overrides (build.py)."""
    from vtfread import read_vtf
    src = os.path.join(pdir, 'materials', 'sprites', 'obj_icons')
    for f in sorted(glob.glob(os.path.join(src, 'icon_obj_*.vtf'))):
        name = os.path.basename(f)[:-4]
        if not any(t in name for t in ('_blu', '_red', '_neutral')) or 'cap_' in name or 'mannhattan' in name:
            continue
        team = 'blue' if '_blu' in name else 'red' if '_red' in name else 'neutral'
        out.thumb('obj/' + name, cp_icon(read_vtf(f), team))
    hud = os.path.join(pdir, 'materials', 'hud')
    for name in ('blue', 'red', 'grey', 'grey_with_red'):
        team = name if name in ('blue', 'red') else ('ink' if name == 'grey' else 'red')
        out.thumb(f'obj/objectives_flagpanel_compass_{name}', ring(team, pointer=True))
        if name in ('blue', 'red'):
            out.thumb(f'obj/objectives_flagpanel_compass_{name}_noarrow', ring(team))
    for g in ('home', 'home_alt', 'dropped', 'moving', 'moving_alt'):
        p = os.path.join(hud, f'objectives_flagpanel_ico_flag_{g}.vtf')
        if os.path.exists(p):
            out.thumb(f'obj/objectives_flagpanel_ico_flag_{g}', glyph(read_vtf(p)))
    p = os.path.join(hud, 'objectives_flagpanel_briefcase.vtf')
    if os.path.exists(p):
        out.thumb('obj/objectives_flagpanel_briefcase', briefcase(read_vtf(p)))
    payload_icons(out)


HUB_W = 644                  # units: the loadout hub's sections, as wide as its row of nine class cards


def hub_art(out):
    """The loadout hub (the inventory's first page): a strip over each section (number, name, rule), the glass frame
    behind the class cards and a tile behind each of the five page buttons."""
    w = HUB_W * 2
    for key, num, label, jp, note in (('roster', '01', 'OPERATIVES', '兵科', 'SELECT A CLASS TO EDIT ITS LOADOUT'),
                                      ('systems', '02', 'SYSTEMS', 'システム', 'SOUL HARVEST DIVISION  //  ARMORY')):
        t = Tex(w, 28, 2)
        t.rect(0, 7, 10, 17, c(RED))
        t.text(20, 12, f'{num}  //  {label}', ('mono', 18), c(WHITE), 'lm')
        t.text(40 + 11 * len(f'{num}  //  {label}'), 12, jp, ('jp5', 16), c(GREY), 'lm')
        t.text(w - 2, 12, note, ('mono', 14), c(GREY, 170), 'rm')
        t.rect(0, 24, 64, 27, c(RED))
        t.rect(64, 25, w, 26, c(RED, 130))
        out.thumb(f'hub_strip_{key}', t.result())
    h = 268
    t = glass(w, h, cuts={'tl': 22, 'br': 22}, fill_a=150, edge_a=80)
    t.brackets(8, 8, w - 8, h - 8, 20, c(WHITE, 110), 2)
    for i in range(0, w - 60, 23):                       # a ruler along the foot
        t.rect(30 + i, h - 12, 31 + i, h - (5 if i % 115 else 2) - 2, c(RED, 150 if i % 115 == 0 else 70))
    out.thumb('hub_frame', t.result())
    tw, th = 224, 176
    for i in range(1, 6):
        t = glass(tw, th, cuts={'br': 18}, fill_a=205, edge_a=110)
        t.rect(10, 12, 18, 20, c(RED))
        t.text(26, 16, '%02d' % i, ('mono', 20), c(RED), 'lm')
        t.text(tw - 12, 16, 'SYS', ('mono', 16), c(GREY), 'rm')
        t.brackets(44, 30, tw - 44, th - 46, 14, c(WHITE, 150), 2)
        t.rect(2, th - 40, tw - 2, th - 39, c(RED, 110))
        out.thumb(f'hub_tile_{i}', t.result())


def portrait_cards(out, pdir):
    """Class / team / loadout cards, from the game's own class portraits in the hologram duotone."""
    from vtfread import read_vtf

    def tex(rel):
        return read_vtf(os.path.join(pdir, 'materials', rel + '.vtf'))

    for btn, por, sel, num, lbl, kana in CLASSES:
        fig = tex(f'vgui/class_sel_sm_{sel}_red')
        out.thumb(f'inv_{btn}', tall_card(fig, num, kana, label_txt=lbl))
        out.thumb(f'inv_{btn}_a', tall_card(fig, num, kana, active=True, label_txt=lbl))
    # the class select's code matrix: one cell per class, and the wide RANDOM one under them
    for btn, por, sel, num, lbl, kana in CLASSES + [('random', 'silhouette', 'random', 0, 'RANDOM', 'ランダム')]:
        fig = tex(f'vgui/class_portraits/{por}')  # the large bust, not the small class-select figure
        for sfx, lit in (('', False), ('_h', True)):
            # the resting cell also in azure (b/): the class select follows the player's team
            out.thumb(f'cs_cell_{btn}{sfx}', matrix_cell(fig, CELL_CODES[btn], num, lbl, kana, lit,
                                                         *(RANDOM_CELL if btn == 'random' else CELL)), team=not lit)
    for team, name in (('blue', 'blu'), ('red', 'red')):
        out.thumb(f'team_tag_{name}', team_tag(team))
        out.thumb(f'team_tag_{name}_h', team_tag(team, hover=True))


def menu_art(out):
    import screens
    scene = menu_background()
    out.console('background_reaper_widescreen', scene.resize((2048, 1024), Image.LANCZOS))
    sq = scene.crop(((scene.width - scene.height) // 2, 0, (scene.width + scene.height) // 2, scene.height))
    out.console('background_reaper', sq.resize((1024, 1024), Image.LANCZOS))
    out.thumb('logo', logo())
    out.thumb('emblem', logo(compact=True))
    import menu
    menu.art(out)
    menu.screen_art(out)
    import loadout
    loadout.art(out)
    import extras
    extras.art(out)
    import blackwall
    blackwall.art(out)
    out.thumb('popup', popup_bg(screens.POPUP_W, screens.POPUP_H))
    import ingame
    cards = {'photo': ingame.tex_photo_bg(), 'card': ingame.tex_health(), 'ammo': ingame.tex_ammo()}
    for name, alt in (('layout_centred', False), ('layout_minmode', True)):
        out.thumb(name, layout_preview(scene, alt, cards))
        out.thumb(name + '_h', layout_preview(scene, alt, cards, hover=True))
    out.thumb('score_blue', banner('blue'))
    out.thumb('score_red', banner('red', mirror=True))
    out.thumb('score_main', score_main())
    out.thumb('rule_v', rule_v(), mips=False)
    out.thumb('win_page', win_page())
    out.thumb('search_bar', search_bar())
    out.thumb('search_field', search_bar(chip=False))
    out.thumb('craft_list', craft_card(512, 614))
    out.thumb('craft_recipe', craft_card(512, 586, band=0.14))
    out.thumb('craft_chip', craft_chip())


def build(root, preview=None, portraits=None):
    out = Out(root, preview)
    generic(out)
    hud_cards(out)
    menu_art(out)
    if portraits:
        objective_icons(out, portraits)
        portrait_cards(out, portraits)
    hub_art(out)
    os.makedirs(os.path.join(root, 'resource'), exist_ok=True)
    app_icon(os.path.join(root, 'resource', 'game.ico'))
