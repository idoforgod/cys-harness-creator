#!/usr/bin/env bash
# CYS Harness Creator — install the /harness-creator skill globally.
# Re-run after editing skills/harness-creator/SKILL.md or references/.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.claude/skills/harness-creator"
rm -rf "$DST"; mkdir -p "$DST/references"
cp "$HERE/skills/harness-creator/SKILL.md" "$DST/SKILL.md"
cp "$HERE/skills/harness-creator/references/"*.md "$DST/references/"
echo "installed /harness-creator -> $DST (SKILL.md + $(ls "$DST/references" | wc -l | tr -d ' ') references; tools stay at $HERE)"
