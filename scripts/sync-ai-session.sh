#!/usr/bin/env bash
# Sync Cursor global agent-transcripts into the repo's ai-session/ directory
# so AI collaboration history is preserved as a mandatory deliverable.
set -euo pipefail

CURSOR_PROJ="$HOME/.cursor/projects/Users-rayseus-Documents-practice-miao-test"
REPO_ROOT="$(git rev-parse --show-toplevel)"
DST_ROOT="$REPO_ROOT/ai-session"

if [ ! -d "$CURSOR_PROJ" ]; then
  echo "ERROR: cursor project dir not found: $CURSOR_PROJ" >&2
  exit 1
fi

mkdir -p "$DST_ROOT"

for sub in agent-transcripts terminals canvases mcps; do
  SRC="$CURSOR_PROJ/$sub"
  if [ -d "$SRC" ]; then
    mkdir -p "$DST_ROOT/$sub"
    rsync -a --delete "$SRC/" "$DST_ROOT/$sub/"
    echo "synced: $sub"
  fi
done

echo "AI session synced -> $DST_ROOT"
