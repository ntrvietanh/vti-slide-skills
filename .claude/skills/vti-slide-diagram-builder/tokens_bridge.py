"""Parse VTI brand tokens from page-builder's tokens.css at module load.

The skill never hardcodes hex colour literals. Every colour reference
in the diagram primitives goes through ``TOKENS[<name>]`` so a change
in `tokens.css` propagates through automatically. A lint check at
verify-time greps the primitives for hex literals to enforce this.

Public surface
--------------
- ``TOKENS``                 — dict[str, str] of token-name → hex value
- ``ACCENT_TO_TOKEN``        — short accent alias → token name
- ``token(name)``            — safe getter (falls back to ink for unknowns)
- ``accent(alias)``          — short alias getter (e.g. ``accent("deep")``)
- ``font_body``              — the body font stack, derived from tokens
"""
from __future__ import annotations

import re
from pathlib import Path

# Resolve the page-builder skill at import time.
_THIS_DIR = Path(__file__).resolve().parent
_SKILLS_DIR = _THIS_DIR.parent  # .claude/skills/
_TOKENS_CSS = _SKILLS_DIR / "vti-slide-page-builder" / "tokens.css"


def _parse_tokens(css_path: Path) -> dict[str, str]:
    """Extract every ``--vti-*`` and ``--blue-*`` declaration into a dict.

    Robust against block-level grouping; only the first hex value per
    name is kept (the rest are usually media-query overrides).
    """
    out: dict[str, str] = {}
    if not css_path.exists():
        return out
    text = css_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+?)\s*;"
    )
    for m in pattern.finditer(text):
        name, value = m.group(1), m.group(2).strip()
        # Keep first wins
        out.setdefault(name, value)
    return out


# Module-level constant — parsed once at import.
TOKENS: dict[str, str] = _parse_tokens(_TOKENS_CSS)


# Short alias → token name (so primitives can write `accent("deep")`).
ACCENT_TO_TOKEN: dict[str, str] = {
    "navy":     "vti-navy",
    "deep":     "vti-blue-deep",
    "blue":     "vti-blue",
    "medium":   "vti-blue-medium",
    "bright":   "vti-bright",
    "sky":      "vti-sky",
    "light":    "vti-light",
    "pale":     "vti-paleblue",
    "amber":    "vti-amber",
    "orange":   "vti-orange",
    "teal":     "vti-teal",
    "green":    "vti-green",
    "red":      "vti-red",
    "magenta":  "vti-magenta",
    "purple":   "vti-purple",
    "ink":      "vti-ink",
    "ink-soft": "vti-ink-soft",
    "muted":    "vti-muted",
    "border":   "vti-border",
    "divider":  "vti-divider",
    "bg":       "vti-bg",
    "white":    "vti-white",
}


def token(name: str) -> str:
    """Safe getter — returns hex for token name, falling back to ink.

    Strips the leading '--' if the caller passed a CSS variable form.
    """
    key = name.lstrip("-")
    if key in TOKENS:
        return TOKENS[key]
    return TOKENS.get("vti-ink", "#1F2A3A")


def accent(alias: str) -> str:
    """Resolve a short alias to a hex value via ACCENT_TO_TOKEN.

    Falls back to vti-ink for unknown aliases so primitives never crash
    on a typo; instead the diagram renders with neutral ink.
    """
    return token(ACCENT_TO_TOKEN.get(alias, "vti-ink"))


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
    )


def tint(alias: str, ratio: float = 0.92) -> str:
    """Soft-tint background derived from an accent — mix accent with white.

    Used by quadrant cells, KPI bands, and other tinted backgrounds where
    the accent itself would be too dominant.

    ratio=0.92 means 92% white + 8% accent → very pale tint
    ratio=0.0  → pure accent
    ratio=1.0  → pure white
    """
    r, g, b = _hex_to_rgb(accent(alias))
    nr = int(r + (255 - r) * ratio)
    ng = int(g + (255 - g) * ratio)
    nb = int(b + (255 - b) * ratio)
    return _rgb_to_hex(nr, ng, nb)


# Pre-resolved common values used on every render.
font_body: str = TOKENS.get(
    "vti-font-body",
    "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
)


__all__ = [
    "TOKENS", "ACCENT_TO_TOKEN",
    "token", "accent", "tint",
    "font_body",
]
