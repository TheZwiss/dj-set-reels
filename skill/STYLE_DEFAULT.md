# Reel style guide

This file holds the DJ's taste. It starts as the taste of **ZWYSS** (who built this kit). Every rule
comes from their feedback on their first reels, and quotes are verbatim. As soon as this DJ gives
feedback, the orchestrator adds it here with their quote. **The DJ's own rules override the defaults
below**, and contradicted defaults get deleted. The DJ should never have to explain their taste twice.

## The one rule

**Everything on screen must match what is happening in the picture and the music at that exact moment.**
Captions that describe something you can't see, cuts and drops that land off the beat, and captions
that appear before or after the action were called "unmatching, out of touch and cringe" and
"your stuff always feels kind of detached". Before you write or place anything, look at the frames
(`frames.py`) and the audio (`audio.py env`).

## Captions: voice

- Write as the DJ posting their own story: first person, POV, lowercase, short, spontaneous and
  emotional. Write the feeling, not a description. Think of a text to a friend, not a TV narrator.
- Playful punctuation and stretched words are on-brand: `??` `!!` `:)` `:(` `HELLLLP`.
- Name what is visible. If a woman fixes it on camera, write "she", not "they" or "my team".
- Use few captions, one per story beat. No caption is fine while the music carries the moment,
  for example after the payoff drop. Don't shout on the drop ("NOW!!"), and don't caption the crowd's
  feelings.
- Use the language the DJ writes in (default English). If the DJ dictates text, use it **verbatim**,
  keeping their spelling and casing ("wheres", "thats", "Bass").

**Approved captions (the DJ wrote most of these; this is the target voice):**

| clip type | captions in order |
|---|---|
| hard drop (pure hype) | `THE HARDEST DROP OF THE NIGHT` (caps hook), then 4-3-2-1 countdown on the break bar |
| forgot the bass (funny) | `me about to drop the track` → `whoops wheres my Bass??` (drop without bass) → `there it is :)` (bass back in) |
| headphones died (story) | `my headphones just died` → `HELLLLP :(` (on the drop) → `team trying to fix it` → `she fixed it!!` → `Holy shit thats loud` |
| fake drop (funny) | `setting up the drop` → `sike` (on the fake drop), nothing else |
| mix-in / mashup (craft) | `Mashup action incoming` → `spotting one of my favourites` → `cueing it up` → `Mix it in` → `Oh yeah that works` → `Chop` × every fader chop |

**Rejected. Never write like this:**

| rejected | why |
|---|---|
| `the drop is coming...` | narrator teaser, "cringe" |
| `...wait` / `...and it worked` | meme-template narration |
| `forgot to turn the bass back in` / `so I dropped it 1 bar later` | explains instead of reacting; the DJ's version was `whoops wheres my Bass??` |
| `so I dropped it blind` / `2nd drop. still blind.` | made-up drama, not what's visible |
| `1 min later` | time-jump labels; just jump-cut |
| `my team trying to fix it` / `they fixed it` / `THEY WORK AGAIN` | became `team trying to fix it` / `she fixed it!!` (specific, emotional) |
| `first drop of my set` / `double mix in!!` / `sneaking the next track in :)` | "caption bad": labels and jargon. Rewritten as play-by-play of the moves |
| `me about to drop it` / `they want it so bad` / `not yet :)` / `NOW!!` | "cringe". Don't reuse an approved hook, don't caption the crowd's feelings, don't shout on the drop |
| removing all text from a story clip | "worthless without storytelling" |

## Captions: timing

- A caption starts on the frame where the thing it describes becomes visible, within ±2 frames.
  Examples:
  - `she fixed it!!` starts when the DJ's face lights up with the headphones on, not when they pick
    them up.
  - `Holy shit thats loud` starts when the scream starts.
  - `whoops wheres my Bass??` covers the bar of the drop without bass while the hand goes to the knob.

  Find the frame with `frames.py ... 4` (4 fps) before you place the caption.
- Hold a caption while it's true. End it when the next story beat starts.
- Times the DJ gives come from a player that shows whole seconds, so "0:22" means somewhere between
  0:21.5 and 0:22.9. Put the caption on the actual action frame, and mention it if it differs from
  their number.
- The DJ's times usually refer to the **last version they watched** (output time), not the set.

## Countdowns

Use a countdown **only** for a pure hard-drop hype clip that has a silent or break bar right before the
drop. Never use one on story or funny clips ("Why the fucking countdown?"). If you're unsure, leave it
out.

## Music timing: drops, cuts, effects

- **The drop** is the first beat where the full, regular kick and bass pattern starts. These are NOT
  drops:
  - a bass swell (in one case 1 s before the drop)
  - a single stab (0.5 s before)
  - a track that drops without bass (low EQ down); the bass coming back is the drop

  The DJ notices every time a drop effect is 1–2 beats off ("dropping one beat too early").
- Flash, punch and shake go only on real drops (cfg `drops`). The kick pulse runs only after a real
  drop (`pulse`). A fake drop gets no effect; let it fall flat, since that's the joke.
- The BPM changes during a set. Measure it per clip, set beat0 to the drop onset, and verify with
  `audio.py env --grid`: after the drop, the big `B###` bursts must sit on the `|` rows.
- Cuts land on beats. Bigger shot changes go on bar lines counted from the real drop (1 bar = 4 beats).
- The DJ's timestamps are approximate (±2 s), and moment lists have typos (e.g. "26:23" between
  35:58 and 37:27 means 36:23). Trust the surrounding times.

## Show the DJ craft

**Craft and mix-in clips: caption the moves step by step.** Use short present-tense calls that follow
the DJ's hands as they happen: the hook (`Mashup action incoming`), picking the track
(`spotting one of my favourites`), headphone cue (`cueing it up`), the fader/EQ moment (`Mix it in`),
the reaction when it lands (`Oh yeah that works`). Don't use labels or jargon summaries.

**Rhythm tricks get one word per hit** (chops, stutters): one `Chop` per actual chop, as many as there
are ("it can be 8 chop words or 7 just as many as i chop"), each appearing exactly on its hit.
**Place them around the action, never in a list.** Each word pops up at a different spot around the
hand doing the trick, with varied size and angle (`x`, `rot`, `size`, `punch`), and never covers the
hand: "The "Chop" are lazily listed at the top, they should be dynamically positioned around by hand
doing the actual chopping in a interesting way."

**Release the trick into a cut.** On the final hit of a trick (the last chop, the fader flicked up
right on the beat), cut to the crowd, then keep cutting between the DJ, the crowd and the birdseye
cam on beats so the energy stays visual: "on my last chop right on beat when i flick the fader up the
last time ... it should cut to the crowd not stay on my face and then cut between me, the crowd and
the birdseye cam to keep it interesting".

Whenever the DJ does something on the mixer (filter, EQ or low knob, fader chops, loops, mixing in a
track), show it in close-up for as long as it lasts: "could be shown a bit to keep the attention and
look nice". Find it in `audio.py env`: a filter makes the bass disappear or the full band thin out,
and chops show up as rhythmic gaps. Then confirm the hand with `frames.py` (crop on the mixer).

**Close-up framings that worked.** These are from ZWYSS's cameras (1920x1080 front cam). Find your own
with `frames.py --crop` and add them here.

| what | cam | settings |
|---|---|---|
| hands on the mixer, from the front | djcam | `cx` toward the hands, `cy` = bottom (clamps), zoom 1.45→1.75, `ease: out`. Check the fingers are in frame, not just the forearm |
| one knob (EQ/low) | djcam | zoom 1.5→2.4, `ease: out` |
| faders and hand from above | top | zoom 2.1→2.3, soft but readable; keep it ~1 s |

## Cameras

Camera names in project.json: `djcam` (front, main), `crowd` (behind the crowd facing the DJ), `top`
(birdseye over the decks). A project may have fewer cameras or extra ones.

- **djcam** is the main camera. Faces must stay in frame. Check frames where the DJ ducks or leans,
  and fix them with zoom below 1 (fit mode) plus a `cx` shift.
- **crowd** goes on drops, about 1 bar at a time.
- **top** (birdseye): use it only when it shows something (hands on the mixer, people at the decks),
  never on an empty mixer. Chop it in as **short snippets** (½ beat to 2 beats) between djcam and
  crowd for variety, especially in breaks and after drops: "use the birds eye view aswell and chop it
  in a bit in short snippets to make it more interesting".
- **Story clips:** frame so that everyone involved is visible, because the picture has to prove the
  caption. Use djcam fit mode at zoom 0.62–0.8 with `cx` toward them.
- Jump cuts between moments of a story are fine. Bars from the same section can also be dropped with
  a jump cut on a bar line.

## Format

- 9:16, 1080x1920, 25 fps, 20–32 s (longer if the DJ asks). Put a hook in the first second: a caption
  from frame 0.
- The brand line (project.json `brand`) sits at the top. Captions go in the upper third (default y 430)
  at size 92. Use size 130 for a single shout like `HELLLLP :(`. Move a caption down (y ~1150, on the
  shirt) when it would cover the face, and keep it off the hands in close-ups.
- Characters the display font lacks (often `?`) are drawn automatically from a fallback font.
  Never use `@`, `#` or emoji.
- Audio is the set recording. Aim for -9.5 to -11 LUFS with true peak below -0.3 dBFS
  (`gain_db` -2.5 to -4).
- No other effects: no transitions, stickers, zoom-blur, or shake outside real drops.

## Reference clips

Approved clips in this project (`clips/<ID>_<slug>/cfg.json` and `notes.md`) are working examples.
Copy their patterns. The orchestrator lists them here as they get approved:

- (none yet)
