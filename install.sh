#!/usr/bin/env bash
# CYS Harness Creator — install the /harness-creator skill globally.
# Re-run after editing skills/harness-creator/SKILL.md or references/.
# Installs into the ACTIVE Claude config dir ($CLAUDE_CONFIG_DIR, default ~/.claude) so it works under a
# custom profile; pass extra config dirs as args to install into several profiles at once, e.g.
#   ./install.sh ~/.claude ~/.claude-cysinsight ~/.claude-cysfuturist
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGETS=("$@"); [ ${#TARGETS[@]} -eq 0 ] && TARGETS=("${CLAUDE_CONFIG_DIR:-$HOME/.claude}")
for CFG in "${TARGETS[@]}"; do
  DST="$CFG/skills/harness-creator"
  rm -rf "$DST"; mkdir -p "$DST/references"
  cp "$HERE/skills/harness-creator/SKILL.md" "$DST/SKILL.md"
  cp "$HERE/skills/harness-creator/references/"*.md "$DST/references/"
  echo "installed /harness-creator -> $DST (SKILL.md + $(ls "$DST/references" | wc -l | tr -d ' ') references; tools stay at $HERE)"
done
