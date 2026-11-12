"""Store / GitHub thumbnail (1920 x 1080, comfig.app and the repo): a clean title card.

    python tools/thumbnail.py [style] [out.png]      style: blackwall (default), menu, wall

blackwall: Cyberpunk 2077's own Blackwall screen behind the title; menu: a still of the main menu's video; wall:
the Wall's red code alone. The title alone (the menu logo's seal, (DON'T FEAR) and THE REAPER) large in the middle,
glitched with the game's own glitch mask; the menu's corner brackets. Nothing else.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'style'))
import build_art as B  # noqa: E402
import menu  # noqa: E402
import preview_menu as PM  # noqa: E402

W, H = 1920, 1080
FONTS = os.path.join(HERE, 'fonts')
CYAN = (0, 214, 255)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


CP = os.path.join(HERE, 'art', 'cp2077')


def backdrop(style):
    if style == 'blackwall':  # Cyberpunk 2077's own Blackwall screen (q304), its red code, behind the title
        im = Image.open(os.path.join(CP, 'blackwall_screen.png')).convert('RGB').resize((W, H), Image.LANCZOS)
        im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(1.5))).enhance(0.5).convert('RGBA')
    elif style == 'menu':
        im = Image.open(os.path.join(HERE, '..', 'video', 'menu_still.jpg')).convert('RGB').resize((W, H))
        im = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(3))).enhance(0.55).convert('RGBA')
    else:
        im = B.wall_over(Image.new('RGBA', (W, H), B.INK + (255,)), 'right', 0.9)
        im = B.wall_over(im, 'left', 0.35)
    # darker round the title, the corners darkest
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    v = Image.fromarray((np.clip(0.55 - 0.35 * np.exp(-r * r * 2.2) + (r - 0.9) * 0.6, 0, 0.85) * 255)
                        .astype(np.uint8))
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    shade.putalpha(v)
    im.alpha_composite(shade)
    band = np.clip(1 - np.abs((yy - H * 0.5) / (H * 0.26)), 0, 1) ** 0.8 * 175
    b = Image.new('RGBA', (W, H), (4, 2, 4, 0))
    b.putalpha(Image.fromarray(band.astype(np.uint8)))
    im.alpha_composite(b)
    return im


def title(cv):
    """The menu logo's title alone: the 死神 seal, (DON'T FEAR) and the THE REAPER wordmark (no rule, no subline)."""
    PM.seal(cv, 60, 94, 56)
    cv.text(134, 76, "(DON'T FEAR)", PM.F('mich', 14), PM.rgba(PM.RED), 'lt', spacing=5)
    PM.wordmark(cv, 132, 98)


def logo(width):
    art = menu.cut(menu.render(title), (56, 66, 621, 156))
    k = width / art.width
    return art.resize((int(art.width * k), int(art.height * k)), Image.LANCZOS)


def tears(im, seed, n=8):
    d = ImageDraw.Draw(im)
    r = np.random.default_rng(seed)
    for _ in range(n):
        y = r.uniform(H * 0.08, H * 0.25) if r.random() < 0.5 else r.uniform(H * 0.75, H * 0.9)  # clear of the title
        x0 = r.uniform(W * 0.08, W * 0.7)
        w = r.uniform(140, 520)
        h = float(r.choice([3, 4, 6, 9]))
        col = (B.HOT, (240, 236, 236), CYAN)[int(r.integers(3))]
        d.rectangle([x0, y, x0 + w, y + h], fill=col + (int(r.uniform(120, 220)),))


def brackets(im):
    d = ImageDraw.Draw(im)
    m, a = 46, 70
    for x, y, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)):
        d.line([(x, y + sy * a), (x, y), (x + sx * a, y)], fill=B.RED + (230,), width=4)


def glitch(logo, seed=3, share=0.22):
    """Cyberpunk's glitch on the logo alone: a few horizontal slices (where the game's own glitch mask has bars)
    shoved sideways, with a red copy left and a cyan copy right of each shoved slice; most of it stays clean."""
    mask = Image.open(os.path.join(CP, 'glitch_mask.png')).convert('L').resize(logo.size, Image.NEAREST)
    m = np.asarray(mask) > 128
    r = np.random.default_rng(seed)
    src = np.asarray(logo).copy()
    out = src.copy()
    band = 6
    for y in range(0, src.shape[0], band):
        if r.random() > share or not m[y].any():
            continue
        sl = slice(y, y + band)
        dx = int(r.choice([-18, -10, 8, 14, 22]))
        cols = m[y]
        piece = np.roll(src[sl], dx, axis=1)
        out[sl][:, cols] = piece[:, cols]
        for off, col in ((-5, (255, 20, 60)), (5, (0, 214, 255))):
            ghost = np.roll(piece, off, axis=1)
            a = ghost[..., 3:4].astype(np.float32) / 255 * 0.55
            seg = out[sl].astype(np.float32)
            seg[..., :3] = seg[..., :3] * (1 - a * cols[None, :, None]) + np.array(col) * a * cols[None, :, None]
            seg[..., 3] = np.maximum(seg[..., 3], ghost[..., 3] * 0.55 * cols[None, :])
            out[sl] = seg.astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


def code_strip(im):
    """Cyberpunk's cyberspace loading text, small and dim along the foot."""
    t = Image.open(os.path.join(CP, 'cyberspace_loading.png')).convert('RGBA')
    t = t.resize((int(t.width * 0.9), int(t.height * 0.9)), Image.LANCZOS)
    a = t.split()[3].point(lambda v: int(v * 0.35))
    tinted = Image.new('RGBA', t.size, B.RED + (0,))
    tinted.putalpha(a)
    im.alpha_composite(tinted, (70, H - 70 - t.height))


def card(style='blackwall'):
    """The title alone, large, in the middle, with its glitch; the menu's corner brackets."""
    im = backdrop(style)
    lg = logo(1560)
    x, y = (W - lg.width) // 2 + 20, (H - lg.height) // 2
    glow = lg.split()[3].filter(ImageFilter.GaussianBlur(30))
    halo = Image.new('RGBA', (W, H), B.RED + (0,))
    a = Image.new('L', (W, H), 0)
    a.paste(glow.point(lambda v: int(v * 0.4)), (x, y))
    halo.putalpha(a)
    im.alpha_composite(halo)
    im.alpha_composite(glitch(lg), (x, y))
    brackets(im)
    return im.convert('RGB')


def main(style='blackwall', out=None):
    out = out or os.path.join(HERE, '..', 'thumbnail.png')
    card(style).save(out, optimize=True)
    print('wrote', out)


if __name__ == '__main__':
    main(*sys.argv[1:])
