# vti-slide-decorator

Post-compose decoration layer for VTI slide decks. Analyzes whitespace
in a finished slide deck (HTML), classifies gaps, picks a strategy per
gap, and injects an SVG/CSS decoration overlay as a SEPARATE LAYER
underneath the content (z-index lower) so the original layout and
content are never modified.

## When to use

Invoke this skill **after** `vti-slide-creator` produces a composed
deck HTML. Do NOT invoke during composition or as part of the planner —
this is a strictly post-processing step. The order is:

```
vti-slide-creator (Phase 1-5) → composed deck HTML
  ↓
vti-slide-decorator (this skill) → decorated deck HTML
  ↓
audit_typography → final deck
```

Triggers: any user request mentioning "decorate", "fill empty space",
"add background pattern", "make slide less plain", or after creator
finishes a deck and the user wants the visual finishing pass.

## Architecture — 6 stages

```
[composed deck HTML]
  ↓
1. RENDER       — Playwright headless screenshot per slide (1280×720 PNG)
2. DETECT       — pixel-level whitespace analysis with chrome-zone awareness
                  · Header zone (top 10%) and Footer zone (bottom 8%)
                    are EXCLUDED from detection (never decoration targets)
                  · Gaps adjacent to footer extend INTO it for cohesive
                    "content + footer" decoration coverage
3. CLASSIFY     — gap taxonomy: size / position / aspect / brand-context
4. SELECT       — strategy per gap from 4-strategy library
5. GENERATE     — SVG overlay matching gap dimensions + VTI brand
6. INJECT       — wrap in z-index lower layer; merge into slide HTML
  ↓
[decorated deck HTML]
```

**Critical contracts:**
- Decorator NEVER touches content/layout. Output `<div class="slide">`
  HTML is identical to input, just with an additional
  `<div class="vti-decoration-layer">` sibling at lower z-index.
- Header/footer chrome zones are inviolable — they are NEVER decoration
  targets. Logo, page badges, breadcrumbs stay clean.
- BUT: when whitespace is adjacent to footer, the decoration may EXTEND
  through the footer for visual cohesion (single decoration cluster
  spanning content area + footer reads more unified).

## Strategy library — 4 patterns

Decoration variety beats decoration uniformity. The skill picks ONE
strategy per slide based on gap classification + slide content keywords:

| Strategy | When to use | What it produces |
|---|---|---|
| `abstract_geometric` | Large corner/edge gaps; slide is data/numbers | Gradient blob, dot grid, line mesh — VTI blue palette, ≤30% opacity |
| `topical_motif` | Slide content has clear visual subject (camera, chart, shelf, building) | Simple SVG primitive derived from 3 keywords in slide title/body |
| `typographic` | Empty bottom-right corner, content full-bodied | Improved oversized numeral + section glyph (VTI brand pattern) |
| `none` | Content fills naturally OR explicit user opt-out | No decoration injected |

**VTI brand reference:** all strategies pull from the same brand palette
established in `vti-slide-page-builder`:
- Primary blue `#0c447c` / `#185fa5` (cover-bg-tokyo geometry)
- Mesh patterns from `toc-mesh` special page
- Triangle/diamond geometry from cover hero
- Dot grids from `data-dense` layouts

See `strategies/README.md` for visual demos of each strategy.

## API

```python
from decorator import decorate, decorate_slide
from whitespace_analyzer import detect_gaps
from gap_classifier import classify_gap
from strategy_selector import select_strategy

# High-level: decorate a whole deck
decorated_html = decorate(composed_deck_html, *,
                          strategies='auto',           # or list of strategies to allow
                          screenshot_dir='/tmp/decorate', # for debugging
                          render_path=None)             # custom Playwright config

# Mid-level: per-slide
gaps = detect_gaps(slide_screenshot_path)
strategy = select_strategy(slide_html, gaps, slide_meta)
overlay_svg = strategy.generate(gaps)
decorated_slide = inject_overlay(slide_html, overlay_svg)

# Debug: visualize detected gaps
from whitespace_analyzer import visualize_gaps
visualize_gaps(slide_screenshot_path, gaps, output_path='/tmp/gaps_debug.png')
```

## Phases (build order)

This skill is being built in 6 incremental sub-steps. Each ships a
visible visual test:

| # | What | Test | Status |
|---|---|---|---|
| 3.1 | Skill scaffold + `whitespace_analyzer.py` first cut | Run on s15 v1 → output JSON gaps + overlay red rectangles. Eye-confirm matches actual whitespace. | ✓ DONE (v0.1) |
| 3.2 | Chrome-zone awareness + footer merge | All 29 v1 slides processed → 3 NONE (cover/toc/full caps), 26 DECORATE, 23 with footer-merged gaps | ✓ DONE (v0.2) |
| 3.3 | `gap_classifier.py` — taxonomy expansion | Output table per slide → spot-check 5 picks accurate | pending |
| 3.4 | 4 strategy SVG generators | 4 standalone demo HTMLs, one per strategy. Visual identity rich. | pending |
| 3.5 | `strategy_selector.py` — pick per gap+slide | Output reasoning trace per slide. Eye-review 5. | pending |
| 3.6 | Injection + audit | Re-decorate v1 deck → visual diff vs v1 thumbs | pending |

## Versions

- v0.1 (W3.1) — whitespace_analyzer first cut, decorator API stub
- v0.2 (W3.2) — chrome-zone exclusion + footer-adjacent merge logic.
  29-slide v1 audit: 3 correctly classified NONE, 23 with footer-merged
  gaps. Test verifies header-band + footer-band never get decoration
  while content+footer gaps span both for visual cohesion.
- v0.3 (W3.3) — gap_classifier.py shipped. Taxonomy: size_class
  (xs/small/medium/large/xl) · region (corner/edge/center) ·
  brand_context (footer-merged/bottom-band/side-strip/corner-pocket/
  standalone-block) · compatible_strategies (ordered list, best-first).
  29-slide audit: 26 with eligible gaps, 3 NONE; primary distribution
  typographic 43, abstract_geometric 8, topical_motif 1.
- v0.4 (W3.4) — 4 strategy generators shipped, all SVG-based.
  Visual style: cover-bg-tokyo inspired layered triangles + brand
  gradients + opacity 0.18-0.65 calibrated for contrast.
  - typographic: gradient numeral + accent bar prefix + eyebrow.
    viewBox aspect-matched to gap (no positioning distortion).
    4 layout variants per brand_context.
  - abstract_geometric: 4 variants picked by aspect/size:
      thin-h → diagonal_strip (3 overlapping triangles + gradient)
      thin-v → vertical_ladder (chevrons + accent line)
      large square/landscape → triangle_cluster (cover-bg style + halo)
      small/medium → mixed_dots (varying-size dot pattern + accent)
  - topical_motif: 6 motifs in keyword library:
      retail/store/shelf → shelf grid + product silhouettes
      ai/intelligence/neural → 3-layer neural with gradient nodes
      data/analytic/metric → bar chart with trend line + grid
      delivery/engineer/process → 3D-feel chevron pipeline
      scale/global/apac → globe with location dots
      default → cover-bg-tokyo overlapping triangles
  - none: empty string for full slides / explicit skip.
  Demo render: s11 typographic, s28 abstract_geometric, s23
  topical_motif (AI matched), s17 none.
- v1.0 (W3.5-3.6) — strategy_selector + injection + audit (next)

## Hard constraints

1. **Z-index discipline:** decoration layer MUST be lower than content.
   `.vti-decoration-layer { position: absolute; inset: 0; z-index: 1;
   pointer-events: none }` — content `.slide-content { z-index: 10 }`.
2. **Opacity ceiling:** decoration ≤ 30% opacity (never compete with
   text). Topical motifs may go up to 40% if line-only.
3. **No new fonts/icons:** decorator uses only inline SVG primitives,
   no external assets. CSS already has VTI brand fonts loaded.
4. **No text in decoration** beyond the typographic strategy's numeral.
   Decoration is visual, not informational.
5. **Determinism:** same input deck + same strategy mode → same output.
   No random seeds, no time-of-day variation.
6. **Idempotence:** running decorator twice on already-decorated deck
   must NOT double-decorate (skip slides that already have
   `.vti-decoration-layer`).

## File layout

```
vti-slide-decorator/
├── SKILL.md               # this file
├── decorator.py           # main API: decorate(), decorate_slide()
├── whitespace_analyzer.py # pixel-level gap detection (W3.1, W3.2)
├── gap_classifier.py      # gap taxonomy (W3.3)
├── strategy_selector.py   # pick strategy per gap+slide (W3.5)
├── strategies/
│   ├── __init__.py
│   ├── abstract_geometric.py
│   ├── topical_motif.py
│   ├── typographic.py
│   └── none.py
├── generators/            # low-level SVG builders shared by strategies
│   ├── __init__.py
│   ├── blob.py            # gradient blob
│   ├── dot_grid.py
│   ├── mesh.py
│   └── glyph.py
└── examples/              # 4 demo HTMLs showcasing each strategy
```

## Decoration layer HTML contract

```html
<!-- BEFORE decorator: -->
<div class="slide" style="position: relative">
  <!-- chrome + content -->
</div>

<!-- AFTER decorator: -->
<div class="slide" style="position: relative">
  <div class="vti-decoration-layer" aria-hidden="true">
    <svg ...>...decoration SVG...</svg>
  </div>
  <!-- chrome + content (unchanged, but z-index bumped to 10) -->
</div>
```

CSS injected into deck `<style>`:
```css
.vti-decoration-layer { position: absolute; inset: 0; z-index: 1;
                        pointer-events: none; overflow: hidden }
.slide > *:not(.vti-decoration-layer) { position: relative; z-index: 10 }
```
