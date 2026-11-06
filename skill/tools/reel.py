"""Vertical reel renderer: multicam DJ set -> 1080x1920 beat-synced reel.

  reel.py CFG.json OUT.mp4                       render
  reel.py CFG.json --preview S1,S2,... OUT.jpg   preview frames at timeline seconds S (a strip of thumbnails)

All times in the cfg are timeline seconds (see proj.py). The project (cameras, sync, set audio, fonts,
brand line) is read from the project.json found above the cfg file.
"""
import json, math, subprocess, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import proj
from proj import W, H

P = None  # Project, set in main
FPS = 25


def cam_info(name):
    c = P.cam(name)
    return dict(file=P.cam_file(name), w=c["w"], h=c["h"], cx=c.get("cx", c["w"] / 2), cy=c.get("cy", c["h"] / 2),
                vf=c.get("vf") or "null")


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


class Reel:
    def __init__(self, cfg):
        self.cfg = cfg
        self.beat = 60.0 / cfg["bpm"]
        self.beat0 = cfg["beat0"]
        self.offsets = cfg.get("offsets", {})  # per-cam sync correction (s)
        # chunks: contiguous set-time ranges; output timeline = concatenation
        self.chunks = cfg["chunks"]
        self.out_len = sum(b - a for a, b in self.chunks)

    # map output time -> set time
    def set_time(self, ot):
        acc = 0.0
        for a, b in self.chunks:
            if ot < acc + (b - a) or (a, b) == tuple(self.chunks[-1]):
                return a + (ot - acc)
            acc += b - a

    def out_time(self, st):
        acc = 0.0
        for a, b in self.chunks:
            if a - 1e-6 <= st <= b + 1e-6:
                return acc + st - a
            acc += b - a
        raise ValueError(st)

    def font(self, size, display=True):
        return ImageFont.truetype(P.font_display if display else P.font_text, size)

    def text_img(self, text, size, display=True, stroke=None, fill=(255, 255, 255)):
        # glyphs missing from the caption font (e.g. "?", "·") come from the fallback fonts
        fpath = P.font_display if display else P.font_text
        f = self.font(size, display)
        chain = [(f, P.charset_of(fpath))]
        for fbp in (P.font_fallback, P.font_label):
            if fbp != fpath:
                chain.append((ImageFont.truetype(fbp, int(size * 0.92)), P.charset_of(fbp)))
        def pick(ch):
            if ch.isspace():
                return f
            for ff, cs in chain:
                if ch in cs:
                    return ff
            return None
        bad = [c for c in text if c != "\n" and pick(c) is None]
        if bad:
            raise ValueError(f"glyphs not in any font: {bad!r} in {text!r}")
        stroke = stroke if stroke is not None else max(3, size // 14)
        lines = text.split("\n")
        def runs(l):
            out = []
            for ch in l:
                ff = pick(ch)
                if out and out[-1][1] is ff: out[-1][0] += ch
                else: out.append([ch, ff])
            return out
        widths = [sum(ff.getlength(r) for r, ff in runs(l)) + 2 * stroke for l in lines]
        asc = f.getmetrics()[0]
        lh = int(size * 1.08)
        wmax = int(max(widths)) + 1
        img = Image.new("RGBA", (wmax + 40, lh * len(lines) + 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i, (l, w) in enumerate(zip(lines, widths)):
            x = 20 + (wmax - w) / 2 + stroke; y = 20 + i * lh + asc
            for r, ff in runs(l):
                d.text((x, y), r, font=ff, anchor="ls", fill=fill + (255,), stroke_width=stroke,
                       stroke_fill=(0, 0, 0, 255))
                x += ff.getlength(r)
        # soft shadow
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: v * 0.55))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 6))
        out.alpha_composite(img)
        return out

    def beats_in(self, t0, t1):
        k = math.ceil((t0 - self.beat0) / self.beat - 1e-6)
        while True:
            t = self.beat0 + k * self.beat
            if t >= t1:
                return
            yield k, t
            k += 1

    def render(self, out_path, preview_frames=None):
        cfg = self.cfg
        shots = cfg["shots"]  # each: set-time start, end, cam, opts
        captions = cfg.get("captions", [])
        cap_imgs = [self.text_img(c["text"], c.get("size", 92), c.get("display", True)) for c in captions]
        brand_text = cfg.get("brand", P.brand)
        brand = self.text_img(brand_text, 40, display=False, stroke=3) if brand_text else None
        drops = cfg.get("drops", [])
        pulse_ranges = cfg.get("pulse", [])  # set-time ranges with kick pulse

        enc = None
        if preview_frames is None:
            audio = out_path + ".wav"
            self.render_audio(audio)
            enc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                 "-r", str(FPS), "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a",
                 "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                 "-profile:v", "high", "-c:a", "aac", "-b:a", "320k", "-shortest",
                 "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
        total_frames = int(round(self.out_len * FPS))
        frame_idx = 0
        previews = []
        for si, sh in enumerate(shots):
            a, b, cam = sh["a"], sh["b"], sh["cam"]
            f0 = int(round(self.out_time(a) * FPS))
            f1 = int(round(self.out_time(b) * FPS)) if si < len(shots) - 1 else total_frames
            n = f1 - f0
            if n <= 0:
                continue
            c = cam_info(cam)
            start_src = P.src(cam, a + (f0 / FPS - self.out_time(a))) + self.offsets.get(cam, 0.0)
            dec = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-ss", f"{start_src:.4f}", "-i", c["file"], "-an",
                 "-vf", c["vf"] + ",format=rgb24", "-frames:v", str(n), "-f", "rawvideo", "-"],
                stdout=subprocess.PIPE)
            fsz = c["w"] * c["h"] * 3
            for i in range(n):
                raw = dec.stdout.read(fsz)
                if len(raw) < fsz:
                    raw = last_raw  # pad with last frame if source ends early
                last_raw = raw
                ot = (f0 + i) / FPS
                st = a + (ot - self.out_time(a))
                want = preview_frames is None or (f0 + i) in preview_frames
                if not want:
                    continue
                frame = Image.frombuffer("RGB", (c["w"], c["h"]), raw, "raw", "RGB", 0, 1)
                img = self.compose(frame, c, sh, st, ot, a, b, drops, pulse_ranges)
                img = self.overlay(img, ot, captions, cap_imgs, brand)
                if enc:
                    enc.stdin.write(img.tobytes())
                else:
                    previews.append((f0 + i, img))
            dec.stdout.close(); dec.wait()
            frame_idx = f1
        if enc:
            enc.stdin.close(); enc.wait()
            os.remove(out_path + ".wav")
        return previews

    def compose(self, frame, c, sh, st, ot, a, b, drops, pulse_ranges):
        dur = b - a
        p = (st - a) / dur if dur > 0 else 0
        z0, z1 = sh.get("zoom", (1.0, 1.0))
        ez = sh.get("ease", "linear")
        pp = ease_out(p) if ez == "out" else p
        z = z0 + (z1 - z0) * pp
        cx = sh.get("cx", c["cx"]); cy = sh.get("cy", c["cy"])
        if "cx1" in sh:
            cx = cx + (sh["cx1"] - cx) * pp
        dx = dy = 0.0
        flash = 0.0
        for d in drops:
            dt = st - d
            if 0 <= dt < 0.6:
                z *= 1 + 0.16 * (1 - ease_out(dt / 0.35))  # punch-in that settles
                amp = 14 * math.exp(-dt / 0.18)
                dx += amp * math.sin(dt * 95); dy += amp * math.cos(dt * 77)
            if 0 <= dt < 0.16:
                flash = max(flash, 0.85 * (1 - dt / 0.16))
        for r0, r1 in pulse_ranges:
            if r0 <= st < r1:
                # kick pulse: small zoom bump on every beat
                k = (st - self.beat0) / self.beat
                ph = (k - math.floor(k)) * self.beat
                z *= 1 + 0.035 * math.exp(-ph / 0.07)
        base = H / c["h"]
        s = base * z
        # clamp so the crop stays inside the source (when covering)
        half_w = W / 2 / s; half_h = H / 2 / s
        if half_w * 2 <= c["w"]:
            cx = min(max(cx, half_w), c["w"] - half_w)
        if half_h * 2 <= c["h"]:
            cy = min(max(cy, half_h), c["h"] - half_h)
        cx -= dx / s; cy -= dy / s
        data = (1 / s, 0, cx - W / 2 / s, 0, 1 / s, cy - H / 2 / s)
        img = frame.transform((W, H), Image.AFFINE, data, resample=Image.BICUBIC)
        if z < 1.0:  # fit mode: blurred cover behind
            sb = (H / c["h"]) * 1.0
            bg = frame.resize((int(c["w"] * sb / 8), int(c["h"] * sb / 8)), Image.BILINEAR)
            bgx = (bg.width - W / 8) / 2
            bg = bg.crop((int(bgx), 0, int(bgx + W / 8), int(H / 8))).filter(ImageFilter.GaussianBlur(6))
            bg = bg.resize((W, H), Image.BILINEAR).point(lambda v: int(v * 0.55))
            mask = Image.new("L", (W, H), 0)
            top = int(H / 2 - c["h"] * s / 2); bot = int(H / 2 + c["h"] * s / 2)
            ImageDraw.Draw(mask).rectangle((0, max(top, 0), W, min(bot, H)), fill=255)
            bg.paste(img, (0, 0), mask)
            img = bg
        if flash > 0:
            img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), flash)
        return img

    def overlay(self, img, ot, captions, cap_imgs, brand):
        img = img.convert("RGBA")
        for c, ci in zip(captions, cap_imgs):
            t0 = self.out_time(c["a"]); t1 = self.out_time(c["b"])
            if not (t0 <= ot < t1):
                continue
            age = ot - t0
            sc = 0.82 + 0.18 * ease_out(age / 0.12) if c.get("pop", True) else 1.0
            if c.get("punch"):
                sc *= 1 + 0.12 * math.exp(-age / 0.08)
            alpha = min(1.0, (t1 - ot) / 0.08) if c.get("fade_out", True) else 1.0
            im = ci if abs(sc - 1) < 1e-3 else ci.resize((max(1, int(ci.width * sc)), max(1, int(ci.height * sc))), Image.BICUBIC)
            if c.get("rot"):
                im = im.rotate(c["rot"], resample=Image.BICUBIC, expand=True)
            if alpha < 1:
                im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
            y = int(c.get("y", 430) - im.height / 2)
            x = int(c.get("x", W / 2) - im.width / 2)
            x = max(0, min(W - im.width, x))
            img.alpha_composite(im, (x, y))
        if brand is not None:
            b = brand.copy(); b.putalpha(b.getchannel("A").point(lambda v: int(v * 0.8)))
            img.alpha_composite(b, (int(W / 2 - b.width / 2), 210))
        return img.convert("RGB")

    def render_audio(self, out_wav):
        parts = []
        inputs = []
        xf = self.cfg.get("audio_xfade", 0.03)
        for i, (a, b) in enumerate(self.chunks):
            inputs += ["-ss", f"{P.audio_time(a) - (xf if i else 0):.4f}", "-t", f"{b - a + (xf if i else 0) + (xf if i < len(self.chunks)-1 else 0):.4f}", "-i", P.audio_file]
        n = len(self.chunks)
        if n == 1:
            fc = "[0:a]anull[m]"
        else:
            fc = "[0:a][1:a]acrossfade=d=%.3f:c1=tri:c2=tri[x1]" % (2 * xf)
            for i in range(2, n):
                fc += ";[x%d][%d:a]acrossfade=d=%.3f:c1=tri:c2=tri[x%d]" % (i - 1, i, 2 * xf, i)
            fc += ";[x%d]anull[m]" % (n - 1)
        L = self.out_len
        fc += (f";[m]afade=t=in:d=0.04,afade=t=out:st={L - 0.35:.3f}:d=0.35,"
               f"volume={self.cfg.get('gain_db', 0)}dB,alimiter=limit=0.89:attack=3:release=60,"
               f"atrim=0:{L:.4f}[o]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[o]",
                        "-ar", "48000", "-c:a", "pcm_s16le", out_wav], check=True)


if __name__ == "__main__":
    argv = sys.argv[1:]
    explicit = proj.pop_project_arg(argv)
    sys.argv = [sys.argv[0]] + argv
    if len(argv) < 2:
        sys.exit(__doc__)
    P = proj.Project(proj.find_root(sys.argv[1], explicit))
    FPS = P.fps
    cfg = json.load(open(sys.argv[1]))
    r = Reel(cfg)
    if len(sys.argv) > 3 and sys.argv[2] == "--preview":
        times = [float(x) for x in sys.argv[3].split(",")]
        frames = {int(round(r.out_time(t) * FPS)) for t in times}
        pv = r.render(None, preview_frames=frames)
        thumbs = [im.resize((270, 480)) for _, im in sorted(pv)]
        sheet = Image.new("RGB", (270 * len(thumbs), 480))
        for i, t in enumerate(thumbs):
            sheet.paste(t, (270 * i, 0))
        sheet.save(sys.argv[4])
    else:
        r.render(sys.argv[2])
