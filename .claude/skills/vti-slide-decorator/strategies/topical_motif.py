"""
strategies/topical_motif.py — W3.4 v2

Richer motifs: bigger SVG, layered fills + line art, brand gradient on key
elements. Each motif uses 80%+ of viewBox for impact.

Keyword library:
  retail/store/planogram/shelf  → shelf grid + product silhouettes
  ai/intelligence/neural/vision → 3-layer neural with gradient nodes
  data/analytic/metric/kpi      → bar chart with trend line + grid
  delivery/engineer/process     → 3D-feel chevron pipeline
  scale/global/apac             → globe with scattered location dots
  default                       → cover-bg-tokyo style triangles
"""
from __future__ import annotations
from gap_classifier import ClassifiedGap

INK_DEEP    = '#0c447c'
INK_MID     = '#185fa5'
INK_LIGHT   = '#2A82DE'
INK_LIGHTER = '#74B0F0'

OP_FILL    = 0.20
OP_LINE    = 0.45
OP_ACCENT  = 0.65


def _gradient_def(grad_id: str, vertical=True) -> str:
    coords = 'x1="0" y1="0" x2="0" y2="1"' if vertical else 'x1="0" y1="0" x2="1" y2="0"'
    return (
        f'<defs><linearGradient id="{grad_id}" {coords}>'
        f'<stop offset="0%" stop-color="{INK_DEEP}" stop-opacity="{OP_FILL*1.5:.3f}"/>'
        f'<stop offset="100%" stop-color="{INK_LIGHT}" stop-opacity="{OP_FILL*0.6:.3f}"/>'
        f'</linearGradient></defs>'
    )


# ---------------------------------------------------------------------------
# Motif: retail — shelf grid + product silhouettes
# ---------------------------------------------------------------------------
def _motif_retail(uid: str) -> str:
    parts = [_gradient_def(f'rg{uid}')]
    # Shelf back panel (subtle gradient)
    parts.append(
        f'<rect x="12" y="22" width="76" height="64" rx="1" '
        f'fill="url(#rg{uid})"/>')
    # Shelf horizontal lines (3 shelves)
    for y in (38, 58, 78):
        parts.append(
            f'<line x1="12" y1="{y}" x2="88" y2="{y}" stroke="{INK_DEEP}" '
            f'stroke-width="0.6" stroke-opacity="{OP_LINE}"/>')
    # Vertical posts
    parts.append(
        f'<line x1="12" y1="22" x2="12" y2="86" stroke="{INK_DEEP}" '
        f'stroke-width="0.5" stroke-opacity="{OP_LINE*0.8:.3f}"/>')
    parts.append(
        f'<line x1="88" y1="22" x2="88" y2="86" stroke="{INK_DEEP}" '
        f'stroke-width="0.5" stroke-opacity="{OP_LINE*0.8:.3f}"/>')
    # Top rail
    parts.append(
        f'<rect x="10" y="20" width="80" height="2" '
        f'fill="{INK_DEEP}" fill-opacity="{OP_ACCENT}"/>')
    # Product blocks — varied heights, brand colors
    prods = [
        # (x, y_start, w, h)  — y_start determined by shelf
        (16, 26, 7, 12), (25, 28, 6, 10), (33, 25, 8, 13), (43, 27, 6, 11),
        (51, 25, 7, 13), (60, 28, 6, 10), (68, 26, 8, 12), (78, 27, 7, 11),
        (16, 42, 7, 16), (25, 45, 7, 13), (34, 42, 6, 16), (42, 44, 8, 14),
        (52, 42, 6, 16), (60, 45, 7, 13), (69, 42, 8, 16), (79, 44, 7, 14),
        (16, 62, 8, 16), (26, 64, 6, 14), (34, 62, 7, 16), (43, 64, 7, 14),
        (52, 62, 8, 16), (62, 64, 6, 14), (70, 62, 7, 16), (79, 64, 7, 14),
    ]
    colors = [INK_MID, INK_LIGHT, INK_DEEP, INK_LIGHTER]
    for i, (x, y, w, h) in enumerate(prods):
        c = colors[i % 4]
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="0.5" '
            f'fill="{c}" fill-opacity="{OP_FILL*1.3:.3f}"/>')
    # Floor accent
    parts.append(
        f'<line x1="10" y1="88" x2="90" y2="88" stroke="{INK_DEEP}" '
        f'stroke-width="0.7" stroke-opacity="{OP_ACCENT}"/>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Motif: AI neural network — bigger nodes, gradient on layer-2
# ---------------------------------------------------------------------------
def _motif_ai_neural(uid: str) -> str:
    parts = [_gradient_def(f'ai{uid}', vertical=False)]
    L1 = [(15, 35), (15, 50), (15, 65)]
    L2 = [(50, 22), (50, 38), (50, 54), (50, 70), (50, 86)]
    L3 = [(85, 35), (85, 50), (85, 65)]
    # Edges
    for x1, y1 in L1:
        for x2, y2 in L2:
            parts.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{INK_MID}" stroke-width="0.3" '
                f'stroke-opacity="{OP_LINE*0.5:.3f}"/>')
    for x1, y1 in L2:
        for x2, y2 in L3:
            parts.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{INK_MID}" stroke-width="0.3" '
                f'stroke-opacity="{OP_LINE*0.5:.3f}"/>')
    # Layer 1 nodes — outlined
    for x, y in L1:
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="3" fill="white" '
            f'stroke="{INK_DEEP}" stroke-width="0.8" '
            f'stroke-opacity="{OP_ACCENT}"/>')
    # Layer 2 nodes — gradient filled (the "brain" layer, most prominent)
    for x, y in L2:
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="3.5" fill="url(#ai{uid})"/>')
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="3.5" fill="none" '
            f'stroke="{INK_DEEP}" stroke-width="0.4" '
            f'stroke-opacity="{OP_LINE}"/>')
    # Layer 3 nodes — solid filled
    for x, y in L3:
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="3" fill="{INK_MID}" '
            f'fill-opacity="{OP_FILL*1.5:.3f}"/>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Motif: data bars — bars + trend line + grid
# ---------------------------------------------------------------------------
def _motif_data_bars(uid: str) -> str:
    parts = [_gradient_def(f'db{uid}', vertical=True)]
    # Background grid lines (horizontal)
    for y in (30, 45, 60, 75):
        parts.append(
            f'<line x1="14" y1="{y}" x2="86" y2="{y}" stroke="{INK_MID}" '
            f'stroke-width="0.2" stroke-opacity="{OP_FILL*0.7:.3f}" '
            f'stroke-dasharray="1.5 1.5"/>')
    # Bars (8) with gradient + rounded tops
    bars = [
        (18, 65, 25), (26, 55, 35), (34, 45, 45), (42, 60, 30),
        (50, 32, 58), (58, 50, 40), (66, 38, 52), (74, 53, 37),
    ]
    for x, y, h in bars:
        parts.append(
            f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="1" '
            f'fill="url(#db{uid})"/>')
    # Trend line connecting bar tops
    pts = ' '.join(f'{x+3},{y}' for x, y, h in bars)
    parts.append(
        f'<polyline points="{pts}" fill="none" stroke="{INK_DEEP}" '
        f'stroke-width="0.8" stroke-opacity="{OP_LINE}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>')
    # Trend line dots
    for x, y, h in bars:
        parts.append(
            f'<circle cx="{x+3}" cy="{y}" r="1.2" fill="{INK_DEEP}" '
            f'fill-opacity="{OP_ACCENT}"/>')
    # X-axis baseline
    parts.append(
        f'<line x1="14" y1="92" x2="86" y2="92" stroke="{INK_DEEP}" '
        f'stroke-width="0.7" stroke-opacity="{OP_ACCENT}"/>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Motif: pipeline — 3D-feel chevrons + endpoint
# ---------------------------------------------------------------------------
def _motif_pipeline(uid: str) -> str:
    parts = [_gradient_def(f'pp{uid}', vertical=False)]
    # 4 chevrons left-to-right with shadow effect
    for i, x in enumerate((14, 30, 46, 62)):
        # Shadow chevron (offset)
        parts.append(
            f'<polygon points="{x+1.5},42 {x+10.5},51 {x+1.5},60" '
            f'fill="{INK_DEEP}" fill-opacity="{OP_FILL*0.5:.3f}"/>')
        # Main chevron with gradient
        parts.append(
            f'<polygon points="{x},40 {x+10},50 {x},60" '
            f'fill="url(#pp{uid})"/>')
        # Outline
        parts.append(
            f'<polygon points="{x},40 {x+10},50 {x},60" '
            f'fill="none" stroke="{INK_DEEP}" stroke-width="0.4" '
            f'stroke-opacity="{OP_LINE}"/>')
    # Endpoint: gear-like ring with center dot
    parts.append(
        f'<circle cx="84" cy="50" r="9" fill="white" '
        f'stroke="{INK_DEEP}" stroke-width="0.8" '
        f'stroke-opacity="{OP_LINE}"/>')
    parts.append(
        f'<circle cx="84" cy="50" r="6" fill="none" stroke="{INK_MID}" '
        f'stroke-width="0.5" stroke-opacity="{OP_LINE*0.7:.3f}"/>')
    parts.append(
        f'<circle cx="84" cy="50" r="2.5" fill="{INK_DEEP}" '
        f'fill-opacity="{OP_ACCENT}"/>')
    # Gear teeth (small)
    for angle_deg in (0, 60, 120, 180, 240, 300):
        import math
        rad = math.radians(angle_deg)
        x1 = 84 + 9 * math.cos(rad)
        y1 = 50 + 9 * math.sin(rad)
        x2 = 84 + 11 * math.cos(rad)
        y2 = 50 + 11 * math.sin(rad)
        parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{INK_DEEP}" stroke-width="0.6" '
            f'stroke-opacity="{OP_LINE}"/>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Motif: globe — concentric circles + scattered location dots
# ---------------------------------------------------------------------------
def _motif_globe_wave(uid: str) -> str:
    cx, cy = 50, 50
    parts = [_gradient_def(f'gl{uid}')]
    # Soft fill base
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="36" fill="url(#gl{uid})" '
        f'fill-opacity="{OP_FILL*0.5:.3f}"/>')
    # Concentric arcs
    for r, op_mult in [(36, 1.0), (28, 0.8), (20, 0.6), (12, 0.4)]:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{INK_MID}" stroke-width="0.5" '
            f'stroke-opacity="{OP_LINE*op_mult:.3f}"/>')
    # Equator + meridian
    parts.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="36" ry="10" fill="none" '
        f'stroke="{INK_DEEP}" stroke-width="0.5" stroke-opacity="{OP_LINE}"/>')
    parts.append(
        f'<ellipse cx="{cx}" cy="{cy}" rx="10" ry="36" fill="none" '
        f'stroke="{INK_DEEP}" stroke-width="0.5" stroke-opacity="{OP_LINE}"/>')
    # Location dots — scattered across the globe surface
    locations = [(35, 30), (62, 35), (45, 50), (60, 55), (38, 65), (55, 70)]
    for x, y in locations:
        # Outer ring
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="2.5" fill="none" '
            f'stroke="{INK_DEEP}" stroke-width="0.4" '
            f'stroke-opacity="{OP_LINE*0.8:.3f}"/>')
        # Inner solid
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="1.2" fill="{INK_DEEP}" '
            f'fill-opacity="{OP_ACCENT}"/>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Motif: default — cover-bg-tokyo style overlapping triangles
# ---------------------------------------------------------------------------
def _motif_default_triangles(uid: str) -> str:
    parts = [_gradient_def(f'dt{uid}', vertical=False)]
    # Soft gradient background blob
    parts.append(
        f'<defs><radialGradient id="dtb{uid}" cx="50%" cy="60%" r="50%">'
        f'<stop offset="0%" stop-color="{INK_LIGHTER}" stop-opacity="{OP_FILL*0.7:.3f}"/>'
        f'<stop offset="100%" stop-color="{INK_DEEP}" stop-opacity="0"/>'
        f'</radialGradient></defs>'
        f'<rect x="0" y="0" width="100" height="100" fill="url(#dtb{uid})"/>')
    # 3 overlapping triangles in cover-bg style
    parts.append(
        f'<polygon points="20,80 50,25 65,80" fill="{INK_LIGHT}" '
        f'fill-opacity="{OP_FILL*1.2:.3f}"/>')
    parts.append(
        f'<polygon points="40,80 65,35 85,80" fill="{INK_MID}" '
        f'fill-opacity="{OP_FILL}"/>')
    parts.append(
        f'<polygon points="55,80 75,45 90,80" fill="{INK_DEEP}" '
        f'fill-opacity="{OP_FILL*0.7:.3f}"/>')
    # Outline accent on largest triangle
    parts.append(
        f'<polygon points="20,80 50,25 65,80" fill="none" '
        f'stroke="{INK_DEEP}" stroke-width="0.4" '
        f'stroke-opacity="{OP_LINE*0.6:.3f}"/>')
    # Bottom line accent
    parts.append(
        f'<line x1="15" y1="82" x2="90" y2="82" stroke="{INK_DEEP}" '
        f'stroke-width="0.5" stroke-opacity="{OP_LINE}"/>')
    return ''.join(parts)


# ---------------------------------------------------------------------------
# Keyword → motif lookup
# ---------------------------------------------------------------------------
KEYWORD_MAP = [
    (('retail', 'store', 'planogram', 'shelf', 'sku'),
        _motif_retail, 'retail'),
    (('ai', 'intelligence', 'neural', 'model', 'ml ', 'vision', 'forecast'),
        _motif_ai_neural, 'ai-neural'),
    (('data', 'analytic', 'metric', 'kpi', 'dashboard'),
        _motif_data_bars, 'data-bars'),
    (('delivery', 'engineer', 'process', 'workflow', 'pipeline', 'method'),
        _motif_pipeline, 'pipeline'),
    (('scale', 'global', 'apac', 'reach', 'office', 'country'),
        _motif_globe_wave, 'globe'),
]


def _pick_motif(slide_meta: dict, uid: str) -> tuple[str, str]:
    haystack = ' '.join([
        str(slide_meta.get('section_name', '')),
        str(slide_meta.get('slide_title', '')),
    ]).lower()
    for keywords, motif_fn, variant in KEYWORD_MAP:
        if any(kw in haystack for kw in keywords):
            return motif_fn(uid), variant
    return _motif_default_triangles(uid), 'triangles'


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

    body, variant = _pick_motif(meta, uid)

    x_pct = g.x / sw * 100
    y_pct = g.y / sh * 100
    w_pct = g.w / sw * 100
    h_pct = g.h / sh * 100

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%; height:100%; display:block;">'
        f'{body}</svg>'
    )

    return (
        f'<div class="vti-decor vti-decor--topical-motif" '
        f'data-variant="{variant}" '
        f'data-gap-id="{g.position}-{cg.size_class}" '
        f'style="position:absolute; '
        f'left:{x_pct:.2f}%; top:{y_pct:.2f}%; '
        f'width:{w_pct:.2f}%; height:{h_pct:.2f}%; '
        f'pointer-events:none; overflow:hidden;">'
        f'{svg}</div>'
    )
