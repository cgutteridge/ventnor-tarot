"""
compose_numerals.py — overlay a Roman numeral onto a rectified tarot card.

Reads card metadata from card-numerals.json. If a card has no numeral
(Aces, courts) the source is copied unchanged. Otherwise the numeral is
composited at the top of the illustration in near-black with an optional
per-letterform glow that hugs the text edges and blends into the card art.

Usage
-----
    python3 scripts/compose_numerals.py \\
        --card maj07 \\
        --source illustrations-rectified/maj07.png \\
        --output illustrations-numeralled/maj07.png \\
        --data card-numerals.json \\
        [--font path/to/font.ttf]

The --font argument is optional; the script falls back to Times New Roman
from the macOS system fonts, then to Pillow's built-in bitmap font.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Vertical centre of the numeral as a fraction of the card height.
# The top ~10% is reserved as low-importance headroom; we aim for ~2.8%
# to match the cap-top position in the vtarot/wands02.png framed reference.
NUMERAL_Y_FRAC = 0.018

# Target rendered cap-height as a fraction of card height.
# ~4% gives visual weight comparable to wands02 while accommodating wider
# multi-character numerals (XVIII etc.) without dominating the composition.
NUMERAL_HEIGHT_FRAC = 0.040

# Gaussian blur radius for the per-letterform glow, in pixels, at the
# canonical 700 × 1200 resolution. Scaled proportionally for other sizes.
GLOW_BLUR_RADIUS_AT_700 = 11.0

# Number of glow compositing passes.  Two passes build a slightly richer halo
# without crossing into a visible blob behind the text.
GLOW_PASSES = 2

# System-font fallback paths tried in order.
SYSTEM_FONT_CANDIDATES: list[str] = [
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Times New Roman.ttf",
    "/System/Library/Fonts/Times.ttc",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert a ``#rrggbb`` hex string to an RGBA tuple."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Expected a 6-digit hex color, got: {hex_color!r}")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r, g, b, alpha


def _load_font(font_path: Optional[str], target_size: int) -> ImageFont.FreeTypeFont:
    """
    Load a TrueType font at *target_size* points.

    Resolution order:
    1. Caller-supplied *font_path* (``--font`` argument).
    2. System candidates in :data:`SYSTEM_FONT_CANDIDATES`.
    3. Pillow's built-in bitmap font (poor quality; warns to stderr).
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


def _measure_text(font: ImageFont.FreeTypeFont | ImageFont.ImageFont, text: str) -> tuple[int, int]:
    """Return (width, height) of *text* rendered in *font*."""
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _find_font_size(
    font_path: Optional[str],
    text: str,
    target_height_px: int,
    search_min: int = 8,
    search_max: int = 200,
) -> tuple[ImageFont.FreeTypeFont, int]:
    """
    Binary-search for the largest font size whose rendered cap-height is at
    most *target_height_px*.  Returns ``(font, size)``.
    """
    best_font = _load_font(font_path, search_min)
    best_size = search_min

    lo, hi = search_min, search_max
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        _, h = _measure_text(font, text)
        if h <= target_height_px:
            best_font, best_size = font, mid
            lo = mid + 1
        else:
            hi = mid - 1

    return best_font, best_size


# ---------------------------------------------------------------------------
# Core compositing
# ---------------------------------------------------------------------------


def _composite_numeral(
    source: Image.Image,
    numeral: str,
    numeral_color: str,
    glow_color: str,
    needs_glow: bool,
    font_path: Optional[str],
) -> Image.Image:
    """
    Return a copy of *source* with the numeral composited at the top.

    Glow technique (when *needs_glow* is True):
        1. Render the numeral in white on a transparent layer.
        2. Gaussian-blur that layer so the glow radiates from the letterforms.
        3. Tint the blurred layer with *glow_color*.
        4. Composite in order: source → glow → sharp numeral.

    The result is an RGB image (no alpha channel) matching the input mode.
    """
    w, h = source.size
    target_height_px = int(h * NUMERAL_HEIGHT_FRAC)
    font, _ = _find_font_size(font_path, numeral, target_height_px)

    text_w, text_h = _measure_text(font, numeral)
    # Horizontal centre; vertical: align the cap top to NUMERAL_Y_FRAC
    bbox = font.getbbox(numeral)
    ascent_offset = bbox[1]  # top of bounding box relative to drawing origin
    x = (w - text_w) // 2 - bbox[0]
    y = int(h * NUMERAL_Y_FRAC) - ascent_offset

    # Work in RGBA so we can alpha-composite layers cleanly.
    base = source.convert("RGBA")

    if needs_glow:
        blur_radius = GLOW_BLUR_RADIUS_AT_700 * (w / 700.0)
        glow_rgba = _hex_to_rgba(glow_color)

        for _ in range(GLOW_PASSES):
            # Render numeral in solid white on a transparent layer.
            glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(glow_layer)
            draw.text((x, y), numeral, font=font, fill=(255, 255, 255, 255))

            # Blur outward from letterforms.
            glow_layer = glow_layer.filter(
                ImageFilter.GaussianBlur(radius=blur_radius)
            )

            # Tint the glow with glow_color: replace RGB while keeping the
            # blurred alpha channel, which encodes the halo shape.
            r_ch, g_ch, b_ch, a_ch = glow_layer.split()
            solid = Image.new("RGBA", (w, h), glow_rgba[:3] + (0,))
            tinted = Image.merge("RGBA", [
                solid.split()[0],
                solid.split()[1],
                solid.split()[2],
                a_ch,
            ])

            base = Image.alpha_composite(base, tinted)

    # Draw the sharp numeral on top.
    draw = ImageDraw.Draw(base)
    draw.text((x, y), numeral, font=font, fill=_hex_to_rgba(numeral_color))

    # Return in the same mode as the input.
    return base.convert(source.mode)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _load_card_data(data_path: str, card_id: str) -> dict:
    """Load and return the metadata dict for *card_id* from *data_path*."""
    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    cards = {c["id"]: c for c in data["cards"]}
    if card_id not in cards:
        raise KeyError(f"Card {card_id!r} not found in {data_path}")
    return {
        "card": cards[card_id],
        "numeral_color": data.get("numeralColor", "#1c1814"),
        "glow_color": data.get("glowColor", "#fffdf5"),
    }


def compose(
    card_id: str,
    source_path: str,
    output_path: str,
    data_path: str,
    font_path: Optional[str] = None,
) -> None:
    """
    Composite the numeral for *card_id* onto *source_path* and save the
    result to *output_path*.

    If the card has no numeral (Ace or court) the source is copied unchanged.
    Creates the output directory if it does not exist.

    Parameters
    ----------
    card_id:
        Short card identifier matching the ``id`` field in *data_path*
        (e.g. ``"maj07"``).
    source_path:
        Path to the rectified source PNG.
    output_path:
        Destination PNG path.
    data_path:
        Path to ``card-numerals.json``.
    font_path:
        Optional path to a TrueType or OpenType font file.  If not supplied,
        falls back to system candidates and then Pillow's built-in font.
    """
    meta = _load_card_data(data_path, card_id)
    card = meta["card"]
    numeral: Optional[str] = card.get("numeral")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if numeral is None:
        # Use shutil.copy (not copy2) so the output gets the current mtime.
        # This ensures Make treats it as up-to-date on subsequent runs unless
        # a prerequisite genuinely changes.
        shutil.copy(source_path, output_path)
        return

    with Image.open(source_path) as img:
        result = _composite_numeral(
            source=img,
            numeral=numeral,
            numeral_color=meta["numeral_color"],
            glow_color=meta["glow_color"],
            needs_glow=card.get("needsGlow", False),
            font_path=font_path,
        )
        result.save(output_path)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Overlay a Roman numeral onto a rectified tarot card illustration."
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
        help="Source rectified PNG.",
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
        help="Optional TrueType/OpenType font file path.",
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
