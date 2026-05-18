"""Public API — 7 standardised diagram primitives for VTI slide decks.

v0.3.0 split the primitives across two backends:

- ``backend="mermaid"`` (5 primitives): ``flow_diagram``, ``quadrant``,
  ``layered_stack``, ``fanout_pipeline``, ``hybrid_swimlane``. These
  return a **render task** (Mermaid source) — the caller (agent) renders
  it via the Mermaid Chart MCP tool
  ``mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram``,
  saves the returned SVG to ``work/diagrams/<slide_id>.svg``, then reads
  the viewBox to fill in ``natural_w`` / ``natural_h``.

- ``backend="python"`` (2 primitives): ``footprint_map``, ``data_path``.
  These render natively to SVG and return ``{svg, natural_w, natural_h}``
  as before — no agent step required.

Return shapes::

    # backend == "mermaid"
    {
        "primitive":     str,
        "backend":       "mermaid",
        "mermaid_code":  str,    # Mermaid source incl. theme directive
        "hint_w":        int,    # expected natural width (sanity check)
        "hint_h":        int,    # expected natural height (sanity check)
    }

    # backend == "python"
    {
        "primitive":     str,
        "backend":       "python",
        "svg":           str,    # complete <svg> element
        "natural_w":     int,
        "natural_h":     int,
    }

`natural_w / natural_h` is the SVG's native viewBox — consumers (the
creator's Phase 4 layout-designer) use these to set the hosting cell's
aspect-ratio so the diagram is never cropped.

All colours come from `tokens_bridge.TOKENS`. Hex literals in this file
are forbidden (verify-time grep enforces it).
"""
from __future__ import annotations

from typing import Any

import mermaid_codegen
from svg_primitives import (
    CANVAS_W, CANVAS_H_WIDE, CANVAS_H_TALL,
    STROKE_NORMAL,
    svg_open, svg_close,
    svg_title_label, svg_text,
    svg_box, svg_box_filled,
    svg_connector_horizontal,
    even_split_x,
)
from tokens_bridge import accent

VERSION = "0.3.0"

# Primitives whose rendering is delegated to Mermaid Chart MCP. Listed
# here as a single source of truth — ``describe_primitive`` and any
# external dispatcher (creator Phase 3) can read this to decide whether
# to expect an immediate SVG or to invoke the MCP render step.
MERMAID_BACKED: frozenset[str] = frozenset({
    "flow_diagram",
    "quadrant",
    "layered_stack",
    "fanout_pipeline",
    "hybrid_swimlane",
})

PYTHON_BACKED: frozenset[str] = frozenset({
    "footprint_map",
    "data_path",
})


def _native_result(svg: str, w: int, h: int, name: str) -> dict[str, Any]:
    """Return-shape helper for native (Python-rendered) primitives."""
    return {
        "primitive":  name,
        "backend":    "python",
        "svg":        svg,
        "natural_w":  w,
        "natural_h":  h,
    }


# Backwards-compatibility alias — old internal callers used ``_result``.
# Marks the result as python-backed for the same shape consumers expect.
def _result(svg: str, w: int, h: int, name: str) -> dict[str, Any]:
    return _native_result(svg, w, h, name)


def _mermaid_task(task: dict[str, Any]) -> dict[str, Any]:
    """Wrap a ``mermaid_codegen`` return into the public render-task shape."""
    return {
        "primitive":     task["primitive"],
        "backend":       "mermaid",
        "mermaid_code":  task["mermaid_code"],
        "hint_w":        task["hint_w"],
        "hint_h":        task["hint_h"],
    }


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

    Mermaid-backed (v0.3.0). Returns a render task — caller invokes the
    MCP tool ``validate_and_render_mermaid_diagram`` with
    ``result["mermaid_code"]`` to obtain SVG, then reads viewBox for
    ``natural_w`` / ``natural_h``.

    Args:
        steps:        list of {"title": str, "sub"?: str, "number"?: str}
                      (3-7 entries)
        orientation:  'horizontal' (default) or 'vertical'
        accent_alias: 'deep' | 'navy' | 'sky' | 'teal' (uniform colour)
        title:        optional top-of-canvas heading
        subtitle:     optional subheading under title
    """
    return _mermaid_task(mermaid_codegen.flow_diagram(
        steps,
        orientation=orientation,
        accent_alias=accent_alias,
        title=title,
        subtitle=subtitle,
    ))


# ===========================================================================
# 2. quadrant — exactly 4 cells in a 2x2 grid + optional bottom band
# ===========================================================================
def make_quadrant(
    cells: list[dict],
    *,
    title: str | None = None,
    footer: str | None = None,
) -> dict[str, Any]:
    """Exactly 4 cells in a 2x2 grid (Mermaid ``quadrantChart``).

    Mermaid-backed (v0.3.0). Each cell's ``items`` list packs into the
    quadrant label via ``<br/>``. For richer per-cell layout, fall back
    to the v0.2.x SVG primitive via git history.

    Args:
        cells:  list of 4 dicts: {"title": str, "accent": str (alias),
                                  "items": list[str], "point"?: str}
                Cell order: TL, TR, BL, BR (Mermaid Q2, Q1, Q3, Q4).
        title:  optional top heading
        footer: optional caption (echoed as a ``%% footer:`` comment)
    """
    return _mermaid_task(mermaid_codegen.quadrant(
        cells,
        title=title,
        footer=footer,
    ))


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

    Mermaid-backed (v0.3.0). Each layer becomes a flowchart node packed
    with ``label`` + ``items`` via ``<br/>``. ``kpi_band`` becomes a
    dotted-edge note attached to the last layer; ``side_annotations``
    become muted notes hanging off the side.

    Args:
        layers:           list of {"label": str, "items": list[str],
                                   "accent": str (alias),
                                   "filled"?: bool} (4-6 entries)
        side_annotations: optional list of {"text": str, "y": int (ignored)}
        kpi_band:         optional KPI string
        title:            optional heading
    """
    return _mermaid_task(mermaid_codegen.layered_stack(
        layers,
        side_annotations=side_annotations,
        kpi_band=kpi_band,
        title=title,
    ))


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

    Mermaid-backed (v0.3.0). Renders as a top-down flowchart with the
    parallel models inside a subgraph cluster.

    Args:
        input_label:  text for the top input node
        models:       list of {"name": str, "desc"?: str} (3-7 entries)
        fusion_label: text for the fusion node
        outputs:      list of {"label": str, "accent": str (alias)} (2-3)
        title:        optional heading
        subtitle:     optional subheading
    """
    return _mermaid_task(mermaid_codegen.fanout_pipeline(
        input_label,
        models,
        fusion_label,
        outputs,
        title=title,
        subtitle=subtitle,
    ))


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

    Mermaid-backed (v0.3.0). Each tier becomes a ``subgraph`` cluster
    containing its stages; ``fleet_box`` becomes a shared input node
    wired to the first stage of each lane. ``filled`` stages use the
    accent class; un-filled stages use the outline variant.

    Args:
        tiers:     list of {"label": str, "accent": str (alias),
                            "stages": list[{"title": str, "sub"?: str,
                                            "filled"?: bool}]} (2-3)
        fleet_box: optional input column {"label": str, "sub"?: str}
        header:    optional top caption (rendered as ``%% header:`` note)
        footer:    optional bottom caption (rendered as ``%% footer:`` note)
        title:     optional heading

    Open issue: Mermaid has no native swimlane primitive — subgraph
    workaround may look denser than v0.2.x. Fall back to git-history
    SVG version if visual quality is unacceptable.
    """
    return _mermaid_task(mermaid_codegen.hybrid_swimlane(
        tiers,
        fleet_box=fleet_box,
        header=header,
        footer=footer,
        title=title,
    ))


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
        "backend":      "mermaid",
        "hint_size":    "1180x280 (horizontal) / 1180x480 (vertical)",
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
        "backend":      "mermaid",
        "hint_size":    "1180x600",
        "good_for":     ["four-pillar platforms", "2x2 framework grids"],
        "params":       {
            "cells": "list[{title, accent, items[], point?}] (exactly 4, order TL/TR/BL/BR)",
            "title": "optional",
            "footer": "optional caption",
            "x_axis": "optional ('Low','High')",
            "y_axis": "optional ('Low','High')",
        },
    },
    "footprint_map": {
        "name":         "footprint_map",
        "backend":      "python",
        "natural_size": "1180x480",
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
        "backend":      "mermaid",
        "hint_size":    "1180x460",
        "good_for":     ["protocol layers", "FHIR/HealthLake stacks", "IoT gateways"],
        "params": {
            "layers": "list[{label, items[], accent, filled?}] (4-6)",
            "side_annotations": "optional list[{text}]",
            "kpi_band": "optional KPI string",
            "title": "optional",
        },
    },
    "fanout_pipeline": {
        "name":         "fanout_pipeline",
        "backend":      "mermaid",
        "hint_size":    "1180x600",
        "good_for":     ["multi-model CV pipelines", "ensemble verification"],
        "params": {
            "input_label": "str",
            "models": "list[{name, desc?}] (3-7)",
            "fusion_label": "str",
            "outputs": "list[{label, accent}] (2-3)",
            "title": "optional",
            "subtitle": "optional",
        },
    },
    "hybrid_swimlane": {
        "name":         "hybrid_swimlane",
        "backend":      "mermaid",
        "hint_size":    "1180x480",
        "good_for":     ["security+retail dual stack", "edge+server split"],
        "params": {
            "tiers": "list[{label, accent, stages[]}] (2-3)",
            "fleet_box": "optional input column",
            "header": "optional top caption",
            "footer": "optional bottom caption",
            "title": "optional",
        },
    },
    "data_path": {
        "name":         "data_path",
        "backend":      "python",
        "natural_size": "1180x280",
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


def backend_for(name: str) -> str:
    """Return ``"mermaid"`` or ``"python"`` for a primitive name.

    Lets the caller decide whether to invoke an MCP render step after
    calling ``make_<primitive>`` (mermaid) or to consume the returned
    SVG directly (python). Raises ``ValueError`` for unknown names.
    """
    if name in MERMAID_BACKED:
        return "mermaid"
    if name in PYTHON_BACKED:
        return "python"
    raise ValueError(
        f"unknown primitive {name!r}; valid: {list(_PRIMITIVES.keys())}"
    )


def call(name: str, **kwargs) -> dict[str, Any]:
    """Dispatcher — call a primitive by name with kwargs."""
    if name not in _PRIMITIVES:
        raise ValueError(
            f"unknown primitive {name!r}; valid: {list(_PRIMITIVES.keys())}"
        )
    return _PRIMITIVES[name](**kwargs)


__all__ = [
    "VERSION",
    "MERMAID_BACKED",
    "PYTHON_BACKED",
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
    "backend_for",
    "call",
]
