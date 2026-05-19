"""Restore slide 5 to the original `vs-compare` component (Pull vs Push).

build_phase_5 regen produces narrative + vs-divider + narrative (3 stacked
rows) which renders top/bottom with a VS circle in the middle and ~60%
empty canvas below — the layout_designer doesn't know to keep the
two halves on a side-by-side `vs-compare` grid.

This patch replaces slide 5's rows with the single vs-compare row that
phase_5.backup.json had at 14:39 (before regen).

Idempotent: skips if row[0] is already a single `vs-compare` cell.
"""
from __future__ import annotations

import json
from pathlib import Path

WORK = Path("work")
target = WORK / "phase_5.json"
ds = json.loads(target.read_text())


def find_slide(title_substr: str) -> dict:
    for d in ds:
        meta = d.get("slide_meta") or {}
        title = meta.get("slide_title") or ""
        if title_substr.lower() in title.lower():
            return d
    raise KeyError(f"slide not found: {title_substr!r}")


slide5 = find_slide("AI chatbot")
row0 = slide5.get("rows", [{}])[0]
cells = row0.get("cells") or []
already = (
    len(slide5.get("rows", [])) == 1
    and len(cells) == 1
    and cells[0].get("component") == "vs-compare"
)

if not already:
    slide5["rows"] = [{
        "height":    "1fr",
        "kind_hint": "vs_compare",
        "cells": [{
            "col_start": 1,
            "col_span":  12,
            "component": "vs-compare",
            "props": {
                "left": {
                    "label": "PULL · ON-DEMAND CHATBOT",
                    "narrative": (
                        "Asking an AI chatbot only works if you remember to ask. "
                        "Opening the app, typing the query, reading the answer — "
                        "every step costs attention. The pattern of \"I will open "
                        "the chatbot every evening\" fades within a week. A system "
                        "that depends on user discipline does not scale."
                    ),
                    "items": [
                        "Needs you to remember to ask, every time",
                        "Each query costs attention — open, type, read",
                        "\"I'll check every evening\" fades within a week",
                        "Scales with user discipline, not system effort",
                    ],
                },
                "right": {
                    "label": "PUSH · SCHEDULED PIPELINE",
                    "narrative": (
                        "Our system flips the contract. It runs on its own clock "
                        "and pushes results into the channels you already watch. "
                        "Mail Summary, Chat Crawl, Meeting Prep, and the Weekly "
                        "recap each fire on their own schedule and are waiting for "
                        "you when you next look. You read when convenient, not "
                        "when prompted."
                    ),
                    "items": [
                        "Runs on its own schedule — no trigger needed",
                        "Delivers into channels you already watch",
                        "Summarizes mail and chat conversations regularly",
                        "Wraps each day and week without being asked",
                    ],
                },
            },
            "source_block_kind": "vs_compare",
            "row_span": 1,
        }],
    }]
    print("  slide 5: restored vs-compare (pull · push)")
else:
    print("  slide 5: already patched, skip")


target.write_text(
    json.dumps(ds, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
