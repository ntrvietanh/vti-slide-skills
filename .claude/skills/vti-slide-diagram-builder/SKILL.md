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

## v0.3.0 — split-backend rendering

The 7 primitives now split across two rendering backends:

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
    "mermaid_code":  "%%{init:...}%%\nflowchart LR\n  S0[\"...\"] --> S1[...]\n  ...",
    "hint_w":        1180,
    "hint_h":        280,   # caller compares to actual viewBox after render
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

## Primitive reference

### `make_flow_diagram(steps, *, orientation='horizontal', accent_alias='deep', title=None, subtitle=None)` — Mermaid

Sequential 3-7 boxes connected by arrows. Renders as Mermaid
`flowchart LR` (horizontal) or `flowchart TB` (vertical).

```python
make_flow_diagram(
    steps=[
        {"title": "DATA",          "sub": "POS · IoT · EHR"},
        {"title": "ETL",           "sub": "Lambda · Step Func"},
        {"title": "STORAGE",       "sub": "Aurora · OpenSearch"},
        {"title": "ORCHESTRATION", "sub": "ECS / Fargate brain"},
        {"title": "LLM",           "sub": "Bedrock · 4o · Gemini"},
    ],
    orientation='horizontal',
    accent_alias='deep',
)
```

### `make_quadrant(cells, *, title=None, footer=None, x_axis=None, y_axis=None)` — Mermaid

4 cells in a 2×2 grid. Renders as Mermaid `quadrantChart`. Cell order
**TL, TR, BL, BR** — the codegen reorders for Mermaid's Q1–Q4. Each
cell's `items` (up to 5) pack into the quadrant label via `<br/>`.

```python
make_quadrant(
    cells=[
        {"title": "SAFETY",  "accent": "red",    "items": ["SOS", "Fall detect"]},
        {"title": "HEALTH",  "accent": "teal",   "items": ["BLE vitals"]},
        {"title": "LIFE",    "accent": "amber",  "items": ["Smart lighting"]},
        {"title": "EMOTION", "accent": "purple", "items": ["Family video"]},
    ],
    title="Smart Elder Care — 4-pillar platform",
)
```

### `make_footprint_map(cities, *, region='APAC', scale_label=None, title=None)` — Python

Continent outline (APAC only at v0.1.0) with pinned cities. One city
can be `highlight=True` for emphasis. **No Mermaid equivalent** — stays
native Python.

### `make_layered_stack(layers, *, side_annotations=None, kpi_band=None, title=None)` — Mermaid

4-6 cards left-to-right. Each layer becomes a flowchart node packing
`label` + `items` via `<br/>`. `kpi_band` becomes a dotted-edge note
attached to the last layer.

### `make_fanout_pipeline(input_label, models, fusion_label, outputs, *, title=None, subtitle=None)` — Mermaid

Top input → N parallel models → fusion → branched outputs. Parallel
models live inside a `subgraph` cluster.

### `make_hybrid_swimlane(tiers, *, fleet_box=None, header=None, footer=None, title=None)` — Mermaid

2+ horizontal lanes sharing one input column. Each tier becomes a
`subgraph` containing its stages. `fleet_box` becomes a shared input
node wired into the first stage of each lane.

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

Key token mappings:

| Mermaid var | VTI token |
|---|---|
| `primaryColor` | `--vti-blue-deep` |
| `primaryTextColor` | `--vti-white` |
| `secondaryColor` | `--vti-teal` |
| `tertiaryColor` (subgraph fill) | `--vti-light` |
| `background` | `--vti-bg` |
| `lineColor` | `--vti-ink-soft` |
| `textColor` | `--vti-ink` |
| `fontFamily` | `--vti-font-body` |

For `quadrantChart`, Mermaid uses a separate set of theme variables
(`quadrant1Fill`, `quadrantPointFill`, etc.) — see
`theme_bridge._quadrant_theme_variables()`.

## Discovery

```python
from diagram_builder import list_primitives, describe_primitive
list_primitives()
# ['flow_diagram', 'quadrant', 'footprint_map', 'layered_stack',
#  'fanout_pipeline', 'hybrid_swimlane', 'data_path']

describe_primitive('flow_diagram')
# {
#   "name":      "flow_diagram",
#   "backend":   "mermaid",
#   "hint_size": "1180x280 (horizontal) / 1180x480 (vertical)",
#   "good_for":  ["sequence/process", "ETL pipelines", "AWS reference architecture"],
#   "params":    {"steps": "...", "orientation": "...", "accent_alias": "...", ...},
# }
```

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

0.3.0 — split-backend rendering: 5 Mermaid + 2 Python. Mermaid
themed via `theme_bridge.py` from `tokens.css`. Agent renders Mermaid
output via `mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram`.

0.2.0 — tighter canvases (CANVAS_H_WIDE 460→280, CANVAS_H_TALL 600→480).

0.1.0 — initial 7 native SVG primitives.
