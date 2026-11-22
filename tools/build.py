"""Builds the Reaper HUD.

    python build.py                     -> rebuilds the HUD in the project folder itself
    python build.py --install           -> also installs it into tf/custom
    python build.py --stock DIR         -> takes the game's stock UI files from DIR (an extracted copy, such as the
                                           repository's "stock" branch) instead of TF2's VPKs

The project folder is the HUD: resource/, scripts/, materials/ and info.vdf sit at its root, so the folder (a
GitHub ZIP or a clone) works when dropped straight into tf/custom. tools/, docs/ and update.bat are ignored by the game.

The HUD is derived from the game's own current UI files (extracted from tf2_misc_dir.vpk at build time),
re-skinned through the scheme and patched where the layout changes. Only files that differ from stock are shipped.
"""
import colorsys
import json
import os
import re
import shutil
import sys
import tempfile

import numpy as np
from PIL import Image

import kv
import vpk
import term
import build_art
import blackwall
import extras
import ingame
import minmode
import loadout
import menu
import screens

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)  # the project folder is the HUD
HUD_NAME = 'reaper-hud'
HUD_PARTS = ('resource', 'scripts', 'materials', 'sound', 'media', 'cfg', 'info.vdf')  # what the build owns in the project folder
MUSIC = os.path.join(OUT, 'music', 'menu.mp3')  # the main menu's music (see menu_music)
VIDEO_JSON = os.path.join(OUT, 'video', 'menu_video.json')  # the main menu's animated background (tools/video.py)
STILL = os.path.join(OUT, 'video', 'menu_still.jpg')  # one frame of it, for the loading screens
RK_DIR = os.path.join(OUT, 'materials', 'vgui', 'replay', 'thumbnails', 'rk')
VIDEO_PARTS = ('mm_video', 'mm_video_b', 'mm_video_c')  # its textures, which tools/video.py writes into RK_DIR
INTRO = os.path.join(OUT, 'media', 'valve.webm')  # the game's startup video, which tools/intro.py writes there
IN_CUSTOM = os.path.basename(os.path.dirname(OUT)).lower() == 'custom'
if IN_CUSTOM:  # the game folder is known for sure: <tf>/custom/<this folder>
    vpk.TF = os.path.dirname(os.path.dirname(OUT))
T = 'replay/thumbnails/rk/'

# ------------------------------------------------------------------ palette
C = {
    'RK_Text': '236 232 232 255',
    'RK_TextDim': '236 232 232 150',
    'RK_TextMid': '200 196 198 255',
    'RK_Grey': '138 132 138 255',
    'RK_GreyDim': '138 132 138 120',
    'RK_Ink': '7 7 9 255',
    'RK_InkSoft': '7 7 9 200',
    'RK_Shadow': '0 0 0 190',
    'RK_Red': '224 26 46 255',
    'RK_RedDim': '224 26 46 110',
    'RK_RedGhost': '224 26 46 170',
    'RK_RedDeep': '52 6 14 255',
    'RK_Hot': '255 52 76 255',
    'RK_Pink': '255 200 206 255',
    'RK_Amber': '255 196 48 255',
    # team colours stay apart from the HUD's own crimson: RED a warm coral, BLU a steel blue
    'RK_TeamRed': '255 120 104 255',
    'RK_TeamBlue': '112 164 232 255',
    # kill feed names: deep enough to read on your own (light) rows too
    'RK_FeedRed': '214 52 56 255',
    'RK_FeedBlue': '60 116 214 255',
}

SCHEME_COLORS = {
    'Orange': '224 26 46 255', 'OrangeDim': '224 26 46 120', 'LightOrange': '255 90 104 128',
    'GoalOrange': '255 80 96 255', 'TFOrange': '60 8 16 255', 'Purple': '110 104 110 255',
    'White': '236 232 232 255', 'Yellow': '236 232 232 255', 'TransparentYellow': '236 232 232 140',
    'BrightYellow': '236 232 232 255', 'GreenSolid': '224 26 46 255',
    'Black': '9 9 11 255', 'TransparentBlack': '5 5 7 215', 'TransparentLightBlack': '0 0 0 110',
    'FooterBGBlack': '8 8 10 255',
    'HUDBlueTeam': '88 122 172 127', 'HUDRedTeam': '176 60 62 127', 'HUDSpectator': '110 108 112 127',
    'HUDBlueTeamSolid': '88 122 172 255', 'HUDRedTeamSolid': '176 60 62 255',
    'HUDDeathWarning': '255 52 76 255', 'HudOffWhite': '214 210 212 255', 'HudBlack': '14 14 16 255',
    'HudPanelForeground': '10 10 12 200', 'HudPanelBackground': '10 10 12 200', 'HudPanelBorder': '255 255 255 40',
    'HudProgressBarActive': '236 232 232 255', 'HudProgressBarInActive': '58 56 60 255',
    'HudProgressBarActiveLow': '255 52 76 255', 'HudProgressBarInActiveLow': '255 52 76 99',
    'HudTimerProgressActive': '236 232 232 255', 'HudTimerProgressInActive': '28 28 30 255',
    'HudTimerProgressWarning': '255 52 76 255', 'HudTrainingHint': '224 26 46 255',
    'TanDark': '112 108 112 255', 'TanLight': '236 232 232 255', 'TanDarker': '14 14 16 255',
    'StoreDarkTan': '58 56 60 255', 'StoreGreen': '120 16 30 255', 'SaleGreen': '120 16 30 255',
    'LowHealthRed': '255 52 76 255', 'ProgressOffWhite': '236 232 232 255', 'ProgressBackground': '255 255 255 36',
    'HealthBgGrey': '36 34 38 255', 'ProgressOffWhiteTransparent': '236 232 232 128',
    'LabelDark': '12 12 14 255', 'LabelTransparent': '18 18 20 200', 'BuildMenuActive': '236 232 232 255',
    'MatchmakingDialogTitleColor': '236 232 232 255', 'MatchmakingMenuItemBackground': '12 12 14 255',
    'MatchmakingMenuItemBackgroundActive': '60 8 16 255', 'MatchmakingMenuItemTitleColor': '236 232 232 255',
    'MatchmakingMenuItemDescriptionColor': '160 156 160 255', 'HTMLBackground': '14 14 16 255',
    'ItemAttribLevel': '112 108 112 255', 'ItemAttribNeutral': '236 232 232 255', 'ItemFlags': '112 108 112 255',
    'LightRed': '180 50 60 255', 'LighterRed': '210 70 80 255', 'LighterDarkBrown': '22 22 24 255',
    'DarkBrown': '12 12 14 255',
    'UpgradeDefaultFg': '58 56 60 255', 'UpgradeDefaultBg': '80 78 82 255',
    'UpgradeArmedFg': '90 10 22 255', 'UpgradeArmedBg': '224 26 46 255',
    'UpgradeDepressedFg': '110 12 26 255', 'UpgradeDepressedBg': '255 52 76 255',
    'UpgradeSelectedFg': '110 12 26 255', 'UpgradeSelectedBg': '255 52 76 255',
    'UpgradeDisabledFg': '40 40 42 255', 'UpgradeDisabledBg': '52 52 54 255',
}
KEEP_COLOR = re.compile(r'Quality|Rarity|PartyMember|Halloween|Quest|ItemSet|ItemIsotope|ItemBundle|ItemLimited|'
                        r'Attrib(Positive|Negative)|Disguise|Team(Red|Blue|Spec)|Credits|ForTesting', re.I)


def retint(val):
    """Tan / brown / orange family -> neutral grey or crimson. Everything else untouched."""
    m = re.fullmatch(r'\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})(?:\s+(\d{1,3}))?\s*', val)
    if not m:
        return val
    r, g, b = (int(m.group(i)) for i in (1, 2, 3))
    if max(r, g, b) > 255:
        return val
    a = m.group(4)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = h * 360
    if not (10 <= hue <= 52 and s >= 0.07):
        return val
    if s > 0.55 and v > 0.5:
        k = min(1.0, v / 0.84)
        nr, ng, nb = (round(c * k) for c in (224, 26, 46))
    else:
        l = round(0.299 * r + 0.587 * g + 0.114 * b)
        l = round(l * 0.92)  # a touch darker, a hint of red in the grey
        nr, ng, nb = l, max(0, l - 3), l
    return f'{nr} {ng} {nb}' + (f' {a}' if a is not None else '')


# ------------------------------------------------------------------ fonts
# shipped with the HUD (resource/fonts, SIL OFL): the game loads them through CustomFontFiles
SHIPPED_FONTS = ('Rajdhani-Bold.ttf', 'Rajdhani-SemiBold.ttf', 'ShareTechMono-Regular.ttf', 'Tektur-SemiBold.ttf')
# the in-game text face: chat, kill feed, the scoreboard, voice menu, target ID. Tektur (shipped, SIL OFL; a static
# 600 weight cut of the variable font, family "Tektur SemiBold"): cut corners, more cyberpunk than Bahnschrift,
# and it has Cyrillic, so Russian names do not come out as boxes
GAME_FACE = 'Tektur SemiBold'
FONT_REMAP = {
    'tf2 build': 'Rajdhani',
    'tf2 secondary': 'Bahnschrift SemiCondensed',
    'tf2': 'Bahnschrift SemiCondensed',
    'tf2 professor': 'Bahnschrift SemiCondensed',
}
# FONT_REMAP leaves Verdana alone, and these stock fonts are Verdana on every screen of 600+ lines: the chat kept
# the stock look at 900p / 1080p
CHAT_FONTS = ('ChatFont', 'ChatMiniFont')
# the rest of the in-game text the game draws in Verdana / Arial / Tahoma: players said the scoreboard kept the classic
# lettering. "Default" is the scoreboard's player names (the game picks it in code), the others its stat lines, the
# timer's sub line, target ID, hints, the spectator bar and the trackers. Only the face changes, each size stays
STOCK_FACES = ('verdana', 'arial', 'tahoma')
# the scoreboard's own stock fonts (TF2 Secondary, so Bahnschrift through FONT_REMAP): headers, team counts, names
SCOREBOARD_FONTS = ('ScoreboardMedium', 'ScoreboardMediumSmall', 'ScoreboardSmall', 'ScoreboardTeamCountNew',
                    'ScoreboardTeamName')
STOCK_FACE_FONTS = ('Default', 'DefaultSmall', 'DefaultVerySmall', 'ScoreboardVerySmall', 'ScoreboardSmallest',
                    'ClockSubText', 'ClockSubTextSuddenDeath', 'ClockSubTextTiny', 'TargetID', 'HudHintText',
                    'SpectatorKeyHints', 'SpectatorVerySmall', 'PlayerPanelPlayerName', 'TFFontSmall',
                    'TFFontMedium', 'GoalText', 'ItemTrackerScore_InGame', 'AchievementTracker_Desc',
                    'QuestObjectiveTracker_Desc', 'QuestObjectiveTracker_DescBlur', 'QuestObjectiveTracker_DescGlow',
                    'HudNumbers', 'InstructionalText')


def font_block(name, tall, weight=400, italic=0, outline=0, dropshadow=0, antialias=1):
    return [['1', [['name', name, None], ['tall', str(tall), None], ['weight', str(weight), None],
                   ['additive', '0', None], ['antialias', str(antialias), None], ['italic', str(italic), None],
                   ['outline', str(outline), None], ['dropshadow', str(dropshadow), None]], None]]


RES_BANDS = (1, 600, 720, 768, 800, 864, 900, 960, 1024, 1050, 1080, 1200, 1440, 1600, 2160)  # screen heights


def banded_font(low, high, split=1080, **flags):
    """A font that changes with the screen height: low below `split` lines, high from there up, each a
    (name, tall, weight, outline) with tall in 480-line units. Entries with a "yres" range take their size in pixels
    (the game scales only range-less fonts), so each band gets the proportional size of its lowest height."""
    entries = []
    for i, lo in enumerate(RES_BANDS):
        hi = RES_BANDS[i + 1] - 1 if i + 1 < len(RES_BANDS) else 10000
        name, tall, weight, outline = low if lo < split else high
        blk = font_block(name, round(tall * max(lo, 480) / 480), weight, outline=outline, **flags)[0][1]
        entries.append([str(i + 1), blk + [['yres', f'{lo} {hi}', None]], None])
    return entries


# Rajdhani (shipped) draws digits and fixed English words: its Bold is the family "Rajdhani", its SemiBold the family
# "Rajdhani SemiBold". Anything the game writes in the player's language or a player's name goes in Bahnschrift
# (Windows), which covers far more scripts. Share Tech Mono (shipped) draws the terminal lines.
RK_FONTS = {
    'RK_Health': font_block('Rajdhani', 38, 700),
    'RK_Ammo': font_block('Rajdhani', 38, 700),
    'RK_AmmoSmall': font_block('Rajdhani SemiBold', 15, 600),
    'RK_Damage': font_block('Rajdhani', 22, 700, outline=1),      # 0.9 (preview 05): the damage number larger
    'RK_DamageBig': font_block('Rajdhani', 30, 700, outline=1),
    'RK_Killfeed': banded_font(('Tektur SemiBold', 12, 600, 0), ('Tektur SemiBold', 11, 600, 0), split=1440),
    'RK_Small': font_block('Bahnschrift SemiCondensed', 8, 400),
    'RK_Menu': font_block('Bahnschrift SemiCondensed', 12, 500),
    'RK_Title': font_block('Bahnschrift SemiBold Condensed', 20, 600),
    'RK_ScoreBig': font_block('Rajdhani', 40, 700),
    'RK_WinBig': font_block('Rajdhani', 26, 700),          # 0.9: the win panel's RED WINS
    'RK_Streak': font_block('Bahnschrift SemiBold Condensed', 24, 600),
    'RK_HealthBig': font_block('Rajdhani', 38, 700),
    'RK_Reserve': font_block('Rajdhani SemiBold', 21, 600),
    'RK_HealthHuge': font_block('Rajdhani', 42, 700),
    'RK_Sticky': font_block('Rajdhani', 20, 700),
    'RK_NoticeTitle': font_block('Bahnschrift SemiBold Condensed', 17, 600),
    'RK_NoticeBody': font_block('Bahnschrift SemiCondensed', 11, 400),
    # spectator key hints / tip / map name: outlined, they float over the map now that the black bars are gone
    'RK_SpecHint': font_block('Bahnschrift SemiCondensed', 10, 500, outline=1),
    'RK_SpecMap': font_block('Bahnschrift SemiBold Condensed', 14, 600, outline=1),
    'RK_Button': font_block('Rajdhani', 10, 700),
    'RK_PanelTitle': font_block('Rajdhani', 11, 700),
    'RK_Mono': font_block('Share Tech Mono', 7, 400),
}

def scalable_border(image, corner=8, draw=2, color=None, draw_h=None):
    b = [['bordertype', 'scalable_image', None], ['backgroundtype', '2', None], ['image', 'replay/thumbnails/rk/' + image, None],
         ['src_corner_height', str(corner), None], ['src_corner_width', str(corner), None],
         ['draw_corner_width', str(draw), None], ['draw_corner_height', str(draw if draw_h is None else draw_h), None]]
    if color:
        b.append(['color', color, None])
    return b


RK_BORDERS = {
    'RK_Nav': scalable_border('nav', 4, 2),
    'RK_NavArmed': scalable_border('nav_hover', 4, 2),
    'RK_Frame': scalable_border('panel_thin'),
    'RK_ScoreBG': scalable_border('panel'),
    'RK_ScoreMain': scalable_border('score_main', 0, 0),  # whole-image borders: the art stretched over the panel
    'RK_TornTag': scalable_border('ig_strip', 0, 0),
    'RK_TopBand': scalable_border('top_band', 0, 0),
    'RK_StreakCard': scalable_border('streak_card', 40, 4, draw_h=3),  # only as tall as its text; text starts 5 in
    'RK_RespawnCard': scalable_border('respawn_card', 0, 0),  # the respawn label's own border (patch_spectator)
    'RK_SpecTop': scalable_border('spec_bar_top', 0, 0),  # 0.9: the spectator bars (patch_spectator)
    'RK_SpecBot': scalable_border('spec_bar_bot', 0, 0),
    'RK_KeyChip': scalable_border('menu_key', 0, 0),  # build / disguise menu number labels (patch_menu)
    'RK_IntelCard': scalable_border('intel_card', 0, 0),  # the intel you carry (patch_flagpanel)
}
RK_BORDERS['RK_Card_none'] = scalable_border('blank', 0, 0)
# the open chat (ingame.patch_chat): the game paints these two borders only while the chat is open
RK_BORDERS['RK_ChatWell'] = scalable_border('chat_well', 0, 0)
RK_BORDERS['RK_ChatInput'] = scalable_border('chat_input', 12, 3)
for _c in screens.CARD_BORDERS + extras.XH_CARDS + blackwall.KS_CARDS:  # whole-image borders: zero corners stretch the art over the button
    RK_BORDERS[f'RK_Card_{_c}'] = scalable_border(_c, 0, 0)
    RK_BORDERS[f'RK_Card_{_c}_h'] = scalable_border(_c + '_h', 0, 0)


# ------------------------------------------------------------------ borders
def border_image(name, has_color):
    n = name.lower()
    rules = [
        (('mainmenubuttondepressedarmed', 'mainmenubuttonarmed', 'mainmenuminibuttonarmed'), 'btn_hover'),
        (('mainmenubuttondepressed',), 'btn_down'),
        (('mainmenubuttondisabled',), 'btn_off'),
        (('mainmenubuttondefault', 'mainmenuminibuttondefault'), 'btn'),
        (('notificationhighpriority', 'replayhighlightborder'), 'panel_accent'),
        (('mainmenubgborder', 'mainmenuhighlightborder', 'traininresultsbg', 'trainingresultsbg', 'notificationdefault', 'loadoutitempopupborder',
          'graydialogborder', 'replaygraydialogborder', 'replaydefaultborder', 'queststatusborder', 'replayballoonborder'), 'panel'),
        (('redbgopaque', 'redbgmoreopaque', 'replayfatlineborderredbgopaque'), 'panel_red_opaque'),
        (('redbg', 'redwiththinborder'), 'panel_red'),
        (('bluebgopaque', 'bluebgmoreopaque'), 'panel_blue_opaque'),
        (('bluebg', 'bluewiththinborder'), 'panel_blue'),
        (('clearbg',), 'panel_clear'),
        (('tffatlineborderopaque', 'replayfatlineborderopaque'), 'panel_opaque'),
        (('tffatlineborder',), 'panel'),
        (('thinlineborder',), 'panel_thin'),
        (('loadoutitemmouseoverborder',), 'item_hover'),
        (('outlinedgreybox',), 'item_sel'),
        (('outlineddullgreybox', 'econitemborder'), 'item_plain'),
    ]
    for keys, img in rules:
        if any(n.startswith(k) or n == k or k in n for k in keys):
            return img
    if n.startswith('backpackitem'):
        if 'selected' in n:
            return 'item_sel'
        if 'mouseover' in n:
            return 'item_hover'
        if has_color:
            return 'item'
        return 'item_plain'
    return None


def retint_scheme(src_text):
    """SourceScheme: only its colours move from tan to grey / crimson."""
    root = kv.parse(src_text)
    scheme = kv.find(root, 'Scheme')
    for section in ('Colors', 'BaseSettings'):
        for ent in kv.walk(kv.find(scheme, section) or []):
            if not isinstance(ent[1], list):
                ent[1] = retint(ent[1])
    # hover text (the store's class filters, the main menu's server icons) is drawn with this scheme: ink and white like
    # the HUD's own, not the base file's colours
    base = kv.find(scheme, 'BaseSettings')
    if base is not None:
        kv.setmany(base, **{'Tooltip.TextColor': '236 232 232 255', 'Tooltip.BgColor': '12 12 14 240'})
    return kv.dump(root) + '\n'


def build_scheme(src_text):
    root = kv.parse(src_text)
    scheme = kv.find(root, 'Scheme')
    colors = kv.find(scheme, 'Colors')
    for ent in colors:
        k = ent[0]
        if isinstance(ent[1], list):
            continue
        if k in SCHEME_COLORS:
            ent[1] = SCHEME_COLORS[k]
        elif not KEEP_COLOR.search(k):
            ent[1] = retint(ent[1])
    for k, v in C.items():
        kv.set(colors, k, v)

    base = kv.find(scheme, 'BaseSettings')
    for ent in kv.walk(base):
        if not isinstance(ent[1], list):
            ent[1] = retint(ent[1])
    kv.setmany(base, **{
        'Button.ArmedBgColor': 'RK_RedDeep', 'Button.SelectedBgColor': 'RK_RedDeep',
        'Button.DepressedBgColor': 'RK_Red', 'Button.DepressedTextColor': 'RK_Ink',
        'Econ.Button.ArmedBgColor': 'RK_RedDeep', 'Econ.Button.DepressedBgColor': 'RK_Red',
        'Econ.Button.DepressedFgColor': 'RK_Ink', 'Econ.Button.BgColor': '22 20 24 255',
        'Button.BgColor': '22 20 24 255', 'Button.TextColor': 'RK_Text', 'Button.ArmedTextColor': 'RK_Text',
        'CheckButton.TextColor': 'RK_Text', 'CheckButton.SelectedTextColor': 'RK_Text',
        'CheckButton.Border1': 'RK_Grey', 'CheckButton.Border2': 'RK_Grey', 'CheckButton.Check': 'RK_Red',
        'CheckButton.HighlightFgColor': 'RK_Red',
        'ListPanel.SelectedBgColor': 'RK_RedDeep', 'ListPanel.SelectedOutOfFocusBgColor': 'RK_RedDeep',
        'ListPanel.SelectedTextColor': 'RK_Text', 'SectionedListPanel.SelectedBgColor': 'RK_RedDeep',
        'SectionedListPanel.SelectedTextColor': 'RK_Text', 'SectionedListPanel.OutOfFocusSelectedTextColor': 'RK_Text',
        'RichText.SelectedBgColor': 'RK_RedDeep', 'Tooltip.TextColor': 'RK_Text', 'Tooltip.BgColor': 'RK_Ink',
        'Menu.ArmedTextColor': 'RK_Ink', 'Menu.ArmedBgColor': 'RK_Red', 'Menu.BgColor': '7 7 9 240',
        'Frame.BgColor': '7 7 9 235', 'Frame.OutOfFocusBgColor': '7 7 9 235',
        'TextEntry.SelectedBgColor': 'RK_RedDeep', 'TextEntry.CursorColor': 'RK_Red',
        # the chat's typing line: the game keeps its own panel see-through, so its dark field is the text entry's
        # (every other text entry of the HUD brings its own colour), the typed text bone white instead of orange
        'TextEntry.BgColor': '4 4 6 240', 'Chat.TypingText': 'RK_Text',
        'Slider.NobColor': 'RK_Red', 'Slider.TrackColor': '30 31 32 255',
        'ScrollBarSlider.FgColor': 'RK_Grey', 'ScrollBarButton.FgColor': 'RK_Grey',
        'ItemColor': '224 26 46 200', 'MenuColor': 'RK_Text', 'VguiScreenCursor': 'RK_Red',
        'SelectionNumberFg': 'RK_Text', 'SelectionTextFg': 'RK_Text',
    })
    kv.setmany(base, **loadout.SCHEME_BASE)

    fonts = kv.find(scheme, 'Fonts')
    for fnt in fonts:
        if not isinstance(fnt[1], list):
            continue
        for sub in fnt[1]:
            if isinstance(sub[1], list):
                for e in sub[1]:
                    if e[0].lower() == 'name' and e[1].lower() in FONT_REMAP:
                        e[1] = FONT_REMAP[e[1].lower()]
    for name in CHAT_FONTS + SCOREBOARD_FONTS:
        for sub in kv.find(fonts, name) or []:
            if isinstance(sub[1], list):
                kv.set(sub[1], 'name', GAME_FACE)
    for name in STOCK_FACE_FONTS:
        for sub in kv.find(fonts, name) or []:
            if isinstance(sub[1], list) and (kv.get(sub[1], 'name') or '').lower() in STOCK_FACES:
                kv.set(sub[1], 'name', GAME_FACE)
    for name, blk in {**RK_FONTS, **ingame.FONTS, **menu.FONTS, **loadout.FONTS, **extras.FONTS}.items():
        kv.remove(fonts, name)
        fonts.append([name, blk, None])
    files = kv.find(scheme, 'CustomFontFiles')
    nums = [int(e[0]) for e in files if e[0].isdigit()]
    for i, f in enumerate(SHIPPED_FONTS):
        files.append([str(max(nums + [0]) + 1 + i), 'resource/fonts/' + f, None])

    borders = kv.find(scheme, 'Borders')
    changed = 0
    for b in borders:
        if not isinstance(b[1], list):
            continue
        body = b[1]
        if (kv.get(body, 'bordertype') or '').lower() != 'scalable_image':
            continue
        img = border_image(b[0], kv.get(body, 'color') is not None)
        if not img:
            continue
        kv.set(body, 'image', T + img)
        item = img.startswith('item')
        kv.set(body, 'src_corner_height', '8')
        kv.set(body, 'src_corner_width', '8')
        kv.set(body, 'draw_corner_width', '3' if item else '2')
        kv.set(body, 'draw_corner_height', '3' if item else '2')
        if img == 'item_sel':
            kv.remove(body, 'color')
        changed += 1
    changed += loadout.tile_borders(borders)  # the backpack tiles, in the loadout's look
    for name in ('MainMenuButtonGlow', 'MainMenuButtonGlow2'):  # orange glow behind highlighted menu buttons
        blk = kv.find(borders, name)
        if blk is not None:
            kv.set(blk, 'color', '224 26 46 255')
    for name, blk in {**RK_BORDERS, **ingame.BORDERS, **menu.BORDERS, **loadout.BORDERS, **extras.BORDERS}.items():
        kv.remove(borders, name)
        borders.append([name, blk, None])
    print(f'  scheme: {changed} borders re-skinned')
    return '\n'.join([kv.dump(root), ''])


# ------------------------------------------------------------------ generic res re-skin
IMAGE_MAP = {
    '../hud/color_panel_brown': T + 'panel', '../hud/color_panel_brown_opaque': T + 'panel_opaque',
    '../hud/tournament_panel_brown': T + 'panel_thin',
    '../hud/color_panel_red': T + 'panel_red', '../hud/color_panel_red_opaque': T + 'panel_red_opaque',
    '../hud/color_panel_red_more_opaque': T + 'panel_red_opaque',
    '../hud/color_panel_blu': T + 'panel_blue', '../hud/color_panel_blu_opaque': T + 'panel_blue_opaque',
    '../hud/color_panel_blu_more_opaque': T + 'panel_blue_opaque',
    '../hud/color_panel_clear': T + 'panel_clear', '../hud/notification_black': T + 'panel_clear',
    '../hud/death_panel_red_bg': T + 'panel_red', '../hud/death_panel_blue_bg': T + 'panel_blue',
    '../hud/score_panel_red_bg': T + 'panel_red', '../hud/score_panel_blue_bg': T + 'panel_blue',
    '../hud/score_panel_red_bg_solid': T + 'panel_red_opaque', '../hud/score_panel_blue_bg_solid': T + 'panel_blue_opaque',
    '../hud/character_red_bg': T + 'blank', '../hud/character_blue_bg': T + 'blank',
    '../hud/character_red_bg_lodef': T + 'blank', '../hud/character_blue_bg_lodef': T + 'blank',
    '../hud/character_red_bg_clipped': T + 'blank', '../hud/character_blue_bg_clipped': T + 'blank',
    '../hud/character_red_bg_lodef_clipped': T + 'blank', '../hud/character_blue_bg_lodef_clipped': T + 'blank',
    '../hud/ammo_red_bg': T + 'blank', '../hud/ammo_blue_bg': T + 'blank',
    '../hud/ammo_red_bg_lodef': T + 'blank', '../hud/ammo_blue_bg_lodef': T + 'blank',
    'item_carousel_bg': T + 'inspect_bg',  # the tan backdrop of the backpack's item inspection
}
for _t in ('red', 'blue'):
    for _v in ('', '_lodef', '_horiz1', '_horiz2', '_horiz1_lodef', '_horiz2_lodef', '_vert', '_vert_lodef'):
        IMAGE_MAP[f'../hud/misc_ammo_area_{_t}{_v}'] = T + 'ig_strip'
        IMAGE_MAP[f'../hud/misc_ammo_area{_v}_{_t}'] = T + 'ig_strip'
IMAGE_KEYS = re.compile(r'^(image|teambg_\d(_lodef)?|image_name|bgimage|image_default|image_armed|image_selected)$', re.I)
COLOR_KEY = re.compile(r'colou?r|_override$', re.I)


def reskin_res(node):
    changed = False
    for ent in kv.walk(node):
        if isinstance(ent[1], list):
            continue
        key, val = ent[0], ent[1]
        if IMAGE_KEYS.match(key) and val.lower() in IMAGE_MAP:
            ent[1] = IMAGE_MAP[val.lower()]
            changed = True
        elif COLOR_KEY.search(key):
            nv = retint(val)
            m = BUTTON_FG.match(key)
            if m and (luma(nv) < 90 or nv.startswith('200 80 60')):
                # stock buttons draw dark text on tan plates; ours are ink, so the text has to go light
                nv = {'default': '210 206 208 255', 'armed': '255 255 255 255'}.get(m.group(1).lower(), '236 232 232 255')
            if nv != val:
                ent[1] = nv
                changed = True
    return changed


BUTTON_FG = re.compile(r'^(default|armed|depressed|selected)FgColor_override$', re.I)


def luma(val):
    m = re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+).*', val)
    if not m:
        return 255
    r, g, b = (int(x) for x in m.groups())
    return 0.299 * r + 0.587 * g + 0.114 * b


# ------------------------------------------------------------------ custom panels
def img_panel(name, x, y, w, h, image, z=1, drawcolor=None, visible=1):
    e = {'ControlName': 'ImagePanel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': visible, 'enabled': 1, 'scaleImage': 1, 'image': T + image, 'mouseinputenabled': 0}
    if drawcolor:
        e['drawcolor'] = drawcolor
    return e


def label(name, x, y, w, h, text, font, fg, align='west', z=5):
    return {'ControlName': 'CExLabel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
            'visible': 1, 'enabled': 1, 'labelText': text, 'textAlignment': align, 'font': font, 'fgcolor': fg}


STATUS_ICONS = ('PlayerStatusBleedImage', 'PlayerStatusHookBleedImage', 'PlayerStatusMilkImage', 'PlayerStatusGasImage',
                'PlayerStatusMarkedForDeathImage', 'PlayerStatusMarkedForDeathSilentImage', 'PlayerStatusSlowed')


def team_img(name, x, y, w, h, image, z=1):
    """Image that swaps to the local player's team art (red = teambg_2, blue = teambg_3)."""
    e = img_panel(name, x, y, w, h, image + '_red', z=z)
    e.update(ControlName='CTFImagePanel', teambg_2=T + image + '_red', teambg_3=T + image + '_blue')
    return e


# ------------------------------------------------------------------ in-game
# The in-game HUD (health card, ammo card, meter strips, target ID, kill feed, timer, chat) is laid out from the style
# preview in ingame.py. cl_hud_minmode switches it to the raised layout (HUD Settings): the stock *_minmode keys are
# stripped (strip_minmode) so the cvar moves nothing but the cards.
def box(x, y, w, h):
    return dict(xpos=x, ypos=y, wide=w, tall=h)


def strip_minmode(node):
    """Drop every stock *_minmode key: cl_hud_minmode is this HUD's layout switch, not the stock minimal HUD."""
    changed = False
    for ent in list(kv.walk(node)):
        if isinstance(ent[1], list):
            before = len(ent[1])
            ent[1][:] = [e for e in ent[1] if not e[0].lower().endswith('_minmode')]
            changed |= len(ent[1]) != before
    before = len(node)
    node[:] = [e for e in node if not e[0].lower().endswith('_minmode')]
    return changed or len(node) != before


def patch_tracker(root):
    """Contract tracker ("Contract Inactive / Press [ F2 ] to view") at the top right, below the kill feed.
    The game sizes its box from the header's width plus stats_buffer_width: our header font is condensed and the
    "Press [ F2 ]" line kept its wide stock font, so that line ran under the folder icon: more buffer."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.set(kv.find(body, 'ItemAttributeTracker'), 'stats_buffer_width', 50)
    kv.set(kv.find(body, 'QuestsStatusContainer'), 'ypos', 146)


def patch_inspect(root):
    """An F tap on a teammate opens the inspect card (their item), and the game hides the ammo, sticky, uber and item
    meter counters while it is open: it locks their render group when the card shows and unlocks it when the card
    hides. A HUD reload with the card open hid the card without the unlock, so the counters stayed gone until the map
    changed. Loading the card as visible keeps that bookkeeping right."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.set(kv.find(body, 'itempanel'), 'visible', 1)


def patch_rocketpack(root):
    """Thermal Thruster: the CHARGES strip in its row (ingame.METER_ROW). Its file #bases the generic meter but sets
    each of its panels itself, at the stock box's places: the label and both bars lay below a strip's foot, where the
    strip cut them off. The name goes where every strip has it, the two charges side by side in the bar's place. The
    game paints them white while a launch is ready and red while it is not, so they stay plain bars on the faint track
    of the charge-up bars: a segment sheet over them would turn both states the team's colour."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    top = kv.find(body, 'HudItemEffectMeter')
    row = ingame.METER_ROW['hudrocketpack.res']
    x, y, w, h = ingame.strip_box(row)
    ingame.put(top, x, y, w, h)
    kv.set(top, 'xpos_minmode', ingame.strip_box(row, True)[0])
    kv.set(top, 'ypos_minmode', ingame.strip_box(row, True)[1])
    bg = ingame.find(body, 'ItemEffectMeterBG')
    kv.setmany(bg, xpos=0, ypos=0, zpos=0, wide=w, tall=h, scaleImage=1, visible=1, **ingame.team_keys('ig_strip'))
    for key in ('teambg_2_lodef', 'teambg_3_lodef'):
        kv.remove(bg, key)
    kv.setmany(ingame.find(body, 'ItemEffectIcon'), xpos=0, ypos=0, wide=0, tall=0)
    lx, ly, lw, lh = ingame.STRIP_LABEL
    # the game colours the name itself (white, grey while disabled); the stock dark red is only its first frame
    kv.setmany(ingame.find(body, 'ItemEffectMeterLabel'), xpos=lx, ypos=ly, zpos=2, wide=lw, tall=lh,
               font='RK_StripLabel', textAlignment='west', textinsetx=0, autoResize=0, visible=1,
               fgcolor='236 232 232 255')
    # the #base brings in the generic strip's own panels too: its segment sheet would lie over the two bars (the
    # Hueco Mundo HUD had a stray strip over the Thruster's text that way)
    kv.add_block(body, 'RK_BarMul', {'ControlName': 'ImagePanel', 'fieldName': 'RK_BarMul', 'xpos': 0, 'ypos': 0,
                                     'wide': 0, 'tall': 0, 'visible': 0, 'enabled': 0, 'image': T + 'blank'})
    bx, by, bw, bh = ingame.STRIP_BAR
    gap = 2
    half = (bw - gap) // 2
    for i, n in enumerate(('ItemEffectMeter', 'ItemEffectMeter2')):
        kv.setmany(ingame.find(body, n), ControlName='ContinuousProgressBar', fieldName=n,
                   xpos=bx + i * (half + gap), ypos=by, zpos=2, wide=half if i == 0 else bw - half - gap, tall=bh,
                   visible=1, enabled=1, fgcolor_override='255 255 255 255', bgcolor_override='236 232 232 45')


# stock meter files (shield / bow / uber charge, Dead Ringer, stickies, item meters) lose the stock boxes before the
# strip patches lay them out
METER_FILE = re.compile(r'resource/ui/hud\w*(charge|meter|pipes)\w*\.res$')


# the game paints item meter bars with these; it reads them as raw r g b a, so scheme colour names don't work
METER_COLORS = dict(MeterFG='255 255 255 255', MeterBG='118 116 120 255')


def recolor_meters(root):
    for ent in kv.walk(root):
        if not isinstance(ent[1], list) and ent[0] in METER_COLORS:
            ent[1] = METER_COLORS[ent[0]]


def patch_meter_style(root):
    recolor_meters(root)
    for ent in kv.walk(root):
        blk = ent[1]
        if not isinstance(blk, list):
            continue
        ctl = (kv.get(blk, 'ControlName') or '').lower()
        if ctl in ('continuousprogressbar', 'progressbar'):
            kv.setmany(blk, fgcolor_override='224 26 46 255', bgcolor_override='236 232 232 45')
        elif ctl in ('imagepanel', 'ctfimagepanel'):
            img = (kv.get(blk, 'image') or '').lower()
            if img.startswith('../hud/') and ('_bg' in img or 'misc_ammo' in img):
                kv.set(blk, 'image', T + 'ig_strip')
                for key in ('teambg_1', 'teambg_2', 'teambg_3'):
                    if kv.get(blk, key) is not None:
                        kv.set(blk, key, T + 'ig_strip')


CTF_STRIP = 48  # CTF's flag strip (patch_flagpanel) starts this far above the screen's bottom

# ÜberCharge: tf2_misc does not always carry hudmediccharge.res, so the stock layout is kept here as a fallback.
STOCK_MEDIC = '''"Resource/UI/HudMedicCharge.res"
{
	"Background"	{ "ControlName" "CTFImagePanel" "fieldName" "Background" "xpos" "0" "ypos" "0" "zpos" "0" "wide" "130" "tall" "65"
		"visible" "1" "enabled" "1" "image" "../hud/medic_charge_blue_bg" "scaleImage" "1" "teambg_2" "../hud/medic_charge_red_bg"
		"teambg_3" "../hud/medic_charge_blue_bg" }
	"ChargeLabel"	{ "ControlName" "CExLabel" "fieldName" "ChargeLabel" "xpos" "30" "ypos" "24" "zpos" "1" "wide" "90" "tall" "15"
		"visible" "1" "enabled" "1" "labelText" "#TF_Ubercharge" "textAlignment" "center" "dulltext" "0" "brighttext" "0"
		"font" "HudFontSmallest" }
	"IndividualChargesLabel"	{ "ControlName" "CExLabel" "fieldName" "IndividualChargesLabel" "xpos" "30" "ypos" "24"
		"zpos" "1" "wide" "90" "tall" "15" "visible" "0" "enabled" "1" "labelText" "#TF_IndividualUbercharges"
		"textAlignment" "center" "dulltext" "0" "brighttext" "0" "font" "HudFontSmallest" }
	"ChargeMeter"	{ "ControlName" "ContinuousProgressBar" "fieldName" "ChargeMeter" "xpos" "30" "ypos" "38" "zpos" "2"
		"wide" "86" "tall" "8" "visible" "1" "enabled" "1" }
	"ChargeMeter1"	{ "ControlName" "ContinuousProgressBar" "fieldName" "ChargeMeter1" "xpos" "30" "ypos" "38" "zpos" "2"
		"wide" "19" "tall" "8" "visible" "0" "enabled" "1" }
	"ChargeMeter2"	{ "ControlName" "ContinuousProgressBar" "fieldName" "ChargeMeter2" "xpos" "52" "ypos" "38" "zpos" "2"
		"wide" "19" "tall" "8" "visible" "0" "enabled" "1" }
	"ChargeMeter3"	{ "ControlName" "ContinuousProgressBar" "fieldName" "ChargeMeter3" "xpos" "74" "ypos" "38" "zpos" "2"
		"wide" "19" "tall" "8" "visible" "0" "enabled" "1" }
	"ChargeMeter4"	{ "ControlName" "ContinuousProgressBar" "fieldName" "ChargeMeter4" "xpos" "96" "ypos" "38" "zpos" "2"
		"wide" "19" "tall" "8" "visible" "0" "enabled" "1" }
	"HealthClusterIcon"	{ "ControlName" "ImagePanel" "fieldName" "HealthClusterIcon" "xpos" "2" "ypos" "17" "zpos" "1"
		"wide" "36" "tall" "36" "visible" "1" "enabled" "1" "image" "../hud/ico_health_cluster" "scaleImage" "1" }
	"ResistIcon"	{ "ControlName" "ImagePanel" "fieldName" "ResistIcon" "xpos" "0" "ypos" "-25" "zpos" "1" "wide" "36"
		"tall" "36" "visible" "0" "enabled" "1" "image" "../HUD/defense_buff_bullet_blue" "scaleImage" "1" }
}
'''


def patch_streak_notice(root):
    """Killstreak splash ("... is GODLIKE!"): the game sizes and places the background around the text every frame,
    so the card is a nine-slice border on it instead of the stock flat box."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    bg = kv.find(body, 'Background')
    kv.remove(bg, 'bgcolor_override')
    kv.setmany(bg, PaintBackgroundType=0, paintbackground=0, paintborder=1, border='RK_StreakCard')


NOTIF_IMAGES = {T + 'panel_red': T + 'notif_red', T + 'panel_blue': T + 'notif_blue', T + 'panel_clear': T + 'notif_ink'}


def patch_notification(root, rel):
    """HUD notifications (resource/ui/notifications/*): the game stretches the background to the text, so the card
    art is a flat notice card; the base file sets the lettering."""
    for ent in kv.walk(root):
        if not isinstance(ent[1], list) and ent[0].lower() == 'image' and ent[1] in NOTIF_IMAGES:
            ent[1] = NOTIF_IMAGES[ent[1]]
    if rel.endswith('base_notification.res'):
        body = next(e[1] for e in root if isinstance(e[1], list))
        kv.setmany(kv.find(body, 'Notification_Label'), font='RK_NoticeTitle', fgcolor='RK_Text')
        # the stock icons (the intel returned / taken / dropped...) are dark, made for the stock light cards, and
        # vanished on ours: the icon panel paints a light chip behind its icon (it moves the panel with the text, and
        # the chip goes with it)
        kv.setmany(kv.find(body, 'Notification_Icon'), paintbackground=1, PaintBackgroundType=0,
                   bgcolor_override='236 232 232 235')


def patch_freezepanel(root):
    """Death screen "You were killed by ...". The game paints its background flat in the killer's team colour from code
    (hud/color_panel_*), so that panel shrinks to nothing and a card takes its place. The card follows the
    local player's team inverted (your killer is nearly always on the other team): local RED -> BLU card."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    bases = [e[1] for e in body if e[0] == 'FreezePanelBase' and isinstance(e[1], list)]
    for base in bases:
        bg = kv.find(base, 'FreezePanelBG')
        if bg is not None:
            kv.setmany(bg, wide=0, tall=0)
    base = bases[-1]  # the file defines the panel twice; the last block is the one the game lays out
    # 265 wide: it ends at the base's own edge (267), which clips what lies past it (the card's edge did, by 3)
    card = img_panel('RK_FreezeCard', 2, 154, 265, 44, 'freeze_blue', z=0)
    card.update(ControlName='CTFImagePanel', teambg_2=T + 'freeze_blue', teambg_3=T + 'freeze_red')
    kv.add_block(base, 'RK_FreezeCard', card)
    # plain vgui Labels: fgcolor_override (fgcolor is CExLabel only)
    # the game's line ("You were killed by", set from code) is kept but drawn clear; FLATLINED BY in its place
    kv.setmany(kv.find(base, 'FreezeLabel'), xpos=44, ypos=160, font='RK_NoticeBody', fgcolor_override='0 0 0 0')
    kv.remove(base, 'RK_FlatlineLabel')
    # in the killer's team colour, as the card: inverted from the local player's team (local RED -> BLU killer)
    line = img_panel('RK_Flatline', 44, 158, 200, 12, 'flatline_blue', z=3)
    line.update(ControlName='CTFImagePanel', teambg_2=T + 'flatline_blue', teambg_3=T + 'flatline_red')
    kv.add_block(base, 'RK_Flatline', line)
    kv.setmany(kv.find(base, 'FreezeLabelKiller'), ypos=170, tall=24, font='RK_Title')   # 0.9: the killer's name large
    kv.set(kv.find(base, 'AvatarImage'), 'zpos', 2)
    # the killer's health tag (patch_killer_health), centred on the card's toned end (x 4 to 41 past its stripe)
    tw, th = ingame.TAG
    kv.setmany(kv.find(base, 'FreezePanelHealth'), xpos=7, ypos=154 + (44 - th) // 2, wide=tw, tall=th)


def patch_invite(root):
    """Party invite ("... has invited you to their party", Accept / Decline). The game slides it in at the top left,
    where the matchmaking bar (zpos 10001) sits over it: the stock bar is a see-through gradient, ours an ink band that
    hid it. It draws above the bar now (its position is the game's, set by an animation)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.set(kv.find(body, 'InviteNotification'), 'zpos', 10010)


def patch_statpanel(root):
    """Death screen record card ("On the bright side... You came close to your record for ..."): the stock framed box
    becomes a card in your own team's tone, the class portrait on its toned end, the text in the notice
    fonts over an crimson rule. It starts below the spectator target ID, whose bottom the stock box covered."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.setmany(kv.find(body, 'StatPanelBG'), xpos=0, ypos=20, wide=266, tall=92, image=T + 'stat_blue',
               teambg_2=T + 'stat_red', teambg_3=T + 'stat_blue')
    kv.setmany(kv.find(body, 'StatPanelClassImage'), xpos=6, ypos=28, wide=70, tall=70)
    # plain vgui Labels: fgcolor_override (fgcolor is CExLabel only)
    for n, extra in (('titleLable', dict(ypos=26, tall=12, font='RK_NoticeBody', fgcolor_override='RK_Red')),
                     ('summaryLabel', dict(ypos=38, tall=40, font='RK_NoticeBody', fgcolor_override='RK_Text')),
                     ('StatLabelLarge', dict(ypos=80, tall=22, font='RK_NoticeTitle', fgcolor_override='RK_Text')),
                     ('StatLabelSmall', dict(ypos=83, tall=16, font='RK_NoticeBody', fgcolor_override='RK_TextMid'))):
        kv.setmany(kv.find(body, n), xpos=82, wide=176, **extra)
    kv.setmany(kv.find(body, 'StatBox'), wide=0, tall=0)  # the game paints it translucent black from code


def patch_tournament(root):
    """Match start countdown (casual / competitive): the digits on a square card, in the health font."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    bg = kv.find(body, 'CountdownBG')
    if bg is not None:
        kv.setmany(bg, image=T + 'countdown_card', src_corner_width=60, src_corner_height=60, draw_corner_width=9,
                   draw_corner_height=9, wide=50, tall=50)
        comp = kv.find(bg, 'if_competitive')
        if comp is not None:
            kv.setmany(comp, xpos='cs-0.5', ypos=145)
    # the digits centred on the card (Rajdhani stands upright: the Hueco Mundo HUD's 4-unit lean correction for its
    # slanted face put them left of the middle here); the shadow keeps its 0.8 unit offset
    for n, color, x in (('CountdownLabel', 'RK_Text', 'cs-0.5'), ('CountdownLabelShadow', 'RK_Shadow', 'cs-0.48')):
        blk = kv.find(body, n)
        if blk is None:
            continue
        kv.set(blk, 'font', 'RK_HealthHuge')
        comp = kv.find(blk, 'if_competitive')
        if comp is not None:
            kv.setmany(comp, font='RK_HealthHuge', fgcolor=color, xpos=x)
        else:
            kv.set(blk, 'fgcolor', color)


# ------------------------------------------------------------------ center-screen notices
# Team goal ("You are now Attacking!"), team switch (autobalanced) and alert (autobalance warning) share one card:
# team-toned panel, a crimson seal with the notice's kanji where the stock icon was, text beside it split by an
# crimson rule. Labels keep the stock order; any label that can carry a sentence wraps.
NOTICE_W, NOTICE_H = 320, 82
NOTICES = {  # file: background, stock icon, seal, [(label, box, font, colour, wrap)], rule box
    'resource/ui/hudteamgoal.res': (
        'HudTeamGoalBG', 'GoalImage', 'seal_goal',
        [('SwitchLabel', (76, 10, 234, 22), 'RK_NoticeTitle', 'RK_Text', 0),
         ('GoalLabel', (76, 38, 234, 38), 'RK_NoticeBody', 'RK_TextMid', 1)], (76, 31, 220, 6)),
    'resource/ui/hudteamswitch.res': (
        'HudTeamSwitchBG', 'SwitchImage', 'seal_switch',
        [('BalanceLabel', (76, 8, 234, 26), 'RK_NoticeBody', 'RK_TextMid', 1),
         ('SwitchLabel', (76, 42, 234, 36), 'RK_NoticeTitle', 'RK_Text', 1)], (76, 35, 220, 6)),
    'resource/ui/hudalert.res': (
        'HudAlertBG', 'AlertImage', 'seal_alert',
        [('AlertLabel', (76, 10, 234, 56), 'RK_NoticeTitle', 'RK_Text', 1)], (76, 70, 220, 6)),
}


def patch_notice(root, rel):
    bg, icon, seal, labels, rule = NOTICES[rel]
    body = next(e[1] for e in root if isinstance(e[1], list))
    blk = kv.find(body, bg)
    kv.setmany(blk, xpos=0, ypos=0, zpos=-1, wide=NOTICE_W, tall=NOTICE_H, image=T + 'notice_blue',
               teambg_2=T + 'notice_red', teambg_3=T + 'notice_blue')
    for key in ('teambg_2_lodef', 'teambg_3_lodef'):
        kv.remove(blk, key)
    kv.setmany(kv.find(body, icon), xpos=0, ypos=0, wide=0, tall=0, visible=0)
    # the seal and the rule in the local player's team colour (the card is already toned by the team)
    kv.add_block(body, 'RK_NoticeSeal', ingame.timg('RK_NoticeSeal', 12, 12, 52, 58, seal, z=1))
    kv.add_block(body, 'RK_NoticeRule', ingame.timg('RK_NoticeRule', *rule, 'notice_rule', z=1))
    for name, bx, font, color, wrap in labels:
        # stock labels are plain vgui Labels, which take fgcolor_override (fgcolor is CExLabel only)
        kv.setmany(kv.find(body, name), zpos=2, font=font, fgcolor_override=color, textAlignment='north-west',
                   wrap=wrap, **box(*bx))


def patch_building(root, rel):
    """Engineer / spy building status items (resource/ui/hud_obj_*.res): stock background hidden, a
    card sized to the item underneath the stock icons and bars, the building's kanji as a faint watermark.
    Written against whatever the game ships, so it only reads the item size and hides background icons."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    top = next((e[1] for e in body if isinstance(e[1], list)), None)
    if top is None:
        return
    w, h = kv.get(top, 'wide'), kv.get(top, 'tall')
    if not (w and h and w.isdigit() and h.isdigit()):
        return
    w, h = int(w), int(h)
    for ent in kv.walk(body):
        if not isinstance(ent[1], list):
            continue
        fname = (kv.get(ent[1], 'fieldName') or ent[0]).lower()
        icon = (kv.get(ent[1], 'icon') or '').lower()
        if fname == 'background' or icon.startswith('obj_status_background'):
            kv.setmany(ent[1], visible=0, wide=0, tall=0)
    kind = next((k for k in build_art.BUILDING_KANJI if k in rel), None)
    kv.add_block(body, 'RK_BldCard', team_img('RK_BldCard', 0, 0, w, h, 'bld', z=-2))
    s = h - 6
    if kind:
        kv.add_block(body, 'RK_BldKanji', img_panel('RK_BldKanji', w - s - 4, 3, s, s, 'bld_k_' + kind, z=-1,
                                                    drawcolor='236 232 232 34'))
    # alerts (low ammo / health, sapper): the stock tray slid a bright white tab over the card's kanji end. It stays
    # hidden (the game still runs its slide, which is what shows the icons), and the icons sit on the kanji instead:
    # the wrench in white, the sapper in crimson
    for ent in kv.walk(body):
        if not isinstance(ent[1], list):
            continue
        if (kv.get(ent[1], 'ControlName') or '').lower() == 'cbuildingstatusalerttray':
            kv.set(ent[1], 'visible', 0)
        elif ent[0] in ('WrenchIcon', 'SapperIcon'):
            iw, ih = int(kv.get(ent[1], 'wide') or 27), int(kv.get(ent[1], 'tall') or 27)
            kv.setmany(ent[1], xpos=w - s // 2 - 4 - iw // 2, ypos=3 + s // 2 - ih // 2,
                       iconColor='236 232 232 255' if ent[0] == 'WrenchIcon' else '255 52 76 255')


def patch_killer_health(root):
    """Killcam: the killer's health (FreezePanelKillerHealth.res) on the target ID's health tag
    (ingame.patch_spec_health), laid out from scratch: whatever the stock file holds doesn't matter. Its gauge and
    edge take the killer's team colour as the death card does, the local player's inverted (your killer is nearly
    always on the other team). Up to 0.6.0 it was a square tile filled by the plain material hud/health_color, which
    Valve's servers keep stock: there it showed the stock cross."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    del body[:]
    for name in ('PlayerStatusHealthBonusImage', 'PlayerStatusHealthImageBG', 'PlayerStatusHealthImage'):
        kv.add_block(body, name, {'ControlName': 'ImagePanel', 'fieldName': name, 'xpos': 0, 'ypos': 0, 'zpos': 0,
                                  'wide': 0, 'tall': 0, 'visible': 1, 'enabled': 1, 'scaleImage': 1})
    kv.add_block(body, 'PlayerStatusHealthValue', label('PlayerStatusHealthValue', 0, 0, 0, 0, '%Health%',
                                                        'RK_TidHealth', 'RK_Text', align='center'))
    ingame.patch_spec_health(root)
    for n in ('RK_HealthMul', 'RK_TagPlate'):
        blk = kv.find(body, n)
        red, blu = kv.get(blk, 'teambg_2'), kv.get(blk, 'teambg_3')
        kv.setmany(blk, image=blu, teambg_1=blu, teambg_2=blu, teambg_3=red)
    # a dead killer (the game sends health 0, blanks the number and hides PlayerStatusHealthImageBG): LOST over the
    # number's place. The game shows that panel again for any health above 0, so it is the cover over the mark here
    # (ingame.tex_tag_cover, the plate's own glass) and the gauge's track moves to a panel of its own; the gauge
    # itself turns the dead material's grey (hud/health_dead -> hp_dead)
    w, h = ingame.TAG
    gx, gy, gw, gh = ingame.TAG_GAUGE
    kv.add_block(body, 'RK_TagTrack', img_panel('RK_TagTrack', gx, gy, gw, gh, 'ig_tag_track', z=1))
    kv.add_block(body, 'RK_TagDead', img_panel('RK_TagDead', 0, 0, w, h, 'ig_tag_dead', z=5))
    kv.setmany(kv.find(body, 'PlayerStatusHealthImageBG'), xpos=0, ypos=0, wide=w, tall=h, zpos=6,
               image=T + 'ig_tag_cover')
    kv.set(kv.find(body, 'RK_HealthValue'), 'zpos', 7)


def recolor_logos(node):
    """TF2's spinning logo (CTFLogoPanel: the queue box, a searching party slot, an invite, the in-game queue status)
    is drawn by the game in the panel's foreground colour: the HUD's crimson instead of the stock orange. Logos in
    other colours mean something (the paint kit dialog's green, red and tan) and keep them."""
    changed = False
    for ent in node:
        if isinstance(ent[1], list):
            if ((kv.get(ent[1], 'ControlName') or '').lower() == 'ctflogopanel'
                    and (kv.get(ent[1], 'fgcolor_override') or 'TFOrange').lower() in ('tforange', 'orange')):
                kv.set(ent[1], 'fgcolor_override', '224 26 46 255')
                changed = True
            changed |= recolor_logos(ent[1])
    return changed


def patch_flagpanel(root):
    """CTF: the captures go beside the timer at the top (ingame.patch_flag_scores, as the preview), the two flags stay
    in rings at the bottom centre."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for n in ('LeftSideBG', 'RightSideBG', 'OutlineBG', 'PlayingToBG'):
        kv.setmany(kv.find(body, n), wide=0, tall=0, visible=0)
    ingame.patch_flag_scores(body)
    # the capture limit under the timer box, with the scores beside the box: the top reads as the CTF scoreboard
    kv.setmany(kv.find(body, 'PlayingTo'), xpos='c-55', ypos=ingame.GOAL_Y, wide=110, tall=8, zpos=5,
               font='RK_StripLabel', allcaps=1, textAlignment='center', fgcolor='RK_Text')
    # the rings (64 units, centred in their 160-wide panels) well apart, the compass card (c-20 to c20) in the
    # middle between them: centres at c-80 and c80, level with the card's
    kv.setmany(kv.find(body, 'BlueFlag'), xpos='c-160', ypos='r62')
    kv.setmany(kv.find(body, 'RedFlag'), xpos='c0', ypos='r62')
    # carrying the intel: the compass to your capture zone sits between the rings, with the intel card inside. The
    # game sets the carried picture itself, from hud/objectives_flagpanel_carried_*, and Valve's servers keep that
    # material stock (sv_pure): so the picture is drawn see-through and the card is the panel's border, from the
    # replay/thumbnails path every server allows; the game still shows and hides the panel
    capture = kv.find(body, 'CaptureFlag')
    kv.setmany(capture, xpos='c-20', ypos='r%d' % (CTF_STRIP + 1), wide=40, tall=40)
    for n in ('CarriedImage', 'SpecCarriedImage'):
        kv.setmany(kv.find(body, n), xpos='c-12', ypos='r%d' % (CTF_STRIP - 7), wide=24, tall=24,
                   drawcolor='0 0 0 0', border='RK_IntelCard', paintborder=1)
    for blk in (capture, kv.find(body, 'CarriedImage')):
        for cond in ('if_hybrid', 'if_specialdelivery'):
            kv.remove(blk, cond)
    # the pickup flash (FlagOutline) animates this one at the old spot: nothing left to draw
    kv.setmany(kv.find(body, 'OutlineImage'), wide=0, tall=0, visible=0, image=T + 'blank')


def patch_flagstatus(root):
    """Each flag's ring a size up, so its state reads at a glance: the briefcase and its state glyph centred in it.
    The ring, briefcase and glyphs are our pictures through the redirected stock materials (objective_icons)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.setmany(kv.find(body, 'Arrow'), xpos=48, ypos=0, wide=64, tall=64)
    brief = kv.find(body, 'Briefcase')
    kv.setmany(brief, xpos=63, ypos=15, wide=34, tall=34)
    for e in brief:
        if isinstance(e[1], list):
            kv.setmany(e[1], xpos=61, ypos=13, wide=38, tall=38)
    kv.setmany(kv.find(body, 'StatusIcon'), xpos=66, ypos=18, wide=28, tall=28)


def patch_hudlayout(root):
    body = kv.find(root, 'Resource/HudLayout.res')
    ingame.patch_hudlayout(body)
    extras.patch_hudlayout(body)  # the damage indicator's sizes
    for n in ('HudItemEffectMeter', 'HudDemomanCharge', 'HudBowCharge', 'HudFlameRocketCharge'):
        blk = kv.find(body, n)
        if blk is not None:
            recolor_meters(blk)
    for n, y in (('HudTeamGoal', 65), ('HudTeamSwitch', 75), ('HudAlert', 130)):
        kv.setmany(kv.find(body, n), xpos='c-%d' % (NOTICE_W // 2), ypos=y, wide=NOTICE_W, tall=NOTICE_H + 8)
    # hitmarker: flashed by the DamagedPlayer animation (ANIMS_HITMARKER), its glow in the team's colour
    hm = kv.add_block(body, 'RK_Hitmarker', ingame.timg('RK_Hitmarker', 'c-12', 'c-12', 24, 24, 'hitmarker', z=10))
    hm.append(['alpha', '0', None])


HUD_VMT = ('"UnlitGeneric"\n{\n\t"$baseTexture"\t"vgui/replay/thumbnails/rk/%s"\n\t"$translucent"\t"1"\n'
           '\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n}\n')


def redirect_objective_materials():
    """Point the stock control-point / flag materials at our thumbnails (same trick as other HUDs).
    Note: sv_pure servers may keep the stock look for these, everything else is unaffected."""
    src = os.path.join(OUT, 'materials', 'vgui', 'replay', 'thumbnails', 'rk', 'obj')
    for f in sorted(os.listdir(src)):
        if not f.endswith('.vtf'):
            continue
        name = f[:-4]
        folder = 'hud' if name.startswith(('objectives_', 'cart_')) else os.path.join('sprites', 'obj_icons')
        write(os.path.join(OUT, 'materials', folder, name + '.vmt'), HUD_VMT % ('obj/' + name))
    # the health gauge fill is drawn by the game from hud/health_color (bottom-up): plain white, which the gauge's
    # Modulate sheet turns into crimson segments (sv_pure servers keep the stock fill; the sheet handles that too)
    write(os.path.join(OUT, 'materials', 'hud', 'health_color.vmt'), HUD_VMT % 'ig_white')
    # ...and a dead player's tile (the killcam when the killer died too) is ours instead of the stock grey cross
    write(os.path.join(OUT, 'materials', 'hud', 'health_dead.vmt'), HUD_VMT % 'hp_dead')
    # server-sent HUD notifications set these backgrounds in code (not from a .res): our notification cards
    for stock, ours in (('score_panel_red_bg', 'notif_red'), ('score_panel_blue_bg', 'notif_blue'),
                        ('notification_black', 'notif_ink')):
        write(os.path.join(OUT, 'materials', 'hud', stock + '.vmt'), HUD_VMT % ours)


def prune_textures():
    """Drop the textures nothing refers to (art the layouts no longer use): every .res, the scheme, the scripts and
    the material overrides are searched for rk/ paths, and the materials of those for the textures they draw on
    besides their own (the menu video's second part is its material's detail texture)."""
    rk = os.path.join(OUT, 'materials', 'vgui', 'replay', 'thumbnails', 'rk')
    refs = set()
    pat = re.compile(r'replay/thumbnails/rk/([\w/]+)', re.I)
    for dirpath, _, files in os.walk(OUT):
        rel = os.path.relpath(dirpath, OUT).replace('\\', '/')
        if rel.startswith(('tools', 'docs', '.git')) or rel.startswith('materials/vgui/replay/thumbnails/rk'):
            continue
        for fn in files:
            if fn.endswith(('.res', '.txt', '.vmt')):
                refs.update(m.lower() for m in pat.findall(open(os.path.join(dirpath, fn), encoding='utf-8',
                                                                 errors='replace').read()))
    for name in list(refs):
        vmt = os.path.join(rk, name + '.vmt')
        if os.path.isfile(vmt):
            refs.update(m.lower() for m in pat.findall(open(vmt, encoding='utf-8', errors='replace').read()))
    dropped = 0
    for dirpath, _, files in os.walk(rk):
        for fn in files:
            if not fn.endswith('.vtf'):
                continue
            name = os.path.relpath(os.path.join(dirpath, fn[:-4]), rk).replace('\\', '/').lower()
            if name not in refs:
                for ext in ('.vtf', '.vmt'):
                    p = os.path.join(dirpath, fn[:-4] + ext)
                    if os.path.exists(p):
                        os.remove(p)
                dropped += 1
    print(f'  unused textures dropped: {dropped}')


CREDIT = '// The Reaper HUD - made by Ingalther. Licence: CC BY-NC-SA 4.0 (credit required, no selling).\n'


def video_info():
    """tools/video.py's account of the menu video (video/menu_video.json) with its texture files, or None when
    there is none: the loop in one texture (mm_video.vtf) or split over two or three (mm_video, _b, _c), where the
    game reads them (RK_DIR), which the build leaves in place (kept_files)."""
    if not os.path.isfile(VIDEO_JSON):
        return None
    info = json.load(open(VIDEO_JSON, encoding='utf-8'))
    files = [os.path.join(RK_DIR, name + '.vtf') for name in VIDEO_PARTS[:info.get('parts', 1)]]
    if not all(os.path.isfile(f) for f in files):
        return None
    info['files'] = files
    return info


def kept_files(video):
    """The files the build leaves in place in the folders it otherwise makes afresh: the menu video's textures and
    the startup video. tools/video.py and tools/intro.py write them where the game reads them, so the HUD holds each
    once (tens of megabytes; they used to be copies of files in video/)."""
    files = list(video['files']) if video else []
    if os.path.isfile(INTRO):
        files.append(INTRO)
    return {os.path.normcase(os.path.abspath(f)) for f in files}


def clear(path, keep):
    """Remove a file or folder the build makes, but for the files in keep and the folders holding them."""
    if not os.path.isdir(path):
        if os.path.exists(path) and os.path.normcase(os.path.abspath(path)) not in keep:
            os.remove(path)
        return
    for dirpath, _, files in os.walk(path, topdown=False):
        for fn in files:
            f = os.path.join(dirpath, fn)
            if os.path.normcase(os.path.abspath(f)) not in keep:
                os.remove(f)
        if not os.listdir(dirpath):
            os.rmdir(dirpath)


def video_vmt(base, fps, frames=None, parts=1, detail=None, first=None):
    """The menu video's material. A loop in one texture: base played by the AnimatedTexture proxy. A loop split over
    `parts` textures of `frames` frames each: the material works out where in the loop the game's clock is (its
    frame L, from CurrentTime) and from that one number both the frame each texture shows and which part is on
    screen. So the switch from one part to the next falls exactly on the frame where the part ends: with the
    AnimatedTexture proxy running the frames and a separate clock test running the switch, the two disagreed when
    the clock landed within a rounding error of a switch, and a frame from 3.7 s away flashed up.
    detail: the second part, as the detail texture (detail blend mode 3: shows the base at blend factor 0, the
    detail at 1), shown from frame `frames` on. first: this material shows only from loop frame `first` on ($alpha:
    the third part, over the other two)."""
    t = 'vgui/replay/thumbnails/rk/'
    keys = [('$basetexture', t + base)]
    if detail:
        keys += [('$detail', t + detail), ('$detailscale', '1'), ('$detailblendmode', '3'),
                 ('$detailblendfactor', '0')]
    if first:
        keys += [('$translucent', '1'), ('$alpha', '0')]
    keys += [('$vertexcolor', '1'), ('$vertexalpha', '1'), ('$no_fullbright', '1'), ('$ignorez', '1')]
    split = parts > 1
    if split:
        # float vars ("0.0", so the math proxies keep them as floats); "1" and "0" stay ints, as LessOrEqual copies
        # whichever it picks into the switch
        keys += [('$t', '0.0'), ('$fps', '%.6f' % fps), ('$tf', '0.0'), ('$l', '0.0'), ('$one', '1'), ('$zero', '0')]
        if detail:
            keys += [('$b0', '%d.0' % frames), ('$lb', '0.0')]
        if first:
            keys += [('$c0', '%d.0' % first), ('$lc', '0.0')]
    out = '"UnlitGeneric"\n{\n' + ''.join(f'\t"{k}"\t"{v}"\n' for k, v in keys) + '\t"Proxies"\n\t{\n'

    def proxy(name, **kw):
        return f'\t\t"{name}"\n\t\t{{\n' + ''.join(f'\t\t\t"{k}"\t"{v}"\n' for k, v in kw.items()) + '\t\t}\n'
    if not split:
        out += proxy('AnimatedTexture', animatedtexturevar='$basetexture', animatedtextureframenumvar='$frame',
                     animatedtextureframerate='%g' % fps)
        return out + '\t}\n}\n'
    last = str(frames - 1)
    # L: the clock in frames, wrapped to the loop's length (an exact number of frames)
    out += proxy('CurrentTime', resultVar='$t')
    out += proxy('Multiply', srcVar1='$t', srcVar2='$fps', resultVar='$tf')
    out += proxy('WrapMinMax', srcVar1='$tf', minVal='0', maxVal=str(frames * parts), resultVar='$l')
    if first:  # the third part: frame L - first, shown once L reaches first
        out += proxy('Subtract', srcVar1='$l', srcVar2='$c0', resultVar='$lc')
        out += proxy('Clamp', srcVar1='$lc', min='0', max=last, resultVar='$frame')
        out += proxy('LessOrEqual', srcVar1='$c0', srcVar2='$l', lessEqualVar='$one', greaterVar='$zero',
                     resultVar='$alpha')
        return out + '\t}\n}\n'
    # the first part: frame L; the second: frame L - frames, faded in once L reaches frames (from then on the first
    # rests on its last frame, under the second; from the third part's start the second does, under the third)
    out += proxy('Clamp', srcVar1='$l', min='0', max=last, resultVar='$frame')
    if detail:
        out += proxy('Subtract', srcVar1='$l', srcVar2='$b0', resultVar='$lb')
        out += proxy('Clamp', srcVar1='$lb', min='0', max=last, resultVar='$detailframe')
        out += proxy('LessOrEqual', srcVar1='$b0', srcVar2='$l', lessEqualVar='$one', greaterVar='$zero',
                     resultVar='$detailblendfactor')
    return out + '\t}\n}\n'


GAME_MENU_ENTRY = '''
\t// The Reaper HUD: the main menu video's third part (resource/ui/mainmenuoverride.res, RK_MenuVideo). It is no
\t// button: listed here only at the menu, the game hides it in a game, as it hides the Background, so the ESC menu
\t// over a match shows the match
\t"RK_MenuVideo"
\t{
\t\t"label"\t\t\t""
\t\t"command"\t\t"engine echo"
\t\t"OnlyAtMenu"\t"1"
\t}
'''


def game_menu(work):
    """resource/gamemenu.res: the game's own (its main menu entries) with RK_MenuVideo added, a panel of ours that
    the main menu then shows only at the menu (CHudMainMenuOverride: an entry with OnlyAtMenu is hidden in a game
    or a replay). Only with a video in three parts, whose third part that panel plays (menu.mainmenu)."""
    src = os.path.join(work, 'resource', 'gamemenu.res')
    if menu.VIDEO_PARTS != 3 or not os.path.isfile(src):
        return
    text = open(src, encoding='utf-8', errors='replace').read().rstrip()
    assert text.endswith('}'), 'resource/gamemenu.res: no closing brace'
    write(os.path.join(OUT, 'resource', 'gamemenu.res'), text[:-1].rstrip() + '\n' + GAME_MENU_ENTRY + '}\n')


def menu_video():
    """Puts the menu video (made by tools/video.py) in place as the materials behind the main menu, played on a
    loop at the frame rate tools/video.py wrote next to it. One texture: mm_video, played by the AnimatedTexture
    proxy. Split over two or three: mm_video plays the first and the second (its detail texture, mm_video_b); with
    three, mm_video_c is the third, shown over them (on a panel of ours that the game hides in a game,
    menu.mainmenu and game_menu); video_vmt has how. The textures are already in place (tools/video.py writes them
    there and the build keeps them, kept_files): this writes their materials."""
    info = video_info()
    if info is None:
        return
    parts, fps, frames = info['parts'], info['fps'], info['frames']
    write(os.path.join(RK_DIR, 'mm_video.vmt'), video_vmt('mm_video', fps, frames, parts,
                                                          detail='mm_video_b' if parts > 1 else None))
    if parts == 3:
        write(os.path.join(RK_DIR, 'mm_video_c.vmt'), video_vmt('mm_video_c', fps, frames, parts, first=2 * frames))
    print(f"  menu video: {parts} x {frames} frames at {fps:g} fps ({frames * parts / fps:g} s) behind the main menu")
    loading_still()


def intro_video():
    """The game's startup video: media/valve.webm (tools/intro.py writes it there and the build keeps it,
    kept_files), which the game plays instead of its own (tf/media/startupvids.txt names media/valve.bik, and the
    64-bit game plays the WebM beside it, hl2/media/valve.webm; a tf/custom folder's comes first)."""
    if not os.path.isfile(INTRO):
        return
    # the list naming it outright, so the game finds ours whether it looks up the WebM by the .bik's name or beside
    # the .bik it found. A plain list of files: no credit line, which the game would take for a file
    with open(os.path.join(OUT, 'media', 'startupvids.txt'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('media/valve.webm\n')
    print(f'  startup video: media/valve.webm ({os.path.getsize(INTRO) / 2 ** 20:.1f} MB)')


def loading_still():
    """The loading screens (the game starting, a map loading) cannot move: they show the console background the
    chapterbackgrounds file names, here a frame of the menu video under the menu's own shade, so loading and menu
    look alike."""
    if not os.path.isfile(STILL):
        return
    img = np.asarray(Image.open(STILL).convert('RGB').resize((2048, 1024), Image.LANCZOS), np.float32)
    alpha = np.interp(np.linspace(0, 1, img.shape[1]), [0, 0.32, 0.6, 1], [0.62, 0.52, 0.25, 0.10])[None, :, None]
    img = img * (1 - alpha) + np.array(build_art.INK, np.float32) * alpha
    wide = Image.fromarray(np.clip(np.rint(img), 0, 255).astype(np.uint8), 'RGB')
    out = build_art.Out(OUT)
    out.console('background_reaper_video_widescreen', wide)
    h = wide.height
    out.console('background_reaper_video', wide.crop(((wide.width - h) // 2, 0, (wide.width + h) // 2, h)))


def game_tracks():
    """The game's menu music: every sound/ui/.../gamestartup*.mp3 or .wav in its sound VPKs and loose sound folders.
    The holidays have their own, as wav (gamestartup_halloween...), and the game plays those while one is on."""
    pat = re.compile(r'sound/ui/(?:[^/]+/)*gamestartup[^/]*\.(?:mp3|wav)')
    names = set()
    for pak in ('tf2_sound_misc', '../hl2/hl2_sound_misc'):
        path = os.path.join(vpk.TF, pak + '_dir.vpk')
        if os.path.isfile(path):
            names |= {k for k in vpk.read_vpk(path)[0] if pat.fullmatch(k)}
    for base in (vpk.TF, os.path.join(vpk.TF, '..', 'hl2')):
        top = os.path.join(base, 'sound', 'ui')
        for dirpath, _, files in os.walk(top):
            for f in files:
                rel = 'sound/ui/' + os.path.relpath(os.path.join(dirpath, f), top).replace('\\', '/').lower()
                if pat.fullmatch(rel):
                    names.add(rel)
    return names


def menu_music():
    """TF2 plays one of sound/ui/gamestartup*.mp3 at random when the main menu first loads, or a holiday's own wav
    while a holiday is on. With music/menu.mp3 (and music/menu.wav, the same music as ADPCM for the wav ones) in the
    project, every one of the game's tracks is replaced by it, so the HUD's music is the one that plays. Each is a
    hard link to the one file (a copy where links are not possible). Needs the game's files (an update.bat build);
    not in git (.gitignore), since the game's list of tracks can change with an update."""
    if not os.path.isfile(MUSIC):
        return
    if not os.path.isfile(os.path.join(vpk.TF, 'tf2_misc_dir.vpk')):
        print("  menu music: no game files here, so it is left out")
        return
    names = game_tracks()
    if not any(n.endswith('.mp3') for n in names):  # not where they used to be: cover the usual names
        names |= {f'sound/ui/gamestartup{i}.mp3' for i in range(1, 41)}
        print("  menu music: the game's own tracks were not found; using the usual names")
    wav = MUSIC[:-4] + '.wav'
    done = {'mp3': 0, 'wav': 0}
    for name in sorted(names):
        ext = name.rsplit('.', 1)[1]
        src = MUSIC if ext == 'mp3' else wav
        if not os.path.isfile(src):
            continue
        dst = os.path.join(OUT, *name.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy(src, dst)
        done[ext] += 1
    holiday = sorted(n.rsplit('/', 1)[1] for n in names if n.endswith('.wav'))
    print(f"  menu music: in place of the game's {done['mp3']} tracks and {done['wav']} holiday tracks"
          + (f" ({', '.join(holiday)})" if holiday else ''))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if path.endswith(('.res', '.txt')) and not text.startswith('//'):
        text = CREDIT + text
    with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(text)


ANIMS = r'''// The Reaper HUD - health / ammo feedback (loaded before hudanimations_tf.txt, so these win)

// overheal: the card's glow in the team's colour (RK_HealthFlash, a team picture) breathes; the digits stay white
event HudHealthBonusPulse
{
	Animate PlayerStatusHealthValue		FgColor	"RK_Text"	Linear 0.0 0.0
	Animate RK_HealthFlash	Alpha	"150"	Linear 0.0 0.35
	Animate RK_HealthFlash	Alpha	"30"	Linear 0.35 0.45
	RunEvent HudHealthBonusPulseLoop	0.8
}
event HudHealthBonusPulseLoop
{
	RunEvent HudHealthBonusPulse 0.0
}
event HudHealthBonusPulseStop
{
	StopEvent HudHealthBonusPulse 0.0
	StopEvent HudHealthBonusPulseLoop 0.0
	Animate PlayerStatusHealthValue		FgColor	"RK_Text"	Linear 0.0 0.0
	Animate RK_HealthFlash	Alpha	"0"	Linear 0.0 0.0
}

// low ammo: the digits flash amber, the card's hairline burns and LOW flickers over its label in the team's colour
// (RK_AmmoFlash)
event HudLowAmmoPulse
{
	Animate AmmoInClip		FgColor	"RK_Amber"	Linear 0.0 0.0
	Animate AmmoNoClip		FgColor	"RK_Amber"	Linear 0.0 0.0
	Animate RK_AmmoFlash	Alpha	"230"	Flicker 0.6 0.0 0.12
	Animate RK_AmmoFlash	Alpha	"40"	Linear 0.15 0.2
	Animate AmmoInClip		FgColor	"RK_Text"	Linear 0.2 0.15
	Animate AmmoNoClip		FgColor	"RK_Text"	Linear 0.2 0.15
	RunEvent HudLowAmmoPulseLoop	0.45
}
event HudLowAmmoPulseLoop
{
	RunEvent HudLowAmmoPulse 0.0
}
event HudLowAmmoPulseStop
{
	StopEvent HudLowAmmoPulse 0.0
	StopEvent HudLowAmmoPulseLoop 0.0
	Animate AmmoInClip		FgColor	"RK_Text"	Linear 0.0 0.0
	Animate AmmoNoClip		FgColor	"RK_Text"	Linear 0.0 0.0
	Animate RK_AmmoFlash	Alpha	"0"	Linear 0.0 0.0
}

// the top strip's slots (ingame.patch_matchstatus): the stock events slid the dead panel and the respawn seconds
// 19-21 units down, past the bottom of our 20-unit slot; here they stay on it, the cross fading in
event TeamStatus_PlayerDead
{
	SetVisible DeathPanel  0 0
	SetVisible SkullPanel  1 0
	SetVisible respawntime  1 0
	Animate SkullPanel ypos 0 Linear 0 0
	Animate respawntime ypos 1 Linear 0 0
	Animate SkullPanel Alpha 0 Linear 0 0
	Animate SkullPanel Alpha 255 Flicker 0.7 0 0.35
}
event TeamStatus_PlayerAlive
{
	SetVisible DeathPanel  0 0
	SetVisible SkullPanel  0 0
	SetVisible respawntime 0 0
	Animate SkullPanel ypos 0 Linear 0 0
	Animate respawntime ypos 1 Linear 0 0
}

'''


ANIMS_HITMARKER = r'''
// hitmarker (your damage on an enemy). Restarted through its own event: re-running DamagedPlayer on
// every hit would stack its animations (the well-known hitmarker lag)
event DamagedPlayer
{
	StopEvent RK_HitmarkerFlash 0.0
	RunEvent RK_HitmarkerFlash 0.0
}
event RK_HitmarkerFlash
{
	Animate RK_Hitmarker	Alpha	"255"	Linear 0.0 0.0
	Animate RK_Hitmarker	Alpha	"0"		Linear 0.08 0.22
}
'''

ANIMS_MENU = r'''
// voice / build menus (HudMenu): slide in from the left on open, slide back out and fade on close.
// Sits higher than stock so its bottom (0. Exit) ends above the top of the chat box, even with a full chat
event MenuOpen
{
	StopEvent MenuClose 0.0
	Animate HudMenu ypos			"-107"		Linear 0.0 0.0
	Animate HudMenu xpos			"-40"		Linear 0.0 0.0
	Animate HudMenu xpos			"0"			Deaccel 0.0 0.18
	Animate HudMenu Alpha			"255"		Linear 0.0 0.12
	Animate HudMenu SelectionAlpha	"255"		Linear 0.0 0.12
	Animate HudMenu FgColor			"FgColor"	Linear 0.0 0.12
	Animate HudMenu MenuColor		"MenuColor"	Linear 0.0 0.12
	Animate HudMenu ItemColor		"ItemColor"	Linear 0.0 0.12
	Animate HudMenu TextScan		"1"			Linear 0.0 0.12
	Animate HudMenu Blur			"1"			Linear 0.0 0.01
}
event MenuClose
{
	Animate HudMenu xpos			"-40"		Accel 0.0 0.16
	Animate HudMenu Alpha			"0"			Linear 0.0 0.16
	Animate HudMenu SelectionAlpha	"0"			Linear 0.0 0.16
	Animate HudMenu FgColor			"0 0 0 0"	Linear 0.0 0.16
	Animate HudMenu MenuColor		"0 0 0 0"	Linear 0.0 0.16
	Animate HudMenu ItemColor		"0 0 0 0"	Linear 0.0 0.16
}
'''

# ------------------------------------------------------------------ respawn card, menus, objectives
SPEC_HINTS = ('ClassOrTeamLabel', 'SwitchCamModeKeyLabel', 'SwitchCamModeLabel', 'CycleTargetFwdKeyLabel',
              'CycleTargetFwdLabel', 'CycleTargetRevKeyLabel', 'CycleTargetRevLabel', 'TipLabel')
SPEC_KEYS = re.compile(r'SwitchCamMode|CycleTarget|ClassOrTeam', re.I)  # key hint labels (+ controller icons)


def patch_spectator(root):
    """Spectator / death screen (spectator.res, spectatortournament.res).
    - The black letterbox bars are gone. The game shows them again in code on every scheme load and only sizes them
      from the file (the top bar keeps its tall, the bottom one runs from its ypos to the screen bottom), so they
      are shrunk to nothing instead of hidden.
    - The key hints, map name and tip that sat on the bars get outlined lettering so they read over the map.
    - "Respawn in X seconds" sits on a card that is the label's own border: the game hides the label
      whenever there is no respawn timer (spectator team, freezecam), and the card goes with it."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for name, vals in (('topbar', dict(tall=0, visible=0)),
                       ('BottomBar', dict(ypos=9999, wide=0, tall=0, visible=0)),
                       ('bottombarblank', dict(ypos='r0', tall=0, visible=0))):
        blk = kv.find(body, name)
        if blk is not None:
            kv.setmany(blk, **vals)
    for name in SPEC_HINTS:
        blk = kv.find(body, name)
        if blk is not None:
            kv.set(blk, 'font', 'RK_SpecHint')
    blk = kv.find(body, 'MapLabel')
    if blk is not None:
        kv.set(blk, 'font', 'RK_SpecMap')
    # the camera key hints were on the top bar: without it they ran over the engineer's building cards (top left, also
    # shown while dead), so the group moves to the bottom left and ends right above the tip (r67). Only the stock
    # top-left group moves (numeric ypos), not the centred "change class" line
    group = [e[1] for e in body if isinstance(e[1], list) and SPEC_KEYS.search(e[0])
             and not (kv.get(e[1], 'xpos') or 'c').lower().startswith(('c', 'r'))
             and (kv.get(e[1], 'ypos') or '').isdigit()]
    if group:
        bottom = max(int(kv.get(b, 'ypos')) + int(kv.get(b, 'tall') or 0) for b in group)
        for b in group:
            kv.set(b, 'ypos', 'r%d' % (70 + bottom - int(kv.get(b, 'ypos'))))
    kv.remove(body, 'RK_RespawnCard')  # older builds drew the card as a separate (always visible) image
    lbl = kv.find(body, 'ReinforcementsLabel')
    if lbl is None:
        return
    # the game creates this one as a plain vgui Label: fgcolor_override, not fgcolor. The card ends above the
    # game's "Press [ , ] to Change Class" line (ypos 68)
    kv.remove(lbl, 'fgcolor')
    kv.setmany(lbl, xpos='c-160', ypos=37, wide=320, tall=29, zpos=2, font='RK_NoticeTitle', fgcolor_override='RK_Text',
               textAlignment='center', paintbackground=0, paintborder=1, border='RK_RespawnCard')


MENU_DIRS = ('resource/ui/build_menu/', 'resource/ui/destroy_menu/', 'resource/ui/disguise_menu/',
             'resource/ui/hudmenutauntselection')  # the taunt menu (G) is built like them
MENU_TEXT = {'tandarker': '236 232 232 255', 'redsolid': '200 196 198 255'}  # no crimson text: BLU stays blue (the card's tone shows the state)
MENU_ICONS = {'hud_menu_bg': 'menu_bg'}
MENU_STATES = (('cant_afford', 'red'), ('already_built', 'dim'), ('unavailable', 'dim'), ('inactive', 'dim'))
BOX = ('xpos', 'ypos', 'wide', 'tall')


def patch_menu(root, rel):
    """Engineer build / destroy and spy disguise menus. Their tan backgrounds and slot cards are icons from the
    game's texture list (CIconPanel), so they are hidden and art is laid in their place: ink sheet, slot
    cards toned by state (crimson ready, grey built / unavailable, crimson not enough metal). The key chips are such
    icons too: hidden, and each number label carries an crimson chip as its own border (RK_KeyChip). The game shows
    and hides chips and numbers separately (the disguise menu's simple mode switches them per step), so a chip of its
    own showed up empty, or covered its number."""
    body = next((e[1] for e in root if isinstance(e[1], list)), None)
    if body is None or '/pipboy/' in rel:  # the PDA skin's menus keep their own art
        return
    state = next((st for key, st in MENU_STATES if key in rel.split('/')[-1]), 'on')
    chips = {}  # chip box by name suffix: NumberBg -> NumberLabel / NewNumberLabel, NumberBg1 -> NumberLabel1
    for ent in list(body):
        blk = ent[1]
        if not isinstance(blk, list):
            continue
        icon = (kv.get(blk, 'icon') or '').lower()
        if icon == 'ico_key_blank':
            if kv.get(blk, 'wide') != '0':
                chips[ent[0].lower()[len('numberbg'):]] = [kv.get(blk, key) for key in BOX]
            kv.setmany(blk, wide=0, tall=0)
            continue
        img = MENU_ICONS.get(icon) or ('menu_item_' + state if icon.startswith('hud_menu_item_bg') else None)
        if ent[0] == 'Divider':
            # a fill colour cannot follow the team: the rule is the team picture laid in its place, the stock line
            # hidden (BLU had a crimson line under the menu's head)
            dx, dy, dw = (kv.get(blk, k) or '0' for k in ('xpos', 'ypos', 'wide'))
            kv.setmany(blk, tall=0, visible=0)
            kv.add_block(body, 'RK_MenuRule', ingame.timg('RK_MenuRule', dx, dy, dw, 2, 'notice_rule', z=2))
        if img is None or kv.get(blk, 'visible') == '0':
            continue
        x, y, w, h, z = (kv.get(blk, key) or '0' for key in BOX + ('zpos',))
        kv.setmany(blk, visible=0, wide=0, tall=0)
        # the sheet and the slot cards in the local player's team colour
        kv.add_block(body, 'RK_' + ent[0], ingame.timg('RK_' + ent[0], x, y, w, h, img, z=z))
    for ent in body:  # the numbers move onto their chip's box (the engineer menus centre them across the slot)
        name = ent[0].lower()
        if isinstance(ent[1], list) and 'numberlabel' in (kv.get(ent[1], 'fieldName') or name).lower():
            chip = chips.get(name[name.find('numberlabel') + len('numberlabel'):])
            if chip:
                kv.setmany(ent[1], **dict(zip(BOX, chip)))
            kv.setmany(ent[1], zpos=5, border='RK_KeyChip', paintborder=1)
    # the metal cost and mode lines: the stock cards were tan, so a ready card wrote them near black (TanDarker),
    # which vanished on our toned cards; light now, and the not-enough-metal red a hot one that reads on dark
    for ent in kv.walk(body):
        if isinstance(ent[1], list):
            continue
        if ent[0].lower() in ('fgcolor', 'fgcolor_override', 'iconcolor'):
            ent[1] = MENU_TEXT.get(ent[1].lower(), ent[1])


def patch_taunt_menu(root):
    """The taunt menu (G) on top of patch_menu's ink sheet and key chips: the film reel icon gone, TAUNT in the
    HUD's title face from the left edge without its drop shadow, the two hint lines in the notice face."""
    body = next((e[1] for e in root if isinstance(e[1], list)), None)
    if body is None:
        return
    for n in ('IcoReelIcon', 'TitleLabelDropshadow'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, visible=0, wide=0, tall=0)
    title = kv.find(body, 'TitleLabel')
    if title is not None:
        kv.setmany(title, xpos=17, ypos=20, tall=28, font='RK_Title', fgcolor='236 232 232 255', allcaps=1)
    for n, col in (('WeaponTauntLabel', '200 196 198 255'), ('CancelLabel', '200 196 198 255')):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, font='RK_NoticeBody', fgcolor=col)


def patch_disguise_status(root):
    """The "disguised as" box on a notice card (team tone of the disguise)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    bg = kv.find(body, 'DisguiseStatusBG')
    if bg is None:
        return
    kv.setmany(bg, image=T + 'disguise_card', teambg_1=T + 'disguise_card', teambg_2=T + 'disguise_card',
               teambg_3=T + 'disguise_card', src_corner_width=40, src_corner_height=40, draw_corner_width=5,
               draw_corner_height=5)
    for key in ('teambg_2_lodef', 'teambg_3_lodef'):
        kv.remove(bg, key)


def patch_escort(root):
    """Payload track on a strip (single cart; the multi-cart layout keeps the stock look)."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    if kv.find(body, 'LevelBar') is None:
        return
    strip = kv.add_block(body, 'RK_EscortStrip', ingame.timg('RK_EscortStrip', 50, 106, 300, 40, 'escort_strip',
                                                             z=-1))
    strip.append(['if_multiple_trains', [['visible', '0', None], ['wide', '0', None]], None])
    # the cart's pin a little higher: its point stopped on the home and checkpoint rings (the game only moves the
    # panel sideways; the multi-cart layout keeps its own height)
    item = kv.find(body, 'EscortItemPanel')
    if item is not None:
        kv.set(item, 'ypos', 2)


def patch_cp_progress(root):
    """Capture progress ring gets a ink rim instead of the tan teardrop."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    for n in ('Teardrop', 'TeardropSide'):
        blk = kv.find(body, n)
        if blk is not None:
            kv.setmany(blk, visible=0, wide=0, tall=0)
    kv.add_block(body, 'RK_CpRim', ingame.timg('RK_CpRim', 22, -1, 57, 57, 'cp_rim', z=21))


def unpin(node):
    """A panel pinned to its parent's right or bottom edge (pinCorner 1-3) keeps its distance to that edge as it was
    when its settings were read: when the parent's size changes after that (the game's resolution changed, a page
    sized by the code), it moves, off the place this HUD gave it (the loadout's ITEMS / TAUNTS, 300 px up at
    1920 x 1080). In the files the HUD ships, every panel that does not also resize with its parent is pinned top
    left: where its xpos and ypos say."""
    n = 0
    for _, val, _ in node:
        if isinstance(val, list):
            pin = str(kv.get(val, 'pinCorner', '0')).strip()
            if pin in ('1', '2', '3') and str(kv.get(val, 'autoResize', '0')).strip() == '0':
                kv.set(val, 'pinCorner', 0)
                n += 1
            n += unpin(val)
    return n


def stock_files(work):
    """Fill work/ with the game's stock UI files and the class / objective art the textures are drawn from: from
    --stock DIR (an extracted copy), or from TF2's VPKs. Returns (UI files found, folder holding materials/)."""
    if '--stock' in sys.argv:
        src = sys.argv[sys.argv.index('--stock') + 1]
        n = 0
        for dirpath, _, files in os.walk(src):
            for fn in files:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, src).replace('\\', '/').lower()
                if rel.startswith(('resource/', 'scripts/', 'materials/')):
                    dst = os.path.join(work, *rel.split('/'))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy(full, dst)
                    n += not rel.startswith('materials/')
        return n, work
    if not os.path.isfile(os.path.join(vpk.TF, 'tf2_misc_dir.vpk')):  # update.bat shows this and stops
        sys.exit(f"TF2's game files are not in {vpk.TF}\n"
                 'Put this HUD folder into ...\\Team Fortress 2\\tf\\custom and run update.bat from there.')
    vpk.extract('../hl2/hl2_misc', ['resource/ui/basechat.res'], work)
    n = vpk.extract('tf2_misc', ['resource/*.res', 'resource/ui/*.res', 'resource/ui/*/*.res',
                                 'resource/ui/*/*/*.res', 'resource/ui/*/*/*/*.res', 'scripts/hudlayout.res',
                                 'scripts/hudanimations_manifest.txt'], work)
    pdir = os.path.join(work, 'tex')
    vpk.extract('tf2_textures', ['materials/vgui/class_portraits/*.vtf', 'materials/vgui/class_sel_sm_*.vtf',
                                 'materials/sprites/obj_icons/*.vtf', 'materials/hud/objectives_flagpanel*.vtf'], pdir)
    return n, pdir


def main():
    video = video_info()
    menu.VIDEO = video is not None  # the main menu puts the video behind it when there is one
    menu.VIDEO_PARTS = video['parts'] if video else 0
    menu.VIDEO_SHADED = bool(video and video.get('shade'))
    install = '--install' in sys.argv
    work = tempfile.mkdtemp(prefix='rk_stock_')
    n, pdir = stock_files(work)
    print(f'extracted {n} stock files')
    keep = kept_files(video)
    for entry in HUD_PARTS:  # only the HUD parts: tools/, docs/, README... stay; in them, the videos (kept_files)
        clear(os.path.join(OUT, entry), keep)

    custom = {
        'resource/ui/hudplayerhealth.res': lambda root: (ingame.patch_health(root), blackwall.patch_health(root),
                                                          extras.crosshair_panel(root, extras.crosshair_pick(OUT, vpk.TF)),
                                                          minmode.health(root)),
        'resource/ui/hudplayerclass.res': lambda root: (ingame.patch_class(root), minmode.player_class(root),
                                                         blackwall.patch_class(root)),
        'resource/ui/hudammoweapons.res': lambda root: (ingame.patch_ammo(root), minmode.ammo(root)),
        'resource/ui/huddamageaccount.res': ingame.patch_damage,
        'resource/ui/mainmenuoverride.res': lambda root: menu.mainmenu(root, screens.hud_settings_popup),
        'resource/ui/matchmakingdashboard.res': menu.dashboard,
        'resource/ui/steamfriendpanel.res': menu.patch_friend,
        'resource/ui/dashboardpartymember.res': menu.patch_party_member,
        'resource/ui/classselection.res': menu.classselection,
        'resource/ui/charinfopanel.res': screens.charinfo,
        'resource/ui/charinfoloadoutsubpanel.res': screens.loadout_sub,
        'resource/ui/classloadoutpanel.res': loadout.class_loadout,
        'resource/ui/loadoutpresetpanel.res': loadout.preset_panel,
        'resource/ui/econ/backpackpanel.res': screens.backpack,
        'resource/ui/itemselectionpanel.res': screens.item_selection,
        'resource/ui/craftingpanel.res': screens.crafting,
        'resource/ui/craftingstatusdialog.res': screens.crafting_dialog,
        'resource/ui/newrecipefounddialog.res': screens.crafting_dialog,
        'resource/ui/votehud.res': extras.vote,
        'resource/ui/scoreboard.res': screens.scoreboard,
        'scripts/hudlayout.res': lambda root: (patch_hudlayout(root), minmode.layout(root)),
        'resource/ui/hudaccountpanel.res': ingame.patch_account,
        'resource/ui/huditemeffectmeter_killstreak.res': lambda root: (ingame.patch_killstreak(root), minmode.killstreak(root)),
        'resource/ui/teammenu.res': menu.teammenu,
        'resource/ui/hudobjectiveflagpanel.res': patch_flagpanel,
        'resource/ui/flagstatus.res': patch_flagstatus,
        'resource/ui/basechat.res': ingame.patch_chat,
        'resource/ui/statsummary.res': screens.statsummary,
        'resource/ui/spectatorguihealth.res': ingame.patch_spec_health,
        'resource/ui/spectatortournamentguihealth.res': ingame.patch_tournament_health,
        'resource/ui/healthiconpanel.res': ingame.patch_health_icon,
        'resource/ui/freezepanelkillerhealth.res': patch_killer_health,
        'resource/ui/huddemomanpipes.res': ingame.patch_pipes,
        'resource/ui/huddemomancharge.res': ingame.patch_charge,
        'resource/ui/hudbowcharge.res': ingame.patch_charge,
        'resource/ui/hudflamerocketcharge.res': ingame.patch_charge,
        'resource/ui/hudmediccharge.res': lambda root: (ingame.patch_uber(root), blackwall.patch_uber(root)),
        'resource/ui/hudkillstreaknotice.res': patch_streak_notice,
        'resource/ui/hudmatchstatus.res': lambda root: (ingame.patch_matchstatus(root), extras.match_doors(root)),
        'resource/ui/hudobjectivetimepanel.res': ingame.patch_timepanel,
        'resource/ui/hudroundcounter.res': ingame.patch_roundcounter,
        'resource/ui/hudobjectivekothtimepanel.res': ingame.patch_koth_timers,
        'resource/ui/winpanel.res': screens.winpanel,
        'resource/ui/freezepanel_basic.res': patch_freezepanel,
        'resource/ui/invitenotification.res': patch_invite,
        'resource/ui/statpanel_base.res': patch_statpanel,
        'resource/ui/hudtournament.res': patch_tournament,
        'resource/ui/targetid.res': ingame.patch_targetid,
        'resource/ui/mapinfomenu.res': menu.mapinfo,
        'resource/ui/textwindow.res': menu.textwindow,
        'resource/ui/textwindow_sc.res': menu.textwindow,
        'resource/ui/textwindowcustomserver.res': menu.textwindow,
        'resource/ui/textwindowcustomserver_sc.res': menu.textwindow,
        'resource/ui/spectator.res': patch_spectator,
        'resource/ui/spectatortournament.res': patch_spectator,
        'resource/ui/spectator_sc.res': patch_spectator,  # Steam Controller variant
        'resource/ui/disguisestatuspanel.res': patch_disguise_status,
        'resource/ui/objectivestatusescort.res': patch_escort,
        'resource/ui/controlpointprogressbar.res': patch_cp_progress,
        'resource/ui/hudrocketpack.res': patch_rocketpack,
        'resource/ui/hudinspectpanel.res': patch_inspect,
        'resource/ui/huditemattributetracker.res': patch_tracker,
        'resource/ui/pvprankpanel.res': menu.patch_rank,
        **extras.RES,  # notification toasts, the casual match summary, MvM
    }
    medic = os.path.join(work, 'resource', 'ui', 'hudmediccharge.res')
    if not os.path.exists(medic):
        write(medic, STOCK_MEDIC)
    killer = os.path.join(work, 'resource', 'ui', 'freezepanelkillerhealth.res')
    if not os.path.exists(killer):  # laid out from scratch anyway (patch_killer_health)
        write(killer, '"Resource/UI/FreezePanelKillerHealth.res"\n{\n}\n')
    flame = os.path.join(work, 'resource', 'ui', 'hudflamerocketcharge.res')
    if not os.path.exists(flame):  # the Dragon's Fury's charge-up loads this one; laid out by ingame.patch_charge
        write(flame, '"Resource/UI/HudFlameRocketCharge.res"\n{\n\t"ChargeMeter"\n\t{\n'
                     '\t\t"ControlName"\t"ContinuousProgressBar"\n\t\t"fieldName"\t"ChargeMeter"\n\t}\n}\n')
    shipped = 0
    for dirpath, _, files in os.walk(work):
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, work).replace('\\', '/').lower()
            if not rel.endswith('.res') or rel in ('resource/clientscheme.res', 'resource/sourcescheme.res',
                                                  'resource/chatscheme.res'):
                continue
            text = open(full, encoding='utf-8', errors='replace').read()
            root = kv.parse(text)
            changed = reskin_res(root)
            changed |= strip_minmode(root)
            changed |= recolor_logos(root)
            if METER_FILE.search(rel) and not rel.endswith('killstreak.res'):  # first: the card patches refine it
                patch_meter_style(root)
                changed = True
            if rel in custom:
                custom[rel](root)
                changed = True
            elif rel.startswith('resource/ui/hud_obj_'):
                patch_building(root, rel)
                changed = True
            elif rel.startswith('resource/ui/notifications/'):
                patch_notification(root, rel)
                changed = True
            elif rel in NOTICES:
                patch_notice(root, rel)
                changed = True
            elif rel.startswith(('resource/ui/huditemeffectmeter', 'resource/ui/hudpowerupeffectmeter')):
                # hudpowerupeffectmeter: Mannpower's powerup charge, a meter like the others (the stock file had it
                # over the health card's foot)
                ingame.patch_meter(root, rel)
                changed = True
            elif screens.DIALOG_FILE.match(rel):
                screens.confirm_dialog(root)
                changed = True
            elif rel.startswith(MENU_DIRS):
                patch_menu(root, rel)
                if 'tauntselection' in rel:
                    patch_taunt_menu(root)
                changed = True
            if changed:
                unpin(root)
                write(os.path.join(OUT, rel), kv.dump(root) + '\n')
                shipped += 1
    print(f'  res files shipped: {shipped}')

    write(os.path.join(OUT, 'resource/clientscheme.res'),
          build_scheme(open(os.path.join(work, 'resource/clientscheme.res'), encoding='utf-8', errors='replace').read()))
    ss = os.path.join(work, 'resource/sourcescheme.res')
    if os.path.exists(ss):  # GameUI dialogs (loading window...) take their colours from here
        write(os.path.join(OUT, 'resource/sourcescheme.res'),
              retint_scheme(open(ss, encoding='utf-8', errors='replace').read()))
    os.makedirs(os.path.join(OUT, 'resource', 'fonts'), exist_ok=True)
    for f in SHIPPED_FONTS + ('OFL.txt',):
        shutil.copy(os.path.join(HERE, 'fonts', f), os.path.join(OUT, 'resource', 'fonts', f))
    write(os.path.join(OUT, 'scripts/hudanimations_rk.txt'), ANIMS + blackwall.ANIMS + ingame.CHAT_ANIMS + ANIMS_HITMARKER + ANIMS_MENU)
    write(os.path.join(OUT, 'scripts/hudanimations_manifest.txt'),
          'hudanimations_manifest\n{\n\t"file"\t\t"scripts/hudanimations.txt"\n'
          '\t"file"\t\t"scripts/hudanimations_rk.txt"\n\t"file"\t\t"scripts/hudanimations_tf.txt"\n}\n')
    bg = 'background_reaper_video' if os.path.isfile(STILL) else 'background_reaper'  # see loading_still
    bgs = '\n'.join(f'\t{i}\t"{bg}"' for i in range(1, 5))
    write(os.path.join(OUT, 'scripts/chapterbackgrounds.txt'),
          f'"chapters"\n{{\n{bgs}\n}}\n"BackgroundMaps"\n{{\n{bgs}\n}}\n')
    if menu.VIDEO:
        # the main menu's class picture (TFCharacterImage) is the shade over the video (menu.mainmenu): the game
        # picks that picture from this file and hides the panel in a game. With the shade in the video's frames
        # (tools/video.py --shade) the panel shows nothing
        pic = 'blank' if menu.VIDEO_SHADED else 'mm_video_shade'
        write(os.path.join(OUT, 'scripts/characterbackgrounds.txt'),
              '"CharacterBackgrounds"\n{\n\t"reaper_shade"\n\t{\n\t\t"image"\t"replay/thumbnails/rk/%s"\n'
              '\t\t"weight"\t"1"\n\t}\n}\n' % pic)
    game_menu(work)
    write(os.path.join(OUT, 'info.vdf'), f'"{HUD_NAME}"\n{{\n\t"ui_version"\t"3"\n}}\n')

    print('  generating artwork...')
    build_art.build(OUT, portraits=pdir)
    loadout.sounds(OUT)  # the loadout page's button sounds
    own = extras.crosshair_own(OUT, vpk.TF)  # the player's own crosshair, for HUD Settings' MINE
    print('  own crosshair kept: ' + ((own['cl_crosshair_file'] or 'the weapons\' own') if own else 'none yet'))
    print('  crosshair: ' + (extras.crosshair_pick(OUT, vpk.TF) or 'the game\'s own'))
    blackwall.sounds(OUT, vpk.TF)  # the Blackwall's sounds (near death, ÜberCharge full, the kill sound)
    redirect_objective_materials()
    menu_video()
    intro_video()
    prune_textures()
    menu_music()
    shutil.rmtree(work, ignore_errors=True)
    print('built ->', OUT)

    if install:
        dst = os.path.join(vpk.TF, 'custom', HUD_NAME)
        remove_other_copies(OUT if IN_CUSTOM else dst)
        if IN_CUSTOM:  # already in tf/custom: the build above was the install
            dst = OUT
        else:
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            os.makedirs(dst)
            for entry in HUD_PARTS + ('README.txt', 'LICENSE.txt'):
                src = os.path.join(OUT, entry)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(dst, entry))
                elif os.path.exists(src):
                    shutil.copy(src, os.path.join(dst, entry))
        print('installed ->', dst)
        set_desktop_icon(os.path.join(dst, 'resource', 'game.ico'))


def is_our_install(path):
    vdf = os.path.join(path, 'info.vdf')
    return os.path.isfile(vdf) and HUD_NAME in open(vdf, encoding='utf-8', errors='replace').read()


def remove_other_copies(keep):
    """Two copies of the HUD in tf/custom load together and mix their files (counters drawn from one copy's
    layout with the other's panels go missing or land off screen). Plain installed copies (an older
    custom/reaper-hud, an extra ZIP folder) are removed; a project folder (with .git or tools) is only
    reported, since it may hold someone's work."""
    custom = os.path.join(vpk.TF, 'custom')
    if not os.path.isdir(custom):
        return
    for entry in sorted(os.listdir(custom)):
        p = os.path.join(custom, entry)
        if not os.path.isdir(p) or os.path.normcase(os.path.abspath(p)) == os.path.normcase(os.path.abspath(keep)):
            continue
        if not is_our_install(p):
            continue
        if os.path.exists(os.path.join(p, '.git')) or os.path.isdir(os.path.join(p, 'tools')):
            print('WARNING: another The Reaper HUD folder is in tf/custom and loads together with this one:', p)
            print('         delete one of them (keep the one you run update.bat in), then restart TF2.')
        else:
            shutil.rmtree(p)
            print('removed another copy of the HUD (two copies mix their files) ->', p)


def set_desktop_icon(ico):
    """Point the Steam desktop shortcut at the HUD's icon (original line kept as a comment)."""
    url = os.path.join(os.path.expanduser('~'), 'Desktop', 'Team Fortress 2.url')
    if not os.path.exists(url):
        return
    lines = open(url, encoding='utf-8', errors='replace').read().splitlines()
    if not any(l.startswith(';orig ') for l in lines):
        lines += [';orig ' + l for l in lines if l.startswith('IconFile=')]
    lines = ['IconFile=' + ico if l.startswith('IconFile=') else l for l in lines]
    open(url, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('desktop shortcut icon ->', ico)


if __name__ == '__main__':
    term.colours()
    main()
