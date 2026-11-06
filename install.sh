#!/usr/bin/env bash
# Installs the dj-reels skill + reel-editor agent for Claude Code (user level), and the Python tools venv.
# Re-run after `git pull` to update. Your projects (project.json, STYLE.md, clips) are never touched.
set -euo pipefail
cd "$(dirname "$0")"
SK="$HOME/.claude/skills/dj-reels"
AG="$HOME/.claude/agents"

command -v ffmpeg >/dev/null || { echo "ffmpeg is missing. macOS: brew install ffmpeg"; exit 1; }
FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
for f in exposure ebur128 alimiter; do
  grep -q " $f " <<<"$FILTERS" || { echo "your ffmpeg lacks the '$f' filter; install a full build (brew install ffmpeg)"; exit 1; }
done
command -v python3 >/dev/null || { echo "python3 is missing"; exit 1; }

mkdir -p "$SK" "$AG"
rsync -a --delete --exclude ".venv" --exclude "__pycache__" skill/ "$SK/"
cp agents/reel-editor.md "$AG/reel-editor.md"

if [ ! -x "$SK/tools/.venv/bin/python" ]; then
  if command -v uv >/dev/null; then uv venv -q "$SK/tools/.venv"; else python3 -m venv "$SK/tools/.venv"; fi
fi
if command -v uv >/dev/null; then
  uv pip install -q --python "$SK/tools/.venv/bin/python" -r "$SK/tools/requirements.txt"
else
  "$SK/tools/.venv/bin/python" -m pip install -q -r "$SK/tools/requirements.txt"
fi
"$SK/tools/.venv/bin/python" -c "import numpy, scipy, PIL, fontTools" && echo "installed: $SK and $AG/reel-editor.md"
echo "Restart Claude Code, then say e.g. \"set up reels for my set\"."
