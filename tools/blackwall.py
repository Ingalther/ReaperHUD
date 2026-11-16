"""The Blackwall breaks through: the low-health glitch after Cyberpunk 2077's own (p_health_low.effect and the
materials and particles it uses, read from the game into the cp2077-pack branch, whose README describes them) and the
Blackwall Gateway's sounds.

When: TF2 starts HudHealthDyingPulse once when health falls under HealthDeathWarning x max health and
HudHealthDyingPulseStop when it climbs back (tf_hud_playerstatus.cpp). THRESHOLD is the game's 49 % (Cyberpunk's is
40 %). Nothing tells a HUD how far under it health is, so the glitch runs at one strength, Cyberpunk's at about a
fifth of the health. HudMedicCharged starts once when the ÜberCharge is full and HudMedicChargedStop when it
has been spent (tf_hud_mediccharge.cpp); the game tells a HUD nothing when the Medic deploys it.

What (ANIMS):
- on the way under, the Blackwall's hit (ui/rk/bw_lowhealth.wav, once) and a burst of its glyph strips;
- then Cyberpunk's 1 s cycle until health climbs back: the stepped magenta-crimson vignette with its glitch bars and
  data text, in three slices that jump sideways four times a second (low_health.mt: Rows 3, OffsetChangeSpeed 4);
  glitch blocks popping in the top band and the outer lower corners for 0.2-0.8 s (p_health_low_emission_rate); the
  HUD kick once a second, the card's critical overlay and the digits' red and cyan copies flashing hard and dying away
  over the second (the effect's HudParameter glitchParameter); a thin glyph line now and then; code scrolling up two
  columns at the sides (blackwall_onscreen_assembly);
- ÜberCharge full: the Gateway's sound (ui/rk/bw_uber.wav, once) and its glyphs bursting over the ÜBER strip, then the
  strip's READY loop as before.
Everything but the digits' red and cyan copies is in the team's colour (team pictures: crimson on RED, azure on BLU).

Where: the health panel is the whole screen (ingame.patch_health), so the screen-wide layers are its children. The
ÜBER strip's panel is the strip: the game puts the Vaccinator's resist icon at its 0, 0, so it cannot grow, and the
Gateway's burst stays on it.

Sound: TF2 plays it through the animation's PlaySound (vgui's surface PlaySound, a 2D sound). The game's own files are
in tools/sounds, cut by make_sounds; the build copies them to sound/ui/rk. Valve's servers (sv_pure) may refuse
sounds from a HUD; a copy also sits in the one folder they load a HUD's pictures from, to try (see the README).
"""
import os
import random
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

import kv
import ingame as G
from build_art import THUMB, linear_alpha, to_blue
from vtf import write_vtf

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'art', 'cp2077')   # Cyberpunk 2077's textures used here (from the cp2077-pack branch)
SND = os.path.join(HERE, 'sounds')          # the cut sounds (make_sounds); sounds() puts them in the HUD
T = 'replay/thumbnails/rk/'
PX = 2.25

THRESHOLD = '0.49'      # HudPlayerHealth's HealthDeathWarning (the game's own)
VIG = (176, 6, 58)      # low_health.mt's VignetteColor (164, 0, 78), kept inside crimson's hues for BLU's azure twin
VIG_DEEP, VIG_HOT = (70, 4, 22), (255, 120, 150)
TEXT = (210, 40, 60)    # FluffTextColor (185, 38, 38), brighter: ours is drawn over the scene, not mixed into it
BLOCK = ((40, 3, 9), (150, 12, 39), (255, 80, 40), (255, 190, 150))   # screen_glitch.mt's ArtifactColor to orange
GLYPH = (255, 88, 128)  # blackwall_onscreen.mt's Color
SLICES = 3              # Rows 3: the vignette's slices, each a third of the screen's height
SLIDE = 14              # they reach this far past both sides of the screen; they jump up to that far
CYCLE = 1.0             # the effect's loop, s

# the glitch blocks: (zone, x, y, w, h) in units; x 'cN' from the screen's centre, 'rN' from its right edge, a
# number from its left. Cyberpunk's three emitters: a band along the top (here below TF2's timer strip and right of
# the centre) and the two lower corners (here their outer edges, clear of the health and ammo cards)
BLOCKS = [('top', 'c40', 52, 30, 9), ('top', 'c96', 64, 44, 7), ('top', 'c150', 48, 18, 11), ('top', 'c205', 70, 36, 8),
          ('top', 'c262', 56, 24, 12), ('top', 'c120', 84, 14, 6), ('left', 4, 262, 22, 18), ('left', 10, 318, 14, 14),
          ('left', 2, 372, 28, 10), ('left', 16, 412, 12, 22), ('right', 'r30', 248, 26, 14),
          ('right', 'r20', 300, 16, 16), ('right', 'r36', 356, 30, 10), ('right', 'r18', 404, 14, 20)]
# the Blackwall's glyph strips (blackwall_onscreen_mid and _extreme): x from the centre, width (inside +-300, so a
# 4:3 screen shows them all); the thin ones also flash alone now and then
STRIPS = [('c-300', 56), ('c-188', 4), ('c-150', 2), ('c140', 3), ('c226', 42)]
THIN = (2, 3, 4)        # indices of the thin strips
CODE = (('RK_BWCodeL', 'c-326', 22), ('RK_BWCodeR', 'c304', 22))      # the scrolling code columns


def _load(name, mode='RGBA'):
    return Image.open(os.path.join(SRC, name)).convert(mode)


def _ramp(t, stops):
    """t (0..1 array) -> RGB along stops, evenly spaced colours."""
    stops = np.asarray(stops, np.float32)
    pos = np.linspace(0, 1, len(stops))
    return np.stack([np.interp(t, pos, stops[:, i]) for i in range(3)], -1)


def _over(dst, rgb, a):
    """Composite (rgb, a) over dst (straight alpha, float RGBA in 0..1 / 0..255)."""
    out_a = a + dst[..., 3] * (1 - a)
    safe = np.where(out_a > 1e-6, out_a, 1)
    dst[..., :3] = (rgb * a[..., None] + dst[..., :3] * (dst[..., 3] * (1 - a))[..., None]) / safe[..., None]
    dst[..., 3] = out_a


def _img(a):
    a = a.copy()
    a[..., 3] *= 255
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')


# ------------------------------------------------------------------ art
def vignette():
    """The screen's glitch (low_health.mt over a full-screen quad), 1024 x 576: the vignette in 15 hard steps
    (VignetteSteps), Cyberpunk's glitch bars (FluffPattern) and data columns (FluffText) showing through it toward the
    edges, scan lines. Weaker toward the bottom edge, where TF2's cards are."""
    W_, H_ = 1024, 576
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    u = (xx + 0.5) / W_ * 2 - 1
    v = (yy + 0.5) / H_ * 2 - 1
    r = np.sqrt(u * u + (v * np.where(v < 0, 0.95, 0.62)) ** 2)
    m = np.clip((r - 0.68) / 0.66, 0, 1)
    m = m * m * (3 - 2 * m)
    steps = np.floor(m * 15) / 15
    out = np.zeros((H_, W_, 4), np.float32)
    _over(out, np.broadcast_to(np.array(VIG, np.float32), (H_, W_, 3)), steps * 0.72)
    pat = np.asarray(_load('fx_fluff_pattern_d.png').resize((W_, H_), Image.LANCZOS), np.float32) / 255
    lum = pat[..., :3].max(-1)
    _over(out, _ramp(lum, (VIG_DEEP, VIG, VIG_HOT)), np.clip(lum * 1.4, 0, 1) * m ** 0.9 * 0.8)
    txt = np.asarray(_load('fx_fluff_text_r.png', 'L').resize((W_, H_), Image.LANCZOS), np.float32) / 255
    _over(out, np.broadcast_to(np.array(TEXT, np.float32), (H_, W_, 3)), np.clip(txt * 1.3, 0, 1) * m * 0.75)
    out[(np.arange(H_) % 3) == 0, :, 3] *= 0.7
    return _img(out)


def slices(img):
    h = img.height // SLICES
    return [img.crop((0, i * h, img.width, (i + 1) * h)) for i in range(SLICES)]


def blocks(n=4, seed=11):
    """Glitch blocks (screen_glitch.mt's artifacts): pieces of Cyberpunk's glitch bars in its artifact red going to
    orange, a hot top edge, their red and cyan copies slipped either side; 128 x 64 each, stretched to their boxes."""
    pat = np.asarray(_load('fx_fluff_pattern_d.png'), np.float32) / 255
    lum_all = pat[..., :3].max(-1)
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < n:
        w, h = int(rng.integers(96, 260)), int(rng.integers(40, 120))
        x, y = int(rng.integers(0, 1024 - w)), int(rng.integers(0, 1024 - h))
        lum = lum_all[y:y + h, x:x + w]
        if lum.mean() < 0.22:          # mostly empty: try elsewhere
            continue
        lum = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).resize((128, 64), Image.LANCZOS),
                         np.float32) / 255
        a = np.zeros((64, 128, 4), np.float32)
        _over(a, np.broadcast_to(np.array(BLOCK[1], np.float32) * 0.5, (64, 128, 3)), np.full((64, 128), 0.55))
        _over(a, _ramp(lum, BLOCK), np.clip(0.35 + lum, 0, 1))
        a[:3, :, :3] = BLOCK[3]
        a[:3, :, 3] = 1
        res = np.zeros_like(a)
        for dx, col, al in ((-4, G.SPLIT_R, 0.43), (4, G.SPLIT_C, 0.35)):
            ghost = np.zeros_like(a)
            ghost[..., :3] = col
            ghost[..., 3] = np.roll(a[..., 3], dx, axis=1) * al
            _over(res, ghost[..., :3], ghost[..., 3])
        _over(res, a[..., :3], a[..., 3])
        out.append(_img(res))
    return out


def glyph_sheet():
    table = np.asarray(_load('blackwall_character_table.png', 'L'), np.float32) / 255
    return [table[r * 64:(r + 1) * 64, c_ * 64:(c_ + 1) * 64] for r in range(8) for c_ in range(8)]


def glyph_strip(seed=5):
    """A Blackwall strip (blackwall_onscreen.mt): a grid of its cipher glyphs (blackwall_character_table), some bright,
    most dim, in its pink-red, over a faint wash. 128 x 1024: two cells across, sixteen down."""
    cells = glyph_sheet()
    rng = np.random.default_rng(seed)
    a = np.zeros((1024, 128), np.float32)
    for row in range(16):
        for col in range(2):
            k = rng.choice([0.25, 0.4, 0.6, 1.0], p=[0.35, 0.3, 0.2, 0.15])
            a[row * 64:(row + 1) * 64, col * 64:(col + 1) * 64] = cells[int(rng.integers(0, 64))] * k
    a[::64, :] = np.maximum(a[::64, :], 0.35)        # GridSize: the cells' lines
    a[:, ::64] = np.maximum(a[:, ::64], 0.35)
    a[:, 125:] = np.maximum(a[:, 125:], 0.5)
    a = np.maximum(a, 0.12)
    rgb = np.broadcast_to(np.array(GLYPH, np.float32), (1024, 128, 3))
    return Image.fromarray(np.dstack([rgb, np.clip(a, 0, 1) * 255]).astype(np.uint8), 'RGBA')


def code_column():
    """Scrolling code (fx_text_code: lines of code, 512 x 2048) cut to a column, in the vignette's text colour;
    128 x 1024, it wraps when the material scrolls it."""
    code = _load('fx_text_code.png', 'L').crop((0, 0, 256, 2048)).resize((128, 1024), Image.LANCZOS)
    a = np.asarray(code, np.float32) / 255
    rgb = np.broadcast_to(np.array(TEXT, np.float32), (1024, 128, 3))
    return Image.fromarray(np.dstack([rgb, np.clip(a * 2.4, 0, 1) * 255]).astype(np.uint8), 'RGBA')


def uber_burst(seed=9):
    """The Gateway over the ÜBER strip (112 x 13 units, 512 x 64): a row of the Blackwall's glyphs in its pink-red over
    a dark crimson wash, tears across, a hot frame."""
    cells = glyph_sheet()
    rng = np.random.default_rng(seed)
    out = np.zeros((64, 512, 4), np.float32)
    _over(out, np.broadcast_to(np.array((60, 6, 20), np.float32), (64, 512, 3)), np.full((64, 512), 0.75))
    for i in range(8):
        g = np.asarray(Image.fromarray((cells[int(rng.integers(0, 64))] * 255).astype(np.uint8)).resize((52, 52)),
                       np.float32) / 255
        k = rng.choice([0.45, 1.0])
        sub = out[6:58, i * 64 + 6:i * 64 + 58]
        _over(sub, np.broadcast_to(np.array(GLYPH, np.float32), (52, 52, 3)), np.clip(g * k * 1.3, 0, 1))
    for y in rng.integers(4, 60, 5):
        x0 = int(rng.integers(0, 380))
        tear = out[y:y + 2, x0:x0 + int(rng.integers(60, 140))]
        _over(tear, np.array((255, 200, 210), np.float32), np.full(tear.shape[:2], 0.9))
    out[:2, :, :3] = G.HOT
    out[:2, :, 3] = 1
    out[-2:, :, :3] = G.HOT
    out[-2:, :, 3] = 1
    return _img(out)


def _vmt(path, base, scroll=None):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('"UnlitGeneric"\n{\n'
                f'\t"$basetexture"\t"{base}"\n'
                '\t"$translucent"\t"1"\n\t"$vertexcolor"\t"1"\n\t"$vertexalpha"\t"1"\n'
                '\t"$no_fullbright"\t"1"\n\t"$ignorez"\t"1"\n')
        if scroll:
            f.write('\t"Proxies"\n\t{\n\t\t"TextureScroll"\n\t\t{\n'
                    '\t\t\t"texturescrollvar"\t"$basetexturetransform"\n'
                    f'\t\t\t"texturescrollrate"\t"{scroll[0]}"\n'
                    f'\t\t\t"texturescrollangle"\t"{scroll[1]}"\n'
                    '\t\t}\n\t}\n')
        f.write('}\n')


def _special(out, name, img, scroll):
    """A texture whose material scrolls it (TextureScroll: rate in heights a second, angle), and its BLU twin."""
    for prefix, im in (('', img), ('b/', to_blue(img))):
        p = os.path.join(out.root, THUMB, prefix + name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        write_vtf(p + '.vtf', linear_alpha(im), alpha=True, mips=False, clamp=False)
        _vmt(p + '.vmt', f'vgui/replay/thumbnails/rk/{prefix}{name}', scroll)
        if out.preview and not prefix:
            im.save(os.path.join(out.preview, name + '.png'))


def art(out):
    for i, im in enumerate(slices(vignette()), 1):
        out.thumb(f'bw_vig{i}', im, mips=False, team=True)
    for i, im in enumerate(blocks(), 1):
        out.thumb(f'bw_block{i}', im, mips=False, team=True)
    out.thumb('bw_uber', uber_burst(), mips=False, team=True)
    out.thumb('bw_glyphs', glyph_strip(), mips=False, team=True)
    _special(out, 'bw_code', code_column(), (0.12, 90))
    for name, *_ in KILLSOUNDS:
        if os.path.isfile(os.path.join(SND, name + '.wav')):
            env = _envelope(name)
            out.thumb(f'ksc_{name}', ks_card(env), mips=False)
            out.thumb(f'ksc_{name}_h', ks_card(env, hover=True), mips=False)
    for key, label in (('tf2', 'TF2'), ('off', 'OFF')):
        out.thumb(f'ksc_{key}', ks_card(label=label), mips=False)
        out.thumb(f'ksc_{key}_h', ks_card(hover=True, label=label), mips=False)


# ------------------------------------------------------------------ sounds
# the game's sounds (cp2077-pack branch, sounds/): file, start, length, fade-out (s). bw_lowhealth: the Blackwall hitting
# V (q303); bw_uber: the Blackwall Gateway quickhack's kill (vfx_blackwall_hack_npc_death, the game's mix)
SOUNDS = {'bw_lowhealth': ('19_q303_sc_03_blackwall_hits_v_4.07s.wav', 0.30, 2.9, 0.8),
          'bw_uber': ('01_vfx_blackwall_hack_npc_death_7.8s.wav', 0.0, 3.0, 0.9)}
PEAK = -3.0             # dBFS
# the kill sounds HUD Settings offers (KILL SOUND): name, card label, file, start, length, fade-out (s); short
# Blackwall hits, the Gateway quickhack's first
KILLSOUNDS = [('ks_01', 'GATEWAY', '01_vfx_blackwall_hack_npc_death_7.8s.wav', 0.0, 2.0, 0.7),
              ('ks_02', 'HITS', '19_q303_sc_03_blackwall_hits_v_4.07s.wav', 0.30, 1.9, 0.6),
              ('ks_03', 'BREACH', '05_q303_sc_03_blackwall_quick_in_1.26s.wav', 0.0, 1.26, 0.2),
              ('ks_04', 'SHORT', '03_w_expl_blackwall_shortcircuit_1.62s.wav', 0.0, 1.62, 0.25),
              ('ks_05', 'GLITCH', '37_q305_blackwall_brooklyn_transition_start_glitch_01_1.29s.wav', 0.0, 1.29, 0.2),
              ('ks_06', 'ARC', '49_vfx_blackwall_obj_static_electric_arc_0.73s.wav', 0.0, 0.73, 0.12)]
LOUD = -5.0   # the kill sounds' mean level, dBFS: as loud as a kill sound has to be over a fight


def _fold(src, mono):
    """The game's files are 5.1 (FL FR FC LFE SL SR), 4.0, stereo or mono: their channels folded to stereo with the
    centre and surrounds at -3 dB and the LFE in (an automatic fold-down leaves the LFE out, and the Blackwall's hits
    lose their weight), or to mono."""
    ch = int(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=channels', '-of', 'csv=p=0', src],
                            capture_output=True, text=True).stdout.split()[0])
    left, right = {6: ({0: 1, 2: 0.707, 4: 0.707, 3: 0.7}, {1: 1, 2: 0.707, 5: 0.707, 3: 0.7}),
                   4: ({0: 1, 2: 0.707}, {1: 1, 3: 0.707}), 1: ({0: 1}, {0: 1})}.get(ch, ({0: 1}, {1: 1}))

    def mix(gains):
        return '+'.join(f'{g:g}*c{i}' for i, g in sorted(gains.items()))
    if mono:
        both = {i: (left.get(i, 0) + right.get(i, 0)) / 2 for i in set(left) | set(right)}
        return f'pan=mono|c0={mix(both)}'
    return f'pan=stereo|c0={mix(left)}|c1={mix(right)}'


# the kill sounds: the low end cut and the 3 kHz range lifted (rockets and explosions are bass: a kill sound is heard
# over them by its upper mids, and bass spends the limiter's room)
PRESENCE = 'highpass=f=140,equalizer=f=3200:t=q:w=0.9:g=5,equalizer=f=7000:t=q:w=1.2:g=2'


def _levels(path):
    out = subprocess.run(['ffmpeg', '-v', 'info', '-i', path, '-af', 'volumedetect', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return (float(out.split('mean_volume:')[1].split('dB')[0]), float(out.split('max_volume:')[1].split('dB')[0]))


def cut(src, dst, start, length, fade, mono=False, loud=None):
    """src -> dst: the slice folded (_fold), 44.1 kHz 16-bit (what TF2 plays), its peak at PEAK; with loud, its mean
    level brought up to it first, the peaks held by a limiter (a quiet sound with one sharp peak stays quiet when
    only its peak is set)."""
    fl = f'{_fold(src, mono)},afade=t=in:d=0.005,afade=t=out:st={length - fade:.3f}:d={fade:.3f}'
    tmp = dst + '.tmp.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start}', '-t', f'{length}', '-i', src,
                    '-af', fl, '-ar', '44100', '-c:a', 'pcm_f32le', tmp], check=True)
    mean, peak = _levels(tmp)
    if loud is None:
        af, codec = f'volume={PEAK - peak:.2f}dB', 'pcm_s16le'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-c:a', codec, dst], check=True)
    else:
        gain = loud - mean
        for _ in range(12):   # the limiter takes some of the level back: aim again
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af',
                            f'{PRESENCE},volume={gain:.2f}dB,asoftclip=type=tanh,volume=-0.5dB', '-ar', '44100',
                            '-c:a', 'pcm_s16le', dst], check=True)
            got = _levels(dst)[0]
            if abs(got - loud) < 0.4:
                break
            gain += loud - got
    os.remove(tmp)


def make_sounds(pack):
    """Cut the HUD's sounds from the cp2077-pack branch's sounds folder into tools/sounds (needs ffmpeg)."""
    os.makedirs(SND, exist_ok=True)
    for name, (src, start, length, fade) in SOUNDS.items():
        cut(os.path.join(pack, src), os.path.join(SND, name + '.wav'), start, length, fade)
        print('  ', name)
    for name, _, src, start, length, fade in KILLSOUNDS:
        cut(os.path.join(pack, src), os.path.join(SND, name + '.wav'), start, length, fade, loud=LOUD)
        print('  ', name)


# The kill sound. TF2 plays it from a sound script entry (tf_hud_account.cpp, tf_dingalingaling_lasthit), the default
# one ui/killsound.wav; Valve's servers (sv_pure: cfg/pure_server_full.txt wants every sound from the game's own files)
# take a file of the player's own for that one and ui/hitsound.wav alone. So the kill sound picked in HUD Settings has
# to be that file, and a menu cannot copy files: the card runs host_writeconfig, which writes the game's settings to
# cfg/rk_killsound_<pick>.cfg in TF2's folder, and the build (update.bat) finds the newest such file, copies the pick
# to sound/ui/killsound.wav and keeps the pick in CHOICE for the builds after it. TF2 reads the file when it starts.
CHOICE = 'rk_killsound.txt'
MARK = 'rk_killsound_'


def killsound_choice(root, tf):
    """The pick: from the newest mark HUD Settings wrote (then the marks go), else the one kept from before."""
    store = os.path.join(root, CHOICE)
    cfg = os.path.join(tf, 'cfg') if tf else None
    marks = []
    if cfg and os.path.isdir(cfg):
        marks = sorted((os.path.join(cfg, f) for f in os.listdir(cfg) if f.lower().startswith(MARK)),
                       key=os.path.getmtime)
    if marks:
        pick = os.path.basename(marks[-1])[len(MARK):].lower()
        pick = pick[:-4] if pick.endswith('.cfg') else pick
        with open(store, 'w', encoding='utf-8') as f:
            f.write(pick + '\n')
        for m in marks:
            try:
                os.remove(m)
            except OSError:
                pass
        return pick
    if os.path.isfile(store):
        return open(store, encoding='utf-8').read().strip().lower()
    return None


def sounds(root, tf=None):
    """The build: the cut sounds where PlaySound reads them (sound/ui/rk) and a copy in the folder sv_pure lets a HUD
    load pictures from (materials/vgui/replay/thumbnails/rk/snd), to try on Valve's servers; the kill sounds' previews
    (sound/ui/rk), and the kill sound picked in HUD Settings as ui/killsound.wav."""
    for name in SOUNDS:
        src = os.path.join(SND, name + '.wav')
        if not os.path.isfile(src):
            continue
        for d in (os.path.join(root, 'sound', 'ui', 'rk'), os.path.join(root, THUMB, 'snd')):
            os.makedirs(d, exist_ok=True)
            shutil.copy(src, os.path.join(d, name + '.wav'))
    for name, *_ in KILLSOUNDS:
        src = os.path.join(SND, name + '.wav')
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(root, 'sound', 'ui', 'rk', name + '.wav'))
    pick = killsound_choice(root, tf)
    labels = {n: lbl for n, lbl, *_ in KILLSOUNDS}
    ours = os.path.join(root, 'sound', 'ui', 'killsound.wav')
    if pick in labels and os.path.isfile(os.path.join(SND, pick + '.wav')):
        shutil.copy(os.path.join(SND, pick + '.wav'), ours)
        print(f'  kill sound: {labels[pick]} (picked in HUD Settings)')
        for other in other_killsounds(root, tf):
            try:
                os.replace(other, other + ASIDE)
                print(f'    your other kill sound is set aside so the pick can play: {other} -> killsound.wav{ASIDE}')
                print('    (HUD Settings > KILL SOUND > TF2, then update.bat, puts it back)')
            except OSError as e:
                print(f'    WARNING: another kill sound plays instead of the pick, and could not be set aside: '
                      f'{other} ({e})')
    elif pick:
        if os.path.isfile(ours):
            os.remove(ours)
        for other in other_killsounds(root, tf, aside=True):
            if not os.path.exists(other[:-len(ASIDE)]):
                os.replace(other, other[:-len(ASIDE)])
                print(f'    your own kill sound is back: {other[:-len(ASIDE)]}')
        print(f'  kill sound: not the HUD\'s ({pick})')
    else:
        print('  kill sound: none picked in HUD Settings yet')


ASIDE = '.rk_off'


def other_killsounds(root, tf, aside=False):
    """Kill sound files of the player's own outside this HUD: TF2 plays one ui/killsound.wav, and with two the other
    folder's can win (tf/custom's folders load in name order). With aside, the ones this build set aside."""
    if not tf:
        return []
    name = 'killsound.wav' + (ASIDE if aside else '')
    places = [os.path.join(tf, 'sound', 'ui', name)]
    custom = os.path.join(tf, 'custom')
    if os.path.isdir(custom):
        me = os.path.normcase(os.path.abspath(root))
        places += [os.path.join(custom, d, 'sound', 'ui', name) for d in sorted(os.listdir(custom))
                   if os.path.normcase(os.path.abspath(os.path.join(custom, d))) != me]
    return [f for f in places if os.path.isfile(f)]


# HUD Settings' KILL SOUND row: a card per kill sound (its waveform), TF2's own, off
KS_CARD = 40
KS_CARDS = [f'ksc_{n}' for n, *_ in KILLSOUNDS] + ['ksc_tf2', 'ksc_off']   # (build.RK_BORDERS: their hover borders)


def _envelope(name, bars=14):
    import wave
    with wave.open(os.path.join(SND, name + '.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    parts = np.array_split(x, bars)
    e = np.array([np.sqrt(np.mean(p ** 2)) if len(p) else 0 for p in parts])
    return np.sqrt(e / max(e.max(), 1e-6))


def ks_card(env=None, hover=False, label=None):
    """A kill sound's card in HUD Settings: black glass, the torn frame, the sound's waveform in crimson with its red
    and cyan copies; under the pointer a crimson wash and a hot frame. label: text instead (TF2, OFF)."""
    from build_art import c, chamfer
    p = G.Px(KS_CARD, KS_CARD, 256 / (KS_CARD * PX))
    w, h = p.W, p.H
    shape = chamfer(0, 0, w, h, br=10)
    p.poly(shape, c((40, 8, 14) if hover else (9, 9, 11), 240))
    G.scan_in(p, shape, (236, 232, 232), 12)
    edge = chamfer(0.5, 0.5, w - 0.5, h - 0.5, br=9.5)
    if hover:
        p.outline(edge, c(G.HOT), 1.5)
    else:
        G.torn(p, edge, seed=8, a=150, gaps=0.2, seg=30)
    if env is not None:
        bw = (w - 18) / len(env)
        cy = h / 2
        for i, v in enumerate(env):
            bh = max(2.0, v * (h - 26))
            x0 = 9 + i * bw
            for dx, col, a in ((-1.2, G.SPLIT_R, 120), (1.2, G.SPLIT_C, 100)):
                p.rect(x0 + dx, cy - bh / 2, x0 + bw * 0.6 + dx, cy + bh / 2, c(col, a))
            p.rect(x0, cy - bh / 2, x0 + bw * 0.6, cy + bh / 2, c((255, 255, 255) if hover else G.RED))
    elif label:
        p.text(w / 2, h / 2, label, ('raj7', h * 0.28), c((236, 232, 232) if hover else (138, 132, 138)), 'mm')
    return p.result()


def killsound_section(motd, y, add, label_block, card_button, block, red, grey, popup_w):
    """HUD Settings' KILL SOUND row: a card per kill sound (a click plays it and picks it), TF2's own, OFF, and a note
    on when the pick takes over."""
    add(motd, 'RK_PopupSection5', label_block('RK_PopupSection5', 22, y, 300, 12, 'KILL SOUND', 'RK_Mono', red))
    pick = ('engine tf_dingalingaling_lasthit 1; tf_dingalingaling_last_effect 0; tf_dingaling_lasthit_volume 1; '
            'host_writeconfig ' + MARK)
    cards = [(n, lbl, pick + n, f'ui/rk/{n}.wav') for n, lbl, *_ in KILLSOUNDS]
    cards += [('tf2', 'TF2', pick + 'tf2', 'UI/buttonclick.wav'),
              ('off', 'OFF', 'engine tf_dingalingaling_lasthit 0', 'UI/buttonclick.wav')]
    for i, (n, lbl, command, snd) in enumerate(cards):
        name = f'RK_Ks_{n}'
        x = 22 + i * (KS_CARD + 8)
        blk = block(name, {'fieldName': name, 'visible': 1, 'enabled': 1, 'tabPosition': 0, 'sound_depressed': snd,
                           'sound_armed': 'UI/buttonrollover.wav'})
        kv.remove(motd, name)
        motd.append([name, blk, None])
        card_button(motd, blk, f'ksc_{n}', x, y + 16, KS_CARD, KS_CARD, command)
        kv.set(blk, 'actionsignallevel', 2)
        add(motd, name + 'Name', label_block(name + 'Name', x - 4, y + 18 + KS_CARD, KS_CARD + 8, 10, lbl, 'RK_Small',
                                              grey, align='center'))
    nx = 22 + len(cards) * (KS_CARD + 8) + 6
    blk = label_block('RK_PopupNote6', nx, y + 16, popup_w - nx - 22, KS_CARD + 12, 'Click a sound to hear it. The last one '
                      'you click becomes your kill sound after you close TF2 and run update.bat (in the HUD\'s '
                      'folder). TF2: the kill sound you had before. OFF: no kill sound.', 'RK_Small',
                      '128 124 130 255', align='north-west')
    blk['wrap'] = 1
    add(motd, 'RK_PopupNote6', blk)


# ------------------------------------------------------------------ the HUD's panels
def _img_panel(name, x, y, w, h, image, z, **extra):
    e = {'ControlName': 'CTFImagePanel', 'fieldName': name, 'xpos': x, 'ypos': y, 'zpos': z, 'wide': w, 'tall': h,
         'visible': 1, 'enabled': 1, 'scaleImage': 1, 'alpha': 0, 'mouseinputenabled': 0, **G.team_keys(image)}
    e.update(extra)
    return e


def patch_health(root):
    """HudPlayerHealth.res (after ingame.patch_health): the threshold, the screen's layers, the digits' kick copies."""
    body = kv.find(root, 'Resource/UI/HudPlayerHealth.res')
    kv.set(kv.find(body, 'HudPlayerHealth'), 'HealthDeathWarning', THRESHOLD)
    kv.remove(body, 'RK_EdgeDanger')             # the 0.6 edge glow: the vignette takes its place
    # the screen's layers sit in one full-screen panel, the gate: the loop animates the layers, the gate's alpha
    # decides whether any of it shows (see anims: a respawn has to be able to shut it)
    gate = []
    h = 480 // SLICES
    for i in range(SLICES):
        kv.add_block(gate, f'RK_BWVig{i + 1}', _img_panel(f'RK_BWVig{i + 1}', -SLIDE, i * h, f'f-{2 * SLIDE}', h,
                                                           f'bw_vig{i + 1}', 0))
    for name, x, w in CODE:
        kv.add_block(gate, name, _img_panel(name, x, 0, w, 480, 'bw_code', 0))
    for i, (_, x, y, w, h_) in enumerate(BLOCKS, 1):
        kv.add_block(gate, f'RK_BWBlock{i}', _img_panel(f'RK_BWBlock{i}', x, y, w, h_, f'bw_block{(i - 1) % 4 + 1}', 1))
    for i, (x, w) in enumerate(STRIPS, 1):
        kv.add_block(gate, f'RK_BWStrip{i}', _img_panel(f'RK_BWStrip{i}', x, 0, w, 480, 'bw_glyphs', 1))
    for old in [k for k, v, _ in body if k.startswith('RK_BW')]:
        kv.remove(body, old)
    kv.add_block(body, GATE, {'ControlName': 'EditablePanel', 'fieldName': GATE, 'xpos': 0, 'ypos': 0, 'zpos': 0,
                              'wide': 'f0', 'tall': 480, 'visible': 1, 'enabled': 1, 'alpha': 0,
                              'mouseinputenabled': 0, 'PaintBackgroundType': 0, 'paintbackground': 0})
    kv.find(body, GATE).extend(gate)
    # the card's own glitch, in a second gate over the card (z 9, the danger tint's): the tint and torn strips of the
    # wall across the card, flickering with the loop. (The digits' copies are labels the game fills with the health,
    # which it only does for the health panel's own children: they stay outside and kick once.)
    card = []
    for k, v, c in list(body):
        if k == 'RK_HealthDanger':
            body.remove([k, v, c]) if [k, v, c] in body else None
            card.append([k, v, c])
    body[:] = [e for e in body if e[0] != 'RK_HealthDanger']
    for i, box in enumerate(CARD_TEARS, 1):
        x, y, w, h_ = G.at(box)
        G.add(card, G.timg(f'RK_BWCard{i}', x, y, w, h_, f'bw_block{(i - 1) % 4 + 1}', z=10, alpha=0))
    kv.add_block(body, GATE_CARD, {'ControlName': 'EditablePanel', 'fieldName': GATE_CARD, 'xpos': 0, 'ypos': 0,
                                   'zpos': 9, 'wide': 'f0', 'tall': 480, 'visible': 1, 'enabled': 1, 'alpha': 0,
                                   'mouseinputenabled': 0, 'PaintBackgroundType': 0, 'paintbackground': 0})
    kv.find(body, GATE_CARD).extend(card)
    # the HUD kick's chromatic aberration: the digits' red and cyan copies, three units either side, over the sheets
    dx, dy, dw, dh = G.at(G.DIGITS)
    for name, ox, col in (('RK_HealthKickR', -3, '255 20 60 255'), ('RK_HealthKickC', 3, '0 214 255 255')):
        G.add(body, G.lbl(name, dx + ox, dy, dw, dh, '%Health%', 'RK_Digits', col, z=10, alpha=0))


def patch_uber(root):
    """HudMedicCharge.res (after ingame.patch_uber): the Gateway's burst over the strip."""
    body = next(e[1] for e in root if isinstance(e[1], list))
    kv.add_block(body, 'RK_UberBreach', _img_panel('RK_UberBreach', 0, 0, G.UBER_CARD[0], G.UBER_CARD[1], 'bw_uber', 7))


# ------------------------------------------------------------------ animations
def _a(panel, var, value, start, length, interp='Linear'):
    return f'\tAnimate {panel}\t{var}\t"{value}"\t{interp} {start:.3f} {length:.3f}'


GATE = 'RK_BWGate'
GATE_CARD = 'RK_BWGateCard'
# torn strips across the health card (card-local boxes, units)
CARD_TEARS = [(0, 9, 187, 4), (62, 31, 125, 3), (0, 49, 96, 5), (118, 19, 69, 8), (20, 40, 150, 2)]


def _cycle(name, nxt, seed):
    """One second of the low-health effect (its loop, 0.25 to 1.25 s of p_health_low.effect)."""
    rng = random.Random(seed)
    L = [f'event {name}', '{']
    # the card: its danger tint beats with the kick, two or three torn strips cross it, the whole overlay jumps
    L += [_a('RK_HealthDanger', 'Alpha', 255, 0, 0.03), _a('RK_HealthDanger', 'Alpha', 130, 0.03, 0.08),
          _a('RK_HealthDanger', 'Alpha', 60, 0.11, 0.55)]
    for i in rng.sample(range(1, len(CARD_TEARS) + 1), 3):
        t0, life = rng.uniform(0.0, 0.8), rng.uniform(0.08, 0.3)
        L += [_a(f'RK_BWCard{i}', 'Alpha', rng.randint(150, 255), t0, 0.0),
              _a(f'RK_BWCard{i}', 'Alpha', 0, t0 + life, 0.05)]
    for t0 in (0.0, 0.5):
        L += [_a(GATE_CARD, 'xpos', rng.choice((-3, -2, 2, 3)), t0, 0), _a(GATE_CARD, 'xpos', 0, t0 + 0.06, 0)]
    # the vignette: flares with the kick; its three slices jump sideways four times a second (OffsetChangeSpeed 4)
    for i in range(1, SLICES + 1):
        p = f'RK_BWVig{i}'
        L += [_a(p, 'Alpha', 255, 0, 0.03), _a(p, 'Alpha', 190, 0.06, 0.3)]
        for k, t in enumerate((0.0, 0.25, 0.5, 0.75)):
            reach = SLIDE - 2 if k == 0 else 7
            L.append(_a(p, 'xpos', -SLIDE + rng.randint(-reach, reach), t, 0))
    # glitch blocks: a few pop each second (live 0.2-0.8 s, alpha 0.4-1)
    for i in rng.sample(range(1, len(BLOCKS) + 1), 6):
        t, life = rng.uniform(0.0, 0.85), rng.uniform(0.2, 0.8)
        L += [_a(f'RK_BWBlock{i}', 'Alpha', rng.randint(110, 255), t, 0.02),
              _a(f'RK_BWBlock{i}', 'Alpha', 0, t + life * 0.5, life * 0.5)]
    # a thin line of the wall flashes for 0.1 s
    s = rng.choice(THIN) + 1
    t = rng.uniform(0.2, 0.85)
    L += [_a(f'RK_BWStrip{s}', 'Alpha', 255, t, 0), _a(f'RK_BWStrip{s}', 'Alpha', 0, t + 0.1, 0)]
    L += [f'\tRunEvent {nxt}\t{CYCLE:.1f}', '}']
    return L


def _kick():
    L = []
    # the HUD kick: glitchParameter 0.176 at 29 ms, 0.090 at 111 ms, 0.030 at 659 ms, 0 at 997 ms
    L += [_a('RK_HealthKickR', 'Alpha', 230, 0, 0.02), _a('RK_HealthKickR', 'Alpha', 0, 0.05, 0.16),
          _a('RK_HealthKickC', 'Alpha', 200, 0, 0.02), _a('RK_HealthKickC', 'Alpha', 0, 0.06, 0.16)]
    L += [_a('PlayerStatusHealthValue', 'FgColor', '255 255 255 0', 0, 0),
          _a('RK_HealthHot', 'FgColor', '255 255 255 255', 0, 0),
          _a('PlayerStatusHealthValue', 'FgColor', 'RK_Text', 0.12, 0.12),
          _a('RK_HealthHot', 'FgColor', '255 255 255 0', 0.12, 0.12)]
    return L


def anims():
    L = ['', '// near death (under THRESHOLD): the Blackwall breaks through (tools/blackwall.py). Once on the way under: its',
         '// hit and a burst of its glyph strips; then Cyberpunk 2077\'s 1 s low-health cycle, three of them in turn so',
         '// the blocks and the jumps do not repeat every second']
    L += ['event HudHealthDyingPulse', '{', '\tPlaySound 0 "ui/rk/bw_lowhealth.wav"']
    for i, (_, w) in enumerate(STRIPS, 1):
        L += [_a(f'RK_BWStrip{i}', 'Alpha', 255, 0.0, 0.2, 'Flicker 0.8'),
              _a(f'RK_BWStrip{i}', 'Alpha', 0, 0.3 + 0.06 * i, 0.4)]
    for i in range(1, SLICES + 1):
        L.append(_a(f'RK_BWVig{i}', 'Alpha', 255, 0.0, 0.15, 'Flicker 0.7'))
    for name, _, _ in CODE:
        L.append(_a(name, 'Alpha', 120, 0.1, 0.4))
    # the card's kick, once (outside the gate, so not in the loop); the gate open; an older loop's chain cut
    L += _kick()
    L += [f'\tStopEvent {e}\t0.0' for e in ('RK_DyingA', 'RK_DyingB', 'RK_DyingC')]
    L += [_a(GATE, 'Alpha', 255, 0, 0), _a(GATE_CARD, 'Alpha', 255, 0, 0), '\tRunEvent RK_DyingA\t0.15', '}']
    L += _cycle('RK_DyingA', 'RK_DyingB', 1) + _cycle('RK_DyingB', 'RK_DyingC', 2) + _cycle('RK_DyingC', 'RK_DyingA', 3)
    L += ['// the stock loop: nothing runs it now (the first event of a name is the one the game plays: ours)',
          'event HudHealthDyingPulseLoop', '{', '}']
    L += ['event HudHealthDyingPulseStop', '{']
    L += [f'\tStopEvent {e}\t0.0' for e in ('HudHealthDyingPulse', 'HudHealthDyingPulseLoop', 'RK_DyingA', 'RK_DyingB',
                                            'RK_DyingC')]
    L += [_a('PlayerStatusHealthValue', 'FgColor', 'RK_Text', 0, 0), _a('RK_HealthHot', 'FgColor', '255 255 255 0', 0, 0),
          _a('RK_HealthDanger', 'Alpha', 0, 0, 0), _a('RK_HealthKickR', 'Alpha', 0, 0, 0),
          _a('RK_HealthKickC', 'Alpha', 0, 0, 0)]
    for i in range(1, SLICES + 1):
        L += [_a(f'RK_BWVig{i}', 'Alpha', 0, 0, 0.35), _a(f'RK_BWVig{i}', 'xpos', -SLIDE, 0.35, 0)]
    L += [_a(f'RK_BWBlock{i}', 'Alpha', 0, 0, 0.1) for i in range(1, len(BLOCKS) + 1)]
    L += [_a(f'RK_BWStrip{i}', 'Alpha', 0, 0, 0.1) for i in range(1, len(STRIPS) + 1)]
    L += [_a(name, 'Alpha', 0, 0, 0.3) for name, _, _ in CODE]
    L += [_a(GATE, 'Alpha', 0, 0.35, 0), _a(GATE_CARD, 'Alpha', 0, 0, 0), _a(GATE_CARD, 'xpos', 0, 0, 0), '}']
    # The game never stops the pulse of a player who dies under the threshold: the health panel is hidden at once,
    # and a respawn resets its state (CTFHudPlayerHealth::Reset) without running HudHealthDyingPulseStop, so the loop
    # ran on at full health. A respawn does run HudSpyDisguiseHide (CTFHudPlayerClass::Reset), on the whole HUD: it
    # cannot stop the loop (that is the health panel's), but it shuts the gate. The stock event's own lines first.
    # The same reset cancels every running animation (CHud::ResetHUD) first: a hitmarker mid-flash (a hit just as the
    # round restarts, the end of warmup) stayed on screen at full alpha, so it is put out here too.
    L += ['event HudSpyDisguiseHide', '{', _a('PlayerStatusSpyOutlineImage', 'Position', '3 413', 0.0, 0.2),
          _a('PlayerStatusSpyOutlineImage', 'Size', '55 55', 0.0, 0.2),
          _a('PlayerStatusSpyOutlineImage', 'Alpha', 0, 0.2, 0.1),
          _a(GATE, 'Alpha', 0, 0, 0), _a(GATE_CARD, 'Alpha', 0, 0, 0), _a(GATE_CARD, 'xpos', 0, 0, 0),
          _a('RK_Hitmarker', 'Alpha', 0, 0, 0), '}']
    L += ['', '// ÜberCharge full: the Gateway (its sound once, its glyphs over the strip), then the strip breathes READY',
          'event HudMedicCharged', '{', '\tPlaySound 0 "ui/rk/bw_uber.wav"',
          _a('RK_UberBreach', 'Alpha', 255, 0.0, 0.3, 'Flicker 0.9'), _a('RK_UberBreach', 'Alpha', 0, 0.6, 0.6),
          _a('ChargeMeter', 'FgColor', '255 255 255 255', 0.0, 0.1),
          _a('RK_UberReady', 'Alpha', 255, 0.0, 0.12, 'Flicker 0.5'),
          '\tRunEvent RK_UberReadyLoop\t1.2', '}',
          'event RK_UberReadyLoop', '{',
          _a('ChargeMeter', 'FgColor', '255 255 255 255', 0.0, 0.1),
          _a('ChargeMeter', 'FgColor', '120 120 120 255', 0.3, 0.3),
          _a('RK_UberReady', 'Alpha', 255, 0.0, 0.12, 'Flicker 0.5'),
          _a('RK_UberReady', 'Alpha', 150, 0.3, 0.3),
          '\tRunEvent RK_UberReadyLoop2\t0.6', '}',
          'event RK_UberReadyLoop2', '{', '\tRunEvent RK_UberReadyLoop\t0.0', '}',
          'event HudMedicChargedLoop', '{', '}',
          'event HudMedicChargedStop', '{']
    L += [f'\tStopEvent {e}\t0.0' for e in ('HudMedicCharged', 'HudMedicChargedLoop', 'RK_UberReadyLoop',
                                            'RK_UberReadyLoop2')]
    L += [_a('ChargeMeter', 'FgColor', '255 255 255 255', 0.0, 0.0001), _a('RK_UberReady', 'Alpha', 0, 0, 0),
          _a('RK_UberBreach', 'Alpha', 0, 0, 0), '}', '']
    return '\n'.join(L)


ANIMS = anims()


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'sounds':
        make_sounds(sys.argv[2])
    else:
        print('python blackwall.py sounds <cp2077-pack sounds folder>')
