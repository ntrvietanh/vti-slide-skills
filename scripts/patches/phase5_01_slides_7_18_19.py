"""Restore slide 7 / 18 / 19 customizations to work/phase_5.json.

Idempotent — safe to re-run after every `build_phase_5.py` regen.

- Slide 7 "Four design principles": narrative row[0] + 4
  `practice-card-leveled` cards in row[1].
- Slide 18 "Scale, operations": append bottom strip
  (kpi-row col_span 8 + callout col_span 4) — sentinel
  `kind_hint == 'kpi_strip_with_callout'`.
- Slide 19 "Three engineering patterns": append bottom strip
  (quote-block col_span 7 + tags col_span 5) — sentinel
  `kind_hint == 'quote_plus_tags'`.
"""
from __future__ import annotations

import json
from pathlib import Path

WORK = Path("work")
target = WORK / "phase_5.json"
ds = json.loads(target.read_text())


def find_slide(title_substr: str) -> dict:
    """Return descriptor whose slide_title contains substring (ci)."""
    for d in ds:
        meta = d.get("slide_meta") or {}
        title = meta.get("slide_title") or ""
        if title_substr.lower() in title.lower():
            return d
    raise KeyError(f"slide not found: {title_substr!r}")


def row_has_kind(slide: dict, kind: str) -> bool:
    """True if any row of the slide has the given kind_hint."""
    return any((r.get("kind_hint") == kind) for r in (slide.get("rows") or []))


# ---------------------------------------------------------------------------
# Slide 7 — Four design principles
# Row 0: narrative replaced; Row 1: 4 practice-card-leveled
# ---------------------------------------------------------------------------
LEVELED_CARDS = [
    {
        "title": "Python + LLM split",
        "icon":  "split",
        "core":  "Python lo phần xác định; LLM lo phần phán đoán.",
        "color_tone": "deep",
        "levels": [
            {"badge": "L1",
             "body":  "**Boundary.** Python owns crawl, parse, dedup, format. "
                      "LLM never calls APIs directly — every source is pre-fetched."},
            {"badge": "L2",
             "body":  "**Handoff.** Python pre-processes context → LLM reasons on "
                      "that context → Python applies the decision."},
            {"badge": "L3",
             "body":  "**Discipline.** Deterministic side is idempotent + "
                      "log-debuggable; reasoning side is swappable without rewriting "
                      "the pipeline."},
        ],
    },
    {
        "title": "Scheduled cadence",
        "icon":  "clock",
        "core":  "Hệ thống đến với người dùng theo lịch, không cần mở app.",
        "color_tone": "deep",
        "levels": [
            {"badge": "L1",
             "body":  "**Push, not pull.** Output lands in Discord and Drive on a "
                      "fixed clock — there is nothing to open."},
            {"badge": "L2",
             "body":  "**Stable cost.** Token spend tracks the schedule, not how "
                      "active the user is on a given day."},
            {"badge": "L3",
             "body":  "**Cumulative chain.** Chat 08:00 → Meeting 23:30 → Weekly "
                      "Mon 03:00 — each pipeline feeds the next."},
        ],
    },
    {
        "title": "Drive-as-database",
        "icon":  "database",
        "core":  "Drive là system of record — không có DB, không tốn infra.",
        "color_tone": "deep",
        "levels": [
            {"badge": "L1",
             "body":  "**Single store.** Catalog, persona memory, action tracker, "
                      "daily recap, weekly archive — all on Drive."},
            {"badge": "L2",
             "body":  "**Human-editable.** Open Drive directly; edit the Notes "
                      "column in Excel — no API required."},
            {"badge": "L3",
             "body":  "**Atomic writes.** The tmp + rename pattern compensates for "
                      "Drive having no transactional guarantee."},
        ],
    },
    {
        "title": "Markdown memory",
        "icon":  "file-text",
        "core":  "Markdown là handoff layer giữa Python và LLM.",
        "color_tone": "deep",
        "levels": [
            {"badge": "L1",
             "body":  "**Format.** Python writes .md context files; the LLM reads "
                      "them as its working memory."},
            {"badge": "L2",
             "body":  "**Decision back.** The LLM writes JSON decisions into the "
                      "same folder; Python applies them."},
            {"badge": "L3",
             "body":  "**Tunable.** Tune prompts by editing files; the "
                      "\"hard-rules\" header at the top encodes every past failure."},
        ],
    },
]

slide7 = find_slide("Four design principles")

# Idempotency sentinel: row[1] cells are all practice-card-leveled.
existing_kinds = [c.get("component") for c in slide7["rows"][1].get("cells", [])]
slide7_changed = existing_kinds != ["practice-card-leveled"] * 4

if slide7_changed:
    slide7["rows"][0]["cells"][0]["props"] = {
        "paragraphs": [
            "Each principle is a simple rule on the surface — but it earns its "
            "keep through a three-step **level upgrade**: from boundary, to handoff, "
            "to discipline. Read down a column to see the principle harden."
        ],
    }
    new_card_cells = []
    for i, card in enumerate(LEVELED_CARDS):
        new_card_cells.append({
            "col_start":         1 + i * 3,
            "col_span":          3,
            "component":         "practice-card-leveled",
            "props":             card,
            "row_span":          1,
            "source_block_kind": "practice_card_leveled",
        })
    slide7["rows"][1]["cells"] = new_card_cells
    slide7["rows"][1]["height"]    = "1fr"
    slide7["rows"][1]["kind_hint"] = "practice_card_leveled_row"
    print(f"  slide 7: narrative + {len(new_card_cells)} practice-card-leveled cards")
else:
    print("  slide 7: already patched, skip")


# ---------------------------------------------------------------------------
# Slide 18 — Scale, operations: append bottom kpi-row + callout strip
# ---------------------------------------------------------------------------
slide18 = find_slide("Scale, operations")
if not row_has_kind(slide18, "kpi_strip_with_callout"):
    slide18.setdefault("rows", []).append({
        "cells": [
            {
                "col_start": 1,
                "col_span":  8,
                "component": "kpi-row",
                "props": {
                    "items": [
                        {"icon": "clock",      "value": "5×",    "label": "MAIL DIGEST · per workday"},
                        {"icon": "server-off", "value": "0",     "label": "NO BROKER, NO DB"},
                        {"icon": "rocket",     "value": "~days", "label": "SETUP / new pipeline"},
                    ],
                },
                "row_span": 1,
                "source_block_kind": "kpi_row",
            },
            {
                "col_start": 9,
                "col_span":  4,
                "component": "callout",
                "props": {
                    "tone":  "deep",
                    "title": "BOTTOM LINE",
                    "text":  "Token spend tracks cadence, not user activity — so "
                             "monthly cost is forecast-able from day one.",
                },
                "row_span": 1,
                "source_block_kind": "callout",
            },
        ],
        "height":    "auto",
        "kind_hint": "kpi_strip_with_callout",
    })
    print("  slide 18: appended kpi-row + BOTTOM LINE callout")
else:
    print("  slide 18: already patched, skip")


# ---------------------------------------------------------------------------
# Slide 19 — Three engineering patterns: append bottom quote + tags strip
# ---------------------------------------------------------------------------
slide19 = find_slide("engineering patterns")
if not row_has_kind(slide19, "quote_plus_tags"):
    slide19.setdefault("rows", []).append({
        "cells": [
            {
                "col_start": 1,
                "col_span":  7,
                "component": "quote-block",
                "props": {
                    "quote": "Same shape, swap the inbox. The patterns are the "
                             "product — not the LLM, not the prompt, not even the "
                             "data domain.",
                    "style": "card",
                },
                "row_span": 1,
                "source_block_kind": "quote_block",
            },
            {
                "col_start": 8,
                "col_span":  5,
                "component": "tags",
                "props": {
                    "items": ["Mail digests", "Chat summaries", "Ticketing queues",
                              "Doc review", "Meeting prep"],
                    "tone":  "soft",
                },
                "row_span": 1,
                "source_block_kind": "tags",
            },
        ],
        "height":    "auto",
        "kind_hint": "quote_plus_tags",
    })
    print("  slide 19: appended quote-block + tags strip")
else:
    print("  slide 19: already patched, skip")


target.write_text(
    json.dumps(ds, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
