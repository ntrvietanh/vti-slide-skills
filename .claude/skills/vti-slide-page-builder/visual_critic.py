"""Visual critique loop (v4.0 / M4) — the system finally LOOKS at its output.

Pre-M4 the pipeline composed HTML and shipped it without rendering a pixel:
every quality judgement was a static estimate made before content existed.
This module closes that loop. It renders the composed deck in headless
Chromium and MEASURES each slide — both in-page (JS) and from the rendered
PNG (Pillow), no vision model needed:

  * minimum rendered font size — HTML text only; SVG chart/diagram text is
    excluded because it scales with its cell (raw px would false-flag),
  * content overflow / clipping past the 1280×720 slide box,
  * blank charts (an ECharts placeholder that produced no <svg>),
  * ink ratio + ink centroid from the PNG → real whitespace / "content
    dumped at the top" (grid cells always fill, so a DOM-bbox fill metric
    lies; pixels don't),
  * near-duplicate neighbours (average-hash on the PNGs).

The loop is deliberately LIGHT (the user's choice): it AUTO-FIXES only the
one issue with a safe mechanical remedy — a sparse, top-clustered slide gets
``slide_meta.vertical_align = "center"`` (redistributes existing empty space
on auto rows; a no-op when rows already fill, so never harmful) — and
SURFACES everything else in a render-for-review sheet (real PNGs + verdict
badges) for the human ★ and for Claude to propose targeted edits.

Public surface
--------------
- ``critique(html_path)``            → [report dict] (renders PNGs + measures)
- ``measure_html(html_path)``        → [JS-only measure] (no screenshot)
- ``auto_repair(slides, compose_fn)``→ {slides, reports, changelog, rounds}
- ``render_review(html_path, out_html)`` → review sheet Path (PNGs + badges)
"""
from __future__ import annotations

import base64
import html as _html
import tempfile
from pathlib import Path
from typing import Callable

SLIDE_W_PX = 1280
SLIDE_H_PX = 720
CHROME_TOP_PX = 70
CHROME_BOTTOM_PX = 64
CHROME_LR_PX = 56

# Rubric thresholds.
MIN_FONT_PX = 11.0          # below → hard to read when projected (fail)
MAX_OVERFLOW_PX = 2.0       # content beyond the slide box → clipped (fail)
SPARSE_INK = 0.20           # ink ratio below this = sparse
TOP_CLUSTER_CENTROID = 0.35 # ink centroid Y above (higher) third = top-heavy
DUP_HASH_DISTANCE = 4       # avg-hash Hamming ≤ this = near-duplicate (warn)


# ---------------------------------------------------------------------------
# In-page measurement (font / overflow / charts)
# ---------------------------------------------------------------------------
_MEASURE_JS = r"""
() => {
  const slides = Array.from(document.querySelectorAll('.slide'));
  return slides.map((s) => {
    const sr = s.getBoundingClientRect();
    let minFont = Infinity, textCount = 0, overflow = 0;
    let charts = 0, blankCharts = 0;
    s.querySelectorAll('.vti-echart').forEach((c) => {
      charts++; if (!c.querySelector('svg')) blankCharts++;
    });
    s.querySelectorAll('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      overflow = Math.max(overflow, r.right - sr.right, r.bottom - sr.bottom);
      const inSvg = el.closest('svg') !== null;
      if (!inSvg && el.children.length === 0 &&
          el.textContent && el.textContent.trim().length > 0) {
        const fs = parseFloat(getComputedStyle(el).fontSize);
        if (fs && fs < minFont) minFont = fs;
        textCount++;
      }
    });
    return {
      minFontPx: isFinite(minFont) ? Math.round(minFont * 100) / 100 : null,
      textCount,
      overflowPx: Math.round(Math.max(0, overflow)),
      charts, blankCharts,
    };
  });
}
"""


def _ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for visual_critic. Install with:\n"
            "  pip install playwright && python -m playwright install chromium"
        ) from exc


def measure_html(html_path: str | Path) -> list[dict]:
    """Render the deck and run the in-page JS measurement (no screenshot)."""
    html_path = Path(html_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(html_path)
    _ensure_playwright()
    from playwright.sync_api import sync_playwright

    html = html_path.read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            ctx = browser.new_context(
                viewport={"width": SLIDE_W_PX, "height": SLIDE_H_PX},
                device_scale_factor=1,
            )
            page = ctx.new_page()
            page.goto(html_path.as_uri(), wait_until="networkidle")
            page.evaluate("() => document.fonts && document.fonts.ready")
            if "vti-echart" in html:
                try:
                    page.wait_for_function(
                        "window.__vtiChartsReady === true", timeout=8000)
                except Exception:
                    pass
            measures = page.evaluate(_MEASURE_JS)
        finally:
            browser.close()
    for i, m in enumerate(measures):
        m["index"] = i + 1
    return measures


# ---------------------------------------------------------------------------
# PNG metrics: ink ratio + vertical centroid (real whitespace)
# ---------------------------------------------------------------------------
def _png_metrics(png_path: Path, *, white_cut: int = 245) -> dict:
    """Ink ratio + vertical ink centroid over the CONTENT area (chrome cropped).

    ink_ratio: fraction of content-area pixels darker than ``white_cut``.
    centroid_y: 0 (top) .. 1 (bottom) — where the ink mass sits.
    """
    from PIL import Image
    im = Image.open(png_path).convert("L")
    w, h = im.size
    crop = im.crop((
        int(w * CHROME_LR_PX / SLIDE_W_PX), int(h * CHROME_TOP_PX / SLIDE_H_PX),
        int(w * (SLIDE_W_PX - CHROME_LR_PX) / SLIDE_W_PX),
        int(h * (SLIDE_H_PX - CHROME_BOTTOM_PX) / SLIDE_H_PX),
    ))
    W, H = crop.size
    data = crop.load()
    total = 0
    dark = 0
    wsum = 0
    step = 3  # subsample for speed
    for y in range(0, H, step):
        for x in range(0, W, step):
            total += 1
            if data[x, y] < white_cut:
                dark += 1
                wsum += y
    ink = dark / total if total else 0.0
    centroid = (wsum / dark / H) if dark else 0.5
    return {"ink_ratio": round(ink, 4), "centroid_y": round(centroid, 3)}


def _ahash(png_path: Path, size: int = 16) -> int:
    from PIL import Image
    img = Image.open(png_path).convert("L").resize((size, size))
    px = list(img.getdata())
    avg = sum(px) / len(px)
    bits = 0
    for i, v in enumerate(px):
        if v >= avg:
            bits |= (1 << i)
    return bits


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------
def verdict(measure: dict, *,
            min_font_px: float = MIN_FONT_PX,
            max_overflow_px: float = MAX_OVERFLOW_PX) -> dict:
    """Grade one slide. 'fail' = hard defect, 'warn' = human look, 'pass'."""
    issues: list[dict] = []
    mf = measure.get("minFontPx")
    if mf is not None and mf + 0.5 < min_font_px:
        issues.append({"code": "font_too_small", "severity": "fail",
                       "detail": f"min rendered font {mf:.1f}px < {min_font_px:.0f}px"})
    if measure.get("overflowPx", 0) > max_overflow_px:
        issues.append({"code": "overflow", "severity": "fail",
                       "detail": f"content overflows slide by "
                                 f"{measure['overflowPx']:.0f}px (clipped)"})
    if measure.get("blankCharts", 0) > 0:
        issues.append({"code": "blank_chart", "severity": "fail",
                       "detail": f"{measure['blankCharts']} chart(s) rendered empty"})
    ink = measure.get("ink_ratio")
    cen = measure.get("centroid_y")
    if (ink is not None and cen is not None
            and ink < SPARSE_INK and cen < TOP_CLUSTER_CENTROID
            and measure.get("textCount", 0) > 0):
        issues.append({
            "code": "sparse_top_clustered", "severity": "warn",
            "detail": f"ink {ink:.0%}, centroid y={cen:.2f} — content dumped "
                      f"at top, empty base (auto-fix: vertical-center)",
        })
    status = "pass"
    if any(i["severity"] == "fail" for i in issues):
        status = "fail"
    elif issues:
        status = "warn"
    return {"status": status, "issues": issues}


def _annotate_dupes(reports: list[dict], png_paths: list[Path],
                    *, distance: int = DUP_HASH_DISTANCE) -> None:
    hashes = [_ahash(p) for p in png_paths]
    for i in range(1, len(hashes)):
        if _hamming(hashes[i - 1], hashes[i]) <= distance:
            reports[i]["issues"].append({
                "code": "neighbour_dup", "severity": "warn",
                "detail": f"near-identical to slide {i} — vary the layout",
            })
            if reports[i]["status"] == "pass":
                reports[i]["status"] = "warn"


def critique(html_path: str | Path, *,
             images_dir: str | Path | None = None,
             scale: int = 1) -> list[dict]:
    """Full visual judgement: render PNGs, measure (JS + ink), grade, dedup.

    Returns one report per slide: ``{index, status, issues, png, minFontPx,
    overflowPx, ink_ratio, centroid_y, ...}``. Renders the deck ONCE.
    """
    html_path = Path(html_path).resolve()
    if images_dir is None:
        images_dir = Path(tempfile.mkdtemp(prefix="vti_critic_"))
    try:
        from exporter import render_slides_to_pngs
    except ImportError as exc:
        raise RuntimeError(
            "critique needs vti-slide-pptx-exporter on PYTHONPATH "
            "(render_slides_to_pngs)."
        ) from exc

    png_paths = render_slides_to_pngs(html_path, images_dir, scale=scale, force=True)
    js = measure_html(html_path)
    reports: list[dict] = []
    for i, png in enumerate(png_paths):
        m = dict(js[i]) if i < len(js) else {"index": i + 1}
        m.update(_png_metrics(png))
        m["png"] = str(png)
        reports.append({**m, **verdict(m)})
    _annotate_dupes(reports, png_paths)
    return reports


# ---------------------------------------------------------------------------
# Light auto-repair (≤2 rounds) — only the safe mechanical fix
# ---------------------------------------------------------------------------
def auto_repair(slides: list[dict],
                compose_fn: Callable[[list[dict]], str],
                *,
                max_rounds: int = 2) -> dict:
    """Compose → critique → apply the SAFE fix → re-compose, up to max_rounds.

    The only auto-applied fix balances whitespace on a sparse, top-clustered
    slide (``slide_meta.vertical_align='center'``). It redistributes existing
    empty space on auto rows and is a no-op when rows already fill — never
    destructive. Every other finding is returned for the human/LLM.

    ``compose_fn(slides) -> deck HTML`` is passed as a callback so this
    page-builder module does not import the creator.
    """
    import copy
    slides = copy.deepcopy(slides)
    tmpdir = Path(tempfile.mkdtemp(prefix="vti_repair_"))
    tmp_html = tmpdir / "deck.html"
    changelog: list[str] = []
    reports: list[dict] = []
    rounds = 0

    for rounds in range(1, max_rounds + 1):
        tmp_html.write_text(compose_fn(slides), encoding="utf-8")
        reports = critique(tmp_html, images_dir=tmpdir / f"r{rounds}")
        applied = False
        for rep in reports:
            idx = rep["index"] - 1
            if idx >= len(slides):
                continue
            if any(i["code"] == "sparse_top_clustered" for i in rep["issues"]):
                meta = slides[idx].setdefault("slide_meta", {})
                if meta.get("vertical_align") != "center":
                    meta["vertical_align"] = "center"
                    changelog.append(
                        f"slide {rep['index']}: vertical_align→center "
                        f"(ink {rep.get('ink_ratio', 0):.0%}, "
                        f"centroid {rep.get('centroid_y', 0):.2f})")
                    applied = True
        if not applied:
            break

    return {"slides": slides, "reports": reports, "changelog": changelog,
            "rounds": rounds}


# ---------------------------------------------------------------------------
# Render-for-review sheet (real PNGs + verdict badges)
# ---------------------------------------------------------------------------
_BADGE = {"pass": ("#1A7A4A", "PASS"), "warn": ("#ED8B2C", "WARN"),
          "fail": ("#B02020", "FAIL")}


def render_review(html_path: str | Path,
                  out_html: str | Path,
                  *, scale: int = 1) -> Path:
    """Render every slide, grade it, and build a single review HTML — each
    slide's PNG + verdict badge + measured issues. Makes the Phase-6 ★
    checkpoint sighted (real pixels, not a descriptor wireframe)."""
    out_html = Path(out_html).resolve()
    images_dir = out_html.parent / "review-images"
    reports = critique(html_path, images_dir=images_dir, scale=scale)

    cards = []
    for rep in reports:
        color, label = _BADGE.get(rep["status"], _BADGE["pass"])
        b64 = base64.b64encode(Path(rep["png"]).read_bytes()).decode()
        issue_html = "".join(
            f'<li><b>{_html.escape(it["code"])}</b> — {_html.escape(it["detail"])}</li>'
            for it in rep["issues"]
        ) or '<li class="ok">no issues measured</li>'
        meta = (f'min-font {rep.get("minFontPx")}px · ink {rep.get("ink_ratio",0):.0%} '
                f'· overflow {rep.get("overflowPx",0)}px')
        cards.append(f"""
        <div class="rev-card">
          <div class="rev-head">
            <span class="rev-idx">Slide {rep['index']}</span>
            <span class="rev-badge" style="background:{color}">{label}</span>
          </div>
          <img src="data:image/png;base64,{b64}" alt="slide {rep['index']}"/>
          <div class="rev-meta">{meta}</div>
          <ul class="rev-issues">{issue_html}</ul>
        </div>""")

    n_fail = sum(1 for r in reports if r["status"] == "fail")
    n_warn = sum(1 for r in reports if r["status"] == "warn")
    n_pass = len(reports) - n_fail - n_warn
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>VTI deck — visual review</title>
<style>
  body {{ margin:0; background:#EEF3F9; font-family:'Plus Jakarta Sans',system-ui,sans-serif; color:#1F2A3A; }}
  .rev-top {{ padding:18px 28px; background:#fff; border-bottom:1px solid #C8DCF0; position:sticky; top:0; z-index:2; }}
  .rev-top h1 {{ margin:0; font-size:18px; }}
  .rev-top .sum {{ color:#4B5A6E; font-size:13px; margin-top:4px; }}
  .rev-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:22px; padding:24px 28px; }}
  .rev-card {{ background:#fff; border:1px solid #C8DCF0; border-radius:12px; overflow:hidden; box-shadow:0 3px 10px rgba(5,25,52,.07); }}
  .rev-head {{ display:flex; justify-content:space-between; align-items:center; padding:10px 14px; }}
  .rev-idx {{ font-weight:600; font-size:14px; }}
  .rev-badge {{ color:#fff; font-size:11px; font-weight:600; padding:3px 10px; border-radius:999px; letter-spacing:.04em; }}
  .rev-card img {{ width:100%; display:block; border-top:1px solid #E4ECF5; }}
  .rev-meta {{ font-size:11px; color:#6B7A8D; padding:6px 18px 0; }}
  .rev-issues {{ margin:4px 0 14px; padding:2px 18px 0 30px; font-size:12.5px; color:#4B5A6E; }}
  .rev-issues .ok {{ color:#1A7A4A; list-style:none; margin-left:-14px; }}
</style></head><body>
  <div class="rev-top">
    <h1>Visual review — {len(reports)} slides</h1>
    <div class="sum">{n_fail} fail · {n_warn} warn · {n_pass} pass · rendered + measured (not a wireframe). Approve at the ★ or send fixes.</div>
  </div>
  <div class="rev-grid">{''.join(cards)}</div>
</body></html>"""
    out_html.write_text(doc, encoding="utf-8")
    return out_html


__all__ = [
    "measure_html", "critique", "verdict", "auto_repair", "render_review",
    "MIN_FONT_PX", "MAX_OVERFLOW_PX", "SPARSE_INK",
]
