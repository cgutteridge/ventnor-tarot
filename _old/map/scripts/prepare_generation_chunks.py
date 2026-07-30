#!/usr/bin/env python3
"""Prepare overlapping source crops for chunked map-master generation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


TILE_SIZE = 256


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing manifest: {path}")
    return json.loads(path.read_text())


def ranges(total_tiles: int, chunks: int) -> list[tuple[int, int]]:
    base = total_tiles // chunks
    extra = total_tiles % chunks
    out: list[tuple[int, int]] = []
    start = 0
    for i in range(chunks):
        width = base + (1 if i < extra else 0)
        end = start + width
        out.append((start, end))
        start = end
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zoom", type=int, required=True)
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--rows", type=int, default=3)
    parser.add_argument("--overlap-tiles", type=int, default=1)
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args()

    root = project_root()
    manifest = load_manifest(args.manifest or root / "map" / "manifest.json")
    entry = manifest["zooms"][str(args.zoom)]

    ref_path = root / "map" / "reference" / f"z{args.zoom}.png"
    if not ref_path.exists():
        raise SystemExit(f"Missing reference image: {ref_path}")

    out_root = root / "map" / "tmp" / f"z{args.zoom}-chunks"
    ref_dir = out_root / "reference"
    ref_dir.mkdir(parents=True, exist_ok=True)

    x_ranges = ranges(entry["tiles_wide"], args.cols)
    y_ranges = ranges(entry["tiles_high"], args.rows)
    overlap = args.overlap_tiles * TILE_SIZE

    chunks: list[dict[str, Any]] = []
    for row, (core_tile_y0, core_tile_y1) in enumerate(y_ranges):
        for col, (core_tile_x0, core_tile_x1) in enumerate(x_ranges):
            core_x0 = core_tile_x0 * TILE_SIZE
            core_y0 = core_tile_y0 * TILE_SIZE
            core_x1 = core_tile_x1 * TILE_SIZE
            core_y1 = core_tile_y1 * TILE_SIZE

            src_x0 = max(0, core_x0 - overlap)
            src_y0 = max(0, core_y0 - overlap)
            src_x1 = min(entry["pixel_width"], core_x1 + overlap)
            src_y1 = min(entry["pixel_height"], core_y1 + overlap)

            chunk_id = f"r{row}c{col}"
            out_path = ref_dir / f"{chunk_id}.png"
            width = src_x1 - src_x0
            height = src_y1 - src_y0
            subprocess.run(
                [
                    "convert",
                    str(ref_path),
                    "-crop",
                    f"{width}x{height}+{src_x0}+{src_y0}",
                    "+repage",
                    str(out_path),
                ],
                check=True,
            )
            chunks.append(
                {
                    "id": chunk_id,
                    "row": row,
                    "col": col,
                    "reference": str(out_path.relative_to(root)),
                    "core": {"x": core_x0, "y": core_y0, "width": core_x1 - core_x0, "height": core_y1 - core_y0},
                    "source": {"x": src_x0, "y": src_y0, "width": width, "height": height},
                    "neighbors": {
                        "west": f"r{row}c{col - 1}" if col > 0 else None,
                        "north": f"r{row - 1}c{col}" if row > 0 else None,
                    },
                }
            )

    plan = {
        "zoom": args.zoom,
        "canvas": {"width": entry["pixel_width"], "height": entry["pixel_height"]},
        "grid": {"cols": args.cols, "rows": args.rows, "overlap_tiles": args.overlap_tiles},
        "chunks": chunks,
    }
    plan_path = out_root / "chunk-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"Wrote {plan_path}")
    print(f"Wrote {len(chunks)} reference chunks to {ref_dir}")


if __name__ == "__main__":
    main()
