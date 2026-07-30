#!/usr/bin/env python3
"""Composite healed numeral/corner patches into illustrations-cleaned/.

Reads ``tmp/illustration-clean-work/<stem>/`` and pastes each available healed
patch onto a copy of the raw illustration.
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


def load_meta(card_dir: Path) -> dict[str, Any]:
    """Load ``meta.json`` for one clean-work card directory."""
    path = card_dir / "meta.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing meta.json in {card_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_pending(card_dir: Path, meta: dict[str, Any]) -> list[dict[str, Any]]:
    """Recompute pending patches from meta + healed directory contents."""
    healed_dir = card_dir / "healed"
    pending: list[dict[str, Any]] = []
    for name, info in meta.get("patches", {}).items():
        if not info.get("needs_heal"):
            continue
        patch_file = info["file"]
        if not (healed_dir / patch_file).is_file():
            kind = "numeral" if name == "numeral" else "corner"
            pending.append({"kind": kind, "patch": patch_file, "mask": info.get("mask")})
    (card_dir / "pending.json").write_text(
        json.dumps({"file": meta["file"], "patches": pending}, indent=2) + "\n",
        encoding="utf-8",
    )
    return pending


def composite_card(
    card_dir: Path,
    output_dir: Path,
    allow_partial: bool,
) -> dict[str, Any]:
    """Composite healed patches for one card into ``illustrations-cleaned``.

    Args:
        card_dir: Per-card clean-work directory.
        output_dir: Destination directory.
        allow_partial: When True, composite even if some needed heals are missing
            (unhealed regions keep the raw pixels).

    Returns:
        Result summary dictionary.
    """
    meta = load_meta(card_dir)
    pending = refresh_pending(card_dir, meta)
    if pending and not allow_partial:
        return {
            "file": meta["file"],
            "status": "blocked",
            "pending": [p["patch"] for p in pending],
        }

    source = card_dir / "source.png"
    if not source.is_file():
        raise FileNotFoundError(f"missing source.png in {card_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / meta["file"]
    subprocess.check_call(["magick", str(source), str(dest)])

    healed_dir = card_dir / "healed"
    applied: list[str] = []
    for name, info in meta.get("patches", {}).items():
        if not info.get("needs_heal"):
            continue
        healed = healed_dir / info["file"]
        if not healed.is_file():
            continue
        left = int(info["left"])
        top = int(info["top"])
        # Overlay healed patch at the recorded origin.
        subprocess.check_call(
            [
                "magick",
                str(dest),
                str(healed),
                "-geometry",
                f"+{left}+{top}",
                "-compose",
                "Over",
                "-composite",
                str(dest),
            ]
        )
        applied.append(info["file"])

    return {
        "file": meta["file"],
        "status": "written",
        "applied": applied,
        "still_pending": [p["patch"] for p in pending],
        "output": str(dest.as_posix()),
    }


def composite_all(
    work_root: Path,
    output_dir: Path,
    allow_partial: bool,
    only: list[str] | None,
) -> int:
    """Composite every card work directory under ``work_root``."""
    if not work_root.is_dir():
        raise SystemExit(
            f"Work root not found: {work_root}\nRun: make clean-extract"
        )

    card_dirs = sorted(
        p for p in work_root.iterdir() if p.is_dir() and (p / "meta.json").is_file()
    )
    if only:
        wanted = set(only)
        card_dirs = [
            p
            for p in card_dirs
            if p.name in wanted or f"{p.name}.png" in wanted
        ]
    if not card_dirs:
        raise SystemExit(f"No card work dirs with meta.json in {work_root}")

    written = 0
    blocked = 0
    for card_dir in card_dirs:
        try:
            result = composite_card(card_dir, output_dir, allow_partial)
        except Exception as exc:  # noqa: BLE001
            print(f"{card_dir.name}: ERROR {exc}", file=sys.stderr)
            blocked += 1
            continue
        if result["status"] == "written":
            written += 1
            pending = result.get("still_pending") or []
            extra = f" (partial; missing {pending})" if pending else ""
            print(
                f"{result['file']}: wrote {result['output']} "
                f"applied={result['applied']}{extra}"
            )
        else:
            blocked += 1
            print(
                f"{result['file']}: blocked, pending {result['pending']}",
                file=sys.stderr,
            )

    print(f"Composited {written}; blocked {blocked}")
    return 0 if blocked == 0 or allow_partial else 1


def status_report(work_root: Path) -> int:
    """Print heal/composite readiness for each card work directory."""
    if not work_root.is_dir():
        print(f"No work root at {work_root} (run make clean-extract)")
        return 1
    total_pending = 0
    ready = 0
    cards = 0
    for card_dir in sorted(p for p in work_root.iterdir() if p.is_dir()):
        meta_path = card_dir / "meta.json"
        if not meta_path.is_file():
            continue
        cards += 1
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pending = refresh_pending(card_dir, meta)
        total_pending += len(pending)
        if pending:
            print(f"{meta['file']}: pending {len(pending)} -> {[p['patch'] for p in pending]}")
        else:
            ready += 1
            print(f"{meta['file']}: ready to composite")
    print(f"{cards} cards; {ready} ready; {total_pending} pending patches")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for compositing cleaned illustrations."""
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Composite healed patches into illustrations-cleaned/."
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=root / "tmp" / "illustration-clean-work",
        help="Working directory for patches",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=root / "illustrations-cleaned",
        help="Output directory (default: illustrations-cleaned)",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Composite even when some required healed patches are missing",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Only print pending/ready status",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Optional list of card stems or filenames",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Composite healed patches or print clean-work status."""
    args = parse_args(argv)
    if args.status:
        return status_report(args.work_root)
    return composite_all(args.work_root, args.output_dir, args.allow_partial, args.only)


if __name__ == "__main__":
    raise SystemExit(main())
