# vti-slide-diagram-builder — CHANGELOG

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
