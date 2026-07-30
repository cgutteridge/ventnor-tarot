#!/usr/bin/env python3
"""Crop Ventnor Tarot illustrations from a reviewed bounds manifest.

Reads ``tmp/illustration-bounds.json`` and writes frame-free crops to
``illustrations-raw/`` using ImageMagick.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the Ventnor Tarot project root (four levels above this script)."""
    return Path(__file__).resolve().parents[4]


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate the illustration-bounds manifest.

    Args:
        path: Path to ``illustration-bounds.json``.

    Returns:
        Parsed manifest dictionary.

    Raises:
        SystemExit: If the manifest is missing or malformed.
    """
    if not path.is_file():
        raise SystemExit(
            f"Manifest not found: {path}\n"
            "Run detect_illustration_bounds.py first, then review the bounds."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if "cards" not in data or not isinstance(data["cards"], list):
        raise SystemExit(f"Manifest missing cards list: {path}")
    return data


def crop_card(
    source: Path,
    dest: Path,
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    """Crop one card illustration with ImageMagick.

    Args:
        source: Finished card image path.
        dest: Output crop path.
        left: Inclusive left edge in source pixels.
        top: Inclusive top edge in source pixels.
        width: Crop width in pixels.
        height: Crop height in pixels.
    """
    geom = f"{width}x{height}+{left}+{top}"
    subprocess.check_call(
        ["magick", str(source), "-crop", geom, "+repage", str(dest)]
    )


def apply_crops(
    manifest: dict[str, Any],
    cards_dir: Path,
    output_dir: Path,
) -> tuple[int, list[str]]:
    """Apply every crop described in the manifest.

    Args:
        manifest: Loaded bounds manifest.
        cards_dir: Directory containing source card PNGs.
        output_dir: Destination directory for illustration crops.

    Returns:
        ``(success_count, error_messages)``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    errors: list[str] = []

    for card in manifest["cards"]:
        name = card.get("file")
        if not name:
            errors.append("card entry missing file")
            continue
        try:
            left = int(card["left"])
            top = int(card["top"])
            right = int(card["right"])
            bottom = int(card["bottom"])
            width = int(card.get("width", right - left))
            height = int(card.get("height", bottom - top))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{name}: invalid bounds ({exc})")
            continue

        if width != right - left or height != bottom - top:
            # Prefer explicit edges when width/height drift after manual edits.
            width = right - left
            height = bottom - top

        if width <= 0 or height <= 0:
            errors.append(f"{name}: non-positive crop size {width}x{height}")
            continue

        source = cards_dir / name
        if not source.is_file():
            errors.append(f"{name}: source missing at {source}")
            continue

        dest = output_dir / name
        try:
            crop_card(source, dest, left, top, width, height)
            flag = " flagged" if card.get("flagged") else ""
            panel = " panel" if card.get("numeral_panel") else ""
            print(f"{name}: {width}x{height} -> {dest.as_posix()}{panel}{flag}")
            ok += 1
        except subprocess.CalledProcessError as exc:
            errors.append(f"{name}: magick failed ({exc})")
        except OSError as exc:
            errors.append(f"{name}: {exc}")

    return ok, errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for illustration cropping."""
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Crop Ventnor Tarot illustrations from a bounds manifest."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=root / "tmp" / "illustration-bounds.json",
        help="Reviewed bounds manifest (default: <project>/tmp/illustration-bounds.json)",
    )
    parser.add_argument(
        "--cards-dir",
        type=Path,
        default=root / "vtarot",
        help="Directory of finished card PNGs (default: <project>/vtarot)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "illustrations-raw",
        help="Output directory (default: <project>/illustrations-raw)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Crop illustrations from the reviewed manifest into illustrations-raw/."""
    args = parse_args(argv)
    manifest = load_manifest(args.manifest)
    ok, errors = apply_crops(manifest, args.cards_dir, args.output_dir)
    print(f"Cropped {ok} card(s) into {args.output_dir}")
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
