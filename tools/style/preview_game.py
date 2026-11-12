"""In-game style preview for the Reaper HUD, over a cleaned-up game screenshot.

    python tools/style/preview_game.py      -> docs/style-ingame.jpg
"""
import os

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

import rart
from ui_kit import (GREY, HOT, INK, K, PANEL, RED, RED_DEEP, RED_DIM, TEAM_BLU, TEAM_RED, WHITE,
                    Canvas, F, label, panel, rgba, seg_bar, vseg_bar)

W, H = 1920, 1080
HERE = os.path.dirname(os.path.abspath(__file__))
SHOT = os.path.join(HERE, 'game_src.jpg')  # a 2Fort screenshot
def backdrop():
    """The screenshot (its old HUD, chat and scoreboard avatars already painted out), softened and darkened so
    the HUD reads first."""
    im = Image.open(SHOT).convert('RGB')
    im = im.filter(ImageFilter.GaussianBlur(1.1))
    im = ImageEnhance.Color(im).enhance(0.55)
    a = np.asarray(im, np.float32) / 255
    a *= 0.58
    a[..., 0] *= 1.10
    a[..., 2] *= 0.92
    return rart.to_image(a)


def crosshair(cv, cx=960, cy=540):
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        cv.line([(cx + dx * 6, cy + dy * 6), (cx + dx * 13, cy + dy * 13)], rgba(WHITE, 230), 2)
    cv.rect(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, rgba(HOT))


def big_number(cv, x, y, s, size, anchor='ls'):
    """Health / ammo digits: a red ghost a few pixels left (a second label in game) and a soft red bloom."""
    f = F('raj7', size)
    cv.glow_text(x, y, s, f, RED, radius=10, strength=0.55, anchor=anchor)
    cv.text(x - 3, y, s, f, rgba(RED, 170), anchor)
    cv.text(x, y, s, f, rgba(WHITE), anchor)


def portrait(cv, x0, y0, x1, y1):
    src = Image.open(os.path.join(HERE, 'portrait_src.jpg')).convert('RGB')  # the 3D soldier, from the same match
    src = src.resize((int((x1 - x0) * K), int((y1 - y0) * K)), Image.LANCZOS)
    a = np.asarray(src, np.float32) / 255
    lum = a @ np.array([0.3, 0.55, 0.15], np.float32)
    # red duotone, as the HUD's scanline overlay tints the 3D model in game
    out = np.stack([0.10 + lum * 1.05, 0.02 + lum * 0.30, 0.04 + lum * 0.34], -1)
    rows = (np.arange(out.shape[0]) // K) % 3 == 0
    out[rows] *= 0.55
    cv.im.paste(rart.to_image(out), (int(x0 * K), int(y0 * K)))
    cv.brackets(x0 + 4, y0 + 4, x1 - 4, y1 - 4, 10, rgba(WHITE, 200), 1)
    cv.text(x0 + 8, y1 - 10, 'ID 0451-S', F('mono', 10), rgba(WHITE, 170), 'lm')


def health(cv):
    x0, y0, x1, y1 = 56, 818, 476, 964
    panel(cv, x0, y0, x1, y1, tab=False, cut='tr', cut_px=18)
    portrait(cv, x0 + 8, y0 + 8, x0 + 132, y1 - 8)
    lx = x0 + 146
    label(cv, lx, y0 + 18, 'HEALTH', '体力')
    cv.text(x1 - 30, y0 + 18, 'SOLDIER', F('mono', 11), rgba(GREY), 'rm')
    big_number(cv, lx, y0 + 102, '142', 78)
    cv.text(lx + 128, y0 + 100, '/ 200', F('raj6', 24), rgba(GREY), 'ls')
    vseg_bar(cv, x1 - 24, y0 + 32, x1 - 12, y1 - 14, 0.71, 16)
    cv.line([(lx, y1 - 32), (x1 - 40, y1 - 32)], rgba(RED, 60), 1)
    cv.mixed(lx, y1 - 18, [('撃破 ', F('jp5', 11), rgba(RED)), ('STREAK', F('mono', 12), rgba(GREY)),
                           ('  03', F('raj7', 16), rgba(WHITE))], 'lm')


def ammo(cv):
    x0, y0, x1, y1 = 1508, 856, 1864, 964
    panel(cv, x0, y0, x1, y1, tab=False, cut='tl', cut_px=18)
    cv.rect(x1 - 3, y0, x1, y1, rgba(RED))
    label(cv, x0 + 30, y0 + 18, 'AMMO', '弾薬')
    big_number(cv, x1 - 118, y0 + 92, '4', 78, anchor='rs')
    cv.text(x1 - 106, y0 + 90, '/ 20', F('raj6', 28), rgba(GREY), 'ls')
    cv.hatch(x0 + 30, y1 - 24, x0 + 140, y1 - 16, RED_DIM, 255, step=5, width=1.5)
    # item meter card above it
    m0, m1 = 1612, 818
    panel(cv, m0, m1, x1, m1 + 30, tab=False, cut=None)
    cv.text(m0 + 12, m1 + 15, 'BUFF BANNER', F('mono', 11), rgba(GREY), 'lm')
    seg_bar(cv, m0 + 104, m1 + 11, x1 - 12, m1 + 19, 0.64, 22)


def team_status(cv):
    def slot(x, team, dead=False, cls_seed=0):
        col = TEAM_BLU if team == 'blu' else TEAM_RED
        cv.rect(x, 8, x + 40, 44, rgba(PANEL, 220))
        r = np.random.default_rng(cls_seed)
        base = np.array(col) * 0.35
        for i in range(4):
            for j in range(4):
                v = r.uniform(0.5, 1.3) * (0.4 if dead else 1)
                cv.rect(x + 4 + i * 8, 12 + j * 7.5, x + 12 + i * 8, 19.5 + j * 7.5,
                        rgba(tuple(int(min(255, cc * v)) for cc in base)))
        cv.rect(x, 8, x + 40, 10, rgba(col, 110 if dead else 255))
        if dead:
            cv.line([(x + 12, 18), (x + 28, 36)], rgba(RED), 2)
            cv.line([(x + 28, 18), (x + 12, 36)], rgba(RED), 2)
    for i in range(6):
        slot(612 + i * 46, 'blu', dead=(i == 2), cls_seed=i)
        slot(1032 + i * 46, 'red', dead=(i == 4), cls_seed=10 + i)
    # timer and scores
    cv.chamfer(894, 0, 1026, 58, fill=rgba(PANEL, 236), bl=12, br=12)
    cv.chamfer(894, 0, 1026, 58, outline=rgba(RED, 120), width=1, bl=12, br=12)
    cv.text(960, 26, '4:59', F('raj7', 32), rgba(WHITE), 'mm')
    cv.text(960, 48, 'CAPTURE THE FLAG', F('mono', 9), rgba(GREY), 'mm')
    cv.text(902, 30, '0', F('raj7', 20), rgba(TEAM_BLU), 'lm')
    cv.text(1018, 30, '0', F('raj7', 20), rgba(TEAM_RED), 'rm')


def weapon_icon(cv, kind, x, y, col):
    """Rough stand-ins for TF2's kill icons."""
    if kind == 'rocket':
        cv.rect(x, y - 4, x + 34, y + 4, col)
        cv.poly([(x + 34, y - 6), (x + 42, y), (x + 34, y + 6)], fill=col)
        cv.rect(x + 8, y + 4, x + 13, y + 10, col)
    elif kind == 'gun':
        cv.rect(x, y - 3, x + 30, y + 2, col)
        cv.poly([(x + 26, y + 2), (x + 34, y + 2), (x + 38, y + 10), (x + 30, y + 10)], fill=col)
        cv.rect(x - 4, y - 5, x + 4, y + 4, col)
    else:
        cv.poly([(x, y + 3), (x + 26, y - 3), (x + 34, y), (x + 26, y + 3)], fill=col)
        cv.rect(x + 26, y - 4, x + 38, y + 4, col)


def kill_feed(cv):
    rows = [('Ingalther', TEAM_RED, 'rocket', 'Static', TEAM_BLU, True),
            ('Vex', TEAM_BLU, 'gun', 'Kuroi', TEAM_RED, False),
            ('Nyx', TEAM_BLU, 'knife', 'Reiko', TEAM_RED, False)]
    y = 72
    for a, ca, icon, b, cb, local in rows:
        fa, fb = F('bar6', 18), F('bar6', 18)
        wa, wb = cv.width(a, fa), cv.width(b, fb)
        w = 14 + wa + 12 + 46 + 12 + wb + 14
        x1 = 1890
        x0 = x1 - w
        cv.rect(x0, y, x1, y + 30, rgba(RED_DEEP, 240) if local else rgba(PANEL, 205))
        if local:
            cv.rect(x0, y + 29, x1, y + 30, rgba(RED))
        cv.text(x0 + 14, y + 15, a, fa, rgba(ca), 'lm')
        weapon_icon(cv, icon, x0 + 14 + wa + 14, y + 15, rgba(WHITE, 235))
        cv.text(x1 - 14, y + 15, b, fb, rgba(cb), 'rm')
        y += 36


def target_id(cv):
    x0, y0, x1, y1 = 806, 600, 1114, 648
    panel(cv, x0, y0, x1, y1, tab=False, cut='br', cut_px=10)
    cv.rect(x0, y0, x0 + 3, y1, rgba(TEAM_BLU))
    cv.text(x0 + 16, y0 + 17, 'Static', F('bar6', 20), rgba(TEAM_BLU), 'lm')
    cv.mixed(x0 + 16, y0 + 37, [('SCOUT', F('mono', 10), rgba(GREY)), ('  //  ', F('mono', 10), rgba(RED, 150)),
                                ('スカウト', F('jp5', 9), rgba(GREY))], 'lm')
    cv.text(x1 - 30, y0 + 25, '63', F('raj7', 26), rgba(WHITE), 'rm')
    vseg_bar(cv, x1 - 22, y0 + 8, x1 - 14, y1 - 8, 0.5, 8, gap=1.5)


def damage(cv):
    for s, x, y, a, size in (('-62', 1006, 488, 255, 30), ('-18', 1032, 452, 140, 24)):
        f = F('raj7', size)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1.4, -1.4), (1.4, 1.4), (-1.4, 1.4), (1.4, -1.4)):
            cv.text(x + dx, y + dy, s, f, rgba(INK, a), 'mm')
        cv.text(x, y, s, f, rgba(HOT, a), 'mm')


def chat(cv):
    lines = [[('*DEAD* ', GREY), ('Kuroi', TEAM_RED), (' :  gg, that rocket was clean', WHITE)],
             [('Static', TEAM_BLU), (' :  intel incoming, watch sewers', WHITE)],
             [('Ingalther', TEAM_RED), (' :  死神を恐れるな', WHITE)]]
    y = 704
    for parts in lines:
        x = 60
        for t, col in parts:
            f = F('jp5', 15) if any(ord(ch) > 0x2000 for ch in t) else F('bar6', 17)
            cv.text(x + 1, y + 1, t, f, rgba(INK, 200), 'lm')
            x += cv.text(x, y, t, f, rgba(col), 'lm')
        y += 26


def build():
    cv = Canvas(backdrop())
    team_status(cv)
    kill_feed(cv)
    crosshair(cv)
    target_id(cv)
    damage(cv)
    chat(cv)
    health(cv)
    ammo(cv)
    return cv.result()


if __name__ == '__main__':
    build().save(os.path.join(os.path.dirname(os.path.dirname(HERE)), 'docs', 'style-ingame.jpg'), quality=92)
