#!/usr/bin/env python3
"""Re-author + re-render all 7 deck diagrams against diagram-builder v0.5.0.

Uses the **native-SVG backend** (default in v0.5.0) so the rendered SVG
sizes are predictable and Phase 4's layout-designer can pre-size host
cells correctly. No mermaid-cli step required.

Outputs:
    work/diagrams/<slide>.svg
    work/diagrams/_render_manifest.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO / ".claude" / "skills" / "vti-slide-diagram-builder"))

import diagram_builder as db  # noqa: E402

WORK   = REPO / "work"
DIAGS  = WORK / "diagrams"
DIAGS.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 7 diagrams — re-authored against v0.4.0 contract
# (action labels only; metrics → captions)
# ---------------------------------------------------------------------------
def build_specs() -> list[dict]:
    specs: list[dict] = []

    specs.append({
        "slide_id":  "s06-four-pipelines",
        "primitive": "layered_stack",
        "kwargs": dict(
            layers=[
                {"label": "MAIL SUMMARY"},
                {"label": "CHAT CRAWL"},
                {"label": "MEETING PREP"},
                {"label": "WEEKLY SUMMARY"},
            ],
            kpi_band="Chat → Meeting · Meeting → Weekly · Memory threads them all",
            captions=[
                "every 2h · triage inbox",
                "daily 08:00 · summarize spaces",
                "daily 23:30 · brief schema",
                "Mon 03:00 · 5-agent cluster",
            ],
            title="Four pipelines, one cumulative context",
        ),
    })

    specs.append({
        "slide_id":  "s07-mail",
        "primitive": "fanout_pipeline",
        "kwargs": dict(
            input_label="INBOX TRIGGER",
            models=[
                {"name": "TRIAGE",     "desc": "new threads"},
                {"name": "DONE-CHECK", "desc": "pending actions"},
                {"name": "UNSNOOZE",   "desc": "skipped now active"},
            ],
            fusion_label="LLM REASONING",
            outputs=[
                {"label": "STATE"},
                {"label": "DIGEST"},
                {"label": "AUTO-CLASSIFIER QUEUE"},
            ],
            captions=[
                "pending · skipped · processed",
                "Discord · customers + internal + auto",
                "HITL suggestion queue",
            ],
            title="Mail Summary — every 2h triage with 3-context reasoning",
            subtitle="paginate + diff vs prior state",
        ),
    })

    specs.append({
        "slide_id":  "s08-chat",
        "primitive": "flow_diagram",
        "kwargs": dict(
            steps=[
                {"title": "DISCOVER"},
                {"title": "CLASSIFY"},
                {"title": "BATCH-STAMP"},
                {"title": "CRAWL ACTIVE"},
                {"title": "SUMMARIZE"},
                {"title": "MERGE + POST"},
            ],
            orientation="horizontal",
            captions=[
                "all spaces · lastActiveTime",
                "client-side",
                "180+ inactive · 1 write",
                "~20 active · paginate",
                "per-space daily VI",
                "Drive · Discord recap",
            ],
            title="Chat Crawl — 200+ spaces fit into ~15 API calls",
            subtitle="Classify-before-fetch using metadata already returned by list-spaces",
        ),
    })

    specs.append({
        "slide_id":  "s09-meeting",
        "primitive": "layered_stack",
        "kwargs": dict(
            layers=[
                {"label": "MEMORY"},
                {"label": "RECAP DOC"},
                {"label": "PREP DOC"},
                {"label": "ACTION TRACKER"},
            ],
            kpi_band="ONE brief artifact — single source of truth · consistency by schema",
            captions=[
                "replace section · persona drift",
                "today · 9-page Word",
                "tomorrow · per-PIC research",
                "upsert · preserve notes · Excel",
            ],
            title="Meeting Prep — daily 23:30 · single brief → four writers",
        ),
    })

    specs.append({
        "slide_id":  "s10-weekly",
        "primitive": "fanout_pipeline",
        "kwargs": dict(
            input_label="WEEK WINDOW",
            models=[
                {"name": "AGENT 1", "desc": "cluster A"},
                {"name": "AGENT 2", "desc": "cluster B"},
                {"name": "AGENT 3", "desc": "cluster C"},
                {"name": "AGENT 4", "desc": "cluster D"},
                {"name": "AGENT 5", "desc": "cluster E"},
            ],
            fusion_label="MERGE + CATEGORISE",
            outputs=[
                {"label": "WEEKLY DOC"},
                {"label": "MEMORY SNAPSHOT"},
                {"label": "DISCORD POSTS"},
            ],
            captions=[
                "Word · 6 sub-sections",
                "memory + brief snapshot",
                "rate-limited ~33 posts",
            ],
            title="Weekly Summary — cluster planner partitions, then 5 agents run in parallel",
            subtitle="Cluster is decided per-week by an LLM planner — no hard-coded customer routing",
        ),
    })

    specs.append({
        "slide_id":  "s11-cluster",
        "primitive": "hybrid_swimlane",
        "kwargs": dict(
            tiers=[
                {"label": "FRESH-SIGNAL INGESTION",
                 "stages": [
                     {"title": "MAIL SUMMARY",  "sub": "triage"},
                     {"title": "CHAT CRAWL",    "sub": "summarize"},
                 ]},
                {"label": "DEEP REASONING",
                 "stages": [
                     {"title": "MEETING PREP",   "sub": "four writers"},
                     {"title": "WEEKLY SUMMARY", "sub": "cluster planner"},
                 ]},
            ],
            fleet_box={"label": "SHARED RESOURCES",
                       "sub":   "OAuth · Drive · Memory · Action Tracker · Discord"},
            header="One executive · two cadence layers · shared state on Google Drive",
            footer=("Data feeds: Chat summaries → Meeting Prep · "
                    "Meeting recaps → Weekly Summary · Memory bidirectional"),
            title="How the four pipelines wire together",
            captions=[
                "every 2h · daily 08:00",
                "daily 23:30 · Mon 03:00",
            ],
        ),
    })

    specs.append({
        "slide_id":  "s12-day-in-life",
        "primitive": "layered_stack",
        "kwargs": dict(
            layers=[
                {"label": "MORNING"},
                {"label": "WORK HOURS"},
                {"label": "EVENING"},
                {"label": "NEXT MONDAY"},
            ],
            kpi_band="0 forgotten action items · weekly drift captured by Monday",
            captions=[
                "07:00 Mail · 08:02 Chat · 09:00 Mail #2",
                "11:00 NxGen · 15:00 EP · 13/15/17 Mail",
                "22:00 user edits · 23:30 Meeting Prep",
                "03:00 Weekly · ~33 Discord posts",
            ],
            title="A Thursday in the life — what the executive actually sees",
        ),
    })

    return specs


_VIEWBOX_RE = re.compile(r'viewBox="([\d.\-eE+ ]+)"')


def _read_viewbox(svg_path: Path) -> tuple[int, int]:
    """Return (natural_w, natural_h) from the SVG viewBox."""
    text = svg_path.read_text(encoding="utf-8", errors="ignore")
    m = _VIEWBOX_RE.search(text)
    if not m:
        raise RuntimeError(f"no viewBox in {svg_path}")
    parts = m.group(1).split()
    if len(parts) != 4:
        raise RuntimeError(f"unexpected viewBox shape in {svg_path}: {parts!r}")
    _x, _y, w, h = parts
    return int(round(float(w))), int(round(float(h)))


def main() -> None:
    specs = build_specs()
    manifest: dict[str, dict] = {}

    for spec in specs:
        slide_id  = spec["slide_id"]
        primitive = spec["primitive"]
        kwargs    = spec["kwargs"]

        make_fn = getattr(db, f"make_{primitive}")
        # v0.5.0 default backend is "svg" — result carries svg + natural_w/_h
        result = make_fn(**kwargs)
        if result.get("backend") != "svg":
            raise RuntimeError(
                f"{slide_id}: expected svg backend, got {result.get('backend')!r}"
            )

        svg_path = DIAGS / f"{slide_id}.svg"
        svg_path.write_text(result["svg"], encoding="utf-8")

        # Sanity-check viewBox matches the result claim.
        nat_w_read, nat_h_read = _read_viewbox(svg_path)
        nat_w, nat_h = result["natural_w"], result["natural_h"]
        if (nat_w_read, nat_h_read) != (nat_w, nat_h):
            print(f"  WARN {slide_id}: viewBox {nat_w_read}x{nat_h_read} != "
                  f"reported {nat_w}x{nat_h}", flush=True)

        manifest[slide_id] = {
            "status":     "ok",
            "svg_path":   f"work/diagrams/{slide_id}.svg",
            "svg_bytes":  svg_path.stat().st_size,
            "natural_w":  nat_w,
            "natural_h":  nat_h,
            "aspect":     f"{nat_w / nat_h:.2f}",
            "primitive":  primitive,
            "backend":    "svg",
            "captions":   result.get("captions") or [],
        }
        print(f"  rendered {slide_id}.svg  {nat_w}x{nat_h}  "
              f"aspect={nat_w / nat_h:.2f}", flush=True)

    (DIAGS / "_render_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Wrote {len(manifest)} diagrams to {DIAGS}/")
    for k, v in manifest.items():
        print(f"  {k}  {v['natural_w']}x{v['natural_h']}  aspect={v['aspect']}  "
              f"captions={len(v['captions'])}")


if __name__ == "__main__":
    main()
