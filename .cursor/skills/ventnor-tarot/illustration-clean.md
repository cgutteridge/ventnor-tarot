# Ventnor Tarot Illustration Clean (legacy migration)

## Purpose

Take approved crops from `illustrations-raw/` and produce `illustrations-cleaned/`
by removing overlaid Roman numerals and healing curved corner bites via **focused
AI on small patches only**.

## When to use

**Only** on the legacy migration path after frame-crop. For new cards, generate
clean **700 × 1200** (7:12) art directly into `illustrations-rectified/` per `cards.md`.

## Pipeline context

```text
Legacy: vtarot → raw → cleaned (this skill) → rebuild rectified 7:12 / 700×1200 → photos/js (no reframe)
New:    landscape + RW → rectified 7:12 / 700×1200 (approve) → photos/js → [optional] frame if no gallery card yet
```

## Makefile vs agent

| Step | Who | Command |
|------|-----|---------|
| Extract patches | Make | `make clean-extract` |
| Focused AI heal | Agent (this skill) or API | `tmp/illustration-clean-work/` |
| Composite | Make | `make clean-composite` |
| Status | Make | `make clean-status` |

```bash
make clean-extract
# heal pending patches with this skill
make clean-composite
make clean-status
```

## Patch layout

```text
tmp/illustration-clean-work/<card-stem>/
  source.png
  meta.json
  patches/ … numeral + corner patches and masks
  healed/  … agent writes same filenames here
  pending.json
```

## Agent heal rules

For each `pending.json` entry: open **only** that patch; same pixel size; remove
numeral/glow or heal corner frame residue; save under `healed/`. Never full-card AI.

## Quality check

- [ ] no numeral/glow; square photo corners
- [ ] no new objects/text in patches
- [ ] output `illustrations-cleaned/<name>.png`

## Do not

- start new cards here
- full-card AI passes
- modify `vtarot/` or overwrite `illustrations-raw/`
- treat cleaned files as print masters — rebuild **rectified 7:12 / 700 × 1200** next
