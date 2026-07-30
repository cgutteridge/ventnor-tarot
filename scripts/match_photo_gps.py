#!/usr/bin/env python3
"""Match Ventnor Tarot background photos to original JPEGs and extract GPS."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


@dataclass(frozen=True)
class Gps:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Fingerprint:
    ahash: int
    dhash: int
    color: tuple[float, ...]


@dataclass(frozen=True)
class SourcePhoto:
    path: Path
    gps: Gps | None
    fingerprint: Fingerprint
    image: Image.Image
    width: int
    height: int


def rational_to_float(value: Any) -> float:
    try:
        return float(value)
    except TypeError:
        return value[0] / value[1]


def dms_to_decimal(value: Any, ref: str) -> float:
    degrees, minutes, seconds = (rational_to_float(part) for part in value)
    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if ref in {"S", "W"} else decimal


def extract_gps(image: Image.Image) -> Gps | None:
    gps_tag = next(key for key, name in ExifTags.TAGS.items() if name == "GPSInfo")
    gps_keys = {name: key for key, name in ExifTags.GPSTAGS.items()}

    exif = image.getexif()
    if gps_tag not in exif:
        return None

    raw_gps = exif.get_ifd(gps_tag)
    lat = raw_gps.get(gps_keys["GPSLatitude"])
    lat_ref = raw_gps.get(gps_keys["GPSLatitudeRef"])
    lon = raw_gps.get(gps_keys["GPSLongitude"])
    lon_ref = raw_gps.get(gps_keys["GPSLongitudeRef"])

    if not lat or not lat_ref or not lon or not lon_ref:
        return None

    return Gps(
        latitude=dms_to_decimal(lat, lat_ref),
        longitude=dms_to_decimal(lon, lon_ref),
    )


def open_image(path: Path, max_size: int = 768) -> Image.Image:
    image = Image.open(path)
    try:
        image.draft("RGB", (max_size, max_size))
    except Exception:
        pass
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return image


def average_hash(image: Image.Image, size: int = 16) -> int:
    thumb = image.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(thumb.getdata())
    avg = sum(pixels) / len(pixels)
    result = 0
    for pixel in pixels:
        result = (result << 1) | int(pixel >= avg)
    return result


def difference_hash(image: Image.Image, size: int = 16) -> int:
    thumb = image.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(thumb.getdata())
    result = 0
    for y in range(size):
        row = y * (size + 1)
        for x in range(size):
            result = (result << 1) | int(pixels[row + x] > pixels[row + x + 1])
    return result


def color_histogram(image: Image.Image) -> tuple[float, ...]:
    thumb = image.resize((96, 96), Image.Resampling.LANCZOS)
    histogram = thumb.histogram()
    bins: list[float] = []
    for channel in range(3):
        values = histogram[channel * 256 : (channel + 1) * 256]
        for start in range(0, 256, 32):
            bins.append(sum(values[start : start + 32]))
    total = sum(bins) or 1
    return tuple(value / total for value in bins)


def center_crop_to_aspect(image: Image.Image, aspect: float) -> Image.Image:
    width, height = image.size
    current = width / height
    if math.isclose(current, aspect, rel_tol=0.005):
        return image
    if current > aspect:
        new_width = int(height * aspect)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))
    new_height = int(width / aspect)
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))


def fingerprint(image: Image.Image) -> Fingerprint:
    return Fingerprint(
        ahash=average_hash(image),
        dhash=difference_hash(image),
        color=color_histogram(image),
    )


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def color_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(abs(a - b) for a, b in zip(left, right))


def score(left: Fingerprint, right: Fingerprint) -> float:
    return (
        hamming(left.ahash, right.ahash)
        + hamming(left.dhash, right.dhash)
        + color_distance(left.color, right.color) * 120
    )


def confidence(best: float, second: float | None) -> str:
    if best <= 35 and (second is None or second - best >= 20):
        return "high"
    if best <= 65 and (second is None or second - best >= 10):
        return "medium"
    return "low"


def iter_images(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def build_source(path: Path) -> SourcePhoto | None:
    try:
        original = Image.open(path)
        gps = extract_gps(original)
        width, height = original.size
        image = open_image(path)
    except Exception:
        return None
    return SourcePhoto(
        path=path,
        gps=gps,
        fingerprint=fingerprint(image),
        image=image,
        width=width,
        height=height,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--project-photos", default=Path("vtarot/photos"), type=Path)
    parser.add_argument("--output", default=Path("tmp/photo-gps-audit.csv"), type=Path)
    parser.add_argument("--json-output", default=Path("tmp/photo-gps-audit.json"), type=Path)
    args = parser.parse_args()

    sources = [source for path in iter_images(args.sources) if (source := build_source(path))]
    project_paths = iter_images(args.project_photos)

    rows: list[dict[str, Any]] = []
    for project_path in project_paths:
        try:
            project_image = open_image(project_path)
        except Exception:
            continue

        project_aspect = project_image.width / project_image.height
        project_fingerprints = [
            fingerprint(project_image),
            fingerprint(center_crop_to_aspect(project_image, project_aspect)),
        ]

        candidates: list[tuple[float, SourcePhoto]] = []
        for source in sources:
            source_variants = [
                source.fingerprint,
                fingerprint(center_crop_to_aspect(source.image, project_aspect)),
            ]
            best_variant_score = min(
                score(project_fp, source_fp)
                for project_fp in project_fingerprints
                for source_fp in source_variants
            )
            candidates.append((best_variant_score, source))

        candidates.sort(key=lambda item: item[0])
        best_score, best_source = candidates[0]
        second_score = candidates[1][0] if len(candidates) > 1 else None
        gps = best_source.gps
        rows.append(
            {
                "card_id": project_path.stem,
                "project_photo": str(project_path),
                "matched_source": str(best_source.path),
                "score": round(best_score, 3),
                "second_score": round(second_score, 3) if second_score is not None else "",
                "confidence": confidence(best_score, second_score),
                "latitude": gps.latitude if gps else "",
                "longitude": gps.longitude if gps else "",
                "source_has_gps": bool(gps),
                "source_width": best_source.width,
                "source_height": best_source.height,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    args.json_output.write_text(json.dumps(rows, indent=2) + "\n")

    gps_count = sum(1 for source in sources if source.gps)
    high_count = sum(1 for row in rows if row["confidence"] == "high")
    print(f"Scanned {len(sources)} source images; {gps_count} have GPS.")
    print(f"Matched {len(rows)} project photos; {high_count} high-confidence matches.")
    print(args.output)
    print(args.json_output)


if __name__ == "__main__":
    main()
