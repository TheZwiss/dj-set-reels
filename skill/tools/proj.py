"""Shared project loader for all dj-reels tools.

A *project* is a folder with a `project.json` (created by `setup_project.py init`). Every tool finds it
like this:
  1. `--project DIR` on the command line, or
  2. the REELS_PROJECT environment variable, or
  3. walking up from the current directory (or from the cfg.json you pass) until it finds project.json.

Timeline: all times in cfgs and on the command line are *timeline seconds* = the timestamps the DJ uses
for their set (normally: position in the set recording). The set audio file time = t + audio.offset.
Camera source time = cam.sync.offset + t * cam.sync.speed (+ a per-clip cfg "offsets" correction).
"""
import json, os, shutil, subprocess, sys

W, H = 1080, 1920
TOOLS = os.path.dirname(os.path.abspath(__file__))

FALLBACK_FONTS = [  # rounded/bold sans used for glyphs the display font lacks, and for labels
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
LABEL_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _first_font(cands):
    for c in cands:
        if os.path.exists(c):
            return c
    if shutil.which("fc-match"):
        r = subprocess.run(["fc-match", "-f", "%{file}", "sans:bold"], capture_output=True, text=True)
        if r.stdout and os.path.exists(r.stdout):
            return r.stdout
    sys.exit("no usable bold sans font found; set fonts.display / fonts.text in project.json")


def pop_project_arg(argv):
    """Remove `--project DIR` from argv (in place) and return DIR or None."""
    if "--project" in argv:
        i = argv.index("--project")
        d = argv[i + 1]
        del argv[i:i + 2]
        return d
    return None


def find_root(start=None, explicit=None):
    if explicit:
        return os.path.abspath(explicit)
    if os.environ.get("REELS_PROJECT"):
        return os.path.abspath(os.environ["REELS_PROJECT"])
    d = os.path.abspath(start or os.getcwd())
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        if os.path.isfile(os.path.join(d, "project.json")):
            return d
        nd = os.path.dirname(d)
        if nd == d:
            sys.exit("project.json not found. cd into the reels project folder first, pass --project DIR, "
                     "or set REELS_PROJECT.")
        d = nd


class Project:
    def __init__(self, root):
        self.root = root
        self.path = os.path.join(root, "project.json")
        self.cfg = json.load(open(self.path))
        c = self.cfg
        self.media_dir = c.get("media_dir", root)
        self.fps = c.get("fps", 25)
        self.brand = c.get("brand", "")
        self.audio_file = self.media(c["audio"]["file"])
        self.audio_offset = c["audio"].get("offset", 0.0)
        self.cams = c["cameras"]
        self.cache = os.path.join(root, ".cache")
        f = c.get("fonts", {})
        fb = _first_font(FALLBACK_FONTS)
        self.font_display = self.media(f["display"]) if f.get("display") else fb
        self.font_text = self.media(f["text"]) if f.get("text") else self.font_display
        self.font_fallback = fb
        self.font_label = _first_font(LABEL_FONTS)
        self._charset = None

    def media(self, f):
        return f if os.path.isabs(f) else os.path.join(self.media_dir, f)

    def cam(self, name):
        if name not in self.cams:
            sys.exit(f"unknown camera {name!r}; project cameras: {', '.join(self.cams)}")
        return self.cams[name]

    def cam_file(self, name):
        return self.media(self.cam(name)["file"])

    def src(self, name, t):
        """timeline seconds -> camera source-file seconds"""
        s = self.cam(name).get("sync", {})
        return s.get("offset", 0.0) + t * s.get("speed", 1.0)

    def audio_time(self, t):
        return t + self.audio_offset

    def charset_of(self, path):
        """characters a font file can draw (from its cmap)"""
        if self._charset is None:
            self._charset = {}
        if path not in self._charset:
            from fontTools.ttLib import TTFont
            try:
                cmap = TTFont(path, fontNumber=0).getBestCmap() or {}
                self._charset[path] = {chr(k) for k in cmap}
            except Exception:
                self._charset[path] = set()
        return self._charset[path]

    def save(self):
        with open(self.path, "w") as fh:
            json.dump(self.cfg, fh, indent=2)
            fh.write("\n")


def load(start=None, argv=None):
    explicit = pop_project_arg(argv) if argv is not None else None
    return Project(find_root(start, explicit))
