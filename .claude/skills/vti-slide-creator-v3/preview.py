"""
Phase 5 Layout Review — Wireframe widget renderer + single-slide preview.

Two APIs serve different needs:

1. ``render_layout_review_widget(slides)`` — primary Phase 5 tool.
   Renders all slides as 16:9 wireframe boxes (NOT full render). Each box
   shows row/cell structure with component names + char-fit indicators.
   Empty bottom of a 16:9 box = visible sparse signal. Red-bordered
   cells = predicted overflow. Output is a single HTML fragment for
   ``visualize:show_widget`` — user reviews planned layout BEFORE
   compose, catches issues early.

2. ``render_inline_preview(slide)`` — single-slide full render at 0.5×.
   Useful AFTER wireframe review when you want to verify one specific
   slide pixel-perfect before committing to deck compose. Slow.

3. ``render_grid_summary(slide)`` — plain-text grid summary for logs.
4. ``deck_stats(slides)`` — programmatic summary, no render.

Phase 5 protocol:
   plan → render_layout_review_widget(slides) → user reviews →
   apply slide_edits → re-wireframe → user OK → compose_deck →
   decorator skill → audit → final.
"""
from __future__ import annotations

import sys
from pathlib import Path

_PAGE_BUILDER_ROOT = (
    Path(__file__).resolve().parent.parent / "vti-slide-page-builder-v3"
)
if str(_PAGE_BUILDER_ROOT) not in sys.path:
    sys.path.insert(0, str(_PAGE_BUILDER_ROOT))

from composer_grid import compose_slide_grid  # noqa: E402
import composer_grid as _cg  # noqa: E402


# ============================================================================
# Wireframe widget — primary Phase 5 review tool
# ============================================================================

_COMP_META_RAW = getattr(_cg, '_COMPONENT_META', {})

_SKIP_PROP_KEYS = {
    'icon', 'src', 'image', 'color_tone', 'tone', 'frame', 'aspect_ratio',
    'caption_position', 'density', 'layout', 'icon_style', 'number',
}

_LAYOUT_CAPACITY = {'default': 1500, 'case-study': 1300, 'data-dense': 1800}


def _walk_chars(value):
    total = 0
    if isinstance(value, str):
        if value.startswith('data:') or value.lower().endswith(
                ('.png', '.jpg', '.jpeg', '.svg', '.webp')):
            return 0
        return len(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            if k in _SKIP_PROP_KEYS:
                continue
            total += _walk_chars(v)
    elif isinstance(value, list):
        for item in value:
            total += _walk_chars(item)
    return total


def _cell_chars(cell):
    return _walk_chars(cell.get('props', {}))


def _cell_capacity(cell):
    comp = cell.get('component', '')
    raw = _COMP_META_RAW.get(comp, {})
    if raw.get('capacity_chars_fixed'):
        return raw['capacity_chars_fixed']
    return raw.get('capacity_chars_per_col', 30) * cell.get('col_span', 1)


def _cell_kind(cell):
    return _COMP_META_RAW.get(cell.get('component', ''), {}).get('kind', 'text')


def _fit_status(cell):
    chars = _cell_chars(cell)
    cap = _cell_capacity(cell)
    if cap == 0:
        return 'ok'
    ratio = chars / cap
    if ratio < 0.4:
        return 'sparse'
    if ratio > 1.05:
        return 'overflow'
    if ratio > 0.85:
        return 'tight'
    return 'ok'


def _slide_summary(slide):
    if 'special' in slide:
        return {
            'kind': 'special', 'special_name': slide['special'],
            'chars': _walk_chars(slide.get('props', {})),
            'cells_count': 1, 'rows_count': 1, 'flags': [],
        }
    rows = slide.get('rows', [])
    cells_total = sum(len(r.get('cells', [])) for r in rows)
    chars_total = 0
    overflows, sparse, image_cells = [], [], []
    for ri, r in enumerate(rows):
        for ci, c in enumerate(r.get('cells', [])):
            chars_total += _cell_chars(c)
            fit = _fit_status(c)
            if fit == 'overflow':
                overflows.append((ri, ci, c.get('component')))
            elif fit == 'sparse':
                sparse.append((ri, ci, c.get('component')))
            if c.get('component') == 'image-tile':
                image_cells.append((ri, ci))
    layout_class = slide.get('slide_meta', {}).get('layout_class', 'default')
    capacity = _LAYOUT_CAPACITY.get(layout_class, 1500)
    fill_pct = chars_total / capacity if capacity else 0
    flags = []
    if fill_pct < 0.40:
        flags.append('SPARSE')
    if fill_pct > 1.10:
        flags.append('OVERCROWDED')
    if overflows:
        flags.append(f'OVERFLOW×{len(overflows)}')
    if image_cells:
        flags.append(f'IMG×{len(image_cells)}-aspect-risk')
    return {
        'kind': 'content', 'rows_count': len(rows),
        'cells_count': cells_total, 'chars': chars_total,
        'capacity': capacity, 'fill_pct': fill_pct, 'flags': flags,
        'overflows': overflows, 'sparse_cells': sparse,
        'image_cells': image_cells,
    }


_WIREFRAME_STYLE = """<style>
.wf{font-size:11px;line-height:1.3}
.wf .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:0 0 8px;padding:8px 10px;background:var(--color-background-secondary);border-radius:6px}
.wf .stats div{font-size:10px}
.wf .stats b{display:block;font-size:16px;font-weight:500;color:var(--color-text-primary);margin-top:2px}
.wf .lg{display:flex;gap:8px;font-size:10px;color:var(--color-text-secondary);margin:0 0 10px;flex-wrap:wrap}
.wf .lg span{display:inline-flex;align-items:center;gap:3px}
.wf .lg i{width:8px;height:8px;border:0.5px solid;display:inline-block}
.wf .sb-sp{display:flex;align-items:baseline;gap:6px;padding:5px 10px;margin-bottom:4px;background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);border-radius:5px;font-size:11px;color:var(--color-text-secondary);font-style:italic}
.wf .sb-169{aspect-ratio:16/9;border:0.5px solid var(--color-border-secondary);border-radius:6px;background:var(--color-background-primary);display:flex;flex-direction:column;margin-bottom:10px;overflow:hidden}
.wf .hd{padding:4px 10px;border-bottom:0.5px solid var(--color-border-tertiary);display:flex;align-items:baseline;gap:6px;flex-shrink:0;background:var(--color-background-secondary)}
.wf .ca{flex:1;padding:6px 8px 6px 22px;display:flex;flex-direction:column;gap:3px;overflow:hidden;position:relative}
.wf .ft{padding:3px 10px;border-top:0.5px solid var(--color-border-tertiary);display:flex;justify-content:space-between;align-items:center;flex-shrink:0;font-size:9px;color:var(--color-text-secondary);font-family:monospace;background:var(--color-background-secondary)}
.wf .pn{font-family:monospace;background:#0c447c;color:#fff;padding:0 5px;border-radius:3px;font-size:9px;font-weight:500;font-style:normal}
.wf .tt{flex:1;font-weight:500;font-style:normal;color:var(--color-text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}
.wf .mt{font-family:monospace;font-size:9px;color:var(--color-text-secondary);font-style:normal}
.wf .rw{display:grid;grid-template-columns:repeat(12,1fr);gap:2px;position:relative;flex-shrink:0}
.wf .rl{position:absolute;left:-18px;top:50%;transform:translateY(-50%);font-size:8px;color:#888;font-family:monospace}
.wf .cell{border:0.5px solid;border-radius:3px;padding:3px 5px;min-height:36px;display:flex;flex-direction:column;justify-content:center;overflow:hidden}
.wf .cn{font-size:10px;font-weight:500;line-height:1.2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wf .cm{font-size:9px;opacity:.7;font-family:monospace;line-height:1.1}
.wf .k-text{background:#e6f1fb;border-color:#185fa5;color:#0c447c}
.wf .k-data{background:#eaf3de;border-color:#3b6d11;color:#27500a}
.wf .k-card{background:#eeedfe;border-color:#534ab7;color:#3c3489}
.wf .k-visual,.wf .k-media{background:#faeeda;border-color:#854f0b;color:#633806}
.wf .k-structural{background:#f1efe8;border-color:#5f5e5a;color:#444441}
.wf .f-overflow{border-width:1.5px;border-color:#a32d2d!important;background:#fcebeb!important;color:#791f1f!important}
.wf .f-sparse{border-style:dashed;opacity:.7}
.wf .f-tight{border-width:1px;border-color:#ba7517!important}
.wf .fok{color:#3b6d11;font-weight:500}
.wf .fwn{color:#ba7517;font-weight:500}
.wf .fer{color:#a32d2d;font-weight:500}
.wf .fl{padding:1px 4px;border-radius:2px;color:#fff;font-size:8px;margin-left:3px;font-weight:500}
.wf .flo{background:#a32d2d}
.wf .flw{background:#ba7517}
.wf .fln{background:#5f5e5a}
.wf .ca::after{content:"";position:absolute;top:0;left:0;right:0;bottom:0;background:repeating-linear-gradient(135deg,transparent 0 12px,rgba(0,0,0,0.012) 12px 13px);pointer-events:none}
</style>"""


def _row_html(row, idx):
    cells = row.get('cells', [])
    fv = row.get('_fill_verified', False)
    parts = []
    for c in cells:
        comp = c.get('component', '?')
        cs, csp = c.get('col_start', 1), c.get('col_span', 12)
        chars, cap, fit = _cell_chars(c), _cell_capacity(c), _fit_status(c)
        kind = _cell_kind(c)
        parts.append(
            f'<div class="cell k-{kind} f-{fit}" '
            f'style="grid-column:{cs}/span {csp}">'
            f'<div class="cn">{comp}</div>'
            f'<div class="cm">{cs}-{cs+csp-1}·{chars}/{cap}c</div></div>'
        )
    fvm = '✓' if fv else ''
    return (f'<div class="rw"><span class="rl">r{idx}{fvm}</span>'
            f'{"".join(parts)}</div>')


def _slide_block(idx, slide):
    if 'special' in slide:
        sp = slide['special']
        props = slide.get('props', {})
        ttl = (props.get('deck_title') or props.get('section_title') or
               props.get('intro_text', '')[:60] or sp).replace('\n', ' ')
        if len(ttl) > 70:
            ttl = ttl[:70] + '…'
        ch = _walk_chars(props)
        return (f'<div class="sb-sp"><span class="pn">{idx:02d}</span>'
                f'<span class="tt">{ttl}</span>'
                f'<span class="mt">special:{sp} · {ch}c</span></div>')
    summ = _slide_summary(slide)
    meta = slide.get('slide_meta', {})
    ttl = meta.get('slide_title', '')
    if len(ttl) > 75:
        ttl = ttl[:75] + '…'
    sec = meta.get('section_name', '—')
    lay = meta.get('layout_class', 'default')
    pg = meta.get('page_number', idx)
    rs = ''.join(_row_html(r, ri+1)
                 for ri, r in enumerate(slide.get('rows', [])))
    flags_html = ''
    for f in summ['flags']:
        cls = ('flo' if 'OVERFLOW' in f or 'OVERCROWDED' in f else
               'flw' if 'SPARSE' in f or 'aspect' in f else 'fln')
        flags_html += f'<span class="fl {cls}">{f}</span>'
    fc = ('fok' if 0.55 <= summ['fill_pct'] <= 1.0 else
          'fwn' if 0.40 <= summ['fill_pct'] <= 1.10 else 'fer')
    clean = '<span class="fok">○ clean</span>'
    return (
        f'<div class="sb-169">'
        f'<div class="hd"><span class="pn">{pg:02d}</span>'
        f'<span class="tt">{ttl}</span>'
        f'<span class="mt">{sec} · {lay}</span></div>'
        f'<div class="ca">{rs}</div>'
        f'<div class="ft"><span>{summ["rows_count"]}r · '
        f'{summ["cells_count"]}c · '
        f'<span class="{fc}">{summ["chars"]}/{summ["capacity"]}c '
        f'({int(summ["fill_pct"]*100)}%)</span></span>'
        f'<span>{flags_html or clean}</span></div></div>'
    )


def render_layout_review_widget(slides: list) -> str:
    """Phase 5 — primary tool. Render ALL slides as 16:9 wireframe boxes for
    batch layout review BEFORE compose.

    Args:
        slides: list of slide dicts (regular ``{slide_meta, rows}`` or
            ``{special, props}`` special-page).

    Returns:
        Self-contained HTML fragment. Pass directly to
        ``visualize:show_widget`` as ``widget_code``.

    Each content slide renders at 16:9 aspect ratio matching the real
    slide. Empty bottom area = visible sparse signal. Cells are colored
    by component category (text/data/card/visual/structural). Red-
    bordered cell = predicted overflow. Dashed cell = predicted sparse.

    Phase 5 checkpoint: user reviews this widget; flags issues; calls
    ``slide_edits`` to fix; re-render. Repeat until no critical flags.
    Then proceed to compose_deck.
    """
    n = len(slides)
    sparse_n = overflow_n = image_n = 0
    chars_total = 0
    for s in slides:
        if 'special' in s:
            continue
        sm = _slide_summary(s)
        chars_total += sm['chars']
        if 'SPARSE' in sm['flags']:
            sparse_n += 1
        if any('OVERFLOW' in f for f in sm['flags']):
            overflow_n += 1
        if any('IMG' in f for f in sm['flags']):
            image_n += 1
    fer = "fer" if sparse_n > 0 else "fok"
    fov = "fer" if overflow_n > 0 else "fok"
    head = (
        f'<div class="wf">{_WIREFRAME_STYLE}'
        f'<div class="stats">'
        f'<div>slides<b>{n}</b></div>'
        f'<div>chars<b>{chars_total:,}</b></div>'
        f'<div>sparse-flag<b class="{fer}">{sparse_n}</b></div>'
        f'<div>overflow-flag<b class="{fov}">{overflow_n}</b></div>'
        f'</div>'
        f'<div class="lg">'
        f'<span><i style="background:#e6f1fb;border-color:#185fa5"></i>text</span>'
        f'<span><i style="background:#eaf3de;border-color:#3b6d11"></i>data/stat</span>'
        f'<span><i style="background:#eeedfe;border-color:#534ab7"></i>card</span>'
        f'<span><i style="background:#faeeda;border-color:#854f0b"></i>visual</span>'
        f'<span><i style="background:#f1efe8;border-color:#5f5e5a"></i>structural</span>'
        f'<span style="margin-left:6px">·</span>'
        f'<span><i style="background:#fcebeb;border-color:#a32d2d"></i>overflow</span>'
        f'<span><i style="background:#fff;border:0.5px dashed #888"></i>sparse</span>'
        f'<span style="margin-left:6px">·</span>'
        f'<span style="color:var(--color-text-tertiary);font-style:italic">'
        f'each box = 16:9 slide · empty bottom = whitespace</span>'
        f'</div>'
    )
    cards = ''.join(_slide_block(i+1, s) for i, s in enumerate(slides))
    return head + cards + '</div>'


# ============================================================================
# Single-slide preview (full render at half scale)
# ============================================================================

_PREVIEW_FRAME_CSS = """
.vti-preview-frame {
  position: relative;
  width: 640px;
  max-width: 100%;
  height: 360px;
  margin: 0 auto;
  overflow: hidden;
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: 10px;
  background: #FFFFFF;
}
.vti-preview-frame > .slide.layout-grid {
  transform: scale(0.5);
  transform-origin: top left;
}
.vti-preview-meta {
  text-align: center;
  font-family: var(--font-mono, monospace);
  font-size: 10px;
  color: var(--color-text-tertiary);
  margin-top: 6px;
}
"""


def render_inline_preview(slide_input: dict, *,
                          show_chrome: bool = True,
                          show_meta_footer: bool = True) -> str:
    """Single-slide full render at 0.5× scale. Useful AFTER wireframe
    review to verify ONE slide pixel-perfect before deck compose.
    Slow — not for batch review.
    """
    sm = dict(slide_input.get("slide_meta", {}))
    sm["show_chrome"] = show_chrome
    composed = compose_slide_grid({**slide_input, "slide_meta": sm})
    slide_html = composed["slide_html"]
    slide_css = composed["slide_css"]
    meta = composed["metadata"]
    meta_footer_html = ""
    if show_meta_footer:
        comps = ", ".join(meta["components_rendered"])
        meta_footer_html = (
            f'<div class="vti-preview-meta">'
            f'rows: {meta["row_count"]} · cells: {meta["cell_count"]} · '
            f'components: {comps}</div>'
        )
    return (
        f"<style>\n{slide_css}\n{_PREVIEW_FRAME_CSS}\n</style>\n"
        f'<div class="vti-preview-frame">\n{slide_html}\n</div>\n'
        f'{meta_footer_html}'
    )


def render_grid_summary(slide_input: dict) -> str:
    """Plain-text grid summary for logs / chat reasoning."""
    rows = slide_input.get("rows", [])
    lines = []
    for ri, row in enumerate(rows, 1):
        h = row.get("height", "auto")
        cells = row.get("cells", [])
        cell_descs = []
        for c in cells:
            cs, cn = c.get("col_start", 1), c.get("col_span", 12)
            comp = c.get("component", "?")
            cell_descs.append(f"col {cs}-{cs + cn - 1}: {comp}")
        lines.append(f"Row {ri} (h={h}): " + " | ".join(cell_descs))
    return "\n".join(lines)


def deck_stats(slides: list) -> dict:
    """Programmatic deck summary (no render). For scripts / CI / logs."""
    out = {
        'slide_count': len(slides), 'special_count': 0, 'content_count': 0,
        'total_chars': 0, 'sparse_slides': [], 'overflow_slides': [],
        'image_slides': [], 'flagged_slides': [],
    }
    for i, s in enumerate(slides, 1):
        if 'special' in s:
            out['special_count'] += 1
            continue
        out['content_count'] += 1
        sm = _slide_summary(s)
        out['total_chars'] += sm['chars']
        if 'SPARSE' in sm['flags']:
            out['sparse_slides'].append(i)
        if any('OVERFLOW' in f for f in sm['flags']):
            out['overflow_slides'].append(i)
        if any('IMG' in f for f in sm['flags']):
            out['image_slides'].append(i)
        if sm['flags']:
            out['flagged_slides'].append((i, sm['flags']))
    return out
