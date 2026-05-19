"""
vti-slide-page-builder — Grid + Components renderer
========================================================
Pure compositional renderer. No intents, no recipes. Caller passes a
slide-grid descriptor (rows × cells × component picks + props) and this
returns rendered HTML + aggregated CSS.

Architecture
------------
- Components live under ``components/<name>/`` with ``component.html``
  (placeholder template) + ``component.css`` (scoped styles).
- Each component has a Python render function decorated with
  ``@register_component`` that fills the placeholders.
- The grid renderer places component HTML into a 12-column CSS grid
  with N rows, each cell positioned via ``grid-column`` + ``grid-row``.
- Chrome (header / footer / breadcrumb / page-num / logo) is reused
  verbatim from v2 — preserved unchanged per the architecture decision.

Public API
----------
``compose_slide_grid(slide_input: dict) -> dict``
    Render one slide. Returns ``{slide_html, slide_css, metadata}``.

``catalog() -> dict``
    Return the registered component names (for orchestrator discovery).

``ValidationError``
    Raised on schema violation. ``.code``, ``.field``, ``.hint``.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SKILL_ROOT     = Path(__file__).resolve().parent
COMPONENTS_DIR = SKILL_ROOT / "components"
CHROME_DIR     = SKILL_ROOT / "chrome"
ASSETS_DIR     = SKILL_ROOT / "assets"
SPECIAL_PAGES_DIR = SKILL_ROOT / "special-pages"
TOKENS_PATH    = SKILL_ROOT / "tokens.css"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ValidationError(Exception):
    """Raised when input descriptor or component props are invalid."""

    def __init__(self, code: str, field: str, hint: str = ""):
        self.code, self.field, self.hint = code, field, hint
        msg = f"[{code}] {field}"
        if hint:
            msg += f": {hint}"
        super().__init__(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _esc(s: Any) -> str:
    """HTML-escape a value. Returns empty string for None.

    v3.5 (Gap D): emits a soft warning to ``_LAST_ESC_WARNINGS`` when the
    input contains a literal HTML entity sequence (``&lt;``, ``&gt;``,
    ``&amp;``, ``&quot;``, ``&#nn;``). The composer collects these and
    surfaces them in the slide-render metadata so callers can spot
    pre-escaped source strings.
    """
    if s is None:
        return ""
    text = str(s)
    # Gap D detector — schema strings should be plain Unicode; pre-escaping
    # produces literal `&LT;` after CSS uppercase. We DON'T mutate input
    # (back-compat). We only emit a warning.
    if _ENTITY_PATTERN.search(text):
        _LAST_ESC_WARNINGS.append(text[:60])
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


# v3.5 — module-level state for pre-escape warnings (Gap D). Cleared at
# the start of every compose_slide_grid call.
import re as _re_v35  # noqa: E402 (intentional, keeps v3.5 additions grouped)
_ENTITY_PATTERN = _re_v35.compile(r"&(lt|gt|amp|quot|apos|#\d+);")
_LAST_ESC_WARNINGS: list[str] = []


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _require(props: dict, key: str, ctx: str = "props") -> Any:
    """Raise ValidationError if `key` is missing or empty in props."""
    v = props.get(key)
    if v is None or v == "" or (isinstance(v, list) and not v):
        raise ValidationError("missing_required", f"{ctx}.{key}")
    return v


def _check_max_chars(value: str, limit: int, field: str) -> None:
    if len(str(value)) > limit:
        raise ValidationError(
            "chars_exceeded", field,
            f"max {limit} chars, got {len(str(value))}",
        )


def _normalize_image_src(value: Any, field: str) -> tuple[str, str]:
    """Coerce an `image` prop into ``(src, alt)``.

    Accepts a plain string (path / URL / data URI) OR a dict
    ``{"path": str, "alt"?: str, ...}`` — the latter is what upstream
    drafters sometimes emit when they carry source-asset metadata
    forward. Anything else is a hard error so the renderer can never
    silently `str(dict)` into the HTML `src` attribute again.
    """
    if isinstance(value, str):
        return value, ""
    if isinstance(value, dict):
        path = value.get("path") or value.get("src") or value.get("url")
        if not isinstance(path, str) or not path:
            raise ValidationError(
                "invalid_value", field,
                "dict form must carry a non-empty 'path' (str); "
                f"got keys {sorted(value)!r}",
            )
        alt = value.get("alt") or value.get("caption") or ""
        return path, str(alt) if alt else ""
    raise ValidationError(
        "invalid_value", field,
        f"expected str path or {{'path': str, 'alt'?: str}} dict, "
        f"got {type(value).__name__}",
    )


# ---------------------------------------------------------------------------
# Icon library — small starter set, expand as needed
# ---------------------------------------------------------------------------
ICON_SVGS: dict[str, str] = {
    "brain": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44A2.5 2.5 0 0 1 4.5 17a2.5 2.5 0 0 1-1.98-4.04A2.5 2.5 0 0 1 4.5 9c0-1.04.5-1.94 1.27-2.5A2.5 2.5 0 0 1 9.5 2Z"/>
<path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44A2.5 2.5 0 0 0 19.5 17a2.5 2.5 0 0 0 1.98-4.04A2.5 2.5 0 0 0 19.5 9c0-1.04-.5-1.94-1.27-2.5A2.5 2.5 0 0 0 14.5 2Z"/>
</svg>''',
    "cloud": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M6.5 19a4.5 4.5 0 1 1 .5-8.95A5.5 5.5 0 0 1 17.7 11.95H18a4 4 0 0 1 0 8H6.5z"/>
</svg>''',
    "code": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M7 8l-4 4 4 4"/>
<path d="M17 8l4 4-4 4"/>
<path d="M14 4l-4 16"/>
</svg>''',
    "chart-bar": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<rect x="3" y="12" width="4" height="8" rx="0.5"/>
<rect x="10" y="6" width="4" height="14" rx="0.5"/>
<rect x="17" y="9" width="4" height="11" rx="0.5"/>
</svg>''',
    "chevron-right": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M9 6l6 6-6 6"/>
</svg>''',
    "check": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M5 12l5 5L20 7"/>
</svg>''',
    "x": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M6 6l12 12"/>
<path d="M18 6L6 18"/>
</svg>''',
    "bulb": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M9 18h6"/>
<path d="M10 21h4"/>
<path d="M8.5 14a6 6 0 1 1 7 0c-.6.45-1 1.15-1 1.85V16a1 1 0 0 1-1 1h-3a1 1 0 0 1-1-1v-.15c0-.7-.4-1.4-1-1.85z"/>
</svg>''',
    "tools": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94L7.6 18.4a2.1 2.1 0 0 1-3-3l6.9-6.9A6 6 0 0 1 18.47 2.53z"/>
</svg>''',
    "rocket": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
<path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
<path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
</svg>''',
    "handshake": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M11 17l2 2a1 1 0 1 0 3-3"/>
<path d="M14 14l2.5 2.5a1 1 0 1 0 3-3l-3.88-3.88a3 3 0 0 0-4.24 0l-.88.88a2 2 0 0 1-2.83 0l-.7-.7a1 1 0 0 1 0-1.42L8.5 5.5"/>
<path d="M3.5 13.5l5 5"/>
<path d="M11.5 8.5l-1 1a2 2 0 0 1-2.83 0l-.86-.86a2 2 0 0 1 0-2.83l3.66-3.65a1 1 0 0 1 1.41 0l3.18 3.18"/>
</svg>''',
    "shield-check": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M12 3l8 4v5c0 4.5-3.4 8.4-8 9-4.6-.6-8-4.5-8-9V7z"/>
<path d="M9 12l2 2 4-4"/>
</svg>''',
    "users": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
<circle cx="9" cy="7" r="4"/>
<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
<path d="M16 3.13a4 4 0 0 1 0 7.75"/>
</svg>''',
    "star": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/>
</svg>''',
    "lock": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<rect x="3" y="11" width="18" height="11" rx="2"/>
<path d="M7 11V7a5 5 0 0 1 10 0v4"/>
</svg>''',
    "building-skyscraper": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M3 21h18"/>
<path d="M5 21V7l8-4v18"/>
<path d="M19 21V11l-6-4"/>
<path d="M9 9h.01M9 13h.01M9 17h.01"/>
</svg>''',
    "world": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="12" r="10"/>
<path d="M2 12h20"/>
<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>''',
    "eye": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/>
<circle cx="12" cy="12" r="3"/>
</svg>''',
    "message": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
</svg>''',
    "sparkles": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>
<path d="M12 8a4 4 0 0 0 4 4 4 4 0 0 0-4 4 4 4 0 0 0-4-4 4 4 0 0 0 4-4z"/>
</svg>''',
    "wifi": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M5 12.55a11 11 0 0 1 14 0"/>
<path d="M1.42 9a16 16 0 0 1 21.16 0"/>
<path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
<line x1="12" y1="20" x2="12.01" y2="20"/>
</svg>''',
    "cpu": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<rect x="4" y="4" width="16" height="16" rx="2"/>
<rect x="9" y="9" width="6" height="6"/>
<path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>
</svg>''',
    "bell": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/>
<path d="M13.73 21a2 2 0 0 1-3.46 0"/>
</svg>''',
    # ── Icons added 2026-05-19 to close common naming-gap silent-fails ──
    "clock": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="12" r="10"/>
<path d="M12 6v6l4 2"/>
</svg>''',
    "database": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<ellipse cx="12" cy="5" rx="9" ry="3"/>
<path d="M3 5v6c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
<path d="M3 11v6c0 1.66 4 3 9 3s9-1.34 9-3v-6"/>
</svg>''',
    "file-text": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
<path d="M14 2v6h6"/>
<path d="M8 13h8M8 17h8M8 9h2"/>
</svg>''',
    "inbox": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
<path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
</svg>''',
    "at-sign": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="12" r="4"/>
<path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-3.92 7.94"/>
</svg>''',
    "message-square": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
</svg>''',
    "refresh-cw": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<polyline points="23 4 23 10 17 10"/>
<polyline points="1 20 1 14 7 14"/>
<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
</svg>''',
    "network": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="4" r="2"/>
<circle cx="4" cy="20" r="2"/>
<circle cx="20" cy="20" r="2"/>
<path d="M12 6v6M12 12L4 18M12 12l8 6"/>
</svg>''',
    "compass": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="12" cy="12" r="10"/>
<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
</svg>''',
    "gauge": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M12 14l4-4"/>
<path d="M3.34 19a10 10 0 1 1 17.32 0"/>
</svg>''',
    "route": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<circle cx="6" cy="19" r="3"/>
<path d="M9 19h6a4 4 0 0 0 0-8H9a4 4 0 0 1 0-8h6"/>
<circle cx="18" cy="5" r="3"/>
</svg>''',
    "trending-up": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
<polyline points="17 6 23 6 23 12"/>
</svg>''',
    "trending-flat": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<polyline points="22 12 18 8 18 16 22 12"/>
<line x1="2" y1="12" x2="18" y2="12"/>
</svg>''',
    "puzzle": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M19.5 11.5h-1c-1.1 0-2-.9-2-2s.9-2 2-2h1V5a1 1 0 0 0-1-1h-3v1.5c0 1.1-.9 2-2 2s-2-.9-2-2V4h-3a1 1 0 0 0-1 1v3h1.5c1.1 0 2 .9 2 2s-.9 2-2 2H5v3a1 1 0 0 0 1 1h2.5c0-1.1.9-2 2-2s2 .9 2 2H15a1 1 0 0 0 1-1v-2.5c1.1 0 2-.9 2-2s-.9-2-2-2"/>
</svg>''',
    "server-off": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M2 2l20 20"/>
<path d="M5.7 5.7A2 2 0 0 0 4 7.7V10a2 2 0 0 0 2 2h2.3M18 12h-2.3M22 10V7.7a2 2 0 0 0-2-2H10.3"/>
<path d="M6 17h12a2 2 0 0 0 2-2V13.3M4 13.3V15a2 2 0 0 0 2 2"/>
</svg>''',
    "user-check": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
<circle cx="8.5" cy="7" r="4"/>
<polyline points="17 11 19 13 23 9"/>
</svg>''',
    "check-circle": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
<polyline points="22 4 12 14.01 9 11.01"/>
</svg>''',
    "split": '''<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
<path d="M16 3h5v5"/>
<path d="M8 3H3v5"/>
<path d="M12 22V12"/>
<path d="M21 3L12 12 3 3"/>
</svg>''',
    # ── Generic fallback (used by render_icon when an unknown name is passed) ──
    "_fallback": '''<svg viewBox="0 0 24 24" fill="currentColor" stroke="none" aria-hidden="true">
<circle cx="12" cy="12" r="3"/>
</svg>''',
}


# Track unknown icon names seen this process so we warn once per name.
_UNKNOWN_ICONS_SEEN: set[str] = set()


def render_icon(name: str) -> str:
    """Return inline SVG for an icon name.

    If the name is unknown, emit a one-time stderr warning and fall back
    to the generic ``_fallback`` glyph (a small filled dot). This avoids the
    silent-fail pattern where unknown names rendered as empty space inside
    a circle slot, leading decks to ship with inconsistent icon visibility.

    Note: callers wanting strict behaviour can check ``name in ICON_SVGS``
    before calling — render_icon never raises.
    """
    if name not in ICON_SVGS:
        if name and name not in _UNKNOWN_ICONS_SEEN:
            _UNKNOWN_ICONS_SEEN.add(name)
            import sys
            print(
                f"[composer_grid] WARN: unknown icon name {name!r} — using fallback. "
                f"Available: {sorted(n for n in ICON_SVGS if not n.startswith('_'))}",
                file=sys.stderr,
            )
        return ICON_SVGS.get("_fallback", "")
    return ICON_SVGS[name]


# ---------------------------------------------------------------------------
# Component registry
# ---------------------------------------------------------------------------
_COMPONENT_RENDERERS: dict[str, Callable[[dict], str]] = {}

# ---------------------------------------------------------------------------
# Component metadata registry — single source of truth for what each
# component does, when to use it, and how to size it. Consumed by the
# creator skill's pick step (Phase 5.2) via catalog(verbose=True).
#
# Each entry is a dict with:
#     role           — one-sentence explanation of what the component does
#     kind           — text | data | card | structural
#     good_for       — list of content shapes this handles WELL
#     bad_for        — list of content shapes that should NOT use this
#     best_col_spans — col_span values that look right (in 12-col grid)
#     natural_height — typical row-height value to use ('auto' / '1fr' / 'Npx')
#     schema_brief   — short summary of required props
#     picks_content_kinds — list of content-block kinds (from creator's
#                       content_drafter.CONTENT_BLOCK_SCHEMAS) this component
#                       is the natural pick for. Used by creator's
#                       picks_for_kind() helper.
# ---------------------------------------------------------------------------
_COMPONENT_META: dict[str, dict] = {}

# Tracks which components have been rendered during the current
# compose_slide_grid() call — INCLUDING transitive ones (e.g. stat-mini
# rendered inside kpi-row). Cleared at the start of every compose_slide_grid.
_USED_COMPONENTS_THIS_RENDER: set[str] = set()


def register_component(name: str, *, meta: dict | None = None):
    """Decorator: register a component renderer fn(props) -> html_str.

    Args:
        name:  the component name (e.g. "stat-hero").
        meta:  optional metadata dict (see ``_COMPONENT_META`` docstring).
               If omitted, callers querying ``catalog(verbose=True)`` get
               a stub metadata entry with empty role + kind=unknown.
    """
    def _decorator(fn: Callable[[dict], str]):
        _COMPONENT_RENDERERS[name] = fn
        if meta is not None:
            _COMPONENT_META[name] = meta
        return fn
    return _decorator


def render_component(name: str, props: dict) -> str:
    """Render one component to HTML. Raises if name unregistered.

    Side effect: appends ``name`` to ``_USED_COMPONENTS_THIS_RENDER`` so
    transitive component usage (e.g. stat-mini inside kpi-row) is captured
    and the right CSS gets loaded by ``compose_slide_grid``.
    """
    fn = _COMPONENT_RENDERERS.get(name)
    if fn is None:
        raise ValidationError(
            "unknown_component", name,
            f"registered: {sorted(_COMPONENT_RENDERERS.keys())}",
        )
    _USED_COMPONENTS_THIS_RENDER.add(name)
    return fn(props)


def _component_css(name: str) -> str:
    """Load the CSS for a component."""
    return _read_file(COMPONENTS_DIR / name / "component.css")


def _component_template(name: str) -> str:
    """Load the HTML template for a component."""
    return _read_file(COMPONENTS_DIR / name / "component.html")


def _fill(template: str, mapping: dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders. Mapping values are NOT escaped here —
    callers must escape user input before passing in."""
    out = template
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", v if v is not None else "")
    return out


# ---------------------------------------------------------------------------
# Component renderers
# ---------------------------------------------------------------------------
# Note: there is no `eyebrow-title` component. Section name + slide title
# are first-class fields on `slide_meta` (`section_name` + `slide_title`)
# and rendered into the chrome breadcrumb at top-left as
# "SECTION | TITLE". Adding an in-slide title in row 1 would duplicate
# that — content rows are reserved for actual content blocks.

@register_component("narrative-paragraph", meta={
    "role": "1-4 paragraph body text with optional **emphasis** wrapping.",
    "kind": "text",
    "good_for": ["intro / framing prose under a heading", "body of explanatory slide", "callout text beside a stat or visual"],
    "bad_for":  ["lists (use bullet-list-checked instead)", "long-form copy (>4 paragraphs splits across slides)"],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "auto",
    "schema_brief":   "paragraphs: list[str≤400] (1-4 items), align?: 'left'|'center', max_width?: str (e.g. '780px')",
    "font_levels_used":  ["body"],
    "font_weights_used": [400],
    "capacity_chars_per_col": 80,
    "picks_content_kinds": ["narrative"],
})
def _r_narrative_paragraph(props: dict) -> str:
    paragraphs = _require(props, "paragraphs", "narrative-paragraph.props")
    if not isinstance(paragraphs, list):
        raise ValidationError("invalid_type", "narrative-paragraph.props.paragraphs",
                              "must be array of strings")
    if len(paragraphs) > 4:
        raise ValidationError("too_many", "narrative-paragraph.props.paragraphs",
                              f"max 4 paragraphs, got {len(paragraphs)}")
    align = props.get("align", "left")
    if align not in ("left", "center"):
        raise ValidationError("invalid_value", "narrative-paragraph.props.align",
                              "must be 'left' or 'center'")
    max_width = props.get("max_width", "")
    inline_style = ""
    if max_width:
        inline_style += f"max-width: {max_width};"

    # Each paragraph supports inline emphasis: text inside **double-asterisks**
    # becomes <strong>. Useful for highlighting key phrases inline.
    EMPH_RE = re.compile(r"\*\*(.+?)\*\*")
    para_html_parts: list[str] = []
    for p in paragraphs:
        _check_max_chars(p, 400, "narrative-paragraph.props.paragraphs[]")
        # Escape first, then re-allow our limited markdown for **strong**.
        escaped = _esc(p)
        styled  = EMPH_RE.sub(r"<strong>\1</strong>", escaped)
        para_html_parts.append(f'<p class="vti-narrative__p">{styled}</p>')

    return _fill(_component_template("narrative-paragraph"), {
        "ALIGN":           align,
        "INLINE_STYLE":    inline_style,
        "PARAGRAPHS_HTML": "\n".join(para_html_parts),
    })


@register_component("stat-hero", meta={
    "role": "Dominant single stat (84-128px font) — anchors a slide visually around 1 number.",
    "kind": "data",
    "good_for": ["headline metric / scale claim", "dominant number paired with narrative", "single-stat focal point"],
    "bad_for":  ["multiple stats (use kpi-row)", "supporting context number (use stat-mini)"],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "1fr (centered) or auto",
    "schema_brief":   "value: str≤8, label: str≤30, decoration?: 'rings'|'none'",
    "font_levels_used":  ["hero", "caption"],
    "font_weights_used": [400, 600],
    "capacity_chars_fixed":   40,
    "picks_content_kinds": ["hero_stat"],
})
def _r_stat_hero(props: dict) -> str:
    value = _esc(_require(props, "value", "stat-hero.props"))
    label = _esc(_require(props, "label", "stat-hero.props"))
    _check_max_chars(props["value"], 8, "stat-hero.props.value")
    _check_max_chars(props["label"], 30, "stat-hero.props.label")
    decoration = props.get("decoration", "rings")
    if decoration not in ("rings", "none"):
        raise ValidationError("invalid_value", "stat-hero.props.decoration",
                              "must be 'rings' or 'none'")

    deco_html = ""
    if decoration == "rings":
        deco_html = (
            '<span class="vti-stat-hero__deco vti-stat-hero__deco--outer"></span>'
            '<span class="vti-stat-hero__deco vti-stat-hero__deco--inner"></span>'
        )
    return _fill(_component_template("stat-hero"), {
        "DECORATION": decoration,
        "DECO_HTML":  deco_html,
        "VALUE":      value,
        "LABEL":      label,
    })


_PRACTICE_TONE_MAP = {
    "deep":   "var(--vti-blue-deep)",
    "medium": "var(--vti-blue-medium)",
    "sky":    "var(--vti-sky)",
    "navy":   "var(--vti-navy)",
}


@register_component("practice-card", meta={
    "role": "Hero card with colored top half (icon + title) and white body — for 3 peer practice areas / capabilities / steps.",
    "kind": "card",
    "good_for": ["3 peer practice areas / capabilities", "numbered step or principle (1-4)", "dominant feature card"],
    "bad_for":  ["5+ peer items (cards too narrow)", "short labels alone (use value-medallion)"],
    "best_col_spans": [3, 4, 6],
    "natural_height": "auto",
    "schema_brief":   "title: str≤28, body: str≤220, icon: str, number?: str, color_tone?: 'deep'|'medium'|'sky'|'navy'|hex",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 70,
    "picks_content_kinds": ["features_3"],
})
def _r_practice_card(props: dict) -> str:
    title = _esc(_require(props, "title", "practice-card.props"))
    body  = _esc(_require(props, "body",  "practice-card.props"))
    icon  = props.get("icon", "")
    number = props.get("number", "")
    color_tone = props.get("color_tone", "deep")
    _check_max_chars(props["title"], 28, "practice-card.props.title")
    _check_max_chars(props["body"], 220, "practice-card.props.body")

    # Resolve color: token name OR raw hex.
    if color_tone in _PRACTICE_TONE_MAP:
        bg_color = _PRACTICE_TONE_MAP[color_tone]
    elif re.match(r"^#[0-9A-Fa-f]{6}$", str(color_tone)):
        bg_color = color_tone
    else:
        raise ValidationError(
            "invalid_value", "practice-card.props.color_tone",
            f"must be one of {list(_PRACTICE_TONE_MAP.keys())} or a hex color",
        )

    icon_svg = render_icon(icon) if icon else ""
    icon_html = (
        f'<span class="vti-practice-card__icon">{icon_svg}</span>'
        if icon_svg else ""
    )
    has_icon_class = " vti-practice-card--has-icon" if icon_svg else ""
    number_html = (
        f'<span class="vti-practice-card__num">{_esc(number)}</span>'
        if number else ""
    )

    return _fill(_component_template("practice-card"), {
        "BG_COLOR":       bg_color,
        "NUMBER_HTML":    number_html,
        "ICON_HTML":      icon_html,
        "HAS_ICON_CLASS": has_icon_class,
        "TITLE":          title,
        "BODY":           body,
    })


@register_component("practice-card-leveled", meta={
    "role": "Variant of practice-card: header (icon + title) over a body of "
            "badged 'level' rows (L1 / L2 / L3 …) instead of a single "
            "paragraph. Use when each principle / capability has a staged "
            "progression worth showing inline.",
    "kind": "card",
    "good_for": [
        "3-4 peer principles, each with 2-4 levels of maturity / progression",
        "design-rationale slides where the headline IS the level upgrade",
    ],
    "bad_for": [
        "single-line peer items (use value-medallion)",
        "items without an inherent ordered progression (use practice-card)",
    ],
    "best_col_spans": [3, 4],
    "natural_height": "auto",
    "schema_brief":   "title: str≤28, icon: str, core?: str≤90, "
                      "levels: list[{badge: str≤4, body: str≤140}] (2-4 items), "
                      "color_tone?: 'deep'|'medium'|'sky'|'navy'|hex",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 240,
    "picks_content_kinds": ["leveled_principles"],
})
def _r_practice_card_leveled(props: dict) -> str:
    title  = _esc(_require(props, "title", "practice-card-leveled.props"))
    levels = _require(props, "levels", "practice-card-leveled.props")
    icon   = props.get("icon", "")
    core   = props.get("core", "")
    color_tone = props.get("color_tone", "deep")

    _check_max_chars(props["title"], 28, "practice-card-leveled.props.title")
    if core:
        _check_max_chars(core, 90, "practice-card-leveled.props.core")
    if not isinstance(levels, list) or not (2 <= len(levels) <= 4):
        raise ValidationError(
            "invalid_count", "practice-card-leveled.props.levels",
            f"must have 2-4 items, got {len(levels) if isinstance(levels, list) else type(levels).__name__}",
        )

    if color_tone in _PRACTICE_TONE_MAP:
        bg_color = _PRACTICE_TONE_MAP[color_tone]
    elif re.match(r"^#[0-9A-Fa-f]{6}$", str(color_tone)):
        bg_color = color_tone
    else:
        raise ValidationError(
            "invalid_value", "practice-card-leveled.props.color_tone",
            f"must be one of {list(_PRACTICE_TONE_MAP.keys())} or a hex color",
        )

    icon_svg  = render_icon(icon) if icon else ""
    icon_html = (
        f'<span class="vti-practice-card__icon">{icon_svg}</span>'
        if icon_svg else ""
    )
    has_icon_class = " vti-practice-card--has-icon" if icon_svg else ""
    core_html = (
        f'<p class="vti-practice-card__core">{_esc(core)}</p>'
        if core else ""
    )

    level_rows: list[str] = []
    for i, lvl in enumerate(levels):
        if not isinstance(lvl, dict):
            raise ValidationError(
                "invalid_value", f"practice-card-leveled.props.levels[{i}]",
                "each level must be a dict with 'badge' and 'body'",
            )
        badge = _require(lvl, "badge", f"practice-card-leveled.props.levels[{i}]")
        body  = _require(lvl, "body",  f"practice-card-leveled.props.levels[{i}]")
        _check_max_chars(badge, 4,  f"practice-card-leveled.props.levels[{i}].badge")
        _check_max_chars(body, 140, f"practice-card-leveled.props.levels[{i}].body")
        level_rows.append(
            '<div class="vti-practice-card__level">'
            f'<span class="vti-practice-card__level-badge">{_esc(badge)}</span>'
            f'<span class="vti-practice-card__level-body">{_inline_strong(_esc(body))}</span>'
            '</div>'
        )

    # Pull in the base practice-card CSS too — this variant reuses
    # .vti-practice-card / .vti-practice-card__top / .vti-practice-card__title
    # from the base component.
    _USED_COMPONENTS_THIS_RENDER.add("practice-card")

    return _fill(_component_template("practice-card-leveled"), {
        "BG_COLOR":       bg_color,
        "ICON_HTML":      icon_html,
        "HAS_ICON_CLASS": has_icon_class,
        "TITLE":          title,
        "CORE_HTML":      core_html,
        "LEVELS_HTML":    "\n      ".join(level_rows),
    })


# ---------------------------------------------------------------------------
# Component renderers — Sprint A (6 more)
# ---------------------------------------------------------------------------

@register_component("stat-mini", meta={
    "role": "Compact stat card (icon disc + value + label) for tight slots — typically used as a child of kpi-row.",
    "kind": "data",
    "good_for": ["supporting metric (paired with hero stat or narrative)", "single cell in a kpi-row"],
    "bad_for":  ["primary headline number (use stat-hero)", "stand-alone hero (too small)"],
    "best_col_spans": [3, 4],
    "natural_height": "auto",
    "schema_brief":   "icon: str, value: str≤8, label: str≤30, tone?: 'default'|'white'",
    "font_levels_used":  ["title", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   40,
    "picks_content_kinds": [],   # used inside kpi-row — not picked directly
})
def _r_stat_mini(props: dict) -> str:
    value = _esc(_require(props, "value", "stat-mini.props"))
    label = _esc(_require(props, "label", "stat-mini.props"))
    icon  = props.get("icon", "")
    tone  = props.get("tone", "default")
    _check_max_chars(props["value"], 8, "stat-mini.props.value")
    _check_max_chars(props["label"], 30, "stat-mini.props.label")
    if tone not in ("default", "white"):
        raise ValidationError("invalid_value", "stat-mini.props.tone",
                              "must be 'default' or 'white'")
    return _fill(_component_template("stat-mini"), {
        "TONE":     tone,
        "ICON_SVG": render_icon(icon) if icon else "",
        "VALUE":    value,
        "LABEL":    label,
    })


@register_component("kpi-row", meta={
    "role": "Horizontal strip of 2-5 stat-mini cards.",
    "kind": "data",
    "good_for": ["supporting metrics row at bottom of slide", "quick fact strip below a hero"],
    "bad_for":  ["1 single stat (use stat-hero)", ">5 items (split across 2 rows or use a different shape)"],
    "best_col_spans": [12],
    "natural_height": "auto",
    "schema_brief":   "items: list[{icon, value, label}] (2-5 items)",
    "font_levels_used":  ["title", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   200,
    "picks_content_kinds": ["supporting_stats"],
})
def _r_kpi_row(props: dict) -> str:
    items = _require(props, "items", "kpi-row.props")
    if not isinstance(items, list):
        raise ValidationError("invalid_type", "kpi-row.props.items",
                              "must be array of objects")
    if not (2 <= len(items) <= 5):
        raise ValidationError("invalid_count", "kpi-row.props.items",
                              f"must have 2-5 items, got {len(items)}")
    items_html_parts: list[str] = [
        render_component("stat-mini", item) for item in items
    ]
    return _fill(_component_template("kpi-row"), {
        "COL_COUNT":   str(len(items)),
        "ITEMS_HTML":  "\n".join(items_html_parts),
    })


@register_component("bullet-list-checked", meta={
    "role": "Vertical list with check-icon bullets.",
    "kind": "text",
    "good_for": ["feature list / capability list", "comparison panel content", "benefit highlights"],
    "bad_for":  ["numbered sequence (use practice-card with number instead)", "single short statement (use narrative-paragraph)"],
    "best_col_spans": [4, 5, 6, 7],
    "natural_height": "auto",
    "schema_brief":   "items: list[str≤100] (2-8 items), density?: 'compact'|'default'|'loose', marker?: 'check'|'x' (default 'check' — use 'x' for negative/problem side of a comparison)",
    "font_levels_used":  ["body"],
    "font_weights_used": [400],
    "capacity_chars_per_col": 40,
    "picks_content_kinds": ["list"],
})
def _r_bullet_list_checked(props: dict) -> str:
    items = _require(props, "items", "bullet-list-checked.props")
    if not isinstance(items, list):
        raise ValidationError("invalid_type", "bullet-list-checked.props.items",
                              "must be array of strings")
    if not (2 <= len(items) <= 8):
        raise ValidationError("invalid_count", "bullet-list-checked.props.items",
                              f"must have 2-8 items, got {len(items)}")
    density = props.get("density", "default")
    if density not in ("compact", "default", "loose"):
        raise ValidationError("invalid_value",
                              "bullet-list-checked.props.density",
                              "must be 'compact', 'default', or 'loose'")
    marker = props.get("marker", "check")
    if marker not in ("check", "x"):
        raise ValidationError("invalid_value",
                              "bullet-list-checked.props.marker",
                              "must be 'check' or 'x'")
    marker_svg = render_icon(marker)
    item_html_parts: list[str] = []
    for item in items:
        _check_max_chars(item, 100, "bullet-list-checked.props.items[]")
        item_html_parts.append(
            f'<li class="vti-bullet-list-checked__item">'
            f'<span class="vti-bullet-list-checked__icon">{marker_svg}</span>'
            f'<span class="vti-bullet-list-checked__text">{_esc(item)}</span>'
            f'</li>'
        )
    return _fill(_component_template("bullet-list-checked"), {
        "DENSITY":    density,
        "MARKER":     marker,
        "ITEMS_HTML": "\n".join(item_html_parts),
    })


@register_component("value-medallion", meta={
    "role": "Vertical icon disc + title + tagline — for short labels (4-6 peers).",
    "kind": "card",
    "good_for": ["4-6 values / pillars / principles", "icon-led short labels in a row"],
    "bad_for":  ["1-2 items (looks empty)", "items with body paragraphs (use practice-card)"],
    "best_col_spans": [2, 3],
    "natural_height": "auto",
    "schema_brief":   "icon: str, title: str≤22, tagline?: str≤60, number?: str, color_tone?: tone|hex",
    "font_levels_used":  ["title", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 25,
    "picks_content_kinds": ["values"],
})
def _r_value_medallion(props: dict) -> str:
    title   = _esc(_require(props, "title", "value-medallion.props"))
    icon    = _require(props, "icon", "value-medallion.props")
    number  = props.get("number", "")
    tagline = props.get("tagline", "")
    color_tone = props.get("color_tone", "deep")
    _check_max_chars(props["title"], 22, "value-medallion.props.title")
    if tagline:
        _check_max_chars(tagline, 60, "value-medallion.props.tagline")
    if number:
        _check_max_chars(number, 4, "value-medallion.props.number")

    if color_tone in _PRACTICE_TONE_MAP:
        bg_color = _PRACTICE_TONE_MAP[color_tone]
    elif re.match(r"^#[0-9A-Fa-f]{6}$", str(color_tone)):
        bg_color = color_tone
    else:
        raise ValidationError(
            "invalid_value", "value-medallion.props.color_tone",
            f"must be one of {list(_PRACTICE_TONE_MAP.keys())} or a hex color",
        )

    icon_svg = render_icon(icon) if icon else ""
    number_html = (
        f'<span class="vti-value-medallion__num">{_esc(number)}</span>'
        if number else ""
    )
    tagline_html = (
        f'<span class="vti-value-medallion__tagline">{_esc(tagline)}</span>'
        if tagline else ""
    )
    return _fill(_component_template("value-medallion"), {
        "BG_COLOR":     bg_color,
        "ICON_SVG":     icon_svg,
        "NUMBER_HTML":  number_html,
        "TITLE":        title,
        "TAGLINE_HTML": tagline_html,
    })


@register_component("catalog-column", meta={
    "role": "Colored header band + chevron rows + count badge — for service catalogs.",
    "kind": "card",
    "good_for": ["categorized service / feature list (2-3 categories)", "items grouped by track/phase/tier with optional tag pills"],
    "bad_for":  ["single uncategorized list (use bullet-list-checked)", "narrative content (no body in this component)"],
    "best_col_spans": [4, 6],
    "natural_height": "auto",
    "schema_brief":   "label: str≤24, category_icon: str, items: list[str|{text, tag?}] (2-8), count_text?: str, color_tone?: tone|hex",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 70,
    "picks_content_kinds": ["catalog"],
})
def _r_catalog_column(props: dict) -> str:
    label    = _esc(_require(props, "label", "catalog-column.props"))
    label_icon = _require(props, "category_icon", "catalog-column.props")
    items    = _require(props, "items", "catalog-column.props")
    count_text = props.get("count_text", "")
    color_tone = props.get("color_tone", "deep")
    _check_max_chars(props["label"], 24, "catalog-column.props.label")
    if not isinstance(items, list):
        raise ValidationError("invalid_type", "catalog-column.props.items",
                              "must be array")
    if not (2 <= len(items) <= 8):
        raise ValidationError("invalid_count", "catalog-column.props.items",
                              f"must have 2-8 items, got {len(items)}")

    if color_tone in _PRACTICE_TONE_MAP:
        bg_color = _PRACTICE_TONE_MAP[color_tone]
    elif re.match(r"^#[0-9A-Fa-f]{6}$", str(color_tone)):
        bg_color = color_tone
    else:
        raise ValidationError(
            "invalid_value", "catalog-column.props.color_tone",
            f"must be one of {list(_PRACTICE_TONE_MAP.keys())} or a hex color",
        )

    chev_svg = render_icon("chevron-right")
    item_html_parts: list[str] = []
    for it in items:
        if isinstance(it, str):
            text, tag = it, ""
        elif isinstance(it, dict):
            text = it.get("text", "")
            tag = it.get("tag", "")
        else:
            raise ValidationError("invalid_type",
                                  "catalog-column.props.items[]",
                                  "each item must be string or {text, tag?}")
        if not text:
            raise ValidationError("missing_required",
                                  "catalog-column.props.items[].text")
        _check_max_chars(text, 80, "catalog-column.props.items[].text")
        if tag:
            _check_max_chars(tag, 16, "catalog-column.props.items[].tag")
        tag_html = (
            f'<span class="vti-catalog-column__item-tag">{_esc(tag)}</span>'
            if tag else ""
        )
        item_html_parts.append(
            f'    <div class="vti-catalog-column__item">'
            f'<span class="vti-catalog-column__item-chev">{chev_svg}</span>'
            f'<span class="vti-catalog-column__item-text">{_esc(text)}</span>'
            f'{tag_html}</div>'
        )
    count_html = (
        f'<span class="vti-catalog-column__count">{_esc(count_text)}</span>'
        if count_text else ""
    )

    return _fill(_component_template("catalog-column"), {
        "BG_COLOR":         bg_color,
        "LABEL_ICON_SVG":   render_icon(label_icon),
        "LABEL":            label,
        "COUNT_BADGE_HTML": count_html,
        "ITEMS_HTML":       "\n".join(item_html_parts),
    })


@register_component("vs-divider", meta={
    "role": "VS badge with optional connecting line — sits between 2 panels.",
    "kind": "structural",
    "good_for": ["center divider in 2-panel comparison layouts"],
    "bad_for":  ["general spacer (use empty cell or 1fr row)", "more than 2 panels (use a different shape)"],
    "best_col_spans": [1, 2],
    "natural_height": "auto / 1fr",
    "schema_brief":   "label?: str≤6 (default 'VS'), has_line?: bool, line_style?: 'dashed'|'solid', orientation?: 'horizontal'|'vertical' (default 'horizontal')",
    "font_levels_used":  ["caption"],
    "font_weights_used": [500],
    "capacity_chars_fixed":   10,
    "picks_content_kinds": ["comparison_divider"],
})
def _r_vs_divider(props: dict) -> str:
    label    = _esc(props.get("label", "VS"))
    has_line = props.get("has_line", True)
    line_style = props.get("line_style", "dashed")
    orientation = props.get("orientation", "horizontal")
    _check_max_chars(props.get("label", "VS"), 6, "vs-divider.props.label")
    if line_style not in ("dashed", "solid"):
        raise ValidationError("invalid_value", "vs-divider.props.line_style",
                              "must be 'dashed' or 'solid'")
    if orientation not in ("horizontal", "vertical"):
        raise ValidationError("invalid_value", "vs-divider.props.orientation",
                              "must be 'horizontal' or 'vertical'")
    line_html = '<div class="vti-vs-divider__line"></div>' if has_line else ""
    return _fill(_component_template("vs-divider"), {
        "LINE_STYLE":  line_style,
        "LINE_HTML":   line_html,
        "LABEL":       label,
        "ORIENTATION": orientation,
    })


# ---------- (decoration-band component removed in v3.13.1) ---------------
# Auto-decoration logic was relocated to the separate `vti-slide-decorator`
# skill, which performs pixel-level whitespace analysis on the rendered
# deck HTML and injects an SVG overlay layer (z-index lower) without
# touching content. The composer itself no longer emits any decoration —
# it produces clean content slides only.


# ---------------------------------------------------------------------------
# Component renderers — Sprint B (4 components: image-tile, logo-grid,
# quote-block, process-flow). Round out the vocabulary with media (image,
# logo grids), social proof (testimonials), and methodology (steps).
# ---------------------------------------------------------------------------

_VALID_FRAME = {"rounded", "soft", "square"}
_VALID_CAPTION_POS = {"overlay", "below", "none"}
_VALID_BG = {"default", "none"}
_VALID_ASPECT_RE = re.compile(r"^\s*\d+\s*:\s*\d+\s*$")


@register_component("image-tile", meta={
    "role": "Single image inside a sized frame, with optional caption — for "
            "office photos, screenshots, illustrations, products.",
    "kind": "media",
    "good_for": [
        "single hero photo paired with text",
        "office building / team photo",
        "product or screenshot reference",
        "diagram or illustration",
    ],
    "bad_for": [
        "multiple peer logos (use logo-grid)",
        "icon only (use practice-card or stat-mini)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8],
    "natural_height": "1fr",
    "schema_brief": "image: str (path or URL), caption?: str≤120, "
                    "aspect_ratio?: 'W:H' (default '16:9'), "
                    "frame?: 'rounded'|'soft'|'square', "
                    "caption_position?: 'overlay'|'below'|'none', "
                    "bg?: 'default'|'none' (default 'default'), "
                    "captions?: list[str≤80] — per-step strip rendered "
                    "beneath the image (paired with diagram_spec.captions "
                    "from vti-slide-diagram-builder v0.4.0+)",
    "font_levels_used":  ["caption"],
    "font_weights_used": [400],
    "capacity_chars_fixed":   60,
    "picks_content_kinds": ["image", "photo"],
})
def _r_image_tile(props: dict) -> str:
    image_raw = _require(props, "image", "image-tile.props")
    image, image_alt = _normalize_image_src(image_raw, "image-tile.props.image")
    caption  = props.get("caption", "")
    aspect   = props.get("aspect_ratio", "16:9")
    frame    = props.get("frame", "rounded")
    cap_pos  = props.get("caption_position", "below" if caption else "none")
    bg       = props.get("bg", "default")
    captions_strip = props.get("captions") or []

    if not _VALID_ASPECT_RE.match(aspect):
        raise ValidationError(
            "invalid_value", "image-tile.props.aspect_ratio",
            f"expected 'W:H' format (e.g. '16:9'), got {aspect!r}",
        )
    if frame not in _VALID_FRAME:
        raise ValidationError(
            "invalid_value", "image-tile.props.frame",
            f"must be one of {sorted(_VALID_FRAME)}",
        )
    if cap_pos not in _VALID_CAPTION_POS:
        raise ValidationError(
            "invalid_value", "image-tile.props.caption_position",
            f"must be one of {sorted(_VALID_CAPTION_POS)}",
        )
    if bg not in _VALID_BG:
        raise ValidationError(
            "invalid_value", "image-tile.props.bg",
            f"must be one of {sorted(_VALID_BG)}",
        )
    if caption:
        _check_max_chars(caption, 120, "image-tile.props.caption")

    # Build caption HTML + CSS modifier classes
    frame_class = frame
    caption_html = ""
    if caption and cap_pos == "overlay":
        caption_html = (
            f'<figcaption class="vti-image-tile__caption '
            f'vti-image-tile__caption--overlay">{_esc(caption)}</figcaption>'
        )
    elif caption and cap_pos == "below":
        # "below" mode changes the figure layout (height auto, no frame bg)
        frame_class = f"{frame} vti-image-tile--has-below-caption"
        caption_html = (
            f'<figcaption class="vti-image-tile__caption '
            f'vti-image-tile__caption--below">{_esc(caption)}</figcaption>'
        )
    if bg == "none":
        frame_class = f"{frame_class} vti-image-tile--no-bg"

    # Captions strip (v0.4.0) — per-step text row beneath the image,
    # one cell per diagram step. Sourced from diagram_spec.captions
    # which the vti-slide-diagram-builder skill emits alongside the
    # Mermaid SVG. Presence flips the figure into auto-height mode so
    # the strip fits below without forcing the SVG into a fixed-aspect
    # crop. ``captions`` and ``caption`` may coexist (e.g. a slide that
    # wants both a hero caption and a per-step strip).
    captions_strip_html = ""
    if captions_strip:
        if not isinstance(captions_strip, list):
            raise ValidationError(
                "invalid_value", "image-tile.props.captions",
                f"must be a list[str], got {type(captions_strip).__name__}",
            )
        if len(captions_strip) > 7:
            raise ValidationError(
                "invalid_value", "image-tile.props.captions",
                f"max 7 entries (matches diagram primitive max steps), "
                f"got {len(captions_strip)}",
            )
        cells: list[str] = []
        for i, c in enumerate(captions_strip):
            if not isinstance(c, str):
                raise ValidationError(
                    "invalid_value", f"image-tile.props.captions[{i}]",
                    f"must be a str, got {type(c).__name__}",
                )
            _check_max_chars(c, 80, f"image-tile.props.captions[{i}]")
            cells.append(
                f'<span class="vti-image-tile__captions-strip-cell">'
                f'{_esc(c)}</span>'
            )
        captions_strip_html = (
            '<div class="vti-image-tile__captions-strip">'
            + "".join(cells)
            + "</div>"
        )
        # Auto-height the figure so the strip doesn't overflow.
        if "vti-image-tile--has-below-caption" not in frame_class:
            frame_class = f"{frame_class} vti-image-tile--has-below-caption"

    return _fill(_component_template("image-tile"), {
        "FRAME_CLASS":         frame_class,
        "ASPECT_RATIO_CSS":    aspect.replace(":", " / "),
        "IMAGE_SRC":           _esc(image),
        "ALT_TEXT":            _esc(caption or image_alt or "VTI image"),
        "CAPTION_HTML":        caption_html,
        "CAPTIONS_STRIP_HTML": captions_strip_html,
    })


_VALID_LOGO_TONE     = {"color", "muted", "monochrome"}
_VALID_LOGO_DENSITY  = {"loose", "compact"}


@register_component("logo-grid", meta={
    "role": "Even N-column grid of partner / customer / award logos. "
            "Three tone modes (color, muted, monochrome) handle visual "
            "compatibility when many brands clash.",
    "kind": "media",
    "good_for": [
        "trusted-by row (8-12 customer logos)",
        "strategic partners callout (4-6 logos)",
        "awards & certifications row",
    ],
    "bad_for": [
        "single hero logo (just use an image-tile)",
        "logos that need bullet copy each (use practice-card)",
    ],
    "best_col_spans": [12],
    "natural_height": "auto",
    "schema_brief": "logos: list[{image?: str, name?: str}] (>=2), "
                    "cols?: int 3-6 (default 4), "
                    "tone?: 'color'|'muted'|'monochrome' (default 'muted'), "
                    "density?: 'loose'|'compact'",
    "font_levels_used":  ["caption"],
    "font_weights_used": [400],
    "capacity_chars_fixed":   100,
    "picks_content_kinds": ["logos", "partners", "trust_signals"],
})
def _r_logo_grid(props: dict) -> str:
    logos = _require(props, "logos", "logo-grid.props")
    if not isinstance(logos, list) or len(logos) < 2:
        raise ValidationError(
            "invalid_value", "logo-grid.props.logos",
            f"expected a list of >=2 logo entries, got {logos!r}",
        )

    cols    = int(props.get("cols", 4))
    tone    = props.get("tone", "muted")
    density = props.get("density", "loose")

    if cols < 3 or cols > 6:
        raise ValidationError(
            "invalid_value", "logo-grid.props.cols",
            f"must be between 3 and 6, got {cols}",
        )
    if tone not in _VALID_LOGO_TONE:
        raise ValidationError(
            "invalid_value", "logo-grid.props.tone",
            f"must be one of {sorted(_VALID_LOGO_TONE)}",
        )
    if density not in _VALID_LOGO_DENSITY:
        raise ValidationError(
            "invalid_value", "logo-grid.props.density",
            f"must be one of {sorted(_VALID_LOGO_DENSITY)}",
        )

    # Build cells. Each cell either an <img> (if image given) or a
    # text-name fallback so the grid stays aligned even with missing files.
    cells = []
    for i, logo in enumerate(logos):
        if not isinstance(logo, dict):
            raise ValidationError(
                "invalid_value", f"logo-grid.props.logos[{i}]",
                "each logo entry must be a dict {image?, name?}",
            )
        image_raw = logo.get("image", "")
        name  = logo.get("name", "")
        if image_raw:
            image, image_alt = _normalize_image_src(
                image_raw, f"logo-grid.props.logos[{i}].image",
            )
            inner = (f'<img class="vti-logo-grid__img" src="{_esc(image)}" '
                     f'alt="{_esc(name or image_alt)}">')
        elif name:
            inner = f'<span class="vti-logo-grid__name">{_esc(name)}</span>'
        else:
            raise ValidationError(
                "missing_field", f"logo-grid.props.logos[{i}]",
                "each entry needs at least 'image' or 'name'",
            )
        cells.append(f'  <div class="vti-logo-grid__cell">{inner}</div>')

    return _fill(_component_template("logo-grid"), {
        "TONE":       tone,
        "DENSITY":    density,
        "COLS":       str(cols),
        "LOGOS_HTML": "\n".join(cells),
    })


_VALID_QUOTE_STYLE  = {"hero", "card"}
_VALID_QUOTE_ACCENT = {"deep", "navy", "sky"}


@register_component("quote-block", meta={
    "role": "Pull quote / testimonial with optional attribution "
            "(name, role, company). Two visual styles — hero (centered) "
            "or card (pale-blue background with corner quote mark).",
    "kind": "text",
    "good_for": [
        "single customer testimonial",
        "leadership statement / mission quote",
        "press review pull quote",
    ],
    "bad_for": [
        "multiple peer quotes — they need their own slides",
        "long-form text (use narrative-paragraph)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief": "quote: str≤320, attribution?: {name: str, role?: str, "
                    "company?: str}, style?: 'hero'|'card' (default 'card'), "
                    "accent?: 'deep'|'navy'|'sky' (default 'deep')",
    "font_levels_used":  ["body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 30,
    "picks_content_kinds": ["quote", "testimonial"],
})
def _r_quote_block(props: dict) -> str:
    quote = _require(props, "quote", "quote-block.props")
    _check_max_chars(quote, 320, "quote-block.props.quote")

    attribution = props.get("attribution") or {}
    style       = props.get("style", "card")
    accent      = props.get("accent", "deep")

    if style not in _VALID_QUOTE_STYLE:
        raise ValidationError(
            "invalid_value", "quote-block.props.style",
            f"must be one of {sorted(_VALID_QUOTE_STYLE)}",
        )
    if accent not in _VALID_QUOTE_ACCENT:
        raise ValidationError(
            "invalid_value", "quote-block.props.accent",
            f"must be one of {sorted(_VALID_QUOTE_ACCENT)}",
        )

    # Build attribution block if present. Three optional fields, each
    # rendered only if non-empty so partial attribution still looks clean.
    attr_html = ""
    if attribution and isinstance(attribution, dict):
        name    = attribution.get("name", "")
        role    = attribution.get("role", "")
        company = attribution.get("company", "")
        rows = []
        if name:
            rows.append(f'<span class="vti-quote-block__attribution-name">'
                        f'{_esc(name)}</span>')
        if role or company:
            sep = " · " if (role and company) else ""
            rows.append(f'<span class="vti-quote-block__attribution-role">'
                        f'{_esc(role)}{sep}{_esc(company)}</span>')
        if rows:
            attr_html = (
                f'<figcaption class="vti-quote-block__attribution">'
                f'{"".join(rows)}</figcaption>'
            )

    return _fill(_component_template("quote-block"), {
        "STYLE":            style,
        "ACCENT":           accent,
        "QUOTE":            _esc(quote),
        "ATTRIBUTION_HTML": attr_html,
    })


_VALID_FLOW_DIRECTION = {"horizontal", "vertical"}
_VALID_FLOW_ACCENT    = {"deep", "navy", "sky"}


@register_component("process-flow", meta={
    "role": "Sequence of 3-7 numbered steps with chevron connectors — for "
            "methodology, project lifecycle, customer journey explanations.",
    "kind": "structural",
    "good_for": [
        "3-7 step methodology",
        "project lifecycle (Discover → Design → Deliver → Run)",
        "decision flow / customer journey",
    ],
    "bad_for": [
        "2 steps (use a vs-divider or two practice-cards)",
        "8+ steps (split across two slides)",
        "non-sequential peers (use catalog-column or practice-card)",
    ],
    "best_col_spans": [12],
    "natural_height": "auto",
    "schema_brief": "steps: list[{title: str≤30, body?: str≤140, "
                    "number?: str, icon?: str}] (3-7 entries), "
                    "direction?: 'horizontal'|'vertical' (default 'horizontal'), "
                    "accent?: 'deep'|'navy'|'sky'",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   480,
    "picks_content_kinds": ["process", "steps", "methodology"],
})
def _r_process_flow(props: dict) -> str:
    steps = _require(props, "steps", "process-flow.props")
    if not isinstance(steps, list) or not 3 <= len(steps) <= 7:
        raise ValidationError(
            "invalid_value", "process-flow.props.steps",
            f"expected list of 3-7 step objects, got "
            f"{len(steps) if isinstance(steps, list) else type(steps).__name__}",
        )

    direction = props.get("direction", "horizontal")
    accent    = props.get("accent", "deep")

    if direction not in _VALID_FLOW_DIRECTION:
        raise ValidationError(
            "invalid_value", "process-flow.props.direction",
            f"must be one of {sorted(_VALID_FLOW_DIRECTION)}",
        )
    if accent not in _VALID_FLOW_ACCENT:
        raise ValidationError(
            "invalid_value", "process-flow.props.accent",
            f"must be one of {sorted(_VALID_FLOW_ACCENT)}",
        )

    # Render each step. Number defaults to position (01, 02, 03…) if not
    # explicitly given — same convention as practice-card.
    step_htmls = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValidationError(
                "invalid_value", f"process-flow.props.steps[{i}]",
                "each step must be a dict {title, body?, number?, icon?}",
            )
        title = _esc(_require(step, "title", f"process-flow.props.steps[{i}]"))
        _check_max_chars(step["title"], 30, f"process-flow.steps[{i}].title")
        body = step.get("body", "")
        if body:
            _check_max_chars(body, 140, f"process-flow.steps[{i}].body")
        number = step.get("number") or f"{i+1:02d}"
        icon   = step.get("icon", "")

        # Badge: icon SVG when given, otherwise the number text.
        if icon:
            badge_inner = render_icon(icon)
        else:
            badge_inner = _esc(str(number))

        body_html = (f'<p class="vti-process-flow__body">{_esc(body)}</p>'
                     if body else "")

        step_htmls.append(
            f'  <div class="vti-process-flow__step">\n'
            f'    <div class="vti-process-flow__badge">{badge_inner}</div>\n'
            f'    <div class="vti-process-flow__text">\n'
            f'      <h4 class="vti-process-flow__title">{title}</h4>\n'
            f'      {body_html}\n'
            f'    </div>\n'
            f'  </div>'
        )

    return _fill(_component_template("process-flow"), {
        "DIRECTION":  direction,
        "ACCENT":     accent,
        "STEPS_HTML": "\n".join(step_htmls),
    })


_VALID_SECTION_HEADER_SIZES = {"small", "default", "large"}


@register_component("section-header", meta={
    "role": "Small bold heading for grouping content within a row or column "
            "(e.g. 'Customer Problems' above a bullet list, 'Key metrics' "
            "above a kpi-row). One step DOWN from the slide-level subhead "
            "or chrome breadcrumb.",
    "kind": "text",
    "good_for": [
        "labeling a section within a multi-section column",
        "title above bullet-list-checked / narrative-paragraph / kpi-row",
        "subhead inside a case-study right-column section group",
    ],
    "bad_for": [
        "main slide title (use the chrome breadcrumb)",
        "case-study slide subhead (use the layout's own subhead field)",
        "stat values (use stat-mini / stat-hero)",
    ],
    "best_col_spans": [3, 4, 5, 6, 7, 8, 12],
    "natural_height": "auto",
    "schema_brief":
        "title: str≤40, "
        "size?: 'small'|'default'|'large' (default 'default'), "
        "rule?: bool (default false — show thin underline)",
    "font_levels_used":  ["title", "caption"],
    "font_weights_used": [500],
    "capacity_chars_per_col": 18,
    "picks_content_kinds": ["section_header", "subhead"],
})
def _r_section_header(props: dict) -> str:
    title = _require(props, "title", "section-header.props")
    _check_max_chars(title, 40, "section-header.props.title")
    size = props.get("size", "default")
    rule = bool(props.get("rule", False))

    if size not in _VALID_SECTION_HEADER_SIZES:
        raise ValidationError(
            "invalid_value", "section-header.props.size",
            f"must be one of {sorted(_VALID_SECTION_HEADER_SIZES)}",
        )

    size_class = f" vti-section-header--{size}" if size != "default" else ""
    rule_class = " vti-section-header--ruled" if rule else ""

    return _fill(_component_template("section-header"), {
        "TITLE":      _esc(title),
        "SIZE_CLASS": size_class,
        "RULE_CLASS": rule_class,
    })


# ===========================================================================
# Phase E1 components — data display
# ===========================================================================

# ---------- table -----------------------------------------------------------

_VALID_TABLE_DENSITY = {"compact", "default", "loose"}
_VALID_ALIGN         = {"left", "center", "right"}


@register_component("table", meta={
    "role": "Generic data table — rows × columns of values with optional "
            "header row, per-column alignment, highlighted rows, and "
            "first-column emphasis. Use for revenue tables, KPI scorecards, "
            "specification matrices.",
    "kind": "data",
    "good_for": [
        "tabular numeric data (revenue by quarter)",
        "label/value pairs (config table)",
        "feature specifications (model x capability)",
    ],
    "bad_for": [
        "feature comparison with check/x (use comparison-table instead)",
        "single KPI display (use stat-hero / stat-mini)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 9, 10, 11, 12],
    "natural_height": "auto",
    "schema_brief":
        "headers: list[str], rows: list[list[str]], "
        "alignment?: list['left'|'center'|'right'], "
        "column_widths?: list[str], "
        "highlight_rows?: list[int], "
        "first_col_emphasis?: bool, density?: 'compact'|'default'|'loose'",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 60,
    "picks_content_kinds": ["table", "data_table"],
})
def _r_table(props: dict) -> str:
    headers = props.get("headers", [])
    rows    = _require(props, "rows", "table.props")
    if not isinstance(rows, list) or not rows:
        raise ValidationError(
            "missing_required", "table.props.rows",
            "rows must be a non-empty list of lists",
        )
    n_cols = max(len(headers), max(len(r) for r in rows))
    if n_cols == 0:
        raise ValidationError("empty_table", "table.props",
                              "table must have at least one column")

    alignment      = props.get("alignment", ["left"] * n_cols)
    column_widths  = props.get("column_widths", [])
    highlight_rows = set(props.get("highlight_rows", []))
    first_col_emp  = bool(props.get("first_col_emphasis", False))
    density        = props.get("density", "default")

    if density not in _VALID_TABLE_DENSITY:
        raise ValidationError(
            "invalid_value", "table.props.density",
            f"must be one of {sorted(_VALID_TABLE_DENSITY)}",
        )
    for i, a in enumerate(alignment):
        if a not in _VALID_ALIGN:
            raise ValidationError(
                "invalid_value", f"table.props.alignment[{i}]",
                f"must be one of {sorted(_VALID_ALIGN)}",
            )

    # Build column template (CSS grid columns)
    if column_widths and len(column_widths) >= n_cols:
        cols_template = " ".join(column_widths[:n_cols])
    else:
        cols_template = " ".join(["minmax(0, 1fr)"] * n_cols)

    def _cell_html(text: str, ci: int, is_header: bool = False) -> str:
        align = alignment[ci] if ci < len(alignment) else "left"
        align_class = (f" vti-table__cell--align-{align}"
                       if align != "left" else "")
        # numeric heuristic: pure number-ish strings get tabular-nums
        text_str = str(text)
        is_numeric = bool(text_str.strip()) and all(
            c in "0123456789.,+-%$€£¥ " for c in text_str.strip()
        )
        num_class = " vti-table__cell--numeric" if is_numeric else ""
        return (f'<div class="vti-table__cell{align_class}{num_class}">'
                f'{_esc(text_str)}</div>')

    header_html = ""
    if headers:
        header_cells = "".join(_cell_html(h, i, is_header=True)
                               for i, h in enumerate(headers))
        header_html = (f'<div class="vti-table__row vti-table__row--header">'
                       f'{header_cells}</div>')

    row_htmls = []
    for ri, r in enumerate(rows):
        row_class = ("vti-table__row vti-table__row--highlight"
                     if ri in highlight_rows else "vti-table__row")
        # Pad short rows
        padded = list(r) + [""] * (n_cols - len(r))
        cells = "".join(_cell_html(c, ci) for ci, c in enumerate(padded))
        row_htmls.append(f'<div class="{row_class}">{cells}</div>')

    first_col_class = " vti-table--first-col-emphasis" if first_col_emp else ""

    return _fill(_component_template("table"), {
        "DENSITY":         density,
        "FIRST_COL_CLASS": first_col_class,
        "COLS_TEMPLATE":   cols_template,
        "HEADER_HTML":     header_html,
        "ROWS_HTML":       "\n".join(row_htmls),
    })


# ---------- bar-chart -------------------------------------------------------

_VALID_BAR_ORIENTATION = {"vertical", "horizontal"}
_VALID_BAR_TONES       = {"deep", "medium", "sky", "navy", "gray"}


@register_component("bar-chart", meta={
    "role": "Categorical bar chart — vertical (column) or horizontal "
            "orientation. Renders as inline SVG with viewBox so it scales "
            "to any cell size. Single-series only — for multi-series use "
            "stacked-bar (Phase E4).",
    "kind": "data",
    "good_for": [
        "quarterly revenue / volume comparisons",
        "ranked category data (top-N)",
        "before / after comparisons (2-3 bars)",
    ],
    "bad_for": [
        "share of whole (use pie-chart)",
        "trend over time with many points (use line-chart)",
        "multi-series comparison (use stacked-bar)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "1fr or auto with min ~200px",
    "schema_brief":
        "items: list[{label, value, tone?}], "
        "orientation?: 'vertical'|'horizontal' (default vertical), "
        "title?: str, show_values?: bool (default true), "
        "y_label?: str, max_value?: number",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   120,
    "picks_content_kinds": ["bar_chart", "column_chart"],
})
def _r_bar_chart(props: dict) -> str:
    items = _require(props, "items", "bar-chart.props")
    if not isinstance(items, list) or not items:
        raise ValidationError("missing_required", "bar-chart.props.items",
                              "items must be a non-empty list")

    orientation = props.get("orientation", "vertical")
    if orientation not in _VALID_BAR_ORIENTATION:
        raise ValidationError(
            "invalid_value", "bar-chart.props.orientation",
            f"must be one of {sorted(_VALID_BAR_ORIENTATION)}",
        )

    title       = props.get("title", "")
    show_values = bool(props.get("show_values", True))
    max_value   = props.get("max_value")
    if max_value is None:
        max_value = max(float(it.get("value", 0)) for it in items)
    max_value = float(max_value) or 1.0   # avoid div-by-zero

    n = len(items)

    if orientation == "vertical":
        VB_W, VB_H = 800, 400
        plot_left, plot_right  = 60, 780
        plot_top,  plot_bottom = 30, 340
        plot_w = plot_right - plot_left
        plot_h = plot_bottom - plot_top

        bar_slot = plot_w / n
        bar_w    = bar_slot * 0.55

        bars_svg, value_labels, cat_labels = [], [], []
        for i, it in enumerate(items):
            value = float(it.get("value", 0))
            label = str(it.get("label", ""))
            tone  = it.get("tone", "deep")
            if tone not in _VALID_BAR_TONES:
                raise ValidationError(
                    "invalid_value",
                    f"bar-chart.props.items[{i}].tone",
                    f"must be one of {sorted(_VALID_BAR_TONES)}",
                )
            h = (value / max_value) * plot_h
            x = plot_left + bar_slot * i + (bar_slot - bar_w) / 2
            y = plot_bottom - h
            bars_svg.append(
                f'<rect class="vti-bar-chart__bar vti-bar-chart__bar--{tone}" '
                f'x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
                f'height="{h:.1f}" rx="3"/>')
            cat_labels.append(
                f'<text class="vti-bar-chart__cat-label" '
                f'x="{x + bar_w / 2:.1f}" y="{plot_bottom + 22:.1f}">'
                f'{_esc(label)}</text>')
            if show_values:
                value_labels.append(
                    f'<text class="vti-bar-chart__value-label" '
                    f'x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}">'
                    f'{_esc(_fmt_num(value))}</text>')

        axes = (f'<line class="vti-bar-chart__axis-line" '
                f'x1="{plot_left}" y1="{plot_bottom}" '
                f'x2="{plot_right}" y2="{plot_bottom}"/>')
    else:
        # horizontal
        VB_W, VB_H = 800, 60 * n + 40
        plot_left, plot_right  = 160, 760
        plot_top,  plot_bottom = 20, VB_H - 20
        plot_w = plot_right - plot_left

        bar_slot = (plot_bottom - plot_top) / n
        bar_h    = bar_slot * 0.55

        bars_svg, value_labels, cat_labels = [], [], []
        for i, it in enumerate(items):
            value = float(it.get("value", 0))
            label = str(it.get("label", ""))
            tone  = it.get("tone", "deep")
            if tone not in _VALID_BAR_TONES:
                raise ValidationError(
                    "invalid_value",
                    f"bar-chart.props.items[{i}].tone",
                    f"must be one of {sorted(_VALID_BAR_TONES)}",
                )
            w = (value / max_value) * plot_w
            y = plot_top + bar_slot * i + (bar_slot - bar_h) / 2
            x = plot_left
            bars_svg.append(
                f'<rect class="vti-bar-chart__bar vti-bar-chart__bar--{tone}" '
                f'x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
                f'height="{bar_h:.1f}" rx="3"/>')
            cat_labels.append(
                f'<text class="vti-bar-chart__cat-label" '
                f'x="{plot_left - 10:.1f}" y="{y + bar_h / 2 + 5:.1f}">'
                f'{_esc(label)}</text>')
            if show_values:
                value_labels.append(
                    f'<text class="vti-bar-chart__value-label" '
                    f'x="{x + w + 8:.1f}" y="{y + bar_h / 2 + 5:.1f}">'
                    f'{_esc(_fmt_num(value))}</text>')

        axes = (f'<line class="vti-bar-chart__axis-line" '
                f'x1="{plot_left}" y1="{plot_top}" '
                f'x2="{plot_left}" y2="{plot_bottom}"/>')

    title_html = ""
    if title:
        title_html = f'<div class="vti-bar-chart__title">{_esc(title)}</div>'

    return _fill(_component_template("bar-chart"), {
        "ORIENTATION":      orientation,
        "TITLE_HTML":       title_html,
        "VB_W":             str(VB_W),
        "VB_H":             str(VB_H),
        "AXES_SVG":         axes,
        "BARS_SVG":         "\n".join(bars_svg),
        "VALUE_LABELS_SVG": "\n".join(value_labels),
        "CAT_LABELS_SVG":   "\n".join(cat_labels),
    })


def _fmt_num(n: float) -> str:
    """Format a numeric value tersely for chart labels."""
    if n == int(n):
        return f"{int(n):,}"
    if abs(n) >= 100:
        return f"{n:,.0f}"
    return f"{n:,.1f}"


# ---------- pie-chart -------------------------------------------------------

import math as _math

_VALID_PIE_LAYOUTS  = {"legend-right", "legend-below"}

# VTI brand chart palette — ordered by emphasis (most → least).
# All blues are tints/shades of the VTI brand blue + neutral grays for
# de-emphasis. NO amber/yellow per design rule: "emphasis = VTI blue".
_VTI_CHART_PALETTE = [
    "var(--vti-blue-deep)",      # #0844A4 — primary brand, max emphasis
    "var(--vti-blue-medium)",    # #1B5DE6 — secondary
    "var(--vti-sky)",            # #0782FF — tertiary
    "#7DC1FE",                   # blue-cyan — quaternary (lightest blue)
    "#6B7280",                   # gray-500 — neutral
    "#9CA3AF",                   # gray-400 — softer neutral
    "#374151",                   # gray-700 — extra series if needed
    "#D1D5DB",                   # gray-300 — extra series if needed
]
_PIE_DEFAULT_COLORS = _VTI_CHART_PALETTE


def _polar(cx: float, cy: float, r: float, angle_deg: float) -> tuple:
    a = _math.radians(angle_deg - 90)   # 0° points up
    return (cx + r * _math.cos(a), cy + r * _math.sin(a))


def _arc_path(cx: float, cy: float, r: float,
              start_a: float, end_a: float) -> str:
    """SVG path for a pie segment from start_a to end_a (degrees, clockwise)."""
    x1, y1 = _polar(cx, cy, r, start_a)
    x2, y2 = _polar(cx, cy, r, end_a)
    large = 1 if (end_a - start_a) > 180 else 0
    return (f"M {cx} {cy} L {x1:.2f} {y1:.2f} "
            f"A {r} {r} 0 {large} 1 {x2:.2f} {y2:.2f} Z")


@register_component("pie-chart", meta={
    "role": "Share-of-whole pie or donut chart with optional center label "
            "and legend on right (default) or below (for narrow cells). "
            "Auto-percentage from absolute values.",
    "kind": "data",
    "good_for": [
        "market share / customer mix",
        "budget allocation",
        "team / capability breakdown",
    ],
    "bad_for": [
        "trend over time (use line-chart)",
        "ranked comparison (use bar-chart)",
        "more than ~7 segments (becomes unreadable)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "1fr or auto with min ~200px",
    "schema_brief":
        "items: list[{label, value, color?}], "
        "donut?: bool (default false), "
        "center_value?: str, center_label?: str, "
        "layout?: 'legend-right'|'legend-below' (default legend-right)",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   100,
    "picks_content_kinds": ["pie_chart", "donut_chart", "share_chart"],
})
def _r_pie_chart(props: dict) -> str:
    items = _require(props, "items", "pie-chart.props")
    if not isinstance(items, list) or not items:
        raise ValidationError("missing_required", "pie-chart.props.items",
                              "items must be a non-empty list")
    if len(items) > 8:
        raise ValidationError(
            "invalid_value", "pie-chart.props.items",
            "too many segments (>8 unreadable); aggregate small slices",
        )

    donut        = bool(props.get("donut", False))
    center_value = props.get("center_value", "")
    center_label = props.get("center_label", "")
    layout       = props.get("layout", "legend-right")
    if layout not in _VALID_PIE_LAYOUTS:
        raise ValidationError(
            "invalid_value", "pie-chart.props.layout",
            f"must be one of {sorted(_VALID_PIE_LAYOUTS)}",
        )

    total = sum(float(it.get("value", 0)) for it in items)
    if total <= 0:
        raise ValidationError(
            "invalid_value", "pie-chart.props.items",
            "sum of item values must be positive",
        )

    cx, cy, r = 100.0, 100.0, 90.0

    segments_svg = []
    legend_rows  = []
    angle_pos    = 0.0
    for i, it in enumerate(items):
        value = float(it.get("value", 0))
        label = str(it.get("label", ""))
        color = it.get("color", _PIE_DEFAULT_COLORS[i % len(_PIE_DEFAULT_COLORS)])
        share = value / total
        pct   = round(share * 100, 1)
        end_a = angle_pos + share * 360.0

        # Single-segment full-circle special case (avoid 360° arc bug)
        if len(items) == 1:
            seg = (f'<circle class="vti-pie-chart__segment" '
                   f'cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
        else:
            d = _arc_path(cx, cy, r, angle_pos, end_a)
            seg = (f'<path class="vti-pie-chart__segment" '
                   f'd="{d}" fill="{color}"/>')
        segments_svg.append(seg)

        legend_rows.append(
            f'<div class="vti-pie-chart__legend-row">'
            f'<span class="vti-pie-chart__swatch" '
            f'style="background:{color};"></span>'
            f'<span class="vti-pie-chart__legend-label">{_esc(label)}</span>'
            f'<span class="vti-pie-chart__legend-pct">{pct:.0f}%</span>'
            f'</div>'
        )
        angle_pos = end_a

    donut_hole_svg = ""
    center_label_svg = ""
    if donut:
        donut_hole_svg = (f'<circle class="vti-pie-chart__hole" '
                          f'cx="{cx}" cy="{cy}" r="55"/>')
        if center_value:
            center_label_svg += (
                f'<text class="vti-pie-chart__center-value" '
                f'x="{cx}" y="{cy - 4}">{_esc(center_value)}</text>')
        if center_label:
            center_label_svg += (
                f'<text class="vti-pie-chart__center-label" '
                f'x="{cx}" y="{cy + 16}">{_esc(center_label)}</text>')

    legend_html = (f'<div class="vti-pie-chart__legend">'
                   f'{"".join(legend_rows)}</div>')

    return _fill(_component_template("pie-chart"), {
        "LAYOUT":            layout,
        "SEGMENTS_SVG":      "\n".join(segments_svg),
        "DONUT_HOLE_SVG":    donut_hole_svg,
        "CENTER_LABEL_SVG":  center_label_svg,
        "LEGEND_HTML":       legend_html,
    })


# ---------- trend-stat -------------------------------------------------------

_VALID_TRENDS = {"up", "down", "flat"}


@register_component("trend-stat", meta={
    "role": "Single KPI value + delta arrow + period descriptor. "
            "Like stat-mini but with directional movement (▲ up green, "
            "▼ down red, — flat gray).",
    "kind": "data",
    "good_for": [
        "QoQ / YoY KPI movements (revenue +18% vs Q3)",
        "scoreboard panels (3-4 trend-stats in a row)",
    ],
    "bad_for": [
        "single static stat (use stat-hero / stat-mini)",
        "category comparisons (use bar-chart)",
    ],
    "best_col_spans": [3, 4, 5, 6],
    "natural_height": "auto",
    "schema_brief":
        "value: str, delta: str (e.g. '+18.3%'), "
        "trend: 'up'|'down'|'flat', period?: str, label?: str, "
        "size?: 'small'|'default'",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   100,
    "picks_content_kinds": ["trend_stat", "kpi_movement"],
})
def _r_trend_stat(props: dict) -> str:
    value  = _require(props, "value", "trend-stat.props")
    delta  = _require(props, "delta", "trend-stat.props")
    trend  = props.get("trend", "flat")
    period = props.get("period", "")
    label  = props.get("label", "")
    size   = props.get("size", "default")

    if trend not in _VALID_TRENDS:
        raise ValidationError(
            "invalid_value", "trend-stat.props.trend",
            f"must be one of {sorted(_VALID_TRENDS)}",
        )

    arrows = {
        "up":   '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 2 L13 9 L10 9 L10 14 L6 14 L6 9 L3 9 Z"/></svg>',
        "down": '<svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 14 L13 7 L10 7 L10 2 L6 2 L6 7 L3 7 Z"/></svg>',
        "flat": '<svg viewBox="0 0 16 16" fill="currentColor"><rect x="3" y="7" width="10" height="2" rx="1"/></svg>',
    }

    size_class = " vti-trend-stat--small" if size == "small" else ""
    # Hack: append size class on root by reusing TREND placeholder isn't ideal,
    # so pass via a separate marker. Simpler: include in template on `vti-trend-stat`.
    # For now we render via root-level concat in the HTML template wrapping.
    out = _fill(_component_template("trend-stat"), {
        "TREND":     trend,
        "VALUE":     _esc(str(value)),
        "DELTA":     _esc(str(delta)),
        "PERIOD":    _esc(period),
        "LABEL":     _esc(label),
        "ARROW_SVG": arrows[trend],
    })
    if size_class:
        out = out.replace('class="vti-trend-stat ',
                          f'class="vti-trend-stat{size_class} ', 1)
    return out


# ===========================================================================
# Paragraph / text components — richer ways to present text content.
#
# Design principle (per VTI brand rule): emphasis = VTI blue (deep / navy).
# These components compose well WITH visual components (image-tile, charts,
# stat-hero, etc.) — kicker above headline, headline above narrative,
# tags below image, etc.
# ===========================================================================

# ---------- lead-paragraph --------------------------------------------------

_VALID_LEAD_ALIGN = {"left", "center"}
_VALID_LEAD_TONE  = {"default", "muted"}


@register_component("lead-paragraph", meta={
    "role": "Opening paragraph (the 'lede') — larger and heavier than "
            "narrative-paragraph (17px / weight 500 vs 14px / weight 400). "
            "Use to introduce a content slide before the body text. "
            "Inline **emphasis** wraps in <strong> with VTI blue color.",
    "kind": "text",
    "good_for": [
        "first paragraph on a content slide",
        "executive summary text",
        "topic sentence above a chart or list",
    ],
    "bad_for": [
        "regular body paragraphs (use narrative-paragraph)",
        "single-sentence hero statement (use headline)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "text: str OR paragraphs: list[str], "
        "align?: 'left'|'center' (default 'left'), "
        "tone?: 'default'|'muted' (default 'default')",
    "font_levels_used":  ["body"],
    "font_weights_used": [400],
    "capacity_chars_per_col": 100,
    "picks_content_kinds": ["lead_paragraph", "lede"],
})
def _r_lead_paragraph(props: dict) -> str:
    text = props.get("text")
    paragraphs = props.get("paragraphs")
    if text and not paragraphs:
        paragraphs = [text]
    if not paragraphs:
        raise ValidationError(
            "missing_required", "lead-paragraph.props",
            "must provide text or paragraphs",
        )

    align = props.get("align", "left")
    tone  = props.get("tone", "default")
    if align not in _VALID_LEAD_ALIGN:
        raise ValidationError(
            "invalid_value", "lead-paragraph.props.align",
            f"must be one of {sorted(_VALID_LEAD_ALIGN)}",
        )
    if tone not in _VALID_LEAD_TONE:
        raise ValidationError(
            "invalid_value", "lead-paragraph.props.tone",
            f"must be one of {sorted(_VALID_LEAD_TONE)}",
        )

    paragraphs_html = "\n".join(
        f"<p>{_inline_strong(_esc(p))}</p>" for p in paragraphs
    )
    tone_class = f" vti-lead-paragraph--{tone}" if tone != "default" else ""

    return _fill(_component_template("lead-paragraph"), {
        "ALIGN":            align,
        "TONE_CLASS":       tone_class,
        "PARAGRAPHS_HTML":  paragraphs_html,
    })


def _inline_strong(s: str) -> str:
    """Convert markdown **bold** to <strong> for inline emphasis.
    Operates on already-escaped text (so <, > are entities). Simple regex."""
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


# ---------- headline --------------------------------------------------------

_VALID_HEADLINE_SIZE  = {"medium", "large"}
_VALID_HEADLINE_COLOR = {"deep", "navy", "ink"}
_VALID_HEADLINE_ALIGN = {"left", "center"}


@register_component("headline", meta={
    "role": "Big inline hero statement for content slides — distinct from "
            "the chrome breadcrumb (slide title). 26px / 36px sizes. "
            "Optional leading vertical bar accent for stronger anchor.",
    "kind": "text",
    "good_for": [
        "hero statement that sets the slide's main argument",
        "section opener inside a content slide",
        "punchy 1-sentence summaries",
    ],
    "bad_for": [
        "small section labels (use kicker)",
        "body-text paragraphs (use narrative-paragraph)",
        "data values (use stat-hero)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "text: str, size?: 'medium'|'large' (default 'medium'), "
        "color?: 'deep'|'navy'|'ink' (default 'deep'), "
        "align?: 'left'|'center' (default 'left'), "
        "show_bar?: bool (default false — leading vertical bar accent)",
    "font_levels_used":  ["display"],
    "font_weights_used": [600],
    "capacity_chars_per_col": 8,
    "picks_content_kinds": ["headline", "hero_statement"],
})
def _r_headline(props: dict) -> str:
    text  = _require(props, "text", "headline.props")
    size  = props.get("size", "medium")
    color = props.get("color", "deep")
    align = props.get("align", "left")
    show_bar = bool(props.get("show_bar", False))

    if size not in _VALID_HEADLINE_SIZE:
        raise ValidationError(
            "invalid_value", "headline.props.size",
            f"must be one of {sorted(_VALID_HEADLINE_SIZE)}",
        )
    if color not in _VALID_HEADLINE_COLOR:
        raise ValidationError(
            "invalid_value", "headline.props.color",
            f"must be one of {sorted(_VALID_HEADLINE_COLOR)}",
        )
    if align not in _VALID_HEADLINE_ALIGN:
        raise ValidationError(
            "invalid_value", "headline.props.align",
            f"must be one of {sorted(_VALID_HEADLINE_ALIGN)}",
        )
    # Leading bar only makes sense on left-aligned headlines
    if show_bar and align == "center":
        show_bar = False

    bar_html = '<span class="vti-headline__bar"></span>' if show_bar else ""
    bar_class = " vti-headline--with-bar" if show_bar else ""

    return _fill(_component_template("headline"), {
        "SIZE":      size,
        "COLOR":     color,
        "ALIGN":     align,
        "BAR_CLASS": bar_class,
        "BAR_HTML":  bar_html,
        "TEXT":      _inline_strong(_esc(text)),
    })


# ---------- kicker ----------------------------------------------------------

_VALID_KICKER_ALIGN = {"left", "center"}


@register_component("kicker", meta={
    "role": "Small uppercase eyebrow / kicker label — sits ABOVE a headline, "
            "narrative, image, or chart to label the section / topic. "
            "Optional thin underline (rule: true).",
    "kind": "text",
    "good_for": [
        "eyebrow above a headline ('OUR APPROACH' → big headline)",
        "section labels above visual content",
        "category / topic markers",
    ],
    "bad_for": [
        "regular section title (use section-header)",
        "main slide title (use chrome breadcrumb)",
        "long sentences (kicker is for 1-4 words)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "auto",
    "schema_brief":
        "text: str (≤40 chars), "
        "rule?: bool (default false — show underline), "
        "align?: 'left'|'center' (default 'left')",
    "font_levels_used":  ["caption"],
    "font_weights_used": [500],
    "capacity_chars_per_col": 5,
    "picks_content_kinds": ["kicker", "eyebrow", "topic_label"],
})
def _r_kicker(props: dict) -> str:
    text = _require(props, "text", "kicker.props")
    _check_max_chars(text, 40, "kicker.props.text")
    rule  = bool(props.get("rule", False))
    align = props.get("align", "left")

    if align not in _VALID_KICKER_ALIGN:
        raise ValidationError(
            "invalid_value", "kicker.props.align",
            f"must be one of {sorted(_VALID_KICKER_ALIGN)}",
        )

    rule_class = " vti-kicker--ruled" if rule else ""

    return _fill(_component_template("kicker"), {
        "ALIGN":      align,
        "RULE_CLASS": rule_class,
        "TEXT":       _esc(text),
    })


# ---------- numbered-list ---------------------------------------------------

_VALID_NUMLIST_DENSITY = {"compact", "default", "loose"}
_VALID_NUMLIST_STYLE   = {"circle", "block"}


@register_component("numbered-list", meta={
    "role": "Items with prominent numbered anchors (01, 02, 03 …). Use when "
            "ORDERING is meaningful — vs bullet-list-checked which is for "
            "set-of-things. Items can be plain strings OR dicts with "
            "{title, body} for richer entries.",
    "kind": "text",
    "good_for": [
        "ordered steps in a methodology",
        "ranked list (top 5 priorities)",
        "phased plan with descriptions",
    ],
    "bad_for": [
        "unordered sets (use bullet-list-checked)",
        "key-value pairs (use definition-list)",
        "process flow visualization (use process-flow / timeline)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "auto",
    "schema_brief":
        "items: list[str | {title, body?}], "
        "density?: 'compact'|'default'|'loose', "
        "number_style?: 'circle'|'block' (default 'circle')",
    "font_levels_used":  ["body"],
    "font_weights_used": [400],
    "capacity_chars_per_col": 40,
    "picks_content_kinds": ["numbered_list", "ordered_list", "ranked_list"],
})
def _r_numbered_list(props: dict) -> str:
    items = _require(props, "items", "numbered-list.props")
    if not isinstance(items, list) or not items:
        raise ValidationError(
            "missing_required", "numbered-list.props.items",
            "items must be a non-empty list",
        )
    if len(items) > 9:
        raise ValidationError(
            "invalid_value", "numbered-list.props.items",
            "max 9 items (>9 becomes hard to scan)",
        )

    density = props.get("density", "default")
    style   = props.get("number_style", "circle")
    if density not in _VALID_NUMLIST_DENSITY:
        raise ValidationError(
            "invalid_value", "numbered-list.props.density",
            f"must be one of {sorted(_VALID_NUMLIST_DENSITY)}",
        )
    if style not in _VALID_NUMLIST_STYLE:
        raise ValidationError(
            "invalid_value", "numbered-list.props.number_style",
            f"must be one of {sorted(_VALID_NUMLIST_STYLE)}",
        )

    items_html = []
    for i, it in enumerate(items, 1):
        if isinstance(it, str):
            content = (
                f'<div class="vti-numbered-list__title">{_esc(it)}</div>'
            )
            item_cls = "vti-numbered-list__item vti-numbered-list__item--plain"
        elif isinstance(it, dict):
            title = it.get("title", "")
            body  = it.get("body", "")
            body_html = (f'<div class="vti-numbered-list__body">{_esc(body)}</div>'
                         if body else "")
            content = (
                f'<div class="vti-numbered-list__title">{_esc(title)}</div>'
                f'{body_html}'
            )
            item_cls = "vti-numbered-list__item"
        else:
            raise ValidationError(
                "invalid_type", f"numbered-list.props.items[{i - 1}]",
                "each item must be str or {title, body?}",
            )

        items_html.append(
            f'<li class="{item_cls}">'
            f'<span class="vti-numbered-list__num">{i:02d}</span>'
            f'<div class="vti-numbered-list__content">{content}</div>'
            f'</li>'
        )

    return _fill(_component_template("numbered-list"), {
        "DENSITY":    density,
        "STYLE":      style,
        "ITEMS_HTML": "\n".join(items_html),
    })


# ---------- definition-list -------------------------------------------------

_VALID_DEFLIST_LAYOUT  = {"horizontal", "stacked"}
_VALID_DEFLIST_DENSITY = {"compact", "default", "loose"}


@register_component("definition-list", meta={
    "role": "Term: value pairs. horizontal layout = term on left "
            "(uppercase blue), value on right (ink). stacked layout = "
            "term above (small uppercase), value below (larger). "
            "Use for spec sheets, capability summaries, key-value pairs.",
    "kind": "text",
    "good_for": [
        "company spec sheet (Engineers: 1,200+; Hubs: 4)",
        "capability summary (Languages: VN/JP/KR/EN)",
        "after-image data block on a slide",
    ],
    "bad_for": [
        "rich tabular data (use table)",
        "feature comparison (use comparison-table)",
        "single statistic (use stat-hero / stat-mini)",
    ],
    "best_col_spans": [3, 4, 5, 6, 7, 8],
    "natural_height": "auto",
    "schema_brief":
        "items: list[{term, value}], "
        "layout?: 'horizontal'|'stacked' (default 'horizontal'), "
        "density?: 'compact'|'default'|'loose' (default 'default')",
    "font_levels_used":  ["body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 60,
    "picks_content_kinds": ["definition_list", "key_value", "spec_sheet"],
})
def _r_definition_list(props: dict) -> str:
    items = _require(props, "items", "definition-list.props")
    if not isinstance(items, list) or not items:
        raise ValidationError(
            "missing_required", "definition-list.props.items",
            "items must be a non-empty list",
        )
    layout  = props.get("layout", "horizontal")
    density = props.get("density", "default")

    if layout not in _VALID_DEFLIST_LAYOUT:
        raise ValidationError(
            "invalid_value", "definition-list.props.layout",
            f"must be one of {sorted(_VALID_DEFLIST_LAYOUT)}",
        )
    if density not in _VALID_DEFLIST_DENSITY:
        raise ValidationError(
            "invalid_value", "definition-list.props.density",
            f"must be one of {sorted(_VALID_DEFLIST_DENSITY)}",
        )

    items_html = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValidationError(
                "invalid_type", f"definition-list.props.items[{i}]",
                "each item must be {term, value}",
            )
        term  = it.get("term", "")
        value = it.get("value", "")
        items_html.append(
            f'<div class="vti-definition-list__item">'
            f'<dt class="vti-definition-list__term">{_esc(str(term))}</dt>'
            f'<dd class="vti-definition-list__value">{_esc(str(value))}</dd>'
            f'</div>'
        )

    return _fill(_component_template("definition-list"), {
        "LAYOUT":     layout,
        "DENSITY":    density,
        "ITEMS_HTML": "\n".join(items_html),
    })


# ---------- tags ------------------------------------------------------------

_VALID_TAGS_TONE = {"deep", "medium", "sky", "soft"}
_VALID_TAGS_SIZE = {"default", "small"}


@register_component("tags", meta={
    "role": "Inline pill chips for categorization / capability badges. "
            "4 tones: solid (deep/medium/sky) for prominence, soft (pale "
            "blue bg + deep blue text) for many-tag scenarios. Wrap to "
            "multiple rows automatically.",
    "kind": "text",
    "good_for": [
        "capability list under an image-tile or headline",
        "category markers ('AI · Cloud · Data')",
        "tech stack badges (Python · React · Kubernetes)",
    ],
    "bad_for": [
        "long phrases (tags are 1-3 words each)",
        "ranked / ordered lists (use numbered-list)",
        "single emphasis label (use kicker)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "items: list[str], "
        "tone?: 'deep'|'medium'|'sky'|'soft' (default 'soft'), "
        "size?: 'default'|'small' (default 'default')",
    "font_levels_used":  ["caption"],
    "font_weights_used": [500],
    "capacity_chars_per_col": 30,
    "picks_content_kinds": ["tags", "chips", "badges"],
})
def _r_tags(props: dict) -> str:
    items = _require(props, "items", "tags.props")
    if not isinstance(items, list) or not items:
        raise ValidationError(
            "missing_required", "tags.props.items",
            "items must be a non-empty list",
        )
    tone = props.get("tone", "soft")
    size = props.get("size", "default")
    if tone not in _VALID_TAGS_TONE:
        raise ValidationError(
            "invalid_value", "tags.props.tone",
            f"must be one of {sorted(_VALID_TAGS_TONE)}",
        )
    if size not in _VALID_TAGS_SIZE:
        raise ValidationError(
            "invalid_value", "tags.props.size",
            f"must be one of {sorted(_VALID_TAGS_SIZE)}",
        )

    tags_html = "\n".join(
        f'<span class="vti-tag">{_esc(str(t))}</span>' for t in items
    )

    return _fill(_component_template("tags"), {
        "TONE":      tone,
        "SIZE":      size,
        "TAGS_HTML": tags_html,
    })


# ---------- pull-quote ------------------------------------------------------

_VALID_PULLQUOTE_SIZE  = {"default", "large"}
_VALID_PULLQUOTE_ALIGN = {"left", "center"}


@register_component("pull-quote", meta={
    "role": "Editorial pull-out quote — large italic text with big opening "
            "quote mark. Different from quote-block (which has structured "
            "name/role/company attribution). pull-quote is for memorable "
            "phrases pulled from prose; attribution is optional and free-form.",
    "kind": "text",
    "good_for": [
        "memorable phrase highlight on a content slide",
        "editorial / book-style quote",
        "key insight pulled from a longer passage",
    ],
    "bad_for": [
        "structured testimonial (use quote-block)",
        "factual statement / claim (use callout)",
        "long passages (pull-quote is 1-2 sentences max)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "text: str, attribution?: str, "
        "size?: 'default'|'large' (default 'default'), "
        "align?: 'left'|'center' (default 'left')",
    "font_levels_used":  ["display"],
    "font_weights_used": [400],
    "capacity_chars_per_col": 20,
    "picks_content_kinds": ["pull_quote", "editorial_quote"],
})
def _r_pull_quote(props: dict) -> str:
    text  = _require(props, "text", "pull-quote.props")
    size  = props.get("size", "default")
    align = props.get("align", "left")
    attribution = props.get("attribution", "")

    if size not in _VALID_PULLQUOTE_SIZE:
        raise ValidationError(
            "invalid_value", "pull-quote.props.size",
            f"must be one of {sorted(_VALID_PULLQUOTE_SIZE)}",
        )
    if align not in _VALID_PULLQUOTE_ALIGN:
        raise ValidationError(
            "invalid_value", "pull-quote.props.align",
            f"must be one of {sorted(_VALID_PULLQUOTE_ALIGN)}",
        )

    attribution_html = ""
    if attribution:
        attribution_html = (
            f'<cite class="vti-pull-quote__attribution">{_esc(attribution)}</cite>'
        )

    return _fill(_component_template("pull-quote"), {
        "SIZE":             size,
        "ALIGN":            align,
        "TEXT":             _inline_strong(_esc(text)),
        "ATTRIBUTION_HTML": attribution_html,
    })


# ===========================================================================
# Phase E2 components — process / structure
# ===========================================================================

# ---------- swimlane --------------------------------------------------------

_VALID_SWIMLANE_TONES   = {"deep", "medium", "sky", "navy"}
_VALID_SWIMLANE_DENSITY = {"compact", "rich"}


@register_component("swimlane", meta={
    "role": "Multi-actor process diagram with horizontal lanes (one per actor) "
            "× columns (one per step). Two density modes: "
            "'compact' (default) shows title + small icon per step; 'rich' "
            "adds a body paragraph per step describing what happens. Empty "
            "steps render as hatched cells. Steps can be marked accent for "
            "the key handoff in a flow.",
    "kind": "diagram",
    "good_for": [
        "customer journey across actors (Customer / System / Support)",
        "release process across teams",
        "data pipeline showing transitions and what each stage does (rich)",
    ],
    "bad_for": [
        "single-track linear flow (use process-flow)",
        "free-form network / non-linear structures",
    ],
    "best_col_spans": [8, 10, 11, 12],
    "natural_height":
        "compact: auto (~60px per lane); rich: ~110px+ per lane",
    "schema_brief":
        "lanes: list[{name, tone?, steps: list[{title, icon?, body?, "
        "accent?: bool} | None]}], "
        "density?: 'compact'|'rich' (default compact), "
        "step_count?: int (auto from longest lane)",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   400,
    "picks_content_kinds": ["swimlane", "process_lanes"],
})
def _r_swimlane(props: dict) -> str:
    lanes = _require(props, "lanes", "swimlane.props")
    if not isinstance(lanes, list) or not lanes:
        raise ValidationError("missing_required", "swimlane.props.lanes",
                              "lanes must be a non-empty list")

    density = props.get("density", "compact")
    if density not in _VALID_SWIMLANE_DENSITY:
        raise ValidationError(
            "invalid_value", "swimlane.props.density",
            f"must be one of {sorted(_VALID_SWIMLANE_DENSITY)}",
        )

    # Compute step count from longest lane (or explicit override)
    n_steps = props.get("step_count", 0) or max(
        len(la.get("steps", []) or []) for la in lanes
    )
    if n_steps < 2:
        raise ValidationError("invalid_value", "swimlane.props",
                              "swimlane needs at least 2 steps")

    lanes_html = []
    for li, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            raise ValidationError("invalid_type", f"swimlane.props.lanes[{li}]",
                                  "each lane must be a dict")
        name = lane.get("name", f"Lane {li + 1}")
        tone = lane.get("tone", "deep")
        if tone not in _VALID_SWIMLANE_TONES:
            raise ValidationError(
                "invalid_value", f"swimlane.props.lanes[{li}].tone",
                f"must be one of {sorted(_VALID_SWIMLANE_TONES)}",
            )
        steps = lane.get("steps", []) or []
        # Pad to n_steps
        steps = list(steps) + [None] * (n_steps - len(steps))

        steps_html = []
        for si, step in enumerate(steps[:n_steps]):
            if (step is None or step == ""
                    or (isinstance(step, dict) and not step)):
                steps_html.append(
                    '<div class="vti-swimlane__step '
                    'vti-swimlane__step--empty"></div>'
                )
                continue

            if isinstance(step, dict):
                title  = step.get("title", "")
                icon   = step.get("icon", "")
                body   = step.get("body", "")
                accent = bool(step.get("accent", False))
            else:
                title, icon, body, accent = str(step), "", "", False

            step_cls = "vti-swimlane__step"
            if accent:
                step_cls += " vti-swimlane__step--accent"

            icon_html = ""
            if icon:
                icon_svg = render_icon(icon)
                if icon_svg:
                    icon_html = (
                        f'<div class="vti-swimlane__step-icon">{icon_svg}</div>'
                    )

            # Body only rendered in rich mode (compact mode would crowd cells)
            body_html = ""
            if body and density == "rich":
                body_html = (
                    f'<div class="vti-swimlane__step-body">{_esc(body)}</div>'
                )

            steps_html.append(
                f'<div class="{step_cls}">'
                f'{icon_html}'
                f'<div class="vti-swimlane__step-title">{_esc(title)}</div>'
                f'{body_html}'
                f'</div>'
            )

        lanes_html.append(
            f'<div class="vti-swimlane__lane vti-swimlane__lane--{tone}">'
            f'<div class="vti-swimlane__lane-name">{_esc(name)}</div>'
            f'<div class="vti-swimlane__steps">{"".join(steps_html)}</div>'
            f'</div>'
        )

    return _fill(_component_template("swimlane"), {
        "DENSITY":    density,
        "N_STEPS":    str(n_steps),
        "LANES_HTML": "\n".join(lanes_html),
    })


# ---------- timeline --------------------------------------------------------

_VALID_TIMELINE_ORIENTATION = {"horizontal", "vertical"}


@register_component("timeline", meta={
    "role": "Card-based events on a time axis. Each event = a richer card "
            "with optional body, deliverables list (✓ bullets), and metric "
            "badge (e.g. '+28% / conversion'). Horizontal = events distributed "
            "left-to-right with track running through dots; vertical = events "
            "stacked top-to-bottom with track on left. Milestone items get an "
            "navy-accented card + larger navy dot (deeper than regular events).",
    "kind": "diagram",
    "good_for": [
        "project phases by quarter with deliverables shipped",
        "company milestones with KPI deltas at each step",
        "rollout plan over months — what was delivered when",
    ],
    "bad_for": [
        "non-temporal sequences (use process-flow)",
        "more than ~5 events horizontally (cards become cramped — use vertical)",
    ],
    "best_col_spans": [6, 8, 10, 12],
    "natural_height":
        "auto (~150-220px horizontal depending on card content; "
        "~80px per event vertical)",
    "schema_brief":
        "items: list[{date, title, body?, deliverables?: list[str], "
        "metric?: {value, label}, milestone?: bool}], "
        "orientation?: 'horizontal'|'vertical' (default horizontal)",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   400,
    "picks_content_kinds": ["timeline"],
})
def _r_timeline(props: dict) -> str:
    items = _require(props, "items", "timeline.props")
    if not isinstance(items, list) or not items:
        raise ValidationError("missing_required", "timeline.props.items",
                              "items must be a non-empty list")
    orientation = props.get("orientation", "horizontal")
    if orientation not in _VALID_TIMELINE_ORIENTATION:
        raise ValidationError(
            "invalid_value", "timeline.props.orientation",
            f"must be one of {sorted(_VALID_TIMELINE_ORIENTATION)}",
        )

    events_html = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValidationError("invalid_type", f"timeline.props.items[{i}]",
                                  "each item must be a dict")
        date         = it.get("date", "")
        title        = it.get("title", "")
        body         = it.get("body", "")
        deliverables = it.get("deliverables", []) or []
        metric       = it.get("metric")
        milestone    = bool(it.get("milestone", False))

        cls = "vti-timeline__event"
        if milestone:
            cls += " vti-timeline__event--milestone"

        # Metric badge (top-right of card)
        metric_html = ""
        if metric and isinstance(metric, dict) and metric.get("value"):
            metric_html = (
                f'<div class="vti-timeline__metric">'
                f'<div class="vti-timeline__metric-value">'
                f'{_esc(str(metric.get("value", "")))}</div>'
                + (f'<div class="vti-timeline__metric-label">'
                   f'{_esc(str(metric.get("label", "")))}</div>'
                   if metric.get("label") else "")
                + '</div>'
            )

        # Body paragraph
        body_html = ""
        if body:
            body_html = f'<div class="vti-timeline__card-body">{_esc(body)}</div>'

        # Deliverables list (with checkmarks)
        deliverables_html = ""
        if deliverables:
            li_html = "\n".join(
                f'<li class="vti-timeline__deliverable">{_esc(str(d))}</li>'
                for d in deliverables
            )
            deliverables_html = (
                f'<ul class="vti-timeline__deliverables">{li_html}</ul>'
            )

        # Card
        card_html = (
            f'<div class="vti-timeline__card">'
            f'<div class="vti-timeline__card-head">'
            f'<div class="vti-timeline__card-title">{_esc(title)}</div>'
            f'{metric_html}'
            f'</div>'
            f'{body_html}'
            f'{deliverables_html}'
            f'</div>'
        )

        # Order in DOM matters for CSS positioning:
        #   horizontal: card → dot → date  (card at top, date below)
        #   vertical:   date → dot → card  (date above, dot+card next to each other)
        if orientation == "horizontal":
            events_html.append(
                f'<div class="{cls}">'
                f'{card_html}'
                f'<div class="vti-timeline__dot"></div>'
                f'<div class="vti-timeline__date">{_esc(date)}</div>'
                f'</div>'
            )
        else:
            events_html.append(
                f'<div class="{cls}">'
                f'<div class="vti-timeline__date">{_esc(date)}</div>'
                f'<div class="vti-timeline__dot"></div>'
                f'{card_html}'
                f'</div>'
            )

    return _fill(_component_template("timeline"), {
        "ORIENTATION": orientation,
        "EVENTS_HTML": "\n".join(events_html),
    })


# ---------- funnel ----------------------------------------------------------

# funnel uses the shared VTI chart palette
_FUNNEL_DEFAULT_COLORS = _VTI_CHART_PALETTE


@register_component("funnel", meta={
    "role": "Sequential reduction funnel — each stage narrower than the last "
            "based on its absolute value, with the % drop from previous "
            "(or % of top) shown alongside.",
    "kind": "diagram",
    "good_for": [
        "sales / conversion funnels",
        "qualification pipelines",
        "drop-off analysis",
    ],
    "bad_for": [
        "non-monotonic series (some segments could go up — funnel implies decrease)",
        "more than 6 stages (becomes cramped)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8],
    "natural_height": "1fr or auto with min ~250px",
    "schema_brief":
        "stages: list[{label, value, color?}], "
        "show_pct_of_top?: bool (default true)",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   300,
    "picks_content_kinds": ["funnel", "conversion_funnel"],
})
def _r_funnel(props: dict) -> str:
    stages = _require(props, "stages", "funnel.props")
    if not isinstance(stages, list) or len(stages) < 2:
        raise ValidationError("invalid_value", "funnel.props.stages",
                              "funnel needs at least 2 stages")
    if len(stages) > 6:
        raise ValidationError("invalid_value", "funnel.props.stages",
                              "max 6 stages (>6 becomes cramped)")

    show_pct_of_top = bool(props.get("show_pct_of_top", True))
    n = len(stages)
    seg_height = 60   # px per segment in viewBox
    VB_H = seg_height * n + 20
    max_val = float(stages[0].get("value", 1)) or 1.0
    cx = 200
    max_w = 320

    segments_svg, labels_svg = [], []
    for i, st in enumerate(stages):
        label = str(st.get("label", ""))
        value = float(st.get("value", 0))
        color = st.get("color", _FUNNEL_DEFAULT_COLORS[i % len(_FUNNEL_DEFAULT_COLORS)])

        ratio_top = value / max_val
        next_val = float(stages[i + 1].get("value", value * 0.6)) if i + 1 < n else value * 0.6
        ratio_bot = next_val / max_val

        w_top = max(max_w * ratio_top, 30)
        w_bot = max(max_w * ratio_bot, 24)
        y_top = 10 + i * seg_height
        y_bot = y_top + seg_height - 4   # small gap between segments

        x1 = cx - w_top / 2
        x2 = cx + w_top / 2
        x3 = cx + w_bot / 2
        x4 = cx - w_bot / 2

        segments_svg.append(
            f'<polygon class="vti-funnel__segment" '
            f'points="{x1:.1f},{y_top} {x2:.1f},{y_top} '
            f'{x3:.1f},{y_bot} {x4:.1f},{y_bot}" fill="{color}"/>'
        )

        # Labels (centered)
        cy = (y_top + y_bot) / 2
        pct = (value / max_val * 100) if show_pct_of_top else 100
        labels_svg.append(
            f'<text class="vti-funnel__segment-label" x="{cx}" y="{cy - 12}">'
            f'{_esc(label)}</text>'
        )
        labels_svg.append(
            f'<text class="vti-funnel__segment-value" x="{cx}" y="{cy + 6}">'
            f'{_esc(_fmt_num(value))}</text>'
        )
        if show_pct_of_top:
            labels_svg.append(
                f'<text class="vti-funnel__segment-pct" x="{cx}" y="{cy + 22}">'
                f'{pct:.1f}% of top</text>'
            )

    return _fill(_component_template("funnel"), {
        "VB_H":         str(VB_H),
        "SEGMENTS_SVG": "\n".join(segments_svg),
        "LABELS_SVG":   "\n".join(labels_svg),
    })


# ---------- quadrant-matrix -------------------------------------------------

@register_component("quadrant-matrix", meta={
    "role": "2×2 strategic positioning matrix. Each quadrant has a label and "
            "a list of items. Highlight one quadrant for emphasis (e.g. 'quick wins').",
    "kind": "diagram",
    "good_for": [
        "effort × impact prioritization",
        "BCG growth-share matrix",
        "feasibility × value mapping",
    ],
    "bad_for": [
        "more than 4 categories (use a different chart)",
        "continuous data (use scatter — out of scope)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto (~280-320px)",
    "schema_brief":
        "x_start: str, x_end: str, y_start: str, y_end: str, "
        "quadrants: {tl: {label, items, highlight?}, tr: {...}, "
        "bl: {...}, br: {...}}",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   400,
    "picks_content_kinds": ["quadrant", "matrix_2x2"],
})
def _r_quadrant_matrix(props: dict) -> str:
    x_start = props.get("x_start", "Low")
    x_end   = props.get("x_end",   "High")
    y_start = props.get("y_start", "Low")
    y_end   = props.get("y_end",   "High")
    quads   = _require(props, "quadrants", "quadrant-matrix.props")

    # Render in order tl tr bl br for proper grid placement.
    cells_html = []
    for key in ("tl", "tr", "bl", "br"):
        q = quads.get(key, {})
        label = q.get("label", "")
        items = q.get("items", [])
        highlight = bool(q.get("highlight", False))
        items_html = "".join(
            f'<div class="vti-quadrant__item">{_esc(it)}</div>' for it in items
        )
        cls = ("vti-quadrant__cell vti-quadrant__cell--highlight"
               if highlight else "vti-quadrant__cell")
        cells_html.append(
            f'<div class="{cls}" data-quad="{key}">'
            f'<div class="vti-quadrant__cell-label">{_esc(label)}</div>'
            f'<div class="vti-quadrant__items">{items_html}</div>'
            f'</div>'
        )

    return _fill(_component_template("quadrant-matrix"), {
        "Y_END":      _esc(y_end),
        "Y_START":    _esc(y_start),
        "X_START":    _esc(x_start),
        "X_END":      _esc(x_end),
        "CELLS_HTML": "\n".join(cells_html),
    })


# ===========================================================================
# Phase E3 components — comparison / context
# ===========================================================================

# ---------- comparison-table ------------------------------------------------

_CHECK_ICON = '<svg class="vti-comparison-table__icon vti-comparison-table__icon--check" viewBox="0 0 20 20" fill="currentColor"><path d="M16.7 5.3 L8 14 L3.3 9.3 L4.7 7.9 L8 11.2 L15.3 3.9 Z"/></svg>'
_X_ICON     = '<svg class="vti-comparison-table__icon vti-comparison-table__icon--x" viewBox="0 0 20 20" fill="currentColor"><path d="M14.3 5.7 L11.4 8.6 L14.3 11.4 L12.9 12.9 L10 10 L7.1 12.9 L5.7 11.4 L8.6 8.6 L5.7 5.7 L7.1 4.3 L10 7.1 L12.9 4.3 Z"/></svg>'

_LEVEL_DOTS = {
    "best":   3, "better": 3, "high":   3,
    "good":   2, "ok":     2, "medium": 2,
    "fair":   1, "low":    1, "poor":   1,
}


def _comparison_dots(level: int, max_dots: int = 3) -> str:
    dots = []
    for i in range(max_dots):
        cls = "vti-comparison-table__dot" if i < level else "vti-comparison-table__dot vti-comparison-table__dot--off"
        dots.append(f'<span class="{cls}"></span>')
    return f'<div class="vti-comparison-table__dots">{"".join(dots)}</div>'


@register_component("comparison-table", meta={
    "role": "Feature comparison matrix — distinct from data table. Cells "
            "render booleans as ✓ / ✕ icons, level keywords ('best'/'good'/'fair') "
            "as colored dot indicators, and strings as text. One column can be "
            "highlighted as the 'recommended' option.",
    "kind": "data",
    "good_for": [
        "vendor / option comparison",
        "feature matrix across product tiers",
        "build vs buy decision matrix",
    ],
    "bad_for": [
        "pure numeric tabular data (use table)",
        "single feature deep dive (use bullet-list)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "columns: list[{name, highlight?}] (Option A/B/C — first column "
        "implicitly the feature names), "
        "rows: list[{feature, values: list[bool|str|level_keyword]}]",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 80,
    "picks_content_kinds": ["comparison_table", "feature_matrix"],
})
def _r_comparison_table(props: dict) -> str:
    columns = _require(props, "columns", "comparison-table.props")
    rows    = _require(props, "rows",    "comparison-table.props")
    if len(columns) < 2:
        raise ValidationError("invalid_value", "comparison-table.props.columns",
                              "need at least 2 option columns")

    # First column is feature names (implicit), then option columns
    n_opt = len(columns)
    cols_template = f"minmax(0, 1.4fr) " + " ".join(["minmax(0, 1fr)"] * n_opt)

    # Header
    header_cells = ['<div class="vti-comparison-table__cell vti-comparison-table__cell--feature">Feature</div>']
    for col in columns:
        cls = "vti-comparison-table__cell"
        if col.get("highlight"):
            cls += " vti-comparison-table__cell--highlight"
        header_cells.append(f'<div class="{cls}">{_esc(col.get("name", ""))}</div>')
    header_html = (f'<div class="vti-comparison-table__row vti-comparison-table__row--header">'
                   f'{"".join(header_cells)}</div>')

    # Data rows
    row_htmls = []
    for ri, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError("invalid_type", f"comparison-table.props.rows[{ri}]",
                                  "each row must be a dict")
        feature = row.get("feature", "")
        values  = row.get("values", [])
        cells = [f'<div class="vti-comparison-table__cell vti-comparison-table__cell--feature">{_esc(feature)}</div>']
        for ci, v in enumerate(values[:n_opt]):
            cls = "vti-comparison-table__cell"
            if columns[ci].get("highlight"):
                cls += " vti-comparison-table__cell--highlight"
            if v is True:
                content = _CHECK_ICON
            elif v is False:
                content = _X_ICON
            elif isinstance(v, str) and v.lower() in _LEVEL_DOTS:
                content = _comparison_dots(_LEVEL_DOTS[v.lower()])
            else:
                content = _esc(str(v))
            cells.append(f'<div class="{cls}">{content}</div>')
        # Pad short rows
        while len(cells) - 1 < n_opt:
            cells.append('<div class="vti-comparison-table__cell"></div>')
        row_htmls.append(f'<div class="vti-comparison-table__row">{"".join(cells)}</div>')

    return _fill(_component_template("comparison-table"), {
        "COLS_TEMPLATE": cols_template,
        "HEADER_HTML":   header_html,
        "ROWS_HTML":     "\n".join(row_htmls),
    })


# ---------- callout ---------------------------------------------------------

_VALID_CALLOUT_TONES = {"info", "warn", "tip", "deep"}

_CALLOUT_DEFAULT_ICONS = {
    "info": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
    "warn": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/><path d="M12 9v4M12 17h.01"/></svg>',
    "tip":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6M10 22h4M15.09 14c.18-.98.65-1.74 1.41-2.5C17.5 10.5 18 9.5 18 8a6 6 0 0 0-12 0c0 1.5.5 2.5 1.5 3.5.76.76 1.23 1.52 1.41 2.5"/></svg>',
    "deep": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15 9 22 10 17 15 18 22 12 19 6 22 7 15 2 10 9 9 12 2"/></svg>',
}


@register_component("callout", meta={
    "role": "Emphasized text block (note / warn / tip / deep) with colored "
            "left border + icon + optional title.",
    "kind": "text",
    "good_for": [
        "key takeaway above content",
        "warning / caveat in a slide",
        "tip / best-practice note",
    ],
    "bad_for": [
        "long-form prose (use narrative-paragraph)",
        "decoration without semantic emphasis",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "tone: 'info'|'warn'|'tip'|'deep' (default 'info'), "
        "text: str, title?: str, icon?: str (override default)",
    "font_levels_used":  ["title", "body"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 60,
    "picks_content_kinds": ["callout", "note", "warning", "tip"],
})
def _r_callout(props: dict) -> str:
    tone = props.get("tone", "info")
    if tone not in _VALID_CALLOUT_TONES:
        raise ValidationError("invalid_value", "callout.props.tone",
                              f"must be one of {sorted(_VALID_CALLOUT_TONES)}")
    text  = _require(props, "text", "callout.props")
    title = props.get("title", "")
    icon  = props.get("icon", "")
    icon_svg = render_icon(icon) or _CALLOUT_DEFAULT_ICONS[tone]

    title_html = ""
    if title:
        title_html = f'<div class="vti-callout__title">{_esc(title)}</div>'

    return _fill(_component_template("callout"), {
        "TONE":       tone,
        "ICON_SVG":   icon_svg,
        "TITLE_HTML": title_html,
        "TEXT":       _esc(text),
    })


# ---------- before-after ----------------------------------------------------

@register_component("before-after", meta={
    "role": "Two-panel split with arrow between — left = before state "
            "(gray), right = after state (blue accent). Use for transformation, "
            "migration outcomes, problem→solution narratives.",
    "kind": "comparison",
    "good_for": [
        "before/after of a transformation",
        "manual vs automated process comparison",
    ],
    "bad_for": [
        "more than 2 states (use comparison-table)",
        "non-temporal comparison (use side-by-side narrative)",
    ],
    "best_col_spans": [8, 10, 12],
    "natural_height": "auto",
    "schema_brief":
        "before: {label?, title, items: list[str]}, "
        "after:  {label?, title, items: list[str]}",
    "font_levels_used":  ["title", "body"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   500,
    "picks_content_kinds": ["before_after", "transformation"],
})
def _r_before_after(props: dict) -> str:
    before = _require(props, "before", "before-after.props")
    after  = _require(props, "after",  "before-after.props")

    def _items_html(items):
        return "\n".join(f'<li>{_esc(it)}</li>' for it in (items or []))

    return _fill(_component_template("before-after"), {
        "BEFORE_LABEL": _esc(before.get("label", "Before")),
        "BEFORE_TITLE": _esc(before.get("title", "")),
        "BEFORE_ITEMS": _items_html(before.get("items", [])),
        "AFTER_LABEL":  _esc(after.get("label", "After")),
        "AFTER_TITLE":  _esc(after.get("title", "")),
        "AFTER_ITEMS":  _items_html(after.get("items", [])),
    })


# ---------- vs-compare ------------------------------------------------------

@register_component("vs-compare", meta={
    "role": "Two-panel storytelling comparison with VS badge between — each "
            "panel = kicker label + narrative paragraph + check/x bullet list. "
            "Use for problem↔solution, pull↔push, manual↔automated, on-demand"
            "↔scheduled. Composite of kicker + narrative-paragraph + "
            "bullet-list-checked + vs-divider (vertical).",
    "kind": "comparison",
    "good_for": [
        "problem vs solution storytelling",
        "pull vs push, manual vs automated",
        "before-state with explanation + after-state with explanation",
    ],
    "bad_for": [
        "purely temporal before→after (use before-after — has arrow)",
        "more than 2 sides (use comparison-table)",
        "short labels only without prose (use comparison-table)",
    ],
    "best_col_spans": [10, 12],
    "natural_height": "auto",
    "schema_brief":
        "left: {label: str≤40, narrative: str≤500, items: list[str≤100] (2-6)}, "
        "right: {label: str≤40, narrative: str≤500, items: list[str≤100] (2-6)}, "
        "left_marker?: 'check'|'x' (default 'x'), "
        "right_marker?: 'check'|'x' (default 'check'), "
        "vs_label?: str≤6 (default 'VS'), "
        "line_style?: 'dashed'|'solid' (default 'dashed')",
    "font_levels_used":  ["caption", "body"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   1200,
    "picks_content_kinds": ["vs_compare", "comparison_story"],
})
def _r_vs_compare(props: dict) -> str:
    left  = _require(props, "left",  "vs-compare.props")
    right = _require(props, "right", "vs-compare.props")

    def _panel_blocks(side: dict, where: str, marker: str) -> tuple[str, str, str]:
        label     = _require(side, "label",     f"vs-compare.props.{where}")
        narrative = _require(side, "narrative", f"vs-compare.props.{where}")
        items     = _require(side, "items",     f"vs-compare.props.{where}")
        _check_max_chars(label,     40,  f"vs-compare.props.{where}.label")
        _check_max_chars(narrative, 500, f"vs-compare.props.{where}.narrative")
        if not isinstance(items, list) or not (2 <= len(items) <= 6):
            raise ValidationError("invalid_count",
                                  f"vs-compare.props.{where}.items",
                                  f"must have 2-6 items, got {len(items) if isinstance(items, list) else type(items).__name__}")
        # Use render_component() (not _r_*) so transitive component usage
        # is tracked in _USED_COMPONENTS_THIS_RENDER and the inner CSS
        # (kicker / narrative-paragraph / bullet-list-checked) gets
        # bundled into the deck. Bypassing the wrapper left those CSS
        # chunks out, so SVG bullets rendered at browser default (~300px).
        kicker_html = render_component(
            "kicker", {"text": label, "rule": True, "align": "left"}
        )
        narrative_html = render_component(
            "narrative-paragraph", {"paragraphs": [narrative]}
        )
        bullets_html = render_component("bullet-list-checked", {
            "items":   items,
            "density": "default",
            "marker":  marker,
        })
        return kicker_html, narrative_html, bullets_html

    left_marker  = props.get("left_marker",  "x")
    right_marker = props.get("right_marker", "check")
    if left_marker not in ("check", "x"):
        raise ValidationError("invalid_value", "vs-compare.props.left_marker",
                              "must be 'check' or 'x'")
    if right_marker not in ("check", "x"):
        raise ValidationError("invalid_value", "vs-compare.props.right_marker",
                              "must be 'check' or 'x'")

    l_kicker, l_narr, l_bullets = _panel_blocks(left,  "left",  left_marker)
    r_kicker, r_narr, r_bullets = _panel_blocks(right, "right", right_marker)

    divider_html = render_component("vs-divider", {
        "label":       props.get("vs_label", "VS"),
        "has_line":    True,
        "line_style":  props.get("line_style", "dashed"),
        "orientation": "vertical",
    })

    return _fill(_component_template("vs-compare"), {
        "LEFT_KICKER_HTML":     l_kicker,
        "LEFT_NARRATIVE_HTML":  l_narr,
        "LEFT_BULLETS_HTML":    l_bullets,
        "DIVIDER_HTML":         divider_html,
        "RIGHT_KICKER_HTML":    r_kicker,
        "RIGHT_NARRATIVE_HTML": r_narr,
        "RIGHT_BULLETS_HTML":   r_bullets,
    })


# ---------- icon-list -------------------------------------------------------

_VALID_ICON_LIST_DENSITY = {"compact", "default", "loose"}


@register_component("icon-list", meta={
    "role": "Items each with a custom icon + title + optional body text. "
            "Richer than bullet-list-checked — use when each item warrants "
            "its own visual identity.",
    "kind": "text",
    "good_for": [
        "feature list with capability icons",
        "value-add bullets with thematic icons",
        "service catalog rows",
    ],
    "bad_for": [
        "homogeneous bullets (use bullet-list-checked)",
        "single item (use callout)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "auto",
    "schema_brief":
        "items: list[{icon, title, body?}], "
        "density?: 'compact'|'default'|'loose' (default 'default'), "
        "icon_style?: 'plain'|'circle' (default 'plain')",
    "font_levels_used":  ["title", "body"],
    "font_weights_used": [400, 500],
    "capacity_chars_per_col": 50,
    "picks_content_kinds": ["icon_list", "feature_list"],
})
def _r_icon_list(props: dict) -> str:
    items = _require(props, "items", "icon-list.props")
    if not isinstance(items, list) or not items:
        raise ValidationError("missing_required", "icon-list.props.items",
                              "items must be a non-empty list")
    density = props.get("density", "default")
    if density not in _VALID_ICON_LIST_DENSITY:
        raise ValidationError("invalid_value", "icon-list.props.density",
                              f"must be one of {sorted(_VALID_ICON_LIST_DENSITY)}")
    icon_style = props.get("icon_style", "plain")
    icon_cls = "vti-icon-list__icon"
    if icon_style == "circle":
        icon_cls += " vti-icon-list__icon--circle"

    items_html = []
    for i, it in enumerate(items):
        icon  = it.get("icon", "")
        title = it.get("title", "")
        body  = it.get("body", "")
        icon_svg = render_icon(icon) if icon else ""
        body_html = f'<div class="vti-icon-list__body">{_esc(body)}</div>' if body else ""
        items_html.append(
            f'<div class="vti-icon-list__item">'
            f'<div class="{icon_cls}">{icon_svg}</div>'
            f'<div class="vti-icon-list__content">'
            f'<div class="vti-icon-list__title">{_esc(title)}</div>'
            f'{body_html}</div></div>'
        )

    return _fill(_component_template("icon-list"), {
        "DENSITY":    density,
        "ITEMS_HTML": "\n".join(items_html),
    })


# ===========================================================================
# Phase E4 components — numbers / progress
# ===========================================================================

# ---------- progress-bar ----------------------------------------------------

_VALID_PROGRESS_TONES = {"deep", "medium", "sky", "navy", "success", "warning"}


@register_component("progress-bar", meta={
    "role": "One or more horizontal % completion bars with label + value. "
            "Multi-bar mode shows several metrics stacked.",
    "kind": "data",
    "good_for": [
        "migration / rollout progress dashboards",
        "OKR / goal tracking with multiple KRs",
        "capability maturity ratings",
    ],
    "bad_for": [
        "single static stat (use stat-mini)",
        "categorical comparison (use bar-chart)",
    ],
    "best_col_spans": [4, 5, 6, 7, 8, 12],
    "natural_height": "auto",
    "schema_brief":
        "items: list[{label, value, max?, tone?, value_text?}], "
        "(value is 0-100 or 0-max if max specified)",
    "font_levels_used":  ["body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   80,
    "picks_content_kinds": ["progress_bar", "progress_bars", "okr_tracker"],
})
def _r_progress_bar(props: dict) -> str:
    items = _require(props, "items", "progress-bar.props")
    if not isinstance(items, list) or not items:
        raise ValidationError("missing_required", "progress-bar.props.items",
                              "items must be a non-empty list")

    bars_html = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            raise ValidationError("invalid_type", f"progress-bar.props.items[{i}]",
                                  "each item must be a dict")
        label = it.get("label", "")
        value = float(it.get("value", 0))
        max_v = float(it.get("max", 100))
        tone  = it.get("tone", "deep")
        value_text = it.get("value_text", "")
        if tone not in _VALID_PROGRESS_TONES:
            raise ValidationError("invalid_value",
                                  f"progress-bar.props.items[{i}].tone",
                                  f"must be one of {sorted(_VALID_PROGRESS_TONES)}")
        pct = max(0.0, min(100.0, value / max_v * 100.0))
        if not value_text:
            value_text = f"{pct:.0f}%"
        bars_html.append(
            f'<div class="vti-progress-bar vti-progress-bar--{tone}">'
            f'<div class="vti-progress-bar__row">'
            f'<span class="vti-progress-bar__label">{_esc(label)}</span>'
            f'<span class="vti-progress-bar__value">{_esc(value_text)}</span>'
            f'</div>'
            f'<div class="vti-progress-bar__track">'
            f'<div class="vti-progress-bar__fill" style="width: {pct:.1f}%;"></div>'
            f'</div></div>'
        )

    return _fill(_component_template("progress-bar"), {
        "BARS_HTML": "\n".join(bars_html),
    })


# ---------- gauge-dial ------------------------------------------------------

_VALID_GAUGE_TONES = {"deep", "medium", "sky", "navy", "success", "warning"}


@register_component("gauge-dial", meta={
    "role": "Semicircular gauge showing a single metric with min/max "
            "endpoints and a color-coded fill arc. Center text shows current "
            "value + suffix (e.g. '/100', '%').",
    "kind": "data",
    "good_for": [
        "CSAT / NPS scoreboard",
        "single-metric headline (target progress)",
        "service health summary",
    ],
    "bad_for": [
        "multi-metric comparison (use kpi-row)",
        "non-bounded values (use stat-hero)",
    ],
    "best_col_spans": [3, 4, 5, 6],
    "natural_height": "auto (~160-200px)",
    "schema_brief":
        "value: number, max?: number (default 100), "
        "value_text?: str (display override), suffix?: str (default '/100'), "
        "label?: str, tone?: 'deep'|'medium'|'sky'|'navy'|'success'|'warning'",
    "font_levels_used":  ["hero", "caption"],
    "font_weights_used": [400, 600],
    "capacity_chars_fixed":   40,
    "picks_content_kinds": ["gauge", "gauge_dial"],
})
def _r_gauge_dial(props: dict) -> str:
    value = float(_require(props, "value", "gauge-dial.props"))
    max_v = float(props.get("max", 100))
    if max_v <= 0:
        raise ValidationError("invalid_value", "gauge-dial.props.max",
                              "max must be positive")
    tone  = props.get("tone", "deep")
    if tone not in _VALID_GAUGE_TONES:
        raise ValidationError("invalid_value", "gauge-dial.props.tone",
                              f"must be one of {sorted(_VALID_GAUGE_TONES)}")
    suffix     = props.get("suffix", f"/ {int(max_v)}" if max_v != 100 else "")
    label      = props.get("label", "")
    value_text = str(props.get("value_text", _fmt_num(value)))

    # Arc math: center (100, 110), radius 80. Track from (20, 110) → (180, 110)
    # going through top. For value v, fill arc goes from (20, 110) clockwise
    # (sweep_flag=1) through the top to end point at angle 180°-t*180°.
    t = max(0.0, min(1.0, value / max_v))
    if t < 0.001:
        fill_path = "M 20 110"   # degenerate — just a point
    else:
        end_angle_deg = 180 - t * 180
        end_angle_rad = _math.radians(end_angle_deg)
        x_end = 100 + 80 * _math.cos(end_angle_rad)
        y_end = 110 - 80 * _math.sin(end_angle_rad)
        large = 0   # always less than 180° for values 0-1 of t
        fill_path = f"M 20 110 A 80 80 0 {large} 1 {x_end:.2f} {y_end:.2f}"

    label_html = ""
    if label:
        label_html = f'<div class="vti-gauge__label">{_esc(label)}</div>'

    out = _fill(_component_template("gauge-dial"), {
        "FILL_PATH":  fill_path,
        "VALUE_TEXT": _esc(value_text),
        "SUFFIX":     _esc(suffix),
        "LABEL_HTML": label_html,
    })
    # Add tone class to root element
    out = out.replace('class="vti-gauge"',
                      f'class="vti-gauge vti-gauge--{tone}"', 1)
    return out


# ---------- stacked-bar -----------------------------------------------------

# stacked-bar uses the shared VTI chart palette
_STACKED_DEFAULT_COLORS = _VTI_CHART_PALETTE


@register_component("stacked-bar", meta={
    "role": "Multi-series stacked bar chart. Each category (x-axis) shows "
            "a single bar made of stacked segments (one per series).",
    "kind": "data",
    "good_for": [
        "revenue mix over quarters",
        "headcount composition by region over years",
        "any composition-over-categories pattern",
    ],
    "bad_for": [
        "single series (use bar-chart)",
        "trend over time without composition (use line-chart)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "1fr or auto with min ~250px",
    "schema_brief":
        "categories: list[str], "
        "series: list[{name, color?, values: list[number]}], "
        "title?: str",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   120,
    "picks_content_kinds": ["stacked_bar", "composition_chart"],
})
def _r_stacked_bar(props: dict) -> str:
    categories = _require(props, "categories", "stacked-bar.props")
    series     = _require(props, "series",     "stacked-bar.props")
    if not categories or not series:
        raise ValidationError("missing_required", "stacked-bar.props",
                              "categories and series must both be non-empty")

    n_cat = len(categories)
    # Validate values per series match category count
    for i, s in enumerate(series):
        if len(s.get("values", [])) != n_cat:
            raise ValidationError(
                "invalid_value", f"stacked-bar.props.series[{i}].values",
                f"must have exactly {n_cat} values matching categories",
            )

    # Compute totals per category, find max for scaling
    totals = []
    for ci in range(n_cat):
        totals.append(sum(float(s["values"][ci]) for s in series))
    max_total = max(totals) or 1.0

    VB_W, VB_H = 800, 400
    plot_left, plot_right = 50, 780
    plot_top,  plot_bottom = 30, 340
    plot_w = plot_right - plot_left
    plot_h = plot_bottom - plot_top

    bar_slot = plot_w / n_cat
    bar_w = bar_slot * 0.55

    bars_svg = []
    for ci in range(n_cat):
        x = plot_left + bar_slot * ci + (bar_slot - bar_w) / 2
        y_cursor = plot_bottom
        for si, s in enumerate(series):
            v = float(s["values"][ci])
            color = s.get("color", _STACKED_DEFAULT_COLORS[si % len(_STACKED_DEFAULT_COLORS)])
            seg_h = (v / max_total) * plot_h
            y_cursor -= seg_h
            bars_svg.append(
                f'<rect class="vti-stacked-bar__segment" '
                f'x="{x:.1f}" y="{y_cursor:.1f}" '
                f'width="{bar_w:.1f}" height="{seg_h:.1f}" fill="{color}"/>'
            )

    cat_labels_svg = []
    for ci, label in enumerate(categories):
        x_center = plot_left + bar_slot * ci + bar_slot / 2
        cat_labels_svg.append(
            f'<text class="vti-stacked-bar__cat-label" '
            f'x="{x_center:.1f}" y="{plot_bottom + 22:.1f}">{_esc(label)}</text>'
        )

    axes_svg = (
        f'<line class="vti-stacked-bar__axis-line" '
        f'x1="{plot_left}" y1="{plot_bottom}" '
        f'x2="{plot_right}" y2="{plot_bottom}"/>'
    )

    legend_rows = []
    for si, s in enumerate(series):
        color = s.get("color", _STACKED_DEFAULT_COLORS[si % len(_STACKED_DEFAULT_COLORS)])
        legend_rows.append(
            f'<div class="vti-stacked-bar__legend-row">'
            f'<span class="vti-stacked-bar__swatch" style="background:{color};"></span>'
            f'<span>{_esc(s.get("name", f"Series {si + 1}"))}</span>'
            f'</div>'
        )
    legend_html = f'<div class="vti-stacked-bar__legend">{"".join(legend_rows)}</div>'

    title = props.get("title", "")
    title_html = ""
    if title:
        title_html = f'<div class="vti-stacked-bar__title">{_esc(title)}</div>'

    return _fill(_component_template("stacked-bar"), {
        "TITLE_HTML":     title_html,
        "AXES_SVG":       axes_svg,
        "BARS_SVG":       "\n".join(bars_svg),
        "CAT_LABELS_SVG": "\n".join(cat_labels_svg),
        "LEGEND_HTML":    legend_html,
    })


# ---------- line-chart ------------------------------------------------------

@register_component("line-chart", meta={
    "role": "Single-series line chart for trend over time. Optional area "
            "fill below the line, optional dot markers + value labels at "
            "each point.",
    "kind": "data",
    "good_for": [
        "trend over time (revenue, signups, traffic)",
        "delta-from-target tracking",
    ],
    "bad_for": [
        "categorical comparison (use bar-chart)",
        "composition (use stacked-bar)",
        "very few data points <3 (use trend-stat)",
    ],
    "best_col_spans": [6, 7, 8, 10, 12],
    "natural_height": "1fr or auto with min ~200px",
    "schema_brief":
        "items: list[{label, value}], "
        "area_fill?: bool (default true), "
        "show_dots?: bool (default true), "
        "show_values?: bool (default false), "
        "title?: str",
    "font_levels_used":  ["title", "body", "caption"],
    "font_weights_used": [400, 500],
    "capacity_chars_fixed":   120,
    "picks_content_kinds": ["line_chart", "trend_chart"],
})
def _r_line_chart(props: dict) -> str:
    items = _require(props, "items", "line-chart.props")
    if not isinstance(items, list) or len(items) < 2:
        raise ValidationError("invalid_value", "line-chart.props.items",
                              "line-chart needs at least 2 points")

    area_fill   = bool(props.get("area_fill", True))
    show_dots   = bool(props.get("show_dots", True))
    show_values = bool(props.get("show_values", False))
    title       = props.get("title", "")

    n = len(items)
    values = [float(it.get("value", 0)) for it in items]
    max_v = max(values) or 1.0

    plot_left, plot_right = 60, 770
    plot_top,  plot_bottom = 30, 340
    plot_w = plot_right - plot_left
    plot_h = plot_bottom - plot_top

    pts = []
    for i, v in enumerate(values):
        x = plot_left + (i / max(1, n - 1)) * plot_w
        y = plot_bottom - (v / max_v) * plot_h
        pts.append((x, y))

    line_d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    line_svg = f'<path class="vti-line-chart__line" d="{line_d}"/>'

    area_svg = ""
    if area_fill:
        area_d = (f"M {pts[0][0]:.1f} {plot_bottom} "
                  + " ".join(f"L {x:.1f} {y:.1f}" for x, y in pts)
                  + f" L {pts[-1][0]:.1f} {plot_bottom} Z")
        area_svg = f'<path class="vti-line-chart__area" d="{area_d}"/>'

    dots_svg = []
    if show_dots:
        for x, y in pts:
            dots_svg.append(f'<circle class="vti-line-chart__dot" '
                            f'cx="{x:.1f}" cy="{y:.1f}" r="4"/>')

    value_labels_svg = []
    if show_values:
        for (x, y), v in zip(pts, values):
            value_labels_svg.append(
                f'<text class="vti-line-chart__value-label" '
                f'x="{x:.1f}" y="{y - 12:.1f}">{_esc(_fmt_num(v))}</text>'
            )

    cat_labels_svg = []
    for i, it in enumerate(items):
        x = plot_left + (i / max(1, n - 1)) * plot_w
        cat_labels_svg.append(
            f'<text class="vti-line-chart__cat-label" '
            f'x="{x:.1f}" y="{plot_bottom + 22:.1f}">'
            f'{_esc(it.get("label", ""))}</text>'
        )

    axes_svg = (f'<line class="vti-line-chart__axis-line" '
                f'x1="{plot_left}" y1="{plot_bottom}" '
                f'x2="{plot_right}" y2="{plot_bottom}"/>')

    title_html = ""
    if title:
        title_html = f'<div class="vti-line-chart__title">{_esc(title)}</div>'

    return _fill(_component_template("line-chart"), {
        "TITLE_HTML":       title_html,
        "AXES_SVG":         axes_svg,
        "AREA_SVG":         area_svg,
        "LINE_SVG":         line_svg,
        "DOTS_SVG":         "\n".join(dots_svg),
        "VALUE_LABELS_SVG": "\n".join(value_labels_svg),
        "CAT_LABELS_SVG":   "\n".join(cat_labels_svg),
    })


# ---------------------------------------------------------------------------
# Chrome rendering — preserved from v2
# ---------------------------------------------------------------------------
_LOGO_MARKER_RE = re.compile(r'<!--\s*VTI_LOGO_INJECT\s+([^>]+?)-->')


def _resolve_logo_markers(html: str) -> str:
    """Replace VTI_LOGO_INJECT comment markers with embedded data-URL <img>.

    Two distinct injection paths, decided by the marker's `position`:

      • `position="top-right"` — used only in `chrome/header.html`, where
        the marker sits inside the bare `<header class="hdr">` with no
        positioning wrapper. The injected IMG must carry `class="logo-tr"`
        so chrome/header.css absolutely positions it (top:24px right:60px).

      • Everything else (`cover-top`, `toc-top-left`, `contact-photo`,
        `bottom-left`, …) — used only inside special-page templates,
        where each marker lives inside a wrapper <div> whose CSS already
        owns positioning (`.cv-logo-row` flex-centers, `.toc-mesh-logo`
        absolute top-left, `.ct-logo-tr` / `.ct-logo-bl` absolute, etc.).
        Adding a class here would FIGHT the wrapper:
          - flex centering overridden by `position: absolute` →
            cover & closing logos jump to slide top-right corner
          - two stacked absolutes compound offsets →
            contact white logo "falls" off the photo
          - top-left wrapper shoved to top-right →
            TOC logo on the wrong side of the mesh
        These cases inject a PLAIN <img> with no positioning class; the
        wrapper alone owns layout.

    `chrome/header.css` only defines `.logo-tr` — there are no `.logo-tl`,
    `.logo-bl`, or `.logo-br` classes (verified). And the chrome HTML
    only emits `position="top-right"`. So matching exactly that one
    string is correct and complete; any future chrome positions would
    need new chrome CSS classes regardless.
    """
    def _replace(m: re.Match) -> str:
        attrs = m.group(1)
        variant_m  = re.search(r'variant="([^"]+)"',  attrs)
        size_m     = re.search(r'size="([^"]+)"',     attrs)
        position_m = re.search(r'position="([^"]+)"', attrs)

        variant  = variant_m.group(1)  if variant_m  else "full-color"
        size     = size_m.group(1)     if size_m     else "110px"
        position = position_m.group(1) if position_m else "top-right"

        # 'full-color' / 'colour' / blue → blue logo. White or light → white.
        is_white = "white" in variant or "light" in variant
        logo_file = "logo-vti-apac-white.png" if is_white else "logo-vti-apac-blue.png"
        logo_path = ASSETS_DIR / logo_file
        if not logo_path.exists():
            return ""

        b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        src_attr = f'src="data:image/png;base64,{b64}"'

        if position == "top-right":
            # Chrome context: img owns its absolute positioning via class.
            return (f'<img class="logo-tr" {src_attr} alt="VTI APAC" '
                    f'style="width:{size};height:auto;">')

        # Special-page context: parent wrapper owns positioning.
        # Plain img — no class — so wrapper flex/absolute rules win.
        return (f'<img {src_attr} alt="VTI APAC" '
                f'style="width:{size};height:auto;display:block;">')

    return _LOGO_MARKER_RE.sub(_replace, html)


def _render_chrome(slide_meta: dict,
                   logo_variant: str = "full-color") -> tuple[str, str, str]:
    """Return (header_html, footer_html, chrome_css) for one slide.

    Args:
        slide_meta:   the standard slide_meta dict (section_name, slide_title,
                      page_number, doc_title, copyright_year).
        logo_variant: variant for the chrome top-right logo marker. Defaults
                      to ``"full-color"`` (the unchanged behaviour for content
                      slides). Pass ``"full-white"`` for case-study slides
                      whose dark sidebar sits behind the logo, so a single
                      ``.logo-tr`` element renders at the standard chrome
                      size on every slide — no parallel sidebar logo.
    """
    header_tpl = _read_file(CHROME_DIR / "header.html")
    footer_tpl = _read_file(CHROME_DIR / "footer.html")
    header_css = _read_file(CHROME_DIR / "header.css")
    footer_css = _read_file(CHROME_DIR / "footer.css")

    # Override the chrome marker's variant if requested. This is a string
    # substitution on the template before logo resolution, so every other
    # aspect (size, position, classes) stays identical to the baseline
    # chrome treatment used by every content slide.
    if logo_variant != "full-color":
        header_tpl = header_tpl.replace(
            'variant="full-color"',
            f'variant="{logo_variant}"',
        )

    section_raw = (slide_meta.get("section_name") or "").upper()
    slide_title = (slide_meta.get("slide_title") or "").upper()
    page_num   = int(slide_meta.get("page_number") or 0)
    doc_title  = slide_meta.get("doc_title") or ""
    cy         = slide_meta.get("copyright_year") or 2026

    # Breadcrumb HTML — supports two patterns:
    #   1) section only:        "ABOUT VTI"
    #   2) section + title:     "ABOUT VTI | OUR PRACTICES"
    # The chrome CSS has .bc-section + .bc-sep + .bc-title classes that
    # render the title in heavier weight than the section.
    if slide_title and section_raw:
        breadcrumb_html = (
            f'<span class="bc-section">{_esc(section_raw)}</span>'
            f'<span class="bc-sep"> | </span>'
            f'<span class="bc-title">{_esc(slide_title)}</span>'
        )
    elif slide_title:
        breadcrumb_html = (
            f'<span class="bc-title">{_esc(slide_title)}</span>'
        )
    else:
        breadcrumb_html = _esc(section_raw)

    header_html = _fill(header_tpl, {"BREADCRUMB": breadcrumb_html})
    header_html = _resolve_logo_markers(header_html)

    footer_html = _fill(footer_tpl, {
        "PAGE_NUM":       f"{page_num:02d}",
        "DOC_TITLE":      _esc(doc_title),
        "COPYRIGHT_YEAR": _esc(cy),
    })
    footer_html = _resolve_logo_markers(footer_html)

    chrome_css = "\n".join([header_css, footer_css])
    return header_html, footer_html, chrome_css


# ---------------------------------------------------------------------------
# Grid renderer
# ---------------------------------------------------------------------------
_GRID_CSS = """
/* ------------------------------------------------------------------
 * v3 slide canvas + grid
 * ------------------------------------------------------------------ */
.slide.layout-grid {
  position: relative;
  width: 1280px;
  height: 720px;
  background: #FFFFFF;
  overflow: hidden;
  font-family: var(--vti-font-body, 'Inter', sans-serif);
  color: var(--vti-ink, #2C2C2A);
  box-sizing: border-box;
}
.layout-grid .vti-slide-content {
  position: absolute;
  top: 70px;
  left: 56px;
  right: 56px;
  bottom: 64px;
  display: flex;
  flex-direction: column;
}
.layout-grid .vti-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  flex: 1;
  width: 100%;
  height: 100%;
  gap: 18px;
  /* Prevent auto rows from stretching when the grid container is taller
   * than the sum of natural row heights. Extra space goes to the bottom.
   * Authors who want stretching should use 1fr rows explicitly.
   */
  align-content: start;
}
/* v3.13.8 — opt-in vertical centering for sparse slides.
 * Set slide_meta.vertical_align = "center" to distribute leftover space
 * above + below content instead of dumping it all at the bottom.
 */
.layout-grid .vti-grid--center { align-content: center; }
.layout-grid .vti-grid-cell {
  display: flex;
  align-items: stretch;
  justify-content: stretch;
  min-width: 0;     /* prevents grid blowout from long content */
  min-height: 0;
}
/* v3.13.9 — ensure the single component inside each grid-cell fills the
 * cell's width. `justify-content: stretch` on the flex parent is not a
 * valid flexbox value, so without this rule a content-width child (e.g.
 * .vti-callout, .vti-tags) only takes the width of its inline content
 * even when the cell spans 12 columns. Width-stretchers like
 * .vti-practice-card / .vti-stat-mini already self-set width:100% so
 * they're unaffected; this just covers the gap for components that
 * don't.
 */
.layout-grid .vti-grid-cell > * { width: 100%; }
"""


def _validate_cell(cell: dict, where: str) -> None:
    col_start = cell.get("col_start", 1)
    col_span  = cell.get("col_span", 12)
    row_span  = cell.get("row_span", 1)
    component = cell.get("component", "")
    if not component:
        raise ValidationError("missing_required", f"{where}.component")
    if not isinstance(col_start, int) or not (1 <= col_start <= 12):
        raise ValidationError("invalid_value", f"{where}.col_start",
                              "must be int 1..12")
    if not isinstance(col_span, int) or not (1 <= col_span <= 12):
        raise ValidationError("invalid_value", f"{where}.col_span",
                              "must be int 1..12")
    if col_start + col_span - 1 > 12:
        raise ValidationError(
            "out_of_bounds", f"{where}.col_span",
            f"col_start({col_start}) + col_span({col_span}) - 1 = "
            f"{col_start + col_span - 1} exceeds 12-col grid",
        )
    if not isinstance(row_span, int) or row_span < 1 or row_span > 8:
        raise ValidationError("invalid_value", f"{where}.row_span",
                              "must be int 1..8 (default 1)")


# ---------------------------------------------------------------------------
# v3.5 — Pre-render validators (Gap A / B / C / D from baseline v3.4)
#
# These run during _compose_grid_body and populate the `warnings` list
# returned in slide metadata. They DO NOT raise — backward compatible.
# Callers (creator skill, audit tooling) can read warnings post-render.
# ---------------------------------------------------------------------------

# T1 5-level type scale (from tokens.css). Used by Gap C aggregator.
_TYPE_LEVELS = {"hero", "display", "title", "body", "caption"}
_WEIGHT_VALUES = {400, 500, 600}

# v3.10 — Per-layout-class budgets. Slides can declare layout_class to
# opt into relaxed thresholds. Default is the strict T1/T2/T3 contract;
# case-study allows hero+title+body+caption (4 levels) and weight 600
# alongside 400+500 (3 weights), reflecting that hero stat anchors
# legitimately need more visual hierarchy on case-study layouts.
_LAYOUT_BUDGETS = {
    "default": {
        "max_type_levels":   3,   # T1 — 3 levels visible per slide
        "max_non_600_weights": 2, # T2 — 400 + 500
        "allow_600_anchor":  True,
    },
    "case-study": {
        "max_type_levels":   4,   # hero + title + body + caption
        "max_non_600_weights": 2,
        "allow_600_anchor":  True,
    },
    "data-dense": {
        "max_type_levels":   4,   # display + title + body + caption (e.g. Why-VTI)
        "max_non_600_weights": 2,
        "allow_600_anchor":  True,
    },
}

def _validate_col_span(component: str, col_span: int, where: str) -> str | None:
    """Gap A — col_span ∉ best_col_spans → warning string (or None)."""
    meta = _COMPONENT_META.get(component, {})
    best = meta.get("best_col_spans") or []
    if best and col_span not in best:
        return (
            f"[gap-A col-span] {where}: '{component}' col_span={col_span} "
            f"not in best_col_spans={best}; layout may overflow or look thin"
        )
    return None


def _validate_1fr_row(row: dict, ri: int, where_prefix: str) -> str | None:
    """Gap B — `1fr` row without `_fill_verified` flag → warning."""
    height = str(row.get("height", "auto"))
    if height != "1fr":
        return None
    if row.get("_fill_verified") is True:
        return None
    return (
        f"[gap-B 1fr-fill] {where_prefix}[{ri}]: row uses height='1fr' "
        f"without _fill_verified=True. Per T7/P7, default is 'auto'; "
        f"use '1fr' only when content fill ≥70% has been verified."
    )


def _aggregate_type_budget(rows: list, where_prefix: str,
                            layout_class: str = "default") -> list[str]:
    """Gap C — aggregate font_levels_used / font_weights_used across all
    components on a slide. Emit warning when per-slide budget exceeded.

    Components that don't declare font_levels_used / font_weights_used are
    skipped (opt-in coverage). This is a soft pre-check that complements
    the post-render audit_typography.py.

    v3.10 — applies per-layout-class budgets. layout_class='case-study'
    relaxes type-levels 3→4 (allows hero+title+body+caption); 'data-dense'
    similarly relaxes for display+title+body+caption (Why-VTI / TOC).
    Default keeps strict T1/T2/T3 contract.
    """
    warnings: list[str] = []
    levels_seen: set[str] = set()
    weights_seen: set[int] = set()
    declared_count = 0
    total_components = 0

    budget = _LAYOUT_BUDGETS.get(layout_class, _LAYOUT_BUDGETS["default"])

    for row in rows:
        for cell in row.get("cells", []):
            comp = cell.get("component")
            if not comp:
                continue
            total_components += 1
            meta = _COMPONENT_META.get(comp, {})
            lv = meta.get("font_levels_used")
            wt = meta.get("font_weights_used")
            if lv or wt:
                declared_count += 1
            if lv:
                for x in lv:
                    if x in _TYPE_LEVELS:
                        levels_seen.add(x)
            if wt:
                for x in wt:
                    if x in _WEIGHT_VALUES:
                        weights_seen.add(x)

    # Per-slide budget per T1/T2/T3 (from page-builder SKILL.md):
    # max N type levels visible per layout_class, max 2 weights default
    # + 600 on hero/display.
    max_levels = budget["max_type_levels"]
    if len(levels_seen) > max_levels:
        warnings.append(
            f"[gap-C type-budget] {where_prefix}: {len(levels_seen)} type "
            f"levels declared ({sorted(levels_seen)}); layout_class="
            f"'{layout_class}' allows max {max_levels}. Add chrome (~1 level) "
            f"makes this likely {max_levels + 1}+."
        )
    # T2: 600 is permitted only when paired with hero or display level.
    has_anchor = ("hero" in levels_seen) or ("display" in levels_seen)
    non_600_weights = weights_seen - {600}
    weight_violation = (
        (600 in weights_seen and not has_anchor and not budget["allow_600_anchor"]) or
        (len(non_600_weights) > budget["max_non_600_weights"])
    )
    if weight_violation:
        explain = "T2: max 2 weights (400/500); 600 only when hero or display is on slide."
        warnings.append(
            f"[gap-C weight-budget] {where_prefix}: weights={sorted(weights_seen)}, "
            f"hero_or_display={has_anchor}, layout_class='{layout_class}'. {explain}"
        )
    # Coverage diagnostic (informational, not budget violation)
    if total_components > 0 and declared_count == 0:
        # No component declared font metadata; we couldn't check at all.
        # Don't emit a warning — back-compat. The post-render audit will
        # still catch it.
        pass
    return warnings


def _drain_esc_warnings(where_prefix: str) -> list[str]:
    """Gap D — convert collected pre-escape detections into proper
    warning strings. Drains _LAST_ESC_WARNINGS list."""
    out = []
    if _LAST_ESC_WARNINGS:
        for snippet in _LAST_ESC_WARNINGS:
            out.append(
                f"[gap-D pre-escaped] {where_prefix}: source string contains "
                f"literal HTML entity ({snippet!r}…). Use plain Unicode in "
                f"schema values; composer auto-escapes via _esc()."
            )
        _LAST_ESC_WARNINGS.clear()
    return out


# ---------------------------------------------------------------------------
# v3.7 — Capacity-fill projection (Gap E from baseline v3.6 v3.7-candidates)
#
# Closes the loop on P6 v3.4: composer estimates actual chars in props vs
# component capacity, surfaces sparse cells / dishonest _fill_verified
# declarations / sparse slides.
# ---------------------------------------------------------------------------

def _walk_chars(obj: Any) -> int:
    """Recursively count chars in all string leaves of a props dict.
    Used by capacity-fill projection to estimate actual content density.

    v3.8: skip data URIs and binary-image paths so embedded images don't
    inflate fill estimates.
    """
    if obj is None or isinstance(obj, bool):
        return 0
    if isinstance(obj, str):
        # Skip data URIs (base64-embedded images often 30-60K chars)
        if obj.startswith("data:"):
            return 0
        # Skip obvious image filenames (low signal-to-noise for capacity)
        low = obj.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            return 0
        return len(obj)
    if isinstance(obj, (int, float)):
        return len(str(obj))
    if isinstance(obj, list):
        return sum(_walk_chars(x) for x in obj)
    if isinstance(obj, dict):
        return sum(_walk_chars(v) for v in obj.values())
    return 0


def _component_capacity(comp_name: str, col_span: int, props: dict | None = None) -> int:
    """Return projected char capacity for a component at the given col_span.

    Reads `capacity_chars_per_col` (linear scaling) or `capacity_chars_fixed`
    (fixed-structure component, ignores col_span). Returns 0 if unknown
    (component opts out of capacity check).

    v3.9 — narrative-paragraph gets dynamic capacity inferred from props:
    - intro pattern (col_span >= 10, 1 paragraph, <300 chars total) →
      reduced capacity 35/col so a one-line intro at col-12 doesn't
      register as "sparse" (a tiny intro IS the right content there).
    - main body (col_span <= 8 or multi-paragraph) → keeps 80/col.
    """
    meta = _COMPONENT_META.get(comp_name, {})

    # v3.9 — narrative-paragraph dynamic capacity based on usage role
    if comp_name == "narrative-paragraph" and props is not None:
        paragraphs = props.get("paragraphs") or []
        total_chars = sum(len(str(p)) for p in paragraphs)
        is_intro = (
            col_span >= 10
            and len(paragraphs) <= 1
            and total_chars < 300
        )
        if is_intro:
            return col_span * 35   # intro mode — short single para at wide col
        # otherwise fall through to default per_col

    # v3.10 — callout dynamic capacity. When callout is used as a wide
    # pull-out anchor (col 12, body < 200 chars), the planner is using it
    # as a short emphasis bar — use lower capacity. Standard sidebar
    # callout (col 4-6 with full body) keeps default 60/col.
    if comp_name == "callout" and props is not None:
        body_text = str(props.get("text", "") or props.get("body", ""))
        title_text = str(props.get("title", ""))
        total = len(body_text) + len(title_text)
        is_pullout = col_span >= 10 and total < 200
        if is_pullout:
            return col_span * 30   # pullout mode — slim emphasis bar

    if "capacity_chars_fixed" in meta:
        return int(meta["capacity_chars_fixed"])
    per_col = meta.get("capacity_chars_per_col")
    if per_col is not None:
        return int(per_col) * int(col_span)
    return 0


def _project_slide_fill(rows: list) -> dict:
    """Compute total-slide capacity-fill metrics without emitting warnings.
    Used by both Gap E validator and v3.11 auto-decoration trigger.

    Returns: {slide_actual, slide_capacity, slide_fill, cell_metrics}
    where cell_metrics is a list of per-cell (component, col_span, actual,
    capacity, fill_ratio).
    """
    slide_actual = 0
    slide_capacity = 0
    cell_metrics = []
    for row in rows:
        for cell in row.get("cells", []):
            comp = cell.get("component")
            if not comp:
                continue
            col_span = int(cell.get("col_span", 12))
            props = cell.get("props") or {}
            cap = _component_capacity(comp, col_span, props)
            if cap <= 0:
                continue
            actual = _walk_chars(props)
            slide_actual += actual
            slide_capacity += cap
            cell_metrics.append({
                "component": comp,
                "col_span":  col_span,
                "actual":    actual,
                "capacity":  cap,
                "fill":      (actual / cap) if cap > 0 else 0,
            })
    slide_fill = (slide_actual / slide_capacity) if slide_capacity > 0 else 0
    return {
        "slide_actual":   slide_actual,
        "slide_capacity": slide_capacity,
        "slide_fill":     slide_fill,
        "cell_metrics":   cell_metrics,
    }


# ---------------------------------------------------------------------------
# v3.13 — Density mode profiles (closes gap #32 page-builder side)
#
# Mirrors the creator-side ``capacity.DENSITY_MODES`` so warnings at compose
# time use the same thresholds as Phase 4 audits. Three named profiles —
# 'standard' is the legacy hardcoded behavior (v3.7-3.12). 'sparse-ok'
# tolerates lower fill (hero/breathing slides). 'dense' tolerates higher
# fill (spec sheets, info-rich detail). Plumbed via ``slide_meta.density_mode``.
# ---------------------------------------------------------------------------
_DENSITY_MODE_THRESHOLDS = {
    "standard": {
        "cell_fill_min":      0.70,   # _fill_verified must hit this
        "slide_sparse_below": 0.40,
        "slide_overcrowded_above": 1.15,
    },
    "sparse-ok": {
        "cell_fill_min":      0.50,
        "slide_sparse_below": 0.20,
        "slide_overcrowded_above": 1.15,
    },
    "dense": {
        "cell_fill_min":      0.80,
        "slide_sparse_below": 0.55,
        "slide_overcrowded_above": 1.25,
    },
}


def _validate_fill_honesty(rows: list, where_prefix: str,
                           density_mode: str = "standard") -> list[str]:
    """Gap E — capacity-fill projection.

    Two checks:
      1. PER-CELL honesty: row uses _fill_verified=True but cell's actual
         chars project to <{cell_fill_min}× of capacity → declaration is
         dishonest.
      2. PER-SLIDE sparse: total slide chars / total capacity below
         {slide_sparse_below}× → hint to add content / restructure
         (decoration is now handled by the separate ``vti-slide-decorator``
         skill post-compose).

    Components without capacity declaration are skipped.

    v3.13 — thresholds parameterized by ``density_mode`` (closes gap #32
    page-builder side). Pre-v3.13 these were hardcoded as 70/40/115%
    (the 'standard' profile). Slides with ``slide_meta.density_mode``
    set to 'sparse-ok' or 'dense' now relax/tighten accordingly.
    """
    profile = _DENSITY_MODE_THRESHOLDS.get(density_mode)
    if profile is None:
        # Unknown mode — fall back to standard but emit a warning.
        profile = _DENSITY_MODE_THRESHOLDS["standard"]
    cell_min = profile["cell_fill_min"]
    sparse_below = profile["slide_sparse_below"]
    overcrowded_above = profile["slide_overcrowded_above"]

    warnings: list[str] = []

    # Per-cell honesty — uses fresh metrics, not the shared projection,
    # because we need access to the row.height + _fill_verified flag.
    for ri, row in enumerate(rows):
        is_1fr_verified = (
            str(row.get("height", "auto")) == "1fr"
            and row.get("_fill_verified") is True
        )
        if not is_1fr_verified:
            continue
        for ci, cell in enumerate(row.get("cells", [])):
            comp = cell.get("component")
            if not comp:
                continue
            col_span = int(cell.get("col_span", 12))
            props = cell.get("props") or {}
            cap = _component_capacity(comp, col_span, props)
            if cap <= 0:
                continue
            actual = _walk_chars(props)
            fill = actual / cap
            if fill < cell_min:
                warnings.append(
                    f"[gap-E fill-honesty] {where_prefix}[{ri}].cells[{ci}]: "
                    f"row uses _fill_verified=True but '{comp}' projected "
                    f"fill={fill:.0%} ({actual} / {cap} chars) is below "
                    f"{cell_min:.0%} (mode={density_mode}). "
                    f"Either drop _fill_verified=True (use auto), or expand "
                    f"content to honour the declaration."
                )

    # Per-slide aggregate
    metrics = _project_slide_fill(rows)
    slide_capacity = metrics["slide_capacity"]
    slide_fill = metrics["slide_fill"]
    slide_actual = metrics["slide_actual"]

    if slide_capacity > 0:
        if slide_fill < sparse_below:
            warnings.append(
                f"[gap-E slide-sparse] {where_prefix}: total slide fill "
                f"{slide_fill:.0%} ({slide_actual} / {slide_capacity} chars) "
                f"below {sparse_below:.0%} (mode={density_mode}). "
                f"Per P7 Loop 2, slides under this threshold should: "
                f"(1) add real content, or (2) restructure layout. Decoration "
                f"is now handled by the post-compose ``vti-slide-decorator`` skill."
            )
        elif slide_fill > overcrowded_above:
            warnings.append(
                f"[gap-E slide-overcrowded] {where_prefix}: total slide fill "
                f"{slide_fill:.0%} ({slide_actual} / {slide_capacity} chars) "
                f"above {overcrowded_above:.0%} (mode={density_mode}). "
                f"Per P6, slides over this threshold are too dense; consider "
                f"splitting into two slides or moving content to an appendix."
            )

    return warnings


def _compose_grid_body(rows: list, where_prefix: str = "rows",
                        layout_class: str = "default",
                        density_mode: str = "standard",
                        vertical_align: str = "start",
                        ) -> tuple[str, set[str], list[str]]:
    """Render rows × cells into the inner grid HTML.

    Used by both ``compose_slide_grid`` (which then wraps in chrome) and
    ``compose_case_study`` (which wraps in the case-study layout frame).
    Caller is responsible for chrome/wrapper + CSS aggregation.

    Side effect: adds component names to ``_USED_COMPONENTS_THIS_RENDER``
    so the caller picks up transitive components (e.g. stat-mini inside
    kpi-row) when assembling slide_css.

    Args:
        rows: list of row dicts.
        where_prefix: tag for warning messages.
        layout_class: 'default' | 'case-study' | 'data-dense' (T1/T2 budget).
        density_mode: v3.13 (closes gap #32 page-builder side) — one of
            'standard' | 'sparse-ok' | 'dense'. Adjusts the cell-fill /
            slide-sparse / slide-overcrowded thresholds in
            ``_validate_fill_honesty``. Routed from
            ``slide_meta.density_mode`` by ``compose_slide_grid``.

    Returns:
        (body_html, top_level_components, warnings)
    """
    if not rows or not isinstance(rows, list):
        raise ValidationError("missing_required", where_prefix,
                              "must be non-empty array")

    top_level_components: set[str] = set()
    cell_html_parts: list[str] = []
    warnings: list[str] = []

    # v3.5 — Gap C, aggregate font budget across the whole slide --------
    warnings.extend(_aggregate_type_budget(rows, where_prefix, layout_class))

    # v3.7 — Gap E, capacity-fill projection -----------------------------
    # v3.13 — pass density_mode to make thresholds mode-aware.
    warnings.extend(_validate_fill_honesty(rows, where_prefix,
                                            density_mode=density_mode))

    # v3.5 — clear esc-warning buffer; render loop will populate it -----
    _LAST_ESC_WARNINGS.clear()

    for ri, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValidationError("invalid_type", f"{where_prefix}[{ri}]",
                                  "must be dict")
        # v3.5 — Gap B, 1fr row needs _fill_verified -------------------
        w = _validate_1fr_row(row, ri, where_prefix)
        if w:
            warnings.append(w)

        cells = row.get("cells")
        if not cells or not isinstance(cells, list):
            raise ValidationError("missing_required",
                                  f"{where_prefix}[{ri}].cells",
                                  "must be non-empty array")
        for ci, cell in enumerate(cells):
            where = f"{where_prefix}[{ri}].cells[{ci}]"
            if not isinstance(cell, dict):
                raise ValidationError("invalid_type", where, "must be dict")
            _validate_cell(cell, where)
            comp_name = cell["component"]
            props = cell.get("props") or {}

            # v3.5 — Gap A, col_span ∉ best_col_spans -------------------
            w = _validate_col_span(comp_name, cell.get("col_span", 12), where)
            if w:
                warnings.append(w)

            comp_html = render_component(comp_name, props)
            top_level_components.add(comp_name)

            grid_style = (
                f"grid-column: {cell.get('col_start', 1)} / span "
                f"{cell.get('col_span', 12)}; "
                f"grid-row: {ri + 1} / span {cell.get('row_span', 1)};"
            )
            cell_html_parts.append(
                f'<div class="vti-grid-cell" style="{grid_style}">'
                f'{comp_html}'
                f'</div>'
            )

    # v3.5 — Gap D, drain any pre-escape detections from this body ------
    warnings.extend(_drain_esc_warnings(where_prefix))

    # Build grid-template-rows from row heights
    row_heights = [str(r.get("height", "auto")) for r in rows]
    grid_rows_css = " ".join(row_heights)

    if vertical_align not in ("start", "center"):
        raise ValidationError(
            "invalid_value", f"{where_prefix}.vertical_align",
            f"must be 'start' or 'center', got {vertical_align!r}",
        )
    grid_class = "vti-grid" + (" vti-grid--center" if vertical_align == "center" else "")

    body_html = (
        f'<div class="{grid_class}" '
        f'style="grid-template-rows: {grid_rows_css};">\n'
        f'    ' + "\n    ".join(cell_html_parts) + '\n'
        f'  </div>'
    )

    return body_html, top_level_components, warnings


def compose_slide_grid(slide_input: dict) -> dict:
    """Render one slide. Returns {slide_html, slide_css, metadata}."""
    if not isinstance(slide_input, dict):
        raise ValidationError("invalid_type", "slide_input", "must be dict")
    slide_meta = slide_input.get("slide_meta") or {}
    rows = slide_input.get("rows")

    show_chrome = slide_meta.get("show_chrome", True)
    # v3.10 — layout_class drives Gap C threshold + post-render audit
    layout_class = slide_meta.get("layout_class", "default")
    if layout_class not in _LAYOUT_BUDGETS:
        raise ValidationError(
            "invalid_value", "slide_meta.layout_class",
            f"must be one of {sorted(_LAYOUT_BUDGETS.keys())}, got {layout_class!r}",
        )
    # v3.13 — density_mode drives gap-E fill thresholds (closes #32 PB side)
    density_mode = slide_meta.get("density_mode", "standard")
    if density_mode not in _DENSITY_MODE_THRESHOLDS:
        raise ValidationError(
            "invalid_value", "slide_meta.density_mode",
            f"must be one of {sorted(_DENSITY_MODE_THRESHOLDS.keys())}, "
            f"got {density_mode!r}",
        )
    # v3.13.8 — vertical_align distributes leftover space top+bottom
    # ('center') vs dumping it all at the bottom ('start', default).
    vertical_align = slide_meta.get("vertical_align", "start")

    # Reset transitive-component tracker for this render -----------------
    _USED_COMPONENTS_THIS_RENDER.clear()

    rows = list(rows or [])  # local copy
    # Decoration is handled by the separate ``vti-slide-decorator`` skill
    # post-compose. The composer emits clean content slides only.

    # Render body grid (delegates to shared helper) ----------------------
    grid_html, top_level_components, warnings = _compose_grid_body(
        rows, layout_class=layout_class, density_mode=density_mode,
        vertical_align=vertical_align)

    # Chrome --------------------------------------------------------------
    if show_chrome:
        header_html, footer_html, chrome_css = _render_chrome(slide_meta)
    else:
        header_html, footer_html, chrome_css = "", "", ""

    # Final slide HTML ----------------------------------------------------
    section_class = ""  # reserved for future variant layouts
    # position:relative kept so the future decorator skill's overlay layer
    # can anchor to the slide canvas via position:absolute.
    slide_html = (
        f'<div class="slide layout-grid {section_class}" '
        f'data-layout-class="{layout_class}" '
        f'style="position: relative;">\n'
        f'{header_html}\n'
        f'<div class="vti-slide-content">\n'
        f'  {grid_html}\n'
        f'</div>\n'
        f'{footer_html}\n'
        f'</div>'
    )

    # Aggregate CSS — use the FULL transitive set so compound components
    # (e.g. kpi-row → stat-mini) include their inner-component CSS too.
    all_used = sorted(_USED_COMPONENTS_THIS_RENDER)
    tokens_css = _read_file(TOKENS_PATH)
    component_css_parts = [_component_css(c) for c in all_used]
    slide_css = "\n\n".join(filter(None, [
        tokens_css,
        chrome_css,
        _GRID_CSS,
        *component_css_parts,
    ]))

    # Inline any local asset references that components emit (image-tile,
    # logo-grid, etc. all reference images by path). Search SKILL_ROOT
    # first so internal asset names ('assets/x.png') keep priority, then
    # the caller's cwd so project-relative paths (e.g. 'work/extracted_images/…'
    # produced by the creator's Phase-3 lift cache) also resolve.
    search_dirs = [SKILL_ROOT, Path.cwd()]
    slide_html = _inline_assets_in_html(slide_html, search_dirs)
    slide_css  = _inline_assets_in_css(slide_css,  search_dirs)

    return {
        "slide_html": slide_html,
        "slide_css":  slide_css,
        "metadata": {
            "components_used":     sorted(top_level_components),
            "components_rendered": all_used,
            "row_count":  len(rows),
            "cell_count": sum(len(r["cells"]) for r in rows),
            "warnings":   warnings,
        },
    }


# ---------------------------------------------------------------------------
# Catalog (for orchestrator discovery)
# ---------------------------------------------------------------------------
def catalog(*, verbose: bool = False) -> dict:
    """Return registered components — primary protocol surface for the
    creator skill (and any other consumer) to discover what's available.

    Args:
        verbose: if True, include full component metadata (role, kind,
                 best_col_spans, schema_brief, picks_content_kinds).
                 Default False keeps the response small for quick checks.

    Always returns:
        skill, version, components, icons

    With verbose=True also returns:
        component_meta:        dict[name → meta dict]
        picks_for_content_kind: dict[content_kind → list of component names]
                               (reverse lookup; built from each component's
                                picks_content_kinds list)
    """
    base = {
        "skill":      "vti-slide-page-builder",
        "version":    "3.18.0",
        "components": sorted(_COMPONENT_RENDERERS.keys()),
        "icons":      sorted(ICON_SVGS.keys()),
    }
    if not verbose:
        return base

    # Build the reverse picker map by walking each component's
    # picks_content_kinds. This is the single source of truth for
    # "which components can render content of kind X" — creator's
    # picks_for_kind() is a thin wrapper around this.
    picks: dict[str, list[str]] = {}
    for comp_name, meta in _COMPONENT_META.items():
        for kind in meta.get("picks_content_kinds", []):
            picks.setdefault(kind, []).append(comp_name)
    for kind in picks:
        picks[kind].sort()

    base["component_meta"] = {
        name: dict(_COMPONENT_META.get(name, {"role": "", "kind": "unknown"}))
        for name in sorted(_COMPONENT_RENDERERS.keys())
    }
    base["picks_for_content_kind"] = picks
    return base


def describe_component(name: str) -> dict:
    """Return metadata for one component. Raises if unregistered."""
    if name not in _COMPONENT_RENDERERS:
        raise ValidationError(
            "unknown_component", name,
            f"registered: {sorted(_COMPONENT_RENDERERS.keys())}",
        )
    return dict(_COMPONENT_META.get(name, {}))


# Component category — used to organize catalog output. Maps each component
# name to a top-level category. The creator skill can iterate by category
# when planning slide layouts (e.g. "I need a chart" → look at 'data viz').
COMPONENT_CATEGORIES = {
    # Stats / data display
    "stat-hero":         "stats",
    "stat-mini":         "stats",
    "kpi-row":           "stats",
    "value-medallion":   "stats",
    "trend-stat":        "stats",
    # Text · paragraph (single text blocks)
    "narrative-paragraph": "text-paragraph",
    "lead-paragraph":     "text-paragraph",
    "headline":           "text-paragraph",
    "kicker":             "text-paragraph",
    "section-header":     "text-paragraph",
    "pull-quote":         "text-paragraph",
    "quote-block":        "text-paragraph",
    "callout":            "text-paragraph",
    # Text · list (multi-item collections)
    "bullet-list-checked": "text-list",
    "numbered-list":       "text-list",
    "icon-list":           "text-list",
    "definition-list":     "text-list",
    "tags":                "text-list",
    # Cards (richer single units with structure)
    "practice-card":          "card",
    "practice-card-leveled":  "card",
    "catalog-column":         "card",
    # Visuals (image, logos)
    "image-tile":        "visual",
    "logo-grid":         "visual",
    # Tables
    "table":             "table",
    "comparison-table":  "table",
    # Charts
    "bar-chart":         "chart",
    "pie-chart":         "chart",
    "stacked-bar":       "chart",
    "line-chart":        "chart",
    "progress-bar":      "chart",
    "gauge-dial":        "chart",
    # Diagrams (flow / relationship visualizations)
    "process-flow":      "diagram",
    "swimlane":          "diagram",
    "timeline":          "diagram",
    "funnel":            "diagram",
    "quadrant-matrix":   "diagram",
    "before-after":      "diagram",
    "vs-divider":        "diagram",
}

CATEGORY_DESCRIPTIONS = {
    "stats":          "Numeric values + labels. KPIs, hero stats, supporting numbers.",
    "text-paragraph": "Single text blocks — paragraphs, headlines, eyebrow labels, "
                      "callouts, quotes.",
    "text-list":      "Multi-item text collections — bullets, numbered lists, key-value pairs, "
                      "tags.",
    "card":           "Richer single units — number/icon/title/body composites.",
    "visual":         "Image and logo content.",
    "table":          "Tabular structured data.",
    "chart":          "Data visualizations — bars, pies, lines, progress, gauges.",
    "diagram":        "Process flows, timelines, matrices, structural relationships.",
}


def catalog_by_category(*, verbose: bool = True) -> dict:
    """Return components grouped by category — the most useful shape for the
    creator skill when planning a slide.

    Returns:
        {
          "skill":      str,
          "version":    str,
          "categories": [
            {
              "name":         "stats",
              "description":  "...",
              "components": [
                {"name": "stat-hero", "role": "...", "kind": "data",
                 "good_for": [...], "bad_for": [...],
                 "best_col_spans": [...], "natural_height": "...",
                 "schema_brief": "...", "picks_content_kinds": [...]},
                ...
              ]
            },
            ...
          ],
          "picks_for_content_kind": dict   # reverse lookup
        }
    """
    base = catalog(verbose=verbose)
    component_meta = base.get("component_meta", {})

    categories = []
    for cat_name, cat_desc in CATEGORY_DESCRIPTIONS.items():
        comps_in_cat = [
            name for name, c in COMPONENT_CATEGORIES.items() if c == cat_name
        ]
        comps_in_cat = sorted(c for c in comps_in_cat if c in _COMPONENT_RENDERERS)

        cat_components = []
        for cn in comps_in_cat:
            entry = {"name": cn}
            entry.update(component_meta.get(cn, {}))
            cat_components.append(entry)

        categories.append({
            "name":        cat_name,
            "description": cat_desc,
            "count":       len(cat_components),
            "components":  cat_components,
        })

    return {
        "skill":      base["skill"],
        "version":    base["version"],
        "categories": categories,
        "picks_for_content_kind": base.get("picks_for_content_kind", {}),
    }


def catalog_markdown() -> str:
    """Return the full component catalog as a markdown document for human +
    LLM consumption. The creator skill can read this for planning, or it can
    be embedded in skill documentation.
    """
    by_cat = catalog_by_category(verbose=True)

    lines = []
    lines.append(f"# {by_cat['skill']} · component catalog")
    lines.append("")
    lines.append(f"_v{by_cat['version']}_ — "
                 f"{sum(c['count'] for c in by_cat['categories'])} atomic components "
                 f"across {len(by_cat['categories'])} categories.")
    lines.append("")
    lines.append("Every component is grid-flexible: it works at any "
                 "`col_span` (1-12) and `row_span` (1-N) within a slide's "
                 "12-column grid. Charts use SVG `viewBox` to scale; tables "
                 "use CSS `minmax(0, 1fr)` columns; text blocks flex naturally.")
    lines.append("")
    lines.append("Emphasis design rule: the VTI brand blue (`var(--vti-blue-deep)` "
                 "or `var(--vti-navy)`) is ALWAYS used for emphasis in slides. "
                 "Tints/shades for variation, grays for de-emphasis. NO yellow/amber.")
    lines.append("")

    # Quick-reference index
    lines.append("## Quick reference")
    lines.append("")
    for cat in by_cat["categories"]:
        names = ", ".join(f"`{c['name']}`" for c in cat["components"])
        lines.append(f"- **{cat['name']}** ({cat['count']}) — {names}")
    lines.append("")

    # Per-category detailed breakdown
    for cat in by_cat["categories"]:
        lines.append(f"## {cat['name']}")
        lines.append("")
        lines.append(f"_{cat['description']}_")
        lines.append("")

        for c in cat["components"]:
            lines.append(f"### `{c['name']}`")
            lines.append("")
            lines.append(f"**Role.** {c.get('role', '')}")
            lines.append("")

            kind = c.get("kind", "")
            if kind:
                lines.append(f"**Kind:** `{kind}`")
                lines.append("")

            schema = c.get("schema_brief", "")
            if schema:
                lines.append(f"**Schema:** `{schema}`")
                lines.append("")

            best = c.get("best_col_spans", [])
            if best:
                lines.append(f"**Best col_spans:** {best}  ·  "
                             f"**Natural height:** `{c.get('natural_height', 'auto')}`")
                lines.append("")

            good = c.get("good_for", [])
            bad  = c.get("bad_for", [])
            if good:
                lines.append("**Use for:**")
                for g in good:
                    lines.append(f"- {g}")
                lines.append("")
            if bad:
                lines.append("**Don't use for:**")
                for b in bad:
                    lines.append(f"- {b}")
                lines.append("")

            picks = c.get("picks_content_kinds", [])
            if picks:
                aliases = ", ".join(f"`{p}`" for p in picks)
                lines.append(f"**Block kind aliases:** {aliases}")
                lines.append("")

    # Reverse lookup section
    lines.append("## Reverse lookup — content kind → component")
    lines.append("")
    lines.append("When you have content of a particular kind (e.g. a chart, a quote, "
                 "a callout), this index tells you which components can render it.")
    lines.append("")
    picks = by_cat.get("picks_for_content_kind", {})
    for kind in sorted(picks.keys()):
        comps = picks[kind]
        lines.append(f"- `{kind}` → {', '.join(f'`{c}`' for c in comps)}")

    return "\n".join(lines)


# ===========================================================================
# Mini template engine — for special pages with {{#each}} loops
# ===========================================================================
# Supports a Mustache/Handlebars-ish subset:
#   {{KEY}}              simple substitution from ctx
#   {{this.KEY}}         dotted-path lookup — also works for {{KEY.SUB}}
#   {{#each ARRAY}}...{{/each}}
#                        iterate over a list, binding `this` to each item.
#                        Inner blocks may reference `{{this.field}}` and may
#                        themselves contain nested `{{#each this.sub}}`.
#
# This is intentionally tiny — it only handles the patterns we found in the
# 13 special-page templates (toc, contact). It is NOT a full Mustache impl.
# ---------------------------------------------------------------------------

def _resolve_path(path: str, ctx: dict) -> Any:
    """Resolve a dotted path like 'this.foo.bar' against ctx (dict-of-dicts)."""
    val: Any = ctx
    for part in path.strip().split("."):
        if val is None:
            return ""
        if isinstance(val, dict):
            val = val.get(part, "")
        else:
            val = getattr(val, part, "")
    return val if val is not None else ""


def _find_outer_each(s: str) -> tuple[int, int, str, int, int] | None:
    """Find the FIRST top-level {{#each VAR}}…{{/each}} block in s.

    Returns (open_start, close_end, var_path, body_start, body_end), or None
    if no balanced block is found. Walks the string with a depth counter so
    nested {{#each}} blocks are matched correctly to their {{/each}}.
    """
    open_re  = re.compile(r"\{\{#each\s+([\w\.]+)\}\}")
    close_re = re.compile(r"\{\{/each\}\}")

    m = open_re.search(s)
    if not m:
        return None
    open_start = m.start()
    body_start = m.end()
    var_path   = m.group(1)

    depth = 1
    pos = body_start
    while pos < len(s):
        next_open  = open_re.search(s, pos)
        next_close = close_re.search(s, pos)
        if not next_close:
            return None  # malformed — unclosed {{#each}}
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                return (open_start, next_close.end(), var_path,
                        body_start, next_close.start())
            pos = next_close.end()
    return None


def _fill_template(template: str, ctx: dict) -> str:
    """Render a template with simple subs + {{#each}} loops."""
    # 1) Expand each-blocks outside-in, recursively rendering bodies.
    while True:
        block = _find_outer_each(template)
        if block is None:
            break
        open_start, close_end, var_path, body_start, body_end = block
        body = template[body_start:body_end]
        items = _resolve_path(var_path, ctx)
        if not isinstance(items, list):
            items = []
        rendered_items: list[str] = []
        for item in items:
            sub_ctx = {**ctx, "this": item}
            rendered_items.append(_fill_template(body, sub_ctx))
        template = (template[:open_start] + "".join(rendered_items)
                    + template[close_end:])

    # 2) Substitute simple {{X}} / {{this.X}} placeholders.
    #    Skip {{#…}} and {{/…}} (already gone but be safe) and unknown paths
    #    silently resolve to "".
    def _sub(m: "re.Match[str]") -> str:
        token = m.group(1).strip()
        if not token or token.startswith("#") or token.startswith("/"):
            return m.group(0)
        val = _resolve_path(token, ctx)
        return "" if val is None else str(val)

    return re.sub(r"\{\{([^{}]+?)\}\}", _sub, template)


# ===========================================================================
# Special-page registry + renderer
# ===========================================================================
# Each entry declares:
#   - required:  list of prop keys that MUST be supplied
#   - optional:  dict of prop keys → default value
#   - has_chrome: True if the page renders the standard chrome breadcrumb +
#                 footer (so we include chrome CSS in the bundle).
#                 The page itself is responsible for the actual chrome HTML
#                 — this flag only controls CSS bundling.
#
# Prop keys are case-insensitive for the user's convenience: the renderer
# uppercases each key when building the template context (matching the
# existing {{UPPER_CASE_PLACEHOLDER}} convention).
# ---------------------------------------------------------------------------

# ===========================================================================
# Contact page defaults
# ===========================================================================
# Default channel-icon SVGs (24×24 viewBox, currentColor stroke). Provided
# so callers can pass channels with just `{type, text}` and let the
# renderer inject the matching icon_svg automatically. Outline-style to
# match the rest of the deck's icon language.
# Brand-trademarked marks (LinkedIn, Facebook, X, etc.) are intentionally
# NOT included — pass `icon_svg` explicitly for those if needed.

_CONTACT_CHANNEL_ICONS: dict[str, str] = {
    "email": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="5" width="18" height="14" rx="2"/>'
        '<path d="M3 7l9 6 9-6"/></svg>'
    ),
    "website": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M3 12h18"/>'
        '<path d="M12 3a14 14 0 0 1 0 18"/>'
        '<path d="M12 3a14 14 0 0 0 0 18"/></svg>'
    ),
    "phone": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4'
        'a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>'
    ),
    "linkedin": (   # generic users glyph — NOT the LinkedIn trademark
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="9" cy="8" r="3"/><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>'
        '<path d="M16 11h5M18.5 8.5v5"/></svg>'
    ),
    "facebook": (   # generic "f" glyph — not the brand wordmark
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 8h2.5V5H14a3 3 0 0 0-3 3v2H9v3h2v8h3v-8h2.5l.5-3H14V8.5'
        'a.5.5 0 0 1 .5-.5"/></svg>'
    ),
    "address": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M12 22s7-7.5 7-13a7 7 0 1 0-14 0c0 5.5 7 13 7 13z"/>'
        '<circle cx="12" cy="9" r="2.5"/></svg>'
    ),
}


# Canonical VTI defaults are loaded from data/vti-defaults.json — single
# source of truth, editable without touching Python. The file ships with
# real VTI contact data; do NOT invent placeholder data inline.

import json as _json

_DEFAULTS_PATH = SKILL_ROOT / "data" / "vti-defaults.json"


def _load_canonical_defaults() -> dict:
    """Read data/vti-defaults.json. Cached on first call."""
    if not _DEFAULTS_PATH.exists():
        return {}
    with open(_DEFAULTS_PATH, "r", encoding="utf-8") as f:
        raw = _json.load(f)
    # Strip the documentation keys (start with `_`)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


_CANONICAL_DEFAULTS: dict = _load_canonical_defaults()


# Default contact data is read from JSON — see data/vti-defaults.json.
_DEFAULT_CONTACT_PROPS: dict[str, Any] = _CANONICAL_DEFAULTS.get("contact", {})


SPECIAL_PAGES: dict[str, dict] = {
    # ---- 5 framing pages ----
    "cover": {
        "required":  ["deck_title"],
        "optional":  {"deck_tagline": "",
                      "cover_variant": "standard",        # 'standard' | 'co-brand'
                      "customer_logo_style": ""},
        "has_chrome": False,
    },
    "toc": {
        "required":  ["toc_items"],   # list[{title, page, items?}]
        "optional":  {"toc_cols": 2,
                      "doc_title": "", "page_num": 0,
                      "copyright_year": 2026},
        "has_chrome": False,    # toc has its own footer
    },
    "section-divider": {
        "required":  ["section_title"],
        "optional":  {"section_description": "",
                      "dv_bg_style": ""},
        "has_chrome": False,
    },
    "contact": {
        "required":  [],
        "optional":  {"contact_headline": _DEFAULT_CONTACT_PROPS["contact_headline"],
                      "channels": _DEFAULT_CONTACT_PROPS["channels"],
                      "offices":  _DEFAULT_CONTACT_PROPS["offices"]},
        "has_chrome": False,    # contact has its own framing
    },
    "closing": {
        "required":  [],
        "optional":  {"closing_message": ""},
        "has_chrome": False,
    },
    # ---- 8 narrator pages (all use chrome breadcrumb + footer) ----
    "about-vti": {
        "required":  [],
        "optional":  {"intro_text": ""},
        "has_chrome": True,
    },
    "vision-mission-values": {
        "required":  [],
        "optional":  {"vision_title": "Vision", "vision_body": "",
                      "mission_title": "Mission", "mission_body": ""},
        "has_chrome": True,
    },
    "who-we-serve": {
        "required":  [],
        "optional":  {
            "caption": "",
            "stat_customers_value": "", "stat_customers_label": "Customers",
            "stat_projects_value":  "", "stat_projects_label":  "Projects",
            "legend_banking": "Banking & Finance",
            "legend_construction": "Construction",
            "legend_healthcare": "Healthcare",
            "legend_internet": "Internet & Media",
            "legend_mfg": "Manufacturing",
            "legend_others": "Others",
            "legend_public": "Public sector",
            "legend_retail": "Retail",
            "legend_utilities": "Utilities",
        },
        "has_chrome": True,
    },
    "awards-certifications": {
        "required":  [],
        "optional":  {"footnote": ""},
        "has_chrome": True,
    },
    "strategic-partners": {
        "required":  [],
        "optional":  {"tagline": ""},
        "has_chrome": True,
    },
    "project-management-method": {
        "required":  [],
        "optional":  {"intro_text": ""},
        "has_chrome": True,
    },
    "quality-assurance": {
        "required":  [],
        "optional":  {"activities_title": "Quality activities",
                      "callout_text": ""},
        "has_chrome": True,
    },
    "quality-management-process": {
        "required":  [],
        "optional":  {"intro_text": ""},
        "has_chrome": True,
    },
}


def _build_breadcrumb_html(section: str, title: str) -> str:
    """Mirror the chrome breadcrumb composer so narrator pages get the
    same SECTION | TITLE pattern as content slides."""
    section = (section or "").upper()
    title   = (title or "").upper()
    if section and title and section != title:
        return (f'<span class="bc-section">{_esc(section)}</span>'
                f'<span class="bc-sep"> | </span>'
                f'<span class="bc-title">{_esc(title)}</span>')
    return _esc(title or section)


import base64


_MIME_BY_EXT = {
    ".jpg":  "image/jpeg", ".jpeg": "image/jpeg",
    ".png":  "image/png",  ".gif":  "image/gif",
    ".svg":  "image/svg+xml", ".webp": "image/webp",
    ".woff": "font/woff",  ".woff2": "font/woff2",
}


def _file_to_data_url(path: Path) -> str:
    """Read a binary asset and return a `data:<mime>;base64,...` URL."""
    mime = _MIME_BY_EXT.get(path.suffix.lower(), "application/octet-stream")
    b64  = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _resolve_asset_path(url: str, search_dirs: list[Path]) -> Path | None:
    """Try to resolve a relative URL against each search dir, return the
    first existing path (or None if not found anywhere)."""
    for d in search_dirs:
        candidate = (d / url).resolve()
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _inline_assets_in_css(css: str, search_dirs: list[Path]) -> str:
    """Replace `url('rel/path.ext')` references in CSS with inline base64
    data URLs so the CSS is portable when rendered anywhere.

    Skips `data:` URLs (already inlined), `http(s):` URLs (remote — left
    as-is so the browser fetches them), and `#fragment` references. Local
    paths that can't be resolved are left untouched (logged silently).
    """
    def replace(m: "re.Match[str]") -> str:
        raw = m.group(1).strip()
        url = raw.strip("'\"")
        if url.startswith(("http://", "https://", "data:", "#")) or not url:
            return m.group(0)
        path = _resolve_asset_path(url, search_dirs)
        if path is None:
            return m.group(0)
        return f"url('{_file_to_data_url(path)}')"

    return re.sub(r"url\(([^)]+)\)", replace, css)


def _inline_assets_in_html(html: str, search_dirs: list[Path]) -> str:
    """Replace `<img src="rel/path">` references in HTML with inline
    base64 data URLs. Same skip rules as the CSS variant; also skips
    unfilled `{{…}}` template placeholders.
    """
    def replace(m: "re.Match[str]") -> str:
        full = m.group(0)
        src  = m.group(1)
        if (src.startswith(("http://", "https://", "data:", "{{"))
                or not src):
            return full
        path = _resolve_asset_path(src, search_dirs)
        if path is None:
            return full
        return full.replace(f'src="{src}"',
                            f'src="{_file_to_data_url(path)}"')

    return re.sub(r'<img\b[^>]*\bsrc="([^"]+)"', replace, html)


# ===========================================================================
# Post-render integrity guards
# ===========================================================================
# These checks run on every `compose_special_page` call and raise
# immediately if any of the four classes of bug we've hit before sneaks
# back in. They're cheap (O(n) string scans) and they make the wrapper
# self-policing — bugs become hard errors at the call site, not silent
# visual regressions discovered later.

# Wrapper classes used by the 13 special-page templates. A logo <img>
# inside any of these wrappers is positioned BY THE WRAPPER's CSS — the
# img itself MUST be plain (no `.logo-*` class). If a `.logo-*` class
# leaks in, we re-create the bug where:
#   - cover/closing logo jumps to top-right (flex centering overridden)
#   - TOC logo jumps to top-right (top-left wrapper overridden)
#   - contact white logo "falls" off the photo (stacked absolutes compound)
_SPECIAL_PAGE_LOGO_WRAPPERS = (
    "cv-logo--vti",     # cover top-center logo (inside .cv-logo-row flex)
    "cl-logo",          # closing top-center logo (flex)
    "toc-mesh-logo",    # toc top-left
    "ct-logo-tr",       # contact white logo on photo
    "ct-logo-bl",       # contact full-color logo bottom-left
    "dv-logo",          # section-divider logo
)


def _assert_special_page_clean(name: str, html: str, css: str) -> None:
    """Verify post-render output is free of the 4 known regression classes.

    Raises ``ValidationError`` (specific code each) on any failure so
    callers see *why* immediately rather than chasing a visual bug.
    """
    # ── Guard 1: no unfilled `{{X}}` placeholders in HTML ─────────────
    # CSS comments may legitimately contain `{{X}}` (documentation), so
    # we only scan HTML output. CSS leak isn't user-visible anyway.
    leftover = re.findall(r"\{\{[^{}#/][^{}]*\}\}", html)
    if leftover:
        raise ValidationError(
            "placeholder_leak", f"compose_special_page({name})",
            f"unfilled placeholders in rendered HTML: {leftover[:3]}",
        )

    # ── Guard 2: every <!-- VTI_LOGO_INJECT --> marker must be resolved ─
    if "VTI_LOGO_INJECT" in html:
        raise ValidationError(
            "logo_marker_leak", f"compose_special_page({name})",
            "VTI_LOGO_INJECT comment(s) survived _resolve_logo_markers — "
            "logo image not embedded; check marker syntax in template",
        )

    # ── Guard 3: no relative asset paths anywhere ─────────────────────
    # The asset inliner must convert all local references to data URLs.
    # Surviving relative paths break when the HTML is opened standalone
    # — exactly the bug that made the cover background go missing.
    rel_in_css  = re.search(r"url\(\s*['\"]?\.{1,2}/[^)]+\)", css)
    rel_in_html = re.search(r'<img\b[^>]*\bsrc="\.{1,2}/[^"]+"', html)
    if rel_in_css:
        raise ValidationError(
            "relative_asset_path", f"compose_special_page({name})",
            f"relative url() not inlined in CSS: {rel_in_css.group(0)[:80]} — "
            "_inline_assets_in_css must cover all local references",
        )
    if rel_in_html:
        raise ValidationError(
            "relative_asset_path", f"compose_special_page({name})",
            f"relative <img src> not inlined: {rel_in_html.group(0)[:80]}",
        )

    # ── Guard 4: special-page logo wrappers must contain a plain <img> ─
    # If `_resolve_logo_markers` ever re-introduces a fallback that adds
    # `class="logo-tr"` to non-chrome markers, the img will fight the
    # wrapper's positioning. Catch it here.
    for wrapper in _SPECIAL_PAGE_LOGO_WRAPPERS:
        m = re.search(
            rf'<div\s[^>]*class="[^"]*\b{re.escape(wrapper)}\b[^"]*"[^>]*>\s*'
            r'(<img\b[^>]*>)',
            html,
        )
        if m and re.search(r'\bclass="logo-[a-z]+', m.group(1)):
            raise ValidationError(
                "logo_class_regression", f"compose_special_page({name})",
                f"<img> inside .{wrapper} has a .logo-* positioning class — "
                "must be plain so the wrapper's CSS controls placement",
            )

    # ── Guard 5 (contact only): canonical VTI data must be present ────
    # If someone re-introduces inline placeholder data and bypasses the
    # JSON file, this breaks. The 4 anchor strings come from
    # data/vti-defaults.json; changing the JSON intentionally requires
    # updating these anchors too — that's the deliberate friction.
    if name == "contact":
        anchors = [
            "info@vti.com.vn",
            "VTI.JSC",
            "vti.com.vn",
            "VIETNAM HEADQUARTER",
        ]
        missing = [a for a in anchors if a not in html]
        if missing:
            raise ValidationError(
                "canonical_data_missing", f"compose_special_page({name})",
                f"contact rendered without canonical VTI strings: {missing} — "
                "either data/vti-defaults.json was bypassed, or the file was "
                "edited away from the canonical contact deck",
            )


# ===========================================================================
# Skill integrity validator (call once before bundling/publishing)
# ===========================================================================
def validate_skill_integrity() -> dict:
    """Scan the skill on disk and return a structured report.

    Run before packaging the skill so missing files / corrupted defaults /
    deleted assets surface as a hard error before the skill ships.

    Returns a dict ``{"ok": bool, "errors": [...], "checks": [...]}`` —
    no exceptions raised; caller inspects ``ok`` and ``errors``.
    """
    report: dict = {"ok": True, "errors": [], "checks": []}

    def _check(label: str, condition: bool, error_msg: str = "") -> None:
        report["checks"].append((label, condition))
        if not condition:
            report["ok"] = False
            report["errors"].append(error_msg or label)

    # 13 special-page directories with page.html + page.css
    for page_name in sorted(SPECIAL_PAGES.keys()):
        d = SPECIAL_PAGES_DIR / page_name
        _check(f"special-pages/{page_name}/page.html exists",
               (d / "page.html").is_file(),
               f"missing: special-pages/{page_name}/page.html")
        _check(f"special-pages/{page_name}/page.css exists",
               (d / "page.css").is_file(),
               f"missing: special-pages/{page_name}/page.css")

    # data/vti-defaults.json — single source of truth
    _check("data/vti-defaults.json exists", _DEFAULTS_PATH.is_file(),
           "missing: data/vti-defaults.json (canonical brand defaults)")
    if _DEFAULTS_PATH.is_file():
        contact = _CANONICAL_DEFAULTS.get("contact", {})
        _check("vti-defaults.json has canonical email",
               any(c.get("text") == "info@vti.com.vn"
                   for c in contact.get("channels", [])),
               "vti-defaults.json: contact.channels missing info@vti.com.vn")
        _check("vti-defaults.json has 4 office regions",
               len(contact.get("offices", [])) == 4,
               f"vti-defaults.json: expected 4 offices, "
               f"got {len(contact.get('offices', []))}")

    # Critical assets
    for asset in ("logo-vti-apac-blue.png", "logo-vti-apac-white.png",
                  "cover-bg-tokyo.jpg", "toc-mesh.jpg", "divider-visual.png",
                  "flag-vn.png", "flag-jp.png", "flag-kr.png", "flag-sg.png"):
        _check(f"assets/{asset} exists", (ASSETS_DIR / asset).is_file(),
               f"missing asset: assets/{asset}")

    # Tokens + chrome
    _check("tokens.css exists", TOKENS_PATH.is_file(),
           "missing: tokens.css")
    _check("chrome/header.css exists",
           (CHROME_DIR / "header.css").is_file(),
           "missing: chrome/header.css")

    return report


# ---------------------------------------------------------------------------
# v3.13.1 — TOC entry-text aliasing
# ---------------------------------------------------------------------------
_TOC_TITLE_ALIASES = ("title", "label", "name", "section")


def _normalize_toc_items(items: list) -> list:
    """Normalize TOC entries so the template's ``{{this.title}}`` lookup
    finds text whether the caller used ``title``, ``label``, ``name``, or
    ``section``. First non-empty wins. Also recursively normalizes
    nested ``items``.

    Entries that are not dicts are passed through unchanged.
    """
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            out.append(it)
            continue
        new = dict(it)
        if not new.get("title"):
            for alias in _TOC_TITLE_ALIASES[1:]:
                if new.get(alias):
                    new["title"] = new[alias]
                    break
        if isinstance(new.get("items"), list):
            new["items"] = _normalize_toc_items(new["items"])
        out.append(new)
    return out


def compose_special_page(name: str, props: dict | None = None) -> dict:
    """Render one of the 13 lift-and-shift special pages.

    Args:
        name:  page identifier (e.g. ``"cover"``, ``"toc"``, ``"closing"``).
               Must be a key of ``SPECIAL_PAGES``.
        props: prop dict matching the page's schema (see ``SPECIAL_PAGES``).

    Returns:
        ``{"slide_html": str, "slide_css": str, "metadata": {...}}`` —
        same shape as ``compose_slide_grid`` so a deck can mix both.
    """
    props = dict(props or {})
    if name not in SPECIAL_PAGES:
        raise ValidationError(
            "unknown_special_page", name,
            f"valid: {sorted(SPECIAL_PAGES.keys())}",
        )
    schema = SPECIAL_PAGES[name]

    # Validate required props
    for key in schema.get("required", []):
        if key not in props or props[key] in ("", None, []):
            raise ValidationError(
                "missing_required_prop",
                f"compose_special_page({name})",
                f"prop '{key}' is required",
            )

    # Build render context — defaults first, then user props (uppercased keys
    # to match the {{UPPER_CASE}} convention in templates). Lists/dicts pass
    # through as-is for the {{#each}} engine.
    ctx: dict[str, Any] = {}
    for k, v in schema.get("optional", {}).items():
        ctx[k.upper()] = v
    for k, v in props.items():
        ctx[k.upper()] = v

    # Derive BREADCRUMB for narrator pages from section_name + slide_title,
    # mirroring chrome's logic.
    if schema.get("has_chrome") and "BREADCRUMB" not in ctx:
        ctx["BREADCRUMB"] = _build_breadcrumb_html(
            ctx.get("SECTION_NAME", ""),
            ctx.get("SLIDE_TITLE", ""),
        )
    # Format page number with zero-padding (chrome convention)
    if "PAGE_NUM" in ctx:
        try:
            ctx["PAGE_NUM"] = f'{int(ctx["PAGE_NUM"]):02d}'
        except (TypeError, ValueError):
            pass

    # Contact page: auto-fill icon_svg for any channel that supplies a
    # known `type` but not its own `icon_svg`. Lets callers pass the
    # minimal `[{type, text}]` shape and get rendered icons for free.
    if name == "contact" and isinstance(ctx.get("CHANNELS"), list):
        enriched: list[Any] = []
        for ch in ctx["CHANNELS"]:
            if (isinstance(ch, dict)
                    and not ch.get("icon_svg")
                    and ch.get("type") in _CONTACT_CHANNEL_ICONS):
                ch = {**ch, "icon_svg": _CONTACT_CHANNEL_ICONS[ch["type"]]}
            enriched.append(ch)
        ctx["CHANNELS"] = enriched

    # TOC page: normalize entry text-field aliases (v3.13.1 fix).
    # The template uses `{{this.title}}` and `{{this.page}}`, but external
    # callers historically pass `label` (the v3.x deck-build scripts did
    # this) or `name`. Without normalization those aliases render as empty
    # strings → bullets + page-numbers visible but no entry text. Map
    # `label`/`name` → `title` (only when `title` itself is missing).
    if name == "toc" and isinstance(ctx.get("TOC_ITEMS"), list):
        ctx["TOC_ITEMS"] = _normalize_toc_items(ctx["TOC_ITEMS"])

    # Load templates
    page_dir  = SPECIAL_PAGES_DIR / name
    page_html = _read_file(page_dir / "page.html")
    page_css  = _read_file(page_dir / "page.css")

    # Apply template engine + resolve logo markers
    rendered_html = _fill_template(page_html, ctx)
    rendered_html = _resolve_logo_markers(rendered_html)

    # Inline ALL local asset references (url('../assets/...') in CSS,
    # <img src="..."> in HTML) as base64 data URLs, so the produced HTML
    # is self-contained and renders correctly when served from any path.
    # Search order: the page's own dir first (handles ./assets/...), then
    # the skill root (handles ../../assets/... and bare asset names).
    asset_search_dirs = [page_dir, SKILL_ROOT]
    page_css      = _inline_assets_in_css(page_css, asset_search_dirs)
    rendered_html = _inline_assets_in_html(rendered_html, asset_search_dirs)

    # Bundle CSS: tokens always; chrome only when the page declares it.
    css_parts = [_read_file(TOKENS_PATH)]
    if schema.get("has_chrome"):
        css_parts.append(_read_file(CHROME_DIR / "header.css"))
        css_parts.append(_read_file(CHROME_DIR / "footer.css"))
    css_parts.append(page_css)
    full_css = "\n\n".join(filter(None, css_parts))

    # Self-policing: catch any of the 4 known regression classes here so
    # they fail loudly at the call site instead of becoming silent visual
    # bugs in a deck the user only notices later.
    _assert_special_page_clean(name, rendered_html, full_css)

    return {
        "slide_html": rendered_html,
        "slide_css":  full_css,
        "metadata": {
            "kind":               "special-page",
            "special_page":       name,
            "components_rendered": [f"special:{name}"],
        },
    }


def list_special_pages() -> list[str]:
    """Return the 13 registered special-page names."""
    return sorted(SPECIAL_PAGES.keys())


def describe_special_page(name: str) -> dict:
    """Return the schema entry for one special page (required + optional + flags)."""
    if name not in SPECIAL_PAGES:
        raise ValidationError(
            "unknown_special_page", name,
            f"valid: {sorted(SPECIAL_PAGES.keys())}",
        )
    return dict(SPECIAL_PAGES[name])


# ===========================================================================
# Case-study layout — sidebar + main panel + flexible body grid
# ===========================================================================
# Three named variants (mapping to the existing footer.css hooks):
#   • "split"        — variant A · standard
#   • "visual-split" — variant B · with-visual
#   • "arch-deep"    — variant C · architecture-deep
#
# All three share the same chrome (dark sidebar with VTI logo + customer
# metadata + copyright; main panel with title bar + subhead + body grid +
# page badge footer). They differ only in subtle CSS tweaks that emphasize
# a media area or tighten vertical room for tall diagrams. The actual body
# composition is fully grid-based — same rows × cells contract as
# compose_slide_grid, so all 13 atomic components work inside.
# ---------------------------------------------------------------------------

_VALID_CS_VARIANTS = {"split", "visual-split", "arch-deep"}


def _build_cs_metadata_rows(meta: list) -> str:
    """Render the sidebar metadata rows (icon + label + emphasized value)."""
    rows_html = []
    for i, row in enumerate(meta or []):
        if not isinstance(row, dict):
            raise ValidationError(
                "invalid_value", f"compose_case_study.sidebar.metadata[{i}]",
                "each metadata entry must be a dict",
            )
        icon  = row.get("icon", "")
        label = row.get("label", "")
        value = row.get("value", "")
        if not (label or value):
            continue
        icon_svg = render_icon(icon) if icon else ""
        # Label + value rendered on the same paragraph; value gets the
        # yellow accent color (.cs-meta-row__value).
        text_parts = []
        if label:
            text_parts.append(
                f'<span class="cs-meta-row__label">{_esc(label)}</span>'
            )
        if value:
            text_parts.append(
                f'<span class="cs-meta-row__value">{_esc(value)}</span>'
            )
        rows_html.append(
            f'      <div class="cs-meta-row">\n'
            f'        <span class="cs-meta-row__icon">{icon_svg}</span>\n'
            f'        <div class="cs-meta-row__text">{"".join(text_parts)}</div>\n'
            f'      </div>'
        )
    return "\n".join(rows_html)


def compose_case_study(spec: dict) -> dict:
    """Render one case-study slide. Returns ``{slide_html, slide_css, metadata}``.

    Spec shape::

        {
          "variant":    "split" | "visual-split" | "arch-deep",  # default "split"
          "no_sidebar": False,                                   # True for continuation
          "case_meta": {
            "number":       "01",
            "code":         "CS01",
            "title":        "AI BOOKING & CONCIERGE CHATBOT",
            "title_suffix": "WORKFLOW",                # optional, after em-dash
          },
          "main": {
            "subhead": "Case study overview",
            "rows":    [...],                          # standard grid rows
          },
          "sidebar": {                                  # required unless no_sidebar
            "customer_name": "Censored Hotel A",
            "metadata": [
              {"icon": "world",  "label": "Headquartered", "value": "in Southeast Asia"},
              ...
            ],
          },
          "footer": {                                   # used to build chrome footer
            "page_number":  "06",
            "doc_title":    "VTI APAC · GenAI for Hospitality",
            "copyright_year": 2026,
          },
        }

    Multi-slide cases: pass the SAME case_meta on every slide of the case;
    page 2+ pass `no_sidebar: True`. The breadcrumb, chrome footer, and
    doc_title remain identical across the case so the deck visually links
    every page back to the lead slide — no special "continuation" framing.
    """
    if not isinstance(spec, dict):
        raise ValidationError("invalid_type", "compose_case_study.spec",
                              "spec must be a dict")

    variant    = spec.get("variant", "split")
    no_sidebar = bool(spec.get("no_sidebar", False))

    if variant not in _VALID_CS_VARIANTS:
        raise ValidationError(
            "invalid_value", "compose_case_study.variant",
            f"must be one of {sorted(_VALID_CS_VARIANTS)}",
        )

    case_meta = spec.get("case_meta") or {}
    main_spec = spec.get("main") or {}
    sidebar   = spec.get("sidebar") or {}
    footer    = spec.get("footer") or {}

    # Required-field gate
    if not case_meta.get("title"):
        raise ValidationError("missing_required",
                              "compose_case_study.case_meta.title", "")
    if not main_spec.get("rows"):
        raise ValidationError("missing_required",
                              "compose_case_study.main.rows", "")
    if not no_sidebar and not sidebar.get("customer_name"):
        raise ValidationError(
            "missing_required",
            "compose_case_study.sidebar.customer_name",
            "required when no_sidebar is False (the default)",
        )

    # ── Render body grid via shared helper ───────────────────────────────
    _USED_COMPONENTS_THIS_RENDER.clear()
    body_grid_html, _top_components, _warnings = _compose_grid_body(
        main_spec["rows"], where_prefix="main.rows"
    )

    # ── Build slide_meta for chrome ──────────────────────────────────────
    # Chrome breadcrumb composes "<section> | <title>" with .bc-section
    # and .bc-title styling. Map case fields:
    #   section_name = "CASE 01"
    #   slide_title  = "CS01 · AI BOOKING & CONCIERGE CHATBOT — WORKFLOW"
    case_num = str(case_meta.get("number", "")).strip()
    section_name = f"CASE {case_num}" if case_num else ""
    code_part   = case_meta.get("code", "").strip()
    title_part  = case_meta.get("title", "").strip()
    suffix_part = case_meta.get("title_suffix", "").strip()
    slide_title = ""
    if code_part:
        slide_title = f"{code_part} · {title_part}"
    else:
        slide_title = title_part
    if suffix_part:
        slide_title = f"{slide_title} — {suffix_part}"

    chrome_meta = {
        "section_name":    section_name,
        "slide_title":     slide_title,
        "page_number":     footer.get("page_number", 0),
        "page_total":      footer.get("page_total", 0),
        "doc_title":       footer.get("doc_title", ""),
        "copyright_year":  footer.get("copyright_year", 2026),
    }
    # When the sidebar is present, the standard top-right chrome logo
    # sits ON the dark sidebar — render it in its white variant so it
    # reads against the dark background. When no sidebar, default
    # full-color is correct (logo on white main panel). Same SIZE and
    # SAME POSITION in both cases — single chrome system, one logo.
    chrome_logo_variant = "full-color" if no_sidebar else "full-white"
    header_html, footer_html, chrome_css = _render_chrome(
        chrome_meta, logo_variant=chrome_logo_variant
    )

    # ── Build sidebar HTML (or empty for no_sidebar slides) ──────────────
    # NOTE: the sidebar does NOT render its own logo — the standard chrome
    # `.logo-tr` (already rendered by _render_chrome above) handles the
    # top-right logo on every CS slide, with variant flipped white for
    # has-sidebar context. This keeps logo size + position identical with
    # all other slides in the deck.
    sidebar_html = ""
    if not no_sidebar:
        meta_rows = _build_cs_metadata_rows(sidebar.get("metadata", []))
        sidebar_html = (
            f'<aside class="cs-sidebar">\n'
            f'  <div class="cs-sidebar__customer">'
            f'{_esc(sidebar.get("customer_name", ""))}</div>\n'
            f'  <div class="cs-sidebar__meta">\n'
            f'    {meta_rows}\n'
            f'  </div>\n'
            f'</aside>'
        )

    # ── Compose final HTML via template ──────────────────────────────────
    sidebar_class = " has-sidebar" if not no_sidebar else " no-sidebar"

    page_html = _read_file(SPECIAL_PAGES_DIR / "case-study" / "page.html")
    page_css  = _read_file(SPECIAL_PAGES_DIR / "case-study" / "page.css")

    rendered_html = _fill(page_html, {
        "VARIANT":         variant,
        "SIDEBAR_CLASS":   sidebar_class,
        "HEADER_HTML":     header_html,
        "SUBHEAD":         _esc(main_spec.get("subhead", "")),
        "BODY_GRID_HTML":  body_grid_html,
        "FOOTER_HTML":     footer_html,
        "SIDEBAR_HTML":    sidebar_html,
    })

    rendered_html = _resolve_logo_markers(rendered_html)

    # ── CSS bundle: tokens + chrome + grid + components + case-study ────
    all_used = sorted(_USED_COMPONENTS_THIS_RENDER)
    component_css_parts = [_component_css(c) for c in all_used]
    css_parts = [
        _read_file(TOKENS_PATH),
        chrome_css,                # standard chrome (header + footer)
        _GRID_CSS,                 # base grid for .vti-grid / .vti-grid-cell
        *component_css_parts,
        page_css,                  # case-study layout (sidebar overlay + tweaks)
    ]
    full_css = "\n\n".join(filter(None, css_parts))

    # ── Inline assets ────────────────────────────────────────────────────
    asset_search_dirs = [
        SPECIAL_PAGES_DIR / "case-study",
        SKILL_ROOT,
    ]
    full_css      = _inline_assets_in_css(full_css, asset_search_dirs)
    rendered_html = _inline_assets_in_html(rendered_html, asset_search_dirs)

    # ── Run integrity guards (skip contact canonical-data check) ────────
    _assert_special_page_clean("case-study", rendered_html, full_css)

    return {
        "slide_html": rendered_html,
        "slide_css":  full_css,
        "metadata": {
            "kind":               "case-study",
            "variant":            variant,
            "no_sidebar":         no_sidebar,
            "components_rendered": all_used,
            "case_code":          case_meta.get("code", ""),
        },
    }


# ===========================================================================
# Deck-level renderer — multi-slide aggregator with CSS dedup
# ===========================================================================
def compose_deck(slides: list) -> dict:
    """Render a list of slides into one deck blob, deduplicating CSS.

    Each item in ``slides`` is one of:

      1. A regular slide_input dict (the kind that ``compose_slide_grid``
         consumes).
      2. A special-page descriptor: ``{"special": <name>, "props": {...}}``
         — routed to ``compose_special_page``.

    Returns:
        {
          "deck_html":         str,            # all slides' HTML, in order
          "slide_htmls":       list[str],      # per-slide HTML for custom shells
          "deck_css":          str,            # ONE deduplicated CSS bundle
          "slide_metadatas":   list[dict],     # per-slide metadata, in order
        }

    Why this exists: ``compose_slide_grid`` returns a self-contained
    ``slide_css`` per slide (tokens + chrome + grid + that slide's
    components). Stacking N slides naively repeats tokens/chrome N times,
    AND if you only keep slide 1's CSS you lose component CSS used by
    later slides. ``compose_deck`` splits each slide's CSS by its join
    boundary (``\\n\\n``) and dedupes chunks across the whole deck — so
    each component's CSS appears at most once and the deck is small.
    """
    if not isinstance(slides, list) or not slides:
        raise ValidationError(
            "compose_deck", "input",
            "slides must be a non-empty list",
        )

    htmls: list[str] = []
    metas: list[dict] = []
    seen: set[str] = set()
    chunks: list[str] = []

    for i, item in enumerate(slides):
        if isinstance(item, dict) and "special" in item:
            out = compose_special_page(item["special"], item.get("props", {}))
        elif isinstance(item, dict) and item.get("kind") == "case-study":
            out = compose_case_study(item)
        elif isinstance(item, dict) and "rows" in item:
            out = compose_slide_grid(item)
        else:
            raise ValidationError(
                "compose_deck", f"slides[{i}]",
                "each item must be a slide_input dict (with 'rows') or "
                "a special-page descriptor (with 'special')",
            )
        htmls.append(out["slide_html"])
        metas.append(out["metadata"])
        for ch in out["slide_css"].split("\n\n"):
            ch = ch.strip()
            if ch and ch not in seen:
                seen.add(ch)
                chunks.append(ch)

    return {
        "deck_html":       "\n".join(htmls),
        "slide_htmls":     htmls,
        "deck_css":        "\n\n".join(chunks),
        "slide_metadatas": metas,
    }


# ===========================================================================
# outline_to_deck — high-level orchestrator
# ===========================================================================
#
# `compose_deck` is the lowest-level deck assembler: every slide must be a
# fully-formed slide_input / special_page / case_study descriptor.
#
# `outline_to_deck` is one step higher. The user gives a thin outline of
# slide INTENTS (cover, toc, divider, content, case-study, contact, closing)
# and the orchestrator:
#
#   • auto-fills page_number / page_total / doc_title / copyright_year
#   • auto-picks components from short snake_case `kind` aliases
#   • auto-assigns col_start across cells in a row from col_span sums
#   • auto-builds TOC items from divider + content/case-study items
#   • picks sensible row heights (default "auto")
#
# Returns the same shape as `compose_deck` so consumers don't change.
# ---------------------------------------------------------------------------

# Outline-time `kind` → component name. Snake_case for ergonomics.
# Aliases collapse common variations to one component (kpis ≡ kpi_row, etc.).
BLOCK_KIND_MAP: dict[str, str] = {
    "stat":            "stat-hero",
    "stat_hero":       "stat-hero",
    "stat_mini":       "stat-mini",
    "narrative":       "narrative-paragraph",
    "paragraph":       "narrative-paragraph",
    "practice_card":          "practice-card",
    "practice_card_leveled":  "practice-card-leveled",
    "leveled_principles":     "practice-card-leveled",
    "kpi_row":         "kpi-row",
    "kpis":            "kpi-row",
    "bullets":         "bullet-list-checked",
    "checklist":       "bullet-list-checked",
    "image":           "image-tile",
    "logos":           "logo-grid",
    "logo_grid":       "logo-grid",
    "quote":           "quote-block",
    "process":         "process-flow",
    "section_header":  "section-header",
    "subhead":         "section-header",
    "catalog":         "catalog-column",
    "value":           "value-medallion",
    "vs":              "vs-divider",

    # Phase E1 — data display
    "table":           "table",
    "data_table":      "table",
    "bar_chart":       "bar-chart",
    "column_chart":    "bar-chart",      # vertical bar = "column"
    "pie_chart":       "pie-chart",
    "donut_chart":     "pie-chart",      # donut is a pie variant
    "trend_stat":      "trend-stat",
    "kpi_movement":    "trend-stat",

    # Phase E2 — process / structure
    "swimlane":        "swimlane",
    "process_lanes":   "swimlane",
    "timeline":        "timeline",
    "funnel":          "funnel",
    "conversion_funnel": "funnel",
    "quadrant":        "quadrant-matrix",
    "matrix_2x2":      "quadrant-matrix",
    "quadrant_matrix": "quadrant-matrix",

    # Phase E3 — comparison / context
    "comparison_table": "comparison-table",
    "feature_matrix":   "comparison-table",
    "callout":         "callout",
    "note":            "callout",
    "warning":         "callout",
    "tip":             "callout",
    "before_after":    "before-after",
    "transformation":  "before-after",
    "vs_compare":      "vs-compare",
    "comparison_story": "vs-compare",
    "pull_vs_push":    "vs-compare",
    "icon_list":       "icon-list",
    "feature_list":    "icon-list",

    # Phase E4 — numbers / progress
    "progress_bar":    "progress-bar",
    "progress_bars":   "progress-bar",
    "okr_tracker":     "progress-bar",
    "gauge":           "gauge-dial",
    "gauge_dial":      "gauge-dial",
    "stacked_bar":     "stacked-bar",
    "composition_chart": "stacked-bar",
    "line_chart":      "line-chart",
    "trend_chart":     "line-chart",

    # Paragraph / text components
    "lead_paragraph":  "lead-paragraph",
    "lede":            "lead-paragraph",
    "headline":        "headline",
    "hero_statement":  "headline",
    "kicker":          "kicker",
    "eyebrow":         "kicker",
    "topic_label":     "kicker",
    "numbered_list":   "numbered-list",
    "ordered_list":    "numbered-list",
    "ranked_list":     "numbered-list",
    "definition_list": "definition-list",
    "key_value":       "definition-list",
    "spec_sheet":      "definition-list",
    "tags":             "tags",
    "chips":            "tags",
    "badges":           "tags",
    "pull_quote":      "pull-quote",
    "editorial_quote": "pull-quote",
}

# Layout-only fields that must NOT pass into component props.
_LAYOUT_FIELDS = {"kind", "col_start", "col_span", "row_span"}


def _block_to_props(block: dict) -> tuple[str, dict]:
    """Strip layout-only fields and apply per-kind normalization.

    Returns (component_name, props_dict).
    """
    if not isinstance(block, dict):
        raise ValidationError(
            "invalid_type", "content block",
            f"each block must be a dict, got {type(block).__name__}",
        )
    kind = block.get("kind")
    if not kind or kind not in BLOCK_KIND_MAP:
        raise ValidationError(
            "unknown_kind", f"block.kind={kind!r}",
            f"valid kinds: {sorted(BLOCK_KIND_MAP.keys())}",
        )
    component = BLOCK_KIND_MAP[kind]
    props = {k: v for k, v in block.items() if k not in _LAYOUT_FIELDS}

    # Per-kind normalization
    if kind in ("narrative", "paragraph"):
        # narrative-paragraph component takes `paragraphs: list[str]`. The
        # outline-level shorthand `text: str` wraps to a one-element list.
        if "text" in props and "paragraphs" not in props:
            text = props.pop("text")
            props["paragraphs"] = [text] if isinstance(text, str) else list(text)

    return component, props


def _pack_blocks_to_cells(content_rows: list, where: str) -> list:
    """Convert outline content_rows into compose_slide_grid rows × cells.

    Each row in `content_rows` is one of:
      • list of block dicts            — uses default row height "auto"
      • dict {height, blocks}          — explicit row height

    Auto-assigns col_start by accumulating col_span (1-12 grid).
    """
    if not isinstance(content_rows, list):
        raise ValidationError(
            "invalid_type", f"{where}.rows",
            "rows must be a list",
        )
    if not content_rows:
        raise ValidationError(
            "missing_required", f"{where}.rows",
            "rows cannot be empty",
        )

    out_rows = []
    for ri, row_in in enumerate(content_rows):
        if isinstance(row_in, list):
            blocks, row_height = row_in, "auto"
        elif isinstance(row_in, dict):
            blocks = row_in.get("blocks", [])
            row_height = row_in.get("height", "auto")
        else:
            raise ValidationError(
                "invalid_type", f"{where}.rows[{ri}]",
                "each row must be a list of blocks OR a dict {height, blocks}",
            )

        if not blocks:
            raise ValidationError(
                "empty_row", f"{where}.rows[{ri}]",
                "each row must contain at least one block",
            )

        col_pos = 1
        cells = []
        for bi, block in enumerate(blocks):
            try:
                component, props = _block_to_props(block)
            except ValidationError as e:
                # Re-raise with row context (use the .field attr, not .where)
                e.field = f"{where}.rows[{ri}].blocks[{bi}].{e.field}"
                raise

            col_span  = block.get("col_span", 12)
            col_start = block.get("col_start", col_pos)
            row_span  = block.get("row_span", 1)

            cells.append({
                "col_start": col_start,
                "col_span":  col_span,
                "row_span":  row_span,
                "component": component,
                "props":     props,
            })
            col_pos = col_start + col_span

        out_rows.append({"height": row_height, "cells": cells})

    return out_rows


def _auto_build_toc(outline: list) -> list:
    """Scan an outline and build TOC items.

    Structure: each `divider` opens a new section. Subsequent `content`
    items and `case-study` LEAD slides (those WITH a sidebar) are added
    as sub-bullets. Continuation case-study slides (no_sidebar=True) and
    framing slides (cover, toc, contact, closing) are skipped — they're
    not natural TOC entries.
    """
    toc_items = []
    current_section = None

    for i, item in enumerate(outline):
        page_num = i + 1
        t = item.get("type")

        if t in ("divider", "section-divider"):
            current_section = {
                "title": item.get("title", ""),
                "page":  f"{page_num:02d}",
                "items": [],
            }
            toc_items.append(current_section)

        elif t == "content" and current_section is not None:
            current_section["items"].append({
                "title": item.get("title", ""),
                "page":  f"{page_num:02d}",
            })

        elif t == "case-study" and current_section is not None \
                and not item.get("no_sidebar", False):
            cm = item.get("case_meta", {})
            label = (f"{cm.get('code', 'CS')} · {cm.get('title', '')}"
                     if cm.get("code") else cm.get("title", ""))
            current_section["items"].append({
                "title": label,
                "page":  f"{page_num:02d}",
            })

    return toc_items


def _outline_to_descriptor(item: dict, page_num: int, total: int,
                           doc_title: str, copyright_year: int,
                           deck_title: str = "",
                           deck_tagline: str = "") -> dict:
    """Convert one outline item to a compose_deck descriptor."""
    if not isinstance(item, dict):
        raise ValidationError(
            "invalid_type", f"outline[{page_num - 1}]",
            "each outline item must be a dict",
        )
    t = item.get("type")
    if not t:
        raise ValidationError(
            "missing_required", f"outline[{page_num - 1}].type",
            "each outline item needs a `type`",
        )
    where = f"outline[{page_num - 1}]"

    if t == "cover":
        return {"special": "cover", "props": {
            "deck_title":   item.get("title",   deck_title) or "VTI APAC",
            "deck_tagline": item.get("tagline", deck_tagline) or "",
        }}

    if t == "toc":
        return {"special": "toc", "props": {
            "doc_title":      doc_title,
            "page_num":       page_num,
            "copyright_year": copyright_year,
            "toc_items":      item.get("toc_items", []),
            "toc_cols":       item.get("toc_cols", 1),
        }}

    if t in ("divider", "section-divider"):
        return {"special": "section-divider", "props": {
            "section_title":       item.get("title", ""),
            "section_description": item.get("description", ""),
        }}

    if t == "contact":
        return {"special": "contact", "props": item.get("props", {})}

    if t == "closing":
        return {"special": "closing", "props": {
            "closing_message": item.get("message", ""),
        }}

    if t == "content":
        slide_meta = {
            "page_number":    page_num,
            "page_total":     total,
            "doc_title":      doc_title,
            "copyright_year": copyright_year,
            "section_name":   item.get("section", ""),
            "slide_title":    item.get("title", ""),
        }
        rows = _pack_blocks_to_cells(item.get("rows", []), where)
        return {"slide_meta": slide_meta, "rows": rows}

    if t == "case-study":
        cs = {
            "kind":       "case-study",
            "variant":    item.get("variant", "split"),
            "no_sidebar": bool(item.get("no_sidebar", False)),
            "case_meta":  item.get("case_meta", {}),
            "main": {
                "subhead": item.get("main_subhead", ""),
                "rows":    _pack_blocks_to_cells(item.get("rows", []), where),
            },
            "footer": {
                "page_number":    page_num,
                "page_total":     total,
                "doc_title":      doc_title,
                "copyright_year": copyright_year,
            },
        }
        if not cs["no_sidebar"]:
            cs["sidebar"] = item.get("sidebar", {})
        return cs

    raise ValidationError(
        "unknown_outline_type", f"{where}.type",
        f"got {t!r}; valid: cover, toc, divider, content, "
        f"case-study, contact, closing",
    )


def outline_to_deck(spec: dict) -> dict:
    """High-level orchestrator: outline → rendered deck.

    Spec shape::

        {
          "doc_title":      "VTI APAC capabilities pitch 2026",
          "deck_title":     "VTI APAC",                    # for cover
          "deck_tagline":   "Capabilities pitch · 2026",   # for cover
          "copyright_year": 2026,                          # default 2026
          "outline": [
            {"type": "cover"},                # uses deck_title/tagline
            {"type": "toc"},                  # auto-builds items
            {"type": "divider", "title": "01 / About",
             "description": "..."},
            {"type": "content",
             "section": "About", "title": "Three practices",
             "rows": [
                # row 1
                [{"kind": "stat_hero", "value": "1,200+",
                  "label": "Engineers", "col_span": 5},
                 {"kind": "narrative", "text": "...", "col_span": 7}],
                # row 2 (auto-fills col_start)
                [{"kind": "practice_card", "title": "...", "body": "...",
                  "icon": "brain", "col_span": 4} for _ in range(3)],
             ]},
            {"type": "case-study",
             "case_meta": {"number": "01", "code": "CS01", "title": "..."},
             "variant": "split",
             "main_subhead": "Case study overview",
             "rows": [...],
             "sidebar": {"customer_name": "...", "metadata": [...]}},
            {"type": "case-study", "no_sidebar": True,
             "case_meta": {**CS01_META, "title_suffix": "ARCHITECTURE"},
             "rows": [...]},
            {"type": "contact"},
            {"type": "closing", "message": "Hello@vti-apac.com"},
          ],
        }

    Returns the same shape as `compose_deck`.
    """
    if not isinstance(spec, dict):
        raise ValidationError(
            "invalid_type", "outline_to_deck.spec",
            "spec must be a dict",
        )

    outline = spec.get("outline")
    if not outline or not isinstance(outline, list):
        raise ValidationError(
            "missing_required", "outline_to_deck.spec.outline",
            "outline must be a non-empty list",
        )

    doc_title      = spec.get("doc_title", "")
    deck_title     = spec.get("deck_title", "")
    deck_tagline   = spec.get("deck_tagline", "")
    copyright_year = int(spec.get("copyright_year", 2026))

    total = len(outline)

    # Auto-fill TOC items if a `toc` outline item omits `toc_items`.
    auto_toc = _auto_build_toc(outline)
    for item in outline:
        if isinstance(item, dict) and item.get("type") == "toc" \
                and not item.get("toc_items"):
            item["toc_items"] = auto_toc

    # Convert each outline item to a compose_deck descriptor.
    descriptors = []
    for i, item in enumerate(outline):
        descriptors.append(_outline_to_descriptor(
            item, i + 1, total, doc_title, copyright_year,
            deck_title, deck_tagline,
        ))

    return compose_deck(descriptors)
