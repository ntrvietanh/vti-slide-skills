# vti-slide-skills · Coordinated 4-Skill Baseline · 2026-05-19

This bundle pins four skills at versions that work together as a coordinated set. Use these together — they share contracts that previous-version mixes did not. **v4.0 baseline** — phase pipeline restructured 5 → 6, new `vti-slide-diagram-builder` skill added. **2026-05-19 ripple** — diagram-builder v0.4.0 brand-discipline pass adds the `captions` strip contract; layout_designer and image-tile updated to forward it. **2026-05-19 (afternoon) revert** — diagram-builder v0.5.0 restores the v0.1.0 native-SVG branch alongside the v0.3.0 Mermaid branch because Mermaid-cli outputs had unpredictable aspect ratios (1.35 → 14.17 depending on content) that broke Phase 4 cell sizing; SVG is the new default backend with Mermaid retained as an opt-in.

## Versions

| Skill | Version | Bumped from |
|---|---|---|
| `vti-slide-creator` | **4.8.0** | 4.7.0 (**M2** `build_deck_html` injects the ECharts runtime once per deck when a chart is present; **M3** Phase 4 → DESIGN art-director — 6-step scaffold + `realize_archetype` selection/fill, Phase 5 → realize+validate, new `art_direction.py` Art Direction Brief + `ration_archetypes`; old scorer kept as image-dominant fallback) |
| `vti-slide-creator` (prev) | 4.7.0 | 4.6.1 (`layout_designer` forwards `diagram_spec.captions` through `_image_cell_props` so the page-builder can render the per-step caption strip beneath synthesized diagrams; Phase 3 (CONTENT-PLAN) guidance updated with the action-label / captions-strip authoring contract paired to diagram-builder v0.4.0) |
| `vti-slide-page-builder` | **4.4.0** | 4.3.0 (finish ECharts: gauge-dial / progress-bar / funnel → ECharts gauge / track-bars / funnel; new cell `valign` option (center\|bottom) fixes pull-quote-style content floating at the top of a 1fr row, applied in quote-impact + stat-anchor archetypes) |
| `vti-slide-page-builder` (prev) | 4.3.0 | 4.2.0 (**M4 — visual critique loop**: new `visual_critic.py` renders+measures each slide (min-font / overflow / blank-chart / ink-ratio+centroid / neighbour-dup); `auto_repair` light loop auto-applies only the safe sparse-top → `vertical_align:center` fix; `render_review` builds a sighted Phase-6 review sheet (real PNGs + verdict badges); reuses Pillow, additive) |
| `vti-slide-page-builder` (prev) | 4.2.0 | 4.1.0 (**M3 — archetype library + cell surfaces**: new `archetypes.py` — 12 curated asymmetric/intentful layouts with `list_archetypes`/`describe_archetype`/`slots_for`/`realize_archetype` → `slide_input`; cells gain `surface = panel|tint|elevated` (light containers via `_GRID_CSS`); `catalog(verbose=True)` now returns `archetypes` + `cell_surfaces`; purely additive — deterministic scorer kept as fallback) |
| `vti-slide-page-builder` (prev) | 4.1.0 | 4.0.0 (**M2 — ECharts data charts**: bar/pie/line/stacked-bar render via vendored Apache ECharts 5.5.1 SVG renderer (`echarts_specs.py` + `vendor/echarts.min.js`); unchanged prop contract; runtime injected once per deck only when a chart is present; `animation:false` + svg renderer → synchronous paint + `window.__vtiChartsReady` flag that exporter/figma renderers wait on, so PPTX/PNG never screenshot a blank chart; fixes the `tone="sky"`→black-bar bug) |
| `vti-slide-page-builder` (prev) | 4.0.0 | 3.18.5 (**M1 — fluid typography**: the 5 fixed px type tokens in `tokens.css` became `clamp(min, calc(base + B·cqw), max)` + two new steps `--vti-fs-lead`/`--vti-fs-small`; `.vti-grid-cell` carries `container-type: inline-size` so `cqw` resolves per-cell; each clamp MAX = the old fixed px so container-less contexts (chrome/special-pages) are unchanged; all 113 hardcoded `font-size: Npx` across 37 component CSS files migrated to `var(--vti-fs-*)`; weights 300/700 re-opened for display/hero only; type-budget audit collapses lead→body, small→caption) |
| `vti-slide-decorator` | **0.5.2** | unchanged |
| `vti-slide-diagram-builder` | **0.6.0** | 0.5.0 (**M2 — depth pass**: `svg_open` injects shared `<defs>` — per-accent vertical gradients + soft `feDropShadow` + line-icon symbols; `svg_box`/`svg_box_filled` fill with gradient + carry the soft shadow; quadrant cells lifted with the same shadow; connectors darkened muted→ink-soft; `svg_icon()` helper available for M3. All colours via the token bridge — no hex literals) |
| `vti-slide-diagram-builder` (prev) | 0.5.0 | 0.4.0 (native-SVG branch restored alongside the v0.3.0 Mermaid branch — 5 dual-backend primitives `flow_diagram`, `quadrant`, `layered_stack`, `fanout_pipeline`, `hybrid_swimlane` now accept `backend="svg"|"mermaid"` with `svg` as default; `VTI_DIAGRAM_BACKEND` env override; SVG outputs land at predictable canvases 1180×280/320 horizontal flow, 1180×480/520 others; v0.4.0 brand discipline / `_assert_step_clean` validator / captions baked into bottom strip all preserved) |
| `vti-slide-figma-mockup` | **0.1.0** | NEW (8 Figma-backed UI mockup / wireframe / demo-screenshot kinds — `screen-mobile`, `screen-tablet`, `screen-desktop`, `screen-bare`, `flow-mobile`, `flow-desktop`, `wireframe-mobile`, `wireframe-desktop`; emits Figma render tasks for orchestrator to execute via Figma MCP; `mockup_executor.record_render` lands `work/mockups/<id>/{render.png, render.svg?, meta.json}` + auto-appends `work/mockups/INDEX.md`; v0.1.0 wires into Phase 3 via `lift`-strategy stop-gap using `to_resolved_image()` — native `image_decision.strategy="mockup"` integration deferred to a follow-up creator bump) |

## What this baseline closes

**v4.0 (2026-05-10):** restructures the pipeline to fix three structural bugs the v3.19 deck output exposed (SVG cropping in `image-tile`, lift resolver picking junk, sparse layouts when image was small):

| # | Bug / change | Closed in |
|---:|---|---|
| 50 | SVG diagrams cropped because of hardcoded 16:9 aspect | creator 4.0 (`layout_designer` sets cell aspect = natural) + page-builder 3.13.2 (`object-fit: contain` for soft frames as defense-in-depth) |
| 51 | Lift resolver picked icons / chrome via positional heuristic | creator 4.0 (`resolve_lift_image()` uses `classify_image_kind` from source_ingester) |
| 52 | No layout-design phase — Phase 5 ran component-pick + layout in one step | creator 4.0 (Phase 4 LAYOUT-DESIGN split out of Phase 5) |
| 53 | Diagram drawing was per-deck ad-hoc Python; no VTI Standard | new sibling `vti-slide-diagram-builder` v0.1.0 (7 primitives, brand-token-driven) |
| 54 | Outline review was a separate phase, redundant | creator 4.0 (Phase 2 merged outline + review) |
| 55 | No batch wireframe review before final compose | creator 4.0 (Phase 6 REVIEW-AND-COMPOSE) |
| 56 | Image-aside layouts wasted right-column space; KPI/list rows fell to a full-width strip below the image | creator 4.3.0 (`_design_image_aside_stack` uses `row_span` so the image cell stretches across N right-column rows) |
| 57 | Project-relative image paths (e.g. lift cache `work/extracted_images/…`) silently rendered as alt-text | page-builder 3.13.3 (`compose_slide_grid` searches `[SKILL_ROOT, Path.cwd()]`) |
| 58 | `resolve_lift_image()` heuristic (filename-token + aspect-ratio score) gave every slide of a multi-slide case study the same image and let corporate filler (logos, cert badges, exec portraits) pass as content | creator 4.4.0 (`image_picker.py` — 4-step orchestrator-in-the-loop protocol: enumerate → caption → decide → auto-escalate `lift`/`synthesize`/`text-only`; `allocate_case_study_images` enforces 1-to-1 best-fit across multi-slide CS) |
| 59 | Drafters that handed a `{path, alt}` dict to `image-tile.props.image` (carrying source-asset metadata forward) silently produced `src="{'path': ..., 'alt': ...}"` in HTML — 17 image-tiles in the retail deck rendered as empty bordered figures with only the figcaption visible | page-builder 3.13.4 (`_normalize_image_src` at the renderer boundary in `_r_image_tile` and `_r_logo_grid` — accepts `str` or `{path, alt}`, raises `ValidationError` for any other shape so the regression cannot return) |
| 60 | Mermaid diagrams produced "rainbow swimlanes" (per-element accent params drifted to 4–6 different brand colours per slide) and nodes packed metrics next to step names (`"BATCH-STAMP / 180+ inactive · 1 Drive write"`) — readers parsed digits and missed the action narrative | diagram-builder 0.4.0 (blue-mono gradient via `gradient_classdefs(n)`; round-edge `(label)` shape; `_assert_step_clean` validator raises on metric tokens in labels; new `captions: list[str]` strip rendered by page-builder 3.13.5 beneath the SVG) |
| 61 | Mermaid-cli output sized the SVG to its laid-out content with very loose external bounds — flow_diagram came back at aspect 14.17, layered_stack at 8.62, etc. Phase 4 sized host cells against the hint_w/hint_h constants and the resulting cells either letterboxed the diagram (≤30% fill) or cropped past lane borders | diagram-builder 0.5.0 (native-SVG branch restored from v0.1.0 as a parallel rendering backend; default flips back to `svg`; canvas sizes pinned to 1180×280/320 horizontal flow or 1180×480/520 tall; Mermaid kept as opt-in via `backend="mermaid"` or `VTI_DIAGRAM_BACKEND=mermaid`) |

End-to-end the four skills now support the 6-phase pipeline:

```
Phase 1 ANALYZE                       → ContextDoc
Phase 2 PLAN-OUTLINE-AND-REVIEW       → DeckOutline                     ★ checkpoint
Phase 3 CONTENT-PLAN                  → SlideContentPlan + diagram_spec + resolved_image
Phase 4 LAYOUT-DESIGN                 → SlideLayoutPlan (no-crop, ≥70% fill)
Phase 5 COMPONENT-PICK                → slide_input descriptors
Phase 6 REVIEW-AND-COMPOSE            → layout-review.html + deck-composed.html ★ checkpoint
```

**v3.19 (prior baseline):** kept here for history.

End-to-end the trio now supports:

| # | Gap | Closed in |
|---:|---|---|
| 5 | Source-summary not section-aware | creator 3.18.0 |
| 6 | No image-extraction validation | creator 3.18.0 |
| 21 | `source_hint` not validated against assets | creator 3.18.0 |
| 22 | No deck-wide block stat | creator 3.18.0 |
| 23 | 70-90% density band tight | creator 3.18.0 |
| 32 | Density-mode toggle (creator side) | creator 3.18.0 |
| 32 | Density-mode toggle (page-builder side) | page-builder 3.13.0 + creator 3.19.0 propagation |
| 41 | Stale `_VISUAL_FILL_KINDS` (audit bug) | creator 3.18.1 |
| 42 | Audit framework block→cell mismatch | creator 3.19.0 |
| W3.6 | Decorator `decorate()` was NotImplementedError | decorator 0.5.0 |

Open follow-ups (deferred, non-blocking):
- `#43` — `select_strategy` could augment section-bias with slide content keyword scan (decorator v0.6)
- Audit step in decorator (`pipeline_status['audit']` is STUB)

## Cross-skill contract — `slide_meta` shape

All three skills agree on this shape. The creator builds it via `plan_to_slide_input`; the page-builder consumes it in `compose_slide_grid`; the decorator reads `section_name` and `slide_title` from the rendered HTML.

```python
slide_meta = {
    'page_number':    int,
    'page_total':     int,
    'doc_title':      str,
    'copyright_year': int,
    'section_name':   str,         # e.g. 'RETAIL CASES'
    'slide_title':    str,
    'show_chrome':    bool,        # default True
    'layout_class':   str,         # 'default' | 'case-study' | 'data-dense'
    'density_mode':   str,         # 'standard' | 'sparse-ok' | 'dense'  (NEW v3.13/v3.19)
}
```

## Density mode profiles

The three modes share thresholds across creator audits and page-builder fill-honesty checks. Set once at Phase 4 (`plan['density_mode'] = 'sparse-ok'`); both skills pick it up.

| Mode | Drafting target | Cell SPARSE band | Slide SPARSE avg | Slide OVERCROWDED avg | Use for |
|---|---:|---:|---:|---:|---|
| `standard` | 85% | <50% | <40% | >110% | typical decks (default) |
| `sparse-ok` | 65% | <25% | <20% | >110% | hero / breathing / quote / single-stat-focal slides |
| `dense` | 95% | <60% | <55% | >120% | spec sheets / technical detail / dense-by-design |

`BLOCK_KIND_CAPS` (per-component schema caps in creator's `capacity.py`) are NOT relaxed — those are absolute render invariants. `'dense'` mode lets you draft to 95% of declared cell capacity, but you can't exceed `narrative.paragraphs_each_max=400`.

## Quick start

```bash
# Add all four skills to PYTHONPATH:
source scripts/setup.sh

# Verify
bash scripts/verify.sh
# → creator:        4.4.0
# → page-builder:   3.13.3
# → decorator:      0.5.2
# → diagram-builder:0.1.0  (7 primitives)
```

## End-to-end: build + decorate a deck

```python
import sys, json
# (PYTHONPATH must include all 3 skill dirs; see Quick start)

from creator import (
    plan_to_slide_input, build_deck_html,
    validate_for_compose, audit_visual_balance, audit_block_distribution, audit_deck_density,
)
from decorator import decorate

# 1. Load Phase 4 plans (built via creator's make_slide_content_plan, etc.)
with open('work/plans_v5.json') as f: plans = json.load(f)

# 2. Validate before render
assert validate_for_compose(plans)['ok']
assert audit_visual_balance(plans)['flag'] == 'ok'

# 3. Optional: mark hero slides as 'sparse-ok' so page-builder
#    doesn't emit slide-sparse warnings
for p in plans:
    if p['slide_id'] in ('s04-footprint', 's17-forward-store-ai'):
        p['density_mode'] = 'sparse-ok'

# 4. Compose slide_inputs (slide_meta.density_mode auto-propagates)
slide_inputs = [
    plan_to_slide_input(p, page_number=i, page_total=len(plans), doc_title='VTI Group')
    for i, p in enumerate(plans, start=1)
]

# 5. Build a complete deck HTML
html = build_deck_html(slide_inputs, title='VTI Cross-Domain Capabilities')
open('outputs/deck.html', 'w').write(html)

# 6. Run decorator (post-process — reads HTML, renders screenshots,
#    detects whitespace gaps, injects decoration layer per slide)
decorate('outputs/deck.html', output_path='outputs/deck_decorated.html')
```

## Verification — coordinated audit ladder

```python
from creator import (validate_for_compose, audit_visual_balance,
                     audit_block_distribution, audit_deck_density)

# 1. Schema + caps
r = validate_for_compose(plans)
assert r['ok']

# 2. Slide-level visual balance (Principle 8)
vb = audit_visual_balance(plans)
assert vb['flag'] == 'ok' and vb['visual_pct'] >= 60

# 3. Block-level distribution (gap #22)
bd = audit_block_distribution(plans)
assert not bd['anti_pattern_flags']

# 4. Per-cell density audit (gap #42 fixed — auto-expand)
dd = audit_deck_density(plans)        # bare list — auto-expands
assert dd['overflow_count'] == 0
```

## Migration

If you have a prior session's plans/outline/context_doc files: zero changes needed. All v3.18.x plans work as-is.

If you have hand-rolled audit harnesses that built layout lists per plan:

```python
# Before (v3.18.x)
plans_with_layouts = [(p, derive_layout(p)) for p in plans]
audit_deck_density(plans_with_layouts)

# After (v3.19.0) — bare list, auto-expand handles features_3 etc.
audit_deck_density(plans)
```

The legacy tuple form still works, so migration is incremental.

## What's in this bundle

```
vti-slide-skills-2026-05-10-baseline/
├── COORDINATED_BASELINE.md           ← THIS FILE
├── vti-slide-creator/                ← 3.19.0
│   ├── SKILL.md
│   ├── CHANGELOG.md                  ← 3.13.1 → 3.19.0 history
│   ├── creator.py                    ← main entry; __version__ = "3.19.0"
│   ├── capacity.py                   ← DENSITY_MODES table
│   ├── content_drafter.py            ← make_image_decision (gap #21)
│   ├── context_doc.py                ← sources_for_section (gap #5)
│   ├── source_ingester.py            ← classify_image_kind (gap #6)
│   ├── cross_phase.py                ← audit_block_distribution (gap #22)
│   │                                    expand_plan_for_audit (gap #42)
│   └── ... (component_catalog, deck_planner, grid_helpers, image_decisions,
│           preview, slide_edits, _contracts/)
├── vti-slide-page-builder/           ← 3.13.0
│   ├── SKILL.md
│   ├── CHANGELOG.md                  ← NEW; 3.12.0 → 3.13.0 history
│   ├── composer_grid.py              ← _DENSITY_MODE_THRESHOLDS, mode-aware
│   │                                    fill checks; catalog() reports v3.13
│   ├── tokens.css
│   └── ... (assets, chrome, components, special-pages, etc.)
└── vti-slide-decorator/              ← 0.5.0
    ├── SKILL.md
    ├── CHANGELOG.md                  ← NEW; v0.1 → v0.5 history
    ├── decorator.py                  ← W3.6 pipeline implemented;
    │                                    __version__ = "0.5.0"
    ├── whitespace_analyzer.py        ← unchanged (W3.1, W3.2)
    ├── gap_classifier.py             ← unchanged (W3.3)
    └── strategies/                   ← unchanged (W3.4)
        ├── abstract_geometric.py
        ├── topical_motif.py
        ├── typographic.py
        └── none.py
```

## Verification done before bundling

| Test | Result |
|---|---|
| `creator.info()['version'] == '3.19.0'` | ✓ |
| `composer_grid.catalog()['version'] == '3.13.0'` | ✓ |
| `decorator.__version__ == '0.5.0'` | ✓ |
| `validate_for_compose(plans_v5)` ok=True | ✓ |
| `audit_visual_balance(plans_v5)` flag=ok, 93.8% visual | ✓ |
| `audit_block_distribution(plans_v5)` no anti-patterns | ✓ |
| `audit_deck_density(plans_v5)` 0 overflow, 3 real sparse | ✓ |
| All 16 plans_v5 compose via page-builder without errors | ✓ |
| `density_mode` propagates: plan → slide_meta → page-builder warnings | ✓ |
| Decorator end-to-end on real v5 deck (21 slides, 8.4MB) | ✓ 16.5s, 16 layers injected |
| Decorator idempotent on re-run | ✓ structural |

## Provenance

This baseline was produced in a single session continuation from `vti-session-2026-05-09-full.tar.gz`. The prior session ended at creator v3.17.1 with 6 deferred gaps, no decorator implementation, and one bug surfaced by the audit rerun. This session closed all 6 + the rerun-surfaced bug + the decorator W3.6 pipeline, in that order, with cross-skill verification at each step.

The full work history is in each skill's `CHANGELOG.md`. Read those for design rationale and migration guidance.
