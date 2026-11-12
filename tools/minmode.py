"""MINMODE (cl_hud_minmode 1): the HUD's second layout since 0.9, in place of the old CORNERS one.

The default layout (the cards either side of the crosshair) lives in the plain keys; this one only in *_minmode keys,
written by the passes below after every other patch of a file (kv.set clears a key's _minmode twin, so nothing may
set those keys after them). The look is the competitive HUDs' minimal one: no cards, no portrait; the health and the
ammo as bare numbers well out either side of the crosshair, a quarter of the screen down (flawhud's spot), on a
faint ink plate that fades away from the crosshair, the plain number (no gauge column, no MAX line), the item meters under the ammo, the ÜberCharge card between the two.

Units are the HUD's 480-line ones; 'cN' is N from the screen's centre."""
import numpy as np
from PIL import Image

import kv

MM_Y = 318                      # the plates' top (742 px at 1080 lines)
PLATE = (138, 44)               # a plate's box
H_X = -270                      # the health plate's left edge from the centre (it ends 132 in from the crosshair)
A_X = 133                       # the ammo panel's left edge from the centre
GAUGE_X = -130                  # the health gauge, on the health plate's inner end
NUM_T = 32                      # the numbers' label height
METER_Y = MM_Y + PLATE[1] + 4   # the first item meter row, under the ammo plate (more rows go down from it)
STREAK_Y = MM_Y + PLATE[1] + 4  # the kill streak row under the health plate

FONTS = {}


def fonts(font_block):
    FONTS.update({
        'RK_MMNum': font_block('Rajdhani', 30, 700),
        'RK_MMSplit': font_block('Rajdhani', 30, 700, additive=1),
        'RK_MMRes': font_block('Rajdhani SemiBold', 11, 600),
    })
    return FONTS


def c(v):
    return 'c%d' % v


# ------------------------------------------------------------------ art
def plate(side, label, jp):
    """The ink plate under a number: darkest at the end by the crosshair, fading out to the outer one; its label in
    small mono and katakana by the inner end, a rule along its foot with a hot stub at the inner end. side: 'l' for
    the health (its inner end is the right one), 'r' for the ammo. In the team's colour (a team picture)."""
    import ingame as G
    p = G.Px(*PLATE)
    w, h = p.W, p.H
    ramp = np.linspace(0, 1, int(p.t.im.width)) if side == 'l' else np.linspace(1, 0, int(p.t.im.width))
    a = (np.clip(ramp, 0, 1) ** 1.3 * 190).astype(np.uint8)
    shade = Image.new('RGBA', p.t.im.size, (7, 7, 9, 0))
    shade.putalpha(Image.fromarray(np.tile(a, (p.t.im.height, 1))))
    p.t.im.alpha_composite(shade)
    if side == 'l':
        p.text(w - 14, 10, label, ('mono', 12), G.c(G.RED), 'rm')
        p.text(w - 14 - 30, 10, jp, ('jp5', 11), G.c(G.GREY), 'rm')
        p.rect(0, h - 5, w, h - 3, G.c(G.RED, 150))
        p.rect(w - 60, h - 7, w, h - 1, G.c(G.HOT))
    else:
        p.text(14, 10, label, ('mono', 12), G.c(G.RED), 'lm')
        p.text(14 + 38, 10, jp, ('jp5', 11), G.c(G.GREY), 'lm')
        p.rect(0, h - 5, w, h - 3, G.c(G.RED, 150))
        p.rect(0, h - 7, 60, h - 1, G.c(G.HOT))
        p.rect(0, 4, 4, h - 10, G.c(G.HOT))
    return p.result()


def art(out):
    out.thumb('mm_plate_h', plate('l', 'HP', '完全性'), team=True)
    out.thumb('mm_plate_a', plate('r', 'RDS', '弾薬'), team=True)


# ------------------------------------------------------------------ helpers
def mm(blk, **keys):
    """Set *_minmode keys (kv.set: one value each)."""
    for k, v in keys.items():
        kv.set(blk, k + '_minmode', v)


def hide(blk):
    """Gone in minmode: no size (animations move some of these, none sizes them)."""
    mm(blk, wide=0, tall=0)


def only_mm(body, name, entries, box):
    """A panel of minmode alone: no size in the default layout, its box in minmode."""
    x, y, w, h = box
    entries = dict(entries, fieldName=name, xpos=x, ypos=y, wide=0, tall=0)
    blk = kv.add_block(body, name, entries)
    mm(blk, wide=w, tall=h)
    return blk


def _children(body):
    return [(k, v) for k, v, *_ in body if isinstance(v, list)]


# ------------------------------------------------------------------ files
HEALTH_HIDE = ('PlayerStatusHealthBonusImage', 'RK_HealthFlash', 'RK_HealthTears', 'RK_HealthDanger', 'RK_HealthGlow',
               'RK_HealthGhost', 'RK_HealthHot', 'RK_DigitsAdd', 'RK_DigitsMul', 'RK_MaxSlash', 'RK_HealthKickR',
               'RK_HealthKickC', 'RK_BWGateCard')
STATUS_ICONS = ('PlayerStatusBleedImage', 'PlayerStatusHookBleedImage', 'PlayerStatusMilkImage', 'PlayerStatusGasImage',
                'PlayerStatusSlowed')


def health(root):
    import ingame as G
    body = kv.find(root, 'Resource/UI/HudPlayerHealth.res')
    for name in HEALTH_HIDE:
        blk = kv.find(body, name)
        if blk is not None:
            hide(blk)
    # the number, right-aligned to the plate's inner end; its cyan copy a unit to the right
    nx = H_X + PLATE[0] - 6 - 70
    for name, dx, font in (('PlayerStatusHealthValue', 0, 'RK_MMNum'), ('RK_HealthSplit', 1, 'RK_MMSplit')):
        blk = kv.find(body, name)
        if blk is not None:
            mm(blk, xpos=c(nx + dx), ypos=MM_Y + 7, wide=70, tall=NUM_T, font=font, textAlignment='east')
    # MAX 200 at the plate's outer end: "MAX" is a label of its own, the number the game's own max label beside it
    # with its text untouched (a label's text set in a _minmode key is shown raw: the game fills %MaxHealth% only in
    # the plain key, the same trap as the sticky count's %activepipes%)
    blk = kv.find(body, 'PlayerStatusMaxHealthValue')
    if blk is not None:
        mm(blk, xpos=c(H_X + 26), ypos=MM_Y + 3, wide=40, tall=10, font='RK_StripLabel', textAlignment='west')
    only_mm(body, 'RK_MMMax', G.lbl('RK_MMMax', 0, 0, 0, 0, 'MAX', 'RK_StripLabel', '138 132 138 255'),
            (c(H_X + 4), MM_Y + 3, 22, 10))
    # no gauge column (the user's call): the number alone
    for name in ('PlayerStatusHealthImage', 'PlayerStatusHealthImageBG', 'RK_HealthMul', 'RK_GaugeSide_l',
                 'RK_GaugeSide_r'):
        blk = kv.find(body, name)
        if blk is not None:
            hide(blk)
    # the status icons (bleed, jarate, buffs, runes...) in a row over the plate's outer end
    for name, blk in _children(body):
        if name in STATUS_ICONS or name.startswith(('PlayerStatus_', 'PlayerStatusMarked')):
            mm(blk, xpos=c(H_X), ypos=MM_Y - 20, wide=18, tall=18)
    only_mm(body, 'RK_MMPlateH', G.timg('RK_MMPlateH', 0, 0, 0, 0, 'mm_plate_h', z=1),
            (c(H_X), MM_Y, PLATE[0], PLATE[1]))


def player_class(root):
    body = next(e[1] for e in root if isinstance(e[1], list))
    for name in ('RK_HealthCard', 'RK_PhotoBG', 'RK_PhotoFx', 'classmodelpanel', 'PlayerStatusClassImage'):
        blk = kv.find(body, name)
        if blk is not None:
            hide(blk)
    # the spy's disguise: small, left of the health plate
    for name in ('PlayerStatusSpyImage', 'PlayerStatusSpyOutlineImage'):
        blk = kv.find(body, name)
        if blk is not None:
            mm(blk, xpos=c(H_X - 26), ypos=MM_Y + 14, wide=22, tall=22)


def ammo(root):
    import ingame as G
    body = kv.find(root, 'Resource/UI/HudAmmoWeapons.res')
    for name in ('HudWeaponAmmoBG', 'RK_AmmoFlash', 'RK_AmmoTears', 'RK_AmmoAdd', 'RK_AmmoMul'):
        blk = kv.find(body, name)
        if blk is not None:
            hide(blk)
    # the clip right-aligned so "/ 20" can follow at a fixed place; a clipless weapon's number from the plate's start
    for name, x, w, font, align in (('AmmoInClip', 4, 48, 'RK_MMNum', 'east'), ('AmmoInClipShadow', 5, 48, 'RK_MMSplit', 'east'),
                                    ('AmmoNoClip', 8, 90, 'RK_MMNum', 'west'), ('AmmoNoClipShadow', 9, 90, 'RK_MMSplit', 'west')):
        blk = kv.find(body, name)
        if blk is not None:
            mm(blk, xpos=x, ypos=7, wide=w, tall=NUM_T, font=font, textAlignment=align)
    blk = kv.find(body, 'AmmoInReserve')
    if blk is not None:
        mm(blk, xpos=58, ypos=22, wide=70, tall=12, font='RK_MMRes', textAlignment='west')
    # "/": the reserve's shadow carries the slash picture as its border and hides with the reserve; here at a fixed
    # small size (not sized to its text) right before the reserve. (labelText in a _minmode key would show raw)
    blk = kv.find(body, 'AmmoInReserveShadow')
    if blk is not None:
        mm(blk, xpos=52, ypos=23, wide=5, tall=10, font='RK_MMRes', auto_wide_tocontents=0)
    only_mm(body, 'RK_MMPlateA', G.timg('RK_MMPlateA', 0, 0, 0, 0, 'mm_plate_a', z=1), (0, 0, PLATE[0], PLATE[1]))


def killstreak(root):
    body = next(e[1] for e in root if isinstance(e[1], list))
    blk = kv.find(body, 'HudItemEffectMeter')
    if blk is not None:  # the 撃破 STREAK row under the health plate
        mm(blk, xpos=c(H_X + 4), ypos=STREAK_Y)


def layout(root):
    """hudlayout.res: the ammo panel's place; the meters, metal, stickies and Über follow ingame.strip_box /
    center_box / CENTER (their alt boxes are this layout's)."""
    import ingame as G
    body = next(e[1] for e in root if isinstance(e[1], list))
    blk = kv.find(body, 'HudWeaponAmmo')
    if blk is not None:
        mm(blk, xpos=c(A_X), ypos=MM_Y, wide=G.AMMO[2], tall=G.AMMO[3])
    blk = kv.find(body, 'HudVoiceSelfStatus')
    if blk is not None:
        mm(blk, xpos=c(H_X - 30), ypos=MM_Y - 26)
