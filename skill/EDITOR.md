# Reel editor procedure (one clip per run)

You are the **reel editor**. You make or fix ONE reel and report back to the orchestrator.

**Read the project's `STYLE.md` completely before you start.** It holds the DJ's taste, and following
it is the whole job.

```
R = <project folder from your task: the folder with project.json>
T = ~/.claude/skills/dj-reels/tools        P = $T/.venv/bin/python
```

Run every tool from inside the project, e.g. `cd "$R" && $P "$T/audio.py" env 600 615`. Quote paths,
because they may contain spaces. Work files (contact sheets, previews) go in `$R/clips/<ID>_<slug>/work/`.

All times are **timeline seconds**: the DJ's timestamps (12:06 = 726 s). Output times (what the DJ sees
in the player) apply only to `frames.py out` and `check.py`. `project.json` lists the cameras (names,
sizes, sync) and the set recording. Read it once.

## Hard rules

- Never touch `Approved/`, `project.json` or any source media.
  Delete only inside `clips/<ID>_<slug>/work/`.
- Make or fix only the clip you were given. Render at most one final file per run, plus a re-render
  if QC fails.
- You can't ask the DJ anything. Make the best call and list doubts under `unsure:` in your report.
- Text the DJ dictated (captions, times) is used **verbatim** and overrides STYLE.md.
- Don't claim something is verified unless you looked at it (frames) or measured it (audio).

## Steps

### 1. Read the inputs

- The `QUEUE.md` row for your clip: the DJ's own notes on the moment.
- `clips/<ID>_<slug>/notes.md`, if it exists. On a fix run it holds the feedback history, and all of that
  feedback still applies. Keep the previous cfg as `work/cfg_v<N>.json` before you change it.
- One approved `clips/*/cfg.json` that's closest to your clip type, as a template (if there is one).

### 2. Audio: understand the music

- Look at the envelope with `$P "$T/audio.py" env A B`. Use the DJ's window ±10 s. Run it in pieces of
  about 15 s, because the output is long.
- Write down the buildup, the **real drop(s)**, any fake drop or swell, filters, chops and mix-ins.
  Use the drop rules in STYLE.md "Music timing".
- Get the exact drop time with `$P "$T/audio.py" onset T`, where T is the env row where the drop burst
  starts.
- Get the tempo with `$P "$T/audio.py" bpm D D+8`.
- Verify the grid with `$P "$T/audio.py" env D-3 D+3 --grid BPM,D`. The `B###` bursts after the drop
  must start on the `|` rows. If the onset lands more than 30 ms before a `|` row's burst, take the
  `|` row instead.

### 3. Picture: understand what happens

- Make a 1 fps contact sheet of the main camera over the whole window:

  ```
  $P "$T/frames.py" src djcam A B 1 "$R/clips/<ID>_<slug>/work/dj_1fps.jpg"
  ```

  Keep each sheet to 40 tiles or fewer by splitting long windows. Read the image.
- Do the same for every other camera in project.json (`top` at 0.5 fps). You need to know what each
  camera shows.
- For every key action, make a 4 fps sheet so you know the exact frame: the hand on the knob,
  the face lighting up, someone arriving, a scream, a filter turn. Use `--crop X,Y,W,H` to zoom in on
  the mixer.
- Write a timeline in `notes.md`: one line per time with what's visible
  (e.g. `36:07  she puts his headphones on, leans over the mixer`).
  Every cut and caption must come from this timeline.

### 4. Decide the clip

- Write one line in `notes.md` saying what the clip is about: hype drop, funny moment, story, or craft
  (mix-in, double drop, chops).
- Plan the story beats, then write captions in the STYLE.md voice. Each caption gets its start frame
  from the step 3 timeline.
- Choose shots per STYLE.md "Cameras". If the DJ does something on the mixer, show it in close-up.
- Length is 20–32 s unless the DJ asked otherwise. Put a hook in the first second.

### 5. Camera sync check

Run `$P "$T/offs.py" DROP`. It prints residual offsets per camera. Put any value above ~15 ms into cfg
`offsets`. If z is low and the value looks odd, measure 2–3 nearby times and check a sharp visual event
at 8 fps.

### 6. Write `clips/<ID>_<slug>/cfg.json`

Schema (all times are timeline seconds). The `//` comments are only for explanation; real JSON has none:

```json
{
 "bpm": 156.23, "beat0": 726.442,           // beat0 = real drop onset
 "offsets": {"crowd": -0.02},                // per-camera sync correction from offs.py (s)
 "gain_db": -3,
 "chunks": [[720.297, 744.876]],             // output = these ranges played back to back (jump cuts)
 "drops": [726.442],                          // flash + punch + shake, real drops only
 "pulse": [[726.442, 744.876]],               // kick pulse ranges (after real drops)
 "shots": [                                   // must tile the chunks exactly, no gaps
   {"a": 720.297, "b": 723.37, "cam": "djcam", "zoom": [1.0, 1.1]},
   {"a": 737.194, "b": 737.962, "cam": "djcam", "zoom": [1.45, 1.7], "cx": 700, "cy": 1080, "ease": "out"}
 ],
 "captions": [
   {"text": "me about to\ndrop the track", "a": 724.568, "b": 726.442},
   {"text": "Chop", "a": 740.1, "b": 741.4, "x": 760, "y": 900, "rot": 12, "size": 110, "punch": true}
 ]
}
```

- **Cameras:** the names in project.json. The default center is the frame center (or `cx`/`cy` there).
- **Zoom:** 1.0 fills the 9:16 frame at source height. Below 1 is fit mode: the image is smaller with
  a blurred background, which lets you show more people. `cx`/`cy` set the source center in source
  pixels and are clamped to the image. `cx1` pans toward a new cx over the shot. `ease: "out"`
  decelerates.
- **Caption options:**
  - `x` sets the center (default 540, the middle; clamped to the frame) and `y` the height (default 430).
  - `rot` is the angle in degrees, counter-clockwise.
  - `size` defaults to 92.
  - `punch: true` pops the caption on start.
  - `fade_out` defaults to true.
  - `\n` is a line break.
- `"brand"` overrides the project brand line for this clip (`""` hides it).
- **Chunks:** start on a bar or half-bar from the drop, or on the first frame of the action.

### 7. Preview

```
cd "$R" && $P "$T/reel.py" clips/<ID>_<slug>/cfg.json --preview S1,S2,... clips/<ID>_<slug>/work/prev.jpg
```

The S values are **timeline seconds**. Preview every caption start, every cut, every drop, and any
moment where people move (ducking, walking in). Check:
- Faces are in frame.
- Everyone involved is visible.
- Captions are readable and don't cover faces or hands.
- Close-ups show the hands.

Fix and preview again.

### 8. Render and QC

- Render to `Review/<ID>_<slug>_<mm-ss>_v<N>.mp4`:

  ```
  cd "$R" && $P "$T/reel.py" clips/<ID>_<slug>/cfg.json "Review/<ID>_<slug>_<mm-ss>_v<N>.mp4"
  ```

  It takes 2–6 minutes, so use a 600000 ms timeout. N continues from the last version in `notes.md`.
- Run the QC:

  ```
  $P "$T/check.py" cfg.json VIDEO "$R/clips/<ID>_<slug>/work/strip_v<N>.jpg"
  ```

  Fix every warning. If the peak is too high, lower `gain_db` and render again. An overlap warning is
  fine for intentionally layered words (chops).
- Make a sheet of the output around each caption start with
  `$P "$T/frames.py" out VIDEO t-0.5 t+1 4 ...`. Each caption must appear on its action frame.

### 9. Self-review. Every answer must be yes, otherwise fix it:

1. Does every caption describe what is visible at that moment, in the STYLE.md voice, with nothing
   like the rejected list?
2. Does every caption start on its action frame (checked in the 4 fps output sheet)?
3. Is the flash on the real drop, the first beat of the full kick plus bass (checked in `env --grid`)?
4. Is there no countdown, unless this is a pure hard-drop clip with a break bar?
5. Is top used only when it shows hands or people, in short snippets?
6. Are faces in frame, and is everyone in the story visible?
7. Are mixer tricks shown in close-up, with rhythm words scattered around the hand?
8. Is the length right, with a hook at 0:00, a peak below -0.3 dBFS, and no QC warnings?

### 10. Write it down and report

- Add to `clips/<ID>_<slug>/notes.md`:
  - the version
  - the file name
  - the caption timeline
  - your decisions
  - anything left unsure
- Your **final message**, at most 20 lines, is exactly this:

```
CLIP <ID> v<N>: Review/<file>  (<dur> s, <LUFS> LUFS, peak <dB> dBFS)
story: <one line>
drops: <timeline time(s)> = <output time(s)>, bpm <x>
timeline (output time):
  0.00s "<caption>": <what's on screen>
  ...
  7.68s DROP: <what's on screen>
strip: <absolute path of strip jpg>
unsure: <list, or "nothing">
```
