"""Public API — 7 standardised diagram primitives for VTI slide decks.

v0.5.0 restores the native-SVG rendering branch alongside the v0.3.0
Mermaid branch. Five of the seven primitives now have **two backends**:

- ``backend="svg"`` (default, restored from v0.1.0):
  ``flow_diagram``, ``quadrant``, ``layered_stack``,
  ``fanout_pipeline``, ``hybrid_swimlane``. Renders natively to a single
  ``<svg>`` element with predictable dimensions (canonical canvas
  1180×280/480 plus optional caption strip). No MCP call needed.

- ``backend="mermaid"`` (opt-in for the same 5 primitives): returns a
  Mermaid render task — agent renders via
  ``mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram``,
  saves the returned SVG, reads the actual viewBox.

The remaining two primitives (``footprint_map``, ``data_path``) are
always Python-rendered and ignore the ``backend`` kwarg.

Return shapes::

    # backend == "svg" (native Python SVG)
    {
        "primitive":     str,
        "backend":       "svg",
        "svg":           str,    # complete <svg> element
        "natural_w":     int,
        "natural_h":     int,
        "captions":      list[str],
    }

    # backend == "mermaid" (render task — caller invokes MCP)
    {
        "primitive":     str,
        "backend":       "mermaid",
        "mermaid_code":  str,
        "hint_w":        int,
        "hint_h":        int,
        "captions":      list[str],
    }

    # python-only primitives (footprint_map, data_path)
    {
        "primitive":     str,
        "backend":       "python",
        "svg":           str,
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

import os
import re
from typing import Any

import mermaid_codegen
import svg_render
from svg_primitives import (
    CANVAS_W, CANVAS_H_WIDE, CANVAS_H_TALL,
    STROKE_NORMAL,
    svg_open, svg_close,
    svg_title_label, svg_text,
    svg_box, svg_box_filled,
    svg_connector_horizontal,
    even_split_x,
)
from tokens_bridge import accent, token

VERSION = "0.7.0"

# Default backend for the 5 dual-backend primitives. Can be overridden
# per-call (kwarg ``backend=``) or globally via env var
# ``VTI_DIAGRAM_BACKEND`` (values: ``"svg"`` or ``"mermaid"``).
_DEFAULT_DUAL_BACKEND = os.environ.get("VTI_DIAGRAM_BACKEND", "svg").lower()
if _DEFAULT_DUAL_BACKEND not in ("svg", "mermaid"):
    _DEFAULT_DUAL_BACKEND = "svg"


def _resolve_backend(backend: str | None) -> str:
    """Pick a backend for the dual-backend primitives.

    Precedence: explicit kwarg → env default → ``"svg"``.
    """
    if backend is None:
        return _DEFAULT_DUAL_BACKEND
    backend = backend.lower()
    if backend not in ("svg", "mermaid"):
        raise ValueError(
            f"backend must be 'svg' or 'mermaid', got {backend!r}"
        )
    return backend


# ---------------------------------------------------------------------------
# Content discipline (v0.4.0)
# ---------------------------------------------------------------------------
# Node labels in Mermaid-backed primitives must be pure action/state
# names. Quantitative or temporal tokens belong in the parallel
# ``captions`` array, which the page-builder renders as a small text
# strip below the diagram. The regex below flags the most common
# offenders so authoring agents fail fast instead of producing the
# noisy "step + metrics" boxes that motivated v0.4.0.
_METRIC_PATTERN = re.compile(
    r"""(
        \d+\s*\+                                       # 180+ , 200+
      | ~\s*\d+                                        # ~20  , ~15
      | \d+\s*[:.]\s*\d+                               # 08:00, 1.5
      | \d+\s*(?:%|x|×)                                # 5% , 2x , 3×
      | \d+\s*(?:spaces?|threads?|hours?|hrs?|hr
                |min|mins?|minutes?
                |sec|secs?|seconds?|ms
                |days?|weeks?|months?|years?
                |GB|MB|KB|TB
                |reqs?|calls?|writes?|reads?)
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def _assert_step_clean(value: Any, *, field: str = "label") -> None:
    """Raise if ``value`` contains a metric token.

    Applied to every node-rendered string in the 5 Mermaid primitives
    (``title``, ``sub``, ``label``, ``items[]``, ``name``, ``desc``,
    ``input_label``, ``fusion_label``). Lists are walked recursively.
    ``None`` and non-string scalars are skipped.
    """
    if value is None:
        return
    if isinstance(value, (list, tuple)):
        for it in value:
            _assert_step_clean(it, field=field)
        return
    s = str(value)
    m = _METRIC_PATTERN.search(s)
    if m:
        raise ValueError(
            f"diagram-builder v0.4.0: {field}={s!r} contains metric "
            f"token {m.group(0)!r}. Node labels must be pure action/state "
            f"names (1-3 words). Move quantitative content to the "
            f"`captions=[...]` keyword — the page-builder renders it as "
            f"a small strip below the diagram."
        )

# Primitives that support BOTH the native-SVG and Mermaid backends (the
# caller picks at call time via the ``backend`` kwarg).
DUAL_BACKEND: frozenset[str] = frozenset({
    "flow_diagram",
    "quadrant",
    "layered_stack",
    "fanout_pipeline",
    "hybrid_swimlane",
})

# Back-compat alias — older callers used ``MERMAID_BACKED`` to mean
# "these primitives need the MCP render step". With v0.5.0 they only
# need MCP when ``backend="mermaid"`` is requested, but the membership
# of the set is the same.
MERMAID_BACKED: frozenset[str] = DUAL_BACKEND

# Primitives that are always Python-rendered (no Mermaid equivalent
# exists for these — footprint_map has no Mermaid geo-map, data_path's
# cloud-as-brain styling isn't expressible in Mermaid cleanly).
PYTHON_BACKED: frozenset[str] = frozenset({
    "footprint_map",
    "data_path",
    "cycle",
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
        "captions":      task.get("captions") or [],
    }


# ===========================================================================
# 1. flow_diagram — horizontal sequence of 3-7 boxes + chevron arrows
# ===========================================================================
def make_flow_diagram(
    steps: list[dict],
    *,
    orientation: str = "horizontal",
    accent_alias: str | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    captions: list[str] | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    """Sequential flow of 3-7 boxes connected by arrows.

    Dual-backend (v0.5.0). ``backend="svg"`` (default) renders natively
    via ``svg_render.flow_diagram``; ``backend="mermaid"`` returns a
    Mermaid render task.

    Content discipline (v0.4.0): ``title``/``sub`` must be action/state
    names only — no metrics, no times, no cardinalities. Move
    quantitative info to ``captions`` (one entry per step).
    """
    for s in steps:
        _assert_step_clean(s.get("title"), field="steps[].title")
        _assert_step_clean(s.get("sub"),   field="steps[].sub")
    if _resolve_backend(backend) == "svg":
        return svg_render.flow_diagram(
            steps,
            orientation=orientation,
            accent_alias=accent_alias,
            title=title,
            subtitle=subtitle,
            captions=captions,
        )
    return _mermaid_task(mermaid_codegen.flow_diagram(
        steps,
        orientation=orientation,
        accent_alias=accent_alias,
        title=title,
        subtitle=subtitle,
        captions=captions,
    ))


# ===========================================================================
# 2. quadrant — exactly 4 cells in a 2x2 grid + optional bottom band
# ===========================================================================
def make_quadrant(
    cells: list[dict],
    *,
    title: str | None = None,
    footer: str | None = None,
    captions: list[str] | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    """Exactly 4 cells in a 2x2 grid.

    Dual-backend (v0.5.0). ``backend="svg"`` (default) renders v0.1.0
    style hand-laid 2×2 grid; ``backend="mermaid"`` uses Mermaid
    ``quadrantChart``.

    Content discipline (v0.4.0): cell ``title`` and ``items`` must be
    action/state names only; metrics → ``captions``.
    """
    for c in cells:
        _assert_step_clean(c.get("title"), field="cells[].title")
        _assert_step_clean(c.get("items"), field="cells[].items")
    if _resolve_backend(backend) == "svg":
        return svg_render.quadrant(
            cells,
            title=title,
            footer=footer,
            captions=captions,
        )
    return _mermaid_task(mermaid_codegen.quadrant(
        cells,
        title=title,
        footer=footer,
        captions=captions,
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
    captions: list[str] | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    """Left-to-right horizontal stack of 4-6 vertical cards.

    Dual-backend (v0.5.0). ``backend="svg"`` (default) renders the v0.1.0
    horizontal stack with one card per layer + arrows; ``backend="mermaid"``
    emits a flowchart with each layer packed as a node.

    Content discipline (v0.4.0): ``label`` and ``items`` must be
    action/state names — no metrics. Quantitative info → ``kpi_band``
    (single short string) or ``captions`` (parallel array).
    """
    for layer in layers:
        _assert_step_clean(layer.get("label"), field="layers[].label")
        _assert_step_clean(layer.get("items"), field="layers[].items")
    if _resolve_backend(backend) == "svg":
        return svg_render.layered_stack(
            layers,
            side_annotations=side_annotations,
            kpi_band=kpi_band,
            title=title,
            captions=captions,
        )
    return _mermaid_task(mermaid_codegen.layered_stack(
        layers,
        side_annotations=side_annotations,
        kpi_band=kpi_band,
        title=title,
        captions=captions,
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
    captions: list[str] | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    """Top input → N parallel models → fusion → branched outputs.

    Dual-backend (v0.5.0). ``backend="svg"`` (default) renders the v0.1.0
    hand-laid 4-tier diagram with explicit fusion bar; ``backend="mermaid"``
    uses Mermaid flowchart with a parallel-models subgraph.

    Content discipline: all node labels must be action/state names —
    quantitative info → ``captions``.
    """
    _assert_step_clean(input_label,  field="input_label")
    _assert_step_clean(fusion_label, field="fusion_label")
    for m in models:
        _assert_step_clean(m.get("name"), field="models[].name")
        _assert_step_clean(m.get("desc"), field="models[].desc")
    for o in outputs:
        _assert_step_clean(o.get("label"), field="outputs[].label")
    if _resolve_backend(backend) == "svg":
        return svg_render.fanout_pipeline(
            input_label,
            models,
            fusion_label,
            outputs,
            title=title,
            subtitle=subtitle,
            captions=captions,
        )
    return _mermaid_task(mermaid_codegen.fanout_pipeline(
        input_label,
        models,
        fusion_label,
        outputs,
        title=title,
        subtitle=subtitle,
        captions=captions,
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
    captions: list[str] | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    """Two or more horizontal lanes sharing one input column on the left.

    Dual-backend (v0.5.0). ``backend="svg"`` (default) renders the v0.1.0
    layout with explicit fleet column + per-lane stage boxes;
    ``backend="mermaid"`` uses one subgraph per tier (denser look).

    Content discipline (v0.4.0): stage ``title``/``sub`` must be
    action/state names.
    """
    if fleet_box:
        _assert_step_clean(fleet_box.get("label"), field="fleet_box.label")
        _assert_step_clean(fleet_box.get("sub"),   field="fleet_box.sub")
    for tier in tiers:
        for stage in (tier.get("stages") or []):
            _assert_step_clean(stage.get("title"), field="stages[].title")
            _assert_step_clean(stage.get("sub"),   field="stages[].sub")
    if _resolve_backend(backend) == "svg":
        return svg_render.hybrid_swimlane(
            tiers,
            fleet_box=fleet_box,
            header=header,
            footer=footer,
            title=title,
            captions=captions,
        )
    return _mermaid_task(mermaid_codegen.hybrid_swimlane(
        tiers,
        fleet_box=fleet_box,
        header=header,
        footer=footer,
        title=title,
        captions=captions,
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
# cycle — closed loop of 3-8 stages around a ring + centre hub (v0.7)
# ===========================================================================
def make_cycle(
    stages: list[dict],
    *,
    title: str | None = None,
    subtitle: str | None = None,
    hub: dict | None = None,
    width: int = 1168,
    height: int = 566,
) -> dict[str, Any]:
    """A CLOSED CYCLE: 3-8 stages arranged around a ring with a centre hub and
    clockwise directional arrows. The right hero for CYCLIC processes — feedback
    loops, governance loops, lifecycles — where a linear flow would misrepresent
    the "it comes back around" nature.

    Each stage = ``{num?: str, title: str, desc?: str}`` (title = short
    action/state name; desc = a brief qualifier, kept non-quantitative per the
    brand content discipline). ``hub`` = ``{title?, lines?: list[str]}`` for the
    centre. Native SVG only (no Mermaid ring renders cleanly). Geometry leaves a
    margin so no stage label clips the canvas edge.
    """
    import math as _math
    n = len(stages)
    if not (3 <= n <= 8):
        raise ValueError(f"make_cycle needs 3-8 stages, got {n}")
    navy, deep, med = token("vti-navy"), token("vti-blue-deep"), token("vti-blue-medium")
    ink, inks, border = token("vti-ink"), token("vti-ink-soft"), token("vti-border")
    white = token("vti-white")
    cx, cy = width / 2, height / 2 + 22
    R = min((height - 200) / 2, (width - 360) / 2)
    NODE_R = max(34, min(48, R * 0.27))
    HUB_R = max(60, R * 0.50)
    hub = hub or {}
    start = -90
    angles = [start + i * (360 / n) for i in range(n)]

    def _pos(a, r):
        t = _math.radians(a)
        return cx + r * _math.cos(t), cy + r * _math.sin(t)

    P = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
         f'font-family="Plus Jakarta Sans, Arial, sans-serif">']
    P.append(
        '<defs>'
        f'<linearGradient id="cyhub" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{med}"/><stop offset="1" stop-color="{navy}"/></linearGradient>'
        f'<linearGradient id="cynode" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{med}"/><stop offset="1" stop-color="{deep}"/></linearGradient>'
        '<filter id="cysoft" x="-40%" y="-40%" width="180%" height="180%">'
        f'<feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="{navy}" flood-opacity="0.18"/></filter>'
        '</defs>')
    if title:
        P.append(f'<text x="40" y="54" font-size="30" font-weight="700" fill="{navy}" '
                 f'letter-spacing="0.4">{title}</text>')
    if subtitle:
        P.append(f'<text x="42" y="82" font-size="15" font-weight="500" fill="{inks}">{subtitle}</text>')
    # orbit + clockwise direction chevrons
    P.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{R:.0f}" fill="none" stroke="{border}" '
             f'stroke-width="2" stroke-dasharray="2 9" stroke-linecap="round"/>')
    for i in range(n):
        mid = angles[i] + (360 / n) / 2
        x, y = _pos(mid, R)
        t = _math.radians(mid)
        rot = _math.degrees(_math.atan2(_math.cos(t), -_math.sin(t)))
        P.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f})">'
                 f'<path d="M -7 -7 L 7 0 L -7 7" fill="none" stroke="{med}" stroke-width="3" '
                 f'stroke-linecap="round" stroke-linejoin="round"/></g>')
    # hub
    P.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{HUB_R:.0f}" fill="url(#cyhub)" filter="url(#cysoft)"/>')
    hub_lines = ([hub["title"]] if hub.get("title") else []) + list(hub.get("lines") or [])
    if hub_lines:
        ly = cy - (len(hub_lines) - 1) * 9
        for j, line in enumerate(hub_lines):
            big = (j == 0 and hub.get("title"))
            ls_attr = 'letter-spacing="1.4"' if big else ''
            fill_c = white if big else "#9FC6FF"
            P.append(f'<text x="{cx:.0f}" y="{ly + j*19:.0f}" text-anchor="middle" '
                     f'font-size="{13 if big else 11}" font-weight="{700 if big else 500}" '
                     f'fill="{fill_c}" {ls_attr}>{line}</text>')
    # stage nodes
    for i, st in enumerate(stages):
        a = angles[i]
        x, y = _pos(a, R)
        num = str(st.get("num") or (i + 1)).zfill(2)
        P.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{NODE_R:.0f}" fill="url(#cynode)" filter="url(#cysoft)"/>')
        P.append(f'<text x="{x:.1f}" y="{y+9:.1f}" text-anchor="middle" font-size="26" '
                 f'font-weight="700" fill="{white}">{num}</text>')
        ca = _math.cos(_math.radians(a))
        ttl, desc = st.get("title", ""), st.get("desc", "")
        if abs(ca) < 0.2:                       # top / bottom node
            up = _math.sin(_math.radians(a)) < 0
            ty = y - NODE_R - 16 if up else y + NODE_R + 26
            P.append(f'<text x="{x:.1f}" y="{ty:.1f}" text-anchor="middle" font-size="19" '
                     f'font-weight="700" fill="{navy}" letter-spacing="0.6">{ttl}</text>')
            if desc:
                P.append(f'<text x="{x:.1f}" y="{ty+20:.1f}" text-anchor="middle" font-size="13" '
                         f'font-weight="500" fill="{inks}">{desc}</text>')
        else:
            right = ca > 0
            anc = "start" if right else "end"
            lx = x + (NODE_R + 18) if right else x - (NODE_R + 18)
            P.append(f'<text x="{lx:.1f}" y="{y-2:.1f}" text-anchor="{anc}" font-size="19" '
                     f'font-weight="700" fill="{navy}" letter-spacing="0.6">{ttl}</text>')
            if desc:
                P.append(f'<text x="{lx:.1f}" y="{y+18:.1f}" text-anchor="{anc}" font-size="13" '
                         f'font-weight="500" fill="{inks}">{desc}</text>')
    P.append('</svg>')
    return _native_result("\n".join(P), width, height, "cycle")


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
    "cycle":            make_cycle,
}


_PRIMITIVE_META: dict[str, dict] = {
    "flow_diagram": {
        "name":            "flow_diagram",
        "backend":         "dual (svg|mermaid; default svg)",
        "hint_size":       "1180x280 (horizontal) / 1180x480 (vertical)",
        "good_for":        ["sequence/process", "ETL pipelines", "AWS reference architecture"],
        "content_profile": "action_label_only",
        "params":          {
            "steps":       "list[{title<=30, sub?<=60, number?}] (3-7); "
                           "labels must be action/state names — no metrics",
            "orientation": "'horizontal'|'vertical'",
            "title":       "optional",
            "subtitle":    "optional",
            "captions":    "optional list[str] rendered as a strip "
                           "below the SVG (one per step). Put numbers here.",
        },
    },
    "cycle": {
        "name":            "cycle",
        "backend":         "python (native SVG)",
        "hint_size":       "1168x566",
        "good_for":        ["feedback loops", "governance / closed loops", "lifecycles"],
        "content_profile": "action_label_only",
        "params":          {
            "stages":   "list[{num?, title<=20, desc?<=40}] (3-8) around a ring",
            "hub":      "optional {title?, lines?[]} for the centre",
            "title":    "optional (top-left)",
            "subtitle": "optional",
        },
    },
    "quadrant": {
        "name":            "quadrant",
        "backend":         "dual (svg|mermaid; default svg)",
        "hint_size":       "1180x600",
        "good_for":        ["four-pillar platforms", "2x2 framework grids"],
        "content_profile": "action_label_only",
        "params":          {
            "cells":   "list[{title, items[], point?}] (exactly 4, "
                       "order TL/TR/BL/BR). Pure action/state names.",
            "title":   "optional",
            "footer":  "optional caption",
            "x_axis":  "optional ('Low','High')",
            "y_axis":  "optional ('Low','High')",
            "captions": "optional strip below the diagram",
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
        "name":            "layered_stack",
        "backend":         "dual (svg|mermaid; default svg)",
        "hint_size":       "1180x460",
        "good_for":        ["protocol layers", "FHIR/HealthLake stacks", "IoT gateways"],
        "content_profile": "action_label_only",
        "params": {
            "layers":           "list[{label, items[]}] (4-6); "
                                "labels and items must be action/state names",
            "side_annotations": "optional list[{text}]",
            "kpi_band":         "optional KPI string",
            "title":            "optional",
            "captions":         "optional strip below the diagram",
        },
    },
    "fanout_pipeline": {
        "name":            "fanout_pipeline",
        "backend":         "dual (svg|mermaid; default svg)",
        "hint_size":       "1180x600",
        "good_for":        ["multi-model CV pipelines", "ensemble verification"],
        "content_profile": "action_label_only",
        "params": {
            "input_label":  "str (action/state name)",
            "models":       "list[{name, desc?}] (3-7); action names only",
            "fusion_label": "str",
            "outputs":      "list[{label}] (2-3); action names only",
            "title":        "optional",
            "subtitle":     "optional",
            "captions":     "optional strip below the diagram",
        },
    },
    "hybrid_swimlane": {
        "name":            "hybrid_swimlane",
        "backend":         "dual (svg|mermaid; default svg)",
        "hint_size":       "1180x480",
        "good_for":        ["security+retail dual stack", "edge+server split"],
        "content_profile": "action_label_only",
        "params": {
            "tiers":     "list[{label, stages[]}] (2-3); "
                         "stages must be action/state names",
            "fleet_box": "optional input column",
            "header":    "optional top caption",
            "footer":    "optional bottom caption",
            "title":     "optional",
            "captions":  "optional strip below the diagram",
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
    "cycle":                 "cycle",
    "loop":                  "cycle",
    "feedback-loop":         "cycle",
    "lifecycle":             "cycle",
    "closed-loop":           "cycle",
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


def backend_for(name: str, *, requested: str | None = None) -> str:
    """Return the resolved backend for a primitive name.

    - For dual-backend primitives (the 5 in ``DUAL_BACKEND``), returns
      ``requested`` if explicitly given, else the env/default backend.
    - For Python-only primitives (``PYTHON_BACKED``), always returns
      ``"python"`` (the ``requested`` arg is ignored — there's no
      Mermaid equivalent).

    Lets the caller decide whether the result of ``make_<primitive>``
    will contain a finished ``svg`` (svg/python backends) or a Mermaid
    ``mermaid_code`` render task. Raises ``ValueError`` for unknown
    primitive names.
    """
    if name in DUAL_BACKEND:
        return _resolve_backend(requested)
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
    "DUAL_BACKEND",
    "MERMAID_BACKED",
    "PYTHON_BACKED",
    "make_flow_diagram",
    "make_quadrant",
    "make_footprint_map",
    "make_layered_stack",
    "make_fanout_pipeline",
    "make_hybrid_swimlane",
    "make_data_path",
    "make_cycle",
    "list_primitives",
    "describe_primitive",
    "primitive_for_intent",
    "backend_for",
    "call",
]
