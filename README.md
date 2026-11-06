# dj-set-reels

Turn a filmed DJ set into beat-synced vertical reels (9:16) with Claude Code. Claude finds the drops,
cuts between your cameras on the beat, and writes POV captions that land on the exact frame. It also
remembers every piece of feedback you give, so you only have to explain your taste once.

Built by ZWYSS for their set at NONSENSE. The default style is theirs and adapts to yours.

## What you need

- [Claude Code](https://claude.com/claude-code)
- `ffmpeg` (macOS: `brew install ffmpeg`)
- `python3` (and optionally [`uv`](https://docs.astral.sh/uv/))
- Your footage:
  - **The set recording.** The mixer/USB recording is best; a camera's audio works too.
  - **1–3 cameras**, each recording the whole set:
    - a front cam facing the DJ (`djcam`)
    - a crowd cam behind the crowd facing the DJ (`crowd`)
    - a birdseye cam over the decks (`top`)

  The cameras need their own audio for automatic sync.

## Install

```bash
git clone https://github.com/TheZwiss/dj-set-reels.git
cd dj-set-reels
./install.sh
```

This installs the `dj-reels` skill into `~/.claude/skills/` and the `reel-editor` agent into
`~/.claude/agents/`, and sets up a Python environment for the tools. Restart Claude Code afterwards.
To update later, run `git pull && ./install.sh`.

## Use

Open Claude Code in a folder of your choice and talk to it:

1. **"Set up reels for my set."** Claude asks where your footage is, which file is which camera, your
   brand line (e.g. `NAME · live at VENUE`) and, optionally, a font. It then syncs all cameras to the
   set recording automatically.
2. **Give it your moment list**, one line per moment, with times from the set recording:

   ```
   1. 5:39 buildup, 6:03 first drop, 6:16 double mix in
   2. 8:31 buildup, 8:44 fake drop break, 8:50 drop
   3. 35:58 headphones died, team comes to troubleshoot, 37:27 headphones work again
   ```

3. **"Make clips."** Claude makes 3 clips, one after another. Each clip is made by a separate editor
   agent, which keeps the main conversation small. The renders go to `Review/`.
4. **Give feedback in your own words**, e.g. "the caption at 0:06 is cringe, write 'sike' there" or
   "show my hands on the mixer more". Claude saves it word for word, turns general points into style
   rules, and renders a new version.
5. **Approve** by saying "approved" or by moving the file into `Approved/`.

Everything lives in files, so you can close Claude Code, /compact or come back days later. Say
"make clips" and it continues where it left off.

## Project folder

```
Reels/
  project.json   cameras, sync, set recording, brand, fonts
  QUEUE.md       every moment and its status (todo / review / changes / approved)
  STYLE.md       your taste: starts as ZWYSS's, then grows with your feedback
  clips/<ID>_<slug>/  cfg.json (the edit), notes.md (timeline + all your feedback)
  Review/        new renders
  Approved/      finished reels
```

## How it works

| file | role |
|---|---|
| `skill/SKILL.md` | the orchestrator: setup, the clip loop, how feedback is stored |
| `agents/reel-editor.md` + `skill/EDITOR.md` | the editor agent and its step-by-step procedure |
| `skill/STYLE_DEFAULT.md` | the default taste: caption voice, timing, drops, cameras, what's cringe |
| `skill/tools/setup_project.py` | creates a project; syncs cameras to the set audio (coarse match + drift fit) |
| `skill/tools/audio.py` | beat-accurate envelope view, drop onsets, BPM |
| `skill/tools/frames.py` | labelled contact sheets, so the editor *sees* what happens at which second |
| `skill/tools/offs.py` | per-clip sync check |
| `skill/tools/reel.py` | the renderer: multicam cuts, zooms, drop flash/punch, kick pulse, captions |
| `skill/tools/check.py` | QC: length, loudness, true peak, caption timeline, a frame strip for review |

Rendering uses ffmpeg plus Pillow, at 1080x1920, 25 fps, H.264 and AAC 320k. A 30 s reel takes 2–5
minutes.

## Tips

- If a camera looks too dark (log profiles, dark clubs), ask Claude to brighten that camera. It sets
  an exposure filter in `project.json`.
- If a camera has no audio, Claude syncs it visually from a light flash or a hand hitting a button.
- If your timestamps come from an edited video rather than the raw recording, tell Claude the
  difference once (`audio.offset`).
