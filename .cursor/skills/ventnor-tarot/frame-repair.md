# Ventnor Tarot Frame Repair

Repair only the faulty **framed gallery** card region. Use `vtarot/wands02.png` as
the permanent frame reference.

If the fault is in the artwork (figures, location, grade), fix
`illustrations-rectified/` first (per `cards.md`), then reframe — do not hide art
problems inside a frame repair.

## Frame anatomy

- Photograph fills the inner frame to its top edge.
- Roman numeral overlays the photograph; never a separate cream header.
- No horizontal rule or bar beneath the numeral.
- Subtle glow behind numeral only if needed for legibility.
- Cream outer frame, gold inner border, rounded corners, title panel, and divider
  match `vtarot/wands02.png`.

## Repair workflow

1. Work from the most recent framed card; copy into `tmp/`; preserve the source.
2. Identify the smallest region that contains the fault.
3. Extend the existing photograph naturally behind the numeral when replacing an
   unwanted header, bar, or divider. Do not extend or regenerate the outer frame.
4. Reapply the correct numeral (value, placement, scale, serif). Glow only if needed.
5. Preserve **1024 × 1536 px**, 2:3 portrait output.
6. Inspect at full size: photo to top inner edge; no panel/line under numeral.
7. Save in `tmp/` for approval. Once approved, move the existing primary to
   `rejected/` with a `-frame-*` or `-numeral-*` suffix, then write `vtarot/`.

## Do not

- extend, crop, resize, redraw, or regenerate the outer frame
- create a cream numeral header
- add a straight edge beneath the numeral
- modify the illustration to hide a frame fault
- overwrite the published primary before approval and versioning
- skip updating from rectified masters when the user is replacing art wholesale
