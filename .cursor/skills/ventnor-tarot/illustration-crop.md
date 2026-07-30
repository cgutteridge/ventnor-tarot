# Ventnor Tarot Illustration Crop (legacy migration)

## Purpose

Extract the photographic illustration from **existing** framed cards in `vtarot/`,
excluding cream outer frame, gold border, bottom title panel, and cream numeral
panels. Write crops to `illustrations-raw/`.

## When to use

**Only** for migrating cards that already exist as framed `vtarot/` images and do
not yet have an `illustrations-rectified/` master.

For **new or replacement** cards, follow `cards.md` / `AGENTS.md`: create approved
**700 × 1200** (7:12) art in `illustrations-rectified/` first. Legacy migrations
from `vtarot/` do not require reframing the gallery card afterward.

## Pipeline context

```text
New cards:     landscape + RW → rectified 7:12 / 700×1200 (approve) → photos + card-data.js → [optional] frame vtarot/ if no gallery card yet
Legacy only:   vtarot framed → raw → cleaned → rebuild rectified → photos/js (no reframe)
```

## Rules

- Never modify files in `vtarot/` with this skill.
- Write working files under `tmp/`; crops to `illustrations-raw/`.
- Keep overlaid numerals; crop cream numeral **panels**.
- Do not silently crop without a bounds manifest unless the user skips review.

## Frame anatomy

Match `vtarot/wands02.png`: cream outer, gold inner, title panel below; numeral
should be over the photo (faulty cards may have a cream numeral header — exclude it).

## Two-step workflow

### Step 1 — Identify crop regions

```bash
python3 .cursor/skills/ventnor-tarot/illustration-crop/scripts/detect_illustration_bounds.py
```

Writes `tmp/illustration-bounds.json` and optional previews. Review flagged cards;
edit bounds if needed.

### Step 2 — Apply crops

```bash
python3 .cursor/skills/ventnor-tarot/illustration-crop/scripts/crop_illustrations.py
```

Writes `illustrations-raw/<name>.png`.

## Quality check

- [ ] no cream outer frame / gold border / title panel
- [ ] no cream numeral header
- [ ] overlaid numeral may remain
- [ ] filename matches source primary card name

## Do not

- use this as the start of a **new** card
- full-image AI regenerate
- upload or change the gallery
- skip onward to framing without a proper 7:12 / 700 × 1200 rectified rebuild and approval
