"""
Phase 2 (PLAN-OUTLINE) + Phase 3 (PLAN-REVIEW).

Produces and iterates on a ``DeckOutline``:

    {
        "doc_title": str,
        "section_arc": [str],        # narrative sections in order
        "slides": [{
            "slide_id":      str,    # stable ID (e.g. "s001-cover")
            "section":       str,    # which section_arc entry
            "kind":          str,    # "cover" | "section-divider"
                                     # | "content" | "closing"
                                     # | special-page name
            "topic":         str,    # 1-line topic
            "summary":       str,    # 1-2 sentence summary
            "block_kinds":   [str],  # planned content kinds (for Phase 4)
            "image_strategy_hint": str,  # initial guess for Phase 4
        }],
    }

Phase 2 builds the initial outline from a ContextDoc. Phase 3 iterates
on it with the user (add / remove / reorder slides) until approved.
The actual narrative arc design is Claude reasoning; this module
provides:
  - DeckOutline + Slide schemas + validators
  - slide-list manipulation helpers (add / remove / move / replace)
  - integrity checks (no duplicate IDs, valid kinds, etc.)
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Slide kind taxonomy
# ---------------------------------------------------------------------------
# "framing" pages are the structural slides (cover, ToC, dividers, contact,
# closing). "narrator" pages are the 8 lift-and-shift v2 specials. "content"
# is everything else — the actual storytelling slides built via Phase 4 + 5.
FRAMING_KINDS = ["cover", "toc", "section-divider", "contact", "closing"]
NARRATOR_KINDS = [
    "about-vti", "vision-mission-values", "who-we-serve",
    "awards-certifications", "strategic-partners",
    "project-management-method", "quality-assurance",
    "quality-management-process",
]
CONTENT_KIND = "content"

ALL_SLIDE_KINDS = [CONTENT_KIND] + FRAMING_KINDS + NARRATOR_KINDS


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------
def make_slide_outline_entry(
    slide_id: str,
    kind: str,
    topic: str,
    section: str = "",
    summary: str = "",
    block_kinds: list | None = None,
    image_strategy_hint: str = "",
    # v3.14 — first-class v3.4 (P6 capacity-first) fields
    layout_sketch: str = "",
    char_budget: int = 0,
    image_strategy: str = "",
    rationale: str = "",
    need_input: str = "",
) -> dict:
    """Build one slide entry in the outline.

    v3.14 fields (Principle 6 capacity-first commitments):
        layout_sketch:  1-line layout (e.g. "hero stat 1-5 + narrative 6-12 + kpi-row 1-12")
        char_budget:    total chars target across all cells (use layout_sketch_capacity())
        image_strategy: concrete description (e.g. "Lift retail/p4 (group photo)")
        rationale:      1-line WHY this layout/strategy was chosen
        need_input:     ✅ + brief note if user input/asset required, else ""
    """
    if kind not in ALL_SLIDE_KINDS:
        raise ValueError(
            f"slide kind {kind!r} not in {ALL_SLIDE_KINDS}"
        )
    if not re.match(r"^[a-z0-9_-]+$", slide_id):
        raise ValueError(
            f"slide_id {slide_id!r} must be lowercase alphanumeric "
            f"with hyphens/underscores"
        )
    if char_budget < 0:
        raise ValueError(f"char_budget must be non-negative, got {char_budget}")
    return {
        "slide_id":            slide_id,
        "section":             section,
        "kind":                kind,
        "topic":                topic,
        "summary":             summary,
        "block_kinds":         block_kinds or [],
        "image_strategy_hint": image_strategy_hint,
        # v3.14 — Phase 2 capacity commitments
        "layout_sketch":       layout_sketch,
        "char_budget":         char_budget,
        "image_strategy":      image_strategy,
        "rationale":           rationale,
        "need_input":          need_input,
    }


def make_deck_outline(doc_title: str,
                      section_arc: list[str],
                      slides: list[dict]) -> dict:
    """Wrap section_arc + slides into a DeckOutline envelope."""
    return {
        "doc_title":   doc_title,
        "section_arc": list(section_arc),
        "slides":      list(slides),
    }


# ---------------------------------------------------------------------------
# Manipulation helpers (Phase 3 — review/iteration)
# ---------------------------------------------------------------------------
def add_slide(outline: dict, entry: dict, position: int | None = None) -> dict:
    """Insert a slide entry into the outline.

    Args:
        outline: existing outline dict (not mutated)
        entry: slide entry from ``make_slide_outline_entry()``
        position: **0-indexed** insertion index (matches ``list.insert()``).
                  ``position=0`` puts the slide at slot 1 (1-indexed).
                  ``position=None`` (default) appends to the end.

    Returns:
        New outline with the entry inserted. Original is not mutated.

    Note (v3.14): The ``slide_id`` should NOT carry positional information
    (e.g. ``s11-procurement`` becomes misleading after edits). Use stable
    semantic IDs like ``slide-procurement``, ``slide-scangoo`` and let
    page numbers come from outline order. Use ``renumber_slide_ids()``
    if you want to align IDs to current positions for readability.
    """
    out = {**outline, "slides": list(outline.get("slides", []))}
    if position is None:
        out["slides"].append(entry)
    else:
        out["slides"].insert(position, entry)
    return out


def remove_slide(outline: dict, slide_id: str) -> dict:
    """Remove a slide by ID. Raises KeyError if not found."""
    new_slides = [s for s in outline.get("slides", [])
                  if s.get("slide_id") != slide_id]
    if len(new_slides) == len(outline.get("slides", [])):
        raise KeyError(f"slide_id {slide_id!r} not found in outline")
    return {**outline, "slides": new_slides}


def move_slide(outline: dict, slide_id: str, new_position: int) -> dict:
    """Move a slide to a new position."""
    slides = list(outline.get("slides", []))
    idx = next((i for i, s in enumerate(slides)
                if s.get("slide_id") == slide_id), None)
    if idx is None:
        raise KeyError(f"slide_id {slide_id!r} not found")
    entry = slides.pop(idx)
    slides.insert(new_position, entry)
    return {**outline, "slides": slides}


def replace_slide(outline: dict, slide_id: str, new_entry: dict) -> dict:
    """Replace a slide entry. The new_entry must have a slide_id."""
    if not new_entry.get("slide_id"):
        raise ValueError("replacement entry must have a slide_id")
    slides = list(outline.get("slides", []))
    found = False
    for i, s in enumerate(slides):
        if s.get("slide_id") == slide_id:
            slides[i] = new_entry
            found = True
            break
    if not found:
        raise KeyError(f"slide_id {slide_id!r} not found")
    return {**outline, "slides": slides}


# ---------------------------------------------------------------------------
# Validators + integrity checks
# ---------------------------------------------------------------------------
def validate_deck_outline(outline: Any, *, strict_section_order: bool = True
                          ) -> tuple[bool, list[str]]:
    """Returns (ok, errors). Catches:
        - missing required fields
        - duplicate slide_ids
        - slides referencing non-existent sections
        - invalid slide kinds
        - v3.14: out-of-order section grouping (if strict_section_order)
        - v3.14: cover/closing/dividers in wrong positions

    Args:
        strict_section_order: when True (default), each section_arc entry's
            slides must be contiguous (no foreign-section slide interleaved).
            Set False when intentionally allowing mixed-section slides
            (rare; usually a sign of an outline bug).
    """
    errors: list[str] = []
    if not isinstance(outline, dict):
        return False, ["DeckOutline must be a dict"]

    if not outline.get("doc_title"):
        errors.append("missing 'doc_title'")
    sections = outline.get("section_arc", [])
    if not isinstance(sections, list):
        errors.append("'section_arc' must be a list")
        sections = []

    slides = outline.get("slides", [])
    if not isinstance(slides, list):
        errors.append("'slides' must be a list")
        return len(errors) == 0, errors
    if not slides:
        errors.append("'slides' must have at least 1 entry")

    seen_ids: set[str] = set()
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            errors.append(f"slides[{i}] must be a dict")
            continue
        sid = s.get("slide_id")
        if not sid:
            errors.append(f"slides[{i}] missing 'slide_id'")
        elif sid in seen_ids:
            errors.append(f"slides[{i}] duplicate slide_id {sid!r}")
        else:
            seen_ids.add(sid)
        kind = s.get("kind")
        if kind not in ALL_SLIDE_KINDS:
            errors.append(
                f"slides[{i}] invalid kind {kind!r}; "
                f"valid: {ALL_SLIDE_KINDS}"
            )
        if not s.get("topic"):
            errors.append(f"slides[{i}] missing 'topic'")
        sec = s.get("section", "")
        if sec and sec not in sections:
            errors.append(
                f"slides[{i}] section {sec!r} not in section_arc {sections}"
            )

    # v3.14 — Structural checks
    # 1. Cover should be first, closing/contact should be last (when present)
    if slides:
        first = slides[0]
        if first.get("kind") not in ("cover", "content"):
            # Allow content-as-first if no cover declared
            if any(s.get("kind") == "cover" for s in slides):
                errors.append(
                    f"slides[0] kind={first.get('kind')!r}; "
                    f"cover slide should be first"
                )
        last = slides[-1]
        if last.get("kind") not in ("closing", "contact", "content"):
            if any(s.get("kind") in ("closing", "contact") for s in slides):
                errors.append(
                    f"slides[-1] kind={last.get('kind')!r}; "
                    f"closing/contact slide should be last"
                )

    # 2. Section continuity: slides claiming the same section should be contiguous
    if strict_section_order and sections:
        seen_sections: list[str] = []
        prev_sec = None
        for i, s in enumerate(slides):
            sec = s.get("section", "") or ""
            if not sec:
                continue
            if sec != prev_sec:
                if sec in seen_sections:
                    errors.append(
                        f"slides[{i}] section {sec!r} appears non-contiguous "
                        f"(section block already closed). "
                        f"Group slides by section or pass "
                        f"strict_section_order=False"
                    )
                else:
                    seen_sections.append(sec)
            prev_sec = sec

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------
def slide_count_by_kind(outline: dict) -> dict:
    """Tally how many slides of each kind."""
    counts: dict[str, int] = {}
    for s in outline.get("slides", []):
        k = s.get("kind", "?")
        counts[k] = counts.get(k, 0) + 1
    return counts


def section_distribution(outline: dict) -> dict:
    """Tally how many slides per section."""
    counts: dict[str, int] = {}
    for s in outline.get("slides", []):
        sec = s.get("section", "")
        counts[sec] = counts.get(sec, 0) + 1
    return counts


def renumber_slide_ids(outline: dict, prefix: str = "s") -> dict:
    """v3.14 — Renumber slide IDs to match current positions.

    Each slide's ``slide_id`` becomes ``{prefix}{NN}-{tail}`` where:
        - ``NN`` is the current 1-indexed position (zero-padded to 2)
        - ``tail`` is the original ID stripped of any leading
          ``{prefix}\\d+-`` prefix (so ``s11-procurement`` → ``procurement``)

    Use after Phase 3 edits when you want IDs to read in current order
    (e.g. for cleaner debugging logs). Functional behavior unchanged —
    slide_ids are only stable identifiers, never relied on for ordering.

    Original outline is NOT mutated; a new outline is returned.
    """
    import re as _re
    pat = _re.compile(rf"^{_re.escape(prefix)}\d+-")
    new_slides = []
    for i, s in enumerate(outline.get("slides", []), start=1):
        old_id = s.get("slide_id", "")
        tail = pat.sub("", old_id) if old_id else f"slide-{i}"
        new_id = f"{prefix}{i:02d}-{tail}"
        new_slides.append({**s, "slide_id": new_id})
    return {**outline, "slides": new_slides}


def render_outline_summary(outline: dict) -> str:
    """Plain-text outline for chat display / logs.

    For the user-facing outline table per SKILL.md Phase 2 format,
    use ``render_outline_table()`` instead.
    """
    lines = [f"# {outline.get('doc_title', '')}"]
    sections = outline.get("section_arc", [])
    if sections:
        lines.append("")
        lines.append("Sections: " + " → ".join(sections))
    lines.append("")
    for i, s in enumerate(outline.get("slides", []), start=1):
        sid = s.get("slide_id", "")
        kind = s.get("kind", "")
        sec = s.get("section", "")
        topic = s.get("topic", "")
        sec_label = f"[{sec}] " if sec else ""
        lines.append(f"{i:02d}. {sec_label}({kind}) {topic}  — id={sid}")
    return "\n".join(lines)


def render_outline_table(outline: dict, *, include_rationale: bool = True,
                         include_need_input: bool = True) -> str:
    """Phase 2 outline as a markdown table per SKILL.md Phase 2 format (v3.14).

    10 columns: # · Section · Kind · Topic · Block kinds · Layout sketch ·
    Char budget · Image strategy · Rationale · Need Input.

    The ``include_rationale`` and ``include_need_input`` flags allow trimming
    columns for narrower views (e.g. chat-readability on mobile).

    Below the table, also emits:
        - Total slide count + kind distribution
        - Section distribution
        - Total deck char budget (sum of per-slide char_budget fields)
    """
    lines: list[str] = []
    lines.append(f"**{outline.get('doc_title', '(untitled)')}**")
    sections = outline.get("section_arc", [])
    if sections:
        lines.append(f"Section arc: {' → '.join(sections)}")
    lines.append("")

    # Build header
    cols = ["#", "Section", "Kind", "Topic", "Block kinds",
            "Layout sketch", "Char budget", "Image strategy"]
    if include_rationale:
        cols.append("Rationale")
    if include_need_input:
        cols.append("Need Input")
    lines.append("| " + " | ".join(cols) + " |")
    align = ["---"] * len(cols)
    align[6] = "---:"  # char budget right-align
    lines.append("|" + "|".join(align) + "|")

    for i, s in enumerate(outline.get("slides", []), start=1):
        sec      = s.get("section") or "—"
        kind     = s.get("kind", "")
        topic    = s.get("topic", "")
        bk       = ", ".join(s.get("block_kinds", []) or []) or "—"
        layout   = s.get("layout_sketch", "") or "—"
        budget   = s.get("char_budget", 0)
        budget_s = f"~{budget}" if budget else "—"
        img      = s.get("image_strategy", "") or "—"
        rat      = s.get("rationale", "") or ""
        need     = s.get("need_input", "") or ""
        row = [f"{i:02d}", sec, kind, topic, bk, layout, budget_s, img]
        if include_rationale:
            row.append(rat)
        if include_need_input:
            row.append(need)
        # Escape pipes in cell content
        row = [c.replace("|", "\\|") if isinstance(c, str) else c for c in row]
        lines.append("| " + " | ".join(str(c) for c in row) + " |")

    # Footer stats
    lines.append("")
    lines.append(f"**Stats:** {len(outline.get('slides', []))} slides · "
                 f"kinds: {dict(slide_count_by_kind(outline))} · "
                 f"sections: {dict(section_distribution(outline))}")
    total_budget = sum(s.get("char_budget", 0) for s in outline.get("slides", []))
    if total_budget:
        lines.append(f"**Total char budget:** ~{total_budget:,} chars")
    return "\n".join(lines)
