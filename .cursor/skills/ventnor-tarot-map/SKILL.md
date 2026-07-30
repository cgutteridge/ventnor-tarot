---
name: ventnor-tarot-map
description: >-
  Paints the zoom-level master illustrations for the Ventnor Tarot map (an
  aged tarot/woodcut-engraving-styled Leaflet map of the project's area) and
  publishes them as XYZ tiles. Use when generating, correcting, or replacing
  a map zoom master, or when the map's tile pipeline needs to be re-run.
---

# Ventnor Tarot Map

## Purpose

Produce one hand/AI-painted master illustration per zoom level for the
Leaflet map at `vtarot/map.html`, covering the stretch of Ventnor this deck
is drawn from: Bonchurch Beach, Steephill Cove, the St Boniface Down radar
station, the top of Upper Ventnor Cemetery, and out past the far side of
Ventnor Botanic Garden.

This is a companion feature to the card deck (see `Skill.md`) but is scoped
to `map/` and `vtarot/map-tiles/` + `vtarot/map.html` only. **Never touch**
`illustrations-rectified/`, `vtarot/<cardId>.png`, `vtarot/photos/`, or
`vtarot/card-data.js` from this skill.

## How the map is built

Unlike the cards, the map is not one image — it's a standard XYZ tile
pyramid so Leaflet can pan/zoom it. To keep a hand-painted look seamless
across tile boundaries, each zoom level is painted as **one single coherent
master image**, sized and geographically aligned so it slices into tiles
with no seams. Do not generate per-tile; do not paint one universal image
for all zooms.

| Location | Role |
|---|---|
| `map/manifest.json` | Source of truth: for each zoom, exact `pixel_width`/`pixel_height` and `geo_bounds`. Regenerate with `map/scripts/tile_grid.py` if the landmark bbox changes. |
| `map/reference/z{zoom}.png` | Real, stitched OpenStreetMap tiles at the manifest's exact canvas size — the accurate skeleton (coastline, roads, buildings) to paint over. Internal only, never published. Regenerate with `map/scripts/fetch_reference.py`. |
| `map/tmp/` | Draft painted masters awaiting approval. |
| `map/masters/z{zoom}.png` | Approved final painted master per zoom (canonical, like `illustrations-rectified/`). |
| `vtarot/map-tiles/{z}/{x}/{y}.png` | Published XYZ tiles, sliced from `map/masters/` via `map/scripts/slice_tiles.py`. Currently populated with placeholder real-OSM tiles standing in for unfinished art — swapping in painted masters is a drop-in replacement of the same files. |
| `rejected/` | Superseded master versions, with a reason suffix, same convention as card art. |

## Style rules — aged tarot/woodcut engraving map

- **Palette**: parchment `#f3ebe0`, ink `#1c1814`, gold `#b8924a`, sea-ink
  `#1a3a4a` (same variables as `vtarot/index.html`).
- **Coastline**: hand-inked hairline, slightly wobbly/irregular (engraving
  style), not a clean vector line.
- **Hills/downs**: fine cross-hatch shading rather than flat green fill.
- **Paths/roads**: dashed gold hairline.
- **Landmarks**: a small woodcut-style vignette icon at each of the four
  boundary landmarks (a cup, a sword, a star, a moon — pick a natural
  assignment) integrated into the artwork itself. These are **not** Leaflet
  markers — no pins, no click interactions, no per-card links on this map.
- **Labels**: serif, tracked-out capitals (Cormorant Garamond), matching the
  card frame typography.
- Preserve the real geometry from the `map/reference/z{zoom}.png` skeleton —
  coastline shape, road layout, building footprints — this is a stylistic
  reinterpretation, not an invented layout.

## Workflow — new or replacement zoom master

1. Confirm `map/manifest.json` covers the intended area (re-run
   `tile_grid.py` first if not — e.g. to extend the bbox).
2. Confirm `map/reference/z{zoom}.png` exists for the target zoom (re-run
   `fetch_reference.py` if not).
3. Paint a draft at **exactly** `pixel_width` x `pixel_height` from the
   manifest for that zoom, in `map/tmp/z{zoom}-draft.png`.
4. **Inspect** the draft for AI artifacts and generative mush (same checklist
   as `Skill.md`'s Artifact inspection section). Highlight and discuss any
   issues before proceeding.
5. **Stop for human approval.** Do not treat drafts as final.
6. On approval: if replacing an existing master, move it to `rejected/` with
   a reason suffix first, then write `map/masters/z{zoom}.png`.
7. Run `python3 map/scripts/slice_tiles.py --zooms {zoom}` to publish the
   approved master into `vtarot/map-tiles/{zoom}/`.
8. Reload `vtarot/map.html` and check pan/zoom around that level for seams,
   missing tiles, or misaligned geometry against the reference.

Do not run `upload.sh` (deployment) as part of this workflow unless the user
explicitly asks.

## Quality check

- [ ] painted at the manifest's exact pixel size for that zoom
- [ ] inspected for AI artifacts / generative mush; issues discussed if found
- [ ] coastline, roads, and buildings match the real reference skeleton
- [ ] palette matches the site's parchment/ink/gold/sea-ink variables
- [ ] the four landmark vignettes are present and legible
- [ ] no Leaflet markers/pins added — labels live in the artwork only
- [ ] sliced tiles load with no gaps or 404s across `vtarot/map.html`
