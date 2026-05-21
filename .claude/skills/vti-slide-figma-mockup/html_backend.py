"""HTML mockup backend — pure-local renderer, no external quota.

The HTML backend mirrors the Figma backend's surface (task descriptor →
PNG + sidecar JSON) but uses Playwright + Chromium to render local
HTML+CSS. It's the **default** backend in v0.2.0 because:

1. No external quota (Figma Starter caps at 6 MCP calls / month).
2. Deterministic — same input → same PNG, byte-exact.
3. Editable — the user can hand-tweak the HTML source between runs.
4. Brand-tokens are inline CSS that mirror
   ``vti-slide-page-builder/tokens.css``, so styling stays consistent.

The flow split between this module and the orchestrator:

- ``frame_html(task, body)`` builds the OUTER frame (browser chrome,
  phone bezel, flow strip with 3 frames) + injects the brand CSS.
  The ``body`` is HTML that the orchestrator authors per-slide using
  the task's ``brief`` as the design spec.

- ``render_to_png(html, ...)`` is the Playwright headless render.

- ``record_html_render(...)`` (in ``mockup_executor``) calls both,
  writes ``render.png``, ``source.html``, ``meta.json``, and appends
  ``work/mockups/INDEX.md``.
"""
from __future__ import annotations

from pathlib import Path

VERSION = "0.2.4"


# ---------------------------------------------------------------------------
# SVG icon library (v0.2.2 — replaces emoji glyphs)
# ---------------------------------------------------------------------------
# 1.5px stroked icons in 24×24 viewBox; render at any size via svg_icon().
# Use `currentColor` so CSS color cascade controls hue.
_SVG_ICONS: dict[str, str] = {
    "lock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><polyline points="2 6 12 13 22 6"/></svg>',
    "chat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    "calendar": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "mic": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
    "zap": '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    "sparkles": '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M12 0l2 8 8 2-8 2-2 8-2-8-8-2 8-2zM19 14l1 3 3 1-3 1-1 3-1-3-3-1 3-1z"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    "x": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    "warning": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "hourglass": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2h12M6 22h12M6 2v6a6 6 0 0 0 12 0V2M6 22v-6a6 6 0 0 1 12 0v6"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "arrow-right": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    "user": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "users": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    "bell": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>',
    "package": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    "file-text": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "message-circle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
    "trending-up": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
}


def svg_icon(name: str, size: int = 12, color: str | None = None,
             stroke_width: float | None = None) -> str:
    """Inline-SVG icon helper. Use in body_html in place of emoji glyphs.

    Renders inside a flex span so it sits inline with text. Inherits text
    color via ``currentColor`` unless ``color`` is explicit. ``size`` is
    the bounding box (square, both width + height).

    Examples::

        svg_icon("lock", size=10)
        svg_icon("zap", size=14, color="var(--blue)")
        svg_icon("warning", size=12, color="#8A1818")
    """
    svg = _SVG_ICONS.get(name)
    if svg is None:
        raise KeyError(f"unknown svg icon {name!r}; known: {sorted(_SVG_ICONS)}")
    style = (
        f"display:inline-flex; align-items:center; justify-content:center; "
        f"width:{size}px; height:{size}px; flex:0 0 {size}px;"
    )
    if color:
        style += f"color:{color};"
    inner = svg
    if stroke_width is not None and "stroke-width=" in inner:
        import re
        inner = re.sub(r'stroke-width="[^"]*"', f'stroke-width="{stroke_width}"', inner)
    return f'<span class="ic" style="{style}">{inner}</span>'


# ---------------------------------------------------------------------------
# Brand tokens (mirror of vti-slide-page-builder/tokens.css)
# ---------------------------------------------------------------------------
_TOKENS_CSS = """
:root {
  --navy: #051934;
  --blue-deep: #0844A4;
  --blue: #004AAD;
  --blue-mid: #1B5DE6;
  --bright: #0468E6;
  --sky: #0782FF;
  --light: #DAE9F6;
  --paleblue: #EAF2FB;
  --ink: #1F2A3A;
  --ink-soft: #4B5A6E;
  --muted: #6B7A8D;
  --border: #C8DCF0;
  --divider: #E4ECF5;
  --bg: #F0F5FB;
  --white: #FFFFFF;
  --amber: #F8C379;
  --amber-strong: #F4B73A;
  --amber-pale: #FEF6E5;
  --amber-ink: #7E5500;
  --green: #1A7A4A;
  --green-pale: #E6F1EC;
  --red: #B02020;
  --rose: #FCEAEA;
  --font: 'Plus Jakarta Sans', 'Inter', 'Arial', system-ui, sans-serif;
  --font-mac: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: var(--font); color: var(--ink); }
"""

_NEUTRAL_TOKENS_CSS = """
:root {
  --navy: #0F172A;
  --blue: #4F46E5;
  --blue-deep: #4338CA;
  --blue-mid: #6366F1;
  --bright: #6366F1;
  --sky: #818CF8;
  --light: #EEF2FF;
  --paleblue: #F5F7FF;
  --ink: #0F172A;
  --ink-soft: #475569;
  --muted: #94A3B8;
  --border: #E2E8F0;
  --divider: #F1F5F9;
  --bg: #F8FAFC;
  --white: #FFFFFF;
  --amber: #F59E0B; --amber-strong: #D97706; --amber-pale: #FEF3C7; --amber-ink: #92400E;
  --green: #059669; --green-pale: #D1FAE5;
  --red: #DC2626; --rose: #FEE2E2;
  --font: 'Inter', system-ui, sans-serif;
  --font-mac: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: var(--font); color: var(--ink); }
"""

_DARK_TOKENS_CSS = """
:root {
  --navy: #020617;
  --blue: #0468E6; --blue-deep: #1B5DE6; --blue-mid: #0782FF; --bright: #0782FF; --sky: #38BDF8;
  --light: #1E293B; --paleblue: #0F172A;
  --ink: #F1F5F9; --ink-soft: #CBD5E1; --muted: #64748B;
  --border: #334155; --divider: #1E293B;
  --bg: #020617; --white: #0F172A;
  --amber: #F59E0B; --amber-strong: #FBBF24; --amber-pale: #422006; --amber-ink: #FBBF24;
  --green: #10B981; --green-pale: #064E3B;
  --red: #EF4444; --rose: #450A0A;
  --font: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  --font-mac: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', system-ui, sans-serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: var(--font); color: var(--ink); background: var(--bg); }
"""


def _tokens_for(style: str) -> str:
    s = (style or "brand-vti").lower()
    if s == "neutral": return _NEUTRAL_TOKENS_CSS
    if s == "dark-mode": return _DARK_TOKENS_CSS
    return _TOKENS_CSS


# ---------------------------------------------------------------------------
# Frame templates — outer chrome per mockup kind
# ---------------------------------------------------------------------------
_BROWSER_CHROME = """
<div class="bc-chrome">
  <span class="bc-dot" style="background:#FF5F57"></span>
  <span class="bc-dot" style="background:#FEBC2E"></span>
  <span class="bc-dot" style="background:#28C840"></span>
  <div class="bc-url">🔒 {url}</div>
</div>
"""

_PHONE_FRAME = """
<div class="ph-bezel">
  <div class="ph-notch"></div>
  <div class="ph-status">
    <span class="ph-time">{time}</span>
    <span class="ph-icons">●●●●● 5G ▮▮▮</span>
  </div>
  {body}
</div>
"""

_MAC_WINDOW_CSS = """
/* === Mac OS window wrapper (v0.2.4) — macOS Tahoe / Liquid Glass === */
/* When rendered via slide-hero kind the PNG canvas is transparent;
   the .mac-window is the only painted region. Insets give the
   drop-shadow room to fade (~24px above, ~48px below, ~36px sides).
   Tahoe-style: 14px corner radius, layered translucent titlebar with
   inset highlights, refined traffic lights with radial gradients. */
.mac-window {
  position: fixed;
  top: 50px; left: 40px; right: 40px; bottom: 60px;
  background: var(--white);
  border-radius: 14px;
  box-shadow:
    0 18px 48px rgba(0, 0, 0, 0.16),
    0 4px 12px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    inset 0 0 0 0.5px rgba(0, 0, 0, 0.10);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.mac-titlebar {
  height: 38px; flex: 0 0 38px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0) 100%),
    linear-gradient(180deg, #F6F6F8 0%, #ECECEF 100%);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  box-shadow: inset 0 -0.5px 0 rgba(255, 255, 255, 0.5);
  display: flex; align-items: center;
  padding: 0 16px;
  gap: 9px;
  position: relative;
}
.mac-dot {
  width: 13px; height: 13px; border-radius: 50%;
  display: inline-block;
  flex: 0 0 13px;
  box-shadow:
    inset 0 0.5px 0 rgba(255, 255, 255, 0.4),
    inset 0 -0.5px 0 rgba(0, 0, 0, 0.12),
    0 0.5px 1px rgba(0, 0, 0, 0.08);
}
.mac-dot.red    { background: radial-gradient(circle at 35% 30%, #FF8682 0%, #FF5F57 55%, #EF4940 100%); }
.mac-dot.yellow { background: radial-gradient(circle at 35% 30%, #FFD46A 0%, #FEBC2E 55%, #E5A114 100%); }
.mac-dot.green  { background: radial-gradient(circle at 35% 30%, #5BE074 0%, #28C840 55%, #18AC2E 100%); }
.mac-body {
  flex: 1 1 auto;
  overflow: hidden;
  /* Tahoe wallpaper — subtle colored radial mesh under glass cards.
     The colors are pulled toward the VTI brand palette (blue + violet
     + sky) so glass cards on top read as VTI-tinted glass, not generic
     macOS desktop. */
  background:
    radial-gradient(at 0%   0%,   rgba( 79, 138, 240, 0.22) 0%, transparent 55%),
    radial-gradient(at 100% 0%,   rgba(149, 121, 232, 0.18) 0%, transparent 55%),
    radial-gradient(at 100% 100%, rgba( 79, 174, 240, 0.20) 0%, transparent 55%),
    radial-gradient(at 0%   100%, rgba(122, 196, 240, 0.16) 0%, transparent 55%),
    linear-gradient(135deg, #F6F8FC 0%, #EEF1F8 100%);
  display: flex; flex-direction: column;
  font-family: var(--font-mac);
  font-size: 14px;
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: -0.005em;
}
.ic { display: inline-flex; flex: 0 0 auto; vertical-align: middle; }
.ic svg { width: 100%; height: 100%; display: block; }
"""

_FRAMES_CSS = """
/* === Browser chrome === */
.browser {
  background: var(--white); border-radius: 14px; border: 1px solid var(--border);
  overflow: hidden; box-shadow: 0 8px 24px rgba(5,25,52,.08);
  display: flex; flex-direction: column;
}
.bc-chrome {
  background: var(--paleblue);
  padding: 10px 14px;
  display: flex; align-items: center; gap: 8px;
  border-bottom: 1px solid var(--border);
}
.bc-dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; flex: 0 0 11px; }
.bc-url {
  background: var(--white); border-radius: 6px; padding: 4px 10px;
  font-size: 10px; color: var(--ink-soft); flex: 1 1 auto; margin-left: 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.browser-body { padding: 16px 18px; display: flex; flex-direction: column; gap: 14px; }

/* === Phone bezel === */
.phone { background: var(--ink); padding: 12px; border-radius: 36px; box-shadow: 0 12px 28px rgba(0,0,0,.18); display: inline-block; }
.ph-bezel { background: var(--white); border-radius: 24px; overflow: hidden; width: 360px; }
.ph-notch { width: 90px; height: 22px; background: var(--ink); border-radius: 0 0 12px 12px; margin: 0 auto; }
.ph-status { padding: 4px 16px; font-size: 10px; color: var(--ink-soft); display: flex; justify-content: space-between; }

/* === Flow strip wrapper === */
.flow-strip {
  background: var(--bg);
  padding: 48px 56px;
  display: flex; flex-direction: column; gap: 20px; align-items: center;
  min-width: 100vw;
}
.flow-title { font-size: 22px; font-weight: 700; color: var(--navy); text-align: center; margin: 0; }
.flow-sub { font-size: 13px; color: var(--muted); margin: 0; }
.flow-row {
  display: flex; gap: 32px; align-items: stretch; justify-content: center;
  margin-top: 12px;
}
.flow-row > * { flex: 0 0 600px; }
.flow-caps {
  display: flex; gap: 32px; justify-content: center; width: 100%;
  margin-top: 4px;
}
.flow-caps > * {
  flex: 0 0 600px; text-align: center;
  font-size: 13px; font-weight: 600; color: var(--blue);
}
"""

# Re-usable atom CSS (avatars, chips, dividers, etc.)
_ATOMS_CSS = """
.av {
  width: 30px; height: 30px; border-radius: 50%; background: var(--blue-mid);
  color: var(--white); font-size: 11px; font-weight: 600;
  display: inline-flex; align-items: center; justify-content: center; flex: 0 0 auto;
}
.av-sm { width: 18px; height: 18px; font-size: 8px; }
.av-md { width: 22px; height: 22px; font-size: 9px; }
.av-stack { display: inline-flex; }
.av-stack > .av + .av { margin-left: -6px; border: 2px solid var(--white); }

.chip {
  display: inline-flex; align-items: center;
  padding: 3px 8px; border-radius: 10px;
  font-size: 10px; font-weight: 500; line-height: 1;
}
.chip-blue   { background: var(--paleblue);   color: var(--blue); }
.chip-amber  { background: var(--amber-pale); color: var(--amber-ink); }
.chip-green  { background: var(--green-pale); color: var(--green); }
.chip-muted  { background: var(--divider);    color: var(--ink-soft); }
.chip-white  { background: var(--white);      color: var(--ink-soft); border: 1px solid var(--border); }

.sec-hdr {
  display: flex; align-items: stretch;
  border-radius: 6px; overflow: hidden;
}
.sec-hdr .bar { width: 4px; flex: 0 0 4px; }
.sec-hdr .lbl {
  padding: 7px 10px; display: flex; align-items: center; gap: 8px;
  font-size: 12px; color: var(--ink);
}
.sec-hdr .lbl b { font-weight: 600; }
.sec-hdr .lbl span.cnt { color: var(--muted); font-weight: 500; }
.sec-hdr-amber  { background: var(--amber-pale); }
.sec-hdr-amber  .bar { background: var(--amber-strong); }
.sec-hdr-blue   { background: var(--paleblue); }
.sec-hdr-blue   .bar { background: var(--blue-mid); }
.sec-hdr-gray   { background: var(--divider); }
.sec-hdr-gray   .bar { background: var(--muted); }
.sec-hdr-green  { background: var(--green-pale); }
.sec-hdr-green  .bar { background: var(--green); }

.card {
  background: var(--white); border: 1px solid var(--divider); border-radius: 8px;
  padding: 10px 12px;
}
.card-sm { padding: 8px 10px; border-radius: 6px; }
.card-row { display: flex; gap: 10px; align-items: flex-start; }
.card-row .col { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.muted { color: var(--muted); }
.ink-soft { color: var(--ink-soft); }
.fw-600 { font-weight: 600; }
.fs-10 { font-size: 10px; }
.fs-11 { font-size: 11px; }
.fs-12 { font-size: 12px; }
.fs-13 { font-size: 13px; }
.fs-14 { font-size: 14px; }
.fs-18 { font-size: 18px; }

.row { display: flex; align-items: center; gap: 8px; }
.row-tight { display: flex; align-items: center; gap: 6px; }
.col-v { display: flex; flex-direction: column; }
.gap-2 { gap: 2px; } .gap-4 { gap: 4px; } .gap-6 { gap: 6px; } .gap-8 { gap: 8px; } .gap-10 { gap: 10px; }

.spark { display: inline-flex; align-items: flex-end; gap: 2px; height: 20px; }
.spark span { width: 5px; background: var(--blue-mid); border-radius: 1px; display: inline-block; }

.check {
  width: 14px; height: 14px; flex: 0 0 14px;
  border-radius: 3px; border: 1.5px solid var(--muted); background: var(--white);
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 9px; color: var(--white);
}
.check-done { background: var(--green); border-color: var(--green); }
.strike { text-decoration: line-through; color: var(--muted); }

.kicker { font-size: 11px; color: var(--muted); }
.h1 { font-size: 18px; font-weight: 700; color: var(--navy); margin: 0; }
.h2 { font-size: 13px; font-weight: 700; color: var(--blue); margin: 0; }
.h3 { font-size: 12px; font-weight: 600; color: var(--ink-soft); margin: 0; }
.h4 { font-size: 11px; font-weight: 600; color: var(--navy); margin: 0; }

.divider { height: 1px; background: var(--divider); width: 100%; }

/* Active / focused meeting card */
.card-active {
  border: 2px solid var(--blue-mid); background: var(--paleblue);
}
"""


# ---------------------------------------------------------------------------
# Outer wrappers
# ---------------------------------------------------------------------------
def _full_doc(style: str, body: str, extra_css: str = "",
              transparent_bg: bool = False) -> str:
    """Return a complete <!doctype><html>… document with brand tokens
    + frames CSS + atoms CSS + the body content.

    ``transparent_bg=True`` (v0.2.2) drops html/body backgrounds so
    Playwright ``omit_background=True`` produces a transparent PNG
    outside the mac-window. The mac-window itself paints white.
    """
    transparent_overlay = """
html, body { background: transparent !important; }
""" if transparent_bg else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
{_tokens_for(style)}
{_FRAMES_CSS}
{_MAC_WINDOW_CSS}
{_ATOMS_CSS}
{extra_css}
{transparent_overlay}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def frame_html(*,
               kind: str,
               style: str,
               title: str,
               subtitle: str | None,
               captions: list[str] | None,
               screens: list[dict[str, str]],
               extra_css: str = "") -> str:
    """Compose a full HTML document for a mockup kind.

    Args
    ----
    kind: one of the 8 mockup kinds. Determines outer frame.
    style: 'brand-vti' | 'neutral' | 'dark-mode'.
    title / subtitle: shown above flow-* strips. Ignored by screen-*.
    captions: per-screen captions for flow-* kinds (must equal len(screens)).
    screens: list of dicts each with keys:
        - 'url' (browser kinds only) — text shown in the address bar
        - 'body_html' — the inner HTML of the screen's content area
    For single-screen kinds, pass a 1-item screens list.

    Returns the full HTML string. Caller passes to ``render_to_png``.
    """
    parts: list[str] = []

    is_flow = kind.startswith("flow-")
    is_phone = kind == "screen-mobile" or kind == "wireframe-mobile"

    if is_flow:
        parts.append('<div class="flow-strip">')
        parts.append(f'<h1 class="flow-title">{_esc(title)}</h1>')
        if subtitle:
            parts.append(f'<p class="flow-sub">{_esc(subtitle)}</p>')
        parts.append('<div class="flow-row">')
        for sc in screens:
            parts.append(_browser(sc.get("url", ""), sc["body_html"]))
        parts.append('</div>')
        if captions:
            parts.append('<div class="flow-caps">')
            for c in captions:
                parts.append(f'<div>{_esc(c)}</div>')
            parts.append('</div>')
        parts.append('</div>')
    elif is_phone:
        # Single phone screen
        sc = screens[0]
        parts.append(f'''<div style="padding:48px; background:var(--bg); display:flex; justify-content:center;">
  <div class="phone">
    <div class="ph-bezel">
      <div class="ph-notch"></div>
      <div class="ph-status"><span>{_esc(sc.get("time","9:41"))}</span><span>●●●●● 5G ▮▮▮</span></div>
      <div style="padding: 14px 16px;">{sc["body_html"]}</div>
    </div>
  </div>
</div>''')
    elif kind == "slide-hero" or kind == "slide-mini":
        # v0.2.2 — wrap body in a macOS-style window with traffic lights.
        # PNG canvas outside the window is transparent so the mockup
        # drops cleanly onto a slide background.
        sc = screens[0]
        parts.append(f'''<div class="mac-window">
  <div class="mac-titlebar">
    <span class="mac-dot red"></span>
    <span class="mac-dot yellow"></span>
    <span class="mac-dot green"></span>
  </div>
  <div class="mac-body">{sc["body_html"]}</div>
</div>''')
    else:
        # Single browser (tablet / desktop / bare)
        sc = screens[0]
        wrap_open = '<div style="padding:48px; background:var(--bg);">'
        if kind == "screen-bare":
            parts.append(wrap_open)
            parts.append(f'<div style="background:var(--white); border-radius:14px; padding:16px 18px;">{sc["body_html"]}</div>')
            parts.append('</div>')
        else:
            parts.append(wrap_open)
            parts.append(_browser(sc.get("url",""), sc["body_html"]))
            parts.append('</div>')

    # v0.2.2 — slide-hero / slide-mini render with transparent canvas
    # so the mac-window appears floating on the slide background.
    transparent = (kind == "slide-hero" or kind == "slide-mini")
    return _full_doc(style, "\n".join(parts),
                     extra_css=extra_css, transparent_bg=transparent)


def _browser(url: str, body_html: str) -> str:
    return f'''<div class="browser">
  <div class="bc-chrome">
    <span class="bc-dot" style="background:#FF5F57"></span>
    <span class="bc-dot" style="background:#FEBC2E"></span>
    <span class="bc-dot" style="background:#28C840"></span>
    <div class="bc-url">🔒 {_esc(url)}</div>
  </div>
  <div class="browser-body">{body_html}</div>
</div>'''


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Playwright render
# ---------------------------------------------------------------------------
def _ensure_playwright() -> None:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "playwright not installed — `pip install playwright && "
            "python -m playwright install chromium`"
        ) from e


# Default viewports per kind. The Playwright context uses these as the
# viewport, but if the content overflows the page screenshots full_page.
_KIND_VIEWPORT: dict[str, tuple[int, int]] = {
    "screen-mobile":      (480, 1000),
    "screen-tablet":      (1200, 900),
    "screen-desktop":     (1500, 980),
    "screen-bare":        (1240, 800),
    "flow-mobile":        (1800, 1100),
    "flow-desktop":       (2000, 1200),
    "wireframe-mobile":   (480, 1000),
    "wireframe-desktop":  (1500, 980),
    "slide-hero":         (1680, 1000),   # v0.2.3 — padded for mac-window drop shadow
    "slide-mini":         (1880, 1000),   # v0.2.3 — padded for mac-window drop shadow
}


def render_to_png(
    *,
    html: str,
    out_path: str | Path,
    kind: str = "screen-desktop",
    scale: int = 2,
    full_page: bool = True,
    extra_wait_ms: int = 200,
    viewport: tuple[int, int] | None = None,
    omit_background: bool | None = None,
) -> tuple[int, int]:
    """Render the given HTML to a PNG at ``out_path``.

    Returns ``(natural_w, natural_h)`` — the actual rendered pixel size
    (un-scaled — divide by ``scale`` to get logical CSS pixels).

    ``full_page=True`` (default) captures the full document height even
    if it exceeds the viewport — useful when content overflows. Pair
    with ``full_page=False`` + explicit ``viewport=(w, h)`` to lock the
    PNG to an exact aspect ratio (e.g. 16:9 slide hero).

    ``scale=2`` writes hi-DPI for crisper embedding in PPTX or web
    slides. ``viewport`` (optional) overrides the per-kind default.
    """
    _ensure_playwright()
    from playwright.sync_api import sync_playwright

    if viewport is not None:
        vw, vh = viewport
    else:
        vw, vh = _KIND_VIEWPORT.get(kind, (1500, 980))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # v0.2.2 — slide-hero / slide-mini default to transparent PNG so
    # the mac-window floats on the slide background.
    if omit_background is None:
        omit_background = (kind == "slide-hero" or kind == "slide-mini")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_context(
                viewport={"width": vw, "height": vh},
                device_scale_factor=scale,
            )
            page = ctx.new_page()
            page.set_content(html, wait_until="domcontentloaded")
            try:
                page.evaluate("() => document.fonts && document.fonts.ready")
            except Exception:
                pass
            if extra_wait_ms > 0:
                page.wait_for_timeout(extra_wait_ms)
            if not full_page:
                # Explicit clip to viewport — guarantees output dims even if
                # CSS pushes content past viewport boundary.
                page.screenshot(
                    path=str(out_path),
                    full_page=False,
                    clip={'x': 0, 'y': 0, 'width': vw, 'height': vh},
                    omit_background=omit_background,
                )
            else:
                page.screenshot(
                    path=str(out_path),
                    full_page=True,
                    omit_background=omit_background,
                )
        finally:
            browser.close()

    # Read back PNG dimensions
    data = out_path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"screenshot at {out_path} is not a PNG")
    w = int.from_bytes(data[16:20], "big")
    h = int.from_bytes(data[20:24], "big")
    return w, h


__all__ = [
    "VERSION",
    "frame_html",
    "render_to_png",
    "svg_icon",
]
