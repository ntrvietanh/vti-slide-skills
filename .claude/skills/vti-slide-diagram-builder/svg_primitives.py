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
from tokens_bridge import accent, font_body, token, tint

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
STROKE_THIN = 1.5
STROKE_NORMAL = 2
STROKE_THICK = 3
ARROW_HEAD_SIZE = 6
CORNER_RADIUS = 8

# v4.0/M2 — depth pass. Accent aliases that get a pre-defined vertical
# gradient (lighter top → accent bottom) so filled boxes read with depth
# instead of flat colour. Outlined (white) boxes get a barely-there sheen
# gradient + a soft drop shadow. Every colour is resolved via the token
# bridge (accent/tint) — no hex literals in source (verify-time lint).
_GRAD_ALIASES = ["navy", "deep", "blue", "medium", "sky", "light", "teal", "amber"]


def esc(text: str | None) -> str:
    """Escape XML-special characters in user text. Empty/None → ''."""
    if text is None:
        return ""
    return _html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# v4.0/M2 — shared <defs>: gradients, soft shadow, icon symbols
# ---------------------------------------------------------------------------
def _lin_grad(gid: str, top_hex: str, bottom_hex: str) -> str:
    return (
        f'    <linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">\n'
        f'      <stop offset="0" stop-color="{top_hex}"/>\n'
        f'      <stop offset="1" stop-color="{bottom_hex}"/>\n'
        f'    </linearGradient>\n'
    )


# A compact line-icon set (24×24, currentColor strokes). Latent in M2 —
# available via svg_icon() for the M3 archetype layer to wire into nodes;
# adding them to <defs> costs nothing when unused.
_ICON_PATHS: dict[str, str] = {
    "gear":     '<path d="M12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM12 3v2M12 19v2M5 12H3M21 12h-2M6 6l1.5 1.5M16.5 16.5L18 18M18 6l-1.5 1.5M7.5 16.5L6 18" />',
    "database": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v12c0 1.66 3.13 3 7 3s7-1.34 7-3V6M5 12c0 1.66 3.13 3 7 3s7-1.34 7-3"/>',
    "cloud":    '<path d="M7 18a4 4 0 01-.5-7.97A5.5 5.5 0 0117.5 11 3.5 3.5 0 0117 18H7z"/>',
    "check":    '<path d="M4 12.5l5 5L20 6.5"/>',
    "user":     '<circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0114 0"/>',
    "chart":    '<path d="M4 20V4M4 20h16M8 17v-5M12 17V8M16 17v-8"/>',
    "loop":     '<path d="M4 9a8 8 0 0114-3l2 2M20 15a8 8 0 01-14 3l-2-2M18 4v4h-4M6 20v-4h4"/>',
    "shield":   '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z"/>',
    "doc":      '<path d="M7 3h7l4 4v14H7zM14 3v4h4M9 12h6M9 16h6"/>',
}
_ICON_SYMBOLS = "".join(
    f'    <symbol id="vti-ic-{name}" viewBox="0 0 24 24" '
    f'fill="none" stroke="currentColor" stroke-width="1.8" '
    f'stroke-linecap="round" stroke-linejoin="round">{path}</symbol>\n'
    for name, path in _ICON_PATHS.items()
)


def _defs() -> str:
    """Shared gradient/filter/icon definitions injected once per <svg>.

    IDs are stable (matching the existing `diag-title`/`diag-desc` pattern):
    every diagram defines identical content, so url(#…) references resolve
    consistently even with multiple diagrams inlined in one deck document.
    """
    parts = ["  <defs>\n"]
    # White-card sheen: white → barely-there blue tint at the bottom.
    parts.append(_lin_grad("vtiFillWhite", accent("white"), tint("deep", 0.94)))
    # Accent gradients: a lifted (lighter) top → the accent at the bottom.
    for a in _GRAD_ALIASES:
        parts.append(_lin_grad(f"vtiGrad-{a}", tint(a, 0.28), accent(a)))
    # Soft drop shadow — tuned subtle to match the brand's "soft elevated
    # surfaces" identity (see tokens.css --vti-shadow-*).
    parts.append(
        '    <filter id="vtiSoftShadow" x="-25%" y="-25%" width="150%" height="160%">\n'
        f'      <feDropShadow dx="0" dy="2.5" stdDeviation="5" '
        f'flood-color="{accent("navy")}" flood-opacity="0.16"/>\n'
        '    </filter>\n'
    )
    parts.append(_ICON_SYMBOLS)
    parts.append("  </defs>\n")
    return "".join(parts)


def svg_icon(x: int, y: int, size: int, name: str, *,
             color_alias: str = "deep") -> str:
    """Render a line icon from the built-in set via <use>.

    No-op (empty string) for an unknown name so callers never crash.
    """
    if name not in _ICON_PATHS:
        return ""
    return (
        f'  <use href="#vti-ic-{name}" x="{x}" y="{y}" '
        f'width="{size}" height="{size}" color="{accent(color_alias)}"/>\n'
    )


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
        f'{_defs()}'
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
            stroke_width: float = STROKE_NORMAL,
            radius: int = CORNER_RADIUS,
            opacity: float = 1.0,
            shadow: bool = True,
            gradient: bool = True) -> str:
    """Outlined rounded rectangle.

    v4.0/M2 — depth pass: a white box gets a barely-there sheen gradient
    (``vtiFillWhite``) and a soft drop shadow; an accent fill gets its
    pre-defined accent gradient. Pass ``shadow=False`` / ``gradient=False``
    to opt out (e.g. decorative or semi-transparent boxes). Shadow is
    auto-suppressed for translucent boxes so it never doubles up.
    """
    op = f' opacity="{opacity}"' if opacity < 1.0 else ""
    if fill_alias == "white":
        fill = "url(#vtiFillWhite)" if gradient else "white"
    elif gradient and fill_alias in _GRAD_ALIASES:
        fill = f"url(#vtiGrad-{fill_alias})"
    else:
        fill = accent(fill_alias)
    filt = ' filter="url(#vtiSoftShadow)"' if (shadow and opacity >= 1.0) else ""
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" stroke="{accent(stroke_alias)}" '
        f'stroke-width="{stroke_width}"{op}{filt}/>\n'
    )


def svg_box_filled(x: int, y: int, w: int, h: int, *,
                   fill_alias: str,
                   radius: int = CORNER_RADIUS,
                   opacity: float = 1.0,
                   shadow: bool = True,
                   gradient: bool = True) -> str:
    """Solid fill rounded rectangle (no stroke).

    v4.0/M2 — uses the accent's vertical gradient + a soft drop shadow for
    depth. Shadow auto-suppressed when translucent.
    """
    op = f' opacity="{opacity}"' if opacity < 1.0 else ""
    if gradient and fill_alias in _GRAD_ALIASES:
        fill = f"url(#vtiGrad-{fill_alias})"
    else:
        fill = accent(fill_alias)
    filt = ' filter="url(#vtiSoftShadow)"' if (shadow and opacity >= 1.0) else ""
    return (
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}"{op}{filt}/>\n'
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
              accent_alias: str = "ink-soft",
              stroke_width: float = STROKE_NORMAL,
              dashed: bool = False) -> str:
    """Straight arrow with filled-triangle head at (x2, y2).

    The triangle points in the direction (x1, y1) → (x2, y2).
    v4.0/M2 — default connector colour darkened muted→ink-soft for legible
    contrast on the pale canvas (muted read washed out).
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
    "STROKE_THIN", "STROKE_NORMAL", "STROKE_THICK", "ARROW_HEAD_SIZE",
    "CORNER_RADIUS",
    "esc",
    "svg_open", "svg_close", "svg_icon",
    "svg_title_label", "svg_subtitle_label", "svg_text",
    "svg_box", "svg_box_filled", "svg_card",
    "svg_arrow", "svg_connector_horizontal", "svg_connector_vertical",
    "even_split_x",
]
