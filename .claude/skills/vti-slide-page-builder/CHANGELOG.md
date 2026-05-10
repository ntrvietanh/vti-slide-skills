# vti-slide-page-builder — CHANGELOG

## v3.13.9 (2026-05-10) — practice-card: elevation shadow

Cosmetic only. Adds a two-layer `box-shadow` to `.vti-practice-card` so cards
lift off the slide background instead of relying solely on the 0.5px hairline
border. Tuned at rgba ≈0.04 / ≈0.08 with larger blur (6px / 28px) and a -4px
spread on the diffuse layer — soft, diffused lift well short of Material
elevation.

## v3.13.8 (2026-05-10) — slide_meta.vertical_align flag for vertical centering

Additive opt-in. Default behavior unchanged. New `slide_meta.vertical_align`
field accepts `"start"` (default) or `"center"`. When `"center"`, the inner
grid container gets a `vti-grid--center` modifier class which overrides
`align-content: start` to `align-content: center` — leftover space is split
between the top and bottom of the canvas instead of dumping it all under the
last row.

Use case: sparse slides like `engagement-models` (3 practice-cards + narrative
+ kpi-row) that fill ~60% of vertical space and look bottom-anchored. Authors
opt in per-slide, so dense slides still anchor from the top.

`row.height: 1fr` rows continue to work as before (1fr expands to fill, so
align-content has no effect on those rows). Pure-`auto` slides are the ones
that benefit from this flag.

## v3.13.7 (2026-05-10) — icon palette: 6 additions (eye, message, sparkles, wifi, cpu, bell)

Additive only. Existing 16 icon names unchanged. Adds:

- `eye` — vision / Computer Vision
- `message` — NLP / chat / conversational
- `sparkles` — Generative AI / innovation
- `wifi` — wireless / connectivity / RF tier
- `cpu` — edge compute / gateway hardware
- `bell` — alert / rules engine / notification

Motivation: KPI cards on the StarHub deck (and `icon-list` rows on
slides 7 + 25) were rendering blue empty discs because authors used
glyphs (`◎`, `◯`) or non-existent names — `render_icon` returned `''`
which the icon-disc CSS still paints as a flat blue circle. The
existing palette covered structural / business semantics but had gaps
for AI capability bands (CV / NLP / GenAI) and IoT eldercare RF-tier
labels. These 6 additions close those gaps without changing any
existing renderer.

`catalog()` now reports 22 icons (was 16). No prop schema changes.

## v3.13.6 (2026-05-10) — image-tile: optional `bg` flag to suppress frame background

Additive prop. The default soft frame paints `--vti-paleblue` behind
the image — fine for screenshots/photos, but redundant when the
embedded SVG diagram already carries its own pale-blue rectangle (e.g.
`s22-omron`, `s27-eldercare-pillars`, `s28-telemedicine`). The double
band reads as two stacked frames.

New prop `bg: 'default' | 'none'` (default `'default'`, fully
backwards-compatible). Setting `bg: 'none'` adds a
`vti-image-tile--no-bg` modifier that zeros out both the figure-level
fill and the soft-variant's letterbox color. No effect on caption,
aspect, or frame radius — purely the background paint.

## v3.13.5 (2026-05-10) — practice-card: compact horizontal header for icon variant

Layout tweak. The icon variant of `practice-card` previously stacked
the icon ABOVE the title with `min-height: 144px` on the top region
and a 48-px icon. That hero footprint forced 5/6/7-card capability
grids to drop their trailing narrator paragraph for vertical space —
slides 10, 14, 25 lost their "synthesis" copy.

Fix: switch the icon variant's `.vti-practice-card__top-content` from
`flex-direction: column` to `row` (icon-left, title-right), shrink the
icon to 36 px, drop `min-height` to 88 px, tighten padding. The
no-icon variant is unchanged. Saves ~55 px of card height — the
narrator paragraph now fits below the grid on dense capability slides.



Patch release. `image-tile` and per-entry `logo-grid` images previously
crashed silently when an upstream drafter handed in a dict like
`{"path": "...", "alt": "..."}` instead of a plain string path. The
renderer ran `_esc(image)` which did `str(dict)` and emitted
`src="{'path': '...', 'alt': '...'}"` straight into the HTML. The
browser couldn't load it, so 17 image-tiles in the production retail
deck rendered as empty bordered figures with only the figcaption
visible — which Michael flagged as "rất nhiều block trắng có 1 dòng
text bên dưới."

Fix: new `_normalize_image_src` helper at the renderer boundary
accepts EITHER `str` (path/URL/data URI) OR `{"path": str, "alt"?: str}`
dict, extracts the path, and propagates `alt` to the `<img alt>`
attribute when no caption is present. Anything else (int, list, dict
without `path`) raises a clear `ValidationError` so any future
regression surfaces immediately at compose time instead of silently
shipping broken HTML.

Both `_r_image_tile` (line 745) and `_r_logo_grid` (line 891) go
through the same helper. No upstream API change — drivers can keep
emitting either shape.

## v3.13.3 (2026-05-10) — Fix: project-relative asset paths now resolve

Patch release. `compose_slide_grid` previously searched only
`[SKILL_ROOT]` for `<img src="…">` and `url(…)` references, so
project-root-relative paths produced by upstream skills (e.g. the
creator's Phase-3 lift cache writing `work/extracted_images/foo.png`)
silently 404'd in the rendered HTML — every lift screenshot in the
StarHub deck rendered as bare alt-text.

Fix: search list is now `[SKILL_ROOT, Path.cwd()]`. SKILL_ROOT keeps
priority so internal asset names (`assets/x.png`) still resolve to the
skill, but project paths now also work when drivers run from the
project root (the standard `source scripts/setup.sh` flow).

Also confirmed first production use of `row_span > 1` on cells. The
field has been validated since v3.x but unused; the creator's
`image-aside-stack` patterns (creator v4.3.0) now emit
`row_span=N` on image cells. No page-builder change needed —
existing emission of `grid-row: ri / span N` already handles it.

No API change. Single touch: `compose_slide_grid` line ~3947.

## v3.13.2 (2026-05-10) — Fix: image-tile soft frame no longer crops

Patch release. The v3.19 deck output had every SVG architecture
diagram cropped on the right side because:

- Caller (v3.19 build scripts) passed `aspect_ratio: "16:9"` for cells
  hosting SVGs whose viewBox was 1180×460 (≈2.56:1).
- `image-tile` `<img>` styled with `object-fit: cover` cropped the SVG
  to fit the 16:9 frame, losing the right ~30% of every diagram.

The clean architectural fix (creator-v3 v4.0) is to set the cell's
`aspect_ratio` to match the image's natural ratio so cropping never
applies. This patch is the **defense-in-depth complement**: even if a
future caller passes a wrong `aspect_ratio`, the `--soft` frame variant
now uses `object-fit: contain` so the image is at least fully visible
(letterboxed in pale-blue) instead of cropped.

The default `cover` behaviour is preserved for `--rounded` and
`--square` frames where cinematic edge-crop is the desired aesthetic
(hero photos, group shots).

### Files

- `components/image-tile/component.css` — added
  `.vti-image-tile--soft .vti-image-tile__img { object-fit: contain; }`

---

## v3.13.1 (2026-05-10) — Fix: TOC entry-text aliasing

Patch release. The TOC special-page template uses
`{{this.title}}` for entry text, but external callers (notably the v3.x
deck-build scripts) historically pass `label`. Without normalization
those entries rendered as bullets + page numbers WITHOUT any text —
the most visible symptom in deck v5 v3.12 output.

v3.13.1 adds `_normalize_toc_items` in `compose_special_page` that
maps `label` / `name` / `section` → `title` (only when `title` is
absent or empty). Recurses into nested `items` for sub-bullets.

### Backward compatibility

Zero changes for callers that already pass `title`. New aliases are
additive — first non-empty wins, so explicit `title` always takes
precedence over an alias.

### Smoke tests

```python
# v3.x build script style — `label` field
result = pb.compose_special_page('toc', {'toc_items': [
    {'label': 'ABOUT VTI', 'page': 3},
    {'label': 'SERVICES',  'page': 6},
]})
# → renders with "ABOUT VTI", "SERVICES" entry text (was empty in v3.13.0)

# Canonical creator API — `title` field
result = pb.compose_special_page('toc', {'toc_items': [
    {'title': 'ABOUT VTI', 'page': 3},
]})
# → still works (was working in v3.13.0 too)
```

### Why a patch (not minor)

Single targeted bug fix; no schema additions; no API surface changes.
Patch level is appropriate.

---

## v3.13.0 (2026-05-10) — Coordinated 3-skill baseline · density_mode threshold profiles

Minor release. Closes the page-builder side of gap #32 (density-mode
toggle). Adds three named density profiles for the gap-E fill-honesty
checks; reads `slide_meta.density_mode` from the input passed to
`compose_slide_grid`.

This release lands together with:
- vti-slide-creator v3.19.0 (gap #42 + density_mode propagation)
- vti-slide-decorator v0.5.0 (W3.6 pipeline implemented)

### `_DENSITY_MODE_THRESHOLDS` table

Mirrors `vti-slide-creator/capacity.DENSITY_MODES`:

| Mode | cell_fill_min | slide_sparse_below | slide_overcrowded_above |
|---|---:|---:|---:|
| `standard` | 70% | 40% | 115% |
| `sparse-ok` | 50% | 20% | 115% |
| `dense` | 80% | 55% | 125% |

`standard` is the legacy v3.7-v3.12 hardcoded behavior — no behavioral
change for callers that don't set `slide_meta.density_mode`. The
'sparse-ok' profile tolerates breathing/hero slides; 'dense' tolerates
spec-sheet detail.

### `_validate_fill_honesty` is mode-aware

```python
# Pre-v3.13 hardcoded thresholds; v3.13 reads from profile.
warnings = _validate_fill_honesty(rows, where_prefix,
                                   density_mode='sparse-ok')
```

When called from `_compose_grid_body`, `density_mode` is sourced from
`slide_meta.density_mode` (set by creator's `plan_to_slide_input`).
Defaults to `'standard'` if absent or unknown, preserving v3.12 behavior.

### `compose_slide_grid` accepts `slide_meta.density_mode`

New optional field on `slide_meta`:

```python
slide_input = {
    'slide_meta': {
        'page_number': 9, 'page_total': 21,
        'doc_title': '...', 'section_name': 'RETAIL CASES',
        'slide_title': '...', 'layout_class': 'default',
        'density_mode': 'sparse-ok',   # v3.13 — optional, default 'standard'
    },
    'rows': [...],
}
```

Validation: must be one of `'standard'` / `'sparse-ok'` / `'dense'`.
Unknown values raise `ValidationError`.

### Smoke tests

| Test | v3.12.0 | v3.13.0 |
|---|---|---|
| 29% fill, mode=standard → SPARSE warning | hardcoded 40% | profile-driven 40% (same) |
| 29% fill, mode=sparse-ok → no warning | N/A | profile 20% threshold |
| 29% fill, mode=dense → SPARSE warning | N/A | profile 55% threshold |
| 50% fill, mode=dense → SPARSE warning | N/A | ✓ |
| Unknown mode raises ValidationError | N/A | ✓ |
| Default mode='standard' for plans without field | N/A | ✓ (backward compat) |

### Migration from v3.12.0

Zero breaking changes. Pre-v3.13 callers that don't set
`slide_meta.density_mode` continue to use the same hardcoded thresholds
(now exposed as the `'standard'` profile).

To use density modes end-to-end, set `plan['density_mode']` at Phase 4
in the creator skill — `plan_to_slide_input` will propagate it into
`slide_meta`, and the page-builder will pick it up.

### What this release does NOT change

- `BLOCK_KIND_CAPS` (per-component schema caps in creator's
  `capacity.py`) — these are absolute render invariants, NOT relaxed
  by density modes. `'dense'` mode lets you draft to 95% of declared
  cell capacity, but you can't exceed `narrative.paragraphs_each_max=400`
  regardless of mode. Re-tightening this would require a separate
  design decision and is out of scope for the v3.13 release.
- Component capacity declarations (`capacity_chars_per_col`,
  `capacity_chars_fixed`) — unchanged. Mode adjusts thresholds, not
  the underlying capacity numbers.
