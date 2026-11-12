"""Turns a video into the main menu's animated background: its frames as a DXT1 texture (drawn stretched to the
screen) that the material plays on a loop, at the rate written in video/menu_video.json. The texture goes where the
game reads it, materials/vgui/replay/thumbnails/rk/mm_video.vtf, and the build leaves it there, so the HUD holds it
once. Also video/menu_still.jpg, one full-size frame for the loading screens, which cannot move. The build only
writes the material (build.py, menu_video); this needs ffmpeg and is run by hand:

    python tools/video.py menu_loop.mp4 --start 128 --frames 330 --size 1020x508 --crossfade 45 --shade

--size       the frames' size (default 1024x512; multiples of 4, as DXT1 takes the picture in blocks of 4 x 4);

--start      the frame the loop starts on (default 0). A file's first frames are often an encoder's repeats, which
             stutter at the seam; then take the loop from its second round;
--frames     one loop's length in the video's own frames, so that the frame after the last is the first again (the
             Blackwall clip, 30 fps, repeats every 100 frames, 3.33 s: its frame 100 is frame 0 again);
--parts      textures the loop is split over, played one after another (1 to 3; see below);
--crossfade  for a shot that does not loop by itself: its last N frames fade into the N frames before --start, so
             the loop runs on into its first frame without a jump (a camera move needs a long fade: half a
             second read as a cut);
--shade      the main menu's shade (darker behind the buttons on the left) drawn into the frames: then the panel
             that drew it (the class picture) shows nothing (build.py, menu.mainmenu).

The game refuses a texture bigger than 32 M pixels counting every frame, with each of width, height and frame
count rounded down to a power of two (Q_log2 in CVTFTexture::Unserialize), and shows its purple and black error
pattern instead, without a word in the console. At 1024 x 512 that is 127 frames; at 1020 x 508, which counts as
512 x 256, it is 511, so the whole 11 s loop (330 frames) fits in one texture at a size no eye can tell from
1024 x 512, and plays with no switch at all. (The game loads textures that are not a power of two at their own
size wherever the graphics card can, which every card that runs TF2 today can.) Split over two or three textures
of the same length (--parts), the main menu's background plays parts one and two (the second as its detail
texture), a panel of ours that resource/gamemenu.res lists as shown only at the menu the third (build.py,
menu_video and game_menu): that froze in the game for the third part, so the loop is one texture now. A loop
longer than the parts can hold is resampled to that many frames, evenly spread, and played at the rate that keeps
its real length.

The current video: video/menu_loop.mp4 on the video-source branch, a 20 s shot of the wall's circuitry (30 fps)
that fades in from black and back out; the loop is its bright middle, frames 128 to 457 (11 s), its last 1.5 s
fading into the 45 frames just before it (83 to 127, still bright), so the camera's move dissolves into its start.
"""
import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

import dxt
from vtf import FMT_DXT1, write_vtf_frames

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'video')  # menu_video.json and the still
RK = os.path.join(os.path.dirname(HERE), 'materials', 'vgui', 'replay', 'thumbnails', 'rk')  # the textures
SIZE = '1024x512'
MAX_LOG2 = 25  # the engine's limit: floor(log2) of width + height + frame count
PART_NAMES = ('mm_video', 'mm_video_b', 'mm_video_c')  # build.py VIDEO_PARTS
INK = (7, 7, 9)  # build_art.INK


def max_frames(w, h):
    return 2 ** (MAX_LOG2 - int(math.log2(w)) - int(math.log2(h)) + 1) - 1


def fits(w, h, n):
    return int(math.log2(w)) + int(math.log2(h)) + int(math.log2(n)) <= MAX_LOG2


def part_file(i):
    """The i-th part's texture: mm_video.vtf (the only one for a loop in one texture), mm_video_b.vtf, mm_video_c.vtf."""
    return os.path.join(RK, PART_NAMES[i] + '.vtf')


def shade_alpha(width):
    """The main menu's shade over the video (menu.art, mm_video_shade), its darkness from left to right."""
    return np.interp(np.linspace(0, 1, width), [0, 0.32, 0.6, 1], [0.62, 0.52, 0.25, 0.10])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('video')
    ap.add_argument('--start', type=int, default=0, help='the frame the loop starts on')
    ap.add_argument('--frames', type=int, required=True, help="one loop's length, in the video's frames")
    ap.add_argument('--parts', type=int, default=1, choices=(1, 2, 3), help='textures the loop is split over')
    ap.add_argument('--crossfade', type=int, default=0, help="frames at the loop's end faded into those before it")
    ap.add_argument('--shade', action='store_true', help="draw the main menu's shade into the frames")
    ap.add_argument('--size', default=SIZE, help='the frames\' size, WxH (multiples of 4)')
    args = ap.parse_args()
    W, H = (int(v) for v in args.size.lower().split('x'))
    assert W % 4 == 0 and H % 4 == 0, 'DXT1 takes the picture in blocks of 4 x 4: --size in multiples of 4'
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                            '-of', 'default=nw=1:nk=1', args.video], capture_output=True, text=True, check=True)
    num, den = (int(x) for x in probe.stdout.strip().split('/'))
    src_fps = num / den
    per = min(args.frames // args.parts, max_frames(W, H))
    count = per * args.parts
    assert fits(W, H, per)
    k = args.crossfade
    assert not k or count == args.frames, 'a crossfade needs every frame of the loop (no resampling)'
    assert args.start >= k, 'the crossfade fades into the frames before --start'
    assert args.parts < 3 or args.shade, "with 3 parts the shade's panel plays the third: --shade"
    picks = {args.start + round(i * args.frames / count): i for i in range(count)}
    fps = count / (args.frames / src_fps)
    first, last = args.start - k, args.start + args.frames
    shade = shade_alpha(W)[None, :, None].astype(np.float32) if args.shade else None
    vf = f"select='gte(n\\,{first})*lt(n\\,{last})',scale={W}:{H}:flags=lanczos"
    proc = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', args.video, '-vf', vf,
                             '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                            stdout=subprocess.PIPE)
    blocks, brightness, before, n = [None] * count, [0.0] * count, [], first
    while True:
        raw = proc.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            break
        frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        if n < args.start:  # the frames the loop's end fades into
            before.append(frame.astype(np.float32))
        elif n in picks:
            i = picks[n]
            out = frame.astype(np.float32)
            brightness[i] = float(out.mean())
            j = i - (count - k)
            if k and j >= 0:  # the loop's last k frames fade into the k before its first, in linear light (a
                t = (j + 1) / (k + 1)  # plain mix of the two dims the bright lines halfway through)
                t = t * t * (3 - 2 * t)
                out = ((out / 255) ** 2.2 * (1 - t) + (before[j] / 255) ** 2.2 * t) ** (1 / 2.2) * 255
            if shade is not None:
                out = out * (1 - shade) + np.array(INK, np.float32) * shade
            blocks[i] = dxt.encode(np.clip(np.rint(out), 0, 255).astype(np.uint8))
            if (i + 1) % 20 == 0:
                print(f'  {i + 1} / {count}', file=sys.stderr)
        n += 1
    proc.wait()
    assert all(b is not None for b in blocks), 'the video ended before the loop did'
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(RK, exist_ok=True)
    for f in [part_file(i) for i in range(len(PART_NAMES))] + \
            [os.path.join(OUT, n) for n in ('menu_video.vtf', 'menu_video_a.vtf', 'menu_video_b.vtf', 'menu_video_c.vtf')]:
        if os.path.exists(f):  # the last video's parts (and the copies in video/ that older versions kept)
            os.remove(f)
    for p in range(args.parts):
        write_vtf_frames(part_file(p), W, H, FMT_DXT1, blocks[p * per:(p + 1) * per])
    # the still: the brightest moment of the loop, at full size and without the shade (the loading screens have
    # their own, build.py loading_still)
    best = max(range(count), key=lambda i: brightness[i])
    src = next(s for s, v in picks.items() if v == best)
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', args.video, '-vf',
                    f"select='eq(n\\,{src})',scale=1920:1080:flags=lanczos", '-fps_mode', 'passthrough',
                    '-frames:v', '1', '-q:v', '2', os.path.join(OUT, 'menu_still.jpg')], check=True)
    with open(os.path.join(OUT, 'menu_video.json'), 'w', encoding='utf-8') as f:
        json.dump({'fps': round(fps, 4), 'frames': per, 'parts': args.parts, 'size': [W, H],
                   'source': os.path.basename(args.video), 'start': args.start, 'loop_frames': args.frames,
                   'crossfade': k, 'shade': bool(args.shade), 'still_frame': src}, f, indent=2)
        f.write('\n')
    size = sum(os.path.getsize(part_file(p)) for p in range(args.parts)) / 2 ** 20
    print(f'{count} frames ({args.parts} x {per}) at {fps:.4g} fps ({args.frames / src_fps:.2f} s a loop) -> '
          f'{os.path.relpath(RK, os.path.dirname(HERE))} ({size:.1f} MB); still: frame {src}')


if __name__ == '__main__':
    main()
