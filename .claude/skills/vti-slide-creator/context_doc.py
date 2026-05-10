"""
Phase 1 — ContextDoc.

The ContextDoc captures everything we know about a deck *before* writing
any slides:
  - audience    — who is this deck for
  - purpose     — what should the deck achieve
  - customer    — the named customer / partner / region (if applicable)
  - tone        — formal | conversational | technical | sales-pitch | …
  - source_summary — what the source content is about (1-3 sentences)
  - source_assets — list of extracted images (paths + captions)
  - key_facts   — bullet list of verified facts pulled from the source

This is Claude-authored from source ingestion + user confirmation; the
module here just provides schemas + validators + a constructor.
"""
from __future__ import annotations
from typing import Any


VALID_TONES = [
    "formal", "conversational", "technical", "sales-pitch",
    "executive-brief", "training", "academic",
]


def make_context_doc(
    audience: str,
    purpose: str,
    customer: str = "",
    tone: str = "formal",
    source_summary: str = "",
    source_assets: list | None = None,
    key_facts: list | None = None,
    constraints: list | None = None,
    # v3.14 — optional structured multi-source field
    sources: list | None = None,
) -> dict:
    """Build a ContextDoc envelope.

    Args:
        audience:       e.g. "enterprise IT decision-makers in Japan"
        purpose:        e.g. "introduce VTI cloud practice to a new partner"
        customer:       optional named customer / region
        tone:           one of VALID_TONES
        source_summary: 1-3 sentences describing the (combined) source material
        source_assets:  flat list of {kind, path, caption?} from source ingestion
        key_facts:      list of verified facts (strings) from the sources
        constraints:    optional list of constraints (e.g. "max 12 slides")
        sources:        v3.14 — optional structured per-source records when
                        the deck has 2+ inputs. Each entry::

                          {'label': 'Retail Capability v3',
                           'path': '/path/to/file.pptx',
                           'kind': 'pptx',
                           'summary': '44-slide capability profile + 7 cases',
                           'asset_paths': ['/.../images_retail/image1.png', ...],
                           'sections': ['ABOUT VTI', 'RETAIL CASES']}

                        v3.18 — `sections` (optional) lists which deck
                        sections this source contributes to. Closes gap
                        #5: a single source can map to multiple sections
                        (e.g. retail PPTX feeds both ABOUT VTI overview
                        and RETAIL CASES). Use ``sources_for_section()``
                        to query at Phase 4 drafting time.

                        Mutually compatible with ``source_assets`` (a
                        flat-merged list across all sources). Single-source
                        decks can leave ``sources=None``.
    """
    if tone not in VALID_TONES:
        raise ValueError(
            f"tone must be one of {VALID_TONES}, got {tone!r}"
        )
    return {
        "audience":       audience,
        "purpose":        purpose,
        "customer":       customer,
        "tone":           tone,
        "source_summary": source_summary,
        "source_assets":  source_assets or [],
        "key_facts":      key_facts or [],
        "constraints":    constraints or [],
        "sources":        sources or [],
    }


def validate_context_doc(doc: Any) -> tuple[bool, list[str]]:
    """Validate a ContextDoc. Returns (ok, errors)."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return False, ["ContextDoc must be a dict"]
    for f in ("audience", "purpose"):
        if not doc.get(f):
            errors.append(f"missing or empty required field '{f}'")
    tone = doc.get("tone", "formal")
    if tone not in VALID_TONES:
        errors.append(f"tone {tone!r} not in {VALID_TONES}")
    for list_field in ("source_assets", "key_facts", "constraints", "sources"):
        v = doc.get(list_field, [])
        if not isinstance(v, list):
            errors.append(f"{list_field} must be a list")
    # Validate each source_asset shape
    for i, asset in enumerate(doc.get("source_assets", []) or []):
        if not isinstance(asset, dict):
            errors.append(f"source_assets[{i}] must be a dict")
            continue
        if not asset.get("kind") or not asset.get("path"):
            errors.append(
                f"source_assets[{i}] needs at least 'kind' and 'path'"
            )
    # v3.14 — validate each source record (if multi-source)
    for i, src in enumerate(doc.get("sources", []) or []):
        if not isinstance(src, dict):
            errors.append(f"sources[{i}] must be a dict")
            continue
        for k in ("label", "kind", "path"):
            if not src.get(k):
                errors.append(f"sources[{i}] missing '{k}'")
        # v3.18 — `sections` (gap #5): optional list[str] mapping
        # source → contributing deck sections. Validate shape only.
        secs = src.get("sections")
        if secs is not None:
            if not isinstance(secs, list):
                errors.append(f"sources[{i}].sections must be a list")
            else:
                for j, s in enumerate(secs):
                    if not isinstance(s, str):
                        errors.append(
                            f"sources[{i}].sections[{j}] must be a str"
                        )
    return len(errors) == 0, errors


def has_source_images(doc: dict) -> bool:
    """Convenience for Phase 4 image_decisions.suggest_strategy()."""
    for asset in doc.get("source_assets", []) or []:
        if isinstance(asset, dict) and asset.get("kind") == "image":
            return True
    return False


def sources_for_section(doc: dict, section: str) -> list[dict]:
    """v3.18 — Return the structured source records that map to ``section``.

    Closes gap #5: pre-v3.18 there was no way to ask "which source(s)
    contribute to the RETAIL CASES section?". Phase 4 drafters had to
    infer from the flat ``source_summary`` text, which mis-attributed
    images and key facts when one source covered multiple sections.

    Args:
        doc: ContextDoc dict (multi-source preferred — for single-source
             decks ``sources=[]`` and this returns ``[]``).
        section: section name to query (case-insensitive match against
                 each source's ``sections[]``).

    Returns:
        List of source records (subset of ``doc['sources']``) where
        ``section`` appears in the record's ``sections`` field. Records
        without a ``sections`` field never match — Phase 1 must annotate
        each source with the sections it covers for this helper to work.

    Use during Phase 4 drafting to scope image assets, key facts, and
    captions to the right source per slide::

        retail_sources = sources_for_section(doc, 'RETAIL CASES')
        retail_images = sum((s.get('asset_paths', []) for s in retail_sources), [])
    """
    sec_norm = section.strip().casefold()
    out: list[dict] = []
    for src in doc.get("sources", []) or []:
        secs = src.get("sections") or []
        if any(isinstance(s, str) and s.strip().casefold() == sec_norm
               for s in secs):
            out.append(src)
    return out
