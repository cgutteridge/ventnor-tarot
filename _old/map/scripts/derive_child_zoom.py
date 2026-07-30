#!/usr/bin/env python3
"""Derive a zoom master from its parent by 2x upscale + crop.

The manifest's tile-aligned zoom levels nest exactly: zoom z+1's tile range
is always zoom z's tile range doubled, then trimmed by a whole tile on one
or more edges. That means a child zoom's canvas is pixel-identical to its
parent canvas upscaled 2x and cropped to the child's tile-aligned window --
no separate AI generation, no seams, no joins. Only the parent (the widest
zoom actually painted from scratch) needs original art; every tighter zoom
is derived deterministically from it.

Usage:
    python3 map/scripts/derive_child_zoom.py --parent 15 --child 16
    python3 map/scripts/derive_child_zoom.py --parent 16 --child 17
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing manifest: {path}. Run tile_grid.py first.")
    return json.loads(path.read_text())


def crop_offset(parent: dict[str, Any], child: dict[str, Any]) -> tuple[int, int]:
    """Pixel offset of the child window inside the parent canvas upscaled 2x."""
    left = (child["tile_x_min"] - 2 * parent["tile_x_min"]) * 256
    top = (child["tile_y_min"] - 2 * parent["tile_y_min"]) * 256
    if left < 0 or top < 0:
        raise SystemExit(
            "Child zoom is not nested inside parent zoom's tile range -- "
            "re-check the manifest (bbox may have changed between zooms)."
        )
    return left, top


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=int, required=True, help="Parent zoom level (e.g. 15)")
    parser.add_argument("--child", type=int, required=True, help="Child zoom level (e.g. 16)")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Directory containing the approved parent master z{parent}.png (default: map/masters)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory to write the derived child draft (default: map/tmp)",
    )
    args = parser.parse_args()

    root = project_root()
    manifest_path = args.manifest or (root / "map" / "manifest.json")
    manifest = load_manifest(manifest_path)

    parent = manifest["zooms"][str(args.parent)]
    child = manifest["zooms"][str(args.child)]

    source_dir = args.source_dir or (root / "map" / "masters")
    out_dir = args.out_dir or (root / "map" / "tmp")
    out_dir.mkdir(parents=True, exist_ok=True)

    parent_path = source_dir / f"z{args.parent}.png"
    if not parent_path.exists():
        raise SystemExit(f"Missing approved parent master: {parent_path}")

    left, top = crop_offset(parent, child)
    upscaled_w = parent["pixel_width"] * 2
    upscaled_h = parent["pixel_height"] * 2

    if left + child["pixel_width"] > upscaled_w or top + child["pixel_height"] > upscaled_h:
        raise SystemExit(
            f"Child window ({left},{top})+{child['pixel_width']}x{child['pixel_height']} "
            f"exceeds the 2x-upscaled parent canvas ({upscaled_w}x{upscaled_h})."
        )

    out_path = out_dir / f"z{args.child}-draft-from-z{args.parent}.png"
    subprocess.run(
        [
            "convert",
            str(parent_path),
            "-filter", "Mitchell",
            "-resize", f"{upscaled_w}x{upscaled_h}!",
            "-crop", f"{child['pixel_width']}x{child['pixel_height']}+{left}+{top}",
            "+repage",
            str(out_path),
        ],
        check=True,
    )
    print(
        f"z{args.child}: derived from z{args.parent} "
        f"(upscale 2x -> crop +{left}+{top} -> {child['pixel_width']}x{child['pixel_height']}) "
        f"-> {out_path}"
    )


if __name__ == "__main__":
    main()
