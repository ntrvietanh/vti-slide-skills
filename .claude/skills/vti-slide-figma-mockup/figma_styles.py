"""Brand-style instruction blocks for Figma mockup briefs.

The blocks here are plain-English paragraphs handed to ``use_figma`` so
the design model paints the UI in VTI brand colors / a neutral palette
/ a dark-mode palette. Hex literals mirror
``vti-slide-page-builder/tokens.css`` — when tokens drift, update both.

Not pulling tokens.css at runtime by design: the brief is a stable
text contract, not a derived asset. Embedding hex literals lets the
brief be reviewed as a unit without a tokens.css fetch.
"""
from __future__ import annotations

# Mirror of tokens.css --vti-* color family. If tokens.css moves these,
# update here too — verified by `python -c "import theme_bridge"` smoke test.
_VTI_PALETTE = {
    "navy":       "#051934",
    "blue-deep":  "#0844A4",
    "blue":       "#004AAD",
    "blue-mid":   "#1B5DE6",
    "bright":     "#0468E6",
    "sky":        "#0782FF",
    "light":      "#DAE9F6",
    "paleblue":   "#EAF2FB",
    "ink":        "#1F2A3A",
    "ink-soft":   "#4B5A6E",
    "muted":      "#6B7A8D",
    "border":     "#C8DCF0",
    "bg":         "#F0F5FB",
}


def brand_style_block() -> str:
    """Style instructions for ``style="brand-vti"``."""
    p = _VTI_PALETTE
    return f"""
Use the VTI brand palette — blues only for primary surfaces, no rainbow
accents. Core colors:

- Primary action / brand fill: {p['blue']} (deeper buttons {p['blue-deep']},
  hover {p['blue-mid']}, links {p['bright']}).
- Header / cover dark fill: {p['navy']}.
- Surface tint / subtle background: {p['light']} or {p['paleblue']}.
- Slide page background: {p['bg']}.
- Body text: {p['ink']}. Secondary text: {p['ink-soft']}. Captions / muted:
  {p['muted']}.
- Card / table borders: {p['border']}. Divider hairlines: {p['border']} at
  40% opacity.

Typography: Plus Jakarta Sans for both display and body (fallback Arial,
system-ui). Sizes target the VTI scale: hero 64 px, display 32 px,
section title 24 px, card title 18 px, body 15 px, caption 12 px.

Corner radius: 8 px on cards and panels, 10 px on buttons, 50% on
avatars. Drop shadows are subtle — 0 4 12 rgba(5,25,52,.08) max. No
neon glow, no gradients beyond {p['blue']} → {p['sky']}.

Iconography: outlined / stroked icons at 1.5 px stroke. Avoid filled
emoji icons unless explicitly asked.
""".strip()


def neutral_style_block() -> str:
    """Style instructions for ``style="neutral"`` (third-party UIs,
    wireframes)."""
    return """
Use a generic modern-SaaS visual style. Primary surface white
(#FFFFFF), page background slate-50 (#F8FAFC). Brand color is a single
muted indigo (#4F46E5) — used sparingly for primary actions only.
Body text slate-900 (#0F172A), secondary slate-600 (#475569), captions
slate-400 (#94A3B8). Borders slate-200 (#E2E8F0).

Typography: Inter or system-ui. Common SaaS sizes: 14 px body, 16 px
section headings, 24 px page titles. Corner radius 6-8 px. Subtle
shadows only. No brand-specific logos or colors — this is intentionally
generic so it can stand in for any third-party product.

Iconography: outlined icons, 1.5 px stroke.
""".strip()


def dark_style_block() -> str:
    """Style instructions for ``style="dark-mode"``."""
    p = _VTI_PALETTE
    return f"""
Dark mode variant of the VTI palette. Surfaces: slate-900 (#0F172A) for
the deepest layer, slate-800 (#1E293B) for cards. Page background
slate-950 (#020617).

Brand accent stays VTI blue but shifted brighter for contrast:
{p['bright']} for primary actions, {p['sky']} for highlights and links.
Avoid the deep navy {p['navy']} — too low-contrast on dark.

Text: slate-100 (#F1F5F9) for primary, slate-300 (#CBD5E1) for
secondary, slate-500 (#64748B) for muted captions. Borders slate-700
(#334155). Hairlines slate-800 at 60% opacity.

Typography matches the brand-vti scale. Corner radius and shadows
match. Shadows on dark mode use rgba(0,0,0,.40) for noticeable depth.
""".strip()


__all__ = [
    "brand_style_block",
    "neutral_style_block",
    "dark_style_block",
]
