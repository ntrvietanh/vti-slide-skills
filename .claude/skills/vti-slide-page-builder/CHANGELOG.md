# vti-slide-page-builder — CHANGELOG

## v4.4.0 (2026-06-16) — finish ECharts migration + cell vertical-align

- **gauge-dial / progress-bar / funnel → ECharts** (the last three SVG
  charts). gauge = native ECharts gauge (progress arc + centre value);
  progress-bar = horizontal bars with a track (`showBackground`); funnel =
  native funnel with "% of top" labels. Prop contracts unchanged; the
  `tone="sky"`-style bugs are gone (tones map to brand hexes). Now every
  data chart shares one ECharts path + the chart-ready handshake.
- **Cell `valign` option** (`center` | `bottom`) — fixes "content floats at
  the top of a tall 1fr row" (e.g. a pull-quote) that grid-level
  `vertical_align` couldn't reach: it aligns the content WITHIN the cell.
  Ignored when a surface is set (surfaces already centre). Applied in the
  `quote-impact` and `stat-anchor-*` archetypes; quote slides now grade
  `pass` instead of `warn` in visual_critic.

## v4.3.0 (2026-06-16) — M4: visual critique loop (the system looks at its output)

New `visual_critic.py` — the pipeline finally renders + measures its own
output instead of composing blind.

- **`critique(html_path)`** renders the deck to PNGs (reusing the exporter's
  chart-ready wait) and measures each slide: min rendered font px (HTML text
  only — SVG chart/diagram text excluded, it scales with its cell);
  **overflow/clipping** past the 1280×720 box; **blank charts** (ECharts
  placeholder with no `<svg>`); **ink ratio + vertical centroid** from the
  PNG (real whitespace — the DOM grid always fills, so a bbox-fill metric
  lies); **near-duplicate neighbours** (avg-hash). Verdicts: fail
  (font_too_small / overflow / blank_chart) · warn (sparse_top_clustered /
  neighbour_dup) · pass.
- **`auto_repair(slides, compose_fn, max_rounds=2)`** — light loop (user's
  choice). Auto-applies ONLY the safe mechanical fix: a sparse, top-clustered
  slide gets `slide_meta.vertical_align='center'` (redistributes empty space
  on auto rows; a no-op when rows already fill — never destructive). Returns
  the repaired slides + a changelog; everything else is surfaced, not mutated.
  Takes `compose_fn` as a callback so this module never imports the creator.
- **`render_review(html_path, out_html)`** — builds a single review HTML:
  each slide's real PNG + verdict badge + measured issues. Makes the Phase-6
  ★ checkpoint sighted (rendered pixels, not a descriptor wireframe).

Reuses Pillow (already present) for PNG metrics; no new heavy deps. Purely
additive — composition is unchanged.

## v4.2.0 (2026-06-16) — M3: archetype library + cell surfaces (art-director layer)

Breaks "luôn một khung cố định". The composer already rendered arbitrary
asymmetric grids; M3 adds the authoring layer that actually uses that range.

- **`archetypes.py`** — a curated library of 12 hand-tuned, intentful slide
  layouts (hero-statement, stat-anchor-left/right, lead-plus-three-cards,
  narrative-with-sidebar, two-panel-compare, data-story-left, kpi-band-top,
  quote-impact, dominant-diagram, feature-with-visual, catalog-grid). Each is
  data (asymmetric col spans + focal cells + surfaces + deliberate
  whitespace). API: `list_archetypes()`, `describe_archetype(id)`,
  `slots_for(id)`, `realize_archetype(id, slots, slide_meta, overrides)` →
  a standard `slide_input`. The orchestrator SELECTS by intent and FILLS
  slots; optional slots drop cleanly, required ones raise.
- **Cell surfaces** — a cell may set `surface = panel | tint | elevated` to
  wrap its component in a styled container (padding + radius + shadow/bg) via
  `_GRID_CSS`, so archetypes build panels / tinted cards / elevated blocks
  without bespoke components. All light surfaces (dark text stays legible);
  unknown values warn + ignore. Cells with no surface are unchanged.
- **Discovery** — `catalog(verbose=True)` now also returns `archetypes`
  (the selection list) and `cell_surfaces`, so the whole design system is
  visible from the one call the creator already makes.
- The deterministic `layout_designer` scorer path is untouched (kept as the
  fallback for image-dominant slides + back-compat). This milestone is
  purely additive.

## v4.1.0 (2026-06-16) — M2: ECharts-backed data charts

Fixes "chart cũng không có" / the flat-and-buggy state of the existing SVG
charts. The four data-chart components now render via **Apache ECharts**
(vendored locally, SVG renderer) instead of hand-templated SVG:

- **bar-chart, pie-chart, line-chart, stacked-bar** → `echarts_specs.py`
  builds an ECharts `option` from the *unchanged* prop contract; the
  component emits a `<div class="vti-echart" data-vti-echart="…">`
  placeholder. Richer output: gradient bar fills + value labels + dashed
  y-gridlines; donut centre label; smooth line + gradient area; brand
  palette + legend. Fixes the old bug where `tone="sky"` had no CSS class
  and rendered **black** bars.
- **Vendored runtime**: `vendor/echarts.min.js` (ECharts 5.5.1, ~1MB).
  `chart_runtime_html()` returns the bundle + a tiny boot script; injected
  **once per deck** by `creator.build_deck_html`, and **only when a chart is
  present** (`deck_uses_charts()`), so chart-less decks stay lean.
- **Export-safe by design** (the screenshot race any JS-charting path
  risks): the boot script inits each chart with the **SVG renderer** and
  **`animation:false`**, so `setOption` paints synchronously into the DOM,
  then sets `window.__vtiChartsReady`. `exporter.render_slides_to_pngs` and
  the figma `html_backend.render_to_png` now wait on that flag (guarded by a
  `vti-echart` content check + 8s timeout fallback) before screenshotting.
- gauge-dial / progress-bar / funnel stay on their existing SVG (simple
  indicator widgets, no race); the dead SVG-chart template helpers remain
  but are no longer the bar/pie/line/stacked path.

The decorator's faint `_motif_data_bars` background motif is intentionally
left as-is: it is decorative texture (opacity ~0.2), not a presented data
chart, so it does not conflict with the real charts now in the page-builder.

## v4.0.0 (2026-06-16) — M1: fluid typography (clamp + container-query)

First milestone of the "art-director" restructure (see repo plan). Kills
the root cause of "font không hợp với trình bày tổng thể": typography was
locked to 5 FIXED px sizes (64/32/24/15/12) that never adapted to how much
room a cell had. Now the named type scale is **fluid** and **container-aware**.

**tokens.css — fluid scale.** The 5 canonical levels became
`clamp(min, calc(base + B·cqw), max)`, and two in-between steps were added
(`--vti-fs-lead`, `--vti-fs-small`) for a smoother ramp:

| token | fluid range |
|---|---|
| `--vti-fs-hero`    | 40 → 64px |
| `--vti-fs-display` | 22 → 32px |
| `--vti-fs-title`   | 17 → 24px |
| `--vti-fs-lead`    | 15 → 18px *(new)* |
| `--vti-fs-body`    | 13 → 15px |
| `--vti-fs-small`   | 12 → 13px *(new)* |
| `--vti-fs-caption` | 11 → 12px |

  - **Safe by construction:** each clamp's MAX = the pre-M1 fixed value, so
    any container-less context (chrome, special-pages) resolves to exactly
    the old size — no regression. Only narrow cells shrink.
  - Legacy fs aliases (`--vti-fs-section/page-title/h2/h3/stat/tiny`) now
    point at the fluid canonical levels, so legacy-named consumers become
    fluid for free.
  - Weights: `--vti-fw-airy` (300) and `--vti-fw-strong` (700) re-opened,
    but only for the display/hero tiers (body stays 400/500).

**composer_grid.py — container queries.** `.vti-grid-cell` now sets
`container-type: inline-size`, so the `cqw` terms resolve against each
cell's own width. A title in a 4-col cell shrinks; the same token in a
12-col cell holds its ceiling.

**Typography budget audit.** `_TYPE_LEVELS` gains `lead`/`small`;
`_aggregate_type_budget` collapses them onto their neighbour (lead→body,
small→caption) so the richer scale does not inflate the "distinct visible
levels" count. Weight check updated: anchor-tier weights {300,600,700}
are free only when a hero/display level is present.

**Component CSS sweep.** All 113 hardcoded `font-size: Npx` declarations
across 37 component CSS files were replaced with `var(--vti-fs-*)` tokens
(context-judged: labels/eyebrows → caption, dense running text → small),
each carrying a `/* was Npx */` traceability comment. Components now
consume the fluid scale instead of bypassing it with raw px (the literal
source of the "12px overused 68×" finding).

Adaptive row HEIGHT was found to already be `auto` for content rows —
the rigidity was the fixed font, not the row. The deterministic
`BLOCK_KIND_EST_H` estimate is retained for now (it only feeds the
still-active Phase-4 scorer) and will be removed in M3 when that scorer
is replaced.

## v3.18.5 (2026-06-09) — case-study body grid: stop auto-rows stretching

The case-study layout's `.cs-body .vti-grid` set `height:100%` but never
constrained row sizing, so when the body content was shorter than the
panel the implicit auto-rows stretched to fill — pushing each
`section-header` far above its own bullet list / paragraph (a visibly
large header↔content gap). Added `grid-auto-rows: min-content` +
`align-content: start` so rows take their natural height and pack to the
top (leftover space falls to the bottom of the panel). Row-gap trimmed
16px→14px. The main `.layout-grid .vti-grid` already did this; case-study
slides (class `layout-case-study-*`, not `layout-grid`) were missing it.

## v3.18.4 (2026-06-09) — wire Principle-5 custom_block escape hatch into composer

`slide_edits.replace_with_custom_html` has long produced a `custom_block`
flag on a slide, and its docstring promised "the composer recognizes this
and bypasses the row/cell rendering" — but `compose_slide_grid` never
checked for it, so any custom-HTML slide raised
`[missing_required] rows: must be non-empty array`. The escape hatch was
documented-but-dead.

`compose_slide_grid` now honours `custom_block`:
- renders `custom_block['html']` inside `.vti-custom-block` within the
  content area, still wrapped by chrome (unless `keep_chrome=False`);
- skips `_compose_grid_body` (no rows/cells required);
- appends `custom_block['css']` to the slide CSS bundle, plus a default
  `.vti-custom-block { flex:1; min-height:0; display:flex; flex-direction:column }`
  so the block fills the content area;
- reports `metadata.custom_block=True`; `cell_count` is now null-safe for
  row dicts without a `cells` key.

Unblocks structured custom one-pagers (e.g. the CTC case-study 6-block
layout: Customer · Painpoint · VTI Solution · Technology · Diagram ·
Achievement).

## v3.18.3 (2026-05-20) — practice-card: multi-line body renders as bullet list

Promotes the v3.18.2 `\n` handling from `<br>` line breaks to a proper semantic
`<ul class="vti-practice-card__bullets">` with disc markers, blue marker color,
and tightened line-height. Single-line bodies still render as a flowing `<p>`.

Template now emits the body wrapper directly (was always wrapped in `<p>` —
which produced invalid HTML when body was a list). Single-paragraph callers
are unaffected because the renderer now produces the `<p>` itself.

## v3.18.2 (2026-05-20) — practice-card: body honours `\n` as line break

`practice-card.props.body` previously rendered as a single flowing paragraph,
forcing authors to use em-dash density to separate multiple intents inside one
card. Now any `\n` in the body string is converted to `<br>` after HTML escape,
so authors can write one intent per line for readability.

Backwards compatible: existing single-line bodies render unchanged.

## v3.18.1 (2026-05-20) — tags: don't stretch pill height to fill cell

`.vti-tags` container is placed inside a `.vti-grid-cell` which uses
`align-items: stretch`. That stretched `.vti-tags` to 100% of the cell
height; combined with its own `display: flex; flex-wrap: wrap` (default
`align-content: stretch`), the wrapped flex lines distributed the
spare height across rows and individual pills ballooned to ~2-3× the
text height.

Fix: add `align-content: flex-start; align-items: flex-start;` to
`.vti-tags` so:
- wrapped flex lines pack at the top of the container instead of
  stretching to fill it
- each pill keeps its content-derived height regardless of how tall
  the parent cell happens to be

Visual result: pills now hug the text with just the configured
`padding: 4px 11px`, matching the chip aesthetic described in the
component role.

- **CSS only** — `.claude/skills/vti-slide-page-builder/components/tags/component.css`.
- No schema / API change.
- **Bumped `version: 3.18.1`** in `info()` and `SKILL.md`.

## v3.18.0 (2026-05-19) — image-tile captions strip

`image-tile` accepts a new optional prop `captions: list[str≤80]` (up to
7 entries). When present, the component renders a compact flex-row strip
beneath the image: one equal-width cell per entry, ink-soft caption
typography. Pairs with `vti-slide-diagram-builder` v0.4.0+, which emits
the same array alongside the Mermaid SVG so authoring agents can keep
node labels clean (action/state names only) while still showing the
per-step metrics readers want.

### What changed

- **Schema** — `image-tile.props.captions: list[str≤80]` (optional,
  max 7 entries). Validates type + per-entry length; raises
  `ValidationError` on garbage.
- **Render** — emits
  ```html
  <div class="vti-image-tile__captions-strip">
    <span class="vti-image-tile__captions-strip-cell">...</span>
    ...
  </div>
  ```
  inside the figure, after the image and any `caption` text. Presence
  also adds `vti-image-tile--has-below-caption` so the figure flips
  to auto-height and the strip doesn't overflow.
- **CSS** — `.vti-image-tile__captions-strip` flex-row, gap 12px,
  margin-top 8px. Each cell uses `var(--vti-fs-caption)` size and
  `var(--vti-ink-soft)` colour — sits inside the blue-family +
  neutrals palette so it never competes with the diagram itself.
- **Bumped `version: 3.18.0`** in both `info()` and `SKILL.md`.

### Why

The companion diagram-builder v0.4.0 strips metrics out of node labels
into a separate `captions` array. The page-builder needed a place to
render that array; image-tile was the natural host since synthesized
diagrams already flow through it.

### Backwards-compat

`captions` is optional. Existing callers that don't supply the prop
render exactly as before — same figure markup, same aspect-ratio
behaviour.

---

## v3.17.0 (2026-05-19) — practice-card-leveled: maturity-ladder variant

New component `practice-card-leveled` — a variant of `practice-card` whose
body holds a sequence of badged "level" rows (L1 / L2 / L3 …) instead of
a single paragraph. Use when each peer principle has a staged progression
worth showing inline (e.g. the s05-philosophy "Four design principles"
slide, where each principle goes Boundary → Handoff → Discipline).

Schema:
```
{
  "title":      str≤28,        # uppercase card title
  "icon":       str,           # icon registry key
  "core":       str≤90,        # optional italic tagline above the levels
  "levels":     [              # 2-4 items, each:
    {"badge": str≤4,           #   "L1" / "L2" / "1" / "→"
     "body":  str≤140},        #   markdown **bold** supported
    ...
  ],
  "color_tone": "deep" | "medium" | "sky" | "navy" | "#RRGGBB"
}
```

Implementation notes:
- The renderer pulls in base `practice-card` CSS too (shared header
  classes), so a slide using only the leveled variant still gets the
  card border / radius / title styles.
- New CSS lives in `components/practice-card-leveled/component.css`
  and *augments* the base by overriding the header padding (88px → 72px)
  to reclaim vertical room for the levels block.
- Registered under `BLOCK_KIND_MAP` keys `practice_card_leveled` and
  `leveled_principles` so creator-side outline kinds map cleanly.

## v3.16.3 (2026-05-19) — fix: vs-compare middle-aligns its content stack

Bug: inside a vs-compare panel, the narrative paragraph sat at the top
and the bullets at the bottom with a huge dead gap between them.
Cause: `.vti-narrative` self-sets `height: 100%` + `justify-content:
center` so a standalone narrative cell pleasantly centers vertically;
but inside a flex column with sibling kicker + bullets, that `height:
100%` made the narrative consume the column's remaining vertical
space, pushing bullets to the floor of the column.

Fix: in `vs-compare/component.css`, override `.vti-narrative` to
`height: auto; justify-content: flex-start` for the context only, and
add `justify-content: center` to `.vti-vs-compare__col` so the (now
compact) kicker + narrative + bullets stack sits visually centered in
the panel.

## v3.16.2 (2026-05-19) — fix: vs-compare bundles inner-component CSS

Bug: `_r_vs_compare` (introduced in v3.16.0) called `_r_kicker`,
`_r_narrative_paragraph`, `_r_bullet_list_checked`, and `_r_vs_divider`
directly instead of going through the `render_component()` wrapper.
The wrapper is what adds component names to
`_USED_COMPONENTS_THIS_RENDER`, which drives the CSS bundle. By
bypassing it, none of those inner components were registered → their
CSS was never loaded → SVG bullet markers fell back to browser-default
SVG sizing (~300×150), rendering huge X / check marks on slide 5 of
any deck using vs-compare (e.g. the Chat/Email Summary Agent deck,
Act I problem slide).

Fix: switch the four direct `_r_*` calls inside `_r_vs_compare` to
`render_component()` so transitive component usage is tracked the
same way `kpi-row → stat-mini` already does. No schema changes.

## v3.16.1 (2026-05-19) — fix: grid-cell children fill full width

Bug: `.layout-grid .vti-grid-cell` declared `justify-content: stretch`,
which is **not a valid flexbox value**, so any component placed inside
a grid-cell that didn't self-set `width: 100%` rendered at intrinsic
content width — even when the cell spanned the full 12 columns.

Discovered on slide 18 of the Chat/Email Summary deck: a `callout`
component spanning `col_span: 12` shrank to ~50% of the slide. Affects
11 components missing `width: 100%`: callout, definition-list,
headline, icon-list, kicker, lead-paragraph, numbered-list,
pull-quote, section-header, tags, trend-stat.

Fix: added `.layout-grid .vti-grid-cell > * { width: 100%; }` to the
embedded grid CSS in `composer_grid.py`. Components that already
self-set `width: 100%` (practice-card, stat-mini, kpi-row, etc.) are
unaffected. No schema or contract changes.

## v3.16.0 (2026-05-19) — vs-compare: official storytelling comparison variant

Promotes the slide-5 (Act I · Problem) storytelling pattern into a
first-class **composite component**: `vs-compare`. Each side = kicker
label + narrative paragraph + check/x bullet list, with a vertical VS
divider between. Solves the "trống trải" issue from the original
3-row-stacked vs-divider layout and gives decks one block to author
instead of seven hand-positioned grid cells.

Changes:

- **New component:** `vs-compare` (composition, not a leaf). Renderer
  `_r_vs_compare` calls existing `_r_kicker`, `_r_narrative_paragraph`,
  `_r_bullet_list_checked`, and `_r_vs_divider` (orientation: vertical)
  to assemble both panels, so design discipline (font levels, weights,
  marker SVGs) stays consistent.
- **Schema:**
  ```
  left:  {label: ≤40, narrative: ≤500, items: list[≤100] (2-6)}
  right: {label: ≤40, narrative: ≤500, items: list[≤100] (2-6)}
  left_marker?:  'check'|'x' (default 'x'  — problem side)
  right_marker?: 'check'|'x' (default 'check' — solution side)
  vs_label?:     str≤6 (default 'VS')
  line_style?:   'dashed'|'solid' (default 'dashed')
  ```
- **CSS grid:** 5fr / 2fr / 5fr columns; each panel is flex-column with
  gap: 16px. Component is `width: 100%; height: 100%` — meant to occupy
  one full-slide cell (best `col_span`: 10 or 12).
- **Content-kind mappings added:** `vs_compare`, `comparison_story`,
  `pull_vs_push` → `vs-compare`.
- **+1 new icon:** `x` (24px cross stroke, currentColor) — used by
  `bullet-list-checked` when `marker: "x"`.
- **`bullet-list-checked` gained `marker` prop:** `"check"` (default,
  blue) or `"x"` (gray). Backward compatible — existing callers
  unchanged.
- **`vs-divider` gained `orientation` prop:** `"horizontal"` (default,
  unchanged) or `"vertical"` (border-left line, badge mid-column).
  Used internally by `vs-compare` but available standalone.

When to reach for `vs-compare` vs sibling components:
- **`vs-compare`** — prose-led problem↔solution with bullets, single
  block of authored content.
- **`before-after`** — temporal transformation, has an arrow (not a VS
  badge), no narrative slot.
- **`comparison-table`** — n×m feature matrix, short cells only.

## v3.15.0 (2026-05-19) — vs-divider: vertical orientation for side-by-side comparison

Adds an `orientation` prop to the `vs-divider` component so it can sit in
a narrow middle column between two side-by-side panels (drawing a vertical
dashed line) rather than only between two stacked rows.

Changes:

- **New prop:** `orientation: "horizontal" | "vertical"` (default
  `"horizontal"` — backward compatible). Validated in `_r_vs_divider`.
- **Template:** `vs-divider/component.html` now emits
  `data-orientation="{{ORIENTATION}}"`.
- **CSS:** new selectors under `[data-orientation="vertical"]` flip the
  line from `border-top` (horizontal, centered top:50%) to `border-left`
  (vertical, centered left:50%, pinned top/bottom). Container's
  `min-height` is dropped and `min-width: 60px` is added when vertical so
  the line gets a usable axis even in tight column gutters. Solid line
  style is mirrored for the vertical case.

Why: Phase 3 already emits layout hints like `"narrative 5 + vs-divider 2
+ narrative 5"` for 2-panel comparisons. Without a vertical orientation,
the rendered slide collapses into 3 stacked full-width rows and leaves
~40% of the canvas empty. With this prop, LayoutPlans can place the
divider in a 2-col middle slot spanning 2 rows.

## v3.14.0 (2026-05-19) — icon registry: +18 names, fallback glyph, warn on miss

Closes the silent-fail pattern where `render_icon(<unknown>)` returned an
empty string, leaving icon slots in `value-medallion`, `practice-card`, and
`kpi-row` rendering as **empty blue circles** when callers used reasonable
but unregistered Lucide-style names (e.g. `clock`, `database`, `network`,
`refresh-cw`, `inbox`). The result was inconsistent icon coverage across
cards in the same deck — depending on which names happened to be present.

Changes:

- **+18 icons** added to `ICON_SVGS`: `clock`, `database`, `file-text`,
  `inbox`, `at-sign`, `message-square`, `refresh-cw`, `network`,
  `compass`, `gauge`, `route`, `trending-up`, `trending-flat`, `puzzle`,
  `server-off`, `user-check`, `check-circle`, `split`. Registry total: 22 → 40.
- **Fallback glyph** `_fallback` added (a small filled dot). `render_icon`
  now returns this glyph instead of an empty string when a name is
  unknown — so the slot never collapses, even if name resolution fails.
- **One-time stderr warning** when `render_icon` is called with an
  unknown name. The warning lists available icon names so callers can
  fix at the source. Tracked via a module-level `_UNKNOWN_ICONS_SEEN` set
  (no warning spam across many calls with the same name).
- `catalog()` icon-count expected to read 40 going forward (callers that
  hard-code 22 in tests should update).

Migration: existing decks that depended on silent-empty behaviour now
render a fallback dot. If you want the previous "render nothing" behaviour,
inspect `name in ICON_SVGS` before calling — `render_icon` no longer raises
and no longer returns `""`.

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
