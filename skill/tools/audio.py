"""Audio analysis of the set recording. All times are timeline seconds (the DJ's timestamps, see proj.py).
Run from inside the project folder (or pass --project DIR).

  audio.py env A B [--grid BPM,BEAT0] [--step S]
        ASCII envelope, one row per 48 ms. B### = bass (<110 Hz), X*** = full band.
        With --grid, '|' marks every beat. THIS is how you find and verify drops, fake drops,
        filters, fader chops and swells. Read it, don't guess.
  audio.py onset T
        exact onset (+-5 ms) of the bass hit that starts at/just after T (searches T-0.1 .. T+0.6; pass T = the env row where the burst starts).
        Use it on the drop you found in `env` -> that value is your drop time and beat0.
  audio.py bpm A B
        tempo of the steady kicks in [A,B] (reliable to ~0.05 bpm). Use 5-10 s right AFTER a real drop.
        A DJ set's BPM usually changes over the night, so measure it per clip.

Pitfalls (all of these happened while building this kit, see STYLE.md "Music timing"):
  * a bass SWELL / single stab before the drop is NOT the drop (the drop is the first beat of the full,
    regular kick + bass; in one case: swell 0.9 s early, stab 0.5 s early)
  * a drop WITHOUT bass (low EQ turned down) is not the bass drop; the bass coming back is
  * every automatic beat grid tried was off by 0.5-2 beats. Always check `env --grid`:
    after the drop, the big B### bursts must start on the '|' rows.
  * `onset` can read early when a bass line runs underneath; if it lands >30 ms before the `|` row burst,
    take the `|` row.
"""
import os, sys, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proj

P = proj.load(argv=sys.argv)
C = P.cache
SR = 4000
OFF = -P.audio_offset  # audio file time = timeline time - OFF


def ensure_cache():
    os.makedirs(C, exist_ok=True)
    full, bass = os.path.join(C, "set_4k.f32"), os.path.join(C, "bass.f32")
    if not os.path.exists(full):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", P.audio_file, "-ac", "1", "-ar", str(SR),
                        "-f", "f32le", full], check=True)
    if not os.path.exists(bass):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", full,
                        "-af", "lowpass=f=110,lowpass=f=110", "-f", "f32le", bass], check=True)
    return np.memmap(full, dtype=np.float32, mode="r"), np.memmap(bass, dtype=np.float32, mode="r")


X, BASS = ensure_cache()


def idx(t):
    return int((t - OFF) * SR)


def rms(sig, a, b, hop=0.005, win=0.01):
    s = np.asarray(sig[idx(a):idx(b) + int(win * SR)], dtype=np.float64) ** 2
    n, h = int(win * SR), int(hop * SR)
    cs = np.concatenate([[0], np.cumsum(s)])
    starts = np.arange(0, len(s) - n, h)
    return a + starts / SR, np.sqrt((cs[starts + n] - cs[starts]) / n)


def onset(T):
    a = T - 0.1
    s = np.asarray(BASS[idx(a):idx(T + 0.6)], dtype=np.float64) ** 2
    env = np.convolve(s, np.ones(40) / 40, "same")
    m = env.max()
    i = int(np.argmax(env > 0.25 * m))
    return a + i / SR


def bpm(a, b):
    t, e = rms(BASS, a, b, hop=0.0025, win=0.01)
    r = np.maximum(0, e[2:] - e[:-2]); t = t[1:-1]
    best = (0, 0)
    for v in np.arange(140, 176, 0.01):
        P = 60 / v
        h, _ = np.histogram((t - a) % P, bins=int(P / 0.005), range=(0, P), weights=r)
        h = h + np.roll(h, 1) + np.roll(h, -1)
        if h.max() > best[0]:
            best = (h.max(), v)
    return best[1]


def mmss(t):
    return f"{int(t // 60)}:{t % 60:06.3f}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "onset":
        T = float(sys.argv[2]); o = onset(T)
        print(f"onset {o:.3f}  ({mmss(o)})")
    elif cmd == "bpm":
        print(f"bpm {bpm(float(sys.argv[2]), float(sys.argv[3])):.2f}")
    elif cmd == "env":
        a, b = float(sys.argv[2]), float(sys.argv[3])
        rest = sys.argv[4:]
        step, gb = 0.048, None
        while rest:
            k = rest.pop(0)
            if k == "--step": step = float(rest.pop(0))
            elif k == "--grid":
                v, b0 = map(float, rest.pop(0).split(",")); gb = (60 / v, b0)
        for t in np.arange(a, b, step):
            s, e = idx(t), idx(t) + int(step * SR)
            rb = np.sqrt(np.mean(np.asarray(BASS[s:e], dtype=np.float64) ** 2))
            rx = np.sqrt(np.mean(np.asarray(X[s:e], dtype=np.float64) ** 2))
            mark = " "
            if gb:
                k = (t - gb[1]) / gb[0]
                mark = "|" if abs(k - round(k)) * gb[0] < step / 2 else " "
            print(f"{t:9.3f} {mmss(t)}{mark} B{'#' * int(rb * 50):<36} X{'*' * int(rx * 36)}")
    else:
        sys.exit(__doc__)
