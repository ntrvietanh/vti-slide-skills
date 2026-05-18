"""Codegen for the 5 Mermaid-backed primitives.

Each function takes the same kwargs as its sibling ``make_<primitive>``
function in ``diagram_builder.py`` and returns the **Mermaid source
string** (prepended with the VTI theme init directive). It does **not**
render — rendering happens agent-side via the Mermaid Chart MCP
``validate_and_render_mermaid_diagram`` tool. The agent saves the
returned SVG to ``work/diagrams/<slide_id>.svg`` and reads the viewBox
to recover ``natural_w`` / ``natural_h``.

Hint dimensions
---------------
Each function also returns a ``hint_w`` / ``hint_h`` pair used as a
sanity-check expected aspect ratio. After Mermaid renders, the caller
compares the actual viewBox to the hint and warns if they diverge more
than 25 %% (a sign the descriptor and the resulting diagram disagree).

Public surface
--------------
- ``flow_diagram(steps, orientation, accent_alias, title, subtitle)``
- ``quadrant(cells, title, footer)``
- ``layered_stack(layers, side_annotations, kpi_band, title)``
- ``fanout_pipeline(input_label, models, fusion_label, outputs, title)``
- ``hybrid_swimlane(tiers, fleet_box, header, footer, title)``

All return ``{"mermaid_code": str, "primitive": str, "hint_w": int,
"hint_h": int}``.

Backend
-------
Mermaid Chart MCP tool name (for the agent):
``mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram``
"""
from __future__ import annotations

import re
from typing import Any

from theme_bridge import init_directive, init_directive_quadrant
from tokens_bridge import ACCENT_TO_TOKEN, accent

# Canonical width — kept aligned with the native primitives in
# svg_primitives.CANVAS_W so layouts stay predictable. Heights are
# primitive-specific and tracked as ``hint_h``.
HINT_W = 1180


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_NODE_ID_RE = re.compile(r"[^A-Za-z0-9_]+")


def _node_id(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def _escape(text: str) -> str:
    """Mermaid label-safe escape.

    Mermaid node labels in ``[" ... "]`` form accept most characters but
    interior double-quotes break the parser. Replace ``"`` with `’` and
    strip newlines (Mermaid uses ``<br/>`` for line breaks inside
    quoted labels).
    """
    if text is None:
        return ""
    s = str(text).replace('"', "’")
    return s.replace("\n", "<br/>").replace("\r", "")


def _two_line(title: str, sub: str | None) -> str:
    """Produce a two-line node label using Mermaid's ``<br/>`` separator."""
    if sub:
        return f"<b>{_escape(title)}</b><br/>{_escape(sub)}"
    return f"<b>{_escape(title)}</b>"


def _classdef(name: str, fill_alias: str, stroke_alias: str,
              color_alias: str = "white") -> str:
    """Emit a ``classDef`` line referencing tokens (no hex literals)."""
    return (
        f"classDef {name} fill:{accent(fill_alias)},"
        f"stroke:{accent(stroke_alias)},"
        f"color:{accent(color_alias)},"
        "stroke-width:2px;"
    )


def _result(code: str, primitive: str, hint_h: int) -> dict[str, Any]:
    return {
        "mermaid_code":  code,
        "primitive":     primitive,
        "hint_w":        HINT_W,
        "hint_h":        hint_h,
    }


# ---------------------------------------------------------------------------
# 1. flow_diagram — sequence of 3-7 boxes + arrows
# ---------------------------------------------------------------------------
def flow_diagram(
    steps: list[dict],
    *,
    orientation: str = "horizontal",
    accent_alias: str = "deep",
    title: str | None = None,
    subtitle: str | None = None,
) -> dict[str, Any]:
    if not 3 <= len(steps) <= 7:
        raise ValueError(f"flow_diagram needs 3-7 steps, got {len(steps)}")
    if orientation not in ("horizontal", "vertical"):
        raise ValueError("orientation must be 'horizontal' or 'vertical'")
    if accent_alias not in ACCENT_TO_TOKEN:
        accent_alias = "deep"

    direction = "LR" if orientation == "horizontal" else "TB"
    hint_h = 280 if orientation == "horizontal" else 480

    lines: list[str] = [init_directive(), f"flowchart {direction}"]

    if title:
        # Use the title as the first comment line — Mermaid does not have
        # a chart-level title for flowchart, so we surface it in the
        # diagram_spec descriptor (still kept on the SlideContentPlan).
        lines.append(f"%% title: {_escape(title)}")
    if subtitle:
        lines.append(f"%% subtitle: {_escape(subtitle)}")

    # Define nodes
    for i, step in enumerate(steps):
        nid = _node_id("S", i)
        label = _two_line(step.get("title", f"Step {i + 1}"),
                          step.get("sub"))
        number = step.get("number")
        if number:
            label = f"<b>{_escape(number)}</b> · {label}"
        lines.append(f'  {nid}["{label}"]:::flowAccent')

    # Edges
    for i in range(len(steps) - 1):
        lines.append(f"  {_node_id('S', i)} --> {_node_id('S', i + 1)}")

    # Class definition (one accent for the whole flow)
    lines.append("")
    lines.append(_classdef("flowAccent", accent_alias, "navy"))

    return _result("\n".join(lines), "flow_diagram", hint_h)


# ---------------------------------------------------------------------------
# 2. quadrant — 2x2 grid using Mermaid native quadrantChart
# ---------------------------------------------------------------------------
def quadrant(
    cells: list[dict],
    *,
    title: str | None = None,
    footer: str | None = None,
    x_axis: tuple[str, str] | None = None,
    y_axis: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Render as Mermaid ``quadrantChart``.

    Caller passes the same 4-cell shape used by ``make_quadrant``; we
    map each cell to one quadrant label and (optionally) plot one data
    point at the quadrant centroid so the items list shows up.

    Note: Mermaid ``quadrantChart`` does not natively support per-cell
    bulleted item lists. We pack each cell's items into the quadrant
    label using ``<br/>`` separators. If a deck needs richer per-cell
    layout, fall back to native Python ``make_quadrant``.
    """
    if len(cells) != 4:
        raise ValueError(f"quadrant needs exactly 4 cells, got {len(cells)}")

    hint_h = 600
    lines: list[str] = [init_directive_quadrant(), "quadrantChart"]
    lines.append(f"  title {_escape(title or 'Quadrant')}")

    # Axes — default to anonymous "Low → High" if caller didn't provide
    xl, xr = x_axis or ("Low", "High")
    yb, yt = y_axis or ("Low", "High")
    lines.append(f"  x-axis {_escape(xl)} --> {_escape(xr)}")
    lines.append(f"  y-axis {_escape(yb)} --> {_escape(yt)}")

    # Mermaid quadrant order: Q1 top-right, Q2 top-left, Q3 bottom-left,
    # Q4 bottom-right. Our caller passes cells in reading order
    # (TL, TR, BL, BR) — re-order to Mermaid's expectation.
    tl, tr, bl, br = cells[0], cells[1], cells[2], cells[3]
    order_map = [
        ("quadrant-1", tr),
        ("quadrant-2", tl),
        ("quadrant-3", bl),
        ("quadrant-4", br),
    ]
    for slot, cell in order_map:
        head = cell.get("title", "")
        items = cell.get("items") or []
        joined = "<br/>".join(_escape(it) for it in items[:5])
        label = f"<b>{_escape(head)}</b>"
        if joined:
            label += f"<br/>{joined}"
        lines.append(f'  {slot} "{label}"')

    # Plot the four corners as data points so caller can attach short
    # labels via cells[i]["point"] (optional).
    for i, cell in enumerate(cells):
        pt = cell.get("point")
        if not pt:
            continue
        # Centroid of each quadrant in [0..1] coords
        coords = [(0.25, 0.75), (0.75, 0.75), (0.25, 0.25), (0.75, 0.25)][i]
        lines.append(f'  "{_escape(pt)}": [{coords[0]:.2f}, {coords[1]:.2f}]')

    if footer:
        lines.append(f"%% footer: {_escape(footer)}")

    return _result("\n".join(lines), "quadrant", hint_h)


# ---------------------------------------------------------------------------
# 3. layered_stack — 4-6 cards left-to-right
# ---------------------------------------------------------------------------
def layered_stack(
    layers: list[dict],
    *,
    side_annotations: list[dict] | None = None,
    kpi_band: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    if not 4 <= len(layers) <= 6:
        raise ValueError(f"layered_stack needs 4-6 layers, got {len(layers)}")

    hint_h = 460
    lines: list[str] = [init_directive(), "flowchart LR"]
    if title:
        lines.append(f"%% title: {_escape(title)}")

    accents_used: set[str] = set()
    for i, layer in enumerate(layers):
        nid = _node_id("L", i)
        label_top = layer.get("label", f"Layer {i + 1}")
        items = layer.get("items") or []
        joined = "<br/>".join(_escape(it) for it in items[:6])
        label = f"<b>{_escape(label_top)}</b>"
        if joined:
            label += f"<br/>{joined}"
        accent_name = layer.get("accent", "deep")
        if accent_name not in ACCENT_TO_TOKEN:
            accent_name = "deep"
        accents_used.add(accent_name)
        lines.append(f'  {nid}["{label}"]:::a_{accent_name}')

    for i in range(len(layers) - 1):
        lines.append(f"  {_node_id('L', i)} --> {_node_id('L', i + 1)}")

    if kpi_band:
        lines.append(f'  KPI["{_escape(kpi_band)}"]:::a_ink')
        # Wire KPI under the last layer as a sibling note
        lines.append(f"  {_node_id('L', len(layers) - 1)} -.-> KPI")
        accents_used.add("ink")

    if side_annotations:
        for j, note in enumerate(side_annotations[:4]):
            nid = f"A{j}"
            lines.append(f'  {nid}["{_escape(note.get("text", ""))}"]:::a_muted')
            accents_used.add("muted")

    lines.append("")
    for alias in accents_used:
        lines.append(_classdef(f"a_{alias}", alias, "navy"))

    return _result("\n".join(lines), "layered_stack", hint_h)


# ---------------------------------------------------------------------------
# 4. fanout_pipeline — input → N parallel models → fusion → outputs
# ---------------------------------------------------------------------------
def fanout_pipeline(
    input_label: str,
    models: list[dict],
    fusion_label: str,
    outputs: list[dict],
    *,
    title: str | None = None,
    subtitle: str | None = None,
) -> dict[str, Any]:
    if not 3 <= len(models) <= 7:
        raise ValueError(f"fanout_pipeline needs 3-7 models, got {len(models)}")
    if not 2 <= len(outputs) <= 3:
        raise ValueError(
            f"fanout_pipeline needs 2-3 outputs, got {len(outputs)}"
        )

    hint_h = 600
    lines: list[str] = [init_directive(), "flowchart TB"]
    if title:
        lines.append(f"%% title: {_escape(title)}")
    if subtitle:
        lines.append(f"%% subtitle: {_escape(subtitle)}")

    lines.append(f'  IN["<b>{_escape(input_label)}</b>"]:::a_deep')
    lines.append("  subgraph PARALLEL [Parallel models]")
    for i, model in enumerate(models):
        nid = _node_id("M", i)
        label = _two_line(model.get("name", f"Model {i + 1}"),
                          model.get("desc"))
        lines.append(f'    {nid}["{label}"]:::a_blue')
    lines.append("  end")
    lines.append(f'  FUSE["<b>{_escape(fusion_label)}</b>"]:::a_navy')

    for i in range(len(models)):
        lines.append(f"  IN --> {_node_id('M', i)}")
        lines.append(f"  {_node_id('M', i)} --> FUSE")

    accents_used = {"deep", "blue", "navy"}
    for j, out in enumerate(outputs):
        nid = _node_id("O", j)
        accent_name = out.get("accent", "teal")
        if accent_name not in ACCENT_TO_TOKEN:
            accent_name = "teal"
        accents_used.add(accent_name)
        lines.append(
            f'  {nid}["<b>{_escape(out.get("label", ""))}</b>"]'
            f":::a_{accent_name}"
        )
        lines.append(f"  FUSE --> {nid}")

    lines.append("")
    for alias in accents_used:
        lines.append(_classdef(f"a_{alias}", alias, "navy"))

    return _result("\n".join(lines), "fanout_pipeline", hint_h)


# ---------------------------------------------------------------------------
# 5. hybrid_swimlane — 2+ horizontal lanes sharing one input column
# ---------------------------------------------------------------------------
def hybrid_swimlane(
    tiers: list[dict],
    *,
    fleet_box: dict | None = None,
    header: str | None = None,
    footer: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    if not 2 <= len(tiers) <= 3:
        raise ValueError(f"hybrid_swimlane needs 2-3 tiers, got {len(tiers)}")

    hint_h = 480
    lines: list[str] = [init_directive(), "flowchart LR"]
    if title:
        lines.append(f"%% title: {_escape(title)}")
    if header:
        lines.append(f"%% header: {_escape(header)}")

    accents_used: set[str] = set()

    # Shared fleet column on the left, if any
    if fleet_box:
        flabel = _two_line(fleet_box.get("label", "Input"),
                           fleet_box.get("sub"))
        lines.append(f'  FLEET["{flabel}"]:::a_ink')
        accents_used.add("ink")

    for ti, tier in enumerate(tiers):
        tier_id = f"T{ti}"
        tier_label = tier.get("label", f"Tier {ti + 1}")
        accent_name = tier.get("accent", "deep")
        if accent_name not in ACCENT_TO_TOKEN:
            accent_name = "deep"
        accents_used.add(accent_name)

        lines.append(f"  subgraph {tier_id} [{_escape(tier_label)}]")
        lines.append(f"    direction LR")

        stages = tier.get("stages") or []
        last_node = None
        for si, stage in enumerate(stages):
            nid = f"{tier_id}_S{si}"
            label = _two_line(stage.get("title", f"Stage {si + 1}"),
                              stage.get("sub"))
            cls = f"a_{accent_name}" if stage.get("filled") else f"a_{accent_name}_outline"
            lines.append(f'    {nid}["{label}"]:::{cls}')
            if last_node is not None:
                lines.append(f"    {last_node} --> {nid}")
            last_node = nid
        lines.append("  end")

        if fleet_box and stages:
            lines.append(f"  FLEET --> {tier_id}_S0")

    if footer:
        lines.append(f"%% footer: {_escape(footer)}")

    # Emit both filled and outline classDef variants
    lines.append("")
    for alias in accents_used:
        lines.append(_classdef(f"a_{alias}", alias, "navy"))
        # Outline variant — same stroke, white-fill, accent-text
        lines.append(
            f"classDef a_{alias}_outline fill:{accent('white')},"
            f"stroke:{accent(alias)},color:{accent(alias)},"
            "stroke-width:2px;"
        )

    return _result("\n".join(lines), "hybrid_swimlane", hint_h)


__all__ = [
    "flow_diagram",
    "quadrant",
    "layered_stack",
    "fanout_pipeline",
    "hybrid_swimlane",
    "HINT_W",
]
