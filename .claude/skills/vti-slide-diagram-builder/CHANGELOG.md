# vti-slide-diagram-builder — CHANGELOG

## v0.7.0 (2026-06-17) — `cycle` primitive (closed-loop / feedback diagram)

- **New `make_cycle(stages, *, title, subtitle, hub, ...)`** — a closed cycle of
  3–8 stages around a ring with a centre hub and clockwise direction chevrons.
  The right hero for CYCLIC processes (feedback loops, governance loops,
  lifecycles) where a linear `flow_diagram` misrepresents "it comes back
  around". Native SVG (token-driven colours, soft shadow), viewBox 1168×566
  with margins so no stage label clips. Registered in `_PRIMITIVES`,
  `_PRIMITIVE_META`, `PYTHON_BACKED`, and intents (`loop`, `feedback-loop`,
  `lifecycle`, `closed-loop`, `cycle`). Codifies the per-deck loop SVG that was
  previously hand-generated.

## v0.6.0 (2026-06-16) — M2: depth pass (gradients + soft shadow + icon set)

Fixes "diagram không đẹp": the native SVG primitives were flat (white box +
1-colour stroke, no depth). All five primitives flow through
`svg_primitives.svg_box` / `svg_box_filled` / `svg_open`, so the upgrade is
central and applies everywhere automatically:

- **Shared `<defs>`** injected by `svg_open`: a white-card sheen gradient
  (`vtiFillWhite`), per-accent vertical gradients (`vtiGrad-{navy,deep,blue,
  medium,sky,light,teal,amber}` — lifted top → accent bottom), a soft
  `feDropShadow` filter (`vtiSoftShadow`, tuned subtle to match the brand's
  soft-elevated-surface identity), and a compact line-icon symbol set.
- **`svg_box` / `svg_box_filled`** now fill with the matching gradient and
  carry the soft shadow by default (opt out via `shadow=False`/`gradient=
  False`; shadow auto-suppressed on translucent boxes). Outlined boxes read
  as elevated cards; filled boxes (input/fusion/footer bands) get depth.
- **Quadrant cells** (inline rect in `svg_render`) lifted with the same
  shadow so the 2×2 grid reads as panels, not flat colour fields.
- **Connectors** darkened `muted → ink-soft` for legible contrast on the
  pale canvas (arrows were washed out).
- **Icons**: `svg_icon(x, y, size, name)` + a 9-glyph set (gear, database,
  cloud, check, user, chart, loop, shield, doc) available as `<symbol>`s.
  Latent in M2 (no contract change) — the M3 archetype layer wires them
  into nodes.

All colours resolve via the token bridge (`accent`/`tint`) — no hex
literals in source (verify-time lint preserved). Canvas heights unchanged
to avoid rippling Phase-4 aspect/no-crop sizing (the "cramped" feel is
addressed by M3 giving diagrams a dominant focal cell with breathing room).

## v0.5.0 (2026-05-19) — Native-SVG branch restored alongside Mermaid

The v0.3.0 Mermaid migration produced diagrams with wildly inconsistent
output sizes — `flow_diagram` came back at aspect 14.17, `layered_stack`
at 8.62, etc. — because Mermaid-cli sizes the SVG to its laid-out
content with very loose external bounds. Phase 4's layout-designer
sized host cells against the `hint_w/hint_h` constants (1180×280 /
1180×480) and the resulting cells ended up either letterboxing the
diagram or cropping it, depending on the slide. The screenshots that
motivated this revert showed text shrunk to 60% of cell width or
overflowing past lane borders.

### What changed

- **New `svg_render.py` module** restores hand-authored native-SVG
  layouts for the 5 dual-backend primitives (`flow_diagram`, `quadrant`,
  `layered_stack`, `fanout_pipeline`, `hybrid_swimlane`). The renders
  are ports of the v0.1.0 implementations with one addition: a
  `captions` strip baked into the bottom of the SVG (height
  `CAPTION_STRIP_H = 40`) so the v0.4.0 content discipline still holds.
- **`diagram_builder.py` dispatch.** Every `make_*` for the 5
  dual-backend primitives now accepts a `backend` kwarg:
  - `backend="svg"` (default): returns `{primitive, backend, svg,
    natural_w, natural_h, captions}` — caller writes SVG to disk and
    reads `natural_w/_h` for cell sizing. No MCP step required.
  - `backend="mermaid"`: returns the v0.4.0 render task (`mermaid_code`
    + `hint_w/_h`). Identical to pre-v0.5.0 behaviour.
- **Env override.** `VTI_DIAGRAM_BACKEND={svg|mermaid}` flips the
  default; precedence is kwarg → env → `"svg"`.
- **`DUAL_BACKEND` frozenset** added to the module surface. The old
  `MERMAID_BACKED` set is kept as an alias for back-compat — same
  membership.
- **`backend_for(name, *, requested=...)`** now resolves the backend a
  caller will actually get, so consumers (creator's Phase 3) can
  branch on it before deciding whether to invoke the Mermaid MCP step.
- **Predictable canvases.** SVG outputs land at:
  - `flow_diagram` horizontal: 1180×280 (or 320 with captions)
  - `flow_diagram` vertical:   1180×480 (or 520 with captions)
  - `quadrant`:                1180×480 (or 520 with captions)
  - `layered_stack`:           1180×480 (or 520 with captions)
  - `fanout_pipeline`:         1180×480 (or 520 with captions)
  - `hybrid_swimlane`:         1180×480 (or 520 with captions)

  Compared to the Mermaid outputs of the same primitives at v0.4.0
  (aspect ratios 1.35 → 14.17 depending on content), the SVG renders
  return one of two aspect ratios (≈3.7 horizontal flow or ≈2.3 tall).
  Phase 4's layout-designer can plan cell sizes against these without
  surprise letterboxing.

### Migration

- **No breaking change** for callers that don't pass `backend=` — the
  new default is `svg`, which removes the MCP render step. Callers
  who want Mermaid output unchanged must pass `backend="mermaid"` or
  set `VTI_DIAGRAM_BACKEND=mermaid`.
- The v0.4.0 `_assert_step_clean` validator still runs at every
  `make_*` entry regardless of backend — content discipline is
  preserved.
- `MERMAID_BACKED` is still exported but is now equivalent to
  `DUAL_BACKEND`; new code should prefer `DUAL_BACKEND`.

### Why we kept Mermaid as an opt-in instead of removing it

Mermaid output is still useful for ad-hoc previews and for primitives
we may add in the future where hand-SVG would be too much work
(diagrams with auto-routed edges, large state machines, etc.). Keeping
the branch means we don't have to re-build the v0.4.0 theme bridge if
we want to lean on Mermaid again.

## v0.4.0 (2026-05-19) — Brand discipline pass

Three opinionated changes locked across all 5 Mermaid primitives so
diagrams stop drifting from VTI's visual identity. The migration of
v0.3.0 made Mermaid the rendering backend; v0.4.0 makes the **authoring
contract** match the brand.

### What changed

- **Blue-mono gradient.** Node fill is now index-driven: `step0`
  (lightest, `--vti-paleblue`) → `step{n-1}` (darkest, `--vti-navy`).
  No more per-element accent colours producing rainbow swimlanes. The
  per-call `accent_alias` (on `flow_diagram`) and per-element `accent`
  (on `layered_stack` layers, `fanout_pipeline` outputs, `quadrant`
  cells, `hybrid_swimlane` tiers) are deprecated — still accepted but
  logged as `DeprecationWarning` and ignored.
  - New helper `theme_bridge.gradient_classdefs(n)` emits `classDef
    stepN` lines sampling 7 ordered blue-family tokens
    (`paleblue`, `light`, `sky`, `blue-medium`, `blue`, `blue-deep`,
    `navy`) and flips text colour to `--vti-white` once the fill goes
    dark. Stroke is always `--vti-navy` for a unified outline.
  - `_flowchart_theme_variables()` cleaned: removed every teal / amber
    / orange reference; theme variables now only pull from the blue
    family + neutrals.
- **Round-edge nodes.** Every node renders with Mermaid's `(label)`
  round-rectangle shape (`rx/ry=14` via `classDef`). Subgraphs and
  `quadrantChart` cells stay rectangular — Mermaid doesn't expose
  shape config for them (deferred; no native fix available).
- **Steps-only content.** Node labels are pure action/state names —
  no metrics, no times, no cardinalities. A new
  `_assert_step_clean` validator runs at every `make_*()` entry and
  raises `ValueError` on the most common offenders (`"~20 spaces"`,
  `"180+"`, `"08:00"`, `"5%"`, `"2x"`, `"daily"`, etc.). Authoring
  agents fail fast instead of producing the noisy "step + metrics"
  boxes that motivated this pass.
- **Captions strip.** Every Mermaid `make_*()` accepts a new
  `captions: list[str] | None` kwarg. Captions are **not** rendered
  into the Mermaid source — they pass through in the return dict for
  the page-builder to render as a small text strip below the SVG
  (one cell per main node, parallel index).
- **`describe_primitive()` content_profile field.** Each of the 5
  Mermaid primitives reports `"content_profile": "action_label_only"`
  so authoring agents can introspect the contract.

### Return-shape addition

```python
{
    "primitive":     "flow_diagram",
    "backend":       "mermaid",
    "mermaid_code":  "...",
    "hint_w":        1180,
    "hint_h":        280,
    "captions":      ["...", "...", ...],   # NEW — may be []
}
```

`captions` is always present; empty list when caller didn't supply any.
Existing callers that don't read the field continue to work.

### Why

Output samples from v0.3.0 (`work/diagrams/_mermaid_src/s06–s08.mmd`)
showed two failure modes the rendering layer can't fix:

1. **Rainbow palette.** With each step letting the agent pick an
   `accent`, decks drifted to 4–6 different brand colours per slide.
2. **Metrics packed into labels.** Step boxes carrying `"180+ inactive
   · 1 Drive write"`, `"~20 spaces · paginate"`, `"daily 08:00"` —
   readers parse digits and miss the action narrative.

Both stemmed from a **gap in the authoring contract**: the skill
documented signatures but not content rules. v0.4.0 closes that gap.

### Breaking change for callers

Code that previously passed `accent_alias="teal"` or
`layers[i]["accent"]="amber"` will:

- Still run (no exception).
- Log a one-time `DeprecationWarning` per call site.
- Render with the gradient — the per-element accent is dropped.

Cleanup at leisure. The deprecation cycle has no defined end date;
the warnings stay until callers stop emitting them.

### Files touched

- `theme_bridge.py` — `_flowchart_theme_variables()` blue-only,
  `gradient_classdefs(n)` helper added.
- `mermaid_codegen.py` — all 5 codegens emit `(label)` not `[label]`,
  use `:::stepN` class refs, accept and pass-through `captions`.
- `diagram_builder.py` — `VERSION = "0.4.0"`, `_assert_step_clean`
  validator, `_mermaid_task` includes `captions`, `_PRIMITIVE_META`
  rewritten with `content_profile` field and caption-aware param docs.

### Cross-skill ripple

- `vti-slide-page-builder/composer_grid.py` — renders the new
  `captions` array as a `<div class="diagram-captions">` strip beneath
  the diagram SVG (see that skill's CHANGELOG).
- `vti-slide-creator/SKILL.md` Phase 3 (CONTENT-PLAN) — guidance updated
  to author `steps`/`layers`/etc. as action names and route metrics to
  the parallel `captions` array.
- `COORDINATED_BASELINE.md` — diagram-builder contract row reflects
  new return shape + content rule + version map.

---

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
