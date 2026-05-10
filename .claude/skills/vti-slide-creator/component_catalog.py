"""
Component catalog — thin proxy over page-builder's catalog API.

Single source of truth: each component declares its metadata at registration
time in ``vti-slide-page-builder-v3/composer_grid.py`` via the ``meta=`` kwarg
of ``register_component``. This module just imports + re-exposes that data
in the shape the creator's pick step expects.

Why this matters: when a new component is added to the page-builder, the
creator picks it up automatically — no syncing two hardcoded lists.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Wire up the page-builder so we can call its catalog().
_PAGE_BUILDER_ROOT = (
    Path(__file__).resolve().parent.parent / "vti-slide-page-builder-v3"
)
if str(_PAGE_BUILDER_ROOT) not in sys.path:
    sys.path.insert(0, str(_PAGE_BUILDER_ROOT))

from composer_grid import (                      # noqa: E402
    catalog as _builder_catalog,
    catalog_by_category as _builder_by_category,
    catalog_markdown as _builder_markdown,
    describe_component as _builder_describe,
    COMPONENT_CATEGORIES as _COMPONENT_CATEGORIES,
    CATEGORY_DESCRIPTIONS as _CATEGORY_DESCRIPTIONS,
)


# Pull verbose metadata at import time. Cheap (~1ms) and lets callers do
# fast lookups without re-querying the builder on every call.
_FULL = _builder_catalog(verbose=True)
COMPONENT_CATALOG: dict[str, dict] = _FULL["component_meta"]
PICKS_FOR_CONTENT_KIND: dict[str, list[str]] = _FULL["picks_for_content_kind"]


# ---------------------------------------------------------------------------
# Public API — same shape as before, now backed by page-builder's registry
# ---------------------------------------------------------------------------
def list_components(kind: str | None = None) -> list[str]:
    """Return component names, optionally filtered by kind
    (text | data | card | structural)."""
    if kind is None:
        return sorted(COMPONENT_CATALOG.keys())
    return sorted(
        name for name, meta in COMPONENT_CATALOG.items()
        if meta.get("kind") == kind
    )


def describe(name: str) -> dict:
    """Return metadata for one component (raises if unregistered).

    Delegates to page-builder's describe_component() so a freshly added
    component is available the moment its registration runs.
    """
    return _builder_describe(name)


def picks_for_kind(content_kind: str) -> list[str]:
    """Quick lookup: given a content block kind, return candidate components.

    The mapping comes from each component's ``picks_content_kinds`` meta
    field. To register a new component as the picker for some kind, just
    add it in the component's metadata — this function picks it up.

    content_kind ∈ creator.content_drafter.CONTENT_BLOCK_SCHEMAS keys.
    """
    return PICKS_FOR_CONTENT_KIND.get(content_kind, [])[:]


def refresh() -> None:
    """Re-pull metadata from the page-builder. Call this if components are
    registered AFTER the creator package has been imported (rare — components
    register at module-import time)."""
    global COMPONENT_CATALOG, PICKS_FOR_CONTENT_KIND, _FULL
    _FULL = _builder_catalog(verbose=True)
    COMPONENT_CATALOG = _FULL["component_meta"]
    PICKS_FOR_CONTENT_KIND = _FULL["picks_for_content_kind"]


# ---------------------------------------------------------------------------
# Category helpers — expose the 8-category grouping for layout planning.
# Categories are: stats, text-paragraph, text-list, card, visual,
#                 table, chart, diagram.
# ---------------------------------------------------------------------------

CATEGORIES: dict[str, str] = dict(_CATEGORY_DESCRIPTIONS)
COMPONENT_TO_CATEGORY: dict[str, str] = dict(_COMPONENT_CATEGORIES)


def list_categories() -> list[str]:
    """Return the 8 category names in canonical order."""
    return list(_CATEGORY_DESCRIPTIONS.keys())


def list_components_by_category(category: str) -> list[str]:
    """Return all component names in a given category (sorted).

    Use this when planning a slide: 'I need a chart' → list_components_by_category('chart').
    """
    if category not in CATEGORIES:
        raise ValueError(
            f"unknown category: {category!r}; valid: {list_categories()}"
        )
    return sorted(
        n for n, c in COMPONENT_TO_CATEGORY.items() if c == category
    )


def by_category() -> dict:
    """Return components grouped by category — primary protocol surface
    for the LAYOUT phase. Each category lists its components with full
    metadata (role, kind, schema_brief, best_col_spans, good_for, bad_for).

    Returns the same shape as page-builder's ``catalog_by_category()``.
    """
    return _builder_by_category(verbose=True)


def markdown() -> str:
    """Return the full component catalog as markdown — useful for embedding
    in prompts or saving as a reference doc.

    The markdown groups components by category, lists each component's
    role/schema/best_col_spans/use cases, and ends with a reverse-lookup
    section (content kind → component picks).
    """
    return _builder_markdown()

