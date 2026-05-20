"""Build a baseline `pptx-notes.json` from the creator's phase outputs.

This is the *starting point*, not the final narration. Claude or the
user is expected to revise the file before the final PPTX build.

Strategy:
  * `phase_2.json` gives per-slide `topic`, `section`, `kind`, `summary`.
  * `phase_3.json` is keyed by `slide_id` and carries the actual block
    content (narrative paragraphs, hero stats, card bodies, …).
  * We stitch those into a Vietnamese script + a kind-driven hint
    cheat-sheet.

Output shape — a *list* parallel to deck slide order (1-based):

    [
      {"slide_index": 1, "slide_title": "...", "script": "...", "hints": "..."},
      ...
    ]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Hints per block kind. The output of phase 3 uses these `kind` strings
# (see vti-slide-creator/content_drafter.py). When a slide combines
# multiple kinds, we concatenate hints in block order, dedup-preserving.
KIND_HINTS = {
    "hero_stat": "Đọc chậm con số chính, dừng 1 nhịp để khán giả ngấm.",
    "narrative": "Kể như đang nói chuyện, không đọc theo gạch đầu dòng.",
    "features_3": "Đi tuần tự từng card trái → phải, mỗi card 15–20s.",
    "features_4": "Bốn card đi theo cặp (2 trên + 2 dưới) hoặc đi quanh kim đồng hồ.",
    "checklist": "Xác nhận trạng thái từng dòng, đánh dấu dòng đang nói.",
    "kpi_grid": "Nhấn mạnh con số nào là điểm chính, giải thích đơn vị nếu cần.",
    "process_steps": "Đi theo mũi tên/luồng, nối ý 'sau bước này thì…'.",
    "comparison_table": "So sánh theo cột — đặt câu hỏi 'cái này tốt hơn vì…'.",
    "callout": "Nhấn câu callout — tốc độ chậm, ánh mắt vào khán giả.",
    "quote": "Đọc trích dẫn với tone khác (chậm, thấp hơn), nghỉ trước-sau.",
    "diagram": "Trỏ vào từng node theo thứ tự logic, đừng đọc nhãn — giải thích quan hệ.",
    "image": "Mô tả 1 câu image cho ngữ cảnh, không dừng quá lâu.",
    "timeline": "Đi từ trái sang phải, gắn từng mốc với thông điệp.",
    "stat_grid": "Đi nhanh, nhấn vào con số bất ngờ nhất.",
    "definition": "Đọc rõ thuật ngữ + 1 ví dụ ngắn.",
}

# Kind → narration weight. Higher = include earlier in the script.
KIND_WEIGHT = {
    "hero_stat": 100,
    "callout": 95,
    "narrative": 80,
    "features_3": 60,
    "features_4": 60,
    "kpi_grid": 55,
    "stat_grid": 55,
    "checklist": 50,
    "process_steps": 45,
    "timeline": 45,
    "comparison_table": 40,
    "diagram": 40,
    "quote": 35,
    "image": 20,
    "definition": 70,
}


def _str(x: Any) -> str:
    return (x or "").strip() if isinstance(x, str) else ""


def _block_to_prose(block: dict) -> str:
    """Render one block as 1–3 spoken sentences."""
    kind = block.get("kind", "")
    c = block.get("content") or {}

    if kind == "hero_stat":
        val = _str(c.get("value"))
        lbl = _str(c.get("label"))
        if val and lbl:
            return f"Con số chính ở đây là {val} — {lbl}."
        return _str(val or lbl)

    if kind == "narrative":
        paras = c.get("paragraphs") or []
        return " ".join(_str(p) for p in paras if _str(p))

    if kind in ("features_3", "features_4"):
        cards = c.get("cards") or []
        bits = []
        for card in cards:
            t = _str(card.get("title"))
            b = _str(card.get("body"))
            if t and b:
                # Compress card body to 1 line for spoken pacing.
                b_one = b.split("\n", 1)[0].rstrip(".") + "."
                bits.append(f"{t}: {b_one}")
            elif t:
                bits.append(t)
        return " ".join(bits)

    if kind == "callout":
        return _str(c.get("text") or c.get("body") or c.get("message"))

    if kind == "quote":
        q = _str(c.get("quote") or c.get("text"))
        who = _str(c.get("attribution") or c.get("author"))
        return f'"{q}" — {who}.' if who else q

    if kind == "checklist":
        items = c.get("items") or []
        labels = [_str(it.get("label") if isinstance(it, dict) else it) for it in items]
        labels = [l for l in labels if l]
        if labels:
            return "Các điểm chính: " + "; ".join(labels) + "."
        return ""

    if kind in ("kpi_grid", "stat_grid"):
        cells = c.get("cells") or c.get("stats") or []
        bits = []
        for cell in cells:
            v = _str(cell.get("value"))
            l = _str(cell.get("label") or cell.get("name"))
            if v and l:
                bits.append(f"{v} {l}")
        return ", ".join(bits) + "." if bits else ""

    if kind == "process_steps":
        steps = c.get("steps") or []
        titles = [_str(s.get("title") if isinstance(s, dict) else s) for s in steps]
        titles = [t for t in titles if t]
        if titles:
            return "Luồng đi qua các bước: " + " → ".join(titles) + "."
        return ""

    if kind == "comparison_table":
        # Just announce that it's a comparison; details left to the
        # human to narrate.
        rows = c.get("rows") or []
        return f"Bảng so sánh có {len(rows)} hàng — diễn giải sự khác biệt theo cột." if rows else ""

    if kind == "timeline":
        items = c.get("items") or c.get("events") or []
        return f"Timeline có {len(items)} mốc — đi từ trái sang phải." if items else ""

    if kind == "diagram":
        title = _str(c.get("title") or c.get("caption"))
        return f"Diagram: {title}." if title else "Giải thích sơ đồ này theo luồng quan hệ."

    if kind == "definition":
        term = _str(c.get("term"))
        body = _str(c.get("definition") or c.get("body"))
        if term and body:
            return f"{term} — {body}"
        return body or term

    # Generic fallback: try to pull `title`/`body`/`text`.
    for key in ("title", "heading", "body", "text"):
        if _str(c.get(key)):
            return _str(c.get(key))

    return ""


def _hints_for_kinds(kinds: list[str]) -> str:
    """One hint per distinct kind, in deck-blocks order."""
    seen: list[str] = []
    for k in kinds:
        if k in KIND_HINTS and k not in seen:
            seen.append(k)
    lines = [f"- {KIND_HINTS[k]}" for k in seen]
    return "\n".join(lines)


def _phase2_special_script(slide_meta: dict) -> tuple[str, str]:
    """Script + hints for cover/toc/contact/closing/section slides."""
    kind = slide_meta.get("kind", "")
    topic = _str(slide_meta.get("topic"))
    summary = _str(slide_meta.get("summary"))
    section = _str(slide_meta.get("section"))

    if kind == "cover":
        return (
            f"Chào mừng đến với phần trình bày: {topic}. {summary}".strip(),
            "- Tự giới thiệu tên, vai trò trong 1 câu.\n"
            "- Đặt expectation: 'Trong N phút tới chúng ta sẽ đi qua…'\n"
            "- Tốc độ vừa phải, mắt nhìn khán giả thay vì màn hình.",
        )

    if kind == "toc":
        return (
            "Đây là lộ trình chúng ta sẽ đi qua hôm nay. " + summary,
            "- Đọc nhanh các section, dừng 1 nhịp ở section quan trọng nhất.\n"
            "- Nói rõ section nào là 'điểm đến' / kết luận chính.",
        )

    if kind == "contact":
        return (
            "Đây là thông tin liên hệ — sau buổi này ai cần follow-up xin ghi lại.",
            "- Dừng đủ lâu để khán giả ghi/quét QR.\n"
            "- Gợi ý cách follow-up phù hợp (email vs Zalo vs LinkedIn).",
        )

    if kind == "closing":
        return (
            "Cảm ơn mọi người đã theo dõi. " + summary,
            "- Tóm 3 ý chốt trước khi 'thank you'.\n"
            "- Mời câu hỏi và để 1 nhịp im lặng — không vội fill.",
        )

    if kind == "section":
        return (
            f"Chuyển sang phần: {section or topic}. {summary}".strip(),
            "- Dừng 1 nhịp dài hơn — đây là đánh dấu chuyển section.\n"
            "- Nhắc lại tại sao section này quan trọng với khán giả.",
        )

    return ("", "")


def _stitch_script(slide_meta: dict, blocks: list[dict]) -> str:
    """Compose a spoken script from blocks ordered by narration weight."""
    if not blocks:
        return _str(slide_meta.get("summary"))

    ordered = sorted(
        enumerate(blocks),
        key=lambda kv: KIND_WEIGHT.get(kv[1].get("kind", ""), 0),
        reverse=True,
    )

    paragraphs: list[str] = []
    summary = _str(slide_meta.get("summary"))
    if summary:
        paragraphs.append(summary)

    for _, block in ordered:
        line = _block_to_prose(block).strip()
        if line:
            paragraphs.append(line)

    # Cap length — speaker notes shouldn't be a wall of text.
    text = "\n\n".join(paragraphs)
    if len(text) > 1800:
        text = text[:1800].rsplit(". ", 1)[0] + "."
    return text


def derive_notes_from_phases(
    phase_2_path: str | Path | None,
    phase_3_path: str | Path | None,
    n_slides: int | None = None,
) -> list[dict]:
    """Return list of notes records in deck order (1-based slide_index).

    Both phase paths are optional — the more inputs you give, the
    richer the baseline. With nothing, returns empty notes for the
    requested slide count.
    """
    phase_2: dict = {}
    if phase_2_path and Path(phase_2_path).exists():
        phase_2 = json.loads(Path(phase_2_path).read_text(encoding="utf-8"))

    phase_3: dict = {}
    if phase_3_path and Path(phase_3_path).exists():
        phase_3 = json.loads(Path(phase_3_path).read_text(encoding="utf-8"))

    slides = phase_2.get("slides") or []
    if not slides and n_slides:
        # Phase 2 missing → emit blanks parallel to image count.
        return [
            {
                "slide_index": i,
                "slide_title": f"Slide {i}",
                "script": "",
                "hints": "",
            }
            for i in range(1, n_slides + 1)
        ]

    out: list[dict] = []
    for i, slide_meta in enumerate(slides, start=1):
        slide_id = slide_meta.get("slide_id", "")
        kind = slide_meta.get("kind", "")
        title = _str(slide_meta.get("topic")) or _str(slide_meta.get("section")) or f"Slide {i}"

        # Special slides: framing template-driven scripts.
        if kind in ("cover", "toc", "contact", "closing", "section"):
            script, hints = _phase2_special_script(slide_meta)
            out.append(
                {
                    "slide_index": i,
                    "slide_title": title,
                    "script": script,
                    "hints": hints,
                }
            )
            continue

        # Content slides: stitch from phase_3 blocks if available.
        slide_node = phase_3.get(slide_id) or {}
        blocks = slide_node.get("blocks") or []
        script = _stitch_script(slide_meta, blocks)
        kinds = [b.get("kind", "") for b in blocks]
        hints = _hints_for_kinds(kinds) or "- Giữ nhịp đều, kết bằng câu chuyển sang slide sau."

        out.append(
            {
                "slide_index": i,
                "slide_title": title,
                "script": script,
                "hints": hints,
            }
        )

    # If image count exceeds outline slides (e.g., extra slides added
    # post-Phase-2), pad with blanks so notes list stays aligned.
    if n_slides and n_slides > len(out):
        for i in range(len(out) + 1, n_slides + 1):
            out.append(
                {
                    "slide_index": i,
                    "slide_title": f"Slide {i}",
                    "script": "",
                    "hints": "",
                }
            )

    return out
