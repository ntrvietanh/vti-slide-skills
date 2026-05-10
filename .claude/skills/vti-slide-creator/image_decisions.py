"""
Phase 4 — Image strategy heuristics.

For each slide, decide one of 4 strategies for visual content:

    LIFT          — extract an existing image from the source material
                    (PDF / PPTX / DOCX uploaded by the user)
    SYNTHESIZE    — generate a new illustration via Claude (custom SVG or
                    descriptive prompt fed to an image-generation model)
    WEB-SEARCH    — search the web for a relevant photo / logo / chart
    TEXT-ONLY     — no image — let layout density carry the slide

Heuristics here are STARTERS only. Claude should override based on:
  - what's actually present in the source (lift only works if image exists)
  - branding constraints (e.g. avoid stock photography for brand voice)
  - audience (executive decks favour text-only + bold typography)
"""
from __future__ import annotations

from typing import Iterable


STRATEGY_GUIDE: dict[str, dict] = {
    "lift": {
        "when":     "Source has a directly relevant existing image.",
        "good_for": ["case studies with screenshots", "team photos",
                     "diagrams already in the source", "product UI shots"],
        "bad_for":  ["topics not covered in source",
                     "generic concepts the source illustrates poorly"],
    },
    "synthesize": {
        "when":     "Topic is conceptual / philosophical / methodological.",
        "good_for": ["pillars / values", "abstract methodology",
                     "vision / mission", "process / journey diagrams"],
        "bad_for":  ["specific people / places / products needing accuracy",
                     "data visualizations with real numbers"],
    },
    "web-search": {
        "when":     "Topic needs current data / external proof / branded imagery.",
        "good_for": ["partner logos", "certifications & badges",
                     "geographic / facility photos", "industry trend visuals"],
        "bad_for":  ["proprietary content", "internal team photos",
                     "anything legally sensitive"],
    },
    "text-only": {
        "when":     "Slide is content-dense (3+ cards, kpi-row, etc.).",
        "good_for": ["service catalogs", "comparison panels",
                     "value-medallion 6-up", "kpi-strip slides"],
        "bad_for":  ["sparse single-stat slides that need a visual anchor"],
    },
}


def describe_strategies() -> dict:
    """Return the full strategy guide (for prompts / docs)."""
    return STRATEGY_GUIDE


# ---------------------------------------------------------------------------
# Heuristic suggester
# ---------------------------------------------------------------------------
_DENSE_KINDS = {"features_3", "values", "catalog", "supporting_stats"}

_CONCRETE_TOKENS = (
    "case", "screenshot", "team", "office", "facility",
    "client", "product", "ui", "dashboard",
)
_ABSTRACT_TOKENS = (
    "vision", "mission", "value", "principle", "philosophy",
    "approach", "methodology", "framework", "pillar",
)
_EXTERNAL_TOKENS = (
    "trend", "industry", "certification", "standard",
    "ranking", "partner", "badge", "award", "compliance",
)


def suggest_strategy(slide_topic: str,
                     block_kinds: Iterable[str],
                     has_source_images: bool = False) -> dict:
    """Heuristic suggestion. Returns ``{strategy, reason}``.

    Args:
        slide_topic: short topic text for the slide.
        block_kinds: the kinds present in the SlideContentPlan.blocks
                     list (use ``content_drafter.block_kinds_in(plan)``).
        has_source_images: whether the source had extractable images
                     (set by Phase 1 ANALYZE).
    """
    block_kinds = set(block_kinds)
    topic = slide_topic.lower()

    # 1. Content-dense slides → text-only
    if block_kinds & _DENSE_KINDS:
        return {
            "strategy": "text-only",
            "reason": ("slide already has cards or kpi strip — visual "
                       "anchors come from those, no extra image needed"),
        }

    # 2. Concrete topic + source has images → lift
    if has_source_images and any(t in topic for t in _CONCRETE_TOKENS):
        return {
            "strategy": "lift",
            "reason": ("topic looks concrete and source likely has a "
                       "matching image"),
        }

    # 3. Abstract / methodology topic → synthesize illustration
    if any(t in topic for t in _ABSTRACT_TOKENS):
        return {
            "strategy": "synthesize",
            "reason": "abstract concept benefits from custom illustration",
        }

    # 4. External / industry topic → web search
    if any(t in topic for t in _EXTERNAL_TOKENS):
        return {
            "strategy": "web-search",
            "reason": "topic requires external imagery (logos, certs, trend data)",
        }

    # 5. Default — text-only is safest
    return {
        "strategy": "text-only",
        "reason": "default — let typography + layout carry the slide",
    }
