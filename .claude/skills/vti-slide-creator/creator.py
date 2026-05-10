"""
vti-slide-creator-v3 — main orchestrator for the 6-phase pipeline (v4.0).

Phases:

    1. ANALYZE              — parse source + extract images + propose
                              audience / purpose / customer; user confirms
                              ContextDoc.
    2. PLAN-OUTLINE-AND-REVIEW — design deck arc + slide list AND review
                              with user inline (single phase, single
                              checkpoint).
    3. CONTENT-PLAN         — for each slide draft typed content blocks,
                              resolve image strategy (lift / synthesize),
                              and DRAW the SVG diagram via the
                              vti-slide-diagram-builder skill so its
                              natural dimensions feed Phase 4. Also
                              filters lift candidates with
                              `classify_image_kind()` so junk icons
                              never reach the deck.
    4. LAYOUT-DESIGN        — for each slide, given content blocks +
                              diagram dims + lift dims, design the
                              12-col grid: row heights, image cell
                              col_span and aspect_ratio, fill metric.
                              Output: SlideLayoutPlan with no-crop +
                              ≥70% screen-fill assertions.
    5. COMPONENT-PICK       — translate SlideLayoutPlan → render-ready
                              slide_input descriptors. Mostly mechanical
                              now since layout is pre-decided.
    6. REVIEW-AND-COMPOSE   — render layout review widget for ALL
                              slides as 16:9 wireframes → user confirms →
                              compose final HTML deck.

Public surface (re-exported)
----------------------------
- Phase 1: ContextDoc / source ingestion
- Phase 2: DeckOutline (single-phase outline+review)
- Phase 3: SlideContentPlan with diagram_spec / lift_resolver
- Phase 4: SlideLayoutPlan (NEW module: layout_designer)
- Phase 5: grid helpers, component catalog
- Phase 6: render_layout_review_widget, deck_stats
"""
from __future__ import annotations

# --- Phase 5 (Sprint 2) ---------------------------------------------------
from preview import render_inline_preview, render_grid_summary, render_layout_review_widget, deck_stats  # noqa: F401
from component_catalog import (                                  # noqa: F401
    COMPONENT_CATALOG, list_components, describe, picks_for_kind,
)
from grid_helpers import (                                       # noqa: F401
    even_split, asymmetric_split, with_divider,
    make_cell, make_row, make_slide,
    narrative_row, stat_plus_narrative_row,
    cards_row, kpi_strip_row,
)

# --- Phase 3 (was Phase 4 in v3.x — content drafting) -------------------
from content_drafter import (                                    # noqa: F401
    CONTENT_BLOCK_SCHEMAS, IMAGE_STRATEGIES,
    make_block, make_image_decision, make_slide_content_plan,
    validate_block, validate_plan,
    block_kinds_in, has_block_kind, list_block_kinds,
    resolve_lift_image,                                          # v4.0
)
from image_decisions import (                                    # noqa: F401
    STRATEGY_GUIDE, describe_strategies, suggest_strategy,
)

# --- Phase 4 (NEW in v4.0 — layout design with no-crop + fill metric) -----
from layout_designer import (                                    # noqa: F401
    SLIDE_W_PX, SLIDE_H_PX, CONTENT_AREA_W_PX, CONTENT_AREA_H_PX,
    make_layout_row, make_layout_cell, make_layout_plan,
    design_slide_layout,
    validate_layout_plan, layout_metrics,
)

# --- v3.14 — capacity model + cross-phase validation -----------------------
from capacity import (                                           # noqa: F401
    cell_capacity, cell_target, layout_sketch_capacity,
    BLOCK_KIND_CAPS, block_kind_caps,
)
from cross_phase import (                                        # noqa: F401
    validate_for_compose,
    split_long_paragraphs,
    deck_density_summary,
    audit_plan_density, audit_deck_density,                      # v3.14
    audit_visual_balance,                                        # v3.16
    audit_block_distribution,                                    # v3.18
    expand_plan_for_audit,                                       # v3.19
)
from capacity import (                                           # noqa: F401 (re-import for visual flag)
    VISUAL_BLOCK_KINDS, TEXT_BLOCK_KINDS, is_visual_block,
    DENSITY_MODES, density_mode_for, cell_target_mode,           # v3.18
)

# --- Phase 1 (Sprint 4) ---------------------------------------------------
from context_doc import (                                        # noqa: F401
    VALID_TONES,
    make_context_doc, validate_context_doc, has_source_images,
    sources_for_section,                                         # v3.18
)
from source_ingester import (                                    # noqa: F401
    detect_kind, ingest_source, ingest_pre_extracted, summarize_source,
    extract_pptx_images, video_keyframes_stub,                   # v3.14
    classify_image_kind,                                         # v3.18
)

# --- Phase 2 + 3 (Sprint 5) -----------------------------------------------
from deck_planner import (                                       # noqa: F401
    FRAMING_KINDS, NARRATOR_KINDS, ALL_SLIDE_KINDS,
    make_slide_outline_entry, make_deck_outline,
    add_slide, remove_slide, move_slide, replace_slide,
    validate_deck_outline,
    slide_count_by_kind, section_distribution,
    render_outline_summary, render_outline_table,                # v3.14
    renumber_slide_ids,                                          # v3.14
)

__version__ = "4.0.1"


def info() -> dict:
    """Return a snapshot of what the creator currently supports."""
    return {
        "skill":   "vti-slide-creator-v3",
        "version": __version__,
        "phases_implemented": [1, 2, 3, 4, 5, 6],
        "phases_pending":     [],
        "components_known":   list_components(),
        "block_kinds_known":  list_block_kinds(),
        "image_strategies":   IMAGE_STRATEGIES,
        "slide_kinds_known":  ALL_SLIDE_KINDS,
        "tones_known":        VALID_TONES,
    }


# ---------------------------------------------------------------------------
# Phase 4 → Phase 5 bridge: SlideContentPlan ──▶ first-pass slide_input
# ---------------------------------------------------------------------------
def plan_to_slide_input(plan: dict,
                        page_number: int = 1, page_total: int = 1,
                        doc_title: str = "",
                        copyright_year: int = 2026) -> dict:
    """Auto-compose a starter ``slide_input`` from a ``SlideContentPlan``.

    Title routing
    -------------
    The plan's ``topic`` becomes ``slide_meta.slide_title`` and the plan's
    ``section_name`` becomes ``slide_meta.section_name``. The chrome
    renders them at top-left as "SECTION | TITLE". There is no header
    row in the content grid.

    Block→row defaults (v3.14 — preserves plan.blocks order)
    --------------------------------------------------------
    Each block becomes one row, in the ORDER it appears in plan.blocks,
    with these special pairings:

    - hero_stat IMMEDIATELY followed by narrative → merged into row 1 at 5+7
    - hero_stat alone               → row, col 1-12 (1fr)
    - narrative alone               → row, col 1-12
    - features_3                    → row, 3× practice-card (col 4+4+4)
    - values                        → row, 4-6× value-medallion
    - catalog                       → row, 2-3× catalog-column
    - supporting_stats              → row, kpi-row col 1-12
    - list                          → row, bullet-list-checked col 1-12

    The order matters. v3.13 hardcoded a fixed kind→row order that ignored
    plan.blocks order; v3.14 preserves whatever order the drafter chose.
    For non-default arrangements (image-side, asymmetric splits), Claude
    composes the grid manually using grid_helpers.
    """
    ok, errs = validate_plan(plan)
    if not ok:
        raise ValueError(f"plan validation failed: {errs}")

    blocks = plan["blocks"]
    section_name = plan.get("section_name", "")
    slide_title  = plan.get("topic", "")
    layout_hint  = plan.get("layout_hint", "")

    rows: list[dict] = []

    # ===========================================================
    # v3.17 Principle 9 — image layout patterns
    # If layout_hint specified, route to a custom row arrangement
    # instead of the default vertical stack.
    # ===========================================================
    if layout_hint and any(b.get("kind") == "image_tile" for b in blocks):
        return _compose_image_layout(
            plan, layout_hint,
            page_number=page_number, page_total=page_total,
            doc_title=doc_title, copyright_year=copyright_year,
        )

    # Walk blocks in declared order. Special-case: hero_stat directly
    # followed by narrative merge into one asymmetric row.
    i = 0
    while i < len(blocks):
        b = blocks[i]
        kind = b.get("kind")
        content = b.get("content", {})

        if kind == "hero_stat":
            # Peek ahead for narrative
            if i + 1 < len(blocks) and blocks[i+1].get("kind") == "narrative":
                rows.append(stat_plus_narrative_row(
                    stat_props      = content,
                    narrative_props = blocks[i+1]["content"],
                    stat_left=True, stat_span=5, height="1fr",
                ))
                i += 2
                continue
            else:
                rows.append(make_row("1fr", [
                    make_cell(1, 12, "stat-hero", content)
                ]))
        elif kind == "narrative":
            rows.append(narrative_row(
                content["paragraphs"],
                height="1fr" if i == 0 else "auto",
                align=content.get("align", "left"),
            ))
        elif kind == "features_3":
            rows.append(cards_row("practice-card", content["cards"]))
        elif kind == "values":
            rows.append(cards_row("value-medallion", content["cards"]))
        elif kind == "catalog":
            rows.append(cards_row("catalog-column", content["columns"]))
        elif kind == "supporting_stats":
            rows.append(kpi_strip_row(content["items"]))
        elif kind == "list":
            rows.append(make_row("auto", [
                make_cell(1, 12, "bullet-list-checked", content)
            ]))
        elif kind == "comparison_divider":
            # vs-divider — narrow center cell
            rows.append(make_row("auto", [
                make_cell(6, 2, "vs-divider", content)
            ]))
        # ---- v3.16 visual block kinds -----------------------------------
        elif kind == "image_tile":
            rows.append(make_row("1fr", [
                make_cell(1, 12, "image-tile", content)
            ]))
        elif kind == "process_flow":
            rows.append(make_row("auto", [
                make_cell(1, 12, "process-flow", content)
            ]))
        elif kind == "bar_chart":
            rows.append(make_row("1fr", [
                make_cell(1, 12, "bar-chart", content)
            ]))
        elif kind == "pie_chart":
            rows.append(make_row("1fr", [
                make_cell(1, 12, "pie-chart", content)
            ]))
        elif kind == "logo_grid":
            rows.append(make_row("auto", [
                make_cell(1, 12, "logo-grid", content)
            ]))
        elif kind == "icon_list":
            rows.append(make_row("auto", [
                make_cell(1, 12, "icon-list", content)
            ]))
        i += 1

    if not rows:
        kinds = [b.get('kind') for b in blocks]
        raise ValueError(
            f"plan_to_slide_input: no rows generated. "
            f"blocks present: {kinds}"
        )

    return make_slide(
        slide_meta={
            "page_number":    page_number,
            "page_total":     page_total,
            "doc_title":      doc_title,
            "copyright_year": copyright_year,
            "section_name":   section_name,
            "slide_title":    slide_title,
            # v3.19 — propagate density_mode to page-builder. Default
            # 'standard' if not declared on the plan; page-builder reads
            # this for fill-honesty thresholds.
            "density_mode":   plan.get("density_mode", "standard"),
        },
        rows=rows,
    )


def _compose_image_layout(plan: dict, layout_hint: str, *,
                          page_number: int, page_total: int,
                          doc_title: str, copyright_year: int) -> dict:
    """v3.17 · Principle 9 — image layout patterns.

    Three patterns supported:
      - ``"pattern-a-content-first"``: image col_span=4 + narrative col_span=8,
        stats below as full-width band. Image is supporting; content dominates.
      - ``"pattern-b-image-narrative-side-by-side"``: image col_span=8 +
        narrative col_span=4, stats below as full-width thin band. Image is
        focal; narrative explains.
      - ``"pattern-b-full-width-image"``: image col_span=12 1fr (large hero),
        narrative + stats stacked below at auto height. For dense diagrams
        that need full slide width.
    """
    blocks = plan["blocks"]
    section_name = plan.get("section_name", "")
    slide_title  = plan.get("topic", "")

    # Extract typed blocks
    img_block  = next((b for b in blocks if b.get("kind") == "image_tile"), None)
    narr_block = next((b for b in blocks if b.get("kind") == "narrative"), None)
    stat_block = next((b for b in blocks if b.get("kind") == "supporting_stats"), None)

    if not img_block:
        raise ValueError("layout_hint requires an image_tile block")

    rows: list[dict] = []

    if layout_hint == "pattern-a-content-first":
        # narrative col 1-8, image col 9-12
        if narr_block:
            rows.append(make_row("1fr", [
                make_cell(1, 8, "narrative-paragraph", narr_block["content"]),
                make_cell(9, 4, "image-tile", img_block["content"]),
            ]))
        else:
            rows.append(make_row("1fr", [
                make_cell(1, 12, "image-tile", img_block["content"]),
            ]))
        if stat_block:
            rows.append(kpi_strip_row(stat_block["content"]["items"]))

    elif layout_hint == "pattern-b-image-narrative-side-by-side":
        # image col 1-8, narrative col 9-12
        if narr_block:
            rows.append(make_row("1fr", [
                make_cell(1, 8, "image-tile", img_block["content"]),
                make_cell(9, 4, "narrative-paragraph", narr_block["content"]),
            ]))
        else:
            rows.append(make_row("1fr", [
                make_cell(1, 12, "image-tile", img_block["content"]),
            ]))
        if stat_block:
            rows.append(kpi_strip_row(stat_block["content"]["items"]))

    elif layout_hint == "pattern-b-full-width-image":
        # full-width image (large), narrative below (auto), stats below (auto)
        rows.append(make_row("1fr", [
            make_cell(1, 12, "image-tile", img_block["content"]),
        ]))
        if narr_block:
            rows.append(narrative_row(
                narr_block["content"]["paragraphs"],
                height="auto",
                align=narr_block["content"].get("align", "left"),
            ))
        if stat_block:
            rows.append(kpi_strip_row(stat_block["content"]["items"]))

    else:
        raise ValueError(f"unknown layout_hint: {layout_hint!r}")

    return make_slide(
        slide_meta={
            "page_number":    page_number,
            "page_total":     page_total,
            "doc_title":      doc_title,
            "copyright_year": copyright_year,
            "section_name":   section_name,
            "slide_title":    slide_title,
            "density_mode":   plan.get("density_mode", "standard"),  # v3.19
        },
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Phase 1-3 entry points — these are thin wrappers that delegate to the
# real modules. They exist so callers can ``from creator import …`` and
# get a unified surface even though the heavy reasoning is Claude's job.
# ---------------------------------------------------------------------------
def analyze_source(path: str) -> dict:
    """Phase 1 — Ingest a source file. For binary formats, returns a stub
    pointing to the right format-skill (docx/pdf/pptx).

    The downstream ContextDoc construction (audience / purpose / tone /
    summary) is Claude's reasoning; use ``make_context_doc()`` to wrap
    the result after Claude proposes values and the user confirms.
    """
    return ingest_source(path)


def plan_deck_outline(*args, **kwargs):
    """Phase 2 — Designing the deck arc + slide list is Claude reasoning
    over the ContextDoc. Use ``make_deck_outline()`` and
    ``make_slide_outline_entry()`` to construct the result, then
    ``validate_deck_outline()`` to check it.

    This is the canonical pattern; there is no auto-planner. Each deck
    is a unique narrative — we don't want a generic template.
    """
    raise NotImplementedError(
        "Phase 2 is Claude reasoning. Use make_deck_outline() + "
        "make_slide_outline_entry() to construct, validate_deck_outline() "
        "to check."
    )


def review_outline(*args, **kwargs):
    """Phase 3 — Iterating on the outline with the user is Claude
    conversation. Use ``add_slide / remove_slide / move_slide /
    replace_slide`` helpers to apply user feedback to the outline.
    """
    raise NotImplementedError(
        "Phase 3 is iterative chat. Use add_slide/remove_slide/move_slide/"
        "replace_slide helpers between turns."
    )


# ---------------------------------------------------------------------------
# v3.17.1 · build_deck_html — closes gap #33 (manual DECK_SHELL wrapping)
# ---------------------------------------------------------------------------
DECK_SHELL_DEFAULT = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=1280">
<title>{title}</title>
<style>
{css}
/* === deck preview shell — scrollable card stack ===
   Each composed slide is a fixed 1280×720 card with rounded corners
   and a drop shadow, sitting on a pale-blue page background. The
   flex column with gap prevents any chrome of slide N+1 from
   visually overlapping the footer of slide N (the bug that the
   pre-v4.0.1 driver-side preview shell was working around).

   IMPORTANT: nothing else is injected here. The chrome system already
   provides slide page-numbers (footer chevron) — never add a parallel
   per-slide number badge from the shell. Doing so produced the v4.0
   "16 in top-left of every slide" bug. */
html, body {{
  margin: 0; padding: 0;
  background: #DAE9F6;
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}}
body {{
  display: flex; flex-direction: column;
  align-items: center; gap: 40px;
  padding: 40px 0;
  min-height: 100vh;
}}
.slide {{
  width:  1280px !important;
  height: 720px  !important;
  margin: 0;
  position: relative;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 12px 30px rgba(5, 25, 52, 0.18);
  overflow: hidden;
}}
</style>
</head>
<body>
{slides}
</body>
</html>
"""


def build_deck_html(slides, title="VTI Deck", lang="en", shell=None):
    """v3.17.1 — Compose a complete, ready-to-write HTML document from
    a list of ``slide_input`` dicts.

    Wraps ``composer_grid.compose_deck()`` output (which returns a dict
    of {deck_html, slide_htmls, deck_css, slide_metadatas}) in a full
    DOCTYPE + <html><head><style> + <body> shell so the caller can write
    directly to disk and open in a browser.

    Without this helper, callers were manually wrapping deck_html +
    deck_css (the gap #33 we hit during v3.16 — first deck delivered had
    no CSS because we wrote only deck_html).

    Args:
        slides: list of slide_input dicts (or special-page descriptors)
        title: deck title used in <title>
        lang: HTML lang attribute (default 'en')
        shell: optional custom shell template (must contain
               {title}, {css}, {slides}, {lang} placeholders).
               Pass None for default VTI-friendly shell.

    Returns:
        str — full HTML document, ready to write.

    Example::

        slides = [plan_to_slide_input(p, page_number=i+1, page_total=N,
                                       doc_title=outline['doc_title'])
                  for i, p in enumerate(plans)]
        html = build_deck_html(slides, title=outline['doc_title'])
        open('/tmp/deck.html', 'w', encoding='utf-8').write(html)
    """
    from composer_grid import compose_deck
    deck = compose_deck(slides)
    template = shell if shell is not None else DECK_SHELL_DEFAULT
    return template.format(
        title=title, lang=lang,
        css=deck["deck_css"],
        slides=deck["deck_html"],
    )
