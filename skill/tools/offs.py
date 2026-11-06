"""Measure the camera sync at given timeline times:  offs.py T1[,T2,...] [--cam NAME]

For every camera with an audio track (or only --cam NAME), it cross-correlates a 20 s bass envelope of
the camera audio against the set recording and prints the residual offset in ms. Put the value for the
clip's cameras into cfg "offsets": {"<cam>": seconds} when it's more than ~15 ms.

The z score shows how clear the match is. In a loud club, z is often only 2-3. If one reading is far from
its neighbours (measure 2-3 times around the clip), trust the neighbours, and check a sharp visual event
(a light flash, a hand hitting a button) in `frames.py src` at 4-8 fps.
Cameras drift over a long set; `setup_project.py sync` fits that drift linearly. What's left is what this
tool measures per clip.
"""
import os, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfiltfilt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proj

SR = 4000
sos = butter(4, [40, 150], btype='band', fs=SR, output='sos')


def get(path, ss, dur):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0.0, ss):.4f}', '-i', path, '-t', str(dur), '-vn',
                        '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(float)


def env(x):
    return np.log(np.sqrt(np.convolve(sosfiltfilt(sos, x) ** 2, np.ones(40) / 40, 'same'))[::4] + 1e-4)


def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return bool(r.stdout.strip())


def measure(P, cam, t, win=20.0, search=1.0):
    """residual offset (s) of camera `cam` at timeline time t, and z score. Positive = camera content
    appears later in its file than the sync predicts (add it to cfg offsets)."""
    ref = env(get(P.audio_file, P.audio_time(t), win)); ref -= ref.mean()
    c = env(get(P.cam_file(cam), P.src(cam, t) - search, win + 2 * search)); c -= c.mean()
    if len(c) < len(ref) or len(ref) < 100:
        return None, 0.0
    cc = np.correlate(c, ref, 'valid')
    L = int(np.argmax(cc)); z = (cc.max() - cc.mean()) / (cc.std() + 1e-12)
    return (L - int(search * 1000)) / 1000.0, z


if __name__ == "__main__":
    argv = sys.argv[1:]
    P = proj.load(argv=argv)
    only = None
    if "--cam" in argv:
        i = argv.index("--cam"); only = argv[i + 1]; del argv[i:i + 2]
    if len(argv) != 1:
        sys.exit(__doc__)
    cams = [only] if only else [c for c in P.cams if has_audio(P.cam_file(c))]
    for t in [float(v) for v in argv[0].split(',')]:
        parts, rec = [], {}
        for cam in cams:
            o, z = measure(P, cam, t)
            if o is None:
                parts.append(f"{cam} n/a"); continue
            parts.append(f"{cam} {o * 1000:+.0f} ms (z={z:.1f})")
            if abs(o) > 0.015:
                rec[cam] = round(o, 3)
        print(f"{t:.2f}: " + "   ".join(parts) + (f"  ->  \"offsets\": {rec}".replace("'", '"') if rec else "  -> no offsets needed"))
