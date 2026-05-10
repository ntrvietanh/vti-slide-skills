"""
Cross-phase consistency checks + content-fitting helpers.

Closes gaps #30 (no cross-phase validator) and #31 (no paragraph
splitter). Provides:

- ``validate_for_compose(plans)`` — Phase 4 → Phase 5 dry-run check.
  For each plan, walks every block and returns the list of compose-time
  violations BEFORE Phase 5 attempts to render. Catches the class of
  failure that previously surfaced only at compose: ``[chars_exceeded]``,
  ``[missing_required]``, etc.

- ``split_long_paragraphs(content, max_per_para=400)`` — narrative-block
  helper. Takes a ``narrative`` block content and splits any paragraph
  longer than ``max_per_para`` into multiple smaller paragraphs at
  sentence boundaries. Preserves total density without violating the
  per-paragraph hard cap.

- ``deck_density_summary(plans)`` — programmatic stats for evaluation
  scripts: how many blocks, total chars, density distribution.
"""
from __future__ import annotations

import re
from typing import Iterable

from content_drafter import validate_block, CONTENT_BLOCK_SCHEMAS


# ---------------------------------------------------------------------------
# Visual-balance audit (v3.16) — closes Principle 8 enforcement
# ---------------------------------------------------------------------------
def audit_visual_balance(plans: list,
                         warn_threshold: float = 0.60,
                         block_threshold: float = 0.40) -> dict:
    """v3.16 — Per-deck check: enough slides carry visual elements.

    A slide is "visual-bearing" if any of:
      - has a block kind in `capacity.VISUAL_BLOCK_KINDS`
      - image_decision.kind in ('lift', 'synthesize')

    Args:
        plans: list of SlideContentPlan dicts
        warn_threshold: visual_pct below this → 'warn' (default 60%)
        block_threshold: visual_pct below this → 'block' (default 40%)

    Returns::

        {
          'visual_count':       int,
          'text_only_count':    int,
          'visual_pct':         float (0-100),
          'flag':               'ok'|'warn'|'block',
          'text_only_slides':   [slide_id, ...],
          'recommendations':    [{slide_id, current_blocks, suggestion}, ...],
        }

    Use this as a gate between Phase 4 and Phase 5: if flag != 'ok',
    revisit Phase 2 outline and increase visual diversity.
    """
    from capacity import VISUAL_BLOCK_KINDS

    visual_count = 0
    text_only = []
    recommendations = []

    for plan in plans:
        sid = plan.get("slide_id", "?")
        kinds = [b.get("kind", "") for b in plan.get("blocks", [])]
        img_decision = plan.get("image_decision", {})
        img_strategy = img_decision.get("strategy", "") if isinstance(img_decision, dict) else ""

        has_visual_block = any(k in VISUAL_BLOCK_KINDS for k in kinds)
        has_image_strategy = img_strategy in ("lift", "synthesize")

        if has_visual_block or has_image_strategy:
            visual_count += 1
        else:
            text_only.append(sid)
            recommendations.append({
                "slide_id":       sid,
                "current_blocks": kinds,
                "suggestion":     _suggest_visual_for(kinds),
            })

    total = len(list(plans))
    text_only_count = len(text_only)
    visual_pct = (visual_count / total * 100) if total else 0.0

    if visual_pct < block_threshold * 100:
        flag = "block"
    elif visual_pct < warn_threshold * 100:
        flag = "warn"
    else:
        flag = "ok"

    return {
        "visual_count":     visual_count,
        "text_only_count":  text_only_count,
        "visual_pct":       round(visual_pct, 1),
        "flag":             flag,
        "text_only_slides": text_only,
        "recommendations":  recommendations,
    }


# ---------------------------------------------------------------------------
# Block-kind distribution audit (v3.18 — closes gap #22)
# ---------------------------------------------------------------------------
def audit_block_distribution(plans: list,
                             dominant_threshold: float = 0.50) -> dict:
    """v3.18 — Per-deck block-kind census + anti-pattern detection.

    Where ``audit_visual_balance`` answers "are there enough visual
    slides", this answers "what's the *shape* of the deck content-wise".
    A deck where 50%+ of blocks are a single kind is monotone, even if
    the visual ratio is technically passing (e.g. 8 narrative + 8
    image_tile = 50/50 visual but visually monotone because every image
    slide looks identical).

    Args:
        plans: list of SlideContentPlan dicts
        dominant_threshold: fraction above which a single kind triggers
                            'dominant_kind_overuse' anti-pattern flag
                            (default 0.50 = 50%)

    Returns::

        {
          'total_blocks':        int,
          'kinds_used':          int (distinct count),
          'visual_kinds':        {kind: count, ...},     # subset
          'text_kinds':          {kind: count, ...},     # subset
          'visual_block_pct':    float (0-100),          # visual blocks / total
          'dominant_kind':       (kind, count, pct) | None,
          'anti_pattern_flags':  ['dominant_kind_overuse', 'all_text_blocks',
                                  'no_charts', 'no_process_flows', ...],
          'recommendations':     [str, ...],
        }

    Use this complementary to ``audit_visual_balance`` — that audits
    *slide* visual ratio, this audits *block* distribution. Both can
    pass while the deck still feels monotone. v3.16 added Principle 8
    visual ratio; v3.18 adds the per-kind distribution view requested
    by gap #22.

    Anti-patterns detected:

    - ``dominant_kind_overuse``: one kind > ``dominant_threshold``
    - ``all_text_blocks``: 0 blocks in VISUAL_BLOCK_KINDS
    - ``no_charts``: 0 blocks of bar_chart/pie_chart
    - ``no_process_flows``: 0 process_flow blocks (signals no
      sequence/journey content — usually a missed opportunity)
    - ``narrative_heavy``: narrative blocks > 40% of all blocks
      (storytelling-only deck pattern — should mix with stat/chart)
    """
    from capacity import VISUAL_BLOCK_KINDS, TEXT_BLOCK_KINDS

    by_kind: dict[str, int] = {}
    for p in plans:
        for b in p.get("blocks", []):
            kind = b.get("kind", "?")
            by_kind[kind] = by_kind.get(kind, 0) + 1
    total = sum(by_kind.values())

    visual_kinds = {k: c for k, c in by_kind.items() if k in VISUAL_BLOCK_KINDS}
    text_kinds   = {k: c for k, c in by_kind.items() if k in TEXT_BLOCK_KINDS}
    visual_block_count = sum(visual_kinds.values())
    visual_block_pct = (visual_block_count / total * 100) if total else 0.0

    dominant = None
    if by_kind:
        top_kind, top_count = max(by_kind.items(), key=lambda kv: kv[1])
        top_pct = top_count / total
        if top_pct > dominant_threshold:
            dominant = (top_kind, top_count, round(top_pct * 100, 1))

    flags: list[str] = []
    recs: list[str] = []
    if dominant:
        flags.append("dominant_kind_overuse")
        recs.append(
            f"'{dominant[0]}' is {dominant[2]}% of blocks "
            f"(>{dominant_threshold*100:.0f}%) — diversify with other kinds"
        )
    if visual_block_count == 0 and total > 0:
        flags.append("all_text_blocks")
        recs.append(
            "no visual blocks at all — add image_tile / process_flow / "
            "bar_chart / icon_list to at least 60% of slides"
        )
    if not (by_kind.get("bar_chart", 0) + by_kind.get("pie_chart", 0)):
        flags.append("no_charts")
        recs.append(
            "no charts in deck — if any slide has 3+ stats, "
            "consider bar_chart / pie_chart instead of supporting_stats"
        )
    if by_kind.get("process_flow", 0) == 0:
        flags.append("no_process_flows")
        # No rec — sometimes legitimately absent; just flag for awareness.
    narrative_count = by_kind.get("narrative", 0)
    if total and narrative_count / total > 0.40:
        flags.append("narrative_heavy")
        recs.append(
            f"narrative is {narrative_count/total*100:.0f}% of blocks — "
            "mix in icon_list / bar_chart to break storytelling monotony"
        )

    return {
        "total_blocks":       total,
        "kinds_used":         len(by_kind),
        "visual_kinds":       visual_kinds,
        "text_kinds":         text_kinds,
        "visual_block_pct":   round(visual_block_pct, 1),
        "dominant_kind":      dominant,
        "anti_pattern_flags": flags,
        "recommendations":    recs,
    }


def _suggest_visual_for(kinds: list) -> str:
    """Heuristic suggestion for converting a text-only slide to visual."""
    s = set(kinds)
    if "narrative" in s and ("hero_stat" in s or "supporting_stats" in s):
        # Case-study / metric-narrative shape → lift screenshots or chart the metrics
        return ("Add image_tile (lift screenshots from source) "
                "OR replace supporting_stats with bar_chart")
    if "features_3" in s and len(kinds) >= 2 and kinds.count("features_3") >= 2:
        # Multiple features_3 → too many cards, switch to icon_list
        return "Replace stacked features_3 with icon_list (compact density)"
    if "list" in s and "narrative" not in s:
        # Pure list → most lists are better as logos/icons
        return ("Replace bullet-list with logo_grid (if items are entities) "
                "or icon_list (if items have labels+icons)")
    if "narrative" in s and len(s) == 1:
        # Pure narrative — needs visual companion
        return "Add image_tile (lift) or process_flow if message is sequential"
    if "features_3" in s:
        return "Pair features_3 with image_tile or replace with icon_list"
    return "Add image_tile, process_flow, bar_chart, pie_chart, or logo_grid"


# ---------------------------------------------------------------------------
# Cross-phase validator
# ---------------------------------------------------------------------------
def validate_for_compose(plans: Iterable[dict]) -> dict:
    """Dry-run Phase 4 → Phase 5: for each plan, surface every block-level
    violation that would fail compose.

    Returns::

        {
            'ok': bool,
            'violation_count': int,
            'plan_results': [
                {'slide_id': '...', 'ok': bool, 'errors': [...]},
                ...
            ]
        }

    Use BEFORE Phase 5 wireframe to bounce drafts that can't compose.
    """
    plan_results = []
    total_violations = 0
    for plan in plans:
        sid = plan.get("slide_id", "?")
        plan_errs: list[str] = []
        for i, block in enumerate(plan.get("blocks", [])):
            ok, errs = validate_block(block)
            if not ok:
                for e in errs:
                    plan_errs.append(f"blocks[{i}] ({block.get('kind','?')}): {e}")
        plan_results.append({
            "slide_id": sid,
            "ok":       len(plan_errs) == 0,
            "errors":   plan_errs,
        })
        total_violations += len(plan_errs)
    return {
        "ok":               total_violations == 0,
        "violation_count":  total_violations,
        "plan_results":     plan_results,
    }


# ---------------------------------------------------------------------------
# Paragraph splitter — preserves density while satisfying per-paragraph cap
# ---------------------------------------------------------------------------
_SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z\u201C"])')
# Sub-clause boundaries — em-dash, semicolon, colon followed by space
_SUBCLAUSE_BREAK = re.compile(r'(?<=[\u2014;:])\s+')


def split_long_paragraphs(content: dict, max_per_para: int = 400,
                          target_per_para: int = 380,
                          max_paragraphs: int = 4) -> dict:
    """Split paragraphs longer than ``max_per_para`` at sentence boundaries.
    If a single sentence exceeds the cap, falls back to sub-clause splits
    at em-dashes / semicolons / colons.

    Packs aggressively (default target 380, just below max 400) to stay
    under ``max_paragraphs`` for the narrative-block schema.

    Args:
        content: a narrative block's content dict, e.g. ``{'paragraphs': [...]}``
        max_per_para: hard cap (default 400 — narrative-paragraph schema)
        target_per_para: split target (default 380 — tight under cap)
        max_paragraphs: max paragraphs in result (default 4 — narrative cap)

    Returns:
        New content dict with split paragraphs. Original is not mutated.

    Raises:
        ValueError if the content can't be packed under both the per-para
        cap AND the paragraph-count cap. In that case the layout sketch
        needs more space (12-col narrative cell, or two narrative rows).

    Example::

        # Phase 4 wrote a 700-char paragraph; cap is 400.
        new_content = split_long_paragraphs(narr_block['content'])
    """
    paras = list(content.get("paragraphs", []))
    out: list[str] = []
    for p in paras:
        if not isinstance(p, str) or len(p) <= max_per_para:
            out.append(p)
            continue
        out.extend(_split_one(p, max_per_para, target_per_para))
    if len(out) > max_paragraphs:
        # Try repacking with target=max_per_para to squeeze fewer paragraphs
        all_units: list[str] = []
        for p in paras:
            if not isinstance(p, str): continue
            if len(p) <= max_per_para:
                all_units.append(p)
            else:
                all_units.extend(_split_one(p, max_per_para, max_per_para))
        # Greedy pack again at max
        repacked: list[str] = []
        current = ""
        for u in all_units:
            sep = " " if current else ""
            if len(current) + len(sep) + len(u) <= max_per_para:
                current = current + sep + u
            else:
                if current: repacked.append(current)
                current = u
        if current: repacked.append(current)
        if len(repacked) <= max_paragraphs:
            out = repacked
        else:
            total = sum(len(p) for p in paras if isinstance(p, str))
            raise ValueError(
                f"split_long_paragraphs: total content {total} chars cannot "
                f"fit in {max_paragraphs} paragraphs of {max_per_para} chars "
                f"each ({max_paragraphs * max_per_para} max). "
                f"Layout needs more space (try 12-col narrative cell, or "
                f"split into two narrative rows)."
            )
    new = dict(content)
    new["paragraphs"] = out
    return new


def _split_one(text: str, max_per_para: int, target_per_para: int) -> list[str]:
    """Split one long paragraph into multiple ≤max_per_para chunks."""
    # First pass: split at sentence boundaries
    sentences = _SENTENCE_END.split(text)
    # If any sentence still exceeds max, split it at sub-clause boundaries
    units: list[str] = []
    for s in sentences:
        if len(s) <= max_per_para:
            units.append(s)
            continue
        sub = _SUBCLAUSE_BREAK.split(s)
        if all(len(u) <= max_per_para for u in sub):
            units.extend(sub)
        else:
            # Last resort: hard-split at word boundaries near target
            units.extend(_word_split(s, target_per_para))
    # Greedy pack into target-sized paragraphs
    out: list[str] = []
    current = ""
    for u in units:
        sep = " " if current else ""
        if len(current) + len(sep) + len(u) <= target_per_para:
            current = current + sep + u
        else:
            if current:
                out.append(current)
            current = u
    if current:
        out.append(current)
    # Final safety: confirm everything fits
    for o in out:
        if len(o) > max_per_para:
            raise ValueError(
                f"split_long_paragraphs: post-split unit still exceeds "
                f"max ({len(o)} > {max_per_para}). Starts: {o[:60]!r}…"
            )
    return out


def _word_split(text: str, target: int) -> list[str]:
    """Last-resort word-boundary split (no clean sentence/clause boundary)."""
    words = text.split(" ")
    out: list[str] = []
    current = ""
    for w in words:
        sep = " " if current else ""
        if len(current) + len(sep) + len(w) <= target:
            current = current + sep + w
        else:
            if current:
                out.append(current)
            current = w
    if current:
        out.append(current)
    return out


# ---------------------------------------------------------------------------
# Density summary — programmatic stats
# ---------------------------------------------------------------------------
def deck_density_summary(plans: Iterable[dict]) -> dict:
    """Aggregate density stats across a deck. Useful for QA scripts."""
    plans_list = list(plans)
    total_blocks = 0
    total_chars  = 0
    by_kind: dict[str, int] = {}
    for p in plans_list:
        for b in p.get("blocks", []):
            kind = b.get("kind", "?")
            total_blocks += 1
            by_kind[kind] = by_kind.get(kind, 0) + 1
            total_chars += _block_text_chars(b)
    return {
        "plan_count":     len(plans_list),
        "block_count":    total_blocks,
        "blocks_by_kind": by_kind,
        "total_chars":    total_chars,
    }


# ---------------------------------------------------------------------------
# Per-plan density audit (#17-19, #23-25 — closes density-helper gap)
# ---------------------------------------------------------------------------
# Block kinds whose visual presence fills a cell regardless of char count.
# These contribute "presence" to fill-% but minimal chars. Treated as 100%
# of their cell capacity for fill-% purposes, regardless of actual content
# length.
#
# v3.18.1 — sync with the canonical capacity.VISUAL_BLOCK_KINDS (closes
# stale-set bug exposed by audit_block_distribution rerun on v5 plans).
# Pre-v3.18.1 this set was {"hero_stat", "supporting_stats"} only — a
# v3.14 leftover never updated when v3.16 promoted process_flow /
# bar_chart / pie_chart / logo_grid / icon_list / image_tile / values /
# catalog / comparison_divider to first-class visual block kinds. The
# audit was measuring those as text-density, false-flagging visually-
# full slides as SPARSE because their text payloads are short labels.
#
# Caveat for icon_list / values / catalog: these have text payload per
# item (~50 chars × 4-6 items). They DO contribute readable text. But
# the audit's role is to detect "this slide will look empty" — and a
# logo grid / icon row visually fills its cell regardless of caption
# length. Treating them as visual-fill is the conservative choice.
# Per-item char caps are still enforced by validate_block.
_VISUAL_FILL_KINDS = {
    "hero_stat", "supporting_stats",
    "process_flow", "bar_chart", "pie_chart",
    "logo_grid", "icon_list", "image_tile",
    "values", "catalog", "comparison_divider",
}

# Block kinds that compete linearly with cell width for char density.
# These ARE measured by char-count fill-%. Note: features_3 is included
# even though it has a card-grid visual structure — its 3 cards carry
# substantial body text (~220 chars each cap), so char fill is a
# meaningful signal. v3.18.1: removed values + catalog (now in visual-
# fill set; their text caps are enforced separately).
_TEXT_DENSE_KINDS = {"narrative", "list", "features_3"}


def audit_plan_density(plan: dict,
                       layout: list[tuple[str, int]] | None = None,
                       density_mode: str | None = None,
                       expand: bool | None = None) -> dict:
    """Audit text-density of a SlideContentPlan against a planned layout.

    Args:
        plan: SlideContentPlan dict (with `slide_id`, `blocks`, etc.)
        layout: ordered list of (component_name, col_span) tuples
                describing the cells the plan will compose into. Order
                must match the order the plan's blocks will produce
                (one cell per relevant block, in `plan.blocks` order).
                v3.19 — pass ``None`` to auto-derive from the plan via
                ``expand_plan_for_audit()`` (handles features_3 / values
                / catalog expansion correctly).
        density_mode: v3.18 (closes gap #23) — one of 'standard',
                      'sparse-ok', 'dense'. Adjusts the cell-fill bands
                      and slide-avg SPARSE/OVERCROWDED thresholds. If
                      None, reads ``plan.get('density_mode')`` and
                      falls back to 'standard'. Use 'sparse-ok' for
                      breathing-room/hero slides; 'dense' for info-rich
                      detail slides. See ``capacity.DENSITY_MODES``.
        expand: v3.19 (closes gap #42) — when True, expand expansion-kind
                blocks (features_3, values, catalog) into per-cell
                pseudo-blocks before auditing. When False, use legacy
                1:1 block-to-cell mode (caller's responsibility to
                supply a matching layout). When None (default), expand
                iff ``layout`` is None.

    Returns:
        ::

            {
                'slide_id': str,
                'cells': [
                    {
                        'block_idx': int,        # index in plan.blocks
                        'block_kind': str,
                        'component': str,
                        'col_span': int,
                        'capacity': int,         # from cell_capacity()
                        'chars': int,            # text chars in block
                        'fill_pct': int,         # 0-200+
                        'role': 'text'|'visual', # which audit tier
                        'flag': 'ok'|'thin'|'major-thin'|'overflow',
                    },
                    ...
                ],
                'flags': list[str],  # slide-level flags ('SPARSE', 'OVERFLOW', etc.)
                'overall_fill_pct': int,
            }

    The audit separates "visual fill" components (hero_stat, supporting_stats)
    from "text dense" components (narrative, list, cards). Visual blocks
    are assumed to fill their cells visually regardless of char count.

    Closes #17-19, #23-25 — pre-v3.14 the audit treated all blocks as
    text-dense, false-flagging hero/kpi cells as "MAJOR thin" because
    a 1-stat block contributes ~50 chars to a 200-cap cell.

    v3.18 — density_mode parameter (gap #23) lets sparse/dense decks
    use bands appropriate to their intent.

    v3.19 — expand parameter (gap #42) handles features_3 / values /
    catalog blocks that compose into multiple cells. When expand=True
    (or layout is None), the plan is auto-expanded via
    expand_plan_for_audit() so each card / value / column gets its own
    audit cell. When expand=False AND a literal layout is supplied,
    backward-compatible 1:1 mode is used.
    """
    from capacity import cell_capacity, density_mode_for

    # Resolve density_mode: explicit > plan-level > 'standard'
    if density_mode is None:
        density_mode = plan.get("density_mode") or "standard"
    profile = density_mode_for(density_mode)
    sparse_below, ok_low, ok_high, overflow_above = profile["bands"]
    slide_sparse_avg = profile["sparse_avg"]
    slide_overcrowded_avg = profile["overcrowded_avg"]

    # v3.19 — auto-expand when no explicit layout, or when expand=True.
    # When layout is a 1:1 layout (backward compat), auto-detect
    # expansion need: if any block's kind is in _EXPANSION_KINDS, the
    # caller probably wants expand=True; warn but do NOT auto-rewrite.
    expand_resolved = expand
    if expand_resolved is None:
        expand_resolved = (layout is None)

    if expand_resolved:
        blocks, layout = expand_plan_for_audit(plan)
    else:
        blocks = plan.get("blocks", [])

    if len(blocks) != len(layout):
        raise ValueError(
            f"audit_plan_density: layout has {len(layout)} cells but "
            f"{'expanded' if expand_resolved else 'plan'} has {len(blocks)} "
            f"blocks. They must align 1:1 in order. "
            f"Tip: pass expand=True (or omit layout) to auto-expand "
            f"features_3/values/catalog into per-cell pseudo-blocks."
        )
    cells_audit: list[dict] = []
    for idx, (b, (comp, span)) in enumerate(zip(blocks, layout)):
        kind = b.get("kind", "")
        chars = _block_text_chars_v319(b)
        cap = cell_capacity(comp, span)
        if kind in _VISUAL_FILL_KINDS:
            role = "visual"
            # Visual blocks fill visually; map to capacity-or-100% whichever
            # is smaller. Underfilled only if drafted item count is below
            # the schema minimum (catch by validate_block instead).
            fill = 100  # by definition fills its cell visually
        else:
            role = "text"
            fill = int((chars / cap) * 100) if cap else 0

        if role == "text":
            if fill > overflow_above:
                flag = "overflow"
            elif fill < sparse_below:
                flag = "major-thin"
            elif fill < ok_low:
                flag = "thin"
            else:
                flag = "ok"
        else:
            flag = "ok"  # visual blocks always ok for fill-% (cap is enforced separately)

        cells_audit.append({
            "block_idx":   idx,
            "block_kind":  kind,
            "component":   comp,
            "col_span":    span,
            "capacity":    cap,
            "chars":       chars,
            "fill_pct":    fill,
            "role":        role,
            "flag":        flag,
        })

    # Slide-level flags
    slide_flags: list[str] = []
    text_cells = [c for c in cells_audit if c["role"] == "text"]
    if text_cells:
        avg_text_fill = sum(c["fill_pct"] for c in text_cells) / len(text_cells)
        if avg_text_fill < slide_sparse_avg:
            slide_flags.append("SPARSE")
        elif avg_text_fill > slide_overcrowded_avg:
            slide_flags.append("OVERCROWDED")
    overflow_count = sum(1 for c in cells_audit if c["flag"] == "overflow")
    if overflow_count:
        slide_flags.append(f"OVERFLOW×{overflow_count}")
    thin_count = sum(1 for c in cells_audit if c["flag"] == "major-thin")
    if thin_count:
        slide_flags.append(f"THIN×{thin_count}")

    overall = int(sum(c["fill_pct"] for c in cells_audit) / len(cells_audit)) if cells_audit else 0
    return {
        "slide_id":         plan.get("slide_id", "?"),
        "cells":            cells_audit,
        "flags":            slide_flags,
        "overall_fill_pct": overall,
    }


def audit_deck_density(plans_or_pairs: list,
                       density_mode: str | None = None) -> dict:
    """Audit a whole deck.

    Two input forms accepted (v3.19):

    1. **List of plans** (recommended) — auto-expand each plan via
       ``expand_plan_for_audit``. Handles features_3/values/catalog
       expansion correctly without the caller building the layout.
    2. **List of (plan, layout) pairs** (legacy) — caller supplies an
       explicit layout per plan. The audit assumes 1:1 block:cell unless
       the layout was already pre-expanded.

    Returns aggregate stats + per-slide audits. Use after Phase 4 drafting,
    before Phase 5 wireframe, to flag content-fit issues at the right
    granularity.

    v3.18 — ``density_mode`` (gap #23). When set, applies to every
    plan as the default. Per-plan ``plan['density_mode']`` field
    overrides the deck-level default — so a deck can be 'standard'
    overall with a few cover/hero slides flagged 'sparse-ok'.

    v3.19 — accepts plain plan list (gap #42); auto-expand removes
    the harness boilerplate that v3.18 audits required.
    """
    per_slide = []
    overflow_slides = []
    thin_slides = []
    for entry in plans_or_pairs:
        # Detect legacy (plan, layout) tuple vs bare plan dict
        if isinstance(entry, tuple) and len(entry) == 2:
            plan, layout = entry
            eff_mode = plan.get("density_mode") or density_mode
            audit = audit_plan_density(plan, layout, density_mode=eff_mode,
                                        expand=False)
        else:
            plan = entry
            eff_mode = plan.get("density_mode") or density_mode
            audit = audit_plan_density(plan, layout=None,
                                        density_mode=eff_mode,
                                        expand=True)
        per_slide.append(audit)
        if any("OVERFLOW" in f for f in audit["flags"]):
            overflow_slides.append(audit["slide_id"])
        if "SPARSE" in audit["flags"]:
            thin_slides.append(audit["slide_id"])
    return {
        "slide_count":     len(per_slide),
        "overflow_count":  len(overflow_slides),
        "sparse_count":    len(thin_slides),
        "overflow_slides": overflow_slides,
        "sparse_slides":   thin_slides,
        "per_slide":       per_slide,
    }


# ---------------------------------------------------------------------------
# Density audit — per-cell fill % vs declared capacity
# ---------------------------------------------------------------------------
def audit_slide_density(slide_input: dict) -> dict:
    """v3.15 — Per-cell density audit on a composed slide_input.

    Walks every cell in the slide's rows, computes drafted chars vs declared
    capacity (from ``capacity.cell_capacity``), flags overflow / sparse.
    Closes gap #19 + #24 — previously the audit had to be hand-rolled in
    each session.

    Args:
        slide_input: dict from ``plan_to_slide_input`` or hand-built —
            shape ``{slide_meta, rows: [{height, cells: [...]}]}``.

    Returns::

        {
            'slide_id': str (from slide_meta.slide_title or '?'),
            'rows':     int,
            'cells':    int,
            'overflow_count': int,
            'sparse_count':   int,
            'cells_audit': [
                {
                    'row':          int (1-indexed),
                    'col_start':    int,
                    'col_span':     int,
                    'component':    str,
                    'drafted':      int,    # text chars actually present
                    'capacity':     int,    # cell_capacity()
                    'target':       int,    # cell_target()
                    'fill_pct':     float,  # drafted/capacity * 100
                    'flag':         '' | 'overflow' | 'sparse' | 'mild-thin'
                },
                ...
            ]
        }

    Special pages (``{special, props}``) skip the audit and return
    ``{'special': True, 'kind': name}``.
    """
    if 'special' in slide_input:
        return {'special': True, 'kind': slide_input['special']}

    from capacity import cell_capacity, cell_target

    cells_audit = []
    overflow_count = 0
    sparse_count = 0

    for row_idx, row in enumerate(slide_input.get('rows', []), start=1):
        for cell in row.get('cells', []):
            comp = cell.get('component', '')
            col_span = cell.get('col_span', 12)
            col_start = cell.get('col_start', 1)
            try:
                cap = cell_capacity(comp, col_span)
                tgt = cell_target(comp, col_span)
            except (KeyError, ValueError):
                cap = 0; tgt = 0

            drafted = _cell_text_chars(cell.get('props', {}))
            pct = (drafted / cap * 100) if cap > 0 else 0.0
            flag = ''
            if cap > 0:
                if pct > 100: flag = 'overflow'; overflow_count += 1
                elif pct < 40: flag = 'sparse';  sparse_count += 1
                elif pct < 70: flag = 'mild-thin'

            cells_audit.append({
                'row':       row_idx,
                'col_start': col_start,
                'col_span':  col_span,
                'component': comp,
                'drafted':   drafted,
                'capacity':  cap,
                'target':    tgt,
                'fill_pct':  round(pct, 1),
                'flag':      flag,
            })

    return {
        'slide_id':       slide_input.get('slide_meta', {}).get('slide_title', '?'),
        'rows':           len(slide_input.get('rows', [])),
        'cells':          len(cells_audit),
        'overflow_count': overflow_count,
        'sparse_count':   sparse_count,
        'cells_audit':    cells_audit,
    }


def _cell_text_chars(props) -> int:
    """Count text chars in a cell's props, ignoring image/icon/styling fields."""
    if isinstance(props, str):
        if props.startswith('data:') or props.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.svg', '.webp')):
            return 0
        return len(props)
    elif isinstance(props, dict):
        total = 0
        for k, v in props.items():
            if k in _SKIP_PROP_KEYS:
                continue
            total += _cell_text_chars(v)
        return total
    elif isinstance(props, list):
        return sum(_cell_text_chars(item) for item in props)
    return 0


def _block_text_chars(block: dict) -> int:

    """Total text chars in a block (text-density calc)."""
    c = block.get("content", {})
    k = block.get("kind", "")
    if k == "narrative":
        return sum(len(p) for p in c.get("paragraphs", []) if isinstance(p, str))
    if k == "list":
        return sum(len(it) for it in c.get("items", []) if isinstance(it, str))
    if k == "features_3":
        n = 0
        for card in c.get("cards", []) or []:
            n += len(str(card.get("title", ""))) + len(str(card.get("body", "")))
        return n
    if k == "hero_stat":
        return len(str(c.get("value", ""))) + len(str(c.get("label", "")))
    if k == "supporting_stats":
        n = 0
        for it in c.get("items", []) or []:
            n += len(str(it.get("value", ""))) + len(str(it.get("label", "")))
        return n
    return 0


# ---------------------------------------------------------------------------
# v3.19 — Expand multi-cell blocks for accurate per-cell density audit.
# Closes gap #42: audit_plan_density assumed 1 block = 1 cell, but
# plan_to_slide_input expands features_3 (1 block) into 3 practice-card
# cells, values into 4-6 medallions, catalog into 2-3 columns. The
# pre-v3.19 audit either rejected with shape mismatch or, when fed a
# 1:1 layout, summed all sub-cells' chars into one cap → false overflow.
# ---------------------------------------------------------------------------

# Block kinds that compose into multiple cells. Maps kind →
# (items_field, item_to_pseudo_block_kind, default_component, default_span).
# When auditing, each item becomes one pseudo-block of `pseudo_kind` so
# audit_plan_density sees the per-cell shape it expects.
_EXPANSION_KINDS: dict[str, dict] = {
    "features_3": {
        "items_field":  "cards",
        "pseudo_kind":  "features_3_card",
        "component":    "practice-card",
        "span":         4,
    },
    "values": {
        "items_field":  "items",
        "pseudo_kind":  "values_item",
        "component":    "value-medallion",
        "span":         3,
    },
    "catalog": {
        "items_field":  "items",
        "pseudo_kind":  "catalog_item",
        "component":    "catalog-column",
        "span":         6,
    },
}


# Per-pseudo-kind char counter — counts ONE item's text payload only.
def _pseudo_block_chars(pseudo_kind: str, item: dict) -> int:
    if pseudo_kind == "features_3_card":
        # features_3 cards use 'title' or 'header' interchangeably across
        # callers; cover both.
        title = str(item.get("title", "") or item.get("header", ""))
        body  = str(item.get("body", ""))
        return len(title) + len(body)
    if pseudo_kind == "values_item":
        return len(str(item.get("title", ""))) + len(str(item.get("body", "")))
    if pseudo_kind == "catalog_item":
        return len(str(item.get("name", ""))) + len(str(item.get("description", "")))
    return 0


def expand_plan_for_audit(plan: dict) -> tuple[list[dict], list[tuple[str, int]]]:
    """v3.19 — Expand a SlideContentPlan's expansion-kind blocks (features_3,
    values, catalog) into 1-block-per-cell pseudo-blocks.

    Returns ``(expanded_blocks, expanded_layout)`` ready to feed
    ``audit_plan_density(... expanded=True)``. Non-expansion blocks pass
    through unchanged with their default 1:1 layout cell.

    Each pseudo-block carries:
        {'kind': '<pseudo_kind>',          # e.g. 'features_3_card'
         'content': <single item dict>,    # one card / value / column
         '_origin_block_idx': int}         # back-ref to original block
    """
    out_blocks: list[dict] = []
    out_layout: list[tuple[str, int]] = []
    for idx, b in enumerate(plan.get("blocks", [])):
        kind = b.get("kind", "")
        if kind in _EXPANSION_KINDS:
            spec = _EXPANSION_KINDS[kind]
            items = (b.get("content") or {}).get(spec["items_field"], []) or []
            for item in items:
                out_blocks.append({
                    "kind":              spec["pseudo_kind"],
                    "content":           dict(item) if isinstance(item, dict) else {"value": str(item)},
                    "_origin_block_idx": idx,
                    "_origin_kind":      kind,
                })
                out_layout.append((spec["component"], spec["span"]))
        else:
            # Non-expansion blocks: pass through with their default cell shape.
            # Use the same KIND_TO_DEFAULT_CELL table that plan_to_slide_input
            # would use for vertical-stack layouts.
            comp, span = _DEFAULT_CELL_FOR_KIND.get(
                kind, ("narrative-paragraph", 12)
            )
            out_blocks.append(dict(b, _origin_block_idx=idx, _origin_kind=kind))
            out_layout.append((comp, span))
    return out_blocks, out_layout


# Default (component, span) per kind when no layout_hint is given. Mirrors
# plan_to_slide_input's vertical-stack defaults. Used by expand_plan_for_audit
# for non-expansion blocks.
_DEFAULT_CELL_FOR_KIND: dict[str, tuple[str, int]] = {
    "narrative":          ("narrative-paragraph",  12),
    "hero_stat":          ("stat-hero",             5),
    "supporting_stats":   ("kpi-row",              12),
    "list":               ("bullet-list-checked", 12),
    "image_tile":         ("image-tile",          12),
    "process_flow":       ("process-flow",        12),
    "bar_chart":          ("bar-chart",           12),
    "pie_chart":          ("pie-chart",            6),
    "logo_grid":          ("logo-grid",           12),
    "icon_list":          ("icon-list",           12),
    "comparison_divider": ("comparison-divider",  12),
}


# ---------------------------------------------------------------------------
# v3.19 — pseudo-block char counters merged into _block_text_chars dispatch.
# Add coverage for the 3 pseudo-kinds emitted by expand_plan_for_audit.
# ---------------------------------------------------------------------------
def _block_text_chars_v319(block: dict) -> int:
    """v3.19 — extends _block_text_chars to handle pseudo-kinds emitted by
    expand_plan_for_audit. For real kinds, falls through to _block_text_chars.
    """
    k = block.get("kind", "")
    if k in ("features_3_card", "values_item", "catalog_item"):
        return _pseudo_block_chars(k, block.get("content") or {})
    return _block_text_chars(block)
