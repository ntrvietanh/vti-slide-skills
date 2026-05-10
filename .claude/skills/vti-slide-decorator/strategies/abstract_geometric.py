"""
strategies/abstract_geometric.py — W3.4 v2

Cover-bg-tokyo inspired layered geometric composition:
- Multiple overlapping translucent triangles
- Brand gradient base layer
- Diagonal accent lines for movement

Variants by aspect/size:
  thin-h        → diagonal_strip (3 triangles + gradient)
  thin-v        → vertical_ladder (chevron stack)
  large square  → triangle_cluster (overlapping triangles, asymmetric)
  small/medium  → mixed_dots (varying-size dot pattern + accent)
"""
from __future__ import annotations
from gap_classifier import ClassifiedGap

INK_DEEP   = '#0c447c'
INK_MID    = '#185fa5'
INK_LIGHT  = '#2A82DE'
INK_LIGHTER = '#74B0F0'

OP_FILL_BIG    = 0.20
OP_FILL_SMALL  = 0.12
OP_STROKE      = 0.35
OP_GRAD        = 0.22


def _gradient_def(grad_id: str, direction='horizontal') -> str:
    """Linear gradient — horizontal or diagonal."""
    if direction == 'horizontal':
        coords = 'x1="0" y1="0" x2="1" y2="0"'
    elif direction == 'diagonal':
        coords = 'x1="0" y1="0" x2="1" y2="1"'
    else:  # vertical
        coords = 'x1="0" y1="0" x2="0" y2="1"'
    return (
        f'<defs><linearGradient id="{grad_id}" {coords}>'
        f'<stop offset="0%" stop-color="{INK_DEEP}" stop-opacity="0"/>'
        f'<stop offset="40%" stop-color="{INK_MID}" stop-opacity="{OP_GRAD}"/>'
        f'<stop offset="70%" stop-color="{INK_LIGHT}" stop-opacity="{OP_GRAD*0.7:.3f}"/>'
        f'<stop offset="100%" stop-color="{INK_DEEP}" stop-opacity="0"/>'
        f'</linearGradient></defs>'
    )


# ---------------------------------------------------------------------------
# diagonal_strip — best for thin-h footer bands
# ---------------------------------------------------------------------------
def _diagonal_strip(uid: str) -> str:
    grad_id = f'gs{uid}'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 30" '
        f'preserveAspectRatio="none" '
        f'style="width:100%; height:100%; display:block;">'
        f'{_gradient_def(grad_id, "horizontal")}'
        # Gradient base
        f'<rect x="0" y="0" width="200" height="30" fill="url(#{grad_id})"/>'
        # 3 overlapping triangles, varying opacity
        f'<polygon points="20,30 50,8 80,30" fill="{INK_LIGHT}" '
        f'fill-opacity="{OP_FILL_BIG}"/>'
        f'<polygon points="55,30 95,12 135,30" fill="{INK_MID}" '
        f'fill-opacity="{OP_FILL_BIG*0.8:.3f}"/>'
        f'<polygon points="100,30 140,5 180,30" fill="{INK_DEEP}" '
        f'fill-opacity="{OP_FILL_BIG*0.6:.3f}"/>'
        # Diagonal accent line
        f'<line x1="0" y1="22" x2="200" y2="22" stroke="{INK_DEEP}" '
        f'stroke-width="0.3" stroke-opacity="{OP_STROKE*0.6:.3f}"/>'
        f'<line x1="0" y1="28" x2="200" y2="28" stroke="{INK_MID}" '
        f'stroke-width="0.4" stroke-opacity="{OP_STROKE}"/>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# triangle_cluster — best for large square/landscape
# ---------------------------------------------------------------------------
def _triangle_cluster(uid: str) -> str:
    grad_id = f'tc{uid}'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%; height:100%; display:block;">'
        f'{_gradient_def(grad_id, "diagonal")}'
        # Soft gradient blob behind
        f'<defs><radialGradient id="bg{uid}" cx="50%" cy="50%" r="60%">'
        f'<stop offset="0%" stop-color="{INK_LIGHTER}" stop-opacity="{OP_FILL_BIG*0.8:.3f}"/>'
        f'<stop offset="100%" stop-color="{INK_DEEP}" stop-opacity="0"/>'
        f'</radialGradient></defs>'
        f'<rect x="0" y="0" width="100" height="100" fill="url(#bg{uid})"/>'
        # 4 overlapping translucent triangles, asymmetric
        f'<polygon points="15,85 45,20 70,85" fill="{INK_LIGHT}" '
        f'fill-opacity="{OP_FILL_BIG}"/>'
        f'<polygon points="35,85 65,30 90,85" fill="{INK_MID}" '
        f'fill-opacity="{OP_FILL_BIG*0.85:.3f}"/>'
        f'<polygon points="50,85 75,45 95,85" fill="{INK_DEEP}" '
        f'fill-opacity="{OP_FILL_BIG*0.55:.3f}"/>'
        # Outline accent on largest triangle
        f'<polygon points="15,85 45,20 70,85" fill="none" '
        f'stroke="{INK_DEEP}" stroke-width="0.4" '
        f'stroke-opacity="{OP_STROKE*0.7:.3f}"/>'
        # Bottom line accent
        f'<line x1="10" y1="86" x2="95" y2="86" stroke="{INK_DEEP}" '
        f'stroke-width="0.5" stroke-opacity="{OP_STROKE}"/>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# mixed_dots — varying-size dot pattern + accent (small/medium standalone)
# ---------------------------------------------------------------------------
def _mixed_dots(uid: str, gap_w: int, gap_h: int) -> str:
    aspect = gap_w / max(gap_h, 1)
    cols = 9
    rows = max(3, round(cols / aspect))
    sx = 100 / (cols + 1)
    sy = 100 / (rows + 1)

    dots = []
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            x = c * sx
            y = r * sy
            # Distance from a focal point (right side)
            fx, fy = 75, 50
            d = ((x-fx)**2 + (y-fy)**2)**0.5 / 60
            d = min(d, 1)
            opacity = OP_FILL_BIG * (1 - 0.7 * d)
            radius = 1.4 - 0.6 * d
            if radius > 0.3:
                dots.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.2f}" '
                    f'fill="{INK_MID}" fill-opacity="{opacity:.3f}"/>')
    # Plus a horizontal accent line
    dots.append(
        f'<line x1="10" y1="92" x2="90" y2="92" stroke="{INK_DEEP}" '
        f'stroke-width="0.35" stroke-opacity="{OP_STROKE*0.8:.3f}"/>')
    # And a small triangle accent corner
    dots.append(
        f'<polygon points="80,20 92,20 86,30" fill="{INK_LIGHT}" '
        f'fill-opacity="{OP_FILL_BIG*0.9:.3f}"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%; height:100%; display:block;">'
        f'{"".join(dots)}</svg>'
    )


# ---------------------------------------------------------------------------
# vertical_ladder — for thin-v side strips
# ---------------------------------------------------------------------------
def _vertical_ladder(uid: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 200" '
        f'preserveAspectRatio="none" '
        f'style="width:100%; height:100%; display:block;">'
        # Vertical accent line
        f'<line x1="6" y1="20" x2="6" y2="180" stroke="{INK_DEEP}" '
        f'stroke-width="0.6" stroke-opacity="{OP_STROKE}"/>'
        # Triangles pointing right
        f'<polygon points="12,40 22,50 12,60" fill="{INK_MID}" '
        f'fill-opacity="{OP_FILL_BIG}"/>'
        f'<polygon points="12,80 22,90 12,100" fill="{INK_LIGHT}" '
        f'fill-opacity="{OP_FILL_BIG*0.85:.3f}"/>'
        f'<polygon points="12,120 22,130 12,140" fill="{INK_DEEP}" '
        f'fill-opacity="{OP_FILL_BIG*0.7:.3f}"/>'
        # Small dots between
        f'<circle cx="6" cy="35" r="1.2" fill="{INK_MID}" fill-opacity="{OP_STROKE}"/>'
        f'<circle cx="6" cy="75" r="1.2" fill="{INK_MID}" fill-opacity="{OP_STROKE}"/>'
        f'<circle cx="6" cy="115" r="1.2" fill="{INK_MID}" fill-opacity="{OP_STROKE}"/>'
        f'<circle cx="6" cy="155" r="1.2" fill="{INK_MID}" fill-opacity="{OP_STROKE}"/>'
        f'</svg>'
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate(cg: ClassifiedGap,
             slide_meta: dict = None,
             slide_size: tuple[int, int] = (2560, 1440)) -> str:
    g = cg.gap
    sw, sh = slide_size
    meta = slide_meta or {}
    uid = str(meta.get('page_number', 0))

    if g.aspect == 'thin-h':
        body = _diagonal_strip(uid)
        variant = 'diagonal-strip'
    elif g.aspect == 'thin-v':
        body = _vertical_ladder(uid)
        variant = 'vertical-ladder'
    elif cg.size_class in ('large', 'xl'):
        body = _triangle_cluster(uid)
        variant = 'triangle-cluster'
    elif cg.size_class in ('small', 'medium'):
        body = _mixed_dots(uid, g.w, g.h)
        variant = 'mixed-dots'
    else:
        return ''

    x_pct = g.x / sw * 100
    y_pct = g.y / sh * 100
    w_pct = g.w / sw * 100
    h_pct = g.h / sh * 100

    return (
        f'<div class="vti-decor vti-decor--abstract-geometric" '
        f'data-variant="{variant}" '
        f'data-gap-id="{g.position}-{cg.size_class}" '
        f'style="position:absolute; '
        f'left:{x_pct:.2f}%; top:{y_pct:.2f}%; '
        f'width:{w_pct:.2f}%; height:{h_pct:.2f}%; '
        f'pointer-events:none; overflow:hidden;">'
        f'{body}</div>'
    )
