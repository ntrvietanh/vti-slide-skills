"""
strategies/typographic.py — W3.4 v2

Bold, layered typographic decoration: oversized numeral + eyebrow + accent bar.
Brand gradient fill on numeral. viewBox matches gap aspect for clean positioning.
"""
from __future__ import annotations
from gap_classifier import ClassifiedGap

INK_DEEP  = '#0c447c'
INK_MID   = '#185fa5'
INK_LIGHT = '#2A82DE'

OP_NUMERAL = 0.18
OP_ACCENT  = 0.55
OP_EYEBROW = 0.65


def _section_short(section_name: str, max_chars: int = 22) -> str:
    if not section_name:
        return ''
    s = section_name.upper()
    for sep in ('·', '—', '|', '-'):
        if sep in s:
            _, _, rest = s.rpartition(sep)
            s = rest.strip()
    parts = s.split(maxsplit=1)
    if parts and parts[0].isdigit() and len(parts) > 1:
        s = parts[1]
    return s[:max_chars]


def _build_gradient(grad_id: str) -> str:
    return (
        f'<defs><linearGradient id="{grad_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{INK_DEEP}"/>'
        f'<stop offset="60%" stop-color="{INK_MID}"/>'
        f'<stop offset="100%" stop-color="{INK_LIGHT}"/>'
        f'</linearGradient></defs>'
    )


def generate(cg: ClassifiedGap,
             slide_meta: dict = None,
             slide_size: tuple[int, int] = (2560, 1440)) -> str:
    g = cg.gap
    sw, sh = slide_size
    meta = slide_meta or {}

    label = meta.get('decoration_label')
    page_num = meta.get('page_number', 0)
    numeral = f"{int(page_num):02d}" if page_num else ''
    if label is None:
        label = _section_short(meta.get('section_name', ''))
    if not numeral and not label:
        return ''

    aspect = g.w / max(g.h, 1)
    vb_w, vb_h = (round(aspect * 100), 100)
    grad_id = f'tg{int(page_num) if page_num else 0}'

    ctx = cg.brand_context
    parts = [_build_gradient(grad_id)]

    if ctx == 'corner-pocket':
        cx, cy = vb_w / 2, vb_h * 0.70
        parts.append(
            f'<text x="{cx}" y="{cy}" '
            f'font-family="Barlow Condensed, sans-serif" '
            f'font-size="80" font-weight="700" text-anchor="middle" '
            f'fill="url(#{grad_id})" fill-opacity="{OP_NUMERAL}">{numeral}</text>')
        bar_y = vb_h * 0.85
        bar_w = vb_w * 0.30
        parts.append(
            f'<rect x="{(vb_w - bar_w)/2:.1f}" y="{bar_y:.1f}" '
            f'width="{bar_w:.1f}" height="0.6" '
            f'fill="{INK_DEEP}" fill-opacity="{OP_ACCENT}"/>')

    elif ctx == 'footer-merged':
        num_x = vb_w - 6
        num_y = vb_h * 0.92
        parts.append(
            f'<text x="{num_x}" y="{num_y}" '
            f'font-family="Barlow Condensed, sans-serif" '
            f'font-size="95" font-weight="700" text-anchor="end" '
            f'fill="url(#{grad_id})" fill-opacity="{OP_NUMERAL}">{numeral}</text>')
        bar_h = 60
        bar_x = num_x - 60
        bar_y = num_y - bar_h
        parts.append(
            f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" '
            f'width="0.8" height="{bar_h}" '
            f'fill="{INK_DEEP}" fill-opacity="{OP_ACCENT}"/>')
        if label:
            parts.append(
                f'<text x="{num_x}" y="{bar_y - 2}" '
                f'font-family="Barlow Condensed, sans-serif" '
                f'font-size="9" font-weight="600" letter-spacing="2.5" '
                f'text-anchor="end" '
                f'fill="{INK_MID}" fill-opacity="{OP_EYEBROW}">{label}</text>')

    elif ctx == 'bottom-band':
        num_x = 8
        num_y = vb_h * 0.85
        parts.append(
            f'<text x="{num_x}" y="{num_y}" '
            f'font-family="Barlow Condensed, sans-serif" '
            f'font-size="75" font-weight="700" text-anchor="start" '
            f'fill="url(#{grad_id})" fill-opacity="{OP_NUMERAL}">{numeral}</text>')
        line_y = vb_h * 0.55
        parts.append(
            f'<line x1="{vb_w*0.20:.1f}" y1="{line_y:.1f}" '
            f'x2="{vb_w*0.80:.1f}" y2="{line_y:.1f}" '
            f'stroke="{INK_MID}" stroke-width="0.4" '
            f'stroke-opacity="{OP_ACCENT}"/>')
        if label:
            parts.append(
                f'<text x="{vb_w - 8}" y="{vb_h * 0.62:.1f}" '
                f'font-family="Barlow Condensed, sans-serif" '
                f'font-size="11" font-weight="600" letter-spacing="3" '
                f'text-anchor="end" '
                f'fill="{INK_MID}" fill-opacity="{OP_EYEBROW}">{label}</text>')

    else:
        num_x = vb_w - 6
        num_y = vb_h * 0.85
        parts.append(
            f'<text x="{num_x}" y="{num_y}" '
            f'font-family="Barlow Condensed, sans-serif" '
            f'font-size="80" font-weight="700" text-anchor="end" '
            f'fill="url(#{grad_id})" fill-opacity="{OP_NUMERAL}">{numeral}</text>')
        bar_h = 50
        bar_x = num_x - 50
        bar_y = num_y - bar_h
        parts.append(
            f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" '
            f'width="0.7" height="{bar_h}" '
            f'fill="{INK_DEEP}" fill-opacity="{OP_ACCENT}"/>')
        if label:
            parts.append(
                f'<text x="{num_x}" y="{bar_y - 2}" '
                f'font-family="Barlow Condensed, sans-serif" '
                f'font-size="8" font-weight="600" letter-spacing="2" '
                f'text-anchor="end" '
                f'fill="{INK_MID}" fill-opacity="{OP_EYEBROW}">{label}</text>')

    body = ''.join(parts)

    x_pct = g.x / sw * 100
    y_pct = g.y / sh * 100
    w_pct = g.w / sw * 100
    h_pct = g.h / sh * 100

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {vb_w} {vb_h}" '
        f'preserveAspectRatio="none" '
        f'style="width:100%; height:100%; display:block;">'
        f'{body}</svg>'
    )

    return (
        f'<div class="vti-decor vti-decor--typographic" '
        f'data-gap-id="{g.position}-{cg.size_class}" '
        f'style="position:absolute; '
        f'left:{x_pct:.2f}%; top:{y_pct:.2f}%; '
        f'width:{w_pct:.2f}%; height:{h_pct:.2f}%; '
        f'pointer-events:none; overflow:hidden;">'
        f'{svg}</div>'
    )
