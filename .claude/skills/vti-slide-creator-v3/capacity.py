"""
Capacity model — single source of truth for char limits across phases.

Resolves the v3.13 gap (#27): SKILL Phase 2 budget table used 200 chars/col
for narrative cells, but page-builder declared 80 chars/col. Phase 4 drafted
to the looser target, Phase 5 audited at the tighter target, 15/16 slides
flagged overflow.

This module exposes the page-builder's declared values directly so all phases
agree on capacity. Three levels of strictness:

1. ``cell_capacity(component, col_span)``
   The maximum chars a cell can hold without overflow. From declared
   ``capacity_chars_fixed`` (e.g. ``kpi-row=200``) or
   ``capacity_chars_per_col × col_span`` (e.g. ``narrative-paragraph=80×7=560``).
   This is the soft "target before overflow" — Phase 5 wireframe widget
   flags red when chars > capacity.

2. ``cell_target(component, col_span, ratio=0.85)``
   Phase 4 drafting target — chars to aim for when drafting content.
   Default 85% of capacity gives breathing room.

3. ``BLOCK_KIND_CAPS``
   Hard caps enforced at compose time by individual render functions.
   Each block kind has per-sub-field limits (e.g. ``narrative.paragraphs[]≤400``,
   ``hero_stat.label≤30``, ``features_3.cards[].body≤220``). These are
   ABSOLUTE — exceeding them raises ValidationError at compose. Phase 4
   ``validate_block`` now enforces these so drafts never reach a doomed
   compose.

Usage
-----
::

    from capacity import cell_capacity, cell_target, BLOCK_KIND_CAPS

    # Phase 2 layout planning
    cap = cell_capacity('narrative-paragraph', 7)   # 560
    target = cell_target('narrative-paragraph', 7)  # 476

    # Phase 4 drafting — limits per block kind
    BLOCK_KIND_CAPS['narrative']['paragraphs_each_max']  # 400
    BLOCK_KIND_CAPS['features_3']['card_body_max']       # 220
"""
from __future__ import annotations

from component_catalog import describe, COMPONENT_CATALOG


# ---------------------------------------------------------------------------
# Cell-level capacity (from page-builder declared metadata)
# ---------------------------------------------------------------------------
def cell_capacity(component: str, col_span: int) -> int:
    """Return the soft capacity (chars before overflow) for a cell.

    Reads ``capacity_chars_fixed`` if declared (kpi-row, stat-hero, etc.),
    else falls back to ``capacity_chars_per_col × col_span``.

    Raises KeyError if component is not registered.
    """
    if col_span < 1 or col_span > 12:
        raise ValueError(f"col_span must be 1..12, got {col_span}")
    meta = describe(component)  # raises if unregistered
    fixed = meta.get("capacity_chars_fixed")
    if fixed is not None:
        return int(fixed)
    per_col = meta.get("capacity_chars_per_col", 80)
    return int(per_col) * col_span


def cell_target(component: str, col_span: int, ratio: float = 0.85) -> int:
    """Phase 4 target — drafting goal, default 85% of capacity."""
    if not 0.4 <= ratio <= 1.1:
        raise ValueError(f"ratio must be 0.4..1.1, got {ratio}")
    return int(cell_capacity(component, col_span) * ratio)


# ---------------------------------------------------------------------------
# v3.18 — Density modes (closes gap #23 and creator-side scope of gap #32)
# ---------------------------------------------------------------------------
# Three named drafting/audit profiles. Each defines:
#   - target_ratio: cell_target multiplier (Phase 4 drafting goal)
#   - bands:        (sparse_below, ok_below_low, ok_below_high, overflow_above)
#                   used by audit_plan_density to flag cells. Char fill
#                   percentage is compared against these to set:
#                     fill < sparse_below     → flag = 'major-thin'
#                     fill < ok_below_low     → flag = 'thin'
#                     fill <= ok_below_high   → flag = 'ok'
#                     fill > overflow_above   → flag = 'overflow'
#   - sparse_avg:   slide-level avg-fill below this triggers SPARSE flag
#   - overcrowded_avg: slide-level avg-fill above this triggers OVERCROWDED
#
# 'sparse-ok' relaxes the lower bands so legitimate hero/breathing slides
# don't false-flag. 'dense' tightens the upper band for info-rich decks
# where >80% fill is the design intent.
#
# IMPORTANT — scope of this toggle:
# This affects DRAFTING TARGETS and AUDIT THRESHOLDS only. The page-builder
# component-level HARD caps in BLOCK_KIND_CAPS are NOT relaxed — those
# are absolute render-time invariants. Gap #32's full architectural fix
# would also relax page-builder caps; that requires page-builder skill
# changes and is OUT OF CREATOR SCOPE. Document this if a user asks why
# 'dense' mode still rejects a 500-char paragraph.
DENSITY_MODES: dict[str, dict] = {
    "standard": {
        "target_ratio":    0.85,
        "bands":           (50, 70, 100, 100),
        "sparse_avg":      40,
        "overcrowded_avg": 110,
        "description": (
            "Default — Phase 4 drafts to 85% of cell capacity, audit "
            "flags >100% as overflow, <50% as major-thin, <40% slide "
            "avg as SPARSE. Use for typical executive/case-study decks."
        ),
    },
    "sparse-ok": {
        "target_ratio":    0.65,
        "bands":           (25, 45, 100, 105),
        "sparse_avg":      20,
        "overcrowded_avg": 110,
        "description": (
            "Hero / breathing-room mode. Phase 4 drafts to 65% of "
            "capacity (intentional whitespace), audit tolerates fills "
            "down to 25% before flagging major-thin, slide-avg SPARSE "
            "threshold is 20%. Use for cover-style, single-stat-focal, "
            "or quote-driven slides where empty space is intentional."
        ),
    },
    "dense": {
        "target_ratio":    0.95,
        "bands":           (60, 80, 110, 115),
        "sparse_avg":      55,
        "overcrowded_avg": 120,
        "description": (
            "Information-rich mode. Phase 4 drafts to 95% of capacity, "
            "audit allows up to 110% before overflow, slide-avg SPARSE "
            "threshold rises to 55%. Use for technical-detail slides, "
            "spec sheets, or any deck where dense legibility is the "
            "explicit goal. NOTE: BLOCK_KIND_CAPS hard caps are NOT "
            "relaxed — see source comment for details."
        ),
    },
}


def density_mode_for(name: str) -> dict:
    """v3.18 — Look up a density mode profile by name.

    Raises ValueError on unknown name.
    """
    if name not in DENSITY_MODES:
        raise ValueError(
            f"unknown density_mode '{name}'; "
            f"valid: {sorted(DENSITY_MODES.keys())}"
        )
    return dict(DENSITY_MODES[name])


def cell_target_mode(component: str, col_span: int,
                     density_mode: str = "standard") -> int:
    """v3.18 — Like ``cell_target`` but parameterized by named density mode.

    Closes gap #23: instead of a magic 0.85 ratio, callers pick a mode
    that matches the deck's visual intent. Equivalent to
    ``cell_target(component, col_span, ratio=DENSITY_MODES[density_mode]['target_ratio'])``
    but named for readability.
    """
    profile = density_mode_for(density_mode)
    return cell_target(component, col_span, ratio=profile["target_ratio"])


# ---------------------------------------------------------------------------
# Block-kind hard caps (extracted from page-builder render-time validators)
#
# These are the LIMITS each component's `_r_<name>` function checks via
# `_check_max_chars()` — exceeding them raises ValidationError at compose
# time. Phase 4 validate_block() now enforces them so drafts never reach a
# doomed compose.
# ---------------------------------------------------------------------------
BLOCK_KIND_CAPS: dict[str, dict] = {
    # ---- text -------------------------------------------------------------
    "narrative": {
        "paragraphs_count_min": 1,
        "paragraphs_count_max": 4,
        "paragraphs_each_max":  400,   # narrative-paragraph
    },
    "list": {
        "items_count_min": 2,
        "items_count_max": 8,
        "items_each_max":  100,        # bullet-list-checked
    },

    # ---- data -------------------------------------------------------------
    "hero_stat": {
        "value_max": 8,                # stat-hero.value
        "label_max": 30,               # stat-hero.label
    },
    "supporting_stats": {
        "items_count_min": 2,
        "items_count_max": 5,
        "item_value_max":  8,          # stat-mini.value
        "item_label_max":  30,         # stat-mini.label
    },

    # ---- card -------------------------------------------------------------
    "features_3": {
        "cards_count_min":   3,
        "cards_count_max":   3,
        "card_title_max":   28,        # practice-card.title
        "card_body_max":   220,        # practice-card.body
    },
    "values": {
        "cards_count_min":      4,
        "cards_count_max":      6,
        "card_title_max":      22,     # value-medallion.title
        "card_tagline_max":    60,
        "card_number_max":      4,
    },
    "catalog": {
        "columns_count_min":    2,
        "columns_count_max":    3,
        "column_label_max":    24,     # catalog-column.label
        "column_item_text_max": 80,
        "column_item_tag_max":  16,
    },

    # ---- structural -------------------------------------------------------
    "comparison_divider": {
        "label_max": 6,                # vs-divider.label
    },

    # ---- visual blocks (v3.16) -------------------------------------------
    "image_tile": {
        "caption_max": 120,            # image-tile.caption
    },
    "process_flow": {
        "steps_count_min":   3,
        "steps_count_max":   7,
        "step_title_max":   30,        # process-flow.steps[].title
        "step_body_max":   140,        # process-flow.steps[].body
    },
    "bar_chart": {
        "items_count_min":  2,
        "items_count_max": 12,
        "item_label_max":  40,
    },
    "pie_chart": {
        "items_count_min":  2,
        "items_count_max":  8,
        "item_label_max":  30,
        "center_value_max": 8,
        "center_label_max": 24,
    },
    "logo_grid": {
        "logos_count_min":  2,
        "logos_count_max": 18,
        "logo_name_max":   30,
    },
    "icon_list": {
        "items_count_min":  3,
        "items_count_max": 12,
        "item_title_max": 30,
        "item_body_max":  100,
    },
}


# ---------------------------------------------------------------------------
# Visual-vs-text classification (v3.16) — used by audit_visual_balance().
# A "visual block" carries meaning the eye reads in 2 seconds without prose.
# ---------------------------------------------------------------------------
VISUAL_BLOCK_KINDS = {
    "image_tile",        # photographic / mockup evidence
    "process_flow",      # ordered sequence diagram
    "bar_chart",         # data viz
    "pie_chart",         # share-of-total
    "logo_grid",         # proof signals
    "icon_list",         # parallel items at-a-glance
    "values",            # 4-6 medallions
    "catalog",           # categorized columns w/ icons
    "hero_stat",         # one big number is visual
    "supporting_stats",  # kpi-row visuals
    "comparison_divider",
}

TEXT_BLOCK_KINDS = {
    "narrative",
    "list",
    "features_3",        # 3 cards w/ heavy body text
}


def is_visual_block(kind: str) -> bool:
    """v3.16 — True if block kind contributes a visual element to the slide."""
    return kind in VISUAL_BLOCK_KINDS


def block_kind_caps(kind: str) -> dict:
    """Return cap dict for a block kind. Raises if kind unknown."""
    if kind not in BLOCK_KIND_CAPS:
        raise ValueError(
            f"unknown block kind '{kind}'; "
            f"valid: {sorted(BLOCK_KIND_CAPS.keys())}"
        )
    return dict(BLOCK_KIND_CAPS[kind])


# ---------------------------------------------------------------------------
# Layout sketch capacity helper — used by Phase 2 to size budgets
# ---------------------------------------------------------------------------
def layout_sketch_capacity(cells: list[tuple[str, int]]) -> dict:
    """Estimate total + per-cell capacity for a layout sketch.

    Args:
        cells: list of (component_name, col_span) tuples representing
               cells across all rows of the slide.

    Returns:
        ``{'total_capacity': int, 'total_target': int, 'per_cell': [...]}``

    Example::

        layout_sketch_capacity([
            ('stat-hero', 5),
            ('narrative-paragraph', 7),
            ('kpi-row', 12),
        ])
        # {'total_capacity': 800, 'total_target': 680, 'per_cell': [...]}
    """
    per_cell = []
    total_cap = 0
    total_tgt = 0
    for component, col_span in cells:
        cap = cell_capacity(component, col_span)
        tgt = cell_target(component, col_span)
        per_cell.append({
            "component": component,
            "col_span":  col_span,
            "capacity":  cap,
            "target":    tgt,
        })
        total_cap += cap
        total_tgt += tgt
    return {
        "total_capacity": total_cap,
        "total_target":   total_tgt,
        "per_cell":       per_cell,
    }
