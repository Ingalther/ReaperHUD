"""Main menu style preview for the Reaper HUD (the backdrop is a placeholder for the menu artwork).

    python tools/style/preview_menu.py      -> docs/style-menu.jpg
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import rart
from ui_kit import (GREY, GREY_D, INK, K, PANEL, RED, RED_DEEP, RED_DIM, SPLIT_C, SPLIT_R, WHITE, Canvas, F, panel,
                    rgba, seg_bar)

W, H = 1920, 1080


def placeholder_backdrop(seed=3):
    """Black void, red particle dust and a glow where the reaper artwork will stand."""
    r = np.random.default_rng(seed)
    img = np.zeros((H, W, 3), np.float32) + rart.c(5, 5, 7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((xx - 1180) / 1.0, (yy - 430) / 1.15)
    rart.add(img, rart.RED, 0.38 * np.exp(-(d / 230) ** 2))
    rart.add(img, rart.BLOOD, 0.35 * np.exp(-(d / 520) ** 2))
    m = rart.Mask(W, H, 2)
    for _ in range(2600):
        x = r.normal(1180, 330)
        y = r.normal(470, 260)
        s = r.choice([0.5, 0.7, 0.9, 1.2])
        m.rect(x, y, x + s, y + s, fill=int(r.uniform(40, 255)))
    dust = m.get()
    rart.add(img, rart.c(255, 70, 90), dust * 0.9)
    rart.add(img, rart.RED, rart.blur(dust, 2.5) * 0.9)
    # vertical glitch streaks
    for _ in range(14):
        x = int(r.normal(1180, 260))
        if 0 <= x < W:
            y0 = int(r.uniform(60, 700))
            img[y0:y0 + int(r.uniform(60, 380)), x] += rart.c(120, 14, 30) * r.uniform(0.3, 0.9)
    img *= (0.80 + 0.20 * (np.arange(H) % 3 != 0))[:, None, None]
    v = np.hypot((xx - W / 2) / (W * 0.6), (yy - H / 2) / (H * 0.62))
    img *= (1 - 0.6 * rart.smoothstep(0.6, 1.2, v))[..., None]
    img += r.normal(0, 0.01, (H, W, 1)).astype(np.float32)
    return rart.to_image(img)


# ------------------------------------------------------------------ icons
def icon_chat(cv, x, y, s, col):
    cv.d.rounded_rectangle([x * K, y * K, (x + s) * K, (y + s * 0.72) * K], radius=4 * K, outline=col, width=2 * K)
    cv.poly([(x + s * 0.22, y + s * 0.70), (x + s * 0.2, y + s * 0.95), (x + s * 0.45, y + s * 0.70)], fill=col)


def icon_power(cv, cx, cy, r, col):
    cv.d.arc([(cx - r) * K, (cy - r) * K, (cx + r) * K, (cy + r) * K], start=-55, end=235, fill=col, width=2 * K)
    cv.line([(cx, cy - r - 2), (cx, cy - 1)], col, 2)


def icon_gear(cv, cx, cy, r, col):
    for i in range(8):
        a = i * math.pi / 4
        cv.line([(cx + (r - 1) * math.cos(a), cy + (r - 1) * math.sin(a)),
                 (cx + (r + 3) * math.cos(a), cy + (r + 3) * math.sin(a))], col, 3)
    cv.d.ellipse([(cx - r) * K, (cy - r) * K, (cx + r) * K, (cy + r) * K], outline=col, width=2 * K)
    cv.d.ellipse([(cx - r * 0.35) * K, (cy - r * 0.35) * K, (cx + r * 0.35) * K, (cy + r * 0.35) * K], fill=col)


def icon_list(cv, x, y, s, col):
    for i in range(3):
        yy = y + 3 + i * (s - 6) / 2
        cv.rect(x, yy - 1.5, x + 3, yy + 1.5, col)
        cv.rect(x + 6, yy - 1.5, x + s, yy + 1.5, col)


def icon_plus(cv, cx, cy, r, col):
    cv.rect(cx - r, cy - 1.5, cx + r, cy + 1.5, col)
    cv.rect(cx - 1.5, cy - r, cx + 1.5, cy + r, col)


def icon_play(cv, cx, cy, r, col):
    cv.poly([(cx - r * 0.7, cy - r), (cx + r, cy), (cx - r * 0.7, cy + r)], fill=col)


# ------------------------------------------------------------------ pieces
def wordmark(cv, x, y):
    """THE REAPER in a wide corporate face; its last letters break up into pixel dust."""
    f = F('mich', 46)
    txt = 'THE REAPER'
    sp = 2
    m = Image.new('L', cv.im.size, 0)
    d = ImageDraw.Draw(m)
    xx = x
    for ch in txt:
        d.text((xx * K, y * K), ch, font=f, fill=255, anchor='lt')
        xx += f.getlength(ch) / K + sp
    end = xx - sp
    a = np.asarray(m, np.uint8).copy()
    r = np.random.default_rng(8)
    blk = 3 * K
    x_start = (x + (end - x) * 0.9) * K
    ys, xs = np.nonzero(a)
    y0, y1 = ys.min(), ys.max()
    out = a.copy()
    dust = np.zeros_like(a)
    for by in range(y0 - y0 % blk, y1 + 1, blk):
        for bx in range(int(x_start) - int(x_start) % blk, int(end * K) + blk, blk):
            cell = a[by:by + blk, bx:bx + blk]
            if not cell.any():
                continue
            t = min(1.0, max(0.0, (bx - x_start) / (end * K - x_start)))
            if r.random() < 0.62 * t ** 1.2:
                out[by:by + blk, bx:bx + blk] = 0
                if r.random() < 0.6:  # the fragment drifts off to the right and up
                    dx = int(r.exponential(18) * K) + blk
                    dy = int(r.normal(-5, 6) * K)
                    ty, tx = by + dy, bx + dx
                    if 0 <= ty < a.shape[0] - blk and 0 <= tx < a.shape[1] - blk:
                        dust[ty:ty + blk, tx:tx + blk] = int(r.uniform(90, 255))
    # two thin tears through the word (rows of it shifted), then its chromatic split: a red copy to the left, a
    # cyan one to the right, the word, its dust
    for (ty, th, shift) in ((0.36, 0.05, 12), (0.71, 0.04, -9)):
        r0 = int(y0 + (y1 - y0) * ty)
        r1 = r0 + max(K, int((y1 - y0) * th))
        out[r0:r1] = np.roll(out[r0:r1], shift * K, axis=1)
    ghost = Image.fromarray(np.roll(out, -2 * K, axis=1))
    cv.masked(ghost, SPLIT_R, 130)
    cv.masked(Image.fromarray(np.roll(out, 2 * K, axis=1)), SPLIT_C, 80)
    cv.masked(Image.fromarray(out), WHITE)
    cv.masked(Image.fromarray(dust), RED, 255)
    cv.glow_mask(Image.fromarray(dust), RED, 4, 0.8)
    return end


def seal(cv, x, y, s):
    cv.rect(x - 2, y + 2, x + s - 2, y + s + 2, rgba(SPLIT_R, 90))     # its chromatic split
    cv.rect(x + 2, y - 1, x + s + 2, y + s - 1, rgba(SPLIT_C, 60))
    cv.rect(x, y, x + s, y + s, rgba(RED))
    cv.rect(x + 3, y + 3, x + s - 3, y + s - 3, rgba(RED))
    cv.d.rectangle([(x + 3) * K, (y + 3) * K, (x + s - 3) * K, (y + s - 3) * K], outline=rgba(INK, 120), width=K)
    cv.vtext(x + s / 2, y + 4, '死神', F('jp9', 20), rgba(WHITE), 22)
    cv.rect(x - 4, y + s * 0.58, x + s + 6, y + s * 0.58 + 2, rgba(WHITE, 160))   # a tear across it
    cv.rect(x + s * 0.3, y + s * 0.58 + 2, x + s + 6, y + s * 0.58 + 3, rgba(SPLIT_C, 120))


def top_bar(cv):
    cv.rect(0, 0, W, 46, rgba(INK, 236))
    cv.rect(0, 46, W, 47, rgba(RED, 150))
    icon_chat(cv, 16, 12, 24, rgba(WHITE, 210))
    for i in range(6):
        x = 58 + i * 36
        if i == 0:
            cv.rect(x, 8, x + 30, 38, rgba(RED_DEEP))
            cv.text(x + 15, 23, 'I', F('raj7', 20), rgba(RED), 'mm')
            cv.d.rectangle([x * K, 8 * K, (x + 30) * K - 1, 38 * K - 1], outline=rgba(RED, 200), width=K)
        else:
            cv.d.rectangle([x * K, 8 * K, (x + 30) * K - 1, 38 * K - 1], outline=rgba(GREY_D, 255), width=K)
            icon_plus(cv, x + 15, 23, 4, rgba(GREY_D))
    # find a game
    x0, x1 = 1590, 1866
    cv.chamfer(x0, 0, x1, 46, fill=rgba(RED), bl=14)
    cv.hatch(x0 + 14, 0, x0 + 46, 46, RED_DIM, 255, step=6, width=2)
    cv.text(x0 + 60, 23, 'FIND A GAME', F('raj7', 23), rgba(INK), 'lm', spacing=1)
    for k in range(2):
        xx = x1 - 30 + k * 9
        cv.poly([(xx, 15), (xx + 7, 23), (xx, 31), (xx - 3, 31), (xx + 4, 23), (xx - 3, 15)], fill=rgba(INK))
    cv.rect(1868, 0, W, 46, rgba((20, 18, 22)))
    icon_power(cv, 1894, 24, 9, rgba(RED))


def logo(cv):
    seal(cv, 60, 94, 56)
    cv.text(134, 76, '(DON\'T FEAR)', F('mich', 14), rgba(RED), 'lt', spacing=5)
    wordmark(cv, 132, 98)
    cv.rect(60, 162, 60 + 34, 165, rgba(RED))
    cv.rect(94, 163, 600, 164, rgba(RED, 140))
    cv.mixed(60, 178, [('BEYOND THE WALL', F('mono', 12), rgba(GREY)), ('  //  ', F('mono', 12), rgba(RED)),
                       ('黒壁の彼方', F('jp5', 11), rgba(RED)), ('  //  ', F('mono', 12), rgba(RED)),
                       ('HUD BY INGALTHER', F('mono', 12), rgba(GREY))], 'lm')


def profile(cv):
    x0, y0, x1, y1 = 60, 200, 600, 298
    panel(cv, x0, y0, x1, y1, tab_h=40)
    # medal placeholder: a hexagon with the level
    cx, cy, rr = 109, 249, 34
    hexp = [(cx + rr * math.cos(math.pi / 6 + i * math.pi / 3), cy + rr * math.sin(math.pi / 6 + i * math.pi / 3))
            for i in range(6)]
    cv.poly(hexp, fill=rgba(RED_DEEP), outline=rgba(RED), width=1.5)
    cv.text(cx, cy - 2, '32', F('raj7', 26), rgba(WHITE), 'mm')
    cv.text(cx, cy + 19, 'LV', F('mono', 10), rgba(RED), 'mm')
    cv.text(162, 214, 'Ingalther', F('bar6', 25), rgba(WHITE), 'lt')
    cv.mixed(162, 252, [('CASUAL', F('raj7', 16), rgba(RED)), ('  ·  LEVEL 32  ·  TIER 5', F('raj6', 16), rgba(GREY))],
             'lm')
    seg_bar(cv, 162, 266, 584, 273, 0.63, 34)
    cv.text(162, 286, '1 876 712 XP', F('mono', 11), rgba(GREY), 'lm')
    cv.text(584, 286, '1 877 500 XP', F('mono', 11), rgba(GREY), 'rm')
    icon_gear(cv, 578, 220, 6, rgba(GREY))


BUTTONS = [('ITEMS', 'アイテム'), ('SHOP', 'ショップ'), ('OPTIONS', '設定'), ('ADVANCED OPTIONS', '詳細設定'),
           ('ACHIEVEMENTS', '実績'), ('WORKSHOP', 'ワークショップ'), ('REPLAYS', 'リプレイ'), ('HUD SETTINGS', 'HUD設定')]


def buttons(cv, hover=0):
    x0, x1, y, h, gap = 60, 560, 326, 44, 7
    for i, (en, jp) in enumerate(BUTTONS):
        y0, y1 = y + i * (h + gap), y + i * (h + gap) + h
        cy = (y0 + y1) / 2
        if i == hover:
            cv.chamfer(x0, y0, x1, y1, fill=rgba(RED), br=12)
            r = np.random.default_rng(4)
            for _ in range(26):  # the armed button sheds a little pixel dust off its cut corner
                s = r.choice([2, 3, 3, 4])
                dx = r.exponential(16)
                yy = r.uniform(y0 + 4, y1 - 2)
                cv.rect(x1 - 4 + dx, yy, x1 - 4 + dx + s, yy + s, rgba(RED, int(255 * max(0.15, 1 - dx / 50))))
            fg, num, sub = rgba(INK), rgba(INK), rgba(INK, 170)
        else:
            cv.chamfer(x0, y0, x1, y1, fill=rgba(PANEL, 196), br=12)
            cv.rect(x0, y0, x0 + 2, y1, rgba(RED_DIM))
            cv.line([(x0, y1), (x1 - 12, y1)], rgba(RED, 40), 1)
            fg, num, sub = rgba(WHITE), rgba(RED), rgba(GREY)
        cv.text(x0 + 18, cy, '%02d' % (i + 1), F('mono', 14), num, 'lm')
        cv.text(x0 + 54, cy + 1, en, F('raj7', 23), fg, 'lm', spacing=1)
        cv.text(x1 - 22, cy, jp, F('jp5', 12), sub, 'rm')


def quick_icons(cv):
    y0 = 996
    for i, fn in enumerate((icon_list, icon_plus, icon_play, icon_gear)):
        x0 = 60 + i * 50
        cv.chamfer(x0, y0, x0 + 42, y0 + 42, fill=rgba(PANEL, 210), tr=9)
        cv.chamfer(x0, y0, x0 + 42, y0 + 42, outline=rgba(RED, 110), width=1, tr=9)
        col = rgba(WHITE, 220)
        if fn is icon_list:
            fn(cv, x0 + 11, y0 + 12, 20, col)
        elif fn is icon_gear:
            fn(cv, x0 + 21, y0 + 21, 7, col)
        else:
            fn(cv, x0 + 21, y0 + 21, 8, col)


FRIENDS = [('Kuroi', 'Online', RED), ('Static', 'Playing Team Fortress 2', WHITE), ('Nyx', 'Online', RED),
           ('Vex', 'Away', GREY), ('Reiko', 'Playing other game', GREY), ('Hollow', 'Away', GREY),
           ('Ghost', 'Online', RED)]


def avatar(cv, x, y, s, seed):
    r = np.random.default_rng(seed)
    base = np.array([r.uniform(30, 90), r.uniform(10, 30), r.uniform(14, 40)])
    n = 6
    for i in range(n):
        for j in range(n):
            v = r.uniform(0.5, 1.4)
            col = tuple(int(min(255, c * v)) for c in base)
            cv.rect(x + i * s / n, y + j * s / n, x + (i + 1) * s / n, y + (j + 1) * s / n, rgba(col))


def friends(cv):
    x0, y0, x1, y1 = 1384, 596, 1864, 900
    panel(cv, x0, y0, x1, y1, tab_h=40, cut='tl')
    cv.text(1402, 616, 'FRIENDS', F('raj7', 21), rgba(WHITE), 'lm', spacing=1)
    cv.text(1494, 617, '7 ONLINE', F('mono', 11), rgba(GREY), 'lm')
    cv.hatch(1720, 612, 1790, 621, RED_DIM, 255, step=5, width=1.5)
    cv.text(1846, 616, 'シグナル', F('jp5', 12), rgba(RED), 'rm')
    cv.line([(x0 + 1, 636), (x1 - 1, 636)], rgba(RED, 70), 1)
    for i, (name, status, col) in enumerate(FRIENDS):
        cx = 1400 + (i % 2) * 234
        cy = 652 + (i // 2) * 58
        avatar(cv, cx, cy, 38, i + 4)
        cv.d.rectangle([cx * K, cy * K, (cx + 38) * K - 1, (cy + 38) * K - 1], outline=rgba(RED, 90), width=K)
        cv.text(cx + 50, cy + 2, name, F('bar6', 18), rgba(WHITE), 'lt')
        cv.text(cx + 50, cy + 25, status, F('bar4', 14), rgba(col, 230), 'lt')


def tagline(cv):
    cv.vtext(1890, 104, '死神を恐れるな', F('jp7', 17), rgba(RED, 210), 21)
    cv.line([(1890, 262), (1890, 330)], rgba(RED, 120), 1)
    m = Image.new('L', (400 * K, 30 * K), 0)
    ImageDraw.Draw(m).text((0, 0), "DON'T FEAR THE REAPER", font=F('mono', 11), fill=170)
    m = m.rotate(-90, expand=True)
    solid = Image.new('RGB', m.size, GREY)
    cv.im.paste(solid, (int(1884 * K), int(340 * K)), m)


def frame(cv):
    for (x, y, dx, dy) in ((16, 62, 1, 1), (1904, 62, -1, 1), (1904, 1064, -1, -1), (16, 1064, 1, -1)):
        cv.line([(x + dx * 18, y), (x, y), (x, y + dy * 18)], rgba(RED, 170), 1)


def version(cv):
    cv.text(1864, 1050, 'THE REAPER HUD  v0.1  //  made by Ingalther', F('mono', 12), rgba(GREY, 190), 'rm')


def build(backdrop=None):
    base = backdrop or placeholder_backdrop()
    cv = Canvas(base)
    frame(cv)
    top_bar(cv)
    logo(cv)
    profile(cv)
    buttons(cv)
    quick_icons(cv)
    friends(cv)
    tagline(cv)
    version(cv)
    return cv.result()


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    build().save(os.path.join(root, 'docs', 'style-menu.jpg'), quality=92)
