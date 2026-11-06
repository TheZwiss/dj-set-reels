"""QC for a rendered reel.  check.py CFG.json VIDEO.mp4 STRIP.jpg

Prints duration, loudness, true peak, the caption + drop timeline in OUTPUT time (what the user sees
in the player), and warnings. Writes one strip image: a frame 0.3 s after every caption start and
0.1 s after every drop, labelled -> this strip is what the orchestrator looks at.
"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proj

LABEL = ImageFont.truetype(proj._first_font(proj.LABEL_FONTS), 17)


def main(cfgp, video, strip):
    cfg = json.load(open(cfgp))
    chunks = cfg["chunks"]

    def ot(st):
        acc = 0.0
        for a, b in chunks:
            if a - 1e-6 <= st <= b + 1e-6:
                return acc + st - a
            acc += b - a
        return None

    warn = []
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                video], capture_output=True, text=True).stdout)
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1]); pk = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    print(f"{video}\n  duration {dur:.2f}s  loudness {I} LUFS  true peak {pk} dBFS")
    if pk > -0.3: warn.append(f"true peak {pk} dBFS > -0.3 -> lower gain_db and re-render")
    if not (-12.5 <= I <= -8.5): warn.append(f"loudness {I} LUFS outside -12.5..-8.5 (target -9.5..-11)")
    if not (14 <= dur <= 40): warn.append(f"duration {dur:.1f}s outside 14-40 s")

    marks = []
    print("  timeline (output time = player time):")
    caps = sorted(cfg.get("captions", []), key=lambda c: c["a"])
    for i, c in enumerate(caps):
        a, b = ot(c["a"]), ot(c["b"])
        if a is None or b is None:
            warn.append(f"caption {c['text']!r} starts/ends outside the chunks"); continue
        print(f"    {a:6.2f}-{b:6.2f}s  \"{c['text'].replace(chr(10), ' / ')}\"  (set {c['a']:.3f})")
        if i and caps[i - 1]["b"] > c["a"] + 1e-3 and caps[i - 1].get("y", 430) == c.get("y", 430):
            warn.append(f"captions overlap: {caps[i-1]['text']!r} / {c['text']!r}")
        marks.append((min(a + 0.3, b - 0.05), f"{a:.2f}s {c['text'].replace(chr(10), ' ')}"[:34]))
    for d in cfg.get("drops", []):
        o = ot(d)
        if o is None:
            warn.append(f"drop {d} outside the chunks"); continue
        print(f"    {o:6.2f}s  DROP (set {d:.3f})")
        marks.append((o + 0.1, f"{o:.2f}s DROP"))
    if any(c["text"].strip() in "1234" for c in caps):
        warn.append("countdown digits found - only allowed for pure hard-drop clips with a break bar (STYLE.md)")

    marks.sort()
    tiles = []
    for t, lab in marks:
        p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1",
                            "-vf", "scale=216:384,format=rgb24", "-f", "rawvideo", "-"], capture_output=True)
        if len(p.stdout) == 216 * 384 * 3:
            im = Image.frombuffer("RGB", (216, 384), p.stdout, "raw", "RGB", 0, 1).copy()
            ImageDraw.Draw(im).text((4, 360), lab, font=LABEL, fill=(255, 255, 0), stroke_width=2,
                                    stroke_fill=(0, 0, 0))
            tiles.append(im)
    if tiles:
        S = Image.new("RGB", (216 * min(len(tiles), 8), 384 * ((len(tiles) + 7) // 8)))
        for i, im in enumerate(tiles):
            S.paste(im, ((i % 8) * 216, (i // 8) * 384))
        S.save(strip, quality=85)
        print(f"  strip: {strip}")
    print("  WARNINGS:" if warn else "  no warnings")
    for w in warn:
        print("   -", w)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
