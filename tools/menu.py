"""Main menu of the Reaper HUD, laid out element for element from docs/style-menu.jpg.

The art is cut straight out of the style preview's own drawing (tools/style/preview_menu.py and ui_kit.py): each
piece is drawn by the preview's code at its own place on a 1080p canvas, once over black and once over white, and the
two renders give the piece's exact colours and transparency. The boxes are the preview's pixel boxes turned into HUD
units (2.25 px per unit at 1080p). What the game draws itself (the rank medal, avatars, names, the XP fill, the menu
scene behind) goes into the boxes and fonts the preview gives it.
"""
import os
import sys

import numpy as np
from PIL import Image

import kv

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'style'))
import ui_kit  # noqa: E402  (the preview's drawing kit)
import preview_menu as PM  # noqa: E402
from ui_kit import (F, rgba, panel, tears, INK, PANEL, RED, RED_DIM, RED_DEEP, WHITE, GREY, GREY_D, SPLIT_R,  # noqa
                    SPLIT_C)

PX = 2.25
T = 'replay/thumbnails/rk/'
HOT = (255, 52, 76)
TEXT = '236 232 232 255'
TEXT_RGB = (236, 232, 232)
HOT_RGB = (255, 52, 76)
VERSION = open(os.path.join(os.path.dirname(HERE), 'VERSION'), encoding='utf-8').read().strip()


def u(px):
    return int(round(px / PX))


# ------------------------------------------------------------------ geometry (preview px)
VIDEO = False  # build.py sets it when video/menu_video.json and its textures are there: the main menu's background
VIDEO_PARTS = 0  # textures the video is split over (build.py menu_video); with 3 the class picture panel plays one
VIDEO_SHADED = False  # the video's frames carry the main menu's shade (tools/video.py --shade)
TOP_H = 47                                # the top bar: 46 px of ink and its crimson hairline
FIND = (1590, 1866)                       # FIND A GAME, right edge 54 px in
POWER = (1866, 1920)
PARTY_X, PARTY_STEP, PARTY_S = 58, 36, 30
LOGO_BOX = (56, 66, 621, 191)
PROFILE_BOX = (60, 200, 600, 298)
NAV_X0, NAV_X1, NAV_Y, NAV_H, NAV_STEP = 60, 560, 326, 44, 51
NAV_ART_W = 567 - 60 + 60                 # the button art runs past the button for the armed one's pixel dust
NAV_LABELS = [('ITEMS', 'アイテム'), ('SHOP', 'ショップ'), ('OPTIONS', '設定'), ('ADVANCED OPTIONS', '詳細設定'),
              ('MY ACHIEVEMENTS', '実績'), ('WORKSHOP', 'ワークショップ'), ('REPLAYS', 'リプレイ'), ('HUD SETTINGS', 'HUD設定')]
NAV_BUTTONS = ('CharacterSetupButton', 'GeneralStoreButton', 'SettingsButton', 'TF2SettingsButton',
               'AchievementsButton', 'WorkshopButton', 'ReplayButton')  # RK_HudSettingsButton is the 8th
FRIENDS_BOX = (1384, 596, 1864, 900)
CHIP_Y, CHIP_X, CHIP_STEP, CHIP_S = 996, 60, 50, 42
FOOTER = 59                               # units: the footer band (the matchmaking dimmer's 59 units from the bottom)
TAGLINE_BOX = (1876, 96, 1904, 520)
BRACKETS = {'tl': (15, 61, 35, 81), 'tr': (1885, 61, 1905, 81), 'bl': (15, 1045, 35, 1065), 'br': (1885, 1045, 1905, 1065)}


# ------------------------------------------------------------------ cutting art out of the preview
def render(draw):
    """The preview's drawing over black and over white (2 x 1080p, the preview's own supersampling)."""
    out = []
    for bg in (0, 255):
        cv = ui_kit.Canvas(Image.new('RGB', (1920, 1080), (bg, bg, bg)))
        draw(cv)
        out.append(np.asarray(cv.im, np.float32))
    return out


def cut(renders, box):
    """RGBA of a box: alpha from how much the two renders differ, colour from the one over black."""
    b, w = renders
    k = ui_kit.K
    x0, y0, x1, y1 = (int(round(v * k)) for v in box)
    B, Wt = b[y0:y1, x0:x1], w[y0:y1, x0:x1]
    a = np.clip(1 - (Wt - B) / 255, 0, 1).max(-1, keepdims=True)
    col = np.where(a > 1e-3, B / np.maximum(a, 1e-3), 0)
    return Image.fromarray(np.clip(np.concatenate([col, a * 255], -1), 0, 255).astype(np.uint8), 'RGBA')


def buttons_all(cv, armed):
    """preview_menu.buttons with every button in one state (the armed one sheds its pixel dust off its cut corner)."""
    x0, x1, y, h, gap = NAV_X0, NAV_X1, NAV_Y, NAV_H, NAV_STEP - NAV_H
    for i, (en, jp) in enumerate(NAV_LABELS):
        y0, y1 = y + i * (h + gap), y + i * (h + gap) + h
        cy = (y0 + y1) / 2
        if armed:
            cv.chamfer(x0 - 2, y0, x1 - 2, y1, fill=rgba(SPLIT_R, 90), br=12)      # its chromatic split
            cv.chamfer(x0 + 2, y0, x1 + 2, y1, fill=rgba(SPLIT_C, 70), br=12)
            cv.chamfer(x0, y0, x1, y1, fill=rgba(RED), br=12)
            tears(cv, x1 - 150, y0 + 3, x1 - 16, y0 + 12, n=3, seed=20 + i, col=WHITE, alpha=150)
            r = np.random.default_rng(4)
            for _ in range(26):
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


def find_game(cv, armed=False):
    x0, x1 = FIND
    cv.chamfer(x0, 0, x1, 46, fill=rgba(HOT if armed else RED), bl=14)
    cv.hatch(x0 + 14, 0, x0 + 46, 46, RED_DIM, 255, step=6, width=2)
    cv.text(x0 + 58, 23, 'FIND A GAME', F('raj7', 23), rgba((255, 255, 255), 90), 'lm', spacing=1)   # a white tear
    cv.text(x0 + 60, 23, 'FIND A GAME', F('raj7', 23), rgba(INK), 'lm', spacing=1)
    tears(cv, x0 + 56, 6, x1 - 44, 40, n=2, seed=33, col=WHITE, alpha=110)
    for k in range(2):
        xx = x1 - 30 + k * 9
        cv.poly([(xx, 15), (xx + 7, 23), (xx, 31), (xx - 3, 31), (xx + 4, 23), (xx - 3, 15)], fill=rgba(INK))


def power_block(cv, armed=False):
    cv.rect(POWER[0] + 2, 0, 1920, 46, rgba(RED_DEEP if armed else (20, 18, 22)))


def party_slot(cv, x):
    cv.d.rectangle([x * ui_kit.K, 8 * ui_kit.K, (x + 30) * ui_kit.K - 1, 38 * ui_kit.K - 1], outline=rgba(GREY_D, 255),
                   width=ui_kit.K)


def chip_art(cv, x0, armed):
    if armed:
        cv.chamfer(x0, CHIP_Y, x0 + CHIP_S, CHIP_Y + CHIP_S, fill=rgba(RED), tr=9)
    else:
        cv.chamfer(x0, CHIP_Y, x0 + CHIP_S, CHIP_Y + CHIP_S, fill=rgba(PANEL, 210), tr=9)
        cv.chamfer(x0, CHIP_Y, x0 + CHIP_S, CHIP_Y + CHIP_S, outline=rgba(RED, 110), width=1, tr=9)


def icon_music(cv, cx, cy, r, col):
    """A speaker sending out sound: the chip that turns the music off and on."""
    cv.rect(cx - r, cy - r * 0.36, cx - r * 0.45, cy + r * 0.36, col)
    cv.poly([(cx - r * 0.45, cy - r * 0.36), (cx + r * 0.12, cy - r), (cx + r * 0.12, cy + r),
             (cx - r * 0.45, cy + r * 0.36)], fill=col)
    x0, k = cx + r * 0.12, ui_kit.K
    for rr in (r * 0.45, r * 0.85):
        cv.d.arc([(x0 - rr) * k, (cy - rr) * k, (x0 + rr) * k, (cy + rr) * k], start=-50, end=50, fill=col,
                 width=2 * k)


GLYPHS = (('list', PM.icon_list), ('plus', PM.icon_plus), ('play', PM.icon_play), ('gear', PM.icon_gear),
          ('music', icon_music))


def glyphs(cv):
    """The chip icons in white, each on its own chip's place (the game tints them: white, ink when armed)."""
    col = rgba((255, 255, 255))
    for i, (_, fn) in enumerate(GLYPHS):
        x0 = CHIP_X + i * CHIP_STEP
        if fn is PM.icon_list:
            fn(cv, x0 + 11, CHIP_Y + 12, 20, col)
        elif fn is PM.icon_gear:
            fn(cv, x0 + 21, CHIP_Y + 21, 7, col)
        elif fn is icon_music:  # a touch bigger, as wide as the list and the gear; the speaker and its waves are
            fn(cv, x0 + 21, CHIP_Y + 21, 9, col)  # as wide either side of its centre, so it sits in the chip's middle
        else:
            fn(cv, x0 + 21, CHIP_Y + 21, 8, col)


def friends_art(cv):
    x0, y0, x1, y1 = FRIENDS_BOX
    panel(cv, x0, y0, x1, y1, tab_h=40, cut='tl')
    # game: TF2 does not give the menu the number of friends online, so the preview's "7 ONLINE" says ONLINE only
    cv.text(1494, 617, 'ONLINE', F('mono', 11), rgba(GREY), 'lm')
    cv.hatch(1720, 612, 1790, 621, RED_DIM, 255, step=5, width=1.5)
    cv.text(1846, 616, 'シグナル', F('jp5', 12), rgba(RED), 'rm')
    cv.line([(x0 + 1, 636), (x1 - 1, 636)], rgba(RED, 70), 1)


def avatar_frame(cv):
    cv.d.rectangle([1400 * ui_kit.K, 652 * ui_kit.K, (1400 + 38) * ui_kit.K - 1, (652 + 38) * ui_kit.K - 1],
                   outline=rgba(RED, 90), width=ui_kit.K)


XP_TRACK = '12 235 56 255'   # the XP bar's empty part: dark grey under mm_xp_mul (patch_rank)


def xp_mul(k=4):
    """Modulate-2x sheet over the XP bar (preview: seg_bar 162..584 x 266..273), which the game paints (100, 255, 100)
    (patch_rank): 2 x (255, 13, 59) x that green = the crimson (200, 26, 46); black at the gaps of its 34 segments.
    The bar's track under it (XP_TRACK) comes out a neutral dark grey."""
    n, gap, x0, x1 = 34, 2, 162, 584
    W, H = round((x1 - x0) * k), round((273 - 266) * k)
    a = np.zeros((H, W, 4), np.uint8)
    a[..., :3] = (255, 13, 59)
    a[..., 3] = 255
    w = (x1 - x0 - gap * (n - 1)) / n
    for i in range(n - 1):
        xa = (i + 1) * w + i * gap
        a[:, round(xa * k):round((xa + gap) * k), :3] = 0
    return Image.fromarray(a, 'RGBA')


def art(out):
    """Every main menu texture (rk/mm_*)."""
    top = render(lambda cv: (cv.rect(0, 0, 1920, 46, rgba(INK, 236)), cv.rect(0, 46, 1920, 47, rgba(RED, 150))))
    out.thumb('mm_topbar', cut(top, (100, 0, 164, TOP_H)), mips=False)
    r = render(lambda cv: (find_game(cv), PM.icon_chat(cv, 16, 12, 24, rgba((255, 255, 255))),
                           [party_slot(cv, PARTY_X + i * PARTY_STEP) for i in range(1)],
                           PM.icon_plus(cv, PARTY_X + PARTY_STEP + 15, 23, 4, rgba(GREY_D))))
    # a terminal cursor blinking after the credit line (on, off; 2 frames a second). It is also the test of whether
    # the game runs animated textures on the main menu, the way an animated background would have to
    on = Image.new('RGBA', (8, 16), (0, 0, 0, 0))
    on.paste(Image.new('RGBA', (8, 13), RED + (255,)), (0, 2))
    out.anim('mm_cursor', [on, Image.new('RGBA', (8, 16), (0, 0, 0, 0))], 2)
    # over the menu video: the shade's darkness from left to right (the buttons' side darker)
    alpha = np.interp(np.linspace(0, 1, 256), [0, 0.32, 0.6, 1], [0.62, 0.52, 0.25, 0.10])
    shade = np.zeros((4, 256, 4), np.uint8)
    shade[..., :3] = INK
    shade[..., 3] = np.rint(alpha * 255).astype(np.uint8)
    out.thumb('mm_video_shade', Image.fromarray(shade, 'RGBA'), mips=False)
    # over the video behind the centred menus (class and team select): darker overall, most at the bottom. When the
    # video's frames carry the main menu's shade (VIDEO_SHADED) this only adds what that shade leaves, so the left
    # is not darker than the rest (only where the shade alone is darker than this, there)
    alpha = np.interp(np.linspace(0, 1, 256), [0, 0.5, 1], [0.40, 0.48, 0.72])[:, None]
    if VIDEO_SHADED:
        left = np.interp(np.linspace(0, 1, 256), [0, 0.32, 0.6, 1], [0.62, 0.52, 0.25, 0.10])[None, :]
        alpha = np.clip(1 - (1 - alpha) / (1 - left), 0, 1)
    dim = np.zeros((256, 256 if VIDEO_SHADED else 4, 4), np.uint8)
    dim[..., :3] = INK
    dim[..., 3] = np.rint(np.broadcast_to(alpha, dim.shape[:2]) * 255).astype(np.uint8)
    out.thumb('mm_video_dim', Image.fromarray(dim, 'RGBA'), mips=False)
    out.thumb('mm_findgame', cut(r, (FIND[0], 0, FIND[1], TOP_H)))
    out.thumb('mm_g_chat', cut(r, (14, 10, 42, 40)))
    # the power block is a plain block: Quit puts its icon on it as its own image, and Disconnect / Resume (wider,
    # with text) take the same block
    out.thumb('mm_power', cut(render(power_block), (POWER[0], 0, POWER[1], TOP_H)))
    out.thumb('mm_g_power', cut(render(lambda cv: PM.icon_power(cv, 1894, 24, 9, rgba((255, 255, 255)))),
                                (1882, 12, 1906, 36)))
    out.thumb('mm_party', cut(r, (PARTY_X, 8, PARTY_X + 30, 38)))
    out.thumb('mm_party_plus', cut(r, (PARTY_X + PARTY_STEP + 8, 16, PARTY_X + PARTY_STEP + 22, 30)))
    r = render(lambda cv: (find_game(cv, True), power_block(cv, True)))
    out.thumb('mm_findgame_h', cut(r, (FIND[0], 0, FIND[1], TOP_H)))
    out.thumb('mm_power_h', cut(r, (POWER[0], 0, POWER[1], TOP_H)))
    r = render(lambda cv: (PM.logo(cv), PM.tagline(cv), PM.frame(cv), panel(cv, *PROFILE_BOX, tab_h=40),
                           friends_art(cv), avatar_frame(cv)))
    out.thumb('mm_logo', cut(r, LOGO_BOX))
    out.thumb('mm_tagline', cut(r, TAGLINE_BOX))
    for k, box in BRACKETS.items():
        out.thumb('mm_bracket_' + k, cut(r, box), mips=False)
    out.thumb('mm_profile', cut(r, PROFILE_BOX))
    out.thumb('mm_friends', cut(r, FRIENDS_BOX))
    out.thumb('mm_avatar_frame', cut(r, (1400, 652, 1438, 690)), mips=False)
    out.thumb('mm_xp_mul', xp_mul(), mips=False)
    with open(os.path.join(out.root, 'materials/vgui/replay/thumbnails/rk/mm_xp_mul.vmt'), 'w',
              encoding='utf-8') as f:
        f.write('"Modulate"\n{\n\t"$basetexture"\t"vgui/replay/thumbnails/rk/mm_xp_mul"\n\t"$mod2x"\t"1"\n'
                '\t"$ignorez"\t"1"\n}\n')
    fy = 1080 - FOOTER * PX
    foot = render(lambda cv: (cv.rect(0, fy, 1920, 1080, rgba(INK, 236)), cv.rect(0, fy, 1920, fy + 1, rgba(RED, 150))))
    out.thumb('mm_footer', cut(foot, (100, fy, 164, 1080)), mips=False)
    for armed in (False, True):
        r = render(lambda cv: buttons_all(cv, armed))
        for i in range(len(NAV_LABELS)):
            y0 = NAV_Y + i * NAV_STEP
            out.thumb(f'mm_nav{i}' + ('_h' if armed else ''), cut(r, (NAV_X0, y0, NAV_X0 + NAV_ART_W, y0 + 45)))
    for armed in (False, True):
        r = render(lambda cv: chip_art(cv, CHIP_X, armed))
        out.thumb('mm_chip' + ('_h' if armed else ''), cut(r, (CHIP_X, CHIP_Y, CHIP_X + CHIP_S, CHIP_Y + CHIP_S)))
    r = render(glyphs)
    for i, (name, _) in enumerate(GLYPHS):
        x0 = CHIP_X + i * CHIP_STEP
        out.thumb('mm_g_' + name, cut(r, (x0 + 8, CHIP_Y + 8, x0 + 34, CHIP_Y + 34)))


# ------------------------------------------------------------------ scheme
FONTS = {
    'RK_ProfileName': [['1', [['name', 'Bahnschrift SemiCondensed', None], ['tall', '13', None], ['weight', '600', None],
                              ['antialias', '1', None]], None]],
    'RK_ProfileDesc': [['1', [['name', 'Rajdhani', None], ['tall', '9', None], ['weight', '700', None],
                              ['antialias', '1', None]], None]],
    'RK_ProfileDesc2': [['1', [['name', 'Rajdhani SemiBold', None], ['tall', '9', None], ['weight', '600', None],
                               ['antialias', '1', None]], None]],
    'RK_Mono12': [['1', [['name', 'Share Tech Mono', None], ['tall', '6', None], ['weight', '400', None],
                         ['antialias', '1', None]], None]],
    'RK_FriendsTitle': [['1', [['name', 'Rajdhani', None], ['tall', '12', None], ['weight', '700', None],
                               ['antialias', '1', None]], None]],
    'RK_FriendName': [['1', [['name', 'Bahnschrift SemiCondensed', None], ['tall', '10', None], ['weight', '600', None],
                             ['antialias', '1', None]], None]],
    'RK_FriendStatus': [['1', [['name', 'Bahnschrift SemiCondensed', None], ['tall', '8', None],
                               ['weight', '400', None], ['antialias', '1', None]], None]],
}


def _border(image):
    return [['bordertype', 'scalable_image', None], ['backgroundtype', '2', None], ['image', T + image, None],
            ['src_corner_height', '0', None], ['src_corner_width', '0', None], ['draw_corner_width', '0', None],
            ['draw_corner_height', '0', None]]


BORDERS = {name: _border(img) for name, img in (
    ('RK_TopBar', 'mm_topbar'), ('RK_FindGame', 'mm_findgame'), ('RK_FindGame_h', 'mm_findgame_h'),
    ('RK_PowerBlock', 'mm_power'), ('RK_PowerBlock_h', 'mm_power_h'), ('RK_MMProfile', 'mm_profile'),
    ('RK_MMFriends', 'mm_friends'), ('RK_MMChip', 'mm_chip'), ('RK_MMChip_h', 'mm_chip_h'),
    ('RK_PartySlot', 'mm_party'))}
for _i in range(len(NAV_LABELS)):
    BORDERS[f'RK_MMNav{_i}'] = _border(f'mm_nav{_i}')
    BORDERS[f'RK_MMNav{_i}_h'] = _border(f'mm_nav{_i}_h')


# ------------------------------------------------------------------ .res helpers
def _block(entries):
    return [[k, v if isinstance(v, list) else str(v), None] for k, v in entries.items()]


def put(body, name, entries):
    kv.remove(body, name)
    body.append([name, _block(entries), None])
    return body[-1][1]


def image(name, box_px, img, z=0, **extra):
    x0, y0, x1, y1 = box_px
    e = {'ControlName': 'ImagePanel', 'fieldName': name, 'xpos': u(x0), 'ypos': u(y0), 'zpos': z,
         'wide': u(x1) - u(x0), 'tall': u(y1) - u(y0), 'visible': 1, 'enabled': 1, 'scaleImage': 1,
         'image': T + img, 'mouseinputenabled': 0}
    e.update(extra)
    return e


def right(x_px):
    """An x near the right edge, from the right (any screen width)."""
    return 'r%d' % u(1920 - x_px)


def bottom(y_px):
    return 'r%d' % u(1080 - y_px)


# ------------------------------------------------------------------ main menu
def mainmenu(root, hud_settings_popup):
    body = kv.find(root, 'Resource/UI/MainMenuOverride.res')
    # the scene fills the height at every aspect ratio, right-aligned (the holiday and aspect variants go)
    bg = kv.find(body, 'Background')
    bg[:] = [e for e in bg if not (isinstance(e[1], list) and e[0].lower().startswith(
        ('if_halloween', 'if_fullmoon', 'if_christmas', 'if_wider', 'if_taller')))]
    kv.setmany(bg, visible=1, image='../console/background_reaper_widescreen', xpos='rs1', wide='o1.778', tall='f0',
               zpos=-200)
    kv.remove(body, 'RK_Video')
    kv.remove(body, 'RK_VideoShade')
    kv.remove(body, 'RK_MenuVideo')
    character = kv.find(body, 'TFCharacterImage')
    if VIDEO:
        # the looping video (build.py, menu_video) is the scene itself: the stock Background, a plain ImagePanel the
        # game makes itself, which plays the animated material like any other and which the game hides while you are
        # in a game, so the ESC menu over a match shows the match (a panel of our own covered it). The shade over it,
        # darker behind the buttons on the left, is the class picture's panel, which the game hides in a game too:
        # its picture comes from scripts/characterbackgrounds.txt, which build.py writes naming the shade (the res
        # names it as well, for the holidays, when the game picks no picture from that file)
        kv.set(bg, 'image', T + 'mm_video')
        character[:] = [e for e in character if not isinstance(e[1], list)]
        if VIDEO_SHADED or VIDEO_PARTS == 3:
            # the shade is in the frames (tools/video.py --shade), so the class picture shows nothing
            kv.setmany(character, xpos=0, ypos=0, zpos=-199, wide=0, tall=0, visible=0, enabled=1, scaleImage=1,
                       image=T + 'blank', mouseinputenabled=0)
        else:
            kv.setmany(character, xpos=0, ypos=0, zpos=-199, wide='f0', tall='f0', visible=1, enabled=1,
                       scaleImage=1, image=T + 'mm_video_shade', mouseinputenabled=0)
        if VIDEO_PARTS == 3:
            # a video in three parts: the Background plays the first two (build.py, menu_video) and RK_MenuVideo the
            # third over it, laid out like the Background. RK_MenuVideo is listed in resource/gamemenu.res as shown
            # only at the menu (build.py, game_menu), so the game hides it in a game as it hides the Background. (The
            # class picture's panel is hidden in a game too, but during Halloween, October 1 to November 8, also at
            # the menu for two of its six backgrounds, picked at random.) The current video is one texture
            # (tools/video.py): the third part froze in the game
            put(body, 'RK_MenuVideo', {
                'ControlName': 'EditablePanel', 'fieldName': 'RK_MenuVideo', 'xpos': 0, 'ypos': 0, 'zpos': -199,
                'wide': 'f0', 'tall': 'f0', 'visible': 1, 'enabled': 1, 'mouseinputenabled': 0,
                'paintbackground': 0, 'paintborder': 0,
                'Video': _block({'ControlName': 'ImagePanel', 'fieldName': 'Video', 'xpos': 'rs1', 'ypos': 0,
                                 'zpos': 0, 'wide': 'o1.778', 'tall': 'f0', 'visible': 1, 'enabled': 1,
                                 'scaleImage': 1, 'image': T + 'mm_video_c', 'mouseinputenabled': 0,
                                 'proportionaltoparent': 1})})
    else:
        kv.setmany(character, visible=0, wide=0, tall=0)
    # the footer: the matchmaking panels' dimmer stops FOOTER units above the screen's bottom (the stock footer's top,
    # set in code), so the menu's foot is a band as dark as the dimmer, the chips and the version line on it
    put(body, 'RK_Footer', {'ControlName': 'ImagePanel', 'fieldName': 'RK_Footer', 'xpos': 0, 'ypos': 'r%d' % FOOTER,
                            'zpos': -150, 'wide': 'f0', 'tall': FOOTER, 'visible': 1, 'enabled': 1, 'scaleImage': 1,
                            'image': T + 'mm_footer', 'mouseinputenabled': 0})
    logo = kv.find(body, 'TFLogoImage')
    logo[:] = [e for e in logo if not isinstance(e[1], list)]
    x0, y0, x1, y1 = LOGO_BOX
    kv.setmany(logo, xpos=u(x0), ypos=u(y0), wide=u(x1) - u(x0), tall=u(y1) - u(y0), image=T + 'mm_logo')
    kv.remove(body, 'RK_Tagline')
    tx0, ty0, tx1, ty1 = TAGLINE_BOX
    put(body, 'RK_Tagline', image('RK_Tagline', TAGLINE_BOX, 'mm_tagline', z=-50, xpos=right(tx0)))
    for k, (bx0, by0, bx1, by1) in BRACKETS.items():
        e = image('RK_Bracket_' + k, (bx0, by0, bx1, by1), 'mm_bracket_' + k, z=-50)
        if k[1] == 'r':
            e['xpos'] = right(bx0)
        if k[0] == 'b':
            e['ypos'] = bottom(by0)
        put(body, 'RK_Bracket_' + k, e)

    # the profile card, (60, 200)-(600, 298): the game's rank panel draws the medal, name, rank lines and XP bar in it
    px0, py0, px1, py1 = PROFILE_BOX
    kv.setmany(kv.find(body, 'RankBorder'), xpos=u(px0), ypos=u(py0), wide=u(px1) - u(px0), tall=u(py1) - u(py0),
               border='RK_MMProfile', paintborder=1)
    # the medal (a 3D model, centred in its panel at 12 % of the panel's height): centred on the preview's hexagon,
    # (109, 249) px, about 70 px across
    m = 600
    kv.setmany(kv.find(body, 'RankModelPanel'), xpos=u(109) - m // 2, ypos=u(249) - m // 2, wide=m, tall=m)
    # the rank panel's text block sits RANK_BG_X into it: its left edge lands on the card's
    kv.setmany(kv.find(body, 'RankPanel'), xpos=u(px0) - RANK_BG_X, ypos=u(py0), wide=RANK_BG_X + RANK_BG_W, tall=44)
    kv.setmany(kv.find(body, 'CycleRankTypeButton'), xpos=u(578 - 9), ypos=u(220 - 9), wide=u(18), tall=u(18))
    kv.setmany(kv.find(body, 'RankTooltipPanel'), xpos=u(px0) + 2, ypos=u(py0) + 2)
    kv.setmany(kv.find(body, 'NoGCMessage'), xpos=u(px0), ypos=u(py0), wide=u(px1) - u(px0), tall=u(py1) - u(py0))
    kv.setmany(kv.find(body, 'NoGCImage'), xpos=u(px0) + 8, ypos=u(py0) + 8)

    # the eight buttons, (60, 326 + 51 i)-(560, 370 + 51 i); the art runs 60 px past the button's cut corner for
    # the armed one's pixel dust, so the button is that much wider (its text is baked in: the button has none)
    for i, name in enumerate(NAV_BUTTONS):
        blk = kv.find(body, name)
        if blk is not None:
            nav_button(blk, i)
    blk = _block({'ControlName': 'CExImageButton', 'fieldName': 'RK_HudSettingsButton', 'autoResize': 0, 'visible': 1,
                  'enabled': 1, 'tabPosition': 0, 'labelText': '', 'dulltext': 0, 'brighttext': 0, 'default': 1,
                  'Command': 'motd_show', 'sound_depressed': 'UI/buttonclick.wav',
                  'sound_released': 'UI/buttonclickrelease.wav'})
    kv.remove(body, 'RK_HudSettingsButton')
    body.append(['RK_HudSettingsButton', blk, None])
    nav_button(blk, len(NAV_BUTTONS))
    kv.setmany(kv.find(body, 'StoreHasNewItemsImage'), xpos=u(NAV_X1) - 14, ypos=u(NAV_Y + NAV_STEP) + 3, wide=10,
               tall=10, zpos=7)
    for name in ('CommentaryButton', 'CoachPlayersButton', 'NewUserForumsButton', 'ReportBugButton', 'VRBGPanel',
                 'VRModeButton', 'EventPromo', 'SettingsButtonSDK', 'TF2SettingsButtonSDK', 'MOTD_ShowButtonPanel'):
        blk = kv.find(body, name)
        if blk is not None:
            kv.set(blk, 'xpos', 9999)

    # the icon chips at the foot, (60 + 50 i, 996), 42 px: server browser, create server, SourceTV, contracts; the
    # notifications one (shown only while there are any) after them
    chips = [('RK_ServerBrowserButton', 'mm_g_list'), ('RK_CreateServerButton', 'mm_g_plus'),
             ('WatchStreamButton', 'mm_g_play'), ('QuestLogButton', 'mm_g_gear'),
             ('RK_MusicButton', 'mm_g_music'), ('Notifications_ShowButtonPanel', 'glyph_alert')]
    for i, (name, glyph) in enumerate(chips):
        x = u(CHIP_X + i * CHIP_STEP)
        if name.startswith('RK_'):
            cmd, tip = CHIP_COMMANDS[name]
            icon_button(body, name, x, glyph, cmd, tip)
            continue
        blk = kv.find(body, name)
        if blk is None:
            continue
        kv.setmany(blk, xpos=x, ypos=u(CHIP_Y), wide=u(CHIP_S), tall=u(CHIP_S))
        sub = 'Notifications_ShowButtonPanel_SB' if name.startswith('Notifications') else 'SubButton'
        btn = kv.find(blk, sub)
        if btn is None:
            continue
        kv.setmany(btn, xpos=0, ypos=0, wide=u(CHIP_S), tall=u(CHIP_S), paintbackground=0,
                   image_drawcolor='236 232 232 220', image_armedcolor='7 7 9 255')
        chip(btn)
        img = kv.find(btn, 'SubImage')
        if img is not None:
            kv.setmany(img, xpos='cs-0.5', ypos='cs-0.5', wide=u(26), tall=u(26),
                       image=(T + glyph) if glyph.startswith('mm_') else glyph, proportionaltoparent=1)
    # the unread badge (the game's red glyph and the count over it) in the chip's top right corner, inside it: the
    # stock badge, 16 units for the stock 32-unit button, lay half outside the chip and was cut off there
    badge = 10
    note = kv.find(body, 'Notifications_ShowButtonPanel')
    for n in ('SubImage', 'Notifications_CountLabel'):
        kv.setmany(kv.find(note, n), xpos=u(CHIP_S) - badge, ypos=0, wide=badge, tall=badge)
    kv.set(kv.find(note, 'Notifications_CountLabel'), 'font', 'RK_CardCount')
    # in game: report, vote, mute and coach are a second row of the same chips, right above the first (stock paints
    # them as tan rounded buttons); the game picks each one's icon
    for i, name in enumerate(('ReportPlayerButton', 'CallVoteButton', 'MutePlayersButton', 'RequestCoachButton')):
        blk = kv.find(body, name)
        if blk is None:
            continue
        kv.setmany(blk, xpos=u(CHIP_X + i * CHIP_STEP), ypos=u(CHIP_Y - CHIP_STEP), wide=u(CHIP_S), tall=u(CHIP_S))
        btn = kv.find(blk, 'SubButton')
        if btn is None:
            continue
        kv.remove(btn, 'RoundedCorners')
        kv.setmany(btn, xpos=0, ypos=0, wide=u(CHIP_S), tall=u(CHIP_S), paintbackground=0, textinsetx=0,
                   image_drawcolor='236 232 232 220', image_armedcolor='7 7 9 255', labelText='')
        chip(btn)
        img = kv.find(btn, 'SubImage')
        if img is not None:
            kv.setmany(img, xpos='cs-0.5', ypos='cs-0.5', wide=u(26), tall=u(26), proportionaltoparent=1)
    kv.setmany(kv.find(body, 'BackToReplaysButton'), xpos=u(CHIP_X), ypos=u(CHIP_Y) - 60)
    friends(kv.find(body, 'FriendsContainer'))
    hud_settings_popup(kv.find(body, 'MOTD_Panel'))
    title = kv.find(kv.find(body, 'Notifications_Panel') or [], 'Notifications_TitleLabel')
    if title is not None:  # stock draws it dark for the tan bubble; the panel is black glass now
        kv.set(title, 'fgcolor', TEXT)
    # right of the menu column (it covered REPLAYS and HUD SETTINGS at the column's foot), its foot over the chips
    kv.setmany(kv.find(body, 'Notifications_Panel'), xpos=u(640), ypos=u(CHIP_Y) - 150)
    for n in ('BackgroundFooter', 'FooterLine'):
        kv.setmany(kv.find(body, n), visible=0, wide=0, tall=0)
    # credit, bottom right: its right edge 1864 px across, centred on y 1050
    put(body, 'RK_Credit', {'ControlName': 'CExLabel', 'fieldName': 'RK_Credit', 'xpos': 'r%d' % (u(1920 - 1864) + 400),
                            'ypos': bottom(1050 - 7), 'zpos': 1, 'wide': 400, 'tall': 6, 'visible': 1, 'enabled': 1,
                            'mouseinputenabled': 0, 'textinsetx': 0,
                            'labelText': f'THE REAPER HUD  v{VERSION}  //  made by Ingalther',
                            'textAlignment': 'east', 'font': 'RK_Mono12', 'fgcolor': '138 132 138 190'})
    put(body, 'RK_Cursor', image('RK_Cursor', (1866, 1050 - 7, 1873, 1050 + 7), 'mm_cursor', z=1,
                                 xpos='r%d' % u(1920 - 1866)))


CHIP_COMMANDS = {
    # straight to the community server browser and the create-server window (stock hides both behind Find a Game);
    # the hover text is the game's own name for each, from the Find a Game list
    'RK_ServerBrowserButton': ('OpenServerBrowser', '#MMenu_PlayList_ServerBrowser_Button'),
    'RK_CreateServerButton': ('OpenCreateMultiplayerGameDialog', '#MMenu_PlayList_CreateServer_Button'),
    # music off and on: the music volume goes from whatever it is to 0, and from 0 to full (1). The track plays on
    # silently and comes back where it is; while off, the game's other music stays off too
    'RK_MusicButton': ('engine incrementvar snd_musicvolume 0 1 1', 'Music on / off'),
}


def nav_button(blk, i):
    x0, y0 = NAV_X0, NAV_Y + i * NAV_STEP
    kv.setmany(blk, xpos=u(x0), ypos=u(y0), zpos=5, wide=u(x0 + NAV_ART_W) - u(x0), tall=u(y0 + 45) - u(y0), visible=1,
               labelText='', paintbackground=0, paintborder=1, border_default=f'RK_MMNav{i}',
               border_armed=f'RK_MMNav{i}_h', border_depressed=f'RK_MMNav{i}_h', border_selected=f'RK_MMNav{i}_h',
               pinCorner=0, textinsetx=0)
    sub = kv.find(blk, 'SubImage')
    if sub is not None:
        kv.setmany(sub, visible=0, wide=0, tall=0)


def chip(btn):
    """The chip behind a foot-row icon is the button's own border: it shows and hides with the button."""
    kv.setmany(btn, paintborder=1, border_default='RK_MMChip', border_armed='RK_MMChip_h',
               border_depressed='RK_MMChip_h', border_selected='RK_MMChip_h')


def icon_button(body, name, x, glyph, command, tip):
    s = u(CHIP_S)
    blk = _block({
        'ControlName': 'CExImageButton', 'fieldName': name, 'xpos': x, 'ypos': u(CHIP_Y), 'zpos': 1, 'wide': s,
        'tall': s, 'autoResize': 0, 'pinCorner': 0, 'visible': 1, 'enabled': 1, 'tabPosition': 0, 'labelText': '',
        'Command': command, 'tooltiptext': tip, 'paintbackground': 0,
        'image_drawcolor': '236 232 232 220', 'image_armedcolor': '7 7 9 255',
        'sound_depressed': 'UI/buttonclick.wav', 'sound_released': 'UI/buttonclickrelease.wav'})
    blk.append(['SubImage', _block({
        'ControlName': 'ImagePanel', 'fieldName': 'SubImage', 'xpos': 'cs-0.5', 'ypos': 'cs-0.5', 'zpos': 1,
        'wide': u(26), 'tall': u(26), 'visible': 1, 'enabled': 1, 'scaleImage': 1, 'image': T + glyph,
        'proportionaltoparent': 1, 'mouseinputenabled': 0, 'keyboardinputenabled': 0}), None])
    chip(blk)
    kv.remove(body, name)
    body.append([name, blk, None])


def friends(blk):
    """(1384, 596)-(1864, 900): the panel art carries the header line; the game's title (FRIENDS) and its list of
    two columns, (1400 + 234 i, 652 + 58 j): a 38 px avatar, the name and the status beside it."""
    x0, y0, x1, y1 = FRIENDS_BOX
    kv.setmany(blk, xpos=right(x0), ypos=u(y0), wide=u(x1) - u(x0), tall=u(y1) - u(y0), border='RK_MMFriends',
               paintborder=1)
    kv.setmany(kv.find(blk, 'TitleLabel'), xpos=u(18), ypos=u(20) - 6, wide=100, tall=12, font='RK_FriendsTitle',
               fgcolor_override=TEXT, allcaps=1, textinsetx=0)
    lst = kv.find(blk, 'SteamFriendsList')
    if lst is not None:
        kv.setmany(lst, xpos=0, ypos=u(56), wide=u(x1) - u(x0), tall=u(y1) - u(y0) - u(56) - 2, columns_count=2,
                   inset_x=u(16), inset_y=0, row_gap=u(58 - 38), column_gap=u(234) - FRIEND_W, restrict_width=0)
        pk = kv.find(lst, 'friendpanel_kv')
        if pk is not None:
            kv.setmany(pk, wide=FRIEND_W, tall=u(38))
    blk[:] = [e for e in blk if not (isinstance(e[1], list) and e[0] in ('Background', 'InnerShadow', 'BelowDarken'))]


FRIEND_W = 100


def patch_friend(root):
    """One friend (steamfriendpanel.res): the 38 px avatar in a crimson hairline, name and status beside it."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    a = u(38)
    kv.setmany(kv.find(body, 'avatar'), xpos=0, ypos=0, wide=a, tall=a)
    kv.add_block(body, 'RK_AvatarFrame', {'ControlName': 'ImagePanel', 'fieldName': 'RK_AvatarFrame', 'xpos': 0,
                                          'ypos': 0, 'zpos': 5, 'wide': a, 'tall': a, 'visible': 1, 'enabled': 1,
                                          'scaleImage': 1, 'image': T + 'mm_avatar_frame', 'mouseinputenabled': 0})
    kv.setmany(kv.find(body, 'NameLabel'), xpos=u(50), ypos=1, wide=FRIEND_W - u(50), tall=10, font='RK_FriendName',
               fgcolor_override=TEXT)
    kv.setmany(kv.find(body, 'StatusLabel'), xpos=u(50), ypos=u(25) - 1, wide=FRIEND_W - u(50), tall=8,
               font='RK_FriendStatus')


# the rank panel's text block (pvprankpanel.res BGPanel), inside the profile card: x from the card's left edge
RANK_BG_X, RANK_BG_W = 60, u(600 - 60)


def patch_rank(root):
    """Profile card text (pvprankpanel.res): name (162, 214) in 25 px, the rank lines (162, 252) in 16 px, the
    34-segment XP bar (162..584, 266..273) and the XP numbers under it (286). Positions are from the card's top left."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    bgp = kv.find(body, 'BGPanel')
    if bgp is None:
        return
    kv.setmany(bgp, xpos='rs1', ypos=0, wide=RANK_BG_W, tall=44)
    ox, oy = u(60), u(200)   # the card's top left, in px units
    tx = u(162) - ox
    kv.setmany(kv.find(bgp, 'NameLabel'), xpos=tx, ypos=u(215.6) - oy, wide=RANK_BG_W - tx - 14, tall=13,
               font='RK_ProfileName', fgcolor_override=TEXT, textAlignment='north-west')
    # the rank's two lines share the preview's row: CASUAL in crimson on the left, LEVEL / TIER in grey ending where
    # the XP bar ends
    bar_w = u(584) - u(162)
    for n, font, color, align in (('DescLine1', 'RK_ProfileDesc', '224 26 46 255', 'west'),
                                  ('DescLine2', 'RK_ProfileDesc2', '138 132 138 255', 'east')):
        blk = kv.find(bgp, n)
        if blk is None:
            continue
        blk[:] = [e for e in blk if not (isinstance(e[1], list) and e[0] in ('fonts', 'colors'))]
        for key in ('pin_to_sibling', 'pin_corner_to_sibling', 'pin_to_sibling_corner', 'auto_wide_tocontents'):
            kv.remove(blk, key)
        kv.setmany(blk, xpos=tx, ypos=u(252) - oy - 4, wide=bar_w, tall=9, font=font, fgcolor_override=color,
                   textAlignment=align, allcaps=1)
    stats = kv.find(bgp, 'StatsContainer')
    if stats is None:
        return
    kv.setmany(stats, xpos=tx, ypos=0, wide=bar_w, tall=44)
    xp = kv.find(stats, 'XPBar')
    if xp is None:
        return
    kv.setmany(xp, xpos=0, ypos=0, wide=bar_w, tall=44)
    kv.setmany(kv.find(xp, 'CurrentXPLabel'), xpos=0, ypos=u(286) - oy - 3, wide=bar_w // 2, tall=6, font='RK_Mono12',
               fgcolor_override='138 132 138 255', textAlignment='west')
    kv.setmany(kv.find(xp, 'NextLevelXPLabel'), xpos=bar_w - bar_w // 2, ypos=u(286) - oy - 3, wide=bar_w // 2,
               tall=6, font='RK_Mono12', fgcolor_override='138 132 138 255', textAlignment='east')
    pb = kv.find(xp, 'ProgressBarsContainer')
    if pb is None:
        return
    kv.setmany(pb, xpos=0, ypos=u(266) - oy, wide=bar_w, tall=u(273) - u(266))
    # the bar: the game paints the XP you had before your last match in the bar's colour and what it brought in a
    # green of its own (vgui's ContinuousProgressBar, fixed in code), which stays until the game restarts. So the bar
    # is painted that same green throughout and a Modulate-2x sheet over it (mm_xp_mul) turns all of it crimson,
    # with the 34 segments' gaps black
    for e in pb:
        if not isinstance(e[1], list):
            continue
        if e[0] == 'ContinuousProgressBar':
            # the empty part painted so that the sheet turns it a neutral dark grey, 2 x (255, 13, 59) x
            # (12, 235, 56) = (24, 24, 26): plainly empty next to the crimson fill (a crimson track hid the progress)
            kv.setmany(e[1], xpos=0, ypos=0, wide='f0', tall='f0', fgcolor_override='100 255 100 255',
                       bgcolor_override=XP_TRACK)
        else:  # the stock segment overlay and frame
            kv.setmany(e[1], wide=0, tall=0, visible=0)
    kv.remove(pb, 'RK_XPGaps')
    kv.add_block(pb, 'RK_XPMul', {'ControlName': 'ImagePanel', 'fieldName': 'RK_XPMul', 'xpos': 0, 'ypos': 0,
                                  'zpos': 5, 'wide': 'f0', 'tall': 'f0', 'visible': 1, 'enabled': 1, 'scaleImage': 1,
                                  'image': T + 'mm_xp_mul', 'proportionaltoparent': 1, 'mouseinputenabled': 0})


# ------------------------------------------------------------------ top bar (matchmaking dashboard)
def dashboard(root):
    """The top bar, 46 px of ink over a crimson hairline: the chat toggle, the six party slots, FIND A GAME (its
    lettering is in its art) and the power block."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    h = u(TOP_H)
    # the dashboard is an expandable panel: the game sizes it to expanded_height, and TopBar is pinned to its bottom
    # edge, so with the stock 35 the bar sat 14 units down, over the logo
    kv.setmany(kv.find(body, 'MMDashboard'), ypos=0, tall=h, expanded_height=h, collapsed_height=0)
    top = kv.find(body, 'TopBar')
    kv.setmany(top, ypos=0, tall=h)
    for n in ('Gradient', 'OuterShadow'):
        blk = kv.find(top, n)
        if blk is not None:
            kv.setmany(blk, visible=0, wide=0, tall=0)
    kv.setmany(kv.find(top, 'BGPanel'), xpos=0, ypos=0, wide='f0', tall=h, border='RK_TopBar')
    chat = kv.find(top, 'ToggleChatButton')
    kv.setmany(chat, xpos=0, ypos=0, wide=u(56), tall=h)
    kv.setmany(kv.find(chat, 'SubImage'), xpos=u(14), ypos=u(10), wide=u(28), tall=u(30), image=T + 'mm_g_chat')
    for i in range(6):
        slot = kv.find(top, f'PartySlot{i}')
        if slot is not None:
            kv.setmany(slot, xpos=u(PARTY_X + i * PARTY_STEP), ypos=u(8), wide=u(PARTY_S), tall=u(PARTY_S))
    fg = kv.find(top, 'FindAGameButton')
    kv.setmany(fg, xpos='rs1-%d' % u(1920 - FIND[1]), ypos=0, wide=u(FIND[1]) - u(FIND[0]), tall=h, labelText='',
               paintbackground=0, paintborder=1, border_default='RK_FindGame', border_armed='RK_FindGame_h',
               border_depressed='RK_FindGame_h', border_selected='RK_FindGame_h')
    kv.setmany(kv.find(fg, 'SubImage'), wide=0, tall=0, visible=0)
    quit_btn = kv.find(top, 'QuitButton')
    kv.setmany(quit_btn, xpos='rs1', ypos=0, wide=u(POWER[1] - POWER[0]), tall=h, paintbackground=0, paintborder=1,
               border_default='RK_PowerBlock', border_armed='RK_PowerBlock_h', border_depressed='RK_PowerBlock_h',
               border_selected='RK_PowerBlock_h', image_drawcolor='224 26 46 255', image_armedcolor='255 52 76 255')
    kv.setmany(kv.find(quit_btn, 'SubImage'), xpos='cs-0.5', ypos='cs-0.5', wide=u(24), tall=u(24),
               image=T + 'mm_g_power', proportionaltoparent=1)
    # the queue box ("Queued for Casual") slides into the bar's middle at the bar's height: the stock layout is for a
    # 35-unit bar, so its spinning logo (radius 10) and its X / manage buttons (14 units at y 11) stuck out of ours.
    # Both go inside the box, centred on its height
    queue = kv.find(top, 'QueueContainer')
    if queue is not None:
        side = h - 4
        for n in ('QueueLogoButton', 'CTFLogoPanel'):
            blk = kv.find(queue, n)
            if blk is not None:
                kv.setmany(blk, xpos=4, ypos=2, wide=side, tall=side)
        logo = kv.find(queue, 'CTFLogoPanel')
        if logo is not None:
            kv.set(logo, 'radius', side // 2 - 1)
        text = kv.find(queue, 'QueueText')
        if text is not None:
            kv.setmany(text, xpos=side + 10, ypos=0, wide='f%d' % (side + 34), tall='f0')
        for n in ('MultiQueuesManageButton', 'CloseButton'):
            blk = kv.find(queue, n)
            if blk is not None:
                kv.setmany(blk, xpos='rs1-6', ypos='cs-0.5', wide=12, tall=12)
                kv.setmany(kv.find(blk, 'SubImage'), xpos=0, ypos=0, wide=12, tall=12)
    # in a game: Disconnect takes the power block's place, Resume Game sits left of FIND A GAME. Their icons sat at
    # the stock spots for a 35-unit bar (Resume's 10 down, half out of ours): centred on the bar's height now
    dc = kv.find(top, 'DisconnectButton')
    if dc is not None:
        kv.setmany(dc, ypos=0, tall=h, paintbackground=0, paintborder=1, border_default='RK_PowerBlock',
                   border_armed='RK_PowerBlock_h', border_depressed='RK_PowerBlock_h', border_selected='RK_PowerBlock_h',
                   defaultFgColor_override=TEXT, armedFgColor_override=TEXT, font='RK_FriendsTitle', allcaps=1)
    rs = kv.find(top, 'ResumeButton')
    if rs is not None:
        kv.setmany(rs, xpos='rs1-%d' % (u(1920 - FIND[0]) + 4), ypos=0, tall=h, paintbackground=0, paintborder=1,
                   border_default='RK_PowerBlock', border_armed='RK_PowerBlock_h', border_depressed='RK_PowerBlock_h',
                   border_selected='RK_PowerBlock_h', defaultFgColor_override=TEXT, armedFgColor_override=TEXT,
                   font='RK_FriendsTitle', allcaps=1)
    for btn in (dc, rs):
        sub = kv.find(btn, 'SubImage') if btn is not None else None
        if sub is not None:
            kv.setmany(sub, xpos=6, ypos='cs-0.5', wide=14, tall=14, proportionaltoparent=1)


def patch_party_member(root):
    """A party slot of the top bar (dashboardpartymember.res): a grey hairline box, a + while empty."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.setmany(kv.find(body, 'EmptyImage'), xpos='cs-0.5', ypos='cs-0.5', wide='p0.47', tall='p0.47',
               image=T + 'mm_party_plus', proportionaltoparent=1)
    kv.add_block(body, 'RK_SlotFrame', {'ControlName': 'ImagePanel', 'fieldName': 'RK_SlotFrame', 'xpos': 0,
                                        'ypos': 0, 'zpos': 9, 'wide': 'f0', 'tall': 'f0', 'visible': 1, 'enabled': 1,
                                        'scaleImage': 1, 'image': T + 'mm_party', 'proportionaltoparent': 1,
                                        'mouseinputenabled': 0})


# ================================================================== the other full-screen menus
# Class select, team select and the map briefing in the main menu's own language: a header block where the main menu
# has its logo (a mono label, a big title with a crimson ghost, the crimson rule, a mono line), numbered rows like its
# buttons down the left, the screen-corner brackets and the vertical tagline, the menu scene behind.
ROW_X0, ROW_X1, ROW_Y, ROW_H, ROW_STEP = 60, 560, 236, 44, 51
FOOT_Y, FOOT_H, FOOT_W, FOOT_GAP = 996, 42, 172, 12   # three fill the content column, 60 to 600 px
TEAM_COL = {'blu': (112, 164, 232), 'red': (255, 120, 104)}

# class select: the classes as a code matrix on the left (rows OFFENSE / DEFENSE / SUPPORT of hex-coded cells,
# RANDOM under them), the class under the pointer on the right as the game's 3D model in a biometric scan frame
CLASS_GROUPS = [('OFFENSE', '攻撃', ('scout', 'soldier', 'pyro')),
                ('DEFENSE', '防御', ('demoman', 'heavyweapons', 'engineer')),
                ('SUPPORT', '支援', ('medic', 'sniper', 'spy'))]
MX0, MY0, MW = 60, 236, 634                     # px: the matrix panel
CELL_W, CELL_H, CELL_GX = 190, 132, 12          # px: a cell (build_art.CELL), the gap between cells
ROW_LABEL, ROW_GAP, MTITLE, RANDOM_H = 24, 14, 46, 52
MY1 = MY0 + MTITLE + 3 * (ROW_LABEL + CELL_H + ROW_GAP) + 2 + RANDOM_H + 20
SCAN = (885, 120, 1845, 980)                    # px: the scan frame; the model's panel is centred in it
PLATFORM_Y = SCAN[3] - 104                      # px: the platform the model stands on
MODEL = 400                                     # units: the model's panel, a square (the stock one is 480)


def model_panel():
    """The class model's panel (x from the right edge, y, size) so that the model stands in the middle of the scan
    frame with its feet on the platform. The game frames it with the panel's settings: the camera at the panel's
    centre, horizontal fov 25, the model 320 ahead, 10 to the side and 49 down (origin_x / _y / _z): so it stands
    left of the centre and low, both in proportion to the panel's size, and its soles show 15 px under that point at
    the stock 480 (measured in game). The panel stays wholly on the screen: CPotteryWheelPanel::Paint shortens its
    projection by whatever is above the screen's top and draws it from there, which pushes the model down and
    stretches it."""
    k = MODEL * PX / 2 / np.tan(np.radians(25 / 2))   # px per unit of distance across the view, at 1 unit ahead
    left = (SCAN[0] + SCAN[2]) / 2 + 10 / 320 * k - MODEL * PX / 2
    top = PLATFORM_Y - 15 * MODEL / 480 - 49 / 320 * k - MODEL * PX / 2
    assert top >= 0 and left + MODEL * PX <= 1920
    return right(left), u(top), MODEL


def matrix_cells():
    """(class, x0, y0, x1, y1) in px for every cell, RANDOM last."""
    out = []
    for i, (_, _, keys) in enumerate(CLASS_GROUPS):
        y = MY0 + MTITLE + i * (ROW_LABEL + CELL_H + ROW_GAP) + ROW_LABEL
        for j, key in enumerate(keys):
            x = MX0 + 20 + j * (CELL_W + CELL_GX)
            out.append((key, x, y, x + CELL_W, y + CELL_H))
    y = MY0 + MTITLE + 3 * (ROW_LABEL + CELL_H + ROW_GAP) + 2
    out.append(('random', MX0 + 20, y, MX0 + MW - 20, y + RANDOM_H))
    return out


def matrix_frame(cv):
    """The code matrix's panel: black glass, its title and BUFFER slots, each row's number, name and kanji over a
    dotted rule; the cells are images of their own over it."""
    x0, y0, x1, y1 = MX0, MY0, MX0 + MW, MY1
    cv.chamfer(x0, y0, x1, y1, fill=rgba(PANEL, 214), tr=18, bl=18)
    cv.chamfer(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5, outline=rgba(RED, 120), width=1, tr=18, bl=18)
    cv.rect(x0, y0 + 30, x0 + 3, y1 - 40, rgba(RED))
    cv.rect(x0 + 20, y0 + 18, x0 + 27, y0 + 25, rgba(RED))
    cv.mixed(x0 + 34, y0 + 22, [('NEURAL MATRIX', F('mono', 15), rgba(TEXT_RGB)), ('  //  ', F('mono', 13), rgba(RED)),
                                ('神経回路', F('jp5', 13), rgba(GREY))], 'lm')
    bx = x1 - 20
    for _ in range(3):  # BUFFER: three empty slots, right to left
        cv.chamfer(bx - 30, y0 + 13, bx, y0 + 31, outline=rgba(RED, 170), width=1, tl=5)
        bx -= 38
    cv.text(bx - 4, y0 + 22, 'BUFFER', F('mono', 12), rgba(GREY), 'rm')
    cv.rect(x0 + 20, y0 + MTITLE - 4, x1 - 20, y0 + MTITLE - 3, rgba(RED, 110))
    for i, (en, jp, _) in enumerate(CLASS_GROUPS):
        y = y0 + MTITLE + i * (ROW_LABEL + CELL_H + ROW_GAP) + ROW_LABEL / 2
        end = cv.mixed(x0 + 20, y, [('%02d' % (i + 1), F('mono', 12), rgba(RED)), ('  //  ', F('mono', 12), rgba(RED, 140)),
                                    (en, F('mono', 13), rgba(TEXT_RGB)), ('   ', F('mono', 12), rgba(GREY)),
                                    (jp, F('jp5', 12), rgba(GREY))], 'lm')
        for x in range(int(end) + 12, x1 - 20, 6):
            cv.rect(x, y, x + 2, y + 1, rgba(RED, 90))


def scan_frame(cv):
    """The biometric scan frame the class's model stands in: corner brackets, rulers up both sides, a scan beam,
    a platform under the feet, readouts in the corners."""
    x0, y0, x1, y1 = SCAN
    mx = (x0 + x1) / 2
    cv.brackets(x0, y0, x1, y1, 64, rgba(RED), 3)
    for a, b in (((x0 + 80, y0), (x1 - 80, y0)), ((x0 + 80, y1), (x1 - 80, y1)),
                 ((x0, y0 + 80), (x0, y1 - 80)), ((x1, y0 + 80), (x1, y1 - 80))):
        cv.line([a, b], rgba(RED, 46), 1)
    cv.rect(x0 + 26, y0 + 26, x0 + 33, y0 + 33, rgba(RED))
    cv.mixed(x0 + 40, y0 + 30, [('BIOMETRIC SCAN', F('mono', 15), rgba(TEXT_RGB)), ('  //  ', F('mono', 13), rgba(RED)),
                                ('生体走査', F('jp5', 13), rgba(GREY))], 'lm')
    cv.mixed(x1 - 26, y0 + 30, [('SUBJECT', F('mono', 13), rgba(GREY)), ('  //  ', F('mono', 12), rgba(RED)),
                                ('被験体', F('jp5', 12), rgba(GREY))], 'rm')
    cv.text(x1 - 26, y0 + 52, '0x7F3A // SOUL HARVEST DIVISION', F('mono', 11), rgba(GREY, 150), 'rm')
    for side, sx in ((1, x0 + 34), (-1, x1 - 34)):  # rulers
        cv.line([(sx, y0 + 100), (sx, y1 - 120)], rgba(RED, 90), 1)
        for k, y in enumerate(range(y0 + 100, y1 - 119, 20)):
            long = k % 5 == 0
            cv.line([(sx, y), (sx + side * (14 if long else 7), y)], rgba(RED, 150 if long else 80), 1)
            if long and side == 1:
                cv.text(sx + 20, y, '%03d' % (k * 10), F('mono', 10), rgba(GREY, 170), 'lm')
    by = y0 + (y1 - y0) * 0.36  # the scan beam
    for k, a in ((10, 18), (5, 40), (2, 90)):
        cv.rect(x0 + 60, by - k, x1 - 60, by + k, rgba(RED, a))
    cv.rect(x0 + 60, by - 0.5, x1 - 60, by + 0.5, rgba(HOT_RGB, 220))
    py = PLATFORM_Y
    for rx, ry, a, wd in ((250, 38, 70, 1), (200, 30, 150, 2), (130, 19, 110, 1)):
        cv.d.ellipse([(mx - rx) * ui_kit.K, (py - ry) * ui_kit.K, (mx + rx) * ui_kit.K, (py + ry) * ui_kit.K],
                     outline=rgba(RED, a), width=wd * ui_kit.K)
    for k in range(24):
        ang = k * np.pi / 12
        ca, sa = np.cos(ang), np.sin(ang)
        cv.line([(mx + 200 * ca, py + 30 * sa), (mx + 224 * ca, py + 34 * sa)], rgba(RED, 140), 1)
    rows = (('NEURAL SYNC', '98.6 %'), ('LINK STATUS', 'STANDBY'), ('SIGNAL', None))
    for i, (k, v) in enumerate(rows):
        y = y1 - 74 + i * 22
        cv.text(x0 + 30, y, k, F('mono', 12), rgba(GREY), 'lm')
        if v:
            cv.text(x0 + 180, y, v, F('mono', 12), rgba(RED), 'lm')
        else:
            for b in range(8):
                cv.rect(x0 + 180 + b * 11, y - 5, x0 + 187 + b * 11, y + 5, rgba(RED, 230 if b < 6 else 60))
    cv.mixed(x1 - 30, y1 - 30, [('死神', F('jp5', 11), rgba(GREY, 170)), ('  //  ', F('mono', 11), rgba(RED, 170)),
                                ('OPERATIVE PREVIEW', F('mono', 11), rgba(GREY, 170))], 'rm')


# team select, in units: BLU and RED as two big panels side by side, RANDOM and SPECTATE under them
TPANEL_PX = (640, 400)
TP_W, TP_H, TP_GAP, TP_Y = 284, 178, 10, 133
TEAM_EDGE = {'blu': (112, 164, 232), 'red': (224, 26, 46)}
TEAM_DARK = {'blu': (12, 20, 34), 'red': (30, 6, 10)}


# Team select since 0.9: the screen cut in two along a slanted seam, each half a side of the Wall in its team's
# colour; the half under the pointer floods (its hover picture), RANDOM is the node on the seam. Each half is a
# button a little wider than half the screen (THALF_W px of 1920, the slant's reach over the middle), the right one
# over the left where they overlap.
THALF_W, THALF_SLANT = 1120, 320
THALF_TEX = 1024                    # the pictures: square textures, the panel stretches them back
TRANDOM_PX = (300, 92)


def _tfont(key, size):
    from PIL import ImageFont
    name = {'b': 'Rajdhani-Bold.ttf', 'sb': 'Rajdhani-SemiBold.ttf', 'm': 'ShareTechMono-Regular.ttf',
            'jp': 'ReaperJPSubset-Bold.ttf'}[key]
    return ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', name), int(size))


def team_half(team, armed):
    """One half of the team select, THALF_W x 1080 px drawn in the HUD's crimson (BLU's is its azure twin):
    the Wall's pattern stronger towards the outer edge, the team's name huge, PLAYERS over the place of the game's
    count, its number key; armed, the pattern floods, the name turns white with its split copies and BREACH lights."""
    from PIL import ImageDraw, ImageChops, ImageFilter
    import build_art
    w, h = THALF_W, 1080
    left = team == 'blu'
    shape = [(0, 0), (w, 0), (w - THALF_SLANT, h), (0, h)] if left else [(THALF_SLANT, 0), (w, 0), (w, h), (0, h)]
    clip = Image.new('L', (w, h), 0)
    ImageDraw.Draw(clip).polygon(shape, fill=255)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    base = Image.new('RGBA', (w, h), (10, 4, 7, 150 if armed else 90))
    base.putalpha(ImageChops.multiply(base.split()[3], clip))
    im.alpha_composite(base)
    pat = build_art.wall_texture().resize((w, h), Image.BICUBIC)
    ramp = Image.new('L', (w, 1))
    px = ramp.load()
    for x in range(w):
        f = x / (w - 1)
        f = 1 - f if left else f
        px[x, 0] = int(255 * min(1.0, (0.22 + 0.85 * f) * (1.0 if armed else 0.42)))
    pat.putalpha(ImageChops.multiply(ImageChops.multiply(pat.split()[3], ramp.resize((w, h))), clip))
    im.alpha_composite(pat)
    if armed:
        glow = Image.new('RGBA', (w, h), RED + (0,))
        glow.putalpha(clip.point(lambda v: int(v * 0.14)))
        im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    seam = [(w, 0), (w - THALF_SLANT, h)] if left else [(THALF_SLANT, 0), (0, h)]
    d.line(seam, fill=WHITE + (255 if armed else 150,), width=3 if armed else 2)
    x = 300 if left else w - 300          # the text column: 300 px in from the screen's edge side
    anchor = 'l' if left else 'r'
    name = 'BLU' if left else 'RED'
    hot = (255, 52, 76)
    d.rectangle([x - (0 if left else 9), 146, x + (9 if left else 0), 155], fill=hot + (255,))
    d.text((x + (18 if left else -18), 151), ('BLU  //  BUILDERS LEAGUE UNITED' if left else
                                               'RED  //  RELIABLE EXCAVATION DEMOLITION'), font=_tfont('m', 18),
           fill=WHITE + (235,), anchor=anchor + 'm')
    big = _tfont('b', 300)
    if armed:
        lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((x, 340), name, font=big, fill=hot + (255,), anchor=anchor + 'm')
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
        d = ImageDraw.Draw(im)
        d.text((x - 7, 340), name, font=big, fill=hot + (230,), anchor=anchor + 'm')
        d.text((x + 7, 340), name, font=big, fill=(120, 20, 40, 200), anchor=anchor + 'm')
        d.text((x, 340), name, font=big, fill=WHITE + (255,), anchor=anchor + 'm')
    else:
        d.text((x, 340), name, font=big, fill=hot + (190,), anchor=anchor + 'm')
    d.text((x, 560), 'PLAYERS', font=_tfont('m', 20), fill=(WHITE if armed else GREY) + (255,), anchor=anchor + 'm')
    d.text((x, 770), 'KEY 1' if left else 'KEY 2', font=_tfont('m', 18), fill=(WHITE if armed else GREY) + (255,),
           anchor=anchor + 'm')
    bx0, bx1 = (x, x + 250) if left else (x - 250, x)
    if armed:
        d.polygon([(bx0, 820), (bx1, 820), (bx1, 866), (bx1 - 12, 878), (bx0, 878)], fill=WHITE + (255,))
        d.text(((bx0 + bx1) / 2, 849), 'BREACH  >>', font=_tfont('b', 30), fill=INK + (255,), anchor='mm')
    else:
        d.line([(bx0, 820), (bx1, 820), (bx1, 866), (bx1 - 12, 878), (bx0, 878), (bx0, 820)], fill=hot + (170,), width=2)
        d.text(((bx0 + bx1) / 2, 849), 'BREACH', font=_tfont('b', 30), fill=WHITE + (200,), anchor='mm')
    im = im.resize((THALF_TEX, THALF_TEX), Image.LANCZOS)
    return build_art.to_blue(im) if left else im


def team_random(armed):
    """RANDOM, the node on the seam: a hexagon plate."""
    from PIL import ImageDraw
    w, h = TRANDOM_PX
    k = 2
    im = Image.new('RGBA', (w * k, h * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(30 * k, 0), ((w - 30) * k, 0), (w * k - 1, h * k / 2), ((w - 30) * k, h * k - 1), (30 * k, h * k - 1),
           (0, h * k / 2)]
    d.polygon(pts, fill=(WHITE + (255,)) if armed else (7, 7, 9, 245))
    d.line(pts + [pts[0]], fill=WHITE + (255,), width=2 * k)
    d.text((w * k / 2, 36 * k), 'RANDOM', font=_tfont('b', 34 * k), fill=(INK if armed else WHITE) + (255,), anchor='mm')
    d.text((w * k / 2, 68 * k), 'KEY 3  //  LET THE WALL DECIDE', font=_tfont('m', 10 * k),
           fill=(INK if armed else GREY) + (255,), anchor='mm')
    return im.resize((w, h), Image.LANCZOS)


def team_panel(cv, team, armed):
    """A team's panel on the team select, 640 x 400 px: deep team-tinted glass, the name large, its kanji seal,
    JOIN, and room on the right for the game's player count under PLAYERS; armed, the team's light fills it."""
    w, h = TPANEL_PX
    col = TEAM_EDGE[team]
    cuts = {'tr': 40, 'bl': 40}
    cv.chamfer(0, 0, w, h, fill=rgba(TEAM_DARK[team], 236), **cuts)
    if armed:
        cv.chamfer(0, 0, w, h, fill=rgba(col, 52), **cuts)
    cv.scan(0, 0, w, h, rgba(col), alpha=26 if armed else 12, step=3)
    cv.chamfer(1, 1, w - 1, h - 1, outline=rgba(WHITE if armed else col, 255 if armed else 150),
               width=3 if armed else 1, **cuts)
    cv.rect(0, 52, 8, h - 92, rgba(col))
    cv.mixed(34, 48, [('TEAM', F('mono', 16), rgba(GREY)), ('  //  ', F('mono', 14), rgba(col)),
                      ('陣営', F('jp5', 15), rgba(GREY))], 'lm')
    name = 'BLU' if team == 'blu' else 'RED'
    cv.text(34 + 6, 66 + 5, name, F('raj7', 200), rgba(col, 220 if armed else 170), spacing=6)
    cv.text(34, 66, name, F('raj7', 200), rgba(WHITE), spacing=6)
    sx, sy, ss = w - 150, 58, 92  # the kanji seal, clear of the cut corner
    cv.rect(sx, sy, sx + ss, sy + ss, rgba(col))
    cv.text(sx + ss / 2, sy + ss / 2 + 2, '青' if team == 'blu' else '赤', F('jp9', 70), rgba(WHITE), 'mm')
    cv.rect(34, 286, w - 34, 287, rgba(col, 120))
    cv.rect(34, 284, 140, 289, rgba(col))
    cv.mixed(34, 336, [('JOIN', F('raj7', 34), rgba(WHITE)), ('  //  ', F('mono', 16), rgba(col)),
                       ('参加', F('jp5', 18), rgba(GREY))], 'lm')
    if armed:
        cv.text(196, 336, '>>', F('raj7', 34), rgba(col), 'lm')
    cap = [('PLAYERS', F('mono', 14), rgba(GREY)), ('  //  ', F('mono', 14), rgba(col)), ('人数', F('jp5', 14), rgba(GREY))]
    cv.mixed(w - 34 - sum(cv.width(t, f) for t, f, _ in cap), 304, cap, 'lm')
CLASS_COUNTS = {'scout': 'numScout', 'soldier': 'numSoldier', 'pyro': 'numPyro', 'demoman': 'numDemoman',
                'heavyweapons': 'numHeavy', 'engineer': 'numEngineer', 'medic': 'numMedic', 'sniper': 'numSniper',
                'spy': 'numSpy'}
HEADERS = {  # screen: (label, Japanese label, title (None: the game's), mono line)
    'class': ('CLASS SELECT', '兵科選択', 'CHOOSE A CLASS', 'DEPLOYMENT ORDERS  //  出撃命令  //  SOUL HARVEST DIVISION'),
    'team': ('TEAM SELECT', '陣営選択', 'CHOOSE A SIDE', 'ALLEGIANCE  //  所属  //  SOUL HARVEST DIVISION'),
    'map': ('MISSION BRIEFING', '作戦概要', None, None),
}


def header(cv, label, jp, title, line):
    """Where the main menu has its logo: ■ label // LABEL, the big title, the crimson rule, the mono line."""
    ui_kit.label(cv, 60, 100, label, jp)
    if title:
        f = F('raj7', 52)
        cv.text(58, 146, title, f, rgba(RED, 150), 'ls', spacing=2)
        cv.text(60, 146, title, f, rgba(WHITE), 'ls', spacing=2)
    cv.rect(60, 162, 94, 165, rgba(RED))
    cv.rect(94, 163, 600, 164, rgba(RED, 140))
    if line:
        cv.mixed(60, 178, [(part, F('jp5', 11) if is_cjk(part) else F('mono', 12), rgba(GREY))
                           for part in split_cjk(line)], 'lm')


def header_centre(cv, label, jp):
    """The briefing's header, centred: ■ label // LABEL, the room for the game's title, the crimson rule."""
    parts = [(jp, F('jp5', 11), rgba(RED)), ('  //  ', F('mono', 11), rgba(RED, 150)), (label, F('mono', 12), rgba(RED))]
    x = 960 - (13 + sum(cv.width(t, f) for t, f, _ in parts)) / 2
    cv.rect(x, 96.5, x + 7, 103.5, rgba(RED))
    cv.mixed(x + 13, 100, parts, 'lm')
    cv.rect(960 - 300, 163, 960 + 300, 164, rgba(RED, 140))
    cv.rect(960 - 30, 162, 960 + 30, 165, rgba(RED))


HEAD_CENTRE = (660, 84, 1260, 192)  # px: the centred header's box


def cx(x_px):
    """An x in 1080p px as units from the screen's centre (the layout stays centred at any aspect ratio)."""
    return 'c%d' % (u(x_px) - u(960))


def is_cjk(s):
    return any(0x3000 <= ord(ch) <= 0x9fff for ch in s)


def split_cjk(s):
    """'A  //  漢字  //  B' -> runs that are all CJK or all not."""
    runs, cur = [], ''
    for ch in s:
        if cur and is_cjk(ch) != is_cjk(cur[-1]):
            runs.append(cur)
            cur = ''
        cur += ch
    return runs + ([cur] if cur else [])


def foot(cv, x0, armed):
    """A text button of the foot row (the game writes its text): the row shape, the size of the main menu's chips' row."""
    x1, y0, y1 = x0 + FOOT_W, FOOT_Y, FOOT_Y + FOOT_H
    if armed:
        cv.chamfer(x0, y0, x1, y1, fill=rgba(RED), br=12)
    else:
        cv.chamfer(x0, y0, x1, y1, fill=rgba(PANEL, 210), br=12)
        cv.rect(x0, y0, x0 + 2, y1, rgba(RED_DIM))
        cv.chamfer(x0, y0, x1, y1, outline=rgba(RED, 90), width=1, br=12)


def screen_art(out):
    for key, (label, jp, title, line) in HEADERS.items():
        if key == 'map':
            out.thumb('sc_head_map', cut(render(lambda cv: header_centre(cv, label, jp)), HEAD_CENTRE))
            continue
        r = render(lambda cv: header(cv, label, jp, title, line))
        out.thumb('sc_head_' + key, cut(r, (56, 84, 620, 192)), team=key == 'class')
    out.thumb('cs_matrix', cut(render(matrix_frame), (MX0, MY0, MX0 + MW, MY1)), team=True)
    out.thumb('cs_scan', cut(render(scan_frame), SCAN), team=True)
    for team in ('blu', 'red'):
        for armed in (False, True):
            out.thumb(f'sc_thalf_{team}' + ('_h' if armed else ''), team_half(team, armed), mips=False)
    for armed in (False, True):
        out.thumb('sc_trandom' + ('_h' if armed else ''), team_random(armed), mips=False)
    for armed in (False, True):
        sfx = '_h' if armed else ''
        r = render(lambda cv: foot(cv, ROW_X0, armed))
        out.thumb('sc_foot' + sfx, cut(r, (ROW_X0, FOOT_Y, ROW_X0 + FOOT_W, FOOT_Y + FOOT_H)))


SCREEN_FONTS = {
    'RK_FootText': [['1', [['name', 'Rajdhani', None], ['tall', '11', None], ['weight', '700', None],
                           ['antialias', '1', None]], None]],
    'RK_RowCount': [['1', [['name', 'Rajdhani', None], ['tall', '13', None], ['weight', '700', None],
                           ['antialias', '1', None]], None]],
    'RK_CardCount': [['1', [['name', 'Rajdhani', None], ['tall', '9', None], ['weight', '700', None],
                            ['antialias', '1', None]], None]],
    'RK_TeamCount': [['1', [['name', 'Rajdhani', None], ['tall', '34', None], ['weight', '700', None],
                            ['antialias', '1', None]], None]],
    'RK_ScreenTitle': [['1', [['name', 'Rajdhani', None], ['tall', '29', None], ['weight', '700', None],
                              ['antialias', '1', None]], None]],
    'RK_MapTitle': [['1', [['name', 'Rajdhani', None], ['tall', '52', None], ['weight', '700', None],
                           ['antialias', '1', None]], None]],
    'RK_BriefBig': [['1', [['name', 'Bahnschrift SemiCondensed', None], ['tall', '12', None], ['weight', '500', None],
                           ['antialias', '1', None]], None]],
    'RK_Brief': [['1', [['name', 'Bahnschrift SemiCondensed', None], ['tall', '9', None], ['weight', '400', None],
                        ['antialias', '1', None]], None]],
}
FONTS.update(SCREEN_FONTS)
BORDERS['RK_Foot'] = [['bordertype', 'scalable_image', None], ['backgroundtype', '2', None],
                      ['image', T + 'sc_foot', None], ['src_corner_height', '28', None], ['src_corner_width', '28', None],
                      ['draw_corner_width', '6', None], ['draw_corner_height', '6', None]]
BORDERS['RK_Foot_h'] = [list(e) for e in BORDERS['RK_Foot']]
kv.set(BORDERS['RK_Foot_h'], 'image', T + 'sc_foot_h')
BORDERS['RK_None'] = _border('blank')


def frame_dressing(body, video=None):
    """The main menu's scene, corner brackets and vertical tagline, behind a full-screen menu. With video, the main
    menu's looping video instead of the scene (when there is one), under a shade: 'left' darker behind content on
    the left (as the main menu), 'centre' darker overall for content in the middle."""
    if video and VIDEO:
        # the video (in three parts: its third over the first two, build.py menu_video), then the shade; the main
        # menu's shade is already in the frames when VIDEO_SHADED
        scenes = [('RK_Scene', 'mm_video', -41)] + ([('RK_SceneC', 'mm_video_c', -40)] if VIDEO_PARTS == 3 else [])
        shade = None if video == 'left' and VIDEO_SHADED else 'mm_video_shade' if video == 'left' else 'mm_video_dim'
        for n in ('RK_Scene', 'RK_SceneC', 'RK_SceneShade'):
            kv.remove(body, n)
        for n, img, z in scenes:
            body.insert(1, [n, _block({'ControlName': 'ImagePanel', 'fieldName': n, 'xpos': 'rs1', 'ypos': 0, 'zpos': z,
                                       'wide': 'o1.778', 'tall': 'f0', 'visible': 1, 'enabled': 1, 'scaleImage': 1,
                                       'image': T + img, 'mouseinputenabled': 0}), None])
        if shade:
            body.insert(1, ['RK_SceneShade', _block({'ControlName': 'ImagePanel', 'fieldName': 'RK_SceneShade',
                                                     'xpos': 0, 'ypos': 0, 'zpos': -39, 'wide': 'f0', 'tall': 'f0',
                                                     'visible': 1, 'enabled': 1, 'scaleImage': 1, 'image': T + shade,
                                                     'mouseinputenabled': 0}), None])
        dress_frame(body)
        return
    for n, e in (('RK_Scene', {'ControlName': 'ImagePanel', 'fieldName': 'RK_Scene', 'xpos': 'rs1', 'ypos': 0,
                               'zpos': -40, 'wide': 'o1.778', 'tall': 'f0', 'visible': 1, 'enabled': 1, 'scaleImage': 1,
                               'image': '../console/background_reaper_widescreen', 'mouseinputenabled': 0}),
                 ('RK_SceneShade', {'ControlName': 'ImagePanel', 'fieldName': 'RK_SceneShade', 'xpos': 0, 'ypos': 0,
                                    'zpos': -39, 'wide': 'f0', 'tall': 'f0', 'visible': 1, 'enabled': 1,
                                    # 152: shade_full is 60 % black (87 % once corrected for the game's linear
                                    # blending), so this dims the scene by the designed 28 %
                                    'scaleImage': 1, 'image': T + 'shade_full', 'drawcolor': '255 255 255 152',
                                    'mouseinputenabled': 0})):
        kv.remove(body, n)
        body.insert(1, [n, _block(e), None])
    dress_frame(body)


def dress_frame(body):
    """The corner brackets and the vertical tagline."""
    put(body, 'RK_Tagline', image('RK_Tagline', TAGLINE_BOX, 'mm_tagline', z=-30, xpos=right(TAGLINE_BOX[0])))
    for k, (bx0, by0, bx1, by1) in BRACKETS.items():
        e = image('RK_Bracket_' + k, (bx0, by0, bx1, by1), 'mm_bracket_' + k, z=-30)
        if k[1] == 'r':
            e['xpos'] = right(bx0)
        if k[0] == 'b':
            e['ypos'] = bottom(by0)
        put(body, 'RK_Bracket_' + k, e)


def screen_header(body, key, centre=False):
    if centre:
        put(body, 'RK_Header', image('RK_Header', HEAD_CENTRE, 'sc_head_' + key, z=-20, xpos=cx(HEAD_CENTRE[0])))
    else:
        put(body, 'RK_Header', image('RK_Header', (56, 84, 620, 192), 'sc_head_' + key, z=-20))


def foot_button(blk, slot, **extra):
    """A text button in the foot row, slot 0, 1, 2 from the left: the game's text in Rajdhani, all caps."""
    x0 = ROW_X0 + slot * (FOOT_W + FOOT_GAP)
    kv.setmany(blk, xpos=u(x0), ypos=bottom(FOOT_Y), wide=u(FOOT_W), tall=u(FOOT_H), zpos=8, font='RK_FootText',
               allcaps=1, textAlignment='center', paintbackground=0, paintborder=1, border_default='RK_Foot',
               border_armed='RK_Foot_h', border_depressed='RK_Foot_h', border_selected='RK_Foot_h',
               defaultFgColor_override=TEXT, armedFgColor_override='7 7 9 255', depressedFgColor_override='7 7 9 255',
               selectedFgColor_override='7 7 9 255', disabledFgColor_override='96 92 98 255',
               disabledfgcolor2_override='96 92 98 255', **extra)


def classselection(root):
    """Class select, the cyberpunk way: the classes as a code matrix on the left, hex-coded cells in rows OFFENSE /
    DEFENSE / SUPPORT with RANDOM under them, each with its number key and how many teammates play it; the class
    under the pointer stands on the right as the game's 3D model in a biometric scan frame; the menu video behind.
    The class menu rewrites its buttons' pictures, so each cell is an image under a see-through button whose hover
    border is the lit cell (screens.card_button)."""
    import screens
    body = next(e[1] for e in root if isinstance(e[1], list))
    for n in ('MenuBG', 'ShadedBar', 'ClassMenuSelect', 'Offense', 'Defense', 'Support', 'ClassTipsPanel',
              'localPlayerImage', 'localPlayerBG', 'CountLabel', 'Hint'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, xpos=9999, visible=0)
    for e in body:
        if isinstance(e[1], list) and (e[0].startswith('MvMUpgradeImage') or e[0].startswith('countImage')):
            kv.set(e[1], 'xpos', 9999)
    frame_dressing(body, video='centre')
    screen_header(body, 'class')
    put(body, 'RK_Matrix', image('RK_Matrix', (MX0, MY0, MX0 + MW, MY1), 'cs_matrix', z=2))
    put(body, 'RK_Scan', image('RK_Scan', SCAN, 'cs_scan', z=1, xpos=right(SCAN[0])))
    for key, x0, y0, x1, y1 in matrix_cells():
        blk = kv.find(body, key)
        if blk is None:
            continue
        screens.card_button(body, blk, f'cs_cell_{key}', u(x0), u(y0), u(x1) - u(x0), u(y1) - u(y0))
        num = CLASS_COUNTS.get(key)
        if num and kv.find(body, num) is not None:
            # teammates playing it: the cell's top right corner
            kv.setmany(kv.find(body, num), xpos=u(x1) - 16, ypos=u(y0) + 1, wide=12, tall=10, zpos=9,
                       textAlignment='east', fgcolor='255 52 76 255', font='RK_CardCount', autoResize=0,
                       pinCorner=0, textinsetx=0, visible=1)
    # the model in the middle of the scan frame, on its platform; from the right edge, as the frame is
    mx, my, size = model_panel()
    kv.setmany(kv.find(body, 'TFPlayerModel'), xpos=mx, ypos=my, wide=size, tall=size, zpos=3)
    for slot, n in enumerate(('CancelButton', 'EditLoadoutButton', 'ResetButton')):
        blk = kv.find(body, n)
        if blk is not None:
            foot_button(blk, slot)
    # in the player's team colour, as the HUD in a match: the header, the matrix, the scan frame and the cells are
    # team pictures (CTFImagePanel: the b/ twin on BLU). What the scheme draws stays crimson on both teams: a
    # cell's hover, the foot buttons, the counts
    for e in body:
        if isinstance(e[1], list) and (e[0] in ('RK_Header', 'RK_Matrix', 'RK_Scan') or e[0].startswith('RK_Card_')):
            img = kv.get(e[1], 'image')
            if img and img.startswith(T):
                kv.setmany(e[1], ControlName='CTFImagePanel', teambg_1=img, teambg_2=img,
                           teambg_3=T + 'b/' + img[len(T):])


def teammenu(root):
    """Team select as a face-off: BLU and RED as two big panels side by side with their player counts, RANDOM and
    SPECTATE under them, the menu video behind."""
    import screens
    body = next(e[1] for e in root if isinstance(e[1], list))
    for n in ('MenuBG', 'bluedoor', 'reddoor', 'autodoor', 'spectate', 'ShadedBar', 'TeamMenuSelect'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, visible=0, wide=0, tall=0)
    for n in ('teambutton0', 'teambutton1', 'teambutton2', 'teambutton3', 'TeamMenuAuto', 'TeamMenuSpectate'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.set(blk, 'xpos', 9999)
    frame_dressing(body, video='centre')
    kv.remove(body, 'RK_Header')
    sounds = {'sound_depressed': 'UI/buttonclick.wav', 'sound_released': 'UI/buttonclickrelease.wav',
              'sound_armed': 'UI/buttonrollover.wav'}
    hw = u(THALF_W)
    for team, name, cmd, x, count, col, align in (
            ('blu', 'RK_JoinBlue', 'jointeam blue', u(0) - u(960), 'BlueCount', '112 164 232 255', 'west'),
            ('red', 'RK_JoinRed', 'jointeam red', u(1920 - THALF_W) - u(960), 'RedCount', '255 120 104 255', 'east')):
        blk = _block(dict({'fieldName': name, 'visible': 1, 'enabled': 1, 'tabPosition': 0}, **sounds))
        kv.remove(body, name)
        body.append([name, blk, None])
        screens.card_button(body, blk, f'sc_thalf_{team}', f'c{x}', 0, hw, 480, command=cmd)
        # the game's player count, big, under the half's PLAYERS (300 px in from its outer edge, as the art's text)
        cx0 = (u(300) - u(960)) if team == 'blu' else (u(1620) - u(960) - 120)
        kv.setmany(kv.find(body, count), xpos=f'c{cx0}', ypos=u(590), zpos=9, wide=120, tall=u(110),
                   textAlignment=align, fgcolor='236 232 232 255', font='RK_TeamCount', mouseinputenabled=0,
                   textinsetx=0)
    rw, rh = u(TRANDOM_PX[0]), u(TRANDOM_PX[1])
    blk = _block(dict({'fieldName': 'RK_JoinAuto', 'visible': 1, 'enabled': 1, 'tabPosition': 0}, **sounds))
    kv.remove(body, 'RK_JoinAuto')
    body.append(['RK_JoinAuto', blk, None])
    screens.card_button(body, blk, 'sc_trandom', f'c{-rw // 2}', u(540) - rh // 2, rw, rh, command='jointeam auto')
    kv.set(blk, 'zpos', 12)
    kv.set(kv.find(body, 'RK_Card_RK_JoinAuto'), 'zpos', 11)
    bw, by = 110, u(930)
    blk = _block(dict({'ControlName': 'CExButton', 'fieldName': 'RK_JoinSpec', 'visible': 1, 'enabled': 1,
                       'tabPosition': 0, 'labelText': 'SPECTATE', 'Command': 'jointeam spectate'}, **sounds))
    kv.remove(body, 'RK_JoinSpec')
    body.append(['RK_JoinSpec', blk, None])
    foot_button(blk, 0)
    kv.setmany(blk, xpos=f'c{-bw // 2}', ypos=by, wide=bw, zpos=12)
    # "teams are full" / highlander: under those, centred, in the mono line's crimson
    y = by + u(FOOT_H) + 6
    for n in ('HighlanderLabel', 'TeamsFullLabel'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, xpos='c-200', ypos=y, wide=400, tall=10, font='RK_Mono12', fgcolor='224 26 46 255',
                       textAlignment='center')
            y += 12
    for n in ('HighlanderLabelShadow', 'TeamsFullLabelShadow', 'TeamsFullArrow'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, wide=0, tall=0, xpos=9999)
    blk = kv.find(body, 'CancelButton')
    if blk is not None:
        foot_button(blk, 0)


def textwindow(root):
    """The server's welcome message (MOTD) on joining: the stock chalkboard gives way to a terminal page, centred
    on the screen. //  INCOMING TRANSMISSION over the server's title in large type and a crimson rule, the
    server's text (plain or its web page) in a framed glass panel, CONTINUE under the panel's right edge; the menu
    video behind. The text and the web page are the server's own."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for n in ('MenuBG', 'ShadedBar'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, visible=0, wide=0, tall=0)
    frame_dressing(body, video='centre')
    x0, x1, py0, py1 = 300, 1620, 330, 860
    put(body, 'RK_MotdLabel', {'ControlName': 'CExLabel', 'fieldName': 'RK_MotdLabel', 'xpos': cx(x0),
                               'ypos': u(150), 'zpos': 3, 'wide': u(800), 'tall': 12, 'visible': 1, 'enabled': 1,
                               'labelText': '//  INCOMING TRANSMISSION', 'font': 'RK_Mono12',
                               'fgcolor': '224 26 46 255', 'textAlignment': 'west', 'mouseinputenabled': 0})
    # as tall as the map briefing's title: shorter than its font, the game cut the title to "WELCO..."
    kv.setmany(kv.find(body, 'TFMessageTitle'), xpos=cx(x0), ypos=u(170), wide=u(x1 - x0), tall=u(130), zpos=3,
               font='RK_MapTitle', fgcolor=TEXT, textAlignment='west')  # no allcaps: the game sizes the title to
    # its text before the caps, and the wider capitals were cut to "WELCO..."
    put(body, 'RK_MotdRule', {'ControlName': 'ImagePanel', 'fieldName': 'RK_MotdRule', 'xpos': cx(x0),
                              'ypos': u(310), 'zpos': 3, 'wide': u(x1 - x0), 'tall': 1, 'visible': 1, 'enabled': 1,
                              'fillcolor': '224 26 46 160', 'mouseinputenabled': 0})
    put(body, 'RK_MotdPanel', {'ControlName': 'EditablePanel', 'fieldName': 'RK_MotdPanel', 'xpos': cx(x0),
                               'ypos': u(py0), 'zpos': 1, 'wide': u(x1 - x0), 'tall': u(py1 - py0), 'visible': 1,
                               'enabled': 1, 'paintborder': 1, 'border': 'RK_MMProfile',
                               'bgcolor_override': '7 6 9 200', 'PaintBackgroundType': 0, 'mouseinputenabled': 0})
    pad = 28
    blk = kv.find(body, 'TextMessage')  # a text entry: keeps no field of its own (TextEntry.BgColor is the chat's)
    if blk is not None:
        kv.set(blk, 'bgcolor_override', '0 0 0 0')
    for n in ('TFTextMessage', 'HTMLMessage'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, xpos=cx(x0 + pad), ypos=u(py0 + pad), zpos=4, wide=u(x1 - x0 - 2 * pad),
                       tall=u(py1 - py0 - 2 * pad))
    # the text's scroll bar: the armory's plain arrows and a crimson box instead of the stock chalk drawings
    kv.setmany(kv.find(body, 'TFTextMessage'), font='RK_BriefBig', fgcolor='220 216 218 255',
               image_up_arrow='scroll_up_off', image_up_arrow_mouseover='scroll_up_on',
               image_down_arrow='scroll_down_off', image_down_arrow_mouseover='scroll_down_on',
               image_line=T + 'blank', image_box=T + 'menu_item_red')  # the armory's well and box are no
    # materials outside the armory: they drew the missing-texture checks
    ok = kv.find(body, 'ok')
    if ok is not None:
        foot_button(ok, 0)
        kv.setmany(ok, xpos=cx(x1 - FOOT_W), ypos=u(py1 + 24))
        # the frame under it, always drawn: the button's own border showed only after the pointer had been on it
        put(body, 'RK_MotdOkFrame', {'ControlName': 'EditablePanel', 'fieldName': 'RK_MotdOkFrame',
                                     'xpos': cx(x1 - FOOT_W), 'ypos': u(py1 + 24), 'zpos': 7, 'wide': u(FOOT_W),
                                     'tall': u(FOOT_H), 'visible': 1, 'enabled': 1, 'paintborder': 1,
                                     'border': 'RK_Foot', 'mouseinputenabled': 0})
    hint = kv.find(body, 'OkIntroHintIcon')  # Steam Controller variant: the button glyph left of CONTINUE
    if hint is not None:
        kv.setmany(hint, xpos=cx(x1 - FOOT_W - 34), ypos=u(py1 + 24 + (FOOT_H - 25 * PX) / 2))


def mapinfo(root):
    """Map briefing before spawning, centred on the screen: the label and the map's name over the crimson rule, its
    game mode under it, the description in a glass panel, the three buttons right under the panel; the menu video
    behind."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for e in body:
        if isinstance(e[1], list) and ('bg' in e[0].lower() and (kv.get(e[1], 'ControlName') or '').lower() in
                                       ('cmodelpanel', 'ctfimagepanel', 'imagepanel')):
            kv.setmany(e[1], visible=0, wide=0, tall=0)
    for n in ('ShadedBar', 'MapImage'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, visible=0, wide=0, tall=0)
    frame_dressing(body, video='centre')
    # 0.9 (preview 30): a briefing page. Left: ■ 作戦概要 // MISSION BRIEFING, the map's name huge, its mode in
    # crimson mono over a rule, the description in a larger face. Right: the map's own picture in a framed card
    # (the game shows it when the map has one). The buttons at the foot, from the left
    kv.remove(body, 'RK_Header')
    put(body, 'RK_BriefLabel', {'ControlName': 'CExLabel', 'fieldName': 'RK_BriefLabel', 'xpos': cx(110),
                                'ypos': u(238), 'zpos': 3, 'wide': u(600), 'tall': 12, 'visible': 1, 'enabled': 1,
                                'labelText': '//  MISSION BRIEFING', 'font': 'RK_Mono12',
                                'fgcolor': '224 26 46 255', 'textAlignment': 'west'})
    kv.setmany(kv.find(body, 'MapInfoTitle'), xpos=cx(110), ypos=u(270), wide=u(900), tall=u(130),
               font='RK_MapTitle', allcaps=1, fgcolor=TEXT, textAlignment='west')
    kv.setmany(kv.find(body, 'MapInfoType'), xpos=cx(110), ypos=u(410), wide=u(760), tall=12,
               font='RK_Mono12', allcaps=1, fgcolor='224 26 46 255', textAlignment='west')
    put(body, 'RK_BriefRule', {'ControlName': 'ImagePanel', 'fieldName': 'RK_BriefRule', 'xpos': cx(110),
                               'ypos': u(452), 'zpos': 3, 'wide': u(760), 'tall': 1, 'visible': 1, 'enabled': 1,
                               'fillcolor': '224 26 46 160'})
    kv.remove(body, 'RK_BriefPanel')
    kv.setmany(kv.find(body, 'MapInfoText'), xpos=cx(110), ypos=u(480), wide=u(820), tall=u(300),
               font='RK_BriefBig', fgcolor='220 216 218 255')
    mx0, my0, ms = 1250, 220, 440
    img = kv.find(body, 'MapImage')
    if img is not None:
        for k in ('xpos_lodef', 'xpos_hidef', 'ypos_lodef', 'ypos_hidef', 'wide_hidef', 'wide_lodef', 'tall_hidef',
                  'tall_lodef'):
            kv.remove(img, k)
        kv.setmany(img, xpos=cx(mx0 + 6), ypos=u(my0 + 6), wide=u(ms - 12), tall=u(ms - 12), zpos=2, scaleImage=1)
    put(body, 'RK_MapFrame', {'ControlName': 'EditablePanel', 'fieldName': 'RK_MapFrame', 'xpos': cx(mx0),
                              'ypos': u(my0), 'zpos': 1, 'wide': u(ms), 'tall': u(ms), 'visible': 1, 'enabled': 1,
                              'paintborder': 1, 'border': 'RK_MMProfile', 'mouseinputenabled': 0})
    # each keeps its foot-row look (slot), placed CONTINUE first from the left
    for pos, (slot, n) in enumerate(((2, 'MapInfoContinue'), (1, 'MapInfoWatchIntro'), (0, 'MapInfoBack'))):
        blk = kv.find(body, n)
        if blk is not None:
            foot_button(blk, slot)
            kv.setmany(blk, xpos=cx(110 + pos * (FOOT_W + FOOT_GAP)), ypos=u(880))
