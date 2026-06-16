# vti-slide-page-builder

Renderer skill for VTI APAC slide decks. Pairs with `vti-slide-creator`
(the orchestrator).

## Public protocol surface

Two stable APIs that other skills (e.g. the creator) consume:

```python
from composer_grid import (
    catalog,            # discovery: what components & icons are registered
    describe_component, # query metadata for one component
    compose_slide_grid, # render a slide_input descriptor → HTML + CSS
)
```

### `catalog(verbose=False) → dict`

Quick mode (`verbose=False`) — small response for fast checks:
```python
{
  "skill":      "vti-slide-page-builder",
  "version":    "3.18.5",
  "components": ["bullet-list-checked", "catalog-column", ...],   # 9 names
  "icons":      ["bell", "brain", "building-skyscraper", ...],    # 40 names
}
```

Verbose mode (`verbose=True`) — adds full metadata + reverse picker map:
```python
{
  ...above...
  "component_meta": {
    "stat-hero": {
      "role":           "Dominant single stat (84-128px)…",
      "kind":           "data",
      "good_for":       [...],
      "bad_for":        [...],
      "best_col_spans": [4, 5, 6, 7, 8, 12],
      "natural_height": "1fr (centered) or auto",
      "schema_brief":   "value: str≤8, label: str≤30, decoration?: 'rings'|'none'",
      "picks_content_kinds": ["hero_stat"],
    },
    ...
  },
  "picks_for_content_kind": {
    "hero_stat":        ["stat-hero"],
    "features_3":       ["practice-card"],
    "values":           ["value-medallion"],
    ...
  },
}
```

### `describe_component(name) → meta dict`

```python
meta = describe_component("practice-card")
# {role, kind, good_for, bad_for, best_col_spans, natural_height,
#  schema_brief, picks_content_kinds}
```
Raises `ValidationError` if the component name isn't registered.

### `compose_slide_grid(slide_input) → {slide_html, slide_css, metadata}`

Main render entry point. Input shape:

```python
{
  "slide_meta": {
    "page_number":     int,
    "page_total":      int,
    "doc_title":       str,
    "section_name":    str,            # chrome breadcrumb LEFT side
                                       # (uppercased on render)
    "slide_title":     str (optional), # chrome breadcrumb RIGHT side
                                       # — when present, breadcrumb shows
                                       # "SECTION | TITLE". This is the
                                       # ONLY home for a per-slide title;
                                       # content rows must NOT carry an
                                       # in-slide title component.
    "show_chrome":     bool (default True),
    "copyright_year":  int  (default 2026),
  },
  "rows": [
    {
      "height": "auto" | "1fr" | "Npx",
      "cells": [
        {
          "col_start": int,    # 1-12
          "col_span":  int,    # 1-12
          "component": str,    # name from catalog()['components']
          "props":     dict,   # see component's schema_brief
        },
        ...
      ],
    },
    ...
  ],
}
```

Returns:
```python
{
  "slide_html": str,        # ready to inline in <body>
  "slide_css":  str,        # all needed CSS (tokens + chrome + components)
  "metadata":  {
    "row_count":            int,
    "cell_count":           int,
    "components_used":      list[str],   # top-level
    "components_rendered":  list[str],   # transitive (incl. children)
  },
}
```

## Architecture

### Slide canvas
- Fixed 1280×720 px (16:9 standard)
- White background, `overflow: hidden`
- Chrome positioned **absolute** at top-left (breadcrumb) / top-right
  (logo) / bottom-left (page number badge) / bottom-right (copyright).
  Chrome doesn't reserve grid rows.
- Grid lives in `vti-slide-content` box: `top: 70px; left: 56px;
  right: 56px; bottom: 64px` (= 1168 × 586 inner).

### 12-col × N-row grid
- `display: grid; grid-template-columns: repeat(12, 1fr); gap: 18px;
  align-content: start;`
- `align-content: start` ensures auto rows take natural height (extra
  vertical space goes to bottom). Use `1fr` rows explicitly when you
  want stretching.
- Each cell: `grid-column: <start> / span <n>; grid-row: <auto>;`
- Cells with `min-width: 0; min-height: 0;` to prevent grid blowout
  from long content.

### Component registration

Every component lives in `components/<name>/` with two files:
- `component.html` — template with `{{PLACEHOLDER}}` interpolation
- `component.css` — scoped styles (BEM-style `.vti-<name>__<element>`)

And one Python registration in `composer_grid.py`:

```python
@register_component("name", meta={
    "role":            "...",         # one-sentence description
    "kind":            "text|data|card|structural",
    "good_for":        [...],
    "bad_for":         [...],
    "best_col_spans":  [int, ...],     # which spans look right
    "natural_height":  "auto|1fr|...",
    "schema_brief":    "prop1: type, ...",
    "picks_content_kinds": [content_kind, ...],  # from creator's
                                                  # CONTENT_BLOCK_SCHEMAS
})
def _r_name(props: dict) -> str:
    # Validate props
    title = _esc(_require(props, "title", "name.props"))
    _check_max_chars(props["title"], 80, "name.props.title")
    # Fill template
    return _fill(_component_template("name"), {"TITLE": title})
```

The renderer is responsible for:
1. Calling `_require` / `_check_max_chars` on required props (fail-fast)
2. Calling `_esc` on user input before injecting into HTML
3. Rendering child components via `render_component(child_name, child_props)`
   if needed (transitive CSS is auto-tracked)

The metadata is the contract with the creator skill — adding a component
with `picks_content_kinds=["..."]` immediately makes it available as
the auto-pick for that content kind in the creator's Phase 4 → 5 bridge.

## Design discipline (v3.3 — 2026-05-09)

These rules govern what every component is **technically allowed** to emit.
The orchestrator (`vti-slide-creator`) layers higher-level reasoning on
top, but the type/color/sizing contract lives here at the renderer.

### T1 · Canonical 5-level type scale (v3.2)

Every text element a component renders MUST use one of these 5 levels.
Component authors are forbidden from inventing new sizes. Tokens live in
`tokens.css`:

| Level | Token | Size | Allowed uses |
|---|---|---:|---|
| `hero`    | `var(--vti-fs-hero)`    | 64px | Big stat numbers, cover headlines · **max 1 per slide** |
| `display` | `var(--vti-fs-display)` | 32px | Section dividers, in-canvas slide titles · **max 1-2 per slide** |
| `title`   | `var(--vti-fs-title)`   | 24px | Card titles, block heads, key labels |
| `body`    | `var(--vti-fs-body)`    | 15px | Paragraphs, list items, card body |
| `caption` | `var(--vti-fs-caption)` | 12px | Eyebrows, KPI sublabels, footers, captions |

Legacy size tokens (`--vti-fs-section`, `--vti-fs-h2`, `--vti-fs-h3`,
`--vti-fs-stat`, `--vti-fs-small`, `--vti-fs-tiny`) are kept for
back-compat but **deprecated** for new components — they map to the 5
canonical levels above.

### T2 · 2-weight discipline (v3.2)

Use only `--vti-fw-regular` (400) and `--vti-fw-medium` (500). The token
`--vti-fw-semibold` (600) is permitted ONLY on text rendered at `hero`
or `display` size. Tokens `--vti-fw-light` (300) and `--vti-fw-bold` (700)
are **deprecated** — kept so legacy CSS still compiles, but new component
CSS that introduces them will be rejected at code review.

### T3 · Per-slide budget (orchestrator-enforced) (v3.2)

Components are individually disciplined; the **orchestrator** enforces the
per-slide budget:

- **Max 3** of the 5 type levels visible on any one slide
- **Max 2 weights** visible on any one slide
- **Max 1** dominant color (`--vti-blue-deep`) plus neutrals

Enforced by the creator's reasoning protocol (the renderer cannot detect
cross-component combinations). See `vti-slide-creator/SKILL.md
§ Design principles` for the reasoning contract. Validated post-render
by `audit_typography.py` at the baseline root.

### T4 · Semantic colors LOCKED (v3.2)

`--vti-amber`, `--vti-amber-strong`, `--vti-orange`, `--vti-green`,
`--vti-red`, `--vti-magenta`, `--vti-purple`, `--vti-teal` are **reserved
for semantic state ONLY**:

| Color | Allowed semantic | Example |
|---|---|---|
| `--vti-red`   | error / negative / overrun | warn callout, negative-trend stat |
| `--vti-green` | success / confirmation / positive | (rare — explicit success state only) |
| `--vti-amber` | (legacy migration palette) | only inside Migration-themed slides |

NONE of these colors may be used for **decorative** framing, "tip" callouts,
generic highlights, or chart palette diversification. The chart palette is
pure-blue (deep / medium / sky / cyan) plus neutral grays, period.

This rule was applied retroactively in v3.2: the `callout` component's
`tone="tip"` variant was patched from green → `--vti-blue-deep`.

### T5 · No mid-block style variation (v3.2)

Within a single text block (paragraph, list item, card body), font-size,
weight, and color stay constant from start to end. No inline `<b>`, no
random word-level emphasis, no inline color changes. If you need
emphasis, restructure the content so the emphasis IS the block (a kicker,
a callout, a stat-hero) — don't sprinkle bold inside body copy.

### T6 · Components fit content, not stretch (v3.3, refined v3.4)

Default grid behavior should be `auto` rows, NOT `1fr` rows. Components
should be sized by their content, not by row stretching that creates
artificial empty space inside cells. (See T7 for the full peer-equalization
contract this rule depends on.)

| Pattern | When to use |
|---|---|
| `grid-template-rows: auto` | **Default** — rows fit their content (T7 Loop 1) |
| `grid-template-rows: 1fr` | Only when content density is verified ≥70% of cell capacity (T6 prerequisite) **AND** the row needs to anchor visual weight (e.g. case-study hero stat row). Document the justification. |
| `min-height: <derived>` | When uniform height for visual rhythm is needed; derive from largest natural cell, never from "fill canvas" |

**Rationale (v3.3):** Pre-v3.3 several layouts used `1fr` rows by default
to "fill the canvas". Combined with thin per-card content (60-100 chars),
this produced cards stretched to 250-300px tall containing 30-40% content
+ 60-70% empty space inside the box. The fix: rows fit content; if a
slide ends up sparse, the **content** is wrong (Phase 4 should have drafted
more) or the **layout** is wrong (Phase 5 should have picked fewer cells
or asymmetric layout) — never paper over it with row stretch.

**v3.4 refinement:** T6 was advisory. v3.4 splits the discipline:
- T6 stays as the renderer-level "auto is default" contract
- T7 (new) governs the visual contract between peers and slide canvas
- P6 (orchestrator) governs capacity planning at the outline level
- P7 (orchestrator) governs the two-loop fit decision (peer equalization
  vs slide-level whitespace)

When a card or cell ships with <50% content fill, the orchestrator must
trigger one of: (a) expand content, (b) change layout, (c) add intentional
slide-level decoration. See creator SKILL.md § Principle 6 + 7 for the
two-loop fit workflow that drives these decisions upstream.

### T7 · Auto rows are default; peer-equalize via natural max (v3.4)

Two visual contracts the renderer must satisfy:

**Contract 1 — peer equalization within a row.** When `grid-template-rows`
is `auto`, browser grid already aligns all cells in the same row to
`max(natural_heights)` of the peer set — automatically. The renderer
relies on this default; component CSS must NOT override cell height
internally (no `height: 100%` or `min-height: 100%` on top-level cell
wrappers).

**Contract 2 — slide canvas may have empty bottom space.** That's by
design. The renderer's job is NOT to fill the canvas. Slide-level
whitespace is resolved at orchestrator level (creator P7 Loop 2):
content add, decoration add, or layout restructure — NEVER row stretch.

**What this means for component authors:**
- Component CSS must let cells size naturally (do not set fixed heights)
- Card-style components must lay out content top-aligned (so empty
  space goes to the bottom of the cell, where it's already irrelevant
  per peer-equalization)
- No "fill remaining space" tricks — flexbox `flex: 1` on inner content
  panels is OK only when the cell itself is auto-height

**Composer behavior (v3.4 default, v3.5 enforcement):** Composer
currently accepts `1fr` row heights without warning. v3.5 will reject
or warn when `1fr` is used with projected content fill <70%. Until
then, the discipline is reasoning-enforced (creator-side P7 + this T7).

### Capacity reference (v3.3)

Canvas inside chrome = 1160 × 590px. Body 15px × 1.55 line-height ≈
23px/line, ~7.5px/char.

| Layout | Cell width | Capacity raw | Target draft (70%) |
|---|---:|---:|---:|
| 1-col full-width | 1160px | ~3500 chars | ~2400 chars |
| 2-col (each) | 570px | ~1700 chars/col | ~1200 chars/col |
| 3-col card body | 370px | 360-540 chars | **250-380 chars** |
| 4-col card body | 270px | 264-330 chars | **180-230 chars** |
| Asymm 65/35 text col | 400px | ~500-700 chars | 350-490 chars |

(Card body capacity = total cell minus icon 32px + name 28px + padding
32px = ~92px of chrome consumed. Range depends on row height: 200px row
→ 5 lines body, 280px row → 8 lines body.)

Authors of new components must declare a `recommended_chars` hint in the
schema metadata so the orchestrator can validate at planning time that
the content draft is within capacity. (Schema extension scheduled for
v3.4.)

## How to add a new component

```bash
mkdir components/<name>
echo '<div class="vti-<name>">{{PROP}}</div>' > components/<name>/component.html
cat > components/<name>/component.css <<EOF
.vti-<name> { ... }
EOF
```

Then in `composer_grid.py`:

```python
@register_component("<name>", meta={
    "role": "...",
    "kind": "text|data|card|structural",
    "good_for": [...],
    "bad_for":  [...],
    "best_col_spans": [...],
    "natural_height": "auto",
    "schema_brief": "prop: type",
    "picks_content_kinds": ["..."],   # or [] if it's only used as a child
})
def _r_<name>(props: dict) -> str:
    # validate + render
    ...
```

That's it. The creator picks it up automatically — no syncing.

## Component library (13 atomic, as of 3.1.0)

**Sprint A — base 9** (text/data/structural):
`narrative-paragraph` · `stat-hero` · `practice-card` · `stat-mini` ·
`kpi-row` · `bullet-list-checked` · `value-medallion` · `catalog-column` ·
`vs-divider`

**Sprint B — media + flow (4 new)**:
`image-tile` (single image with frame + caption) ·
`logo-grid` (N-column partner/customer logos, 3 tones) ·
`quote-block` (testimonial, hero or card style) ·
`process-flow` (3-7 numbered steps with chevron connectors)

Use `catalog(verbose=True)` to get full metadata for each component.

There is intentionally NO `eyebrow-title` (or any other in-slide title)
component. Section + per-slide title are first-class fields on
`slide_meta` and rendered into the chrome breadcrumb as
`SECTION | TITLE` — see `chrome/chrome.meta.md` for the breadcrumb
spec. Content rows are reserved for real content blocks.

| Kind | Components |
|---|---|
| text       | narrative-paragraph, bullet-list-checked |
| data       | stat-hero, stat-mini, kpi-row |
| card       | practice-card, value-medallion, catalog-column |
| structural | vs-divider |

## Special pages — `compose_special_page(name, props)`

13 lift-and-shift pages from v2, fully renderable:

| Group | Pages |
|---|---|
| Framing (5)  | cover, toc, section-divider, contact, closing |
| Narrator (8) | about-vti, vision-mission-values, who-we-serve, awards-certifications, strategic-partners, project-management-method, quality-assurance, quality-management-process |

### ⚠️ Hard rule: brand defaults live in `data/vti-defaults.json`

Real VTI data (contact info, deck title fallbacks, etc.) is read from
`data/vti-defaults.json` — single source of truth. **Do NOT invent
placeholder data inline.** Edit the JSON to change defaults; never
hardcode VTI content in Python code or in callers.

The contact page in particular ships with the canonical 4-hub layout
(Vietnam HQ + HCMC, Japan ×4 offices, Korea, Singapore) plus 4 channels
(facebook.com/VTI.JSC, info@vti.com.vn, linkedin.com/company/vtijsc/,
https://vti.com.vn/). Calling `compose_special_page("contact", {})`
renders that exact deck — same input, same output, every time.

```python
from composer_grid import (
    compose_special_page,
    list_special_pages,
    describe_special_page,
)

# Simple framing page
out = compose_special_page("cover", {
    "deck_title":   "VTI APAC",
    "deck_tagline": "Corporate profile · 2026",
})
# out → {"slide_html": ..., "slide_css": ..., "metadata": {"kind": "special-page", ...}}

# Page with nested item lists (TOC)
out = compose_special_page("toc", {
    "doc_title": "Demo deck",
    "page_num":  2,
    "toc_items": [
        {"title": "01  Who we are", "page": "03", "items": [
            {"title": "Three practices", "page": "04"},
        ]},
        {"title": "02  What we ship", "page": "05", "items": []},
    ],
})

# Narrator page (chrome breadcrumb auto-derived from section_name + slide_title)
out = compose_special_page("about-vti", {
    "section_name": "About",
    "slide_title":  "About VTI",
    "intro_text":   "We are a 1,200-engineer practice...",
    "page_num":     3, "doc_title": "Profile", "copyright_year": 2026,
})
```

### Page schemas — what props each accepts

Use `describe_special_page(name)` to query the `required` / `optional`
props for a page. The page's section_name + slide_title (when provided)
get composed into the chrome breadcrumb as `SECTION | TITLE` for the
8 narrator pages — same convention as content slides.

### Templating engine

The renderer supports a Mustache-ish subset:
- `{{KEY}}` — simple substitution (matched case-insensitively against
  uppercased prop keys)
- `{{this.field}}` — dotted-path lookup, used inside `{{#each}}` blocks
- `{{#each ARRAY}}…{{/each}}` — iterate, binding `this` to each item;
  nests cleanly (`{{#each this.subitems}}` inside an outer each)

This subset covers the toc and contact templates (the only two with
loops) without dragging in a full Mustache dependency.

## Deck-level renderer — `compose_deck(slides)`

For multi-slide decks. Takes a list of mixed special-page descriptors
and content slide_inputs, returns ONE deck blob with deduplicated CSS:

```python
from composer_grid import compose_deck

deck = compose_deck([
    {"special": "cover", "props": {"deck_title": "VTI APAC", "deck_tagline": "..."}},
    {"special": "toc",   "props": {"toc_items": [...]}},
    {"special": "section-divider", "props": {"section_title": "01 / Who we are"}},
    {  # regular slide_input — same shape compose_slide_grid consumes
        "slide_meta": {"page_number": 4, "page_total": 7, "doc_title": "...",
                       "section_name": "Who we are",
                       "slide_title":  "Three practices, scaled across APAC"},
        "rows": [...],
    },
    {"special": "closing", "props": {"closing_message": "Thanks"}},
])

deck["deck_html"]      # all slides' HTML stacked, in order
deck["slide_htmls"]    # per-slide HTML if you want a custom shell
deck["deck_css"]       # ONE CSS bundle, deduped
deck["slide_metadatas"]
```

Why this exists: each `compose_slide_grid` call returns CSS scoped to
THAT slide's components. Stacking N slides naively keeps tokens / chrome
/ component-CSS in N copies. Worse, taking only one slide's CSS leaves
later slides unstyled (icons render at natural size, layouts collapse).
`compose_deck` splits each per-slide `slide_css` on its `\n\n` join
boundary and dedupes chunks across the deck — each component's CSS
appears at most once.


