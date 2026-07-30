#!/usr/bin/env python3
"""Detect illustration crop bounds for Ventnor Tarot cards.

Scans each finished card in ``vtarot/`` for the non-frame illustration rectangle,
optionally excluding cream Roman-numeral panels, and writes a reviewable manifest
to ``tmp/illustration-bounds.json``.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

REFERENCE_CARD = "wands02.png"
NUMERAL_PANEL_MIN_ROWS = 12
SIZE_DEVIATION_FLAG = 0.12
MARGIN_DEVIATION_FLAG = 40


def project_root() -> Path:
    """Return the Ventnor Tarot project root (four levels above this script)."""
    return Path(__file__).resolve().parents[4]


def load_rgb(path: Path) -> tuple[int, int, bytes]:
    """Load an image as 8-bit interleaved RGB bytes via ImageMagick.

    Args:
        path: Path to a PNG (or other ImageMagick-readable) image.

    Returns:
        ``(width, height, rgb_bytes)`` where ``len(rgb_bytes) == width * height * 3``.
    """
    raw = subprocess.check_output(["magick", str(path), "-depth", "8", "rgb:-"])
    size = subprocess.check_output(
        ["magick", "identify", "-format", "%w %h", str(path)], text=True
    ).split()
    width, height = int(size[0]), int(size[1])
    expected = width * height * 3
    if len(raw) != expected:
        raise RuntimeError(
            f"{path.name}: expected {expected} RGB bytes, got {len(raw)}"
        )
    return width, height, raw


def pixel(raw: bytes, width: int, x: int, y: int) -> tuple[int, int, int]:
    """Return the RGB triple at ``(x, y)``."""
    i = (y * width + x) * 3
    return raw[i], raw[i + 1], raw[i + 2]


def is_cream(rgb: tuple[int, int, int]) -> bool:
    """Return True if the sample matches the aged-paper cream frame/panel."""
    r, g, b = rgb
    return (
        min(r, g, b) >= 140
        and abs(r - g) <= 50
        and abs(g - b) <= 55
        and abs(r - b) <= 65
        and (r + g + b) / 3 >= 165
    )


def is_gold(rgb: tuple[int, int, int]) -> bool:
    """Return True if the sample matches the narrow gold inner border."""
    r, g, b = rgb
    return (
        r > 110
        and g > 70
        and b < 150
        and (r - b) > 30
        and (g - b) > 10
        and r >= g - 20
    )


def is_frame(rgb: tuple[int, int, int]) -> bool:
    """Return True if the sample is cream frame/panel or gold border."""
    return is_cream(rgb) or is_gold(rgb)


def column_fraction(
    raw: bytes,
    width: int,
    height: int,
    x: int,
    y0: int,
    y1: int,
    predicate,
    step: int = 2,
) -> float:
    """Fraction of sampled pixels in a vertical strip matching ``predicate``."""
    samples = 0
    matched = 0
    for y in range(y0, y1, step):
        samples += 1
        if predicate(pixel(raw, width, x, y)):
            matched += 1
    return matched / samples if samples else 0.0


def row_fraction(
    raw: bytes,
    width: int,
    y: int,
    x0: int,
    x1: int,
    predicate,
    step: int = 2,
) -> float:
    """Fraction of sampled pixels in a horizontal strip matching ``predicate``."""
    samples = 0
    matched = 0
    for x in range(x0, x1, step):
        samples += 1
        if predicate(pixel(raw, width, x, y)):
            matched += 1
    return matched / samples if samples else 0.0


def column_frame_fraction(
    raw: bytes, width: int, height: int, x: int, y0: int, y1: int, step: int = 2
) -> float:
    """Fraction of sampled pixels in a vertical strip classified as frame."""
    return column_fraction(raw, width, height, x, y0, y1, is_frame, step)


def column_cream_fraction(
    raw: bytes, width: int, height: int, x: int, y0: int, y1: int, step: int = 2
) -> float:
    """Fraction of sampled pixels in a vertical strip classified as cream."""
    return column_fraction(raw, width, height, x, y0, y1, is_cream, step)


def row_frame_fraction(
    raw: bytes, width: int, y: int, x0: int, x1: int, step: int = 2
) -> float:
    """Fraction of sampled pixels in a horizontal strip classified as frame."""
    return row_fraction(raw, width, y, x0, x1, is_frame, step)


def row_cream_fraction(
    raw: bytes, width: int, y: int, x0: int, x1: int, step: int = 2
) -> float:
    """Fraction of sampled pixels in a horizontal strip classified as cream."""
    return row_fraction(raw, width, y, x0, x1, is_cream, step)


def row_gold_fraction(
    raw: bytes, width: int, y: int, x0: int, x1: int, step: int = 2
) -> float:
    """Fraction of sampled pixels in a horizontal strip classified as gold."""
    return row_fraction(raw, width, y, x0, x1, is_gold, step)


def column_gold_fraction(
    raw: bytes, width: int, height: int, x: int, y0: int, y1: int, step: int = 2
) -> float:
    """Fraction of sampled pixels in a vertical strip classified as gold."""
    return column_fraction(raw, width, height, x, y0, y1, is_gold, step)


def find_side_after_gold(
    raw: bytes,
    width: int,
    height: int,
    reverse: bool,
) -> int:
    """Locate left/right illustration edge just inside the gold border.

    Searches the expected margin band for a gold column that sits inside a cream
    outer frame (ignoring false gold on dark rounded corners). Falls back to
    cream-frame traversal when no clear gold line is found.

    Args:
        raw: Interleaved RGB bytes.
        width: Image width.
        height: Image height.
        reverse: False for left edge, True for right edge.

    Returns:
        Inclusive left x, or exclusive right x.
    """
    y0, y1 = height // 4, (3 * height) // 4
    inner = max(18, int(width * 0.02))
    outer = min(max(inner + 8, int(width * 0.095)), width // 4)

    if reverse:
        xs = range(width - inner - 1, width - outer - 1, -1)
    else:
        xs = range(inner, outer)

    best_x = None
    for x in xs:
        g = column_gold_fraction(raw, width, height, x, y0, y1)
        if g < 0.50:
            continue
        # Require cream paper outside this gold column.
        if reverse:
            outside_xs = list(range(x + 3, min(width - 2, x + 18)))
        else:
            outside_xs = list(range(max(1, x - 18), max(1, x - 2)))
        if not outside_xs:
            continue
        cream_out = sum(
            column_cream_fraction(raw, width, height, ox, y0, y1) for ox in outside_xs
        ) / len(outside_xs)
        if cream_out < 0.40:
            continue
        # First qualifying gold column from the outside is the frame border.
        best_x = x
        break

    if best_x is not None:
        x = best_x
        if reverse:
            while (
                x - 1 >= width - outer
                and best_x - (x - 1) < 12
                and column_gold_fraction(raw, width, height, x - 1, y0, y1) >= 0.55
            ):
                x -= 1
            return x
        while (
            x + 1 < outer
            and (x + 1) - best_x < 12
            and column_gold_fraction(raw, width, height, x + 1, y0, y1) >= 0.55
        ):
            x += 1
        return x + 1

    # Fallback: cream/frame traversal (ignore dark outer corners).
    band = outer
    xs = range(width - 1, width - 1 - band, -1) if reverse else range(0, band)
    state = "outside"
    cream_run = 0
    for x in xs:
        cream_f = column_cream_fraction(raw, width, height, x, y0, y1)
        frame_f = column_frame_fraction(raw, width, height, x, y0, y1)
        if state == "outside":
            if cream_f >= 0.45 or frame_f >= 0.55:
                cream_run += 1
                if cream_run >= 2:
                    state = "in_frame"
            else:
                cream_run = 0
            continue
        if frame_f < 0.40:
            return x if not reverse else x + 1
    return 0 if not reverse else width


def find_top_edge_and_panel(
    raw: bytes, width: int, height: int
) -> tuple[int, int, bool]:
    """Find illustration top edge, skipping a cream numeral panel when present.

    Uses the top gold border as the primary anchor. After that border, a sustained
    cream band is treated as a numeral panel and excluded.

    Args:
        raw: Interleaved RGB bytes.
        width: Image width.
        height: Image height.

    Returns:
        ``(top, cream_band_rows, numeral_panel)``.
    """
    x0, x1 = width // 4, (3 * width) // 4
    search_end = min(120, height // 3)

    gold_start = None
    for y in range(8, search_end):
        if row_gold_fraction(raw, width, y, x0, x1) < 0.35:
            continue
        # Prefer gold that sits below cream outer margin.
        cream_above = 0.0
        n = 0
        for ay in range(max(0, y - 16), max(0, y - 2)):
            cream_above += row_cream_fraction(raw, width, ay, x0, x1)
            n += 1
        if n and cream_above / n < 0.35:
            continue
        gold_start = y
        break

    if gold_start is None:
        state = "outside"
        cream_run = 0
        for y in range(0, search_end):
            cream_f = row_cream_fraction(raw, width, y, x0, x1)
            frame_f = row_frame_fraction(raw, width, y, x0, x1)
            if state == "outside":
                if cream_f >= 0.45 or frame_f >= 0.55:
                    cream_run += 1
                    if cream_run >= 2:
                        state = "in_frame"
                else:
                    cream_run = 0
                continue
            if frame_f < 0.40:
                return y, 0, False
        return 0, 0, False

    y = gold_start
    while y < search_end and row_gold_fraction(raw, width, y, x0, x1) >= 0.25:
        y += 1

    band = 0
    band_start = y
    while y < min(band_start + 160, height // 2) and row_cream_fraction(
        raw, width, y, x0, x1
    ) > 0.55:
        band += 1
        y += 1

    if band >= NUMERAL_PANEL_MIN_ROWS:
        while y < min(y + 24, height // 2) and row_gold_fraction(
            raw, width, y, x0, x1
        ) > 0.28:
            y += 1
        while y < min(y + 8, height // 2) and row_frame_fraction(
            raw, width, y, x0, x1
        ) > 0.50:
            y += 1
        return y, band, True

    return y, band, False


def row_is_title_panel(
    raw: bytes, width: int, y: int, x0: int, x1: int, step: int = 2
) -> bool:
    """Return True if a row looks like the bottom title panel.

    Title rows are mostly cream paper plus dark lettering (and optional gold).
    Dark illustration content alone must not qualify.
    """
    cream = 0
    dark = 0
    gold = 0
    samples = 0
    for x in range(x0, x1, step):
        samples += 1
        rgb = pixel(raw, width, x, y)
        if is_cream(rgb):
            cream += 1
        elif is_gold(rgb):
            gold += 1
        elif max(rgb) <= 90:
            dark += 1
    if not samples:
        return False
    cream_f = cream / samples
    panel_f = (cream + dark + gold) / samples
    return cream_f >= 0.28 and panel_f >= 0.55


def find_bottom_edge(raw: bytes, width: int, height: int) -> int:
    """Find exclusive bottom edge at the title-panel gold divider.

    Searches the lower card band for cream title-panel rows (including dark
    title glyphs), takes the uppermost such row, then walks up through any gold
    divider to the illustration.

    Args:
        raw: Interleaved RGB bytes.
        width: Image width.
        height: Image height.

    Returns:
        Exclusive bottom y coordinate.
    """
    x0, x1 = width // 4, (3 * width) // 4
    lo = int(height * 0.84)
    hi = height - 6

    title_ys = [
        y for y in range(hi, lo - 1, -1) if row_is_title_panel(raw, width, y, x0, x1)
    ]
    if not title_ys:
        return int(height * 0.89)

    title_top = min(title_ys)

    # Only a thin gold rule sits above the title; do not chase gold tones in art.
    y = title_top - 1
    gold_top = title_top
    min_y = max(int(height * 0.70), title_top - 28)
    while y >= min_y and row_gold_fraction(raw, width, y, x0, x1) >= 0.22:
        gold_top = y
        y -= 1
    return gold_top


def detect_bounds(path: Path) -> dict[str, Any]:
    """Detect the illustration crop rectangle for one card image.

    Args:
        path: Path to a finished card PNG.

    Returns:
        Bounds dictionary with geometry, numeral-panel metadata, and notes.
    """
    width, height, raw = load_rgb(path)
    left = find_side_after_gold(raw, width, height, reverse=False)
    right = find_side_after_gold(raw, width, height, reverse=True)
    top, cream_band, numeral_panel = find_top_edge_and_panel(raw, width, height)
    bottom = find_bottom_edge(raw, width, height)

    # If one side failed open, mirror the successful opposite margin.
    if left <= 2 and width - right > 20:
        left = width - right
    if width - right <= 2 and left > 20:
        right = width - left

    if right <= left + 10 or bottom <= top + 10:
        raise RuntimeError(
            f"{path.name}: invalid crop box ({left},{top},{right},{bottom})"
        )

    notes: list[str] = []
    if numeral_panel:
        notes.append(f"cream numeral panel ~{cream_band}px excluded")

    return {
        "file": path.name,
        "source_width": width,
        "source_height": height,
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
        "numeral_panel": numeral_panel,
        "cream_band_rows": cream_band,
        "flagged": False,
        "notes": notes,
    }


def median_int(values: list[int]) -> int:
    """Return the integer median of ``values``."""
    return int(statistics.median(values))


def apply_flags(
    cards: list[dict[str, Any]], reference: dict[str, Any] | None
) -> None:
    """Flag cards whose crop geometry diverges from the reference or deck median.

    Args:
        cards: Mutable list of per-card bound dictionaries.
        reference: Bounds for ``wands02.png`` when present; otherwise ``None``.
    """
    widths = [c["width"] for c in cards]
    heights = [c["height"] for c in cards]
    lefts = [c["left"] for c in cards]
    tops = [c["top"] for c in cards]
    rights = [c["source_width"] - c["right"] for c in cards]
    bottoms = [c["source_height"] - c["bottom"] for c in cards]

    med_w = median_int(widths)
    med_h = median_int(heights)
    med_l = median_int(lefts)
    med_t = median_int(tops)
    med_r = median_int(rights)
    med_b = median_int(bottoms)

    for card in cards:
        reasons: list[str] = []
        if abs(card["width"] - med_w) > med_w * SIZE_DEVIATION_FLAG:
            reasons.append(f"width {card['width']} vs median {med_w}")
        if abs(card["height"] - med_h) > med_h * SIZE_DEVIATION_FLAG:
            reasons.append(f"height {card['height']} vs median {med_h}")
        if abs(card["left"] - med_l) > MARGIN_DEVIATION_FLAG:
            reasons.append(f"left margin {card['left']} vs median {med_l}")
        if abs(card["top"] - med_t) > MARGIN_DEVIATION_FLAG:
            reasons.append(f"top margin {card['top']} vs median {med_t}")
        right_m = card["source_width"] - card["right"]
        bottom_m = card["source_height"] - card["bottom"]
        if abs(right_m - med_r) > MARGIN_DEVIATION_FLAG:
            reasons.append(f"right margin {right_m} vs median {med_r}")
        if abs(bottom_m - med_b) > MARGIN_DEVIATION_FLAG:
            reasons.append(f"bottom margin {bottom_m} vs median {med_b}")

        if reference is not None and card["file"] != REFERENCE_CARD:
            if abs(card["width"] - reference["width"]) > reference["width"] * 0.12:
                reasons.append(
                    f"width far from {REFERENCE_CARD} ({reference['width']})"
                )
            if abs(card["height"] - reference["height"]) > reference["height"] * 0.12:
                reasons.append(
                    f"height far from {REFERENCE_CARD} ({reference['height']})"
                )

        if card["numeral_panel"]:
            reasons.append("numeral panel detected")

        if reasons:
            card["flagged"] = True
            for reason in reasons:
                if reason not in card["notes"]:
                    card["notes"].append(reason)


def write_preview(
    source: Path, bounds: dict[str, Any], preview_dir: Path
) -> None:
    """Write a cropped preview PNG for visual review.

    Args:
        source: Original card path.
        bounds: Detected bounds for that card.
        preview_dir: Directory for preview images.
    """
    preview_dir.mkdir(parents=True, exist_ok=True)
    out = preview_dir / bounds["file"]
    geom = f"{bounds['width']}x{bounds['height']}+{bounds['left']}+{bounds['top']}"
    subprocess.check_call(
        ["magick", str(source), "-crop", geom, "+repage", str(out)]
    )


def detect_all(
    cards_dir: Path,
    manifest_path: Path,
    preview_dir: Path | None,
    write_previews: bool,
) -> dict[str, Any]:
    """Detect bounds for every PNG in ``cards_dir`` and write the manifest.

    Args:
        cards_dir: Directory containing finished card images.
        manifest_path: Output JSON path.
        preview_dir: Optional preview output directory.
        write_previews: When True, write cropped previews.

    Returns:
        The manifest dictionary that was written.
    """
    paths = sorted(cards_dir.glob("*.png"))
    if not paths:
        raise SystemExit(f"No PNG files found in {cards_dir}")

    cards: list[dict[str, Any]] = []
    errors: list[str] = []
    for path in paths:
        try:
            bounds = detect_bounds(path)
            cards.append(bounds)
            if write_previews and preview_dir is not None:
                write_preview(path, bounds, preview_dir)
            panel = " panel" if bounds["numeral_panel"] else ""
            print(
                f"{path.name}: "
                f"({bounds['left']},{bounds['top']})-"
                f"({bounds['right']},{bounds['bottom']}) "
                f"{bounds['width']}x{bounds['height']}{panel}"
            )
        except Exception as exc:  # noqa: BLE001 - collect and continue batch
            errors.append(f"{path.name}: {exc}")
            print(f"{path.name}: ERROR {exc}", file=sys.stderr)

    reference = next((c for c in cards if c["file"] == REFERENCE_CARD), None)
    apply_flags(cards, reference)

    manifest = {
        "version": 1,
        "source_dir": str(cards_dir.as_posix()),
        "reference_card": REFERENCE_CARD,
        "card_count": len(cards),
        "flagged_count": sum(1 for c in cards if c["flagged"]),
        "errors": errors,
        "cards": cards,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {manifest_path} ({manifest['card_count']} cards, "
        f"{manifest['flagged_count']} flagged)"
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for illustration-bound detection."""
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Detect Ventnor Tarot illustration crop bounds."
    )
    parser.add_argument(
        "--cards-dir",
        type=Path,
        default=root / "vtarot",
        help="Directory of finished card PNGs (default: <project>/vtarot)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "tmp" / "illustration-bounds.json",
        help="Output manifest path (default: <project>/tmp/illustration-bounds.json)",
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        default=root / "tmp" / "illustration-crop-previews",
        help="Directory for optional crop previews",
    )
    parser.add_argument(
        "--no-previews",
        action="store_true",
        help="Skip writing crop preview images",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run illustration-bound detection and write the review manifest."""
    args = parse_args(argv)
    detect_all(
        cards_dir=args.cards_dir,
        manifest_path=args.manifest,
        preview_dir=None if args.no_previews else args.preview_dir,
        write_previews=not args.no_previews,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
