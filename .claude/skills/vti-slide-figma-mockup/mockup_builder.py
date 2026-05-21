"""Public API — 8 standardised mockup kinds for VTI slide decks.

**Dual backend (v0.2.0)** — each ``make_*`` returns a task descriptor
the orchestrator (Claude in the loop) renders into a PNG. Pick the
backend via the ``backend`` kwarg or env var ``VTI_MOCKUP_BACKEND``:

- ``backend="html"`` (default) — pure-local Playwright + Chromium
  render. No external quota, deterministic, hand-editable HTML source
  travels with the PNG. Orchestrator writes ``body_html`` per screen.
- ``backend="figma"`` — Figma MCP render via ``use_figma``. Output
  travels with a Figma file URL for hand-editing in Figma. Subject to
  Figma plan quota (Starter = 6 calls / MONTH).

Task descriptor shape (common)::

    {
        "kind":         "screen-mobile" | ... ,
        "backend":      "html" | "figma",
        "frame_label":  str,            # e.g. "iPhone 15 Pro"
        "style":        "brand-vti" | "neutral" | "dark-mode",
        "hint_w":       int,            # canonical canvas width
        "hint_h":       int,            # canonical canvas height
        "title":        str,
        "subtitle":     str | None,
        "captions":     list[str] | None,
        # backend-specific extra fields:
        "brief":        str,            # figma backend: full use_figma prompt
        "html_brief":   str,            # html backend: hints for body_html author
    }

``hint_w / hint_h`` lets Phase 4 (``layout_designer``) pre-size the
hosting image-tile cell to the right aspect ratio so the mockup is
never cropped. After render, the executor overwrites with actual
pixel dimensions.

Brand-style hints come from ``theme_bridge.brand_style_block`` so they
stay in sync with ``vti-slide-page-builder/tokens.css``.
"""
from __future__ import annotations

import os
from typing import Any

from figma_styles import brand_style_block, neutral_style_block, dark_style_block

VERSION = "0.2.0"

# Default backend. Env override: VTI_MOCKUP_BACKEND={html|figma}
_DEFAULT_BACKEND = os.environ.get("VTI_MOCKUP_BACKEND", "html").lower()
if _DEFAULT_BACKEND not in ("html", "figma"):
    _DEFAULT_BACKEND = "html"

_VALID_BACKENDS = frozenset({"html", "figma"})


def _resolve_backend(backend: str | None) -> str:
    if backend is None:
        return _DEFAULT_BACKEND
    b = backend.lower()
    if b not in _VALID_BACKENDS:
        raise ValueError(
            f"backend must be 'html' or 'figma', got {backend!r}"
        )
    return b


# ---------------------------------------------------------------------------
# Canonical canvases per kind
# ---------------------------------------------------------------------------
# Sized so Phase 4 can pick a sensible aspect ratio. Numbers come from
# common device viewports (mobile = 480px-class, tablet = 1024, desktop =
# 1440) so the resulting hosting cell looks proportionate when placed
# inside the 1168×586 slide canvas.
_KIND_META: dict[str, dict[str, Any]] = {
    "screen-mobile": {
        "hint_w": 480, "hint_h": 960,
        "default_frame": "iPhone 15 Pro",
        "frame_instruction": (
            "Wrap the screen content inside a realistic iPhone 15 Pro device "
            "frame (titanium bezel, dynamic island, rounded corners). Show "
            "the iOS status bar at the top with full battery + 5G."
        ),
        "good_for": "single mobile app screen",
    },
    "screen-tablet": {
        "hint_w": 1024, "hint_h": 768,
        "default_frame": "iPad (landscape)",
        "frame_instruction": (
            "Wrap the screen content inside a realistic iPad landscape "
            "device frame (slim bezel, rounded corners, no home button)."
        ),
        "good_for": "single tablet UI screen",
    },
    "screen-desktop": {
        "hint_w": 1440, "hint_h": 900,
        "default_frame": "Chrome on macOS",
        "frame_instruction": (
            "Wrap the UI inside a realistic Chrome-on-macOS browser frame: "
            "traffic-light buttons (red/yellow/green) at top-left, "
            "rounded address bar in the center showing a plausible URL, "
            "tabs row above the address bar with the product name as the "
            "active tab."
        ),
        "good_for": "single desktop / web app screen",
    },
    "screen-bare": {
        "hint_w": 1180, "hint_h": 740,
        "default_frame": "(no frame)",
        "frame_instruction": (
            "Render the UI full-bleed without any device frame or browser "
            "chrome. Just the application surface."
        ),
        "good_for": "screen without device chrome — for hero crops or custom framing",
    },
    "flow-mobile": {
        "hint_w": 1440, "hint_h": 960,
        "default_frame": "iPhone × 3",
        "frame_instruction": (
            "Lay out exactly THREE iPhone 15 Pro frames side-by-side with "
            "20px gap between frames. Each frame shows a different screen "
            "in the user journey. Add a thin arrow between frames pointing "
            "left-to-right. If captions are provided, render each caption "
            "as a short label centered under its frame."
        ),
        "good_for": "3-screen mobile user journey strip",
    },
    "flow-desktop": {
        "hint_w": 1620, "hint_h": 540,
        "default_frame": "Browser × 3",
        "frame_instruction": (
            "Lay out exactly THREE compact browser frames side-by-side with "
            "20px gap between frames. Each frame shows a different screen "
            "in the user journey. Add a thin arrow between frames pointing "
            "left-to-right. If captions are provided, render each caption "
            "as a short label centered under its frame."
        ),
        "good_for": "3-screen desktop user journey strip",
    },
    "wireframe-mobile": {
        "hint_w": 480, "hint_h": 960,
        "default_frame": "iPhone (mono)",
        "frame_instruction": (
            "Render in low-fidelity wireframe style: grayscale only, gray "
            "rectangles for content blocks, single-line placeholders for "
            "text (lorem ipsum is fine), simple stroked icons. Wrap inside "
            "a minimal iPhone outline (no glossy frame, just a black "
            "stroke). NO color, NO shadows, NO photographs."
        ),
        "good_for": "low-fidelity mobile wireframe (early-stage demos)",
    },
    "wireframe-desktop": {
        "hint_w": 1440, "hint_h": 900,
        "default_frame": "Browser (mono)",
        "frame_instruction": (
            "Render in low-fidelity wireframe style: grayscale only, gray "
            "rectangles for content blocks, single-line placeholders for "
            "text, simple stroked icons. Wrap inside a minimal browser "
            "outline (just rectangles for the tab + address bars, no "
            "color). NO color, NO shadows, NO photographs."
        ),
        "good_for": "low-fidelity desktop wireframe",
    },
}


# ---------------------------------------------------------------------------
# Style block resolver
# ---------------------------------------------------------------------------
def _style_block(style: str) -> str:
    """Return the style-instruction paragraph for the Figma brief."""
    style = (style or "brand-vti").lower()
    if style == "brand-vti":
        return brand_style_block()
    if style == "neutral":
        return neutral_style_block()
    if style == "dark-mode":
        return dark_style_block()
    raise ValueError(
        f"style must be one of 'brand-vti' | 'neutral' | 'dark-mode', "
        f"got {style!r}"
    )


# ---------------------------------------------------------------------------
# Brief composer
# ---------------------------------------------------------------------------
def _compose_brief(
    *,
    kind: str,
    user_brief: str,
    title: str,
    subtitle: str | None,
    style: str,
    frame_label: str,
    frame_instruction: str,
    captions: list[str] | None,
) -> str:
    """Assemble the full Figma brief from semantic inputs.

    The brief is what gets passed to ``mcp__claude_ai_Figma__use_figma``
    as the design prompt. Structure:

      1. One-line subject
      2. Style block (palette, type, radii, etc.)
      3. Frame instruction (device / browser chrome)
      4. UI content (the user's brief, verbatim)
      5. Captions (for flow kinds)
      6. Hard constraints (no lorem unless wireframe, etc.)
    """
    lines: list[str] = []
    subject = title.strip()
    if subtitle:
        subject = f"{subject} — {subtitle.strip()}"
    lines.append(f"# Subject\n{subject}\n")

    lines.append(f"# Visual style\n{_style_block(style).strip()}\n")

    lines.append(f"# Frame ({frame_label})\n{frame_instruction.strip()}\n")

    lines.append(f"# UI content\n{user_brief.strip()}\n")

    if captions:
        cap_block = "\n".join(f"- {c}" for c in captions)
        lines.append(f"# Per-screen captions\n{cap_block}\n")

    # Hard constraints stay last so the design model sees them after
    # the freeform brief. Wireframe kinds skip the "real copy" rule.
    is_wireframe = kind.startswith("wireframe-")
    constraints = [
        "Output: single Figma frame at the natural canvas size hinted above.",
        "Do not invent VTI branding beyond what's specified in the style block.",
        "Do not place the company name 'VTI' on the mockup unless the user's brief calls for it.",
    ]
    if not is_wireframe:
        constraints.append(
            "Use realistic copy where possible — actual product names, "
            "plausible dates, real-sounding labels. Lorem ipsum only if "
            "the user's brief explicitly says so."
        )
    else:
        constraints.append(
            "This is a wireframe — placeholder boxes + lorem ipsum text "
            "are expected. Stay strictly grayscale."
        )
    constraints.append(
        "Do not include any marketing taglines, no 'Sign up for free' "
        "CTAs unless the brief asks for them."
    )
    lines.append("# Constraints\n" + "\n".join(f"- {c}" for c in constraints))

    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# Task builders — one per kind
# ---------------------------------------------------------------------------
def _compose_html_brief(
    *,
    kind: str,
    user_brief: str,
    title: str,
    subtitle: str | None,
    style: str,
    frame_label: str,
    frame_instruction: str,
    captions: list[str] | None,
) -> str:
    """HTML-backend brief.

    Unlike the Figma brief (which is the literal use_figma prompt), the
    HTML brief is a HINT to the orchestrator who will hand-author the
    body_html per screen. The brief tells WHAT to render (sections,
    cards, copy) — the HTML/CSS atoms come from ``html_backend``.
    """
    lines: list[str] = []
    subject = title.strip()
    if subtitle:
        subject = f"{subject} — {subtitle.strip()}"
    lines.append(f"# Subject\n{subject}\n")
    lines.append(f"# Style ({style})\nUse VTI brand tokens defined in html_backend's CSS — "
                 f"do NOT hardcode brand hex. Use CSS variables like var(--blue), "
                 f"var(--ink), var(--paleblue), etc. Reuse atom classes (.av, .chip, "
                 f".card, .sec-hdr-amber, etc.) — see html_backend._ATOMS_CSS.\n")
    lines.append(f"# Frame ({frame_label})\n{frame_instruction.strip()}\n"
                 f"NOTE — the outer frame is provided by html_backend.frame_html(); "
                 f"the orchestrator only writes body_html for each screen.\n")
    lines.append(f"# UI content\n{user_brief.strip()}\n")
    if captions:
        cap_block = "\n".join(f"- {c}" for c in captions)
        lines.append(f"# Per-screen captions\n{cap_block}\n")
    is_wireframe = kind.startswith("wireframe-")
    constraints = [
        "Output: an HTML fragment per screen (body_html) — NO <html>, <body>, or <style> tags.",
        "Reuse atom CSS classes from html_backend instead of inline styles where possible.",
        "Do not invent VTI branding beyond the style block. No company name 'VTI' on the mockup unless asked.",
    ]
    if not is_wireframe:
        constraints.append(
            "Use realistic copy — plausible names, dates, labels. Lorem ipsum only if the brief asks."
        )
    else:
        constraints.append(
            "Wireframe — gray placeholder boxes + lorem ipsum allowed. Strictly grayscale."
        )
    lines.append("# Constraints\n" + "\n".join(f"- {c}" for c in constraints))
    return "\n".join(lines).strip() + "\n"


def _build_task(
    *,
    kind: str,
    brief: str,
    title: str,
    subtitle: str | None = None,
    style: str = "brand-vti",
    frame_label: str | None = None,
    captions: list[str] | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    meta = _KIND_META[kind]
    frame = frame_label or meta["default_frame"]
    resolved = _resolve_backend(backend)
    task: dict[str, Any] = {
        "kind":         kind,
        "backend":      resolved,
        "frame_label":  frame,
        "style":        style,
        "hint_w":       meta["hint_w"],
        "hint_h":       meta["hint_h"],
        "title":        title,
        "subtitle":     subtitle,
        "captions":     list(captions) if captions else None,
    }
    if resolved == "figma":
        task["brief"] = _compose_brief(
            kind=kind, user_brief=brief, title=title, subtitle=subtitle,
            style=style, frame_label=frame,
            frame_instruction=meta["frame_instruction"], captions=captions,
        )
    else:  # html
        task["html_brief"] = _compose_html_brief(
            kind=kind, user_brief=brief, title=title, subtitle=subtitle,
            style=style, frame_label=frame,
            frame_instruction=meta["frame_instruction"], captions=captions,
        )
    return task


def make_screen_mobile(*, brief: str, title: str,
                       subtitle: str | None = None,
                       style: str = "brand-vti",
                       frame_label: str | None = None,
                       backend: str | None = None) -> dict[str, Any]:
    """One mobile app screen, framed in an iPhone."""
    return _build_task(kind="screen-mobile", brief=brief, title=title,
                       subtitle=subtitle, style=style,
                       frame_label=frame_label, backend=backend)


def make_screen_tablet(*, brief: str, title: str,
                       subtitle: str | None = None,
                       style: str = "brand-vti",
                       frame_label: str | None = None,
                       backend: str | None = None) -> dict[str, Any]:
    """One tablet UI screen, framed in a landscape iPad."""
    return _build_task(kind="screen-tablet", brief=brief, title=title,
                       subtitle=subtitle, style=style,
                       frame_label=frame_label, backend=backend)


def make_screen_desktop(*, brief: str, title: str,
                        subtitle: str | None = None,
                        style: str = "brand-vti",
                        frame_label: str | None = None,
                        backend: str | None = None) -> dict[str, Any]:
    """One desktop / web app screen, framed in a Chrome browser."""
    return _build_task(kind="screen-desktop", brief=brief, title=title,
                       subtitle=subtitle, style=style,
                       frame_label=frame_label, backend=backend)


def make_screen_bare(*, brief: str, title: str,
                     subtitle: str | None = None,
                     style: str = "brand-vti",
                     backend: str | None = None) -> dict[str, Any]:
    """Screen content without any device frame."""
    return _build_task(kind="screen-bare", brief=brief, title=title,
                       subtitle=subtitle, style=style, backend=backend)


def make_flow_mobile(*, brief: str, title: str,
                     captions: list[str] | None = None,
                     subtitle: str | None = None,
                     style: str = "brand-vti",
                     backend: str | None = None) -> dict[str, Any]:
    """3-screen mobile user journey strip."""
    if captions is not None and len(captions) != 3:
        raise ValueError(
            f"flow-mobile expects exactly 3 captions (or None), got {len(captions)}"
        )
    return _build_task(kind="flow-mobile", brief=brief, title=title,
                       subtitle=subtitle, style=style,
                       captions=captions, backend=backend)


def make_flow_desktop(*, brief: str, title: str,
                      captions: list[str] | None = None,
                      subtitle: str | None = None,
                      style: str = "brand-vti",
                      backend: str | None = None) -> dict[str, Any]:
    """3-screen desktop user journey strip."""
    if captions is not None and len(captions) != 3:
        raise ValueError(
            f"flow-desktop expects exactly 3 captions (or None), got {len(captions)}"
        )
    return _build_task(kind="flow-desktop", brief=brief, title=title,
                       subtitle=subtitle, style=style,
                       captions=captions, backend=backend)


def make_wireframe_mobile(*, brief: str, title: str,
                          subtitle: str | None = None,
                          backend: str | None = None) -> dict[str, Any]:
    """Low-fidelity mobile wireframe (grayscale)."""
    return _build_task(kind="wireframe-mobile", brief=brief, title=title,
                       subtitle=subtitle, style="neutral", backend=backend)


def make_wireframe_desktop(*, brief: str, title: str,
                           subtitle: str | None = None,
                           backend: str | None = None) -> dict[str, Any]:
    """Low-fidelity desktop wireframe."""
    return _build_task(kind="wireframe-desktop", brief=brief, title=title,
                       subtitle=subtitle, style="neutral", backend=backend)


# ---------------------------------------------------------------------------
# Discovery + dispatch
# ---------------------------------------------------------------------------
_KINDS: dict[str, Any] = {
    "screen-mobile":     make_screen_mobile,
    "screen-tablet":     make_screen_tablet,
    "screen-desktop":    make_screen_desktop,
    "screen-bare":       make_screen_bare,
    "flow-mobile":       make_flow_mobile,
    "flow-desktop":      make_flow_desktop,
    "wireframe-mobile":  make_wireframe_mobile,
    "wireframe-desktop": make_wireframe_desktop,
}


def list_kinds() -> list[str]:
    """All registered mockup kinds."""
    return list(_KINDS.keys())


def describe_kind(name: str) -> dict[str, Any]:
    """Metadata for one mockup kind — canvas, default frame, good-for hint."""
    if name not in _KIND_META:
        raise ValueError(
            f"unknown kind {name!r}; valid: {list(_KIND_META.keys())}"
        )
    meta = _KIND_META[name]
    return {
        "name":          name,
        "hint_w":        meta["hint_w"],
        "hint_h":        meta["hint_h"],
        "default_frame": meta["default_frame"],
        "good_for":      meta["good_for"],
    }


def call(kind: str, **kwargs) -> dict[str, Any]:
    """Dispatcher — build a task by kind name with kwargs."""
    if kind not in _KINDS:
        raise ValueError(
            f"unknown kind {kind!r}; valid: {list(_KINDS.keys())}"
        )
    return _KINDS[kind](**kwargs)


__all__ = [
    "VERSION",
    "make_screen_mobile",
    "make_screen_tablet",
    "make_screen_desktop",
    "make_screen_bare",
    "make_flow_mobile",
    "make_flow_desktop",
    "make_wireframe_mobile",
    "make_wireframe_desktop",
    "list_kinds",
    "describe_kind",
    "call",
]
