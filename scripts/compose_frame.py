"""
compose_frame.py — add the Ventnor frame and title panel to a numeralled card.

Takes a numeralled illustration (from ``illustrations-numeralled/``) and
produces a framed gallery card in ``illustrations-framed/``.

Frame layout
------------

::

    ┌─ OUTER_CREAM px ─────────────────────────────────────────────────┐
    │  ┌─ GOLD_WIDTH px ──────────────────────────────────────────────┐ │
    │  │                                                              │ │
    │  │   full art (scaled to INNER_W wide, full height retained)   │ │
    │  │                                                              │ │
    │  │  ┌── TITLE_DIVIDER_H px gold rule (overlay on art bottom) ──┤ │
    │  │  │                                                          │ │
    │  │  │  TITLE CREAM  (card name, centred, overlaid on art)      │ │
    │  │  └──────────────────────────────────────────────────────────┘ │
    │  └──────────────────────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────────────────┘

Art scaling strategy
--------------------
The source art is scaled to fill exactly ``INNER_W`` pixels wide while
preserving its aspect ratio.  **No height is cropped.**  The canvas height
grows to accommodate the full scaled art plus the top and bottom borders.

The title panel is composited **on top of** the bottom portion of the art
(a cream overlay with a gold divider rule above it).  The art beneath it is
preserved — only the overlay covers it.  The numeral at the top is part of
the art and is also fully preserved.

Output size
-----------
- Width: always ``CANVAS_W`` (= ``INNER_W + 2 * (OUTER_CREAM + GOLD_WIDTH)``).
- Height: dynamic — ``2 * (OUTER_CREAM + GOLD_WIDTH) + scaled_art_height``.

For a 700 × 1200 (7:12) source, the output is 1024 × 1692.

Usage
-----
::

    python3 scripts/compose_frame.py \\
        --card maj07 \\
        --source illustrations-numeralled/maj07.png \\
        --output illustrations-framed/maj07.png \\
        --data card-numerals.json \\
        [--font path/to/font.ttf]

"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

OUTER_CREAM: int = 34
"""Cream/aged-paper border width on all four sides (pixels)."""

GOLD_WIDTH: int = 10
"""Gold rule width on all four sides, inset from the cream edge (pixels)."""

BORDER: int = OUTER_CREAM + GOLD_WIDTH
"""Total opaque border on each side before the art begins (pixels)."""

# The inner art width drives the canvas width.
INNER_W: int = 936
"""Width of the art area inside the gold border (pixels).

The canvas width is always ``INNER_W + 2 * BORDER`` = 1024.
"""

CANVAS_W: int = INNER_W + 2 * BORDER  # 1024
"""Output canvas width (pixels). Derived from INNER_W and BORDER."""

# Title panel (overlaid on the art bottom, does not add to canvas height).
TITLE_DIVIDER_H: int = 8
"""Gold horizontal rule at the top of the title overlay (pixels)."""

TITLE_CREAM_H: int = 104
"""Cream title-text area height (pixels)."""

TITLE_PANEL_H: int = TITLE_DIVIDER_H + TITLE_CREAM_H  # 112
"""Total height of the title overlay (gold divider + cream text area)."""

# Colours (flat, first-pass approximations matched to vtarot/wands02.png).
CREAM_COLOR: tuple[int, int, int] = (235, 222, 198)
"""Aged-paper cream used for the outer border and title panel background."""

GOLD_COLOR: tuple[int, int, int] = (175, 142, 68)
"""Flat gold used for the border rule lines."""

TITLE_TEXT_COLOR: tuple[int, int, int] = (28, 24, 20)
"""Near-black used for the title text."""

# Title text sizing.
TITLE_HEIGHT_FRAC: float = 0.40
"""Target title text rendered height as a fraction of TITLE_CREAM_H."""

TITLE_TRACKING: int = 4
"""Extra pixels between each character in the title (crude letter-spacing)."""

# System-font fallback candidates — same order as compose_numerals.py.
SYSTEM_FONT_CANDIDATES: list[str] = [
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Times New Roman.ttf",
    "/System/Library/Fonts/Times.ttc",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
]


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------


def _load_font(
    font_path: Optional[str],
    target_size: int,
) -> ImageFont.FreeTypeFont:
    """
    Load a TrueType font at *target_size* points.

    Resolution order:

    1. Caller-supplied *font_path*.
    2. :data:`SYSTEM_FONT_CANDIDATES` in order.
    3. Pillow's built-in bitmap font (warns to ``stderr``).
    """
    candidates: list[str] = []
    if font_path:
        candidates.append(font_path)
    candidates.extend(SYSTEM_FONT_CANDIDATES)

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=target_size)
            except Exception:
                continue

    print(
        "WARNING: No TrueType font found; falling back to Pillow bitmap font. "
        "Pass --font to specify a TTF/OTF file.",
        file=sys.stderr,
    )
    return ImageFont.load_default()


def _measure_text(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text: str,
) -> tuple[int, int]:
    """Return ``(width, height)`` of *text* rendered in *font* (single line)."""
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _tracked_text_width(
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text: str,
    tracking: int,
) -> int:
    """
    Return the total pixel width of *text* rendered with *tracking* extra pixels
    between characters.
    """
    if not text:
        return 0
    total = sum(font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text)
    total += tracking * (len(text) - 1)
    return total


def _find_font_size(
    font_path: Optional[str],
    text: str,
    target_height_px: int,
    max_width_px: int,
    search_min: int = 8,
    search_max: int = 200,
) -> tuple[ImageFont.FreeTypeFont, int, int]:
    """
    Binary-search for the largest font size whose rendered height is at most
    *target_height_px* and whose tracked width does not exceed *max_width_px*.

    Returns ``(font, point_size, rendered_height_px)``.
    """
    best_font = _load_font(font_path, search_min)
    best_size = search_min
    best_h = 0

    lo, hi = search_min, search_max
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        _, h = _measure_text(font, text)
        tracked_w = _tracked_text_width(font, text, TITLE_TRACKING)
        if h <= target_height_px and tracked_w <= max_width_px:
            best_font, best_size, best_h = font, mid, h
            lo = mid + 1
        else:
            hi = mid - 1

    return best_font, best_size, best_h


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _draw_text_tracked(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    center_x: int,
    top_y: int,
    tracking: int,
) -> None:
    """
    Render *text* in *font* horizontally centred at *center_x* with its
    top-of-bounding-box at *top_y*, applying *tracking* extra pixels between
    each character.

    Parameters
    ----------
    draw:
        Active :class:`~PIL.ImageDraw.ImageDraw` instance.
    text:
        The string to render.
    font:
        Loaded font object.
    fill:
        RGB colour tuple.
    center_x:
        Horizontal centre pixel of the text block.
    top_y:
        Vertical position of the top of the text bounding box.
    tracking:
        Extra pixels inserted between consecutive characters.
    """
    total_w = _tracked_text_width(font, text, tracking)
    x = center_x - total_w // 2

    for ch in text:
        bbox = font.getbbox(ch)
        ch_w = bbox[2] - bbox[0]
        draw.text((x - bbox[0], top_y - bbox[1]), ch, font=font, fill=fill)
        x += ch_w + tracking


def _draw_gold_frame(
    draw: ImageDraw.ImageDraw,
    canvas_w: int,
    canvas_h: int,
) -> None:
    """
    Draw the four gold border strips onto *draw*.

    Each strip is a filled rectangle inside the outer cream margin.  The
    strips overlap at the corners, which is fine for flat fills.

    Parameters
    ----------
    draw:
        Active :class:`~PIL.ImageDraw.ImageDraw` instance.
    canvas_w:
        Total canvas width in pixels.
    canvas_h:
        Total canvas height in pixels.
    """
    gold = GOLD_COLOR

    # Top strip.
    draw.rectangle(
        [OUTER_CREAM, OUTER_CREAM, canvas_w - OUTER_CREAM, OUTER_CREAM + GOLD_WIDTH],
        fill=gold,
    )
    # Bottom strip.
    draw.rectangle(
        [
            OUTER_CREAM,
            canvas_h - OUTER_CREAM - GOLD_WIDTH,
            canvas_w - OUTER_CREAM,
            canvas_h - OUTER_CREAM,
        ],
        fill=gold,
    )
    # Left strip.
    draw.rectangle(
        [OUTER_CREAM, OUTER_CREAM, OUTER_CREAM + GOLD_WIDTH, canvas_h - OUTER_CREAM],
        fill=gold,
    )
    # Right strip.
    draw.rectangle(
        [
            canvas_w - OUTER_CREAM - GOLD_WIDTH,
            OUTER_CREAM,
            canvas_w - OUTER_CREAM,
            canvas_h - OUTER_CREAM,
        ],
        fill=gold,
    )


def _scale_art(source: Image.Image) -> Image.Image:
    """
    Scale *source* to exactly :data:`INNER_W` pixels wide, preserving aspect
    ratio.  No cropping is performed; the full art height is retained.

    Parameters
    ----------
    source:
        The numeralled source image (any size, typically 700 × 1200).

    Returns
    -------
    Image.Image
        Scaled image at ``INNER_W`` × ``round(src_h * INNER_W / src_w)`` pixels.
    """
    src_w, src_h = source.size
    new_h = round(src_h * INNER_W / src_w)
    return source.resize((INNER_W, new_h), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Card metadata
# ---------------------------------------------------------------------------


def _load_card_data(data_path: str, card_id: str) -> dict:
    """
    Load and return the metadata dict for *card_id* from *data_path*.

    Raises
    ------
    KeyError
        If *card_id* is not present in the JSON.
    """
    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    cards = {c["id"]: c for c in data["cards"]}
    if card_id not in cards:
        raise KeyError(f"Card {card_id!r} not found in {data_path}")
    return cards[card_id]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compose(
    card_id: str,
    source_path: str,
    output_path: str,
    data_path: str,
    font_path: Optional[str] = None,
) -> None:
    """
    Composite the Ventnor frame and title panel onto *source_path* and save
    the result to *output_path*.

    The canvas grows around the full art — no art is cropped to accommodate
    the border.  The title panel is composited as an overlay on the bottom
    portion of the art.

    Parameters
    ----------
    card_id:
        Short card identifier matching the ``id`` field in *data_path*
        (e.g. ``"maj07"``).
    source_path:
        Path to the numeralled source PNG (from ``illustrations-numeralled/``).
    output_path:
        Destination PNG path (typically ``illustrations-framed/<id>.png``).
    data_path:
        Path to ``card-numerals.json``.
    font_path:
        Optional path to a TrueType/OpenType font file.  Falls back to system
        candidates and then Pillow's built-in font.
    """
    card = _load_card_data(data_path, card_id)
    title_text = card["name"].upper()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # 1. Scale art to fill INNER_W (full height retained — no cropping).
    with Image.open(source_path) as src:
        art = _scale_art(src.convert("RGB"))

    art_w, art_h = art.size  # art_w == INNER_W

    # 2. Derive canvas dimensions.
    #    Width is fixed (CANVAS_W).  Height grows from the art.
    canvas_h = 2 * BORDER + art_h
    canvas = Image.new("RGB", (CANVAS_W, canvas_h), CREAM_COLOR)
    draw = ImageDraw.Draw(canvas)

    # 3. Draw gold border (4 strips around the whole canvas).
    _draw_gold_frame(draw, CANVAS_W, canvas_h)

    # 4. Paste art inside the border.
    art_x = BORDER   # left edge of art inside the border
    art_y = BORDER   # top edge of art inside the border
    canvas.paste(art, (art_x, art_y))

    # 5. Overlay the title panel on the bottom of the art.
    #    The panel sits inside the gold border, covering the low-importance
    #    bottom zone of the art.
    title_divider_y = art_y + art_h - TITLE_PANEL_H
    title_cream_y = title_divider_y + TITLE_DIVIDER_H
    title_cream_bottom = art_y + art_h  # == canvas_h - BORDER

    # Gold divider rule at the top of the title overlay.
    draw.rectangle(
        [art_x, title_divider_y, art_x + art_w, title_divider_y + TITLE_DIVIDER_H],
        fill=GOLD_COLOR,
    )

    # Cream title background.
    draw.rectangle(
        [art_x, title_cream_y, art_x + art_w, title_cream_bottom],
        fill=CREAM_COLOR,
    )

    # 6. Render title text centred in the cream panel.
    target_text_h = int(TITLE_CREAM_H * TITLE_HEIGHT_FRAC)
    font, _, text_h = _find_font_size(
        font_path,
        title_text,
        target_height_px=target_text_h,
        max_width_px=INNER_W - 24,  # small horizontal inset
    )

    title_center_x = art_x + art_w // 2
    title_center_y = title_cream_y + TITLE_CREAM_H // 2
    text_top_y = title_center_y - text_h // 2

    _draw_text_tracked(
        draw=draw,
        text=title_text,
        font=font,
        fill=TITLE_TEXT_COLOR,
        center_x=title_center_x,
        top_y=text_top_y,
        tracking=TITLE_TRACKING,
    )

    canvas.save(output_path, optimize=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Add the Ventnor frame and title panel to a numeralled tarot card illustration."
        )
    )
    parser.add_argument(
        "--card",
        required=True,
        metavar="ID",
        help="Card identifier matching the 'id' field in the data file (e.g. maj07).",
    )
    parser.add_argument(
        "--source",
        required=True,
        metavar="PATH",
        help="Source numeralled PNG (from illustrations-numeralled/).",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="PATH",
        help="Destination PNG path.",
    )
    parser.add_argument(
        "--data",
        required=True,
        metavar="PATH",
        help="Path to card-numerals.json.",
    )
    parser.add_argument(
        "--font",
        default=None,
        metavar="PATH",
        help="Optional TrueType/OpenType font file.  Falls back to Times New Roman.",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    args = _build_arg_parser().parse_args()
    compose(
        card_id=args.card,
        source_path=args.source,
        output_path=args.output,
        data_path=args.data,
        font_path=args.font,
    )


if __name__ == "__main__":
    main()
