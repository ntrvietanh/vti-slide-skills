# vti-slide-diagram-builder

VTI-Standard diagram primitives for slide decks. Pairs with
`vti-slide-creator` (orchestrator) and consumes brand tokens from
`vti-slide-page-builder/tokens.css`.

## Why this skill exists

Before this skill, every deck rendered diagrams ad-hoc — colors drifted,
arrow heads varied, line weights shifted slide-to-slide. The skill
standardises 7 diagram primitives so all VTI decks share one visual
language.

Each primitive carries its natural dimensions, so the creator's Phase 4
layout-design step can choose a cell aspect ratio that **guarantees the
diagram is never cropped**.

## v0.5.0 — native-SVG branch restored

The v0.3.0 Mermaid migration produced diagrams with very inconsistent
output sizes (aspect ratios from 1.35 to 14.17 depending on content),
so Phase 4's layout-designer could not pre-size host cells reliably and
the page-builder ended up letterboxing or cropping. v0.5.0 restores the
v0.1.0 hand-authored SVG branch alongside the Mermaid backend.

Every `make_*` for the 5 dual-backend primitives now accepts a
`backend` kwarg:

- `backend="svg"` **(default)** — natively rendered to a complete
  `<svg>` element with predictable canvases (1180×280/320 for
  horizontal flow, 1180×480/520 for the rest). Returns
  `{primitive, backend, svg, natural_w, natural_h, captions}`. No MCP
  call required.
- `backend="mermaid"` — returns the v0.4.0 Mermaid render task with
  `mermaid_code` and `hint_w/hint_h`. Identical to pre-v0.5.0
  behaviour. Use this when you want the Mermaid look or for
  diagrams whose layout doesn't fit the SVG primitives.

Env override: `VTI_DIAGRAM_BACKEND={svg|mermaid}` flips the default
backend. Precedence is kwarg → env → `"svg"`.

The v0.4.0 brand discipline (blue-only palette, action-only labels via
`_assert_step_clean`, parallel `captions` array) carries forward into
v0.5.0: captions on the SVG backend are baked into a 40-pixel strip at
the bottom of the canvas, anchored under each step's x-position. On
the Mermaid backend captions remain external (page-builder strip).

## v0.4.0 — brand discipline pass

Three opinionated changes locked across all 5 Mermaid primitives so
diagrams stop drifting from VTI's visual identity:

1. **Blue-mono gradient.** Node fill is index-driven — `step0` is the
   palest blue, `step{n-1}` is navy. No more per-element accents that
   produced rainbow swimlanes. Theme variables also limited to the blue
   family + neutrals (no teal/amber/orange leaks).
2. **Round-edge nodes.** Every node renders with Mermaid's `(label)`
   round-rectangle shape (mild corner radius `rx/ry=14`). Subgraphs and
   `quadrantChart` cells stay rectangular — Mermaid doesn't expose
   shape config for them.
3. **Steps-only content.** Node labels are pure action/state names —
   no metrics, no times, no cardinalities. A new `_assert_step_clean`
   validator raises `ValueError` when an author tries to slip in
   `"~20 spaces"`, `"180+"`, `"08:00"`, `"5%"`, etc. Quantitative info
   goes to the new parallel `captions` array, which the page-builder
   renders as a small text strip below the SVG.

The legacy `accent` / `accent_alias` parameters are accepted for
back-compat but logged as `DeprecationWarning` and ignored.

## v0.3.0 — split-backend rendering

The 7 primitives split across two rendering backends:

| Backend  | Primitives | How it renders |
|---|---|---|
| `mermaid` | `flow_diagram`, `quadrant`, `layered_stack`, `fanout_pipeline`, `hybrid_swimlane` | The skill emits Mermaid source. The **agent** then invokes the Mermaid Chart MCP tool to render to SVG. |
| `python`  | `footprint_map`, `data_path` | Native Python SVG generation — the skill returns SVG directly. (Mermaid has no geo-map equivalent for footprint_map; data_path's brain-emphasis styling is hand-crafted.) |

`diagram_builder.backend_for(name)` returns the backend for a primitive.
`diagram_builder.MERMAID_BACKED` / `PYTHON_BACKED` are the frozenset
constants if you need to switch on them.

## When to use

Invoke this skill **at Phase 3 (CONTENT-PLAN)** of `vti-slide-creator`
≥ 4.0 — when a slide's `image_decision.strategy` is `"synthesize"` and
the diagram intent matches one of the 7 primitives. The agent picks the
primitive, fills the parameters from source-research notes, and gets
back either:

- a **render task** (mermaid backend) — agent runs the MCP step and
  saves SVG to `work/diagrams/<slide_id>.svg`, then reads the viewBox
  to get `natural_w` / `natural_h`, OR
- a **finished result** (python backend) — agent writes the returned
  SVG straight to disk; `natural_w` / `natural_h` already in the dict.

Either way the final `diagram_spec` written into the SlideContentPlan
has the same shape Phase 4 has always expected:

```python
{
    "primitive":  "flow_diagram",
    "args":       {...},
    "svg_path":   "work/diagrams/<slide_id>.svg",
    "natural_w":  <int>,
    "natural_h":  <int>,
}
```

## Public API surface

```python
from diagram_builder import (
    make_flow_diagram,        # 3-7 boxes + arrows (Mermaid)
    make_quadrant,            # 2x2 grid (Mermaid quadrantChart)
    make_footprint_map,       # APAC continent + city pins (Python SVG)
    make_layered_stack,       # 4-6 cards left→right (Mermaid)
    make_fanout_pipeline,     # input → N parallel → fusion → outputs (Mermaid)
    make_hybrid_swimlane,     # 2+ lanes sharing input (Mermaid subgraph)
    make_data_path,           # 4-stage flow w/ cloud-as-brain (Python SVG)
    list_primitives,          # discovery
    describe_primitive,       # metadata + params for one primitive
    primitive_for_intent,     # 'aws-reference' → 'flow_diagram'
    backend_for,              # 'flow_diagram' → 'mermaid'
    MERMAID_BACKED,           # frozenset of mermaid primitive names
    PYTHON_BACKED,            # frozenset of python primitive names
)
```

### Return shapes

```python
# backend == "mermaid"
{
    "primitive":     "flow_diagram",
    "backend":       "mermaid",
    "mermaid_code":  "%%{init:...}%%\nflowchart LR\n  S0(\"...\"):::step0 --> S1...",
    "hint_w":        1180,
    "hint_h":        280,   # caller compares to actual viewBox after render
    "captions":      ["all spaces", "skip vs active", "paginate", "daily digest"],
}

# backend == "python"
{
    "primitive":  "footprint_map",
    "backend":    "python",
    "svg":        "<svg ...>...</svg>",
    "natural_w":  1180,
    "natural_h":  480,
}
```

## Agent workflow for Mermaid-backed primitives

1. Pick the primitive: `primitive_for_intent(intent)` (or pick by hand).
2. Build kwargs from source-research notes.
3. Call `make_<primitive>(...)` — get back a render task.
4. Call MCP:
   ```
   mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram(
       diagramDefinition=task["mermaid_code"]
   )
   ```
5. Save the returned SVG to `work/diagrams/<slide_id>.svg`.
6. Read the SVG viewBox to recover `natural_w` / `natural_h`. Sanity-
   check the actual ratio against `task["hint_w"] / task["hint_h"]` —
   warn if they diverge by more than 25 %.
7. Construct the final `diagram_spec` and pass to
   `content_drafter.make_slide_content_plan(..., diagram_spec=...)`.

## Agent workflow for Python-backed primitives

Steps 1–3 unchanged. The returned dict already has `svg`, `natural_w`,
and `natural_h` — write `result["svg"]` to disk, build the
`diagram_spec` directly. No MCP call needed.

## Content discipline (v0.4.0)

The 5 Mermaid primitives share one authoring contract: **node labels
are pure action/state names; quantitative info goes to `captions`.**
Read this section before authoring any `make_*()` call.

### Rule 1 — node labels are actions, not data

- 1–3 words, prefer ALL-CAPS or Title Case, present-tense verbs
  (`DISCOVER`, `CLASSIFY`, `Stamp inactive`) or short state names
  (`Pending queue`, `Customer digest`).
- No digits. No units (`spaces`, `%`, `x`, `hours`, `MB`). No times
  (`08:00`, `daily 23:30`). No cardinalities (`200+`, `~20`).
- Anything matching the metric pattern raises `ValueError` at
  `make_*()` time — fail fast beats drift.

### Rule 2 — metrics go to `captions`

Every Mermaid-backed `make_*()` accepts a `captions: list[str]` kwarg.
The page-builder renders them as a small text strip directly under the
SVG, one cell per main node (parallel index). Caption strings are short
(≤ 40 chars), free-form, and may contain numbers.

```python
make_flow_diagram(
    steps=[
        {"title": "DISCOVER"},
        {"title": "CLASSIFY"},
        {"title": "BATCH-STAMP"},
        {"title": "CRAWL"},
    ],
    captions=[
        "all spaces · lastActiveTime",   # paired to step 0
        "client-side",                   # step 1
        "180+ inactive · 1 write",       # step 2
        "~20 active · paginate",         # step 3
    ],
)
```

### Rule 3 — `sub` is a qualifier, not a metric slot

`sub` (on `flow_diagram` steps and `hybrid_swimlane` stages) is only
for non-quantitative qualifiers: `"client-side"`, `"HITL"`, `"manual"`.
If the qualifier carries a number, drop it to `captions` and leave
`sub` out.

### Bad / Good

| Bad (raises ValueError)                                  | Good                                                        |
|----------------------------------------------------------|-------------------------------------------------------------|
| `{"title": "CRAWL ACTIVE", "sub": "~20 spaces · paginate"}` | `{"title": "CRAWL ACTIVE"}` + caption `"~20 spaces · paginate"` |
| `{"title": "BATCH-STAMP", "sub": "180+ inactive · 1 Drive write"}` | `{"title": "BATCH-STAMP"}` + caption `"180+ inactive · 1 write"` |
| `{"title": "MAIL SUMMARY", "sub": "every 2 hours · triage inbox"}` | `{"title": "MAIL SUMMARY", "sub": "triage inbox"}` + caption `"every 2 hours"` |
| `{"label": "CHAT CRAWL", "items": ["daily 08:00", "200+ spaces"]}` | `{"label": "CHAT CRAWL"}` + caption `"daily 08:00 · 200+ spaces"` |
| `{"title": "WEEKLY SUMMARY", "sub": "Monday 03:00 · 5-agent cluster"}` | `{"title": "WEEKLY SUMMARY"}` + caption `"Mon 03:00 · 5-agent cluster"` |

### Why this matters

A diagram is a visual narrative of *what happens at each step*, not a
data table. Mixing action names with metrics inside the same box
saturates the cognitive budget — viewers skim the noise and miss the
story. Strip the diagram, give the data its own dedicated row, and
both halves read clearly.

## Primitive reference

### `make_flow_diagram(steps, *, orientation='horizontal', title=None, subtitle=None, captions=None)` — Mermaid

Sequential 3-7 boxes connected by arrows. Renders as Mermaid
`flowchart LR` (horizontal) or `flowchart TB` (vertical). Node fill is
a blue gradient sampled across `len(steps)` (pale → navy).

```python
make_flow_diagram(
    steps=[
        {"title": "DATA"},
        {"title": "ETL"},
        {"title": "STORAGE"},
        {"title": "ORCHESTRATION"},
        {"title": "LLM"},
    ],
    captions=[
        "POS · IoT · EHR",
        "Lambda · Step Func",
        "Aurora · OpenSearch",
        "ECS / Fargate",
        "Bedrock · 4o · Gemini",
    ],
)
```

### `make_quadrant(cells, *, title=None, footer=None, x_axis=None, y_axis=None, captions=None)` — Mermaid

4 cells in a 2×2 grid. Renders as Mermaid `quadrantChart`. Cell order
**TL, TR, BL, BR** — the codegen reorders for Mermaid's Q1–Q4. Each
cell's `items` (up to 5) pack into the quadrant label via `<br/>`.
Cell corners stay rectangular (Mermaid `quadrantChart` doesn't expose
shape config — deferred).

```python
make_quadrant(
    cells=[
        {"title": "SAFETY",  "items": ["SOS", "Fall detect"]},
        {"title": "HEALTH",  "items": ["BLE vitals"]},
        {"title": "LIFE",    "items": ["Smart lighting"]},
        {"title": "EMOTION", "items": ["Family video"]},
    ],
    title="Smart Elder Care — 4-pillar platform",
)
```

### `make_footprint_map(cities, *, region='APAC', scale_label=None, title=None)` — Python

Continent outline (APAC only at v0.1.0) with pinned cities. One city
can be `highlight=True` for emphasis. **No Mermaid equivalent** — stays
native Python.

### `make_layered_stack(layers, *, side_annotations=None, kpi_band=None, title=None, captions=None)` — Mermaid

4-6 cards left-to-right. Each layer becomes a flowchart node packing
`label` + `items` via `<br/>`. `kpi_band` becomes a dotted-edge neutral
note attached to the last layer.

### `make_fanout_pipeline(input_label, models, fusion_label, outputs, *, title=None, subtitle=None, captions=None)` — Mermaid

Top input → N parallel models → fusion → branched outputs. 4-tier
vertical gradient (IN pale → models light → FUSE medium → outputs
navy). Parallel models live inside a `subgraph` cluster.

### `make_hybrid_swimlane(tiers, *, fleet_box=None, header=None, footer=None, title=None, captions=None)` — Mermaid

2+ horizontal lanes sharing one input column. Each tier becomes a
`subgraph` containing its stages. `fleet_box` becomes a shared input
node wired into the first stage of each lane. Stage colour is index-
driven (same gradient slot across all lanes — visual rhythm anchors
the eye horizontally).

**Open issue**: Mermaid has no native swimlane — subgraph workaround
may look denser than the v0.2.x SVG version. If visual quality is
unacceptable on a specific deck, retrieve the v0.2.x implementation
from git history.

### `make_data_path(stages, *, callout=None, title=None)` — Python

4-stage horizontal flow (typically device → mobile → cloud → provider)
with cloud-as-brain emphasis. **Stays native Python** — the brain
styling isn't expressible in Mermaid cleanly.

## VTI brand theming

Mermaid output gets a `%%{init:{theme:'base',themeVariables:{…}}}%%`
directive at the top of every code string, generated by
`theme_bridge.py` from `vti-slide-page-builder/tokens.css`. Diagram
colors stay in sync with the deck chrome — change tokens.css, both
chrome and diagrams update.

**Blue-mono palette (v0.4.0).** Theme variables only reference the VTI
blue family + neutrals. Per-node colour comes from `classDef stepN`
lines emitted alongside the diagram body — one class per step index,
sampling a light→dark gradient via `theme_bridge.gradient_classdefs(n)`:

| Step index (out of 4) | Fill token | Text token |
|---|---|---|
| 0 (lightest) | `--vti-paleblue` | `--vti-ink` |
| 1            | `--vti-sky`      | `--vti-white` |
| 2            | `--vti-blue`     | `--vti-white` |
| 3 (darkest)  | `--vti-navy`     | `--vti-white` |

Stroke is always `--vti-navy` for a unified outline; `rx/ry=14` gives
the round-edge look.

Key theme-variable mappings (used for fallbacks, edges, subgraph titles):

| Mermaid var | VTI token |
|---|---|
| `primaryColor` | `--vti-blue-deep` |
| `primaryTextColor` | `--vti-white` |
| `secondaryColor` | `--vti-blue-medium` |
| `tertiaryColor` (subgraph fill) | `--vti-light` |
| `background` | `--vti-bg` |
| `lineColor` | `--vti-ink-soft` |
| `textColor` | `--vti-ink` |
| `fontFamily` | `--vti-font-body` |

Auxiliary nodes (KPI bands, side annotations, fleet input boxes) use
a separate `meta` class — dashed border, white fill, ink-soft text —
so they don't compete with the gradient.

For `quadrantChart`, Mermaid uses a separate set of theme variables
(`quadrant1Fill`, `quadrantPointFill`, etc.) — see
`theme_bridge._quadrant_theme_variables()`. Quadrant cell fills are
already tinted from the blue family (`paleblue`, `light`, `bg`, `divider`).

## Discovery

```python
from diagram_builder import list_primitives, describe_primitive
list_primitives()
# ['flow_diagram', 'quadrant', 'footprint_map', 'layered_stack',
#  'fanout_pipeline', 'hybrid_swimlane', 'data_path']

describe_primitive('flow_diagram')
# {
#   "name":            "flow_diagram",
#   "backend":         "mermaid",
#   "hint_size":       "1180x280 (horizontal) / 1180x480 (vertical)",
#   "good_for":        ["sequence/process", "ETL pipelines", "AWS reference architecture"],
#   "content_profile": "action_label_only",  # v0.4.0 — no metrics in labels
#   "params":          {"steps": "...", "orientation": "...", "captions": "...", ...},
# }
```

The `content_profile` field tells authoring agents what kind of node
text the primitive accepts. `"action_label_only"` means *no metrics,
no times, no cardinalities inside node labels* — see the Content
discipline section above.

## Manual Figma escape hatch (out of automated path)

If a diagram needs hand-crafted visual richness that neither Mermaid
nor the native primitives offer (e.g. a custom illustration, a
non-standard branded layout), the agent can step outside the standard
flow:

1. Call `mcp__claude_ai_Figma__generate_diagram(...)` — requires the
   `/figma-generate-diagram` skill loaded first.
2. Export the Figma design to SVG via
   `mcp__claude_ai_Canva__export-design` or the Figma MCP equivalent.
3. Save SVG manually to `work/diagrams/<slide_id>.svg`.
4. Parse SVG viewBox for `natural_w` / `natural_h` as usual.
5. Build the `diagram_spec` by hand and pass to `make_slide_content_plan`.

This path is **not automated** — use it only when the user explicitly
asks for hand-crafted visuals.

## Version

0.5.0 — native-SVG branch restored alongside Mermaid. 5 dual-backend
primitives (`flow_diagram`, `quadrant`, `layered_stack`,
`fanout_pipeline`, `hybrid_swimlane`) accept `backend="svg"|"mermaid"`;
default is `svg`. Env override: `VTI_DIAGRAM_BACKEND`. SVG outputs land
at predictable canvases (1180×280/320 horizontal flow; 1180×480/520
others). v0.4.0 content discipline preserved.

0.4.0 — brand discipline pass. Blue-mono index-driven gradient,
round-edge nodes, steps-only content rule with `_assert_step_clean`
validator, parallel `captions` array passed through to the page-builder.
Per-element `accent` / `accent_alias` deprecated (accepted with warning).

0.3.0 — split-backend rendering: 5 Mermaid + 2 Python. Mermaid
themed via `theme_bridge.py` from `tokens.css`. Agent renders Mermaid
output via `mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram`.

0.2.0 — tighter canvases (CANVAS_H_WIDE 460→280, CANVAS_H_TALL 600→480).

0.1.0 — initial 7 native SVG primitives.
