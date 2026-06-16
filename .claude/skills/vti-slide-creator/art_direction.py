"""Art Direction Brief + archetype rationing (v4.0 / M3 — Governor 1).

The M3 "art-director" model lets the orchestrator pick a different
archetype per slide (see vti-slide-page-builder/archetypes.py). Left
unchecked that risks 30 slides in 30 styles. This module is the coherence
governor: a small deck-level **Art Direction Brief** that is produced once
(Phase 2) and injected into every per-slide DESIGN step, plus an
**archetype rationer** that varies layout rhythm so the deck breathes
without becoming random.

The Brief deliberately holds only DESIGN knobs that ContextDoc/​density_mode
don't already carry (accent rotation, surface policy, layout rhythm). Mood
echoes the chosen voice so the design matches the prose.

Public surface
--------------
- ``make_brief(...)``        → validated brief dict (store on plan['art_brief'])
- ``brief_guidance(brief)``  → short text to prepend to each DESIGN prompt
- ``ration_archetypes(intent, used_counts, recent)`` → ordered candidate ids
"""
from __future__ import annotations

# Mood echoes the deck voice (see feedback_voice_handshake) so layout +
# prose agree. Not a hard enum — these are the canonical starting points.
MOODS = {
    "consultative-sales", "technical-deep", "executive-brief", "educational",
}
ACCENT_POLICIES = {
    "rotate-by-section",   # advance the accent each section for rhythm
    "single-accent",       # one brand blue throughout (most conservative)
    "warm-secondary",      # blue base + one secondary hue from motif_vocab
}
DENSITY_TARGETS = {"sparse-ok", "standard", "dense"}
SURFACE_POLICIES = {
    "surfaces-ok",   # archetypes may use panel/tint/elevated freely
    "flat",          # avoid surfaces — plain cells only (minimalist decks)
}


def make_brief(*,
               mood: str,
               accent_policy: str = "rotate-by-section",
               density_target: str = "standard",
               surface_policy: str = "surfaces-ok",
               motif_vocab: list[str] | None = None,
               notes: str = "") -> dict:
    """Build + validate the deck-level Art Direction Brief.

    Raises ValueError on an out-of-vocab enum so a typo is caught at Phase 2
    rather than silently ignored downstream.
    """
    if accent_policy not in ACCENT_POLICIES:
        raise ValueError(f"accent_policy must be one of {sorted(ACCENT_POLICIES)}")
    if density_target not in DENSITY_TARGETS:
        raise ValueError(f"density_target must be one of {sorted(DENSITY_TARGETS)}")
    if surface_policy not in SURFACE_POLICIES:
        raise ValueError(f"surface_policy must be one of {sorted(SURFACE_POLICIES)}")
    return {
        "mood": mood,
        "accent_policy": accent_policy,
        "density_target": density_target,
        "surface_policy": surface_policy,
        "motif_vocab": list(motif_vocab or []),
        "notes": notes.strip(),
    }


def brief_guidance(brief: dict) -> str:
    """Render the brief as a short instruction block to prepend to each
    per-slide DESIGN prompt — keeps every slide on the same art direction."""
    if not brief:
        return ""
    lines = [
        "ART DIRECTION BRIEF (apply to THIS slide so the deck stays coherent):",
        f"- Mood: {brief.get('mood', 'consultative-sales')} — let composition + "
        "whitespace echo this tone.",
        f"- Accent policy: {brief.get('accent_policy', 'rotate-by-section')}.",
        f"- Density target: {brief.get('density_target', 'standard')}.",
        f"- Surfaces: {brief.get('surface_policy', 'surfaces-ok')} "
        "(panel | tint | elevated).",
    ]
    if brief.get("motif_vocab"):
        lines.append(f"- Motif vocabulary: {', '.join(brief['motif_vocab'])}.")
    if brief.get("notes"):
        lines.append(f"- Notes: {brief['notes']}")
    return "\n".join(lines)


def ration_archetypes(intent: str,
                      used_counts: dict[str, int],
                      recent: list[str],
                      *,
                      catalog: list[dict] | None = None) -> list[dict]:
    """Return candidate archetypes for ``intent``, ordered to favour variety.

    Sorting: (1) not used in the last 2 slides first (avoid back-to-back
    repeats), then (2) least-used overall, then (3) declaration order. The
    orchestrator picks the top candidate that fits the slide's content, so
    the deck gets intentional rhythm instead of one repeated frame.

    Args:
        intent: the slide intent tag (matches archetype['intent']).
        used_counts: ``{archetype_id: times_used}`` so far in the deck.
        recent: archetype ids used on the last ~2 slides.
        catalog: archetype list (defaults to the page-builder library). Pass
                 a custom list for testing.
    """
    if catalog is None:
        from archetypes import list_archetypes  # page-builder, on PYTHONPATH
        catalog = list_archetypes()
    matches = [a for a in catalog if a.get("intent") == intent]
    if not matches:  # no exact intent match → offer everything, still rationed
        matches = list(catalog)
    recent_set = set(recent[-2:])
    return sorted(
        matches,
        key=lambda a: (a["id"] in recent_set, used_counts.get(a["id"], 0)),
    )


__all__ = [
    "MOODS", "ACCENT_POLICIES", "DENSITY_TARGETS", "SURFACE_POLICIES",
    "make_brief", "brief_guidance", "ration_archetypes",
]
