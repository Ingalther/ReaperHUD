"""Turns a video into the game's startup video, media/valve.webm, where the game reads it (the build keeps it there).

TF2 plays its intro from media/startupvids.txt, which names media/valve.bik: since the 64-bit update the game plays
the WebM beside it (hl2/media/valve.webm: VP9 and Vorbis), and a media/valve.webm in a tf/custom folder comes first.
So the intro is that file, in the same codecs: VP9 at 1920 x 1080 and 30 fps, the first stereo track as Vorbis
(48 kHz; Opus has been reported to come out silent). The launch option -novid skips it, ours as the game's own.
Needs ffmpeg; run by hand:

    python tools/intro.py intro.mp4

The current intro: video/intro.mp4 on the video-source branch (57 s, 3840 x 2160, an English stereo and a 5.1 track),
a Cyberpunk 2077 trailer; it ships with the HUD, in the public release too (the author's call).
"""
import argparse
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'media', 'valve.webm')


def stereo_track(video):
    """The index (among audio streams) of the first two-channel track, else the first one."""
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=channels',
                            '-of', 'json', video], capture_output=True, text=True, check=True)
    tracks = json.loads(probe.stdout).get('streams', [])
    return next((i for i, s in enumerate(tracks) if s.get('channels') == 2), 0 if tracks else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('video')
    ap.add_argument('--crf', type=int, default=31, help='VP9 quality (lower is better and bigger)')
    args = ap.parse_args()
    audio = stereo_track(args.video)
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-stats', '-y', '-i', args.video, '-map', '0:v:0']
    if audio is not None:
        cmd += ['-map', f'0:a:{audio}', '-c:a', 'libvorbis', '-q:a', '5', '-ar', '48000', '-ac', '2']
    cmd += ['-vf', 'scale=1920:1080:flags=lanczos,fps=30,format=yuv420p', '-c:v', 'libvpx-vp9', '-b:v', '0',
            '-crf', str(args.crf), '-row-mt', '1', '-deadline', 'good', '-cpu-used', '3', '-g', '60', OUT]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run(cmd, check=True)
    print(f'-> media/valve.webm ({os.path.getsize(OUT) / 2 ** 20:.1f} MB)')


if __name__ == '__main__':
    main()
