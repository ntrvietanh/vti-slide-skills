"""Phase 4 — LAYOUT-DESIGN.

Takes a SlideContentPlan (Phase 3) and outputs a SlideLayoutPlan: an
explicit grid layout that fills the slide canvas without cropping the
image and without leaving >30% empty space at the bottom.

Why this module exists
----------------------
v3.x squashed layout-design and component-pick into Phase 5 with simple
``layout_hint`` strings ("pattern-a-content-first", etc.). The hint
didn't carry image dimensions, so:

1. SVG diagrams with viewBox 1180×460 (≈2.56:1) were rendered into
   ``image-tile`` cells with hardcoded ``aspect_ratio: "16:9"``.
   ``object-fit: cover`` cropped the right side.
2. ``pattern-b-image-narrative-side-by-side`` placed image col_span=8 +
   narrative col_span=4 even when the image was tall, leaving the
   bottom of the slide empty while the narrative ran short.

v4.0 fixes both with this module, which sees each slide's actual image
dimensions (natural_w/natural_h from diagram_spec or resolved_image)
and chooses a pattern + cell sizes that satisfy:

- **No-crop**: image cell ``aspect_ratio`` ≥ image natural aspect ratio.
- **Fill**: total computed row heights ≥ 70% of available slide height.

API
---

- ``design_slide_layout(content_plan)`` → SlideLayoutPlan
- ``validate_layout_plan(plan)`` → (ok, errors)
- ``layout_metrics(plan)`` → fill / aspect / overflow indicators
"""
from __future__ import annotations

from typing import Any

# Slide canvas geometry — MUST match page-builder rendered output exactly.
# Source of truth: composer_grid.py _GRID_CSS
#   .slide.layout-grid { width: 1280px; height: 720px; overflow: hidden; }
#   .vti-slide-content { top: 70px; left: 56px; right: 56px; bottom: 64px; }
#   .vti-grid          { gap: 18px; align-content: start; }
# v4.5 (2026-05-10): the legacy 1280×620 / COL_W=106 numbers were wrong by
# ~9% width / 6% height / 24% column-width — every fill estimate was
# optimistic and banner-top heights overflowed the real 586-tall content
# area, producing the visual "content chồng nhau" regression. Fixed here.
SLIDE_W_PX = 1280
SLIDE_H_PX = 720
CHROME_TOP_PX    = 70      # breadcrumb bar (composer_grid.py top: 70px)
CHROME_BOTTOM_PX = 64      # footer        (composer_grid.py bottom: 64px)
CHROME_LR_PX     = 56      # left/right padding inside slide
COL_COUNT = 12
GAP_PX    = 18             # CSS grid gap (both row + column)

CONTENT_AREA_W_PX = SLIDE_W_PX - 2 * CHROME_LR_PX                  # 1168
CONTENT_AREA_H_PX = SLIDE_H_PX - CHROME_TOP_PX - CHROME_BOTTOM_PX  # 586
COL_W_PX = (CONTENT_AREA_W_PX - (COL_COUNT - 1) * GAP_PX) / COL_COUNT  # ≈80.83


def col_span_to_px(span: int) -> int:
    """Pixel width of a cell that spans `span` columns, including gaps."""
    if span <= 0:
        return 0
    return int(span * COL_W_PX + (span - 1) * GAP_PX)


# Realistic block height estimates — measured against rendered v3.13 output.
# Used for: (a) fill_pct metric, (b) deciding row_span cutoff, (c) deciding
# whether a candidate split fits the slide.  Conservative-but-not-loose:
# typical 2-paragraph narrative renders ~140px, a kpi-row ~90px, a row of
# 3 practice-cards ~180px when each card has ~3 lines of body.
BLOCK_KIND_EST_H: dict[str, int] = {
    "narrative":         140,
    "list":              140,
    "icon_list":         180,
    "hero_stat":         170,
    "supporting_stats":  90,
    "features_3":        180,   # row of 3 cards horizontal (each ~3 body lines)
    "values":            210,   # row of 4 medallions (icon + title + tagline)
    "catalog":           220,
    "logo_grid":         130,
    "process_flow":      200,
    "bar_chart":         260,
    "pie_chart":         260,
    "image_tile":        260,
    "comparison_divider": 60,
}

# Stacked-vertical estimates: the same block laid out with each item on its
# own row. Used when the content column is too narrow for horizontal split.
BLOCK_KIND_STACKED_ITEM_H: dict[str, int] = {
    "features_3":  100,   # one practice-card ≈ 100px tall
    "values":       96,   # one medallion w/o tagline ≈ 96
    "catalog":     120,   # one column block stacked
}


# ---------------------------------------------------------------------------
# Public constructors
# ---------------------------------------------------------------------------
def make_layout_row(height: str, cells: list[dict],
                    *, kind_hint: str = "") -> dict:
    """Build one row entry of a SlideLayoutPlan.

    Args:
        height:    'auto' | '1fr' | 'Npx' — fed into compose_slide_grid()
        cells:     list of cell dicts (each has col_start, col_span,
                   component, props)
        kind_hint: optional string describing what this row carries
                   (e.g. 'image-row', 'narrative-row', 'stats-row')
    """
    return {"height": height, "cells": list(cells), "kind_hint": kind_hint}


def make_layout_cell(col_start: int, col_span: int,
                     component: str, props: dict,
                     *, source_block_kind: str = "",
                     row_span: int = 1) -> dict:
    """Build one cell entry of a row.

    ``row_span`` (default 1) lets a cell span multiple grid rows — used by
    the image-side patterns to anchor the image cell while the right column
    stacks N secondary blocks beside it. The page-builder honors values 1-8.
    """
    return {
        "col_start":          col_start,
        "col_span":           col_span,
        "component":          component,
        "props":              props,
        "source_block_kind":  source_block_kind,
        "row_span":           row_span,
    }


def make_layout_plan(slide_id: str,
                     topic: str,
                     section_name: str,
                     rows: list[dict],
                     pattern: str,
                     *,
                     fill_pct: float = 0.0,
                     image_natural_aspect: float | None = None,
                     image_cell_aspect: float | None = None,
                     warnings: list[str] | None = None) -> dict:
    """Wrap the layout decisions for one slide."""
    return {
        "slide_id":              slide_id,
        "topic":                 topic,
        "section_name":          section_name,
        "rows":                  rows,
        "pattern":               pattern,
        "fill_pct":              fill_pct,
        "image_natural_aspect":  image_natural_aspect,
        "image_cell_aspect":     image_cell_aspect,
        "warnings":              warnings or [],
    }


# ---------------------------------------------------------------------------
# Component pick — block-kind → component name + multi-cell expansion
# ---------------------------------------------------------------------------
_BLOCK_TO_COMPONENT: dict[str, str] = {
    "narrative":          "narrative-paragraph",
    "list":               "bullet-list-checked",
    "icon_list":          "icon-list",
    "hero_stat":          "stat-hero",
    "supporting_stats":   "kpi-row",
    "logo_grid":          "logo-grid",
    "process_flow":       "process-flow",
    "bar_chart":          "bar-chart",
    "pie_chart":          "pie-chart",
    "image_tile":         "image-tile",
    "comparison_divider": "vs-divider",
    # Multi-cell types are handled by _expand_multi_cell_block
    "features_3":         "practice-card",
    "values":             "value-medallion",
    "catalog":            "catalog-column",
}


def _even_split_starts(n: int) -> list[tuple[int, int]]:
    """Equal-width split of the 12-col grid for n=2..6 cells."""
    splits = {
        1: [(1, 12)],
        2: [(1, 6),  (7, 6)],
        3: [(1, 4),  (5, 4),  (9, 4)],
        4: [(1, 3),  (4, 3),  (7, 3),  (10, 3)],
        5: [(1, 3),  (4, 2),  (6, 3),  (9, 2),  (11, 2)],
        6: [(1, 2),  (3, 2),  (5, 2),  (7, 2),  (9, 2),  (11, 2)],
    }
    return splits[n][:]


def _expand_multi_cell_block(block: dict) -> list[dict]:
    """Expand features_3 / values / catalog into N cells."""
    kind = block["kind"]
    content = block["content"]
    if kind == "features_3":
        cards = content["cards"]
        component = "practice-card"
        items = cards
    elif kind == "values":
        items = content["cards"]
        component = "value-medallion"
    elif kind == "catalog":
        items = content["columns"]
        component = "catalog-column"
    else:
        raise ValueError(f"_expand_multi_cell_block called with non-multi kind {kind}")

    splits = _even_split_starts(len(items))
    return [
        make_layout_cell(cs, sp, component, item,
                          source_block_kind=kind)
        for (cs, sp), item in zip(splits, items)
    ]


def _block_to_full_row(block: dict) -> dict:
    """Convert a single text/visual block into a full-width row."""
    kind = block["kind"]
    if kind in ("features_3", "values", "catalog"):
        return make_layout_row(
            "auto", _expand_multi_cell_block(block), kind_hint=kind,
        )
    component = _BLOCK_TO_COMPONENT[kind]
    cell = make_layout_cell(1, 12, component, block["content"],
                              source_block_kind=kind)
    return make_layout_row("auto", [cell], kind_hint=kind)


# ---------------------------------------------------------------------------
# Image dimension extraction
# ---------------------------------------------------------------------------
def _image_dims(content_plan: dict) -> tuple[float | None, str | None, str | None,
                                                 int | None, int | None]:
    """Return (natural_aspect, image_path, source, natural_w, natural_h).

    `source` is 'diagram' / 'lift' / None.
    """
    img_dec = content_plan.get("image_decision", {})
    strategy = img_dec.get("strategy")
    if strategy == "synthesize":
        spec = content_plan.get("diagram_spec") or {}
        w, h = spec.get("natural_w"), spec.get("natural_h")
        if w and h:
            return (w / h, spec.get("svg_path", ""), "diagram", int(w), int(h))
    if strategy == "lift":
        resolved = content_plan.get("resolved_image") or {}
        w, h = resolved.get("natural_w"), resolved.get("natural_h")
        if w and h:
            return (w / h, resolved.get("path", ""), "lift", int(w), int(h))
    return (None, None, None, None, None)


def _image_cell_props(image_path: str,
                      natural_w: int, natural_h: int,
                      *, frame: str = "soft") -> dict:
    """Build props dict for image-tile.

    Sets aspect_ratio to natural_w:natural_h (integer W:H) so the
    composer's regex validator accepts it AND the renderer cannot crop.
    """
    return {
        "image":            image_path,
        "caption":          "",
        "aspect_ratio":     f"{natural_w}:{natural_h}",
        "frame":            frame,
        "caption_position": "none",
    }


# ---------------------------------------------------------------------------
# v4.5 flexible-split layout designer
# ---------------------------------------------------------------------------
# The designer searches over candidate splits — image col_span × side ×
# (banner | aside) — and picks the one that best fits the content blocks
# without overflow and without leaving ≥30% of either column empty.
#
# Patterns produced:
#   vertical-stack      : no image
#   image-banner-top    : image full-width at top, content full-width below
#   image-banner-bottom : image full-width at bottom, content full-width above
#   image-aside-LEFT    : image cols 1..K, content cols K+1..12
#   image-aside-RIGHT   : image cols 13-K..12, content cols 1..(12-K)
#
# Image col_span is selected from {3, 4, 5, 6, 7, 8} for aside layouts —
# corresponds to 25/75 → 67/33 splits. Image is allowed to render at less
# than its natural pixel size (image_cell aspect_ratio still pins to
# natural so no crop occurs; CSS object-fit:contain letterboxes if needed).
#
# Right-column multi-cell blocks (features_3 / values / catalog) are
# stacked vertically when content_col_span < N * MIN_HORIZONTAL_PER_ITEM,
# so practice-card titles never clip in narrow columns.

_MIN_IMG_COL_SPAN_ASIDE = 3
_MAX_IMG_COL_SPAN_ASIDE = 8
_MIN_BANNER_H_PX        = 180
_MIN_HORIZONTAL_PER_ITEM = 3   # multi-cell items need ≥3 cols each in a row
_GAP_TOLERANCE_PX        = 12  # acceptable diff between image_h and content_h


def design_slide_layout(content_plan: dict) -> dict:
    """Take a SlideContentPlan, output a SlideLayoutPlan.

    For slides with no image: vertical-stack.

    For slides with an image: search over split candidates (banner +
    aside × col_spans 3..8 × left/right) and pick the candidate with
    the best content-fit score. Image can be shrunk below its natural
    pixel size — we never pad the canvas around it.
    """
    slide_id = content_plan["slide_id"]
    topic = content_plan.get("topic", "")
    section_name = content_plan.get("section_name", "")
    blocks = content_plan.get("blocks", [])
    aspect, img_path, _src, nat_w, nat_h = _image_dims(content_plan)

    warnings: list[str] = []

    if aspect is None or not img_path:
        rows = [_block_to_full_row(b) for b in blocks]
        fill_pct = _estimate_fill_pct(rows)
        if fill_pct < 0.55:
            warnings.append(
                f"low fill ({fill_pct:.0%}) — consider adding a block or scaling text"
            )
        return make_layout_plan(
            slide_id, topic, section_name, rows,
            pattern="vertical-stack", fill_pct=fill_pct,
            warnings=warnings,
        )

    candidates = _enumerate_candidates(blocks, aspect, img_path, nat_w, nat_h)
    if not candidates:
        # Last-resort: banner top with image shrunk to fit.
        plan = _build_banner_layout(
            blocks, aspect, img_path, nat_w, nat_h,
            position="top", forced_image_h=200,
        )
        warnings.append("no fitting candidate — forced banner-top with shrunk image")
    else:
        best = min(candidates, key=lambda c: c["score"])
        plan = best["build"]()
        if best["score"] > 1.0:
            warnings.append(
                f"best candidate score {best['score']:.2f} — fit is loose; "
                "review for empty space"
            )

    fill_pct = _estimate_fill_pct(plan["rows"])
    plan.setdefault("warnings", []).extend(warnings)
    return make_layout_plan(
        slide_id, topic, section_name, plan["rows"],
        pattern=plan["pattern"],
        fill_pct=fill_pct,
        image_natural_aspect=aspect,
        image_cell_aspect=aspect,
        warnings=plan.get("warnings", []),
    )


# ---------------------------------------------------------------------------
# Candidate enumeration — banner ± aside × col_span × side
# ---------------------------------------------------------------------------
def _enumerate_candidates(
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
) -> list[dict]:
    """Build a list of viable layout candidates with fit scores.

    Each candidate carries:
        score     — lower = better; 0 = perfect fit
        build()   — closure that returns {"rows": [...], "pattern": str,
                    "warnings": [...]}
    """
    candidates: list[dict] = []

    # Banner candidates — image full-width at top OR bottom. The image is
    # allowed to shrink below natural height to leave room for content.
    for position in ("top", "bottom"):
        cand = _candidate_banner(blocks, aspect, img_path, nat_w, nat_h,
                                 position=position)
        if cand is not None:
            candidates.append(cand)

    # Aside candidates — image one side at various col_spans (3..8 = 25..67%).
    for img_span in range(_MIN_IMG_COL_SPAN_ASIDE, _MAX_IMG_COL_SPAN_ASIDE + 1):
        for side in ("left", "right"):
            cand = _candidate_aside(blocks, aspect, img_path, nat_w, nat_h,
                                    img_col_span=img_span, side=side)
            if cand is not None:
                candidates.append(cand)

    return candidates


def _candidate_banner(blocks, aspect, img_path, nat_w, nat_h,
                      *, position: str) -> dict | None:
    """Score a banner with content rows above/below.

    The banner cell is auto-sized to match the image natural width at
    the chosen height — not always 12 cols. For wide images, col_span
    will be 12. For medium-aspect images at typical banner heights, the
    banner is ≤10 cols, centered. This eliminates the "image floating
    in 600px of blue letterbox" pattern the user flagged on s14/s18/s27.
    """
    content_h = sum(
        _measure_full_width_block_h(b) for b in blocks
    ) + max(0, len(blocks) - 1) * GAP_PX
    avail_for_image = CONTENT_AREA_H_PX - content_h - GAP_PX
    if avail_for_image < _MIN_BANNER_H_PX:
        return None

    # Natural rendered height at full slide width (12 cols).
    natural_h_full = int(CONTENT_AREA_W_PX / aspect)
    image_h = min(natural_h_full, avail_for_image)
    if image_h < _MIN_BANNER_H_PX:
        return None

    # Auto-fit banner col_span to image natural width at chosen height.
    # Image at height image_h has natural width = image_h × aspect.
    # Pick the smallest col_span whose cell width covers that natural
    # width — anything smaller would crop or letterbox horizontally; anything
    # larger leaves blue space. col_span ≥ 6 to keep banner visually a banner.
    target_w = image_h * aspect
    img_col_span = COL_COUNT
    for span in range(6, COL_COUNT + 1):
        if col_span_to_px(span) >= target_w:
            img_col_span = span
            break

    cell_w = col_span_to_px(img_col_span)
    # Vertical waste
    used_v = image_h + content_h + GAP_PX
    waste_v = (CONTENT_AREA_H_PX - used_v) / CONTENT_AREA_H_PX
    # Residual horizontal waste inside the chosen banner cell
    waste_h = max(0.0, (cell_w - target_w) / cell_w)
    score = abs(waste_v) + 1.5 * waste_h
    if position == "bottom" and aspect < 2.0:
        score += 0.05

    def build():
        return _build_banner_layout(
            blocks, aspect, img_path, nat_w, nat_h,
            position=position, forced_image_h=image_h,
            img_col_span=img_col_span,
        )

    return {"score": score, "build": build,
            "label": f"banner-{position}@h={image_h},span={img_col_span}"}


def _candidate_aside(blocks, aspect, img_path, nat_w, nat_h,
                     *, img_col_span: int, side: str) -> dict | None:
    """Score an aside split (image one side at given col_span).

    Image cell takes ``image_h`` of vertical space — capped at content
    area height. For portrait images (aspect < 1) the natural height
    would exceed the slide; we cap and let object-fit:contain letterbox
    sides inside the cell. For wide images at narrow col_spans the
    natural height is small; cell shrinks to image_h to keep things
    proportional.
    """
    content_col_span = COL_COUNT - img_col_span
    if content_col_span < 3:
        return None  # content column would be unusably narrow

    img_w = col_span_to_px(img_col_span)
    natural_image_h = int(img_w / aspect)
    image_h = min(natural_image_h, CONTENT_AREA_H_PX)
    if image_h < 120:
        return None  # image would be too small to read

    # Lay out blocks in the content column. Multi-cell blocks stack
    # vertically when the column is too narrow.
    content_rows = _layout_blocks_in_column(blocks, content_col_span)
    if content_rows is None:
        return None  # a block can't fit even when stacked
    content_h = sum(r["h"] for r in content_rows) + max(0, len(content_rows) - 1) * GAP_PX

    if content_h > CONTENT_AREA_H_PX:
        return None  # right column would overflow the slide

    # Greedy split: image cell row-spans the first K rows whose
    # cumulative height is closest to image_h. Remaining rows fall to
    # full-width below the aside section.
    cum = 0
    aside_rows = []
    for r in content_rows:
        new_cum = cum + r["h"] + (GAP_PX if aside_rows else 0)
        if new_cum > image_h + _GAP_TOLERANCE_PX and aside_rows:
            break
        aside_rows.append(r)
        cum = new_cum
    rest_rows = content_rows[len(aside_rows):]
    aside_block_h = cum
    rest_h = sum(r["h"] for r in rest_rows) + max(0, len(rest_rows) - 1) * GAP_PX

    # The aside section's effective row height is max(image_h, aside_block_h)
    aside_section_h = max(image_h, aside_block_h)
    total_h = aside_section_h + (GAP_PX + rest_h if rest_rows else 0)
    if total_h > CONTENT_AREA_H_PX:
        return None

    # Score: 0 if image_h ≈ aside_block_h, grows with mismatch
    mismatch = abs(image_h - aside_block_h) / max(image_h, aside_block_h, 1)
    waste = (CONTENT_AREA_H_PX - total_h) / CONTENT_AREA_H_PX
    score = mismatch + 0.3 * abs(waste)
    # Mild preference: avoid extreme col_spans when middle ones also fit
    if img_col_span <= 3 or img_col_span >= 8:
        score += 0.05

    def build():
        return _build_aside_layout(
            blocks, aspect, img_path, nat_w, nat_h,
            img_col_span=img_col_span, side=side,
            aside_rows=aside_rows, rest_rows=rest_rows,
            image_h=image_h,
        )

    return {"score": score, "build": build,
            "label": f"aside-{side}@span={img_col_span},img_h={image_h},"
                     f"aside={aside_block_h},rest={int(rest_h)}"}


# ---------------------------------------------------------------------------
# Block layout helpers — translate blocks into rows of cells in a column
# ---------------------------------------------------------------------------
def _layout_blocks_in_column(blocks: list[dict],
                             col_span: int) -> list[dict] | None:
    """Lay out content blocks inside a column of width `col_span`.

    Returns a list of row descriptors:
        [{"h": int, "kind": str, "cells_template": [{...}, ...]}, ...]
    where each cells_template is parameterised by col_start (filled in
    by the caller). Multi-cell blocks (features_3 / values / catalog)
    stack vertically when col_span < N * _MIN_HORIZONTAL_PER_ITEM.

    Returns None if any block can't fit (e.g. a 6-card values block in a
    3-col column even when stacked).
    """
    rows: list[dict] = []
    for block in blocks:
        kind = block["kind"]
        if kind in ("features_3", "values", "catalog"):
            content = block["content"]
            if kind == "features_3":
                items, component = content["cards"], "practice-card"
            elif kind == "values":
                items, component = content["cards"], "value-medallion"
            else:
                items, component = content["columns"], "catalog-column"
            n = len(items)
            if n == 0:
                continue
            if col_span >= n * _MIN_HORIZONTAL_PER_ITEM:
                # Horizontal split inside the column — single grid row
                each = col_span // n
                slots: list[tuple[int, int]] = []
                used = 0
                for i in range(n):
                    sp = each if i < n - 1 else col_span - used
                    slots.append((used, sp))
                    used += sp
                cells_template = [
                    {"col_offset": ofs, "col_span": sp,
                     "component": component, "props": item,
                     "source_block_kind": kind}
                    for (ofs, sp), item in zip(slots, items)
                ]
                rows.append({
                    "h": BLOCK_KIND_EST_H.get(kind, 150),
                    "kind": kind,
                    "cells_template": cells_template,
                })
            else:
                # Vertical stack — one row per item, full column width
                item_h = BLOCK_KIND_STACKED_ITEM_H.get(kind, 100)
                for i, item in enumerate(items):
                    cells_template = [{
                        "col_offset": 0, "col_span": col_span,
                        "component": component, "props": item,
                        "source_block_kind": kind,
                    }]
                    rows.append({
                        "h": item_h,
                        "kind": f"{kind}__item_{i+1}_of_{n}",
                        "cells_template": cells_template,
                    })
        else:
            component = _BLOCK_TO_COMPONENT[kind]
            cells_template = [{
                "col_offset": 0, "col_span": col_span,
                "component": component, "props": block["content"],
                "source_block_kind": kind,
            }]
            rows.append({
                "h": BLOCK_KIND_EST_H.get(kind, 100),
                "kind": kind,
                "cells_template": cells_template,
            })
    return rows


def _measure_full_width_block_h(block: dict) -> int:
    """Estimated row height of a block when laid out full-width (col=12)."""
    kind = block["kind"]
    return BLOCK_KIND_EST_H.get(kind, 100)


# ---------------------------------------------------------------------------
# Layout builders — turn candidate selections into LayoutPlan rows
# ---------------------------------------------------------------------------
def _build_banner_layout(
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
    *, position: str, forced_image_h: int,
    img_col_span: int = COL_COUNT,
) -> dict:
    """Image at top or bottom; content rows fill the other half.

    ``img_col_span`` controls the banner width — defaults to 12 (full
    slide) but can be 6-11 to center a narrower banner that matches the
    image's natural width at the chosen height. Eliminates the
    horizontal-letterbox space when the image isn't wide enough to fill
    the full slide.
    """
    img_props = _image_cell_props(img_path, nat_w, nat_h)
    img_col_start = (COL_COUNT - img_col_span) // 2 + 1
    image_row = make_layout_row(
        f"{forced_image_h}px",
        [make_layout_cell(img_col_start, img_col_span, "image-tile", img_props,
                          source_block_kind="image_tile")],
        kind_hint=f"image-banner-{position}",
    )
    content_rows = [_block_to_full_row(b) for b in blocks]
    rows = ([image_row] + content_rows) if position == "top" \
           else (content_rows + [image_row])
    return {
        "rows": rows,
        "pattern": f"image-banner-{position}-{img_col_span}of12",
        "warnings": [],
    }


def _build_aside_layout(
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
    *,
    img_col_span: int, side: str,
    aside_rows: list[dict], rest_rows: list[dict],
    image_h: int,
) -> dict:
    """Image one side, content the other; rest_rows fall to full-width below."""
    img_props = _image_cell_props(img_path, nat_w, nat_h)

    if side == "left":
        img_col_start = 1
        content_col_start = img_col_span + 1
    else:
        img_col_start = COL_COUNT - img_col_span + 1
        content_col_start = 1

    image_cell = make_layout_cell(
        img_col_start, img_col_span, "image-tile", img_props,
        source_block_kind="image_tile",
        row_span=max(1, len(aside_rows)),
    )

    rows: list[dict] = []
    if not aside_rows:
        # Image-only at top, then content full-width
        rows.append(make_layout_row(
            f"{image_h}px",
            [image_cell],
            kind_hint=f"image-aside-{side}-only",
        ))
    else:
        for i, r in enumerate(aside_rows):
            content_cells = [
                make_layout_cell(
                    content_col_start + ct["col_offset"],
                    ct["col_span"],
                    ct["component"], ct["props"],
                    source_block_kind=ct["source_block_kind"],
                )
                for ct in r["cells_template"]
            ]
            cells = ([image_cell] + content_cells) if i == 0 else content_cells
            rows.append(make_layout_row(
                "auto", cells,
                kind_hint=f"image-aside-{side}-r{i+1}-{r['kind']}",
            ))

    # rest_rows fall to full-width below the aside section. Single-cell
    # blocks span all 12 cols; multi-cell blocks redistribute evenly.
    for r in rest_rows:
        templates = r["cells_template"]
        n = len(templates)
        if n == 1:
            ct = templates[0]
            full_cells = [make_layout_cell(
                1, COL_COUNT, ct["component"], ct["props"],
                source_block_kind=ct["source_block_kind"],
            )]
        else:
            each = COL_COUNT // n
            cs = 1
            full_cells = []
            for i, ct in enumerate(templates):
                sp = each if i < n - 1 else COL_COUNT - (cs - 1)
                full_cells.append(make_layout_cell(
                    cs, sp, ct["component"], ct["props"],
                    source_block_kind=ct["source_block_kind"],
                ))
                cs += sp
        rows.append(make_layout_row(
            "auto", full_cells,
            kind_hint=f"full-{r['kind']}",
        ))

    pattern = f"image-aside-{side}-{img_col_span}of12"
    return {
        "rows": rows,
        "pattern": pattern,
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Fill metric estimation
# ---------------------------------------------------------------------------
def _estimate_fill_pct(rows: list[dict]) -> float:
    """Sum estimated row heights ÷ available content area.

    Heights from explicit "Npx" entries are used directly; "auto" rows
    use the kind_hint to look up an estimate.
    """
    # Image-aside patterns: an image cell row-spans some rows. Compute
    # the visible height as the aside section (max of image_h and
    # right-column rows it spans) + remaining rows below.
    image_span_h = _image_aside_span_height(rows)
    if image_span_h is not None:
        first = image_span_h["first_row"]
        span = image_span_h["span"]
        non_spanned_rows = rows[:first] + rows[first + span:]
        non_spanned = sum(_row_h_estimate(r) for r in non_spanned_rows) \
                      + max(0, len(non_spanned_rows)) * GAP_PX
        total = image_span_h["height"] + non_spanned
        return min(1.0, total / CONTENT_AREA_H_PX)

    total = sum(_row_h_estimate(r) for r in rows) + max(0, len(rows) - 1) * GAP_PX
    return min(1.0, total / CONTENT_AREA_H_PX)


def _row_h_estimate(row: dict) -> int:
    h = row.get("height", "auto")
    if isinstance(h, str) and h.endswith("px"):
        try:
            return int(h[:-2])
        except ValueError:
            pass
    kind_hint = row.get("kind_hint", "")
    # Normalize hints used by the v4.5 designer:
    #   "image-aside-{side}-r{N}-{block_kind}"  (e.g. image-aside-left-r1-hero_stat)
    #   "full-{block_kind}"
    #   "image-banner-{position}"
    #   plain "block_kind"  (vertical-stack rows)
    # …and v4.4 legacy "image-aside-r{N}-{block_kind}".
    if kind_hint.startswith("image-aside-"):
        # Try to find the block kind suffix after the last "rN-" segment
        parts = kind_hint.split("-")
        # Locate the rN segment
        for idx, p in enumerate(parts):
            if len(p) >= 2 and p.startswith("r") and p[1:].isdigit():
                kind_hint = "-".join(parts[idx + 1:])
                break
    elif kind_hint.startswith("full-"):
        kind_hint = kind_hint[len("full-"):]
    # Strip "__item_X_of_Y" suffix added by vertical-stack expansion
    if "__item_" in kind_hint:
        kind_hint = kind_hint.split("__item_", 1)[0]
        # Per-item is roughly the BLOCK_KIND_STACKED_ITEM_H value
        return BLOCK_KIND_STACKED_ITEM_H.get(kind_hint, 100)
    return BLOCK_KIND_EST_H.get(kind_hint, 100)


def _image_aside_span_height(rows: list[dict]) -> dict | None:
    """If any row has an image-tile cell that shares the row with content
    cells (aside layout — row has 2+ cells, one of which is an image),
    compute the effective rendered height of that image cell.

    Effective height = max(image natural height at cell width,
                           sum of row heights it spans).

    Returns ``{"height": int, "span": int, "first_row": int}`` or
    ``None`` when no aside image cell is present.
    """
    if not rows:
        return None
    image_cell = None
    image_row_idx = -1
    for ridx, row in enumerate(rows):
        cells = row.get("cells", [])
        # Aside row = image cell sharing the row with at least one content cell
        if len(cells) < 2:
            continue
        for c in cells:
            if c.get("component") == "image-tile" and c.get("col_span", 12) < COL_COUNT:
                image_cell = c
                image_row_idx = ridx
                break
        if image_cell:
            break
    if image_cell is None:
        return None
    aspect_str = image_cell.get("props", {}).get("aspect_ratio", "")
    try:
        w_str, h_str = aspect_str.split(":")
        aspect = float(w_str) / float(h_str)
    except (ValueError, ZeroDivisionError):
        return None
    cell_w_px = col_span_to_px(image_cell["col_span"])
    natural_h_px = int(cell_w_px / aspect)
    natural_h_px = min(natural_h_px, CONTENT_AREA_H_PX)  # cap (portrait letterbox)
    span = max(1, image_cell.get("row_span", 1))
    spanned = rows[image_row_idx:image_row_idx + span]
    # Estimate row heights using non-image cells only (image cell auto-sizes)
    def _row_non_image_h(r: dict) -> int:
        non_img = [c for c in r.get("cells", [])
                   if c.get("component") != "image-tile"]
        if not non_img:
            return _row_h_estimate(r)
        # Use the kind_hint estimate (which already strips image-aside prefix)
        return _row_h_estimate(r)
    spanned_h = sum(_row_non_image_h(r) for r in spanned) + max(0, span - 1) * GAP_PX
    return {
        "height": max(natural_h_px, spanned_h),
        "span": span,
        "first_row": image_row_idx,
    }


def layout_metrics(plan: dict) -> dict:
    """Compute fill / overflow indicators for a SlideLayoutPlan."""
    rows = plan.get("rows", [])
    fill_pct = _estimate_fill_pct(rows)
    image_aspect = plan.get("image_natural_aspect")
    cell_aspect = plan.get("image_cell_aspect")
    aspect_ok = (
        image_aspect is None
        or cell_aspect is None
        or abs(cell_aspect - image_aspect) < 0.05
    )
    return {
        "fill_pct":    fill_pct,
        "low_fill":    fill_pct < 0.7,
        "high_fill":   fill_pct > 1.05,    # likely overflow
        "no_crop_ok":  aspect_ok,          # image aspect matches cell
        "row_count":   len(rows),
        "warnings":    plan.get("warnings", []),
    }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------
def validate_layout_plan(plan: Any) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(plan, dict):
        return False, ["plan must be a dict"]
    for f in ("slide_id", "rows", "pattern"):
        if f not in plan:
            errors.append(f"missing required field {f!r}")
    rows = plan.get("rows", [])
    if not isinstance(rows, list):
        errors.append("rows must be a list")
    elif not rows:
        errors.append("rows must have at least 1 entry")
    else:
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(f"rows[{i}] must be a dict")
                continue
            cells = row.get("cells", [])
            if not isinstance(cells, list) or not cells:
                errors.append(f"rows[{i}] must have at least 1 cell")
                continue
            span_total = 0
            for j, c in enumerate(cells):
                if not isinstance(c, dict):
                    errors.append(f"rows[{i}].cells[{j}] must be a dict")
                    continue
                for k in ("col_start", "col_span", "component", "props"):
                    if k not in c:
                        errors.append(f"rows[{i}].cells[{j}] missing {k!r}")
                span_total += int(c.get("col_span", 0))
            if span_total > 12:
                errors.append(
                    f"rows[{i}] cells span {span_total} > 12"
                )
    return len(errors) == 0, errors


__all__ = [
    "SLIDE_W_PX", "SLIDE_H_PX", "CONTENT_AREA_W_PX", "CONTENT_AREA_H_PX",
    "make_layout_row", "make_layout_cell", "make_layout_plan",
    "design_slide_layout",
    "validate_layout_plan",
    "layout_metrics",
]
