# vti-slide-diagram-builder

VTI-Standard SVG diagram primitives for slide decks. Pairs with
`vti-slide-creator` (orchestrator) and consumes brand tokens from
`vti-slide-page-builder/tokens.css`.

## Why this skill exists

Before this skill, every deck rendered diagrams ad-hoc — colors drifted,
arrow heads varied, line weights shifted slide-to-slide. The skill
standardises 7 diagram primitives so all VTI decks share one visual
language.

Each primitive returns an SVG string + its natural dimensions, so the
creator's Phase 4 layout-design step can choose cell aspect ratio that
**guarantees the diagram is never cropped**.

## When to use

Invoke this skill **at Phase 3 (CONTENT-PLAN)** of `vti-slide-creator`
≥ 4.0 — when a slide's `image_decision.strategy` is `"synthesize"` and
the diagram intent matches one of the 7 primitives. The creator picks
the primitive, fills the parameters from its source-research notes, and
gets back `(svg_string, natural_w, natural_h)`. SVG is written to disk
at `work/diagrams/<slide_id>.svg`; dimensions feed into Phase 4.

## Public API surface

```python
from diagram_builder import (
    make_flow_diagram,        # 3-7 boxes + chevron arrows (horizontal or vertical)
    make_quadrant,            # exactly 4 cells in 2x2 grid + optional bottom band
    make_footprint_map,       # APAC-only continent outline + N pins + legend
    make_layered_stack,       # left-to-right horizontal stack of 4-6 vertical cards
    make_fanout_pipeline,     # top input → N parallel models → fusion → branch outputs
    make_hybrid_swimlane,     # 2+ horizontal lanes sharing one input column
    make_data_path,           # 4-stage horizontal flow with cloud-as-brain pattern
    list_primitives,          # discovery: list of registered primitive names
    describe_primitive,       # metadata for one primitive (params + sample)
    primitive_for_intent,     # dispatcher: 'aws-reference' → 'flow_diagram'
)
```

### Common return shape

Every primitive returns a dict:

```python
{
    "svg":        str,    # complete <svg> element with inline styles
    "natural_w":  int,    # viewBox width  (≥ 800)
    "natural_h":  int,    # viewBox height (≥ 400)
    "primitive":  str,    # primitive name (e.g. 'flow_diagram')
}
```

`natural_w / natural_h` is the natural aspect ratio the consumer should
honour to avoid cropping. The Phase 4 layout-designer reads these and
sets the `image-tile` cell `aspect_ratio` prop accordingly.

## Primitive reference

### `make_flow_diagram(steps, *, orientation='horizontal', accent='deep')`

Sequential 3-7 boxes connected by chevron arrows. Each step has a
title (≤ 30 chars), optional sub-text (≤ 60 chars), optional number.

```python
make_flow_diagram(
    steps=[
        {"title": "DATA", "sub": "POS · IoT · EHR"},
        {"title": "ETL", "sub": "Lambda · Step Func"},
        {"title": "STORAGE", "sub": "Aurora · OpenSearch"},
        {"title": "ORCHESTRATION", "sub": "ECS / Fargate brain"},
        {"title": "LLM", "sub": "Bedrock Claude · 4o · Gemini"},
    ],
    orientation='horizontal',  # or 'vertical'
    accent='deep',             # 'deep' | 'navy' | 'sky' | 'teal'
)
```

### `make_quadrant(cells, *, title=None, footer=None)`

Exactly 4 cells in a 2x2 grid. Each cell has accent + title + 3-6 items.

```python
make_quadrant(
    cells=[
        {"title": "SAFETY",  "accent": "red",     "items": ["SOS", "Fall detect", ...]},
        {"title": "HEALTH",  "accent": "teal",    "items": ["BLE vitals", ...]},
        {"title": "LIFE",    "accent": "amber",   "items": ["Smart lighting", ...]},
        {"title": "EMOTION", "accent": "purple",  "items": ["Family video", ...]},
    ],
    title="Smart Elder Care — 4-pillar platform",
    footer="Multi-protocol gateway · >128 nodes · <120ms latency",
)
```

### `make_footprint_map(cities, *, highlight=None, region='APAC', scale_label=None)`

Continent outline (APAC only at v0.1.0) with pinned cities. One city
can be `highlight=True` for emphasis.

```python
make_footprint_map(
    cities=[
        {"name": "Hanoi",      "x": 280, "y": 245},
        {"name": "Tokyo",      "x": 770, "y": 195},
        {"name": "Singapore",  "x": 365, "y": 460, "highlight": True},
    ],
    region='APAC',
    scale_label="4 countries · 9 offices · 1,800+ staff",
)
```

### `make_layered_stack(layers, *, side_annotations=None, kpi_band=None)`

4-6 vertical cards arranged left-to-right with arrows between. Each
card has a label and 2-8 inline items. Optional right-side annotations
and bottom KPI band.

```python
make_layered_stack(
    layers=[
        {"label": "PHYSICAL", "items": ["Wi-Fi", "BLE", "Zigbee", "LoRa"], "accent": "ink"},
        {"label": "LINK",     "items": ["Multi-proto stack"],              "accent": "blue"},
        {"label": "CONVERGENCE", "items": ["Rules engine", "Edge compute"], "accent": "deep"},
        {"label": "APP",      "items": ["IoT PaaS"],                       "accent": "teal"},
        {"label": "CLOUD",    "items": ["App PaaS + SaaS"],                "accent": "navy"},
    ],
    kpi_band="Quantified specs · >128 nodes · <120ms latency",
)
```

### `make_fanout_pipeline(input_label, models, fusion_label, outputs)`

Top input box → N parallel model boxes (3-7) → fusion box at bottom →
2-3 branch outputs.

```python
make_fanout_pipeline(
    input_label="Ward camera (RTSP)",
    models=[
        {"name": "RetinaFace", "desc": "detect + align"},
        {"name": "ArcFace",    "desc": "patient ID"},
        {"name": "OpenPose",   "desc": "body pose"},
        {"name": "YOLOv7",     "desc": "cup / pill"},
        {"name": "Dlib",       "desc": "fine keypoints"},
    ],
    fusion_label="Fusion + verification rules",
    outputs=[
        {"label": "OK → log event",      "accent": "teal"},
        {"label": "Mismatch → alert",    "accent": "red"},
    ],
)
```

### `make_hybrid_swimlane(tiers, *, fleet_box=None, header=None, footer=None)`

2+ horizontal lanes sharing one input column on the left. Each lane has
its own accent and 3-stage flow inside.

```python
make_hybrid_swimlane(
    tiers=[
        {
            "label":  "EDGE TIER — REAL-TIME SECURITY",
            "accent": "red",
            "stages": [
                {"title": "Edge gateway",  "sub": "ARM · Jetson"},
                {"title": "Event filter",  "sub": "intrusion · fall · loiter"},
                {"title": "Security dash", "sub": "+ alerts", "filled": True},
            ],
        },
        {
            "label":  "SERVER TIER — RETAIL ANALYTICS",
            "accent": "blue",
            "stages": [
                {"title": "AI server",  "sub": "A100 40GB"},
                {"title": "Re-detect",  "sub": "RT-DETR · ByteTrack"},
                {"title": "Retail dash","sub": "+ POS / ERP", "filled": True},
            ],
        },
    ],
    fleet_box={"label": "CCTV / NVR", "sub": "Existing fleet"},
    header="EXISTING INFRASTRUCTURE — SKT 1.6M AI CCTVs",
)
```

### `make_data_path(stages, *, callout=None)`

4-stage horizontal flow (typically: device → mobile → cloud → provider).
The middle stage (cloud) gets emphasized as the "brain" of the system.

```python
make_data_path(
    stages=[
        {"label": "PATIENT-SIDE",   "accent": "teal",   "items": ["BLE vitals", ...]},
        {"label": "MOBILE",         "accent": "blue",   "items": ["Patient app"]},
        {"label": "CLOUD (AWS)",    "accent": "deep",   "items": ["Lambda+Aurora", "Triage chatbot"], "brain": True},
        {"label": "PROVIDER-SIDE",  "accent": "magenta","items": ["Caregiver dashboard", ...]},
    ],
    callout={
        "title": "Abnormal-reading flow",
        "body":  "Cloud rules engine matches incoming vitals against thresholds...",
    },
)
```

## Standardisation rules

- **Canonical viewBox**: 1180×600 (16:9 at 1280×720 deck size). Every
  primitive's SVG conforms; `natural_w` and `natural_h` are reported
  exactly (some primitives use 1180×460 for tighter horizontal flows —
  this is reported back so the layout-designer chooses correct cell
  aspect-ratio).
- **Tokens**: every colour comes from `tokens_bridge.TOKENS` (parsed
  from `vti-slide-page-builder/tokens.css` at module load). No hex
  literals in primitives.
- **Typography**: `system-ui, -apple-system, "Segoe UI", Roboto,
  sans-serif` — matches deck chrome.
- **Strokes**: `STROKE_NORMAL = 2`, `STROKE_THICK = 3`,
  `ARROW_HEAD_SIZE = 6`. Arrow heads are filled triangles, never lines.
- **Accessibility**: every `<svg>` has `role="img"` + `<title>` + `<desc>`
  derived from caller params.

## Discovery

```python
from diagram_builder import list_primitives, describe_primitive
list_primitives()
# ['flow_diagram', 'quadrant', 'footprint_map', 'layered_stack',
#  'fanout_pipeline', 'hybrid_swimlane', 'data_path']

describe_primitive('flow_diagram')
# {
#   "name":         "flow_diagram",
#   "natural_size": "1180x460",
#   "good_for":     ["sequence/process", "AWS reference architecture", "ETL pipelines"],
#   "params":       {"steps": "list[{title, sub?, number?}] (3-7)",
#                    "orientation": "'horizontal'|'vertical'",
#                    "accent": "'deep'|'navy'|'sky'|'teal'"},
# }
```

`primitive_for_intent('aws-reference')` returns `'flow_diagram'` — used
by the creator's Phase 3 to map slide topics to primitives.

## Version

0.1.0 — initial primitives drawn from `scripts/diagrams.py` of the
2026-05-10 deck. All 10 diagrams of that deck are expressible via these
7 primitives.
