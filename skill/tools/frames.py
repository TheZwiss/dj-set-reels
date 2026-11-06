"""Labelled contact sheets, so you SEE what happens at which second before you place a cut or caption.

  frames.py src CAM T0 T1 FPS out.jpg [--crop X,Y,W,H] [--offset S] [--cols N] [--tw PX]
      CAM = a camera name from project.json (usually djcam | crowd | top). T0/T1 = timeline seconds.
      Each tile is labelled with its timeline time (mm:ss.ss). --crop is in source pixels
      (see the camera's w/h in project.json). --offset = per-clip sync correction from offs.py.
  frames.py out VIDEO T0 T1 FPS out.jpg [--cols N] [--tw PX]
      Same for a rendered reel; labels are OUTPUT times (what the user sees in the player).

Typical use: 1 fps over the whole moment to get the story, then 4 fps over every key action
(face lights up, scream, hand on knob, someone walks in) to find the exact frame.
Keep sheets <= ~40 tiles so they stay readable.
"""
import os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proj

P = proj.load(argv=sys.argv)
LABEL = ImageFont.truetype(P.font_label, 22)


def mmss(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def grab(path, ss, dur, fps, vf_pre, w, h):
    vf = f"{vf_pre}fps={fps},scale={w}:{h},format=rgb24"
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-i", path, "-t", f"{dur:.3f}", "-an",
                        "-vf", vf, "-f", "rawvideo", "-"], capture_output=True, check=True)
    n = len(r.stdout) // (w * h * 3)
    return [Image.frombuffer("RGB", (w, h), r.stdout[i * w * h * 3:(i + 1) * w * h * 3], "raw", "RGB", 0, 1)
            for i in range(n)]


def sheet(tiles, labels, cols, out):
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (tw * cols, th * rows))
    d = ImageDraw.Draw(S)
    for i, (im, lab) in enumerate(zip(tiles, labels)):
        x, y = (i % cols) * tw, (i // cols) * th
        S.paste(im, (x, y))
        d.text((x + 6, y + 4), lab, font=LABEL, fill=(255, 255, 0), stroke_width=3, stroke_fill=(0, 0, 0))
    S.save(out, quality=85)
    print(f"{out}  ({len(tiles)} tiles)")


def opt(args, k, default, f=str):
    return f(args[args.index(k) + 1]) if k in args else default


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 6:
        sys.exit(__doc__)
    mode = a[0]
    cols, tw = opt(a, "--cols", 6, int), opt(a, "--tw", 0, int)
    if mode == "src":
        cam, t0, t1, fps, out = a[1], float(a[2]), float(a[3]), float(a[4]), a[5]
        cc = P.cam(cam)
        W, H = cc["w"], cc["h"]
        pre = (cc["vf"] + ",") if cc.get("vf") else ""
        crop = opt(a, "--crop", None)
        if crop:
            x, y, cw, ch = map(int, crop.split(","))
            pre = pre + f"crop={cw}:{ch}:{x}:{y},"
            W, H = cw, ch
        tw = tw or 320
        th = int(round(tw * H / W / 2)) * 2
        ss = P.src(cam, t0) + opt(a, "--offset", 0.0, float)
        tiles = grab(P.cam_file(cam), ss, t1 - t0, fps, pre, tw, th)
        labels = [mmss(t0 + i / fps) for i in range(len(tiles))]
    elif mode == "out":
        video, t0, t1, fps, out = a[1], float(a[2]), float(a[3]), float(a[4]), a[5]
        tw = tw or 216
        tiles = grab(video, t0, t1 - t0, fps, "", tw, int(tw * 16 / 9) // 2 * 2)
        labels = [f"{t0 + i / fps:.2f}s" for i in range(len(tiles))]
    else:
        sys.exit(__doc__)
    sheet(tiles, labels, cols, out)
