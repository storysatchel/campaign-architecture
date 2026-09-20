#!/bin/sh
# Sync the four live skills into this monorepo's skills/ dir.
# Live sources: ~/workspace/skills/<name>  ->  ./skills/<name>
# Excludes .git, __pycache__, *.pyc. Run from the repo root.
set -e
cd "$(dirname "$0")/.."
for s in schelling-campaign-map campaign-matrix five-room-dungeon nouns-directory; do
  src="$HOME/workspace/skills/$s/"
  dst="skills/$s/"
  if [ ! -d "$src" ]; then echo "missing live skill: $src"; exit 1; fi
  mkdir -p "$dst"
  rsync -a --delete --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    "$src" "$dst"
  echo "synced $s"
done
