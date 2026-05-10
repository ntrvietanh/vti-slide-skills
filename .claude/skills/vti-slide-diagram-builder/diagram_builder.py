"""Public API — 7 standardised diagram primitives for VTI slide decks.

Each primitive returns::

    {
        "svg":        str,    # complete <svg> element
        "natural_w":  int,
        "natural_h":  int,
        "primitive":  str,
    }

`natural_w / natural_h` is the SVG's native viewBox — consumers (the
creator's Phase 4 layout-designer) use these to set the hosting cell's
aspect-ratio so the diagram is never cropped.

All colours come from `tokens_bridge.TOKENS`. Hex literals in this file
are forbidden (verify-time grep enforces it).
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

VERSION = "0.1.0"


def _result(svg: str, w: int, h: int, name: str) -> dict[str, Any]:
    return {"svg": svg, "natural_w": w, "natural_h": h, "primitive": name}


# ===========================================================================
# 1. flow_diagram — horizontal sequence of 3-7 boxes + chevron arrows
# ===========================================================================
def make_flow_diagram(
    steps: list[dict],
    *,
    orientation: str = "horizontal",
    accent_alias: str = "deep",
    title: str | None = None,
    subtitle: str | None = None,
) -> dict[str, Any]:
    """Sequential flow of 3-7 boxes connected by arrows.

    Args:
        steps:        list of {"title": str, "sub"?: str, "number"?: str}
                      (3-7 entries)
        orientation:  'horizontal' (default) or 'vertical'
        accent_alias: 'deep' | 'navy' | 'sky' | 'teal' (uniform colour)
        title:        optional top-of-canvas heading
        subtitle:     optional subheading under title

    Natural size: 1180×460 (wide).
    """
    if not 3 <= len(steps) <= 7:
        raise ValueError(f"flow_diagram needs 3-7 steps, got {len(steps)}")
    if orientation not in ("horizontal", "vertical"):
        raise ValueError(f"orientation must be horizontal|vertical")

    width, height = CANVAS_W, CANVAS_H_WIDE
    out = svg_open(width, height,
                   title=title or "Flow diagram",
                   desc="Sequential flow of process steps",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)
    if subtitle:
        out += svg_subtitle_label(40, 75, subtitle)

    if orientation == "horizontal":
        # Compute box dimensions to fit horizontally
        n = len(steps)
        positions = even_split_x(width, n, padding=30, gap=22)
        box_h = 130
        box_top = (height - box_h) // 2 + (15 if title else 0)
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
                # Arrow from this box to next
                next_bx, _ = positions[i + 1]
                ay = box_top + box_h // 2
                out += svg_connector_horizontal(bx + bw + 2, ay, next_bx - 4)
    else:
        # vertical
        n = len(steps)
        box_w = 380
        box_h = 70
        gap = 14
        total_h = n * box_h + (n - 1) * gap
        start_y = max(80, (height - total_h) // 2 + (15 if title else 0))
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

    out += svg_close()
    return _result(out, width, height, "flow_diagram")


# ===========================================================================
# 2. quadrant — exactly 4 cells in a 2x2 grid + optional bottom band
# ===========================================================================
def make_quadrant(
    cells: list[dict],
    *,
    title: str | None = None,
    footer: str | None = None,
) -> dict[str, Any]:
    """Exactly 4 cells in a 2x2 grid.

    Args:
        cells:  list of 4 dicts: {"title": str, "accent": str (alias),
                                  "items": list[str]}
        title:  optional top heading
        footer: optional dark band at the bottom

    Natural size: 1180×600 (tall).
    """
    if len(cells) != 4:
        raise ValueError(f"quadrant requires exactly 4 cells, got {len(cells)}")

    width, height = CANVAS_W, CANVAS_H_TALL
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
    grid_bottom = height - band_h - band_pad - 20
    grid_h = grid_bottom - grid_top
    grid_left = 40
    grid_right = width - 40
    grid_w = grid_right - grid_left
    cell_gap = 12
    cell_w = (grid_w - cell_gap) // 2
    cell_h = (grid_h - cell_gap) // 2

    positions = [
        (grid_left, grid_top),
        (grid_left + cell_w + cell_gap, grid_top),
        (grid_left, grid_top + cell_h + cell_gap),
        (grid_left + cell_w + cell_gap, grid_top + cell_h + cell_gap),
    ]
    for (cx, cy), cell in zip(positions, cells):
        accent_alias = cell.get("accent", "deep")
        # Soft tint derived from accent (mix 92% white).
        bg_color = tint(accent_alias, ratio=0.92)
        out += (
            f'  <rect x="{cx}" y="{cy}" width="{cell_w}" height="{cell_h}" '
            f'rx="10" fill="{bg_color}"/>\n'
        )
        # Accent label header
        title_text = cell.get("title", "")
        out += svg_text(cx + 24, cy + 36, title_text,
                        accent_alias=accent_alias, size=14,
                        weight=700, anchor="start")
        out += (
            f'  <line x1="{cx + 24}" y1="{cy + 48}" '
            f'x2="{cx + 84}" y2="{cy + 48}" '
            f'stroke="{accent(accent_alias)}" stroke-width="2"/>\n'
        )
        # Items list
        items = cell.get("items", [])[:8]
        for i, item in enumerate(items):
            out += svg_text(cx + 30, cy + 80 + i * 20,
                            f"• {item}", accent_alias="ink", size=11.5)

    if footer:
        fy = height - band_h - 20
        out += svg_box_filled(40, fy, width - 80, band_h, fill_alias="navy")
        out += svg_text(60, fy + band_h // 2 + 4, footer,
                        accent_alias="white", size=11, anchor="start")

    out += svg_close()
    return _result(out, width, height, "quadrant")


# ===========================================================================
# 3. footprint_map — APAC continent outline + N pinned cities + legend
# ===========================================================================
def make_footprint_map(
    cities: list[dict],
    *,
    region: str = "APAC",
    scale_label: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Continent-outline map with pins. APAC region only at v0.1.0.

    Args:
        cities:      list of {"name": str, "x": int, "y": int,
                              "highlight"?: bool}.
                     Coordinates use the canvas pixel-space directly
                     (1180×600). For convenience: x∈[100, 1080], y∈[100, 540].
        region:      'APAC' (only one supported at v0.1.0)
        scale_label: optional one-line legend (e.g. "4 countries · 9 offices")
        title:       optional top heading

    Natural size: 1180×600 (tall).
    """
    if region != "APAC":
        raise ValueError(f"only region='APAC' supported at v0.1.0, got {region!r}")

    width, height = CANVAS_W, CANVAS_H_TALL
    out = svg_open(width, height,
                   title=title or "APAC footprint map",
                   desc=f"Map of {region} with pinned offices",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)

    # Simplified continent silhouettes — same pattern as the seed but
    # scaled for 1180×600 canvas.
    out += (
        f'  <path d="M 240 100 Q 270 130 290 200 Q 300 280 330 350 '
        f'Q 360 380 380 410 L 420 460 L 400 510 L 360 530 L 320 510 '
        f'L 280 470 L 260 420 L 240 360 L 235 280 Z" '
        f'fill="{accent("light")}" stroke="{accent("border")}" stroke-width="1"/>\n'
    )
    out += (
        f'  <path d="M 720 130 Q 770 150 800 180 Q 840 210 880 240 '
        f'Q 910 250 920 270 L 900 260 L 850 250 L 800 250 L 760 230 '
        f'L 730 200 Z" '
        f'fill="{accent("light")}" stroke="{accent("border")}" stroke-width="1"/>\n'
    )
    out += (
        f'  <path d="M 720 130 Q 710 100 730 80 L 790 70 L 810 90 '
        f'L 800 130 Z" '
        f'fill="{accent("light")}" stroke="{accent("border")}" stroke-width="1"/>\n'
    )
    out += svg_text(450, 80, region, accent_alias="muted", size=14,
                    weight=400, anchor="start")

    # Pins
    for city in cities:
        x, y = city.get("x", 100), city.get("y", 100)
        name = city.get("name", "")
        if city.get("highlight"):
            out += (
                f'  <circle cx="{x}" cy="{y}" r="22" '
                f'fill="{accent("deep")}" opacity="0.18"/>\n'
                f'  <circle cx="{x}" cy="{y}" r="14" '
                f'fill="{accent("deep")}" opacity="0.32"/>\n'
                f'  <circle cx="{x}" cy="{y}" r="8" '
                f'fill="{accent("deep")}"/>\n'
            )
            out += svg_text(x + 18, y + 5, name,
                            accent_alias="navy", size=18, weight=700)
            sub = city.get("sub", "VTI APAC HQ")
            out += svg_text(x + 18, y + 26, sub,
                            accent_alias="deep", size=12)
        else:
            out += (
                f'  <circle cx="{x}" cy="{y}" r="6" '
                f'fill="{accent("blue")}"/>\n'
            )
            out += svg_text(x + 12, y + 4, name,
                            accent_alias="navy", size=14)

    if scale_label:
        out += svg_box(40, height - 80, 360, 60,
                       fill_alias="white", stroke_alias="border",
                       stroke_width=1, radius=6)
        out += (
            f'  <circle cx="60" cy="{height - 50}" r="5" fill="{accent("blue")}"/>\n'
        )
        out += svg_text(74, height - 45, "Standard office",
                        accent_alias="ink", size=12)
        out += (
            f'  <circle cx="200" cy="{height - 50}" r="7" fill="{accent("deep")}"/>\n'
        )
        out += svg_text(214, height - 45, "VTI APAC HQ",
                        accent_alias="ink", size=12)
        out += svg_text(60, height - 25, scale_label,
                        accent_alias="muted", size=11)

    out += svg_close()
    return _result(out, width, height, "footprint_map")


# ===========================================================================
# 4. layered_stack — left-to-right horizontal stack of 4-6 vertical cards
# ===========================================================================
def make_layered_stack(
    layers: list[dict],
    *,
    side_annotations: list[dict] | None = None,
    kpi_band: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Left-to-right horizontal stack of 4-6 vertical cards.

    Args:
        layers:           list of {"label": str, "items": list[str],
                                   "accent": str (alias),
                                   "filled"?: bool (solid fill last layer)}
                          (4-6 entries)
        side_annotations: optional list of {"text": str, "y": int}
        kpi_band:         optional bottom KPI band string
        title:            optional top heading

    Natural size: 1180×600 (tall).
    """
    if not 4 <= len(layers) <= 6:
        raise ValueError(f"layered_stack needs 4-6 layers, got {len(layers)}")

    width, height = CANVAS_W, CANVAS_H_TALL
    out = svg_open(width, height,
                   title=title or "Layered architecture stack",
                   desc="Layered architecture with arrows between layers",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)

    # Reserve space for kpi_band at the bottom
    band_h = 55 if kpi_band else 0
    band_pad = 20 if kpi_band else 0
    layer_top = 90
    layer_bottom = height - band_h - band_pad - 30
    layer_h = layer_bottom - layer_top

    n = len(layers)
    side_w = 0  # reserved for annotations on the right
    if side_annotations:
        side_w = 180
    avail_w = width - 80 - side_w
    box_gap = 26
    box_w = (avail_w - (n - 1) * box_gap) // n

    for i, layer in enumerate(layers):
        bx = 40 + i * (box_w + box_gap)
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

        # Layer label
        out += svg_text(bx + box_w // 2, layer_top + 32,
                        layer.get("label", ""),
                        accent_alias=label_color, size=13, weight=700,
                        anchor="middle")
        # Items
        items = layer.get("items", [])[:10]
        for j, item in enumerate(items):
            out += svg_text(bx + box_w // 2, layer_top + 70 + j * 20,
                            item, accent_alias=item_color, size=11,
                            anchor="middle")

        # Arrow to next
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
        fy = height - band_h - 20
        out += svg_box_filled(40, fy, width - 80, band_h, fill_alias="light")
        out += svg_text(60, fy + 22, "Quantified specs",
                        accent_alias="navy", size=12, weight=700)
        out += svg_text(60, fy + 42, kpi_band,
                        accent_alias="ink", size=11)

    out += svg_close()
    return _result(out, width, height, "layered_stack")


# ===========================================================================
# 5. fanout_pipeline — top input → N parallel boxes → fusion → outputs
# ===========================================================================
def make_fanout_pipeline(
    input_label: str,
    models: list[dict],
    fusion_label: str,
    outputs: list[dict],
    *,
    title: str | None = None,
    subtitle: str | None = None,
) -> dict[str, Any]:
    """Top input → N parallel models → fusion → branched outputs.

    Args:
        input_label:  text for the top input box
        models:       list of {"name": str, "desc"?: str} (3-7 entries)
        fusion_label: text for the fusion bar (the "verification rules" row)
        outputs:      list of {"label": str, "accent": str (alias)} (2-3)
        title:        optional top heading
        subtitle:     optional subheading under title

    Natural size: 1180×600 (tall).
    """
    if not 3 <= len(models) <= 7:
        raise ValueError(f"fanout_pipeline needs 3-7 models, got {len(models)}")
    if not 2 <= len(outputs) <= 3:
        raise ValueError(f"fanout_pipeline needs 2-3 outputs, got {len(outputs)}")

    width, height = CANVAS_W, CANVAS_H_TALL
    out = svg_open(width, height,
                   title=title or "Fan-out pipeline",
                   desc="Parallel models with fusion + branched outputs",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)
    if subtitle:
        out += svg_subtitle_label(40, 75, subtitle)

    # Top input
    in_w, in_h = 280, 56
    in_x = (width - in_w) // 2
    in_y = 110
    out += svg_box_filled(in_x, in_y, in_w, in_h, fill_alias="navy")
    out += svg_text(in_x + in_w // 2, in_y + 36, input_label,
                    accent_alias="white", size=13, weight=700,
                    anchor="middle")

    # Parallel models row
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
        # Arrow from input to this model (subtle dashed)
        out += (
            f'  <path d="M {in_x + in_w // 2} {in_y + in_h + 4} '
            f'L {mx + mw // 2} {model_top - 4}" '
            f'stroke="{accent("border")}" stroke-width="1.5" fill="none"/>\n'
        )

    # Fusion bar
    fusion_top = model_top + model_h + 50
    fusion_h = 70
    out += svg_box_filled(40, fusion_top, width - 80, fusion_h,
                          fill_alias="deep")
    out += svg_text(width // 2, fusion_top + 28, fusion_label,
                    accent_alias="white", size=13, weight=700, anchor="middle")
    # Arrows from each model into fusion bar
    for (mx, mw), _m in zip(positions, models):
        out += (
            f'  <path d="M {mx + mw // 2} {model_top + model_h + 4} '
            f'L {width // 2} {fusion_top - 4}" '
            f'stroke="{accent("border")}" stroke-width="1.5" fill="none"/>\n'
        )

    # Outputs
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
        # Arrow from fusion to output
        out += svg_arrow(width // 2, fusion_top + fusion_h + 4,
                         ox + ow // 2, out_top - 4,
                         accent_alias="muted")

    out += svg_close()
    return _result(out, width, height, "fanout_pipeline")


# ===========================================================================
# 6. hybrid_swimlane — 2+ horizontal lanes sharing one input column
# ===========================================================================
def make_hybrid_swimlane(
    tiers: list[dict],
    *,
    fleet_box: dict | None = None,
    header: str | None = None,
    footer: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Two or more horizontal lanes sharing one input column on the left.

    Args:
        tiers:     list of {"label": str, "accent": str (alias),
                            "stages": list[{"title": str, "sub"?: str,
                                            "filled"?: bool}]}
                   2-3 lanes; each lane has 2-4 stages.
        fleet_box: optional left-most input column dict
                   {"label": str, "sub"?: str}
        header:    optional dark band at the top
        footer:    optional one-line caption at the bottom
        title:     optional top heading (rendered above header band)

    Natural size: 1180×600 (tall).
    """
    if not 2 <= len(tiers) <= 3:
        raise ValueError(f"hybrid_swimlane needs 2-3 tiers, got {len(tiers)}")

    width, height = CANVAS_W, CANVAS_H_TALL
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

    # Layout
    fleet_w = 200 if fleet_box else 0
    fleet_pad = 20 if fleet_box else 40
    lane_x = fleet_pad + fleet_w + (20 if fleet_box else 0)
    lane_w = width - lane_x - 40

    n_tiers = len(tiers)
    lane_top = cursor_y + 20
    lane_h_total = height - lane_top - (50 if footer else 30)
    lane_gap = 18
    lane_h = (lane_h_total - (n_tiers - 1) * lane_gap) // n_tiers

    # Fleet (input) box
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

    # Lanes
    for i, tier in enumerate(tiers):
        ly = lane_top + i * (lane_h + lane_gap)
        accent_alias = tier.get("accent", "deep")
        out += svg_box(lane_x, ly, lane_w, lane_h,
                       fill_alias="white", stroke_alias=accent_alias,
                       stroke_width=STROKE_NORMAL)
        out += svg_text(lane_x + 20, ly + 28,
                        tier.get("label", ""),
                        accent_alias=accent_alias, size=12, weight=700)

        # Stages in lane
        stages = tier.get("stages", [])[:4]
        if stages:
            stage_w = (lane_w - 70) // len(stages)
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

        # Arrow from fleet box to lane (if fleet present)
        if fleet_box:
            ay_in = ly + lane_h // 2
            ay_out = lane_top + lane_h_total // 2
            dashed = (i > 0)
            out += svg_arrow(fleet_pad + fleet_w + 2, ay_out,
                             lane_x - 4, ay_in,
                             accent_alias="muted",
                             dashed=dashed)

    if footer:
        fy = height - 30
        out += svg_text(40, fy, footer, accent_alias="muted", size=11)

    out += svg_close()
    return _result(out, width, height, "hybrid_swimlane")


# ===========================================================================
# 7. data_path — 4-stage horizontal flow with cloud-as-brain emphasis
# ===========================================================================
def make_data_path(
    stages: list[dict],
    *,
    callout: dict | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """4-stage horizontal flow with optional callout band at the bottom.

    Args:
        stages:  list of {"label": str, "accent": str (alias),
                          "items": list[str], "brain"?: bool}.
                 The 'brain' flag makes that stage's box internally split
                 into 2 sub-boxes + a dark "engine" band.
                 Typical pattern: device → mobile → cloud(brain) → provider.
        callout: optional {"title": str, "body": str} band at the bottom
        title:   optional top heading

    Natural size: 1180×460 (wide).
    """
    if not 3 <= len(stages) <= 5:
        raise ValueError(f"data_path needs 3-5 stages, got {len(stages)}")

    width, height = CANVAS_W, CANVAS_H_WIDE
    out = svg_open(width, height,
                   title=title or "Data path",
                   desc="Stages of data flowing from source to consumer",
                   bg="pale")
    if title:
        out += svg_title_label(40, 50, title)

    callout_h = 80 if callout else 0
    flow_top = 90
    flow_bottom = height - callout_h - (20 if callout else 30)
    flow_h = flow_bottom - flow_top
    n = len(stages)
    positions = even_split_x(width, n, padding=30, gap=20)

    for i, ((bx, bw), stage) in enumerate(zip(positions, stages)):
        accent_alias = stage.get("accent", "deep")
        is_brain = stage.get("brain", False)
        out += svg_box(bx, flow_top, bw, flow_h,
                       fill_alias="white",
                       stroke_alias=accent_alias,
                       stroke_width=STROKE_NORMAL)
        out += svg_text(bx + bw // 2, flow_top + 30,
                        stage.get("label", ""),
                        accent_alias=accent_alias, size=12, weight=700,
                        anchor="middle")
        items = stage.get("items", [])[:8]
        item_y = flow_top + 60
        if is_brain and len(items) >= 2:
            # Split into 2 inner sub-boxes + a dark band
            sub_w = (bw - 30) // 2
            sub_h = 55
            sub_y = flow_top + 60
            out += svg_box_filled(bx + 10, sub_y, sub_w, sub_h,
                                  fill_alias="light")
            out += svg_text(bx + 10 + sub_w // 2, sub_y + 22,
                            items[0], accent_alias="navy", size=11,
                            weight=700, anchor="middle")
            if len(items) > 1:
                out += svg_box_filled(bx + 20 + sub_w, sub_y, sub_w, sub_h,
                                      fill_alias="light")
                out += svg_text(bx + 20 + sub_w + sub_w // 2, sub_y + 22,
                                items[1], accent_alias="navy", size=11,
                                weight=700, anchor="middle")
            band_y = sub_y + sub_h + 10
            band_h = 50
            out += svg_box_filled(bx + 10, band_y, bw - 20, band_h,
                                  fill_alias="navy")
            if len(items) > 2:
                out += svg_text(bx + bw // 2, band_y + 22,
                                items[2], accent_alias="white",
                                size=11, weight=700, anchor="middle")
            if len(items) > 3:
                out += svg_text(bx + bw // 2, band_y + 40,
                                items[3], accent_alias="light",
                                size=10, anchor="middle")
        else:
            for j, item in enumerate(items):
                out += svg_text(bx + 16, item_y + j * 20,
                                f"• {item}", accent_alias="ink", size=11)

        # Arrow to next
        if i < n - 1:
            ay = flow_top + flow_h // 2
            next_bx, _ = positions[i + 1]
            out += svg_connector_horizontal(bx + bw + 2, ay, next_bx - 4)

    if callout:
        cy = height - callout_h - 5
        out += svg_box_filled(40, cy, width - 80, callout_h, fill_alias="light")
        out += svg_text(60, cy + 24, callout.get("title", ""),
                        accent_alias="navy", size=12, weight=700)
        out += svg_text(60, cy + 46, callout.get("body", ""),
                        accent_alias="ink", size=11)

    out += svg_close()
    return _result(out, width, height, "data_path")


# ===========================================================================
# Discovery + dispatch
# ===========================================================================
_PRIMITIVES: dict[str, Any] = {
    "flow_diagram":     make_flow_diagram,
    "quadrant":         make_quadrant,
    "footprint_map":    make_footprint_map,
    "layered_stack":    make_layered_stack,
    "fanout_pipeline":  make_fanout_pipeline,
    "hybrid_swimlane":  make_hybrid_swimlane,
    "data_path":        make_data_path,
}


_PRIMITIVE_META: dict[str, dict] = {
    "flow_diagram": {
        "name":         "flow_diagram",
        "natural_size": "1180x460",
        "good_for":     ["sequence/process", "ETL pipelines", "AWS reference architecture"],
        "params":       {
            "steps": "list[{title<=30, sub?<=60, number?}] (3-7)",
            "orientation": "'horizontal'|'vertical'",
            "accent_alias": "'deep'|'navy'|'sky'|'teal'",
            "title": "optional",
            "subtitle": "optional",
        },
    },
    "quadrant": {
        "name":         "quadrant",
        "natural_size": "1180x600",
        "good_for":     ["four-pillar platforms", "2x2 framework grids"],
        "params":       {
            "cells": "list[{title, accent, items[]}] (exactly 4)",
            "title": "optional",
            "footer": "optional bottom band",
        },
    },
    "footprint_map": {
        "name":         "footprint_map",
        "natural_size": "1180x600",
        "good_for":     ["company office locations", "regional deployment maps"],
        "params":       {
            "cities": "list[{name, x, y, highlight?}]",
            "region": "'APAC' (only at v0.1.0)",
            "scale_label": "optional one-line legend",
            "title": "optional",
        },
    },
    "layered_stack": {
        "name":         "layered_stack",
        "natural_size": "1180x600",
        "good_for":     ["protocol layers", "FHIR/HealthLake stacks", "IoT gateways"],
        "params": {
            "layers": "list[{label, items[], accent, filled?}] (4-6)",
            "side_annotations": "optional list[{text, y}]",
            "kpi_band": "optional bottom KPI string",
            "title": "optional",
        },
    },
    "fanout_pipeline": {
        "name":         "fanout_pipeline",
        "natural_size": "1180x600",
        "good_for":     ["multi-model CV pipelines", "ensemble verification"],
        "params": {
            "input_label": "str",
            "models": "list[{name, desc?}] (3-7)",
            "fusion_label": "str",
            "outputs": "list[{label, accent}] (2-3)",
        },
    },
    "hybrid_swimlane": {
        "name":         "hybrid_swimlane",
        "natural_size": "1180x600",
        "good_for":     ["security+retail dual stack", "edge+server split"],
        "params": {
            "tiers": "list[{label, accent, stages[]}] (2-3)",
            "fleet_box": "optional input column on the left",
            "header": "optional top dark band",
            "footer": "optional caption",
            "title": "optional",
        },
    },
    "data_path": {
        "name":         "data_path",
        "natural_size": "1180x460",
        "good_for":     ["RPM stack", "device→cloud→consumer flows"],
        "params": {
            "stages": "list[{label, accent, items[], brain?}] (3-5)",
            "callout": "optional bottom note {title, body}",
            "title": "optional",
        },
    },
}


# Intent → primitive name (creator's Phase 3 uses this)
_INTENT_TO_PRIMITIVE: dict[str, str] = {
    "aws-reference":         "flow_diagram",
    "etl-pipeline":          "flow_diagram",
    "process":               "flow_diagram",
    "four-pillar":           "quadrant",
    "2x2":                   "quadrant",
    "footprint":             "footprint_map",
    "office-map":            "footprint_map",
    "layered-architecture":  "layered_stack",
    "protocol-stack":        "layered_stack",
    "iot-gateway":           "layered_stack",
    "fhir-stack":            "layered_stack",
    "multi-model":           "fanout_pipeline",
    "fanout":                "fanout_pipeline",
    "edge-server-split":     "hybrid_swimlane",
    "security-retail":       "hybrid_swimlane",
    "swimlane":              "hybrid_swimlane",
    "device-cloud":          "data_path",
    "rpm":                   "data_path",
    "data-path":             "data_path",
}


def list_primitives() -> list[str]:
    """All registered primitive names."""
    return list(_PRIMITIVES.keys())


def describe_primitive(name: str) -> dict:
    """Metadata + param spec for one primitive."""
    if name not in _PRIMITIVE_META:
        raise ValueError(
            f"unknown primitive {name!r}; valid: {list(_PRIMITIVES.keys())}"
        )
    return dict(_PRIMITIVE_META[name])


def primitive_for_intent(intent: str) -> str | None:
    """Map a slide intent string (e.g. 'aws-reference') to a primitive name.

    Returns None if no mapping found.
    """
    return _INTENT_TO_PRIMITIVE.get(intent)


def call(name: str, **kwargs) -> dict[str, Any]:
    """Dispatcher — call a primitive by name with kwargs."""
    if name not in _PRIMITIVES:
        raise ValueError(
            f"unknown primitive {name!r}; valid: {list(_PRIMITIVES.keys())}"
        )
    return _PRIMITIVES[name](**kwargs)


__all__ = [
    "VERSION",
    "make_flow_diagram",
    "make_quadrant",
    "make_footprint_map",
    "make_layered_stack",
    "make_fanout_pipeline",
    "make_hybrid_swimlane",
    "make_data_path",
    "list_primitives",
    "describe_primitive",
    "primitive_for_intent",
    "call",
]
