---
name: ventnor-tarot
description: >-
  Ventnor Tarot project skills dispatcher. Covers card creation, generation
  mechanics, frame repair, and legacy migration. Read this file first, then
  load the specific sub-skill(s) for your task.
---

# Ventnor Tarot Skills

This folder contains all project AI skills for the Ventnor Tarot deck.
Read this dispatcher to find the right sub-skill, then **read and follow
that file** before acting.

## Sub-skills

| File | When to use |
|------|-------------|
| [`cards.md`](cards.md) | Card concepts, composition rules, quality checklists, suit objects, background/foreground rules, workflow steps. Load for any card creation, correction, or approval task. |
| [`generation.md`](generation.md) | AI image-tool mechanics: aspect-ratio workaround (9:16 → 7:12), black-bar strip-and-scale method, panel-ratio checks, soft-bleed fallback, glow flag compositing. Load when generating or normalising a rectified draft. |
| [`frame-repair.md`](frame-repair.md) | Repairing malformed frames, numeral areas, borders, dividers, or title panels on framed gallery cards. Load when fixing `illustrations-framed/` or `website/cards/` output without touching the underlying artwork. |
| [`illustration-crop.md`](illustration-crop.md) | **Legacy migration only.** Extracting the illustration from an existing framed `vtarot/` card into `illustrations-raw/`. Load when migrating an old card that has no rectified master yet. |
| [`illustration-clean.md`](illustration-clean.md) | **Legacy migration only.** Removing overlaid numerals and healing curved corners on `illustrations-raw/` crops. Load after illustration-crop, before rebuilding a rectified 7:12 master. |

The map skill (`.cursor/skills/ventnor-tarot-map/`) is a separate pipeline
and is **not** covered here.

## Loading multiple sub-skills

For a typical new card: load `cards.md` + `generation.md`.
For a frame repair: load `frame-repair.md`.
For legacy migration: load `illustration-crop.md` → `illustration-clean.md` →
then `cards.md` for the rectified rebuild.
