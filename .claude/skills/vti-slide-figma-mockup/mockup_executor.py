"""Post-Figma file landing + sidecar JSON writer.

The orchestrator (Claude in the loop) renders the Figma file by
calling MCP tools, then hands the raw outputs here. This module is
the **only** place that touches the filesystem under ``work/mockups/``
so the path conventions stay in one spot.

Output layout per render::

    work/mockups/
      INDEX.md                                 # auto-appended one-liner per render
      <slide_id>_<asset_id>/
        render.png                             # mandatory
        render.svg                             # optional
        meta.json                              # the mockup_spec

``meta.json`` is what the Phase 3 driver loads back into
``content_plan["mockup_spec"]``. The PNG path inside it is repo-relative
(``work/mockups/.../render.png``) so the page-builder's image lookup
(`compose_slide_grid` searches `[SKILL_ROOT, cwd]`) finds it.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

VERSION = "0.2.0"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_SAFE_ID = re.compile(r"[^A-Za-z0-9_-]+")


def _safe(part: str) -> str:
    """Squash anything outside ``[A-Za-z0-9_-]`` to ``_``.

    Used for asset directory names so a stray slash or space in
    ``slide_id`` / ``asset_id`` doesn't escape ``work/mockups/``.
    """
    cleaned = _SAFE_ID.sub("_", (part or "").strip())
    return cleaned or "x"


def asset_dir(work_root: str | Path, slide_id: str, asset_id: str) -> Path:
    """Return ``<work_root>/mockups/<slide_id>_<asset_id>/`` as a Path."""
    return Path(work_root) / "mockups" / f"{_safe(slide_id)}_{_safe(asset_id)}"


# ---------------------------------------------------------------------------
# Dimension fallbacks
# ---------------------------------------------------------------------------
def _png_dims(png_bytes: bytes) -> tuple[int, int]:
    """Best-effort PNG dimension extraction without Pillow.

    PNG signature is 8 bytes, then an IHDR chunk where bytes 16-19 =
    width, 20-23 = height (big-endian uint32). This avoids a Pillow
    dependency for what is essentially a header read.
    """
    if len(png_bytes) < 24:
        raise ValueError("PNG too short to contain IHDR")
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG (bad signature)")
    w = int.from_bytes(png_bytes[16:20], "big")
    h = int.from_bytes(png_bytes[20:24], "big")
    return w, h


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def record_render(
    *,
    task: dict[str, Any],
    slide_id: str,
    asset_id: str,
    figma_url: str,
    figma_file_key: str,
    figma_node_id: str,
    png_bytes: bytes,
    svg_str: str | None = None,
    natural_w: int | None = None,
    natural_h: int | None = None,
    work_root: str | Path = "work",
) -> dict[str, Any]:
    """Land a Figma render to disk and return the ``mockup_spec`` dict.

    Args
    ----
    task : dict
        The task descriptor returned by ``mockup_builder.make_*``.
    slide_id, asset_id : str
        Stable identifiers — combined into the asset directory name.
        ``slide_id`` typically matches the slide's ``slide_id``;
        ``asset_id`` is ``"01"``, ``"02"``, ... when one slide has
        multiple mockups.
    figma_url, figma_file_key, figma_node_id : str
        Returned by ``create_new_file`` / ``use_figma`` MCP calls.
        ``figma_url`` is what gets surfaced in INDEX.md.
    png_bytes : bytes
        Output of ``mcp__claude_ai_Figma__get_screenshot``. Mandatory.
    svg_str : str | None
        Optional SVG export. If Figma's node is exportable as SVG, pass
        it here and ``render.svg`` will be written too. Otherwise
        ``svg_path`` in the spec is ``None``.
    natural_w, natural_h : int | None
        Actual pixel dimensions of the render. If omitted, read from
        the PNG header. Pass explicitly when Figma's get_metadata gives
        a more authoritative number (e.g. for hi-DPI exports).
    work_root : str | Path
        Per-deck working directory. Defaults to ``"work"`` (matches
        repo convention).

    Returns
    -------
    dict — the ``mockup_spec`` ready to assign to
    ``content_plan["mockup_spec"]``.
    """
    if not png_bytes:
        raise ValueError("png_bytes is empty — get_screenshot must return PNG bytes")

    out_dir = asset_dir(work_root, slide_id, asset_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    png_path = out_dir / "render.png"
    png_path.write_bytes(png_bytes)

    svg_path: Path | None = None
    if svg_str:
        svg_path = out_dir / "render.svg"
        svg_path.write_text(svg_str, encoding="utf-8")

    if natural_w is None or natural_h is None:
        w, h = _png_dims(png_bytes)
        natural_w = natural_w or w
        natural_h = natural_h or h

    spec: dict[str, Any] = {
        "kind":           task["kind"],
        "brief":          task["brief"],
        "frame_label":    task.get("frame_label"),
        "style":          task.get("style"),
        "title":          task.get("title"),
        "subtitle":       task.get("subtitle"),
        "captions":       task.get("captions") or [],
        "png_path":       str(png_path).replace("\\", "/"),
        "svg_path":       (str(svg_path).replace("\\", "/")) if svg_path else None,
        "figma_url":      figma_url,
        "figma_file_key": figma_file_key,
        "figma_node_id":  figma_node_id,
        "natural_w":      int(natural_w),
        "natural_h":      int(natural_h),
        "rendered_at":    datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }

    meta_path = out_dir / "meta.json"
    meta_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    _append_index(work_root, slide_id, asset_id, spec)
    return spec


def _append_index(work_root: str | Path, slide_id: str, asset_id: str,
                  spec: dict[str, Any]) -> None:
    """Append one line per render to ``work/mockups/INDEX.md``.

    The user opens this file to grab Figma URLs for hand-editing. Each
    entry has the slide id, kind, title, and the Figma URL.
    """
    index = Path(work_root) / "mockups" / "INDEX.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    if not index.exists():
        index.write_text(
            "# VTI mockups index\n\n"
            "One line per rendered mockup. Open the Figma URL to "
            "tweak the design — the next driver re-run will overwrite "
            "the PNG, so commit your Figma edits before re-running.\n\n",
            encoding="utf-8",
        )
    entry = (
        f"- `{_safe(slide_id)}_{_safe(asset_id)}` ({spec['kind']}, "
        f"{spec['natural_w']}×{spec['natural_h']}) — "
        f"**{spec.get('title') or 'untitled'}** — "
        f"[Figma]({spec['figma_url']})\n"
    )
    with index.open("a", encoding="utf-8") as f:
        f.write(entry)


def record_html_render(
    *,
    task: dict[str, Any],
    slide_id: str,
    asset_id: str,
    screens: list[dict[str, str]],
    work_root: str | Path = "work",
    scale: int = 2,
    viewport: tuple[int, int] | None = None,
    full_page: bool = True,
) -> dict[str, Any]:
    """Render via the HTML backend and land everything to work/mockups/.

    Args
    ----
    task : dict
        Task descriptor from ``mockup_builder.make_*(backend='html')``.
    slide_id, asset_id : str
        Stable identifiers for the asset directory.
    screens : list of dicts
        Per-screen ``{"url": ..., "body_html": ..., "time": ...}``.
        - browser kinds use ``url``; phone kinds use ``time``.
        - single-screen kinds: pass a 1-item list.
        - flow kinds: pass exactly 3 items.
    work_root : str | Path
        Per-deck working directory, defaults to ``"work"``.
    scale : int
        Device scale factor for the PNG (2 = retina-quality).

    Returns
    -------
    dict — the ``mockup_spec`` ready to assign to
    ``content_plan["mockup_spec"]``. Plus an extra ``html_path`` field
    pointing to the saved source HTML.
    """
    import html_backend  # local import — playwright not needed for builder

    if task.get("backend") != "html":
        raise ValueError(
            f"task backend is {task.get('backend')!r}, expected 'html'. "
            f"Use record_render(...) for the figma backend."
        )

    kind = task["kind"]
    # Validate screens count vs kind
    expected_screens = 3 if kind.startswith("flow-") else 1
    if len(screens) != expected_screens:
        raise ValueError(
            f"kind {kind!r} expects {expected_screens} screen(s), got {len(screens)}"
        )

    out_dir = asset_dir(work_root, slide_id, asset_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    html_doc = html_backend.frame_html(
        kind=kind,
        style=task.get("style", "brand-vti"),
        title=task.get("title", ""),
        subtitle=task.get("subtitle"),
        captions=task.get("captions"),
        screens=screens,
    )
    html_path = out_dir / "source.html"
    html_path.write_text(html_doc, encoding="utf-8")

    png_path = out_dir / "render.png"
    natural_w, natural_h = html_backend.render_to_png(
        html=html_doc,
        out_path=png_path,
        kind=kind,
        scale=scale,
        viewport=viewport,
        full_page=full_page,
    )

    spec: dict[str, Any] = {
        "kind":         kind,
        "html_brief":   task.get("html_brief"),
        "frame_label":  task.get("frame_label"),
        "style":        task.get("style"),
        "title":        task.get("title"),
        "subtitle":     task.get("subtitle"),
        "captions":     task.get("captions") or [],
        "png_path":     str(png_path).replace("\\", "/"),
        "html_path":    str(html_path).replace("\\", "/"),
        "svg_path":     None,
        "figma_url":    None,
        "figma_file_key": None,
        "figma_node_id": None,
        "natural_w":    int(natural_w),
        "natural_h":    int(natural_h),
        "backend":      "html",
        "scale":        scale,
        "rendered_at":  datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    (out_dir / "meta.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    _append_index_html(work_root, slide_id, asset_id, spec)
    return spec


def _append_index_html(work_root: str | Path, slide_id: str, asset_id: str,
                       spec: dict[str, Any]) -> None:
    """Append one line per HTML render to ``work/mockups/INDEX.md``."""
    index = Path(work_root) / "mockups" / "INDEX.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    if not index.exists():
        index.write_text(
            "# VTI mockups index\n\n"
            "One line per rendered mockup. HTML renders include a link "
            "to the editable source. Re-running the driver overwrites "
            "both PNG and HTML, so commit changes before re-running.\n\n",
            encoding="utf-8",
        )
    rel_dir = f"{_safe(slide_id)}_{_safe(asset_id)}"
    entry = (
        f"- `{rel_dir}` ({spec['kind']} · html · "
        f"{spec['natural_w']}×{spec['natural_h']}) — "
        f"**{spec.get('title') or 'untitled'}** — "
        f"[png](mockups/{rel_dir}/render.png) · "
        f"[source](mockups/{rel_dir}/source.html)\n"
    )
    with index.open("a", encoding="utf-8") as f:
        f.write(entry)


def load_meta(work_root: str | Path, slide_id: str, asset_id: str) -> dict[str, Any]:
    """Read back a previously written ``meta.json``.

    Useful for resuming a Phase 3 driver after a session restart — the
    spec dict is identical to what ``record_render`` originally
    returned.
    """
    p = asset_dir(work_root, slide_id, asset_id) / "meta.json"
    if not p.exists():
        raise FileNotFoundError(f"no mockup meta at {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def to_resolved_image(spec: dict[str, Any]) -> dict[str, Any]:
    """Adapt a mockup_spec to the legacy ``resolved_image`` shape.

    Until creator Phase 4 reads ``mockup_spec`` natively, the per-deck
    driver can pass the mockup through the existing ``lift`` branch by
    constructing a fake ``resolved_image`` dict. Use::

        content_plan["image_decision"] = {"strategy": "lift", "source_hint": ""}
        content_plan["resolved_image"] = mockup_executor.to_resolved_image(spec)

    See SKILL.md → "Phase 3 integration recipe" for the full pattern.
    """
    return {
        "path":      spec["png_path"],
        "natural_w": spec["natural_w"],
        "natural_h": spec["natural_h"],
        "kind":      "content",
        "score":     1.0,
    }


__all__ = [
    "VERSION",
    "asset_dir",
    "record_render",
    "record_html_render",
    "load_meta",
    "to_resolved_image",
]
