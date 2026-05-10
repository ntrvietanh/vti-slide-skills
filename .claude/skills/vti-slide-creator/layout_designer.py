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

# Slide canvas geometry — matches page-builder rendered output.
SLIDE_W_PX = 1280
SLIDE_H_PX = 720
CHROME_TOP_PX = 60      # breadcrumb bar
CHROME_BOTTOM_PX = 40   # footer
CONTENT_AREA_H_PX = SLIDE_H_PX - CHROME_TOP_PX - CHROME_BOTTOM_PX  # 620
CONTENT_AREA_W_PX = SLIDE_W_PX                                     # 1280
COL_COUNT = 12
COL_W_PX = CONTENT_AREA_W_PX // COL_COUNT  # ≈ 106 (with gutter)

# Per-block estimated heights (used for fill metric).
# These are conservative averages — Phase 4 doesn't know exact font
# rendering, only "is the row likely tall or short".
BLOCK_KIND_EST_H: dict[str, int] = {
    "narrative":         110,   # 1-2 paragraphs
    "list":              120,   # 4-6 items
    "icon_list":         180,   # 6-12 items, denser
    "hero_stat":         170,
    "supporting_stats":  100,
    "features_3":        180,
    "values":            150,
    "catalog":           220,
    "logo_grid":         140,
    "process_flow":      200,
    "bar_chart":         260,
    "pie_chart":         260,
    "image_tile":        260,
    "comparison_divider": 60,
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
# Layout designer — main entry point
# ---------------------------------------------------------------------------
def design_slide_layout(content_plan: dict) -> dict:
    """Take a SlideContentPlan, output a SlideLayoutPlan.

    Picks one of 4 patterns:

    - ``vertical-stack``     : no image, blocks stack top-to-bottom
    - ``image-stacked-top``  : image is wide (aspect ≥ 2.0), full-width
                                row above the content blocks
    - ``image-side-by-side`` : image aspect 1.4-2.0, side-by-side with
                                first narrative; remaining blocks below
    - ``image-tall-side``    : image aspect < 1.4 (rare), narrower image
                                col_span=5 + content col_span=7
    """
    slide_id = content_plan["slide_id"]
    topic = content_plan.get("topic", "")
    section_name = content_plan.get("section_name", "")
    blocks = content_plan.get("blocks", [])
    aspect, img_path, img_source, nat_w, nat_h = _image_dims(content_plan)

    warnings: list[str] = []

    # No image — pure vertical stack
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

    # Image present — pick pattern by aspect ratio
    if aspect >= 2.0:
        return _design_image_stacked_top(
            slide_id, topic, section_name, blocks,
            aspect, img_path, nat_w, nat_h, warnings,
        )
    if aspect >= 1.4:
        return _design_image_side_by_side(
            slide_id, topic, section_name, blocks,
            aspect, img_path, nat_w, nat_h, warnings,
        )
    return _design_image_tall_side(
        slide_id, topic, section_name, blocks,
        aspect, img_path, nat_w, nat_h, warnings,
    )


def _design_image_stacked_top(
    slide_id: str, topic: str, section_name: str,
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
    warnings: list[str],
) -> dict:
    """Wide image (≥2:1) — full-width row at top, content stacked below."""
    rendered_h = int(CONTENT_AREA_W_PX / aspect)
    if rendered_h > CONTENT_AREA_H_PX - 200:
        warnings.append(
            f"image natural aspect {aspect:.2f} flagged stacked but rendered "
            f"height {rendered_h}px would crowd content; switching to side-by-side"
        )
        return _design_image_side_by_side(
            slide_id, topic, section_name, blocks,
            aspect, img_path, nat_w, nat_h, warnings,
        )

    img_props = _image_cell_props(img_path, nat_w, nat_h)
    image_row = make_layout_row(
        f"{rendered_h}px",
        [make_layout_cell(1, 12, "image-tile", img_props,
                            source_block_kind="image_tile")],
        kind_hint="image-row-full",
    )
    rows = [image_row] + [_block_to_full_row(b) for b in blocks]
    fill_pct = _estimate_fill_pct(rows)
    if fill_pct < 0.7:
        warnings.append(
            f"fill {fill_pct:.0%} below 70% — consider scaling image larger or adding a block"
        )
    return make_layout_plan(
        slide_id, topic, section_name, rows,
        pattern="image-stacked-top",
        fill_pct=fill_pct,
        image_natural_aspect=aspect,
        image_cell_aspect=aspect,
        warnings=warnings,
    )


def _design_image_side_by_side(
    slide_id: str, topic: str, section_name: str,
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
    warnings: list[str],
) -> dict:
    """Image aspect 1.4-2.0 — image left (col 1-8), content stack right
    (col 9-12). Image cell row-spans every right-column row so secondary
    blocks (kpi, list, etc.) sit BESIDE the image, not below it.
    """
    return _design_image_aside_stack(
        slide_id, topic, section_name, blocks,
        aspect, img_path, nat_w, nat_h, warnings,
        pattern="image-side-by-side",
        img_col_span=8,
    )


def _design_image_aside_stack(
    slide_id: str, topic: str, section_name: str,
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
    warnings: list[str],
    *,
    pattern: str,
    img_col_span: int,
) -> dict:
    """Shared builder for image-aside-content-stack patterns.

    Layout:
        Row 1: [image col 1..img_col_span row_span=N, block_1 col rest]
        Row 2: [block_2 col rest]
        …
        Row N: [block_N col rest]

    where N = number of right-column blocks.

    The image cell uses ``row_span=N`` so CSS grid stretches it across
    every right-column row. Each right-column row auto-sizes to its
    block's natural height; the image's effective height = sum of those.
    image-tile honors the row_span via its CSS aspect-ratio + object-fit
    (cover/contain) — soft-framed lift screenshots letterbox cleanly.

    Replaces the v4.0 design where only the first narrative sat beside
    the image and remaining blocks dropped to full-width rows below,
    leaving the right column empty above and a wasted strip below.
    """
    content_col_start = img_col_span + 1
    content_col_span  = COL_COUNT - img_col_span

    if not blocks:
        # Image-only — full-row, image natural height in px.
        img_w_px = int(CONTENT_AREA_W_PX * img_col_span / COL_COUNT)
        img_h_px = int(img_w_px / aspect)
        img_props = _image_cell_props(img_path, nat_w, nat_h)
        only_row = make_layout_row(
            f"{img_h_px}px",
            [make_layout_cell(1, COL_COUNT, "image-tile", img_props,
                                source_block_kind="image_tile")],
            kind_hint="image-row-full",
        )
        return make_layout_plan(
            slide_id, topic, section_name, [only_row],
            pattern=pattern, fill_pct=_estimate_fill_pct([only_row]),
            image_natural_aspect=aspect, image_cell_aspect=aspect,
            warnings=warnings,
        )

    img_props = _image_cell_props(img_path, nat_w, nat_h)
    n_rows = len(blocks)
    image_cell = make_layout_cell(
        1, img_col_span, "image-tile", img_props,
        source_block_kind="image_tile",
        row_span=n_rows,
    )

    rows: list[dict] = []
    for i, block in enumerate(blocks):
        right_cells = _expand_block_for_right_column(
            block, col_start=content_col_start, col_span=content_col_span,
        )
        cells = [image_cell] + right_cells if i == 0 else right_cells
        rows.append(make_layout_row(
            "auto", cells,
            kind_hint=f"image-aside-r{i+1}-{block['kind']}",
        ))

    fill_pct = _estimate_fill_pct(rows)
    if fill_pct < 0.7:
        warnings.append(
            f"fill {fill_pct:.0%} below 70% — consider adding supporting block"
        )

    return make_layout_plan(
        slide_id, topic, section_name, rows,
        pattern=pattern,
        fill_pct=fill_pct,
        image_natural_aspect=aspect,
        image_cell_aspect=aspect,
        warnings=warnings,
    )


def _expand_block_for_right_column(block: dict, *,
                                    col_start: int, col_span: int) -> list[dict]:
    """Expand a content block into one or more cells confined to the
    right column (col_start..col_start+col_span-1).

    Multi-cell block kinds (features_3, values, catalog) split the
    available right-column width evenly. Single-cell kinds occupy the
    whole right column.
    """
    kind = block["kind"]
    content = block["content"]

    if kind in ("features_3", "values", "catalog"):
        if kind == "features_3":
            items = content["cards"]
            component = "practice-card"
        elif kind == "values":
            items = content["cards"]
            component = "value-medallion"
        else:
            items = content["columns"]
            component = "catalog-column"
        n = len(items)
        each = max(1, col_span // n)
        cells: list[dict] = []
        for i, item in enumerate(items):
            cs = col_start + i * each
            sp = each if i < n - 1 else col_start + col_span - cs
            cells.append(make_layout_cell(cs, sp, component, item,
                                            source_block_kind=kind))
        return cells

    component = _BLOCK_TO_COMPONENT[kind]
    return [make_layout_cell(col_start, col_span, component, content,
                                source_block_kind=kind)]


def _design_image_tall_side(
    slide_id: str, topic: str, section_name: str,
    blocks: list[dict], aspect: float, img_path: str,
    nat_w: int, nat_h: int,
    warnings: list[str],
) -> dict:
    """Tall / square image (aspect < 1.4) — image col_span=5 left, content
    stack col_span=7 right via row_span on the image cell."""
    return _design_image_aside_stack(
        slide_id, topic, section_name, blocks,
        aspect, img_path, nat_w, nat_h, warnings,
        pattern="image-tall-side",
        img_col_span=5,
    )


# ---------------------------------------------------------------------------
# Fill metric estimation
# ---------------------------------------------------------------------------
def _estimate_fill_pct(rows: list[dict]) -> float:
    """Sum estimated row heights ÷ available content area.

    Heights from explicit "Npx" entries are used directly; "auto" rows
    use the kind_hint to look up an estimate.
    """
    # Image-aside patterns: a single image cell row-spans every row in
    # the plan, so the visual height of those rows is dominated by the
    # IMAGE's natural rendered height — not the sum of the right-column
    # block estimates. Detect and short-circuit that case.
    image_span_h = _image_aside_span_height(rows)
    if image_span_h is not None:
        non_spanned = sum(
            _row_h_estimate(r) for r in rows[image_span_h["span"]:]
        )
        return min(1.0, (image_span_h["height"] + non_spanned) / CONTENT_AREA_H_PX)

    total = sum(_row_h_estimate(r) for r in rows)
    return min(1.0, total / CONTENT_AREA_H_PX)


def _row_h_estimate(row: dict) -> int:
    h = row.get("height", "auto")
    if isinstance(h, str) and h.endswith("px"):
        try:
            return int(h[:-2])
        except ValueError:
            pass
    kind_hint = row.get("kind_hint", "")
    # image-aside-rN-blockkind → strip the rN- prefix to find blockkind
    if kind_hint.startswith("image-aside-"):
        rest = kind_hint.split("-", 3)
        if len(rest) >= 4:
            kind_hint = rest[3]
    return BLOCK_KIND_EST_H.get(kind_hint, 100)


def _image_aside_span_height(rows: list[dict]) -> dict | None:
    """If row 0 has an image cell with row_span > 1, compute the natural
    rendered height of that image at its cell width.

    Returns ``{"height": int, "span": int}`` or ``None`` when the layout
    is not an image-aside stack.
    """
    if not rows:
        return None
    cells = rows[0].get("cells", [])
    image_cell = next(
        (c for c in cells
         if c.get("component") == "image-tile" and c.get("row_span", 1) > 1),
        None,
    )
    if image_cell is None:
        return None
    aspect_str = image_cell.get("props", {}).get("aspect_ratio", "")
    try:
        w_str, h_str = aspect_str.split(":")
        aspect = float(w_str) / float(h_str)
    except (ValueError, ZeroDivisionError):
        return None
    cell_w_px = int(CONTENT_AREA_W_PX * image_cell["col_span"] / COL_COUNT)
    cell_h_px = int(cell_w_px / aspect)
    return {"height": cell_h_px, "span": image_cell.get("row_span", 1)}


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
