# vti-slide-pptx-exporter

**Version: 1.0.0**

Exports a composed VTI deck (`work/deck-composed.html` or
`work/deck-decorated.html`) into a `.pptx` file. Each slide is rendered
as a high-DPI PNG via headless Chromium and pasted full-bleed into a
16:9 PowerPoint slide. Speaker notes (presentation script + delivery
hints) are written into each slide's notes pane.

> **Position in the pipeline.** Strictly post-compose. Run **after**
> Phase 6 (and optionally after `vti-slide-decorator`). This skill does
> not modify the deck HTML — it consumes the final rendered HTML and
> writes a sibling `.pptx`.

```
vti-slide-creator (Phase 1–6) → work/deck-composed.html
   ↓ (optional)
vti-slide-decorator           → work/deck-decorated.html
   ↓
vti-slide-pptx-exporter       → work/deck.pptx     ← this skill
```

## When to use

Invoke when the user asks to:

- "Xuất deck ra PPTX / PowerPoint"
- "Convert deck thành slides PPT"
- "Export each slide as image + put into PPTX"
- "Generate speaker notes / presenter notes"
- "Tạo file .pptx có notes trình bày"

Do **not** invoke during composition or as part of phase 1–6 — wait
until the deck HTML is final.

## Inputs

| Input | Source | Required |
|---|---|---|
| Deck HTML | `work/deck-composed.html` or `work/deck-decorated.html` | yes |
| Phase 2 JSON (outline) | `work/phase_2.json` | optional (for baseline notes) |
| Phase 3 JSON (content blocks) | `work/phase_3.json` | optional (for baseline notes) |
| Notes overrides | `work/pptx-notes.json` | optional (per-slide hand-crafted notes) |

## Outputs

| Output | Description |
|---|---|
| `work/pptx-images/slide_{NN}.png` | One PNG per slide (1280×720 × scale). Cached — re-uses unless `force=True`. |
| `work/pptx-notes.json` | Speaker notes per slide (script + hints). Seeded from phase JSONs on first run, then user-editable. |
| `work/<html-stem>.pptx` | Final PowerPoint file (16:9, 13.333" × 7.5"). Same stem as the input HTML — see Filename inheritance below. |

## Filename inheritance

When `out_pptx` is omitted, the exporter writes the .pptx alongside
the input HTML with the same stem. Pair this with vti-slide-creator's
`deck_filename()` and the PPTX automatically follows the VTI
convention:

```
work/VTI_Day-to-Day-Info-Summarization-Agent_v1.0.html   (input)
work/VTI_Day-to-Day-Info-Summarization-Agent_v1.0.pptx   (output, default)
```

Pass an explicit `out_pptx` only when you want a name that differs
from the HTML.

## Public API

All entrypoints live in `exporter.py`:

```python
from exporter import (
    render_slides_to_pngs,   # HTML → PNGs (one per .slide section)
    build_pptx,              # PNGs + notes → .pptx
    export_deck,             # convenience: both steps + notes-seed
)
from notes_builder import derive_notes_from_phases
```

### `export_deck(html_path, out_pptx, ...) → Path`

One-call export. Handles render + pptx assembly + notes seeding.
Idempotent: re-running won't re-render PNGs that already match the
deck HTML mtime, and won't overwrite a user-edited `pptx-notes.json`.

```python
export_deck(
    html_path='work/VTI_<title>_v1.0.html',
    out_pptx=None,                        # default: <html-stem>.pptx
    images_dir='work/pptx-images',
    notes_path='work/pptx-notes.json',
    phase_2_path='work/phase_2.json',     # for baseline notes
    phase_3_path='work/phase_3.json',     # for baseline notes
    deck_title=None,                      # default: <title> from HTML
    scale=2,                              # 2× DPI for crisp text
    force_render=False,                   # re-render PNGs even if cached
    force_notes=False,                    # overwrite pptx-notes.json
)
```

### `render_slides_to_pngs(html_path, out_dir, scale=2, force=False) → list[Path]`

Loads deck once in headless Chromium, locates every `<section class="slide ...">`,
and screenshots each element. Files are named `slide_01.png`, `slide_02.png`, …

Requires Playwright + a Chromium install (see Requirements below).

### `build_pptx(image_paths, notes, out_pptx, deck_title=None) → Path`

Assembles the final PPTX. `notes` is a dict keyed by 1-based slide
index: `{1: {"script": str, "hints": str}, 2: {...}, ...}`. Missing
entries get blank notes (no error).

### `derive_notes_from_phases(phase_2_path, phase_3_path) → dict[int, dict]`

Produces a baseline `{idx: {script, hints}}` from the outline + block
content. The script stitches together narrative paragraphs / card
bodies / hero stats into spoken prose. Hints are inferred from block
kinds (e.g., `hero_stat` → "pause for emphasis", `features_3` → "walk
through cards left-to-right").

**This is a starting point, not the final narration.** Expect Claude
or the user to revise `work/pptx-notes.json` before the final build.

## Notes shape

`work/pptx-notes.json` is a list parallel to the rendered slides:

```json
[
  {
    "slide_index": 1,
    "slide_title": "Cover",
    "script": "Spoken narration goes here. Multiple paragraphs OK.",
    "hints": "Delivery cues — pacing, emphasis, transitions, gestures."
  },
  ...
]
```

When written into PPTX notes pane, the two fields are joined with a
clear separator:

```
═══ TRÌNH BÀY ═══
<script>

═══ GỢI Ý ═══
<hints>
```

## Requirements

```bash
pip install python-pptx playwright
python -m playwright install chromium
```

`python-pptx` is already pinned in the repo's `.venv`. Playwright +
chromium need a one-time install on first use; the exporter raises a
clear error with the install command if missing.

## Driver pattern (per-deck)

Like the rest of the VTI pipeline, the driver lives in `scripts/` and
is per-deck (gitignored, wiped by `reset.sh`). Minimal template:

```python
# scripts/build_pptx.py
from pathlib import Path
from exporter import export_deck

ROOT = Path(__file__).resolve().parents[1]
export_deck(
    html_path=ROOT / 'work' / 'deck-composed.html',
    out_pptx=ROOT / 'work' / 'deck.pptx',
    images_dir=ROOT / 'work' / 'pptx-images',
    notes_path=ROOT / 'work' / 'pptx-notes.json',
    phase_2_path=ROOT / 'work' / 'phase_2.json',
    phase_3_path=ROOT / 'work' / 'phase_3.json',
)
```

Run it twice: once to seed notes, then again after editing
`pptx-notes.json` to embed the revised narration.

## Out of scope (intentionally)

- Per-slide animation / transitions — PPTX gets static images, no
  PowerPoint animations.
- Editable text in PPTX — slides are flattened to images. To change
  copy, fix the HTML/phase JSON and re-export.
- Video / embedded media — only static visuals.
- Theme / template inheritance — output uses python-pptx's default
  16:9 blank layout. Visual branding is baked into the image.
