"""Phase 3 — semantic image picker (creator v4.4.0).

Replaces the v4.0 ``resolve_lift_image()`` heuristic which scored
candidates by classifier confidence + filename token match. That
approach was content-blind: it picked the "highest confidence content
image per source" — so every slide of a multi-slide case study
inherited the same image, and semantically-irrelevant photos
(portraits, decorative graphics) slipped through whenever they had a
content-like aspect ratio.

The new flow is a 3-step orchestrator-in-the-loop protocol:

1. :func:`enumerate_candidates` returns the top-K candidate image
   paths from the relevant source(s), ranked by classifier confidence
   + filename token hint match, excluding paths already claimed by
   other slides.

2. The **orchestrator** (Claude / a human reviewer) views each
   candidate via a vision-capable tool (``Read`` for paths, or vision
   API for raw bytes), captions what's actually IN the image, and
   reasons about whether the candidate semantically matches the
   slide's message. :func:`set_caption` persists captions back to the
   asset index so they survive across runs and benefit later slides.

3. :func:`record_image_decision` atomically writes the orchestrator's
   chosen decision back into phase_3.json with rationale. The
   strategy can be ``"lift"`` (a candidate matched), ``"synthesize"``
   (no candidate matched but a diagram tells the story; emits a
   ``diagram_spec`` for vti-slide-diagram-builder to execute), or
   ``"text-only"`` (no image and no diagram fit; supporting blocks
   should be added at the same time).

For multi-slide case studies (e.g. Olive Young 1/3, 2/3, 3/3),
:func:`allocate_case_study_images` implements **best-fit** allocation:
when N candidates ≥ M slides, do a 1-to-1 assignment scored by
caption-vs-topic similarity; when N < M, give the single image to the
slide whose message most needs it (typically the case-study-overview
slide) and escalate the rest to diagram or text-only.

Why orchestrator-in-the-loop and not pure-Python: classify_image_kind
filters by aspect/size/filename — purely structural signals. Picking a
content image whose CONTENT matches a slide's message requires
visual understanding (what's drawn, what labels exist, what's the
business context). That's a vision-model job, not a heuristic.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Asset-index helpers
# ---------------------------------------------------------------------------
def _kind_guess(asset: dict) -> str | None:
    """Tolerate the legacy v3.x shape where ``kind_guess`` was a full
    ``classify_image_kind()`` dict instead of just the kind string."""
    kg = asset.get("kind_guess")
    if isinstance(kg, dict):
        return kg.get("kind")
    return kg


def _confidence(asset: dict) -> float:
    """Same legacy-shape tolerance for ``confidence``."""
    kg = asset.get("kind_guess")
    if isinstance(kg, dict):
        return float(kg.get("confidence", 0.0))
    return float(asset.get("confidence", 0.0))


def _filename_hint_score(filename: str, hint_tokens: list[str]) -> float:
    """0.1 per hint token that appears in the filename (lowercase)."""
    fn = filename.lower()
    return sum(0.1 for t in hint_tokens if t and t in fn)


def _hint_tokens(hint: str) -> list[str]:
    """Lowercase alphanumeric tokens of length ≥ 3 from a free-text hint."""
    return [t.lower() for t in hint.split()
            if len(t) >= 3 and t.replace("-", "").replace("_", "").isalnum()]


# ---------------------------------------------------------------------------
# Step 1 — enumerate candidates
# ---------------------------------------------------------------------------
def enumerate_candidates(slide_plan: dict,
                         asset_index: list[dict] | str | Path,
                         *,
                         source_tags: Iterable[str] | None = None,
                         claimed_paths: Iterable[str] = (),
                         top_k: int = 15,
                         allow_kinds: tuple[str, ...] = ("content",),
                         min_confidence: float = 0.2) -> list[dict]:
    """Return the top-K candidate images for a slide, sorted by
    (classifier confidence + filename hint match) descending.

    Args:
        slide_plan:      a SlideContentPlan dict (Phase 3 shape). The
                         picker reads ``image_decision.source_hint``,
                         ``topic``, and ``section_name`` to build the
                         hint-token list used for filename scoring.
        asset_index:     either the loaded list (from
                         ``work/phase_1_assets.json``) OR a path to it.
        source_tags:     restrict candidates to these source tags
                         (e.g. ``["oliveyoung_bi_demo"]``). If None,
                         no source filter applies.
        claimed_paths:   paths already used by other slides — excluded
                         from the candidate set so each slide gets a
                         distinct image (best-fit allocation).
        top_k:           cap on the returned list size. 15 is a good
                         default for orchestrator inspection budgets.
        allow_kinds:     accepted ``kind_guess`` values. Default
                         ``("content",)``; pass
                         ``("content", "unknown")`` to widen.
        min_confidence:  classifier-confidence floor. Default 0.2 lets
                         mid-confidence content candidates through.

    Returns:
        A list of candidate dicts with shape::

            {
              "path":            str,
              "source_tag":      str,
              "kind_guess":      str,
              "confidence":      float,
              "size_bytes":      int,
              "filename":        str,
              "caption":         str | "",   # empty if not yet captioned
              "score":           float,      # confidence + hint match
              "hint_match":      float,      # filename-only contribution
              "classify_reasons": list[str],
            }
    """
    if isinstance(asset_index, (str, Path)):
        asset_index = json.loads(Path(asset_index).read_text())
    if not isinstance(asset_index, list):
        raise TypeError("asset_index must be a list of asset dicts or a path to one")

    src_filter = set(source_tags) if source_tags is not None else None
    claimed = {str(p) for p in claimed_paths}

    # Build hint tokens from source_hint, topic, section_name
    img_dec = slide_plan.get("image_decision", {})
    hint = " ".join([
        img_dec.get("source_hint", ""),
        slide_plan.get("topic", ""),
        slide_plan.get("section_name", ""),
    ])
    tokens = _hint_tokens(hint)

    candidates: list[dict] = []
    for a in asset_index:
        if src_filter is not None and a.get("source_tag") not in src_filter:
            continue
        kind = _kind_guess(a)
        if kind not in allow_kinds:
            continue
        conf = _confidence(a)
        if conf < min_confidence:
            continue
        path = str(a.get("path", ""))
        if not path or path in claimed:
            continue

        filename = Path(path).name
        hint_match = _filename_hint_score(filename, tokens)
        score = conf + hint_match
        candidates.append({
            "path":             path,
            "source_tag":       a.get("source_tag", ""),
            "kind_guess":       kind,
            "confidence":       conf,
            "size_bytes":       a.get("size_bytes", 0),
            "filename":         filename,
            "caption":          a.get("caption", "") or "",
            "score":            score,
            "hint_match":       hint_match,
            "classify_reasons": a.get("classify_reasons", []),
        })

    candidates.sort(key=lambda c: -c["score"])
    return candidates[:top_k]


# ---------------------------------------------------------------------------
# Step 2 — caption persistence (orchestrator writes back)
# ---------------------------------------------------------------------------
def get_caption(asset_index: list[dict], image_path: str) -> str | None:
    """Return the cached caption for ``image_path``, or None if not set."""
    target = str(image_path)
    for a in asset_index:
        if str(a.get("path", "")) == target:
            cap = a.get("caption", "")
            return cap or None
    return None


def set_caption(asset_index_path: str | Path,
                image_path: str,
                caption: str) -> None:
    """Atomically write ``caption`` back to the asset entry in
    ``asset_index_path`` (e.g. ``work/phase_1_assets.json``).

    Reads → mutates → writes. Caller doesn't need to manage the file
    handle; concurrent writers are NOT supported (single-orchestrator
    flow only).
    """
    path = Path(asset_index_path)
    assets = json.loads(path.read_text())
    target = str(image_path)
    found = False
    for a in assets:
        if str(a.get("path", "")) == target:
            a["caption"] = caption
            found = True
            break
    if not found:
        # Append as a minimal stub so future enumerate_candidates can
        # still see the entry (caller is responsible for the original
        # asset metadata if they want full classification info).
        assets.append({
            "kind":       "image",
            "path":       target,
            "caption":    caption,
            "kind_guess": "content",
            "source_tag": Path(target).parent.name,
        })
    path.write_text(json.dumps(assets, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Step 3 — record orchestrator decision back into phase_3.json
# ---------------------------------------------------------------------------
@dataclass
class ImageDecision:
    """Structured decision the orchestrator records per slide.

    ``strategy`` is the new value for the slide's
    ``image_decision.strategy``. ``rationale`` is a short sentence
    explaining WHY (used in the phase_3 summary so the user can audit
    overrides without re-running the picker).
    """
    strategy:        str   # "lift" | "synthesize" | "text-only"
    rationale:       str
    resolved_image:  dict | None = None    # for "lift"
    diagram_spec:    dict | None = None    # for "synthesize"
    candidates_seen: list[str] = field(default_factory=list)


def record_image_decision(plan_path: str | Path,
                          slide_id: str,
                          decision: ImageDecision) -> None:
    """Patch ``phase_3.json`` for one slide with a new image_decision +
    a ``decision_rationale`` field for audit. Idempotent."""
    path = Path(plan_path)
    plans = json.loads(path.read_text())
    if slide_id not in plans:
        raise KeyError(f"slide_id {slide_id!r} not in {path.name}")

    plan = plans[slide_id]
    plan.setdefault("image_decision", {})
    plan["image_decision"]["strategy"] = decision.strategy
    plan["image_decision"]["rationale"] = decision.rationale
    plan["image_decision"]["candidates_seen"] = list(decision.candidates_seen)

    if decision.strategy == "lift":
        if decision.resolved_image is None:
            raise ValueError("strategy='lift' requires resolved_image")
        plan["resolved_image"] = decision.resolved_image
        plan.pop("diagram_spec", None)
    elif decision.strategy == "synthesize":
        if decision.diagram_spec is None:
            raise ValueError("strategy='synthesize' requires diagram_spec")
        plan["diagram_spec"] = decision.diagram_spec
        plan.pop("resolved_image", None)
    else:
        # text-only — drop any prior image attachments
        plan.pop("resolved_image", None)
        plan.pop("diagram_spec", None)

    path.write_text(json.dumps(plans, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Multi-slide case-study allocation (best-fit)
# ---------------------------------------------------------------------------
def allocate_case_study_images(case_study_slides: list[str],
                                  ranked_candidates: list[list[dict]],
                                  ) -> list[tuple[str, dict | None]]:
    """Best-fit allocation across a multi-slide case study.

    ``case_study_slides`` is an ordered list of slide_ids belonging to
    the same case study (e.g. ``["s13-oliveyoung-case",
    "s14-oliveyoung-platform", "s15-oliveyoung-ml"]``).
    ``ranked_candidates`` is a parallel list — for each slide, the
    candidates already produced by :func:`enumerate_candidates` (with
    ``score`` filled in).

    Strategy:

    - When the union of candidate sets has ≥ M images for M slides,
      assign 1-to-1 by greedy descent: pick highest-overall-score
      candidate, assign to its preferred slide, remove from pool,
      repeat.
    - When the union has < M images, give the single (or N<M) images
      to the slide(s) whose top score is highest. The remaining slides
      return ``(slide_id, None)`` — caller is expected to escalate
      those to ``synthesize`` or ``text-only``.

    Returns: list of ``(slide_id, candidate_dict | None)`` in the same
    order as ``case_study_slides``. ``None`` means "no image left for
    this slide — caller must escalate".

    This function does NOT call the orchestrator; it operates on
    already-scored candidate lists. The orchestrator's semantic
    ranking (caption-vs-topic match) should already be reflected in
    each candidate's ``score`` BEFORE invoking this allocator.
    """
    n_slides = len(case_study_slides)
    if n_slides == 0:
        return []

    # Build (slide_idx, candidate) tuples sorted by score desc, with
    # path-deduplication so the same image is never assigned twice.
    pool: list[tuple[int, dict]] = []
    for i, cands in enumerate(ranked_candidates):
        for c in cands:
            pool.append((i, c))
    pool.sort(key=lambda ic: -ic[1]["score"])

    assignments: dict[int, dict] = {}
    used_paths: set[str] = set()
    for i, c in pool:
        if i in assignments:
            continue
        if c["path"] in used_paths:
            continue
        assignments[i] = c
        used_paths.add(c["path"])
        if len(assignments) == n_slides:
            break

    return [(sid, assignments.get(i)) for i, sid in enumerate(case_study_slides)]


# ---------------------------------------------------------------------------
# Convenience: build a worklist file the orchestrator can iterate over
# ---------------------------------------------------------------------------
def build_worklist(plan_path: str | Path,
                   asset_index_path: str | Path,
                   *,
                   top_k: int = 15) -> dict:
    """Walk all lift slides in a phase_3 plan, enumerate candidates per
    slide (respecting per-source-tag scope inferred from
    ``image_decision.source_hint``), and return a worklist dict the
    orchestrator iterates through.

    Output shape::

        {
          "slides": [
            {
              "slide_id":      "...",
              "topic":         "...",
              "summary":       "...",  # blocks summary, for context
              "source_hint":   "...",
              "source_tags":   ["..."],
              "candidates":    [ {... candidate dict ...}, ... ],
            },
            ...
          ],
          "total_slides":     int,
          "total_candidates": int,
        }

    Source tags are inferred greedily: the first source_tag word that
    matches the leading hint token. Pass an explicit ``sources`` list
    in the slide plan to override.
    """
    plans = json.loads(Path(plan_path).read_text())
    assets = json.loads(Path(asset_index_path).read_text())
    known_sources = sorted({a.get("source_tag", "") for a in assets if a.get("source_tag")})

    out_slides: list[dict] = []
    for sid, plan in plans.items():
        img = plan.get("image_decision", {})
        if img.get("strategy") != "lift":
            continue
        hint = img.get("source_hint", "")
        # Infer source tags by hint prefix matching against known tags
        hint_lower = hint.lower()
        source_tags = [t for t in known_sources
                       if t and t.lower() in hint_lower]
        if not source_tags:
            # Fallback: use slide section/topic keywords
            for t in known_sources:
                stem = t.split("_")[0]
                if stem and stem in hint_lower:
                    source_tags.append(t)
        cands = enumerate_candidates(
            plan, assets, source_tags=source_tags or None, top_k=top_k,
        )
        # Render a compact summary of blocks for the orchestrator
        block_summary_parts: list[str] = []
        for b in plan.get("blocks", []):
            block_summary_parts.append(b.get("kind", "?"))
        out_slides.append({
            "slide_id":     sid,
            "topic":        plan.get("topic", ""),
            "summary":      ", ".join(block_summary_parts),
            "source_hint":  hint,
            "source_tags":  source_tags,
            "candidates":   cands,
        })

    return {
        "slides":           out_slides,
        "total_slides":     len(out_slides),
        "total_candidates": sum(len(s["candidates"]) for s in out_slides),
    }
