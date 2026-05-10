"""Low-level SVG building blocks consumed by the 7 high-level primitives.

Every helper here returns an SVG fragment string (no <svg> wrapper).
The high-level primitives in ``diagram_builder`` compose these into
complete diagrams.

Constants
---------
- ``CANVAS_W = 1180``   — canonical canvas width (consumers may override)
- ``CANVAS_H_WIDE = 460`` — wide horizontal flow height
- ``CANVAS_H_TALL = 600`` — tall diagram height (quadrants, fanouts, layered)
- ``STROKE_NORMAL = 2``
- ``STROKE_THICK = 3``
- ``ARROW_HEAD_SIZE = 6``
- ``CORNER_RADIUS = 8``
"""
from __future__ import annotations

import html as _html
from tokens_bridge import accent, font_body, token

CANVAS_W = 1180
# v4.5 (2026-05-10): canvas heights reduced to remove the ~150-200px of
# vertical whitespace below diagrams that the v4.4 generator left at the
# bottom of every flow / quadrant. Old defaults (460, 600) padded the
# canvas far beyond actual content. New defaults size to roughly the
# minimum a primitive needs; primitives that pack densely (quadrant +
# medallions) still pass an explicit `height_override` if they need
# more.
CANVAS_H_WIDE = 280   # was 460 — a 4-step horizontal flow needs ~210px
CANVAS_H_TALL = 480   # was 600 — quadrant 2x2 with 5-item cells needs ~430px
STROKE_NORMAL = 2
STROKE_THICK = 3
ARROW_HEAD_SIZE = 6
CORNER_RADIUS = 8


def esc(text: str | None) -> str:
    """Escape XML-special characters in user text. Empty/None → ''."""
    if text is None:
        return ""
    return _html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# Frame + canvas helpers
# ---------------------------------------------------------------------------
def svg_open(width: int, height: int, *,
             title: str = "", desc: str = "",
             bg: str = "pale") -> str:
    """Open the SVG root element with role=img + title + desc.

    Returns the opening <svg> + bg <rect> + <title> + <desc>.
    The caller is responsible for closing with `</svg>`.
    """
    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'role="img" aria-labelledby="diag-title diag-desc" '
        f'style="width:100%;height:auto;display:block;">\n'
        f'  <title id="diag-title">{esc(title)}</title>\n'
        f'  <desc id="diag-desc">{esc(desc)}</desc>\n'
        f'  <rect width="{width}" height="{height}" fill="{accent(bg)}"/>\n'
    )


def svg_close() -> str:
    return "</svg>\n"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------
def svg_title_label(x: int, y: int, text: str, *,
                    accent_alias: str = "navy",
                    size: int = 14,
                    weight: int = 700,
                    letter_spacing: int = 2) -> str:
    """Section heading — uppercase-style label at top of the canvas."""
    return (
        f'  <text x="{x}" y="{y}" font-size="{size}" '
        f'font-weight="{weight}" fill="{accent(accent_alias)}" '
        f'font-family="{font_body}" letter-spacing="{letter_spacing}">'
        f'{esc(text).upper()}</text>\n'
    )


def svg_subtitle_label(x: int, y: int, text: str, *,
                       accent_alias: str = "muted",
                       size: int = 11) -> str:
    return (
        f'  <text x="{x}" y="{y}" font-size="{size}" '
        f'fill="{accent(accent_alias)}" font-family="{font_body}">'
        f'{esc(text)}</text>\n'
    )


def svg_text(x: int, y: int, text: str, *,
             accent_alias: str = "ink",
             size: int = 11,
             weight: int = 400,
             anchor: str = "start") -> str:
    """Generic text element."""
    weight_attr = f' font-weight="{weight}"' if weight != 400 else ""
    return (
        f'  <text x="{x}" y="{y}" font-size="{size}"{weight_attr} '
        f'fill="{accent(accent_alias)}" font-family="{font_body}" '
        f'text-anchor="{anchor}">{esc(text)}</text>\n'
    )


# ---------------------------------------------------------------------------
# Box helpers
# ---------------------------------------------------------------------------
def svg_box(x: int, y: int, w: int, h: int, *,
            fill_alias: str = "white",
            stroke_alias: str = "border",
            stroke_width: int = STROKE_NORMAL,
            radius: int = CORNER_RADIUS,
            opacity: float = 1.0) -> str:
    """Outlined rounded rectangle."""
    op = f' opacity="{opacity}"' if opacity < 1.0 else ""
    fill = "white" if fill_alias == "white" else accent(fill_alias)
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" stroke="{accent(stroke_alias)}" '
        f'stroke-width="{stroke_width}"{op}/>\n'
    )


def svg_box_filled(x: int, y: int, w: int, h: int, *,
                   fill_alias: str,
                   radius: int = CORNER_RADIUS,
                   opacity: float = 1.0) -> str:
    """Solid fill rounded rectangle (no stroke)."""
    op = f' opacity="{opacity}"' if opacity < 1.0 else ""
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{accent(fill_alias)}"{op}/>\n'
    )


def svg_card(x: int, y: int, w: int, h: int, label: str,
             sub: str = "", *,
             accent_alias: str = "deep",
             title_size: int = 13,
             sub_size: int = 11) -> str:
    """Rounded card with accent stroke + centered title + sub-text."""
    out = svg_box(x, y, w, h,
                  fill_alias="white",
                  stroke_alias=accent_alias,
                  stroke_width=STROKE_NORMAL)
    out += svg_text(x + w // 2, y + h // 2 - (sub_size if sub else 0),
                    label, accent_alias=accent_alias, size=title_size,
                    weight=700, anchor="middle")
    if sub:
        out += svg_text(x + w // 2, y + h // 2 + sub_size + 4,
                        sub, accent_alias="ink", size=sub_size,
                        anchor="middle")
    return out


# ---------------------------------------------------------------------------
# Arrow + connector helpers
# ---------------------------------------------------------------------------
def svg_arrow(x1: int, y1: int, x2: int, y2: int, *,
              accent_alias: str = "muted",
              stroke_width: int = STROKE_NORMAL,
              dashed: bool = False) -> str:
    """Straight arrow with filled-triangle head at (x2, y2).

    The triangle points in the direction (x1, y1) → (x2, y2).
    """
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    line = (
        f'  <path d="M {x1} {y1} L {x2} {y2}" '
        f'stroke="{accent(accent_alias)}" stroke-width="{stroke_width}" '
        f'fill="none"{dash}/>\n'
    )
    # Triangle perpendicular to direction at x2, y2
    import math
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1
    ux, uy = dx / length, dy / length
    # perpendicular vector
    px, py = -uy, ux
    head_size = ARROW_HEAD_SIZE
    tip_x, tip_y = x2, y2
    base_x, base_y = x2 - ux * head_size * 1.6, y2 - uy * head_size * 1.6
    p1x, p1y = base_x + px * head_size, base_y + py * head_size
    p2x, p2y = base_x - px * head_size, base_y - py * head_size
    triangle = (
        f'  <path d="M {tip_x:.1f} {tip_y:.1f} '
        f'L {p1x:.1f} {p1y:.1f} L {p2x:.1f} {p2y:.1f} Z" '
        f'fill="{accent(accent_alias)}"/>\n'
    )
    return line + triangle


def svg_connector_horizontal(x1: int, y: int, x2: int, *,
                             accent_alias: str = "muted",
                             stroke_width: int = STROKE_NORMAL) -> str:
    """Convenience for horizontal arrows between boxes at the same y."""
    return svg_arrow(x1, y, x2, y, accent_alias=accent_alias,
                     stroke_width=stroke_width)


def svg_connector_vertical(x: int, y1: int, y2: int, *,
                           accent_alias: str = "muted",
                           stroke_width: int = STROKE_NORMAL,
                           dashed: bool = False) -> str:
    """Convenience for vertical arrows."""
    return svg_arrow(x, y1, x, y2, accent_alias=accent_alias,
                     stroke_width=stroke_width, dashed=dashed)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def even_split_x(canvas_w: int, n: int, *,
                 padding: int = 30,
                 gap: int = 18) -> list[tuple[int, int]]:
    """Evenly distribute N boxes across the canvas with given padding+gap.

    Returns N (x_start, width) tuples.
    """
    usable = canvas_w - 2 * padding - (n - 1) * gap
    box_w = usable // n
    out = []
    cursor = padding
    for _ in range(n):
        out.append((cursor, box_w))
        cursor += box_w + gap
    return out


__all__ = [
    "CANVAS_W", "CANVAS_H_WIDE", "CANVAS_H_TALL",
    "STROKE_NORMAL", "STROKE_THICK", "ARROW_HEAD_SIZE", "CORNER_RADIUS",
    "esc",
    "svg_open", "svg_close",
    "svg_title_label", "svg_subtitle_label", "svg_text",
    "svg_box", "svg_box_filled", "svg_card",
    "svg_arrow", "svg_connector_horizontal", "svg_connector_vertical",
    "even_split_x",
]
