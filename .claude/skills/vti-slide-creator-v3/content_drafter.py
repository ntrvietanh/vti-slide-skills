"""
Phase 4 — Content drafter.

Decomposes a slide topic into typed content blocks + an image strategy
decision. Output is a ``SlideContentPlan`` consumed by Phase 5.

The actual block decomposition is Claude's reasoning over source material;
this module provides:
  - typed schemas for each content-block kind
  - constructors / validators
  - a SlideContentPlan envelope
  - utilities for inspecting block lists

Public API
----------
``CONTENT_BLOCK_SCHEMAS``     — kind → {required, optional, picker_kind}
``IMAGE_STRATEGIES``          — list of valid image strategy names
``make_block(kind, content)`` — block constructor
``make_slide_content_plan(...)`` — plan envelope constructor
``validate_block(block)``     → (ok, errors)
``validate_plan(plan)``       → (ok, errors)
``block_kinds_in(plan)``      → list of kinds present (for picker)
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Block kind schemas
# ---------------------------------------------------------------------------
# `picker_kind` aligns with component_catalog.picks_for_kind(...) so that
# Phase 5 can map a content block straight to a candidate component.
#
# Note: there is NO `header` block kind. The slide title + section name
# live on the SlideContentPlan envelope itself (`topic` + `section_name`)
# and flow into chrome `slide_meta.slide_title` + `slide_meta.section_name`
# at Phase 5 — the breadcrumb renders them as "SECTION | TITLE". Content
# blocks are reserved for actual content (narrative, stats, lists, cards,
# dividers).
CONTENT_BLOCK_SCHEMAS: dict[str, dict] = {
    "narrative": {
        "description":  "1-4 paragraph body text.",
        "required":     ["paragraphs"],
        "optional":     ["align", "max_width"],
        "picker_kind":  "narrative",
        "expected_count_per_slide": "0-2",
    },
    "hero_stat": {
        "description":  "1 dominant number with a short label.",
        "required":     ["value", "label"],
        "optional":     ["decoration"],
        "picker_kind":  "hero_stat",
        "expected_count_per_slide": "0-1",
    },
    "supporting_stats": {
        "description":  "2-5 small metrics in a horizontal strip.",
        "required":     ["items"],   # list of {icon, value, label}
        "optional":     [],
        "picker_kind":  "supporting_stats",
        "expected_count_per_slide": "0-1",
    },
    "list": {
        "description":  "2-8 bullet items (with check-icon).",
        "required":     ["items"],
        "optional":     ["density"],
        "picker_kind":  "list",
        "expected_count_per_slide": "0-2",
    },
    "features_3": {
        "description":  "3 peer features with body text (hero cards).",
        "required":     ["cards"],   # list of {number?, icon, title, body, color_tone?}
        "optional":     [],
        "picker_kind":  "features_3",
        "expected_count_per_slide": "0-1",
    },
    "values": {
        "description":  "4-6 short labels with optional taglines (medallions).",
        "required":     ["cards"],   # list of {icon, title, tagline?, number?, color_tone?}
        "optional":     [],
        "picker_kind":  "values",
        "expected_count_per_slide": "0-1",
    },
    "catalog": {
        "description":  "2-3 categorized lists with header bands.",
        "required":     ["columns"],  # list of {label, category_icon, items, count_text?, color_tone?}
        "optional":     [],
        "picker_kind":  "catalog",
        "expected_count_per_slide": "0-1",
    },
    "comparison_divider": {
        "description":  "VS badge — sits between 2 panels in compare-mirror.",
        "required":     [],
        "optional":     ["label", "has_line", "line_style"],
        "picker_kind":  "comparison_divider",
        "expected_count_per_slide": "0-1",
    },

    # -----------------------------------------------------------------
    # Visual block kinds (v3.16) — first-class blocks for diversifying
    # decks beyond text. See SKILL.md Principle 8 for selection guide.
    # -----------------------------------------------------------------
    "image_tile": {
        "description":  "Image with optional caption — case-study screenshots, hero photos, lifted source slides.",
        "required":     ["image"],   # path / URL / data: URI
        "optional":     ["caption", "aspect_ratio", "frame", "caption_position"],
        "picker_kind":  "image_tile",
        "expected_count_per_slide": "0-2",
    },
    "process_flow": {
        "description":  "3-7 ordered steps (Req → Design → Dev → Test → Deploy → Maintain).",
        "required":     ["steps"],   # list of {title≤30, body?≤140, number?, icon?}
        "optional":     ["direction"],  # 'horizontal'|'vertical'
        "picker_kind":  "process_flow",
        "expected_count_per_slide": "0-1",
    },
    "bar_chart": {
        "description":  "Bar chart for comparing values (KPIs, forecasts, allocations).",
        "required":     ["items"],   # list of {label, value, tone?}
        "optional":     ["orientation", "x_axis_label", "y_axis_label"],
        "picker_kind":  "bar_chart",
        "expected_count_per_slide": "0-1",
    },
    "pie_chart": {
        "description":  "Pie / donut chart for share-of-total (industry mix, allocation %).",
        "required":     ["items"],   # list of {label, value, color?}
        "optional":     ["donut", "center_value", "center_label"],
        "picker_kind":  "pie_chart",
        "expected_count_per_slide": "0-1",
    },
    "logo_grid": {
        "description":  "Grid of partner / certification / award logos (proof signal).",
        "required":     ["logos"],   # list of {image?, name?}
        "optional":     ["cols", "tone"],   # cols 3-6, tone 'color'|'mono'
        "picker_kind":  "logo_grid",
        "expected_count_per_slide": "0-1",
    },
    "icon_list": {
        "description":  "6-12 parallel items with icon+title+optional 1-line body. Replaces stacked features_3.",
        "required":     ["items"],   # list of {icon, title, body?}
        "optional":     ["density"],  # 'compact'|'default'|'loose'
        "picker_kind":  "icon_list",
        "expected_count_per_slide": "0-1",
    },
}


# ---------------------------------------------------------------------------
# Image strategies
# ---------------------------------------------------------------------------
IMAGE_STRATEGIES: list[str] = ["lift", "synthesize", "web-search", "text-only"]


# ---------------------------------------------------------------------------
# Constructors
# ---------------------------------------------------------------------------
def make_block(kind: str, content: dict[str, Any]) -> dict[str, Any]:
    """Construct a typed content block."""
    if kind not in CONTENT_BLOCK_SCHEMAS:
        raise ValueError(
            f"unknown block kind '{kind}'. "
            f"valid: {list(CONTENT_BLOCK_SCHEMAS.keys())}"
        )
    return {"kind": kind, "content": content}


def make_image_decision(strategy: str, reason: str = "",
                        source_hint: str = "",
                        validate_lift_path: bool = False,
                        available_assets: list | None = None,
                        ) -> dict[str, str]:
    """Construct an image strategy decision.

    Args:
        strategy: one of ``IMAGE_STRATEGIES``
        reason: short why-this-strategy
        source_hint: for ``lift``, path/source ref to the asset.
                     For ``synthesize``, description of what to build.
                     For ``web-search``, query terms.
        validate_lift_path: if True and strategy=='lift', verify
                            ``source_hint`` exists on disk. Raises
                            FileNotFoundError otherwise. Default False
                            so callers can pass placeholders during
                            drafting and validate later.
        available_assets: v3.18 (closes gap #21) — optional list of
                          asset dicts (e.g. ``ContextDoc.source_assets``).
                          When ``strategy='lift'`` and the hint is NOT
                          a literal path, fuzzy-match the hint against
                          ``asset['caption']`` and ``asset['path']``
                          basenames. If no asset's caption/basename
                          contains any token of the hint, raise
                          ValueError. This catches stale hints like
                          ``'retail/p4 group photo'`` after the upstream
                          source was renamed or replaced.

    Returns:
        ``{'strategy': ..., 'reason': ..., 'source_hint': ...}``.
        v3.18 — when ``available_assets`` is supplied and a match is
        found, the dict additionally carries
        ``'matched_asset_path': <abs path>`` so Phase 5 can route
        directly to the file without re-fuzzy-matching.
    """
    if strategy not in IMAGE_STRATEGIES:
        raise ValueError(
            f"strategy must be one of {IMAGE_STRATEGIES}, got '{strategy}'"
        )
    if validate_lift_path and strategy == "lift" and source_hint:
        # Source hint may be a description like "retail/p4 group photo" rather
        # than a literal path. Only validate when it looks like a path.
        if source_hint.startswith("/") or source_hint.startswith("./"):
            from pathlib import Path
            if not Path(source_hint).exists():
                raise FileNotFoundError(
                    f"lift source_hint path does not exist: {source_hint}"
                )

    out: dict = {"strategy": strategy, "reason": reason,
                 "source_hint": source_hint}

    # v3.18 — fuzzy hint validation against available_assets (gap #21)
    if (strategy == "lift" and source_hint and available_assets is not None
            and not (source_hint.startswith("/") or source_hint.startswith("./"))):
        from pathlib import Path
        # Tokenize the hint: split on /, whitespace, dashes
        import re as _re
        tokens = [t.lower() for t in _re.split(r"[\s/\-_]+", source_hint) if len(t) > 2]
        match: dict | None = None
        for asset in available_assets:
            if not isinstance(asset, dict):
                continue
            caption = (asset.get("caption") or "").lower()
            basename = Path(asset.get("path", "")).name.lower()
            haystack = caption + " " + basename
            if any(tok in haystack for tok in tokens):
                match = asset
                break
        if match is None:
            raise ValueError(
                f"lift source_hint {source_hint!r} did not fuzzy-match any "
                f"available asset's caption or basename. "
                f"Either correct the hint, supply a literal path, or pass "
                f"available_assets=None to skip this check."
            )
        out["matched_asset_path"] = match.get("path", "")
    return out


def make_slide_content_plan(slide_id: str,
                            topic: str,
                            blocks: list[dict],
                            image_decision: dict,
                            section_name: str = "",
                            layout_hint: str = "",
                            diagram_spec: dict | None = None,
                            resolved_image: dict | None = None) -> dict:
    """Wrap typed blocks + image decision into a SlideContentPlan.

    The plan is the unit of communication between Phase 3 (this module)
    and Phase 4 (LAYOUT-DESIGN, in v4.0). Phase 4 reads ``blocks``,
    ``diagram_spec``, and ``resolved_image`` to size cells correctly so
    no image is cropped.

    Title routing
    -------------
    ``topic`` is the slide's per-page title and ``section_name`` is its
    breadcrumb section. Both flow straight into the chrome breadcrumb at
    compose time (slide_meta.slide_title and slide_meta.section_name).

    v4.0 — diagram_spec (NEW)
    -------------------------
    When ``image_decision.strategy == 'synthesize'``, Phase 3 calls into
    the ``vti-slide-diagram-builder`` skill, writes the SVG to
    ``work/diagrams/<slide_id>.svg``, and stores the spec here::

        {
            "primitive":    "flow_diagram",       # name from diagram-builder
            "args":         {...},                # caller args (stored for resume)
            "svg_path":     "work/diagrams/...",
            "natural_w":    1180,
            "natural_h":    460,
        }

    Phase 4 reads ``natural_w / natural_h`` to set the hosting
    image-tile cell aspect_ratio so the diagram is never cropped.

    v4.0 — resolved_image (NEW)
    ---------------------------
    When ``image_decision.strategy == 'lift'``, Phase 3's
    ``resolve_lift_image()`` filters source-image candidates via
    ``classify_image_kind()`` and stores the chosen file::

        {
            "path":         "work/sources/_images/foo.jpg",
            "natural_w":    1920,
            "natural_h":    1080,
            "kind":         "content",  # never 'chrome' or 'stock'
            "score":        0.78,
        }

    Layout hint (v3.17, Principle 9)
    --------------------------------
    Optional ``layout_hint`` is a HINT only — Phase 4 may override.

    - ``"pattern-a-content-first"`` — content dominates; image small
    - ``"pattern-b-image-narrative-side-by-side"`` — image dominates
    - ``"pattern-b-full-width-image"`` — image full-width hero
    - ``""`` (empty) — default vertical stack
    """
    return {
        "slide_id":       slide_id,
        "topic":          topic,
        "section_name":   section_name,
        "blocks":         blocks,
        "image_decision": image_decision,
        "layout_hint":    layout_hint,
        "diagram_spec":   diagram_spec,    # None unless synthesize
        "resolved_image": resolved_image,  # None unless lift+resolved
    }


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------
def validate_block(block: Any) -> tuple[bool, list[str]]:
    """Validate one content block. Returns (ok, error_messages).

    v3.14: now enforces per-component HARD CAPS from `capacity.BLOCK_KIND_CAPS`.
    Previously only checked schema-completeness — drafts past compose-time
    limits validated as ok and then crashed at Phase 5 render. This closes
    the gap.
    """
    errors: list[str] = []
    if not isinstance(block, dict):
        return False, ["block must be a dict"]
    kind = block.get("kind")
    if kind not in CONTENT_BLOCK_SCHEMAS:
        valid = list(CONTENT_BLOCK_SCHEMAS.keys())
        return False, [f"unknown block kind '{kind}'; valid: {valid}"]
    schema = CONTENT_BLOCK_SCHEMAS[kind]
    content = block.get("content")
    if not isinstance(content, dict):
        return False, [f"block.content must be dict for kind '{kind}'"]

    # Schema-completeness check (legacy)
    for field in schema["required"]:
        if field not in content or content[field] in ("", None, []):
            errors.append(
                f"block(kind={kind}): missing or empty required field '{field}'"
            )

    # v3.14 — enforce HARD CAPS that compose-time validators will check.
    # Skip if completeness already failed (don't pile-on).
    if not errors:
        try:
            from capacity import BLOCK_KIND_CAPS
            caps = BLOCK_KIND_CAPS.get(kind, {})
            errors.extend(_check_caps(kind, content, caps))
        except ImportError:
            pass  # capacity module optional — fall back to schema-only

    # v3.17.1 — enforce ENUM constraints (catch render-time errors that
    # cap-checks miss: 'EST. 2017' as decoration, 'mono' as tone, etc.)
    if not errors:
        errors.extend(_check_enums(kind, content))

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Enum validation (v3.17.1) — catch render-time enum errors at draft time
# ---------------------------------------------------------------------------
#
# A class of v3.16-build runtime errors slipped past validate_block because
# the schemas only checked CAP (length, count) not VALUE-DOMAIN (enum). A
# stat-hero.decoration of 'EST. 2017' looked like a 9-char string (under
# any cap) but composer_grid raised a hard ValidationError because
# decoration must be exactly 'rings' or 'none'. Same story for logo-grid
# tone: 'mono' is reasonable shorthand but composer wants 'monochrome'.
#
# This table mirrors composer_grid's enum constraints so we catch them at
# Phase 4 instead of at Phase 5 render. Keep in sync with composer_grid
# whenever the rendering enums change.
# ---------------------------------------------------------------------------
BLOCK_KIND_ENUMS: dict[str, dict[str, list[str]]] = {
    "hero_stat": {
        "decoration": ["rings", "none"],
    },
    "logo_grid": {
        "tone": ["color", "monochrome", "muted"],
    },
    "icon_list": {
        "density": ["compact", "default", "loose"],
    },
    "list": {
        "density": ["compact", "default", "loose"],
    },
    "process_flow": {
        "direction": ["horizontal", "vertical"],
    },
    "bar_chart": {
        "orientation": ["vertical", "horizontal"],
    },
    "image_tile": {
        "frame": ["none", "rounded", "shadow", "polaroid"],
        "caption_position": ["below", "overlay-bottom", "overlay-top"],
    },
}


def _check_enums(kind: str, content: dict) -> list[str]:
    """Per-block enum validator. Returns list of error strings.

    Catches values that satisfy length-caps but violate the rendering
    component's value-domain constraints. Keeps validate_block honest:
    if validate_block returns ok=True, the block must render at Phase 5.
    """
    errs: list[str] = []
    enum_map = BLOCK_KIND_ENUMS.get(kind, {})
    for field, allowed in enum_map.items():
        if field not in content:
            continue  # optional fields can be absent
        v = content[field]
        if v is None or v == "":
            continue
        if v not in allowed:
            errs.append(
                f"{kind}.{field} = {v!r} not in allowed values {allowed}"
            )
    return errs


def _check_caps(kind: str, content: dict, caps: dict) -> list[str]:
    """Per-block-kind hard-cap validator. Returns list of error strings."""
    errs: list[str] = []
    if kind == "narrative":
        paras = content.get("paragraphs", []) or []
        c_min = caps.get("paragraphs_count_min", 1)
        c_max = caps.get("paragraphs_count_max", 4)
        each = caps.get("paragraphs_each_max", 400)
        if not c_min <= len(paras) <= c_max:
            errs.append(f"narrative.paragraphs count {len(paras)} not in {c_min}..{c_max}")
        for i, p in enumerate(paras):
            if isinstance(p, str) and len(p) > each:
                errs.append(f"narrative.paragraphs[{i}] is {len(p)} chars (max {each})")
    elif kind == "hero_stat":
        v = content.get("value", "")
        l = content.get("label", "")
        if isinstance(v, str) and len(v) > caps.get("value_max", 8):
            errs.append(f"hero_stat.value is {len(v)} chars (max {caps['value_max']})")
        if isinstance(l, str) and len(l) > caps.get("label_max", 30):
            errs.append(f"hero_stat.label is {len(l)} chars (max {caps['label_max']})")
    elif kind == "supporting_stats":
        items = content.get("items", []) or []
        c_min = caps.get("items_count_min", 2)
        c_max = caps.get("items_count_max", 5)
        if not c_min <= len(items) <= c_max:
            errs.append(f"supporting_stats.items count {len(items)} not in {c_min}..{c_max}")
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                errs.append(f"supporting_stats.items[{i}] must be dict")
                continue
            v = str(it.get("value", "")); l = str(it.get("label", ""))
            if len(v) > caps.get("item_value_max", 8):
                errs.append(f"supporting_stats.items[{i}].value is {len(v)} chars (max {caps['item_value_max']})")
            if len(l) > caps.get("item_label_max", 30):
                errs.append(f"supporting_stats.items[{i}].label is {len(l)} chars (max {caps['item_label_max']})")
    elif kind == "list":
        items = content.get("items", []) or []
        c_min = caps.get("items_count_min", 2)
        c_max = caps.get("items_count_max", 8)
        each = caps.get("items_each_max", 100)
        if not c_min <= len(items) <= c_max:
            errs.append(f"list.items count {len(items)} not in {c_min}..{c_max}")
        for i, it in enumerate(items):
            if isinstance(it, str) and len(it) > each:
                errs.append(f"list.items[{i}] is {len(it)} chars (max {each})")
    elif kind == "features_3":
        cards = content.get("cards", []) or []
        c_min = caps.get("cards_count_min", 3)
        c_max = caps.get("cards_count_max", 3)
        if not c_min <= len(cards) <= c_max:
            errs.append(f"features_3.cards count {len(cards)} not in {c_min}..{c_max}")
        t_max = caps.get("card_title_max", 28)
        b_max = caps.get("card_body_max", 220)
        for i, c in enumerate(cards):
            if not isinstance(c, dict):
                errs.append(f"features_3.cards[{i}] must be dict")
                continue
            t = str(c.get("title", "")); b = str(c.get("body", ""))
            if len(t) > t_max:
                errs.append(f"features_3.cards[{i}].title is {len(t)} chars (max {t_max})")
            if len(b) > b_max:
                errs.append(f"features_3.cards[{i}].body is {len(b)} chars (max {b_max})")
    elif kind == "values":
        cards = content.get("cards", []) or []
        c_min = caps.get("cards_count_min", 4)
        c_max = caps.get("cards_count_max", 6)
        if not c_min <= len(cards) <= c_max:
            errs.append(f"values.cards count {len(cards)} not in {c_min}..{c_max}")
        for i, c in enumerate(cards):
            if not isinstance(c, dict): continue
            t = str(c.get("title", "")); tg = str(c.get("tagline", "") or "")
            if len(t) > caps.get("card_title_max", 22):
                errs.append(f"values.cards[{i}].title is {len(t)} chars (max {caps['card_title_max']})")
            if tg and len(tg) > caps.get("card_tagline_max", 60):
                errs.append(f"values.cards[{i}].tagline is {len(tg)} chars (max {caps['card_tagline_max']})")
    elif kind == "catalog":
        cols = content.get("columns", []) or []
        c_min = caps.get("columns_count_min", 2)
        c_max = caps.get("columns_count_max", 3)
        if not c_min <= len(cols) <= c_max:
            errs.append(f"catalog.columns count {len(cols)} not in {c_min}..{c_max}")
        for i, col in enumerate(cols):
            if not isinstance(col, dict): continue
            l = str(col.get("label", ""))
            if len(l) > caps.get("column_label_max", 24):
                errs.append(f"catalog.columns[{i}].label is {len(l)} chars (max {caps['column_label_max']})")
            for j, item in enumerate(col.get("items", []) or []):
                txt = item if isinstance(item, str) else str(item.get("text", ""))
                if len(txt) > caps.get("column_item_text_max", 80):
                    errs.append(f"catalog.columns[{i}].items[{j}] is {len(txt)} chars (max {caps['column_item_text_max']})")
    elif kind == "comparison_divider":
        label = content.get("label", "VS")
        if isinstance(label, str) and len(label) > caps.get("label_max", 6):
            errs.append(f"comparison_divider.label is {len(label)} chars (max {caps['label_max']})")

    # ---- visual block kinds (v3.16) --------------------------------------
    elif kind == "image_tile":
        # `image` field is required by schema; we don't validate path-exists
        # here (filesystem check is too coarse for in-memory plans).
        cap = content.get("caption", "")
        if isinstance(cap, str) and len(cap) > caps.get("caption_max", 120):
            errs.append(f"image_tile.caption is {len(cap)} chars (max {caps['caption_max']})")
    elif kind == "process_flow":
        steps = content.get("steps", []) or []
        c_min = caps.get("steps_count_min", 3)
        c_max = caps.get("steps_count_max", 7)
        if not c_min <= len(steps) <= c_max:
            errs.append(f"process_flow.steps count {len(steps)} not in {c_min}..{c_max}")
        t_max = caps.get("step_title_max", 30)
        b_max = caps.get("step_body_max", 140)
        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                errs.append(f"process_flow.steps[{i}] must be dict"); continue
            t = str(s.get("title", "")); b = str(s.get("body", "") or "")
            if len(t) > t_max:
                errs.append(f"process_flow.steps[{i}].title is {len(t)} chars (max {t_max})")
            if b and len(b) > b_max:
                errs.append(f"process_flow.steps[{i}].body is {len(b)} chars (max {b_max})")
    elif kind == "bar_chart":
        items = content.get("items", []) or []
        c_min = caps.get("items_count_min", 2)
        c_max = caps.get("items_count_max", 12)
        if not c_min <= len(items) <= c_max:
            errs.append(f"bar_chart.items count {len(items)} not in {c_min}..{c_max}")
        l_max = caps.get("item_label_max", 40)
        for i, it in enumerate(items):
            if not isinstance(it, dict): continue
            l = str(it.get("label", ""))
            if len(l) > l_max:
                errs.append(f"bar_chart.items[{i}].label is {len(l)} chars (max {l_max})")
    elif kind == "pie_chart":
        items = content.get("items", []) or []
        c_min = caps.get("items_count_min", 2)
        c_max = caps.get("items_count_max", 8)
        if not c_min <= len(items) <= c_max:
            errs.append(f"pie_chart.items count {len(items)} not in {c_min}..{c_max}")
        l_max = caps.get("item_label_max", 30)
        for i, it in enumerate(items):
            if not isinstance(it, dict): continue
            l = str(it.get("label", ""))
            if len(l) > l_max:
                errs.append(f"pie_chart.items[{i}].label is {len(l)} chars (max {l_max})")
        cv = str(content.get("center_value", "") or "")
        cl = str(content.get("center_label", "") or "")
        if cv and len(cv) > caps.get("center_value_max", 8):
            errs.append(f"pie_chart.center_value is {len(cv)} chars (max {caps['center_value_max']})")
        if cl and len(cl) > caps.get("center_label_max", 24):
            errs.append(f"pie_chart.center_label is {len(cl)} chars (max {caps['center_label_max']})")
    elif kind == "logo_grid":
        logos = content.get("logos", []) or []
        c_min = caps.get("logos_count_min", 2)
        c_max = caps.get("logos_count_max", 18)
        if not c_min <= len(logos) <= c_max:
            errs.append(f"logo_grid.logos count {len(logos)} not in {c_min}..{c_max}")
        n_max = caps.get("logo_name_max", 30)
        for i, lg in enumerate(logos):
            if not isinstance(lg, dict): continue
            n = str(lg.get("name", "") or "")
            if n and len(n) > n_max:
                errs.append(f"logo_grid.logos[{i}].name is {len(n)} chars (max {n_max})")
    elif kind == "icon_list":
        items = content.get("items", []) or []
        c_min = caps.get("items_count_min", 3)
        c_max = caps.get("items_count_max", 12)
        if not c_min <= len(items) <= c_max:
            errs.append(f"icon_list.items count {len(items)} not in {c_min}..{c_max}")
        t_max = caps.get("item_title_max", 30)
        b_max = caps.get("item_body_max", 100)
        for i, it in enumerate(items):
            if not isinstance(it, dict): continue
            t = str(it.get("title", "")); b = str(it.get("body", "") or "")
            if len(t) > t_max:
                errs.append(f"icon_list.items[{i}].title is {len(t)} chars (max {t_max})")
            if b and len(b) > b_max:
                errs.append(f"icon_list.items[{i}].body is {len(b)} chars (max {b_max})")
    return errs


def validate_plan(plan: Any) -> tuple[bool, list[str]]:
    """Validate a full SlideContentPlan. Returns (ok, error_messages)."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return False, ["plan must be a dict"]

    for f in ("slide_id", "topic", "blocks", "image_decision"):
        if f not in plan:
            errors.append(f"missing required field '{f}'")

    # Validate blocks list
    blocks = plan.get("blocks", [])
    if not isinstance(blocks, list):
        errors.append("blocks must be an array")
    else:
        if len(blocks) == 0:
            errors.append("blocks must have at least 1 entry")
        for i, b in enumerate(blocks):
            ok, errs = validate_block(b)
            if not ok:
                errors.extend([f"blocks[{i}]: {e}" for e in errs])

    # Validate image_decision
    img = plan.get("image_decision", {})
    if not isinstance(img, dict):
        errors.append("image_decision must be a dict")
    else:
        strat = img.get("strategy")
        if strat not in IMAGE_STRATEGIES:
            errors.append(
                f"image_decision.strategy must be one of {IMAGE_STRATEGIES}, "
                f"got {strat!r}"
            )

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Inspection helpers
# ---------------------------------------------------------------------------
def block_kinds_in(plan: dict) -> list[str]:
    """Return the ordered list of block kinds in a plan (for picker logic)."""
    return [b.get("kind") for b in plan.get("blocks", [])
            if isinstance(b, dict) and "kind" in b]


def has_block_kind(plan: dict, kind: str) -> bool:
    """Check if a plan contains at least one block of the given kind."""
    return kind in block_kinds_in(plan)


def list_block_kinds() -> list[str]:
    """Return all valid block kinds (for documentation)."""
    return sorted(CONTENT_BLOCK_SCHEMAS.keys())


# ---------------------------------------------------------------------------
# v4.0 — Phase 3 lift-image resolver (content-aware, not positional)
# ---------------------------------------------------------------------------
def resolve_lift_image(hint: str,
                       search_dir: str,
                       *,
                       prefix_filter: str | None = None,
                       min_confidence: float = 0.2,
                       allow_kinds: tuple[str, ...] = ("content",),
                       ) -> dict | None:
    """Pick the best lift-candidate image matching ``hint``.

    Replaces the positional heuristic (``matches[len(matches)//4]``) that
    Phase 5 of v3.x used to pick the 25th-percentile filename — which
    consistently selected icons / logos because those tend to be early
    in the PPTX media folder.

    Filters via ``source_ingester.classify_image_kind()`` so only files
    classified as ``content`` (or any kind in ``allow_kinds``) are
    eligible. Falls back to None when no candidate clears the bar.

    Args:
        hint:           free-text hint, e.g. "Olive Young dashboard
                        keyframe" or "MINISTOP app screenshot"
        search_dir:     directory to scan (relative paths resolve against
                        the current working directory)
        prefix_filter:  optional filename prefix glob (e.g.
                        ``"vti-group-retail-capability"``) to scope
                        the candidate set
        min_confidence: minimum classifier confidence to accept
                        (default 0.2 — the classifier is conservative
                        with content-class scoring; lower bar lets
                        mid-confidence content images through, while
                        kind!='content' images are still excluded)
        allow_kinds:    tuple of accepted ``kind`` values

    Returns:
        ``{"path": str, "natural_w": int, "natural_h": int,
           "kind": str, "confidence": float, "reasons": [str]}``
        on success, or ``None`` if no acceptable candidate.
    """
    from pathlib import Path
    # Lazy import to avoid circular dependency at module load
    from source_ingester import classify_image_kind  # noqa: PLC0415

    base = Path(search_dir)
    if not base.exists():
        return None

    glob_pat = f"{prefix_filter}*" if prefix_filter else "*"
    candidates = sorted(p for p in base.glob(glob_pat)
                        if p.is_file()
                        and p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if not candidates:
        return None

    hint_tokens = [t.lower() for t in hint.split()
                   if len(t) > 2 and t.isalnum()]

    best: tuple[float, Path, dict] | None = None
    for path in candidates:
        cls = classify_image_kind(path)
        if cls.get("kind") not in allow_kinds:
            continue
        if cls.get("confidence", 0.0) < min_confidence:
            continue
        # Score = classifier confidence + 0.1 per matching hint token
        score = float(cls.get("confidence", 0.0))
        fn = path.name.lower()
        for tok in hint_tokens:
            if tok in fn:
                score += 0.1
        if best is None or score > best[0]:
            best = (score, path, cls)

    if best is None:
        return None
    score, path, cls = best
    metrics = cls.get("metrics") or {}
    return {
        "path":        str(path),
        "natural_w":   int(metrics.get("width") or 0),
        "natural_h":   int(metrics.get("height") or 0),
        "kind":        cls.get("kind"),
        "confidence":  float(cls.get("confidence", 0.0)),
        "score":       float(score),
        "reasons":     cls.get("reasons", []),
    }
