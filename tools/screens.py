"""Full-screen menus: main menu, top bar, class / team select, inventory, crafting, scoreboard, win panel."""
import os

import re

import kv

# the HUD's version (VERSION at the project root): shown small in the main menu's bottom right corner, and the
# number of the GitHub release
VERSION = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'VERSION'),
               encoding='utf-8').read().strip()

T = 'replay/thumbnails/rk/'
SCENE = '../console/background_reaper_widescreen'
TEXT = '236 232 232 255'
GREY = '138 132 138 255'
RED = '224 26 46 255'
OFF = 9999  # parks a panel off screen; code can still toggle it without it showing up
# the inventory's pages (class loadout, backpack, item picker, crafting) start this far down the screen, in units: the
# inventory's property sheet starts under the frame's title bar and its tabs take tabheight + yoffset (34) of it
# (measured in game in 0.3: the LOADOUT tab's top at 37, the class cards at 93 with class_ypos 40)
PAGE_Y = 53


def _root(root):
    return next(e[1] for e in root if isinstance(e[1], list))


def _block(name, entries):
    return [[k, v if isinstance(v, list) else str(v), None] for k, v in entries.items()]


def add(body, name, entries, first=False):
    kv.remove(body, name)
    ent = [name, _block(name, entries), None]
    if first:
        body.insert(1, ent)
    else:
        body.append(ent)


def image(name, x, y, w, h, img, z=0, drawcolor=None, **extra):
    e = {'ControlName': 'ImagePanel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': 1, 'enabled': 1, 'scaleImage': 1, 'image': img, 'mouseinputenabled': 0}
    if drawcolor:
        e['drawcolor'] = drawcolor
    e.update(extra)
    return e


def box(name, x, y, w, h, z=0, bg=None, border=None):
    e = {'ControlName': 'EditablePanel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': 1, 'enabled': 1, 'mouseinputenabled': 0}
    if bg:
        e['bgcolor_override'] = bg
        e['PaintBackgroundType'] = 0
    if border:
        e['border'] = border
        e['paintborder'] = 1
    return e


def scene_backdrop(body, z=-30, shade=150):
    """The menu scene behind a full-screen menu, dimmed so the UI on top stays readable."""
    add(body, 'RK_Scene', image('RK_Scene', 0, 0, 'f0', 480, SCENE, z=z), first=True)
    add(body, 'RK_SceneShade', image('RK_SceneShade', 0, 0, 'f0', 480, T + 'shade_full', z=z + 1,
                                     drawcolor=f'255 255 255 {shade}'), first=True)


# ------------------------------------------------------------------ main menu
# The main menu itself (and its top bar, rank card, friends) is laid out in menu.py, from the style preview.


# ------------------------------------------------------------------ HUD Settings popup
# vgui res files cannot open a new window, so the popup reuses the stock MOTD panel: the main menu code shows it on
# "motd_show" and hides it on "motd_hide". Its news widgets are parked and replaced with the layout picker.
# The two layouts are the plain / *_minmode keys of the in-game cards (ingame.py, INNER); picking one sets
# cl_hud_minmode and reloads the HUD.
LAYOUT_OPTIONS = [  # (button, preview art, cl_hud_minmode, name, description)
    ('RK_LayoutCentred', 'layout_centred', 0, 'CENTRED', 'Health and ammo either side of the crosshair (default)'),
    ('RK_LayoutMin', 'layout_minmode', 1, 'MINMODE', 'Bare numbers either side, no cards'),
]
POPUP_W, POPUP_H = 640, 414  # under the rest: the CROSSHAIR row from y 252, the KILL SOUND row from y 330
CHARACTER_OPTIONS = (('RK_Char3D', '3D MODEL', 1), ('RK_Char2D', '2D IMAGE', 0))  # cl_hud_playerclass_use_playermodel
# QUICK FIXES, the right column: console commands players look up when the game acts up, one click each
# (button, command, what it does)
QUICK_X = 376
QUICK_FIXES = [
    ('FIX SOUND', 'snd_restart', 'Stops broken, looping sounds'),
    ('RELOAD HUD', 'hud_reloadscheme', 'Fixes broken HUD colours and panels'),
    ('FIX PLAYERS', 'record fix; stop', 'Fixes invisible players and animations'),
    ('PRACTICE MAP', 'map itemtest', 'Loads itemtest, a map to practise on'),
    ('DEMO PLAYER', 'demoui', 'Opens the demo player'),
    ('RECONNECT', 'retry', 'Reconnects to the last server'),
]
# what a button runs when it is more than the command it shows: after the loadout's BLU preview (r_skin 1, see
# TEAM_PREVIEW) every model on the practice map would be drawn blue
QUICK_FIX_RUN = {'map itemtest': 'r_skin 0; map itemtest'}


def hud_settings_button(body, i, y):
    """'HUD Settings' entry at the end of the left column, drawn like the stock entries above it."""
    blk = _block('RK_HudSettingsButton', {
        'ControlName': 'CExImageButton', 'fieldName': 'RK_HudSettingsButton', 'autoResize': 0, 'visible': 1,
        'enabled': 1, 'tabPosition': 0, 'labelText': '', 'dulltext': 0, 'brighttext': 0, 'default': 1,
        'Command': 'motd_show', 'sound_depressed': 'UI/buttonclick.wav', 'sound_released': 'UI/buttonclickrelease.wav'})
    kv.remove(body, 'RK_HudSettingsButton')
    body.append(['RK_HudSettingsButton', blk, None])


def label_block(name, x, y, w, h, text, font, fg, align='west', z=2):
    return {'ControlName': 'CExLabel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
            'visible': 1, 'enabled': 1, 'labelText': text, 'textAlignment': align, 'font': font, 'fgcolor': fg}


def hud_settings_popup(motd):
    kv.setmany(motd, xpos='c-%d' % (POPUP_W // 2), ypos=34, zpos=60, wide=POPUP_W, tall=POPUP_H, border='',
               paintborder=0, PaintBackgroundType=0, bgcolor_override='0 0 0 0')
    for e in motd:
        if isinstance(e[1], list) and e[0].startswith('MOTD_') and e[0] != 'MOTD_CloseButton':
            kv.setmany(e[1], xpos=OFF, visible=0)
    kv.setmany(kv.find(motd, 'MOTD_CloseButton'), xpos=POPUP_W - 30, ypos=14, zpos=10, wide=14, tall=14)
    add(motd, 'RK_PopupBG', image('RK_PopupBG', 0, 0, POPUP_W, POPUP_H, T + 'popup', z=-1))
    add(motd, 'RK_PopupTitle', label_block('RK_PopupTitle', 22, 12, 250, 24, 'HUD SETTINGS', 'RK_Title', TEXT))
    add(motd, 'RK_PopupSection', label_block('RK_PopupSection', 22, 42, QUICK_X - 36, 12, 'HEALTH AND AMMO LAYOUT',
                                             'RK_Mono', RED))
    for i, (name, img, mode, title, desc) in enumerate(LAYOUT_OPTIONS):
        x = 22 + i * 168
        blk = _block(name, {'fieldName': name, 'visible': 1, 'enabled': 1, 'tabPosition': 0,
                            'sound_depressed': 'UI/buttonclick.wav', 'sound_released': 'UI/buttonclickrelease.wav',
                            'sound_armed': 'UI/buttonrollover.wav'})
        kv.remove(motd, name)
        motd.append([name, blk, None])
        card_button(motd, blk, img, x, 60, 160, 90, f'engine cl_hud_minmode {mode}; hud_reloadscheme')
        # the main menu runs "engine ..." commands only when they reach it: two levels up from inside MOTD_Panel,
        # like the stock close button
        kv.set(blk, 'actionsignallevel', 2)
        for suffix, y, text, font, color in (('Name', 154, title, 'RK_Menu', TEXT),
                                             ('Desc', 168, desc, 'RK_Small', GREY)):
            add(motd, name + suffix, label_block(name + suffix, x, y, 160, 12, text, font, color))
    note(motd, 'RK_PopupNote0', 184, 'Applies instantly. Same as cl_hud_minmode 0 / 1 in the console.',
         w=QUICK_X - 36)
    # PLAYER CHARACTER: the live 3D model or TF2's own 2D class art on the ID card (the game's own setting, no reload)
    add(motd, 'RK_PopupSection2', label_block('RK_PopupSection2', 22, 202, QUICK_X - 36, 12, 'PLAYER CHARACTER',
                                              'RK_Mono', RED))
    for i, (name, text, value) in enumerate(CHARACTER_OPTIONS):
        popup_button(motd, name, 22 + i * 100, 218, text, f'engine cl_hud_playerclass_use_playermodel {value}')
    note(motd, 'RK_PopupNote3', 238, 'Same as cl_hud_playerclass_use_playermodel 1 / 0 in the console.',
         w=QUICK_X - 36)
    add(motd, 'RK_PopupDivider', {'ControlName': 'ImagePanel', 'fieldName': 'RK_PopupDivider', 'xpos': QUICK_X - 14,
                                  'ypos': 44, 'zpos': 2, 'wide': 1, 'tall': 196, 'visible': 1, 'enabled': 1,
                                  'fillcolor': '224 26 46 90'})
    add(motd, 'RK_PopupSection3', label_block('RK_PopupSection3', QUICK_X, 42, POPUP_W - QUICK_X - 22, 12,
                                              'QUICK FIXES', 'RK_Mono', RED))
    for i, (text, command, desc) in enumerate(QUICK_FIXES):
        y = 60 + i * 31
        popup_button(motd, f'RK_Fix{i}', QUICK_X, y, text, f'engine {QUICK_FIX_RUN.get(command, command)}')
        for suffix, dy, label_text, color in (('Desc', -1, desc, '200 196 198 255'), ('Cmd', 9, command, RED)):
            add(motd, f'RK_Fix{i}{suffix}', label_block(f'RK_Fix{i}{suffix}', QUICK_X + 100, y + dy,
                                                        POPUP_W - QUICK_X - 118, 10, label_text, 'RK_Small', color))
    # CROSSHAIR: the HUD's own crosshairs (extras.py), across the foot under a crimson rule
    add(motd, 'RK_PopupDivider2', {'ControlName': 'ImagePanel', 'fieldName': 'RK_PopupDivider2', 'xpos': 22,
                                   'ypos': 252, 'zpos': 2, 'wide': POPUP_W - 44, 'tall': 1, 'visible': 1, 'enabled': 1,
                                   'fillcolor': '224 26 46 90'})
    import extras
    extras.crosshair_section(motd, 258, add, label_block, card_button, _block, RED, GREY, POPUP_W)
    # KILL SOUND: the Blackwall's kill sounds (blackwall.py), the build makes the pick TF2's kill sound
    add(motd, 'RK_PopupDivider3', {'ControlName': 'ImagePanel', 'fieldName': 'RK_PopupDivider3', 'xpos': 22,
                                   'ypos': 330, 'zpos': 2, 'wide': POPUP_W - 44, 'tall': 1, 'visible': 1, 'enabled': 1,
                                   'fillcolor': '224 26 46 90'})
    import blackwall
    blackwall.killsound_section(motd, 336, add, label_block, card_button, _block, RED, GREY, POPUP_W)


def popup_button(motd, name, x, y, text, command):
    """Flat black button, crimson on hover, hot crimson while pressed; actionsignallevel 2 so its "engine ..."
    command reaches the main menu."""
    add(motd, name, {
        'ControlName': 'CExButton', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': 6, 'wide': 92,
        'tall': 18, 'visible': 1, 'enabled': 1, 'tabPosition': 0, 'labelText': text, 'font': 'RK_Button',
        'textAlignment': 'center', 'Command': command, 'actionsignallevel': 2,
        'paintbackground': 1, 'defaultBgColor_override': '24 22 26 240', 'armedBgColor_override': RED,
        'depressedBgColor_override': '255 52 76 255', 'defaultFgColor_override': TEXT,
        'armedFgColor_override': '7 7 9 255', 'depressedFgColor_override': '7 7 9 255',
        'sound_depressed': 'UI/buttonclick.wav', 'sound_released': 'UI/buttonclickrelease.wav'})


def note(motd, name, y, text, x=22, w=None):
    add(motd, name, label_block(name, x, y, w or POPUP_W - x - 18, 12, text, 'RK_Small', '128 124 130 255'))


# ------------------------------------------------------------------ class select
CLASS_ORDER = [('scout', 'numScout'), ('soldier', 'numSoldier'), ('pyro', 'numPyro'), ('demoman', 'numDemoman'),
               ('heavyweapons', 'numHeavy'), ('engineer', 'numEngineer'), ('medic', 'numMedic'),
               ('sniper', 'numSniper'), ('spy', 'numSpy'), ('random', None)]


def backdrop(body, shade=150):
    """The main menu's scene, corner brackets and vertical tagline behind a full-screen menu."""
    import menu
    menu.frame_dressing(body)


def card_button(body, blk, img, x, y, w, h, command=None):
    """Card = a static ImagePanel underneath (always drawn) + the button on top whose only visual is the hover
    border. The class menu code rewrites button images, and a button's default border is not applied until its
    first state change, so the resting card cannot live on the button itself."""
    name = kv.get(blk, 'fieldName') or 'card'
    add(body, f'RK_Card_{name}', image(f'RK_Card_{name}', x, y, w, h, T + img, z=5))
    kv.setmany(blk, ControlName='CExImageButton', xpos=x, ypos=y, zpos=6, wide=w, tall=h, labelText='',
               paintbackground=0, paintborder=1, scaleImage=1, border_default='RK_Card_none',
               border_armed=f'RK_Card_{img}_h', border_selected=f'RK_Card_{img}_h', border_depressed=f'RK_Card_{img}_h',
               image_drawcolor='0 0 0 0', image_armedcolor='0 0 0 0', image_selectedcolor='0 0 0 0',
               defaultFgColor_override='0 0 0 0', armedFgColor_override='0 0 0 0',
               depressedFgColor_override='0 0 0 0', selectedFgColor_override='0 0 0 0', pinCorner=0)
    for k in ('image_default', 'image_armed', 'image_selected'):
        kv.remove(blk, k)
    if command:
        kv.set(blk, 'Command', command)
    sub = kv.find(blk, 'SubImage')
    if sub is None:
        sub = _block('SubImage', {})
        blk.append(['SubImage', sub, None])
    kv.setmany(sub, ControlName='ImagePanel', fieldName='SubImage', xpos=0, ypos=0, wide=0, tall=0, visible=0,
               image=T + 'blank')


CARD_BORDERS = ['layout_centred', 'layout_minmode', 'team_tag_blu', 'team_tag_red', 'sc_thalf_blu', 'sc_thalf_red', 'sc_trandom'] + [
    f'cs_cell_{c}' for c in ('scout', 'soldier', 'pyro', 'demoman', 'heavyweapons', 'engineer', 'medic', 'sniper',
                             'spy', 'random')]


# ------------------------------------------------------------------ team select
# ------------------------------------------------------------------ map info (intro screen before spawning)
# ------------------------------------------------------------------ inventory
def charinfo(root):
    """Inventory (loadout, backpack, crafting, trading behind it): the main menu's scene and frame. No header: the
    sheet's own tabs sit at the top, where it would go; under them a crimson hairline instead of the tan bar, and BACK
    is the other screens' foot button."""
    import menu
    body = _root(root)
    kv.set(kv.find(body, 'character_info'), 'bgcolor_override', '0 0 0 0')
    menu.frame_dressing(body)
    for n in ('BackgroundHeader', 'BackgroundFooter'):
        kv.setmany(kv.find(body, n), image=T + 'blank', visible=0, wide=0, tall=0)
    kv.setmany(kv.find(body, 'FooterLine'), image=T + 'blank', fillcolor='224 26 46 80', tall=1, ypos=424)
    line = kv.find(kv.find(body, 'Sheet') or [], 'HeaderLine')
    if line is not None:
        kv.setmany(line, image=T + 'blank', fillcolor='224 26 46 80', ypos=36, tall=1)
    back = kv.find(body, 'BackButton')
    if back is not None:
        menu.foot_button(back, 0)


HUB_W = 644                 # units: nine class cards of 68 with 4 between
HUB_CARD = (68, 136)
HUB_ROSTER_Y, HUB_SYS_Y = 22, 228
HUB_PAGES = ('ShowBackpack', 'ShowCrafting', 'ShowArmory', 'ShowTrade', 'ShowPaintkits')


def loadout_sub(root):
    """The inventory's first page, a hub in two sections: 01 OPERATIVES, the nine class cards in a glass frame (the
    game places and grows them itself from the class_* keys), and 02 SYSTEMS, the five pages (backpack, crafting,
    catalog, trading, war paints) as numbered tiles with the game's own icons in them."""
    body = _root(root)
    page = kv.find(body, 'CharInfoLoadoutSubPanel')
    for k in ('bgcolor_override', 'infocus_bgcolor_override', 'outoffocus_bgcolor_override'):
        kv.set(page, k, '0 0 0 0')
    x0 = -HUB_W // 2
    cw, ch = HUB_CARD
    cy = HUB_ROSTER_Y + 20
    # the cards: the game's row (class_ypos, class_wide_min with class_xdelta between), growing a little under the
    # mouse and staying inside the frame; the class's item count in the HUD's crimson
    kv.setmany(page, itemcountcolor='224 26 46 255', itemcountcolor_noitems='138 132 138 255', class_ypos=cy + 6,
               class_wide_min=cw, class_xdelta=4, class_tall_min=ch, class_wide_max=cw + 6, class_tall_max=ch + 12,
               selectlabely_default=9999, selectlabely_onchanges=9999)
    for i, btn in enumerate(('scout', 'soldier', 'pyro', 'demoman', 'heavyweapons', 'engineer', 'medic', 'sniper', 'spy')):
        kv.setmany(kv.find(body, btn), xpos=f'c{x0 + i * (cw + 4)}', ypos=cy + 6, wide=cw, tall=ch, scaleImage=1,
                   activeimage=T + f'inv_{btn}_a', inactiveimage=T + f'inv_{btn}')
    add(body, 'RK_HubStrip1', image('RK_HubStrip1', f'c{x0}', HUB_ROSTER_Y, HUB_W, 14, T + 'hub_strip_roster', z=2))
    add(body, 'RK_HubFrame', image('RK_HubFrame', f'c{x0 - 6}', cy, HUB_W + 12, ch + 12, T + 'hub_frame', z=1))
    # the game's "select a class" line is the strip's own now (off screen); in a match, "changes take effect on
    # respawn" sits under the frame in small crimson (it lay across the cards' tops); under it the name and item
    # count the game shows for the card or page under the mouse
    foot = cy + ch + 14
    kv.setmany(kv.find(body, 'LoadoutChangesLabel'), font='RK_Small', allcaps=1, zpos=150, ypos=foot,
               fgcolor_override='224 26 46 255', tall=10)
    for n, font, y in (('ClassLabel', 'RK_FootText', foot + 10), ('ItemsLabel', 'RK_Small', foot + 21)):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, font=font, ypos=y, tall=12)
    kv.setmany(kv.find(body, 'ShowExplanationsButton'), xpos=f'c{-x0 - 18}', ypos=1, wide=18, tall=18)
    # 02: the pages, a tile behind each icon, its name in the tile's foot
    add(body, 'RK_HubStrip2', image('RK_HubStrip2', f'c{x0}', HUB_SYS_Y, HUB_W, 14, T + 'hub_strip_systems', z=2))
    tw, th, ty = 112, 88, HUB_SYS_Y + 20
    gap = (HUB_W - 5 * tw) // 4
    for i, n in enumerate(HUB_PAGES):
        tx = x0 + i * (tw + gap)
        add(body, f'RK_HubTile{i + 1}', image(f'RK_HubTile{i + 1}', f'c{tx}', ty, tw, th, T + f'hub_tile_{i + 1}', z=1))
        btn = kv.find(body, n + 'Button')
        if btn is not None:
            kv.setmany(btn, xpos=f'c{tx + (tw - 52) // 2}', ypos=ty + 13, wide=52, tall=52)
        lbl = kv.find(body, n + 'Label')
        if lbl is not None:
            kv.setmany(lbl, font='RK_FootText', allcaps=1, fgcolor_override='236 232 232 255')


def overlay_page(name):
    """Sub-pages drawn over the class grid: must stay opaque, so they carry their own copy of the scene, placed as the
    inventory's own (menu.frame_dressing: right-aligned, 16:9, the screen's height) so it does not jump between pages."""
    def patch(root):
        body = _root(root)
        blk = kv.find(body, name)
        for k in ('bgcolor_override', 'infocus_bgcolor_override', 'outoffocus_bgcolor_override'):
            if kv.get(blk, k) is not None:
                kv.set(blk, k, '7 7 9 255')
        add(body, 'RK_Scene', image('RK_Scene', 'rs1', -PAGE_Y, 'o1.778', 480, SCENE, z=-30), first=True)
        # 225: the designed 48 % dimming through shade_full's linear-light corrected black (see menu.frame_dressing)
        add(body, 'RK_SceneShade', image('RK_SceneShade', 0, -PAGE_Y, 'f0', 480, T + 'shade_full', z=-29,
                                         drawcolor='255 255 255 225'), first=True)
    return patch


# the loadout shows every class in RED; these switch the preview between the teams (loadout.class_loadout). r_skin
# forces a model skin (0: off, the RED default; 1: BLU) and is a cheat setting, so the button turns sv_cheats on
# first: that works when no match is running (a server keeps its own sv_cheats), and joining a match turns cheat
# settings back off by itself
TEAM_PREVIEW = (('RK_TeamBlu', 'team_tag_blu', 'BLU', 'sv_cheats 1; r_skin 1'),
                ('RK_TeamRed', 'team_tag_red', 'RED', 'sv_cheats 1; r_skin 0'))


def tag_button(body, name, img, x, y, w, h, text, command):
    """Small card button with a label the game draws in the HUD's menu font: the card is a static image underneath
    and its hover art the armed border, as in card_button."""
    add(body, name + 'Card', image(name + 'Card', x, y, w, h, T + img, z=5))
    add(body, name, {
        'ControlName': 'CExButton', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': 6, 'wide': w, 'tall': h,
        'visible': 1, 'enabled': 1, 'tabPosition': 0, 'labelText': text, 'font': 'RK_Menu',
        'textAlignment': 'center', 'Command': command, 'paintbackground': 0, 'paintborder': 1,
        'border_default': 'RK_Card_none', 'border_armed': f'RK_Card_{img}_h', 'border_depressed': f'RK_Card_{img}_h',
        'defaultFgColor_override': '236 232 232 255', 'armedFgColor_override': '255 255 255 255',
        'depressedFgColor_override': '224 26 46 255', 'sound_depressed': 'UI/buttonclick.wav',
        'sound_released': 'UI/buttonclickrelease.wav', 'sound_armed': 'UI/buttonrollover.wav'})


# ------------------------------------------------------------------ backpack, item selection, crafting
INK_BUTTON = {  # flat ink, crimson on hover, bright crimson while pressed (the HUD Settings popup's buttons)
    'paintbackground': 1, 'defaultBgColor_override': '16 16 18 235', 'armedBgColor_override': '160 18 34 255',
    'depressedBgColor_override': '224 26 46 255', 'selectedBgColor_override': '160 18 34 255',
    'defaultFgColor_override': '236 232 232 255', 'armedFgColor_override': '255 255 255 255',
    'depressedFgColor_override': '7 7 9 255', 'selectedFgColor_override': '255 255 255 255',
    'disabledfgcolor2_override': '96 92 98 255',
    # 0.9: the frame over the fill (extras.ink_button_art): a hot tab on the left, the cut corner
    'paintborder': 1, 'border_default': 'RK_InkBtn', 'border_armed': 'RK_InkBtn_h', 'border_depressed': 'RK_InkBtn_h',
    'border_selected': 'RK_InkBtn_h'}  # the scheme draws disabled text black: ash instead
CRIMSON = '224 26 46 255'
SEARCH_H = 21
SEARCH_CHIP = 25  # manga.search_bar's magnifier chip (about square) plus a gap: the typed text starts after it


def ink_button(blk, font='RK_Menu', main=False):
    """A stock button in the HUD's flat ink style; main: the page's main action, deep crimson at rest."""
    if blk is None:
        return
    kv.setmany(blk, **INK_BUTTON)
    if font:
        kv.set(blk, 'font', font)
    if main:
        kv.set(blk, 'defaultBgColor_override', '44 6 12 240')


DIALOG_FILE = re.compile(r'resource/ui/(econ/)?(confirm\w*|itemrename\w*|genericwaitingdialog|tradingstartdialog|'
                         r'strangecounttransferdialog)\.res$')


def confirm_dialog(root):
    """0.9 (preview 29): the confirm / rename / waiting dialogs as the HUD's cards: the vote panels' black glass page
    with its crimson frame, the title in the HUD's face, every button flat ink with the hot tab (ink_button),
    CONFIRM-like actions (OK / apply / abandon) lit."""
    body = _root(root)
    for k, v, *_ in body:
        if not isinstance(v, list):
            continue
        ctl = (kv.get(v, 'ControlName') or '').lower()
        if ctl in ('frame', 'editablepanel') and v is body[0][1]:
            kv.setmany(v, paintbackground=0, PaintBackgroundType=0, border='RK_MSList_red', paintborder=1)
    def visit(node):
        for k, v, *_ in node:
            if not isinstance(v, list):
                continue
            ctl = (kv.get(v, 'ControlName') or '').lower()
            if ctl in ('cexbutton', 'button'):
                main = any(w in k.lower() for w in ('ok', 'confirm', 'apply', 'abandon', 'accept', 'yes'))
                ink_button(v, main=main)
            elif ctl == 'cexlabel' and 'title' in k.lower():
                kv.setmany(v, font='RK_Title', fgcolor='236 232 232 255')
            visit(v)
    visit(body)


def search_field(body, cx, y, w):
    """The game's name filter (NameFilterTextEntry: the code reads what is typed there) on a search strip
    (manga.search_bar): the strip carries the magnifier, the field sits right of it, see-through, typing in white.
    Its 'Search:' label stays, as a small crimson caption above. cx: units from the screen centre."""
    add(body, 'RK_SearchBar', image('RK_SearchBar', f'c{cx}', y, w, SEARCH_H, T + 'search_bar', z=1))
    kv.setmany(kv.find(body, 'NameFilterTextEntry'), xpos=f'c{cx + SEARCH_CHIP}', ypos=y + 3, zpos=3,
               wide=w - SEARCH_CHIP - 6, tall=SEARCH_H - 6, font='RK_Menu', fgcolor_override='236 232 232 255',
               bgcolor_override='0 0 0 0', paintbackgroundtype=0, paintborder=0)
    kv.setmany(kv.find(body, 'NameFilterLabel'), xpos=f'c{cx + 2}', ypos=y - 11, zpos=1, wide=90, tall=10,
               autoResize=0, font='RK_Small', fgcolor=CRIMSON)


def field_strip(body, name, cx, y, w, h):
    """The search strip without its magnifier, behind a drop-down menu."""
    add(body, name, image(name, f'c{cx}', y, w, h, T + 'search_field', z=0))


def backpack(root):
    """Backpack: the scene backdrop (an opaque page over the class grid), the search strip, the drop-down menus on
    ink strips, flat ink page chips. The page chips' text colour is the game's (by how full each page is: near black
    when empty, tan when partly full, white when full) and the current page's fill is the scheme's TFOrange (deep
    crimson): an ash chip keeps all three readable."""
    overlay_page('backpack_panel')(root)
    body = _root(root)
    search_field(body, 137, 14, 133)
    for name, combo, (cx, w) in (('RK_RarityField', 'ShowRarityComboBox', (-90, 214)),
                                 ('RK_SortField', 'SortByComboBox', (132, 159))):
        field_strip(body, name, cx, 35, w, 19)
        kv.setmany(kv.find(body, combo), zpos=2, fgcolor_override='236 232 232 255',
                   selectionTextColor_override='236 232 232 255', disabledFgColor_override='236 232 232 255')
    kv.setmany(kv.find(body, 'ShowBaseItemsCheckbox'), Font='RK_Menu', textAlignment='west')
    kv.set(kv.find(body, 'CaratLabel'), 'fgcolor_override', CRIMSON)
    chip = kv.find(kv.find(kv.find(body, 'backpack_panel'), 'pagebuttons_kv'), 'Button')
    kv.setmany(chip, PaintBackgroundType=0, paintborder=0, defaultBgColor_override='58 56 60 255',
               armedBgColor_override='160 18 34 255', depressedBgColor_override='224 26 46 255',
               selectedBgColor_override='160 18 34 255')
    for n in ('ShowExplanationsButton', 'CancelApplyToolButton', 'DragToNextPageButton', 'DragToPrevPageButton'):
        ink_button(kv.find(body, n), font=None if n.startswith('Drag') else 'RK_Menu')


def item_selection(root):
    """Picking an item for a loadout slot or a crafting blueprint: full-screen page over the loadout / crafting
    page, so the same scene backdrop; search strip, crimson rules for the dotted tan lines, ink buttons."""
    overlay_page('ItemSelectionPanel')(root)
    body = _root(root)
    search_field(body, 160, 14, 140)
    kv.set(kv.find(body, 'ItemSlotLabel'), 'wide', 210)  # was 375: its box ran under the search field
    for n, y in (('TopLine', 44), ('BottomLine', 334)):
        kv.setmany(kv.find(body, n), ypos=y, tall=1, image=T + 'blank', fillcolor='224 26 46 80', tileImage=0)
    for n in ('CaratLabel', 'CurPageLabel'):
        kv.set(kv.find(body, n), 'fgcolor_override', CRIMSON)
    kv.setmany(kv.find(body, 'OnlyAllowUniqueQuality'), Font='RK_Menu')
    for n in ('CancelButton', 'ShowBackpack', 'ShowSelection', 'PrevPageButton', 'NextPageButton'):
        ink_button(kv.find(body, n))


# crafting page, in units from the screen centre: the recipe list's card on the left (heading, the four category
# icons, the list), the chosen blueprint's card on the right (inside its container, which the game shows only
# while a blueprint is chosen)
CRAFT_LIST = (-306, 4, 302, 362)  # x, y, w, h
CRAFT_ICON, CRAFT_ICON_GAP, CRAFT_ICON_X, CRAFT_ICON_Y = 26, 12, -290, 32
CRAFT_ROW = 15  # recipe row height (the game spaces rows by this plus 2)
CRAFT_PAD = 14  # the blueprint card's inner margin


def crafting(root):
    overlay_page('crafting_panel')(root)
    body = _root(root)
    panel = kv.find(body, 'crafting_panel')
    x, y, w, h = CRAFT_LIST
    add(body, 'RK_CraftListCard', image('RK_CraftListCard', f'c{x}', y, w, h, T + 'craft_list', z=-5))
    kv.setmany(kv.find(body, 'ClassLabel'), xpos='c-290', ypos=10, wide=280, tall=18, font='RK_NoticeTitle',
               textAlignment='north-west', fgcolor_override='236 232 232 255')
    # the four category buttons: the game places them at filter_xoffset + (size + filter_xdelta) * i from the centre
    kv.setmany(panel, filter_xoffset=CRAFT_ICON_X, filter_ypos=CRAFT_ICON_Y, filter_xdelta=CRAFT_ICON_GAP)
    kv.setmany(kv.find(panel, 'recipefilterbuttons_kv'), wide=CRAFT_ICON, tall=CRAFT_ICON, zpos=3)
    for i in range(4):
        cx = CRAFT_ICON_X + (CRAFT_ICON + CRAFT_ICON_GAP) * i - 4
        add(body, f'RK_CraftChip{i}', image(f'RK_CraftChip{i}', f'c{cx}', CRAFT_ICON_Y - 4, CRAFT_ICON + 8,
                                           CRAFT_ICON + 8, T + 'craft_chip', z=1))
    # the recipe list: rows like the main menu's (hairline at rest, crimson wash and edge on hover). The chosen one
    # is held pressed by the game, and CExButton has no pressed-state border: a deep crimson fill and crimson text
    kv.setmany(kv.find(body, 'recipecontainerscroller'), ypos=72, tall=284)
    kv.set(kv.find(body, 'recipecontainer'), 'tall', 284)
    rows = kv.find(panel, 'recipebuttons_kv')
    kv.setmany(rows, font='RK_Menu', tall=CRAFT_ROW, textinsetx=10, use_proportional_insets=1, paintbackground=1,
               paintborder=1, border_default='RK_Nav', border_armed='RK_NavArmed',
               defaultFgColor_override='206 202 204 255', defaultBgColor_override='0 0 0 0',
               armedFgColor_override='255 255 255 255', armedBgColor_override='0 0 0 0',
               depressedFgColor_override=CRIMSON, depressedBgColor_override='70 8 18 230',
               disabledfgcolor2_override='96 92 98 255')
    for k in ('border_depressed', 'border_selected'):
        kv.remove(rows, k)
    # the chosen blueprint: the container grows by the card's margin, everything in it moves in by it
    sel = kv.find(body, 'selectedrecipecontainer')
    kv.setmany(sel, xpos='c0', ypos=4, wide=316, tall=362)
    add(sel, 'RK_CraftRecipeCard', image('RK_CraftRecipeCard', 0, 0, 316, 362, T + 'craft_recipe', z=-1))
    P = CRAFT_PAD
    kv.setmany(kv.find(sel, 'RecipeTitle'), xpos=P, ypos=8, wide=316 - 2 * P, tall=36, font='RK_NoticeTitle',
               fgcolor='236 232 232 255')
    kv.setmany(kv.find(sel, 'RecipeInputStringLabel'), xpos=P, ypos=54, wide=316 - 2 * P, fgcolor='206 202 204 255')
    kv.setmany(kv.find(sel, 'InputLabel'), xpos=P, ypos=78, tall=14, font='RK_Menu', fgcolor=CRIMSON)
    kv.setmany(kv.find(sel, 'OutputLabel'), xpos=P, ypos=246, tall=14, font='RK_Menu', fgcolor=CRIMSON)
    # item slots: the game lays them out from the container's left edge, at item_ypos / output_item_ypos
    kv.setmany(panel, item_crafting_offcenter_x=P, item_ypos=94, output_item_ypos=262)
    kv.setmany(kv.find(sel, 'CraftButton'), xpos=P, ypos=320, wide=186, tall=30, font='RK_NoticeTitle', textinsetx=0)
    ink_button(kv.find(sel, 'CraftButton'), font='RK_NoticeTitle', main=True)
    kv.setmany(kv.find(sel, 'FreeAccountLabel'), xpos=P, ypos=320)
    kv.setmany(kv.find(sel, 'UpgradeButton'), xpos=P + 192, ypos=322, wide=316 - 2 * P - 192, textinsetx=0)
    ink_button(kv.find(sel, 'UpgradeButton'))  # was olive green
    tip = kv.find(body, 'TooltipPanel')  # the category icons' hover text
    kv.setmany(kv.find(tip, 'TipLabel'), font='RK_Menu', fgcolor_override='236 232 232 255')


def crafting_dialog(root):
    """"Crafting..." / "New blueprint found" popups: the game's orange-red text in the HUD's colours."""
    body = _root(root)
    for e in body:
        if isinstance(e[1], list) and (kv.get(e[1], 'fgcolor_override') or '').startswith('200 80 60'):
            kv.set(e[1], 'fgcolor_override', CRIMSON)
    for e in body:
        if isinstance(e[1], list) and (kv.get(e[1], 'ControlName') or '').lower() == 'cexbutton':
            ink_button(e[1])


# ------------------------------------------------------------------ scoreboard
def scoreboard(root):
    body = _root(root)
    # our header font is wider than TF2 Secondary: give "Ping" room so it is not cut to "Pi..."
    kv.setmany(kv.find(body, 'scores'), ping_width=26, name_width=107)
    # one page for the body (dot grid, faint 死神 between the teams)
    kv.setmany(kv.find(body, 'MainBG'), border='RK_ScoreMain')
    for n in ('BlueScoreBG', 'RedScoreBG', 'BlueTeamImage', 'RedTeamImage'):
        kv.setmany(kv.find(body, n), wide=0, tall=0, image=T + 'blank')
    add(body, 'RK_BlueHead', image('RK_BlueHead', -8, -2, 292, 73, T + 'score_blue', z=0))
    add(body, 'RK_RedHead', image('RK_RedHead', 356, -2, 292, 73, T + 'score_red', z=0))

    # the game only shows the team names in tournament mode (small, under the count then); the player count takes
    # the name's place, big, beside the 青 / 赤 stamp. zpos above the banner art (same zpos drew them under it)
    kv.setmany(kv.find(body, 'BlueTeamLabel'), visible=1, xpos=10, ypos=42, wide=142, tall=14, zpos=5,
               font='ScoreboardTeamCountNew', textAlignment='west', fgcolor='128 124 130 255')
    kv.setmany(kv.find(body, 'BlueTeamPlayerCount'), xpos=10, ypos=18, wide=142, tall=24, zpos=5, font='RK_Title',
               textAlignment='west', fgcolor='236 232 232 255')
    kv.setmany(kv.find(body, 'BlueTeamScore'), xpos=170, ypos=6, wide=96, tall=56, font='RK_ScoreBig',
               textAlignment='east', fgcolor='112 164 232 255')
    kv.setmany(kv.find(body, 'BlueTeamScoreDropshadow'), xpos=171, ypos=7, wide=96, tall=56, font='RK_ScoreBig',
               textAlignment='east', fgcolor='0 0 0 200')
    kv.setmany(kv.find(body, 'RedTeamLabel'), visible=1, xpos=488, ypos=42, wide=142, tall=14, zpos=5,
               font='ScoreboardTeamCountNew', textAlignment='east', fgcolor='128 124 130 255')
    kv.setmany(kv.find(body, 'RedTeamPlayerCount'), xpos=488, ypos=18, wide=142, tall=24, zpos=5, font='RK_Title',
               textAlignment='east', fgcolor='236 232 232 255')
    kv.setmany(kv.find(body, 'RedTeamScore'), xpos=374, ypos=6, wide=96, tall=56, font='RK_ScoreBig',
               textAlignment='west', fgcolor='255 120 104 255')
    kv.setmany(kv.find(body, 'RedTeamScoreDropshadow'), xpos=375, ypos=7, wide=96, tall=56, font='RK_ScoreBig',
               textAlignment='west', fgcolor='0 0 0 200')

    kv.setmany(kv.find(body, 'TimerBG'), xpos=280, ypos=4, wide=80, tall=48, border='RK_TornTag')
    kv.setmany(kv.find(body, 'ServerTimeLeftInsetBG'), wide=0, tall=0)
    kv.setmany(kv.find(body, 'ServerTimeLeftLabel'), xpos=280, ypos=10, wide=80, tall=10, fgcolor='128 124 130 255')
    kv.setmany(kv.find(body, 'ServerTimeLeftValue'), xpos=280, ypos=22, wide=80, tall=24,
               fgcolor='236 232 232 255')
    line = kv.find(body, 'VerticalLine')  # crimson hairline between the teams
    kv.remove(line, 'fillcolor')
    kv.setmany(line, visible=1, image=T + 'rule_v', scaleImage=1, xpos=313, wide=14, ypos=72, tall=276)
    kv.setmany(kv.find(body, 'PlayerNameBG'), border='RK_TornTag')
    # tighter rows: 12 players per team fit without the stock grey scroll bar
    for n in ('BluePlayerList', 'RedPlayerList'):
        kv.set(kv.find(body, n), 'linespacing', 16)
    # the local player block moves up 8 so the 4th stats row clears the page's bottom edge; the server / map
    # text ends before the tag's slanted right end; the class model sits lower, clear of the last list row
    for n, y in (('PlayerNameBG', 364), ('PlayerNameLabel', 369), ('ServerLabelNew', 367), ('MapName', 377),
                 ('LocalPlayerStatsPanel', 387), ('LocalPlayerDuelStatsPanel', 387), ('ShadedBar', 364),
                 ('Spectators', 345), ('SpectatorsInQueue', 337)):
        blk = kv.find(body, n)
        if blk is not None:
            kv.set(blk, 'ypos', y)
    for n in ('ServerLabelNew', 'MapName'):
        kv.set(kv.find(body, n), 'wide', 245)
    kv.setmany(kv.find(body, 'classmodelpanel'), xpos=-6, ypos=205, wide=118, tall=240)
    # 2D mode (cl_hud_playerclass_use_playermodel 0) shows the class art instead, where the model stands
    kv.setmany(kv.find(body, 'ClassImage'), xpos=4, ypos=332, wide=108, tall=108)
    # the tag's left edge slants in ~17 at the top: the name starts inside it
    kv.set(kv.find(body, 'PlayerNameLabel'), 'xpos', 130)


def winpanel(root):
    """End-of-round win panel. The game re-sets the stock team borders on its panels every round, so they drop to
    zpos -1 at zero size and our art takes their place: a black glass page (ROUND OVER in its corner), the team
    heads behind the scores, crimson rules instead of the grey lines."""
    body = _root(root)
    kv.setmany(kv.find(body, 'WinPanelBGBorder'), zpos=-1, wide=0, tall=0)  # the page is see-through: no stock box
    add(body, 'RK_WinPage', image('RK_WinPage', 7, 66, 286, 190, T + 'win_page', z=0))
    scores = kv.find(body, 'TeamScoresPanel')
    for n, img, x in (('BlueScoreBG', 'score_blue', 46), ('RedScoreBG', 'score_red', 193)):
        kv.setmany(kv.find(scores, n), zpos=-1, wide=0, tall=0)
        add(scores, 'RK_' + n, image('RK_' + n, x, 11, 143, 48, T + img, z=0))
    for n in ('HorizontalLine', 'HorizontalLine2'):
        blk = kv.find(body, n)
        kv.remove(blk, 'fillcolor')
        kv.setmany(blk, image=T + 'notice_rule', scaleImage=1, ypos=int(kv.get(blk, 'ypos')) - 2, tall=5)
    # a light shade on purpose: solid ink here turned the lower half of the see-through page into a black box (and
    # the bottom-center cards still showed through it, only darker)
    kv.set(kv.find(body, 'ShadedBar'), 'fillcolor', '0 0 0 70')
    # 0.9: RED WINS large, the reason and details under it
    for n in ('WinningTeamLabel', 'AdvancingTeamLabel'):
        kv.setmany(kv.find(body, n), font='RK_WinBig', ypos=68, tall=30)
    for n in ('WinningTeamLabelDropshadow', 'AdvancingTeamLabelDropshadow'):
        kv.setmany(kv.find(body, n), font='RK_WinBig', ypos=69, tall=30, fgcolor='224 26 46 200')
    kv.setmany(kv.find(body, 'WinReasonLabel'), ypos=95)
    kv.setmany(kv.find(body, 'DetailsLabel'), ypos=105)


# ------------------------------------------------------------------ loading screen
def statsummary(root):
    """Map loading / performance report: the menu scene behind it instead of the class poster art."""
    body = _root(root)
    kv.setmany(kv.find(body, 'MainBackground'), wide=0, tall=0, visible=0)
    backdrop(body, shade=175)
    kv.setmany(kv.find(body, 'TitleBanner'), image=T + 'blank', tall=0)
    add(body, 'RK_LoadLogo', image('RK_LoadLogo', 25, 29, 251, 56, T + 'mm_logo', z=2))
    kv.setmany(kv.find(body, 'MapLabel'), font='RK_Title', fgcolor='236 232 232 255')
    kv.setmany(kv.find(body, 'OnYourWayLabel'), fgcolor='224 26 46 255')
    kv.setmany(kv.find(body, 'MapType'), fgcolor='128 124 130 255')
