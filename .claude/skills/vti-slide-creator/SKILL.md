# vti-slide-creator

**Version: 4.6.1**

Multi-phase orchestrator for VTI deck building. Pairs with
`vti-slide-page-builder` (the renderer).

> **Phase 6 contract.** The final HTML deck MUST be assembled via
> `build_deck_html(descriptors, title=…)`. Drivers must NOT hand-roll
> their own `<html><head><body>` shell around `compose_deck()`, and
> must NOT mutate the deck HTML between compose and disk-write. Page
> numbers are owned by the chrome footer chevron — there is no second
> badge. (Removed in v4.0.1 after the "16 in top-left" regression.)

## Strict rules — VTI deck structural mandates (v4.2.0)

These are not advisory. They are non-negotiable and apply to every
deck this skill produces.

### Rule A — Mandatory framing slides

**Every deck MUST include all four of:** `cover`, `toc`, `contact`,
`closing`. They are sourced from the page-builder's precrafted
special-page templates (`{"special": <name>, "props": {...}}`) — never
hand-rolled. Positions are fixed:

| # | Slide | Source |
|---|---|---|
| 1 | Cover    | `{"special": "cover",   "props": {...}}` |
| 2 | TOC      | `{"special": "toc",     "props": {...}}` |
| N-1 | Contact | `{"special": "contact", "props": {...}}` |
| N | Closing  | `{"special": "closing", "props": {...}}` |

A deck without any one of these four is **incomplete** — the Phase 6
compose step should fail-fast or warn loudly.

### Rule B — VTI company-info topics → precrafted special pages

When a slide is about VTI as a company (its profile, awards, partner
network, customer-base distribution, vision/mission, methodology, or
quality system), it MUST use one of the precrafted special-page
templates. Do NOT hand-roll a content slide via `compose_slide_grid`
for these topics.

| Topic | Special page name |
|---|---|
| Company intro / overview / "About VTI" | `about-vti` |
| Vision · Mission · Values | `vision-mission-values` |
| Customer base · domain mix · who we serve | `who-we-serve` |
| Awards & certifications | `awards-certifications` |
| Strategic partners (AWS, Microsoft, IBM, Adobe, …) | `strategic-partners` |
| Project-management methodology | `project-management-method` |
| Quality assurance activities | `quality-assurance` |
| Quality management process | `quality-management-process` |

Customization is **prop-only**: pass props (e.g. `intro_text`, customer
counts, footnotes, taglines) to update copy or numbers, but the layout
and design system stay intact.

**Anti-patterns** (never do these):
- Building "VTI Group at a Glance" as `hero_stat + narrative + supporting_stats`
  → use `about-vti`
- Building "Awards & Partners" as two `logo_grid` rows → split into
  `awards-certifications` AND `strategic-partners` (two slides)
- Building "Engagement Model" as `process_flow + narrative` → use
  `project-management-method` and/or `quality-management-process`
- Building domain-mix pie as a custom `pie_chart` content slide → use
  `who-we-serve`

### Rule C — Topics NOT covered by precraft are hand-rolled

Case studies, technical capabilities (AI stack, specific solutions),
project deliverables, and other non-VTI-company-info topics ARE built
as content slides via `compose_slide_grid`. The precraft mandate (Rule
B) applies ONLY to the 8 VTI-corporate topics listed above.

### Phase 2 outline impact

When drafting the outline, classify each slide topic:
- VTI corporate info → mark `kind` as the matching narrator special
  page name (`about-vti`, `awards-certifications`, etc.)
- Case studies / capabilities / project content → `content`
- Cover / TOC / divider / contact / closing → corresponding framing
  kind

The Phase 2 outline table now also enforces the four-framing-slide
mandate: validate that the outline includes one of each
{`cover`, `toc`, `contact`, `closing`}.

## Output scope — HTML ONLY

This skill produces **a single HTML deck** as the final deliverable.
**PDF export is OUT OF SCOPE.** If the user wants PDF, route to the
separate `vti-pdf-export` skill AFTER the HTML deck is approved.
Do not call any PDF rendering code, do not screenshot slides as part
of this skill's flow, do not export to PDF "as a bonus".

## Checkpoint enforcement — STOP and WAIT

Each of the 5 phases ends with a **mandatory checkpoint**. After
producing the phase output:

1. Present the output clearly to the user.
2. Ask specific yes/no/edit questions (not open-ended "what do you think").
3. **STOP. Do not proceed to the next phase until the user replies.**

Do NOT auto-advance phases by assuming "the user probably wants me to
keep going". Doing so defeats the brainstorm purpose of the pipeline.
If the user says "OK" or equivalent for the current phase, that's
permission for the NEXT phase only — still stop after that phase.

## Protocol with page-builder

The creator does NOT hardcode component metadata. It queries the
page-builder's catalog at import time via:

```python
from component_catalog import (
    list_components,             # all 37 components
    list_categories,             # 8 categories
    list_components_by_category, # filter by category
    describe,                    # full metadata for one component
    by_category,                 # components grouped by category
    markdown,                    # full catalog as markdown
    picks_for_kind,              # content_kind → candidate components
)
```

Each component in the page-builder declares its own metadata at
registration time:

| Field | Purpose |
|---|---|
| `role`            | one-line summary of what the component is for |
| `kind`            | `text` / `data` / `card` / `structural` / `visual` |
| `good_for`        | list of scenarios where this is the right pick |
| `bad_for`         | list of scenarios where to AVOID picking this |
| `best_col_spans`  | list of col_span values that work well |
| `natural_height`  | typical height behavior (`auto`, `1fr`, fixed) |
| `schema_brief`    | one-line schema spec |
| `picks_content_kinds` | content kinds this component can render |

### 8 categories (for layout planning)

| Category | Components | What for |
|---|---|---|
| **stats**          | 5 — `stat-hero`, `stat-mini`, `kpi-row`, `value-medallion`, `trend-stat` | numeric values + labels |
| **text-paragraph** | 8 — `narrative-paragraph`, `lead-paragraph`, `headline`, `kicker`, `section-header`, `pull-quote`, `quote-block`, `callout` | single text blocks |
| **text-list**      | 5 — `bullet-list-checked`, `numbered-list`, `icon-list`, `definition-list`, `tags` | multi-item collections |
| **card**           | 2 — `practice-card`, `catalog-column` | richer single units |
| **visual**         | 2 — `image-tile`, `logo-grid` | image / logo content |
| **table**          | 2 — `table`, `comparison-table` | tabular data |
| **chart**          | 6 — `bar-chart`, `pie-chart`, `stacked-bar`, `line-chart`, `progress-bar`, `gauge-dial` | data visualizations |
| **diagram**        | 7 — `process-flow`, `swimlane`, `timeline`, `funnel`, `quadrant-matrix`, `before-after`, `vs-divider` | structural relationships |

Adding a new component to the page-builder makes it instantly available
to the creator — no syncing of two hardcoded lists.

See `vti-slide-page-builder/COMPONENTS.md` for the full catalog with
schema details, use cases, and best col_spans for every component.

## The 6-phase pipeline (v4.0)

The creator turns raw source content into a polished deck through 6
phases. **Two mandatory checkpoints** (Phase 2 outline-and-review,
Phase 6 review-and-compose) gate the user-visible decisions; the
others are optional skip points.

```
Phase 1 ANALYZE                ──▶ ContextDoc
Phase 2 PLAN-OUTLINE-AND-REVIEW ──▶ DeckOutline                   ★ checkpoint
Phase 3 CONTENT-PLAN (×N)      ──▶ SlideContentPlan
                                    + diagram_spec (synthesize)
                                    + resolved_image (lift)
Phase 4 LAYOUT-DESIGN (×N)     ──▶ SlideLayoutPlan
                                    (no-crop + ≥70% fill assertions)
Phase 5 COMPONENT-PICK (×N)    ──▶ slide_input descriptors
Phase 6 REVIEW-AND-COMPOSE     ──▶ layout-review.html             ★ checkpoint
                                    + deck-composed.html
```

| # | Phase | Output | Notes |
|---:|---|---|---|
| 1 | ANALYZE | `ContextDoc` | source ingest + audience/purpose proposal |
| 2 | PLAN-OUTLINE-AND-REVIEW | `DeckOutline` | merged outline+review, single ★ checkpoint |
| 3 | CONTENT-PLAN | `SlideContentPlan` (×N) | typed blocks + diagram-draw via vti-slide-diagram-builder + lift filter via classify_image_kind |
| 4 | LAYOUT-DESIGN | `SlideLayoutPlan` (×N) | no-crop guarantee, ≥70% screen-fill assertion |
| 5 | COMPONENT-PICK | `slide_input` (×N) | mostly mechanical translation |
| 6 | REVIEW-AND-COMPOSE | `deck-composed.html` | render layout-review widget → user confirms → compose final HTML |

The creator package surface:

```python
from creator import (
    # ====== Phase 1 — ANALYZE ======
    analyze_source,           # ingest a file path → normalized dict
    ingest_pre_extracted,     # build result from extracted-by-skill data
    summarize_source,         # quick text summary
    make_context_doc,         # build ContextDoc envelope
    validate_context_doc,     # check ContextDoc shape
    has_source_images,        # for Phase 4 image_decision

    # ====== Phase 2 — PLAN-OUTLINE ======
    make_deck_outline,        # build DeckOutline envelope
    make_slide_outline_entry, # one slide entry
    validate_deck_outline,    # check shape + duplicate IDs + valid kinds
    render_outline_summary,   # plain-text outline for chat display
    slide_count_by_kind,
    section_distribution,

    # ====== Phase 3 — PLAN-REVIEW (slide-list manipulation) ======
    add_slide, remove_slide, move_slide, replace_slide,

    # ====== Phase 3 — CONTENT-PLAN (was Phase 4 in v3.x) ======
    make_block, make_image_decision, make_slide_content_plan,
    validate_block, validate_plan,
    suggest_strategy,         # image strategy heuristic
    plan_to_slide_input,      # legacy Phase 4 → 5 bridge (kept for back-compat)
    resolve_lift_image,       # v4.0 legacy — content-blind, kept for back-compat
    # ── v4.4 — semantic image picker (replaces resolve_lift_image) ──
    enumerate_candidates,     # top-K candidates per slide (filename-hint scored)
    get_caption, set_caption, # caption persistence (orchestrator writes back)
    record_image_decision,    # write decision + rationale to phase_3.json
    ImageDecision,            # dataclass for the decision payload
    allocate_case_study_images,  # best-fit allocation across multi-slide CS
    build_worklist,           # batch enumerate-candidates for all lift slides

    # ====== Phase 4 — LAYOUT-DESIGN (NEW in v4.0) ======
    design_slide_layout,      # ContentPlan → LayoutPlan with no-crop + fill assertions
    validate_layout_plan,
    layout_metrics,           # fill_pct, no_crop_ok, low_fill, high_fill flags
    make_layout_row, make_layout_cell, make_layout_plan,
    SLIDE_W_PX, SLIDE_H_PX, CONTENT_AREA_W_PX, CONTENT_AREA_H_PX,

    # ====== Phase 5 — COMPONENT-PICK (was the rest of Phase 5 in v3.x) ======
    picks_for_kind, describe, # component catalog lookup
    even_split, asymmetric_split, with_divider,
    narrative_row, stat_plus_narrative_row,
    cards_row, kpi_strip_row,
    make_slide, make_cell, make_row,

    # ====== Phase 5 — Layout review (v3.13) ======
    # PRIMARY checkpoint tool — render ALL slides as 16:9 wireframe boxes
    # for batch review BEFORE compose. Empty bottom = visible sparse.
    # Red border = predicted overflow. Pass output to show_widget.
    render_layout_review_widget,
    # Programmatic stats (no render) — for scripts/CI
    deck_stats,
    # Per-slide edit primitives — fix one slide without rebuilding deck
    change_cell_props, change_cell_component, change_cell_span,
    replace_row, add_row, remove_row, set_row_height,
    mark_fill_verified, change_decoration_label,
    replace_with_custom_html,    # Principle 5 escape hatch
    shorten_practice_cards, find_cells_by_component,
    # Single-slide full-render preview (slow — use after wireframe)
    render_inline_preview,
    render_grid_summary,         # plain-text grid summary
)
```

## Design principles (v3.3 — 2026-05-09)

These are the **reasoning rules** Claude applies during Phase 4 (content)
and Phase 5 (layout). They sit ABOVE the component pipeline — the pipeline
is a starter kit, not a constraint. When a slide's message demands
something the components don't cleanly express, Claude **builds a custom
arrangement** rather than forcing message into the wrong component.

### Principle 1 · One slide, one message, one focal point (v3.2)

Before drafting any slide, ask out loud:

> *"If a CTO read just this slide for 3 seconds, what's the ONE thing they
> walk away with?"*

Write that as a single declarative sentence. Everything on the slide must
either **be** that thing, **support** that thing, or **be cut**. A slide
with 8 small elements of equal visual weight is a slide with no focal
point — that's a Phase 5 failure, not a "we'll fix it in render".

A clean focal hierarchy is typically:
- **HERO** — the focal element (60-70% of slide visual weight): a big
  stat, a hero phrase, a full-bleed product screenshot, a single-frame
  diagram. ONE thing.
- **SUPPORT** — 1-2 elements that prove or contextualize the hero
  (narrative paragraph, definition strip, kpi-row).
- **META** — chrome, page badge, eyebrow label. Recedes.

If the slide doesn't have a clear hero element, restructure before
moving to Phase 5.

### Principle 2 · Visual hierarchy through restraint (v3.2)

Per-slide budget enforced by the orchestrator (see page-builder T1/T2/T3):

- **Max 3** of the 5 type levels (`hero`, `display`, `title`, `body`, `caption`)
- **Max 2** font weights (regular 400 + medium 500; semibold 600 only on hero)
- **Max 1** dominant color (`vti-blue-deep`) plus neutrals (navy + 1-2 grays)

If Phase 5 reasoning produces a layout that would render >3 type levels
on one slide, REDESIGN the layout. Common cause: stacking too many
components from different categories (kicker + lead-paragraph +
narrative-paragraph + 3 cards + callout = 5 distinct font treatments
before chrome). Cut to 3.

The cleanest content slides typically use:
- 1 eyebrow caption (12px, var(--vti-blue-deep), small caps)
- 1 hero phrase OR hero stat (display / hero size)
- 1 body block (paragraph, list, or definition strip)

Three type levels, period.

### Principle 3 · Whitespace must be intentional (v3.2)

Whitespace on a slide either **directs the eye** or **signals you ran out
of content**. Only the first is acceptable. (See Principle 6 for the
capacity-planning discipline that prevents accidental sparse slides.)

When Phase 5 wireframe shows a slide with >30% empty space at bottom:

1. **Add content** — supporting proof points, secondary stats, hero image
2. **Scale up** — make the hero bigger
3. **Cut & rebalance** — choose a layout that doesn't require 720px

NEVER ship a slide that looks "spacious because we ran out". Fix is upstream.

### Principle 4 · Asymmetric balance, not just grid alignment (v3.2)

The 12-col grid is an **alignment** tool, not a composition recipe. Real
composition uses asymmetric balance:

| Pattern | When to use |
|---|---|
| **Hero left + meta right (60/40)** | Case-study overview · product feature reveal |
| **Stat hero left + narrative right (40/60)** | Result slide · headline metric with story |
| **Full-bleed image + text overlay** | Cover · section divider · emotional context |
| **Centered hero + supporting strip** | Rare — for genuine single-message slides |
| **Even 3-col / 4-col grid** | When the message IS "these N peers are equal" |

When you find yourself stacking 3-4 auto-height rows top-down with no
focal element, you're using the grid as a list. Restructure.

### Principle 5 · Custom > generic when the message demands it (v3.2)

The page-builder's 37 components cover ~70% of typical slide needs. The
remaining 30% must be **built custom** — inline SVG illustrations,
hand-composed HTML/CSS layouts, custom diagrams.

Signals that you should build custom instead of using a stock component:

- The narrator special-page renders only decorative graphics; the actual
  message doesn't land. → Build custom slide.
- The closest existing component is "kind of right but missing the visual
  hook" (e.g. a heatmap requires custom 2D color grid). → Build inline SVG.
- A slide needs a hero illustration showing how a system works. → Build SVG.

When building custom, follow the same discipline rules (T1-T6 from
page-builder SKILL.md) — type scale, weight budget, color rules, AND
content-fits-cell apply equally to custom HTML.

The goal is NEVER to avoid components when they fit. The goal is never
to FORCE a component when it doesn't fit. Build with intention.

### Principle 6 · Capacity-first content planning (v3.14 upgrade)

Capacity is an **input** to Phase 2 (outline) and Phase 4 (content),
not a post-render audit. The planner commits to a layout sketch and
total char budget per slide BEFORE drafting content; Phase 4 then
drafts to that budget directly. If the source material can't fill the
budget, the planner picks a different layout — never an oversized one
that gets papered over at render.

**Capacity is a single source of truth (v3.14)** — derived from the
page-builder's declared component metadata, not a static SKILL table.
v3.13 had a static table that disagreed with the builder by 2.5×; Phase
4 drafted to one number, Phase 5 audited at another, 15/16 slides
flagged overflow. v3.14 closes the gap by exposing the page-builder's
declared values directly:

```python
from creator import cell_capacity, cell_target, layout_sketch_capacity

cell_capacity('narrative-paragraph', 7)      # 560
cell_target('narrative-paragraph', 7)        # 476  (85% of capacity)

# Multi-cell layout
layout_sketch_capacity([
    ('stat-hero', 5),
    ('narrative-paragraph', 7),
    ('kpi-row', 12),
])
# {'total_capacity': 800, 'total_target': 680, 'per_cell': [...]}
```

**Common cell capacities** (computed from declared metadata, illustrative):

| Cell | Capacity | Phase 4 target |
|---|---:|---:|
| narrative-paragraph 12-col | 960 | 816 |
| narrative-paragraph 7-col  | 560 | 476 |
| narrative-paragraph 5-col  | 400 | 340 |
| practice-card 4-col        | 280 | 238 |
| bullet-list-checked 12-col | 480 | 408 |
| bullet-list-checked 7-col  | 280 | 238 |
| kpi-row (any width)        | 200 (fixed) | 170 |
| stat-hero (any width)      |  40 (fixed) |  34 |

Always call `cell_capacity()` rather than hardcoding numbers — registered-component
capacity may evolve.

**Hard caps (per sub-field) — v3.14 now enforced at Phase 4:**

The page-builder render functions enforce hard limits via
`_check_max_chars()`. Phase 4 `validate_block()` now mirrors these so
drafts that would crash at compose are caught earlier. Surface limits:

| Block kind | Sub-field cap |
|---|---|
| `narrative` | `paragraphs[]≤400 chars each, 1-4 items` |
| `hero_stat` | `value≤8, label≤30` |
| `supporting_stats` | `items[].value≤8, items[].label≤30, 2-5 items` |
| `list` | `items[]≤100 chars each, 2-8 items` |
| `features_3` | `cards[].title≤28, cards[].body≤220, exactly 3` |
| `values` | `cards[].title≤22, cards[].tagline≤60, 4-6 cards` |
| `catalog` | `columns[].label≤24, items[]≤80, 2-3 columns` |

See `creator.BLOCK_KIND_CAPS` for the authoritative dict.

**Phase 2 commitment** — outline table requires 2 extra columns:
- `Layout sketch` — 1-line sketch (e.g. "narrative 7 + kpi-strip right 5")
- `Char budget` — total chars target, derived from `layout_sketch_capacity()`

**Phase 4 enforcement** — `validate_block()` now enforces hard caps (v3.14).
Drafting past `paragraphs[]≤400` or `practice-card.body≤220` fails validation.
Use `creator.split_long_paragraphs(content)` to repack a too-long narrative
across 1-4 paragraphs ≤400 chars each.

**Cross-phase validation** — `creator.validate_for_compose(plans)` runs
the full Phase 4 → Phase 5 dry-run before any wireframe rendering.
Returns the list of every cap violation across the deck. Use it as the
gate between Phase 4 and Phase 5.

**Decision chain when content is drafted:**

| Fill % of capacity | Action |
|---|---|
| > 100% | OVERFLOW — cap violation; trim or change layout |
| 70-100% | JUST RIGHT — render |
| 50-70% | MILD GAP — accept (Loop 2 of P7 resolves at slide level) |
| < 50% | MAJOR GAP — bounce to Phase 2, change layout |

**Forbidden:** drafting content to express the message at "natural"
length and then stretching boxes via `1fr` to fill canvas. The
imbalance must be resolved at content/layout level — never at render
(see Principle 7).

**Decoration patterns** (legitimate sparse-slide fills, applied via P7
Loop 2):
1. Background pattern — geometric grid/dot, opacity 5-8%, vti-blue-deep
2. Corner accent SVG — chevron/triangle, blue-deep, decorative
3. Half-canvas image — hero photo/illustration fills 40-50% canvas
4. Faded large numeral — "01" "02" at 200-300px, opacity 8%, behind content
5. Vertical accent bar — thin colored line between sections

Decoration constraints: never compete with content (high contrast,
eye-catching), never inside cards (only at slide-level), always
blue-only (stays within T4).

**Rationale (v3.14 vs v3.13):** v3.13 had THREE separate truth sources
for capacity: SKILL Phase 2 static table (200 chars/col), page-builder
declared `capacity_chars_per_col` (80 chars/col), and per-component
hard caps in render functions (e.g. `paragraphs[]≤400`). Phases drafted
against different numbers, surfacing only at compose. v3.14 unifies on
the page-builder's declared values, exposes them via `capacity.py`, and
adds Phase 4 cap enforcement so violations are caught before Phase 5.

### Principle 7 · Two-loop fit discipline (v3.4)

Box-level whitespace and slide-level whitespace are TWO SEPARATE problems
solved in two passes. Don't conflate them. This was the missing rule
that caused v3.3 P6 + T6 to keep failing in practice.

**Loop 1 — peer-equalization within a row.** Each box's height = its
natural content height. Peer boxes in the same row already align to
`max(natural_heights)` of the peer set under `grid-template-rows: auto`
(default browser grid behavior). NEVER use `1fr` to stretch boxes to
fill canvas — that causes the "200-char card stretched to 600px tall
with 70% empty" anti-pattern that v3.3 was supposed to fix but didn't,
because the rule was advisory and the default was still `1fr`.

**Loop 2 — slide-level whitespace.** After Loop 1 settles, the slide
canvas may still have empty space at the bottom. That's a SEPARATE
decision:

| Bottom whitespace | Action |
|---|---|
| <25% | Intentional breathing space — ship as-is |
| 25-50% | Must address, in priority order: (1) add real content, (2) add intentional decoration, (3) restructure layout |
| >50% | Layout is fundamentally wrong — redesign |

**Forbidden:** stretching boxes via `1fr` rows to "fill canvas" with
content that doesn't deserve the space. Always fix the imbalance at
its source — content (P6) or decoration (P3 patterns) — never via
artificial row stretch.

**Why P7 is separate from P6:** P6 governs cell-level content density
(chars per cell vs cell capacity). P7 governs the visual contract
between cells in a row, and between the row stack and the slide canvas.
A slide can pass P6 (every cell ≥70% filled) and still fail P7 (the row
stack only fills 50% of the canvas — needs more rows, not bigger rows).

**Phase 5 default change (v3.4):** When constructing rows, default
`height="auto"`. Use `height="1fr"` only when content density has been
verified ≥70% of cell capacity AND the row needs to anchor visual
weight (e.g. hero stat slide). Document the justification inline.

**Composer behavior (v3.4 default, v3.5 enforcement):** Composer
currently accepts `1fr` without challenge. v3.5 will warn when `1fr` is
used with projected fill <70%. Until then, the discipline is human-read.

### Principle 8 · Visual + content balance is mandatory (v3.16)

A slide is a **visual medium**, not a wall of text. Every content slide
must carry both **substance** (the message) AND **visual element**
(something the eye can read in 2 seconds). Text-only slides ARE allowed
when the message genuinely demands prose — but they must be the
**exception, not the default**.

**The anti-pattern v3.16 rules out:**

A 16-slide deck where 13 slides use `narrative + supporting_stats`
or `features_3` cards. Every slide reads the same. The eye gets no rest.
The reader's brain processes everything as paragraphs. The deck fails
its job because it's a long-form document pretending to be slides.

**The discipline:**

For every content slide in Phase 2 outline, **first** consider visual
options FROM THE LIST BELOW. Only fall back to narrative-paragraph if
none of these can carry the message.

| Content type | Visual-first option | Fallback |
|---|---|---|
| **Process / sequence** ("how X works", workflows) | `process-flow` (3-7 steps with title+body) | narrative split into ordered list |
| **Data / metrics** ("our 5 KPIs", forecast results) | `bar-chart`, `pie-chart`, `gauge-dial`, `kpi-row` | `supporting_stats` |
| **Comparison** (A vs B, before/after) | `comparison-table`, `before-after`, `vs-divider` | 2-col `narrative` |
| **Evidence / proof** (case studies with screenshots) | `image-tile` (lift from source) + brief narrative | narrative-only |
| **Many parallel items** (8-12 services, certifications) | `icon-list` (compact density), `logo-grid`, `catalog-column` | `bullet-list-checked` (last resort) |
| **Hierarchy / relationships** (org structure, 3-tier system) | custom inline SVG (P5) | narrative + indented list |
| **Hero proof point** (one big number that anchors) | `stat-hero` + corroborating component | narrative |
| **Capability / feature group** (3 things together) | `features_3` (3 cards × 1 row only — never stack rows) | catalog-column |
| **Continuous narrative** (story, methodology, philosophy) | narrative-paragraph (≤4 paragraphs) | — |

**Hard rules:**

1. **Per-slide rule** — every content slide must satisfy at least ONE:
   (a) uses a visual component from the list above, OR
   (b) has `image_decision.kind = 'lift' | 'synthesize'` (real image planned), OR
   (c) uses a custom SVG / hand-built layout (P5), OR
   (d) is a `narrator` special-page (about-vti, who-we-serve, etc.),
   (e) has explicit `text_only_justification` field in the outline
       (Claude must articulate WHY this slide can't carry a visual).

2. **Per-deck rule** — across all content slides in a deck:
   visual-bearing slides ≥ 60%. Below 60% triggers a wireframe-time
   warning. Below 40% blocks Phase 5 — the outline must be revised.

3. **Anti-stacking rule (v3.16, slide 06 lesson)** — components with
   fixed-height headers MUST NOT stack vertically:
   - `practice-card` (used by `features_3`): max **1 row × 3 cards**.
     Two rows squeezes the body to ~80px; clipping is guaranteed.
     For >3 capabilities, use `icon-list` or `catalog-column`.
   - `stat-hero`: max 1 per slide (visual-anchor role).
   - `value-medallion`: max 1 row × 4-6 cards.

4. **Source-image lift rule** — when source PPTX/PDF/video has usable
   visuals, prefer `lift` over `text-only`. The pipeline includes
   `extract_pptx_images()` (v3.15) for exactly this. A case-study slide
   describing an app with no app screenshot is a missed opportunity.

**Phase 2 enforcement:** outline table now has a `visual_strategy`
column (alongside `image_strategy`) that must be one of:
  - `<component-name>` (e.g. `process-flow`, `bar-chart`, `image-tile`,
    `logo-grid`, `pie-chart`, `icon-list`)
  - `custom-svg` (with description of what's drawn)
  - `image-lift` / `image-synthesize` (image provides the visual)
  - `text-only:<reason>` (only if Claude can articulate why)

**Phase 4 enforcement:** new visual block kinds — `image_tile`,
`process_flow`, `bar_chart`, `pie_chart`, `logo_grid`, `icon_list` —
are first-class blocks in `CONTENT_BLOCK_SCHEMAS`. Plans can declare
them directly; `plan_to_slide_input` composes them into slide rows.
This means Phase 4 drafts visual components, not just Phase 5 layout.

**Cross-phase audit (v3.16):** `audit_visual_balance(plans)` returns:
```
{
    'visual_count':      int,    # slides with at least one visual block
    'text_only_count':   int,
    'visual_pct':        float,  # 0-100
    'flag':              'ok'|'warn'|'block',
    'text_only_slides':  list[str],
    'recommendations':   list[{slide_id, suggestion}],
}
```
Use after Phase 4, before Phase 5 wireframe.

**Why this principle exists (v3.16 rationale):** The pre-v3.16 skill
default biased Claude toward `narrative + stats` because those blocks
were the most documented and lowest-risk in the schemas. The other 30+
components — process-flow, charts, image-tile, logo-grid — were
catalogued but not surfaced in Phase 2 reasoning. Result: every deck
came out 80%+ text. The user's correction was unambiguous: a deck of
all-text slides fails its medium. v3.16 rewrites Phase 2 reasoning to
default-include visuals and treat text-only as the exception requiring
justification.

### Principle 9 · Image content awareness & fit (v3.17)

When v3.16 surfaced visual components, Claude over-corrected: it began
lifting any large image from source PPTX/video as "evidence" without
inspecting what the image actually showed, and it dropped lifted images
into vertical stacks that compressed them below readability.

User's correction was specific:
> *"các hình bạn cut ra nó thể hiện 1 thông tin cụ thể và đâu thể bị
> crop như vậy được... nếu bạn đưa vào thì phải hiểu nó là cái gì và
> cho vào để làm gì và phải giữ được ý nghĩa cho nó chứ k phải cho vào
> để decord cho hết trống slide"*

Translation: *images extracted from sources convey specific information
and can't be cropped like that. If you bring an image in, you must
understand what it is, why you're using it, and preserve its meaning —
not just dump it in to fill empty space.*

The discipline:

**Before lifting an image — visual inspection is mandatory.**

Auto-extracted images from PPTX/video fall into 3 categories:

| Category | What it looks like | Action |
|---|---|---|
| **Content** | Diagram, screenshot, chart, infographic, branded UI | ✓ Lift if message-relevant |
| **Chrome** | Divider banner, chevron, decorative tinted shape, branded triangle/wedge | ❌ NEVER lift — chrome from another slide's design, not content |
| **Stock** | Generic photo (skyscrapers, hands on tablets, abstract networks, smiling executives) | ❌ NEVER lift — placed in source for visual flow, carries no message |

**Picking by file size is forbidden.** The PPTX largest image may be a
brand-identity chrome graphic (often 1-3 MB because it's a high-res
photograph composited inside a triangular frame). Always view-then-pick.

**For each candidate image, answer 3 questions:**
1. *What does this image actually show?* — articulate the message in
   one sentence
2. *Does it match THIS slide's message?* — Scan&Go case study needs a
   Scan&Go-specific screenshot, NOT a generic retail-tech landscape
3. *What's the natural aspect ratio and minimum readable size?* — a
   dense architecture diagram needs ≥60% slide width; a 4:3 dashboard
   should not be forced into 16:9 cell

**No suitable image → don't force one.** The right move when source
lacks a slide-relevant image is one of:
- Use a different visual approach (process-flow, chart, logo-grid)
- Build custom SVG (Principle 5 — when message demands it)
- Accept content-dominant layout with intentional whitespace (Principle 7
  Loop 2)

**Never grab any image just to satisfy "Principle 8 visual quota".**

### Image layout — two patterns only

When you DO lift a content-grade image, layout follows ONE of two
patterns. No mixed/middle-ground: those are the "compressed image
under text stack" anti-pattern that v3.17 rules out.

**Pattern A · Content-first with supporting image.**

Use when: you have substantive narrative + stats AND want a visual
anchor for emotional or contextual support (NOT to deliver new info).

Layout:
- Content occupies majority of slide (≥60%)
- Image is supporting element: ~30-40% of slide width OR a small hero
  block near top
- Image is sized so its native aspect ratio is preserved
- Image conveys mood/context, not detail — readers don't need to read
  text inside it

```
┌────────────────────────────────────┐
│ [content row: hero_stat + narr]    │
│                                    │
│ ┌──────────┐  ┌─────────────────┐  │
│ │  IMAGE   │  │  narrative      │  │
│ │  (small) │  │  (3-4 lines)    │  │
│ └──────────┘  └─────────────────┘  │
│                                    │
│ [stat row: 4 supporting stats]     │
└────────────────────────────────────┘
```

**Pattern B · Image-first with supporting content.**

Use when: the image IS the message — architecture diagram, dashboard
screenshot, complex infographic. Reader must be able to read text
inside the image.

Layout:
- Image dominates: ~60-70% of slide width OR full-width with content
  band below
- Content (1-2 short paragraphs + caption) arranged beside or under
  the image — NEVER above it (image is the lede)
- Stats, if present, go on a thin band, never compressed beside image
  in a way that shrinks the image

```
┌────────────────────────────────────┐
│ ┌──────────────────┐  ┌──────────┐ │
│ │                  │  │ context  │ │
│ │      IMAGE       │  │ narr     │ │
│ │   (8/12 cols)    │  │ (4/12)   │ │
│ │                  │  │          │ │
│ └──────────────────┘  └──────────┘ │
│                                    │
│ [stat row: thin, full-width]       │
└────────────────────────────────────┘
```

OR full-width image variant:

```
┌────────────────────────────────────┐
│ ┌────────────────────────────────┐ │
│ │       IMAGE  (full width)      │ │
│ │                                │ │
│ │         (60-70% height)        │ │
│ └────────────────────────────────┘ │
│ caption / 1-line context           │
│ [stat row: 3-4 stats, thin]        │
└────────────────────────────────────┘
```

**Forbidden anti-patterns (v3.17 explicit):**

- 🚫 **Image-cropped-by-cell**: image's natural aspect doesn't match
  cell aspect, `object-fit: cover` crops critical content (chart axes,
  table rows, label columns). Always set `aspect_ratio` on image-tile
  to match source.
- 🚫 **Compressed-image-under-text-stack**: 3-row vertical stack with
  image as small middle row. Shrinks dense diagrams below readable
  size. Use Pattern A or B, never compress.
- 🚫 **Decorate-to-fill**: empty bottom 40% of slide → drop random
  image. The right answer is content (P6), not chrome filler.
- 🚫 **Cropped-edge content**: layout cuts off the right or bottom
  ~10-20% of image. Critical info often lives at edges (legends,
  rightmost columns, footer notes).

**Phase 2 outline impact (v3.17):** the `visual_strategy` column for
image-bearing slides must specify:
- `image-lift:pattern-a` (content-first)
- `image-lift:pattern-b` (image-first)
- `image-lift:full-width` (image-first variant)

Phase 4 plan_to_slide_input must compose the corresponding row
structure (cell col_spans, row heights) accordingly.

### Principle 10 · Voice & tone — write like a person, not a spec sheet (v4.6)

Slide narrative blocks are read as if a presenter is speaking them out
loud. Telegraphic, dash-stitched fragments — `Telco-AI peer experience —
SK Telecom runs three live AI programs with VTI today.` — read as
analyst notation, not human speech. The reader has to mentally re-inflate
each fragment into a sentence, which is friction.

**Mandatory voice handshake (Phase 2, before slide-content drafting):**

When the deck outline is approved at the Phase 2 ★ checkpoint, **before
moving into Phase 3 CONTENT-PLAN, ask the user one question**:

> *"What voice should this deck use? Pick one (or describe your own):*
> *— **Consultative-sales** (peer-to-peer, confident, plain language; default for client decks)*
> *— **Technical-deep** (precise, jargon-OK, dense; for engineering audiences)*
> *— **Executive-brief** (terse, outcomes-first, minimal hedging; for C-suite)*
> *— **Educational** (explanatory, pedagogical; for training/onboarding decks)"*

Lock the answer into `plan['voice']`. All Phase 3 narrative drafting reads
this field and writes accordingly. If the user does not answer, default to
**consultative-sales** — it is the most common deck purpose.

**Writing rules that apply to ALL voices (after handshake):**

1. **Full sentences, not fragments.** `Compliance-by-design — 3-Ministry,
   HL7 FHIR, GDPR, PIPA — translatable directly to PDPA, IMDA, HSA.` →
   `Compliance is built in — the 3-Ministry, HL7 FHIR, GDPR and PIPA
   work we already do maps cleanly onto Singapore's PDPA, IMDA and HSA.`

2. **Spell out compressed jargon when it appears in narrative.**
   `edge→gateway→GPU spine` is fine on a diagram label; in prose, write
   `the same edge / gateway / GPU pipeline` or `edge servers feeding into
   gateway GPUs`. The arrow notation reads as code, not English.

3. **No more than ONE em-dash interruption per sentence.** Stacked dashes
   (`X — Y — Z`) make the reader parse three clauses at once.

4. **Avoid tribal compressions** — `near-as-makes-no-difference`,
   `Day-1`, `mid-pivot`, `slideware`. They are insider shorthand that
   reads as cleverness rather than clarity. Prefer `almost
   one-for-one`, `from day one`, `is in the middle of moving`,
   `slides`.

5. **The reader should never need to re-inflate a phrase into a sentence
   to understand it.** If they do, the phrase is too compressed.

**Voice-specific tweaks** (applied on top of the universal rules):

| Voice | Pronouns | Hedging | Sentence length | Jargon density |
|---|---|---|---|---|
| Consultative-sales | "we" / "you" | mild ("almost", "roughly") | 12–22 words | low–mid |
| Technical-deep | "the system" / "we" | minimal | 15–30 words | high (acceptable) |
| Executive-brief | omitted subject ok | none | 8–14 words | low |
| Educational | "we" / "you" / "this" | explanatory | 10–25 words | low, defined on first use |

**Enforcement points:**
- Phase 2 close-out: **MUST** ask the voice question before Phase 3
  starts. This is a checkpoint, not optional.
- Phase 3 CONTENT-PLAN: every `narrative-paragraph` and
  `bullet-list-checked` block must conform to the locked voice + the
  universal rules above.
- Phase 6 REVIEW-AND-COMPOSE: spot-read 3–5 narrative blocks. If any
  fragment-style or stacked-dash sentences slipped through, bounce back
  to Phase 3 with the offending text quoted.

The reason this is now a hard principle: presenter-mode slides are read
aloud or skim-read by a sceptical exec. Spec-sheet prose forces them to
do extra work — and tribal jargon (`Day-1`, `slideware`) signals
in-group knowledge they may not have, which subtly excludes them from
the conversation. Both weaken the pitch.

### How these principles bind to the 5-phase pipeline

| Phase | Where the principles apply |
|---|---|
| Phase 1 ANALYZE  | Identify potential hero elements per slide topic; flag slides where existing components likely won't carry the message (custom-build candidates) |
| Phase 2 OUTLINE  | Each slide row in the outline table commits to **layout sketch + char budget** (P6 v3.4). Image strategy column commits to "lift / synthesize / custom-svg" — not just "no image". Already at this phase the slide's projected fill rate must be ≥70%. **Voice handshake (P10):** before exiting Phase 2, ask the user which voice the deck uses (consultative-sales / technical-deep / executive-brief / educational); store in `plan['voice']`. |
| Phase 4 CONTENT  | Draft content to the budget declared in Phase 2 (P6 v3.4). If draft falls below 70%, BOUNCE BACK to Phase 2 with a narrower-layout proposal — do not proceed. **Voice (P10):** every narrative paragraph and bullet conforms to the locked `plan['voice']` and the universal rules (full sentences, no stacked dashes, no tribal compressions like `Day-1`/`slideware`/`mid-pivot`). |
| Phase 5 LAYOUT   | Default row height = `auto` (P7 Loop 1). `1fr` only with documented justification + content-fill verification. Wireframe MUST show focal point clearly. After Loop 1 settles, evaluate Loop 2 slide-bottom whitespace per P7 decision table. |
| BUILD            | Re-screenshot each slide and audit DOM for type/color violations (`audit_typography.py`). Spot-check 3-5 slides for content-fill ratio AND slide-bottom whitespace (visual judgment under P7). |

## Phase 1 — ANALYZE (Sprint 4)

Source ingestion + ContextDoc construction.

**Source readers** — `source_ingester.py`:
- markdown / text / html → direct Python (always available)
- docx / pdf / pptx → returns a stub with `next_action` directing
  Claude to read the relevant SKILL.md (`/mnt/skills/public/{docx,pdf-reading,pptx}/`).
  After Claude extracts text + images via the format-specific skill,
  call `ingest_pre_extracted()` to build the normalized result.

**Image extraction is mandatory.** Both PDF and PPTX sources typically
contain useful images (hero photos, diagrams, screenshots). Extract them
during Phase 1 — do NOT pass `assets=[]` and skip. Use `pymupdf` for PDF
and zipfile inspection of `ppt/media/` for PPTX. Substantive images
(>5KB, not logo strips) become Phase 4 lift candidates.

**ContextDoc** — `context_doc.py`:
- Required: `audience`, `purpose`
- Optional: `customer`, `tone` (one of 7 valid tones), `source_summary`,
  `source_assets`, `key_facts`, `constraints`
- Tones: formal | conversational | technical | sales-pitch |
  executive-brief | training | academic

### Phase 1 question methodology (CRITICAL)

The audience/purpose/tone inference is Claude's reasoning over the
ingested source. Always **propose first then ask the user to confirm**.

**DO ask** the user about things they know and we cannot infer:
- **Viewer role** — "Who specifically will see this deck? CEO / CTO /
  Head of Engineering / PM / Procurement / mixed audience?" The role
  determines what evidence and abstraction level matters.
- **Usage context** — "Will this be presented live (~15 min, ~30 min,
  full hour)? Sent ahead for self-reading? Used as leave-behind after a
  demo? Marketing/promotional broadcast?" Determines density and
  self-containment.
- **Specific customer / industry interest** — "Generic intro deck, or
  tailored for a specific prospect / vertical?" Determines how much
  domain framing to add.
- **Language** — output language of the deck.

**DO NOT ask** the user about things they cannot easily picture:
- ❌ "How many slides do you want?" — slide count is an OUTPUT of
  Claude's reasoning, not an input. Users cannot intuit "12 vs 16
  slides" — they intuit "I have 15 minutes to present".
- ❌ "What density / tone / format?" — these are derivatives Claude
  recommends from the inputs above.
- ❌ Open-ended "what do you want this deck to do?" — too vague.

After the user confirms viewer + usage + customer + language, Claude
**recommends** length, density, tone, and structural approach with
explicit reasoning (e.g. "15 min present + send-ahead for CTO + Sing
healthcare prospect → 14-16 slides, executive-brief tone, modular slides
that work both in-room and self-read").

## Phase 2 — PLAN-OUTLINE (Sprint 5)

Deck arc design — Claude reasons over the ContextDoc to produce a
DeckOutline.

**DeckOutline** — `deck_planner.py`:
- `doc_title`, `section_arc`, `slides`
- Each slide entry: `slide_id`, `kind`, `topic`, `section`, `summary`,
  `block_kinds` (planned for Phase 4), `image_strategy_hint`

**Slide kinds**:
- `content` — most slides; built via Phase 4 + 5
- 5 framing kinds: `cover`, `toc`, `section-divider`, `contact`, `closing`
- 8 narrator kinds (lift-and-shift v2 specials): `about-vti`, `vision-mission-values`,
  `who-we-serve`, `awards-certifications`, `strategic-partners`,
  `project-management-method`, `quality-assurance`, `quality-management-process`

### Phase 2 output format — REQUIRED markdown table (v3.4)

The `render_outline_summary()` text output is for debugging only. When
presenting the outline to the user, ALWAYS render it as a markdown table
with these columns in order:

```
| # | Section | Kind | Topic | Block kinds | Layout sketch | Char budget | Image strategy | Rationale | Need Input |
```

- `#` — page number (01, 02, …) zero-padded
- `Section` — section name or `—` for unsectioned (cover/toc/contact)
- `Kind` — slide kind from the taxonomy above
- `Topic` — slide title (concise)
- `Block kinds` — comma-separated for content slides, `—` for framing/narrator
- `Layout sketch` — **NEW v3.4 (P6)** — 1-line sketch of the planned grid:
  e.g. `narrative 7 + kpi-strip right 5`, `3-col features_3 + kpi-row 12`,
  `hero stat 5 + narrative 7 + kpi-row 12`. Must be concrete enough that
  a reader knows the row count and span split.
- `Char budget` — **NEW v3.4 (P6)** — total chars target across all cells
  for this slide (after subtracting chrome). Derived from the capacity
  reference table for the chosen layout sketch. Example: `~1400 chars`
  for hero+narrative+kpi-row.
- `Image strategy` — **concrete description**, NOT just a one-word strategy.
  Examples: `Lift pdf/p03-00 (VTI HQ photo)`, `No image — text-only`,
  `Synthesize: redraw architecture as horizontal process-flow`,
  `Built-in narrator illustration (map + circles)`. The user must be
  able to read this column alone and know exactly what visual will land
  on the slide.
- `Rationale` — 1-line explanation of WHY this strategy was chosen for
  THIS slide.
- `Need Input` — ✅ + brief note if user input/asset/decision is required
  (e.g. `✅ disclose client name?`, `✅ override narrator copy?`,
  `✅ provide licensed MRI image?`). Leave blank if no user action needed.

Below the table, also report:
- Total slide count, kind distribution, section distribution (one line each)
- **Total deck char budget** — sum of all per-slide char budgets (v3.4)
- Quick rationale (2-3 lines) of arc structure choices

This is the ONLY presentation format the user should see for the
outline. Bullet lists, prose narration, or paragraph descriptions of
slides are not acceptable substitutes.

## Phase 3 — PLAN-REVIEW (Sprint 5)

PLAN-REVIEW is its OWN checkpoint, distinct from Phase 2. Phase 2
produces the outline; Phase 3 is the conversation that approves or
edits it. Never collapse them together.

### Phase 3 protocol

1. After Phase 2 renders the outline table, the skill enters Phase 3
   automatically.
2. Ask the user 1-3 specific yes/no/edit questions about the outline
   (NOT open-ended "what do you think"). Suggested checkpoints:
   - "Duyệt structure 4-act / N-slide?"
   - "Case study selection ổn? Swap case nào?"
   - "Có muốn cắt / thêm slide nào không?"
3. **STOP. Wait for user reply.** Do not advance to Phase 4 on the
   same turn.
4. If user requests changes → use `add_slide / remove_slide /
   move_slide / replace_slide` helpers to apply, re-render the outline
   table, ask again. This loop is part of Phase 3.
5. If user approves (`OK`, `duyệt`, `giữ`, `proceed`, etc.) → that's
   the green light to enter Phase 4.

Each turn in Phase 3 must be labeled "Phase 3 — PLAN-REVIEW" in the
output so the user knows where we are in the pipeline. Do not skip this
labeling — it's how the user tracks the brainstorm checkpoint.

### Phase 3 image-decision protocol (v4.4 — semantic, not heuristic)

Picking an image for a content slide is a **4-step AI-reasoning loop**,
not a one-shot heuristic. The pre-v4.4 path
(`resolve_lift_image()` in `content_drafter.py`) scored candidates by
classifier confidence + filename token match — both purely structural.
That selected the same "highest-scored content image" for every slide
sourced from one pptx, and let semantically-irrelevant photos
(portraits, decorative graphics) through whenever their aspect ratio
or filename happened to look like content. v4.4 replaces it with the
explicit per-slide protocol below.

For each content slide whose author proposed `strategy="lift"`:

1. **Necessity check.** Read the slide's topic + summary + drafted
   blocks. Ask out loud: *Does this slide's message actually benefit
   from a screenshot, or is the message already complete in text?* If
   no benefit → skip steps 2-3, jump straight to step 4 (escalate to
   `text-only`).

2. **Candidate enumeration.** Call
   `enumerate_candidates(slide_plan, asset_index, source_tags=[…],
   claimed_paths=already_used)` to get top-K filename-scored
   candidates from the relevant source(s). The `claimed_paths` set
   enforces the best-fit rule: an image used by another slide is
   excluded so each slide gets a distinct image.

3. **Visual inspection.** For each candidate, the orchestrator (Claude
   / a human reviewer) opens the image with a vision-capable tool
   (`Read` for paths in this skill, or a vision API for raw bytes) and
   writes a 1-line caption describing what's actually in the picture
   (dashboard? architecture diagram? portrait? logo? UI mock?). Persist
   the caption with `set_caption(asset_index_path, image_path, …)` so
   later slides reuse it without re-inspecting.

4. **Decision + auto-escalation.** Pick one of three strategies and
   record it via `record_image_decision(plan_path, slide_id,
   ImageDecision(...))`:

   - **`lift`** — A candidate's caption semantically matches the slide
     message. Record `resolved_image` with `path` + `natural_w/h` +
     the matching candidate's caption.
   - **`synthesize`** — No candidate fits, but the slide's content is
     architectural / process-shaped (a workflow, a layered system, a
     before/after, a data pipeline). Switch to a diagram via
     `vti-slide-diagram-builder` and record `diagram_spec`.

     **Content discipline (paired with diagram-builder v0.4.0+).** Node
     labels are action/state names only (`DISCOVER`, `BATCH-STAMP`,
     `CRAWL ACTIVE`) — no metrics, no times, no cardinalities. The
     builder enforces this with `_assert_step_clean` and will raise
     `ValueError` on offenders. Route quantitative info to the
     parallel `captions` array, which the page-builder renders as a
     compact text strip beneath the SVG:

     ```python
     # BAD — diagram-builder raises ValueError
     make_flow_diagram(steps=[
         {"title": "BATCH-STAMP", "sub": "180+ inactive · 1 Drive write"},
         ...
     ])

     # GOOD — labels stay clean, numbers move to captions
     make_flow_diagram(
         steps=[
             {"title": "DISCOVER"},
             {"title": "CLASSIFY"},
             {"title": "BATCH-STAMP"},
             {"title": "CRAWL ACTIVE"},
         ],
         captions=[
             "all spaces · lastActiveTime",
             "client-side",
             "180+ inactive · 1 write",
             "~20 active · paginate",
         ],
     )
     ```

     Include `captions` in the persisted `diagram_spec` so Phase 4
     forwards it to the image-tile cell:

     ```python
     diagram_spec = {
         "primitive":  "flow_diagram",
         "args":       {...},
         "svg_path":   "work/diagrams/<slide_id>.svg",
         "natural_w":  <int>,
         "natural_h":  <int>,
         "captions":   [...],   # parallel to steps; may be []
     }
     ```

   - **`text-only`** — No candidate fits AND the message isn't
     diagram-shaped. Drop the image; the layout-designer will
     vertical-stack the existing blocks. If post-drop fill < 70%, add
     a supporting block (kpi-row, hero stat, narrative paragraph).

   The orchestrator auto-escalates without re-asking the user. The
   `rationale` field on the `ImageDecision` records WHY the strategy
   changed — surfaced in the phase_3 summary so the user can audit
   overrides without re-running the picker.

**Multi-slide case studies** (e.g. `s13-oliveyoung-case`,
`s14-oliveyoung-platform`, `s15-oliveyoung-ml`) MUST be allocated
together via `allocate_case_study_images(slides_in_cs, ranked_per_slide)`.
Best-fit rule: when N candidates ≥ M slides, do a 1-to-1 assignment by
caption-vs-topic score; when N < M, give the available image(s) to the
slide(s) where it adds the most value (typically the case-study
overview), and escalate the rest to `synthesize` or `text-only`.

**Why orchestrator-in-the-loop and not pure-Python.** Filename and
aspect-ratio heuristics filter chrome out of the candidate set
(`classify_image_kind` does this). Picking a content image whose
*content* matches a slide's message requires visual understanding —
what's drawn, what labels exist, what business context. That's a
vision-model job. The skill provides the data plumbing
(enumerate / cache / record) and the orchestrator is the model.

### Phase 4 output format — REQUIRED structure

Image strategy is already locked in Phase 2's 8-column table. Phase 4
focuses on **concrete content** per slide and resolving open items.

When presenting Phase 4 output for the brainstorm checkpoint, structure
the response in this fixed order:

1. **Per-slide content draft** — for each content slide:
   - Header: `### s##-id · Topic`
   - One sub-block per block kind, showing concrete content as it will be
     passed to `make_block(kind, content)` — narrative paragraphs verbatim,
     stat values + labels, card titles + bodies + icons, list items
   - For slides with manual Phase 5 components (process-flow, tags, etc.
     not in the 8 block kinds), include a `[MANUAL Phase 5: <component>]`
     section with the planned content.
   - Do NOT use prose narration. The user must see what compose_slide_grid
     will receive.

2. **Narrator + framing slide props** — non-default values for cover
   (`deck_title`, `deck_tagline`), TOC (`toc_items`), section-divider
   (`section_title`, `section_description`), narrator (`intro_text` if
   overriding default).

3. **Open items list** — explicit list of:
   - Research items pending (with proposed search queries)
   - Content needing user verification (client names, NDA, exact figures)
   - Anything still ambiguous from Phase 2 outline

4. **2-4 specific brainstorm questions** — yes/no/edit form, not open-ended

After this output: STOP. Do not enter Phase 5 until user replies.

## Phase 4 — Content drafter (Sprint 3)

For each slide topic from the DeckOutline, Claude reasons through:

```
4.1  DECOMPOSE   raw content ─▶ typed blocks (narrative, stats, ...)
                  8 block kinds: narrative, hero_stat,
                  supporting_stats, list, features_3, values,
                  catalog, comparison_divider

                  ⚠ slide title + section name are NOT blocks. They
                  ride on the plan envelope (`topic` + `section_name`)
                  and are rendered into the chrome breadcrumb at
                  Phase 5. Content blocks hold actual content only.

4.2  IMAGE       decide strategy: lift | synthesize | web-search | text-only
                  use suggest_strategy() heuristic, override per context

4.3  ASSEMBLE    wrap blocks + image_decision into SlideContentPlan
                  validate_plan() before handing off to Phase 5
```

### Quick API (Phase 4)

```python
from creator import (
    # block kinds + image strategies
    CONTENT_BLOCK_SCHEMAS, IMAGE_STRATEGIES,

    # constructors
    make_block, make_image_decision, make_slide_content_plan,

    # validators
    validate_block, validate_plan,

    # heuristics
    suggest_strategy, describe_strategies,

    # Phase 4 → 5 bridge: auto-compose slide_input from plan
    plan_to_slide_input,
)
```

### Block kinds catalog

| Kind | Required | Maps to component(s) |
|---|---|---|
| `narrative`          | paragraphs[1-4] | narrative-paragraph |
| `hero_stat`          | value, label | stat-hero |
| `supporting_stats`   | items[2-5] | kpi-row (stat-mini × N) |
| `list`               | items[2-8] | bullet-list-checked |
| `features_3`         | cards[3] | practice-card × 3 |
| `values`             | cards[4-6] | value-medallion × N |
| `catalog`            | columns[2-3] | catalog-column × N |
| `comparison_divider` | (label, has_line) | vs-divider |

Slide title + section are NOT block kinds. They live on the
SlideContentPlan envelope (`topic` and `section_name`) and ride the
chrome breadcrumb as "SECTION | TITLE".

### Phase 4 → 5 bridge — `plan_to_slide_input(plan)`

Auto-composes a starter slide_input from a SlideContentPlan. The plan's
`topic` becomes `slide_meta.slide_title` and its `section_name` becomes
`slide_meta.section_name` — both are rendered by chrome at top-left as
"SECTION | TITLE", never as a content row. Block→row defaults:
`hero_stat + narrative` → 5+7 split, peer cards in even-split rows,
kpi-row at the bottom. Claude can use the output as-is or customize via
grid_helpers for non-default arrangements (asymmetric, compare-mirror,
etc.).

## Phase 5 — Layout brainstorm loop (Sprint 2)

For each slide, Claude reasons through 4 sub-steps:

```
5.1  DECOMPOSE   raw content ─▶ typed blocks
                  e.g. {kind: "stat", value: "1,200+"},
                       {kind: "narrative", paragraphs: [...]}
                       
5.2  PICK        each block ─▶ a component from catalog
                  consult component_catalog.COMPONENT_CATALOG
                  for role + good_for + bad_for + best_col_spans

5.3  COMPOSE     components ─▶ 12-col × N-row grid descriptor
                  use grid_helpers (even_split, asymmetric_split,
                  stat_plus_narrative_row, cards_row, …)

5.4  WIREFRAME   slides[] ─▶ render_layout_review_widget()
                  ─▶ visualize:show_widget for batch user review
                  16:9 box per slide · empty bottom = sparse signal
                  red border = predicted overflow

[user feedback] ─▶ apply slide_edits per slide ─▶ re-wireframe
                   loop until "○ clean" across all slides

5.5  COMPOSE_DECK final descriptor ─▶ compose_deck() → HTML
                  THEN ─▶ vti-slide-decorator skill (decoration layer)
```

### Phase 5.4 — Layout wireframe widget (CRITICAL · v3.13)

The widget is a **wireframe / blueprint** of the layout, NOT a rendered
slide. Its purpose is to let the user validate component placement,
visual hierarchy, image positioning, and visual fill density BEFORE we
commit to compose. Cheap to iterate at this stage; expensive after.

**API (v3.13):**

```python
from preview import render_layout_review_widget, deck_stats
import slide_edits

# Build all slides via creator helpers / make_slide / etc.
slides = [...]

# Phase 5.4 — primary checkpoint: render wireframe widget
widget_html = render_layout_review_widget(slides)
# Pass widget_html as `widget_code` to visualize:show_widget tool

# User reviews. Flags issues. Apply per-slide edits via slide_edits:
slides[16] = slide_edits.shorten_practice_cards(slides[16], max_chars=110)
slides[16] = slide_edits.change_decoration_label(slides[16], 'IN-STORE OPS')

# Re-render wireframe to verify fix lands
widget_html = render_layout_review_widget(slides)
# Show again. Loop until user OK.

# Then compose the final deck — single call now produces complete HTML:
from creator import build_deck_html
html = build_deck_html(slides, title=outline['doc_title'])
open('/path/to/deck.html', 'w', encoding='utf-8').write(html)

# build_deck_html (v3.17.1) wraps composer_grid.compose_deck() output
# in a full DOCTYPE + <html><head><style> + <body> shell. Without it,
# callers must manually concatenate deck['deck_html'] + deck['deck_css']
# in a hand-written shell — the gap that caused the v3.16 unstyled-deck
# bug. The default shell uses VTI page styling; pass a custom `shell`
# parameter for non-VTI rendering contexts.
```

**The wireframe widget shows (per slide):**
- 16:9 aspect ratio box matching real slide proportions — empty bottom
  area = visible sparse signal (whitespace will land in real render)
- Title bar with slide number, title, section · layout class
- Each row as a 12-col grid strip with proportional cells
- Each cell: component name + col-span + char count vs capacity
  (e.g. `narrative-paragraph 1-7 · 294/560c`)
- Color coding by component category:
  text=blue, data/stat=green, card=purple, visual=amber, structural=gray
- **Red border** on cell = predicted char overflow (chars > capacity)
- **Dashed border** on cell = predicted char sparse (< 40% of capacity)
- Footer with row/cell count, fill %, slide-level flags
- Slide-level flags: SPARSE (<40% fill), OVERCROWDED (>110%),
  OVERFLOW×N (cell-level), IMG×N-aspect-risk (image-tile present)

**Top stats strip:** total slides, total chars, sparse-flagged count,
overflow-flagged count.

**The wireframe MUST NOT:**
- Render the actual slide HTML via compose_slide_grid
- Screenshot a built slide
- Embed real component CSS / fonts / icons
- Look like the final slide visually

It is a **layout intent blueprint**, not a render preview.

**Render order**: build wireframes for ALL slides (special pages render
as compact bars since they have no row structure to wireframe), present
in chat as ONE widget call, ask user for batch approval or per-slide
edits. Loop until clean.

**Decision flow after wireframe:**

| Wireframe shows | Action |
|---|---|
| All slides "○ clean" | Proceed to compose_deck |
| Cell red-bordered (overflow) | Use `slide_edits.change_cell_props` to shorten content, or `change_cell_span` to widen, or `replace_row` for a different layout |
| Cell dashed (sparse) | Add content via `change_cell_props`, OR consolidate with `remove_row`, OR escalate to custom-build via `replace_with_custom_html` |
| Slide flag SPARSE (<40% fill) | Add a row, expand existing rows, or change `layout_class` to one with smaller capacity |
| IMG×N-aspect-risk | Set image-tile `aspect_ratio` matching source asset's natural ratio (4:3 / 9:16 / 1:1 / 21:9) |
| Decoration label too long | `slide_edits.change_decoration_label(slide, 'SHORT')` (≤18 chars to fit overlay) |
| Pattern repetition across slides | Diversify via custom-build (`replace_with_custom_html`) on 1-2 slides to break monotony |

**Decoration concern:** Phase 5 wireframe does NOT visualize decoration
overlays (those are added by `vti-slide-decorator` skill AFTER compose).
The wireframe only signals where decoration WOULD land (empty bottom of
16:9 box). If you don't want decoration on a specific slide, the new
decorator skill handles that — pass `strategies={slide_idx: 'none'}` or
similar opt-out at the decorator stage (see `vti-slide-decorator/SKILL.md`).

After wireframe approval → call `compose_deck(slides)` → call
`vti-slide-decorator` skill to add decoration layer → audit → final.

### What "build" means in this skill

The terminal output of this skill is **one HTML file** containing all
slides with deduplicated CSS. That's it. No PDF, no PNG screenshots,
no thumbnails. If the user later wants PDF, route to `vti-pdf-export`.

### Quick API

```python
from creator import (
    # 5.1 — content kind → component candidates
    picks_for_kind, describe,

    # 5.2 — column-span splitters
    even_split, asymmetric_split, with_divider,

    # 5.3 — row constructors (high-level)
    narrative_row,
    stat_plus_narrative_row, cards_row, kpi_strip_row,

    # 5.3 — slide constructor
    make_slide, make_cell, make_row,
)

# 5.4 — Layout review (v3.13 — primary checkpoint)
from preview import (
    render_layout_review_widget,  # batch wireframe → show_widget
    deck_stats,                   # programmatic stats
    render_inline_preview,        # single-slide full render (slow)
    render_grid_summary,          # plain-text grid summary
)

# 5.4 — Per-slide edits (during user iteration)
from slide_edits import (
    change_cell_props, change_cell_component, change_cell_span,
    add_cell, remove_cell,
    replace_row, add_row, remove_row, set_row_height, mark_fill_verified,
    change_slide_meta, change_decoration_label,
    change_layout_class,
    replace_with_custom_html,    # Principle 5 escape hatch
    shorten_practice_cards,      # convenience
    find_cells_by_component,     # locate cells for batch edits
)
```

### Reasoning template

For each new slide, walk this template aloud (in chat) before rendering:

> **Title routing** — section + slide title go straight onto
> `slide_meta.section_name` and `slide_meta.slide_title`. The chrome
> breadcrumb renders them as "SECTION | TITLE" at top-left. They are
> NOT a content row.
>
> **Decompose** — "this slide has: 1 hero stat, 1 narrative, 3 supporting facts"
>
> **Pick** — "hero → stat-hero, narrative → narrative-paragraph,
> supporting → kpi-row of 3 stat-mini"
>
> **Compose** —
> ```
> slide_meta:    section_name="About VTI", slide_title="Our Practices"
> Row 1 (1fr):   stat-hero col 1-5 + narrative col 6-12   (asymmetric 5+7)
> Row 2 (auto):  kpi-row col 1-12
> ```
>
> **Preview** — render widget. Loop with user until approved.

## Component catalog summary

13 atomic components (see `component_catalog.COMPONENT_CATALOG` for full
metadata). There is intentionally no in-slide title component —
section + slide_title ride the chrome breadcrumb.

| Kind | Components |
|---|---|
| text       | narrative-paragraph, bullet-list-checked |
| data       | stat-hero, stat-mini, kpi-row |
| card       | practice-card, value-medallion, catalog-column |
| structural | vs-divider |

## v3.18 helpers (gap closures)

Six gaps deferred from v3.17.1 are closed in v3.18.0. Quick reference:

```python
from creator import (
    audit_block_distribution,    # gap #22 — block-kind census + anti-patterns
    sources_for_section,         # gap #5  — multi-source section mapping
    classify_image_kind,         # gap #6  — content/chrome/stock heuristic
    cell_target_mode,            # gap #23/#32 — density-mode-aware drafting
    DENSITY_MODES,               # 'standard' | 'sparse-ok' | 'dense'
)

# Phase 1 — annotate sources with their target sections
ctx['sources'][0]['sections'] = ['ABOUT VTI', 'RETAIL CASES']
retail_srcs = sources_for_section(ctx, 'RETAIL CASES')

# Phase 1 — auto-classify lifted images (pre-screen for Principle 9)
assets = extract_pptx_images(pptx, out_dir, auto_classify=True)
content_candidates = [a for a in assets if a['kind_guess'] == 'content']

# Phase 4 — validate hint maps to a real asset
dec = make_image_decision('lift', source_hint='retail/p4 group photo',
                          available_assets=ctx['source_assets'])
# Raises ValueError if no caption fuzzy-matches.

# Phase 4 → 5 — pick density mode for hero / spec-sheet slides
plan['density_mode'] = 'sparse-ok'  # hero/breathing slides
plan['density_mode'] = 'dense'      # spec-sheet/detail slides

# Phase 5 — block-distribution audit (run alongside audit_visual_balance)
dist = audit_block_distribution(plans)
if dist['anti_pattern_flags']:
    print('Anti-patterns:', dist['recommendations'])
```

See CHANGELOG.md v3.18.0 for full details, including the band-table for
the three density modes and the scope-reduction note on gap #32 (hard
render caps remain mode-agnostic; that's a cross-skill change).

## Backward-compat notes

- chrome (header/footer breadcrumb + page num) — preserved verbatim from v2
- 13 special pages (cover, toc, section-divider, contact, closing,
  about-vti, vmv, who-we-serve, awards-certs, strategic-partners,
  pmm, qa, qmp) — preserved verbatim from v2

## Repo layout

```
vti-slide-creator/
├── SKILL.md                  # this file
├── creator.py                # main entry point + re-exports + phase placeholders
├── component_catalog.py      # static metadata for pick reasoning  (Sprint 2)
├── grid_helpers.py           # 12-col grid utilities                (Sprint 2)
├── preview.py                # in-chat widget renderer              (Sprint 2)
└── _contracts/               # JSON schemas (filled in next sprints)
```
