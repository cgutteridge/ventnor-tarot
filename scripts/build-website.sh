#!/usr/bin/env bash
# build-website.sh — assembles website/ from source layers.
#
# Idempotent: rsync only copies files when the source is newer than the
# destination.  Safe to re-run at any time.
#
# What it does:
#   1. Sync illustrations-framed/  → website/cards/
#   2. Sync sources/               → website/sources/
#   3. Sync rider-waite/           → website/rider-waite/
#   4. Generate website/card-data.js from card-details.json
#      (wraps the canonical JSON in a window.CARD_DETAILS = …; assignment)
#
# website/index.html is hand-authored and is NEVER overwritten.
# Edit card-details.json (project root) — never website/card-data.js directly.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve project root regardless of where the script is called from.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SRC_CARDS="$ROOT/illustrations-framed"
SRC_SOURCES="$ROOT/sources"
SRC_RW="$ROOT/rider-waite"
SRC_CARD_DATA="$ROOT/card-details.json"

DEST="$ROOT/website"
DEST_CARDS="$DEST/cards"
DEST_SOURCES="$DEST/sources"
DEST_RW="$DEST/rider-waite"
DEST_CARD_DATA="$DEST/card-data.js"

# ---------------------------------------------------------------------------
# Guard: website/index.html must already exist (hand-authored; not ours to
# create) and we must never overwrite it.
# ---------------------------------------------------------------------------
if [[ ! -f "$DEST/index.html" ]]; then
  echo "ERROR: $DEST/index.html not found." >&2
  echo "Place the hand-authored index.html there before running this script." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Step 1 — framed cards
# ---------------------------------------------------------------------------
echo "==> Syncing framed cards to website/cards/ …"
mkdir -p "$DEST_CARDS"
rsync -a --delete "$SRC_CARDS/" "$DEST_CARDS/"
CARD_COUNT=$(find "$DEST_CARDS" -maxdepth 1 -name "*.png" | wc -l | tr -d ' ')
echo "    $CARD_COUNT PNG(s) in website/cards/"

# ---------------------------------------------------------------------------
# Step 2 — sources
# ---------------------------------------------------------------------------
echo "==> Syncing sources to website/sources/ …"
mkdir -p "$DEST_SOURCES"
rsync -a --delete "$SRC_SOURCES/" "$DEST_SOURCES/"
SOURCE_COUNT=$(find "$DEST_SOURCES" -maxdepth 1 -type f | wc -l | tr -d ' ')
echo "    $SOURCE_COUNT file(s) in website/sources/"

# ---------------------------------------------------------------------------
# Step 3 — Rider–Waite references
# ---------------------------------------------------------------------------
echo "==> Syncing Rider–Waite references to website/rider-waite/ …"
mkdir -p "$DEST_RW"
rsync -a --delete "$SRC_RW/" "$DEST_RW/"
RW_COUNT=$(find "$DEST_RW" -maxdepth 1 -type f | wc -l | tr -d ' ')
echo "    $RW_COUNT file(s) in website/rider-waite/"

# ---------------------------------------------------------------------------
# Step 4 — card-data.js (wrap canonical JSON in window.CARD_DETAILS assignment)
# ---------------------------------------------------------------------------
echo "==> Rebuilding website/card-data.js from card-details.json …"

if [[ ! -f "$SRC_CARD_DATA" ]]; then
  echo "ERROR: card-details.json not found at $SRC_CARD_DATA" >&2
  exit 1
fi

# Validate the JSON is parseable before writing the output file.
python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$SRC_CARD_DATA" || {
  echo "ERROR: $SRC_CARD_DATA is not valid JSON." >&2
  exit 1
}

{ printf 'window.CARD_DETAILS = '; cat "$SRC_CARD_DATA"; printf ';\n'; } > "$DEST_CARD_DATA"

echo "    Written: $DEST_CARD_DATA"

echo ""
echo "Build complete."
echo "  website/cards/       $CARD_COUNT PNG(s)"
echo "  website/sources/     $SOURCE_COUNT file(s)"
echo "  website/rider-waite/ $RW_COUNT file(s)"
echo "  website/card-data.js rebuilt from card-details.json"
echo ""
echo "website/index.html was NOT modified."
