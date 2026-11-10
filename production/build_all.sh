#!/usr/bin/env bash
# Full rebuild of Episode 1 Shorts (RU / KZ / EN): voice → SFX/mix → video.
# Usage: bash production/build_all.sh [ru kz en]
set -euo pipefail
cd "$(dirname "$0")"
PY=${PY:-/tmp/video_venv/bin/python}
if [ ! -x "$PY" ]; then
  uv venv /tmp/video_venv -q && uv pip install --python /tmp/video_venv/bin/python -q -r requirements.txt
fi
for lang in "${@:-ru kz en}"; do
  for l in $lang; do
    "$PY" voice.py "$l" 2>&1 | grep -v "Missing phoneme" || true
    "$PY" sfx.py "$l"
    "$PY" render.py "$l"
  done
done
