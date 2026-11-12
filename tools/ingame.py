"""In-game HUD of the Reaper HUD, laid out element for element from docs/style-ingame.jpg.

Every box here is the style preview's own pixel box at 1920 x 1080 (tools/style/preview_game.py) turned into HUD units
(480 units = the screen's height, so 2.25 px per unit at 1080p). The card textures are drawn with the preview's own
shapes, fonts and colours at those sizes, so the game shows the preview's pixels; what the game draws itself (digits,
names, bars, the 3D model) goes into the boxes and fonts the preview gives it.

What the game cannot do the preview's way is said where it happens (search for "game:").
"""
import math
import os
import zlib

import numpy as np
from PIL import Image

import kv
from build_art import Tex, c, chamfer, linear_alpha, to_blue, PANEL, RED, HOT, RED_DIM, WHITE, GREY, INK

PX = 2.25                    # screen pixels per HUD unit at 1080p
T = 'replay/thumbnails/rk/'
TEAM_RED, TEAM_BLU = (255, 120, 104), (112, 164, 232)
PANEL_A = 226                # the preview's glass (214 over its darkened shot) reads the same over the live game at 226
# the health and ammo cards are opaque, in the dark the glass showed over the usual floor and walls in game: so the
# pieces of the card over the gauge's sides and the digits' sheets match the card exactly whatever is behind it
CARD_FILL = (18, 18, 22)


def u(px):
    return int(round(px / PX))


# ------------------------------------------------------------------ fonts
# vgui asks Windows for a font whose cell (win ascent + descent) is the scheme's "tall", so a font's em is its cell
# over this ratio; text sits in the middle of its label with the baseline `ascent` down the cell
METRICS = {'Rajdhani': (1.276, 930 / 1276), 'Rajdhani SemiBold': (1.276, 930 / 1276),
           'Share Tech Mono': (1.127, 885 / 1127), 'Bahnschrift SemiCondensed': (1.207, 0.8)}


def em(family, tall):
    """Glyph size in px at 1080p of a scheme font this tall."""
    return int(tall * PX) / METRICS[family][0]


def top_for_baseline(family, tall, baseline_px):
    """Top (px) of a label exactly one cell tall whose text baseline lands on baseline_px."""
    return baseline_px - int(tall * PX) * METRICS[family][1]


def font_block(name, tall, weight=400, **extra):
    keys = dict(name=name, tall=tall, weight=weight, additive=0, antialias=1, italic=0, outline=0, dropshadow=0)
    keys.update(extra)
    return [['1', [[k, str(v), None] for k, v in keys.items()], None]]


DIGITS_T = 44     # health / ammo digits: the preview's 78 px Rajdhani Bold
MAXNUM_T = 14     # "/ 200": 24 px Rajdhani SemiBold
RESERVE_T = 16    # "/ 20": 28 px
FONTS = {
    'RK_Digits': font_block('Rajdhani', DIGITS_T, 700),
    # the soft red bloom under the digits (the preview's glow): the same digits blurred, drawn additively
    'RK_DigitsGlow': font_block('Rajdhani', DIGITS_T, 700, blur=4, additive=1),
    # the cyan copy of the digits a unit to the right (the red one is the ghost to the left): added, not drawn over
    'RK_DigitsSplit': font_block('Rajdhani', DIGITS_T, 700, additive=1),
    'RK_MaxNum': font_block('Rajdhani SemiBold', MAXNUM_T, 600),
    'RK_ReserveNum': font_block('Rajdhani SemiBold', RESERVE_T, 600),
    'RK_StreakNum': font_block('Rajdhani', 9, 700),           # "03": 16 px
    'RK_StripNum': font_block('Rajdhani', 11, 700),
    'RK_UberNum': font_block('Rajdhani', 15, 700),            # the Über card's percent: 44 px           # counts on the meter strips: 19 px
    'RK_StripLabel': font_block('Share Tech Mono', 6, 400),   # the game's meter names: 12 px mono
    # target ID: its card is mostly see-through, so the lettering carries a shadow of its own
    'RK_TidName': font_block('Bahnschrift SemiCondensed', 11, 600, dropshadow=1),   # the name: 20 px
    'RK_TidData': font_block('Share Tech Mono', 5, 400, dropshadow=1),              # its second line: 10 px mono
    'RK_TidHealth': font_block('Rajdhani', 15, 700, outline=1),        # the health chip's number: 26 px
    # kill feed names: the condensed bold cut of Bahnschrift, 24 px, tighter and harder than the menu face. The HUD's
    # own faces (Rajdhani, Share Tech Mono) have no Cyrillic, and names in it would come out as boxes
    'RK_Feed': font_block('Bahnschrift SemiBold Condensed', 11, 700),
    'RK_Timer': font_block('Rajdhani', 18, 700),                      # round timer: 32 px
    'RK_TimerHalf': font_block('Rajdhani', 12, 700),                  # KOTH in a match: two times in one box
    'RK_TopScore': font_block('Rajdhani', 15, 700, outline=1),        # CTF scores in the timer box: 34 px
    'RK_SlotTime': font_block('Rajdhani', 7, 700, outline=1),         # respawn seconds on a teammate's slot
    'RK_Damage': font_block('Rajdhani', 14, 700, outline=1),          # damage numbers: 24 px
    'RK_DamageBig': font_block('Rajdhani', 17, 700, outline=1),       # 30 px
    'ChatFont': font_block('Bahnschrift SemiCondensed', 9, 600, dropshadow=1),   # chat: 17 px with a shadow
}
import minmode  # noqa: E402  the MINMODE layout (cl_hud_minmode 1)
FONTS.update(minmode.fonts(font_block))


# ------------------------------------------------------------------ drawing in screen pixels
class Px:
    """A texture for a box wu x hu HUD units, drawn in 1080p screen pixels (the preview's coordinates) at k texture
    pixels per screen pixel."""

    def __init__(self, wu, hu, k=2.0):
        self.W, self.H, self.k = wu * PX, hu * PX, k
        self.t = Tex(max(1, round(self.W * k)), max(1, round(self.H * k)), ss=2)

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def poly(self, pts, fill):
        self.t.poly(self._p(pts), fill)

    def outline(self, pts, fill, width=1.0):
        self.t.outline(self._p(pts), fill, width * self.k)

    def line(self, pts, fill, width=1.0):
        self.t.line(self._p(pts), fill, width * self.k)

    def rect(self, x0, y0, x1, y1, fill):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill)

    def rects(self, boxes, fill):
        k = self.k
        self.t.rects([(a * k, b * k, x * k, y * k) for a, b, x, y in boxes], fill)

    def text(self, x, y, s, fnt, fill, anchor='la', spacing=0.0):
        return self.t.text(x * self.k, y * self.k, s, (fnt[0], fnt[1] * self.k), fill, anchor, spacing * self.k) / self.k

    def width(self, s, fnt):
        return self.t.width(s, (fnt[0], fnt[1] * self.k)) / self.k

    def mixed(self, x, y, runs, anchor='lm'):
        if anchor[0] == 'r':
            x -= sum(self.width(t, f) for t, f, _ in runs)
        for t, f, col in runs:
            x += self.text(x, y, t, f, col, 'l' + anchor[1])
        return x

    def dots(self, x0, y0, x1, y1, color, alpha, step=4):
        self.rects([(x, y, x + 1, y + 1) for y in range(int(y0) + 2, int(y1) - 1, step)
                    for x in range(int(x0) + 2, int(x1) - 1, step)], c(color, alpha))

    def scan(self, x0, y0, x1, y1, color, alpha, step=3):
        self.rects([(x0, y, x1, y + 1) for y in range(int(y0), int(y1), step)], c(color, alpha))

    def hatch(self, x0, y0, x1, y1, color, alpha, step=6, width=2.0):
        k = self.k
        self.t.hatch(x0 * k, y0 * k, x1 * k, y1 * k, color, alpha, step * k, width * k)

    def brackets(self, x0, y0, x1, y1, arm, color, width=1.0):
        k = self.k
        self.t.brackets(x0 * k, y0 * k, x1 * k, y1 * k, arm * k, color, width * k)

    def result(self):
        return self.t.result()


# Beyond the Wall: the HUD's crimson is torn by the wall's light, a red copy to the left and a cyan one to the right
SPLIT_R = (255, 20, 60)
SPLIT_C = (0, 214, 255)


def scan_in(p, pts, color, alpha, step=3):
    """Scan lines across a convex shape, each clipped to it."""
    ys = [y for _, y in pts]
    for y in np.arange(min(ys) + 1, max(ys) - 1, step):
        xs = []
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            if (ay - y) * (by - y) <= 0 and ay != by:
                xs.append(ax + (bx - ax) * (y - ay) / (by - ay))
        if len(xs) >= 2:
            p.rect(min(xs) + 1, y, max(xs) - 1, y + 1, c(color, alpha))


def torn(p, pts, seed=1, col=RED, a=150, split=True, gaps=0.22, seg=46, node=2.0):
    """The HUD's hairline round a shape, bitten in places, with a faint red copy left of it and a cyan one right of
    it, and a node on every corner."""
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
                p.line([(p0[0] - 1.5, p0[1]), (p1[0] - 1.5, p1[1])], c(SPLIT_R, 70), 1)
                p.line([(p0[0] + 1.5, p0[1]), (p1[0] + 1.5, p1[1])], c(SPLIT_C, 45), 1)
            p.line([p0, p1], c(col, a), 1)
    for (x, y) in pts:
        p.rect(x - node, y - node, x + node, y + node, c(col))


def tears(p, x0, y0, x1, y1, n=4, seed=1, col=HOT, alpha=170):
    """Glitch tears: thin bars of crimson and white with a cyan sliver under some (flickered in game; nothing under
    them moves)."""
    r = np.random.default_rng(seed)
    for _ in range(n):
        y = r.uniform(y0, y1)
        h = r.choice([1, 1.5, 2, 2, 3, 4])
        lo = min(24, (x1 - x0) * 0.3)
        xa = r.uniform(x0, x1 - lo)
        w = r.uniform(lo, max(lo + 1, (x1 - x0) * 0.55))
        p.rect(xa, y, min(x1, xa + w), y + h, c(col if r.random() < 0.65 else WHITE, alpha * r.uniform(0.45, 1.0)))
        sx0, sx1 = xa + r.uniform(2, 10), min(x1, xa + w * r.uniform(0.2, 0.6))
        if r.random() < 0.6 and sx1 > sx0 + 1:
            p.rect(sx0, y + h, sx1, y + h + 1, c(SPLIT_C, 110))


def static_bits(p, x0, y0, x1, y1, seed=3, density=0.35, col=RED, cell=2.0):
    """A patch of the wall's static: short runs of cells at random strengths."""
    r = np.random.default_rng(seed)
    boxes = {}
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            if r.random() < density:
                w = cell * r.choice([1, 1, 2, 3, 5])
                a = int(r.uniform(60, 240)) // 30 * 30
                boxes.setdefault(a, []).append((x, y, min(x1, x + w), y + cell))
                x += w
            x += cell
        y += cell
    for a, bs in boxes.items():
        p.rects(bs, c(col, a))


def signal_bars(p, x, y, col=RED, lit=4):
    """SIG and five rising bars: the card's link to the wall."""
    p.text(x, y, 'SIG', ('mono', 9), c(GREY), 'lm')
    for i in range(5):
        h = 3 + i * 2
        p.rect(x + 22 + i * 5, y + 5 - h, x + 25 + i * 5, y + 5, c(col if i < lit else (66, 64, 70)))


def dot_screen(p, x0, y0, x1, y1, cell=3.0, alpha=120):
    """A dot-matrix screen over a picture the game draws (the live model, a class portrait): dark between round
    windows, so what shows through reads as dots."""
    im = p.t.im
    s = im.width / p.W                       # internal px per screen px
    X0, Y0, X1, Y1 = (int(round(v * s)) for v in (x0, y0, x1, y1))
    hh, ww = Y1 - Y0, X1 - X0
    cs = cell * s
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    dx = (xx % cs) - cs / 2 + 0.5
    dy = (yy % cs) - cs / 2 + 0.5
    hole = np.clip(1.2 - np.sqrt(dx * dx + dy * dy) / (cs * 0.46), 0, 1)
    layer = np.zeros((hh, ww, 4), np.uint8)
    layer[..., 3] = np.clip((1 - hole) * alpha, 0, 255).astype(np.uint8)
    im.alpha_composite(Image.fromarray(layer, 'RGBA'), (X0, Y0))


def glass(p, x0, y0, x1, y1, cut=None, cut_px=14, alpha=PANEL_A, edge=150, texture=True, seed=1, fill=PANEL,
          wall='right'):
    """Black glass with faint scan lines, one cut corner and the torn crimson hairline (torn)."""
    cuts = {cut: cut_px} if cut else {}
    shape = chamfer(x0, y0, x1, y1, **cuts)
    p.poly(shape, c(fill, alpha))
    if texture:
        scan_in(p, shape, WHITE, 10)
    if wall and (x1 - x0) >= 150 and (y1 - y0) >= 40:
        wall_in(p, shape, x0, y0, x1, y1, wall)
    inner = {k: max(0.0, v - 0.5) for k, v in cuts.items()}
    torn(p, chamfer(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5, **inner), seed=seed, a=min(255, edge + 50))
    # the cut corner hot
    for key, (cx, cy, dx, dy) in (('tl', (x0, y0, 1, 1)), ('tr', (x1, y0, -1, 1)), ('br', (x1, y1, -1, -1)),
                                  ('bl', (x0, y1, 1, -1))):
        k = cuts.get(key, 0)
        if k:
            p.line([(cx + dx * (k + 22), cy + dy * 0.8), (cx + dx * k, cy + dy * 0.8), (cx + dx * 0.8, cy + dy * k),
                    (cx + dx * 0.8, cy + dy * (k + 22))], c(HOT, 255), 1.6)


def wall_in(p, shape, x0, y0, x1, y1, side='right', strength=0.5):
    """The Blackwall's pattern (build_art.wall_texture) inside a shape, fading in towards one side."""
    from build_art import wall_texture
    from PIL import ImageChops, ImageDraw
    im = p.t.im
    s = p.k * p.t.ss
    X0, Y0, X1, Y1 = (int(round(v * s)) for v in (x0, y0, x1, y1))
    ww, hh = max(1, X1 - X0), max(1, Y1 - Y0)
    pat = wall_texture().resize((ww, hh), Image.BICUBIC)
    ramp = Image.new('L', (ww, 1))
    px = ramp.load()
    for x in range(ww):
        f = x / max(1, ww - 1)
        px[x, 0] = int(255 * strength * (f if side == 'right' else 1 - f) ** 1.3)
    clip = Image.new('L', (ww, hh), 0)
    ImageDraw.Draw(clip).polygon([((px_ * s) - X0, (py_ * s) - Y0) for px_, py_ in shape], fill=255)
    pat.putalpha(ImageChops.multiply(ImageChops.multiply(pat.split()[3], ramp.resize((ww, hh))), clip))
    im.alpha_composite(pat, (X0, Y0))


_TABLE = []


def wall_glyphs(p, x, y, n, size=18, seed=1, color=RED, alpha=235, step=None):
    """A row of the Blackwall's own glyphs (Cyberpunk 2077's blackwall_character_table, an 8 x 8 sheet), n of them
    from (x, y) in the painter's pixels; the same ones every build."""
    if not _TABLE:
        _TABLE.append(Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'art', 'cp2077',
                                              'blackwall_character_table.png')).convert('L'))
    s = p.k * p.t.ss
    px = max(1, round(size * s))
    for i in range(n):
        v = zlib.crc32(('%d|%d' % (seed, i)).encode())
        col, row = v % 8, 2 + (v >> 5) % 6
        g = _TABLE[0].crop((col * 64, row * 64, col * 64 + 64, row * 64 + 64)).resize((px, px), Image.LANCZOS)
        im = Image.new('RGBA', (px, px), color + (0,))
        im.putalpha(g.point(lambda q: int(q * alpha / 255)))
        p.t.im.alpha_composite(im, (round((x + i * (step or size + 2)) * s), round(y * s)))


def tag_label(p, x, y, en, jp=None, color=RED):
    """ui_kit.label: ■ 体力 // HEALTH."""
    p.rect(x, y - 3.5, x + 7, y + 3.5, c(color))
    runs = []
    if jp:
        runs += [(jp, ('jp5', 11), c(color)), ('  //  ', ('mono', 11), c(color, 150))]
    runs.append((en, ('mono', 12), c(color)))
    return p.mixed(x + 13, y, runs)


def vsegs(p, x0, y0, x1, y1, n, color, alpha, gap=2.0):
    h = (y1 - y0 - gap * (n - 1)) / n
    p.rects([(x0, y1 - i * (h + gap) - h, x1, y1 - i * (h + gap)) for i in range(n)], c(color, alpha))


def hsegs(p, x0, y0, x1, y1, n, color, alpha, gap=2.0):
    w = (x1 - x0 - gap * (n - 1)) / n
    p.rects([(x0 + i * (w + gap), y0, x0 + i * (w + gap) + w, y1) for i in range(n)], c(color, alpha))


def mul_texture(wu, hu, n, vertical=False, gap=2.0, k=4.0, thirds=False):
    """Modulate sheet for a bar the game paints white: crimson windows (white x crimson = the preview's crimson, the
    grey track goes deep crimson) with black gaps between n segments. Opaque: the shader only multiplies.
    thirds: the sheet is three times the bar's width and only its middle third has windows (see GAUGE_FILL)."""
    p = Px(wu, hu, k)
    p.rect(0, 0, p.W, p.H, c((0, 0, 0)))
    x0, x1 = (p.W / 3, p.W * 2 / 3) if thirds else (0, p.W)
    (vsegs if vertical else hsegs)(p, x0, 0, x1, p.H, n, RED, 255, gap)
    return p.result()


# ------------------------------------------------------------------ geometry
# health card: the preview's (56, 818)-(476, 964); everything inside is placed from the card's top-left in units
CARD = (25, 364, 187, 65)
PHOTO = (4, 4, 55, 57)                        # the portrait, 8 px in
LX = 65                                       # the text column (preview x0 + 146)
DIGITS = (LX, u(top_for_baseline('Rajdhani', DIGITS_T, 102)), 57, DIGITS_T)      # "142": baseline 102 px down
SLASH_W = 5                                   # "/" column of the slash borders
MAX_X = u(274)                                # "/ 200" starts 128 px right of the digits
MAX_TOP = u(top_for_baseline('Rajdhani SemiBold', MAXNUM_T, 100))
MAX_NUM_X = u(274 + 15.84)                    # the number after "/ " (Rajdhani SemiBold 24.7 px: "/ " = 15.8 px)
GAUGE = (176, 14, 5, 44)                      # (396, 32)-(408, 132) px: 16 segments
# game: the health fill is the material hud/health_color, which sv_pure servers (Valve's) keep stock: a cross. So the
# fill panel is three gauges wide, centred on the gauge: the middle third, the cross's upright, is a straight bar on
# every server, and the outer thirds (the cross's arms; our own plain fill there off Valve's servers) are covered by
# two opaque pieces of the card cut from the card's own art (GAUGE_SIDES), so they vanish into it. The gauge's Modulate
# sheet covers the gauge alone: lit segments in the team's colour, the unlit ones dim, thin black gaps; no box round it
GAUGE_FILL = (GAUGE[0] - GAUGE[2], GAUGE[1], GAUGE[2] * 3, GAUGE[3])
# the pieces either side are pinned to the gauge's sheet (pin_to_sibling): vgui cuts every position and size to whole
# pixels on its own, and a piece placed by its own numbers could stop a pixel short of the gauge and let a line of
# the fill through. The left one reaches 2 units past the fill, the right one to the card's edge
GAUGE_SIDES = {'l': (GAUGE[0] - GAUGE[2] - 2, GAUGE[1], GAUGE[2] + 2, GAUGE[3]),
               'r': (GAUGE[0] + GAUGE[2], GAUGE[1], CARD[2] - GAUGE[0] - GAUGE[2], GAUGE[3])}
# the digits' bloom and their offset ghost are drawn white, and a Modulate sheet in the team's colour over them (under
# the white digits) turns them crimson on RED and azure on BLU: labels cannot change colour with the team, pictures
# can. Round its core it fades to white (no change). Multiplied, the dark card round the digits would go near black
# too, a dark box behind them; an additive sheet over the same box first adds back what the multiply takes from the
# card (tex_team_add), so the card looks the same under it and only the white lettering takes the colour
DIGITS_MUL = (60, 14, 127 - 60, 54 - 14)      # card-local units: the bloom and ghost of up to three digits
DIGITS_FEATHER = (2, 5, 6, 6)                 # left (the portrait is close), top, right, bottom
STREAK = (LX, 52, 104, 9)                     # the 撃破 STREAK 03 row, centred 18 px over the card's foot
STREAK_NUM_X = u(24.47 + 38.91 + 7.03)        # after "撃破 " (jp 11) + "STREAK" (mono 12) + "  " (Rajdhani 16)
# ammo card: (1508, 856)-(1864, 964), 56 px from the right edge
AMMO = (183, 380, 158, 48)                    # xpos is from the right edge
AMMO_DIGITS = (0, u(top_for_baseline('Rajdhani', DIGITS_T, 92)), u(238), DIGITS_T)   # right edge 118 px in from the card's
RES_X = u(250)                                # "/ 20" 106 px in from the card's right edge
RES_TOP = u(top_for_baseline('Rajdhani SemiBold', RESERVE_T, 90))
RES_NUM_X = u(250 + 18.09)
AMMO_NOCLIP_DX = 18                             # see patch_ammo
AMMO_DIGITS_MUL = (46, 10, 110 - 46, 48 - 10)  # the team sheet over the clip's bloom and ghost (see DIGITS_MUL)
AMMO_FEATHER = (7, 5, 2, 5)                     # left, top, right ("/ 20" is close), bottom
# item meter strip: (1612, 818)-(1864, 848); more meters stack up from it
STRIP = (137, 364, 112, 13)
STRIP_STEP = 15
STRIP_LABEL = (5, 4, 40, 6)
STRIP_BAR = (46, 5, 60, 4)                    # (104, 11)-(240, 19) px: 22 segments
STRIP_NUM = (46, 1, 60, 11)
STRIP_COUNT = (0, 1, 112, 11)                 # a strip's count (stickies, metal, revenge...): centred on the strip
CENTER = ('c-56', 340)                        # MINMODE: sticky / ÜberCharge centred between the plates (minmode.MM_Y)
CHARGE_H = 4                                  # the charge-up bar under the centre strip, as long as the strip
# target ID: (806, 600)-(1114, 648)
TID_Y, TID_H = u(600), u(48)
# Two layouts, picked in HUD Settings (cl_hud_minmode). The boxes above are the preview's: the cards in the bottom
# corners, the old CORNERS layout; since 0.9 the *_minmode keys hold MINMODE instead (minmode.py). The default, CENTRED, pulls both cards in toward the
# crosshair, their inner edges INNER units either side of the screen's centre, at the same height (plain keys). As in
# the Hueco Mundo HUD: health from c-347 to c-160, ammo from c160 to c318 (Hueco's blocks span c-365..c-159 and
# c188..c318), clear of the payload bar (c-149..c149) and the CTF rings between them.
INNER = 160
# In CENTRED the two cards sit on one line, their middles at CENTRE_LINE (the corner layout keeps the preview's: both
# cards' feet on its bottom line), low like Hueco's (its health box centred at 381, ammo's foot at 410) and above
# the objective strip at the bottom; the centre strip sits on the same line between them. At 396 the health card is as
# high as in the corner layout (386 read as too high in the game); a Spy's disguise card under it stays clear.
CENTRE_LINE = 396
HEALTH_DY = round(CENTRE_LINE - (CARD[1] + CARD[3] / 2))
AMMO_DY = round(CENTRE_LINE - (AMMO[1] + AMMO[3] / 2))


# ------------------------------------------------------------------ textures
def tex_health():
    x, y, w, h = CARD
    p = Px(w, h)
    # opaque and even (CARD_FILL): the pieces either side of the gauge are cut from it and the digits' sheets are
    # worked out for it, so neither shows as a box
    glass(p, 0, 0, p.W, p.H, cut='tr', cut_px=18, seed=11, alpha=255, fill=CARD_FILL, texture=False)
    tag_label(p, LX * PX, 18, 'INTEGRITY', '完全性')
    # game: the HUD is not told the player's class; the corner carries the card's link to the wall instead
    signal_bars(p, p.W - 92, 18)
    # the gauge's unlit segments: the gauge's sheet multiplies them into dim slots of the team's colour; the fill
    # (white under the sheet) covers them as it rises
    gx, gy, gw, gh = (v * PX for v in GAUGE)
    vsegs(p, gx, gy, gx + gw, gy + gh, 16, WHITE, 70)
    lx = LX * PX
    p.line([(lx, p.H - 32), (lx + 120, p.H - 32)], c(RED, 70), 1)
    p.line([(lx + 134, p.H - 32), (p.W - 40, p.H - 32)], c(RED, 70), 1)
    wall_glyphs(p, p.W - 132, p.H - 27, 4, 16, seed=41)    # the wall's glyphs at the foot, right of the streak
    return p.result()


def tex_critical():
    """Near death (HudHealthDyingPulse flickers it in): the wall breaks into the health card. A hot glow inside its
    outline, static and tears over it, the label struck out by INTEGRITY CRITICAL. In the team's colour (a team
    picture): crimson on RED, azure on BLU."""
    x, y, w, h = CARD
    p = Px(w, h)
    p.t.im.alpha_composite(tex_flash(w, h, HOT, 'tr').resize(p.t.im.size, Image.LANCZOS))
    static_bits(p, 4, 4, p.W - 4, p.H - 4, seed=71, density=0.05, col=HOT, cell=1.5)
    tears(p, 0, 30, p.W, p.H - 10, n=9, seed=73)
    lx = LX * PX
    # the warning over the card's label (all of it), short of its SIG meter (p.W - 92), which stays as it is
    label_end = lx + 13 + sum(p.width(t, f) for t, f in (('完全性', ('jp5', 11)), ('  //  ', ('mono', 11)),
                                                         ('INTEGRITY', ('mono', 12))))
    for size, txt in ((12, '  //  INTEGRITY CRITICAL'), (11, '  //  INTEGRITY CRITICAL'), (10, '  //  INTEGRITY CRITICAL'),
                      (12, '  //  CRITICAL')):
        runs = [('警告', ('jp9', 11), c(INK)), (txt, ('mono', size), c(INK))]
        end = lx + 6 + sum(p.width(t, f) for t, f, _ in runs) + 8
        if end <= p.W - 100:
            break
    p.rect(lx - 2, 9, max(end, label_end + 6), 27, c(HOT))
    p.mixed(lx + 6, 18, runs, 'lm')
    return gauge_hole(p.result())


def gauge_hole(im):
    """A health card overlay (near death, overheal) with the gauge cut out of it: it covers the card round the
    gauge, the pieces either side included, and the gauge itself stays clear."""
    k = im.width / CARD[2]
    x, y, w, h = GAUGE
    a = np.asarray(im, np.uint8).copy()
    a[max(0, round((y - 0.5) * k)):round((y + h + 0.5) * k), max(0, round((x - 0.5) * k)):round((x + w + 0.5) * k), 3] = 0
    return Image.fromarray(a, 'RGBA')


def tex_edge_danger():
    """Near death, over the whole screen (stretched from 1024 x 512): the wall seeping in at the edges, a red
    vignette with streaks of static along the left and right edges and rows of it at the top and bottom."""
    w, h = 1024, 512
    x = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    y = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    d = np.clip((np.maximum(np.abs(x), np.abs(y) * 1.05) - 0.76) / 0.24, 0, 1) ** 1.8
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = RED_DIM
    img[..., 3] = d * 150
    out = Image.fromarray(img.astype(np.uint8), 'RGBA')
    t = Tex(w, h, ss=1)
    t.im.alpha_composite(out)
    r = np.random.default_rng(5)
    for _ in range(60):
        yy = r.uniform(0, h)
        ln = r.uniform(12, 80)
        hh = r.choice([1, 1, 2, 3])
        xx = r.uniform(0, 22) if r.random() < 0.5 else w - r.uniform(0, 22) - ln
        t.rect(xx, yy, xx + ln, yy + hh, c(HOT if r.random() < 0.3 else RED, r.uniform(70, 210)))
    for y0 in (0, h - 3):
        for _ in range(140):
            xx = r.uniform(0, w)
            t.rect(xx, y0, xx + r.choice([1, 2, 4, 7]), y0 + 3, c(HOT, r.uniform(60, 200)))
    return t.result()


def tex_gauge_sides(card):
    """The two pieces of the card either side of the gauge (GAUGE_SIDES), cut out of the card's own art: over the
    fill's outer thirds they hide the stock cross's arms and look like the card itself, which is opaque too
    (CARD_FILL), so they match it over any floor."""
    k = card.width / (CARD[2] * PX)
    out = {}
    for side, (x, y, w, h) in GAUGE_SIDES.items():
        box = tuple(round(v * PX * k) for v in (x, y, x + w, y + h))
        a = np.asarray(linear_alpha(card.crop(box)), np.float32)   # the alpha the game draws it with
        a[..., :3] = a[..., :3] * a[..., 3:4] / 255                 # the glass over black: what the screen shows
        a[..., 3] = 255
        out[side] = Image.fromarray(a.astype(np.uint8), 'RGBA')
    return out


BLU_ACCENT = to_blue(Image.new('RGBA', (1, 1), tuple(RED) + (255,))).getpixel((0, 0))[:3]   # crimson on BLU


def sheet_mask(w, h, feather_px):
    """0..1 over a w x h px sheet: 1 in its core, 0 at its edge, over feather = (left, top, right, bottom) px with
    round corners."""
    fl, ft, fr, fb = (max(0.01, f) for f in feather_px)
    x = np.arange(w)[None, :] + 0.5
    y = np.arange(h)[:, None] + 0.5
    dx = np.maximum(np.maximum((fl - x) / fl, (x - (w - fr)) / fr), 0)
    dy = np.maximum(np.maximum((ft - y) / ft, (y - (h - fb)) / fb), 0)
    t = np.clip(1 - np.sqrt(dx * dx + dy * dy), 0, 1)
    return t * t * (3 - 2 * t)


def sheet_factor(t, col):
    """The sheet's colour as a factor per channel: the team colour in its core, white (1) at its edge."""
    return 1 + (np.array(col, np.float32) / 255 - 1) * t[..., None]


def tex_team_mul(wu, hu, feather, col, k=2.0):
    """Modulate sheet over white lettering (the digits' bloom and ghost): the team colour col in its core, fading to
    white (no change) over feather = (left, top, right, bottom) units round it (see DIGITS_MUL)."""
    w, h = max(2, round(wu * PX * k)), max(2, round(hu * PX * k))
    t = sheet_mask(w, h, [f * PX * k for f in feather])
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = sheet_factor(t, col) * 255
    img[..., 3] = 255
    return Image.fromarray(np.clip(np.rint(img), 0, 255).astype(np.uint8), 'RGBA')


def tex_team_add(wu, hu, feather, col, k=2.0):
    """Additive sheet over the same box as tex_team_mul, drawn just before it: in linear light (as the game blends)
    the card shows CARD_FILL there and the team sheet multiplies it by f, so adding CARD_FILL * (1 - f) / f first
    leaves the card as it was. The white lettering under it clips at white first and comes out in the team's colour."""
    w, h = max(2, round(wu * PX * k)), max(2, round(hu * PX * k))
    t = sheet_mask(w, h, [f * PX * k for f in feather])
    f = sheet_factor(t, col) ** 2.2
    g = (np.array(CARD_FILL, np.float32) / 255) ** 2.2
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = np.clip(g * (1 - f) / np.maximum(f, 1e-4), 0, 1) ** (1 / 2.2) * 255
    img[..., 3] = 255
    return Image.fromarray(np.clip(np.rint(img), 0, 255).astype(np.uint8), 'RGBA')


def tex_photo_bg():
    p = Px(PHOTO[2], PHOTO[3])
    p.rect(0, 0, p.W, p.H, c((26, 5, 10), 255))
    yy = np.linspace(0, 1, p.t.im.height)[:, None]
    glow = np.clip(np.exp(-((yy - 0.75) / 0.45) ** 2) * 70, 0, 255) * np.ones((1, p.t.im.width))
    g = Image.new('RGBA', p.t.im.size, c(RED, 0))
    g.putalpha(Image.fromarray(glow.astype(np.uint8)))
    p.t.im.alpha_composite(g)
    return p.result()


def tex_photo_fx():
    """Over the live 3D model: a crimson wash, a dot-matrix screen (the model reads as dots), a few thin tears, the
    ID brackets and its proxy tag."""
    p = Px(PHOTO[2], PHOTO[3])
    p.rect(0, 0, p.W, p.H, c(RED, 70))
    dot_screen(p, 0, 0, p.W, p.H, cell=3.0, alpha=130)
    tears(p, 0, 0, p.W, p.H, n=3, seed=60, alpha=120)
    p.brackets(4, 4, p.W - 4, p.H - 4, 10, c(WHITE, 200), 1)
    p.text(8, p.H - 10, 'PROXY 0451', ('mono', 10), c(WHITE, 170), 'lm')
    return p.result()


def tex_streak():
    p = Px(STREAK[2], STREAK[3])
    p.mixed(0, p.H / 2, [('撃破 ', ('jp5', 11), c(RED)), ('STREAK', ('mono', 12), c(GREY))], 'lm')
    return p.result()


def tex_slash(tall, em_px):
    """Border art for the "/" in front of the max health / reserve: the glyph in the left column of a 9-slice
    texture (src corners 64 px), the rest clear. The label it sits on is only as wide as the number it shadows,
    so the slash shows exactly when the game shows that number."""
    p = Px(SLASH_W, tall, k=8)
    asc = int(tall * PX) * METRICS['Rajdhani SemiBold'][1]
    p.text(0, asc, '/', ('raj6', em_px), c(GREY), 'ls')
    col = p.result().resize((64, 128), Image.LANCZOS)
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    out.alpha_composite(col, (0, 0))
    return out


def tex_ammo():
    x, y, w, h = AMMO
    p = Px(w, h)
    glass(p, 0, 0, p.W, p.H, cut='tl', cut_px=18, seed=12, alpha=255, fill=CARD_FILL, texture=False, wall='left')  # as tex_health
    for a, b in ((0, 30), (36, 74), (80, p.H)):   # the crimson edge, broken
        p.rect(p.W - 3, a, p.W, b, c(RED))
    tag_label(p, 30, 18, 'ROUNDS', '弾薬')
    wall_glyphs(p, 30, 40, 5, 18, seed=42)                 # the wall's glyphs where the card is empty
    static_bits(p, 30, p.H - 24, 140, p.H - 16, seed=9, density=0.42)
    return p.result()


def tex_ammo_low():
    """Low ammo (HudLowAmmoPulse flickers it in): the card's hairline burns, LOW over its label, tears across it."""
    x, y, w, h = AMMO
    p = Px(w, h)
    p.t.im.alpha_composite(tex_flash(w, h, HOT, 'tl').resize(p.t.im.size, Image.LANCZOS))
    torn(p, chamfer(0.5, 0.5, p.W - 0.5, p.H - 0.5, tl=17.5), seed=12, col=HOT, a=240)
    p.rect(180, 9, 236, 27, c(HOT))
    p.text(208, 18, 'LOW', ('raj7', 15), c(INK), 'mm')
    tears(p, 0, 30, p.W, p.H - 6, n=6, seed=83)
    return p.result()


IDLE_FPS, IDLE_FRAMES = 5, 35      # the passing glitch's flipbook: a 7 s loop


def tex_idle_tears(box, seed, n=8):
    """One frame of the Wall's passing glitch over a card: torn bars of crimson, white and cyan across it and a couple of
    solid slabs, nothing else."""
    x, y, w, h = box
    p = Px(w, h)
    tears(p, 0, 4, p.W, p.H - 4, n=n, seed=seed, alpha=235)
    tears(p, p.W * 0.1, p.H * 0.3, p.W * 0.9, p.H * 0.75, n=3, seed=seed + 7, alpha=200)
    r = np.random.default_rng(seed)
    for _ in range(2):
        bx, by = r.uniform(0, p.W * 0.7), r.uniform(p.H * 0.2, p.H * 0.8)
        p.rect(bx, by, bx + r.uniform(30, 90), by + r.uniform(3, 7), c(HOT, 170))
    return p.result()


def idle_flipbook(box, seed, start):
    """The passing glitch as a looping flipbook (it plays by itself, no animation event needed: the events the game
    starts on a respawn do not reach both cards): clear frames, and at `start` a flicker of three glitch frames
    (on, off, on with other tears). 256 x 128 per frame."""
    blank = Image.new('RGBA', (256, 128), (0, 0, 0, 0))
    on = {start: tex_idle_tears(box, seed), start + 2: tex_idle_tears(box, seed + 11, n=5)}
    return [on[i].resize((256, 128), Image.LANCZOS) if i in on else blank for i in range(IDLE_FRAMES)]


def tex_flash(wu, hu, color, cut, cut_px=18):
    """Low ammo / overheal / low health pulse: a soft glow hugging the inside of the card's outline."""
    p = Px(wu, hu)
    m = Image.new('L', p.t.im.size, 0)
    from PIL import ImageDraw, ImageFilter
    pts = [(xx * p.k * 2, yy * p.k * 2) for xx, yy in chamfer(0, 0, p.W, p.H, **{cut: cut_px})]
    ImageDraw.Draw(m).line(pts + [pts[0]], fill=255, width=int(6 * p.k * 2))
    m = m.filter(ImageFilter.GaussianBlur(7 * p.k * 2))
    inside = Image.new('L', p.t.im.size, 0)
    ImageDraw.Draw(inside).polygon(pts, fill=255)
    a = np.minimum(np.asarray(m, np.float32) * 1.6, np.asarray(inside, np.float32))
    img = np.dstack([np.full(a.shape, v, np.float32) for v in color] + [a])
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').resize(p.result().size, Image.LANCZOS)


def tex_strip(label_txt=None, icon=None):
    """The BUFF BANNER strip: black glass; centre strips carry their own label (the item ones get the game's)."""
    p = Px(STRIP[2], STRIP[3])
    glass(p, 0, 0, p.W, p.H, seed=zlib.crc32(('%s|%s' % (label_txt, icon)).encode()) % 997)  # the same every build
    x = 12
    if icon == 'cross':
        m, s = 15, 5.5
        p.rect(m - s, m - 2, m + s, m + 2, c(WHITE, 230))
        p.rect(m - 2, m - s, m + 2, m + s, c(WHITE, 230))
        x = 34
    if label_txt:
        p.text(x, p.H / 2, label_txt, ('mono', 11), c(GREY), 'lm')
    return p.result()


def tex_strip_track(n=1):
    """The bar's unlit segments under the game's bar (where the strip shows a count instead, it stays clear)."""
    p = Px(STRIP_BAR[2], STRIP_BAR[3], k=4)
    hsegs(p, 0, 0, p.W, p.H, n, WHITE, 24)
    return p.result()


def tex_tid(team):
    """Target ID card, (806, 600)-(1114, 648). The game stretches it to the name and draws it at a third of its
    alpha (tf_hud_target_id_alpha 100), so it is a soft haze behind the name rather than a black bar: feathered at
    the ends and edges, lighter to the right, with the team's colour as a mark at the left and a line under the
    name that fades out."""
    w, h = 600, round(TID_H * PX * 2)
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]

    def ramp(v, a, b):
        t = np.clip((v - a) / (b - a), 0, 1)
        return t * t * (3 - 2 * t)
    # a shadow, not a box: soft all round, deepest behind the start of the name
    alpha = 200 * ramp(x, 0, 0.16) * (1 - 0.75 * ramp(x, 0.35, 1)) * ramp(y, 0, 0.45) * (1 - ramp(y, 0.6, 1))
    col = TEAM_RED if team == 'red' else TEAM_BLU if team == 'blue' else GREY
    base = np.array(INK, np.float32) * 0.9 + np.array(col, np.float32) * 0.1
    img = np.zeros((h, w, 4), np.float32)
    img[..., :3] = base
    img[..., 3] = alpha
    # the line under the name, full at the left, gone by 90 %
    ly0, ly1 = h - 9, h - 4
    fade = 255 * (1 - ramp(x[0], 0.2, 0.9))
    img[ly0:ly1, :, :3] = col
    img[ly0:ly1, :, 3] = np.maximum(img[ly0:ly1, :, 3], fade * ramp(x[0], 0.0, 0.03))
    # the team's mark at the left
    img[round(h * 0.12):ly1, 4:11, :3] = col
    img[round(h * 0.12):ly1, 4:11, 3] = 255
    # a faint hairline over the name
    hair = 46 * ramp(x[0], 0.03, 0.08) * (1 - ramp(x[0], 0.3, 0.55))
    img[2:4, :, :3] = WHITE
    img[2:4, :, 3] = np.maximum(img[2:4, :, 3], hair)
    return Image.fromarray(np.clip(np.rint(img), 0, 255).astype(np.uint8), 'RGBA')


# the health tag: a building's in the target ID, and the one the game floats over the head of the player you look at.
# Black glass with the number on it and, right of the number, a gauge that fills from the bottom in the team's colour
TAG = (31, 16)
TAG_GAUGE = (25, 2, 4, 12)    # x, y, w, h in the tag: 6 segments
TAG_GAUGE_FILL = (TAG_GAUGE[0] - TAG_GAUGE[2], TAG_GAUGE[1], TAG_GAUGE[2] * 3, TAG_GAUGE[3])   # see GAUGE_FILL
TAG_SEGS, TAG_GAP = 6, 1.5


def tex_tag_track():
    """The tag's gauge, under the fill: opaque dark, its six segments faint in white, which the Modulate sheet over
    the gauge turns into dim slots of the team's colour."""
    p = Px(*TAG_GAUGE[2:], k=4)
    p.rect(0, 0, p.W, p.H, c(CARD_FILL))
    vsegs(p, 0, 0, p.W, p.H, TAG_SEGS, WHITE, 70, gap=TAG_GAP)
    return p.result()


def tex_tag_plate():
    """Over the fill: the tag's black glass, opaque so the stock cross's arms either side of the gauge vanish under
    it, with a cut corner, the torn hairline in the team's colour, a white tick at its foot and a window over the
    gauge, a little inside it so vgui's rounding to whole pixels never shows the fill beside it."""
    p = Px(*TAG, k=4)
    glass(p, 0, 0, p.W, p.H, cut='tl', cut_px=7, alpha=255, edge=210, texture=False, seed=23, fill=CARD_FILL)
    p.line([(2 * PX, p.H - 2.5), (9 * PX, p.H - 2.5)], c(WHITE, 220), 1.5)
    img = p.result()
    a = np.asarray(img).copy()
    s = a.shape[1] / p.W
    gx, gy, gw, gh = (v * PX for v in TAG_GAUGE)
    ix, iy = 0.5 * PX, 0.3 * PX
    a[round((gy + iy) * s):round((gy + gh - iy) * s), round((gx + ix) * s):round((gx + gw - ix) * s), 3] = 0
    return Image.fromarray(a, 'RGBA')


def tex_tag_dead():
    """The killcam tag's mark for a dead killer (patch_killer_health): LOST over the number's place, as on a dead
    teammate's slot. It lies under the cover (tex_tag_cover), which the game hides once the killer's health is 0."""
    p = Px(*TAG, k=4)
    p.text((TAG_GAUGE[0] + 0.5) * PX / 2, p.H / 2, 'LOST', ('mono', 10), c(HOT), 'mm')
    return p.result()


def tex_tag_cover():
    """The killcam tag's cover over its LOST mark: the plate's own pixels over the number's place, so while the
    killer lives it vanishes into the plate. It is a plain picture, the same on RED and BLU (the game hides it, and
    only a plain ImagePanel of its own does that), so it takes only what both plates share: their opaque glass and
    white tick, not the hairline in the team's colour; a few pixels inside any other pixel, so its soft edge falls on
    even glass."""
    red = np.asarray(tex_tag_plate())
    blu = np.asarray(to_blue(Image.fromarray(red, 'RGBA')))
    ok = (red[..., 3] == 255) & (np.abs(red.astype(np.int16) - blu).max(-1) <= 1)
    s = red.shape[1] / (TAG[0] * PX)
    ok[:, round((TAG_GAUGE[0] - 1) * PX * s):] = False
    ok[0], ok[-1], ok[:, 0] = False, False, False
    for _ in range(3):
        ok = ok & np.roll(ok, 1, 0) & np.roll(ok, -1, 0) & np.roll(ok, 1, 1) & np.roll(ok, -1, 1)
    a = red.copy()
    a[..., 3] = np.where(ok, 255, 0)
    return Image.fromarray(a, 'RGBA')


def tex_tid_track():
    """The tournament spectator panel's health gauge track (patch_tournament_health)."""
    p = Px(3, 13, k=4)
    vsegs(p, 0, 0, p.W, p.H, 8, WHITE, 22, gap=1.5)
    return p.result()


def tex_timer():
    """Round timer box at the top centre, (894, 0)-(1026, 58), its lower corners cut, the hairline torn."""
    p = Px(59, 26)
    shape = chamfer(0, 0, p.W, p.H, bl=12, br=12)
    p.poly(shape, c(PANEL, 236))
    scan_in(p, shape, WHITE, 10)
    torn(p, chamfer(0.5, 0.5, p.W - 0.5, p.H - 0.5, bl=11.5, br=11.5), seed=21, a=170)
    # game: the casual HUD does not say the game mode, so the preview's CAPTURE THE FLAG is a fixed line
    p.text(p.W / 2, 48, 'ROUND TIME', ('mono', 9), c(GREY), 'mm')
    return p.result()


def tex_slot():
    p = Px(*SLOT, k=4)
    p.rect(0, 0, p.W, p.H, c(PANEL, 220))
    return p.result()


def tex_slot_x():
    """A dead player's slot (TeamStatus_PlayerDead flickers it in): the game's grey portrait of their class shows
    through a thin veil of static, so the strip says which classes are down; the respawn seconds the game writes
    sit in its bottom right corner (patch_teamstatus), and LOST under it (no team colour: it marks both teams'
    dead)."""
    p = Px(*SLOT, k=4)
    ph = (1 + PORTRAIT_H) * PX
    p.rect(0, PX, p.W, ph, c(INK, 60))
    static_bits(p, 0, PX, p.W, ph, seed=41, density=0.08, col=RED, cell=2.0)
    tears(p, 0, ph - 4 * PX, p.W * 0.6, ph, n=1, seed=42, alpha=120)  # low on the left: clear of the face
    p.rect(0, ph, p.W, p.H, c(INK, 175))
    p.text(p.W / 2, ph + (p.H - ph) / 2, 'LOST', ('mono', 8), c(HOT), 'mm')
    return p.result()


def tex_slot_dots():
    """Over a teammate's class portrait (the game's picture): the dot-matrix screen of the HUD's own portrait."""
    p = Px(SLOT[0], PORTRAIT_H, k=4)
    dot_screen(p, 0, 0, p.W, p.H, cell=2.5, alpha=120)
    return p.result()


UBER_CARD = (120, 26)                          # 0.9: ÜberCharge is a card under the crosshair (smaller: it took too much screen)
UBER_BAR = (7, 15, 70, 5)                     # its 22-segment bar under the label
UBER_PCT = (78, 3, 38, 20)                    # the percent, large, at its right


def tex_uber_card():
    """The Über card: the cards' black glass with the Wall from the left, ÜBERCHARGE // ユーバー, the bar's slot."""
    p = Px(*UBER_CARD)
    glass(p, 0, 0, p.W, p.H, cut='tr', cut_px=10, seed=17, alpha=245, fill=CARD_FILL, texture=False, wall='left')
    p.rect(p.W - 3, 10, p.W, p.H, c(RED))
    tag_label(p, UBER_BAR[0] * PX, 13, 'ÜBERCHARGE')  # no ユーバー: the smaller card has no room for it
    bx, by, bw, bh = (v * PX for v in UBER_BAR)
    hsegs(p, bx, by, bx + bw, by + bh, 1, WHITE, 24, gap=0)
    return p.result()


def tex_uber_ready():
    """ÜberCharge ready (HudMedicCharged flickers it in): the card's hairline burns, READY over the percent."""
    p = Px(*UBER_CARD)
    p.t.im.alpha_composite(tex_flash(UBER_CARD[0], UBER_CARD[1], HOT, 'tr', cut_px=10).resize(p.t.im.size,
                                                                                            Image.LANCZOS))
    x, y, w, h = (v * PX for v in UBER_PCT)
    p.rect(x - 6, y, p.W - 10, y + h, c(CARD_FILL))
    p.text(p.W - 10, p.H / 2 + 1, 'READY', ('raj7', 29), c(WHITE), 'rm')
    return p.result()


def _old_tex_uber_ready():
    """ÜberCharge ready (HudMedicCharged flickers it in): the strip's hairline burns and READY covers its label."""
    p = Px(STRIP[2], STRIP[3])
    p.t.im.alpha_composite(tex_flash(STRIP[2], STRIP[3], HOT, 'tr', cut_px=0).resize(p.t.im.size, Image.LANCZOS))
    torn(p, [(0.5, 0.5), (p.W - 0.5, 0.5), (p.W - 0.5, p.H - 0.5), (0.5, p.H - 0.5)], seed=13, col=HOT, a=240)
    p.rect(28, 5, 66, p.H - 5, c(HOT))
    p.text(47, p.H / 2, 'READY', ('mono', 10), c(INK), 'mm')
    return p.result()


MODULATE = {'ig_gauge_mul', 'ig_bar_mul', 'ig_tid_mul', 'ig_uber_mul', 'ig_tag_mul',
            'ig_digits_mul', 'ig_ammo_digits_mul'}
TEAM_TEXTURES = MODULATE - {'ig_tid_mul'}   # these also get a BLU twin (b/<name>)
ADDITIVE = {'ig_digits_add', 'ig_ammo_digits_add'}   # added to what is under them (and their BLU twins)


def textures(out):
    minmode.art(out)
    card = tex_health()
    out.thumb('ig_health', card, team=True)
    for side, im in tex_gauge_sides(card).items():
        out.thumb('ig_gauge_side_' + side, im, mips=False, team=True)
    out.thumb('ig_photo_bg', tex_photo_bg(), team=True)
    out.thumb('ig_photo_fx', tex_photo_fx(), team=True)
    out.thumb('ig_streak', tex_streak(), team=True)
    out.thumb('ig_slash14', tex_slash(MAXNUM_T, em('Rajdhani SemiBold', MAXNUM_T)), mips=False)
    out.thumb('ig_slash16', tex_slash(RESERVE_T, em('Rajdhani SemiBold', RESERVE_T)), mips=False)
    out.thumb('ig_ammo', tex_ammo(), team=True)
    out.thumb('ig_ammo_low', tex_ammo_low(), team=True)              # low ammo: the team's colour
    out.thumb('ig_health_glow', gauge_hole(tex_flash(CARD[2], CARD[3], RED, 'tr')), team=True)   # overheal: team
    out.thumb('ig_health_danger', tex_critical(), team=True)     # near death: the team's colour
    # the passing glitch, every 7 s: the health card at the loop's start, the ammo card half way through it
    out.anim('ig_health_tears', idle_flipbook(CARD, 31, 0), IDLE_FPS)
    out.anim('ig_ammo_tears', idle_flipbook(AMMO, 57, IDLE_FRAMES // 2), IDLE_FPS)
    out.thumb('ig_edge_danger', tex_edge_danger(), team=True)    # near death, round the screen's edges
    out.thumb('ig_slot_dots', tex_slot_dots(), mips=False)
    out.thumb('ig_uber_ready', tex_uber_ready(), team=True)
    out.thumb('ig_uber_card', tex_uber_card(), team=True)
    out.thumb('ig_strip', tex_strip(), team=True)
    out.thumb('ig_strip_track', tex_strip_track(), mips=False)
    for name, txt, icon in (('sticky', 'STICKY', None), ('charge', 'CHARGE', None), ('uber', 'ÜBER', 'cross'),
                            ('metal', 'METAL', None)):
        out.thumb('ig_strip_' + name, tex_strip(txt, icon), team=True)
    for team in ('red', 'blue', 'ink'):
        out.thumb('ig_tid_' + team, tex_tid(team))
    out.thumb('ig_tid_track', tex_tid_track(), mips=False)
    out.thumb('ig_tag_track', tex_tag_track(), mips=False)
    out.thumb('ig_tag_mul', mul_texture(TAG_GAUGE[2], TAG_GAUGE[3], TAG_SEGS, vertical=True, gap=TAG_GAP), mips=False,
              team=True)
    out.thumb('ig_tag_plate', tex_tag_plate(), mips=False, team=True)
    out.thumb('ig_tag_dead', tex_tag_dead(), mips=False)
    out.thumb('ig_tag_cover', tex_tag_cover(), mips=False)
    out.thumb('ig_timer', tex_timer(), team=True)
    out.thumb('ig_slot', tex_slot(), mips=False)
    out.thumb('ig_slot_x', tex_slot_x(), mips=False)
    out.thumb('ig_gauge_mul', mul_texture(GAUGE[2], GAUGE[3], 16, vertical=True), mips=False, team=True)
    out.thumb('ig_bar_mul', mul_texture(STRIP_BAR[2], STRIP_BAR[3], 1, gap=0), mips=False, team=True)   # 0.9: one smooth bar
    out.thumb('ig_uber_mul', mul_texture(UBER_BAR[2], UBER_BAR[3], 1, gap=0), mips=False, team=True)
    # the digits' team sheets and the additive ones under them, worked out per team (the pair must match exactly)
    for team, col in (('', RED), ('b/', BLU_ACCENT)):
        for name, box, feather in (('ig_digits', DIGITS_MUL, DIGITS_FEATHER), ('ig_ammo_digits', AMMO_DIGITS_MUL,
                                                                                AMMO_FEATHER)):
            out.thumb(team + name + '_mul', tex_team_mul(*box[2:], feather, col), mips=False)
            out.thumb(team + name + '_add', tex_team_add(*box[2:], feather, col), mips=False)
    out.thumb('ig_tid_mul', mul_texture(TID_GAUGE_FILL[2], TID_GAUGE_FILL[3], 8, vertical=True, gap=1.5, thirds=True),
              mips=False)
    out.thumb('ig_white', Image.new('RGBA', (16, 16), (255, 255, 255, 255)), mips=False)  # our hud/health_color
    names = list(MODULATE) + ['b/' + n for n in TEAM_TEXTURES]
    for name in names:  # these multiply what is under them (Modulate shader) instead of covering it
        with open(os.path.join(out.root, 'materials/vgui/replay/thumbnails/rk', name + '.vmt'), 'w',
                  encoding='utf-8') as f:
            f.write('"Modulate"\n{\n\t"$basetexture"\t"vgui/replay/thumbnails/rk/%s"\n\t"$mod2x"\t"0"\n'
                    '\t"$ignorez"\t"1"\n}\n' % name)
    for name in list(ADDITIVE) + ['b/' + n for n in ADDITIVE]:
        with open(os.path.join(out.root, 'materials/vgui/replay/thumbnails/rk', name + '.vmt'), 'w',
                  encoding='utf-8') as f:
            f.write('"UnlitGeneric"\n{\n\t"$basetexture"\t"vgui/replay/thumbnails/rk/%s"\n\t"$additive"\t"1"\n'
                    '\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n}\n'
                    % name)


# ------------------------------------------------------------------ scheme borders
def _border(image, corner, draw_w, draw_h):
    return [['bordertype', 'scalable_image', None], ['backgroundtype', '2', None], ['image', T + image, None],
            ['src_corner_height', str(corner), None], ['src_corner_width', str(corner), None],
            ['draw_corner_width', str(draw_w), None], ['draw_corner_height', str(draw_h), None]]


BORDERS = {
    'RK_Slash14': _border('ig_slash14', 64, SLASH_W, MAXNUM_T // 2),
    'RK_Slash16': _border('ig_slash16', 64, SLASH_W, RESERVE_T // 2),
    'RK_Timer': _border('ig_timer', 0, 0, 0),
}


# ------------------------------------------------------------------ .res helpers
def img(name, x, y, w, h, image, z=1, **extra):
    e = {'ControlName': 'ImagePanel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': 1, 'enabled': 1, 'scaleImage': 1, 'image': T + image, 'mouseinputenabled': 0}
    e.update(extra)
    return e


def team_keys(image):
    """A CTFImagePanel's keys: `image` on RED (and for spectators), its BLU twin (b/<image>, build_art.to_blue) on BLU.
    The game swaps the picture itself when the local player changes team (localplayer_changeteam), so the HUD's
    crimson turns azure on BLU wherever it is a picture."""
    return dict(image=T + image, teambg_1=T + image, teambg_2=T + image, teambg_3=T + 'b/' + image)


def timg(name, x, y, w, h, image, z=1, **extra):
    """img() in the local player's team colour (CTFImagePanel, team_keys)."""
    e = img(name, x, y, w, h, image, z, **extra)
    e.update(ControlName='CTFImagePanel', **team_keys(image))
    return e


def lbl(name, x, y, w, h, text, font, fg, align='west', z=5, **extra):
    e = {'ControlName': 'CExLabel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': 1, 'enabled': 1, 'labelText': text, 'textAlignment': align, 'font': font, 'fgcolor': fg,
         'textinsetx': 0, 'mouseinputenabled': 0}
    e.update(extra)
    return e


def centred(x):
    """A corner-layout x -> the CENTRED layout's: the health card's family (left-anchored numbers) moves so the card ends
    INNER left of the centre, the ammo card's family ('rN', from the right edge) so the card starts INNER right of it."""
    if isinstance(x, int):
        return 'c%d' % (x - CARD[0] - INNER - CARD[2])
    if x.startswith('r'):
        return 'c%d' % (INNER + AMMO[0] - int(x[1:]))
    return x


def put(node, x, y, w=None, h=None, alt=True, **extra):
    """Set a box given in the corner layout: the CENTRED twin goes in the plain keys, the corner one in *_minmode keys
    (cl_hud_minmode 1). alt=False: one box for both."""
    for key in ('xpos_minmode', 'ypos_minmode'):
        kv.remove(node, key)
    dy = (HEALTH_DY if isinstance(x, int) else AMMO_DY if str(x).startswith('r') else 0) if alt else 0
    kv.setmany(node, xpos=centred(x) if alt else x, ypos=y + dy, **extra)
    if w is not None:
        kv.set(node, 'wide', w)
    if h is not None:
        kv.set(node, 'tall', h)
    if alt:
        node.append(['xpos_minmode', str(x), None])
        node.append(['ypos_minmode', str(y), None])
    return node


def add(body, entries, alt=True):
    blk = kv.add_block(body, entries['fieldName'], {k: v for k, v in entries.items()})
    if alt:
        put(blk, entries['xpos'], entries['ypos'])
    return blk


def at(local, origin=CARD):
    """Card-local box -> screen box."""
    x, y, w, h = local
    return origin[0] + x, origin[1] + y, w, h


def find(body, name):
    blk = kv.find(body, name)
    if blk is None:
        blk = kv.add_block(body, name, {'fieldName': name})
    return blk


# ------------------------------------------------------------------ health card + portrait
def patch_health(root):
    body = kv.find(root, 'Resource/UI/HudPlayerHealth.res')
    # drawn over HudPlayerClass (zpos 1), which holds the card itself under the portrait (patch_class)
    kv.setmany(kv.find(body, 'HudPlayerHealth'), xpos=0, ypos=0, zpos=2, wide='f0', tall=480, HealthBonusPosAdj=0,
               HealthDeathWarning='0.49', HealthDeathWarningColor='255 255 255 255')
    x0, y0 = CARD[:2]
    # the game's fill (white: ours, or the stock cross sv_pure keeps) rises bottom-up in a panel three gauges wide;
    # the gauge's own Modulate sheet over its middle cuts it into the preview's 16 segments in the team's colour, the
    # card's unlit segments dim under it, and two opaque pieces of the card hide the fill's outer thirds (GAUGE_FILL)
    gx, gy, gw, gh = at(GAUGE)
    put(kv.find(body, 'PlayerStatusHealthImageBG'), gx, gy, gw, gh, zpos=1, image=T + 'blank')
    put(kv.find(body, 'PlayerStatusHealthImage'), *at(GAUGE_FILL), zpos=2)
    add(body, timg('RK_HealthMul', gx, gy, gw, gh, 'ig_gauge_mul', z=3))
    for side, box in GAUGE_SIDES.items():  # pinned to the gauge's sheet, edge to edge (see GAUGE_SIDES)
        ours, theirs = ('PIN_TOPRIGHT', 'PIN_TOPLEFT') if side == 'l' else ('PIN_TOPLEFT', 'PIN_TOPRIGHT')
        kv.remove(body, 'RK_GaugeSide_' + side)
        kv.add_block(body, 'RK_GaugeSide_' + side, timg(
            'RK_GaugeSide_' + side, 0, 0, box[2], box[3], 'ig_gauge_side_' + side, z=3, pin_to_sibling='RK_HealthMul',
            pin_corner_to_sibling=ours, pin_to_sibling_corner=theirs))
    # overheal and near death: the game pulses this panel (HudHealthBonusPulse / HudHealthDyingPulse), a plain image
    # it makes itself, so it stays empty and the HUD's animations (build.py ANIMS) pulse two of ours instead, both in
    # the team's colour. Over the gauge's side pieces and the digits' sheets (under those they came out as dark
    # boxes), under the digits; the gauge is cut out of them (gauge_hole)
    put(kv.find(body, 'PlayerStatusHealthBonusImage'), x0, y0, CARD[2], CARD[3], zpos=1, image=T + 'blank', visible=0)
    add(body, timg('RK_HealthFlash', x0, y0, CARD[2], CARD[3], 'ig_health_glow', z=9, alpha=0))
    add(body, timg('RK_HealthDanger', x0, y0, CARD[2], CARD[3], 'ig_health_danger', z=9, alpha=0))
    add(body, img('RK_HealthTears', x0, y0, CARD[2], CARD[3], 'ig_health_tears', z=10))
    # near death the wall also seeps in round the screen's edges (HudHealthDyingPulse); the panel is the screen
    kv.remove(body, 'RK_EdgeDanger')
    kv.add_block(body, 'RK_EdgeDanger', timg('RK_EdgeDanger', 0, 0, 'f0', 480, 'ig_edge_danger', z=0, alpha=0))
    dx, dy, dw, dh = at(DIGITS)
    put(kv.find(body, 'PlayerStatusHealthValue'), dx, dy, dw, dh, zpos=11, font='RK_Digits', fgcolor='RK_Text',
        textAlignment='west', textinsetx=0)
    # the bloom and the ghost are white under the team's sheet (DIGITS_MUL): crimson on RED, azure on BLU; the
    # additive sheet before it keeps the card round them as it is
    add(body, lbl('RK_HealthGlow', dx, dy, dw, dh, '%Health%', 'RK_Digits' + 'Glow', '255 255 255 150', z=5))
    add(body, lbl('RK_HealthGhost', dx - 1, dy, dw, dh, '%Health%', 'RK_Digits', '255 255 255 170', z=6))
    # near death the digits flash in the team's colour: a label cannot follow the team, so the white digits fade out
    # for a moment over this copy of them, white under the team's sheet like the ghost (HudHealthDyingPulse)
    add(body, lbl('RK_HealthHot', dx, dy, dw, dh, '%Health%', 'RK_Digits', '255 255 255 0', z=6))
    add(body, timg('RK_DigitsAdd', *at(DIGITS_MUL), 'ig_digits_add', z=7))
    add(body, timg('RK_DigitsMul', *at(DIGITS_MUL), 'ig_digits_mul', z=8))
    # the chromatic split: the ghost is its red side, this cyan copy over the sheet its other
    add(body, lbl('RK_HealthSplit', dx + 1, dy, dw, dh, '%Health%', 'RK_DigitsSplit', '0 214 255 110', z=10))
    # "/ 200". game: TF2 sends the max health only while health is 5 or more under it (tf_hud_playerstatus.cpp,
    # SetHealth), so "/ 200" shows whenever you are hurt; the slash is the border of an invisible copy of the number,
    # sized to it (auto_wide_tocontents), so it comes and goes with the number
    add(body, lbl('RK_MaxSlash', x0 + MAX_X, y0 + MAX_TOP, 0, MAXNUM_T, '%MaxHealth%', 'RK_Digits', '0 0 0 0', z=12,
                  auto_wide_tocontents=1, border='RK_Slash14', paintborder=1, paintbackground=0))
    put(kv.find(body, 'PlayerStatusMaxHealthValue'), x0 + MAX_NUM_X, y0 + MAX_TOP, 40, MAXNUM_T, zpos=12,
        font='RK_MaxNum', fgcolor='RK_Grey', textAlignment='west', textinsetx=0)
    for ent in body:  # bleed, milk, marked for death...: beside the card's top right
        if isinstance(ent[1], list) and (ent[0].startswith('PlayerStatus_') or ent[0] in STATUS_ICONS):
            put(ent[1], x0 + CARD[2] + 4, y0, 18, 18)


STATUS_ICONS = ('PlayerStatusBleedImage', 'PlayerStatusHookBleedImage', 'PlayerStatusMilkImage', 'PlayerStatusGasImage',
                'PlayerStatusMarkedForDeathImage', 'PlayerStatusMarkedForDeathSilentImage', 'PlayerStatusSlowed')

# the 3D model framed like the preview's portrait: head and shoulders down to the waist. The stock camera data per
# class is kept (distance, side offset, turn) and the height and field of view are worked out so the view spans
# HEAD_TOP + 5 down to HEAD_TOP + 5 - 2 * HALF world units: (head top above the feet, half the view's height)
FRAME = {'Scout': (76, 23), 'Soldier': (82, 24), 'Pyro': (80, 25), 'Demoman': (78, 24), 'Heavy': (86, 28),
         'Engineer': (74, 23), 'Medic': (84, 24), 'Sniper': (84, 24), 'Spy': (82, 23)}


def frame_model(panel):
    data = kv.find(panel, 'customclassdata')
    if data is None:
        return
    aspect = PHOTO[2] / PHOTO[3]
    for cls, (top, half) in FRAME.items():
        blk = kv.find(data, cls)
        if blk is None:
            continue
        dist = float(kv.get(blk, 'origin_x') or 150)
        fov = 2 * math.degrees(math.atan(half * aspect / dist))
        kv.setmany(blk, fov='%.1f' % fov, origin_z='%d' % -round(top + 5 - half))


def patch_class(root):
    body = kv.find(root, 'Resource/UI/HudPlayerClass.res')
    # the health card lives here, under the portrait; the digits and gauge draw over it from HudPlayerHealth (zpos 2)
    kv.setmany(kv.find(body, 'HudPlayerClass'), xpos=0, ypos=0, zpos=1, wide='f0', tall=480)
    add(body, timg('RK_HealthCard', CARD[0], CARD[1], CARD[2], CARD[3], 'ig_health', z=0))
    px, py, pw, ph = at(PHOTO)
    add(body, timg('RK_PhotoBG', px, py, pw, ph, 'ig_photo_bg', z=1))
    model = kv.find(body, 'classmodelpanel')
    put(model, px, py, pw, ph, zpos=2)
    frame_model(model)
    # 2D mode (HUD Settings > PLAYER CHARACTER, cl_hud_playerclass_use_playermodel 0): the class art fills the
    # portrait's lower square
    put(kv.find(body, 'PlayerStatusClassImage'), px, py + ph - pw, pw, pw, zpos=2)
    for n in ('classmodelpanelBG', 'PlayerStatusClassImageBG'):
        put(kv.find(body, n), 0, 0, 0, 0, alt=False)
    for n in ('PlayerStatusSpyImage', 'PlayerStatusSpyOutlineImage'):
        put(kv.find(body, n), px + 2, py + ph - 28, 26, 26, zpos=4)
    add(body, timg('RK_PhotoFx', px, py, pw, ph, 'ig_photo_fx', z=3))


def patch_killstreak(root):
    """The 撃破 STREAK 03 row of the health card. game: the count has no leading zero."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    x, y, w, h = at(STREAK)
    put(kv.find(body, 'HudItemEffectMeter'), x, y, w, h, zpos=3)  # over the health card
    kv.setmany(kv.find(body, 'ItemEffectMeterBG'), xpos=0, ypos=0, zpos=0, wide=w, tall=h, **team_keys('ig_streak'))
    kv.setmany(kv.find(body, 'ItemEffectMeterCount'), xpos=STREAK_NUM_X, ypos=0, zpos=2, wide=20, tall=h,
               font='RK_StreakNum', textAlignment='west', fgcolor='RK_Text', textinsetx=0)
    kv.setmany(kv.find(body, 'ItemEffectMeterLabel'), xpos=0, ypos=0, wide=0, tall=0, visible=0)


# ------------------------------------------------------------------ ammo card
def patch_ammo(root):
    body = kv.find(root, 'Resource/UI/HudAmmoWeapons.res')
    w, h = AMMO[2], AMMO[3]
    blk = kv.find(body, 'HudWeaponAmmoBG')
    kv.setmany(blk, xpos=0, ypos=0, zpos=0, wide=w, tall=h, scaleImage=1, **team_keys('ig_ammo'))
    for key in ('teambg_2_lodef', 'teambg_3_lodef'):
        kv.remove(blk, key)
    # low ammo: the game finds this panel as a plain image (it would not find a team one) and runs HudLowAmmoPulse on
    # it; it stays empty and the HUD's pulse (build.py ANIMS) flashes RK_AmmoFlash, in the team's colour, instead
    low = kv.find(body, 'HudWeaponLowAmmoImage')
    kv.setmany(low, xpos=0, ypos=0, zpos=1, wide=w, tall=h, image=T + 'blank', scaleImage=1)
    for key in ('teambg_1', 'teambg_2', 'teambg_3', 'teambg_2_lodef', 'teambg_3_lodef'):
        kv.remove(low, key)
    # over the digits' sheets (under them it came out as a dark box), under the digits
    kv.add_block(body, 'RK_AmmoFlash', timg('RK_AmmoFlash', 0, 0, w, h, 'ig_ammo_low', z=9, alpha=0))
    kv.add_block(body, 'RK_AmmoTears', img('RK_AmmoTears', 0, 0, w, h, 'ig_ammo_tears', z=13))
    x, y, dw, dh = AMMO_DIGITS
    big = dict(font='RK_Digits', textAlignment='east', textinsetx=0)
    # a weapon without a clip (flamethrower, minigun, medigun...) has no "/ 20" after its number: that number
    # (AmmoNoClip) moves right, into the middle of the card's free side, instead of ending where the clip's does
    for n, dx, z, col in (('AmmoInClip', 0, 11, 'RK_Text'), ('AmmoNoClip', AMMO_NOCLIP_DX, 11, 'RK_Text'),
                          ('AmmoInClipShadow', 1, 10, '0 214 255 110'),
                          ('AmmoNoClipShadow', AMMO_NOCLIP_DX + 1, 10, '0 214 255 110')):
        kv.setmany(kv.find(body, n), xpos=x + dx, ypos=y, wide=dw, tall=dh, zpos=z, fgcolor=col, **big)
        if 'Shadow' in n:  # the cyan split copy, back: each clip label's own shadow, so it follows that label
            kv.set(kv.find(body, n), 'font', 'RK_DigitsSplit')
    # the shared bloom (one %Ammo% label for both clip labels) would stay behind the moved number: gone; the cyan
    # copy is the shadow labels now (above)
    kv.remove(body, 'RK_AmmoGlow')
    kv.remove(body, 'RK_AmmoSplit')
    kv.add_block(body, 'RK_AmmoAdd', timg('RK_AmmoAdd', *AMMO_DIGITS_MUL, 'ig_ammo_digits_add', z=7))
    kv.add_block(body, 'RK_AmmoMul', timg('RK_AmmoMul', *AMMO_DIGITS_MUL, 'ig_ammo_digits_mul', z=8))
    kv.setmany(kv.find(body, 'AmmoInReserve'), xpos=RES_NUM_X, ypos=RES_TOP, wide=36, tall=RESERVE_T, zpos=12,
               font='RK_ReserveNum', fgcolor='RK_Grey', textAlignment='west', textinsetx=0)
    # "/ 20": the reserve's shadow label is shown and hidden with the reserve, so it carries the slash (see patch_health)
    shadow = kv.find(body, 'AmmoInReserveShadow')
    kv.setmany(shadow, xpos=RES_X, ypos=RES_TOP, wide=0, tall=RESERVE_T, zpos=12, font='RK_Digits', fgcolor='0 0 0 0',
               textAlignment='west', textinsetx=0, auto_wide_tocontents=1, border='RK_Slash16', paintborder=1,
               paintbackground=0)


def ammo_box(alt=False):
    """alt: the corner layout."""
    x, y, w, h = AMMO
    return ('r%d' % x, y, w, h) if alt else (centred('r%d' % x), y + AMMO_DY, w, h)


# ------------------------------------------------------------------ meter strips
# Every item meter is the preview's BUFF BANNER strip: the game's own name for it on the left (game: painted white by
# the game), its bar cut into 22 crimson segments (a Modulate sheet over the white bar the game paints) or its count.
# Several meters can show at once, so each file has a fixed row stacking up from the first strip; files one class
# can show together sit in different rows (checked against the game's per-class meter list, CreateHudElementsForClass):
#   0  the generic file (Sandman, the Heavy's foods, Jarate, Razorback, banners, cloak, Gas Passer, Dragon's Fury),
#      the Bison, the Vita-Saw and the engineer's metal (patch_account)
#   1  a class's own weapon meter: Bonk / Mad Milk / Cleaver, minigun, Eyelander, Air Strike, Cow Mangler, Bazaar
#      Bargain, Heatmaker, Diamondback, Frontier Justice, Pomson, the Pyro's Manmelter and Thermal Thruster, the
#      Medic's MvM shield
#   2  the Soda Popper / Baby Face's Blaster (a Scout's primary, over the Sandman and Bonk), the Spy-cicle (over cloak
#      and Diamondback), the Phlogistinator (a Pyro's primary, over the Manmelter or Thermal Thruster)
#   3  the meters any class can have: the MvM canteen, the Halloween kart, the Mannpower powerup
#   4  the Spy's sapper (MvM only: cloak, Diamondback, Spy-cicle and canteen under it)
# The Gas Passer and the Dragon's Fury load the same generic file, so with both on they share its place (in the stock
# HUD too: a file cannot tell its two copies apart).
METER_ROW = {
    'huditemeffectmeter_organs.res': 0, 'huditemeffectmeter_raygun.res': 0,
    'huditemeffectmeter_cleaver.res': 1, 'huditemeffectmeter_scout.res': 1, 'huditemeffectmeter_particlecannon.res': 1,
    'huditemeffectmeter_demoman.res': 1, 'huditemeffectmeter_heavy.res': 1, 'huditemeffectmeter_engineer.res': 1,
    'huditemeffectmeter_pomson.res': 1, 'huditemeffectmeter_sniper.res': 1, 'huditemeffectmeter_sniperfocus.res': 1,
    'huditemeffectmeter_spy.res': 1, 'hudrocketpack.res': 1,
    'huditemeffectmeter_sodapopper.res': 2, 'huditemeffectmeter_spyknife.res': 2, 'huditemeffectmeter_pyro.res': 2,
    'huditemeffectmeter_powerupbottle.res': 3, 'huditemeffectmeter_kartcharge.res': 3, 'hudpowerupeffectmeter.res': 3,
    'huditemeffectmeter_halloweensouls.res': 3,
    'huditemeffectmeter_sapper.res': 4,
}


def strip_box(row=0, alt=False):
    """Item meter strip `row`, stacked over the ammo card: in the corners right-aligned with it (the screen's edge),
    in CENTRED left-aligned with its inner edge, the side toward the crosshair; alt: the corner layout."""
    x, y, w, h = STRIP
    if alt:  # MINMODE: under the ammo plate, more rows going down
        return 'c%d' % minmode.A_X, minmode.METER_Y + row * STRIP_STEP, w, h
    return 'c%d' % INNER, y + AMMO_DY - row * STRIP_STEP, w, h


def patch_meter(root, rel):
    fname = rel.split('/')[-1]
    body = next(e[1] for e in root if isinstance(e[1], list))
    top = find(body, 'HudItemEffectMeter')
    row = METER_ROW.get(fname, 0)
    x, y, w, h = strip_box(row)
    put(top, x, y, w, h)
    kv.set(top, 'xpos_minmode', strip_box(row, True)[0])
    kv.set(top, 'ypos_minmode', strip_box(row, True)[1])
    for key in [e[0] for e in top if e[0].lower().startswith(('x_offset', 'y_offset'))]:
        kv.remove(top, key)
    based = any(e[0].lower() == '#base' for e in root)
    if based and kv.find(body, 'ItemEffectMeterBG') is None:
        return  # a #base file (Pyro) takes the generic strip as it is: only its row differs
    bg = find(body, 'ItemEffectMeterBG')
    kv.setmany(bg, xpos=0, ypos=0, zpos=0, wide=w, tall=h, scaleImage=1, visible=1, **team_keys('ig_strip'))
    lx, ly, lw, lh = STRIP_LABEL
    lab = kv.find(body, 'ItemEffectMeterLabel')
    if lab is not None:
        kv.setmany(lab, xpos=lx, ypos=ly, zpos=2, wide=lw, tall=lh, font='RK_StripLabel', textAlignment='west',
                   textinsetx=0, autoResize=0, visible=1)
    lab2 = kv.find(body, 'ItemEffectMeterLabel2')
    if lab2 is not None:
        kv.setmany(lab2, xpos=0, ypos=0, wide=0, tall=0)
    bx, by, bw, bh = STRIP_BAR
    bar = kv.find(body, 'ItemEffectMeter')
    count = kv.find(body, 'ItemEffectMeterCount')
    bar_shown = bar is not None and kv.get(bar, 'visible') != '0'
    if bar is not None:
        kv.setmany(bar, xpos=bx, ypos=by, zpos=2, wide=bw, tall=bh, bgcolor_override='118 116 120 255',
                   fgcolor_override='255 255 255 255')
    if bar_shown:
        kv.add_block(body, 'RK_BarMul', timg('RK_BarMul', bx, by, bw, bh, 'ig_bar_mul', z=3))
    if count is not None:
        # a count (revenge crits, heads, organs...) in the middle of the strip, clear of the name on its left
        nx, ny, nw, nh = STRIP_COUNT
        align = 'center'
        if bar_shown:  # the kart: count right of the bar
            nx, nw, align = bx + bw + 1, w - bx - bw - 2, 'west'
        kv.setmany(count, xpos=nx, ypos=ny, zpos=4, wide=nw, tall=nh, font='RK_StripNum', fgcolor='RK_Text',
                   textAlignment=align, textinsetx=0, autoResize=0)
    for i in range(1, 4):  # heavy kill-combo class icons: small, right of the bar
        blk = kv.find(body, 'KillComboClassIcon%d' % i)
        if blk is not None:
            kv.setmany(blk, xpos=bx + (i - 1) * 9, ypos=by - 1, zpos=4, wide=8, tall=8)
    icon = kv.find(body, 'ItemEffectIcon')  # MvM canteen
    if icon is not None:
        kv.setmany(icon, xpos=bx + bw - 11, ypos=1, wide=11, tall=11, zpos=4)


def center_box(alt=False):
    """The centre strip (sticky bombs, ÜberCharge, metal): in CENTRED on the cards' line between them."""
    return CENTER if alt else (CENTER[0], CENTRE_LINE - STRIP[3] // 2)


def patch_pipes(root):
    """Stickies: the STICKY strip with the count; with a shield the same panel shows the CHARGE strip and its bar
    (the game swaps the bar in and the sticky panels out)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    w, h = STRIP[2], STRIP[3]
    kv.setmany(kv.find(body, 'background'), xpos=0, ypos=0, zpos=0, wide=w, tall=h, scaleImage=1,
               **team_keys('ig_strip_charge'))
    kv.setmany(kv.find(body, 'ChargeLabel'), xpos=0, ypos=0, wide=0, tall=0, visible=0)
    bx, by, bw, bh = STRIP_BAR
    kv.setmany(kv.find(body, 'ChargeMeter'), xpos=bx, ypos=by, zpos=1, wide=bw, tall=bh,
               fgcolor_override='255 255 255 255', bgcolor_override='118 116 120 255')
    kv.add_block(body, 'RK_BarMul', timg('RK_BarMul', bx, by, bw, bh, 'ig_bar_mul', z=2))
    for panel, color in (('PipesPresentPanel', 'RK_Text'), ('NoPipesPresentPanel', 'RK_Grey')):
        pnl = kv.find(body, panel)
        if pnl is None:
            continue
        kv.setmany(pnl, xpos=0, ypos=0, zpos=3, wide=w, tall=h)
        kv.setmany(kv.find(pnl, 'PipeIcon'), xpos=0, ypos=0, wide=0, tall=0)
        kv.add_block(pnl, 'RK_PipesStrip', timg('RK_PipesStrip', 0, 0, w, h, 'ig_strip_sticky', z=0))
        # the count in the middle of the strip (STICKY on its left)
        for n, fg in (('NumPipesLabel', color), ('NumPipesLabelDropshadow', '0 0 0 0')):
            blk = kv.find(pnl, n)
            if blk is not None:
                kv.setmany(blk, xpos=STRIP_COUNT[0], ypos=STRIP_COUNT[1], wide=STRIP_COUNT[2], tall=STRIP_COUNT[3],
                           zpos=2, font='RK_StripNum', fgcolor=fg, textAlignment='center', textinsetx=0)
    # a layout switch reloads the HUD and the game refreshes the count only when it changes: the count panel waits
    # hidden for the game, the none-out panel says 0 by itself
    kv.set(kv.find(body, 'PipesPresentPanel'), 'visible', 0)
    for n in ('NumPipesLabel', 'NumPipesLabelDropshadow'):
        kv.set(kv.find(kv.find(body, 'NoPipesPresentPanel'), n), 'labelText', '0')


def patch_charge(root):
    """Sticky launcher, Huntsman and Dragon's Fury charge-up (HudDemomanCharge.res, HudBowCharge.res,
    HudFlameRocketCharge.res): a plain white bar on its faint white track, as long as the centre strip above it
    (patch_hudlayout), the same on both teams."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.setmany(find(body, 'ChargeMeter'), ControlName='ContinuousProgressBar', fieldName='ChargeMeter', xpos=0, ypos=0,
               zpos=1, wide=STRIP[2], tall=CHARGE_H, visible=1, enabled=1, fgcolor_override='236 232 232 255',
               bgcolor_override='236 232 232 45')
    kv.remove(body, 'RK_ChargeMul')


UBER_NUM = (u(68), 1, 14, 11)   # the percent, right of the ÜBER label


def patch_uber(root):
    """ÜberCharge (0.9): the Über card, its 22-segment bar under the label, the percent large at the right. The
    Vaccinator's four charges take the bar's place (the game paints them white; the Modulate sheet turns them
    crimson), its resist icon in the card's top left corner."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    w, h = UBER_CARD
    bg = kv.find(body, 'Background')
    kv.setmany(bg, xpos=0, ypos=0, zpos=0, wide=w, tall=h, scaleImage=1, **team_keys('ig_uber_card'))
    for key in ('teambg_2_lodef', 'teambg_3_lodef'):
        kv.remove(bg, key)
    nx, ny, nw, nh = UBER_PCT
    for n, text in (('ChargeLabel', '%charge%'), ('IndividualChargesLabel', '%charge_count%')):
        kv.setmany(kv.find(body, n), labelText=text, xpos=nx, ypos=ny, zpos=4, wide=nw - 6, tall=nh, font='RK_UberNum',
                   fgcolor='RK_Text', textAlignment='east', textinsetx=0)
    kv.remove(body, 'RK_UberPct')
    kv.add_block(body, 'RK_UberPct', {'ControlName': 'CExLabel', 'fieldName': 'RK_UberPct', 'xpos': nx + nw - 6,
                                      'ypos': ny + 6, 'zpos': 4, 'wide': 8, 'tall': 10, 'visible': 1, 'enabled': 1,
                                      'labelText': '%', 'font': 'RK_StreakNum', 'fgcolor': '138 132 138 255',
                                      'textAlignment': 'west', 'textinsetx': 0, 'mouseinputenabled': 0})
    blk = kv.find(body, 'HealthClusterIcon')
    if blk is not None:
        kv.setmany(blk, xpos=0, ypos=0, wide=0, tall=0)
    bx, by, bw, bh = UBER_BAR
    gap = 1
    seg = (bw - 3 * gap) // 4
    for i in range(4):
        sx = bx + i * (seg + gap)
        blk = kv.find(body, 'ChargeMeter%d' % (i + 1))
        if blk is not None:
            kv.setmany(blk, xpos=sx, ypos=by, zpos=2, wide=seg if i < 3 else bx + bw - sx, tall=bh,
                       bgcolor_override='118 116 120 255')
    kv.setmany(kv.find(body, 'ChargeMeter'), xpos=bx, ypos=by, zpos=2, wide=bw, tall=bh,
               fgcolor_override='255 255 255 255', bgcolor_override='118 116 120 255')
    kv.remove(body, 'RK_UberMul')
    kv.add_block(body, 'RK_UberMul', timg('RK_UberMul', bx, by, bw, bh, 'ig_uber_mul', z=3))
    kv.remove(body, 'RK_UberReady')
    kv.add_block(body, 'RK_UberReady', timg('RK_UberReady', 0, 0, w, h, 'ig_uber_ready', z=6, alpha=0))
    blk = kv.find(body, 'ResistIcon')
    if blk is not None:  # the game pins it to the panel's top left
        kv.setmany(blk, xpos=0, ypos=0, zpos=5, wide=10, tall=10)


ACCOUNT_RISE = 36   # the metal panel reaches this far above its strip: the +/- metal numbers float up in it


def patch_account(root):
    """The engineer's metal: the METAL strip over the ammo card, in the first row of the item meters (the engineer's
    own meters, revenge crits and the Pomson, sit a row up: METER_ROW), the count in its middle; the +/- metal
    floats up from right of it."""
    body = kv.find(root, 'Resource/UI/HudAccountPanel.res')
    w, h = STRIP[2], STRIP[3]
    kv.setmany(kv.find(body, 'CHudAccountPanel'), delta_item_x=w // 2 + 12, delta_item_start_y=ACCOUNT_RISE - 6,
               delta_item_end_y=2, PositiveColor='236 232 232 255', NegativeColor='255 52 76 255',
               delta_item_font='RK_StripNum')
    kv.setmany(kv.find(body, 'AccountBG'), xpos=0, ypos=ACCOUNT_RISE, wide=w, tall=h, scaleImage=1,
               **team_keys('ig_strip_metal'))
    kv.setmany(kv.find(body, 'MetalIcon'), xpos=0, ypos=0, wide=0, tall=0)
    nx, ny, nw, nh = STRIP_COUNT
    kv.setmany(kv.find(body, 'AccountValue'), xpos=nx, ypos=ACCOUNT_RISE + ny, wide=nw, tall=nh, font='RK_StripNum',
               fgcolor='RK_Text', textAlignment='center', textinsetx=0)


def patch_damage(root):
    body = kv.find(root, 'Resource/UI/HudDamageAccount.res')
    # 0.9 (preview 05): the damage you deal large and white (outlined, it floats over the map), heals in cyan
    kv.setmany(kv.find(body, 'CDamageAccountPanel'), PositiveColor='0 214 255 255', NegativeColor='246 242 242 255',
               delta_lifetime='1.6', delta_item_font='RK_Damage', delta_item_font_big='RK_DamageBig')


# ------------------------------------------------------------------ target ID
def patch_targetid(root):
    """(806, 600)-(1114, 648): the team bar, the name, the second line, the health with its 8-segment gauge.
    game: the game puts the health tile left of the name and sizes the card to the name, so the health block sits at
    the left end instead of the right; the name is drawn white (Label.TextColor) by the game."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.setmany(kv.find(body, 'TargetIDBG'), xpos=0, ypos=0, tall=TID_H, image=T + 'ig_tid_ink',
               teambg_1=T + 'ig_tid_ink', teambg_2=T + 'ig_tid_red', teambg_3=T + 'ig_tid_blue')
    for n, image in (('TargetIDBG_Spec_Blue', 'ig_tid_blue'), ('TargetIDBG_Spec_Red', 'ig_tid_red')):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, image=T + image, tall=TID_H, src_corner_width=0, src_corner_height=0, draw_corner_width=0,
                       draw_corner_height=0)
    # the health tag (a building's; a player's floats over their head, patch_health_icon), centred in the card's height
    kv.setmany(kv.find(body, 'SpectatorGUIHealth'), xpos=2, ypos=(TID_H - TAG[1]) // 2, wide=TAG[0], tall=TAG[1])
    kv.setmany(kv.find(body, 'TargetNameLabel'), ypos=2, tall=11, font='RK_TidName', textinsetx=0)
    kv.setmany(kv.find(body, 'TargetDataLabel'), ypos=13, tall=6, font='RK_TidData', textinsetx=0)
    # an engineer looking at a building of theirs: the key that picks it up, in a sub panel the game puts right of
    # the card and makes as tall as the card. The game stacks its pictures up from the key's label (the arrows over
    # it, the building over the arrows); the stock label sat 22 units down, below the card's foot (TID_H), where it
    # was cut off. The label sits in the card's lower half now, the building over it, the arrows left out
    mv = kv.find(body, 'MoveableSubPanel')
    if mv is not None:
        # a plain vgui Label: fgcolor_override (fgcolor is CExLabel only)
        kv.setmany(kv.find(mv, 'MoveableKeyLabel'), ypos=TID_H - 9, tall=8, font='RK_SlotTime',
                   fgcolor_override='RK_Text')
        kv.setmany(kv.find(mv, 'MoveableSymbolIcon'), wide=0, tall=0)
        kv.setmany(kv.find(mv, 'MoveableIcon'), wide=10, tall=10)
    for key in ('font_minmode', 'ypos_minmode', 'xpos_minmode'):
        for n in ('TargetNameLabel', 'TargetDataLabel'):
            kv.remove(kv.find(body, n), key)


def patch_spec_health(root, font='RK_TidHealth'):
    """The health tag (SpectatorGUIHealth.res): the target ID's for buildings and the one the game floats over the
    head of the player you look at (patch_health_icon). The number on black glass and, right of it, a 6-segment gauge
    that fills from the bottom in the team's colour as the health does (crimson on RED, azure on BLU).
    game: the fill is hud/health_color, which Valve's servers keep stock (a cross), and the code paints it white. Its
    panel is three gauges wide, centred on the gauge (see GAUGE_FILL), and the tag's opaque glass goes over it with a
    window on the gauge (tex_tag_plate): only the cross's upright shows, a plain bar, and the arms vanish under the
    glass. Under the fill the gauge's faint segments; over the gauge alone a Modulate sheet that tints it and cuts it
    into segments (the fill's right third, past the tag's edge, is clipped by the tag's panel)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    w, h = TAG
    gx, gy, gw, gh = TAG_GAUGE
    fx, fy, fw, fh = TAG_GAUGE_FILL
    blk = kv.find(body, 'PlayerStatusHealthBonusImage')
    if blk is not None:
        kv.setmany(blk, zpos=1, image=T + 'blank', xpos=0, ypos=0, wide=w, tall=h)
    blk = kv.find(body, 'PlayerStatusHealthImageBG')
    if blk is not None:
        kv.setmany(blk, zpos=1, image=T + 'ig_tag_track', xpos=gx, ypos=gy, wide=gw, tall=gh)
    bld = kv.find(body, 'BuildingStatusHealthImageBG')
    if bld is not None:
        kv.setmany(bld, wide=0, tall=0)
    fill = kv.find(body, 'PlayerStatusHealthImage')
    if fill is not None:
        kv.setmany(fill, zpos=2, xpos=fx, ypos=fy, wide=fw, tall=fh)
        kv.add_block(body, 'RK_HealthMul', timg('RK_HealthMul', gx, gy, gw, gh, 'ig_tag_mul', z=3))
        kv.add_block(body, 'RK_TagPlate', timg('RK_TagPlate', 0, 0, w, h, 'ig_tag_plate', z=4))
    _health_value(body)
    val = kv.find(body, 'RK_HealthValue')
    if val is not None:  # centred on the glass left of the gauge
        kv.setmany(val, xpos=1, ypos=0, zpos=5, wide=gx - 1, tall=h, font=font, fgcolor='RK_Text',
                   textAlignment='center', textinsetx=0)
    lvl = kv.find(body, 'PlayerStatusPlayerLevel')
    if lvl is not None:
        kv.setmany(lvl, xpos=0, ypos=0, wide=0, tall=0)


def patch_health_icon(root):
    """HealthIconPanel.res: the panel the game floats over the head of the player you look at (centred on its
    width, its foot over the head), sized to the health tag."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for name in ('HealthIcon', 'SpectatorGUIHealth'):
        blk = kv.find(body, name)
        if blk is not None:
            kv.setmany(blk, xpos=0, ypos=0, wide=TAG[0], tall=TAG[1])
            for key in ('xpos_minmode', 'ypos_minmode'):
                kv.remove(blk, key)


def _health_value(body):
    # renamed: the main health digits' flash (HudHealthDyingPulse) finds its label by name; the game fills this one
    # through %Health%, not by name
    for ent in body:
        if ent[0] == 'PlayerStatusHealthValue' and isinstance(ent[1], list):
            ent[0] = 'RK_HealthValue'
            kv.set(ent[1], 'fieldName', 'RK_HealthValue')


TID_GAUGE = (24, 4, 3, 13)   # right of the number; its fill's black outer thirds stay clear of the digits
TID_GAUGE_FILL = (TID_GAUGE[0] - TID_GAUGE[2], TID_GAUGE[1], TID_GAUGE[2] * 3, TID_GAUGE[3])   # see GAUGE_FILL


def patch_tournament_health(root, font='RK_TidHealth'):
    """The tournament spectator panel's health (SpectatorTournamentGUIHealth.res), on its dark player card: the
    number with an 8-segment gauge right of it (its Modulate sheet blacks out the stock cross's arms)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    gauge = TID_GAUGE
    for name, z, image in (('PlayerStatusHealthBonusImage', 1, 'blank'), ('PlayerStatusHealthImageBG', 2, 'ig_tid_track')):
        blk = kv.find(body, name)
        if blk is not None:
            kv.setmany(blk, zpos=z, image=T + image, xpos=gauge[0], ypos=gauge[1], wide=gauge[2], tall=gauge[3])
    bld = kv.find(body, 'BuildingStatusHealthImageBG')
    if bld is not None:
        kv.setmany(bld, wide=0, tall=0)
    fill = kv.find(body, 'PlayerStatusHealthImage')
    if fill is not None:
        fx, fy, fw, fh = TID_GAUGE_FILL
        kv.setmany(fill, zpos=3, xpos=fx, ypos=fy, wide=fw, tall=fh)
        kv.add_block(body, 'RK_HealthMul', img('RK_HealthMul', fx, fy, fw, fh, 'ig_tid_mul', z=4))
    _health_value(body)
    val = kv.find(body, 'RK_HealthValue')
    if val is not None:
        kv.setmany(val, xpos=0, ypos=3, zpos=5, wide=20, tall=15, font=font, fgcolor='RK_Text', textAlignment='east',
                   textinsetx=0)
    lvl = kv.find(body, 'PlayerStatusPlayerLevel')
    if lvl is not None:
        kv.setmany(lvl, xpos=0, ypos=0, wide=0, tall=0)


# ------------------------------------------------------------------ top: timer, teammates' slots, CTF scores
SLOT = (18, 20)   # a teammate's slot: the class portrait, and under it a 3-unit health bar on a crimson track
PORTRAIT_H = 14   # the portrait's height in it


def patch_matchstatus(root):
    body = next(e[1] for e in root if isinstance(e[1], list))
    frame = kv.find(body, 'BGFrame')
    if frame is not None:
        # the match's frame is bare: the timer box is the timer's own picture (patch_timepanel), and in CTF the flag
        # panel's, under its scores (patch_flag_scores); one here would cover those
        kv.remove(frame, 'border')
        kv.setmany(frame, xpos='cs-0.5', ypos=0, wide=59, tall=26, paintborder=0, paintbackground=0)
        kv.remove(body, 'RK_MatchBox')
    timer = kv.find(body, 'ObjectiveStatusTimePanel')
    if timer is not None:
        # outside a match (community servers) the timer sat 24 units down with the stock plate: now it is the same
        # box at the top, between the teammates' slots (its box is drawn by HudObjectiveTimePanel.res)
        kv.set(timer, 'ypos', 0)
        m = kv.find(timer, 'if_match')
        if m is not None:
            kv.setmany(m, xpos='cs-0.5', ypos=0, wide=59)
        val = kv.find(timer, 'TimePanelValue')
        if val is not None:
            kv.setmany(val, proportionaltoparent=1, xpos='cs-0.5', ypos=TIMER_Y, wide=TIMER[0], tall=18,
                       font='RK_Timer')
            vm = kv.find(val, 'if_match')
            if vm is not None:
                kv.setmany(vm, xpos='cs-0.5', ypos=TIMER_Y, wide=TIMER[0], tall=18, font='RK_Timer')
            kv.set(val, 'fgcolor', 'RK_Text')
    status = kv.find(body, 'TeamStatus')
    if status is None:
        return
    # six a side: 40 px slots 6 px apart either side of the timer box, (612..882) and (1032..1302) px. A full 12 a
    # side squeezes them to fit (the game's own rule), as the stock strip does
    kv.setmany(status, max_size=SLOT[0], **{'6v6_gap': 2, '12v12_gap': 1}, team1_base_x='c-35', team2_base_x='c32',
               team1_max_expand=133, team2_max_expand=133)
    pp = kv.find(status, 'playerpanels_kv')
    if pp is None:
        return
    kv.setmany(pp, wide=SLOT[0], tall=SLOT[1], ypos=4, **{
        'color_portrait_bg_red': '255 120 104 255', 'color_portrait_bg_blue': '112 164 232 255',
        'color_portrait_bg_red_dead': '255 120 104 90', 'color_portrait_bg_blue_dead': '112 164 232 90',
        'color_bar_health_high': '236 232 232 255', 'color_bar_health_med': '255 186 40 255',
        'color_bar_health_low': '255 52 76 255', 'color_portrait_blend_dead_red': '200 200 200 255',
        'color_portrait_blend_dead_blue': '200 200 200 255'})  # the game's grey portrait of a dead player's class
    kv.remove(pp, 'RK_PortraitFrame')
    kv.add_block(pp, 'RK_SlotBG', img('RK_SlotBG', 0, 0, 'f0', 'f0', 'ig_slot', z=-1, proportionaltoparent=1))
    # the team bar along the slot's top is the panel the game colours per team
    blk = kv.find(pp, 'classimagebg')
    if blk is not None:
        kv.setmany(blk, xpos=0, ypos=0, wide='f0', tall=1, zpos=1, proportionaltoparent=1)
    blk = kv.find(pp, 'classimage')
    if blk is not None:
        kv.setmany(blk, xpos='cs-0.5', ypos=1, wide='o1', tall=PORTRAIT_H, zpos=2, proportionaltoparent=1)
    kv.remove(pp, 'RK_SlotDots')
    kv.add_block(pp, 'RK_SlotDots', img('RK_SlotDots', 0, 1, 'f0', PORTRAIT_H, 'ig_slot_dots', z=3,
                                        proportionaltoparent=1))
    for n in ('healthbar', 'overhealbar'):
        blk = kv.find(pp, n)
        if blk is not None:
            kv.setmany(blk, xpos=1, ypos=PORTRAIT_H + 2, wide='f2', tall=3, zpos=3, proportionaltoparent=1)
    blk = kv.find(pp, 'healthbar')
    if blk is not None:
        kv.set(blk, 'bgcolor_override', '74 16 26 255')   # the health they are missing
    # a dead player's slot: the game's grey portrait of their class under a thin veil of static (tex_slot_x), a
    # teammate's respawn seconds in its bottom right corner, clear of the face. The game slid the stock death panel
    # and the seconds 19-21 units down (TeamStatus_PlayerDead), off the bottom of our 20-unit slot, so neither
    # showed; the HUD's own TeamStatus events (build.py ANIMS) keep them on the slot. The game also re-sets
    # DeathPanel's picture to its stock plate on every death, so the veil is SkullPanel and DeathPanel stays empty
    blk = kv.find(pp, 'respawntime')
    if blk is not None:
        kv.setmany(blk, xpos=0, ypos=1, wide='f0', tall=PORTRAIT_H, zpos=6, font='RK_SlotTime', fgcolor='RK_Text',
                   textAlignment='south-east', textinsetx=1, proportionaltoparent=1)
    blk = kv.find(pp, 'DeathPanel')
    if blk is not None:
        kv.setmany(blk, xpos=0, ypos=0, wide=0, tall=0, zpos=5, image=T + 'blank', scaleImage=1,
                   proportionaltoparent=1)
    blk = kv.find(pp, 'SkullPanel')
    if blk is not None:
        kv.setmany(blk, xpos=0, ypos=0, wide='f0', tall='f0', zpos=5, image=T + 'ig_slot_x', scaleImage=1,
                   proportionaltoparent=1)


TIMER = (59, 26)   # the timer box, units
KOTH_PANEL = 100   # KOTH's timer panels are this wide (stock), both centred on the box in a match
TIMER_Y = u(26) - 9
TIMER_LABELS = ('WaitingForPlayers', 'Overtime', 'SuddenDeath', 'Setup', 'ServerTimeLimit')
GOAL_Y = TIMER[1] + 1   # CTF's "PLAYING TO 3", right under the timer box (build.py, patch_flagpanel)
STATE_Y = GOAL_Y + 9    # the timer's state line under it


def patch_timepanel(root):
    """The round timer's own file, shared by the main timer and KOTH's two. The game paints the stock plate with
    a team-coloured picture of its choosing, so that plate (and its progress ring) goes and the box is an image of
    ours, in a match too (in a match KOTH's two timers share one spot, so their boxes are one). Waiting for players,
    setup, overtime, sudden death and the server's time limit go under the box in the HUD's mono caps, without their
    plates."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for n in ('TimePanelBG', 'TimePanelProgressBar'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, wide=0, tall=0)
    kv.add_block(body, 'RK_TimerBG', timg('RK_TimerBG', 'cs-0.5', 0, TIMER[0], TIMER[1], 'ig_timer', z=1,
                                          proportionaltoparent=1))
    for name in TIMER_LABELS:
        label = kv.find(body, name + 'Label')
        if label is not None:
            kv.setmany(label, proportionaltoparent=1, xpos=0, ypos=STATE_Y, wide='f0', tall=8, zpos=5,
                       font='RK_StripLabel', allcaps=1, textAlignment='center', fgcolor='RK_Text')
            m = kv.find(label, 'if_match')
            if m is not None:
                kv.setmany(m, xpos=0, ypos=STATE_Y, wide='f0', font='RK_StripLabel')
        plate = kv.find(body, name + ('LabelBG' if name == 'ServerTimeLimit' else 'BG'))
        if plate is not None:
            kv.setmany(plate, wide=0, tall=0)


def patch_roundcounter(root):
    """The round counter's plate (comp_round_timer: a blue and red trapezoid with a tan rim) sat over the timer
    box at the top; the box is ours (RK_TimerBG, or the match status' frame), so the plate goes. The round dots and
    win lights stay where the game puts them."""
    body = root[0][1] if root and isinstance(root[0][1], list) else root
    blk = kv.find(body, 'Background')
    if blk is not None:
        kv.setmany(blk, visible=0, wide=0, tall=0, image=T + 'blank')


def patch_koth_timers(root):
    """KOTH's two timers outside a match: the same box (from the timer file), the time in each team's colour since
    the box no longer carries it."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for name, color in (('BlueTimer', '112 164 232 255'), ('RedTimer', '255 120 104 255')):
        blk = kv.find(body, name)
        if blk is None:
            continue
        kv.set(blk, 'ypos', 0)
        val = kv.find(blk, 'TimePanelValue')
        if val is not None:
            kv.setmany(val, proportionaltoparent=1, xpos='cs-0.5', ypos=TIMER_Y, wide=TIMER[0], tall=18,
                       font='RK_Timer', fgcolor=color)
            # in a match (casual) both timers share one box at the top: its blue half and its red half, each time
            # above the box's ROUND TIME line (the stock spot put them on it, one over the other)
            m = kv.find(val, 'if_match')
            if m is None:
                m = kv.add_block(val, 'if_match', {})
            half = TIMER[0] // 2
            kv.setmany(m, xpos=(KOTH_PANEL // 2 - half) if name == 'BlueTimer' else KOTH_PANEL // 2 + 1,
                       ypos=TIMER_Y, wide=half - 1, tall=18, font='RK_TimerHalf',
                       textAlignment='east' if name == 'BlueTimer' else 'west')
            for k in ('xpos_minmode', 'wide_minmode', 'font_minmode', 'font_lodef', 'ypos_minmode'):
                kv.remove(m, k)
        if name == 'RedTimer':  # in a match both timers share the spot: one box (the blue one's) is enough
            kv.add_block(blk, 'RK_TimerBG', {'if_match': [['visible', '0', None], ['wide', '0', None]]})


def patch_flag_scores(body):
    """CTF: the two captures in the timer box, either side of the time and level with it, bright in their team's
    colours. They belong to the flag panel, which the game draws under the match status (it holds the match-start
    doors, which have to cover the whole HUD), so the flag panel draws the box itself, under the scores: the match
    status leaves the box to the timer (patch_timepanel), which CTF has none of. Not in Mann vs. Machine, which has
    its own panel up there."""
    box = timg('RK_FlagBox', 'cs-0.5', 0, TIMER[0], TIMER[1], 'ig_timer', z=0, proportionaltoparent=1)
    box['if_mvm'] = [['visible', '0', None]]
    kv.remove(body, 'RK_FlagBox')
    kv.add_block(body, 'RK_FlagBox', box)
    for n, x, color, align in (('BlueScore', 'c-27', '128 178 255 255', 'west'),
                               ('RedScore', 'c13', '255 92 104 255', 'east')):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, xpos=x, ypos=TIMER_Y + 1, wide=14, tall=16, font='RK_TopScore', fgcolor=color,
                       textAlignment=align, zpos=5)
        sh = kv.find(body, n + 'Shadow')
        if sh is not None:
            kv.setmany(sh, xpos=0, ypos=0, wide=0, tall=0, visible=0)


# ------------------------------------------------------------------ hudlayout
FEED_RIGHT = u(1920 - 1890)


def patch_hudlayout(body):
    # The match status keeps the game's zpos (3): it holds the match-start and match-end doors, which have to cover
    # the whole HUD; everything of ours below it draws at 2 or under (the win panel is 4)
    x, y, w, h = ammo_box()
    ammo = kv.find(body, 'HudWeaponAmmo')
    kv.setmany(ammo, xpos=x, ypos=y, wide=w, tall=h)
    ax, ay, _, _ = ammo_box(True)
    for key, v in (('xpos_minmode', ax), ('ypos_minmode', ay)):
        kv.set(ammo, key, v)
    cx, cy = center_box()
    acx, acy = center_box(True)
    blk = kv.find(body, 'HudMedicCharge')
    if blk is not None:   # 0.9: the Über card, centred under the crosshair, on the cards' line
        uw, uh = UBER_CARD
        kv.setmany(blk, xpos=f'c-{uw // 2}', ypos=CENTRE_LINE - uh // 2, wide=uw, tall=uh, zpos=2)
        kv.set(blk, 'xpos_minmode', f'c-{uw // 2}')
        kv.set(blk, 'ypos_minmode', CENTER[1] + STRIP[3] - uh)
    for n in ('HudDemomanPipes',):
        blk = kv.find(body, n)
        if blk is None:
            continue
        # under the win panel (zpos 4): the strip sits where its list of top players goes at the round's end
        kv.setmany(blk, xpos=cx, ypos=cy, wide=STRIP[2], tall=STRIP[3], zpos=2)
        kv.set(blk, 'xpos_minmode', acx)
        kv.set(blk, 'ypos_minmode', acy)
    # the engineer's metal: the first item meter row over the ammo card (patch_account)
    blk = kv.find(body, 'CHudAccountPanel')
    if blk is not None:
        sx, sy, sw, sh = strip_box(0)
        kv.setmany(blk, xpos=sx, ypos=sy - ACCOUNT_RISE, wide=sw, tall=sh + ACCOUNT_RISE, zpos=2)
        asx, asy, _, _ = strip_box(0, True)
        kv.set(blk, 'xpos_minmode', asx)
        kv.set(blk, 'ypos_minmode', asy - ACCOUNT_RISE)
    # sticky launcher / bow / flame-rocket charge-up: a segmented bar right under the centre strip, as long as it
    # (patch_charge lays the bar out in its panel)
    for n in ('HudDemomanCharge', 'HudBowCharge', 'HudFlameRocketCharge'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, zpos=2, xpos=cx, ypos=cy + STRIP[3] + 2, wide=STRIP[2], tall=CHARGE_H)
            kv.set(blk, 'xpos_minmode', acx)
            kv.set(blk, 'ypos_minmode', acy + STRIP[3] + 2)
            for key in ('wide_minmode', 'tall_minmode'):
                kv.remove(blk, key)
    meter = kv.find(body, 'HudItemEffectMeter')
    if meter is not None:
        sx, sy, sw, sh = strip_box()
        kv.setmany(meter, xpos=sx, ypos=sy, wide=sw, tall=sh)
    for n, ty in (('CMainTargetID', TID_Y), ('CSpectatorTargetID', TID_Y - 40), ('CSecondaryTargetID', TID_Y + TID_H + 3)):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, ypos=ty, tall=TID_H)
            for key in ('tall_minmode', 'ypos_minmode'):
                kv.remove(blk, key)
            for sub in blk:
                if isinstance(sub[1], list):
                    kv.remove(sub[1], 'ypos')
    # kill feed: right edge 30 px in, from 72 px down, slim rows close together with square ends, in a hard
    # condensed face. The game paints each row as one flat colour from these keys (no pictures, no team of its own),
    # so the look is in the colours: cold ink rows, the names in neon team colours, and your own rows lit up like a
    # selected line, near white with dark lettering. The game draws the weapon icons of your rows dark (its inverted
    # set, made for its light rows), which a dark row hid; and a white row is no team's colour, so it reads the same
    # on RED and BLU. The game blends in linear light, so the ink needs a high alpha to look as dark as designed
    dn = kv.find(body, 'HudDeathNotice')
    kv.setmany(dn, xpos='r%d' % (630 + FEED_RIGHT), ypos=u(72), wide=630, tall=300, MaxDeathNotices=5,
               IconScale='0.35', LineHeight=13, LineSpacing=2, CornerRadius=0, RightJustify=1,
               TextFont='RK_Feed', TeamBlue='58 146 255 255', TeamRed='255 64 86 255',
               IconColor='236 232 232 255', LocalPlayerColor='16 14 20 255', BaseBackgroundColor='10 10 15 232',
               LocalBackgroundColor='236 234 242 242')
    # chat: the preview's first line starts 60 px in, the newest one ends 769 px down
    chat = kv.find(body, 'HudChat')
    if chat is not None:
        kv.setmany(chat, xpos=CHAT[0], ypos=CHAT[1], wide=CHAT[2], tall=CHAT[3])
    for n in ('HudVoiceSelfStatus',):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, xpos=centred(CARD[0] + CARD[2] + 4), ypos=CARD[1] + 22 + HEALTH_DY)
            kv.set(blk, 'xpos_minmode', CARD[0] + CARD[2] + 4)
            kv.set(blk, 'ypos_minmode', CARD[1] + 22)


CHAT = (17, 225, 300, 112)   # ends 23 units above the health card (it ran onto it)


def patch_chat(root):
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.setmany(kv.find(body, 'HudChat'), xpos=CHAT[0], ypos=CHAT[1], wide=CHAT[2], tall=CHAT[3])
    # the open chat as one of the HUD's cards (it was the stock grey box): ink glass with the crimson frame, the
    # history on a darker well, the filter button in flat ink, crimson on hover
    # no border: a border is drawn while the chat is closed too (a frame stood on the left of the screen)
    kv.setmany(kv.find(body, 'HudChat'), PaintBackgroundType=0, bgcolor_override='9 9 11 225', paintborder=0)
    hist = kv.find(body, 'HudChatHistory')
    if hist is not None:
        kv.setmany(hist, bgcolor_override='0 0 0 110', fgcolor_override='236 232 232 255')
    line = kv.find(body, 'ChatInputLine')
    if line is not None:
        kv.setmany(line, bgcolor_override='0 0 0 0', fgcolor_override='236 232 232 255')
    btn = kv.find(body, 'ChatFiltersButton')
    if btn is not None:
        kv.setmany(btn, paintbackground=1, defaultBgColor_override='16 16 18 235', armedBgColor_override='160 18 34 255',
                   depressedBgColor_override='224 26 46 255', defaultFgColor_override='236 232 232 255',
                   armedFgColor_override='255 255 255 255', depressedFgColor_override='7 7 9 255', paintborder=0)


CHAT_ANIMS = '''
// casual / competitive matches move the chat to the stock spot on their own; keep it where the HUD puts it
event CompetitiveGame_LowerChatWindow
{
	Animate HudChat ypos %d Accel 0 0
}
event CompetitiveGame_RestoreChatWindow
{
	Animate HudChat ypos %d Accel 0 0
}
''' % (CHAT[1], CHAT[1])
