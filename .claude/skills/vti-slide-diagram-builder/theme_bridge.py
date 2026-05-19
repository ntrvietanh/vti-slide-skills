"""Mermaid theme directive built from VTI brand tokens.

Mermaid (>= v10) accepts a per-diagram ``%%{init: ...}%%`` directive that
overrides theme variables. We emit one such directive prepended to every
codegen output so Mermaid-rendered diagrams visually align with the deck
chrome rendered by ``vti-slide-page-builder``.

Brand discipline (v0.4.0)
-------------------------
**One brand, one hue.** Mermaid theme variables only reference the VTI
blue family + neutrals. Per-node colour comes from ``classDef step{i}``
lines emitted by ``gradient_classdefs(n)`` — a monotonic light→dark
progression across step index (pale-blue → navy). Callers no longer
pick a per-element accent; the gradient is index-driven.

This module re-uses the already-parsed token table from
``tokens_bridge.TOKENS`` — both files share one source of truth.

Public surface
--------------
- ``init_directive()``          — full ``%%{init: {...}}%%`` line ready to
                                   prepend to any Mermaid code string
- ``init_directive_quadrant()`` — variant tuned for ``quadrantChart``
                                   (Mermaid uses a separate set of theme
                                   variable names for that chart type)
- ``gradient_classdefs(n)``     — emit ``classDef step0..step{n-1}`` lines
                                   sampling the blue gradient
- ``font_family()``             — body font stack as a single CSS value
"""
from __future__ import annotations

import json

from tokens_bridge import TOKENS, token


def font_family() -> str:
    """Body font stack from tokens — strip surrounding quotes if present."""
    return TOKENS.get(
        "vti-font-body",
        "'Plus Jakarta Sans', 'Arial', system-ui, sans-serif",
    )


# ---------------------------------------------------------------------------
# Blue-mono gradient (v0.4.0)
# ---------------------------------------------------------------------------
# Ordered light→dark across the VTI blue family. ``gradient_classdefs(n)``
# samples ``n`` evenly-spaced indices and emits one ``classDef stepN ...``
# per step. Text colour flips to white once the fill is dark enough to
# preserve contrast.
_GRADIENT_STEPS: list[tuple[str, str]] = [
    # (fill token alias, text token alias)
    ("vti-paleblue",    "vti-ink"),     # 0 — lightest
    ("vti-light",       "vti-ink"),     # 1
    ("vti-sky",         "vti-white"),   # 2
    ("vti-blue-medium", "vti-white"),   # 3
    ("vti-blue",        "vti-white"),   # 4
    ("vti-blue-deep",   "vti-white"),   # 5
    ("vti-navy",        "vti-white"),   # 6 — darkest
]


def _sampled_indices(n: int) -> list[int]:
    """Pick ``n`` indices from the gradient evenly (anchored at ends)."""
    base = len(_GRADIENT_STEPS)
    if n <= 1:
        return [base - 1]
    if n >= base:
        return list(range(base))
    # Linear sample inclusive of both endpoints.
    out = [round(i * (base - 1) / (n - 1)) for i in range(n)]
    # Deduplicate while preserving order (rounding can collide at small n).
    seen: set[int] = set()
    deduped: list[int] = []
    for idx in out:
        if idx not in seen:
            deduped.append(idx)
            seen.add(idx)
    # Pad back if dedup shrank below n (only possible at very small base).
    while len(deduped) < n:
        deduped.append(min(base - 1, deduped[-1] + 1))
    return deduped


def gradient_classdefs(n: int) -> list[str]:
    """Emit ``classDef step0..step{n-1}`` lines for an n-step blue gradient.

    The classDef names ``step0``, ``step1`` ... must match the ``:::stepN``
    suffixes that ``mermaid_codegen`` attaches to each node.
    """
    indices = _sampled_indices(max(1, int(n)))
    lines: list[str] = []
    for slot, gi in enumerate(indices):
        fill_alias, text_alias = _GRADIENT_STEPS[gi]
        fill = token(fill_alias)
        text = token(text_alias)
        # Use navy as the stroke for a unified outline.
        stroke = token("vti-navy")
        lines.append(
            f"classDef step{slot} fill:{fill},stroke:{stroke},"
            f"color:{text},stroke-width:1.5px,rx:14,ry:14;"
        )
    return lines


def _flowchart_theme_variables() -> dict[str, str]:
    """Theme variables for ``flowchart`` (the kind we use most).

    All references stay inside the VTI blue family + neutrals. Per-node
    colour is overridden by ``classDef step{i}`` lines emitted alongside
    the diagram body, so the theme variables here only matter for
    fallbacks (edges, edge labels, subgraph titles).
    """
    return {
        # Primary fallback — only used if no classDef applies.
        "primaryColor":        token("vti-blue-deep"),
        "primaryTextColor":    token("vti-white"),
        "primaryBorderColor":  token("vti-navy"),

        # Secondary / tertiary kept in the blue family.
        "secondaryColor":       token("vti-blue-medium"),
        "secondaryTextColor":   token("vti-white"),
        "secondaryBorderColor": token("vti-navy"),

        "tertiaryColor":       token("vti-light"),
        "tertiaryTextColor":   token("vti-ink"),
        "tertiaryBorderColor": token("vti-border"),

        # Canvas + lines
        "background":     token("vti-bg"),
        "mainBkg":        token("vti-blue-deep"),
        "lineColor":      token("vti-ink-soft"),
        "textColor":      token("vti-ink"),

        # Cluster (subgraph) styling
        "clusterBkg":     token("vti-paleblue"),
        "clusterBorder":  token("vti-border"),
        "titleColor":     token("vti-navy"),

        # Edge labels
        "edgeLabelBackground": token("vti-bg"),

        # Font
        "fontFamily":     font_family(),
        "fontSize":       "14px",
    }


def _quadrant_theme_variables() -> dict[str, str]:
    """Theme variables specific to ``quadrantChart``.

    Quadrant cells use light blue tints (already inside the brand family);
    points use deep blue. Mermaid does not expose per-cell shape config
    so quadrant corners remain rectangular at v0.4.0 — see CHANGELOG.
    """
    return {
        # Per-quadrant fills — tinted so points / text remain readable.
        "quadrant1Fill":  token("vti-paleblue"),  # top-right
        "quadrant2Fill":  token("vti-light"),     # top-left
        "quadrant3Fill":  token("vti-bg"),        # bottom-left
        "quadrant4Fill":  token("vti-divider"),   # bottom-right

        "quadrant1TextFill": token("vti-ink"),
        "quadrant2TextFill": token("vti-ink"),
        "quadrant3TextFill": token("vti-ink"),
        "quadrant4TextFill": token("vti-ink"),

        # Axis + title
        "quadrantTitleFill":        token("vti-navy"),
        "quadrantXAxisTextFill":    token("vti-ink-soft"),
        "quadrantYAxisTextFill":    token("vti-ink-soft"),

        # Borders
        "quadrantInternalBorderStrokeFill": token("vti-border"),
        "quadrantExternalBorderStrokeFill": token("vti-navy"),

        # Points (datapoints inside quadrants)
        "quadrantPointFill":     token("vti-blue-deep"),
        "quadrantPointTextFill": token("vti-ink"),

        # Font
        "fontFamily": font_family(),
        "fontSize":   "14px",
    }


def _emit(theme_variables: dict[str, str]) -> str:
    """Render an ``%%{init: ...}%%`` line with the given themeVariables."""
    payload = {
        "theme":          "base",
        "themeVariables": theme_variables,
    }
    return "%%{init: " + json.dumps(payload, separators=(",", ":")) + "}%%"


def init_directive() -> str:
    """Init directive for flowchart-family diagrams (5 of our 5 codegens
    use this — flow_diagram, layered_stack, fanout_pipeline,
    hybrid_swimlane, and a fallback for anything else)."""
    return _emit(_flowchart_theme_variables())


def init_directive_quadrant() -> str:
    """Init directive for ``quadrantChart``."""
    return _emit(_quadrant_theme_variables())


__all__ = [
    "init_directive",
    "init_directive_quadrant",
    "gradient_classdefs",
    "font_family",
]
