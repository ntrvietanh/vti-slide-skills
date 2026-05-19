"""Codegen for the 5 Mermaid-backed primitives.

Each function takes the same kwargs as its sibling ``make_<primitive>``
function in ``diagram_builder.py`` and returns the **Mermaid source
string** (prepended with the VTI theme init directive). It does **not**
render — rendering happens agent-side via the Mermaid Chart MCP
``validate_and_render_mermaid_diagram`` tool. The agent saves the
returned SVG to ``work/diagrams/<slide_id>.svg`` and reads the viewBox
to recover ``natural_w`` / ``natural_h``.

Brand discipline (v0.4.0)
-------------------------
**Round-edge node shape** — every node uses Mermaid's ``(label)``
round-rectangle form, not the legacy ``[label]`` square form. **Blue-mono
gradient** — node fill is index-driven (pale → navy via ``:::stepN``
classes). The legacy ``accent_alias`` / per-element ``accent`` keyword
arguments are deprecated; they're accepted for back-compat but ignored
with a one-time warning.

Hint dimensions
---------------
Each function also returns a ``hint_w`` / ``hint_h`` pair used as a
sanity-check expected aspect ratio. After Mermaid renders, the caller
compares the actual viewBox to the hint and warns if they diverge more
than 25 %% (a sign the descriptor and the resulting diagram disagree).

Captions
--------
Each function accepts an optional ``captions: list[str] | None`` that is
**not** rendered into the Mermaid source — it is passed through in the
return dict for the host page-builder to render as a small text strip
below the SVG (one caption per main node, parallel index).

Public surface
--------------
- ``flow_diagram(steps, orientation, title, subtitle, captions)``
- ``quadrant(cells, title, footer, captions)``
- ``layered_stack(layers, side_annotations, kpi_band, title, captions)``
- ``fanout_pipeline(input_label, models, fusion_label, outputs, title, captions)``
- ``hybrid_swimlane(tiers, fleet_box, header, footer, title, captions)``

All return ``{"mermaid_code": str, "primitive": str, "hint_w": int,
"hint_h": int, "captions": list[str]}``.

Backend
-------
Mermaid Chart MCP tool name (for the agent):
``mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram``
"""
from __future__ import annotations

import re
import warnings
from typing import Any

from theme_bridge import (
    init_directive,
    init_directive_quadrant,
    gradient_classdefs,
)
from tokens_bridge import token

# Canonical width — kept aligned with the native primitives in
# svg_primitives.CANVAS_W so layouts stay predictable. Heights are
# primitive-specific and tracked as ``hint_h``.
HINT_W = 1180


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_NODE_ID_RE = re.compile(r"[^A-Za-z0-9_]+")


def _warn_accent_deprecated(field: str, value: Any) -> None:
    """Emit a one-time DeprecationWarning when callers pass per-element accent."""
    warnings.warn(
        f"diagram-builder v0.4.0: per-element {field}={value!r} is ignored; "
        f"node colour is index-driven (blue-mono gradient). Drop the kwarg "
        f"from your call site.",
        DeprecationWarning,
        stacklevel=3,
    )


def _node_id(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def _escape(text: str) -> str:
    """Mermaid label-safe escape.

    Mermaid node labels accept most characters but interior double-quotes
    break the parser. Replace ``"`` with ``’`` and convert newlines to
    Mermaid's ``<br/>`` separator.
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


def _round_node(nid: str, label: str, cls: str | None = None) -> str:
    """Emit a round-edge node line: ``  nid("label"):::cls``.

    Round-rectangle is Mermaid's ``(label)`` shape (mild corner radius).
    Class definitions are emitted separately at the end of each diagram.
    """
    suffix = f":::{cls}" if cls else ""
    return f'  {nid}("{label}"){suffix}'


def _meta_classdef() -> str:
    """Neutral muted class for auxiliary nodes (kpi band, side notes, fleet).

    Stays inside the brand neutrals so it never competes with the blue
    gradient used by the main step nodes.
    """
    return (
        f"classDef meta fill:{token('vti-white')},"
        f"stroke:{token('vti-border')},"
        f"color:{token('vti-ink-soft')},"
        "stroke-width:1.5px,stroke-dasharray:4 3,rx:12,ry:12;"
    )


def _result(
    code: str,
    primitive: str,
    hint_h: int,
    captions: list[str] | None,
) -> dict[str, Any]:
    return {
        "mermaid_code": code,
        "primitive":    primitive,
        "hint_w":       HINT_W,
        "hint_h":       hint_h,
        "captions":     list(captions) if captions else [],
    }


# ---------------------------------------------------------------------------
# 1. flow_diagram — sequence of 3-7 boxes + arrows
# ---------------------------------------------------------------------------
def flow_diagram(
    steps: list[dict],
    *,
    orientation: str = "horizontal",
    accent_alias: str | None = None,  # deprecated, ignored
    title: str | None = None,
    subtitle: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    if not 3 <= len(steps) <= 7:
        raise ValueError(f"flow_diagram needs 3-7 steps, got {len(steps)}")
    if orientation not in ("horizontal", "vertical"):
        raise ValueError("orientation must be 'horizontal' or 'vertical'")
    if accent_alias is not None:
        _warn_accent_deprecated("accent_alias", accent_alias)

    direction = "LR" if orientation == "horizontal" else "TB"
    hint_h = 280 if orientation == "horizontal" else 480

    lines: list[str] = [init_directive(), f"flowchart {direction}"]

    if title:
        lines.append(f"%% title: {_escape(title)}")
    if subtitle:
        lines.append(f"%% subtitle: {_escape(subtitle)}")

    # Define nodes — round shape, per-index gradient class.
    for i, step in enumerate(steps):
        nid = _node_id("S", i)
        label = _two_line(step.get("title", f"Step {i + 1}"), step.get("sub"))
        number = step.get("number")
        if number:
            label = f"<b>{_escape(number)}</b> · {label}"
        lines.append(_round_node(nid, label, cls=f"step{i}"))

    # Edges
    for i in range(len(steps) - 1):
        lines.append(f"  {_node_id('S', i)} --> {_node_id('S', i + 1)}")

    # Class definitions — gradient sampled across the step count.
    lines.append("")
    lines.extend(gradient_classdefs(len(steps)))

    return _result(
        "\n".join(lines), "flow_diagram", hint_h, captions,
    )


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
    captions: list[str] | None = None,
) -> dict[str, Any]:
    """Render as Mermaid ``quadrantChart``.

    Mermaid ``quadrantChart`` does not expose node shape config, so cells
    remain rectangular (no rounded corners) at v0.4.0. Cell fills come
    from theme variables which already sit inside the VTI blue family —
    no per-cell accent needed.
    """
    if len(cells) != 4:
        raise ValueError(f"quadrant needs exactly 4 cells, got {len(cells)}")
    # Per-cell `accent` is silently ignored from v0.4.0 — note via warning
    # only when actually present so quiet callers stay quiet.
    for c in cells:
        if c.get("accent"):
            _warn_accent_deprecated("cells[].accent", c.get("accent"))
            break

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
        coords = [(0.25, 0.75), (0.75, 0.75), (0.25, 0.25), (0.75, 0.25)][i]
        lines.append(f'  "{_escape(pt)}": [{coords[0]:.2f}, {coords[1]:.2f}]')

    if footer:
        lines.append(f"%% footer: {_escape(footer)}")

    return _result("\n".join(lines), "quadrant", hint_h, captions)


# ---------------------------------------------------------------------------
# 3. layered_stack — 4-6 cards left-to-right
# ---------------------------------------------------------------------------
def layered_stack(
    layers: list[dict],
    *,
    side_annotations: list[dict] | None = None,
    kpi_band: str | None = None,
    title: str | None = None,
    captions: list[str] | None = None,
) -> dict[str, Any]:
    if not 4 <= len(layers) <= 6:
        raise ValueError(f"layered_stack needs 4-6 layers, got {len(layers)}")

    hint_h = 460
    lines: list[str] = [init_directive(), "flowchart LR"]
    if title:
        lines.append(f"%% title: {_escape(title)}")

    # Main layer nodes — round, gradient-coloured by index.
    used_meta = False
    for i, layer in enumerate(layers):
        if layer.get("accent"):
            _warn_accent_deprecated("layers[].accent", layer.get("accent"))
        nid = _node_id("L", i)
        label_top = layer.get("label", f"Layer {i + 1}")
        items = layer.get("items") or []
        joined = "<br/>".join(_escape(it) for it in items[:6])
        label = f"<b>{_escape(label_top)}</b>"
        if joined:
            label += f"<br/>{joined}"
        lines.append(_round_node(nid, label, cls=f"step{i}"))

    for i in range(len(layers) - 1):
        lines.append(f"  {_node_id('L', i)} --> {_node_id('L', i + 1)}")

    if kpi_band:
        lines.append(_round_node("KPI", f"<b>{_escape(kpi_band)}</b>", cls="meta"))
        lines.append(f"  {_node_id('L', len(layers) - 1)} -.-> KPI")
        used_meta = True

    if side_annotations:
        for j, note in enumerate(side_annotations[:4]):
            nid = f"A{j}"
            lines.append(
                _round_node(nid, _escape(note.get("text", "")), cls="meta")
            )
            used_meta = True

    lines.append("")
    lines.extend(gradient_classdefs(len(layers)))
    if used_meta:
        lines.append(_meta_classdef())

    return _result("\n".join(lines), "layered_stack", hint_h, captions)


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
    captions: list[str] | None = None,
) -> dict[str, Any]:
    if not 3 <= len(models) <= 7:
        raise ValueError(f"fanout_pipeline needs 3-7 models, got {len(models)}")
    if not 2 <= len(outputs) <= 3:
        raise ValueError(
            f"fanout_pipeline needs 2-3 outputs, got {len(outputs)}"
        )
    # Outputs[i].accent silently ignored from v0.4.0.
    for o in outputs:
        if o.get("accent"):
            _warn_accent_deprecated("outputs[].accent", o.get("accent"))
            break

    hint_h = 600
    lines: list[str] = [init_directive(), "flowchart TB"]
    if title:
        lines.append(f"%% title: {_escape(title)}")
    if subtitle:
        lines.append(f"%% subtitle: {_escape(subtitle)}")

    # 4-tier vertical gradient: IN → models → FUSE → outputs.
    # Use indices 0/1/2/3 mapped against a 4-step gradient sample.
    lines.append(_round_node("IN", f"<b>{_escape(input_label)}</b>", cls="step0"))
    lines.append("  subgraph PARALLEL [Parallel models]")
    for i, model in enumerate(models):
        nid = _node_id("M", i)
        label = _two_line(model.get("name", f"Model {i + 1}"), model.get("desc"))
        lines.append(_round_node(nid, label, cls="step1"))
    lines.append("  end")
    lines.append(_round_node("FUSE", f"<b>{_escape(fusion_label)}</b>", cls="step2"))

    for i in range(len(models)):
        lines.append(f"  IN --> {_node_id('M', i)}")
        lines.append(f"  {_node_id('M', i)} --> FUSE")

    for j, out in enumerate(outputs):
        nid = _node_id("O", j)
        lines.append(_round_node(nid, f"<b>{_escape(out.get('label', ''))}</b>", cls="step3"))
        lines.append(f"  FUSE --> {nid}")

    lines.append("")
    lines.extend(gradient_classdefs(4))

    return _result("\n".join(lines), "fanout_pipeline", hint_h, captions)


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
    captions: list[str] | None = None,
) -> dict[str, Any]:
    if not 2 <= len(tiers) <= 3:
        raise ValueError(f"hybrid_swimlane needs 2-3 tiers, got {len(tiers)}")

    hint_h = 480
    lines: list[str] = [init_directive(), "flowchart LR"]
    if title:
        lines.append(f"%% title: {_escape(title)}")
    if header:
        lines.append(f"%% header: {_escape(header)}")

    used_meta = False
    if fleet_box:
        flabel = _two_line(fleet_box.get("label", "Input"), fleet_box.get("sub"))
        lines.append(_round_node("FLEET", flabel, cls="meta"))
        used_meta = True

    max_stages = 0
    for ti, tier in enumerate(tiers):
        if tier.get("accent"):
            _warn_accent_deprecated("tiers[].accent", tier.get("accent"))
        tier_id = f"T{ti}"
        tier_label = tier.get("label", f"Tier {ti + 1}")
        lines.append(f"  subgraph {tier_id} [{_escape(tier_label)}]")
        lines.append(f"    direction LR")

        stages = tier.get("stages") or []
        max_stages = max(max_stages, len(stages))
        last_node = None
        for si, stage in enumerate(stages):
            nid = f"{tier_id}_S{si}"
            label = _two_line(stage.get("title", f"Stage {si + 1}"), stage.get("sub"))
            # Stage index drives the gradient across all lanes.
            lines.append(_round_node(nid, label, cls=f"step{si}"))
            if last_node is not None:
                lines.append(f"    {last_node} --> {nid}")
            last_node = nid
        lines.append("  end")

        if fleet_box and stages:
            lines.append(f"  FLEET --> {tier_id}_S0")

    if footer:
        lines.append(f"%% footer: {_escape(footer)}")

    lines.append("")
    lines.extend(gradient_classdefs(max(1, max_stages)))
    if used_meta:
        lines.append(_meta_classdef())

    return _result("\n".join(lines), "hybrid_swimlane", hint_h, captions)


__all__ = [
    "flow_diagram",
    "quadrant",
    "layered_stack",
    "fanout_pipeline",
    "hybrid_swimlane",
    "HINT_W",
]
