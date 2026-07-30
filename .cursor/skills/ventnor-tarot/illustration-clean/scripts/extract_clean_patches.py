#!/usr/bin/env python3
"""Extract numeral and corner patches from illustrations-raw for focused AI heal.

Writes per-card working trees under ``tmp/illustration-clean-work/`` including
patch PNGs, soft masks, ``meta.json``, and ``pending.json``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

CORNER_SIZE = 96
NUMERAL_BAND_HEIGHT = 140
NUMERAL_BAND_WIDTH = 520


def project_root() -> Path:
    """Return the Ventnor Tarot project root (four levels above this script)."""
    return Path(__file__).resolve().parents[4]


def card_expects_numeral(filename: str) -> bool:
    """Return True if this Ventnor card normally carries a top numeral.

    Aces and courts have no Roman numeral. Pip cards II–X and all Majors do
    (including Fool ``0``).
    """
    stem = Path(filename).stem
    if stem.startswith("maj"):
        return True
    match = re.fullmatch(r"(cups|wands|swords|pents)(\d{2})", stem)
    if not match:
        return True
    number = int(match.group(2))
    return 2 <= number <= 10


def load_rgb(path: Path) -> tuple[int, int, bytes]:
    """Load an image as 8-bit interleaved RGB bytes via ImageMagick."""
    raw = subprocess.check_output(["magick", str(path), "-depth", "8", "rgb:-"])
    size = subprocess.check_output(
        ["magick", "identify", "-format", "%w %h", str(path)], text=True
    ).split()
    width, height = int(size[0]), int(size[1])
    expected = width * height * 3
    if len(raw) != expected:
        raise RuntimeError(f"{path.name}: expected {expected} bytes, got {len(raw)}")
    return width, height, raw


def pixel(raw: bytes, width: int, x: int, y: int) -> tuple[int, int, int]:
    """Return RGB at ``(x, y)``."""
    i = (y * width + x) * 3
    return raw[i], raw[i + 1], raw[i + 2]


def is_cream(rgb: tuple[int, int, int]) -> bool:
    """Return True for aged-paper cream residue."""
    r, g, b = rgb
    return (
        min(r, g, b) >= 140
        and abs(r - g) <= 50
        and abs(g - b) <= 55
        and abs(r - b) <= 65
        and (r + g + b) / 3 >= 165
    )


def is_gold(rgb: tuple[int, int, int]) -> bool:
    """Return True for gold frame residue."""
    r, g, b = rgb
    return (
        r > 110
        and g > 70
        and b < 150
        and (r - b) > 30
        and (g - b) > 10
        and r >= g - 20
    )


def is_frame_residue(rgb: tuple[int, int, int]) -> bool:
    """Return True for cream/gold leftover frame pixels."""
    return is_cream(rgb) or is_gold(rgb)


def is_dark_ink(rgb: tuple[int, int, int]) -> bool:
    """Return True for dark numeral ink."""
    return max(rgb) <= 95


def is_pale_glow(rgb: tuple[int, int, int], neighbor_sky: bool) -> bool:
    """Return True for pale halo pixels near numeral ink on sky."""
    r, g, b = rgb
    if not neighbor_sky:
        return False
    avg = (r + g + b) / 3
    return avg >= 185 and abs(r - g) <= 35 and abs(g - b) <= 40 and min(r, g, b) >= 160


def write_png_rgb(path: Path, width: int, height: int, rgb: bytes) -> None:
    """Write interleaved RGB bytes as a PNG."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "magick",
            "-size",
            f"{width}x{height}",
            "-depth",
            "8",
            "rgb:-",
            str(path),
        ],
        input=rgb,
        check=True,
    )


def write_png_gray(path: Path, width: int, height: int, gray: bytes) -> None:
    """Write interleaved grayscale bytes as a PNG mask."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "magick",
            "-size",
            f"{width}x{height}",
            "-depth",
            "8",
            "gray:-",
            str(path),
        ],
        input=gray,
        check=True,
    )


def crop_box(
    raw: bytes, src_w: int, left: int, top: int, width: int, height: int
) -> bytes:
    """Copy a rectangular RGB crop from ``raw``."""
    out = bytearray(width * height * 3)
    for y in range(height):
        src = ((top + y) * src_w + left) * 3
        dst = y * width * 3
        out[dst : dst + width * 3] = raw[src : src + width * 3]
    return bytes(out)


def corner_boxes(width: int, height: int, size: int) -> dict[str, tuple[int, int, int, int]]:
    """Return ``name -> (left, top, width, height)`` for four corners."""
    s = min(size, width // 3, height // 3)
    return {
        "corner-tl": (0, 0, s, s),
        "corner-tr": (width - s, 0, s, s),
        "corner-bl": (0, height - s, s, s),
        "corner-br": (width - s, height - s, s, s),
    }


def numeral_box(width: int, height: int) -> tuple[int, int, int, int]:
    """Return ``(left, top, width, height)`` for the top numeral band."""
    band_w = min(NUMERAL_BAND_WIDTH, width)
    band_h = min(NUMERAL_BAND_HEIGHT, height // 4)
    left = max(0, (width - band_w) // 2)
    return left, 0, band_w, band_h


def build_corner_mask(
    raw: bytes, src_w: int, left: int, top: int, width: int, height: int
) -> tuple[bytes, float]:
    """Build a soft grayscale mask for frame residue in a corner patch.

    Returns:
        ``(mask_bytes, residue_fraction)``.
    """
    mask = bytearray(width * height)
    residue = 0
    for y in range(height):
        for x in range(width):
            rgb = pixel(raw, src_w, left + x, top + y)
            if is_frame_residue(rgb):
                mask[y * width + x] = 255
                residue += 1
            else:
                # Also catch thin dark edge lines next to gold.
                r, g, b = rgb
                if max(r, g, b) < 70 and (
                    (x < 8 or y < 8 or x >= width - 8 or y >= height - 8)
                ):
                    mask[y * width + x] = 200
                    residue += 1
    return bytes(mask), residue / (width * height)


def build_numeral_mask(
    raw: bytes, src_w: int, left: int, top: int, width: int, height: int
) -> tuple[bytes, float, bool]:
    """Build a soft mask for Roman numeral ink and nearby glow.

    Returns:
        ``(mask_bytes, ink_fraction, likely_numeral)``.
    """
    ink = [[False] * width for _ in range(height)]
    ink_count = 0
    for y in range(height):
        for x in range(width):
            if is_dark_ink(pixel(raw, src_w, left + x, top + y)):
                ink[y][x] = True
                ink_count += 1

    # Prefer centrally concentrated dark pixels (a centered numeral).
    cx0, cx1 = width // 4, (3 * width) // 4
    cy1 = int(height * 0.75)
    center_ink = sum(
        1 for y in range(0, cy1) for x in range(cx0, cx1) if ink[y][x]
    )
    likely = center_ink >= 40 and ink_count >= 60

    mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if ink[y][x]:
                mask[y * width + x] = 255
                continue
            # Soft glow: pale pixels near ink.
            near = False
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width and ink[ny][nx]:
                        near = True
                        break
                if near:
                    break
            if near and is_pale_glow(pixel(raw, src_w, left + x, top + y), True):
                mask[y * width + x] = 180
    return bytes(mask), ink_count / (width * height), likely


def card_stem(path: Path) -> str:
    """Return filename stem for work-dir naming."""
    return path.stem


def extract_card(
    source: Path,
    work_root: Path,
    corner_size: int,
    force: bool,
) -> dict[str, Any]:
    """Extract patches/masks for one illustration.

    Args:
        source: Path under ``illustrations-raw/``.
        work_root: Root of ``illustration-clean-work``.
        corner_size: Corner patch edge length in pixels.
        force: Rebuild even if ``meta.json`` exists.

    Returns:
        Summary dictionary for this card.
    """
    stem = card_stem(source)
    card_dir = work_root / stem
    patches_dir = card_dir / "patches"
    healed_dir = card_dir / "healed"
    meta_path = card_dir / "meta.json"

    if meta_path.is_file() and not force:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pending = json.loads((card_dir / "pending.json").read_text(encoding="utf-8"))
        return {
            "file": source.name,
            "skipped": True,
            "pending_count": len(pending.get("patches", [])),
            "meta": meta,
        }

    width, height, raw = load_rgb(source)
    card_dir.mkdir(parents=True, exist_ok=True)
    healed_dir.mkdir(parents=True, exist_ok=True)
    patches_dir.mkdir(parents=True, exist_ok=True)

    # Refresh source copy for compositing.
    subprocess.check_call(["magick", str(source), str(card_dir / "source.png")])

    pending: list[dict[str, Any]] = []
    patches_meta: dict[str, Any] = {}

    # Corners
    for name, (left, top, pw, ph) in corner_boxes(width, height, corner_size).items():
        rgb = crop_box(raw, width, left, top, pw, ph)
        mask, frac = build_corner_mask(raw, width, left, top, pw, ph)
        patch_name = f"{name}.png"
        mask_name = f"{name}-mask.png"
        write_png_rgb(patches_dir / patch_name, pw, ph, rgb)
        write_png_gray(patches_dir / mask_name, pw, ph, mask)
        needs = frac >= 0.02
        patches_meta[name] = {
            "file": patch_name,
            "mask": mask_name,
            "left": left,
            "top": top,
            "width": pw,
            "height": ph,
            "residue_fraction": round(frac, 4),
            "needs_heal": needs,
        }
        if needs:
            pending.append(
                {
                    "kind": "corner",
                    "patch": patch_name,
                    "mask": mask_name,
                    "prompt": (
                        "Heal only this corner patch of a photograph. Replace any "
                        "gold or cream curved frame residue with continuous matching "
                        "background from the rest of the patch so the corner becomes "
                        "a natural square photo corner. No frame, border, text, or "
                        "new objects. Keep the same size."
                    ),
                }
            )

    # Numeral band
    nleft, ntop, nw, nh = numeral_box(width, height)
    nrgb = crop_box(raw, width, nleft, ntop, nw, nh)
    nmask, nfrac, likely = build_numeral_mask(raw, width, nleft, ntop, nw, nh)
    write_png_rgb(patches_dir / "numeral.png", nw, nh, nrgb)
    write_png_gray(patches_dir / "numeral-mask.png", nw, nh, nmask)
    expects = card_expects_numeral(source.name)
    needs_numeral = bool(expects and likely)
    patches_meta["numeral"] = {
        "file": "numeral.png",
        "mask": "numeral-mask.png",
        "left": nleft,
        "top": ntop,
        "width": nw,
        "height": nh,
        "ink_fraction": round(nfrac, 4),
        "expects_numeral": expects,
        "detected_numeral": likely,
        "needs_heal": needs_numeral,
    }
    if needs_numeral:
        pending.append(
            {
                "kind": "numeral",
                "patch": "numeral.png",
                "mask": "numeral-mask.png",
                "prompt": (
                    "Remove the Roman numeral and any pale glow/halo from this top "
                    "band of a photograph. Fill with continuous matching sky or "
                    "background texture only. No text, no frame, no new objects. "
                    "Keep the same size."
                ),
            }
        )

    # Drop pending entries already healed.
    still_pending = []
    for item in pending:
        healed_path = healed_dir / item["patch"]
        if not healed_path.is_file():
            still_pending.append(item)

    meta = {
        "file": source.name,
        "stem": stem,
        "source_width": width,
        "source_height": height,
        "corner_size": corner_size,
        "patches": patches_meta,
        "pending_count": len(still_pending),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (card_dir / "pending.json").write_text(
        json.dumps({"file": source.name, "patches": still_pending}, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "file": source.name,
        "skipped": False,
        "pending_count": len(still_pending),
        "meta": meta,
    }


def extract_all(
    raw_dir: Path,
    work_root: Path,
    corner_size: int,
    force: bool,
    only: list[str] | None,
) -> dict[str, Any]:
    """Extract clean-work patches for every (or selected) raw illustration."""
    paths = sorted(raw_dir.glob("*.png"))
    if only:
        wanted = set(only)
        paths = [p for p in paths if p.name in wanted or p.stem in wanted]
    if not paths:
        raise SystemExit(f"No PNG files found in {raw_dir}")

    work_root.mkdir(parents=True, exist_ok=True)
    results = []
    total_pending = 0
    for path in paths:
        try:
            summary = extract_card(path, work_root, corner_size, force)
            results.append(summary)
            total_pending += int(summary["pending_count"])
            flag = " (cached)" if summary.get("skipped") else ""
            print(f"{path.name}: {summary['pending_count']} pending patch(es){flag}")
        except Exception as exc:  # noqa: BLE001
            print(f"{path.name}: ERROR {exc}", file=sys.stderr)
            results.append({"file": path.name, "error": str(exc)})

    index = {
        "raw_dir": str(raw_dir.as_posix()),
        "work_root": str(work_root.as_posix()),
        "card_count": len(results),
        "pending_patches": total_pending,
        "cards": results,
    }
    (work_root / "index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Pending AI patches: {total_pending}")
    return index


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for patch extraction."""
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Extract numeral/corner patches for focused illustration cleaning."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=root / "illustrations-raw",
        help="Input directory (default: illustrations-raw)",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=root / "tmp" / "illustration-clean-work",
        help="Working directory for patches",
    )
    parser.add_argument(
        "--corner-size",
        type=int,
        default=CORNER_SIZE,
        help=f"Corner patch size in pixels (default: {CORNER_SIZE})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild patches even when meta.json exists",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional list of card filenames or stems to process",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Extract clean patches for illustrations-raw cards."""
    args = parse_args(argv)
    extract_all(args.raw_dir, args.work_root, args.corner_size, args.force, args.only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
