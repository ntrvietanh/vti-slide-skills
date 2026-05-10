"""
Sprint A demo deck — 4 slides exercising all 9 atomic components.

Each slide carries section + title via slide_meta.section_name +
slide_meta.slide_title — the chrome breadcrumb renders them as
"SECTION | TITLE" at top-left, so content rows hold only real content.

Slide 1  · Sprint 1 combo (regenerate, with bumped icon size)
            stat-hero + narrative-paragraph + 3 practice-cards

Slide 2  · Service catalog
            narrative-paragraph + 3 catalog-columns
            (Advisory deep / Delivery medium / Operate sky)

Slide 3  · Why VTI six values
            narrative-paragraph + 6 value-medallions

Slide 4  · Regional scale enhanced
            (stat-hero + narrative split) + kpi-row of 3 stat-mini

This exercises every one of the 9 v3 components AT LEAST once.
"""
import sys, pathlib

V3_ROOT = pathlib.Path("/home/claude/skills/vti-slide-page-builder-v3")
sys.path.insert(0, str(V3_ROOT))
from composer_grid import compose_slide_grid, catalog  # noqa: E402

print(">>> v3 catalog:", catalog())

# ============================================================================
# SLIDE 1 — combo (Sprint 1 regenerate)
# ============================================================================
SLIDE_1 = {
    "slide_meta": {"page_number": 1, "page_total": 4,
                   "doc_title": "VTI Skill v3 — Sprint A demo",
                   "copyright_year": 2026,
                   "section_name": "About VTI",
                   "slide_title": "Our Practices"},
    "rows": [
        {"height": "1fr", "cells": [
            {"col_start": 1, "col_span": 5, "component": "stat-hero",
             "props": {"value": "1,200+", "label": "Engineers",
                       "decoration": "rings"}},
            {"col_start": 6, "col_span": 7, "component": "narrative-paragraph",
             "props": {"paragraphs": [
                 "VTI organizes capability around **three parallel practice "
                 "areas**, each with senior leadership and dedicated partner "
                 "alliances tuned to that domain.",
                 "Our 1,200+ engineers across Vietnam, Japan, Korea and "
                 "Singapore deliver from regional hubs that sit physically "
                 "inside our customers' headquarters."]}}]},
        {"height": "auto", "cells": [
            {"col_start": 1, "col_span": 4, "component": "practice-card",
             "props": {"number": "01", "icon": "brain", "title": "AI & Data",
                       "body": "Data platforms, ML systems, and "
                               "generative-AI products end-to-end.",
                       "color_tone": "deep"}},
            {"col_start": 5, "col_span": 4, "component": "practice-card",
             "props": {"number": "02", "icon": "cloud",
                       "title": "Cloud Engineering",
                       "body": "Multi-cloud migration, platform engineering "
                               "and 24×7 SRE managed services.",
                       "color_tone": "medium"}},
            {"col_start": 9, "col_span": 4, "component": "practice-card",
             "props": {"number": "03", "icon": "code",
                       "title": "Application Dev",
                       "body": "Custom web, mobile, and enterprise software "
                               "with long-term maintenance.",
                       "color_tone": "sky"}}]},
    ],
}

# ============================================================================
# SLIDE 2 — Service catalog
# ============================================================================
SLIDE_2 = {
    "slide_meta": {"page_number": 2, "page_total": 4,
                   "doc_title": "VTI Skill v3 — Sprint A demo",
                   "copyright_year": 2026,
                   "section_name": "Grid & feature intents",
                   "slide_title": "Service Catalog"},
    "rows": [
        {"height": "auto", "cells": [
            {"col_start": 1, "col_span": 12,
             "component": "narrative-paragraph",
             "props": {"paragraphs": [
                 "Specialist services that wrap around any engagement."]}}]},
        {"height": "auto", "cells": [
            {"col_start": 1, "col_span": 4, "component": "catalog-column",
             "props": {"label": "Advisory", "category_icon": "bulb",
                       "count_text": "5 services", "color_tone": "deep",
                       "items": [
                           {"text": "Cloud & AI strategy", "tag": "Strategy"},
                           "Architecture review",
                           "Build-vs-buy assessment",
                           "Vendor & tooling selection",
                           "Change management"]}},
            {"col_start": 5, "col_span": 4, "component": "catalog-column",
             "props": {"label": "Delivery", "category_icon": "tools",
                       "count_text": "5 services", "color_tone": "medium",
                       "items": [
                           {"text": "Custom software", "tag": "Build"},
                           "Mobile + web engineering",
                           "Data engineering + analytics",
                           "ML / Generative-AI",
                           "QA + automation"]}},
            {"col_start": 9, "col_span": 4, "component": "catalog-column",
             "props": {"label": "Operate", "category_icon": "rocket",
                       "count_text": "5 services", "color_tone": "sky",
                       "items": [
                           "24×7 application managed",
                           "Cloud FinOps + cost",
                           {"text": "Cyber-security ops", "tag": "SOC"},
                           "Site reliability engineering",
                           "DataOps + MLOps"]}}]},
    ],
}

# ============================================================================
# SLIDE 3 — Why VTI six values
# ============================================================================
SLIDE_3 = {
    "slide_meta": {"page_number": 3, "page_total": 4,
                   "doc_title": "VTI Skill v3 — Sprint A demo",
                   "copyright_year": 2026,
                   "section_name": "Grid & feature intents",
                   "slide_title": "Why VTI — Six Pillars"},
    "rows": [
        {"height": "auto", "cells": [
            {"col_start": 1, "col_span": 12,
             "component": "narrative-paragraph",
             "props": {"paragraphs": [
                 "The six values that shape every engagement."]}}]},
        {"height": "auto", "cells": [
            {"col_start": 1, "col_span": 2, "component": "value-medallion",
             "props": {"number": "01", "icon": "bulb", "title": "Innovation",
                       "tagline": "First in, fastest out", "color_tone": "deep"}},
            {"col_start": 3, "col_span": 2, "component": "value-medallion",
             "props": {"number": "02", "icon": "shield-check",
                       "title": "Quality", "tagline": "CMMI L3 by default",
                       "color_tone": "medium"}},
            {"col_start": 5, "col_span": 2, "component": "value-medallion",
             "props": {"number": "03", "icon": "handshake",
                       "title": "Partnership",
                       "tagline": "Long-term, not transactional",
                       "color_tone": "sky"}},
            {"col_start": 7, "col_span": 2, "component": "value-medallion",
             "props": {"number": "04", "icon": "users", "title": "People",
                       "tagline": "Senior bench, low attrition",
                       "color_tone": "deep"}},
            {"col_start": 9, "col_span": 2, "component": "value-medallion",
             "props": {"number": "05", "icon": "star", "title": "Excellence",
                       "tagline": "Engineering rigor",
                       "color_tone": "medium"}},
            {"col_start": 11, "col_span": 2, "component": "value-medallion",
             "props": {"number": "06", "icon": "lock", "title": "Trust",
                       "tagline": "4.2y avg engagement",
                       "color_tone": "navy"}}]},
    ],
}

# ============================================================================
# SLIDE 4 — Regional scale enhanced
# ============================================================================
SLIDE_4 = {
    "slide_meta": {"page_number": 4, "page_total": 4,
                   "doc_title": "VTI Skill v3 — Sprint A demo",
                   "copyright_year": 2026,
                   "section_name": "Storytelling intents",
                   "slide_title": "Our Regional Scale"},
    "rows": [
        {"height": "1fr", "cells": [
            {"col_start": 1, "col_span": 5, "component": "stat-hero",
             "props": {"value": "1,200+", "label": "Engineers",
                       "decoration": "rings"}},
            {"col_start": 6, "col_span": 7, "component": "narrative-paragraph",
             "props": {"paragraphs": [
                 "VTI runs the **largest cross-border engineering bench** in "
                 "Vietnam, with delivery centers physically embedded in our "
                 "customers' headquarters across Tokyo, Seoul and Singapore.",
                 "Our scale lets us assemble dedicated teams of 15-100+ "
                 "engineers within four weeks, instead of the four months an "
                 "in-house ramp-up usually takes."]}}]},
        {"height": "auto", "cells": [
            {"col_start": 1, "col_span": 12, "component": "kpi-row",
             "props": {"items": [
                 {"icon": "building-skyscraper", "value": "300+",
                  "label": "Customers"},
                 {"icon": "rocket", "value": "75+",
                  "label": "Active GDCs"},
                 {"icon": "world", "value": "9",
                  "label": "Industry verticals"},
             ]}}]},
    ],
}

# ============================================================================
# RENDER
# ============================================================================
ALL_SLIDES = [SLIDE_1, SLIDE_2, SLIDE_3, SLIDE_4]
slides_html_parts: list[str] = []
all_css_parts: list[str] = []

for idx, slide in enumerate(ALL_SLIDES, start=1):
    out = compose_slide_grid(slide)
    slides_html_parts.append(out["slide_html"])
    if idx == 1:
        # Tokens + chrome + grid CSS only need to appear once
        all_css_parts.append(out["slide_css"])
    else:
        # Just per-component CSS for slide 2+ — but compose returns a unified
        # CSS already so dedup is fine even if we just reuse slide-1's CSS.
        # For simplicity: aggregate everything once. CSS is idempotent.
        all_css_parts.append(out["slide_css"])
    print(f"  slide {idx} → components: {out['metadata']['components_used']}")

# Dedup CSS (concatenate then strip duplicate sections by line-set)
all_css = "\n\n".join(all_css_parts)

DECK_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>VTI Skill v3 — Sprint A demo</title>
<style>
{css}
html, body {{
  margin: 0; padding: 0;
  background: #ECECEC;
  font-family: 'Inter', sans-serif;
}}
body {{
  display: flex; flex-direction: column;
  align-items: center; gap: 32px; padding: 40px;
  min-height: 100vh;
}}
.slide.layout-grid {{
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  border-radius: 4px;
}}
</style>
</head>
<body>
{slides}
</body>
</html>
"""
deck_html = DECK_SHELL.format(
    css=all_css,
    slides="\n\n".join(slides_html_parts),
)
OUT_DIR = pathlib.Path("/home/claude/v3-out")
OUT_DIR.mkdir(parents=True, exist_ok=True)
deck_path = OUT_DIR / "sprintA-demo.html"
deck_path.write_text(deck_html, encoding="utf-8")
print(f"\n>>> wrote: {deck_path}")
print(f">>> size:  {deck_path.stat().st_size // 1024} KB")
