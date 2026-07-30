#!/usr/bin/env python3
"""Compute a tile-aligned pixel grid for the Ventnor Tarot map.

Takes the project's landmark bounding box and a list of zoom levels, and
writes ``map/manifest.json`` describing, for each zoom, the exact XYZ tile
range and pixel canvas that a painted master image must fill so it can be
sliced into seamless standard tiles.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

TILE_SIZE = 256

# Landmark coordinates (approx, via OSM Nominatim) bounding the project area.
LANDMARKS = {
    "bonchurch_beach": (50.5978, -1.1870),
    "steephill_cove": (50.5886, -1.2234),
    "radar_station": (50.6027, -1.1958),
    "ventnor_cemetery_top": (50.5967, -1.2159),
    "botanic_garden_far_side": (50.5885, -1.2312),
}

DEFAULT_ZOOMS = [14, 15, 16, 17]
DEFAULT_PADDING = 0.15


def project_root() -> Path:
    """Return the Ventnor Tarot project root (two levels above this script)."""
    return Path(__file__).resolve().parents[2]


def landmark_bounds(padding: float) -> dict[str, float]:
    """Return a padded lat/lon bounding box covering all landmarks."""
    lats = [lat for lat, _lon in LANDMARKS.values()]
    lons = [lon for _lat, lon in LANDMARKS.values()]
    south, north = min(lats), max(lats)
    west, east = min(lons), max(lons)
    lat_pad = (north - south) * padding
    lon_pad = (east - west) * padding
    return {
        "south": south - lat_pad,
        "north": north + lat_pad,
        "west": west - lon_pad,
        "east": east + lon_pad,
    }


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    """Convert lon/lat (degrees) to fractional XYZ tile coordinates."""
    lat_rad = math.radians(lat)
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def tile_to_lonlat(x: float, y: float, zoom: int) -> tuple[float, float]:
    """Convert fractional XYZ tile coordinates to lon/lat (degrees)."""
    n = 2**zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return lon, math.degrees(lat_rad)


def build_manifest(bounds: dict[str, float], zooms: list[int]) -> dict[str, Any]:
    """Compute the tile-aligned grid for each zoom level."""
    zoom_entries: dict[str, Any] = {}
    for zoom in zooms:
        x_min_f, y_min_f = lonlat_to_tile(bounds["west"], bounds["north"], zoom)
        x_max_f, y_max_f = lonlat_to_tile(bounds["east"], bounds["south"], zoom)

        tile_x_min = math.floor(x_min_f)
        tile_x_max = math.floor(x_max_f)
        tile_y_min = math.floor(y_min_f)
        tile_y_max = math.floor(y_max_f)

        tiles_wide = tile_x_max - tile_x_min + 1
        tiles_high = tile_y_max - tile_y_min + 1

        # Geographic bounds of the tile-aligned canvas (snapped outward to
        # whole tiles, not the raw padded landmark bbox).
        west, north = tile_to_lonlat(tile_x_min, tile_y_min, zoom)
        east, south = tile_to_lonlat(tile_x_max + 1, tile_y_max + 1, zoom)

        zoom_entries[str(zoom)] = {
            "zoom": zoom,
            "tile_x_min": tile_x_min,
            "tile_x_max": tile_x_max,
            "tile_y_min": tile_y_min,
            "tile_y_max": tile_y_max,
            "tiles_wide": tiles_wide,
            "tiles_high": tiles_high,
            "pixel_width": tiles_wide * TILE_SIZE,
            "pixel_height": tiles_high * TILE_SIZE,
            "geo_bounds": {"north": north, "south": south, "east": east, "west": west},
        }

    return {
        "tile_size": TILE_SIZE,
        "landmarks": {name: {"lat": lat, "lon": lon} for name, (lat, lon) in LANDMARKS.items()},
        "requested_bounds": bounds,
        "zooms": zoom_entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--zooms",
        type=int,
        nargs="+",
        default=DEFAULT_ZOOMS,
        help=f"Zoom levels to compute (default: {DEFAULT_ZOOMS})",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=DEFAULT_PADDING,
        help=f"Fractional padding added around the landmark bbox (default: {DEFAULT_PADDING})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Output path for manifest.json (default: map/manifest.json)",
    )
    args = parser.parse_args()

    bounds = landmark_bounds(args.padding)
    manifest = build_manifest(bounds, sorted(args.zooms))

    out_path = args.manifest or (project_root() / "map" / "manifest.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Wrote {out_path}")
    for zoom_key, entry in manifest["zooms"].items():
        print(
            f"  z{zoom_key}: {entry['tiles_wide']}x{entry['tiles_high']} tiles "
            f"({entry['pixel_width']}x{entry['pixel_height']}px), "
            f"tiles x[{entry['tile_x_min']}-{entry['tile_x_max']}] "
            f"y[{entry['tile_y_min']}-{entry['tile_y_max']}]"
        )


if __name__ == "__main__":
    main()
