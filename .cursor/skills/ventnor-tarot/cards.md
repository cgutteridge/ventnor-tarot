# Ventnor Tarot — Card Concepts and Workflow

## Purpose

Produce Ventnor interpretations of the Rider–Waite–Smith deck.

**Canonical clean artwork** lives in `illustrations-rectified/` at **7:12**
(**700 × 1200 px**, or an exact 7:12 scale such as 882 × 1512). Frameless: no
cream frame, gold border, title panel, Roman numeral, or other decoration. Masters
must be crisp, photographically clean, and free of AI artifacts. **Never use 9:17**
or **900 × 1700** for rectified art.

**Framed gallery cards** in `website/cards/` (assembled by `make website`) at
**2:3** (**1024 × 1536 px**) are a **phased deliverable for the existing website**
only — composites of approved rectified art with the Ventnor frame, title, and
numeral. Do not treat 2:3 as the canonical artwork standard.

The Two of Wands at `vtarot/wands02.png` remains the permanent **frame and
typography** standard when producing phased gallery cards.

For AI image-tool mechanics (aspect-ratio workaround, black-bar method,
strip-and-scale, panel-ratio checks), read `generation.md`.

---

## Two paths

### A — New or replacement card (default)

1. Build **700 × 1200** (7:12) frameless art → draft in `tmp/` → **human approval** →
   `illustrations-rectified/<cardId>.png`.
2. On approval of art + landscape: copy landscape to `vtarot/photos/<cardId>.<ext>`
   and update `vtarot/card-data.js` (`kind: "background"` only).
   Before copying, resizing, pasting, or converting a landscape source, preserve
   the original downloaded camera file in the source archive. Extract GPS/EXIF
   from that original and record approved coordinates on the `kind: "background"`
   source entry as:

   ```js
   location: {
     latitude: <decimal>,
     longitude: <decimal>,
     source: "exif",
   }
   ```

   If the original file cannot be matched or has no GPS EXIF, do not invent
   coordinates; leave `location` unset or mark it separately as manually inferred
   only after review.
3. When the existing website needs an update: frame into `vtarot/<cardId>.png`
   (crop/compose from the approved rectified file; apply Ventnor frame, title,
   numeral at 2:3).

Do not write a new framed `vtarot/` card until the rectified file is approved,
unless the user explicitly asks to frame-only from an existing approved rectified.
Framing is optional until the gallery site requires it.

### B — Legacy rebuild (existing framed cards only)

When migrating an old framed card that has no rectified master yet:

1. Crop frame → `illustrations-raw/` (illustration-crop skill / Makefile).
2. Clean numerals/corners → `illustrations-cleaned/` (illustration-clean skill).
3. Rebuild **700 × 1200** (7:12) using `vtarot/` card + landscape + Rider–Waite as
   references (not naive plate-padding). Approve → `illustrations-rectified/`.
4. Register landscape in `photos/` + `card-data.js`.

**Do not reframe** into `vtarot/` after a legacy migration. The existing framed
`vtarot/<cardId>.png` already serves the phased website; rectifying is the goal.
Reframe only if the user explicitly asks to replace that gallery card.

---

## Working files

Use `tmp/` for intermediates: references, drafts, crops, preparatory edits.

| Location | Role |
|----------|------|
| `illustrations-rectified/` | Approved 7:12 (700 × 1200) frameless masters |
| `vtarot/` | Framed gallery cards + site (legacy) |
| `vtarot/photos/` | Official landscape sources only |
| `rejected/` | Superseded versions with reason suffixes |

### Saving and versioning

**Rectified masters** use one primary name: `illustrations-rectified/cups01.png`.

**Gallery cards** use one primary name: `vtarot/cups01.png`.

When replacing either:

1. Move the existing primary to `rejected/` with a specific reason suffix.
2. Write the new approved file as the primary name.

Never overwrite a primary without rejecting the previous version first.

**Draft versioning:** never overwrite an existing draft in `tmp/` (or elsewhere).
Write each new draft as a new file with an incremented suffix (`-v2`, `-v3`, …) or
another unique stem. Keep prior drafts until the user says to discard them.

### Publishing and cache versioning

The gallery cache-busts each card via `CARD_IMAGE_VERSIONS` in `vtarot/index.html`
(missing keys default to `"1"`). Before uploading a new or replacement **framed**
card:

1. Set or increment only that card's version (e.g. `wands10: "2"`).
2. If the card is also the hero background (`wands02`), update its `?v=` in the
   hero URL.
3. Upload `vtarot/` only after the card image, `card-data.js` (if changed), and
   `index.html` are ready.

---

## Required inputs

Before generating rectified art, confirm:

1. Rider–Waite–Smith reference in `rider-waite/`
2. Real **landscape** background photograph (approve as official place photo)
3. Enough information to identify the card

If either required image is missing, ask for it. Do not invent a substitute
background.

Optional: photographs of a cup, object, costume, building, or person — use as
direct visual references when supplied. **Do not** publish people references in
`vtarot/photos/` or `card-data.js` unless the user explicitly approves.

---

## Counting thin objects (swords, wands, staves)

Never assume you can accurately count thin metal or wooden objects (swords,
wands, staves, arrows) in a generated or inspected image. Always ask the user
to confirm the count before approving, proceeding to the next step, or
reporting the count as correct.

---

## Suit object references (mandatory)

### Pentacles

All pentacle / coin / disk objects must use `sources/pentacles-reference.png`.

Do not invent a different pentacle design. Do not substitute generic coins or discs.

### Cups

All cup / chalice objects must use `sources/cups-reference.jpg`.

Allowed Ventnor Fringe plastic pint designs in that reference:

- magenta print on a clear/frosted cup
- green print on a clear/frosted cup

Use either design for a single cup; for multiple cups, repeat or mix the two.
Do not invent other cup designs. Do not substitute generic goblets or chalices.

Detail sources if needed: `sources/cups-detail-1.jpg` … `sources/cups-detail-4.jpg`.

**Branding:** keep "VENTNOR FRINGE" (and other print from the refs) readable.
Do not invent alternate logos or garbled festival text.

**Count and framing:** the suit count must be exact (e.g. Ten of Cups = exactly
ten). Every cup must sit fully inside the final **7:12** frame — no clipped
rims, bases, or sides after black-bar strip / side normalize. Inset outermost
cups from the panel edges when composing.

**Arc / rainbow cards (e.g. Ten of Cups):** place cups on or in the rainbow
bands following Rider–Waite geometry. Cups should feel celebratory and
glorious when the card's meaning calls for it (emotional abundance, true
wealth of home and love — not material bling).

- **Lean matches the rainbow:** each cup's picture-plane tilt must follow the
  local tangent of the rainbow at that point (left limb leans with the
  descending left arc, apex more upright, right limb leans with the
  descending right arc). Cups ride the curve — not a flat row under it, and
  not upright cups ignoring the bend.
- **Yaw / facing (anti-stamp):** separately, spin each cup around its vertical
  axis so the Ventnor Fringe print does not show the same angle on every cup
  (e.g. text always on the left). Vary title centred / left / right, more
  figure art, or partial side view — irregularly across the set.

---

## Background preservation

The landscape photograph must remain recognisably the same real photograph.

**Allowed:** crop, rotate, straighten, resize, perspective correction; modest
exposure, contrast, white-balance, colour, or lighting adjustments; extend sky or
low-stakes edges (grass, water, sky) when composing to **700 × 1200** (7:12),
matching the photo's grade. It is also acceptable to remove or soften foreground
floor / pavement shadows when they would interfere with the later title panel or
make the framed card read poorly, provided the ground still matches the approved
place photograph.

**Forbidden:**

- regenerate or replace the location wholesale
- fabricate terrain, buildings, paths, trees, sea defences, railings, walls, roads
- invent scenery that was not in the photograph
- alter ground textures only to shoehorn figures

Place new foreground over the photograph. Do not reconstruct the location.

When the user says "only crop and rotate," make no lighting or colour changes either.

Avoid full-image AI reprocessing loops that cause **img2img drift** / generative
mush. Prefer reference-guided generation of the 700 × 1200 master, then small focused
fixes.

---

## Rider–Waite analysis

Before generating, silently identify:

- card name; suit or Major Arcana identity
- number of figures; number of suit objects; arrangement and direction
- poses, gestures, gaze, facial mood
- clothing colours and broad shapes
- landscape relationship; scale and hierarchy
- symbolic objects; easy-to-miss details
- narrative or emotional tension essential to recognising the card

Preserve critical features. Do not simplify until the card becomes generic.

---

## Foreground

Add only what Rider–Waite requires: people, animals, suit objects, and symbolic
objects that sit in front of or interact with the photographed scene.

Whenever Rider–Waite shows an eagle, replace it with a photorealistic seagull,
preserving pose, placement, scale, and symbolic role.

Foreground must be photorealistic, live-action in appearance, lit to match the
photo, correctly scaled, and compositionally faithful to Rider–Waite.

Do not make added elements look illustrated, painted, theatrical, plastic, or CGI.

---

## Rectified artwork standard (7:12 / 700 × 1200)

- Aspect **7:12** portrait (canonical **700 × 1200 px**, or an exact 7:12 scale)
- **Never** **9:17** or **900 × 1700**
- **No** cream frame, gold border, title panel, Roman numeral, or other decoration
- Full-bleed photograph to square corners
- Crisp detail; no smeared textures, halos, or generative mush
- Colour grade consistent with the approved landscape photo
- Suitable for print; may later be cropped into a phased 2:3 gallery card

### Composition (headroom for framing)

When composing or cropping rectified art, treat the **top ~10%** and **bottom ~10%**
as reserved low-importance zones — even though numerals and titles are added only at
the phased framing step.

- **Top band:** leave room for a Roman numeral overlay (sky, soft foliage, or other
  non-critical detail). Avoid faces, hands, halos, or key symbols here.
- **Bottom band:** leave room for the title panel (grass, path, water edge, plain
  foreground). Avoid feet, suit objects, or narrative focal points here.
- **Middle band:** place the main subject, action, and symbolic centre of the card.

Use crop, reposition, or modest edge extension (sky, grass) to achieve this when
the landscape source is tight. Do not letterbox with empty bars.

For image-tool mechanics — how to request the right aspect ratio, how to strip
black side bars, how to normalise the panel to exactly 700 × 1200 — see
`generation.md`.

---

## Framed gallery standard (2:3 — phased website only)

Produce these only when updating the existing gallery site. Match `vtarot/wands02.png`:

- 2:3 canvas, **1024 × 1536 px**
- cream aged-paper outer frame; narrow gold inner border; rounded corners
- image-area proportions; bottom title panel; decorative divider
- black serif typeface; title size, tracking, alignment, capitalization
- top numeral over the image (not on a separate cream panel); no rule under the numeral
- photograph fills to the top inner edge behind the numeral

Frame by cropping/compositing from the **approved rectified** file when possible.
Do not redesign the frame between cards.

---

## Card text (framed cards only)

Exact title in uppercase in the bottom panel (e.g. `TWO OF WANDS`, `PAGE OF CUPS`,
`THE HERMIT`). Check spelling.

---

## Roman numerals (framed cards only)

Numbered Minor Arcana: `II`–`X` at the top. None on Aces or courts.

Major Arcana: traditional Rider–Waite numeral, including `0` where appropriate.

Match Two of Wands numeral font, size, colour, and position. Overlay on the image;
use a subtle glow only if needed for legibility.

**Source of truth:** `card-numerals.json` at the project root holds the numeral
string and `needsGlow` flag for every card. `illustrations-numeralled/` is the
generated intermediate — rectified art with numerals composited by `make numeralled`.
Derive framed numerals from this data rather than inventing placement or glow choices
independently. See `AGENTS.md` § Numeral compositing pipeline.

---

## Workflow — new / replacement card

1. Confirm Rider–Waite, landscape background, and optional object refs.
2. Copy inputs into `tmp/`; keep originals untouched.
3. Analyse symbolism. Load suit refs for Pentacles/Cups as required.
4. Generate **700 × 1200** (7:12) frameless art into `tmp/` — see `generation.md`
   for tool mechanics.
5. **Inspect the draft** for AI artifacts and damage from repeated processing
   (see **Artifact inspection** below). If any are found, highlight them and
   discuss fix options with the user before treating the draft as ready.
6. **Stop for approval.** State the exact file path(s) the human should open
   (e.g. `tmp/swords14-rectified-draft.png`). Do not treat drafts as final.
7. On approval: write `illustrations-rectified/<cardId>.png` (reject prior master
   first if replacing).
8. Copy approved landscape to `vtarot/photos/<cardId>.<ext>` and update
   `vtarot/card-data.js`.
8a. Run `make illustrations-numeralled/<cardId>.png` to rebuild the numeralled intermediate.
    Review the top band; if the numeral needs a cream halo for legibility, set
    `needsGlow: true` for that card in `card-numerals.json` and rerun.
9. Frame from the rectified master into `tmp/`, then on approval follow **Saving
   and versioning** into `vtarot/<cardId>.png` and bump `CARD_IMAGE_VERSIONS`.

Do not write a design proposal unless asked. After generating, do not describe or
summarize the image unless the user asks — **except** when reporting artifact or
repeated-processing issues found during inspection.

---

## Corrections

- Prefer editing the rectified master for artwork issues; reframe `vtarot/` only
  for new cards or when the user explicitly asks (not after legacy migration).
- Prefer frame-repair skill for frame/numeral/title faults on gallery cards.
- On approval, reject the old primary then write the new primary.
- Change only the requested feature; treat "only change the cup" literally.

If an edit would necessarily alter something else, say so briefly first.

---

## Artifact inspection

When rectifying (new drafts, corrections, or legacy rebuilds), **read the image**
and inspect for:

- **AI artifacts** — smearing, generative mush, warped anatomy or hands, melted
  edges, texture soup, plastic/CGI skin, halos, duplicated features, garbled text
  or patterns, and similar telltales.
- **Repeated-processing damage** — img2img drift, over-smoothed or muddy detail,
  colour shifts, lost landscape fidelity, and cumulative mush from multiple full
  passes or stacked regenerations.

If any issues are found:

1. **Highlight** them clearly (what and where on the card).
2. **Discuss solutions** with the user before approving or writing
   `illustrations-rectified/` — e.g. small focused heal vs regenerate a region vs
   rebuild from references rather than another full-image pass.

Do not silently ship artifact-heavy drafts for approval as if they were clean.
Prefer small focused fixes over further full-image AI loops.

---

## Quality check — rectified

- [ ] 700 × 1200 (7:12), frameless, no title, no numeral, no decoration
- [ ] inspected for AI artifacts and repeated-processing damage; issues highlighted
      and solutions discussed if any were found
- [ ] crisp; no visible AI artifacts, smearing, or generative mush
- [ ] background matches the approved landscape photograph
- [ ] no invented location details; no img2img drift from repeated full passes
- [ ] symbolism complete; suit-object count correct
- [ ] Pentacles / Cups refs used when applicable
- [ ] top ~10% and bottom ~10% are low-importance (headroom for numeral and title)
- [ ] after normalize from tool output, edge symbols (birds, suit objects, etc.)
      are fully in frame — generation used ~6.25% black side bars (preferred) or
      ~10% left/right soft bleed when the tool plate was wider than 7:12

## Quality check — framed gallery card

- [ ] derived from approved rectified art when available
- [ ] title and numeral correct (or numeral intentionally absent)
- [ ] photo fills top inner edge; no numeral panel or rule under numeral
- [ ] frame matches Two of Wands; 1024 × 1536
- [ ] no watermark or extra text
- [ ] `card-data.js` / `photos/` updated if this approval included a landscape source
