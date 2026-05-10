# vti-slide-decorator — CHANGELOG

## v0.5.2 (2026-05-10) — Scope filter: skip special slides

Patch release. The decorator now skips special-page slides (cover, TOC,
section-divider, contact, closing, narrator pages) and only decorates
content slides (`.slide.layout-grid`). v0.5.0/v0.5.1 indiscriminately
decorated every `.slide` element, which polluted carefully-designed
specials — most visibly the section dividers, where the chevron+photo
composition had dot-cluster overlays bleeding through the empty
left-side area.

### What changed

- New `_SPECIAL_SLIDE_CLASSES` constant lists CSS classes that mark
  pre-designed slides: `page-cover`, `page-toc`, `page-section-divider`,
  `page-contact`, `page-closing`, plus narrator pages
  (`page-about-vti`, `page-awards-certifications`, etc.).
- New `_is_decoratable_slide(slide_html)` returns True only when the
  slide is `.slide.layout-grid` AND has none of the special classes.
- `decorate()` now filters the slide-spans loop: special slides are
  passed through unchanged into the output, decoratable slides go
  through the normal detect-classify-generate pipeline.
- `_enumerate_slides` is unchanged (still returns ALL slide spans);
  the per-slide filter happens in `decorate()`.

### Why this is a separate v0.5.2 patch

v0.5.0 W3.6 implementation was the right end-to-end pipeline; v0.5.1
fixed the position-override layout bug; v0.5.2 narrows scope. Each
release fixes one bug visible to users in deck v5. Splitting them
keeps the changelog readable and lets bisects stay precise.

### Verification on rebuilt v5 deck

Rebuilt `deck_v5.html` with the v3.13.1 page-builder + patched build
script (TOC + divider data fixed). Decorator processed:

| Slide # | Class | Action |
|---:|---|---|
| 1 | page-cover | skip |
| 2 | page-toc | skip |
| 3-7 | layout-grid | decorate |
| 8 | page-section-divider (Retail) | skip |
| 9-13 | layout-grid | decorate |
| 14 | page-section-divider (Medical) | skip |
| 15-20 | layout-grid | decorate |
| 21 | page-contact | skip |

16 decoration layers injected (matching 16 content slides), 0 layers
on any of the 5 special slides. Visual confirm on retail-wins
divider: clean stock chevron + VTI HQ photo, no dot/triangle overlays.

### Migration from v0.5.1

Idempotent re-run will strip stray decoration layers from special
slides and leave them clean. No code changes needed for callers.

### Open follow-up

- v0.5.x assumes the v3 page-builder class taxonomy (`layout-grid`,
  `page-cover`, etc.). If a custom shell uses different class names,
  add them to `_SPECIAL_SLIDE_CLASSES` or fork `_is_decoratable_slide`.
  Tracked as gap #45 (configurable scope filter) for v0.6+.

---

## v0.5.1 (2026-05-10) — Fix: position-override regression in injected CSS

Patch release. Reverts the `.vti-slide-content { position: relative }`
override that v0.5.0 injected via a sibling selector. That override
broke the page-builder's intended absolute-positioned content inset
(`left:56; right:56; top:70; bottom:64`), causing every content slide
to render with content stretched to the full 1280px slide width
instead of the intended 1168px. Visible symptom: text cut off at the
right edge on every decorated slide.

### Root cause

v0.5.0 injected this CSS:

```css
.vti-decoration-layer { z-index: 0; }
.vti-decoration-layer ~ .vti-slide-content,
.vti-decoration-layer + .vti-slide-content { position: relative; z-index: 1; }
.vti-decor { box-sizing: border-box; }
.vti-decor svg { display: block; width: 100%; height: 100%; }
```

The intent was to give `.vti-slide-content` a stacking context above
the decoration layer. But the page-builder already sets
`.layout-grid .vti-slide-content { position: absolute; left:56;
right:56; top:70; bottom:64 }`. Overriding to `position: relative`
threw away the right/bottom inset, and the content default `width:
auto` stretched to the full slide width 1280px → right edge of every
narrative paragraph (and every wide block) appeared clipped behind
the slide's `overflow: hidden`.

### Fix

Drop the position-override. Document-order stacking already places
the decoration layer (which comes BEFORE content as the slide's
first child) behind content. Both sit in the slide's positioning
context (slide is `position: relative`). Chrome elements (`.bc`,
footer) have explicit `z-index: 10` that keeps them on top.

v0.5.1 CSS:

```css
.vti-decoration-layer { z-index: 0; }
.vti-decor { box-sizing: border-box; }
.vti-decor svg { display: block; width: 100%; height: 100%; }
```

That's it. No position changes.

### Verification

Re-decorated `deck_v5_image_discipline.html` and measured every
content slide's `.vti-slide-content` at viewport 1280×720:

| Slide | position | left | right | content_w | scrollWidth |
|---|---|---|---|---|---|
| All 16 content slides | absolute | 56px | 56px | 1168 | 1168 |

Text now wraps within the intended 1168px region. Visual spot-check
on s13-medication-ai, s15-delivery, s20-talent confirmed:
- "...AI architecture, model **development**, mobile + web client." (full)
- "...VTI engages on a one-stop full-cycle delivery model: requirement **definition**..." (full)
- "...IT outsourcing · cutting-edge **software** & products · education / human resources..." (full)

All previously-truncated text now fits.

### Migration from v0.5.0

If you generated decorated decks with v0.5.0, re-run `decorate()` —
it's idempotent and will replace the bad CSS with the fixed version
on first run. (The CSS marker comment changed from v0.5 to identical
text but the offending sibling selectors are gone.)

### Caveat: viewport-narrower-than-slide remains

Slides are fixed `width: 1280px; overflow: hidden`. Viewing the deck
in a viewport narrower than 1280px (e.g. Claude.ai's preview pane,
or a phone) WILL show the right edge clipped — that's a property of
the slide canvas, NOT a regression. To make slides responsive, wrap
each slide in a scaled-down container; this is out of scope for
v0.5.x and tracked as gap #44 (decorator-side responsive scaling)
for v0.6+.

---

## v0.5.0 (2026-05-10) — Coordinated 3-skill baseline · W3.6 pipeline implemented

Minor release. Implements the W3.6 pipeline that was a STUB in v0.1
(`decorate()` raised `NotImplementedError`). The decorator is now
end-to-end usable on a composed deck.

This release lands together with:
- vti-slide-creator v3.19.0 (gap #42 + density_mode propagation)
- vti-slide-page-builder v3.13.0 (mode-aware fill thresholds)

### `decorate(deck_html_path, output_path, ...)` — fully wired

The pipeline:
1. Read deck HTML from disk.
2. **Idempotency guard**: if the deck already carries decoration
   layers, strip them from the HTML used to render screenshots — so
   gap detection sees the clean composition. The output deck still
   has decorations re-injected; running `decorate()` twice produces
   structurally equivalent results (same layer count, same strategy
   distribution per slide).
3. Render screenshots via Playwright (chromium) per slide, using
   the existing `screenshot_slides()` helper.
4. Enumerate slide spans in the source deck HTML using a
   depth-tracking scanner that handles nested `<div>`s.
5. For each slide:
   - `detect_gaps(screenshot)` (whitespace_analyzer)
   - `classify_slide_gaps(gaps, slide_meta)` (gap_classifier)
   - `select_strategy(slide_html, classified, slide_meta)` (W3.5,
     newly implemented; see below)
   - For each eligible classified gap, call the strategy's
     `generate(cg, slide_meta=meta, slide_size=(w, h))` to get an
     SVG fragment.
   - Inject all fragments as one `<div class="vti-decoration-layer">`
     positioned absolute, z-index 0, pointer-events none.
6. Inject decoration-layer CSS once into `<head>`.
7. Write decorated HTML to `output_path` if supplied; return as string.

### `select_strategy` — proper W3.5 implementation

Pre-v0.5 this was a stub returning `'typographic'` whenever any gap
was eligible. v0.5 implements section-biased selection:

```python
_SECTION_STRATEGY_BIAS = {
    "ABOUT VTI":     ["typographic", "abstract_geometric"],
    "SERVICES":      ["abstract_geometric", "typographic"],
    "RETAIL CASES":  ["topical_motif", "abstract_geometric"],
    "MEDICAL CASES": ["topical_motif", "abstract_geometric"],
    "WHY VTI":       ["typographic", "abstract_geometric"],
    "FORWARD":       ["abstract_geometric", "topical_motif"],
}
```

Algorithm:
1. No gaps → `'none'`.
2. Pick the largest decoration-eligible classified gap (focal).
3. Apply section bias for the slide's `section_name`.
4. Intersect bias with focal's `compatible_strategies`.
5. Return first match, or focal's first compatible strategy if no bias hit.

### `decorate_slide(slide_html, slide_meta, screenshot_path, ...)`

Single-slide entry point. Used internally by `decorate()` but also
useful for partial decoration (e.g. decorate only one slide of a deck
in isolation). Returns the slide HTML with decoration layer injected.

### `decorate_html(deck_html, ...)`

String-in / string-out variant. Useful for chained pipelines where
the caller has the deck HTML in memory.

### Idempotency

Three layers of idempotency:

1. **HTML strip** — `_strip_decoration_layer` removes existing
   `<div class="vti-decoration-layer">…</div>` (with leading
   whitespace) so re-injection doesn't compound.
2. **Pre-render strip** — when `decorate()` detects existing
   decoration layers in the input deck, it writes a stripped copy
   for the screenshotter, so gap detection sees clean composition.
3. **CSS injection guard** — `_ensure_decoration_css` checks for the
   v0.5 marker comment before injecting, so multiple runs don't
   duplicate the `<style>` block.

The combination guarantees: `decorate(decorate(d)) == decorate(d)` at
the structural level (same layer count, same strategies). Byte-equal
when Playwright produces deterministic screenshots; in practice
near-byte-equal with anti-aliasing micro-differences.

### Compatibility shims

The v0.1 module exposed `classify_gap` returning a small dict; v0.5
keeps that name as a wrapper around `gap_classifier.classify_gap` so
external callers don't break.

### Smoke tests

| Test | Result |
|---|---|
| `__version__ == '0.5.0'` | ✓ |
| `pipeline_status()` shows all stages IMPLEMENTED except `audit` | ✓ |
| `_strip_decoration_layer(_inject_overlay(s, o)) == s` | ✓ |
| `_ensure_decoration_css(_ensure_decoration_css(d)) == _ensure_decoration_css(d)` | ✓ |
| `_enumerate_slides` finds all 4 slides in a 4-slide test deck | ✓ |
| `decorate(test_deck) → decorated HTML with 2 layers, slides preserved` | ✓ |
| `decorate(decorated_deck)` structurally idempotent (same layer count, same strategies) | ✓ |

### Known limitations

- `audit` step (Lighthouse-style decoration audit) remains a STUB —
  planned for v0.6.
- `select_strategy` uses section bias only; could also keyword-scan
  slide content for richer signals (gap #43 in coordinated baseline
  follow-up list).
- Screenshot rendering depends on Playwright + chromium being
  installed; raises ImportError if missing. Document this dependency
  in deployment instructions.
- One decoration is generated per eligible gap; some strategies
  (especially `typographic`) can compound visually if a slide has
  many small gaps. Mitigated by `MIN_ELIGIBLE_AREA_PX2` in
  `gap_classifier.py` (default 100K px²); tune per deck if needed.

### Migration from v0.1

The v0.1 `decorate()` raised `NotImplementedError` so any prior
caller would be wrapped in try/except. Replace those try blocks with
direct calls.

If you used `decorate_slide()` (also stubbed in v0.1), v0.5 changes
its signature: the keyword `screenshot_path` is now positional.
External callers should be rare — most code goes through `decorate()`.

### Cross-skill contract (creator → page-builder → decorator)

All three skills agree on `slide_meta` shape:

```python
slide_meta = {
    'page_number':    int,
    'page_total':     int,
    'doc_title':      str,
    'copyright_year': int,
    'section_name':   str,
    'slide_title':    str,
    'show_chrome':    bool,        # default True
    'layout_class':   str,         # 'default' | 'case-study' | 'data-dense'
    'density_mode':   str,         # 'standard' | 'sparse-ok' | 'dense'
}
```

The decorator reads `section_name` for strategy biasing. It does NOT
inspect `density_mode` directly — but the rendered screenshots reflect
mode-driven layout outcomes, so density_mode indirectly shapes the
gaps the decorator sees.
