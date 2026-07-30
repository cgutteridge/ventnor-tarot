#!/usr/bin/env python3
"""Stitch real OSM raster tiles into one reference image per zoom level.

Reads ``map/manifest.json`` (see ``tile_grid.py``) and, for each zoom, downloads
the covering standard OpenStreetMap tiles and stitches them into a single
``map/reference/z{zoom}.png`` matching the manifest's exact pixel canvas.

This reference image is an internal painting guide only (accurate coastline,
roads, buildings) and is never published — it exists so a painted master can
be laid out precisely, not to be shipped itself. Respects OSM's tile usage
policy: a courteous User-Agent, no parallel hammering, and this project's
modest one-time tile counts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "VentnorTarotMapReference/1.0 (personal art project; one-time tile fetch)"
TILE_SERVER = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
REQUEST_DELAY_SECONDS = 0.2


def project_root() -> Path:
    """Return the Ventnor Tarot project root (two levels above this script)."""
    return Path(__file__).resolve().parents[2]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing manifest: {path}. Run tile_grid.py first.")
    return json.loads(path.read_text())


def fetch_tile(z: int, x: int, y: int, dest: Path) -> None:
    if dest.exists():
        return
    url = TILE_SERVER.format(z=z, x=x, y=y)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        dest.write_bytes(resp.read())
    time.sleep(REQUEST_DELAY_SECONDS)


def stitch_zoom(entry: dict[str, Any], raw_dir: Path, out_path: Path) -> None:
    zoom = entry["zoom"]
    x_min, x_max = entry["tile_x_min"], entry["tile_x_max"]
    y_min, y_max = entry["tile_y_min"], entry["tile_y_max"]
    tiles_wide = entry["tiles_wide"]

    raw_dir.mkdir(parents=True, exist_ok=True)

    tile_paths: list[Path] = []
    for y in range(y_min, y_max + 1):
        for x in range(x_min, x_max + 1):
            dest = raw_dir / f"{zoom}_{x}_{y}.png"
            fetch_tile(zoom, x, y, dest)
            tile_paths.append(dest)

    # ImageMagick montage tiles row-major, matching our x-then-y loop order.
    subprocess.run(
        [
            "montage",
            *[str(p) for p in tile_paths],
            "-tile",
            f"{tiles_wide}x",
            "-geometry",
            "+0+0",
            str(out_path),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--zooms", type=int, nargs="+", default=None, help="Subset of zooms to fetch")
    args = parser.parse_args()

    manifest_path = args.manifest or (project_root() / "map" / "manifest.json")
    manifest = load_manifest(manifest_path)

    raw_dir = project_root() / "map" / "reference" / "_raw-tiles"
    out_dir = project_root() / "map" / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)

    zoom_keys = [str(z) for z in args.zooms] if args.zooms else list(manifest["zooms"].keys())

    for zoom_key in zoom_keys:
        entry = manifest["zooms"][zoom_key]
        out_path = out_dir / f"z{zoom_key}.png"
        print(f"z{zoom_key}: fetching {entry['tiles_wide'] * entry['tiles_high']} tiles...", file=sys.stderr)
        stitch_zoom(entry, raw_dir, out_path)
        print(f"z{zoom_key}: wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
