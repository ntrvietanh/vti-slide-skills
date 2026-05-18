"""Mermaid theme directive built from VTI brand tokens.

Mermaid (>= v10) accepts a per-diagram ``%%{init: ...}%%`` directive that
overrides theme variables. We emit one such directive prepended to every
codegen output so Mermaid-rendered diagrams visually align with the deck
chrome rendered by ``vti-slide-page-builder``.

This module re-uses the already-parsed token table from
``tokens_bridge.TOKENS`` — both files share one source of truth.

Public surface
--------------
- ``init_directive()``          — full ``%%{init: {...}}%%`` line ready to
                                   prepend to any Mermaid code string
- ``init_directive_quadrant()`` — variant tuned for ``quadrantChart``
                                   (Mermaid uses a separate set of theme
                                   variable names for that chart type)
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


def _flowchart_theme_variables() -> dict[str, str]:
    """Theme variables for ``flowchart`` (the kind we use most).

    Picked to mirror VTI's blue-on-pale palette: deep blue primary nodes,
    teal secondary, pale-blue subgraph fills, soft-ink connectors.
    """
    return {
        # Primary node (default first-class node)
        "primaryColor":        token("vti-blue-deep"),
        "primaryTextColor":    token("vti-white"),
        "primaryBorderColor":  token("vti-navy"),

        # Secondary — used by alternate node classes and accent edges
        "secondaryColor":       token("vti-teal"),
        "secondaryTextColor":   token("vti-ink"),
        "secondaryBorderColor": token("vti-blue"),

        # Tertiary — subgraph background / cluster fills
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

    Mermaid maps quadrants in the order Q1 (top-right), Q2 (top-left),
    Q3 (bottom-left), Q4 (bottom-right). We tint each with a different
    VTI accent so a brand-consistent quadrant lands with no caller config.
    """
    return {
        # Per-quadrant fills — tinted so points / text remain readable
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
    "font_family",
]
