"""Native SVG rendering for the 5 Mermaid-backed primitives.

Restores the v0.1.0 hand-authored SVG layouts (predictable canvas, dense
content, tight typography) while keeping the v0.4.0 contract: action-only
node labels with quantitative info supplied via a parallel ``captions``
array that gets rendered as a small text strip baked into the SVG.

Public surface mirrors ``mermaid_codegen`` (one function per primitive)
so ``diagram_builder.make_*`` can dispatch based on the ``backend`` kwarg.

Each function returns the same dict shape the Python-backed primitives
have always produced::

    {
      "primitive":  str,
      "backend":    "svg",
      "svg":        str,    # complete <svg> element
      "natural_w":  int,
      "natural_h":  int,
      "captions":   list[str],  # echoed back so consumers see the same shape
    }

Caller can either consume ``svg`` directly (write to disk) or read
``natural_w / natural_h`` to size the host cell. No MCP render step
needed — this is end-to-end Python.
"""
from __future__ import annotations

from typing import Any

from svg_primitives import (
    CANVAS_W, CANVAS_H_WIDE, CANVAS_H_TALL,
    STROKE_NORMAL,
    svg_open, svg_close,
    svg_title_label, svg_subtitle_label, svg_text,
    svg_box, svg_box_filled,
    svg_arrow, svg_connector_horizontal, svg_connector_vertical,
    even_split_x,
)
from tokens_bridge import accent, tint

# Height of the bottom caption strip (one short line per main element).
CAPTION_STRIP_H = 40


def _result(svg: str, w: int, h: int, name: str,
            captions: list[str] | None) -> dict[str, Any]:
    return {
        "primitive":  name,
        "backend":    "svg",
        "svg":        svg,
        "natural_w":  w,
        "natural_h":  h,
        "captions":   list(captions or []),
    }


def _captions_under_positions(positions: list[tuple[int, int]],
                              captions: list[str] | None,
                              y: int,
                              *,
                              max_chars: int = 36) -> str:
    """Center one caption under each (x, w) slot in ``positions``.

    Long captions wrap to a second line at the next space character past
    ``max_chars`` so they stay inside their slot. Returns SVG fragment.
    """
    if not captions:
        return ""
    out = ""
    for i, (px, pw) in enumerate(positions):
        if i >= len(captions):
            break
        cap = (captions[i] or "").strip()
        if not cap:
            continue
        line1, line2 = _soft_wrap(cap, max_chars)
        cx = px + pw // 2
        out += svg_text(cx, y + 14, line1, accent_alias="muted",
                        size=10, weight=400, anchor="middle")
        if line2:
            out += svg_text(cx, y + 28, line2, accent_alias="muted",
                            size=10, weight=400, anchor="middle")
    return out


def _soft_wrap(text: str, max_chars: int) -> tuple[str, str]:
    """Split ``text`` into two lines at the last space ≤ max_chars.

    If text fits, returns (text, ""). If no space exists, returns
    (text, "") and lets the renderer overflow rather than mid-word break.
    """
    if len(text) <= max_chars:
        return text, ""
    cut = text.rfind(" ", 0, max_chars + 1)
    if cut <= 0:
        return text, ""
    return text[:cut], text[cut + 1:]


# ===========================================================================
# 1. flow_diagram — horizontal sequence of 3-7 boxes + chevron arrows
# ===========================================================================
def flow_diagram(
    steps: list[dict],
    *,
    orientation: str = "horizontal",
    accent_alias: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Sequential flow of 3-7 boxes connected by arrows.

    Renders v0.1.0 layout (predictable rectangles with proper letterspacing).
    ``accent_alias`` (legacy) defaults to ``"deep"`` if not provided; the
    rendering is single-accent — no per-step gradient — matching the
    pre-Mermaid look.
    """
    if not 3 <= len(steps) <= 7:
        raise ValueError(f"flow_diagram needs 3-7 steps, got {len(steps)}")
    if orientation not in ("horizontal", "vertical"):
        raise ValueError("orientation must be horizontal|vertical")
    accent_alias = accent_alias or "deep"

    width = CANVAS_W
    has_captions = bool(captions)
    base_h = CANVAS_H_WIDE if orientation == "horizontal" else CANVAS_H_TALL
    height = base_h + (CAPTION_STRIP_H if has_captions else 0)

    out = svg_open(width, height,
                   title=title or "Flow diagram",
                   desc="Sequential flow of process steps",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)
    if subtitle:
        out += svg_subtitle_label(40, 75, subtitle)

    if orientation == "horizontal":
        n = len(steps)
        positions = even_split_x(width, n, padding=30, gap=22)
        box_h = 130
        box_top = (base_h - box_h) // 2 + (15 if title else 0)
        for i, ((bx, bw), step) in enumerate(zip(positions, steps)):
            out += svg_box(bx, box_top, bw, box_h,
                           stroke_alias=accent_alias,
                           stroke_width=STROKE_NORMAL)
            label = step.get("title", "")
            sub = step.get("sub", "")
            num = step.get("number", "")
            if num:
                out += svg_text(bx + 14, box_top + 22, num,
                                accent_alias=accent_alias, size=11,
                                weight=700, anchor="start")
            out += svg_text(bx + bw // 2, box_top + box_h // 2 - 6,
                            label, accent_alias=accent_alias, size=13,
                            weight=700, anchor="middle")
            if sub:
                out += svg_text(bx + bw // 2, box_top + box_h // 2 + 18,
                                sub, accent_alias="ink", size=11,
                                anchor="middle")
            if i < n - 1:
                next_bx, _ = positions[i + 1]
                ay = box_top + box_h // 2
                out += svg_connector_horizontal(bx + bw + 2, ay, next_bx - 4)

        if has_captions:
            out += _captions_under_positions(positions, captions, base_h)
    else:
        n = len(steps)
        box_w = 380
        box_h = 70
        gap = 14
        total_h = n * box_h + (n - 1) * gap
        start_y = max(80, (base_h - total_h) // 2 + (15 if title else 0))
        cx = width // 2 - box_w // 2
        for i, step in enumerate(steps):
            by = start_y + i * (box_h + gap)
            out += svg_box(cx, by, box_w, box_h,
                           stroke_alias=accent_alias,
                           stroke_width=STROKE_NORMAL)
            out += svg_text(cx + 16, by + 30, step.get("title", ""),
                            accent_alias=accent_alias, size=13, weight=700)
            sub = step.get("sub", "")
            if sub:
                out += svg_text(cx + 16, by + 52, sub,
                                accent_alias="ink", size=11)
            if i < n - 1:
                out += svg_connector_vertical(cx + box_w // 2, by + box_h + 1,
                                              by + box_h + gap - 2)
        # vertical orientation: render captions as a right-side column
        if has_captions:
            cap_x = cx + box_w + 24
            for i, cap in enumerate(captions[:n]):
                if not cap:
                    continue
                by = start_y + i * (box_h + gap) + box_h // 2 + 4
                out += svg_text(cap_x, by, cap, accent_alias="muted",
                                size=10, weight=400, anchor="start")

    out += svg_close()
    return _result(out, width, height, "flow_diagram", captions)


# ===========================================================================
# 2. quadrant — exactly 4 cells in a 2x2 grid + optional bottom band
# ===========================================================================
def quadrant(
    cells: list[dict],
    *,
    title: str | None = None,
    footer: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Exactly 4 cells in a 2x2 grid. ``captions`` (parallel to cells in
    TL/TR/BL/BR order) renders as a small strip below the grid."""
    if len(cells) != 4:
        raise ValueError(f"quadrant requires exactly 4 cells, got {len(cells)}")

    width = CANVAS_W
    has_captions = bool(captions)
    base_h = CANVAS_H_TALL
    height = base_h + (CAPTION_STRIP_H if has_captions else 0)
    out = svg_open(width, height,
                   title=title or "4-quadrant diagram",
                   desc="Four-pillar / four-quadrant grid",
                   bg="pale")

    top_pad = 40 if title else 30
    if title:
        out += svg_title_label(40, top_pad + 10, title)
        top_pad += 30

    band_h = 50 if footer else 0
    band_pad = 14 if footer else 0
    grid_top = top_pad + 10
    grid_bottom = base_h - band_h - band_pad - 20
    grid_h = grid_bottom - grid_top
    grid_left = 40
    grid_right = width - 40
    grid_w = grid_right - grid_left
    cell_gap = 12
    cell_w = (grid_w - cell_gap) // 2
    cell_h = (grid_h - cell_gap) // 2

    positions = [
        (grid_left,                    grid_top),
        (grid_left + cell_w + cell_gap, grid_top),
        (grid_left,                    grid_top + cell_h + cell_gap),
        (grid_left + cell_w + cell_gap, grid_top + cell_h + cell_gap),
    ]
    for (cx, cy), cell in zip(positions, cells):
        accent_alias = cell.get("accent", "deep")
        bg_color = tint(accent_alias, ratio=0.92)
        # v4.0/M2 — lift each tinted cell with the shared soft shadow so the
        # 2×2 grid reads as elevated panels, not flat colour fields.
        out += (
            f'  <rect x="{cx}" y="{cy}" width="{cell_w}" height="{cell_h}" '
            f'rx="10" fill="{bg_color}" filter="url(#vtiSoftShadow)"/>\n'
        )
        title_text = cell.get("title", "")
        out += svg_text(cx + 24, cy + 36, title_text,
                        accent_alias=accent_alias, size=14,
                        weight=700, anchor="start")
        out += (
            f'  <line x1="{cx + 24}" y1="{cy + 48}" '
            f'x2="{cx + 84}" y2="{cy + 48}" '
            f'stroke="{accent(accent_alias)}" stroke-width="2"/>\n'
        )
        items = cell.get("items", [])[:8]
        for i, item in enumerate(items):
            out += svg_text(cx + 30, cy + 80 + i * 20,
                            f"• {item}", accent_alias="ink", size=11.5)

    if footer:
        fy = base_h - band_h - 20
        out += svg_box_filled(40, fy, width - 80, band_h, fill_alias="navy")
        out += svg_text(60, fy + band_h // 2 + 4, footer,
                        accent_alias="white", size=11, anchor="start")

    if has_captions:
        # Captions strip is one wide row under the grid, dot-separated.
        cap_y = base_h + 8
        joined = "  ·  ".join(c for c in captions if c)
        if joined:
            out += svg_text(width // 2, cap_y + 12, joined,
                            accent_alias="muted", size=10, weight=400,
                            anchor="middle")

    out += svg_close()
    return _result(out, width, height, "quadrant", captions)


# ===========================================================================
# 3. layered_stack — left-to-right horizontal stack of 4-6 vertical cards
# ===========================================================================
def layered_stack(
    layers: list[dict],
    *,
    side_annotations: list[dict] | None = None,
    kpi_band: str | None = None,
    title: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Left-to-right horizontal stack of 4-6 vertical cards.

    ``captions`` is parallel to layers; rendered as a strip below the cards.
    """
    if not 4 <= len(layers) <= 6:
        raise ValueError(f"layered_stack needs 4-6 layers, got {len(layers)}")

    width = CANVAS_W
    has_captions = bool(captions)
    base_h = CANVAS_H_TALL
    height = base_h + (CAPTION_STRIP_H if has_captions else 0)

    out = svg_open(width, height,
                   title=title or "Layered architecture stack",
                   desc="Layered architecture with arrows between layers",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)

    band_h = 55 if kpi_band else 0
    band_pad = 20 if kpi_band else 0
    layer_top = 90
    layer_bottom = base_h - band_h - band_pad - 30
    layer_h = layer_bottom - layer_top

    n = len(layers)
    side_w = 180 if side_annotations else 0
    avail_w = width - 80 - side_w
    box_gap = 26
    box_w = (avail_w - (n - 1) * box_gap) // n

    positions: list[tuple[int, int]] = []
    for i, layer in enumerate(layers):
        bx = 40 + i * (box_w + box_gap)
        positions.append((bx, box_w))
        accent_alias = layer.get("accent", "deep")
        filled = layer.get("filled", False)
        if filled:
            out += svg_box_filled(bx, layer_top, box_w, layer_h,
                                  fill_alias=accent_alias)
            label_color = "white"
            item_color = "light"
        else:
            out += svg_box(bx, layer_top, box_w, layer_h,
                           fill_alias="white",
                           stroke_alias=accent_alias,
                           stroke_width=STROKE_NORMAL)
            label_color = accent_alias
            item_color = "ink"

        out += svg_text(bx + box_w // 2, layer_top + 32,
                        layer.get("label", ""),
                        accent_alias=label_color, size=13, weight=700,
                        anchor="middle")
        items = layer.get("items", [])[:10]
        for j, item in enumerate(items):
            out += svg_text(bx + box_w // 2, layer_top + 70 + j * 20,
                            item, accent_alias=item_color, size=11,
                            anchor="middle")

        if i < n - 1:
            ay = layer_top + layer_h // 2
            out += svg_connector_horizontal(
                bx + box_w + 2, ay, bx + box_w + box_gap - 2
            )

    if side_annotations:
        side_x = 40 + n * (box_w + box_gap) - box_gap + 24
        for note in side_annotations[:6]:
            out += svg_text(side_x, note.get("y", layer_top),
                            note.get("text", ""),
                            accent_alias="muted", size=11)

    if kpi_band:
        fy = base_h - band_h - 20
        out += svg_box_filled(40, fy, width - 80, band_h, fill_alias="light")
        out += svg_text(60, fy + 22, "Quantified specs",
                        accent_alias="navy", size=12, weight=700)
        out += svg_text(60, fy + 42, kpi_band,
                        accent_alias="ink", size=11)

    if has_captions:
        out += _captions_under_positions(positions, captions, base_h,
                                         max_chars=28)

    out += svg_close()
    return _result(out, width, height, "layered_stack", captions)


# ===========================================================================
# 4. fanout_pipeline — top input → N parallel boxes → fusion → outputs
# ===========================================================================
def fanout_pipeline(
    input_label: str,
    models: list[dict],
    fusion_label: str,
    outputs: list[dict],
    *,
    title: str | None = None,
    subtitle: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Top input → N parallel models → fusion → branched outputs.

    ``captions`` is parallel to ``models``; rendered as a strip below the
    parallel-models row (not below the outputs — captions describe the
    models, which is where the metric drift mattered).
    """
    if not 3 <= len(models) <= 7:
        raise ValueError(f"fanout_pipeline needs 3-7 models, got {len(models)}")
    if not 2 <= len(outputs) <= 3:
        raise ValueError(f"fanout_pipeline needs 2-3 outputs, got {len(outputs)}")

    width = CANVAS_W
    has_captions = bool(captions)
    base_h = CANVAS_H_TALL
    height = base_h + (CAPTION_STRIP_H if has_captions else 0)
    out = svg_open(width, height,
                   title=title or "Fan-out pipeline",
                   desc="Parallel models with fusion + branched outputs",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)
    if subtitle:
        out += svg_subtitle_label(40, 75, subtitle)

    in_w, in_h = 280, 56
    in_x = (width - in_w) // 2
    in_y = 110
    out += svg_box_filled(in_x, in_y, in_w, in_h, fill_alias="navy")
    out += svg_text(in_x + in_w // 2, in_y + 36, input_label,
                    accent_alias="white", size=13, weight=700,
                    anchor="middle")

    n = len(models)
    positions = even_split_x(width, n, padding=40, gap=22)
    model_h = 96
    model_top = in_y + in_h + 80

    for (mx, mw), m in zip(positions, models):
        out += svg_box(mx, model_top, mw, model_h,
                       fill_alias="white",
                       stroke_alias="blue",
                       stroke_width=STROKE_NORMAL)
        out += svg_text(mx + mw // 2, model_top + 38,
                        m.get("name", ""),
                        accent_alias="blue", size=13, weight=700,
                        anchor="middle")
        desc = m.get("desc", "")
        if desc:
            out += svg_text(mx + mw // 2, model_top + 62,
                            desc, accent_alias="ink", size=11,
                            anchor="middle")
        out += (
            f'  <path d="M {in_x + in_w // 2} {in_y + in_h + 4} '
            f'L {mx + mw // 2} {model_top - 4}" '
            f'stroke="{accent("border")}" stroke-width="1.5" fill="none"/>\n'
        )

    fusion_top = model_top + model_h + 50
    fusion_h = 70
    out += svg_box_filled(40, fusion_top, width - 80, fusion_h,
                          fill_alias="deep")
    out += svg_text(width // 2, fusion_top + 28, fusion_label,
                    accent_alias="white", size=13, weight=700, anchor="middle")
    for (mx, mw), _m in zip(positions, models):
        out += (
            f'  <path d="M {mx + mw // 2} {model_top + model_h + 4} '
            f'L {width // 2} {fusion_top - 4}" '
            f'stroke="{accent("border")}" stroke-width="1.5" fill="none"/>\n'
        )

    out_top = fusion_top + fusion_h + 30
    out_h = 40
    out_n = len(outputs)
    out_positions = even_split_x(width, out_n, padding=200, gap=40)
    for (ox, ow), op in zip(out_positions, outputs):
        oa = op.get("accent", "blue")
        out += svg_box(ox, out_top, ow, out_h,
                       fill_alias="white", stroke_alias=oa,
                       stroke_width=STROKE_NORMAL)
        out += svg_text(ox + ow // 2, out_top + 26,
                        op.get("label", ""),
                        accent_alias=oa, size=12, weight=700, anchor="middle")
        out += svg_arrow(width // 2, fusion_top + fusion_h + 4,
                         ox + ow // 2, out_top - 4,
                         accent_alias="muted")

    if has_captions:
        out += _captions_under_positions(positions, captions, base_h,
                                         max_chars=28)

    out += svg_close()
    return _result(out, width, height, "fanout_pipeline", captions)


# ===========================================================================
# 5. hybrid_swimlane — 2+ horizontal lanes sharing one input column
# ===========================================================================
def hybrid_swimlane(
    tiers: list[dict],
    *,
    fleet_box: dict | None = None,
    header: str | None = None,
    footer: str | None = None,
    title: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Two or more horizontal lanes sharing one input column on the left.

    ``captions`` is parallel to tiers; rendered as a strip below the lanes.
    """
    if not 2 <= len(tiers) <= 3:
        raise ValueError(f"hybrid_swimlane needs 2-3 tiers, got {len(tiers)}")

    width = CANVAS_W
    has_captions = bool(captions)
    base_h = CANVAS_H_TALL
    height = base_h + (CAPTION_STRIP_H if has_captions else 0)

    out = svg_open(width, height,
                   title=title or "Hybrid swimlane",
                   desc="Multiple parallel lanes sharing one input column",
                   bg="pale")

    cursor_y = 30
    if title:
        out += svg_title_label(40, cursor_y + 20, title)
        cursor_y += 30

    if header:
        hb_y = cursor_y + 10
        out += svg_box_filled(40, hb_y, width - 80, 50, fill_alias="navy")
        out += svg_text(60, hb_y + 30, header,
                        accent_alias="white", size=13, weight=700)
        cursor_y = hb_y + 50

    fleet_w = 200 if fleet_box else 0
    fleet_pad = 20 if fleet_box else 40
    lane_x = fleet_pad + fleet_w + (20 if fleet_box else 0)
    lane_w = width - lane_x - 40

    n_tiers = len(tiers)
    lane_top = cursor_y + 20
    lane_h_total = base_h - lane_top - (50 if footer else 30)
    lane_gap = 18
    lane_h = (lane_h_total - (n_tiers - 1) * lane_gap) // n_tiers

    if fleet_box:
        fb_y = lane_top
        fb_h = lane_h_total
        out += svg_box(fleet_pad, fb_y, fleet_w, fb_h,
                       fill_alias="white", stroke_alias="muted",
                       stroke_width=1.5)
        out += svg_text(fleet_pad + fleet_w // 2, fb_y + 35,
                        fleet_box.get("label", ""),
                        accent_alias="navy", size=13, weight=700,
                        anchor="middle")
        sub = fleet_box.get("sub", "")
        if sub:
            out += svg_text(fleet_pad + fleet_w // 2, fb_y + 58,
                            sub, accent_alias="muted", size=11,
                            anchor="middle")

    lane_positions: list[tuple[int, int]] = []
    for i, tier in enumerate(tiers):
        ly = lane_top + i * (lane_h + lane_gap)
        lane_positions.append((lane_x, lane_w))
        accent_alias = tier.get("accent", "deep")
        out += svg_box(lane_x, ly, lane_w, lane_h,
                       fill_alias="white", stroke_alias=accent_alias,
                       stroke_width=STROKE_NORMAL)
        out += svg_text(lane_x + 20, ly + 28,
                        tier.get("label", ""),
                        accent_alias=accent_alias, size=12, weight=700)

        stages = tier.get("stages", [])[:4]
        if stages:
            stage_gap = 18
            avail = lane_w - 60 - (len(stages) - 1) * stage_gap
            stage_w = avail // len(stages)
            stage_h = lane_h - 70
            stage_top = ly + 50
            for j, stage in enumerate(stages):
                sx = lane_x + 30 + j * (stage_w + stage_gap)
                if stage.get("filled"):
                    out += svg_box_filled(sx, stage_top, stage_w, stage_h,
                                          fill_alias=accent_alias)
                    title_color = "white"
                    sub_color = "light"
                else:
                    out += svg_box_filled(sx, stage_top, stage_w, stage_h,
                                          fill_alias="light")
                    title_color = "navy"
                    sub_color = "ink"
                out += svg_text(sx + stage_w // 2, stage_top + stage_h // 2 - 6,
                                stage.get("title", ""),
                                accent_alias=title_color, size=12, weight=700,
                                anchor="middle")
                if stage.get("sub"):
                    out += svg_text(sx + stage_w // 2, stage_top + stage_h // 2 + 14,
                                    stage.get("sub", ""),
                                    accent_alias=sub_color, size=10,
                                    anchor="middle")
                if j < len(stages) - 1:
                    ay = stage_top + stage_h // 2
                    out += svg_connector_horizontal(
                        sx + stage_w + 2, ay,
                        sx + stage_w + stage_gap - 2,
                    )

        if fleet_box:
            ay_in = ly + lane_h // 2
            ay_out = lane_top + lane_h_total // 2
            dashed = (i > 0)
            out += svg_arrow(fleet_pad + fleet_w + 2, ay_out,
                             lane_x - 4, ay_in,
                             accent_alias="muted",
                             dashed=dashed)

    if footer:
        fy = base_h - 30
        out += svg_text(40, fy, footer, accent_alias="muted", size=11)

    if has_captions:
        # One caption per tier — render as inline notes anchored to each lane's
        # right edge below the diagram.
        cap_y = base_h + 8
        # Distribute captions evenly across the lane width.
        cap_positions: list[tuple[int, int]] = []
        n_cap = min(len(captions), n_tiers)
        slot_w = lane_w // max(n_cap, 1)
        for k in range(n_cap):
            cap_positions.append((lane_x + k * slot_w, slot_w))
        out += _captions_under_positions(cap_positions, captions, cap_y - 8,
                                         max_chars=36)

    out += svg_close()
    return _result(out, width, height, "hybrid_swimlane", captions)


__all__ = [
    "flow_diagram",
    "quadrant",
    "layered_stack",
    "fanout_pipeline",
    "hybrid_swimlane",
]
