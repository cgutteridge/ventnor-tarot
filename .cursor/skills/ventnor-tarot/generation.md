# Ventnor Tarot — Image Generation Mechanics

This sub-skill covers the AI image-tool workarounds needed to produce a
correctly-sized **7:12 (700 × 1200 px)** rectified master from a tool that
does not natively support that ratio. Load this alongside `cards.md` whenever
generating or normalising a rectified draft.

---

## Generation size

Image tools do **not** offer native **7:12**, and the Cursor image generator's
`aspect_ratio` enum is only **`1:1` | `4:3` | `3:4` | `16:9` | `9:16`** — there
is **no `2:3` and no `7:12`**. Asking for `2:3` fails validation.

**What to request:** portrait **`9:16`** (tallest allowed option).

**What you usually get:** **1024 × 1536** (**2:3** — the phased framed-gallery
ratio, wider than 7:12). That raw output is **not** a rectified master.

Always normalize rectified drafts and approved masters to exactly
**700 × 1200 px** (or another exact 7:12 size) before saving under `tmp/` as a
rectified preview or writing `illustrations-rectified/<cardId>.png`.

---

## Preferred method: pure-black side bars (force a 7:12-safe panel)

Cover-cropping **2:3 → 7:12** discards **6.25% from each side**. Edge symbols
(seagulls, suit objects, hands, wands) flush to the tool frame get clipped.

**Default for new rectified gens** (proven on The Star / `maj17`):

1. Prompt **solid pure black (`#000000`) vertical bars on left and right**, each
   **~6.25% of total width** (~64 px of 1024). Put the entire scene **only** in
   the centre panel between the bars. No scene content in the bars.
2. **No** yellow dashed guides, crop rulers, annotations, watermarks, or other
   UI chrome in the image — bars only.
3. Strip the black bars (detect near-black columns), then **scale** the centre
   panel to **700 × 1200**. With **6.25%** bars on a 1024 × 1536 plate the panel
   is **896 × 1536** — exact **7:12** — so you scale with little or no further
   side crop.
4. **~7–7.5%** bars also work (slightly taller than 7:12); trim a little from
   the reserved top/bottom bands when normalizing.

---

## Panel-ratio check after stripping (sign-error guard)

The generator does not always produce bars of exactly the requested width.
After stripping, compute `panel_w / panel_h` and compare to `7/12`:

- Panel **wider** than 7:12 (`ratio > 7/12`): crop symmetrically from the
  **sides** until the panel is exactly 7:12, then scale to 700 × 1200.
- Panel **narrower** than 7:12 (`ratio < 7/12`): crop symmetrically from the
  **top and bottom** until the panel is exactly 7:12, then scale to 700 × 1200.
- **Never** use `PIL.Image.crop()` with a negative offset to extend a narrow
  panel — PIL silently pads with black, re-introducing the borders just removed.
  Always crop the excess dimension, not extend the short one.

Do **not** scrub "yellow guide" pixels across the whole plate afterward — that
can damage legitimate yellow stars or gold tones. If chrome appears, scrub only
in the outer few percent of the panel, or regenerate.

Keep narrative subjects inside the centre panel; do not rely on a post-crop
"focused edit" to rescue clipped edge symbols.

---

## Fallback: soft side bleed (no bars)

If black bars are impractical for a given edit:

- Compose with **~10%** low-importance bleed on the **left and right** (sky,
  foliage, plain ground). Exact centred 2:3→7:12 math is **6.25%** per side;
  use **~10%** for margin and for wider tool ratios (e.g. **3:4** crops
  **~11%** per side).
- Then cover-crop / composition-aware crop to **700 × 1200**. Do not letterbox
  the final master with empty bars.

Do not treat 1024 × 1536 or 9:17 tool output as interchangeable with the
rectified standard. Framed gallery cards remain **1024 × 1536** only after the
phased framing step.

---

## Glow flag and numeral compositing

**Source of truth:** `card-numerals.json` stores the `needsGlow` boolean for
every card.

When `needsGlow` is `true`, the compositing script (`make numeralled`) renders
the numeral on a transparent layer, Gaussian-blurs it to spread a halo outward
from the letterforms, tints the result with `glowColor` (cream `#fffdf5`), and
composites it below the sharp numeral. The halo hugs the text edges rather than
flooding a background zone. Colour defaults live at the top of `card-numerals.json`
and can be overridden per card if needed.

After generating or updating a rectified master:

1. Run `make illustrations-numeralled/<cardId>.png`.
2. Review the top band of the numeralled output.
3. If the numeral is hard to read against the background, set `needsGlow: true`
   in `card-numerals.json` for that card and rerun.
4. Do not manually edit files in `illustrations-numeralled/` — they are generated
   output.
