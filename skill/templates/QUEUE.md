# Reel queue

This is the orchestrator's source of truth. Re-read it after a /compact or in a new session.

**Status values:**
- `todo`: not started
- `in-progress`: an editor is working on it
- `review`: rendered and waiting for the user
- `changes`: the user gave feedback that hasn't been applied yet (see `clips/<ID>_<slug>/notes.md`)
- `approved`: in `Approved/`
- `skip`

**IDs** are the moment numbers from the DJ's moment list. The user's notes are copied verbatim (any
language, typos included). Times are timeline mm:ss (= position in the set recording, see project.json).

| ID | user's note | status | file / latest version |
|---|---|---|---|
