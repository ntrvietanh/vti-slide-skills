# Changelog — vti-slide-pptx-exporter

## 1.1.0 — 2026-05-20

- `export_deck()` `out_pptx` is now optional — defaults to
  `<html_path>.with_suffix('.pptx')` so the PPTX inherits the VTI
  deliverable filename stem from the input HTML
  (see `vti-slide-creator/deck_filename.py`).
- SKILL.md documents the inheritance contract.

## 1.0.0 — 2026-05-20

Initial release. Post-compose skill that turns a finished VTI deck
HTML into a PowerPoint (.pptx) file with speaker notes.

- `exporter.render_slides_to_pngs()` — uses Playwright (headless
  Chromium) to screenshot each `<section class="slide">` at
  1280×720 × scale. Cached by deck-HTML mtime.
- `exporter.build_pptx()` — assembles a 16:9 PPTX (13.333" × 7.5"),
  one image-fill slide per PNG, notes written into each slide's
  notes pane via `notes_text_frame`.
- `exporter.export_deck()` — convenience wrapper: render + seed
  notes + build, idempotent.
- `notes_builder.derive_notes_from_phases()` — baseline narration
  from `phase_2.json` (outline) + `phase_3.json` (block content).
  Vietnamese script + per-block-kind delivery hints. Output shape
  is a list-of-records parallel to slide order.
- Special-slide narration handled separately for `cover`, `toc`,
  `contact`, `closing`, `section`.
- Requires: `python-pptx` (already in repo `.venv`), `playwright`
  + chromium (one-time `pip install playwright && python -m
  playwright install chromium`).
