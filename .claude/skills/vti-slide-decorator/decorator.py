"""
vti-slide-decorator — main API.

v0.5 (2026-05-10) — W3.6 pipeline implemented end-to-end. ``decorate()``
now wires screenshot → detect_gaps → classify → select_strategy →
generate → inject as overlay layer. Pipeline is idempotent (re-running
on a decorated deck returns the same output).

Public API:
  decorate(deck_html_path: str, output_path: str = None,
           strategies: str | list = 'auto') → str
    High-level: take a composed deck HTML file path, return decorated
    deck HTML (also written to output_path if supplied).

  decorate_html(deck_html: str, *,
                screenshot_dir: str = None,
                strategies: str | list = 'auto') → str
    String-in / string-out variant. Renders into a temp dir.

  decorate_slide(slide_html: str, slide_meta: dict,
                 screenshot_path: str,
                 strategies: str | list = 'auto') → str
    Per-slide decoration when caller already has a screenshot.

  pipeline_status() → dict
    What's wired vs what's stubbed.

  __version__: skill version (semver string).

Architecture:
  HTML in → render screenshots → detect gaps → classify → select
  strategy → generate SVG → inject as overlay layer → HTML out

  The decorator NEVER modifies content/layout. Output deck is identical
  to input plus a ``<div class="vti-decoration-layer">`` per slide
  positioned at lower z-index than content.
"""
from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Union

from whitespace_analyzer import detect_gaps, visualize_gaps, Gap
from gap_classifier import classify_slide_gaps, ClassifiedGap

# Strategy modules (import here so 'auto' selection can dispatch by name)
from strategies import abstract_geometric, topical_motif, typographic, none as none_strategy

__version__ = "0.5.2"


# ---------------------------------------------------------------------------
# Status — fully implemented as of v0.5
# ---------------------------------------------------------------------------

_PIPELINE_STATUS = {
    'render':                'IMPLEMENTED (Playwright)',
    'whitespace_detection':  'IMPLEMENTED (W3.1, W3.2 chrome-aware)',
    'gap_classification':    'IMPLEMENTED (W3.3)',
    'strategy_selection':    'IMPLEMENTED (W3.5 — v0.5)',
    'strategies': {
        'abstract_geometric': 'IMPLEMENTED (W3.4)',
        'topical_motif':      'IMPLEMENTED (W3.4)',
        'typographic':        'IMPLEMENTED (W3.4)',
        'none':               'IMPLEMENTED (W3.4)',
    },
    'injection':             'IMPLEMENTED (W3.6 — v0.5)',
    'audit':                 'STUB (planned for v0.6 — extends audit_typography)',
}


def pipeline_status() -> dict:
    """Return what's implemented vs stubbed in the pipeline."""
    return dict(_PIPELINE_STATUS)


# ---------------------------------------------------------------------------
# Slide rendering (W3.1 — implemented)
# ---------------------------------------------------------------------------

def screenshot_slides(deck_html_path: str, output_dir: str,
                      *, viewport=(1280, 720),
                      device_scale: float = 2.0) -> list[str]:
    """Render each slide in deck to a PNG. Returns list of screenshot paths.

    Slide identification: looks for elements with class "slide" or with
    explicit "data-slide-index" attribute. Falls back to splitting by
    page-break selectors.

    Uses Playwright sync API. Requires playwright + chromium installed.
    """
    from playwright.sync_api import sync_playwright

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={'width': viewport[0], 'height': viewport[1]},
            device_scale_factor=device_scale,
        )
        page = ctx.new_page()
        page.goto(f'file://{Path(deck_html_path).resolve()}')
        # Wait for fonts/layout
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass  # large decks may not hit idle; carry on

        # Count slides
        n_slides = page.evaluate(
            "() => document.querySelectorAll('.slide').length"
        )
        for i in range(n_slides):
            elem = page.locator('.slide').nth(i)
            out_path = os.path.join(output_dir, f'slide_{i+1:02d}.png')
            elem.screenshot(path=out_path)
            paths.append(out_path)
        browser.close()
    return paths


# ---------------------------------------------------------------------------
# Strategy selection (v0.5 — was stub, now W3.5 proper implementation)
# ---------------------------------------------------------------------------

# Section-level strategy bias. Slide section names route to a preferred
# ordering; intersected with each focal gap's compatible_strategies.
_SECTION_STRATEGY_BIAS = {
    "ABOUT VTI":       ["typographic", "abstract_geometric"],
    "SERVICES":        ["abstract_geometric", "typographic"],
    "RETAIL CASES":    ["topical_motif", "abstract_geometric"],
    "MEDICAL CASES":   ["topical_motif", "abstract_geometric"],
    "WHY VTI":         ["typographic", "abstract_geometric"],
    "FORWARD":         ["abstract_geometric", "topical_motif"],
}


def select_strategy(slide_html: str, gaps: list,
                    slide_meta: Optional[dict] = None) -> str:
    """Pick a strategy name for a slide based on classified gaps + section.

    v0.5 — proper W3.5 implementation. Picks from {abstract_geometric,
    topical_motif, typographic, none} by:

      1. If no gaps OR no decoration-eligible gaps → 'none'.
      2. Pick the largest eligible gap as the focal candidate.
      3. Apply section-level bias: e.g. RETAIL CASES leans
         topical_motif (real-world subject benefits from a motif);
         ABOUT VTI leans typographic (use the section name itself).
      4. Intersect bias with classified gap's compatible_strategies.
      5. Return first match; default to first compatible_strategy.

    Args:
        slide_html: HTML of the single slide (used for keyword scan if needed)
        gaps: list of Gap OR list of ClassifiedGap. If raw Gap, classify
              internally.
        slide_meta: dict with at least ``section_name``; used for bias.

    Returns:
        strategy name (one of: 'abstract_geometric', 'topical_motif',
        'typographic', 'none').
    """
    if not gaps:
        return 'none'

    # Normalize: classify if we got raw Gap objects
    if gaps and isinstance(gaps[0], Gap):
        classified = classify_slide_gaps(gaps, slide_meta)
    else:
        classified = list(gaps)

    eligible = [c for c in classified if getattr(c, 'decoration_eligible', False)]
    if not eligible:
        return 'none'

    # Focal gap = largest eligible
    eligible.sort(key=lambda c: c.gap.area, reverse=True)
    focal = eligible[0]

    # Bias from section
    section = (slide_meta or {}).get('section_name', '') or ''
    bias = _SECTION_STRATEGY_BIAS.get(section.upper().strip(), [])

    # Intersect bias with focal's compatible strategies
    compat = list(focal.compatible_strategies or [])
    for strat in bias:
        if strat in compat:
            return strat

    # No bias hit — return focal's first compatible strategy
    return compat[0] if compat else 'none'


# ---------------------------------------------------------------------------
# Strategy dispatch — name → generate function
# ---------------------------------------------------------------------------
_STRATEGY_DISPATCH = {
    'abstract_geometric': abstract_geometric.generate,
    'topical_motif':      topical_motif.generate,
    'typographic':        typographic.generate,
    'none':               none_strategy.generate,
}


# Compatibility shim — the v0.1 API exposed classify_gap as a per-gap
# function. v0.5 prefers gap_classifier.classify_slide_gaps but we
# keep the shim so external callers don't break.
def classify_gap(gap: Gap, slide_html: str = '',
                 slide_meta: Optional[dict] = None) -> ClassifiedGap:
    """v0.1 compatibility wrapper. Returns ClassifiedGap from
    gap_classifier instead of the v0.1 mini-dict.
    """
    from gap_classifier import classify_gap as _cg
    return _cg(gap, slide_meta)


# ---------------------------------------------------------------------------
# Per-slide decoration (W3.6)
# ---------------------------------------------------------------------------
def decorate_slide(slide_html: str, slide_meta: dict,
                   screenshot_path: str,
                   strategies: Union[str, list] = 'auto') -> str:
    """Decorate a single slide. Returns the slide HTML with a
    ``<div class="vti-decoration-layer">`` injected as the FIRST child of
    its content wrapper (positioned absolute at z-index < content).

    Args:
        slide_html: original slide HTML (one ``<div class="slide ...">``)
        slide_meta: dict with section_name, slide_title, page_number
        screenshot_path: PNG path of the rendered slide
        strategies: 'auto' for selector pick, or a list to constrain
                    (e.g. ['typographic'] forces typographic; 'none'
                    explicitly skips decoration).

    Returns:
        Decorated slide HTML. Idempotent: re-running on a decorated
        slide first strips any existing ``vti-decoration-layer`` then
        re-injects, so the result depends only on the current screenshot.
    """
    # Idempotent: strip any prior decoration layer
    slide_html = _strip_decoration_layer(slide_html)

    # Detect gaps + classify
    gaps = detect_gaps(screenshot_path)
    classified = classify_slide_gaps(gaps, slide_meta)

    # Pick strategy
    if strategies == 'auto':
        strategy_name = select_strategy(slide_html, classified, slide_meta)
    elif isinstance(strategies, str) and strategies in _STRATEGY_DISPATCH:
        strategy_name = strategies
    elif isinstance(strategies, list):
        eligible = [c for c in classified if c.decoration_eligible]
        if not eligible:
            strategy_name = 'none'
        else:
            focal_compat = set(eligible[0].compatible_strategies or [])
            allowed = [s for s in strategies if s in focal_compat] or strategies
            strategy_name = allowed[0] if allowed else 'none'
    else:
        strategy_name = 'none'

    if strategy_name == 'none' or not classified:
        return slide_html  # no decoration

    # Compute slide pixel size from the screenshot for percentage layout
    from PIL import Image
    with Image.open(screenshot_path) as im:
        slide_size = im.size

    # Generate SVG fragment per eligible gap (one decoration per gap)
    eligible = [c for c in classified if c.decoration_eligible]
    gen = _STRATEGY_DISPATCH.get(strategy_name, none_strategy.generate)
    fragments: list[str] = []
    for cg in eligible:
        try:
            frag = gen(cg, slide_meta=slide_meta, slide_size=slide_size)
        except TypeError:
            frag = gen(cg, slide_meta=slide_meta)
        if frag:
            fragments.append(frag)

    if not fragments:
        return slide_html

    overlay = (
        '<div class="vti-decoration-layer" '
        'style="position:absolute; inset:0; z-index:0; '
        'pointer-events:none; overflow:hidden;">\n'
        + '\n'.join(fragments)
        + '\n</div>'
    )

    return _inject_overlay(slide_html, overlay)


# ---------------------------------------------------------------------------
# HTML manipulation helpers
# ---------------------------------------------------------------------------
_DECORATION_RE = re.compile(
    r'<div class="vti-decoration-layer"[^>]*>.*?</div>\s*</div>\s*',
    re.DOTALL,
)


def _strip_decoration_layer(slide_html: str) -> str:
    """Remove any existing decoration layer from a slide HTML.

    The layer's outer </div> is followed by other content; we look for
    the layer's opening tag and walk forward depth-tracking to find its
    matching close. Also consumes the leading whitespace immediately
    before the open tag (which _inject_overlay adds).
    """
    open_re = re.compile(r'<div class="vti-decoration-layer"[^>]*>',
                          re.IGNORECASE)
    while True:
        m = open_re.search(slide_html)
        if not m:
            break
        depth = 1
        j = m.end()
        scan_re = re.compile(r'<(/?)div\b[^>]*>', re.IGNORECASE)
        while depth > 0:
            mm = scan_re.search(slide_html, j)
            if not mm:
                break
            if mm.group(1) == '/':
                depth -= 1
            else:
                depth += 1
            j = mm.end()
        # Walk back over any whitespace immediately before the open tag
        # (matches the "\n" that _inject_overlay prepends).
        start = m.start()
        while start > 0 and slide_html[start - 1] in ' \t\n':
            start -= 1
        # And forward over trailing whitespace after the close tag.
        end = j
        while end < len(slide_html) and slide_html[end] in ' \t\n':
            end += 1
        slide_html = slide_html[:start] + slide_html[end:]
    return slide_html


_SLIDE_OPEN_RE = re.compile(
    r'(<div\s+class="slide[^"]*"[^>]*>)',
    re.IGNORECASE,
)


def _inject_overlay(slide_html: str, overlay_html: str) -> str:
    """Inject the overlay div as the first child of the slide div."""
    m = _SLIDE_OPEN_RE.search(slide_html)
    if not m:
        return slide_html
    insert_pos = m.end()
    return slide_html[:insert_pos] + '\n' + overlay_html + slide_html[insert_pos:]


# ---------------------------------------------------------------------------
# Deck-level slide enumeration
# ---------------------------------------------------------------------------

# Classes that signify special-page slides — these are ALREADY designed
# (cover photo, TOC mesh, divider chevron, contact badge) and don't need
# decoration overlays. Decoration only fires on `.slide.layout-grid`.
_SPECIAL_SLIDE_CLASSES = {
    "page-cover",
    "page-toc",
    "page-section-divider",
    "page-contact",
    "page-closing",
    # narrator pages (rich pre-designed templates)
    "page-about-vti",
    "page-awards-certifications",
    "page-quality-management-process",
    "page-quality-assurance",
    "page-strategic-partners",
    "page-vision-mission-values",
    "page-who-we-serve",
    "page-project-management-method",
}

# v0.5.2 — class for decoration-eligible content slides
_DECORATABLE_SLIDE_CLASS = "layout-grid"


def _slide_classes(slide_html: str) -> set[str]:
    """Return the set of CSS class names on the outermost <div class="slide ...">.
    Empty set if no recognizable slide div.
    """
    m = re.match(r'\s*<div\s+class="([^"]*)"', slide_html, re.IGNORECASE)
    if not m:
        return set()
    return set(m.group(1).split())


def _is_decoratable_slide(slide_html: str) -> bool:
    """v0.5.2 — only `.slide.layout-grid` is target. Special slides
    (cover, toc, section-divider, contact, closing, narrator pages) are
    already richly designed and skipped — their stock visuals would
    fight any decoration overlay.
    """
    classes = _slide_classes(slide_html)
    if _DECORATABLE_SLIDE_CLASS not in classes:
        return False
    if classes & _SPECIAL_SLIDE_CLASSES:
        return False
    return True


def _enumerate_slides(deck_html: str) -> list[tuple[int, int]]:
    """Find each top-level slide div range in the deck HTML."""
    spans: list[tuple[int, int]] = []
    i = 0
    open_re = re.compile(r'<div\s+class="slide[^"]*"[^>]*>', re.IGNORECASE)
    while True:
        m = open_re.search(deck_html, i)
        if not m:
            break
        start = m.start()
        depth = 1
        j = m.end()
        scan_re = re.compile(r'<(/?)div\b[^>]*>', re.IGNORECASE)
        while depth > 0:
            mm = scan_re.search(deck_html, j)
            if not mm:
                break
            if mm.group(1) == '/':
                depth -= 1
            else:
                depth += 1
            j = mm.end()
        end = j
        spans.append((start, end))
        i = end
    return spans


# ---------------------------------------------------------------------------
# Main API — full deck pipeline (W3.6, formerly NotImplementedError)
# ---------------------------------------------------------------------------
def decorate(deck_html_path: str,
             output_path: Optional[str] = None,
             *,
             screenshot_dir: Optional[str] = None,
             strategies: Union[str, list] = 'auto',
             keep_screenshots: bool = False) -> str:
    """High-level: decorate a whole composed deck.

    Args:
        deck_html_path: path to the composed deck HTML on disk
        output_path: optional path to write decorated deck HTML
        screenshot_dir: where per-slide PNGs are saved (defaults to
                        a tempdir, deleted on exit unless
                        keep_screenshots=True)
        strategies: 'auto' (selector) or a list of allowed strategy names
        keep_screenshots: don't delete the temp screenshot dir

    Returns:
        Decorated deck HTML (also written to output_path if given).
        Idempotent — running twice produces the same output.
    """
    deck_html_path = str(Path(deck_html_path).resolve())
    deck_html = Path(deck_html_path).read_text(encoding='utf-8')

    # Idempotency: if the deck already carries decoration layers, strip
    # them BEFORE rendering screenshots so gap detection sees the clean
    # composition. The decoration CSS marker is left in <head> (cheap to
    # inject, harmless if duplicated; _ensure_decoration_css is idempotent).
    deck_html_for_render = deck_html
    if 'vti-decoration-layer' in deck_html:
        deck_html_for_render = _strip_decoration_layer(deck_html)
        # Write the stripped version to a temp file for the renderer
        with tempfile.NamedTemporaryFile('w', suffix='.html',
                                          delete=False,
                                          dir=os.path.dirname(deck_html_path),
                                          ) as f:
            f.write(deck_html_for_render)
            render_path = f.name
        # We now operate on the stripped HTML for splicing too — its
        # slide spans match the screenshots taken from the same source.
        deck_html = deck_html_for_render
    else:
        render_path = deck_html_path

    # 1. Render screenshots
    if screenshot_dir is None:
        ss_dir = tempfile.mkdtemp(prefix='vti_decorator_')
    else:
        ss_dir = screenshot_dir

    try:
        screenshots = screenshot_slides(render_path, ss_dir)

        # 2. Enumerate slide spans in the source deck HTML
        spans = _enumerate_slides(deck_html)
        if len(spans) != len(screenshots):
            n = min(len(spans), len(screenshots))
            spans = spans[:n]
            screenshots = screenshots[:n]

        # 3. Decorate each slide; rebuild deck HTML by splicing.
        #    v0.5.2 — only .slide.layout-grid gets decorated. Special slides
        #    (cover, toc, section-divider, contact, closing, narrator pages)
        #    are passed through unchanged.
        out_chunks: list[str] = []
        cursor = 0
        n_decorated = 0
        n_skipped = 0
        for (start, end), shot in zip(spans, screenshots):
            out_chunks.append(deck_html[cursor:start])
            slide_html = deck_html[start:end]
            if _is_decoratable_slide(slide_html):
                slide_meta = _slide_meta_from_html(slide_html)
                decorated = decorate_slide(slide_html, slide_meta, shot,
                                            strategies=strategies)
                out_chunks.append(decorated)
                n_decorated += 1
            else:
                # Skip special slides — they're already richly designed.
                out_chunks.append(slide_html)
                n_skipped += 1
            cursor = end
        out_chunks.append(deck_html[cursor:])
        decorated_deck = ''.join(out_chunks)

        # 4. Inject decoration-layer CSS once at top of <head>
        decorated_deck = _ensure_decoration_css(decorated_deck)
    finally:
        if not keep_screenshots and screenshot_dir is None:
            import shutil
            shutil.rmtree(ss_dir, ignore_errors=True)
        # Cleanup temp stripped-render file if we made one
        if render_path != deck_html_path and os.path.exists(render_path):
            try:
                os.unlink(render_path)
            except OSError:
                pass

    if output_path:
        Path(output_path).write_text(decorated_deck, encoding='utf-8')
    return decorated_deck


def decorate_html(deck_html: str, *,
                  screenshot_dir: Optional[str] = None,
                  strategies: Union[str, list] = 'auto') -> str:
    """String-in / string-out variant of decorate(). Writes the input
    HTML to a temp file, calls decorate(), returns the decorated string.
    """
    with tempfile.NamedTemporaryFile('w', suffix='.html',
                                      delete=False) as f:
        f.write(deck_html)
        tmp_path = f.name
    try:
        return decorate(tmp_path, screenshot_dir=screenshot_dir,
                        strategies=strategies)
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Slide meta extraction from rendered HTML — best-effort heuristic.
# ---------------------------------------------------------------------------
_SECTION_LABEL_RE = re.compile(
    r'<[^>]+class="[^"]*chrome-section[^"]*"[^>]*>([^<]+)</',
    re.IGNORECASE,
)
_TITLE_LABEL_RE = re.compile(
    r'<[^>]+class="[^"]*chrome-title[^"]*"[^>]*>([^<]+)</',
    re.IGNORECASE,
)
_PAGE_NUM_RE = re.compile(
    r'<[^>]+class="[^"]*chrome-page-number[^"]*"[^>]*>([^<]+)</',
    re.IGNORECASE,
)


def _slide_meta_from_html(slide_html: str) -> dict:
    """Best-effort: pull section_name / slide_title / page_number from
    chrome HTML.
    """
    section = _SECTION_LABEL_RE.search(slide_html)
    title   = _TITLE_LABEL_RE.search(slide_html)
    page    = _PAGE_NUM_RE.search(slide_html)
    try:
        page_num = int((page.group(1).strip() if page else '0') or 0)
    except ValueError:
        page_num = 0
    return {
        'section_name': (section.group(1).strip() if section else ''),
        'slide_title':  (title.group(1).strip() if title else ''),
        'page_number':  page_num,
    }


# ---------------------------------------------------------------------------
# Decoration CSS — injected once into the deck's <head>
#
# v0.5.1 — minimal CSS. Only sets z-index on the decoration layer; does
# NOT override the page-builder's `position: absolute` on
# `.vti-slide-content`. The original v0.5 CSS set `position: relative`
# on .vti-slide-content via a sibling selector, which broke the
# page-builder layout: page-builder uses `position: absolute; left:56;
# right:56; top:70; bottom:64` to inset content from chrome — when
# position became relative, the right/bottom inset stopped applying and
# content stretched to the full 1280px slide width, causing visible
# right-edge overflow on every slide.
#
# Stacking still works: decoration layer comes BEFORE content in
# document order, both sit inside the same stacking context (the slide
# div has `position: relative`), and chrome elements have explicit
# `z-index: 10` to stay above everything. So z-index:0 on the layer is
# sufficient to keep it below content/chrome without touching positions.
# ---------------------------------------------------------------------------
_DECORATION_CSS = """\
/* vti-slide-decorator v0.5 — overlay layer styles */
.vti-decoration-layer { z-index: 0; }
.vti-decor { box-sizing: border-box; }
.vti-decor svg { display: block; width: 100%; height: 100%; }
"""

_DECOR_CSS_MARKER = "/* vti-slide-decorator v0.5 — overlay layer styles */"


def _ensure_decoration_css(deck_html: str) -> str:
    """Inject decoration CSS into <head> exactly once."""
    if _DECOR_CSS_MARKER in deck_html:
        return deck_html
    head_close = deck_html.lower().find('</head>')
    if head_close < 0:
        return f'<style>\n{_DECORATION_CSS}\n</style>\n' + deck_html
    inject = f'<style>\n{_DECORATION_CSS}\n</style>\n'
    return deck_html[:head_close] + inject + deck_html[head_close:]


# ---------------------------------------------------------------------------
# Convenience: full debug pipeline
# ---------------------------------------------------------------------------
def debug_analyze_screenshots(screenshot_paths: list[str], *,
                              output_dir: str = '/tmp/decorator_debug') -> dict:
    """Run whitespace detection + classification on a batch of slide
    screenshots. Saves debug overlay images. Returns per-slide gap data.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    results = {}
    for sp in screenshot_paths:
        name = Path(sp).stem
        gaps = detect_gaps(sp)
        out_path = os.path.join(output_dir, f'{name}_gaps.png')
        visualize_gaps(sp, gaps, out_path)
        classified = classify_slide_gaps(gaps)
        strategy = select_strategy('', classified)
        results[name] = {
            'screenshot': sp,
            'overlay':    out_path,
            'gap_count':  len(gaps),
            'gaps':       [g.to_dict() for g in gaps],
            'strategy':   strategy,
        }
    return results


if __name__ == '__main__':
    import sys
    import json
    if len(sys.argv) > 1:
        in_path = sys.argv[1]
        out_path = sys.argv[2] if len(sys.argv) > 2 else \
                    in_path.replace('.html', '_decorated.html')
        print(f"Decorating {in_path} → {out_path}")
        decorate(in_path, output_path=out_path)
        print("Done.")
    else:
        print("vti-slide-decorator — pipeline status:")
        print(json.dumps(pipeline_status(), indent=2))
