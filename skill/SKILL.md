---
name: dj-reels
description: Turn a filmed DJ set (multi-camera footage + the set recording) into beat-synced vertical 9:16 reels with POV captions, one clip per subagent, with a feedback loop that learns the DJ's taste. Use when the user wants reels/clips/shorts from DJ set footage, says "make clips", gives feedback on a reel, approves one, or wants to set up a new set.
---

# DJ set reels: orchestrator

You are the **orchestrator**. Keep your own context clean. **You don't analyse audio, look at contact
sheets or render yourself.** `reel-editor` subagents do that, one clip per agent and **one agent at a
time**: renders take most of the CPU, and each review should inform the next clip.

```
K = ~/.claude/skills/dj-reels           (this skill: EDITOR.md, STYLE_DEFAULT.md, tools/)
T = $K/tools    P = $T/.venv/bin/python
```

## Find the project

A project is a folder with `project.json`. It holds:

| file | what it is |
|---|---|
| `project.json` | cameras (file, size, sync), set recording, brand line, fonts |
| `QUEUE.md` | status of every moment. **Source of truth for progress. Re-read it after /compact or in a new session.** |
| `STYLE.md` | the DJ's taste: caption voice, timing, cameras, what's cringe. The DJ never wants to explain it twice. |
| `clips/<ID>_<slug>/` | `cfg.json`, `notes.md` (picture timeline, decisions, **all feedback verbatim**), `work/` |
| `Review/` | renders waiting for the DJ |
| `Approved/` | renders the DJ approved |

To find the project:
1. Look for a `CLAUDE.md` line `Reels project: <path>` in the working directory.
2. Otherwise look for `project.json` in the working directory or its subfolders.
3. If there is none, run **Setup**.

## Setup (new set)

1. Ask the DJ for:
   - The footage folder.
   - Which file is the **set recording**. The mixer/USB recording is best; a camera's audio works too.
   - Which camera is which. The names to use are:
     - `djcam`: front, facing the DJ, the main camera.
     - `crowd`: behind or among the crowd, facing the DJ.
     - `top`: birdseye over the decks.

     Fewer cameras are fine.
   - The brand line, e.g. `NAME · live at VENUE`.
   - Optional fonts (.ttf/.otf) for the captions.
   - Where the reels project should live. The default is a `Reels/` folder next to the footage.
2. Run the setup (installs nothing, takes 1–3 min per hour of footage):

   ```
   $P "$T/setup_project.py" init "<project>" --media "<footage folder>" --audio <set file> \
      --cam djcam=<file> [--cam crowd=<file>] [--cam top=<file>] --brand "<brand>" \
      [--font-display <ttf>] [--font-text <ttf>]
   ```

   It writes `project.json`, `STYLE.md` (a copy of the default taste), `QUEUE.md` and the folders, then
   syncs every camera that has audio to the set recording. In the sync output, the residuals should
   mostly be within ±15 ms. A few big outliers are normal and get rejected automatically.
   - **A camera without audio** can't be synced automatically. Spawn a general-purpose agent to find
     its offset visually: it compares a sharp event (a light flash, a hand hitting a button) in
     `frames.py src` of that camera against djcam at 8 fps, then sets
     `cameras.<name>.sync.offset` in project.json.
   - **A dark camera** (e.g. a log profile): spawn an agent to compare a 1 fps sheet of that camera.
     Then set its `vf` in project.json, e.g.
     `format=gbrpf32le,exposure=exposure=1.5:black=0.01,format=yuv420p10le,eq=contrast=1.1:saturation=1.3:gamma=0.92`.
3. **Timeline:** all times are seconds in the set recording (+ `audio.offset`). If the DJ's timestamps
   come from a different video (e.g. an edited full-set video that starts earlier), measure the
   difference once and pass `--audio-offset` (timeline = recording time − offset).
4. Ask for the **moment list**: numbered moments with timestamps and notes, e.g.
   `4. 11:17 buildup mix in, 12:06 HARD DROP`. Copy every moment **verbatim** as a row into
   `QUEUE.md` with status `todo`.
5. Write `Reels project: <absolute project path> (use the dj-reels skill)` into `CLAUDE.md` in the
   working directory, so the project is found again after /compact and in new sessions.
6. Tell the DJ that `STYLE.md` starts with ZWYSS's taste and adapts to theirs with every piece of
   feedback.

## Loop: "make clips" (batch of 3 unless the DJ says otherwise)

1. Read `QUEUE.md`. Take the next `todo` rows in ID order (or the ones the DJ named) and set the first
   one to `in-progress`.
2. Spawn the editor with Agent `subagent_type: "reel-editor"`. The prompt is:
   `Project: <project path>. Make clip <ID>.`, plus anything the DJ said about this clip, verbatim.
   If `reel-editor` isn't listed (agent files load at session start), use `general-purpose` with:
   `You are the reel editor. Read and follow ~/.claude/agents/reel-editor.md. Project: <path>. Make clip <ID>.`
   Wait for it to finish before you spawn the next one.
3. Review the result cheaply. Read the agent's report and **Read the one strip image** it names.
   Check:
   - The captions use the STYLE.md voice and don't resemble anything on the rejected list.
   - There is no countdown, unless it's a pure hard-drop clip.
   - The report says the drops were verified against `env --grid`.
   - In the strip, faces and the people involved are visible, captions are readable, close-ups show
     hands, and top-cam shots show something.
   - The length is right and there are no QC warnings.

   If something fails, `SendMessage` the same agent with the specific fix.
4. Update the `QUEUE.md` row (`review`, file name). Continue with the next clip.
5. Report to the DJ after each clip, or at the end of the batch. For each clip give:
   - the file and its length
   - the captions with their output times on one line
   - anything the editor was unsure about

   After the batch, **stop and wait for feedback**. If the DJ says to perfect the current clips first,
   don't start new ones.

## DJ feedback

- Write it **verbatim** with the date into `clips/<ID>_<slug>/notes.md` under "Feedback history", and
  set the status to `changes`.
- If it says anything general about taste (voice, timing, cameras, effects, pacing), also add it to the
  project `STYLE.md` as a rule with the quote. Remove any default rule it contradicts. Rejected
  captions go into the rejected table, and captions the DJ writes go into the approved table.
- If an editor is still running, forward new feedback for **its** clip with SendMessage. Feedback for
  another clip waits until the current editor finishes. Never run two editors at once.
- To apply feedback, spawn a fresh editor:
  `Project: <path>. Apply feedback to clip <ID>: "<verbatim feedback>"`. Include your reading of
  ambiguous parts. For example, times usually refer to the last version's output time, and a time
  past the clip's end is probably a typo. The editor renders `v<N+1>` into `Review/`. Report back and
  wait.
- Captions or times the DJ dictates are used verbatim and override STYLE.md.
- **Approval:** the DJ says "approved"/"good"/"passt", or moves the file into `Approved/` themselves.
  Then:
  - Move the file to `Approved/` if it isn't there yet.
  - Set the status to `approved`.
  - Delete that clip's older versions from `Review/`.
  - Add the clip to "Reference clips" in STYLE.md.
  - If the DJ keeps the moment list as a file, offer to tick the moment off (✅) there.

## Never

- Edit the footage, `Approved/` (without approval) or anything outside the project.
- Run several editors in parallel, or render more than the batch the DJ asked for.
- Explain the style back to the DJ or ask them to repeat their taste. It's in `STYLE.md`.
