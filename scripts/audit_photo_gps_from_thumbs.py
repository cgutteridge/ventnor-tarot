#!/usr/bin/env python3
"""Audit GPS matches using cached thumbnails from original photos."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageChops, ImageOps, ImageStat


class Features(tuple):
    __slots__ = ()

    @property
    def thumb(self) -> Image.Image:
        return self[0]

    @property
    def hist(self) -> list[float]:
        return self[1]


def open_rgb(path: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def coarse_histogram(image: Image.Image) -> list[float]:
    hist = image.resize((32, 32), Image.Resampling.LANCZOS).histogram()
    bins: list[float] = []
    for channel in range(3):
        values = hist[channel * 256 : (channel + 1) * 256]
        for start in range(0, 256, 32):
            bins.append(sum(values[start : start + 32]))
    total = sum(bins) or 1
    return [value / total for value in bins]


def color_distance(left: list[float], right: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right))


def crop_to_aspect(image: Image.Image, aspect: float) -> Image.Image:
    width, height = image.size
    current = width / height
    if current > aspect:
        new_width = int(height * aspect)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = int(width / aspect)
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def features(image: Image.Image) -> Features:
    return Features(
        (
            ImageOps.fit(image, (128, 128), method=Image.Resampling.LANCZOS),
            coarse_histogram(image),
        )
    )


def compare(project: Features, source: Features) -> float:
    diff = ImageChops.difference(project.thumb, source.thumb)
    rms = sum(value**2 for value in ImageStat.Stat(diff).rms) ** 0.5
    return rms + color_distance(project.hist, source.hist) * 100


def rational_to_float(value: Any) -> float:
    return float(value)


def dms_to_decimal(value: Any, ref: str) -> float:
    degrees, minutes, seconds = (rational_to_float(part) for part in value)
    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if ref in {"S", "W"} else decimal


def gps_for(path: Path) -> tuple[float | str, float | str]:
    gps_tag = next(key for key, name in ExifTags.TAGS.items() if name == "GPSInfo")
    gps_keys = {name: key for key, name in ExifTags.GPSTAGS.items()}
    image = Image.open(path)
    exif = image.getexif()
    if gps_tag not in exif:
        return "", ""
    raw = exif.get_ifd(gps_tag)
    lat = raw.get(gps_keys["GPSLatitude"])
    lat_ref = raw.get(gps_keys["GPSLatitudeRef"])
    lon = raw.get(gps_keys["GPSLongitude"])
    lon_ref = raw.get(gps_keys["GPSLongitudeRef"])
    if not lat or not lat_ref or not lon or not lon_ref:
        return "", ""
    return dms_to_decimal(lat, lat_ref), dms_to_decimal(lon, lon_ref)


def confidence(best: float, second: float) -> str:
    gap = second - best
    if best <= 25 and gap >= 25:
        return "high"
    if best <= 65 and gap >= 10:
        return "medium"
    return "low"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-thumbs", default=Path("tmp/source-thumbs"), type=Path)
    parser.add_argument("--source-originals", required=True, type=Path)
    parser.add_argument("--project-photos", default=Path("vtarot/photos"), type=Path)
    parser.add_argument("--output", default=Path("tmp/photo-gps-audit.csv"), type=Path)
    args = parser.parse_args()

    source_images = [(path, open_rgb(path)) for path in sorted(args.source_thumbs.glob("*.jpg"))]
    rows = []
    for project_path in sorted(args.project_photos.glob("*")):
        if project_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        project = open_rgb(project_path)
        aspect = project.width / project.height
        project_features = features(project)
        sources = [
            (
                source_path,
                [
                    features(source),
                    features(crop_to_aspect(source, aspect)),
                ],
            )
            for source_path, source in source_images
        ]
        scored = []
        for source_path, source_variants in sources:
            scored.append((min(compare(project_features, variant) for variant in source_variants), source_path))
        scored.sort(key=lambda item: item[0])
        best_score, best_thumb = scored[0]
        second_score = scored[1][0]
        original = args.source_originals / best_thumb.name
        lat, lon = gps_for(original)
        rows.append(
            {
                "card_id": project_path.stem,
                "project_photo": str(project_path),
                "matched_source": str(original),
                "score": round(best_score, 2),
                "second_score": round(second_score, 2),
                "confidence": confidence(best_score, second_score),
                "latitude": lat,
                "longitude": lon,
                "map": f"https://www.google.com/maps?q={lat},{lon}" if lat != "" else "",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(args.output)
    for row in rows:
        print(
            f"{row['card_id']}: {row['confidence']} {row['score']}/{row['second_score']} "
            f"{Path(row['matched_source']).name} {row['latitude']} {row['longitude']}"
        )


if __name__ == "__main__":
    main()
