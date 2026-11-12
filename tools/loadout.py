"""The class loadout page (the inventory's page of one class: its weapons, cosmetics, taunts and presets) in the
Beyond the Wall look, as an armoury terminal: a header where the other screens have theirs (■ 兵装 // ARSENAL, the
class's name large with a crimson ghost, the crimson rule), every item slot a black glass card with the torn crimson
frame (lit crimson under the pointer), the class's model in a biometric scan frame between the two columns, the four
presets as a chip strip over it and ITEMS / TAUNTS as a switch under it, the BLU / RED preview top right.

How the game builds the page (class_loadout_panel.cpp, base_loadout_panel.cpp, item_model_panel.cpp,
loadout_preset_panel.cpp in the game's code):
- the item slots are made by code from modelpanels_kv, two columns of four: column 0 at the centre +
  item_xpos_offcenter_a, column 1 at the centre + item_xpos_offcenter_b, row r at item_ypos + item_ydelta * r. Most
  classes fill rows 0-2 on the left (primary, secondary, melee), the Engineer and the Spy all four; the right column
  is head, cosmetic, cosmetic, action. In taunt mode the eight taunts take the same eight places.
- a slot's look is its border, set by code: EconItemBorder at rest, LoadoutItemMouseOverBorder under the pointer
  (or the item quality's backpack border when "show rarities" is on). Scalable image borders paint first, so the card
  is the slot's background: the game draws the item's icon (model_*) and its name (at 5, text_ypos, the card's width
  less 10, centred, in the item's quality colour) over it.
- the preset buttons are made by code from loadoutpresetpanel.res's presetbutton_kv, centred on the screen at
  y = item_ypos; the loaded one takes the Econ.Button.Preset* colours, the others the plain button colours, so a
  preset shows its state only by its colours (they are flat chips, no art can show through them). The ITEMS / TAUNTS
  page buttons are coloured the same way (UpdatePageButtonColor).
- the page sits in the inventory's property sheet: the sheet starts under the frame's title bar, its tabs take
  tabheight + yoffset (34) and the page starts under them, PAGE_Y units down the screen (measured in game in 0.3:
  the LOADOUT tab's top at 37, the class cards at 93 with class_ypos 40).
"""
import math
import os
import wave

import numpy as np
from PIL import Image

import kv
import menu  # (puts tools/style, the preview's drawing kit, on the path)
import ingame as G
import ui_kit  # noqa: E402
from build_art import THUMB, c, chamfer, linear_alpha
from screens import PAGE_Y  # the inventory pages' top on the screen, in units
from vtf import write_vtf
from ui_kit import F, rgba, PANEL, INK, RED, RED_DEEP, WHITE, GREY, SPLIT_R, SPLIT_C  # noqa: E402

T = 'replay/thumbnails/rk/'
PX = 2.25
HOT = (255, 52, 76)

# ------------------------------------------------------------------ geometry (units; x from the screen's centre)
CARD_W, CARD_H = 144, 72    # an item slot
COL_A, COL_B = -312, 168    # the columns' left edges: weapons (taunts 1-4) and cosmetics (taunts 5-8)
ROW_Y, ROW_DY = 58, 77      # rows at 58, 135, 212, 289: the last ends at 361, 414 on the screen (footer line: 424)
STRIP_H = 21                # the name strip at the card's foot: the game writes the item's name in it
TEXT_Y = CARD_H - STRIP_H + 3
# the item's icon: wide, tall, top (centred across; its foot runs 2 into the strip). An icon drawn from the item's 3D
# model (war paints, festive and decorated weapons, item_model_panel.cpp's render-target icons) is painted into one of
# the game's 256 x 256 px _rt_ItemModelPanel textures at the box's size in pixels: a box wider or taller than 256 px
# gets the whole texture stretched over it, the weapon blown up and the texture's unpainted part a black bar under
# it. 76 x 50 stays inside 256 px up to 1600 lines (stock's 82 x 55 up to 1440); a flat icon is fit to the height
ICON = (76, 50, 2)
CORNER_SRC, CORNER = 64, 9  # the card's 9-slice corners: 64 px of its 1024 x 512 texture, drawn 9 units
HEAD = (COL_A, 2, -150, 52)                    # the header (x0, y0, x1, y1)
TEAM_HEAD = (COL_B, 2, COL_B + CARD_W, 13)     # the preview switch's label
SCAN = (-150, 84, 150, 360)                    # the scan frame round the model
PRESET = (-150, 54, 150, 82)                   # the preset strip (the game puts the chips at y = ROW_Y)
PRESET_BTN = (22, 18)
FEET = 317                  # where the model's soles land (fov 30, 190 away, 48 down in a 340 tall panel at y 20)
TOGGLE = (50, 18, 336)      # ITEMS / TAUNTS: each button's width, height, top
HOLO = (-132, 86, 132, 334)                    # the hologram field over the model (dot screen, scan lines, beam)
SOCKET = (COL_A, ROW_Y + 3 * ROW_DY, COL_A + CARD_W, ROW_Y + 3 * ROW_DY + CARD_H)  # the left column's 4th place
NUM = (4, 26, 12, 10)       # a slot's number inside its card: x, y, wide, tall (clear of the icon, "+", quality icons)
CLASS_FONT = 'RK_LoadoutClass'
CLASS_W = 280               # the class's name: from the left column's edge to short of the centre
HOVER_W, HOVER_FRAMES, HOVER_FPS = 512, 12, 10  # the lit card is a flipbook: steady, then a short glitch, 1.2 s
# the inventory's item tiles (backpack, item picker, crafting, trading, and the loadout's slots with "show rarities"
# on): one 48 x 48 unit tile at 256 x 256, 6 unit corners, the rest stretched to any tile size
TILE_U, TILE_SRC, TILE_CORNER = 48, 32, 6
# the item tooltip (LoadoutItemPopupBorder): 300 x 150 units at 1024 x 512, corners 48 x 12 units (its header band
# and label in them); the game starts the item's name 15 or 20 units down, under the band
TIP_W, TIP_H, TIP_CW, TIP_CH = 300, 150, 48, 12
# the page's buttons sound like the wall: sound/ui/rk/, made by sounds() (button sound keys: paths under sound/)
SOUNDS = {'sound_armed': 'ui/rk/hover.wav', 'sound_depressed': 'ui/rk/press.wav', 'sound_released': 'ui/rk/release.wav'}

FONTS = {CLASS_FONT: G.font_block('Bahnschrift SemiBold Condensed', 26, 600)}
# the loaded preset and the page in view: crimson chips with white letters (stock: pale red with tan letters)
SCHEME_BASE = {
    'Econ.Button.PresetDefaultColorFg': '255 255 255 255', 'Econ.Button.PresetArmedColorFg': '255 255 255 255',
    'Econ.Button.PresetDepressedColorFg': '255 255 255 255', 'Econ.Button.PresetDefaultColorBg': '224 26 46 255',
    'Econ.Button.PresetArmedColorBg': '255 52 76 255', 'Econ.Button.PresetDepressedColorBg': '160 18 34 255',
}


def _border(image, src_w=CORNER_SRC, draw_w=CORNER, src_h=None, draw_h=None):
    return [['bordertype', 'scalable_image', None], ['backgroundtype', '2', None], ['image', T + image, None],
            ['src_corner_height', str(src_w if src_h is None else src_h), None], ['src_corner_width', str(src_w), None],
            ['draw_corner_width', str(draw_w), None], ['draw_corner_height', str(draw_w if draw_h is None else draw_h), None]]


# the game's own border names for a slot at rest and under the pointer (also the quest and blueprint item boxes'), and
# for the item tooltip (every inventory page's)
BORDERS = {'EconItemBorder': _border('ld_slot'),
           'LoadoutItemMouseOverBorder': _border('ld_slot_h', HOVER_W * CORNER // CARD_W),
           'LoadoutItemPopupBorder': _border('ld_tip', round(TIP_CW * 1024 / TIP_W), TIP_CW,
                                             round(TIP_CH * 1024 / TIP_W), TIP_CH)}


def tile_borders(borders):
    """The backpack tiles' borders (BackpackItem*: backpack_panel.cpp's g_szItemBorders, a set per item quality: at
    rest, under the pointer, selected, greyed out, greyed out and selected) -> the tile art. The game draws a
    quality's set only with "show rarities" on (cl_showbackpackrarities; the trading page always): those keep their
    colour, which the game multiplies the art by, so their white frame takes the quality's colour."""
    n = 0
    for name, body, _ in borders:
        low = name.lower()
        if not isinstance(body, list) or not low.startswith('backpackitem'):
            continue
        greyed = 'greyed' in low or 'grayed' in low
        coloured = kv.get(body, 'color') is not None
        if greyed:
            img = 'ld_tile_q_h' if 'selected' in low else 'ld_tile_q'
            if not coloured:
                kv.set(body, 'color', '9 9 11 255')  # (they all carry Black or a dark quality colour in stock)
        elif 'selected' in low:
            img = 'ld_tile_sel'
            kv.remove(body, 'color')
        elif 'mouseover' in low:
            img = 'ld_tile_q_h' if coloured else 'ld_tile_h'
        else:
            img = 'ld_tile_q' if coloured else 'ld_tile'
        kv.setmany(body, bordertype='scalable_image', backgroundtype=2, image=T + img, src_corner_width=TILE_SRC,
                   src_corner_height=TILE_SRC, draw_corner_width=TILE_CORNER, draw_corner_height=TILE_CORNER)
        n += 1
    return n


# ------------------------------------------------------------------ art
def X(u):
    """A page x (units from the centre) on the 1080p canvas."""
    return 960 + u * PX


def Y(u):
    """A page y (units from the page's top) on the 1080p canvas."""
    return PAGE_Y * PX + u * PX


def slot_card(hover=False, frame=0, width_px=1024):
    """An item slot, 144 x 72 units drawn at width_px x width_px / 2: black glass with faint scan lines, the name strip
    at its foot, the torn crimson frame with its red and cyan copies and a node on every corner, the bottom right
    corner cut, a crimson tab on the left edge. Under the pointer: a crimson wash, the frame lit hot and whole, white
    corner brackets, the tab the card's full height; frame: its flipbook frame (HOVER_FRAMES at HOVER_FPS), steady but
    for the last three, where the red and cyan copies slip, the wash flares, glitch tears run across and bands of the
    card slide sideways. The glass is opaque: the game blends in linear light, so even 97 % of dark glass let a third
    of the brightness of what lies under it through (the DIAGNOSTICS list under a 4th weapon's card)."""
    k = width_px / (CARD_W * PX)
    p = G.Px(CARD_W, CARD_H, k)
    w, h = p.W, p.H
    cut = 12
    shape = chamfer(0, 0, w, h, br=cut)
    strip_y = h - STRIP_H * PX
    glitch = frame - (HOVER_FRAMES - 3)          # 0, 1, 2 in the glitch; negative while steady
    slip = (1.6, -1.2, 2.4)[glitch] if glitch >= 0 else 0
    if hover:
        p.poly(shape, c((52, 10, 18) if glitch == 1 else (34, 8, 13)))
        G.scan_in(p, shape, RED, 26)
        p.poly(chamfer(0, strip_y, w, h, br=cut), c(RED_DEEP, 230))
        p.rect(0, strip_y, w, strip_y + 1, c(HOT, 200))
    else:
        p.poly(shape, c(PANEL))
        G.scan_in(p, shape, WHITE, 10)
        p.poly(chamfer(0, strip_y, w, h, br=cut), c(INK, 150))
        p.rect(0, strip_y, w, strip_y + 1, c(RED, 70))
    # a dot grid behind the icon, faint: the slot as a socket
    p.dots(10, 8, w - 10, strip_y - 6, WHITE if not hover else (255, 140, 150), 22 if not hover else 40, step=9)
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=cut - 0.5)
    if hover:
        for dx, col, a in ((-1.5 - slip, SPLIT_R, 150), (1.5 + slip, SPLIT_C, 120)):
            p.outline([(x + dx, y) for x, y in edge], c(col, a), 1)
        p.outline(edge, c(HOT), 1.5)
        for x, y in edge:
            p.rect(x - 2, y - 2, x + 2, y + 2, c(WHITE))
        arm = 10
        for (bx, by, sx, sy) in ((4, 4, 1, 1), (w - 4, 4, -1, 1), (4, h - 4, 1, -1)):
            p.line([(bx, by + sy * arm), (bx, by), (bx + sx * arm, by)], c(WHITE, 230), 1.2)
        p.rect(0, 0, 3, h, c(HOT))
        if glitch >= 0:
            G.tears(p, 8, 4, w - 8, strip_y - 4, n=3 + glitch, seed=7 + 13 * glitch, alpha=200)
            G.tears(p, 8, strip_y + 2, w - 8, h - 4, n=1, seed=29 + 5 * glitch, alpha=150)
    else:
        G.torn(p, edge, seed=5, a=150, gaps=0.2, seg=40)
        p.rect(0, 12, 2, h * 0.48, c(RED))
    # a barcode at the name strip's left end, a hatch at its right end by the cut corner
    bx = 7
    for i, bw in enumerate((1, 2, 1, 1, 3, 1, 2)):
        p.rect(bx, strip_y + 6, bx + bw, h - 6, c(WHITE if hover else GREY, 120 if hover else 70))
        bx += bw + 1.5
    for i in range(3):
        x0 = w - 34 + i * 5
        p.line([(x0, h - 5), (x0 + 5, strip_y + 5)], c(HOT if hover else RED, 170 if hover else 90), 1)
    im = p.result()
    from build_art import wall_over
    return wall_over(slip_bands(im, 41 + glitch, 6 * k) if hover and glitch in (0, 2) else im, 'right', 0.24)   # 0.9: the Wall in it


def slip_bands(im, seed, shift_px, n=2):
    """Glitch: n horizontal bands of the picture slid sideways by up to shift_px (texture px), wrapping round."""
    a = np.asarray(im).copy()
    H_, W_ = a.shape[:2]
    r = np.random.default_rng(seed)
    for _ in range(n):
        bh = max(2, int(r.uniform(0.05, 0.12) * H_))
        y = int(r.uniform(0.08, 0.85) * H_)
        dx = int(round(r.choice([-1, 1]) * r.uniform(0.5, 1.0) * shift_px))
        a[y:y + bh] = np.roll(a[y:y + bh], dx, axis=1)
    return Image.fromarray(a, 'RGBA')


def tile(state='rest', quality=False, frame=0):
    """A backpack tile in the slot cards' look (see TILE_U): black glass, faint scan lines and dots, the torn frame
    with a node on every corner, the bottom right corner cut, a tab on the left edge. hover: a wash, the frame lit
    whole, white corner brackets, the tab full height; selected: deep crimson, a white frame. quality: white where
    the crimson is and a grey wash, for the borders the game tints with the quality's colour (tile_borders); their
    red and cyan copies are left out (the tint would turn them orange and green). Opaque, as the slot cards; hover is
    a flipbook as theirs (frame: see slot_card): the game uses these for the loadout's slots too with "show rarities"
    on."""
    k = 256 / (TILE_U * PX)
    p = G.Px(TILE_U, TILE_U, k)
    w, h = p.W, p.H
    cut = 7
    shape = chamfer(0, 0, w, h, br=cut)
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=cut - 0.5)
    acc, hot = (WHITE, WHITE) if quality else (RED, HOT)
    glitch = frame - (HOVER_FRAMES - 3) if state == 'hover' else -1
    if state == 'selected':
        p.poly(shape, c(RED_DEEP))
        G.scan_in(p, shape, RED, 34)
        p.dots(6, 6, w - 6, h - 6, (255, 150, 160), 40, step=7)
        p.outline(edge, c(WHITE), 1.5)
        p.rect(0, 0, 2.5, h, c(HOT))
    elif state == 'hover':
        lit = glitch == 1
        p.poly(shape, c(((76, 76, 80) if lit else (54, 54, 58)) if quality else ((52, 10, 18) if lit else (34, 8, 13))))
        G.scan_in(p, shape, WHITE if quality else RED, 26)
        p.dots(6, 6, w - 6, h - 6, WHITE if quality else (255, 140, 150), 34, step=7)
        if not quality:
            slip = (1.4, -1.0, 2.0)[glitch] if glitch >= 0 else 0
            for dx, col, a in ((-1.2 - slip, SPLIT_R, 150), (1.2 + slip, SPLIT_C, 120)):
                p.outline([(x + dx, y) for x, y in edge], c(col, a), 1)
        p.outline(edge, c(hot), 1.5)
        p.rect(0, 0, 2.5, h, c(hot))
        if glitch >= 0:
            G.tears(p, 4, 4, w - 4, h - 4, n=2 + glitch, seed=17 + 11 * glitch, col=WHITE if quality else HOT,
                    alpha=220)
    else:
        p.poly(shape, c(PANEL))
        G.scan_in(p, shape, WHITE, 10)
        p.dots(6, 6, w - 6, h - 6, WHITE, 18, step=7)
        G.torn(p, edge, seed=3, col=acc, a=210 if quality else 150, split=not quality, gaps=0.2, seg=22, node=1.5)
        p.rect(0, 8, 1.5, h * 0.42, c(acc))
    if state != 'rest':
        for x, y in edge:
            p.rect(x - 1.5, y - 1.5, x + 1.5, y + 1.5, c(WHITE))
        arm = 6
        for (bx, by, sx, sy) in ((3, 3, 1, 1), (w - 3, 3, -1, 1), (3, h - 3, 1, -1)):
            p.line([(bx, by + sy * arm), (bx, by), (bx + sx * arm, by)], c(WHITE, 230), 1)
    im = p.result()
    return slip_bands(im, 53 + glitch, 4 * k) if glitch in (0, 2) else im


def tooltip():
    """The item tooltip: black glass under a deep crimson header band with ■ 情報 // DATA in its left corner and an
    address in its right one (both in the 9-slice's corners, so they keep their size), the torn frame, the bottom
    right corner cut, a crimson tab down the left edge."""
    k = 1024 / (TIP_W * PX)
    p = G.Px(TIP_W, TIP_H, k)
    w, h = p.W, p.H
    band = TIP_CH * PX
    cut = 14
    shape = chamfer(0, 0, w, h, br=cut)
    p.poly(shape, c(PANEL, 244))
    G.scan_in(p, shape, WHITE, 9)
    p.rect(0, 0, w, band - 1.5, c(RED_DEEP, 236))
    p.rect(0, band - 1.5, w, band - 0.5, c(HOT, 220))
    p.rect(9, band / 2 - 3, 15, band / 2 + 3, c(HOT))
    p.mixed(21, band / 2, [('情報', ('jp5', 11), c(WHITE)), (' // ', ('mono', 11), c((255, 140, 150))),
                           ('DATA', ('mono', 12), c(WHITE))], 'lm')
    p.text(w - 12, band / 2, '0x7F3A', ('mono', 10), c((255, 140, 150)), 'rm')
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=cut - 0.5)
    G.torn(p, edge, seed=9, a=170, gaps=0.15, seg=60)
    p.rect(0, band + 6, 2, band + 6 + (h - band) * 0.4, c(RED))
    return p.result()


def holo():
    """The hologram field over the class's model: a dot screen (dark between round windows) and dark scan lines,
    a few faint crimson interference lines, its edges fading out so the field has no border."""
    x0, y0, x1, y1 = HOLO
    wu, hu = x1 - x0, y1 - y0
    p = G.Px(wu, hu, 1024 / (wu * PX))
    w, h = p.W, p.H
    G.dot_screen(p, 0, 0, w, h, cell=3.0, alpha=92)
    p.scan(0, 0, w, h, INK, 70, step=3)
    for y in (0.17, 0.43, 0.71, 0.86):
        p.rect(0, h * y, w, h * y + 1, c(RED, 26))
    im = p.result()
    a = np.asarray(im, np.float32)
    H_, W_ = a.shape[:2]
    feather = 30 * im.width / w           # 30 px at 1080p
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    edge = np.minimum(np.minimum(xx, W_ - 1 - xx), np.minimum(yy, H_ - 1 - yy))
    a[..., 3] *= np.clip(edge / feather, 0, 1)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def beam(out):
    """The scan beam sweeping down the hologram field: one bright line with a soft glow and a fading trail above it,
    on a 64 x 512 texture that wraps (no clamping) and scrolls down 1 / BEAM_S of its height a second (the material's
    TextureScroll proxy), so the beam crosses the field every BEAM_S seconds. Its ends fade at the field's sides."""
    W_, H_ = 64, 512
    yy = np.arange(H_, dtype=np.float32)[:, None]
    xx = np.arange(W_, dtype=np.float32)[None, :]
    cy = 0.5 * H_
    d = yy - cy
    core = np.exp(-(d / 1.2) ** 2)
    glow = np.exp(-(d / 9.0) ** 2)
    trail = np.where(d < 0, np.exp(d / 70.0), 0) * (d > -200)
    a = np.clip(core * 0.7 + glow * 0.24 + trail * 0.09, 0, 1)
    ends = np.clip(np.minimum(xx, W_ - 1 - xx) / 12.0, 0, 1)
    a = a * ends
    rgb = np.zeros((H_, W_, 3), np.float32)
    hot, red = np.array(HOT, np.float32), np.array(RED, np.float32)
    mix = np.clip(core * 1.4, 0, 1)[..., None]
    rgb[:] = red * (1 - mix) + np.array((255, 190, 200), np.float32) * mix
    rgb = np.where((glow > 0.2)[..., None] & (mix < 0.5), hot, rgb)
    img = Image.fromarray(np.dstack([rgb, a[..., None] * 255]).clip(0, 255).astype(np.uint8), 'RGBA')
    name = 'ld_beam'
    p = os.path.join(out.root, THUMB, name)
    write_vtf(p + '.vtf', linear_alpha(img), alpha=True, mips=False, clamp=False)
    with open(p + '.vmt', 'w', encoding='utf-8') as f:
        f.write('"UnlitGeneric"\n{\n'
                f'\t"$basetexture"\t"vgui/replay/thumbnails/rk/{name}"\n'
                '\t"$translucent"\t"1"\n\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n'
                '\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n'
                '\t"Proxies"\n\t{\n\t\t"TextureScroll"\n\t\t{\n'
                '\t\t\t"texturescrollvar"\t"$basetexturetransform"\n'
                f'\t\t\t"texturescrollrate"\t"{1 / BEAM_S:.3f}"\n'
                '\t\t\t"texturescrollangle"\t"270"\n'
                '\t\t}\n\t}\n}\n')
    if out.preview:
        img.save(os.path.join(out.preview, name + '.png'))


BEAM_S = 4.0                # seconds the scan beam takes down the field


def slot_number(n):
    """A slot's number, 01-08, in the HUD's mono crimson over a short crimson rule."""
    p = G.Px(NUM[2], NUM[3], 128 / (NUM[2] * PX))
    w, h = p.W, p.H
    p.text(1, h / 2 - 1, '%02d' % n, ('mono', 13), c(RED, 235), 'lm')
    p.rect(1, h - 3, w * 0.62, h - 2, c(RED, 150))
    return p.result()


def socket():
    """The left column's 4th place when a class has no 4th weapon (all but the Engineer and the Spy; in taunt mode
    taunt 4's card covers it): an empty socket, a dashed outline, ■ 解析 // DIAGNOSTICS over the game's list of the
    loadout's passive attributes (PassiveAttribsLabel, see class_loadout)."""
    p = G.Px(CARD_W, CARD_H, 2.0)
    w, h = p.W, p.H
    p.poly(chamfer(2, 2, w - 2, h - 2, br=15), c(PANEL, 120))
    edge = chamfer(2.5, 2.5, w - 2.5, h - 2.5, br=14.5)  # inside the card's edge and cut: a card over it hides it all
    for (ax, ay), (bx, by) in zip(edge, edge[1:] + edge[:1]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / 10))
        for i in range(n):
            t0, t1 = i / n, (i + 0.55) / n
            p.line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)],
                   c(RED, 90), 1)
    x = (NUM[0] + NUM[2] + 2) * PX
    p.rect(x, 9, x + 6, 15, c(RED))
    p.mixed(x + 11, 12, [('解析', ('jp5', 10), c(RED)), ('  //  ', ('mono', 10), c(RED, 150)),
                         ('DIAGNOSTICS', ('mono', 11), c(RED))], 'lm')
    p.rect(x, 22, w - 14, 23, c(RED, 60))
    return p.result()


def header(cv):
    """■ 兵装 // ARSENAL over the class's name (the game's, see class_loadout), the crimson rule, the mono line (the
    sheet's LOADOUT tab is right above it, so the label does not say it again)."""
    x0, x1 = X(HEAD[0]), X(HEAD[2])
    ui_kit.label(cv, x0, Y(8), 'ARSENAL', '兵装')
    cv.rect(x0, Y(42), x0 + 34, Y(42) + 3, rgba(RED))
    cv.rect(x0 + 34, Y(42) + 1, x1, Y(42) + 2, rgba(RED, 140))
    cv.mixed(x0, Y(48), [('LOADOUT', F('mono', 11), rgba(GREY)), ('  //  ', F('mono', 11), rgba(RED, 150)),
                         ('装備', F('jp5', 10), rgba(GREY)), ('  //  ', F('mono', 11), rgba(RED, 150)),
                         ('SOUL HARVEST DIVISION', F('mono', 11), rgba(GREY))], 'lm')


def team_head(cv):
    ui_kit.label(cv, X(TEAM_HEAD[0]), Y(8), 'TEAM PREVIEW', '陣営')


def preset_strip(cv):
    """■ プリセット // PRESET left of the four chips (the game's buttons), brackets round them, the slot count right
    of them."""
    x0, y0, x1, y1 = PRESET
    cy = Y(ROW_Y + PRESET_BTN[1] / 2)
    parts = [('プリセット', F('jp5', 11), rgba(RED)), ('  //  ', F('mono', 11), rgba(RED, 150)),
             ('PRESET', F('mono', 12), rgba(RED))]
    wpart = sum(cv.width(t, f) for t, f, _ in parts)
    lx = X(-56) - wpart
    cv.rect(lx - 13, cy - 3.5, lx - 6, cy + 3.5, rgba(RED))
    cv.mixed(lx, cy, parts, 'lm')
    bx0, by0, bx1, by1 = X(-53), Y(ROW_Y - 3), X(53), Y(ROW_Y + PRESET_BTN[1] + 3)
    cv.brackets(bx0, by0, bx1, by1, 8, rgba(RED), 1.5)
    cv.mixed(X(57), cy, [('A-D', F('mono', 12), rgba(GREY)), ('  //  ', F('mono', 11), rgba(RED, 150)),
                         ('4 SLOTS', F('mono', 11), rgba(GREY))], 'lm')


def scan_frame(cv):
    """0.9 (preview 26): the model's frame as one of the page's cards: a full hairline box with the top right corner
    cut and hot, ■ 被験体 // SUBJECT in its corner, the Wall faint inside its right side, the brackets round ITEMS /
    TAUNTS at its foot. The old rulers, rings and readouts are gone."""
    x0, y0, x1, y1 = X(SCAN[0]), Y(SCAN[1]), X(SCAN[2]), Y(SCAN[3])
    cut = 22
    pts = [(x0, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1), (x0, y1)]
    cv.poly(pts, fill=rgba((9, 9, 11), 150), outline=rgba(RED, 170), width=1.5)
    cv.line([(x1 - cut, y0), (x1, y0 + cut)], rgba((255, 52, 76)), 3)
    cv.rect(x0, y0, x0 + 3, y0 + 60, rgba((255, 52, 76)))
    ui_kit.label(cv, x0 + 22, y0 + 14, 'SUBJECT', '被験体')
    tw, th, ty = TOGGLE
    sx0, sy0, sx1, sy1 = X(-tw - 4), Y(ty - 3), X(tw + 4), Y(ty + th + 3)
    cv.brackets(sx0, sy0, sx1, sy1, 7, rgba(RED), 1.5)


def art(out):
    out.thumb('ld_slot', slot_card(), mips=False)
    out.anim('ld_slot_h', [slot_card(hover=True, frame=i, width_px=HOVER_W) for i in range(HOVER_FRAMES)], HOVER_FPS)
    for name, draw, box in (('ld_head', header, HEAD), ('ld_team_head', team_head, TEAM_HEAD),
                            ('ld_preset', preset_strip, PRESET), ('ld_scan', scan_frame, SCAN)):
        x0, y0, x1, y1 = box
        im = menu.cut(menu.render(draw), (X(x0), Y(y0), X(x1), Y(y1)))
        if name == 'ld_scan':
            from build_art import wall_over
            im = wall_over(im, 'right', 0.22)  # only where the frame is solid: its lines
        out.thumb(name, im)
    for name, state, q in (('ld_tile', 'rest', False), ('ld_tile_sel', 'selected', False), ('ld_tile_q', 'rest', True)):
        out.thumb(name, tile(state, q), mips=False)
    for name, q in (('ld_tile_h', False), ('ld_tile_q_h', True)):
        out.anim(name, [tile('hover', q, i) for i in range(HOVER_FRAMES)], HOVER_FPS)
    out.thumb('ld_tip', tooltip(), mips=False)
    out.thumb('ld_holo', holo(), mips=False)
    out.thumb('ld_socket', socket(), mips=False)
    for n in range(1, 9):
        out.thumb(f'ld_num{n}', slot_number(n), mips=False)
    beam(out)


# ------------------------------------------------------------------ sounds
RATE = 44100


def _write_wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())


def _crush(x, bits=6, hold=3):
    """Bit-crush and sample-hold: the broken-signal grain."""
    y = np.repeat(x[::hold], hold)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(y * q) / q


def sounds(root):
    """The page's button sounds (SOUNDS), made here so the HUD ships no recordings: hover, a short falling blip,
    crushed; press, a noise tick then a stuttering low chirp; release, a quiet tick. 44.1 kHz mono 16-bit."""
    rng = np.random.default_rng(451)
    t = lambda s: np.arange(int(RATE * s)) / RATE

    tt = t(0.05)
    f = 2600 - 900 * tt / tt[-1]
    hover = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-tt / 0.014) * np.clip(tt / 0.002, 0, 1)
    hover = _crush(hover, 5, 3) * 0.22

    tn = t(0.006)
    tick = rng.uniform(-1, 1, len(tn)) * np.exp(-tn / 0.0015)
    tc = t(0.07)
    f = 900 - 380 * tc / tc[-1]
    chirp = np.sign(np.sin(2 * np.pi * np.cumsum(f) / RATE)) * np.exp(-tc / 0.02) * 0.5
    chirp = _crush(chirp, 4, 4)
    seg = chirp[int(RATE * 0.012):int(RATE * 0.018)]  # a 6 ms slice, stuttered twice
    press = np.concatenate([tick * 0.6, chirp[:int(RATE * 0.018)], seg, seg * 0.7, chirp[int(RATE * 0.018):]])
    press = press * 0.32

    tr = t(0.03)
    release = (rng.uniform(-1, 1, len(tr)) * 0.5 + np.sin(2 * np.pi * 1500 * tr)) * np.exp(-tr / 0.004)
    release = _crush(release, 6, 2) * 0.14

    for key, x in (('sound_armed', hover), ('sound_depressed', press), ('sound_released', release)):
        _write_wav(os.path.join(root, 'sound', SOUNDS[key]), x)


def with_sounds(blk):
    """A button's sound keys set to the page's own sounds."""
    kv.setmany(blk, **SOUNDS)


# ------------------------------------------------------------------ the page
def _blk(entries):
    return [[k, v if isinstance(v, list) else str(v), None] for k, v in entries.items()]


def put(body, name, entries, first=False):
    kv.remove(body, name)
    ent = [name, _blk(entries), None]
    if first:
        body.insert(1, ent)
    else:
        body.append(ent)


def art_panel(body, name, box, image, z=1):
    x0, y0, x1, y1 = box
    put(body, name, {'ControlName': 'ImagePanel', 'fieldName': name, 'xpos': f'c{x0}', 'ypos': y0, 'zpos': z,
                     'wide': x1 - x0, 'tall': y1 - y0, 'visible': 1, 'enabled': 1, 'scaleImage': 1, 'image': T + image,
                     'mouseinputenabled': 0})


def label(body, name, x, y, w, h, text, font, fg, align='west', z=3, **extra):
    e = {'ControlName': 'CExLabel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': 1, 'enabled': 1, 'labelText': text, 'textAlignment': align, 'font': font, 'fgcolor': fg,
         'mouseinputenabled': 0}
    e.update(extra)
    put(body, name, e)


def class_loadout(root):
    import screens
    screens.overlay_page('class_loadout_panel')(root)
    body = screens._root(root)
    panel = kv.find(body, 'class_loadout_panel')
    kv.setmany(panel, item_xpos_offcenter_a=COL_A, item_xpos_offcenter_b=COL_B, item_ypos=ROW_Y, item_ydelta=ROW_DY)
    iw, it, iy = ICON
    kv.setmany(kv.find(panel, 'modelpanels_kv'), wide=CARD_W, tall=CARD_H, model_center_x=1, model_ypos=iy,
               model_wide=iw, model_tall=it, text_ypos=TEXT_Y, text_center=1, name_only=1,
               noitem_textcolor='118 114 122 255')
    # the item options button ("+", on a slot whose item has styles or an effect): an ink chip, crimson under the pointer
    kv.setmany(kv.find(panel, 'itemoptionpanels_kv'), wide=13, tall=13, font='RK_Button', paintbackground=1,
               defaultBgColor_override='16 16 18 240', armedBgColor_override='224 26 46 255',
               depressedBgColor_override='255 52 76 255', defaultFgColor_override='224 26 46 255',
               armedFgColor_override='255 255 255 255', depressedFgColor_override='7 7 9 255')

    # the header: the art (label, rule, mono line) with the class's name in it, its crimson ghost a unit to the left
    art_panel(body, 'RK_LoadoutHead', HEAD, 'ld_head', z=1)
    for n in ('CaratLabel', 'TauntCaratLabel'):  # the stock ">>" marks
        kv.setmany(kv.find(body, n), xpos=OFF, wide=0, tall=0, labelText='')
    # wrap: vgui measures a label's room by its text as written and cuts it by the text in capitals, so "Spy" in
    # capitals came out as "S..."; a wrapping label is never cut (and these fit on one line)
    # (wider than the header art: a long localized name, SCHARFSCHÜTZE, runs on over the empty space before the
    # preset strip rather than onto a second line)
    name = dict(xpos=f'c{COL_A}', ypos=12, wide=CLASS_W, tall=28, font=CLASS_FONT, allcaps=1,
                textAlignment='west', zpos=3, wrap=1)
    kv.setmany(kv.find(body, 'ClassLabel'), fgcolor='236 232 232 255', **name)
    label(body, 'RK_ClassGhost', f'c{COL_A - 1}', 12, CLASS_W, 28, '#ClassBeingEquipped', CLASS_FONT,
          '224 26 46 150', allcaps=1, z=2, wrap=1)
    # taunt mode: a crimson tag on the label row (the code shows TauntLabel only then)
    kv.setmany(kv.find(body, 'TauntLabel'), xpos=f'c{COL_A + 66}', ypos=3, wide=42, tall=10, font='RK_Button',
               allcaps=1, wrap=1, textAlignment='center', fgcolor='7 7 9 255', bgcolor_override='224 26 46 255',
               PaintBackgroundType=0, paintbackground=1, zpos=3)
    kv.setmany(kv.find(body, 'TopLine'), xpos=OFF, wide=0, tall=0, image=T + 'blank')

    # the model in its scan frame, a hologram: the dot screen and scan lines over it, the beam sweeping down it (both
    # over the model's panel, z -1, and let the mouse through to it, so it still turns); the presets over it, the
    # page switch under it
    art_panel(body, 'RK_LoadoutScan', SCAN, 'ld_scan', z=-5)
    art_panel(body, 'RK_LoadoutHolo', HOLO, 'ld_holo', z=0)
    art_panel(body, 'RK_LoadoutBeam', HOLO, 'ld_beam', z=0)
    art_panel(body, 'RK_LoadoutPreset', PRESET, 'ld_preset', z=1)
    pw, ph = PRESET_BTN
    kv.setmany(kv.find(body, 'loadout_preset_panel'), wide=150, tall=ph)
    tw, th, ty = TOGGLE
    for n, x, text in (('CharacterLoadoutButton', -tw - 1, '#Store_Items'), ('TauntLoadoutButton', 1, '#TF_Taunt')):
        blk = kv.find(body, n)
        kv.setmany(blk, xpos=f'c{x}', ypos=ty, wide=tw, tall=th, labelText=text, font='RK_Button', allcaps=1,
                   textAlignment='west', textinsetx=18, use_proportional_insets=1, paintbackground=1,
                   PaintBackgroundType=0, zpos=6, image_drawcolor='236 232 232 255',
                   image_armedcolor='255 255 255 255', image_selectedcolor='255 255 255 255')
        kv.setmany(kv.find(blk, 'SubImage'), xpos=5, ypos=4, wide=10, tall=10)
    kv.setmany(kv.find(body, 'TauntHintLabel'), xpos=f'c{SCAN[0]}', ypos=SCAN[3] + 1, wide=SCAN[2] - SCAN[0], tall=9,
               font='RK_Small', textAlignment='center', centerwrap=0, fgcolor='138 132 138 255', zpos=3)
    for n in ('CharacterLoadoutButton', 'TauntLoadoutButton'):
        with_sounds(kv.find(body, n))
    with_sounds(kv.find(panel, 'itemoptionpanels_kv'))

    # the slots' numbers, 01-04 down the left column and 05-08 down the right (the game's order: in taunt mode its
    # taunts 1-8), inside each card left of its icon; over the cards (z 3), the mouse goes through
    # (pictures, not labels: the game reads a label's "01" as the number 1 and drops the 0)
    for i in range(8):
        x = (COL_A if i < 4 else COL_B) + NUM[0]
        y = ROW_Y + (i % 4) * ROW_DY + NUM[1]
        art_panel(body, f'RK_SlotNum{i}', (x, y, x + NUM[2], y + NUM[3]), f'ld_num{i + 1}', z=3)
    # the left column's 4th place, which only the Engineer and the Spy fill: an empty socket showing the game's list
    # of the loadout's passive attributes (PassiveAttribsLabel: stock keeps it hidden, the code fills it all the
    # same, each line in its attribute's colour). Both under the cards (z -4, -3): a 4th card, or taunt 4's in taunt
    # mode, covers them
    art_panel(body, 'RK_LoadoutSocket', SOCKET, 'ld_socket', z=-4)
    sx0, sy0 = SOCKET[0] + NUM[0] + NUM[2] + 2, SOCKET[1] + 13
    kv.setmany(kv.find(body, 'PassiveAttribsLabel'), visible=1, xpos=f'c{sx0}', ypos=sy0, wide=SOCKET[2] - sx0 - 4,
               tall=SOCKET[3] - sy0 - 3, font='RK_Small', textAlignment='north-west', wrap=1, centerwrap=0,
               fgcolor='138 132 138 255', zpos=-3)

    # the BLU / RED preview, top right over the right column (screens.TEAM_PREVIEW)
    art_panel(body, 'RK_LoadoutTeamHead', TEAM_HEAD, 'ld_team_head', z=1)
    for n in ('RK_TeamBlu', 'RK_TeamBluCard', 'RK_TeamRed', 'RK_TeamRedCard', 'RK_TeamPreviewNote'):
        kv.remove(body, n)
    for i, (n, img, text, command) in enumerate(screens.TEAM_PREVIEW):
        screens.tag_button(body, n, img, f'c{COL_B + i * 50}', 15, 46, 19, text, command)
        with_sounds(kv.find(body, n))
    label(body, 'RK_TeamPreviewNote', f'c{COL_B}', 37, CARD_W, 9, 'Works outside matches', 'RK_Small',
          '128 124 130 255', z=5)

    # the inventory's vertical tagline runs on over the page (the page hides the inventory's own below its top)
    put(body, 'RK_Tagline', {'ControlName': 'ImagePanel', 'fieldName': 'RK_Tagline', 'xpos': 'r20', 'ypos': 43 - PAGE_Y,
                             'zpos': -20, 'wide': 12, 'tall': 188, 'visible': 1, 'enabled': 1, 'scaleImage': 1,
                             'image': T + 'mm_tagline', 'mouseinputenabled': 0})

    # first-time popups (presets, taunts): the stock dark-on-tan text on the HUD's dark glass, light instead
    for pop in ('PresetsExplanation', 'TauntsExplanation'):
        blk = kv.find(body, pop)
        kv.setmany(kv.find(blk, 'TitleLabel'), fgcolor_override='236 232 232 255', font='RK_PanelTitle')
        kv.setmany(kv.find(blk, 'TextLabel'), fgcolor_override='200 196 198 255', font='RK_Menu')
        close = kv.find(blk, 'CloseButton')
        kv.setmany(close, image_drawcolor='200 196 198 255', image_armedcolor='224 26 46 255')
    # the popups' pointers: at the preset chips (stock: c0, 75) and at the TAUNTS switch (stock: c15, 330, the old
    # glyph button)
    kv.setmany(kv.find(body, 'PresetsExplanation'), callout_inparents_x='c0', callout_inparents_y=ROW_Y + ph // 2)
    kv.setmany(kv.find(body, 'TauntsExplanation'), callout_inparents_x=f'c{TOGGLE[0] // 2 + 1}',
               callout_inparents_y=TOGGLE[2] + TOGGLE[1] // 2)
    kv.set(kv.find(body, 'ItemOptionsPanel'), 'bgcolor_override', '12 12 14 245')


OFF = 9999


def preset_panel(root):
    """The four preset chips (A-D): the game sizes them from presetbutton_kv and colours them (see the module's
    note); flat, square, the HUD's button face."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    pw, ph = PRESET_BTN
    chips = kv.find(kv.find(body, 'loadout_preset_panel'), 'presetbutton_kv')
    kv.setmany(chips, wide=pw, tall=ph, font='RK_FootText', textAlignment='center', paintbackground=1,
               PaintBackgroundType=0)
    with_sounds(chips)
