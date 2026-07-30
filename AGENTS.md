# Ventnor Tarot Project Instructions

## Scope

These instructions apply to the whole project.

Use `.cursor/skills/ventnor-tarot/` as the canonical skill set for generating, correcting, framing, and versioning Ventnor Tarot cards. Read the dispatcher `SKILL.md` there first, then load the relevant sub-skills (`cards.md`, `generation.md`, etc.) before changing card images or card-generation assets. `Skill.md` at the project root is a legacy alias; prefer the structured skills folder.

## Primary pipeline (new and replacement cards)

From now on, **rectified artwork is the canonical deliverable**:

1. **Rectified illustration (7:12 / 700 × 1200)** — create crisp, frameless art
   in `illustrations-rectified/`. No cream frame, gold border, title panel, Roman
   numeral, or other decoration. Free of AI artifacts. When rectifying, **inspect**
   for AI artifacts and damage from repeated processing; if any are found,
   **highlight** them and **discuss solutions** before approval. Stop for
   **human approval**.
2. **Register landscape source** — once the rectified card (and its place photo)
   are approved, copy the landscape into `vtarot/photos/` and update
   `vtarot/card-data.js` (`kind: "background"` only; no people photos).
3. **Numeral compositing** — run `make numeralled` to rebuild `illustrations-numeralled/`
   from the approved rectified art. Review the top band of each card and set
   `needsGlow: true` in `card-numerals.json` for cards where the near-black numeral
   needs a cream halo for legibility, then rerun `make numeralled`. See
   **Numeral compositing pipeline** below.
4. **Framing** — run `make framed` to rebuild `illustrations-framed/` from the
   numeralled art. Adds the cream/gold Ventnor frame and a bottom title panel
   (card name in uppercase) at **2:3** (1024 × 1536). All cards get the frame and
   title panel; Aces and courts additionally have no numeral at the top. See
   **Framing pipeline** below.
5. **Framed gallery card (phased)** — only for **new** rectified art that does not
   already have a matching `vtarot/` card, and only when the existing website needs
   it: copy the approved `illustrations-framed/<cardId>.png` to `vtarot/<cardId>.png`
   and bump its version in `CARD_IMAGE_VERSIONS`. See `.cursor/skills/ventnor-tarot/cards.md`.
   Legacy migrations from `vtarot/` do not require reframing.

`illustrations-rectified/` is the print-ready artwork store. Do not skip it for
new or replacement cards. **Never use 9:17** for rectified masters.

## Legacy rebuild (existing framed cards only)

For cards that already exist only as framed `vtarot/` images, keep the migration
path: crop → clean → rebuild rectified from references. See
`.cursor/skills/ventnor-tarot/illustration-crop.md` and
`.cursor/skills/ventnor-tarot/illustration-clean.md`.

**No reframe expected:** if the rectified master was produced **from** an existing
`vtarot/` framed card, the migration is complete once
`illustrations-rectified/<cardId>.png` is approved. Do **not** reframe back into
`vtarot/` unless the user explicitly asks to replace that gallery card.

## Project Structure

- `vtarot/` — finished framed gallery cards and the published site.
- `vtarot/photos/` — official **landscape / place** source photographs (no people
  references). Listed from `vtarot/card-data.js` with `kind: "background"`.
- `vtarot/card-data.js` — per-card notes and public source images.
- `illustrations-rectified/` — approved **7:12** (**700 × 1200**) frameless artworks (canonical
  clean art for print; crisp, decoration-free, artifact-free).
- `illustrations-numeralled/` — **generated** output: rectified art with Roman numerals
  composited at the top. Built by `make numeralled`; do not edit files here manually.
  Rebuild any card with `make illustrations-numeralled/<cardId>.png` after updating the rectified
  master or `card-numerals.json`.
- `illustrations-framed/` — **generated** output: numeralled art with the Ventnor cream/gold
  frame and title panel composited. Width is fixed at 1024 px; height grows from the art
  (≈ 1693 px for a 700 × 1200 source). Built by `make framed`; do not edit files here manually.
  Rebuild any card with `make illustrations-framed/<cardId>.png` after updating the numeralled
  source, `card-numerals.json`, or `scripts/compose_frame.py`.
- `card-numerals.json` — canonical per-card numeral metadata: name, suit, integer
  number, Roman numeral string (null for Aces and courts), and `needsGlow` flag.
  Edit this file to change numeral display or toggle glow; then run `make numeralled`.
- `card-details.json` — canonical per-card gallery data (summaries, notes, source-image
  references). Paths use website-relative prefixes (`sources/`, `rider-waite/`).
  `make website` / `scripts/build-website.sh` wraps this into `website/card-data.js`
  (`window.CARD_DETAILS = <json>;`) — edit `card-details.json`, not the generated file.
  Formerly maintained as `_old/vtarot/card-data.js` (now fully archived).
- `illustrations-raw/` — legacy frame-stripped crops from existing `vtarot/` cards.
- `illustrations-cleaned/` — legacy numeral/corner-cleaned crops.
- `tmp/` — intermediate working files, drafts, and generation outputs before approval.
- `sources/` — canonical source archive: background photos (`<id>-background.<ext>`),
  raw originals (`<id>-background-original.<ext>`), and suit-object references
  (`cups-reference.jpg`, `cups-detail-1–4.jpg`, `pentacles-reference.png`).
- `rider-waite/` — Rider-Waite-Smith reference cards.
- `rejected/` — superseded or rejected versions.

## Card Asset Rules

- Keep `vtarot/` limited to files intended for publication (framed cards + site).
- **New/replacement art** targets **7:12** in `illustrations-rectified/` first
  (canonical size **700 × 1200 px**, or an exact 7:12 scale such as 882 × 1512).
  Never **9:17** or **900 × 1700**.
- **Rectified composition:** keep the top and bottom **~10%** of the frame as
  low-importance or negative space (sky, grass, water, plain ground). Reserve this
  for later Roman numerals (top) and title panel (bottom) when framing phased 2:3
  gallery cards. Keep faces, hands, and key symbols in the middle band.
- **Generation size / side protection:** the image tool cannot request **7:12** or
  **2:3** (enum is only 1:1 / 4:3 / 3:4 / 16:9 / 9:16). Ask for **`9:16`**; expect
  **~1024 × 1536 (2:3)**. Prefer **~6.25% pure-black side bars**, strip, then
  scale to **700 × 1200**; fallback is **~10%** soft left/right bleed. See
  `.cursor/skills/ventnor-tarot/generation.md` § Generation size.
- **Framed gallery cards** in `vtarot/` are a **phased** deliverable for the
  existing website only: **2:3** (1024 × 1536 px), matching `vtarot/wands02.png`
  for frame and typography. They are derived from rectified art, not the canonical
  master format.
- Do not overwrite a primary file in `vtarot/` or `illustrations-rectified/` without
  first moving the old version to `rejected/` with a short, specific reason suffix.
- Before writing any primary file, **always verify existence with `ls`** (e.g.
  `ls illustrations-rectified/wands11.png 2>/dev/null`) rather than relying on
  glob alone. Glob can return false negatives on OneDrive-synced paths. If `ls`
  finds a file, move it to `rejected/` before writing the replacement.
- Use the existing primary filename pattern: `maj10.png`, `cups04.png`,
  `pents10.png`, `swords07.png`, `wands14.png`, etc.
- Preserve original source images unless the user explicitly asks to modify them.
- Use `tmp/` for crops, rotations, drafts, and generation outputs.
- **Draft versioning:** never overwrite an existing draft in `tmp/` (or elsewhere).
  Write each new draft as a new file with an incremented suffix (`-v2`, `-v3`, …)
  or another unique stem. Keep prior drafts until the user says to discard them.

## Site Rules

- `vtarot/index.html` is the gallery page for the finished deck images.
- Keep image references relative to `vtarot/` unless the page structure changes.
- If changing the gallery, verify it still opens as a static HTML page.
- When a card’s rectified art and landscape background are approved:
  1. Ensure `illustrations-rectified/<cardId>.png` is the approved artwork.
  2. Copy the landscape into `vtarot/photos/<cardId>.<ext>`.
  3. Add or update that card in `vtarot/card-data.js` with a `sourceImages` entry
     `{ kind: "background", src: "photos/<cardId>.<ext>", ... }`.
  4. Never publish people-reference photographs or identifying names in `photos/`
     or `card-data.js` unless the user explicitly approves them for the site.

## Numeral compositing pipeline

`illustrations-numeralled/` holds the rectified cards with Roman numerals overlaid —
the intermediate layer between clean rectified art and fully framed gallery cards.

**Data file:** `card-numerals.json` — one entry per card with:
- `id`, `name`, `suit`, `number` (integer), `numeral` (Roman string, or `null` for
  Aces and courts), `needsGlow` (boolean).

**Build command:** `make numeralled` — incremental; only cards whose rectified source
or `card-numerals.json` is newer than the output are recomposed.

**Single card rebuild:** `make illustrations-numeralled/<cardId>.png`
(e.g. `make illustrations-numeralled/maj18.png`).

**Font override:** `make numeralled NUMERAL_FONT=assets/fonts/MyFont.ttf`
Default fallback: Times New Roman from the macOS system fonts.

**Glow flag:** when `needsGlow` is `true`, the compositing script renders the numeral
on a transparent layer, Gaussian-blurs it to spread a halo outward from the
letterforms, tints the result with `glowColor` (cream `#fffdf5`), and composites it
below the sharp numeral. The halo hugs the text edges rather than flooding a background
zone. Colour defaults live at the top of `card-numerals.json` and can be overridden
per card if needed.

**Do not edit files in `illustrations-numeralled/` manually.** They are generated
output. Edit `illustrations-rectified/<cardId>.png` or `card-numerals.json`, then
rebuild with Make.

## Framing pipeline

`illustrations-framed/` holds the fully framed 2:3 gallery cards with the Ventnor
cream/gold border and title panel — the final intermediate before `vtarot/`.

**Build command:** `make framed` — incremental; only cards whose numeralled source
or `card-numerals.json` is newer than the output are recomposed.

**Single card rebuild:** `make illustrations-framed/<cardId>.png`
(e.g. `make illustrations-framed/maj18.png`).

**Font override:** `make framed FRAME_FONT=assets/fonts/MyFont.ttf`
Default fallback: Times New Roman from the macOS system fonts.

**Layout constants** (all in `scripts/compose_frame.py`, at the top of the file):
- Canvas width: fixed at 1024 px. Height: dynamic (2 × border + scaled art height);
  ≈ 1693 px for a 700 × 1200 source.
- Outer cream border: 34 px; gold rule: 10 px; inner art area starts at x/y = 44.
- Title panel: 8 px gold divider + 104 px cream text area = 112 px total, **overlaid**
  on the bottom of the art — no height is added to the canvas.
- Art scaling: source scaled to fill the inner width (936 px); **no height is cropped**.
  The full art is preserved; only the title panel overlays the bottom ~7% (the
  low-importance zone reserved for this by design).
- Title text: card `name` from `card-numerals.json` uppercased, centred, Times New Roman.

**Publishing to vtarot/:** once a framed card is approved, copy
`illustrations-framed/<cardId>.png` to `vtarot/<cardId>.png` (reject the old file
first if replacing) and bump its entry in `CARD_IMAGE_VERSIONS` in `vtarot/index.html`.

**Do not edit files in `illustrations-framed/` manually.** They are generated
output. Edit the numeralled source, `card-numerals.json`, or `scripts/compose_frame.py`,
then rebuild with Make.

## Deployment

- `upload.sh` syncs `vtarot/` to the remote web host.
- Do not run deployment or upload commands unless the user explicitly asks.

## Counting thin objects (swords, wands, staves)

Never assume you can accurately count thin metal or wooden objects (swords,
wands, staves, arrows) in a generated or inspected image. Always ask the user
to confirm the count before approving, proceeding to the next step, or
reporting the count as correct.

## Image generation limit

**Never call `GenerateImage` more than 3 times in a single session without stopping for human review.**

After the 3rd generation attempt, stop, show the user what has been tried (file paths of each draft), explain what is not working, and ask how to proceed. Do not attempt a 4th generation until the user explicitly approves a revised approach.

This limit exists because runaway generation loops are expensive and have caused significant unintended costs. If a card genuinely needs more than 3 attempts, the user must consciously choose to continue — never loop autonomously.

## Human approval requests

Whenever stopping for human approval or asking the human to check a file:

- **Always name the exact file path(s)** the human should open and inspect
  (e.g. `tmp/swords14-rectified-draft.png`). Never refer only to "the draft"
  or "the image" without the path.
- If multiple files are relevant (e.g. a raw crop and a normalised draft), list
  each one separately.

## Style

- Match the existing project conventions and naming.
- Keep edits narrowly scoped to the requested card, page, or instruction file.
- Avoid broad cleanup or reorganizing assets unless the user asks for it.

## Instruction maintenance

When a task surfaces a gap, contradiction, or repeated mistake in how work is
done, **suggest** updates to the project instructions rather than leaving the
lesson implicit. Do this at the end of the task, or as soon as a clear pattern
emerges — do not wait for the user to ask.

Look for triggers such as:

- User feedback that corrects workflow, format, composition, naming, or approval
  steps.
- False starts, backtracking, or errors caused by missing, stale, or ambiguous
  guidance in `AGENTS.md` or a `.cursor/skills/ventnor-tarot/` sub-skill file.
- The same correction or workaround appearing more than once across cards or
  sessions.

When suggesting changes:

1. Name the file(s) that should change: `AGENTS.md` and/or a specific
   sub-skill under `.cursor/skills/ventnor-tarot/`.
2. Propose concrete wording — a new bullet, clarified step, or explicit
   prohibition — not a vague “we should document this”.
3. Say **why** the change would help (what mistake or rework it prevents).
4. Keep suggestions narrowly scoped to the lesson learned; do not propose broad
   rewrites unless several related gaps appear together.

Do **not** edit instruction or skill files unless the user asks you to apply a
suggestion. Offering the suggestion is the default.
