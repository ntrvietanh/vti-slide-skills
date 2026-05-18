# vti-slide-diagram-builder — CHANGELOG

## v0.3.0 (2026-05-18) — Split-backend rendering (Mermaid + Python)

Five primitives migrated from native Python SVG to **Mermaid Chart MCP**
rendering: `flow_diagram`, `quadrant`, `layered_stack`,
`fanout_pipeline`, `hybrid_swimlane`. Two stay native: `footprint_map`
(no Mermaid geo-map equivalent) and `data_path` (hand-crafted
brain-emphasis styling).

### What changed

- **New module `mermaid_codegen.py`** — one function per Mermaid-backed
  primitive returning a Mermaid source string. Each codegen prepends a
  per-diagram `%%{init: ...}%%` directive built from the VTI brand
  token palette (see `theme_bridge.py`).
- **New module `theme_bridge.py`** — generates `init` directives with
  `themeVariables` derived from `vti-slide-page-builder/tokens.css`.
  Two flavours: `init_directive()` for `flowchart` and
  `init_directive_quadrant()` for `quadrantChart`.
- **`diagram_builder.py` return-shape** — the 5 Mermaid-backed
  `make_<primitive>` functions now return a **render task**:
  ```python
  {"primitive": ..., "backend": "mermaid",
   "mermaid_code": ..., "hint_w": ..., "hint_h": ...}
  ```
  The 2 Python-backed functions return the same `svg` / `natural_w` /
  `natural_h` shape as v0.2.x, but now with an explicit
  `"backend": "python"` field.
- **New public constants** — `MERMAID_BACKED`, `PYTHON_BACKED` (frozensets),
  plus `backend_for(name)` helper.
- **Bumped `VERSION = "0.3.0"`**.

### Agent-side render workflow

The skill no longer guarantees an SVG-on-disk after a single function
call. For Mermaid-backed primitives the **agent** is responsible for:

1. Calling `make_<primitive>(...)`
2. Invoking `mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram`
   with the returned `mermaid_code`
3. Saving the rendered SVG to `work/diagrams/<slide_id>.svg`
4. Reading the viewBox to recover `natural_w` / `natural_h`
5. Constructing the final `diagram_spec` for `make_slide_content_plan`

Python-backed primitives skip steps 2–4 — the dict already has the SVG
and dimensions.

### Why

The v0.2.x Python primitives produce SVGs that look stiff next to
Mermaid's optimized auto-layout (especially for variable node count).
Mermaid Chart MCP is purpose-built for diagrams and stays in sync with
upstream Mermaid improvements without us writing more SVG code.
Footprint maps and the brain-emphasis data path have no clean Mermaid
equivalent, so they stay native.

### Breaking change for callers

Callers that previously did:

```python
result = make_flow_diagram(...)
Path("work/diagrams/foo.svg").write_text(result["svg"])
spec = {..., "natural_w": result["natural_w"], "natural_h": result["natural_h"]}
```

now need the dual-branch flow described in `SKILL.md` § *Agent
workflow*. The change is intentional — there is no MCP-callable Python
client, so this responsibility has to live in the agent.

### Open items (tune-after)

- `hybrid_swimlane` Mermaid subgraph layout may look denser than the
  v0.2.x SVG. If unacceptable on a specific deck, fall back to the
  git-history v0.2.x implementation.
- Theme variables for dark-text-on-light-cards contrast may need
  per-deck adjustment.

## v0.2.0 (2026-05-10) — Tighter canvases (remove vertical whitespace)

`CANVAS_H_WIDE: 460 → 280` and `CANVAS_H_TALL: 600 → 480`. The v0.1 defaults padded ~150-200px of vertical whitespace below content in every flow / quadrant / layered-stack output (boxes 130px tall centered in a 460px canvas left ~165px gap top + ~165px gap bottom). Visible in deck render as "diagrams stretched long with whitespace underneath".

New defaults size close to the minimum each primitive actually needs (~210-230 for a 4-step horizontal flow with title; ~430 for a quadrant 2x2 with 5-item cells). Aspect of `flow_diagram` now ~4.21 (1180/280) instead of 2.57 — flatter banner that tucks naturally into the new `vti-slide-creator` 4.5 `image-banner-top` slot without forcing aside fallback.

No API change; primitive signatures unchanged.

## v0.1.0 (2026-05-10) — Initial primitives

First release. Extracted 7 diagram primitives from the ad-hoc
`scripts/diagrams.py` of the 2026-05-10 VTI Singapore deck. The 10
diagrams of that deck are now expressible via these 7 primitives.

### What's new

- **`make_flow_diagram(steps, orientation, accent)`** — sequential 3-7
  boxes connected by chevron arrows. Replaces ad-hoc renderers for
  `aws_reference_arch` and `serverless_procurement`.
- **`make_quadrant(cells, title, footer)`** — exactly 4 cells in 2×2.
  Replaces `elder_care_quadrant`.
- **`make_footprint_map(cities, highlight, region, scale_label)`** —
  APAC continent outline + N pins. Replaces `apac_footprint`.
- **`make_layered_stack(layers, side_annotations, kpi_band)`** —
  left-to-right horizontal stack of 4-6 vertical cards. Replaces
  `fhir_healthlake` and `iot_gateway`.
- **`make_fanout_pipeline(input_label, models, fusion_label, outputs)`**
  — top input → N parallel models → fusion → branch outputs. Replaces
  `medication_pipeline`.
- **`make_hybrid_swimlane(tiers, fleet_box, header, footer)`** — 2+
  horizontal lanes sharing one input column. Replaces
  `hybrid_camera_arch` and `skt_camera_arch`.
- **`make_data_path(stages, callout)`** — 4-stage horizontal flow with
  cloud-as-brain emphasis. Replaces `telehealth_rpm`.

### Standardisation

- **Single source of truth for colour tokens**: `tokens_bridge.py`
  parses `vti-slide-page-builder/tokens.css` at module load. No hex
  literals in primitive code; running
  `grep -E '#[0-9a-fA-F]{3,6}' diagram_builder.py svg_primitives.py`
  must return zero matches.
- **Canonical viewBox**: 1180×460 for horizontal flows / 1180×600 for
  taller diagrams (quadrants, fanouts, layered stacks). Each primitive
  reports its `natural_w` / `natural_h` so the caller can set the
  hosting `image-tile` cell aspect-ratio to avoid cropping.
- **Stroke + arrow constants**: `STROKE_NORMAL = 2`, `STROKE_THICK = 3`,
  `ARROW_HEAD_SIZE = 6`. Arrow heads are filled triangles only.
- **Accessibility**: every emitted `<svg>` carries `role="img"` plus
  `<title>` + `<desc>` children populated from caller intent.

### Integration story (creator-v3 ≥ 4.0 — Phase 3)

The creator's `content_drafter.make_diagram_spec(slide_id, primitive,
args)` calls into this skill, writes the returned SVG to
`work/diagrams/<slide_id>.svg`, and stores
`{primitive, args, svg_path, natural_w, natural_h}` on the
`SlideContentPlan`. Phase 4 (layout-design) reads `natural_w` /
`natural_h` to size the hosting cell so the diagram is never cropped.

### Known limits

- APAC region only for `make_footprint_map`. Other regions deferred to
  v0.2.x.
- Single VTI brand palette — per-tenant brand variants out of scope.
- No PNG fallback — SVG is the canonical format. If a downstream tool
  cannot render SVG, that's a downstream problem (decks render in
  browsers, where SVG is universally supported).
