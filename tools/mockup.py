"""Approximate 1080p previews drawn from the built .res files and textures (no game needed):

    python mockup.py ingame SCREENSHOT OUT.jpg [--demo|--medic]   the in-game HUD over a screenshot
    python mockup.py menu OUT.jpg                                  the main menu
    python mockup.py screen resource/ui/X.res OUT.jpg [BUTTONS]    a full-screen menu, BUTTONS (a,b) hovered

Positions follow vgui's proportional rules (480 units = screen height); a font's glyphs are its scheme "tall" (a cell
height) over the face's cell / em ratio, its text centred in the label by the cell; nine-slice borders, auto-wide
labels, blurred (glow) fonts and Modulate materials are drawn the way the game draws them. Fonts are stand-ins from
tools/fonts (Barlow for Windows' Bahnschrift). What the game itself paints (the 3D model, class portraits, kill icons,
the rank medal) is a placeholder.
"""
import os
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import kv

TOOLS = os.path.dirname(os.path.abspath(__file__))
HUD = os.path.dirname(TOOLS)
W, H = 1920, 1080
S = H / 480
UW = W / S
FACES = {'rajdhani': ('Rajdhani-Bold.ttf', 1.276, 930 / 1276), 'rajdhani semibold': ('Rajdhani-SemiBold.ttf', 1.276, 930 / 1276),
         'share tech mono': ('ShareTechMono-Regular.ttf', 1.127, 885 / 1127),
         'bahnschrift semicondensed': ('BarlowSemiCondensed-SemiBold.ttf', 1.207, 0.8),
         'bahnschrift semibold condensed': ('BarlowSemiCondensed-Bold.ttf', 1.207, 0.8)}
THUMB = 'materials/vgui/replay/thumbnails/rk/'


def vtf(path):
    d = open(path, 'rb').read()
    w, h = struct.unpack_from('<HH', d, 16)
    fmt, mips = struct.unpack_from('<I', d, 52)[0], d[56]
    if fmt == 13:  # DXT1 (the menu video): its first frame
        import dxt
        return Image.fromarray(dxt.decode(d, w, h, 80), 'RGB').convert('RGBA')
    bpp = 4 if fmt == 12 else 3
    size = sum(max(1, w >> i) * max(1, h >> i) * bpp for i in range(1, mips))
    a = np.frombuffer(d, np.uint8, w * h * bpp, 80 + size).reshape(h, w, bpp)
    a = a[..., [2, 1, 0, 3]] if bpp == 4 else np.dstack([a[..., [2, 1, 0]], np.full((h, w), 255, np.uint8)])
    return Image.fromarray(a.copy(), 'RGBA')


_mats = {}
BLU = '--blu' in sys.argv   # draw the HUD as the BLU team sees it (team pictures' teambg_3)


def material(image):
    """image key of a panel -> (texture, modulate): modulate is 0 (drawn over), 1 (Modulate: multiplies) or 2
    (Modulate with $mod2x: twice the product); (None, 0) for game art we do not have."""
    if not image:
        return None, 0
    m = image.lower().replace('\\', '/')
    if m not in _mats:
        _mats[m] = (None, 0)
        for prefix, sub in (('replay/thumbnails/rk/', THUMB), ('../console/', 'materials/console/')):
            if m.startswith(prefix):
                p = os.path.join(HUD, sub + m[len(prefix):])
                if os.path.exists(p + '.vtf'):
                    vmt = open(p + '.vmt', encoding='utf-8').read().lower() if os.path.exists(p + '.vmt') else ''
                    mod = 0
                    if vmt.lstrip().startswith('"modulate"'):
                        mod = 2 if re.search(r'"\$mod2x"\s+"1"', vmt) else 1
                    elif re.search(r'"\$additive"\s+"1"', vmt):
                        mod = 3
                    _mats[m] = (vtf(p + '.vtf'), mod)
    return _mats[m]


def team_image(blk):
    """The picture a panel shows: a team picture's BLU one (teambg_3) when drawing BLU."""
    if BLU and kv.get(blk, 'teambg_3'):
        return kv.get(blk, 'teambg_3')
    return kv.get(blk, 'image')


def pick_block(blocks):
    """A scheme font's entries: the one whose yres band holds 1080, else the first."""
    for _, b, _ in blocks:
        yr = kv.get(b, 'yres')
        if yr:
            lo, hi = (int(v) for v in yr.split())
            if lo <= H <= hi:
                return b, True
    return blocks[0][1], False


def scheme():
    root = kv.parse(open(os.path.join(HUD, 'resource/clientscheme.res'), encoding='utf-8').read())
    sch = kv.find(root, 'Scheme')
    colors = {e[0]: e[1] for e in kv.find(sch, 'Colors') if not isinstance(e[1], list)}
    fonts = {}
    for e in kv.find(sch, 'Fonts'):
        if isinstance(e[1], list) and e[1] and isinstance(e[1][0][1], list):
            b, banded = pick_block([x for x in e[1] if isinstance(x[1], list)])
            tall = float(kv.get(b, 'tall', '10'))
            fonts[e[0]] = dict(face=(kv.get(b, 'name') or '').lower(), cell=int(tall if banded else tall * S),
                               blur=int(kv.get(b, 'blur', '0')) * (1 if banded else S),
                               additive=kv.get(b, 'additive') == '1', outline=kv.get(b, 'outline') == '1',
                               shadow=kv.get(b, 'dropshadow') == '1')
    borders = {}
    for e in kv.find(sch, 'Borders'):
        if isinstance(e[1], list):
            g = lambda k, d='0': kv.get(e[1], k, d)
            borders[e[0]] = dict(image=kv.get(e[1], 'image'), sw=int(g('src_corner_width')), sh=int(g('src_corner_height')),
                                 dw=float(g('draw_corner_width')), dh=float(g('draw_corner_height')))
    return colors, fonts, borders


COLORS, FONTS, BORDERS = scheme()


def color(v):
    v = COLORS.get(v, v)
    nums = [int(x) for x in re.findall(r'\d+', v or '')] or [255, 255, 255, 255]
    return tuple((nums + [255])[:4])


def coord(v, parent, self_size):
    """xpos / ypos: N, rN (from the far edge), cN (from the centre), with an 's' the number is a multiple of the
    panel's own size ('cs-0.5' centres it, 'rs1' puts it against the far edge), an extra +/-N after that."""
    v = str(v).strip()
    anchor, far = 0.0, False
    if v[:1] == 'r':
        anchor, far, v = parent, True, v[1:]
    elif v[:1] == 'c':
        anchor, v = parent / 2, v[1:]
    m = re.fullmatch(r'(s)?(-?[\d.]+)?([+-][\d.]+)?', v)
    if not m:
        return anchor
    k, off = float(m.group(2) or 0), float(m.group(3) or 0)
    if m.group(1):
        return anchor + (-k if far else k) * self_size + off
    return anchor - k if far else anchor + k


def size(v, parent, other=0):
    v = str(v).strip()
    if v.startswith('f'):
        return parent - float(v[1:] or 0)
    if v.startswith('p'):
        return parent * float(v[1:])
    if v.startswith('o'):
        return other * float(v[1:])
    return float(v or 0)


_ttf = {}


def font(name):
    f = FONTS.get(name) or dict(face='bahnschrift semicondensed', cell=int(9 * S), blur=0, additive=False,
                                 outline=False, shadow=False)
    fname, ratio, asc = FACES.get(f['face'], FACES['bahnschrift semicondensed'])
    em = max(4, round(f['cell'] / ratio))
    key = (fname, em)
    if key not in _ttf:
        _ttf[key] = ImageFont.truetype(os.path.join(TOOLS, 'fonts', fname), em)
    return _ttf[key], f, asc


def over(dst, src, xy=(0, 0)):
    """src over dst (in place) in linear light, as the game blends; dst is the opaque screen."""
    x, y = xy
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + src.width, dst.width), min(y + src.height, dst.height)
    if x1 <= x0 or y1 <= y0:
        return
    d = np.asarray(dst.crop((x0, y0, x1, y1)), np.float32) / 255
    sv = np.asarray(src.crop((x0 - x, y0 - y, x1 - x, y1 - y)), np.float32) / 255
    a = sv[..., 3:4]
    d[..., :3] = (sv[..., :3] ** 2.2 * a + d[..., :3] ** 2.2 * (1 - a)) ** (1 / 2.2)
    d[..., 3:4] = a + d[..., 3:4] * (1 - a)
    dst.paste(Image.fromarray((d * 255 + 0.5).clip(0, 255).astype(np.uint8), 'RGBA'), (x0, y0))


class Painter:
    def __init__(self, base, button_state=None):
        self.img = base.convert('RGBA')
        self.button_state = button_state or {}  # button -> border key to draw (border_armed shows the hover)

    def image(self, im, x, y, w, h, alpha=255, modulate=False, drawcolor=None):
        if im is None or w < 1 or h < 1:
            return
        X, Y, Wp, Hp = round(x * S), round(y * S), max(1, round(w * S)), max(1, round(h * S))
        t = im.resize((Wp, Hp), Image.LANCZOS)
        if modulate == 3:  # additive, in linear light as the game blends
            box = (X, Y, X + Wp, Y + Hp)
            dst = np.asarray(self.img.crop(box), np.float32) / 255
            src = np.asarray(t, np.float32)[:dst.shape[0], :dst.shape[1]] / 255
            lin = dst[..., :3] ** 2.2 + src[..., :3] ** 2.2 * src[..., 3:4] * alpha / 255
            dst[..., :3] = np.clip(lin, 0, 1) ** (1 / 2.2)
            self.img.paste(Image.fromarray((dst * 255 + 0.5).astype(np.uint8), 'RGBA'), box[:2])
            return
        if modulate:
            box = (X, Y, X + Wp, Y + Hp)
            dst = np.asarray(self.img.crop(box), np.float32)
            src = np.asarray(t.convert('RGB'), np.float32) / 255 * (2 if modulate == 2 else 1)
            dst[..., :3] = np.clip(dst[..., :3] * src[:dst.shape[0], :dst.shape[1]], 0, 255)
            self.img.paste(Image.fromarray(dst.astype(np.uint8), 'RGBA'), box[:2])
            return
        if drawcolor:
            a = np.asarray(t, np.float32)
            a[..., :4] *= np.array(drawcolor, np.float32) / 255
            t = Image.fromarray(a.astype(np.uint8), 'RGBA')
        if alpha != 255:
            t.putalpha(t.getchannel('A').point(lambda v: v * alpha // 255))
        over(self.img, t, (X, Y))

    def nine(self, border, x, y, w, h):
        """A scalable_image border: corners at their draw size, edges and middle stretched."""
        b = BORDERS.get(border)
        if not b:
            return
        tex, _ = material(b['image'])
        if tex is None:
            return
        if b['sw'] == 0 or b['dw'] == 0:
            self.image(tex, x, y, w, h)
            return
        tw, th = tex.size
        xs = [0, b['sw'], tw - b['sw'], tw]
        ys = [0, b['sh'], th - b['sh'], th]
        dx = [x, x + b['dw'], x + w - b['dw'], x + w]
        dy = [y, y + b['dh'], y + h - b['dh'], y + h]
        for i in range(3):
            for j in range(3):
                if dx[i + 1] - dx[i] > 0 and dy[j + 1] - dy[j] > 0 and xs[i + 1] > xs[i] and ys[j + 1] > ys[j]:
                    self.image(tex.crop((xs[i], ys[j], xs[i + 1], ys[j + 1])), dx[i], dy[j], dx[i + 1] - dx[i],
                               dy[j + 1] - dy[j])

    def text_width(self, s, fnt):
        f, _, _ = font(fnt)
        return ImageDraw.Draw(Image.new('L', (1, 1))).textlength(s, font=f) / S

    def text(self, s, x, y, w, h, fnt, col, align='west'):
        f, info, asc = font(fnt)
        col = color(col)
        if col[3] == 0:
            return
        tw = self.text_width(s, fnt) * S
        X, Wp = x * S, w * S
        bx = X if align.endswith('west') or tw > Wp else (X + Wp - tw if align.endswith('east') else X + (Wp - tw) / 2)
        cell = info['cell']
        if align.startswith('north'):
            top = y * S
        else:
            top = y * S + (h * S - cell) // 2
        base = top + int(cell) * asc
        layer = Image.new('L', self.img.size, 0)
        ImageDraw.Draw(layer).text((bx, base), s, font=f, fill=255, anchor='ls')
        if info['blur']:
            layer = layer.filter(ImageFilter.GaussianBlur(info['blur'] * 0.6))
        if info['additive']:
            a = np.asarray(self.img, np.float32)
            g = np.asarray(layer, np.float32)[..., None] / 255 * col[3] / 255
            a[..., :3] += g * np.array(col[:3], np.float32) * 1.6
            self.img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
            return
        if info['outline'] or info['shadow']:
            dark = layer.filter(ImageFilter.MaxFilter(3)) if info['outline'] else layer.transform(
                layer.size, Image.AFFINE, (1, 0, -2, 0, 1, -2))
            self.img.alpha_composite(Image.merge('RGBA', [Image.new('L', layer.size, 0)] * 3 + [dark.point(
                lambda v: v * 200 // 255)]))
        solid = Image.new('RGBA', self.img.size, col[:3] + (0,))
        solid.putalpha(layer.point(lambda v: v * col[3] // 255))
        self.img.alpha_composite(solid)

    def panels(self, body, px, py, pw, ph, values, skip=(), border_box=True):
        items = []
        for name, blk, _ in body:
            if not isinstance(blk, list) or name in skip:
                continue
            g = lambda k, d=None: kv.get(blk, k, d)
            if g('visible', '1') == '0' and name not in values:  # code shows these when needed
                continue
            w = size(g('wide', '0'), pw, size(g('tall', '0'), ph))
            h = size(g('tall', '0'), ph, w)
            x = px + coord(g('xpos', '0'), pw, w)
            y = py + coord(g('ypos', '0'), ph, h)
            items.append((float(g('zpos', '0') or 0), name, blk, x, y, w, h))
        # pin_to_sibling: this panel's corner on the sibling's corner, its xpos / ypos an offset from there
        boxes = {name: (x, y, w, h) for _, name, _, x, y, w, h in items}
        corner = {'PIN_TOPLEFT': (0, 0), 'PIN_TOPRIGHT': (1, 0), 'PIN_BOTTOMLEFT': (0, 1), 'PIN_BOTTOMRIGHT': (1, 1)}
        for i, (z, name, blk, x, y, w, h) in enumerate(items):
            sib = kv.get(blk, 'pin_to_sibling')
            if sib in boxes:
                sx, sy, sw, sh = boxes[sib]
                ox, oy = corner.get((kv.get(blk, 'pin_corner_to_sibling') or 'PIN_TOPLEFT').upper(), (0, 0))
                tx, ty = corner.get((kv.get(blk, 'pin_to_sibling_corner') or 'PIN_TOPLEFT').upper(), (0, 0))
                x = sx + tx * sw - ox * w + (x - px)
                y = sy + ty * sh - oy * h + (y - py)
                items[i] = (z, name, blk, x, y, w, h)
        for z, name, blk, x, y, w, h in sorted(items, key=lambda e: e[0]):
            g = lambda k, d=None: kv.get(blk, k, d)
            if name in values and callable(values[name]):
                values[name](self, x, y, w, h)
                continue
            txt = g('labelText') or g('labeltext')
            s = None
            if txt is not None and g('font'):
                s = values.get(name, txt if not txt.startswith(('%', '#')) else '')
                if g('auto_wide_tocontents') == '1':
                    w = self.text_width(s, g('font')) if s else 0
            b = g('border') or g(self.button_state.get(name, 'border_default'))
            if b and g('paintborder', '1') != '0' and border_box and w > 0:
                self.nine(b, x, y, w, h)
            if team_image(blk) and g('alpha', '255') != '0':  # alpha 0: a flash its animation lights
                tex, mod = material(team_image(blk))
                dc = color(g('drawcolor')) if g('drawcolor') else None
                self.image(tex, x, y, w, h, modulate=mod, drawcolor=dc)
            if s:
                self.text(s, x, y, w, h, g('font'), g('fgcolor', g('fgcolor_override', 'RK_Text')),
                          g('textAlignment', 'west'))


def res(rel):
    return kv.parse(open(os.path.join(HUD, rel), encoding='utf-8').read())


def first_body(rel):
    return next(e[1] for e in res(rel) if isinstance(e[1], list))


def layout(name):
    return kv.find(kv.find(res('scripts/hudlayout.res'), 'Resource/HudLayout.res'), name)


def box_of(blk, pw=UW, ph=480):
    w = size(kv.get(blk, 'wide', '0'), pw, size(kv.get(blk, 'tall', '0'), ph))
    h = size(kv.get(blk, 'tall', '0'), ph, w)
    return coord(kv.get(blk, 'xpos', '0'), pw, w), coord(kv.get(blk, 'ypos', '0'), ph, h), w, h


def panel_file(p, rel, values, layout_name=None, skip=()):
    """Draw a HUD panel file: its own block (named like it, first in the file) places it, from hudlayout when the
    layout names it; its other blocks are its children."""
    body = first_body(rel)
    own = next((e for e in body if isinstance(e[1], list)), None)
    lay = layout(layout_name) if layout_name else None
    src = lay if lay is not None else own[1]
    x, y, w, h = box_of(src)
    children = [e for e in body if e is not own] if lay is None else body
    p.panels(children, x, y, w, h, values, skip=skip)


def placeholder_icon(p, kind, x, y, col):
    """Stand-ins for TF2's kill icons (the game draws its own)."""
    d = ImageDraw.Draw(p.img)
    X, Y = x * S, y * S
    if kind == 'rocket':
        d.rectangle([X, Y - 4, X + 34, Y + 4], fill=col)
        d.polygon([(X + 34, Y - 6), (X + 42, Y), (X + 34, Y + 6)], fill=col)
    elif kind == 'gun':
        d.rectangle([X, Y - 3, X + 30, Y + 2], fill=col)
        d.polygon([(X + 26, Y + 2), (X + 34, Y + 2), (X + 38, Y + 10), (X + 30, Y + 10)], fill=col)
    else:
        d.polygon([(X, Y + 3), (X + 26, Y - 3), (X + 34, Y), (X + 26, Y + 3)], fill=col)


def kill_feed(p):
    dn = layout('HudDeathNotice')
    g = lambda k: kv.get(dn, k)
    x, y, w, h = box_of(dn)
    right = x + w
    lh, sp = float(g('LineHeight')), float(g('LineSpacing'))
    rows = [('Ingalther', 'red', 'rocket', 'Static', 'blue', True), ('Vex', 'blue', 'gun', 'Kuroi', 'red', False),
            ('Nyx', 'blue', 'knife', 'Reiko', 'red', False)]
    f = g('TextFont')
    for a, ta, icon, b, tb, local in rows:
        wa, wb = p.text_width(a, f), p.text_width(b, f)
        rw = 6 + wa + 5 + 20 + 5 + wb + 6
        x0 = right - rw
        bg = color(g('LocalBackgroundColor') if local else g('BaseBackgroundColor'))
        layer = Image.new('RGBA', p.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle([x0 * S, y * S, right * S, (y + lh) * S], fill=bg)
        over(p.img, layer)
        # the game writes the names in their team's colour on every row, yours too (hud_basedeathnotice.cpp)
        ca = g('TeamRed' if ta == 'red' else 'TeamBlue')
        cb = g('TeamRed' if tb == 'red' else 'TeamBlue')
        p.text(a, x0 + 6, y, wa + 1, lh, f, ca)
        placeholder_icon(p, icon, x0 + 6 + wa + 5, y + lh / 2, (20, 20, 22, 255) if local else (236, 232, 232, 235))
        p.text(b, right - 6 - wb, y, wb + 1, lh, f, cb)
        y += lh + sp


def top_status(p):
    body = first_body('resource/ui/hudmatchstatus.res')
    frame = kv.find(body, 'BGFrame')
    fx, fy, fw, fh = box_of(frame)
    p.nine(kv.get(frame, 'border'), fx, fy, fw, fh)
    # in a match. --timer: a mode with a round timer (payload, control points), its box the timer's own picture.
    # Otherwise casual CTF, which has no round timer: the flag panel draws the box, under the captures (below)
    if '--timer' in sys.argv:
        timer = kv.find(body, 'ObjectiveStatusTimePanel')
        tm = kv.find(timer, 'if_match')
        tw = size(kv.get(tm, 'wide'), UW)
        tx = coord(kv.get(tm, 'xpos'), UW, tw)
        box = kv.find(first_body('resource/ui/hudobjectivetimepanel.res'), 'RK_TimerBG')
        bx, by, bw, bh = box_of(box, tw)
        p.image(material(team_image(box))[0], tx + bx, by, bw, bh)
        val = kv.find(kv.find(timer, 'TimePanelValue'), 'if_match')
        vw = size(kv.get(val, 'wide'), tw)
        p.text('4:59', tx + coord(kv.get(val, 'xpos'), tw, vw), float(kv.get(val, 'ypos')), vw,
               float(kv.get(val, 'tall')), kv.get(val, 'font'), 'RK_Text', 'center')
    else:
        box = kv.find(first_body('resource/ui/hudobjectiveflagpanel.res'), 'RK_FlagBox')
        bx, by, bw, bh = box_of(box)
        p.image(material(team_image(box))[0], bx, by, bw, bh)
    st = kv.find(body, 'TeamStatus')
    pp = kv.find(st, 'playerpanels_kv')
    sw, sh = float(kv.get(pp, 'wide')), float(kv.get(pp, 'tall'))
    gap = float(kv.get(st, '6v6_gap'))
    sy = float(kv.get(pp, 'ypos'))
    slot = material('replay/thumbnails/rk/ig_slot')[0]
    dead = material('replay/thumbnails/rk/ig_slot_x')[0]
    pic, bar = kv.find(pp, 'classimage'), kv.find(pp, 'healthbar')
    py, ph = float(kv.get(pic, 'ypos')), float(kv.get(pic, 'tall'))
    bh = float(kv.get(bar, 'tall'))
    bw = size(kv.get(bar, 'wide'), sw)
    bx, by = coord(kv.get(bar, 'xpos'), sw, bw), float(kv.get(bar, 'ypos'))
    track = color(kv.get(bar, 'bgcolor_override'))
    health = {'blue': (1, 0.85, 0.5, 0, 1, 0.22), 'red': (0.7, 1, 0.45, 1, 0, 0.18)}  # the dead ones: 0
    for team, base, sign in (('blue', coord(kv.get(st, 'team1_base_x'), UW, 0), -1),
                             ('red', coord(kv.get(st, 'team2_base_x'), UW, 0), 1)):
        col = color(kv.get(pp, 'color_portrait_bg_' + team))
        for i in range(6):
            x = base + i * (sw + gap) if sign > 0 else base - i * (sw + gap) - sw
            p.image(slot, x, sy, sw, sh)
            d = ImageDraw.Draw(p.img)
            px0 = x + (sw - ph) / 2  # the class portrait (the game's picture): a placeholder
            d.rectangle([px0 * S, (sy + py) * S, (px0 + ph) * S - 1, (sy + py + ph) * S - 1],
                        fill=(70, 66, 72, 255) if team == 'blue' else (86, 64, 62, 255))
            d.rectangle([x * S, sy * S, (x + sw) * S, (sy + 1) * S], fill=col)
            f = health[team][i]
            if f:
                d.rectangle([(x + bx) * S, (sy + by) * S, (x + bx + bw) * S - 1, (sy + by + bh) * S - 1], fill=track)
                key = 'high' if f > float(kv.get(pp, 'percentage_health_med')) else (
                    'med' if f > float(kv.get(pp, 'percentage_health_low')) else 'low')
                d.rectangle([(x + bx) * S, (sy + by) * S, (x + bx + bw * f) * S - 1, (sy + by + bh) * S - 1],
                            fill=color(kv.get(pp, 'color_bar_health_' + key)))
            else:
                p.image(dead, x, sy, sw, sh)
    if '--timer' not in sys.argv:  # CTF: the captures in the flag panel's box, the capture limit under it
        flag = first_body('resource/ui/hudobjectiveflagpanel.res')
        p.panels([e for e in flag if e[0] in ('BlueScore', 'RedScore', 'PlayingTo')], 0, 0, UW, 480,
                 {'BlueScore': '1', 'RedScore': '2', 'PlayingTo': 'PLAYING TO: 3'})


def target_id(p):
    """Looking at a player: the game floats their health over their head (the health chip, HealthIconPanel.res) and
    the card under the crosshair holds the name only, its art at tf_hud_target_id_alpha (100 of 255)."""
    lay = layout('CMainTargetID')
    _, y, _, h = box_of(lay)
    body = first_body('resource/ui/targetid.res')
    name = 'Static'
    tw = p.text_width(name, kv.get(kv.find(body, 'TargetNameLabel'), 'font'))
    width = (5 + 10) * 3 / S + tw  # XRES(5) + XRES(10) + the name, as the game sums it (a player's has no health tile)
    x = (UW - width) / 2
    tex, _ = material(kv.get(kv.find(body, 'TargetIDBG'), 'teambg_3'))
    p.image(tex, x, y, width, h, alpha=100)
    nx = x + 8 * 3 / S
    for n, s in (('TargetNameLabel', name), ('TargetDataLabel', '')):
        blk = kv.find(body, n)
        if s:
            p.text(s, nx, y + float(kv.get(blk, 'ypos')), 200, float(kv.get(blk, 'tall')), kv.get(blk, 'font'),
                   'RK_Text')
    # the chip over the target's head, a little above the crosshair; it clips the three-chip-wide fill to itself
    icon = kv.find(first_body('resource/ui/healthiconpanel.res'), 'HealthIcon')
    cw, ch = float(kv.get(icon, 'wide')), float(kv.get(icon, 'tall'))
    cx, cy = (UW - cw) / 2, 240 - 34 - ch

    def gauge(pp, gx, gy, gw, gh, frac=0.62):
        x0, x1 = max(gx, cx), min(gx + gw, cx + cw)
        pp.image(Image.new('RGBA', (8, 8), (255, 255, 255, 255)), x0, gy + gh * (1 - frac), x1 - x0, gh * frac)
    p.panels(first_body('resource/ui/spectatorguihealth.res'), cx, cy, cw, ch,
             {'RK_HealthValue': '93', 'PlayerStatusHealthImage': gauge})


def chat(p):
    lay = layout('HudChat')
    x, y, w, h = box_of(lay)
    hist = kv.find(first_body('resource/ui/basechat.res'), 'HudChatHistory')
    hx, hy = x + float(kv.get(hist, 'xpos')), y + float(kv.get(hist, 'ypos'))
    hh = float(kv.get(hist, 'tall'))
    lines = [[('*DEAD* ', 'RK_Grey'), ('Kuroi', '255 120 104 255'), (' :  gg, that rocket was clean', 'RK_Text')],
             [('Static', '112 164 232 255'), (' :  intel incoming, watch sewers', 'RK_Text')],
             [('Ingalther', '255 120 104 255'), (' :  well played', 'RK_Text')]]
    lh = FONTS['ChatFont']['cell'] / S
    ly = hy + hh - lh * len(lines)
    for parts in lines:
        lx = hx
        for t, col in parts:
            tw = p.text_width(t, 'ChatFont')
            p.text(t, lx, ly, tw + 1, lh, 'ChatFont', col)
            lx += tw
        ly += lh


def ingame(shot, out):
    p = Painter(Image.open(shot).convert('RGB').resize((W, H), Image.LANCZOS))
    model = Image.open(os.path.join(TOOLS, 'style', 'portrait_src.jpg')).convert('RGBA')

    def model_panel(pp, x, y, w, h):  # the live model: a stand-in render
        pp.image(model, x, y, w, h)

    def gauge(pp, x, y, w, h, frac=0.71):
        pp.image(Image.new('RGBA', (8, 8), (255, 255, 255, 255)), x, y + h * (1 - frac), w, h * frac)

    body = res('resource/ui/hudplayerclass.res')
    p.panels(kv.find(body, 'Resource/UI/HudPlayerClass.res'), 0, 0, UW, 480,
             {'classmodelpanel': model_panel, 'PlayerStatusClassImage': lambda *a: None,
              'PlayerStatusSpyImage': lambda *a: None, 'PlayerStatusSpyOutlineImage': lambda *a: None,
              'CarryingWeapon': lambda *a: None})
    body = res('resource/ui/hudplayerhealth.res')
    hb = kv.find(body, 'Resource/UI/HudPlayerHealth.res')
    hp = '142'
    values = {'PlayerStatusMaxHealthValue': '200', 'RK_MaxSlash': '200', 'PlayerStatusHealthImage': gauge}
    values.update(PlayerStatusHealthValue=hp, RK_HealthGhost=hp, RK_HealthGlow=hp, RK_HealthSplit=hp)
    if '--critical' in sys.argv:  # near death: HudHealthDyingPulse at the top of its flicker (team pictures on BLU)
        hp = '41'

        def full(image, alpha=255):
            path = 'replay/thumbnails/rk/' + ('b/' if BLU else '') + image
            return lambda pp, x, y, w, h: pp.image(material(path)[0], x, y, w, h, alpha=alpha)

        def hot(pp, x, y, w, h):  # the digits' flash: their copy, white under the team's sheet
            blk = kv.find(hb, 'RK_HealthHot')
            pp.text(hp, x, y, w, h, kv.get(blk, 'font'), '255 255 255 255', kv.get(blk, 'textAlignment'))
        def kick(col):  # the HUD kick's red / cyan copies of the digits (blackwall.py), at their flash
            def draw(pp, x, y, w, h):
                blk = kv.find(hb, 'RK_HealthHot')
                pp.text(hp, x, y, w, h, kv.get(blk, 'font'), col, kv.get(blk, 'textAlignment'))
            return draw

        def slid(image, dx, alpha):  # a slice of the vignette, jumped sideways
            return lambda pp, x, y, w, h: pp.image(material('replay/thumbnails/rk/' + ('b/' if BLU else '') + image)[0],
                                                   x + dx, y, w, h, alpha=alpha)
        # the Blackwall's near-death glitch (tools/blackwall.py) a moment after the once-a-second kick: the vignette's
        # slices jumped, a few glitch blocks and a thin glyph line lit, the code columns
        values.update(RK_HealthDanger=full('ig_health_danger'),
                      PlayerStatusHealthImage=lambda pp, x, y, w, h: gauge(pp, x, y, w, h, frac=0.2),
                      PlayerStatusHealthValue=lambda *a: None, RK_HealthHot=hot,
                      RK_HealthGhost=hp, RK_HealthGlow=hp, RK_HealthSplit=hp,
                      RK_HealthKickR=kick('255 20 60 200'), RK_HealthKickC=kick('0 214 255 170'),
                      RK_BWVig1=slid('bw_vig1', -7, 230), RK_BWVig2=slid('bw_vig2', 5, 230),
                      RK_BWVig3=slid('bw_vig3', -3, 230), RK_BWCodeL=full('bw_code', 120), RK_BWCodeR=full('bw_code', 120),
                      RK_BWStrip4=full('bw_glyphs', 255))
        for i, (img, a) in {2: ('bw_block2', 230), 5: ('bw_block1', 180), 9: ('bw_block3', 200), 12: ('bw_block4', 160),
                            13: ('bw_block2', 210)}.items():
            values['RK_BWBlock%d' % i] = full(img, a)
    hidden = () if '--critical' in sys.argv else ('RK_HealthKickR', 'RK_HealthKickC')  # alpha 0 until the kick
    p.panels(hb, 0, 0, UW, 480, values,
             skip=[n for n, b, _ in hb if n in hidden or n.startswith('PlayerStatus_') or n.endswith(('Image', 'Slowed'))
                   and n not in ('PlayerStatusHealthImage', 'PlayerStatusHealthImageBG')])
    a = layout('HudWeaponAmmo')
    ax, ay, aw, ah = box_of(a)
    root = first_body('resource/ui/hudammoweapons.res')
    p.panels(root, ax, ay, aw, ah, {'AmmoInClip': '4', 'AmmoInClipShadow': '4', 'RK_AmmoGlow': '4',
                                    'AmmoInReserve': '20', 'AmmoInReserveShadow': '20',
                                    'AmmoNoClip': lambda *a: None, 'AmmoNoClipShadow': lambda *a: None,
                                    'HudWeaponLowAmmoImage': lambda *a: None})

    def bar(frac):
        def draw(pp, x, y, w, h):
            pp.image(Image.new('RGBA', (8, 8), (118, 116, 120, 255)), x, y, w, h)
            pp.image(Image.new('RGBA', (8, 8), (255, 255, 255, 255)), x, y, w * frac, h)
        return draw
    if '--engy' not in sys.argv:  # the generic meter's row holds the engineer's metal (no engineer item uses it)
        panel_file(p, 'resource/ui/huditemeffectmeter.res', {'ItemEffectMeterLabel': 'RAGE', 'ItemEffectMeter': bar(0.64)})
    if '--demo' in sys.argv:
        panel_file(p, 'resource/ui/huddemomanpipes.res', {'NumPipesLabel': '3', 'NumPipesLabelDropshadow': '3',
                                                         'ChargeMeter': lambda *a: None, 'ChargeLabel': lambda *a: None},
                   'HudDemomanPipes', skip=('NoPipesPresentPanel',))
        pp = kv.find(first_body('resource/ui/huddemomanpipes.res'), 'PipesPresentPanel')
        lay = layout('HudDemomanPipes')
        x, y, w, h = box_of(lay)
        p.panels(pp, x, y, w, h, {'NumPipesLabel': '3', 'NumPipesLabelDropshadow': '3'})
        panel_file(p, 'resource/ui/huddemomancharge.res', {'ChargeMeter': bar(0.45)}, 'HudDemomanCharge')
    if '--engy' in sys.argv:
        lay = layout('CHudAccountPanel')
        x, y, w, h = box_of(lay)
        p.panels(first_body('resource/ui/hudaccountpanel.res'), x, y, w, h, {'AccountValue': '200'})
    if '--medic' in sys.argv:
        panel_file(p, 'resource/ui/hudmediccharge.res', {'ChargeLabel': '64', 'IndividualChargesLabel': lambda *a: None,
                                                        'ChargeMeter': bar(0.64)},
                   'HudMedicCharge', skip=('ChargeMeter1', 'ChargeMeter2', 'ChargeMeter3', 'ChargeMeter4', 'ResistIcon'))
    panel_file(p, 'resource/ui/huditemeffectmeter_killstreak.res', {'ItemEffectMeterCount': '3'})
    top_status(p)
    kill_feed(p)
    target_id(p)
    chat(p)
    p.img.convert('RGB').save(out, quality=92)


def menu(out, shot=None):
    """The main menu; shot: a game screenshot under it, as the ESC menu over a match (with --ingame)."""
    base = Image.open(shot).convert('RGB').resize((W, H), Image.LANCZOS) if shot else Image.new('RGB', (W, H), (0, 0, 0))
    p = Painter(base, {'CharacterSetupButton': 'border_armed'})
    bg = material('../console/background_reaper_widescreen')[0]
    if bg is not None and not shot:
        p.image(bg, 0, 0, UW, 480)
    body = kv.find(res('resource/ui/mainmenuoverride.res'), 'Resource/UI/MainMenuOverride.res')
    skip = ('RankModelPanel', 'RankPanel', 'MOTD_Panel', 'Notifications_Panel', 'NoGCMessage', 'NoGCImage',
            'CycleRankTypeButton', 'RankTooltipPanel', 'StoreHasNewItemsImage')
    if '--ingame' in sys.argv:  # the ESC menu over a match: the game hides the scene, the class picture (the shade)
        skip += ('Background', 'TFCharacterImage', 'RK_MenuVideo')  # and the video's third part (gamemenu.res)
    p.panels(body, 0, 0, UW, 480, {}, skip=skip)
    fr = kv.find(body, 'FriendsContainer')
    if fr is not None:
        fw, fh = float(kv.get(fr, 'wide')), float(kv.get(fr, 'tall'))
        fx, fy = coord(kv.get(fr, 'xpos'), UW, fw), coord(kv.get(fr, 'ypos'), 480, fh)
        p.panels(fr, fx, fy, fw, fh, {'TitleLabel': 'FRIENDS'})
    p.img.convert('RGB').save(out, quality=92)


def screen(rel, out, armed=()):
    """A full-screen menu's .res (class select, team select, briefing...) over black; armed: buttons drawn hovered."""
    p = Painter(Image.new('RGB', (W, H), (0, 0, 0)), {n: 'border_armed' for n in armed})
    body = next(e[1] for e in res(rel) if isinstance(e[1], list))
    p.panels(body, 0, 0, UW, 480, {})
    p.img.convert('RGB').save(out, quality=92)


if __name__ == '__main__':
    if sys.argv[1] == 'screen':
        screen(sys.argv[2], sys.argv[3], sys.argv[4].split(',') if len(sys.argv) > 4 else ())
    elif sys.argv[1] == 'ingame':
        ingame(sys.argv[2], sys.argv[3])
    else:
        menu(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None)
