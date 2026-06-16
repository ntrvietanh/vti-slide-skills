"""Slide archetype library (v4.0 / M3 — art-director layer).

The pre-M3 pipeline chose geometry with a deterministic scorer in
``layout_designer`` that only emitted a handful of patterns, so similar
slides converged to the same frame. This module is the opposite approach:
a curated catalog of hand-tuned, intentful layouts (asymmetric splits,
focal cells, surfaces, deliberate whitespace) that the orchestrator
SELECTS by slide intent and FILLS with content — the way a designer works
from a deck kit.

The composer already renders any rows/cells with arbitrary col spans +
the M3 cell surfaces, so this layer is purely additive: it produces a
standard ``slide_input`` dict. The old scorer path is untouched.

Public surface
--------------
- ``list_archetypes()``            → compact list for selection
- ``describe_archetype(id)``       → full detail incl. derived slot list
- ``slots_for(id)``                → [{name, component, required}]
- ``realize_archetype(id, slots, slide_meta=None, overrides=None)``
                                   → slide_input dict (rows/cells)

An archetype ``rows`` template uses cells that carry a ``slot`` name; the
component + geometry (col_start/col_span/row_span) + optional ``surface``
live in the template. ``realize_archetype`` fills each slot with the
caller's props, drops optional slots that got no content, and lets the
caller override per-slot span/surface/component for fine art-direction.
"""
from __future__ import annotations

from typing import Any

# Every archetype is data. A cell:
#   {slot, component, col_start, col_span, row_span?, surface?, required?}
# A row: {height, _fill_verified?, cells: [...]}
ARCHETYPES: dict[str, dict[str, Any]] = {

    # ---- big-idea / statement ------------------------------------------
    "hero-statement": {
        "intent": "big-idea",
        "summary": "One bold claim, left-weighted with breathing room on the "
                   "right. Eyebrow + display headline + a single supporting line.",
        "best_for": ["section opener", "a single thesis", "transition / punch line"],
        "avoid_when": ["lots of supporting detail", "comparisons", "data"],
        "whitespace": "Right third + lower area intentionally empty — the idea "
                      "breathes; do not fill it.",
        "accent_policy": "Headline in display tier; everything else recedes.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "kicker", "component": "kicker",
                 "col_start": 1, "col_span": 7, "required": False},
            ]},
            {"height": "auto", "cells": [
                {"slot": "headline", "component": "headline",
                 "col_start": 1, "col_span": 9, "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "support", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 7, "required": False},
            ]},
        ],
    },

    # ---- stat anchor (asymmetric) --------------------------------------
    "stat-anchor-left": {
        "intent": "stat-anchor",
        "summary": "A dominant hero stat in an elevated panel on the left (40%) "
                   "anchors a narrative + checklist on the right (60%).",
        "best_for": ["one headline metric + the story behind it", "proof point"],
        "avoid_when": ["several equally-important numbers (use kpi-band)"],
        "whitespace": "Panel and text columns are balanced; no dead space.",
        "accent_policy": "Stat is the single focal point (hero tier).",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "stat", "component": "stat-hero",
                 "col_start": 1, "col_span": 5, "surface": "elevated",
                 "required": True},
                {"slot": "story", "component": "narrative-paragraph",
                 "col_start": 6, "col_span": 7, "valign": "center",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "points", "component": "bullet-list-checked",
                 "col_start": 6, "col_span": 7, "required": False},
            ]},
        ],
    },
    "stat-anchor-right": {
        "intent": "stat-anchor",
        "summary": "Mirror of stat-anchor-left — narrative left (60%), the hero "
                   "stat panel anchors the right (40%). Use to vary rhythm.",
        "best_for": ["proof point when the previous slide anchored left"],
        "avoid_when": ["several equally-important numbers"],
        "whitespace": "Balanced two-column.",
        "accent_policy": "Stat is the focal point.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "story", "component": "narrative-paragraph",
                 "col_start": 1, "col_span": 7, "valign": "center",
                 "required": True},
                {"slot": "stat", "component": "stat-hero",
                 "col_start": 8, "col_span": 5, "surface": "elevated",
                 "required": True},
            ]},
        ],
    },

    # ---- three pillars (lead-in + cards) -------------------------------
    "lead-plus-three-cards": {
        "intent": "pillars",
        "summary": "A short framing line, then three peer cards across the "
                   "bottom. The lead is left-weighted (not full width) for tension.",
        "best_for": ["three capabilities / pillars / steps", "service triads"],
        "avoid_when": ["only two items", "more than four items"],
        "whitespace": "Right of the lead line is open; cards anchor the base.",
        "accent_policy": "Cards alternate accent per VTI rhythm (deep/sky).",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "lead", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 8, "required": True},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "card1", "component": "practice-card",
                 "col_start": 1, "col_span": 4, "required": True},
                {"slot": "card2", "component": "practice-card",
                 "col_start": 5, "col_span": 4, "required": True},
                {"slot": "card3", "component": "practice-card",
                 "col_start": 9, "col_span": 4, "required": True},
            ]},
        ],
    },

    # ---- main + sidebar (asymmetric 2/3 + 1/3) -------------------------
    "narrative-with-sidebar": {
        "intent": "narrative+support",
        "summary": "Main narrative occupies two-thirds; a tinted sidebar panel "
                   "on the right holds supporting stats or a short list.",
        "best_for": ["an explanation with a few side facts", "context + callout"],
        "avoid_when": ["pure data slides"],
        "whitespace": "Sidebar panel grounds the right; main column leads.",
        "accent_policy": "Sidebar tint sets the support apart without shouting.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "main", "component": "narrative-paragraph",
                 "col_start": 1, "col_span": 8, "required": True},
                {"slot": "sidebar", "component": "kpi-row",
                 "col_start": 9, "col_span": 4, "surface": "tint",
                 "required": True},
            ]},
        ],
    },

    # ---- comparison (two panels +/- divider) --------------------------
    "two-panel-compare": {
        "intent": "comparison",
        "summary": "Two balanced panels side by side (tint vs panel) for an A/B "
                   "or before/after contrast.",
        "best_for": ["before vs after", "us vs them", "option A vs B"],
        "avoid_when": ["three or more options (use cards)"],
        "whitespace": "Symmetric by design — the contrast IS the message.",
        "accent_policy": "Left tinted (neutral/old), right panel (new/preferred).",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "lead", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 10, "required": False},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "left", "component": "bullet-list-checked",
                 "col_start": 1, "col_span": 6, "surface": "tint",
                 "required": True},
                {"slot": "right", "component": "bullet-list-checked",
                 "col_start": 7, "col_span": 6, "surface": "panel",
                 "required": True},
            ]},
        ],
    },

    # ---- data story (chart-dominant, asymmetric) ----------------------
    "data-story-left": {
        "intent": "data-story",
        "summary": "A chart dominates the left (~58%); a narrative + takeaway on "
                   "the right reads the data for the audience.",
        "best_for": ["a trend / breakdown that needs interpretation"],
        "avoid_when": ["the number alone is the point (use stat-anchor)"],
        "whitespace": "Chart fills its column; right column paces the read.",
        "accent_policy": "Chart carries brand palette; text stays neutral.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "chart", "component": "bar-chart",
                 "col_start": 1, "col_span": 7, "required": True},
                {"slot": "read", "component": "narrative-paragraph",
                 "col_start": 8, "col_span": 5, "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "takeaway", "component": "callout",
                 "col_start": 8, "col_span": 5, "required": False},
            ]},
        ],
    },

    # ---- kpi band + narrative ----------------------------------------
    "kpi-band-top": {
        "intent": "metrics",
        "summary": "A full-width KPI strip across the top, then a narrative that "
                   "frames what the numbers mean.",
        "best_for": ["3-5 headline metrics + a sentence of context"],
        "avoid_when": ["a single dominant number (use stat-anchor)"],
        "whitespace": "KPI strip anchors top; narrative grounds the middle.",
        "accent_policy": "Metrics read as one band; narrative recedes.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "kpis", "component": "kpi-row",
                 "col_start": 1, "col_span": 12, "surface": "panel",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "context", "component": "narrative-paragraph",
                 "col_start": 1, "col_span": 9, "required": True},
            ]},
        ],
    },

    # ---- quote impact -------------------------------------------------
    "quote-impact": {
        "intent": "quote",
        "summary": "A single large pull-quote, left-weighted, with attribution. "
                   "Lots of intentional space.",
        "best_for": ["a testimonial", "a guiding principle", "a customer voice"],
        "avoid_when": ["dense content"],
        "whitespace": "The quote floats — surrounding space is the design.",
        "accent_policy": "Quote in display tier; attribution in caption tier.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "quote", "component": "pull-quote",
                 "col_start": 1, "col_span": 10, "valign": "center",
                 "required": True},
            ]},
        ],
    },

    # ---- dominant diagram + caption rail ------------------------------
    "dominant-diagram": {
        "intent": "diagram",
        "summary": "A large diagram/visual as the focal cell (~67%) with a slim "
                   "caption rail on the right that narrates the flow.",
        "best_for": ["architecture / process / flow as the hero"],
        "avoid_when": ["the diagram is small or secondary"],
        "whitespace": "Diagram fills; rail is deliberately narrow.",
        "accent_policy": "Diagram carries the colour; rail text is neutral.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "diagram", "component": "image-tile",
                 "col_start": 1, "col_span": 8, "required": True},
                {"slot": "rail", "component": "numbered-list",
                 "col_start": 9, "col_span": 4, "surface": "tint",
                 "required": False},
            ]},
        ],
    },

    # ---- feature + visual (40/60 split) -------------------------------
    "feature-with-visual": {
        "intent": "feature+visual",
        "summary": "Narrative + checklist on the left (~42%), a supporting image "
                   "or mockup on the right (~58%).",
        "best_for": ["a capability paired with a screenshot / photo"],
        "avoid_when": ["no good supporting image"],
        "whitespace": "Two columns balance; image bleeds to its cell edge.",
        "accent_policy": "Image is the visual anchor; text is the argument.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "title", "component": "headline",
                 "col_start": 1, "col_span": 7, "required": False},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "points", "component": "bullet-list-checked",
                 "col_start": 1, "col_span": 5, "required": True},
                {"slot": "visual", "component": "image-tile",
                 "col_start": 6, "col_span": 7, "required": True},
            ]},
        ],
    },

    # ---- catalog grid -------------------------------------------------
    "catalog-grid": {
        "intent": "catalog",
        "summary": "A short intro then a row of catalog columns (2-4) listing "
                   "grouped items.",
        "best_for": ["a service / product catalog", "grouped offerings"],
        "avoid_when": ["narrative-heavy content"],
        "whitespace": "Columns fill the base; intro is left-weighted.",
        "accent_policy": "Columns alternate accent for rhythm.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "intro", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 8, "required": False},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "col1", "component": "catalog-column",
                 "col_start": 1, "col_span": 4, "required": True},
                {"slot": "col2", "component": "catalog-column",
                 "col_start": 5, "col_span": 4, "required": True},
                {"slot": "col3", "component": "catalog-column",
                 "col_start": 9, "col_span": 4, "required": False},
            ]},
        ],
    },

    # ======================================================================
    # EDITORIAL ARCHETYPES (v4.5) — bold, dark, oversized, full-bleed,
    # chart-led, asymmetric. These break the flat "narrative + one row"
    # default; each fills the canvas with a 1fr row and carries a real visual
    # anchor. Dark / bleed archetypes are self-contained via slide_meta_defaults.
    # ======================================================================

    # ---- dark full-bleed section divider with oversized chapter numeral --
    "stage-divider": {
        "intent": "section-divider",
        "summary": "A dark full-bleed chapter open: an oversized numeral on the "
                   "left anchors a large title on the right, with one framing "
                   "line. The whole slide goes navy-gradient.",
        "best_for": ["section / chapter opener", "a dramatic transition beat"],
        "avoid_when": ["dense content", "data"],
        "whitespace": "The dark stage IS the design; the numeral + title float "
                      "in deliberate space.",
        "accent_policy": "Mega numeral + display title, everything light on dark.",
        "slide_meta_defaults": {"stage": "grad", "layout_class": "editorial"},
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "number", "component": "stat-hero",
                 "col_start": 1, "col_span": 4, "valign": "center",
                 "required": False},
                {"slot": "title", "component": "headline",
                 "col_start": 5, "col_span": 8, "valign": "center",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "framing", "component": "lead-paragraph",
                 "col_start": 5, "col_span": 8, "required": False},
            ]},
        ],
    },

    # ---- one giant number owns ~half the canvas (dark stat panel) --------
    "mega-stat": {
        "intent": "stat-anchor",
        "summary": "A single oversized stat on a dark stage panel owns the left "
                   "half; a narrative + proof points read the number on the right.",
        "best_for": ["one dramatic headline metric", "a scale / impact claim"],
        "avoid_when": ["no real number (do NOT fabricate)", "several peer metrics"],
        "whitespace": "Dark panel anchors left; text column paces the read.",
        "accent_policy": "The number is the whole slide — mega tier, light on dark.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "stat", "component": "stat-hero",
                 "col_start": 1, "col_span": 6, "surface": "stage",
                 "required": True},
                {"slot": "story", "component": "narrative-paragraph",
                 "col_start": 7, "col_span": 6, "valign": "center",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "points", "component": "bullet-list-checked",
                 "col_start": 7, "col_span": 6, "required": False},
            ]},
        ],
    },

    # ---- full-bleed photo + left-anchored text overlay -------------------
    "image-bleed-overlay": {
        "intent": "image-statement",
        "summary": "A full-bleed photo fills the canvas behind a legibility "
                   "scrim; an eyebrow + bold headline + one line sit on the dark "
                   "left. Requires slide_meta.bg_image.",
        "best_for": ["a cinematic opener", "a human / context moment", "a hero image"],
        "avoid_when": ["no strong photo available", "data / detail"],
        "whitespace": "Text on the dark left third; the photo breathes right.",
        "accent_policy": "Headline white over the scrim; everything else recedes.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "kicker", "component": "kicker",
                 "col_start": 1, "col_span": 7, "required": False},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "headline", "component": "headline",
                 "col_start": 1, "col_span": 7, "valign": "center",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "support", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 6, "required": False},
            ]},
        ],
    },

    # ---- asymmetric 60/40 split with a single visual anchor --------------
    "split-anchor-60-40": {
        "intent": "feature+visual",
        "summary": "A deliberate 7/5 imbalance: argument (lead + checklist) on "
                   "the left, a single strong visual anchor (image, chart or "
                   "dark stat) on the right.",
        "best_for": ["a point that needs one supporting visual", "claim + proof"],
        "avoid_when": ["two equal columns (use two-panel-compare)"],
        "whitespace": "Text leads; the anchor grounds the right at full height.",
        "accent_policy": "One anchor carries the colour; text stays neutral.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "lead", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 7, "required": False},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "points", "component": "bullet-list-checked",
                 "col_start": 1, "col_span": 7, "valign": "center",
                 "required": True},
                {"slot": "anchor", "component": "image-tile",
                 "col_start": 8, "col_span": 5, "required": True},
            ]},
        ],
    },

    # ---- chart-led data slide (chart dominates, not a table) -------------
    "chart-lead": {
        "intent": "data-story",
        "summary": "A chart owns two-thirds of the slide; a narrative reads the "
                   "data and a deep-tone callout lands the single takeaway.",
        "best_for": ["a metric / breakdown / trend with real numbers"],
        "avoid_when": ["categorical lists (use catalog/icon-list)", "no numbers"],
        "whitespace": "Chart fills its column; the right rail paces the read.",
        "accent_policy": "Chart carries brand palette (≤1 accent series); "
                         "takeaway callout is the one deep-tone emphasis.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "chart", "component": "bar-chart",
                 "col_start": 1, "col_span": 8, "required": True},
                {"slot": "read", "component": "narrative-paragraph",
                 "col_start": 9, "col_span": 4, "valign": "center",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "takeaway", "component": "callout",
                 "col_start": 9, "col_span": 4, "required": False},
            ]},
        ],
    },

    # ---- three full-height bold cards (strong colour rhythm) -------------
    "triad-bold": {
        "intent": "pillars",
        "summary": "Three full-height cards with strong coloured headers + icons "
                   "fill the slide. An optional eyebrow frames them. Bolder than "
                   "lead-plus-three-cards (no lead paragraph eating height).",
        "best_for": ["three peer capabilities / pillars / steps with icons"],
        "avoid_when": ["only two items", "more than four items",
                       "long multi-paragraph card bodies (use lead-plus-three-cards, 1fr)"],
        "whitespace": "Cards size to content as a centred band — balanced "
                      "breathing room above + below, never tall hollow tiles.",
        "accent_policy": "Cards step deep / sky / navy (or one accent standout).",
        # Centred band: cards are content-height (not stretched), the whole
        # group sits vertically centred so brief peer cards read as an
        # intentional tile band rather than hollow full-height columns.
        "slide_meta_defaults": {"vertical_align": "center"},
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "kicker", "component": "kicker",
                 "col_start": 1, "col_span": 8, "required": False},
            ]},
            {"height": "auto", "cells": [
                {"slot": "card1", "component": "practice-card",
                 "col_start": 1, "col_span": 4, "required": True},
                {"slot": "card2", "component": "practice-card",
                 "col_start": 5, "col_span": 4, "required": True},
                {"slot": "card3", "component": "practice-card",
                 "col_start": 9, "col_span": 4, "required": True},
            ]},
        ],
    },

    # ---- process-flow as a full-width band -------------------------------
    "process-band": {
        "intent": "process",
        "summary": "A short lead, then a full-width process-flow band (tinted) "
                   "owns the slide's centre mass, with an optional outcome "
                   "callout grounding the base.",
        "best_for": ["a sequence / workflow / pipeline of 3-7 steps"],
        "avoid_when": ["unordered items (use icon-list / catalog)"],
        "whitespace": "The flow band fills the middle; lead + outcome frame it.",
        "accent_policy": "Flow carries the brand gradient; callout deep-tone.",
        "rows": [
            {"height": "auto", "cells": [
                {"slot": "lead", "component": "lead-paragraph",
                 "col_start": 1, "col_span": 8, "required": False},
            ]},
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "flow", "component": "process-flow",
                 "col_start": 1, "col_span": 12, "surface": "tint",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "outcome", "component": "callout",
                 "col_start": 1, "col_span": 12, "required": False},
            ]},
        ],
    },

    # ---- KPI band on a dark stage + framing ------------------------------
    "stage-kpi-band": {
        "intent": "metrics",
        "summary": "A luminous dark KPI band across the top, then a narrative "
                   "that frames what the numbers mean. The dark stage makes the "
                   "metrics read as one band instead of a pale flat strip.",
        "best_for": ["3-5 headline metrics + a sentence of context"],
        "avoid_when": ["a single dominant number (use mega-stat)"],
        "whitespace": "Dark band anchors the top; narrative grounds the middle.",
        "accent_policy": "Metrics light on dark; narrative recedes.",
        "rows": [
            {"height": "1fr", "_fill_verified": True, "cells": [
                {"slot": "kpis", "component": "kpi-row",
                 "col_start": 1, "col_span": 12, "surface": "stage-grad",
                 "required": True},
            ]},
            {"height": "auto", "cells": [
                {"slot": "context", "component": "narrative-paragraph",
                 "col_start": 1, "col_span": 8, "required": True},
            ]},
        ],
    },
}


# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------
def _slots(arch: dict) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for row in arch["rows"]:
        for cell in row["cells"]:
            name = cell["slot"]
            if name in seen:
                continue
            seen.add(name)
            out.append({
                "name": name,
                "component": cell["component"],
                "required": bool(cell.get("required", True)),
                "surface": cell.get("surface"),
                "col_span": cell["col_span"],
            })
    return out


def list_archetypes() -> list[dict]:
    """Compact list for the orchestrator's archetype-selection step."""
    return [
        {
            "id": aid,
            "intent": a["intent"],
            "summary": a["summary"],
            "best_for": a["best_for"],
            "avoid_when": a.get("avoid_when", []),
            "required_slots": [s["name"] for s in _slots(a) if s["required"]],
            "optional_slots": [s["name"] for s in _slots(a) if not s["required"]],
        }
        for aid, a in ARCHETYPES.items()
    ]


def describe_archetype(archetype_id: str) -> dict:
    """Full detail for one archetype + its derived slot list."""
    if archetype_id not in ARCHETYPES:
        raise KeyError(
            f"unknown archetype {archetype_id!r}; "
            f"valid: {sorted(ARCHETYPES)}"
        )
    a = ARCHETYPES[archetype_id]
    return {"id": archetype_id, **a, "slots": _slots(a)}


def slots_for(archetype_id: str) -> list[dict]:
    """Just the slot list the caller must fill (name, component, required)."""
    return describe_archetype(archetype_id)["slots"]


# ---------------------------------------------------------------------------
# Realize → slide_input
# ---------------------------------------------------------------------------
def realize_archetype(archetype_id: str,
                      slots: dict[str, dict],
                      slide_meta: dict | None = None,
                      *,
                      overrides: dict[str, dict] | None = None) -> dict:
    """Turn an archetype + slot content into a ``slide_input`` dict.

    Args:
        archetype_id: one of ``ARCHETYPES``.
        slots: ``{slot_name: props}`` — the content for each filled slot.
               Props must match the slot's component schema (see the
               page-builder catalog ``schema_brief``).
        slide_meta: the slide's meta (section_name / slide_title / etc.).
        overrides: optional ``{slot_name: {col_span?, col_start?, row_span?,
               surface?, component?}}`` — lets the art-director fine-tune a
               slot's geometry/treatment/component without editing the
               archetype.

    Behaviour:
        * A required slot with no content → ValueError (loud, not silent).
        * An optional slot with no content → its cell is dropped; a row that
          loses all its cells is dropped too.
        * Returns ``{"slide_meta": ..., "rows": [...]}`` ready for
          ``compose_slide_grid`` / ``compose_deck``.
    """
    if archetype_id not in ARCHETYPES:
        raise KeyError(
            f"unknown archetype {archetype_id!r}; valid: {sorted(ARCHETYPES)}"
        )
    arch = ARCHETYPES[archetype_id]
    overrides = overrides or {}

    out_rows: list[dict] = []
    for row in arch["rows"]:
        out_cells: list[dict] = []
        for cell in row["cells"]:
            name = cell["slot"]
            content = slots.get(name)
            required = bool(cell.get("required", True))
            if content is None:
                if required:
                    raise ValueError(
                        f"archetype {archetype_id!r}: required slot {name!r} "
                        f"(component {cell['component']}) has no content"
                    )
                continue  # optional + empty → drop the cell
            ov = overrides.get(name, {})
            built = {
                "col_start": ov.get("col_start", cell["col_start"]),
                "col_span":  ov.get("col_span", cell["col_span"]),
                "component": ov.get("component", cell["component"]),
                "props":     content,
            }
            row_span = ov.get("row_span", cell.get("row_span", 1))
            if row_span != 1:
                built["row_span"] = row_span
            surface = ov.get("surface", cell.get("surface"))
            if surface:
                built["surface"] = surface
            valign = ov.get("valign", cell.get("valign"))
            if valign:
                built["valign"] = valign
            out_cells.append(built)

        if not out_cells:
            continue  # whole row emptied out → drop it
        out_row = {"height": row.get("height", "auto"), "cells": out_cells}
        if row.get("_fill_verified"):
            out_row["_fill_verified"] = True
        out_rows.append(out_row)

    if not out_rows:
        raise ValueError(
            f"archetype {archetype_id!r}: no rows produced — supply at least "
            f"the required slots {[s['name'] for s in _slots(arch) if s['required']]}"
        )

    # v4.5 — an archetype may declare ``slide_meta_defaults`` (e.g. a dark
    # ``stage`` or a ``layout_class``) that should travel with it so editorial
    # archetypes are self-contained; the caller's slide_meta always wins.
    meta = {**arch.get("slide_meta_defaults", {}), **(slide_meta or {})}
    return {"slide_meta": meta, "rows": out_rows}


__all__ = [
    "ARCHETYPES",
    "list_archetypes", "describe_archetype", "slots_for",
    "realize_archetype",
]
