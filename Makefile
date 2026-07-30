# Ventnor Tarot — print-ready illustration pipeline
#
# Make owns orchestration, patch extract, and compositing.
# Cursor/agent (or an external image API) owns focused AI heal of small patches.
# Never full-image AI regenerate in this pipeline.

ROOT := $(abspath .)
CROP_SCRIPTS := $(ROOT)/.cursor/skills/ventnor-tarot/illustration-crop/scripts
CLEAN_SCRIPTS := $(ROOT)/.cursor/skills/ventnor-tarot/illustration-clean/scripts

VTAROT := $(ROOT)/vtarot
RAW := $(ROOT)/illustrations-raw
CLEANED := $(ROOT)/illustrations-cleaned
BOUNDS := $(ROOT)/tmp/illustration-bounds.json
CLEAN_WORK := $(ROOT)/tmp/illustration-clean-work

.PHONY: help bounds crop raw clean-extract clean-status clean-composite clean-agent-hint numeralled framed website

help:
	@echo "Ventnor print-ready / migration targets:"
	@echo "  Primary (new cards): create 700×1200 art in illustrations-rectified/ (Skill.md),"
	@echo "    approve, update vtarot/photos + card-data.js, then run numeralled -> framed."
	@echo ""
	@echo "  Website assembly:"
	@echo "  make website          Sync framed cards, sources, and rider-waite into website/"
	@echo "                        and rebuild website/card-data.js from _old/vtarot/card-data.js"
	@echo "                        (idempotent; never overwrites website/index.html)"
	@echo ""
	@echo "  Numeral compositing:"
	@echo "  make numeralled                       Overlay numerals onto all rectified cards -> illustrations-numeralled/"
	@echo "  make illustrations-numeralled/X.png   Rebuild one card (e.g. make illustrations-numeralled/maj07.png)"
	@echo "  NUMERAL_FONT=path                     Optional: override font (default: Times New Roman system font)"
	@echo ""
	@echo "  Framing:"
	@echo "  make framed                           Add Ventnor frame + title panel to all numeralled cards -> illustrations-framed/"
	@echo "  make illustrations-framed/X.png       Rebuild one framed card (e.g. make illustrations-framed/maj07.png)"
	@echo "  FRAME_FONT=path                       Optional: override title font (default: Times New Roman system font)"
	@echo ""
	@echo "  Legacy migration (existing framed cards only):"
	@echo "  make bounds           Detect crop bounds -> tmp/illustration-bounds.json"
	@echo "  make crop             Crop vtarot -> illustrations-raw (after reviewing bounds)"
	@echo "  make raw              bounds + crop"
	@echo "  make clean-extract    Extract numeral/corner patches from illustrations-raw"
	@echo "  make clean-status     Show which patches still need focused AI heal"
	@echo "  make clean-composite  Paste healed patches -> illustrations-cleaned"
	@echo "  make clean-agent-hint Reminder for the agent AI step (not runnable AI)"
	@echo ""
	@echo "AI heal is NOT done by Make. After clean-extract, run the"
	@echo "ventnor-tarot-illustration-clean skill in Cursor (or call your own API),"
	@echo "writing healed patches under tmp/illustration-clean-work/<card>/healed/"
	@echo "Then rebuild illustrations-rectified/ at 700×1200 from references (Skill.md)."

bounds: $(BOUNDS)

$(BOUNDS): $(wildcard $(VTAROT)/*.png) $(CROP_SCRIPTS)/detect_illustration_bounds.py
	python3 "$(CROP_SCRIPTS)/detect_illustration_bounds.py" --manifest "$(BOUNDS)"

crop: $(BOUNDS)
	python3 "$(CROP_SCRIPTS)/crop_illustrations.py" --manifest "$(BOUNDS)" --output-dir "$(RAW)"

raw: bounds crop

clean-extract:
	@test -d "$(RAW)" || (echo "Missing $(RAW). Run make raw (and manually recrop as needed) first."; exit 1)
	python3 "$(CLEAN_SCRIPTS)/extract_clean_patches.py" --raw-dir "$(RAW)" --work-root "$(CLEAN_WORK)"

clean-status:
	python3 "$(CLEAN_SCRIPTS)/composite_cleaned.py" --work-root "$(CLEAN_WORK)" --status

clean-composite:
	python3 "$(CLEAN_SCRIPTS)/composite_cleaned.py" --work-root "$(CLEAN_WORK)" --output-dir "$(CLEANED)"

clean-agent-hint:
	@echo "Focused AI heal (agent or external API), not Make:"
	@echo "  1. make clean-extract"
	@echo "  2. In Cursor, load skill .cursor/skills/ventnor-tarot/ → illustration-clean.md"
	@echo "     Heal only files listed in each pending.json"
	@echo "     Save results to tmp/illustration-clean-work/<stem>/healed/"
	@echo "  3. make clean-status"
	@echo "  4. make clean-composite"

# ---------------------------------------------------------------------------
# Numeral compositing
# ---------------------------------------------------------------------------
#
# Overlays Roman numerals onto rectified artwork → illustrations-numeralled/.
# Driven by card-numerals.json (per-card metadata + glow flags).
# Aces and courts (numeral: null) are copied through unchanged.
#
# Usage:
#   make numeralled                      Build / rebuild all numeralled cards
#   make illustrations-numeralled/id.png Rebuild one card (e.g. illustrations-numeralled/maj07.png)
#
# Incremental: a card is only recomposed when its source PNG or
# card-numerals.json is newer than the existing output.
#
# Font: the script falls back to Times New Roman from the macOS system fonts.
# Override by setting NUMERAL_FONT:
#   make numeralled NUMERAL_FONT=assets/fonts/MyFont.ttf

# Paths used inside recipes only (quoted to survive spaces in ROOT).
NUMERAL_DATA := $(ROOT)/card-numerals.json
NUMERAL_SCRIPT := $(ROOT)/scripts/compose_numerals.py
NUMERAL_FONT ?=

# Target and prerequisite positions cannot contain spaces (Make splits on them).
# Use project-relative paths throughout; Make is expected to run from ROOT.
_RECTIFIED_PNGS_REL := $(wildcard illustrations-rectified/*.png)
_NUMERALLED_PNGS_REL := $(patsubst \
	illustrations-rectified/%.png, \
	illustrations-numeralled/%.png, \
	$(_RECTIFIED_PNGS_REL))

numeralled: $(_NUMERALLED_PNGS_REL)

illustrations-numeralled/%.png: illustrations-rectified/%.png card-numerals.json \
		scripts/compose_numerals.py | illustrations-numeralled
	python3 "$(NUMERAL_SCRIPT)" \
	  --card "$*" \
	  --source "$(ROOT)/illustrations-rectified/$*.png" \
	  --output "$(ROOT)/illustrations-numeralled/$*.png" \
	  --data "$(NUMERAL_DATA)" \
	  $(if $(NUMERAL_FONT),--font "$(NUMERAL_FONT)")

illustrations-numeralled:
	mkdir -p "$(ROOT)/illustrations-numeralled"

# ---------------------------------------------------------------------------
# Framing
# ---------------------------------------------------------------------------
#
# Adds the Ventnor cream border, gold rule lines, and title panel to each
# numeralled card → illustrations-framed/ at 1024 × 1536 (2:3).
#
# The art is scaled to fill the frame width; the bottom low-importance zone
# is cropped (reserved by design for the title panel).  All cards receive a
# title panel; Aces and courts additionally have no numeral at the top.
#
# Usage:
#   make framed                         Build / rebuild all framed cards
#   make illustrations-framed/id.png    Rebuild one card
#
# Incremental: a card is only recomposed when its numeralled source or
# card-numerals.json is newer than the existing output.
#
# Font: the script falls back to Times New Roman from the macOS system fonts.
# Override with FRAME_FONT:
#   make framed FRAME_FONT=assets/fonts/MyFont.ttf

FRAME_SCRIPT := $(ROOT)/scripts/compose_frame.py
FRAME_FONT ?=

_FRAMED_PNGS_REL := $(patsubst \
	illustrations-numeralled/%.png, \
	illustrations-framed/%.png, \
	$(_NUMERALLED_PNGS_REL))

framed: $(_FRAMED_PNGS_REL)

illustrations-framed/%.png: illustrations-numeralled/%.png card-numerals.json \
		scripts/compose_frame.py | illustrations-framed
	python3 "$(FRAME_SCRIPT)" \
	  --card "$*" \
	  --source "$(ROOT)/illustrations-numeralled/$*.png" \
	  --output "$(ROOT)/illustrations-framed/$*.png" \
	  --data "$(NUMERAL_DATA)" \
	  $(if $(FRAME_FONT),--font "$(FRAME_FONT)")

illustrations-framed:
	mkdir -p "$(ROOT)/illustrations-framed"

# ---------------------------------------------------------------------------
# Website assembly
# ---------------------------------------------------------------------------
#
# Assembles website/ from source layers.  Idempotent — safe to re-run.
# website/index.html is hand-authored and is never overwritten.
#
# Usage:
#   make website

website:
	bash "$(ROOT)/scripts/build-website.sh"
