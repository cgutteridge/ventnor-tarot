# New Thread Plan — Website Build + Skills Refactor

## Context: current project structure

```
illustrations-framed/       ← 78 framed cards (1024 × 1693 px) — the published deck
illustrations-rectified/    ← canonical 700 × 1200 frameless masters
illustrations-numeralled/   ← generated intermediate (rectified + Roman numerals)
sources/                    ← canonical source archive
  <id>-background.<ext>     ← approved landscape/place photo per card
  <id>-background-original.<ext>  ← raw original where it exists
  cups-reference.jpg / cups-detail-1–4.jpg / pentacles-reference.png
rider-waite/                ← full 78-card RWS reference set
website/                    ← new site (deployable output)
  index.html                ← gallery page (already written)
  card-data.js              ← STUB only — full data lives in _old/vtarot/card-data.js
  cards/                    ← 78 framed card PNGs (already populated from illustrations-framed/)
_old/vtarot/card-data.js    ← archived full card notes and source-image references
                               paths use ../sources/ and ../rider-waite/ (need adjusting)
.cursor/skills/             ← project AI skills (see Task 2)
```

---

## Task 1 — Build script

Write `scripts/build-website.sh` (or a Makefile target `make website`) that assembles
`website/` from source layers. Must be **idempotent** — safe to re-run; only copies
when source is newer than dest.

### Steps the script must perform

1. **`website/cards/`** — sync from `illustrations-framed/`
   ```
   rsync -a --delete illustrations-framed/ website/cards/
   ```

2. **`website/sources/`** — sync from `sources/`
   ```
   rsync -a --delete sources/ website/sources/
   ```

3. **`website/rider-waite/`** — sync from `rider-waite/`
   ```
   rsync -a --delete rider-waite/ website/rider-waite/
   ```

4. **`website/card-data.js`** — rebuild from `_old/vtarot/card-data.js`:
   - Replace all `"../sources/` → `"sources/`
   - Replace all `"../rider-waite/` → `"rider-waite/`
   - Write result to `website/card-data.js`
   - The stub currently in `website/card-data.js` gets replaced by this step.

5. **Verify** — after build, print a count of files in each output directory and
   check that `website/card-data.js` contains no remaining `../` source paths.

### Notes
- `website/index.html` is hand-authored; the script must NOT overwrite it.
- `_old/` is archival; the script reads from it but never writes to it.
- Do not copy the map — it is out of scope.

---

## Task 2 — Skills reorganisation

### Current state
`.cursor/skills/` has five flat skill folders:
```
ventnor-tarot-cards/         SKILL.md   ← main card skill (too large; mixes concepts + generation mechanics)
ventnor-tarot-frame-repair/  SKILL.md
ventnor-tarot-illustration-clean/  SKILL.md
ventnor-tarot-illustration-crop/   SKILL.md
ventnor-tarot-map/           SKILL.md   ← out of scope; leave untouched
```

### Target state
Consolidate into a single folder `.cursor/skills/ventnor-tarot/` with named sub-skills:

```
.cursor/skills/ventnor-tarot/
  SKILL.md               ← thin dispatcher: describes each sub-skill and when to load it
  cards.md               ← card concepts, composition rules, suit object rules,
                            quality checklists, artifact inspection, workflow steps
                            (no image-generation mechanics)
  generation.md          ← sub-skill: how to generate / rectify / frame images
                            using the AI image tool (black bars, aspect ratios,
                            strip-and-scale, glow flags, etc.)
  frame-repair.md        ← content of current ventnor-tarot-frame-repair/SKILL.md
  illustration-clean.md  ← content of current ventnor-tarot-illustration-clean/SKILL.md
  illustration-crop.md   ← content of current ventnor-tarot-illustration-crop/SKILL.md
```

### Split of ventnor-tarot-cards content

**cards.md keeps:**
- Purpose / two paths (A new card, B legacy rebuild)
- Working files table
- Saving and versioning rules
- Required inputs
- Counting thin objects rule
- Suit object references (Pentacles, Cups — the rules, not generation mechanics)
- Background preservation rules
- Rider–Waite analysis checklist
- Foreground rules
- Rectified artwork standard (dimensions, composition headroom)
- Framed gallery standard (dimensions, frame spec)
- Card text and Roman numerals (framed cards)
- Corrections and artifact inspection
- Quality checklists

**generation.md gets:**
- Generation size section (9:16 request, 2:3 output, black-bar method, strip-and-scale)
- Panel-ratio check after stripping
- Fallback soft-side-bleed method
- Glow flag details (how the compositing script works)
- Any other tool-specific mechanics

### Also update
- `AGENTS.md` — update the Project Structure section and any skill path references
  to reflect the new `.cursor/skills/ventnor-tarot/` layout.
- `Skill.md` (root) — if it duplicates content now in a sub-skill, trim it to
  reference the sub-skills instead. Or retire it in favour of the structured skills.
- The old five skill folders can be removed once the new structure is in place.

---

## What NOT to do in this thread
- Do not regenerate any card images.
- Do not touch `illustrations-rectified/`, `illustrations-numeralled/`, or
  `illustrations-framed/`.
- Do not touch the map skill or anything in `_old/`.
- Do not deploy (`upload.sh`).
