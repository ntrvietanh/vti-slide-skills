"""
Sprint 1 demo — render a single slide using all starter components in
an asymmetric 12-col grid that the v2 intent system could not produce:

   Row 1 (1fr):     stat-hero col 1-5  +  narrative-paragraph col 6-12
   Row 2 (auto):    practice-card 1-4  +  practice-card 5-8  +  practice-card 9-12

The slide title ("Three practices, scaled across APAC") rides on the
chrome breadcrumb as `ABOUT VTI | THREE PRACTICES, SCALED ACROSS APAC`
via slide_meta.section_name + slide_meta.slide_title — content rows are
reserved for real content blocks, not titles.

That mixes stat + narrative + 3 cards in ONE slide — no v2 recipe could.
"""
import sys
import pathlib

# Wire up v3
V3_ROOT = pathlib.Path("/home/claude/skills/vti-slide-page-builder")
sys.path.insert(0, str(V3_ROOT))

from composer_grid import compose_slide_grid, catalog  # noqa: E402

print(">>> v3 catalog:", catalog())

# --------------------------------------------------------------------------
# Slide grid descriptor — the new contract
# --------------------------------------------------------------------------
SLIDE_INPUT = {
    "slide_meta": {
        "page_number":    1,
        "page_total":     1,
        "doc_title":      "VTI Skill v3 — Sprint 1 demo",
        "copyright_year": 2026,
        "section_name":   "About VTI",
        "slide_title":    "Three practices, scaled across APAC",
    },
    "rows": [
        # Row 1 — stat-hero (5 cols) + narrative-paragraph (7 cols), asymmetric
        {
            "height": "1fr",
            "cells": [
                {
                    "col_start": 1, "col_span": 5,
                    "component": "stat-hero",
                    "props": {
                        "value":      "1,200+",
                        "label":      "Engineers",
                        "decoration": "rings",
                    },
                },
                {
                    "col_start": 6, "col_span": 7,
                    "component": "narrative-paragraph",
                    "props": {
                        "paragraphs": [
                            "VTI organizes capability around **three parallel "
                            "practice areas**, each with senior leadership and "
                            "dedicated partner alliances tuned to that domain.",
                            "Our 1,200+ engineers across Vietnam, Japan, Korea "
                            "and Singapore deliver from regional hubs that sit "
                            "physically inside our customers' headquarters.",
                        ],
                        "align": "left",
                    },
                },
            ],
        },
        # Row 2 — three practice-cards in equal 4-col columns
        {
            "height": "auto",
            "cells": [
                {
                    "col_start": 1, "col_span": 4,
                    "component": "practice-card",
                    "props": {
                        "number":     "01",
                        "icon":       "brain",
                        "title":      "AI & Data",
                        "body":       "Data platforms, ML systems, and "
                                      "generative-AI products end-to-end.",
                        "color_tone": "deep",
                    },
                },
                {
                    "col_start": 5, "col_span": 4,
                    "component": "practice-card",
                    "props": {
                        "number":     "02",
                        "icon":       "cloud",
                        "title":      "Cloud Engineering",
                        "body":       "Multi-cloud migration, platform "
                                      "engineering and 24×7 SRE managed "
                                      "services.",
                        "color_tone": "medium",
                    },
                },
                {
                    "col_start": 9, "col_span": 4,
                    "component": "practice-card",
                    "props": {
                        "number":     "03",
                        "icon":       "code",
                        "title":      "Application Dev",
                        "body":       "Custom web, mobile, and enterprise "
                                      "software with long-term maintenance.",
                        "color_tone": "sky",
                    },
                },
            ],
        },
    ],
}

# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
out = compose_slide_grid(SLIDE_INPUT)
print(">>> metadata:", out["metadata"])
print(">>> slide_html size:", len(out["slide_html"]), "chars")
print(">>> slide_css size:",  len(out["slide_css"]),  "chars")

# Wrap in deck shell
DECK_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>VTI Skill v3 — Sprint 1 demo</title>
<style>
{css}
/* Demo viewer overrides — keep slide centered with breathing room */
html, body {{
  margin: 0; padding: 0;
  background: #2C2C2A;
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh;
}}
body {{ padding: 40px; }}
</style>
</head>
<body>
{slide}
</body>
</html>
"""
deck_html = DECK_SHELL.format(css=out["slide_css"], slide=out["slide_html"])

OUT_DIR = pathlib.Path("/home/claude/v3-out")
OUT_DIR.mkdir(parents=True, exist_ok=True)
deck_path = OUT_DIR / "sprint1-demo.html"
deck_path.write_text(deck_html, encoding="utf-8")
print(f">>> wrote: {deck_path}")
print(f">>> size:  {deck_path.stat().st_size // 1024} KB")
