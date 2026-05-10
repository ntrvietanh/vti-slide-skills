"""
Phase 1 — Source ingester.

Reads source material into a normalized representation that Claude can
reason over. Output shape::

    {
        "kind":  "markdown" | "text" | "docx" | "pdf" | "pptx" | "html",
        "path":  str,
        "text":  str,             # extracted plain text
        "assets": [               # extracted images / tables / etc.
            {"kind": "image", "path": "...", "caption": "..."},
            {"kind": "table", "path": "...", "preview": "..."},
        ],
        "structure": {
            "headings": [...],    # top-level outline if any
            "page_count": int,    # for paginated formats
        }
    }

Readers
-------
- markdown / text  →  Python stdlib (always available)
- docx             →  uses docx skill (/mnt/skills/public/docx/SKILL.md)
- pdf              →  uses pdf-reading skill (/mnt/skills/public/pdf-reading/)
- pptx             →  uses pptx skill (/mnt/skills/public/pptx/SKILL.md)
- html             →  Python stdlib + html.parser

For binary formats (docx/pdf/pptx) this module returns a *stub* result
with `text=""` and a `next_action` field directing Claude to read the
relevant SKILL.md and fill in the data. That way we don't fight format
parsing here — we delegate to the proven skills.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import html as _html

# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------
_EXT_TO_KIND = {
    ".md":   "markdown",
    ".markdown": "markdown",
    ".txt":  "text",
    ".docx": "docx",
    ".pdf":  "pdf",
    ".pptx": "pptx",
    ".html": "html",
    ".htm":  "html",
    # v3.14 — video formats
    ".mp4":  "video",
    ".mov":  "video",
    ".webm": "video",
    ".m4v":  "video",
}


def detect_kind(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    return _EXT_TO_KIND.get(suffix, "unknown")


# ---------------------------------------------------------------------------
# v3.14 — PPTX image extractor (closes #2 — was previously per-session ad-hoc)
# ---------------------------------------------------------------------------
def extract_pptx_images(pptx_path: str | Path,
                        out_dir: str | Path,
                        min_size_bytes: int = 5000,
                        auto_classify: bool = False,
                        ) -> list[dict]:
    """Extract substantive images from a PPTX file's ``ppt/media/`` directory.

    Args:
        pptx_path: path to a .pptx file
        out_dir: destination directory (created if missing)
        min_size_bytes: skip images smaller than this (filters logo strips,
                        decorative spacers). Default 5000 = 5KB.
        auto_classify: v3.18 — if True, run ``classify_image_kind()`` on
                       each saved image and add ``kind_guess``,
                       ``confidence`` fields. Default False to keep API
                       backward-compatible.

    Returns:
        List of asset dicts ready for ``ContextDoc.source_assets``::

            [{'kind': 'image', 'path': '/abs/path/image01.png',
              'caption': '', 'size_bytes': 12345}, ...]

        With ``auto_classify=True`` each entry additionally carries::

            'kind_guess':  'content' | 'chrome' | 'stock' | 'unknown',
            'confidence':  0.0..1.0,
            'classify_reasons': [str, ...]   # human-readable signals

    Phase 1 ANALYZE step calls this for every uploaded PPTX. Pre-v3.14
    each session reinvented zipfile inspection; v3.14 makes it a helper.
    v3.18 adds the optional ``auto_classify`` heuristic (closes gap #6).
    """
    import zipfile
    pptx_path = Path(pptx_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not pptx_path.exists():
        raise FileNotFoundError(f"pptx not found: {pptx_path}")

    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp",
                  ".webp", ".svg", ".emf", ".wmf"}
    saved: list[dict] = []
    with zipfile.ZipFile(pptx_path) as zf:
        for info in zf.infolist():
            if not info.filename.startswith("ppt/media/"):
                continue
            if info.is_dir():
                continue
            ext = Path(info.filename).suffix.lower()
            if ext not in image_exts:
                continue
            if info.file_size < min_size_bytes:
                continue
            target = out_dir / Path(info.filename).name
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            saved.append({
                "kind":       "image",
                "path":       str(target),
                "caption":    "",
                "size_bytes": info.file_size,
            })
    if auto_classify:
        for entry in saved:
            cls = classify_image_kind(entry["path"], size_bytes=entry["size_bytes"])
            entry["kind_guess"]       = cls["kind"]
            entry["confidence"]       = cls["confidence"]
            entry["classify_reasons"] = cls["reasons"]
    return saved


# ---------------------------------------------------------------------------
# v3.18 — Image content classifier (closes gap #6)
# ---------------------------------------------------------------------------
def classify_image_kind(image_path: str | Path,
                        size_bytes: int | None = None) -> dict:
    """Heuristic classifier: content vs chrome vs stock vs unknown.

    Closes gap #6: pre-v3.18, ``extract_pptx_images`` returned every
    image's path with no signal about whether it's worth lifting.
    Phase 4 build scripts then chose images by file size — wrong
    heuristic, since chrome graphics (decorative dividers, full-bleed
    section banners) are often the *largest* images in a deck. The v5
    iteration of the cross-domain deck hit exactly this trap: 4 of 6
    "lifted" images turned out to be chrome.

    The classifier is a fast pre-screen — Claude should still
    visually inspect anything classified ``content`` before lifting,
    per Principle 9. The classifier's job is to filter out the obvious
    chrome / stock so visual inspection is reserved for the candidates
    that actually have a chance of being useful.

    Heuristic signals
    -----------------

    - **Aspect ratio**:
      - 16:9 or close (1.6-1.9:1) → likely full-slide chrome (banner, divider)
      - extreme wide (>3:1) or tall (<0.4:1) → likely chrome strip
      - 4:3 / 3:4 / 1:1 / phone (9:16, 9:19.5) → likely content
    - **File size**:
      - >2 MB AND aspect 16:9 → strong chrome signal (full-bleed render)
      - <30 KB → likely icon/logo (treated as chrome for content purposes)
    - **Filename**:
      - contains 'bg', 'background', 'banner', 'divider', 'cover' → chrome
      - contains 'logo', 'icon' → chrome (in lift-decision sense)
      - contains 'screenshot', 'mockup', 'dashboard', 'ui' → content
    - **Stock-photo signals** (lower confidence):
      - 16:9 + photo-like file size (200KB-1.5MB) + no filename signal
        → tentative ``stock``

    Args:
        image_path: path to image file (PNG/JPG/JPEG)
        size_bytes: optional pre-known file size (skips a stat() call)

    Returns::

        {
          'kind':       'content' | 'chrome' | 'stock' | 'unknown',
          'confidence': float (0.0..1.0),  # how strong the signals are
          'reasons':    [str, ...],         # human-readable explanation
          'metrics':    {                   # raw signals for debugging
              'aspect_ratio': float | None,
              'size_bytes':   int,
              'width':        int | None,
              'height':       int | None,
              'filename':     str,
          }
        }

    Without PIL/Pillow available, only filename + size signals are used
    (degraded confidence). With PIL, aspect ratio is added.
    """
    from os.path import basename
    p = Path(image_path)
    fname = basename(str(p)).lower()

    if size_bytes is None:
        try:
            size_bytes = p.stat().st_size
        except OSError:
            size_bytes = 0

    width: int | None = None
    height: int | None = None
    aspect: float | None = None
    try:
        from PIL import Image  # optional dep
        with Image.open(p) as im:
            width, height = im.size
            if height:
                aspect = width / height
    except Exception:
        # PIL not available or image unreadable — proceed with filename+size only
        pass

    reasons: list[str] = []
    score = {"content": 0.0, "chrome": 0.0, "stock": 0.0}

    # --- Filename signals ---------------------------------------------------
    chrome_tokens = ("bg", "background", "banner", "divider", "cover",
                     "footer", "header_", "watermark")
    content_tokens = ("screenshot", "mockup", "dashboard", "ui_", "_ui",
                      "diagram", "chart", "architecture", "flow_",
                      "frame_")  # video keyframes are content
    icon_tokens = ("logo", "icon_", "_icon")

    if any(t in fname for t in chrome_tokens):
        score["chrome"] += 0.6
        reasons.append(f"filename contains chrome token")
    if any(t in fname for t in content_tokens):
        score["content"] += 0.5
        reasons.append(f"filename contains content token")
    if any(t in fname for t in icon_tokens):
        score["chrome"] += 0.4
        reasons.append("filename suggests icon/logo (chrome for lift purposes)")

    # --- Size signals -------------------------------------------------------
    if size_bytes < 30_000:
        score["chrome"] += 0.3
        reasons.append(f"small file ({size_bytes}B) — likely icon/logo")

    # --- Aspect signals (only if PIL succeeded) -----------------------------
    if aspect is not None:
        # 16:9 ≈ 1.778
        if 1.6 <= aspect <= 1.95:
            score["chrome"] += 0.35
            reasons.append(f"aspect {aspect:.2f} matches slide-banner 16:9")
            if size_bytes > 2_000_000:
                score["chrome"] += 0.30
                reasons.append("large file + 16:9 → strong chrome signal")
            elif 200_000 <= size_bytes <= 1_500_000:
                score["stock"] += 0.30
                reasons.append("photo-size file + 16:9 → possible stock photo")
        elif aspect > 3.0 or aspect < 0.4:
            score["chrome"] += 0.5
            reasons.append(f"extreme aspect {aspect:.2f} — strip/banner")
        elif 0.7 <= aspect <= 1.4:
            score["content"] += 0.35
            reasons.append(f"square-ish aspect {aspect:.2f} — likely content")
        elif 0.4 <= aspect <= 0.65 or 1.4 < aspect < 1.6:
            score["content"] += 0.30
            reasons.append(f"aspect {aspect:.2f} matches phone/UI shape")

    # --- Decision -----------------------------------------------------------
    best_kind = max(score.items(), key=lambda kv: kv[1])
    if best_kind[1] < 0.30:
        kind = "unknown"
        confidence = 0.0
    else:
        kind = best_kind[0]
        # Cap at 1.0; subtract competing-signal noise
        competing = sum(v for k, v in score.items() if k != kind)
        confidence = min(1.0, max(0.0, best_kind[1] - 0.5 * competing))

    return {
        "kind":       kind,
        "confidence": round(confidence, 2),
        "reasons":    reasons,
        "metrics": {
            "aspect_ratio": round(aspect, 3) if aspect is not None else None,
            "size_bytes":   size_bytes,
            "width":        width,
            "height":       height,
            "filename":     fname,
        },
    }


# ---------------------------------------------------------------------------
# v3.14 — Video stub helper (closes #1)
# ---------------------------------------------------------------------------
def video_keyframes_stub(video_path: str | Path) -> dict:
    """Return a stub ingester result for a video file.

    Videos are not directly readable as text. Phase 1 should:
        1. Use ffprobe to inspect duration/resolution.
        2. Optionally extract keyframes (e.g. 1 every 30s) via ffmpeg
           and treat them as source images.
        3. Optionally transcribe audio via whisper (out of skill scope).

    The returned dict directs Claude to do step 1+2 manually. After
    keyframes are extracted, build the final result via
    ``ingest_pre_extracted(kind='video', text='', assets=[...])``.
    """
    p = Path(video_path)
    return {
        "kind":      "video",
        "path":      str(p),
        "text":      "",
        "assets":    [],
        "structure": {"headings": [], "page_count": None},
        "next_action": (
            f"Video format. Use ffprobe for metadata + ffmpeg to extract "
            f"keyframes (e.g. ``ffmpeg -i {p.name} -vf fps=1/30 frame_%02d.jpg``), "
            f"treat keyframes as image assets, then call ingest_pre_extracted("
            f"kind='video', text='', assets=[{{'kind':'image','path':...}},...]). "
            f"Optionally transcribe audio (whisper) for text content."
        ),
    }


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Direct readers (text-based formats)
# ---------------------------------------------------------------------------
def _read_markdown(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    headings = re.findall(r"^(#{1,6})\s+(.+)$", text, flags=re.MULTILINE)
    return {
        "kind": "markdown", "path": str(path), "text": text,
        "assets": [],
        "structure": {
            "headings": [{"level": len(h), "text": t} for h, t in headings],
            "page_count": None,
        },
    }


def _read_text(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "kind": "text", "path": str(path), "text": text,
        "assets": [],
        "structure": {"headings": [], "page_count": None},
    }


def _read_html(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Crude tag stripper — preserves text and headings
    headings: list[dict] = []
    for m in re.finditer(r"<h([1-6])[^>]*>(.+?)</h\1>", raw,
                          flags=re.IGNORECASE | re.DOTALL):
        headings.append({
            "level": int(m.group(1)),
            "text":  _html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip(),
        })
    text = _html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "kind": "html", "path": str(path), "text": text,
        "assets": [],
        "structure": {"headings": headings, "page_count": None},
    }


# ---------------------------------------------------------------------------
# Stubs for binary formats — direct Claude to the right skill
# ---------------------------------------------------------------------------
def _stub_for_format(path: Path, kind: str, skill_path: str) -> dict:
    return {
        "kind": kind, "path": str(path), "text": "",
        "assets": [],
        "structure": {"headings": [], "page_count": None},
        "next_action": (
            f"Binary format ({kind}). Read the skill at {skill_path} "
            f"to extract text + images, then re-call ingest_source() with "
            f"the extracted data via ingest_pre_extracted()."
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ingest_source(path: str | Path) -> dict:
    """Ingest a source file. Returns a normalized dict (see module docstring).

    For text-based formats (md, txt, html) returns the parsed content
    directly. For binary formats (docx, pdf, pptx) returns a stub with
    a ``next_action`` field directing Claude to the right skill.

    Raises FileNotFoundError if path doesn't exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"source not found: {path}")

    kind = detect_kind(p)
    if kind == "markdown":
        return _read_markdown(p)
    if kind == "text":
        return _read_text(p)
    if kind == "html":
        return _read_html(p)
    if kind == "docx":
        return _stub_for_format(p, "docx", "/mnt/skills/public/docx/SKILL.md")
    if kind == "pdf":
        return _stub_for_format(p, "pdf",
                                "/mnt/skills/public/pdf-reading/SKILL.md")
    if kind == "pptx":
        return _stub_for_format(p, "pptx", "/mnt/skills/public/pptx/SKILL.md")
    if kind == "video":
        return video_keyframes_stub(p)
    return {
        "kind": "unknown", "path": str(p), "text": "",
        "assets": [],
        "structure": {"headings": [], "page_count": None},
        "next_action": f"Unrecognized format {p.suffix!r} — ask user how to handle.",
    }


def ingest_pre_extracted(path: str | Path,
                         kind: str,
                         text: str,
                         assets: list | None = None,
                         structure: dict | None = None) -> dict:
    """Build an ingester result from pre-extracted data.

    Used after Claude reads a binary format via the appropriate skill
    (docx/pdf/pptx) and has the text + image list ready.
    """
    return {
        "kind":      kind,
        "path":      str(path),
        "text":      text,
        "assets":    assets or [],
        "structure": structure or {"headings": [], "page_count": None},
    }


def summarize_source(ingested: dict, max_chars: int = 200) -> str:
    """Quick summary of an ingested source — the first N chars of text
    after stripping markdown headers and excess whitespace. Useful as a
    starter for ContextDoc.source_summary that Claude then refines."""
    txt = ingested.get("text", "")
    txt = re.sub(r"^#{1,6}\s+", "", txt, flags=re.MULTILINE)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) <= max_chars:
        return txt
    return txt[:max_chars].rsplit(" ", 1)[0] + "…"
