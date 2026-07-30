#!/usr/bin/env python3
"""Slice an approved zoom-level master image into standard XYZ tiles.

Reads ``map/manifest.json`` and, for each zoom, crops the corresponding
master image (``map/masters/z{zoom}.png``, or ``--source-dir`` override) into
256x256 tiles named by absolute tile coordinates, written to
``vtarot/map-tiles/{z}/{x}/{y}.png``.

The master must exactly match the manifest's pixel_width/pixel_height for
that zoom — that guarantee is what makes the resulting tiles seamless.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

TILE_SIZE = 256


def project_root() -> Path:
    """Return the Ventnor Tarot project root (two levels above this script)."""
    return Path(__file__).resolve().parents[2]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing manifest: {path}. Run tile_grid.py first.")
    return json.loads(path.read_text())


def image_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["identify", "-format", "%w %h", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    w, h = out.split()
    return int(w), int(h)


def slice_zoom(entry: dict[str, Any], master_path: Path, out_root: Path) -> int:
    zoom = entry["zoom"]
    expected = (entry["pixel_width"], entry["pixel_height"])
    actual = image_size(master_path)
    if actual != expected:
        raise SystemExit(
            f"z{zoom}: {master_path} is {actual[0]}x{actual[1]}px, "
            f"expected {expected[0]}x{expected[1]}px per manifest. "
            "Resize/regenerate the master before slicing."
        )

    count = 0
    for row, y in enumerate(range(entry["tile_y_min"], entry["tile_y_max"] + 1)):
        for col, x in enumerate(range(entry["tile_x_min"], entry["tile_x_max"] + 1)):
            out_dir = out_root / str(zoom) / str(x)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{y}.png"
            subprocess.run(
                [
                    "convert",
                    str(master_path),
                    "-crop",
                    f"{TILE_SIZE}x{TILE_SIZE}+{col * TILE_SIZE}+{row * TILE_SIZE}",
                    "+repage",
                    str(out_path),
                ],
                check=True,
            )
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Directory containing z{zoom}.png masters (default: map/masters)",
    )
    parser.add_argument("--zooms", type=int, nargs="+", default=None, help="Subset of zooms to slice")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output tile root (default: vtarot/map-tiles)",
    )
    args = parser.parse_args()

    root = project_root()
    manifest_path = args.manifest or (root / "map" / "manifest.json")
    manifest = load_manifest(manifest_path)

    source_dir = args.source_dir or (root / "map" / "masters")
    out_root = args.out_dir or (root / "vtarot" / "map-tiles")

    zoom_keys = [str(z) for z in args.zooms] if args.zooms else list(manifest["zooms"].keys())

    for zoom_key in zoom_keys:
        entry = manifest["zooms"][zoom_key]
        master_path = source_dir / f"z{zoom_key}.png"
        if not master_path.exists():
            raise SystemExit(f"z{zoom_key}: missing master {master_path}")
        count = slice_zoom(entry, master_path, out_root)
        print(f"z{zoom_key}: wrote {count} tiles to {out_root / zoom_key}")


if __name__ == "__main__":
    main()
