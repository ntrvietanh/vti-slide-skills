"""
Grid helpers — utilities for composing a 12-col × N-row grid descriptor.

Used by the creator's compose step (Phase 5.3) to lay out picked
components into a slide_input descriptor that compose_slide_grid()
can consume.
"""
from __future__ import annotations
from typing import Any


# ---------------------------------------------------------------------------
# Column-span splitters
# ---------------------------------------------------------------------------
EVEN_SPLITS: dict[int, list[tuple[int, int]]] = {
    # n: list of (col_start, col_span) tuples covering full 12-col row
    1: [(1, 12)],
    2: [(1, 6),  (7, 6)],
    3: [(1, 4),  (5, 4),  (9, 4)],
    4: [(1, 3),  (4, 3),  (7, 3),  (10, 3)],
    # 5 doesn't divide 12 evenly. Use 2-3-2-3-2 (or 3-2-2-2-3).
    5: [(1, 3),  (4, 2),  (6, 3),  (9, 2),  (11, 2)],
    6: [(1, 2),  (3, 2),  (5, 2),  (7, 2),  (9, 2),  (11, 2)],
}


def even_split(n: int) -> list[tuple[int, int]]:
    """Return col_start + col_span tuples for N equal-width cells.

    Raises ValueError if N is unsupported (1-6).
    """
    if n not in EVEN_SPLITS:
        raise ValueError(
            f"even_split supports n=1..6, got n={n}. "
            f"For 7+ peers, split across multiple rows."
        )
    return EVEN_SPLITS[n][:]


def asymmetric_split(spans: list[int]) -> list[tuple[int, int]]:
    """Given desired widths [5, 7] → [(1, 5), (6, 7)].

    Raises ValueError if sum > 12 or any span < 1 or > 12.
    """
    total = sum(spans)
    if total > 12:
        raise ValueError(
            f"asymmetric_split: sum of spans is {total}, must be ≤ 12"
        )
    if any(s < 1 or s > 12 for s in spans):
        raise ValueError(f"asymmetric_split: each span must be 1..12, got {spans}")
    cells: list[tuple[int, int]] = []
    cursor = 1
    for span in spans:
        cells.append((cursor, span))
        cursor += span
    return cells


def with_divider(left_span: int, divider_span: int,
                 right_span: int) -> list[tuple[int, int]]:
    """Convenience for compare-mirror rows: left + divider + right.

    Validates total == 12. Returns 3 (col_start, col_span) tuples.
    """
    return asymmetric_split([left_span, divider_span, right_span])


# ---------------------------------------------------------------------------
# Cell + Row constructors
# ---------------------------------------------------------------------------
def make_cell(col_start: int, col_span: int,
              component: str, props: dict[str, Any]) -> dict[str, Any]:
    """Construct a cell dict for compose_slide_grid()."""
    return {
        "col_start": col_start,
        "col_span":  col_span,
        "component": component,
        "props":     props,
    }


def make_row(height: str, cells: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct a row dict for compose_slide_grid()."""
    return {"height": height, "cells": cells}


# ---------------------------------------------------------------------------
# Common row patterns
# ---------------------------------------------------------------------------
# Note: there is no `header_row()`. Section + per-slide title belong on
# `slide_meta.section_name` + `slide_meta.slide_title` and ride the chrome
# breadcrumb. Content rows are reserved for real content blocks.

def narrative_row(paragraphs: list[str], height: str = "auto",
                  align: str = "left", max_width: str = "") -> dict[str, Any]:
    """A row with a single full-width narrative-paragraph."""
    props: dict[str, Any] = {"paragraphs": paragraphs, "align": align}
    if max_width:
        props["max_width"] = max_width
    return make_row(height, [
        make_cell(1, 12, "narrative-paragraph", props)
    ])


def stat_plus_narrative_row(stat_props: dict, narrative_props: dict,
                            stat_left: bool = True,
                            stat_span: int = 5,
                            height: str = "1fr") -> dict[str, Any]:
    """Common asymmetric pattern: stat-hero + narrative-paragraph in one row.

    By default stat goes left (5 cols) + narrative right (7 cols).
    """
    narrative_span = 12 - stat_span
    if stat_left:
        cells = [
            make_cell(1,             stat_span,      "stat-hero",            stat_props),
            make_cell(stat_span + 1, narrative_span, "narrative-paragraph",  narrative_props),
        ]
    else:
        cells = [
            make_cell(1,                  narrative_span, "narrative-paragraph",  narrative_props),
            make_cell(narrative_span + 1, stat_span,      "stat-hero",            stat_props),
        ]
    return make_row(height, cells)


def cards_row(component: str, cards_props: list[dict],
              height: str = "auto") -> dict[str, Any]:
    """Even-split row of N peer cards (practice-card / value-medallion / etc.).

    Number of cards must be 1..6.
    """
    splits = even_split(len(cards_props))
    cells = [
        make_cell(col_start, col_span, component, props)
        for (col_start, col_span), props in zip(splits, cards_props)
    ]
    return make_row(height, cells)


def kpi_strip_row(items: list[dict], height: str = "auto") -> dict[str, Any]:
    """Full-width kpi-row containing 2-5 stat-mini items."""
    return make_row(height, [
        make_cell(1, 12, "kpi-row", {"items": items})
    ])


# ---------------------------------------------------------------------------
# Slide constructor
# ---------------------------------------------------------------------------
def make_slide(slide_meta: dict, rows: list[dict]) -> dict:
    """Wrap rows + meta into the slide_input dict expected by composer."""
    return {"slide_meta": slide_meta, "rows": rows}
