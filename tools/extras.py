"""The HUD's own crosshairs, its damage direction indicator, and the screens TF2 shows now and then: the casual match
summary, Mann vs. Machine, notification toasts. Each in the Beyond the Wall look.

Crosshairs (tf_hud_crosshair.cpp): with cl_crosshair_file set, the game draws the material vgui/crosshairs/<file>
in a square 2 x cl_crosshair_scale pixels wide (64 at the default 32) at the crosshair, multiplied by
cl_crosshair_red / _green / _blue. Ours are drawn in their own colours, so HUD Settings sets the colour to white
when it picks one; DEFAULT (cfg/rk_crosshair_default.cfg) gives each weapon its own crosshair and the stock grey
back. Valve's servers (sv_pure) load a HUD's textures only from materials/vgui/replay/thumbnails (a missing
crosshair is drawn as the purple and black error pattern), so ours live there, as rk/xhair_<name>, and the file
name climbs out of vgui/crosshairs to them (XH_FILE), the way the stock layouts reach materials/hud with "../hud/".

Damage indicator (tf_hud_damageindicator.cpp): the material VGUI/damageindicator on a quad on a circle round the
screen's centre, turned toward where the damage came from, its top edge outward; MinimumWidth .. MaximumWidth by
the damage taken (hudlayout's HudDamageIndicator), its vertex alpha fading it out. The game names that material
itself, so it stays at its stock path: sv_pure servers keep the stock texture (at our sizes), the others draw ours.
"""
import math
import os
import re

import numpy as np
from PIL import Image, ImageChops, ImageDraw

import kv
import ingame as G
from build_art import Tex, c, chamfer, linear_alpha
from vtf import write_vtf

PX = 2.25
T = 'replay/thumbnails/rk/'
RED, HOT, WHITE, INK, PANEL = (224, 26, 46), (255, 52, 76), (236, 232, 232), (7, 7, 9), (9, 9, 11)
SPLIT_R, SPLIT_C = (255, 20, 60), (0, 214, 255)
GREY = (138, 132, 138)
BAND_HOT = (70, 8, 18)      # a hot band: deeper than the crimson, lighter than ink


def _vmt(path, base, extra=''):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('"UnlitGeneric"\n{\n'
                f'\t"$basetexture"\t"{base}"\n'
                '\t"$translucent"\t"1"\n\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n'
                '\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n' + extra + '}\n')


def _material(root, rel, img, mips=True):
    """materials/<rel>.vtf and .vmt (rel without the extension, e.g. vgui/damageindicator)."""
    p = os.path.join(root, 'materials', rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    write_vtf(p + '.vtf', linear_alpha(img), alpha=True, mips=mips)
    _vmt(p + '.vmt', rel)


# ------------------------------------------------------------------ crosshairs
# drawn in a 64 x 64 px box (the game's square at the default scale), centre 32, 32; a texture of twice that
XH_S = 2


def _arc(t, cx, cy, r, a0, a1, col, width):
    n = max(4, int(abs(a1 - a0) / 6))
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
           for i in range(n + 1)]
    t.line(pts, col, width)


def _xh_dot(t, col, dx, w, core):
    s = XH_S
    r = (3.2 + w / 2) * s
    t.ellipse((32 + dx) * s, 32 * s, r, r, fill=col)


def _xh_cross(t, col, dx, w, core):
    s = XH_S
    for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        t.line([((32 + dx + ax * 4) * s, (32 + ay * 4) * s), ((32 + dx + ax * 11) * s, (32 + ay * 11) * s)], col,
               (1.6 + w) * s)
    if core:
        t.ellipse(32 * s, 32 * s, 1.0 * s, 1.0 * s, fill=col)


def _xh_brackets(t, col, dx, w, core):
    s = XH_S
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x, y = 32 + dx + sx * 9, 32 + sy * 9
        t.line([((x) * s, (y - sy * 5) * s), (x * s, y * s), ((x - sx * 5) * s, y * s)], col, (1.5 + w) * s)
    r = (1.4 + w / 2) * s
    t.ellipse((32 + dx) * s, 32 * s, r, r, fill=col)


def _xh_ring(t, col, dx, w, core):
    s = XH_S
    for a in (45, 135, 225, 315):
        _arc(t, (32 + dx) * s, 32 * s, 9 * s, a - 30, a + 30, col, (1.4 + w) * s)
    for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        t.line([((32 + dx + ax * 11) * s, (32 + ay * 11) * s), ((32 + dx + ax * 15) * s, (32 + ay * 15) * s)], col,
               (1.4 + w) * s)
    r = (1.2 + w / 2) * s
    t.ellipse((32 + dx) * s, 32 * s, r, r, fill=col)


def _xh_chevron(t, col, dx, w, core):
    s = XH_S
    t.line([((32 + dx - 6) * s, 42 * s), ((32 + dx) * s, 37 * s), ((32 + dx + 6) * s, 42 * s)], col, (1.6 + w) * s)
    for sx in (-1, 1):
        t.line([((32 + dx + sx * 7) * s, 32 * s), ((32 + dx + sx * 12) * s, 32 * s)], col, (1.4 + w) * s)
    r = (1.6 + w / 2) * s
    t.ellipse((32 + dx) * s, 32 * s, r, r, fill=col)


def _xh_glitch(t, col, dx, w, core):
    s = XH_S
    for (x0, x1, y) in ((-16, -11, 32), (-9, -5, 31), (5, 9, 33), (11, 16, 32)):
        t.line([((32 + dx + x0) * s, y * s), ((32 + dx + x1) * s, y * s)], col, (1.6 + w) * s)
    t.line([((32 + dx) * s, 37 * s), ((32 + dx) * s, 42 * s)], col, (1.6 + w) * s)
    r = (1.5 + w / 2) * s
    t.ellipse((32 + dx) * s, 32 * s, r, r, fill=col)


CROSSHAIRS = [('dot', 'DOT', _xh_dot), ('cross', 'CROSS', _xh_cross), ('brackets', 'BRACKET', _xh_brackets),
              ('ring', 'RING', _xh_ring), ('chevron', 'CHEVRON', _xh_chevron), ('glitch', 'GLITCH', _xh_glitch)]


def crosshair(draw):
    """One crosshair, 128 x 128: a dark outline (readable on bright walls), the red and cyan copies a pixel either
    side, the crimson shape, a white core dot."""
    t = Tex(64 * XH_S, 64 * XH_S, ss=4)
    draw(t, (0, 0, 0, 150), 0, 1.6, True)
    draw(t, c(SPLIT_R, 120), -1.1, 0, False)
    draw(t, c(SPLIT_C, 110), 1.1, 0, False)
    draw(t, c(RED), 0, 0, True)
    t.ellipse(32 * XH_S, 32 * XH_S, 0.8 * XH_S, 0.8 * XH_S, fill=c((255, 255, 255)))
    return t.result()


XH_CARD = 40                # HUD Settings: a crosshair's card, square, units


def crosshair_card(img, hover=False, label=None):
    """Its card in HUD Settings: black glass with the crosshair at 2.5 times its size in the middle; under the pointer
    a crimson wash and a crimson frame. label: text instead of a crosshair (DEFAULT)."""
    p = G.Px(XH_CARD, XH_CARD, 256 / (XH_CARD * PX))
    w, h = p.W, p.H
    shape = chamfer(0, 0, w, h, br=10)
    p.poly(shape, c((40, 8, 14) if hover else PANEL, 240))
    G.scan_in(p, shape, WHITE, 12)
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=9.5)
    if hover:
        p.outline(edge, c(HOT), 1.5)
    else:
        G.torn(p, edge, seed=4, a=150, gaps=0.2, seg=30)
    im = p.result()
    if img is not None:
        k = im.width / w
        size = int(round(64 * 2.5 * k))               # the crosshair at 2.5 times its size: its middle fills the card
        cross = img.resize((size, size), Image.LANCZOS)
        off = (size - im.width) // 2
        im.alpha_composite(cross.crop((off, off, off + im.width, off + im.height)))
    elif label:
        t = Tex(im.width, im.height, ss=2)
        t.text(im.width / 2, im.height / 2, label, ('raj7', im.height * 0.28), c(WHITE if hover else GREY), 'mm')
        im.alpha_composite(t.result())
    return im


XH_FILE = '../replay/thumbnails/rk/xhair_'   # cl_crosshair_file for ours: vgui/crosshairs/ + this + the name


def crosshairs(root, out):
    for name, _, draw in CROSSHAIRS:
        img = crosshair(draw)
        out.thumb(f'xhair_{name}', img, mips=True)
        out.thumb(f'xh_{name}', crosshair_card(img), mips=False)
        out.thumb(f'xh_{name}_h', crosshair_card(img, hover=True), mips=False)
    out.thumb('xh_default', crosshair_card(None, label='TF2'), mips=False)
    out.thumb('xh_default_h', crosshair_card(None, hover=True, label='TF2'), mips=False)
    for n, lbl in (('mine', 'MINE'), ('save', 'SAVE')):
        out.thumb(f'xh_{n}', crosshair_card(None, label=lbl), mips=False)
        out.thumb(f'xh_{n}_h', crosshair_card(None, hover=True, label=lbl), mips=False)
    os.makedirs(os.path.join(root, 'cfg'), exist_ok=True)
    with open(os.path.join(root, 'cfg', 'rk_crosshair_default.cfg'), 'w', encoding='utf-8') as f:
        f.write('// The Reaper HUD: HUD Settings > CROSSHAIR > DEFAULT. Each weapon\'s own crosshair, in the stock grey.\n'
                'crosshair 1\ncl_crosshair_file ""\ncl_crosshair_red 200\ncl_crosshair_green 200\ncl_crosshair_blue 200\n')
    with open(os.path.join(root, 'cfg', 'rk_crosshair_hud.cfg'), 'w', encoding='utf-8') as f:
        f.write('// The Reaper HUD: HUD Settings > CROSSHAIR > one of the HUD\'s. The HUD draws it itself, so the game\'s '
                'own is turned off.\ncrosshair 0\ncl_crosshair_file ""\n')


# The player's own crosshair, to go back to. A menu cannot read a setting, so the build keeps it: from the note the
# SAVE card leaves (host_writeconfig writes the game's settings, the crosshair as it is at that moment, to
# cfg/rk_crosshair_save.cfg in TF2's folder), else, while none is kept yet, from TF2's own cfg/config.cfg when the
# crosshair in it is not one of the HUD's. Kept in XH_OWN at the HUD's root; MINE runs cfg/rk_crosshair_mine.cfg.
XH_OWN = 'rk_crosshair.txt'
XH_MARK = 'rk_crosshair_save.cfg'
XH_VARS = ('cl_crosshair_file', 'cl_crosshair_scale', 'cl_crosshair_red', 'cl_crosshair_green', 'cl_crosshair_blue')


def _crosshair_in(path):
    """The crosshair settings in a config file the game wrote: {name: value}, or None without cl_crosshair_file."""
    found = {}
    try:
        for line in open(path, encoding='utf-8', errors='replace'):
            m = re.match(r'\s*(cl_crosshair_\w+)\s+"([^"]*)"', line)
            if m and m.group(1).lower() in XH_VARS:
                found[m.group(1).lower()] = m.group(2)
    except OSError:
        return None
    return found if 'cl_crosshair_file' in found else None


def crosshair_own(root, tf):
    """Keep the player's own crosshair and write MINE's config; returns what is kept (None: nothing yet)."""
    store = os.path.join(root, XH_OWN)
    cfg = os.path.join(tf, 'cfg') if tf else None
    own = None
    if cfg and os.path.isdir(cfg):
        mark = os.path.join(cfg, XH_MARK)
        own = _crosshair_in(mark)
        if os.path.isfile(mark):
            try:
                os.remove(mark)
            except OSError:
                pass
        if own is None and not os.path.isfile(store):
            own = _crosshair_in(os.path.join(cfg, 'config.cfg'))
            if own and 'thumbnails/rk/xhair_' in own['cl_crosshair_file'].replace('\\', '/'):
                own = None
    if own:
        with open(store, 'w', encoding='utf-8') as f:
            f.writelines(f'{k} "{own[k]}"\n' for k in XH_VARS if k in own)
    elif os.path.isfile(store):
        own = _crosshair_in(store)
    os.makedirs(os.path.join(root, 'cfg'), exist_ok=True)
    with open(os.path.join(root, 'cfg', 'rk_crosshair_mine.cfg'), 'w', encoding='utf-8') as f:
        f.write('// The Reaper HUD: HUD Settings > CROSSHAIR > MINE. Your own crosshair, as update.bat kept it.\n')
        f.write('crosshair 1\n')
        if own:
            f.writelines(f'{k} "{own[k]}"\n' for k in XH_VARS if k in own)
        else:
            f.write('echo "Reaper HUD: no crosshair of yours is kept yet. Set yours, click SAVE, run update.bat."\n')
    return own


# One of the HUD's crosshairs: Valve's servers (sv_pure) draw a crosshair file of the player's own as the purple and
# black checkerboard, whichever folder it is in, so the HUD draws the crosshair itself: a picture at the screen's
# centre in the health panel (full screen, and hidden with the HUD), the game's own crosshair off (crosshair 0). A
# menu cannot change the HUD's files, so the pick goes the kill sound's way: the card leaves a note
# (host_writeconfig rk_xhairpick_<name>), update.bat's build reads the newest and keeps it in XH_PICK.
XH_PICK = 'rk_crosshair_pick.txt'
XH_PICK_MARK = 'rk_xhairpick_'
XH_SIZE = 28                # the drawn crosshair, units
_pick = []


def crosshair_pick(root, tf):
    """The HUD crosshair picked in HUD Settings (a name from CROSSHAIRS) or None; read once a build."""
    if _pick:
        return _pick[0]
    store = os.path.join(root, XH_PICK)
    cfg = os.path.join(tf, 'cfg') if tf else None
    pick = None
    marks = []
    if cfg and os.path.isdir(cfg):
        marks = sorted((os.path.join(cfg, f) for f in os.listdir(cfg) if f.lower().startswith(XH_PICK_MARK)),
                       key=os.path.getmtime)
    if marks:
        pick = os.path.basename(marks[-1])[len(XH_PICK_MARK):].lower()
        pick = pick[:-4] if pick.endswith('.cfg') else pick
        with open(store, 'w', encoding='utf-8') as f:
            f.write(pick + '\n')
        for m in marks:
            try:
                os.remove(m)
            except OSError:
                pass
    elif os.path.isfile(store):
        pick = open(store, encoding='utf-8').read().strip().lower()
    pick = pick if pick in [n for n, _, _ in CROSSHAIRS] else None
    _pick.append(pick)
    return pick


def crosshair_panel(root, pick):
    """The picked crosshair in the health panel, at the screen's centre in both layouts."""
    body = kv.find(root, 'Resource/UI/HudPlayerHealth.res')
    kv.remove(body, 'RK_Crosshair')
    if not pick:
        return
    half = XH_SIZE // 2
    kv.add_block(body, 'RK_Crosshair', {
        'ControlName': 'ImagePanel', 'fieldName': 'RK_Crosshair', 'xpos': f'c-{half}', 'ypos': f'c-{half}', 'zpos': 20,
        'wide': XH_SIZE, 'tall': XH_SIZE, 'visible': 1, 'enabled': 1, 'mouseinputenabled': 0, 'scaleImage': 1,
        'image': f'replay/thumbnails/rk/xhair_{pick}'})


XH_CARDS = [f'xh_{n}' for n, _, _ in CROSSHAIRS] + ['xh_default', 'xh_mine', 'xh_save']   # (screens.CARD_BORDERS: their hover borders)


def crosshair_section(motd, y, add, label_block, card_button, block, red, grey, popup_w):
    """HUD Settings' CROSSHAIR row: a card per crosshair and DEFAULT, their names under them, a note on the right."""
    add(motd, 'RK_PopupSection4', label_block('RK_PopupSection4', 22, y, 300, 12, 'CROSSHAIR', 'RK_Mono', red))
    cards = [(n, lbl, f'engine exec rk_crosshair_hud; host_writeconfig {XH_PICK_MARK}{n}') for n, lbl, _ in CROSSHAIRS]
    cards.append(('default', 'DEFAULT', f'engine exec rk_crosshair_default; host_writeconfig {XH_PICK_MARK}off'))
    cards.append(('mine', 'MINE', f'engine exec rk_crosshair_mine; host_writeconfig {XH_PICK_MARK}off'))
    cards.append(('save', 'SAVE MINE', 'engine host_writeconfig rk_crosshair_save'))
    for i, (n, lbl, command) in enumerate(cards):
        name = f'RK_Xh_{n}'
        x = 22 + i * (XH_CARD + 8)
        blk = block(name, {'fieldName': name, 'visible': 1, 'enabled': 1, 'tabPosition': 0,
                           'sound_depressed': 'UI/buttonclick.wav', 'sound_released': 'UI/buttonclickrelease.wav',
                           'sound_armed': 'UI/buttonrollover.wav'})
        kv.remove(motd, name)
        motd.append([name, blk, None])
        card_button(motd, blk, f'xh_{n}', x, y + 16, XH_CARD, XH_CARD, command)
        kv.set(blk, 'actionsignallevel', 2)
        add(motd, name + 'Name', label_block(name + 'Name', x, y + 18 + XH_CARD, XH_CARD, 10, lbl, 'RK_Small', grey,
                                              align='center'))
    nx = 22 + len(cards) * (XH_CARD + 8) + 6
    blk = label_block('RK_PopupNote5', nx, y + 16, popup_w - nx - 22, XH_CARD + 14, 'Choose a crosshair for this HUD. It '
                      'shows up after you close TF2 and run update.bat (in the HUD\'s folder). DEFAULT: TF2\'s normal '
                      'crosshair. MINE: the crosshair you used before this HUD. SAVE MINE: saves the crosshair you '
                      'are using right now, so MINE can bring it back.', 'RK_Small', '128 124 130 255', align='north-west')
    blk['wrap'] = 1
    add(motd, 'RK_PopupNote5', blk)


# ------------------------------------------------------------------ damage indicator
DMG = {'MinimumWidth': 56, 'MaximumWidth': 124, 'MinimumHeight': 28, 'MaximumHeight': 62, 'StartRadius': 150,
       'EndRadius': 128, 'MinimumTime': 1, 'MaximumTime': 2.2, 'TravelTime': 0.12, 'FadeOutPercentage': 0.6}


def damage_indicator():
    """The damage indicator, 256 x 128, its top edge outward: an arc bowed round the screen's centre, a hot outer
    edge and a crimson band fading inward, its red and cyan copies slipped either side, bitten in two places, scan
    lines across, its ends fading."""
    W_, H_ = 256, 128
    ss = 4
    img = Image.new('RGBA', (W_ * ss, H_ * ss), (0, 0, 0, 0))
    yy, xx = np.mgrid[0:H_ * ss, 0:W_ * ss].astype(np.float32) / ss
    R = 300.0
    cx, cy = W_ / 2, 0.30 * H_ + R
    r = np.hypot(xx - cx, yy - cy)
    ang = np.degrees(np.arctan2(xx - cx, cy - yy))            # 0 at the arc's middle
    half = np.degrees(np.arcsin((W_ / 2 - 6) / R))
    ends = np.clip((half - np.abs(ang)) / 7.0, 0, 1)
    d = R - r                                                 # 0 at the outer edge, growing inward
    bites = np.ones_like(ang)
    for a0, a1 in ((-11, -8.5), (6.5, 8)):
        bites *= ~((ang > a0) & (ang < a1) & (d > 2))
    scan = 1 - 0.35 * ((np.floor(yy) % 4) == 0)

    def band(shift, col, alpha):
        dd = R - np.hypot(xx - cx - shift, yy - cy)
        edge = np.exp(-((dd - 1.2) / 1.1) ** 2)
        body = np.clip(1 - dd / 26, 0, 1) * (dd > 0)
        a = np.clip(edge * 1.0 + body * 0.7, 0, 1) * ends * bites * scan * alpha
        layer = np.zeros((H_ * ss, W_ * ss, 4), np.float32)
        layer[..., :3] = col
        layer[..., 3] = a * 255
        return Image.fromarray(layer.astype(np.uint8), 'RGBA')

    img.alpha_composite(band(-3.0, SPLIT_R, 0.45))
    img.alpha_composite(band(3.0, SPLIT_C, 0.35))
    img.alpha_composite(band(0, RED, 1.0))
    core = np.exp(-((d - 1.0) / 0.8) ** 2) * ends * bites
    layer = np.zeros((H_ * ss, W_ * ss, 4), np.float32)
    layer[..., :3] = (255, 200, 206)
    layer[..., 3] = core * 230
    img.alpha_composite(Image.fromarray(layer.astype(np.uint8), 'RGBA'))
    return img.resize((W_, H_), Image.LANCZOS)


def damage_material(root):
    _material(root, 'vgui/damageindicator', damage_indicator(), mips=False)


def patch_hudlayout(body):
    blk = kv.find(body, 'HudDamageIndicator')
    if blk is not None:
        kv.setmany(blk, fieldName='HudDamageIndicator', visible=1, enabled=1, **DMG)


# ------------------------------------------------------------------ shared
def _body(root):
    return next(e[1] for e in root if isinstance(e[1], list))


def _deep(node, name):
    """The block named name anywhere under node (the stock nests some panels in containers), or None."""
    for ent in kv.walk(node):
        if isinstance(ent[1], list) and ent[0].lower() == name.lower():
            return ent[1]
    return None


def _set(node, name, **kw):
    """Set keys on the block named name anywhere under node, if it is there."""
    blk = _deep(node, name)
    if blk is not None:
        kv.setmany(blk, **kw)
    return blk


def _border(image, draw_w, draw_h, src_w, src_h):
    """A 9-slice border: corners of src_w x src_h texture px drawn draw_w x draw_h units, the rest stretched."""
    return [['bordertype', 'scalable_image', None], ['backgroundtype', '2', None], ['image', T + image, None],
            ['src_corner_width', str(src_w), None], ['src_corner_height', str(src_h), None],
            ['draw_corner_width', str(draw_w), None], ['draw_corner_height', str(draw_h), None]]


def _whole(image):
    """A border that stretches its art over the whole panel (zero corners)."""
    return _border(image, 0, 0, 0, 0)


def _px(wu, hu, tex_w):
    """A drawing box wu x hu units at tex_w texture px across (G.Px works in 1080p px)."""
    return G.Px(wu, hu, tex_w / (wu * PX))


# ------------------------------------------------------------------ notification toasts
# The game's notifications (econ_notifications.cpp): a CGenericNotificationToast (GenericNotificationToast.res in a
# game, GenericNotificationToastMainMenu.res in the main menu's list) inside a CNotificationToastControl
# (NotificationToastContainer.res in a game, NotificationToastControl.res with its buttons in the main menu). The
# control is as tall as the toast (at least its own height) and paints the border; the toast grows by its text's
# height less its label's. A toast from a player (party invites, trades) shows their avatar and needs twice the
# avatar's y plus its height: the avatar sits in the band, as a chip after the band's label, and adds nothing.
NT_W, NT_H = 200, 50          # the toast art's box, units (1024 x 256 px), 9-sliced onto any toast
NT_CW, NT_CH = 64, 15         # its corners: the band (15 tall) and its label in the top left one
TOAST_Y, TOAST_PAD, TOAST_MIN = 19, 7, 36   # the text's top (under the band), the margin under it, the least height
MM_W, IG_W = 190, 150         # the main menu's toasts and the in-game ones, wide
AV_X = 62                     # the sender's avatar: a 13 unit chip in the band, x
BTN = 13                      # the main menu toast's buttons: in the band's right end, like a window's


def toast(hot=False):
    """A notification: black glass under a band with ■ 受信 // INCOMING in its left corner, the torn crimson frame, the
    bottom right corner cut, a crimson tab down the left edge. hot (high priority): crimson glass, the band deep
    crimson with ■ 警告 // PRIORITY, the frame lit whole with its red and cyan copies."""
    p = _px(NT_W, NT_H, 1024)
    w, h = p.W, p.H
    band = NT_CH * PX
    cut = 12
    shape = chamfer(0, 0, w, h, br=cut)
    p.poly(shape, c((30, 7, 12) if hot else PANEL, 246))
    G.scan_in(p, shape, RED if hot else WHITE, 20 if hot else 9)
    p.rect(0, 0, w, band - 1.5, c(BAND_HOT if hot else INK, 252))
    p.rect(0, band - 1.5, w, band - 0.3, c(HOT if hot else RED, 230 if hot else 170))
    p.rect(9, band / 2 - 3, 15, band / 2 + 3, c(WHITE if hot else RED))
    jp, en = ('警告', 'PRIORITY') if hot else ('受信', 'INCOMING')
    p.mixed(21, band / 2, [(jp, ('jp5', 11), c(WHITE)), ('  //  ', ('mono', 10), c((255, 140, 150) if hot else RED)),
                           (en, ('mono', 12), c(WHITE))], 'lm')
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=cut - 0.5)
    if hot:
        for dx, col, a in ((-1.5, SPLIT_R, 140), (1.5, SPLIT_C, 110)):
            p.outline([(x + dx, y) for x, y in edge], c(col, a), 1)
        p.outline(edge, c(HOT), 1.5)
    else:
        G.torn(p, edge, seed=11, a=150, gaps=0.15, seg=50)
    p.rect(0, band + 5, 2.5, band + 5 + (h - band) * 0.42, c(HOT if hot else RED))
    from build_art import wall_over
    return wall_over(p.result(), 'right', 0.22)   # 0.9: the Wall in it


NS_W, NS_H, NS_TAG = 240, 24, 38   # "You have pending alerts!" strip (inventory, store), its ■ 受信 tag's width


def alert_strip():
    """The pending alerts strip: black glass, the crimson ■ 受信 tag at its left end, the torn frame, a cut corner."""
    p = _px(NS_W, NS_H, 1024)
    w, h = p.W, p.H
    shape = chamfer(0, 0, w, h, br=10)
    p.poly(shape, c(PANEL, 244))
    G.scan_in(p, shape, WHITE, 9)
    tag = NS_TAG * PX
    p.rect(0, 0, tag, h, c(BAND_HOT, 250))
    p.rect(tag - 1, 0, tag, h, c(RED, 200))
    p.rect(8, h / 2 - 3, 14, h / 2 + 3, c(HOT))
    p.text(19, h / 2, '受信', ('jp5', 13), c(WHITE), 'lm')
    G.torn(p, chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=9.5), seed=13, a=150, gaps=0.15, seg=50)
    return p.result()


FONTS = {'RK_Toast': G.font_block('Bahnschrift SemiCondensed', 9, 500),
         'RK_ToastHot': G.font_block('Bahnschrift SemiBold Condensed', 11, 600),
         'RK_Credits': G.font_block('Rajdhani', 13, 700)}
_NT_SRC_W, _NT_SRC_H = round(NT_CW * 1024 / NT_W), round(NT_CH * 256 / NT_H)
BORDERS = {
    'RK_InkBtn': _border('ink_btn', 6, 6, 14, 14),
    'RK_InkBtn_h': _border('ink_btn_h', 6, 6, 14, 14),'NotificationDefault': _border('nt_toast', NT_CW, NT_CH, _NT_SRC_W, _NT_SRC_H),
           'NotificationHighPriority': _border('nt_toast_hot', NT_CW, NT_CH, _NT_SRC_W, _NT_SRC_H),
           'RK_AlertStrip': _whole('nt_strip')}


def _toast_button(blk, x, x_one=None):
    """A main menu toast button: its glyph in light grey on the band, a crimson chip under the pointer."""
    kv.setmany(blk, xpos=x, ypos=1, wide=BTN, tall=BTN, paintbackground=0, border_default='RK_Card_none',
               border_armed='MainMenuMiniButtonArmed', image_drawcolor='200 196 198 255',
               image_armedcolor='255 255 255 255')
    one = kv.find(blk, 'if_one_button')
    if one is not None:
        kv.set(one, 'xpos', x_one)
    kv.setmany(kv.find(blk, 'SubImage'), xpos=2, ypos=2, wide=BTN - 4, tall=BTN - 4)


def toast_control(root):
    """NotificationToastControl.res (the main menu's toasts): the toast art, the buttons in the band."""
    body = _body(root)
    ctl = kv.find(body, 'NotificationToastControl')
    kv.setmany(ctl, wide=MM_W, tall=TOAST_MIN, border='NotificationDefault', paintborder=1, paintbackground=0)
    kv.set(kv.find(ctl, 'if_high_priority'), 'border', 'NotificationHighPriority')
    right, left = MM_W - BTN - 1, MM_W - 2 * BTN - 2
    for name, x, x_one in (('DeleteButton', right, None), ('DeclineButton', right, None),
                           ('TriggerButton', left, right), ('AcceptButton', left, right)):
        blk = kv.find(body, name)
        if blk is not None:
            _toast_button(blk, x, x_one)


def toast_container(root):
    """NotificationToastContainer.res (in a game): the toast art; the game puts the help line ("Press [ F7 ] to
    CLOSE.") under the toast's text, in crimson mono."""
    body = _body(root)
    ctl = kv.find(body, 'NotificationToastContainer')
    kv.setmany(ctl, wide=IG_W, tall=TOAST_MIN, border='NotificationDefault')
    kv.add_block(ctl, 'if_high_priority', {'border': 'NotificationHighPriority'})
    kv.setmany(kv.find(body, 'HelpTextLabel'), xpos=8, wide=IG_W - 16, font='RK_Mono', fgcolor='224 26 46 255',
               textAlignment='north-west', textinsetx=0, textinsety=3)


def toast_body(root, width):
    """GenericNotificationToast(MainMenu).res: the text under the band in light grey (the main menu's was 44 41 44,
    dark on the dark glass), larger and white when the notification is high priority; the sender's avatar in the
    band."""
    body = _body(root)
    top = kv.find(body, 'GenericNotificationToast')
    for k in ('fgcolor', 'fgcolor_override'):
        kv.remove(top, k)
    kv.setmany(top, wide=width, tall=TOAST_Y + 38 + TOAST_PAD)
    for name in ('TextLabel', 'AvatarTextLabel'):
        blk = kv.find(body, name)
        kv.setmany(blk, xpos=8, ypos=TOAST_Y, wide=width - 16, tall=38, font='RK_Toast', fgcolor='236 232 232 255',
                   fgcolor_override='236 232 232 255', textAlignment='north-west', wrap=1)
        kv.add_block(blk, 'if_high_priority', {'font': 'RK_ToastHot', 'fgcolor': '255 255 255 255',
                                               'fgcolor_override': '255 255 255 255'})
    kv.setmany(kv.find(body, 'AvatarImage'), xpos=AV_X + 1, ypos=1, wide=13, tall=13, color_outline='0 0 0 0')
    kv.setmany(kv.find(body, 'AvatarBGPanel'), xpos=AV_X, ypos=0, wide=15, tall=15, PaintBackgroundType=0,
               bgcolor_override='224 26 46 255')


def alerts_present(root):
    """NotificationsPresentPanel.res ("You have pending alerts!" over the inventory and the store)."""
    body = _body(root)
    kv.setmany(kv.find(body, 'NotificationsPresentPanel'), xpos='c70', wide=NS_W, tall=NS_H, border='RK_AlertStrip')
    kv.setmany(kv.find(body, 'TextLabel'), xpos=NS_TAG + 6, ypos=0, wide=NS_W - NS_TAG - 12, tall=NS_H,
               font='RK_Small', fgcolor='236 232 232 255', textAlignment='west', proportionaltoparent=0)


# ------------------------------------------------------------------ casual match summary
# hudmatchsummary.res (the end of a casual / competitive match: the two teams' scores, their players, medals). The game
# slides the team panels in and moves the medals and the labels, so nothing here moves: the score bars, the player
# lists' pages and the team logos take the HUD's art, the scores their team's split copy.
MS_BAR = (180, 36)            # a score bar's art box, units (9-sliced: corners MS_BAR_CW wide, half its height tall)
MS_BAR_CW = 56
MS_SEAL = {'blue': (56, (21, 28)), 'red': (70, (33, 37))}   # the logo's box (square), the seal's centre in it
MS_SEAL_U = 34                # the seal, square, units
MS_SEAL_IN = 30               # its centre's distance from the bar's outer end (bars 5 in from the screen's edges)
TEAM_COL = {'blue': (112, 164, 232), 'red': (255, 120, 104)}
TEAM_DARK = {'blue': (12, 22, 40), 'red': (40, 9, 13)}


def ms_bar(team):
    """A team's score bar: deep team glass, the team's tab on the outer end and a bracket round the seal's place, a
    hatch and the cut corner at the inner end (where the game writes the score), the torn frame in the team's
    colour. BLU's outer end is the left, RED's the right."""
    wu, hu = MS_BAR
    p = _px(wu, hu, 1024)
    w, h = p.W, p.H
    col, dark = TEAM_COL[team], TEAM_DARK[team]
    mirror = team == 'red'
    cut = 12
    shape = chamfer(0, 0, w, h, tl=cut) if mirror else chamfer(0, 0, w, h, tr=cut)
    p.poly(shape, c(dark, 244))
    G.scan_in(p, shape, col, 16)
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, tl=cut - 0.5) if mirror else chamfer(0.5, 0.5, w - 0.5, h - 0.5,
                                                                                   tr=cut - 0.5)
    G.torn(p, edge, seed=17 if mirror else 15, col=col, a=170, gaps=0.15, seg=50)
    ox = w - 3 * PX if mirror else 0
    p.rect(ox, 0, ox + 3 * PX, h, c(col))
    # the seal's place (the logo panel draws it): brackets round it
    sc = (wu - MS_SEAL_IN) if mirror else MS_SEAL_IN
    p.brackets((sc - 19) * PX, 3, (sc + 19) * PX, h - 3, 7, c(col, 200), 1.2)
    # the inner end: a hatch by the cut
    hx = 8 if mirror else w - 8 - 24
    for i in range(4):
        x0 = hx + i * 6
        p.line([(x0, h - 6), (x0 + 6, h - 16)], c(col, 120), 1.2)
    from build_art import wall_over
    return wall_over(p.result(), 'right', 0.3)   # 0.9: the Wall in it


def ms_head(team):
    """0.9 (preview 20): a team list's head at the match's start, filled in the team's colour like the scoreboard's,
    the Wall shading it from the inner end, an ink band at its foot, the cut corner hot. The team's name is the
    game's label on it, in ink."""
    wu, hu = MS_BAR
    p = _px(wu, hu, 1024)
    w, h = p.W, p.H
    col = TEAM_COL[team] if team == 'blue' else (232, 38, 58)
    mirror = team == 'red'
    cut = 12
    shape = chamfer(0, 0, w, h, tl=cut) if mirror else chamfer(0, 0, w, h, tr=cut)
    p.poly(shape, c(col, 240))
    p.rect(0, h - 4 * PX, w, h, c(INK, 230))
    from build_art import wall_texture, HOT
    img = p.result()
    W_, H_ = img.size
    pat = wall_texture().convert('L').resize((W_, H_), Image.BICUBIC)
    ramp = Image.new('L', (W_, 1))
    px = ramp.load()
    for x in range(W_):
        f = x / max(1, W_ - 1)
        px[x, 0] = int(160 * ((1 - f) if mirror else f) ** 1.2)
    shade = Image.new('RGBA', (W_, H_), (0, 0, 0, 0))
    shade.putalpha(ImageChops.multiply(ImageChops.multiply(pat, ramp.resize((W_, H_))),
                                       img.split()[3].point(lambda v: 255 if v > 128 else 0)))
    img.alpha_composite(shade)
    d = ImageDraw.Draw(img)
    hx = W_ - 40 if mirror else 0   # the outer end
    d.rectangle([hx, 0, hx + 40, 6], fill=HOT + (255,))
    return img


def ms_seal(team):
    """The team logo's place: a square seal in the team's colour with 青 / 赤 in white and its red and cyan copies,
    centred where the score bar's outer end is (the logo boxes differ: MS_SEAL)."""
    box, (cx, cy) = MS_SEAL[team]
    t = Tex(256, 256, ss=4)
    k = 256 / box
    s = MS_SEAL_U * k
    x0, y0 = cx * k - s / 2, cy * k - s / 2
    col = TEAM_COL[team]
    for dx, sc, a in ((-3, SPLIT_R, 150), (3, SPLIT_C, 130)):
        t.rect(x0 + dx, y0, x0 + s + dx, y0 + s, c(sc, a))
    t.rect(x0, y0, x0 + s, y0 + s, c(col))
    t.outline([(x0 + 6, y0 + 6), (x0 + s - 6, y0 + 6), (x0 + s - 6, y0 + s - 6), (x0 + 6, y0 + s - 6)], c(INK, 120), 2)
    t.text(x0 + s / 2, y0 + s / 2 + 2, '青' if team == 'blue' else '赤', ('jp9', s * 0.62), c((255, 255, 255)), 'mm')
    return t.result()


def ms_list(team):
    """The player list's page: black glass, a hairline in the team's colour, a dot grid, the bottom outer corner cut
    (9-slice: 128 px, 16 px corners)."""
    p = _px(32, 32, 128)
    w, h = p.W, p.H
    mirror = team == 'red'
    shape = chamfer(0, 0, w, h, bl=10) if mirror else chamfer(0, 0, w, h, br=10)
    p.poly(shape, c(PANEL, 236))
    p.dots(4, 4, w - 4, h - 4, WHITE, 16, step=5)
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, bl=9.5) if mirror else chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=9.5)
    p.outline(edge, c(TEAM_COL[team], 110), 1)
    return p.result()


_MS_SRC_W = round(MS_BAR_CW * 1024 / MS_BAR[0])
for _t in ('blue', 'red'):
    BORDERS[f'RK_MSBar_{_t}'] = _border(f'ms_bar_{_t}', MS_BAR_CW, MS_BAR[1] // 2, _MS_SRC_W, 128)
    BORDERS[f'RK_MSList_{_t}'] = _border(f'ms_list_{_t}', 4, 4, 16, 16)
    BORDERS[f'RK_MSHead_{_t}'] = _border(f'ms_head_{_t}', MS_BAR_CW, MS_BAR[1] // 2, _MS_SRC_W, 128)


def match_summary(root):
    body = _body(root)
    for team, name in (('blue', 'Blue'), ('red', 'Red')):
        _set(body, f'{name}TeamScoreBG', border=f'RK_MSBar_{team}')
        _set(body, f'{name}PlayerListBG', border=f'RK_MSList_{team}')
        _set(body, f'{name}TeamImage', image=T + f'ms_seal_{team}')
        # under the logo: it was grey round the seal (the game shows it with the leader's avatar in competitive)
        _set(body, f'{name}LeaderAvatarBG', bgcolor_override='0 0 0 0')
        r, g, b = TEAM_COL[team]
        for lbl in ('Score', 'Winner'):
            _set(body, f'{name}Team{lbl}', fgcolor='236 232 232 255')
            _set(body, f'{name}Team{lbl}Dropshadow', fgcolor=f'{r} {g} {b} 210')
    _set(body, 'StatsAndMedals', fgcolor='224 26 46 255')


def match_doors(root):
    """The match's start (the doors, the two teams' lists sliding in: HudMatchStatus.res) in the match summary's
    look: the teams' bars and seals, the lists' frames, the countdown white on a crimson ghost."""
    body = _body(root)
    for team, name in (('blue', 'Blue'), ('red', 'Red')):
        panel = kv.find(body, f'{name}TeamPanel')
        if panel is None:
            continue
        r, g, b = TEAM_COL[team]
        # 0.9 (preview 20): the head filled in the team's colour, BLU / RED large in ink on it, no seal
        _set(panel, f'{name}TeamBG', border=f'RK_MSHead_{team}')
        _set(panel, f'{name}PlayerListBG', border=f'RK_MSList_{team}')
        _set(panel, f'{name}TeamImage', visible=0, wide=0, tall=0)
        _set(panel, f'{name}LeaderAvatarBG', bgcolor_override='0 0 0 0')
        # the game's team-name label stays empty in casual matches (the heads came up blank): BLU / RED are the
        # HUD's own lines, the game's is hidden
        _set(panel, f'{name}TeamLabel', visible=0, wide=0)
        kv.remove(panel, f'RK_{name}Head')
        panel.append([f'RK_{name}Head', [[k, str(v), None] for k, v in (
            ('ControlName', 'CExLabel'), ('fieldName', f'RK_{name}Head'), ('xpos', 12 if team == 'blue' else 4),
            ('ypos', 10), ('zpos', 5), ('wide', 131), ('tall', 32), ('visible', 1), ('enabled', 1),
            ('labelText', 'BLU' if team == 'blue' else 'RED'), ('font', 'RK_Title'), ('fgcolor', '7 7 9 255'),
            ('textAlignment', 'west' if team == 'blue' else 'east'))], None])
    # the countdown large in the middle, its crimson ghost behind it; MATCH STARTS is the game's own line
    for n in ('CountdownLabel', 'CountdownLabelShadow'):
        blk = kv.find(body, n)
        if blk is not None:
            # centred on the middle of the screen (it sat low, under the logo's centre)
            kv.setmany(blk, font='RK_HealthHuge', wide=80, tall=60, xpos='cs-0.5' if n == 'CountdownLabel' else 'cs-0.47',
                       ypos='cs-0.62', textAlignment='center')
    _set(body, 'CountdownLabel', fgcolor='236 232 232 255')
    _set(body, 'CountdownLabelShadow', fgcolor='224 26 46 220')


def vote(root):
    """The vote panels (VoteHud.res: a vote running, passed, failed, and the call-a-vote dialog) as the HUD's cards:
    the match summary's black glass page, the header in small crimson mono, the question in the menu face, the
    option the player took marked crimson, the dialog's buttons in flat ink."""
    import screens
    body = _body(root)
    for name in ('VotePassed', 'VoteActive', 'CallVoteFailed', 'VoteFailed', 'VoteSetupDialog'):
        blk = _deep(body, name)
        if blk is None:
            continue
        kv.setmany(blk, border='RK_MSList_red', paintbackground=0, PaintBackgroundType=0)
        for key, val, _ in blk:
            if not isinstance(val, list):
                continue
            if key in ('Header', 'VoteCountLabel', 'ComboLabel'):
                kv.setmany(val, font='RK_Small', fgcolor='224 26 46 255', fgcolor_override='224 26 46 255', allcaps=1)
            elif key in ('Issue', 'PassedTitle', 'FailedTitle', 'TitleLabel'):
                kv.setmany(val, font='RK_FootText', fgcolor='236 232 232 255', fgcolor_override='236 232 232 255')
            elif key.startswith('LabelOption') or key in ('PassedResult', 'FailedReason'):
                kv.setmany(val, font='RK_Small', fgcolor='236 232 232 255', fgcolor_override='236 232 232 255')
            elif key.endswith('CountLabel'):
                kv.setmany(val, font='RK_FootText', fgcolor='236 232 232 255', fgcolor_override='236 232 232 255')
            elif key.endswith('Background_Selected'):
                kv.setmany(val, fillcolor='224 26 46 150', image=T + 'blank')
            elif key.startswith('Divider'):
                kv.setmany(val, fillcolor='224 26 46 120', image=T + 'blank')
            elif key in ('CallVoteButton', 'Button1'):
                screens.ink_button(val, font='RK_FootText', main=key == 'CallVoteButton')


# ------------------------------------------------------------------ Mann vs. Machine
# The MvM screens' stock pictures (the brown, tan, blue and black tournament panels, the green money box) and their
# grey panels take the HUD's glass, crimson and ink. Their places stay: the game lays most of these out from code.
MVM_GLASS = ('mvm_glass', 5, 20)          # 9-slice: corners drawn 5 units, 20 px of the 128 px art
MVM_BAR = ('mvm_fill', 3, 8)              # the wave's progress (32 x 128 px)
MVM_TRACK = ('mvm_track', 3, 8)
MVM_IMAGES = {T + 'panel_thin': MVM_GLASS, '../hud/tournament_panel_black': MVM_GLASS,
              '../hud/tournament_panel_brown': MVM_GLASS, '../hud/tournament_panel_blu': MVM_BAR,
              '../hud/tournament_panel_tan': MVM_TRACK}
CREDITS = (14, 71, 84, 18)                # the money chip in CurrencyStatusPanel: x, y, wide, tall (stock's box)
CREDITS_TAG = 20


def mvm_glass():
    """MvM's panels: black glass, the torn crimson frame, a crimson tab in the top left corner, a dot grid, the bottom
    right corner cut (9-slice: MVM_GLASS)."""
    p = _px(32, 32, 128)
    w, h = p.W, p.H
    shape = chamfer(0, 0, w, h, br=9)
    p.poly(shape, c(PANEL, 238))
    p.dots(4, 4, w - 4, h - 4, WHITE, 14, step=5)
    G.scan_in(p, shape, WHITE, 8)
    G.torn(p, chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=8.5), seed=21, a=160, gaps=0.12, seg=26, node=1.5)
    p.rect(0, 3, 2.5, 10, c(RED))
    return p.result()


def mvm_fill():
    """The wave's progress: crimson, a hot top edge, a deep foot, dark scan lines."""
    p = _px(48, 12, 128)
    w, h = p.W, p.H
    p.rect(0, 0, w, h, c(RED, 250))
    p.rect(0, 0, w, 2, c(HOT))
    p.rect(0, h - 3, w, h, c((122, 16, 30), 250))
    p.scan(0, 2, w, h - 3, INK, 60, step=3)
    return p.result()


def mvm_track():
    """Its track: ink with a crimson hairline."""
    p = _px(48, 12, 128)
    w, h = p.W, p.H
    p.rect(0, 0, w, h, c(INK, 236))
    p.outline([(0.5, 0.5), (w - 0.5, 0.5), (w - 0.5, h - 0.5), (0.5, h - 0.5)], c(RED, 150), 1)
    return p.result()


def mvm_credits():
    """The money: a black glass chip, the crimson 所持金 tag at its left end (the game writes the sum right of it), a
    hatch at the right end, the torn frame."""
    _, _, wu, hu = CREDITS
    p = _px(wu, hu, 512)
    w, h = p.W, p.H
    shape = chamfer(0, 0, w, h, br=8)
    p.poly(shape, c(PANEL, 244))
    G.scan_in(p, shape, WHITE, 10)
    tag = CREDITS_TAG * PX
    p.rect(0, 0, tag, h, c(RED, 250))
    p.text(tag / 2, h / 2, '所持金', ('jp7', 12), c((255, 255, 255)), 'mm')
    for i in range(3):
        x0 = w - 22 + i * 5
        p.line([(x0, h - 6), (x0 + 5, 6)], c(RED, 110), 1)
    G.torn(p, chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=7.5), seed=23, a=150, gaps=0.15, seg=40)
    return p.result()


def mvm_splash():
    """MISSION COMPLETE: a black band across the splash with crimson rules and their red and cyan copies, glitch
    tears, ■ 勝利 // VICTORY above it on the left, its ends fading (the game writes "Victory!" over the band)."""
    wu, hu = 250, 70
    p = _px(wu, hu, 1024)
    w = p.W
    y0, y1 = 16 * PX, 58 * PX
    p.rect(0, y0, w, y1, c(INK, 232))
    G.scan_in(p, [(0, y0), (w, y0), (w, y1), (0, y1)], RED, 18)
    for y in (y0, y1 - 2):
        for dx, col, a in ((-3, SPLIT_R, 120), (3, SPLIT_C, 90)):
            p.rect(30 + dx, y, w - 30 + dx, y + 2, c(col, a))
        p.rect(30, y, w - 30, y + 2, c(RED))
    G.tears(p, 60, y0 + 6, w - 60, y1 - 6, n=4, seed=31, alpha=120)
    p.rect(30, y0 - 18, 37, y0 - 11, c(RED))
    p.mixed(44, y0 - 14.5, [('勝利', ('jp5', 12), c(RED)), ('  //  ', ('mono', 11), c(RED, 150)),
                            ('VICTORY', ('mono', 12), c(RED))], 'lm')
    p.text(w - 30, y0 - 14.5, 'MISSION // 0x4D56', ('mono', 10), c(GREY, 200), 'rm')
    im = p.result()
    a = np.asarray(im, np.float32)
    xx = np.arange(a.shape[1], dtype=np.float32)
    fade = np.clip(np.minimum(xx, a.shape[1] - 1 - xx) / (a.shape[1] * 0.08), 0, 1)
    a[..., 3] *= fade[None, :]
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def _mvm_images(root):
    """MvM's scalable image panels -> the HUD's art with its own corners."""
    for ent in kv.walk(root):
        if not isinstance(ent[1], list):
            continue
        blk = ent[1]
        img = (kv.get(blk, 'image') or '').lower()
        if (kv.get(blk, 'ControlName') or '').lower() == 'scalableimagepanel' and img in MVM_IMAGES:
            name, draw, src = MVM_IMAGES[img]
            kv.setmany(blk, image=T + name, src_corner_width=src, src_corner_height=src, draw_corner_width=draw,
                       draw_corner_height=draw)


def _ink(val):
    """The stock's neutral greys (flat panels, tabs, rims; the scheme retint left them grey) -> the HUD's ink, darker
    the darker they were, so the stock's contrasts between a tab and its page stay."""
    m = re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+)\s*(\d+)?\s*', val or '')
    if not m:
        return None
    r, g, b = (int(x) for x in m.groups()[:3])
    a = m.group(4) or '255'
    if max(r, g, b) - min(r, g, b) > 8 or not 28 <= max(r, g, b) <= 140:
        return None
    v = 9 + (max(r, g, b) - 28) * 0.22
    return f'{round(v)} {round(v)} {round(v + 2)} {a}'


def _mvm_greys(root):
    for ent in kv.walk(root):
        if not isinstance(ent[1], list) and ent[0].lower() == 'bgcolor_override':
            nv = _ink(ent[1])
            if nv:
                ent[1] = nv
        elif not isinstance(ent[1], list) and ent[0].lower() == 'image' and ent[1].lower() == 'loadout_solid_line':
            ent[1] = T + 'notice_rule'


def mvm_generic(root):
    _mvm_images(root)
    _mvm_greys(root)


def mvm_currency(root):
    """The money (CurrencyStatusPanel, bottom left): the chip in place of the white-rimmed green box, the sum in white
    Rajdhani right of the 所持金 tag."""
    body = _body(root)
    for n in ('WhiteBG', 'GreenBG'):
        kv.setmany(kv.find(body, n), wide=0, tall=0, visible=0)
    x, y, w, h = CREDITS
    kv.add_block(body, 'RK_CreditsChip', {
        'ControlName': 'ImagePanel', 'fieldName': 'RK_CreditsChip', 'xpos': x, 'ypos': y, 'zpos': 1, 'wide': w,
        'tall': h, 'visible': 1, 'enabled': 1, 'scaleImage': 1, 'image': T + 'mvm_credits', 'mouseinputenabled': 0})
    lx = x + CREDITS_TAG
    kv.setmany(kv.find(body, 'Currency'), xpos=lx, wide=x + w - lx, font='RK_Credits', fgcolor='236 232 232 255')
    kv.setmany(kv.find(body, 'CurrencyShadow'), xpos=lx + 1, wide=x + w - lx, font='RK_Credits',
               fgcolor='224 26 46 170')


def mvm_world_currency(root):
    """Money still on the ground (under the money): green on ink in a crimson rim (the retint had turned the stock's
    gold box crimson under the green sum)."""
    body = _body(root)
    _set(body, 'BorderBG', bgcolor_override='224 26 46 255')
    _set(body, 'BackgroundGood', bgcolor_override='9 9 11 245')
    _set(body, 'CurrencyGood', fgcolor='112 214 92 255')
    _set(body, 'CurrencyBad', fgcolor='138 132 138 255')


def mvm_wave_complete(root):
    """Wave complete: the HUD's glass; the title on a deep crimson band (the stock's was brick red)."""
    mvm_generic(root)
    body = _body(root)
    _set(body, 'WaveCompleteLabelShadow', bgcolor_override='120 16 30 240')


def mvm_pve_win(root):
    """The robots won: the title on deep BLU (the robots' team)."""
    mvm_generic(root)
    body = _body(root)
    _set(body, 'WinningTeamLabelDropshadow', bgcolor_override='24 40 74 235')


def mvm_victory_splash(root):
    """"Victory!": on the MISSION COMPLETE band, its black shadow a crimson split copy."""
    body = _body(root)
    _set(body, 'SplashBackground', image=T + 'mvm_splash', src_corner_width=0, src_corner_height=0,
         draw_corner_width=0, draw_corner_height=0)
    _set(body, 'SplashLabelShadow', fgcolor='224 26 46 200')


def mvm_loss(root):
    """Wave lost: the HUD's glass, a crimson rule under the header."""
    mvm_generic(root)
    body = _body(root)
    _set(body, 'HeaderDivider', bgcolor_override='224 26 46 140')


RES = {
    'resource/ui/econ/notificationtoastcontrol.res': toast_control,
    'resource/ui/econ/notificationtoastcontainer.res': toast_container,
    'resource/ui/econ/genericnotificationtoast.res': lambda root: toast_body(root, IG_W),
    'resource/ui/econ/genericnotificationtoastmainmenu.res': lambda root: toast_body(root, MM_W),
    'resource/ui/econ/notificationspresentpanel.res': alerts_present,
    'resource/ui/hudmatchsummary.res': match_summary,
    'resource/ui/wavestatuspanel.res': mvm_generic,
    'resource/ui/hudcurrencyaccount.res': mvm_currency,
    'resource/ui/mvminworldcurrency.res': mvm_world_currency,
    'resource/ui/wavecompletesummarypanel.res': mvm_wave_complete,
    'resource/ui/hudpvewinpanel.res': mvm_pve_win,
    'resource/ui/mvmvictorysplash.res': mvm_victory_splash,
    'resource/ui/mvmwavelosspanel.res': mvm_loss,
    'resource/ui/mvmvictorypanel.res': mvm_generic,
    'resource/ui/mvmvictorymannuppanel.res': mvm_generic,
    'resource/ui/mvmvictorymannupentry.res': mvm_generic,
    'resource/ui/mvmvictorymannuptab.res': mvm_generic,
    'resource/ui/mvmscoreboard.res': mvm_generic,
    'resource/ui/hudupgradepanel.res': mvm_generic,
    'resource/ui/upgradebuypanel.res': mvm_generic,
    'resource/ui/tankstatuspanel.res': mvm_generic,
}


def ink_button_art(hover=False):
    """0.9: a button's frame (a 9-slice over the game's flat fill): a hot tab down the left, the hairline round it,
    the bottom right corner cut; hovered, the hairline hot and a white tab."""
    w, h, k = 128, 64, 2
    im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cut = 12
    pts = [(1, 1), (w - 1, 1), (w - 1, h - 1 - cut), (w - 1 - cut, h - 1), (1, h - 1)]
    d.line([(x * k, y * k) for x, y in pts + [pts[0]]], fill=(255, 52, 76, 255) if hover else (224, 26, 46, 170),
           width=2 * k if hover else k)
    d.rectangle([0, 0, 4 * k, h * k], fill=(236, 232, 232, 255) if hover else (255, 52, 76, 255))
    return im.resize((w, h), Image.LANCZOS)


def art(out):
    out.thumb('ink_btn', ink_button_art(), mips=False)
    out.thumb('ink_btn_h', ink_button_art(True), mips=False)
    crosshairs(out.root, out)
    damage_material(out.root)
    out.thumb('nt_toast', toast(), mips=False)
    out.thumb('nt_toast_hot', toast(hot=True), mips=False)
    out.thumb('nt_strip', alert_strip(), mips=False)
    for team in ('blue', 'red'):
        out.thumb(f'ms_bar_{team}', ms_bar(team), mips=False)
        out.thumb(f'ms_head_{team}', ms_head(team), mips=False)
        out.thumb(f'ms_seal_{team}', ms_seal(team))
        out.thumb(f'ms_list_{team}', ms_list(team), mips=False)
    out.thumb('mvm_glass', mvm_glass(), mips=False)
    out.thumb('mvm_fill', mvm_fill(), mips=False)
    out.thumb('mvm_track', mvm_track(), mips=False)
    out.thumb('mvm_credits', mvm_credits(), mips=False)
    out.thumb('mvm_splash', mvm_splash(), mips=False)
