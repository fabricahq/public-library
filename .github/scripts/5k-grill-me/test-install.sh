#!/usr/bin/env bash
set -euo pipefail

consumer=$(mktemp -d)
trap 'rm -rf "$consumer"' EXIT
cd "$consumer"
git init --quiet
trailguide project init --non-interactive
trailguide project add source fabrica --non-interactive \
  --repository "${SOURCE_REPOSITORY:?}" --ref "${SOURCE_REVISION:?}" \
  --skills skills/5k-grill-me
trailguide project sync

cd .agents/skills/5k-grill-me
python3 scripts/grill_ui.py render --snapshot examples/question-help.json \
  --output "$consumer/canvas.html"
grep -qF 'Understanding a design decision' "$consumer/canvas.html"
