"""Create a reels project and sync the cameras to the set recording.

  setup_project.py init PROJECT_DIR --media DIR --audio FILE --cam djcam=FILE [--cam crowd=FILE]
                        [--cam top=FILE] [--brand "NAME · live at VENUE"] [--audio-offset S]
                        [--font-display TTF] [--font-text TTF] [--fps 25] [--no-sync]
      Writes PROJECT_DIR/project.json, STYLE.md (the default taste), QUEUE.md, and the clips/, Review/
      and Approved/ folders. Then it runs `sync` for every camera with an audio track.
      FILE paths are relative to --media (or absolute). --audio is the best recording of the set
      (mixer/USB recording); a camera file works too if there's nothing better.
      Timeline seconds = position in that audio file + --audio-offset (default 0). Use an offset only
      if the DJ's timestamps come from a different video (e.g. an edited full-set video).

  setup_project.py sync [--cam NAME] [--points N (default 16)]
      (Run inside the project.) Finds where each camera sits in the set recording: a coarse match over
      the whole file (10 ms), then fine matches at N points (1 ms), then a linear drift fit.
      Writes cameras.<name>.sync = {offset, speed} into project.json and prints residuals per point.
      Cameras without audio can't be synced automatically: set their offset by hand (see SKILL.md).

  setup_project.py info
      Prints the project summary (cameras, sizes, sync, audio length).
"""
import json, os, shutil, subprocess, sys
import numpy as np
from scipy.signal import butter, sosfiltfilt, fftconvolve

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proj
import offs

SKILL = os.path.dirname(HERE)
SR = 4000


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height:stream_side_data=rotation:stream_tags=rotate:format=duration",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s.get("codec_type") == "video"), None)
    a = any(s.get("codec_type") == "audio" for s in j["streams"])
    info = {"duration": float(j["format"]["duration"]), "has_audio": a}
    if v:
        w, h = v["width"], v["height"]
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        rot = rot or int(v.get("tags", {}).get("rotate", 0) or 0)
        if abs(rot) % 180 == 90:  # ffmpeg auto-rotates on decode
            w, h = h, w
        info.update(w=w, h=h)
    return info


def bass_env(path, hop=0.01):
    """whole-file bass envelope (log rms, 40-150 Hz) at 1/hop Hz"""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    x = np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)
    sos = butter(4, [40, 150], btype="band", fs=SR, output="sos")
    y = sosfiltfilt(sos, x) ** 2
    n = int(hop * SR)
    m = len(y) // n
    e = np.log(np.sqrt(y[:m * n].reshape(m, n).mean(1)) + 1e-4)
    return e - e.mean()


def coarse(P, cam):
    """camera time = audio time - lag; returns lag (s) and a match score"""
    a = bass_env(P.audio_file); c = bass_env(P.cam_file(cam))
    cc = fftconvolve(a, c[::-1], mode="full")  # peak at k = (len(c)-1) + lag
    k = int(np.argmax(cc)); lag = (k - (len(c) - 1)) * 0.01
    z = (cc.max() - cc.mean()) / (cc.std() + 1e-12)
    return lag, z


def sync_cam(P, cam, npts=16):
    c = P.cam(cam)
    info = probe(P.cam_file(cam))
    if not info["has_audio"]:
        print(f"{cam}: no audio track -> set cameras.{cam}.sync.offset by hand (see SKILL.md)"); return
    lag, zc = coarse(P, cam)
    # cam time = audio time - lag = t + audio_offset - lag
    c["sync"] = {"offset": round(P.audio_offset - lag, 4), "speed": 1.0}
    adur = probe(P.audio_file)["duration"]
    t_lo = max(-P.audio_offset, (0 - c["sync"]["offset"])) + 30
    t_hi = min(adur - P.audio_offset, info["duration"] - c["sync"]["offset"]) - 30
    print(f"{cam}: coarse lag {lag:+.2f} s (z={zc:.1f}); overlap {t_lo:.0f}..{t_hi:.0f} s timeline")
    if t_hi - t_lo < 60:
        print(f"  overlap too short for a drift fit; keeping the coarse sync"); return
    for rnd in range(2):
        ts = np.linspace(t_lo, t_hi - 20, npts)
        pts = []
        for t in ts:
            o, z = offs.measure(P, cam, float(t))
            if o is not None:
                pts.append((float(t), o, z))
        # club audio gives low z scores (2-4), so use every point and reject outliers robustly
        T = np.array([p[0] for p in pts]); O = np.array([p[1] for p in pts])
        for _ in range(3):  # robust linear fit
            A = np.vstack([np.ones_like(T), T]).T
            coef, *_ = np.linalg.lstsq(A, O, rcond=None)
            res = O - A @ coef
            keep = np.abs(res - np.median(res)) < max(0.03, 3 * np.median(np.abs(res - np.median(res))))
            if keep.all() or keep.sum() < 3:
                break
            T, O = T[keep], O[keep]
        a0, b0 = coef
        s = c["sync"]
        # cam = off + t*sp + (a0 + b0 t)
        s["offset"] = round(float(s["offset"] + a0), 5); s["speed"] = round(float(s["speed"] + b0), 9)
        print(f"  pass {rnd + 1}: correction {a0 * 1000:+.0f} ms + {b0 * 1e6:+.1f} ppm "
              f"({len(T)}/{len(pts)} points used)")
    print(f"  residuals after fit (ms): " + " ".join(f"{t / 60:.0f}m:{o * 1000:+.0f}(z{z:.0f})" for t, o, z in pts))
    P.save()
    print(f"  -> cameras.{cam}.sync = {c['sync']}")


def init(argv):
    root = os.path.abspath(argv.pop(0))
    def opt(k, default=None, multi=False):
        vals = []
        while k in argv:
            i = argv.index(k); vals.append(argv[i + 1]); del argv[i:i + 2]
        return vals if multi else (vals[-1] if vals else default)
    media = os.path.abspath(opt("--media", root))
    audio = opt("--audio"); cams = opt("--cam", multi=True)
    if not audio or not cams:
        sys.exit("init needs --audio FILE and at least one --cam NAME=FILE\n\n" + __doc__)
    nosync = "--no-sync" in argv
    os.makedirs(root, exist_ok=True)
    pj = os.path.join(root, "project.json")
    if os.path.exists(pj):
        sys.exit(f"{pj} exists already; edit it or use `sync`")
    cfg = {"brand": opt("--brand", ""), "media_dir": media, "fps": int(opt("--fps", 25)),
           "audio": {"file": audio, "offset": float(opt("--audio-offset", 0.0))},
           "fonts": {"display": opt("--font-display"), "text": opt("--font-text")},
           "cameras": {}}
    for spec in cams:
        name, f = spec.split("=", 1)
        path = f if os.path.isabs(f) else os.path.join(media, f)
        info = probe(path)
        cfg["cameras"][name] = {"file": f, "w": info["w"], "h": info["h"],
                                "cx": info["w"] // 2, "cy": info["h"] // 2,
                                "vf": "eq=contrast=1.06:saturation=1.08",
                                "sync": {"offset": 0.0, "speed": 1.0}}
        print(f"{name}: {f} {info['w']}x{info['h']} {info['duration'] / 60:.1f} min audio={info['has_audio']}")
    probe(os.path.join(media, audio) if not os.path.isabs(audio) else audio)
    with open(pj, "w") as fh:
        json.dump(cfg, fh, indent=2); fh.write("\n")
    for d in ("clips", "Review", "Approved", ".cache"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    if not os.path.exists(os.path.join(root, "STYLE.md")):
        shutil.copy(os.path.join(SKILL, "STYLE_DEFAULT.md"), os.path.join(root, "STYLE.md"))
    if not os.path.exists(os.path.join(root, "QUEUE.md")):
        shutil.copy(os.path.join(SKILL, "templates", "QUEUE.md"), os.path.join(root, "QUEUE.md"))
    print(f"project created: {root}")
    if not nosync:
        P = proj.Project(root)
        for cam in P.cams:
            sync_cam(P, cam)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a.pop(0)
    if cmd == "init":
        init(a)
    elif cmd == "sync":
        P = proj.load(argv=a)
        only = a[a.index("--cam") + 1] if "--cam" in a else None
        n = int(a[a.index("--points") + 1]) if "--points" in a else 16
        for cam in ([only] if only else list(P.cams)):
            sync_cam(P, cam, n)
    elif cmd == "info":
        P = proj.load(argv=a)
        print(f"project {P.root}\n audio {P.audio_file} (offset {P.audio_offset})  brand {P.brand!r}")
        for n, c in P.cams.items():
            print(f" {n}: {c['file']} {c['w']}x{c['h']} sync {c.get('sync')}")
    else:
        sys.exit(__doc__)
