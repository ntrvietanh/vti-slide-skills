"""
slide_edits — Per-slide edit primitives for Phase 5 iteration.

After ``render_layout_review_widget`` surfaces issues, use these helpers
to fix one slide at a time without rebuilding the whole deck. Each
function returns a NEW slide_dict (immutable updates, original untouched).

Common workflow inside Phase 5 loop::

    from preview import render_layout_review_widget, deck_stats
    from slide_edits import (change_cell_props, change_cell_component,
                             change_cell_span, replace_row, add_row,
                             remove_row, replace_with_custom_html,
                             change_decoration_label)

    # 1. user reviews wireframe widget; flags s17 cards body truncate
    # 2. fix s17: shorten body text in 6 cards
    slides[16] = change_cell_props(slides[16], row_idx=1, cell_idx=0,
                                   new_props_partial={"body": "Stand inside, zoom shelves, check sightlines."})
    # ... repeat for cells 1-5 in rows 1+2 ...

    # 3. re-render wireframe; verify clean
    widget_html = render_layout_review_widget(slides)
    # show widget; user OK → proceed to compose

For BIG layout changes (e.g. drop 6-card grid → custom SVG diagram), use
``replace_with_custom_html`` — escape hatch to inject a fully custom
HTML/SVG block bypassing the component grid (Principle 5: custom > generic
when message demands it).

All functions are PURE — they return new dicts, do NOT mutate input.
This keeps Phase 5 reversible (easy undo by keeping prior versions).
"""
from __future__ import annotations
import copy
from typing import Any


# ============================================================================
# Cell-level edits
# ============================================================================

def change_cell_props(slide: dict, row_idx: int, cell_idx: int,
                      new_props_partial: dict) -> dict:
    """Update specific props of a cell. Other props untouched.

    Args:
        slide: slide_dict (must have 'rows', not 'special')
        row_idx: 0-based row index
        cell_idx: 0-based cell index within row
        new_props_partial: keys to merge into existing props

    Example::
        # shorten body text in s17 row 1 cell 0
        slide = change_cell_props(slide, 1, 0, {"body": "Shorter text."})
    """
    if 'special' in slide:
        raise ValueError("Cannot edit cells of a special-page slide")
    out = copy.deepcopy(slide)
    cell = out['rows'][row_idx]['cells'][cell_idx]
    cell['props'] = {**cell.get('props', {}), **new_props_partial}
    return out


def change_cell_component(slide: dict, row_idx: int, cell_idx: int,
                          new_component: str, new_props: dict) -> dict:
    """Swap component type entirely (e.g. practice-card → value-medallion).
    Replaces all props since schema differs.
    """
    if 'special' in slide:
        raise ValueError("Cannot edit cells of a special-page slide")
    out = copy.deepcopy(slide)
    cell = out['rows'][row_idx]['cells'][cell_idx]
    cell['component'] = new_component
    cell['props'] = new_props
    return out


def change_cell_span(slide: dict, row_idx: int, cell_idx: int,
                     col_start: int, col_span: int) -> dict:
    """Resize/reposition a cell within its row.
    col_start in 1..12, col_span in 1..12, col_start+col_span ≤ 13.
    """
    if 'special' in slide:
        raise ValueError("Cannot edit cells of a special-page slide")
    if not (1 <= col_start <= 12) or not (1 <= col_span <= 12):
        raise ValueError(f"col_start/col_span out of range: {col_start},{col_span}")
    if col_start + col_span > 13:
        raise ValueError(f"cell extends past col 12: start={col_start} span={col_span}")
    out = copy.deepcopy(slide)
    cell = out['rows'][row_idx]['cells'][cell_idx]
    cell['col_start'] = col_start
    cell['col_span'] = col_span
    return out


def remove_cell(slide: dict, row_idx: int, cell_idx: int) -> dict:
    """Drop one cell from a row. Caller is responsible for resizing
    remaining cells if needed."""
    if 'special' in slide:
        raise ValueError("Cannot edit cells of a special-page slide")
    out = copy.deepcopy(slide)
    out['rows'][row_idx]['cells'].pop(cell_idx)
    return out


def add_cell(slide: dict, row_idx: int, cell: dict, *,
             after_idx: int | None = None) -> dict:
    """Insert a new cell into a row. cell = {col_start, col_span, component, props}."""
    if 'special' in slide:
        raise ValueError("Cannot edit cells of a special-page slide")
    out = copy.deepcopy(slide)
    cells = out['rows'][row_idx]['cells']
    if after_idx is None:
        cells.append(cell)
    else:
        cells.insert(after_idx + 1, cell)
    return out


# ============================================================================
# Row-level edits
# ============================================================================

def replace_row(slide: dict, row_idx: int, new_row: dict) -> dict:
    """Replace a whole row. new_row = {height?, cells: [...], _fill_verified?}."""
    if 'special' in slide:
        raise ValueError("Cannot edit rows of a special-page slide")
    out = copy.deepcopy(slide)
    out['rows'][row_idx] = new_row
    return out


def add_row(slide: dict, after_idx: int | None, new_row: dict) -> dict:
    """Insert a row. after_idx=None → append at end; after_idx=N → insert after row N."""
    if 'special' in slide:
        raise ValueError("Cannot edit rows of a special-page slide")
    out = copy.deepcopy(slide)
    if after_idx is None:
        out['rows'].append(new_row)
    else:
        out['rows'].insert(after_idx + 1, new_row)
    return out


def remove_row(slide: dict, row_idx: int) -> dict:
    """Drop a row. If this leaves slide too sparse, the wireframe will flag it."""
    if 'special' in slide:
        raise ValueError("Cannot edit rows of a special-page slide")
    out = copy.deepcopy(slide)
    out['rows'].pop(row_idx)
    return out


def set_row_height(slide: dict, row_idx: int, height: str) -> dict:
    """Set row height: 'auto' (default) or '1fr' (fill remaining) or
    explicit pixels e.g. '180px'. Use '1fr' carefully — Phase 7 protocol
    says default 'auto' unless content-fill verified."""
    if 'special' in slide:
        raise ValueError("Cannot edit rows of a special-page slide")
    out = copy.deepcopy(slide)
    out['rows'][row_idx]['height'] = height
    return out


def mark_fill_verified(slide: dict, row_idx: int) -> dict:
    """Mark a row as ``_fill_verified=True``. Tells composer the row was
    deliberately built to fill its height — suppresses sparse warnings.
    Only set this AFTER you've verified content actually fills."""
    if 'special' in slide:
        raise ValueError("Cannot edit rows of a special-page slide")
    out = copy.deepcopy(slide)
    out['rows'][row_idx]['_fill_verified'] = True
    return out


# ============================================================================
# Slide-level edits
# ============================================================================

def change_slide_meta(slide: dict, **meta_updates: Any) -> dict:
    """Update slide_meta fields: page_number, slide_title, section_name,
    layout_class, decoration_label, decoration_text."""
    if 'special' in slide:
        # special pages have 'props' not 'slide_meta'
        out = copy.deepcopy(slide)
        out['props'] = {**out.get('props', {}), **meta_updates}
        return out
    out = copy.deepcopy(slide)
    out['slide_meta'] = {**out.get('slide_meta', {}), **meta_updates}
    return out


def change_decoration_label(slide: dict, label: str) -> dict:
    """Override the decoration overlay label. Read by ``vti-slide-decorator``
    skill's typographic strategy. Default = section_name (often too long
    and gets cropped). Set short version e.g. 'SEAMLESS CX' (≤18 chars)."""
    return change_slide_meta(slide, decoration_label=label)


def change_layout_class(slide: dict, new_class: str) -> dict:
    """Change layout_class: 'default' / 'case-study' / 'data-dense'."""
    return change_slide_meta(slide, layout_class=new_class)


# ============================================================================
# Custom-build escape hatch (Principle 5)
# ============================================================================

def replace_with_custom_html(slide: dict, custom_html: str, *,
                             custom_css: str = "",
                             keep_chrome: bool = True) -> dict:
    """Replace the entire grid body with a custom HTML block. Use when
    no component combination fits the message — Principle 5: custom >
    generic when message demands it.

    The composer will still render the chrome (header bar, page footer)
    around your custom block if ``keep_chrome=True``.

    Example use case::
        # s17 6-card grid was truncating bodies → replace with single
        # SVG illustration showing the 6-stage Smart Planogram pipeline
        slide = replace_with_custom_html(slide, '''
            <svg viewBox="0 0 1200 480">...stages...</svg>
        ''', custom_css=".vti-custom-stages { ... }")

    The result is wrapped in a ``custom_block`` flag on the slide; the
    composer recognizes this and bypasses the row/cell rendering.
    """
    if 'special' in slide:
        raise ValueError("Use special-page schema for narrator/cover slides")
    out = copy.deepcopy(slide)
    out['custom_block'] = {
        'html': custom_html,
        'css': custom_css,
        'keep_chrome': keep_chrome,
    }
    # zero out the grid rows since custom takes over
    out['rows'] = []
    return out


# ============================================================================
# Convenience helpers
# ============================================================================

def find_cells_by_component(slide: dict, component: str) -> list[tuple[int, int]]:
    """Locate (row_idx, cell_idx) pairs for cells using ``component``.
    Useful for batch edits like 'shorten all practice-card bodies'."""
    if 'special' in slide:
        return []
    out = []
    for ri, r in enumerate(slide.get('rows', [])):
        for ci, c in enumerate(r.get('cells', [])):
            if c.get('component') == component:
                out.append((ri, ci))
    return out


def shorten_practice_cards(slide: dict, max_chars: int = 130) -> dict:
    """Convenience: trim all practice-card.body to max_chars. Common fix
    when 6-card 4-col-each grid truncates bodies."""
    if 'special' in slide:
        return slide
    out = copy.deepcopy(slide)
    for r in out.get('rows', []):
        for c in r.get('cells', []):
            if c.get('component') == 'practice-card':
                body = c.get('props', {}).get('body', '')
                if len(body) > max_chars:
                    c['props']['body'] = body[:max_chars - 1].rstrip() + '…'
    return out
