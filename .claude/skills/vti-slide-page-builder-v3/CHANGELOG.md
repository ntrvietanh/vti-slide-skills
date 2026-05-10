# vti-slide-page-builder-v3 — CHANGELOG

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
- vti-slide-creator-v3 v3.19.0 (gap #42 + density_mode propagation)
- vti-slide-decorator v0.5.0 (W3.6 pipeline implemented)

### `_DENSITY_MODE_THRESHOLDS` table

Mirrors `vti-slide-creator-v3/capacity.DENSITY_MODES`:

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
