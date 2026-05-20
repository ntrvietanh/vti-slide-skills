# vti-slide-creator — CHANGELOG

## v4.7.0 (2026-05-20) — Deliverable filename convention

New `deck_filename.py` module exports a single function:

    deck_filename(title, customer=None, version="1.0", ext="html")
        → "VTI{-Customer}_Title-Slug_vX.Y.ext"

Phase 6 drivers now write two artifacts: `work/deck-composed.html`
(canonical working file referenced by patches + decorator) and a
deliverable copy under the formula above. PPTX export inherits the
stem automatically. Title/customer slugifier strips Vietnamese
diacritics (ả→a, đ→d) so filenames stay ASCII-portable.

## v4.6.2 (2026-05-19) — Forward diagram captions to image-tile cell

`layout_designer._image_cell_props` accepts a new `captions: list[str] |
None` kwarg and adds it to the image-tile props dict when non-empty.
`design_slide_layout` reads `content_plan["diagram_spec"]["captions"]`
once and threads it through `_enumerate_candidates` →
`_candidate_banner` / `_candidate_aside` → `_build_banner_layout` /
`_build_aside_layout`. Phase 3 (CONTENT-PLAN) guidance in SKILL.md
updated with the action-label / captions-strip authoring contract
paired to diagram-builder v0.4.0.

### What changed

- **`layout_designer.py`** — six closures + builders extended with a
  `diagram_captions: list[str] | None = None` kwarg; default keeps
  the prop absent for non-synthesize slides (image-tile silently
  ignores it).
- **`SKILL.md`** — new "Content discipline" block under the
  `synthesize` strategy: bad / good examples, persisted
  `diagram_spec` shape includes `captions: list[str]`.
- **Bumped `__version__ = "4.6.2"`** in `creator.py`.

### Why

`vti-slide-diagram-builder` v0.4.0 added a steps-only authoring rule
(no metrics in node labels) and a parallel `captions` array. Without
this ripple, layout_designer never read the array and the page-builder
never saw it — the user-facing behaviour would have been "no metrics
appear anywhere", defeating the half of the user's request that asked
for the data to stay on the slide, just outside the diagram.

### Backwards-compat

`diagram_captions` is optional everywhere. Slides without a
`diagram_spec` (text-only, lift) skip the lookup entirely. Slides whose
`diagram_spec` predates v0.4.0 (no `captions` key) get `captions=[]`
and image-tile renders exactly as before.

---

## v4.6.1 (2026-05-10) — Square slide corners in deck shell

Removed `border-radius: 10px` from the `.slide` rule in the Phase-6
deck shell template (`creator.py` line ~466). Slides now render as
square-cornered rectangles on the pale-blue page background. Box-shadow
is preserved — the rounded card look is gone, the elevation cue stays.

User feedback: rounded corners on every slide read as presentation-app
chrome rather than a finished deck. Square corners match the printed /
exported look reviewers expect.

## v4.6.0 (2026-05-10) — Principle 10: Voice & tone (mandatory voice handshake at Phase 2)

Adds **Principle 10 — Voice & tone** to the design principles, plus a new
mandatory checkpoint inside Phase 2. Symptom that triggered this: review
of the StarHub deck showed narrative blocks written in analyst-notation
style (`Telco-AI peer experience — SK Telecom runs three live AI
programs with VTI today.`, `near-as-makes-no-difference`, `Day-1`,
`slideware`) that read as fragments rather than human speech and
quietly excluded readers who don't share the in-group jargon.

### What changed

1. **New mandatory voice handshake at Phase 2 close-out.** Before exiting
   Phase 2 ★ checkpoint into Phase 3 CONTENT-PLAN, the orchestrator
   MUST ask the user one question — pick a voice from
   `consultative-sales` (default) / `technical-deep` / `executive-brief` /
   `educational`, or describe their own. Answer is stored in
   `plan['voice']` and read by every Phase 3 narrative draft.

2. **Universal writing rules** that apply to ALL voices:
   - Full sentences, not telegraphic dash-stitched fragments.
   - Spell out compressed jargon in narrative (`edge→gateway→GPU spine`
     is fine on a diagram label, not in prose).
   - At most one em-dash interruption per sentence.
   - Avoid tribal compressions: `Day-1`, `slideware`, `mid-pivot`,
     `near-as-makes-no-difference` etc.

3. **Voice-specific tweaks** (pronouns, hedging, sentence length, jargon
   density) tabulated per voice for tactical writing decisions.

4. **Phase 6 enforcement spot-check** — REVIEW-AND-COMPOSE reads 3–5
   narrative blocks; if fragment-style or stacked-dash sentences slip
   through, bounce back to Phase 3 with the offending text quoted.

### Why this is a hard rule, not a soft guideline

Slides are read aloud or skim-read by sceptical execs. Spec-sheet prose
forces them to mentally re-inflate every fragment into a sentence —
extra cognitive work — and tribal jargon signals in-group knowledge they
may not share, which subtly excludes them from the conversation. Both
weaken the pitch. The voice handshake ensures the orchestrator and the
user are aligned BEFORE any drafting happens, instead of finding out at
review time that the whole deck reads in the wrong register.

## v4.5.0 (2026-05-10) — Flexible image+content split + correct canvas geometry

**Closes gaps #60, #61, #62, #63** — three structural layout bugs and a wrong-constants regression that produced sparse 54%-fill aside slides AND, in the v4.4-emergency banner-top fix attempt, content-overlap rendering.

### Gap #60 — wrong canvas constants (silent fill miscalc)
`layout_designer` had used `CONTENT_AREA_W_PX=1280` / `CONTENT_AREA_H_PX=620` / `COL_W_PX=106` since v4.0. The page-builder's actual content area is **1168 × 586** (after 56px LR padding + 70/64 top/bottom chrome) with **18px grid gap** and per-col width ≈ 80.83px. Every fill_pct estimate was 9–24% too optimistic, so banner-top heights computed at ~498px actually overflowed the real 586px area, getting visibly clipped at the slide bottom. Fixed: `CONTENT_AREA_W_PX = SLIDE_W_PX - 2 * CHROME_LR_PX` (1168), `CONTENT_AREA_H_PX = SLIDE_H_PX - CHROME_TOP_PX - CHROME_BOTTOM_PX` (586), explicit `GAP_PX = 18`, new `col_span_to_px(span)` helper that includes gap math.

### Gap #61 — rigid pattern selection
`design_slide_layout` picked exactly one of three patterns by aspect-ratio buckets (`stacked-top` ≥2.0, `side-by-side` 1.4-2.0, `tall-side` <1.4) with **fixed col_spans**: image always 8 in side-by-side, always 5 in tall-side, always 12 in stacked-top. For wide diagrams (aspect 2.57) packed beside features_3 cards, this produced 1+1+2-col cards (titles clipping: "AI DOCTO MATCH") and 200px+ of empty space inside the stretched image cell. Replaced with a **candidate-search designer**: enumerate banner-top, banner-bottom, and aside layouts at col_span 3..8 × {left, right} = 14 candidates per slide, score each on (image-vs-content-height mismatch + waste), pick the lowest-score viable candidate.

### Gap #62 — narrow right-column multi-cell blocks
Even-split inside a narrow column (`col_span // n`) gave practice-cards 1-col-wide slots when aspect picked side-by-side col_span=8. New `_layout_blocks_in_column(blocks, col_span)` stacks features_3 / values / catalog **vertically** when `col_span < n * MIN_HORIZONTAL_PER_ITEM` (3); horizontal split otherwise. Practice-card titles now have ≥3 cols (~278px) of width minimum.

### Gap #63 — image cell over-stretch with row_span
`_design_image_aside_stack` set `row_span = N` on the image cell, where N = total right-column rows — but if image natural rendered height was less than the right-column total, the cell stretched and the image only filled the top portion (object-fit:contain), leaving sparse empty space below. New aside builder: greedily pack right-column rows whose cumulative height stays close to image natural height; remaining rows fall to **full-width below** the aside section. Also: image-aside layouts now allow **image to shrink below natural pixel size** (cap at content-area height), letting portrait images render at usable widths instead of being rejected outright.

### New patterns
- `vertical-stack` — unchanged
- `image-banner-top` — wide image full-width row 1, content rows below
- `image-banner-bottom` — wide image full-width row N, content rows above (rare; only wins when explicitly better-scoring)
- `image-aside-{left,right}-{K}of12` — image one side at K∈{3,4,5,6,7,8} cols, content the other side; remainder full-width below if needed

### New helpers / API
- `col_span_to_px(span: int) -> int` — pixel width of a K-col cell including gaps
- `BLOCK_KIND_STACKED_ITEM_H: dict[str, int]` — per-item heights for vertically-stacked multi-cell blocks
- `_enumerate_candidates(...)`, `_candidate_banner(...)`, `_candidate_aside(...)`, `_layout_blocks_in_column(...)`, `_build_banner_layout(...)`, `_build_aside_layout(...)` — internal candidate-search machinery

### Sibling change: `vti-slide-diagram-builder` 0.1.0 → 0.2.0
`CANVAS_H_WIDE: 460 → 280` and `CANVAS_H_TALL: 600 → 480`. The old defaults padded ~150-200px of vertical whitespace below every flow / quadrant. New defaults size to roughly the minimum a primitive needs. Aspect of horizontal flow_diagram now ~4.21 (1180/280) instead of 2.57 — flatter banner that tucks naturally into `image-banner-top` slots without forcing aside fallback.

### Verification
| Test | Before | After |
|---|---:|---:|
| Slides at fill ≥ 70% | 19/26 | 26/26 |
| Validator errors | 0 | 0 |
| No-crop violations | 0 | 0 |
| Slides with low_fill warning | 7 | 0 |

### Migration
Plans from v4.4 still validate with v4.5 (schema unchanged). The new pattern names appear in `plan["pattern"]` strings. Drivers that pattern-match on legacy strings (`"image-side-by-side"`, `"image-tall-side"`, `"image-stacked-top"`) need updating to recognise `"image-aside-{side}-{K}of12"` and `"image-banner-{top,bottom}"`.

## v4.4.0 (2026-05-10) — Semantic image picker (Phase 3 protocol)

**Replaces**: the v4.0 `resolve_lift_image()` heuristic, which scored
candidates by classifier confidence + filename token match. Both
signals are structural — the picker selected the same
"highest-confidence content image per source" for every slide of a
multi-slide case study (Olive Young 1/3, 2/3, 3/3 all received
`frame-01.jpg`), and let semantically-irrelevant photos through
whenever their aspect ratio happened to look like content (VTI logo,
ISO/BCP cert badge, exec portraits leaked into SKT / Omron lift
candidates).

**New module**: `image_picker.py` — 4-step orchestrator-in-the-loop
protocol surfaced through six APIs:

- `enumerate_candidates(slide_plan, asset_index, source_tags=…,
  claimed_paths=…, top_k=15)` — top-K filename-scored candidates,
  excluding paths already claimed by other slides (best-fit
  enforcement).
- `get_caption()` / `set_caption(asset_index_path, image_path, caption)`
  — caption persistence so later slides reuse vision-model captions
  without re-inspecting.
- `record_image_decision(plan_path, slide_id, ImageDecision(...))` —
  atomic write of strategy + rationale + payload (resolved_image OR
  diagram_spec) into phase_3.json. Idempotent; clears stale
  payloads when the strategy changes.
- `ImageDecision` dataclass: `strategy` ∈ `{lift, synthesize,
  text-only}`, `rationale`, `resolved_image | diagram_spec`,
  `candidates_seen`.
- `allocate_case_study_images(slides_in_cs, ranked_per_slide)` —
  greedy 1-to-1 best-fit allocation across multi-slide case studies;
  escalates surplus slides to `None` (caller chooses synth or text).
- `build_worklist(plan_path, asset_index_path)` — batch enumerate
  candidates for every `strategy=lift` slide so the orchestrator can
  iterate.

**SKILL.md update**: new "Phase 3 image-decision protocol (v4.4 —
semantic, not heuristic)" section under Phase 3 documents the 4-step
loop (necessity check → enumerate → caption → decide+escalate) and the
multi-slide best-fit rule. Auto-escalation between `lift` /
`synthesize` / `text-only` happens without re-asking the user;
`rationale` is the audit trail.

`creator.py` re-exports the six image_picker APIs and bumps
`__version__` from `4.0.1` to `4.4.0`. `resolve_lift_image()` stays in
the public surface (back-compat, but content-blind — flagged in the
docstring as legacy).

## v4.3.0 (2026-05-10) — Layout-designer image-aside-stack pattern

**Bug fixed**: when a content slide had an image with aspect < 2.0
(`image-tall-side` or `image-side-by-side`), the layout-designer placed
only the first narrative beside the image and dropped every other
secondary block (kpi-row, list, features, etc.) into a full-width row
*below* the image. Result: empty space on the right of the image AND a
wasted strip below — visible in the StarHub deck the user composed
mid-session ("KPI row bị rơi xuống dưới trong khi phần bên phải còn
trống nhiều").

**Fix**: `_design_image_tall_side` and `_design_image_side_by_side` now
delegate to a new shared `_design_image_aside_stack` builder that emits
N rows with the image cell `row_span=N` so it stretches across all
right-column rows. Right-column blocks stack vertically beside the
image; nothing falls below it. Multi-cell block kinds
(`features_3` / `values` / `catalog`) split the right-column width
evenly via `_expand_block_for_right_column`.

`make_layout_cell` now accepts an optional `row_span` kwarg
(default 1; max 8 — page-builder validator).

Fill metric was also updated: `_estimate_fill_pct` short-circuits when
row 0 contains an image-tile cell with `row_span > 1` and uses the
image's natural rendered height instead of summing the
right-column-row estimates (which would undercount because the image
is what dominates the visual height).

Coordinates with page-builder v3.13.3 (which fixes a separate asset
path resolution bug surfaced by the same StarHub deck).

## v4.2.0 (2026-05-10) — Strict structural mandates (framing + precraft)

Two non-negotiable structural rules added to SKILL.md ("Strict rules —
VTI deck structural mandates"). Source of the rules: user correction
mid-session on the multi-vertical retail+healthcare deck.

**Rule A — Mandatory framing slides (Cover · TOC · Contact · Closing).**
Every deck MUST include all four, sourced from precrafted special-page
templates. Positions fixed: cover #1, toc #2, contact #(N-1),
closing #N. The retail+healthcare deck shipped with cover/toc/closing
but no contact slide — flagged as a structural failure.

**Rule B — VTI company-info topics route to precraft.** When a slide
is about VTI itself (company intro, awards, strategic partners,
PM methodology, QA, vision/mission, customer base, who-we-serve), the
slide MUST use one of the 8 precrafted special-page templates. Do not
hand-roll content slides for these topics. Customization scope is
prop-only — pass `intro_text`, customer counts, taglines, footnote, etc.,
but the layout and design system stay intact.

The retail+healthcare deck rebuilt About VTI, Awards, Partners, Domain
Mix, and Engagement Model as hand-rolled content slides — visually
adequate but drifting from the canonical VTI presentation. The user's
correction was unambiguous: "khi nói về VTI các thông tin cơ bản liên
quan đến cty / award / process tôi muốn bạn luôn luôn dùng các special
page precraft rồi và nếu cần thi thay đổi số hoặc nội dung từ slide
special page đó thôi (k tự tạo 1 slide mới hoàn toàn cho những thứ này)."

**Topic → special-page mapping:**

| Topic | Special page |
|---|---|
| About VTI | `about-vti` |
| Vision/Mission/Values | `vision-mission-values` |
| Customer base / domain mix | `who-we-serve` |
| Awards | `awards-certifications` |
| Partners | `strategic-partners` |
| PM methodology | `project-management-method` |
| QA activities | `quality-assurance` |
| Quality management process | `quality-management-process` |

**Rule C — Non-VTI-corporate topics still hand-roll.** Case studies,
technical capabilities (AI stack), specific project content, and
similar non-corporate-info slides continue to use `compose_slide_grid`
as before. The precraft mandate (Rule B) is scoped to the 8 corporate
topics only.

**Cross-skill contract:** none changed. The 8 special-page templates
already exist in `vti-slide-page-builder/special-pages/` and are
already exposed via `compose_special_page(name, props)`. v4.2.0 is a
discipline change in the creator, not a renderer change.

## v4.1.0 (2026-05-10) — Real video ingest (frames + whisper transcript)

Closes the v3.14 stub gap for video sources. Phase 1 can now ingest
`.mp4 / .mov / .webm / .m4v` directly — no more "video sampled 0
keyframes" outputs that forced the planner to drop the source.

**New helper — `ingest_video(video_path, frames_dir, ...)`** in
`source_ingester.py`:

- Resolves `ffmpeg` from system PATH first, then falls back to the
  `imageio-ffmpeg` bundled binary (so the skill works on machines
  without a system ffmpeg installed).
- Probes duration via `ffmpeg -i` stderr (no separate ffprobe needed).
- Samples keyframes at a configurable interval (`sample_seconds=20`,
  capped at `max_frames=12`), starting at 5 % of duration to skip the
  cold open. Each frame is auto-classified via `classify_image_kind`
  so the lift filter (Principle 9) runs on video frames the same way
  it runs on PPTX/PDF images.
- Extracts the audio track to a 16 kHz mono WAV temp file and
  transcribes via `faster-whisper` (CPU + int8 — works on Apple
  Silicon without CUDA). Default model is `small` (multilingual,
  ~466 MB); callers can pass `whisper_model='tiny'|'base'|'medium'`.
  Language is auto-detected unless a forcing ISO-639-1 code is passed.
- Returns the standard ingester dict shape with the transcript as
  `text`, frames as `assets[]`, and a `structure.transcript_segments`
  list (start/end/text) for downstream slot-by-slot citation.

`ingest_source(path)` now calls `ingest_video()` automatically when
the kind is `video` and ffmpeg is resolvable, with a graceful fallback
to the legacy `video_keyframes_stub()` when ffmpeg/whisper are
unavailable.

`creator` package surface adds `ingest_video` to its public re-exports.

**Why this lands now (v3.18.1 → v4.1.0):** the prior v4.0 ingest run
on the multi-vertical retail+healthcare deck dropped the SKT/Olive
Young BI Dashboard video entirely (no ffmpeg → no frames → no
narrative). User correction: a video that visibly contains the demo
of a live BI dashboard is exactly the kind of evidence content the
deck needs — the skill must be able to read it (frames + audio) the
same way it reads PPTX, not punt with a stub.

**Cross-skill contract:** none — this is a pure expansion of Phase 1
ingest. `COORDINATED_BASELINE.md` does not need an entry; the
ContextDoc shape is unchanged (text + assets + structure are the
same fields, just populated for video sources).

**New optional dependencies** (graceful-degradation guarded):
- `imageio-ffmpeg` — bundled ffmpeg static binary (no system install)
- `faster-whisper` — CTranslate2-backed whisper (smaller + faster
  than `openai-whisper` on CPU)

If neither is installed, `ingest_source()` returns the v3.14 stub
exactly as before — backward-compatible.

## v4.0.1 (2026-05-10) — Fix: deck preview shell owns its own card layout

Patch release. The Phase 6 driver (`scripts/build_phase_6.py`) was
hand-rolling its own deck-shell HTML wrapper around `compose_deck()`
output AND injecting a per-slide `<div class="deck-slide-num">NN</div>`
badge in the top-left of every slide via regex. Result: every composed
slide had a duplicate page number floating outside the chrome system
(the chrome footer chevron already shows the page number).

Root cause: the skill exposed a complete-page builder (`build_deck_html`)
since v3.17.1, but the driver did not use it — so it had to re-implement
the preview shell, and that hand-rolled implementation drifted in a
buggy direction.

### Fix

- `DECK_SHELL_DEFAULT` upgraded to the cards aesthetic the driver had
  evolved toward: 1280×720 fixed cards, 10px radius, deep blue-tinted
  drop shadow, pale-blue (#DAE9F6) page background, flex column with
  40px gap to prevent slide-N+1 chrome from overlapping slide-N footer.
- Inline guardrail comment in `DECK_SHELL_DEFAULT`: never inject a
  parallel per-slide number badge from the shell. The chrome footer
  already owns page numbering.
- `scripts/build_phase_6.py` now calls `build_deck_html(descriptors,
  title=…)` directly. Driver shrinks from ~120 lines (with regex
  injection + inline CSS) to ~45 lines. There is no longer a place for
  ad-hoc HTML mutation between `compose_deck` and disk-write.

### Files

- `creator.py` — `__version__` 4.0.0 → 4.0.1; `DECK_SHELL_DEFAULT`
  upgraded; comment block warning against per-slide badge injection.
- `scripts/build_phase_6.py` — rewritten to use `build_deck_html`.

---

## v4.0.0 (2026-05-10) — 6-phase pipeline · diagram skill integration · no-crop / fill guarantees

**MAJOR / breaking.** Splits Phase 5 (was: layout + component-pick) into
two distinct phases, merges P2+P3 (was: outline + review) into one,
adds new Phase 3 diagram-drawing step, and adds new Phase 6 review +
compose. Driver scripts of v3.19 are not source-compatible.

### Why

The v3.19 deck output (`work/deck-composed.html`, 42 slides) surfaced
three bugs whose root cause was structural:

1. **SVG diagrams cropped** — `make_image_cell()` set
   `aspect_ratio: "16:9"` while SVG viewBoxes were 1180×460 (≈2.56:1).
   `image-tile`'s `object-fit: cover` cut the right side. Phase 5
   could not fix this because diagrams were generated inside Phase 5
   with no feedback path back to layout decisions.
2. **Lift resolver picked junk** — the positional heuristic
   `matches[len(matches)//4]` consistently selected logo / icon images
   because those tend to be early in the PPTX media folder.
3. **Sparse layouts** — `pattern-b-image-narrative-side-by-side`
   placed image col_span=8 + narrative col_span=4 even when the image
   was small, leaving >30% empty bottom while content ran short.

v3.x architecture squashed layout-design + component-pick into one
phase, so none of the three bugs had a clean fix point.

### Phase structure (5 → 6)

| New | Was | Output |
|---:|---|---|
| 1 ANALYZE | 1 (unchanged) | ContextDoc |
| 2 PLAN-OUTLINE-AND-REVIEW | 2 + 3 (merged) | DeckOutline |
| 3 CONTENT-PLAN | 4 + diagram-draw | SlideContentPlan + diagram_spec + resolved_image |
| 4 LAYOUT-DESIGN (NEW) | (split from 5) | SlideLayoutPlan |
| 5 COMPONENT-PICK | 5 (rump) | render-ready slide_input |
| 6 REVIEW-AND-COMPOSE (NEW) | (new) | layout-review.html + deck-composed.html |

### What's new

- **`layout_designer.py`** (NEW) — Phase 4 module. `design_slide_layout`
  picks one of 4 patterns (vertical-stack / image-stacked-top /
  image-side-by-side / image-tall-side) based on the image's natural
  aspect ratio. Sets `image_cell_aspect == image_natural_aspect` so
  the cell never crops. Asserts ≥70% screen-fill via `layout_metrics`.
- **`SlideContentPlan` shape extended** — adds optional
  `diagram_spec` and `resolved_image` fields. Phase 3 populates them;
  Phase 4 reads `natural_w / natural_h` from them.
- **`resolve_lift_image(hint, search_dir, ...)`** in `content_drafter`
  — replaces the v3.x positional heuristic with content-aware filtering
  via `source_ingester.classify_image_kind()`. Junk icons, banners, and
  chrome strips are filtered out before reaching the deck.
- **New sibling skill `vti-slide-diagram-builder` v0.1.0** — 7 SVG
  primitives (flow_diagram, quadrant, footprint_map, layered_stack,
  fanout_pipeline, hybrid_swimlane, data_path). Standardised brand
  tokens, canonical viewBox, accessibility metadata. Phase 3 calls
  into this skill at synthesize time; the SVG is written to
  `work/diagrams/<slide_id>.svg` and the natural dimensions feed
  Phase 4. Replaces the ad-hoc `scripts/diagrams.py` of v3.19.

### Public API (additions)

- `creator.resolve_lift_image(hint, search_dir, *, prefix_filter, ...)`
- `creator.design_slide_layout(content_plan)`
- `creator.validate_layout_plan(plan)`, `creator.layout_metrics(plan)`
- `creator.make_layout_row`, `creator.make_layout_cell`,
  `creator.make_layout_plan`
- Constants `SLIDE_W_PX`, `SLIDE_H_PX`, `CONTENT_AREA_W_PX`,
  `CONTENT_AREA_H_PX`

Changed:
- `make_slide_content_plan(...)` accepts `diagram_spec=None` and
  `resolved_image=None` kwargs.

### Migration

This is a development-test repo with no production users; the v3.19
driver scripts under `scripts/` have been rewritten in place. External
consumers must update Phase 4 / Phase 5 calls — see SKILL.md for the
new pipeline contract.

---

## v3.19.0 (2026-05-10) — Coordinated 3-skill baseline · gap #42 · density_mode propagation

Minor release. Closes gap #42 (audit framework block→cell mismatch
surfaced by v3.18.1 rerun) and lands the creator side of the
coordinated 3-skill baseline. **No breaking changes** — all v3.18.x
audit calls keep working.

This release lands together with:
- vti-slide-page-builder v3.13.0 (mode-aware fill thresholds)
- vti-slide-decorator v0.5.0 (W3.6 pipeline implemented)

### `audit_plan_density` — auto-expansion (gap #42)

The pre-v3.19 audit assumed 1 block = 1 cell. But
``plan_to_slide_input`` expands ``features_3`` (1 block) into 3
practice-card cells, ``values`` into 4-6 medallions, ``catalog`` into
2-3 columns. v3.18.1 hand-rolled harnesses summed all sub-cells' chars
into one cell, false-flagging slides as OVERFLOW (s07-tech 121%,
s14-telehealth 171% in v5 plans were both harness artifact).

v3.19 introduces ``expand_plan_for_audit(plan)`` that walks the plan,
producing ``(expanded_blocks, expanded_layout)`` where each card /
value / column gets its own pseudo-block with just that item's chars,
mapped to the correct ``(component, span)`` cell.

```python
from creator import expand_plan_for_audit, audit_plan_density

# v3.19 ergonomic call — pass plan only, audit auto-expands
audit = audit_plan_density(plan)

# Or supply an explicit layout in legacy 1:1 mode
audit = audit_plan_density(plan, layout=[(comp, span), ...], expand=False)
```

``audit_deck_density`` likewise accepts a bare plan list (auto-expand)
or a list of (plan, layout) tuples (legacy):

```python
from creator import audit_deck_density
result = audit_deck_density(plans)                       # v3.19 ergonomic
result = audit_deck_density(plans_with_layouts)          # legacy form
```

### Pseudo-block kinds

The auto-expander emits three pseudo-kinds:

| Pseudo kind | Origin | Cell shape |
|---|---|---|
| `features_3_card` | one card from features_3.cards | (practice-card, span=4) |
| `values_item` | one item from values.items | (value-medallion, span=3) |
| `catalog_item` | one item from catalog.items | (catalog-column, span=6) |

Each pseudo-block carries ``_origin_block_idx`` and ``_origin_kind``
back-references so callers can map audit results back to the original
plan structure.

### `slide_meta.density_mode` propagation (gap #32 wiring)

``plan_to_slide_input`` now writes ``density_mode`` into the
``slide_meta`` dict it builds. The page-builder v3.13.0 reads this
field in ``compose_slide_grid`` and passes it through to
``_validate_fill_honesty`` so render-time warnings use the same
thresholds as Phase 4 audits. Pre-v3.19 the creator's density mode
was ignored at compose time — this closes the loop.

```python
plan['density_mode'] = 'sparse-ok'
slide_input = plan_to_slide_input(plan)
# slide_input['slide_meta']['density_mode'] == 'sparse-ok'
# Page-builder will use sparse-ok thresholds (sparse@20% instead of 40%)
```

Defaults to `'standard'` when the plan doesn't declare a mode —
backward-compatible with pre-v3.19 plans.

### Re-audit comparison on plans_v5

| | v3.18.1 | v3.19.0 |
|---|---|---|
| Audit call | `audit_deck_density([(p, derive_layout(p)) for p in plans])` | `audit_deck_density(plans)` |
| OVERFLOW slides | 2 (harness artifact) | 0 (real signal) |
| SPARSE slides | 3 | 3 (same — these are real) |
| Clean slides | 5 | 5 |
| s07-tech flag | OVERFLOW 121% (false) | THIN×2 60% (real per-card 44-52%) |
| s14-telehealth flag | OVERFLOW 171% (false) | ok 56% |

### Smoke tests

| Test | Result |
|---|---|
| `info()['version'] == '3.19.0'` | ✓ |
| `expand_plan_for_audit` on s07-tech: 2 blocks → 4 pseudo-blocks | ✓ |
| `audit_deck_density(plans_v5)` zero false OVERFLOW | ✓ |
| `slide_meta.density_mode` propagated through `plan_to_slide_input` | ✓ |
| All v3.18.x audit calls still work | ✓ |
| `validate_for_compose(plans_v5)` ok=True | ✓ |
| `audit_visual_balance(plans_v5)` flag=ok | ✓ |
| `audit_block_distribution(plans_v5)` no anti-patterns | ✓ |

### Surface-area audit — 33 helpers

Added since v3.18.1:
- `expand_plan_for_audit(plan)` → (expanded_blocks, expanded_layout)

### Migration from v3.18.x

Zero breaking changes:

1. Replace `audit_deck_density([(p, derive_layout(p)) for p in plans])`
   with the simpler `audit_deck_density(plans)`. The legacy tuple form
   still works.
2. To use density modes end-to-end, set `plan['density_mode']` once at
   Phase 4. Audits, drafting targets, and page-builder warnings will
   all pick it up.
3. Existing plans without `density_mode` default to `'standard'` —
   no migration needed.

### Remaining gaps (deferred)

| # | Gap | Reason deferred |
|---:|---|---|
| 43 | `select_strategy` in decorator currently uses section bias only — could also use slide content keyword scan | Decorator v0.6 enhancement |

(All v3.17.1 deferred gaps now closed. #32 is fully closed by the
coordinated baseline; #42 is closed by this release.)

---

## v3.18.1 (2026-05-10) — Fix stale _VISUAL_FILL_KINDS in density audit

Patch release. Fixes a v3.16 leftover bug surfaced when `audit_plan_density`
was rerun on plans_v5 with the new `audit_block_distribution` lens: 11 of
14 audited slides were false-flagged SPARSE because the audit measured
visual blocks (process_flow, bar_chart, pie_chart, logo_grid, icon_list,
image_tile, values, catalog, comparison_divider) as text-density, then
saw their short text payloads (step labels, axis labels, captions) and
concluded the cells were nearly empty.

### Root cause

When v3.16 promoted nine new block kinds to first-class visual blocks
in `capacity.VISUAL_BLOCK_KINDS`, the audit's local set
`cross_phase._VISUAL_FILL_KINDS = {"hero_stat", "supporting_stats"}`
was not updated. The two sets diverged. Pre-v3.18.1 the audit treated
everything except hero_stat/supporting_stats as text-density.

### Fix

`_VISUAL_FILL_KINDS` now matches `capacity.VISUAL_BLOCK_KINDS`
exactly:

```python
_VISUAL_FILL_KINDS = {
    "hero_stat", "supporting_stats",
    "process_flow", "bar_chart", "pie_chart",
    "logo_grid", "icon_list", "image_tile",
    "values", "catalog", "comparison_divider",
}
```

`_TEXT_DENSE_KINDS` shrinks correspondingly to `{"narrative", "list",
"features_3"}` — the only kinds where char-count meaningfully measures
fill. (`features_3` has card-grid structure but its 3 cards carry
~220-char body each, so it stays text-density; per-card caps are
enforced separately by validate_block.)

### Caveat for icon_list / values / catalog

These have text payload per item. Treating them as visual-fill is the
conservative choice for the audit — its job is to detect "this slide
will look empty", and an icon row visually fills its cell regardless
of caption length. Per-item char limits remain enforced by
`validate_block` (those caps haven't changed).

### Re-audit comparison on plans_v5

| | v3.18.0 (stale set) | v3.18.1 (synced) |
|---|---|---|
| SPARSE flags | 11 (false positives) | 3 (real, borderline) |
| OVERFLOW flags | 2 (mostly real) | 2 (harness artifact — see deferred) |
| Slides cleanly OK | 1 | 5 |

### Newly surfaced gap (deferred to v3.19+)

The rerun also exposed a structural mismatch between
`audit_plan_density` and the Phase 4→5 bridge:

- `audit_plan_density` requires `len(blocks) == len(layout)` (1:1).
- `plan_to_slide_input` expands `features_3` (1 block) into 3
  practice-card cells, `values` into 4-6 medallions, `catalog` into
  2-3 columns.

Hand-built audit harnesses for v5 plans flatten the bridge's output
to one cell-per-block (picking a "representative cell"), which
overstates char-density for these expansion kinds. The 2 OVERFLOW
flags on `s07-tech` and `s14-telehealth` in the v3.18.1 rerun are
harness-induced — per-card char counts on those slides are 36-47% of
cap, well within budget.

**Open gap** (not in v3.17.1 deferred list — surfaced by v3.18 audits):

- `#42` Audit framework assumes 1 block = 1 cell. Visual-expansion
  block kinds (features_3, values, catalog) need either (a) audit
  harness that expands them when deriving layout, or (b) per-kind
  char-budget transformation in `_block_text_chars` (split features_3
  total across 3 cells before computing fill).

Defer to v3.19. Workaround for now: when auditing decks with these
kinds, build the layout list with the expanded cell shape (e.g.
`('practice-card', 4)` ×3 per features_3 block) and pass each card's
own content through a per-card SlideContentPlan stand-in.

### Smoke tests

| Test | v3.18.0 | v3.18.1 |
|---|---|---|
| `validate_for_compose(plans_v5)` ok | ✓ | ✓ |
| `audit_visual_balance(plans_v5)` flag=ok | ✓ | ✓ |
| `audit_block_distribution(plans_v5)` no anti-patterns | ✓ | ✓ |
| `audit_deck_density(plans_v5)` SPARSE count | 11 | 3 |
| `audit_deck_density(plans_v5)` clean slides | 1 | 5 |

### Migration from v3.18.0

Zero breaking changes. Existing audit calls produce **fewer** SPARSE
flags (less noise). If a CI script previously asserted exact SPARSE
counts on a deck, update those assertions.

---

## v3.18.0 (2026-05-10) — Closes deferred gaps from v3.17.1 baseline

Additive minor release. No new design principles. Closes the six gaps
that v3.17.1 explicitly deferred as LOW-priority / philosophical /
architectural. New public surface: 4 new helpers, 1 new optional field,
1 new optional param on an existing helper. **Backward compatible** —
plans/outline/context_doc data from v3.14-v3.17.1 work unchanged.

### New helpers (4)

| Helper | Closes | Module |
|---|---|---|
| `audit_block_distribution(plans)` | #22 | cross_phase |
| `sources_for_section(doc, section)` | #5 | context_doc |
| `classify_image_kind(path)` | #6 | source_ingester |
| `cell_target_mode(component, span, density_mode)` | #23/#32 | capacity |

Plus `DENSITY_MODES` table + `density_mode_for(name)` lookup.

### `audit_block_distribution(plans)` — closes gap #22

Per-deck block-kind census + anti-pattern detection. Complementary to
v3.16's `audit_visual_balance`: that audits *slide* visual ratio, this
audits *block* distribution. Both can pass while a deck still feels
monotone (e.g. 50/50 narrative + image_tile = visual ratio passes but
every image slide looks identical).

```python
from creator import audit_block_distribution
dist = audit_block_distribution(plans)
# {
#   'total_blocks':       41,
#   'kinds_used':         10,
#   'visual_block_pct':   68.3,
#   'visual_kinds':       {'hero_stat': 7, 'supporting_stats': 8, ...},
#   'text_kinds':         {'narrative': 11, 'features_3': 2},
#   'dominant_kind':      None,                # (kind, count, pct) if >50%
#   'anti_pattern_flags': [],                  # see below
#   'recommendations':    [],
# }
```

Anti-pattern flags detected:
- `dominant_kind_overuse` — one kind > 50% of blocks (configurable)
- `all_text_blocks` — 0 visual blocks
- `no_charts` — 0 bar_chart/pie_chart blocks
- `no_process_flows` — 0 process_flow blocks (advisory)
- `narrative_heavy` — narrative > 40% of all blocks

Run alongside `audit_visual_balance` between Phase 4 and Phase 5.

### `sources_for_section(doc, section)` — closes gap #5

The v3.14 multi-source ContextDoc gave each source a `summary` but no
section mapping. Phase 4 had to infer "which source feeds RETAIL CASES?"
from the flat `source_summary` text — error-prone when one source
covers multiple sections (the retail PPTX in this session covered both
ABOUT VTI and RETAIL CASES).

v3.18 adds an optional `sections: list[str]` field on each source
record. Schema unchanged for callers not using it (backward compatible).

```python
ctx = make_context_doc(
    audience='CTO', purpose='capability profile', tone='executive-brief',
    sources=[
        {'label': 'Retail PPTX', 'kind': 'pptx', 'path': '/x/retail.pptx',
         'sections': ['ABOUT VTI', 'RETAIL CASES']},
        {'label': 'Medical PPTX', 'kind': 'pptx', 'path': '/x/med.pptx',
         'sections': ['MEDICAL CASES']},
    ],
)
retail_sources = sources_for_section(ctx, 'RETAIL CASES')
# [{'label': 'Retail PPTX', ...}]
```

Match is case-insensitive. Sources without a `sections` field never
match — Phase 1 must annotate.

### `classify_image_kind(path)` — closes gap #6

Heuristic content/chrome/stock/unknown classifier for extracted PPTX
images. Closes the v5 trap: pre-v3.18 build scripts picked images by
file size (largest = most substantive); 4 of 6 lifted images turned
out to be chrome (largest images in a deck are usually full-bleed
section banners, not content screenshots).

Signals used (with PIL/Pillow available — falls back to filename + size
otherwise):

- **Aspect ratio**: 16:9 close → chrome / banner; extreme wide or tall
  → chrome strip; square-ish or phone-shaped → likely content
- **File size**: <30 KB → likely icon/logo; >2 MB + 16:9 → strong
  chrome signal
- **Filename tokens**: `bg/banner/divider/cover/footer` → chrome;
  `screenshot/mockup/dashboard/architecture/diagram/frame_` → content;
  `logo/icon` → chrome (in lift-decision sense)

```python
from creator import classify_image_kind
cls = classify_image_kind('/path/to/image123.png')
# {'kind': 'chrome', 'confidence': 0.80,
#  'reasons': ['small file (15965B) — likely icon/logo',
#              'filename suggests icon/logo'],
#  'metrics': {...}}
```

Or wire it into extraction with the new `auto_classify=True` flag on
`extract_pptx_images`:

```python
assets = extract_pptx_images(pptx, out_dir, auto_classify=True)
# Each asset now carries kind_guess, confidence, classify_reasons.
content_candidates = [a for a in assets if a['kind_guess'] == 'content']
```

The classifier is a **pre-screen, not a substitute for visual
inspection** (Principle 9 still applies). Its job is to filter out the
obvious so visual inspection is reserved for real candidates.

### `make_image_decision` — `available_assets` param (closes gap #21)

Pre-v3.18, `make_image_decision('lift', source_hint='retail/p4 group photo')`
only validated source_hint when it looked like a literal path. A
non-path hint sailed through validation even when no asset with that
caption existed.

v3.18 adds `available_assets: list[dict] | None`. When supplied with
a non-path hint, the hint is fuzzy-matched against each asset's
`caption` and `path` basename. No match → `ValueError`. On match, the
returned dict gets a `matched_asset_path` field so Phase 5 can route
directly without re-fuzzy-matching.

```python
from creator import make_image_decision
dec = make_image_decision(
    'lift',
    source_hint='retail/p4 group photo',
    available_assets=context_doc['source_assets'],
)
# {'strategy': 'lift', 'reason': '...', 'source_hint': '...',
#  'matched_asset_path': '/extracted/retail/p4_group_photo.png'}
```

Tokens are split on `/`, whitespace, dashes, underscores. Tokens of
length ≤2 are skipped (filters noise like 'a', 'of').

### Density modes — closes gap #23 (and creator-side scope of gap #32)

Pre-v3.18, density bands were hardcoded: cell SPARSE <50% / OK 70-100%
/ OVERFLOW >100%; slide SPARSE-avg <40% / OVERCROWDED-avg >110%. Hero
slides, breathing-room covers, and dense spec-sheet slides all
false-flagged.

v3.18 introduces three named profiles in `capacity.DENSITY_MODES`:

| Mode | target_ratio | bands (sparse,ok-low,ok-high,overflow) | slide-avg sparse | slide-avg overcrowded | Use for |
|---|---|---|---|---|---|
| `standard` | 0.85 | 50, 70, 100, 100 | 40 | 110 | default — typical decks |
| `sparse-ok` | 0.65 | 25, 45, 100, 105 | 20 | 110 | hero / breathing / quote / single-stat-focal |
| `dense` | 0.95 | 60, 80, 110, 115 | 55 | 120 | spec sheets / technical detail / dense legibility decks |

API plumbing:

```python
# Per-call:
audit_plan_density(plan, layout, density_mode='sparse-ok')
audit_deck_density(plans_with_layouts, density_mode='dense')

# Per-plan (overrides deck-level):
plan['density_mode'] = 'sparse-ok'
audit_deck_density([(plan, layout)])  # picks up plan-level override

# Drafting target:
cell_target_mode('narrative-paragraph', 7, density_mode='sparse-ok')  # → 364
cell_target_mode('narrative-paragraph', 7, density_mode='dense')      # → 532
```

**Scope reduction note (gap #32 architectural)**: the original gap was
"density-mode toggle requires page-builder schema cap relaxation". The
v3.18 implementation covers the **creator side** only — drafting
targets and audit thresholds. The page-builder's render-time
`BLOCK_KIND_CAPS` hard caps are NOT relaxed — those are absolute
invariants enforced at compose. Thus `dense` mode draws to 95% of
declared cell capacity but cannot exceed `narrative.paragraphs_each_max=400`.
A future v3.19+ release could coordinate with vti-slide-page-builder
to introduce mode-aware hard caps; this is deferred and called out in
the docstring of `DENSITY_MODES`.

### Smoke tests pass

| Test | Result |
|---|---|
| `audit_block_distribution(plans_v5)` returns sensible 8 visual + 2 text kinds | ✓ |
| `sources_for_section` matches case-insensitively, returns [] for missing | ✓ |
| `classify_image_kind` correctly flags <30KB icons as chrome | ✓ |
| `make_image_decision(available_assets=...)` raises on hint miss | ✓ |
| `density_mode='sparse-ok'` re-classifies 62.5%-fill cell from thin → ok | ✓ |
| Existing `validate_for_compose(plans_v5)` still passes ok=True | ✓ |
| Existing `audit_visual_balance(plans_v5)` still passes flag=ok | ✓ |
| `creator.info()['version'] == '3.18.0'` | ✓ |

### Surface-area audit — 32 helpers (was 26)

New since v3.17.1:
- `audit_block_distribution`
- `sources_for_section`
- `classify_image_kind`
- `cell_target_mode`
- `density_mode_for`
- `DENSITY_MODES`

### Migration from v3.17.x

Zero breaking changes:

1. All v3.17.x calls still work as-is (new params have defaults).
2. To use density modes, add `'density_mode': 'sparse-ok'` to specific
   plan dicts or pass `density_mode='dense'` to `audit_*` calls.
3. To benefit from gap #6 image classification, pass
   `auto_classify=True` to `extract_pptx_images` — assets get extra
   fields, existing fields untouched.
4. To benefit from gap #5 multi-source section mapping, add
   `'sections': [...]` to each source record in `make_context_doc`.

### Gaps closed since v3.17.1 (cumulative)

| # | Gap | Closed in |
|---:|---|---|
| 5 | Source-summary not section-aware | **v3.18.0** |
| 6 | No image-extraction validation | **v3.18.0** |
| 21 | `source_hint` not validated against assets | **v3.18.0** |
| 22 | No deck-wide block stat | **v3.18.0** |
| 23 | 70-90% density band tight | **v3.18.0** |
| 32 | No density-mode toggle (creator-side scope) | **v3.18.0** |

### Remaining gaps (deferred)

| # | Gap | Reason deferred |
|---:|---|---|
| 32 (page-builder side) | Hard render caps still mode-agnostic | Cross-skill change — needs vti-slide-page-builder coordination |
| 42 | audit_plan_density 1-block=1-cell mismatch with features_3/values/catalog expansion | Surfaced by v3.18.1 rerun — see v3.18.1 entry |

---

## v3.17.1 (2026-05-09) — Baseline consolidation

Stabilization release. No new principles — closes residual runtime gaps
that surfaced during v3.14–v3.17 iterations and packages the skill as a
clean baseline. After this release, the skill is internally consistent:
every helper is re-exported, every block kind validates clean, every
runtime error from this session is caught at validation time.

### `creator.build_deck_html()` — closes gap #33

A complete, ready-to-write HTML document from a list of slide_inputs:

```python
from creator import build_deck_html
html = build_deck_html(slides, title=doc_title)
open('/tmp/deck.html', 'w', encoding='utf-8').write(html)
```

Wraps `composer_grid.compose_deck()` output (which returns `{deck_html,
slide_htmls, deck_css, slide_metadatas}`) in a full DOCTYPE + `<html>` +
`<head><style>` + `<body>` shell. The default shell uses VTI-friendly
page styling (light gray background, centered slides, drop shadows).
Pass a custom `shell` template for non-VTI rendering contexts.

Without this helper (the pre-v3.17.1 state), callers had to manually
concatenate `deck_html + deck_css` in a hand-written DECK_SHELL — and
forgetting to do it produced an unstyled HTML file showing only the
raw slide divs. The v3.16 first-deck delivery hit exactly this bug.

### `content_drafter._check_enums()` — catches render-time enum errors

Adds a value-domain (enum) validator that runs after `_check_caps()`
inside `validate_block`. Catches the class of errors where a block
satisfies length-caps but violates the rendering component's enum
constraints:

```python
make_block('hero_stat', {'value': '1,800+', 'label': 'Engineers',
                          'decoration': 'EST. 2017'})
# Pre-v3.17.1: validate_block returns ok=True; render_component raises
# ValidationError at Phase 5 because decoration must be 'rings' or 'none'.
# v3.17.1: validate_block returns ok=False with clear error.
```

Enum table (`BLOCK_KIND_ENUMS`) covers:

| Kind | Field | Allowed values |
|---|---|---|
| `hero_stat` | `decoration` | rings · none |
| `logo_grid` | `tone` | color · monochrome · muted |
| `icon_list` / `list` | `density` | compact · default · loose |
| `process_flow` | `direction` | horizontal · vertical |
| `bar_chart` | `orientation` | vertical · horizontal |
| `image_tile` | `frame` | none · rounded · shadow · polaroid |
| `image_tile` | `caption_position` | below · overlay-bottom · overlay-top |

Keep this table in sync with `composer_grid` whenever rendering enums
change. (We hit two such errors during the v3.16 build:
`decoration='EST. 2017'` and `tone='mono'`.)

### Smoke tests pass

End-to-end pipeline verified:

| Test | Result |
|---|---|
| `validate_block` · all 14 block kinds | ✓ all clean |
| Enum validation catches bad `decoration`, `tone`, `density`, `direction` | ✓ caught at Phase 4 |
| `build_deck_html` produces complete HTML (DOCTYPE + html + style + body) | ✓ 106KB minimal deck |
| Image layout patterns A / B-side / B-fullwidth route correctly | ✓ all 3 patterns |
| Existing v5 plans still compose ok=True flag=ok | ✓ 16 plans · 21 slides |

### Surface-area audit

26 expected helpers verified present on `creator`:

- Phase 4 drafting: `make_block`, `make_image_decision`,
  `make_slide_content_plan`, `validate_block`, `validate_for_compose`,
  `split_long_paragraphs`, `CONTENT_BLOCK_SCHEMAS`
- Phase 5 composition: `plan_to_slide_input`, `build_deck_html`,
  `compose_slide_grid`
- Capacity model: `cell_capacity`, `cell_target`,
  `layout_sketch_capacity`, `BLOCK_KIND_CAPS`
- Audits: `audit_plan_density`, `audit_deck_density`,
  `audit_visual_balance`, `deck_density_summary`, `is_visual_block`,
  `VISUAL_BLOCK_KINDS`, `TEXT_BLOCK_KINDS`
- Phase 1-2: `make_context_doc`, `make_deck_outline`,
  `make_slide_outline_entry`, `render_outline_table`,
  `renumber_slide_ids`, `extract_pptx_images`, `video_keyframes_stub`

### Gaps closed since v3.13.1 (cumulative)

| # | Gap | Closed in |
|---:|---|---|
| 1 | Video unsupported in source ingester | v3.15 |
| 2 | No PPTX image extractor | v3.15 |
| 3 | ContextDoc single-source only | v3.15 |
| 4 | Multi-source disambiguation | v3.15 |
| 7 | DeckOutline schema missing v3.4 fields | v3.15 |
| 8 | No `render_outline_table` | v3.15 |
| 11 | Weak structural validation | v3.15 |
| 13 | `add_slide` 0-indexed footgun | v3.15 |
| 14 | Numeric `slide_id` prefix | v3.15 |
| 15 | Section continuity not checked | v3.15 |
| 17-19 | Visual-vs-text density not measured | v3.14 |
| 24 | First-class density audit | v3.14 |
| 27 | Capacity model 2.5× mismatch | v3.14 |
| 28 | `plan_to_slide_input` ignored block order | v3.14 |
| 29 | No schema-cap validation | v3.14 |
| 30 | No cross-phase validator | v3.14 |
| 31 | No paragraph splitter | v3.14 |
| 33 | `compose_deck` doesn't return complete HTML | **v3.17.1** |
| 34 | Phase 4 missing visual block kinds | v3.16 |
| 35 | No deck-wide visual balance audit | v3.16 |
| 36 | Anti-stacking rule for fixed-header components | v3.16 |
| 37 | Phase 2 didn't surface visual options | v3.16 |
| 38 | Pre-lift image inspection not enforced | v3.17 |
| 39 | Default vertical-stack compresses dense images | v3.17 |
| 40 | No image layout pattern selection | v3.17 |
| 41 | Enum errors slipped past validate_block | **v3.17.1** |

### Remaining gaps (deferred — non-blocking)

- #5 Source-summary not section-aware (LOW)
- #6 No image-extraction validation (LOW)
- #21 `source_hint` not validated (LOW)
- #22 No deck-wide block stat (LOW)
- #23 70-90% density band tight (philosophical)
- #32 No density-mode toggle (architectural — requires page-builder
  schema cap relaxation)

### Migration from earlier versions

If you have v3.14-v3.17 plans/slides:

1. Re-run `validate_for_compose(plans)` — v3.17.1 enum check may flag
   previously-passing-but-unrenderable values (`decoration='EST. 2017'`,
   `tone='mono'`). Fix per the enum table above.
2. Replace any manual `compose_deck + DECK_SHELL` wrapping with
   `build_deck_html(slides, title=...)`.
3. Re-render. No plan/outline schema changes — old data structures
   work as-is.

## v3.17.0 (2026-05-09) — Image content awareness & fit (Principle 9)

User feedback after v3.16 deck: of 6 images I lifted from sources, 4
were chrome (divider banners, decorative chevrons) or stock photos
(generic skyscrapers, hands-on-tablet stock images), not message-bearing
content. The 2 actual content images (Omron architecture, Olive Young
dashboard) were compressed below readability under vertical row stacks
(image at small size between text + stat rows, critical edges cropped).

User's verdict:
> *"các hình bạn cut ra nó thể hiện 1 thông tin cụ thể và đâu thể bị
> crop như vậy được... bạn đang làm phần đưa hình vào này 1 cách
> chống chế để fill screen chứ k phải để phục vụ mục đích trình bày
> slide"*
> (Translation: extracted images convey specific information and can't
> be cropped like that. You're doing image-insertion perfunctorily to
> fill screen, not to serve slide presentation.)

The pre-v3.17 skill defaulted to:
1. Pick lift-image by file size (largest = most substantive). **Wrong.**
   Source PPTX largest images are often high-res chrome graphics
   (banner photos composited inside triangular branded frames, 1-3 MB
   each). They were placed in source for visual flow, not message.
2. Place lifted images in a default vertical stack (image row + text
   row + stat row). **Wrong** for dense diagrams: shrinks the image
   below readable size, often crops content at right/bottom edges.

### `SKILL.md` — new Principle 9

Added **Principle 9 · Image content awareness & fit**. Defines:

- **Pre-lift inspection mandatory.** Visually classify each candidate:
  - `content` (diagram, screenshot, chart, infographic, branded UI) → lift
    if message-relevant
  - `chrome` (divider banner, decorative shape, branded triangle/wedge)
    → NEVER lift
  - `stock` (generic photo: skyscrapers, tablets, networks, executives)
    → NEVER lift
- **3 questions for each candidate**: what does it show, does it match
  THIS slide's message, what's natural aspect + minimum readable size?
- **No suitable image → don't force one.** Use process-flow / chart /
  custom SVG / accept content-dominant layout. Never grab any image to
  satisfy "Principle 8 visual quota".
- **Two layout patterns only**:
  - **Pattern A — content-first with supporting image**: content
    dominates ≥60%; image is small support (~30-40% width or small hero
    block); image conveys mood/context, not detail
  - **Pattern B — image-first with supporting content**: image
    dominates ≥60-70% (side-by-side or full-width); content arranged
    beside or under, never above; reader must be able to read text in
    the image
- **Forbidden anti-patterns**: image-cropped-by-cell, compressed-image-
  under-text-stack, decorate-to-fill, cropped-edge content
- **Phase 2 outline `visual_strategy` extended**: `image-lift:pattern-a`
  / `image-lift:pattern-b` / `image-lift:full-width`

### `content_drafter.make_slide_content_plan()` — `layout_hint` field

New optional kwarg routes Phase 5 to a specific image layout instead of
the default vertical stack:
- `"pattern-a-content-first"` → narrative col_span=8 + image col_span=4
- `"pattern-b-image-narrative-side-by-side"` → image col_span=8 +
  narrative col_span=4 + stats below as full-width band
- `"pattern-b-full-width-image"` → image col_span=12 1fr (large hero) +
  narrative auto + stats auto stacked below
- `""` (empty) → default vertical stack (one block per row)

### `creator._compose_image_layout()` — pattern routing

When `plan.layout_hint` is set AND plan has `image_tile` block,
`plan_to_slide_input` delegates to `_compose_image_layout` which builds
the corresponding row/cell structure.

### Migration

For decks built under v3.16 that have lifted images:
1. **Visually inspect each lifted image.** If chrome or stock → drop.
2. For chrome/stock-replaced slides: use process-flow, chart, custom
   SVG, or content-dominant layout.
3. For real content images: choose pattern A or B based on whether the
   image is supporting or focal.
4. Set `layout_hint` on the plan to route to the correct pattern.
5. Re-render.

### Gaps resolved

- #38 — Pre-lift image inspection not enforced (file-size heuristic
  picked chrome/stock as "substantive")
- #39 — Default vertical-stack layout compresses dense images below
  readable size
- #40 — No layout pattern selection mechanism (Pattern A vs B) for
  image-bearing slides

## v3.16.0 (2026-05-09) — Visual + content balance is mandatory (Principle 8)

User feedback after seeing the first deck: 13 of 16 content slides used
`narrative + supporting_stats` or stacked `features_3`. Slide 06 had
3×features_3 = 9 cards stacked across 3 rows, which clipped the body
text because `practice-card` has a fixed-height blue header (~120-140px)
and 3-row stack squeezes the body to ~60-80px (needs ~150px for 220
chars). User's verdict: "phần lớn các slide toàn là text — k thể để
đại đa số là text như vậy đc" (most slides are pure text — that's not
acceptable).

The pipeline accepted this because:
1. Phase 2 outline planning didn't enforce visual diversity
2. Phase 4 block kinds were biased toward text-heavy options (narrative,
   features_3, list); visual components like bar-chart, process-flow,
   logo-grid existed in the page-builder catalog but weren't first-class
   in the drafter
3. No audit checked the visual:text ratio across a deck

This release rebaselines the skill around the principle that **a slide
is a visual medium**. Text-only slides are allowed as the exception,
not the default.

### `SKILL.md` — new Principle 8

Added **Principle 8 · Visual + content balance is mandatory**. Defines:

- **Component-by-content-type decision tree** (process → process-flow,
  data → chart, comparison → comparison-table, evidence → image-tile,
  many-items → icon-list/logo-grid, hierarchy → custom SVG, etc.).
  Phase 2 reasoning now consults this tree FIRST, falls back to
  narrative only when no visual option fits.
- **Per-slide rule**: every content slide must have a visual block, an
  image-lift/synthesize decision, a custom SVG, OR an explicit
  `text_only_justification`.
- **Per-deck rule**: visual-bearing slides ≥ 60%. Below 60% warns;
  below 40% blocks Phase 5.
- **Anti-stacking rule** (slide 06 lesson): components with fixed-height
  headers must NOT stack vertically. `features_3` max **1 row × 3 cards**.
  For 6+ items, use `icon_list` or `catalog`.
- **Source-image lift rule**: if source PPTX/video has usable visuals,
  prefer `lift` over `text-only`. `extract_pptx_images()` (v3.15) is
  the right tool.
- **Phase 2 outline now requires `visual_strategy` column** with one of:
  component-name | `custom-svg` | `image-lift` | `image-synthesize` |
  `text-only:<reason>`.

### New first-class visual block kinds (`content_drafter.py`)

Added 6 visual block kinds to `CONTENT_BLOCK_SCHEMAS` so Phase 4 can
draft them directly (previously these only existed at Phase 5
component-composition level):

| Kind | When to use |
|---|---|
| `image_tile` | Case-study screenshot, hero photo, lifted source slide |
| `process_flow` | 3-7 ordered steps (workflow, pipeline) |
| `bar_chart` | Comparing values (KPIs, forecasts, allocations) |
| `pie_chart` | Share-of-total (industry mix, %) |
| `logo_grid` | Partner / certification / award proof |
| `icon_list` | 6-12 parallel items at a glance (replaces stacked features_3) |

Each has a hard-cap entry in `BLOCK_KIND_CAPS` (validated by
`validate_block`) and a routing rule in `plan_to_slide_input`.

### `capacity.py` — visual-vs-text classification

```python
VISUAL_BLOCK_KINDS = {
    'image_tile', 'process_flow', 'bar_chart', 'pie_chart',
    'logo_grid', 'icon_list', 'values', 'catalog',
    'hero_stat', 'supporting_stats', 'comparison_divider',
}
TEXT_BLOCK_KINDS = {'narrative', 'list', 'features_3'}

is_visual_block(kind) → bool
```

### `cross_phase.py` — `audit_visual_balance(plans)`

Returns `{visual_count, text_only_count, visual_pct, flag, text_only_slides,
recommendations}`. Flag is `'ok'` (≥60%), `'warn'` (40-60%), or `'block'`
(<40%). Each text-only slide gets a recommendation (e.g. "Replace stacked
features_3 with icon_list").

### `creator.plan_to_slide_input()` — composes new visual blocks

Routes the 6 new block kinds to their corresponding components:
- `image_tile` → `image-tile` cell, full-width 1fr
- `process_flow` → `process-flow` cell, full-width auto
- `bar_chart` → `bar-chart` cell, full-width 1fr
- `pie_chart` → `pie-chart` cell, full-width 1fr
- `logo_grid` → `logo-grid` cell, full-width auto
- `icon_list` → `icon-list` cell, full-width auto

### Re-exports

`creator.py` exposes the new helpers:
- `audit_visual_balance`
- `VISUAL_BLOCK_KINDS`, `TEXT_BLOCK_KINDS`, `is_visual_block`

### Gaps resolved

- #34 — Phase 4 block schemas missing visual kinds (process-flow,
  charts, image-tile, logo-grid, icon-list)
- #35 — No deck-level visual balance audit
- #36 — Anti-stacking rule for fixed-height-header components not encoded
- #37 — Phase 2 component selection didn't surface visual options first

### Migration

For decks built under v3.15 that are text-heavy:
1. Run `audit_visual_balance(plans)` to identify text-only slides.
2. For each, consult Principle 8 decision tree:
   - process → process_flow
   - data → bar_chart / pie_chart
   - 6+ parallel items → icon_list / logo_grid
   - case study with screenshots → image_tile + lift
3. Replace text-only blocks with visual block kinds.
4. Re-audit until `flag == 'ok'`.
5. Re-compose deck.



After v3.14 fixed the capacity model (#27) and Phase 4 cap enforcement
(#29), the user requested a full audit pass to close all remaining
HIGH/MEDIUM gaps surfaced during pipeline evaluation. This release
closes 8 more gaps.

### `deck_planner.py` — outline schema upgrade (#7, #8, #14, #15)

- `make_slide_outline_entry()` now accepts v3.4 capacity-first fields as
  first-class kwargs: `layout_sketch`, `char_budget`, `image_strategy`,
  `rationale`, `need_input`. v3.13 lost these on every Phase 3 edit
  because `add_slide`/`replace_slide` only round-tripped the legacy 7
  fields; sessions hand-attached the 5 v3.4 fields each round. Now they
  ride through the schema natively.
- New `render_outline_table(outline, include_rationale=True,
  include_need_input=True)` — emits the 10-column v3.4 markdown table
  that SKILL.md Phase 2 mandates. Replaces ad-hoc per-session formatting.
- New `renumber_slide_ids(outline, prefix='s')` — re-aligns IDs to
  current positions after Phase 3 edits (e.g. `s11-procurement` ends up
  at slot 13 → `s13-procurement`). Use for readable logs/exports;
  functional behavior unchanged since IDs are stable identifiers.
- `validate_deck_outline()` adds `strict_section_order` flag (default
  True) — catches non-contiguous section grouping (e.g. ABOUT VTI slide
  inserted between SERVICES slides).
- `validate_deck_outline()` adds structural checks: cover-must-be-first,
  closing/contact-must-be-last (when present).
- `add_slide()` docstring clarifies `position` is **0-indexed** (matches
  `list.insert()`); previously was a footgun.

### `cross_phase.py` — density audit promoted to first-class (#19, #24)

- New `audit_plan_density(plan, layout)` — Phase 4 audit. Walks block ↔
  cell pairs, separates **visual-fill** kinds (hero_stat,
  supporting_stats — fill cell visually regardless of char count) from
  **text-dense** kinds (narrative, list, features_3 cards), and audits
  each tier appropriately. Closes the v3.13 false-flag where hero+kpi
  cells reported 35% fill ⚠⚠ MAJOR thin because the audit treated 50
  chars in a 200-cap cell as text density.
- New `audit_deck_density([(plan, layout), ...])` — aggregate Phase 4
  audit. Returns `{slide_count, overflow_count, sparse_count, ...}`.

### `context_doc.py` — multi-source ContextDoc (#3, #4)

- `make_context_doc()` now accepts an optional `sources` list — each
  entry has `{label, kind, path, summary?, asset_paths?, role?}`.
  Single-source decks unchanged (sources defaults to `[]`).
- `validate_context_doc()` validates each source entry's shape.
- SKILL.md Phase 1 protocol updated: when `len(sources) > 1` and source
  domains conflict, propose 2-3 deck-purpose interpretations BEFORE the
  audience/usage questions.

### `source_ingester.py` — video + PPTX image extraction (#1, #2)

- New `extract_pptx_images(pptx_path, out_dir, min_size=5000)` —
  extracts substantive images from `ppt/media/` via zipfile inspection.
  Closes the gap where each session reinvented this code.
- Video formats added to `_EXT_TO_KIND`: `.mp4`, `.mov`, `.webm`, `.m4v`
  → `video`.
- New `video_keyframes_stub(video_path)` — directs Claude to ffmpeg
  keyframe extraction when a video source is ingested. The pipeline
  treats video as `kind='video'` with `text=''` and image-only assets.

### `creator.py` — re-exports

All new helpers exposed via `from creator import …`:
- `cell_capacity`, `cell_target`, `layout_sketch_capacity`,
  `BLOCK_KIND_CAPS`, `block_kind_caps` (v3.14)
- `validate_for_compose`, `split_long_paragraphs`,
  `audit_plan_density`, `audit_deck_density`, `deck_density_summary`
- `render_outline_table`, `renumber_slide_ids`
- `extract_pptx_images`, `video_keyframes_stub`

### Gaps resolved

- #1  — Source ingester ignores video files
- #2  — No PPTX image-extraction helper
- #3  — ContextDoc single-source schema
- #4  — Phase 1 multi-source intent disambiguation (SKILL update)
- #7  — DeckOutline schema missing v3.4 fields
- #8  — No `render_outline_table` helper
- #13 — `add_slide` 0-indexed footgun
- #14 — Slide-id numeric prefix loses meaning after edits
- #15 — `validate_deck_outline` no section-continuity check
- #19 — No `audit_plan_density` helper
- #24 — No first-class density audit

### Gaps still open

- #5  — `summarize_source` not section-aware (LOW)
- #6  — No ContextDoc image-extraction validation (LOW)
- #21 — `make_image_decision.source_hint` not validated on disk (LOW)
- #22 — No `block_kinds_in_plan` deck-wide stat (LOW — `deck_density_summary` covers most use)
- #32 — Density-mode toggle (skim vs send-ahead) — architectural,
  requires component schema-cap relaxation in page-builder

 + audit-pass closeout

Major release closing **11 gaps** found during end-to-end pipeline run on
a 21-slide capability deck. Two CRITICAL findings, four schema fixes,
plus quality-of-life improvements.

### CRITICAL fixes

#### Capacity model unified across phases (#27)

Discovered while running the pipeline end-to-end: the v3.13 model had
**three separate truth sources** for "how much content fits in a cell":

1. SKILL Phase 2 capacity table — used for outline budget (e.g. 1400 chars
   for 7-col narrative)
2. Page-builder `capacity_chars_per_col` — used for Phase 5 wireframe
   audit (80 chars/col → 560 chars for 7-col narrative — 2.5× tighter)
3. Per-component hard caps in render functions (e.g. `paragraphs[]≤400`,
   `practice-card.body≤220`) — enforced only at compose

Result: Phase 4 drafted to SKILL targets, Phase 5 wireframe flagged
15/16 slides as overflow, and `render_inline_preview` failed on the
first slide with `[chars_exceeded] stat-hero.label: max 30, got 38`.
The pipeline let through drafts that could never compose.

**Fix:** new `creator/capacity.py` module exposes the page-builder's
declared values directly. SKILL Phase 2 budget table replaced with
references to `cell_capacity()` / `cell_target()` / `layout_sketch_capacity()`.

#### Phase 4 didn't enforce hard caps (#29)

`validate_block` previously only checked schema-completeness — drafts
past compose-time limits validated as ok and crashed at Phase 5.

**Fix:** `validate_block()` now mirrors `_check_max_chars()` calls in
each component's `_r_<name>` render function. New `BLOCK_KIND_CAPS`
dict in `capacity.py` defines per-sub-field limits (e.g. narrative
`paragraphs[]≤400`, hero_stat `label≤30`, practice-card `body≤220`).

### New modules

#### `creator/capacity.py`

- `cell_capacity(component, col_span) → int` — reads page-builder's
  declared `capacity_chars_fixed` or `capacity_chars_per_col × col_span`.
- `cell_target(component, col_span, ratio=0.85) → int` — Phase 4 drafting goal.
- `layout_sketch_capacity([(component, col_span), ...])` — multi-cell
  capacity calc for outline planning.
- `BLOCK_KIND_CAPS: dict` — hard caps per block kind / sub-field.
- `block_kind_caps(kind) → dict` — accessor.

#### `creator/cross_phase.py`

- `validate_for_compose(plans)` — Phase 4 → Phase 5 dry-run (#30).
- `split_long_paragraphs(content, max_per_para=400, max_paragraphs=4)`
  — narrative-block helper (#31). Splits at sentence boundaries, falls
  back to em-dashes / semicolons / colons / word boundaries. Repacks
  under 4-paragraph cap when needed. Raises ValueError if total content
  can't fit (signals layout needs more space).
- `audit_plan_density(plan, layout)` — proper visual/text separation
  (#17-19, #23-25). Closes the false-flagging issue where hero_stat /
  supporting_stats blocks were treated as text-density and showed 30%
  fill despite filling their cells visually.
- `audit_deck_density(plans_with_layouts)` — deck-wide audit summary.
- `deck_density_summary(plans)` — programmatic stats for QA scripts.

### deck_planner v3.14 — DeckOutline upgrade (#7, #8, #15, #13, #14, #16)

- `make_slide_outline_entry()` now takes **first-class v3.4 fields**
  (#7): `layout_sketch`, `char_budget`, `image_strategy`, `rationale`,
  `need_input`. Pre-v3.14 these had to be attached post-construction
  and were silently lost by Phase 3 helpers.
- `render_outline_table(outline)` — emits the SKILL.md-spec markdown
  table (#8). 10 columns: # · Section · Kind · Topic · Block kinds ·
  Layout sketch · Char budget · Image strategy · Rationale · Need Input.
- `validate_deck_outline()` now checks **section continuity** (#15) and
  **structural ordering** (cover-first, closing-last). Pass
  `strict_section_order=False` to opt out.
- `add_slide` docstring clarifies `position` is **0-indexed** (matches
  `list.insert()`) (#13). Easy footgun documented.
- `renumber_slide_ids(outline, prefix='s')` (#16) — convenience helper
  to align slide-IDs to current positions after Phase 3 edits. IDs are
  not used for ordering — purely cosmetic for log readability. Note
  added: avoid encoding position in slide_id to begin with (#14).
- `render_outline_summary` clarifies it's for logs/debugging; user-facing
  output should use `render_outline_table()`.

### content_drafter v3.14

- `validate_block()` enforces per-component hard caps (#29 above).
- `make_image_decision()` gains optional `validate_lift_path` flag (#21):
  when `True` and strategy=='lift', verifies `source_hint` exists on
  disk if it looks like a path. Skipped for description-style hints
  ("retail/p4 group photo") since those aren't paths.

### source_ingester v3.14

- `.mp4`, `.mov`, `.webm`, `.m4v` recognized as `kind='video'` (#1).
- `video_keyframes_stub()` returns guidance: ffprobe metadata + ffmpeg
  keyframe extraction → wrap as image assets via `ingest_pre_extracted`.
- `extract_pptx_images(pptx_path, out_dir, min_size_bytes=5000)` (#2)
  — promotes the per-session ad-hoc zipfile inspection into a helper.
  Returns asset dicts ready for `ContextDoc.source_assets`.

### context_doc v3.14

- `ContextDoc` gains optional `sources: [...]` field (#3) for multi-source
  decks. Each entry: `{label, kind, path, summary, asset_paths}`. Single
  -source decks can leave it unset. `validate_context_doc` validates the
  new field shape.

### creator.py order-preserving compose (#28)

`plan_to_slide_input()` now walks `plan.blocks` in declared order. v3.13
hardcoded a kind-precedence order (hero+narr → features_3 → values →
catalog → supporting_stats → list) that ignored Claude's declared order.
A plan declaring `[list, supporting_stats]` came out as `[kpi-row, list]`
— wrong row order. v3.14 preserves declared order, with one special
case: `hero_stat` immediately followed by `narrative` still merges into
a 5+7 asymmetric row.

### SKILL.md updates

- Principle 6 rewritten — capacity from helpers not static table.
- Hard caps subsection enumerating per-sub-field limits Phase 4 enforces.
- Cross-phase validator workflow documented.

### Re-exports from `creator.py`

```python
from creator import (
    # capacity (v3.14)
    cell_capacity, cell_target, layout_sketch_capacity,
    BLOCK_KIND_CAPS, block_kind_caps,
    # cross_phase (v3.14)
    validate_for_compose, split_long_paragraphs,
    audit_plan_density, audit_deck_density, deck_density_summary,
    # deck_planner (v3.14)
    render_outline_table, renumber_slide_ids,
    # source_ingester (v3.14)
    extract_pptx_images, video_keyframes_stub,
)
```

### Migration

For decks built under v3.13 that overflow:
1. Run `validate_for_compose(plans)` to enumerate violations.
2. For long paragraphs, call `split_long_paragraphs(content)` on each
   narrative block (preserves total density, respects 4-para cap).
3. For card-body / list-item / hero-label overflows, trim content to
   match `BLOCK_KIND_CAPS` or change layout.
4. For `>1600c` narratives, change layout (12-col single cell, two
   narrative rows, or content reduction).

### Gaps closed (11 total)

| # | Gap | Module |
|---|---|---|
| 1 | Source ingester ignored video files | source_ingester |
| 2 | No PPTX image extraction helper | source_ingester |
| 3 | ContextDoc single-source schema | context_doc |
| 7 | DeckOutline schema missing v3.4 fields | deck_planner |
| 8 | No `render_outline_table` helper | deck_planner |
| 13 | `add_slide` 0-indexed footgun undocumented | deck_planner |
| 14 | Slide-id naming convention guidance | deck_planner |
| 15 | No section-continuity validation | deck_planner |
| 16 | No `renumber_slide_ids` helper | deck_planner |
| 17-19, 23-25 | Density audit conflated visual/text | cross_phase |
| 21 | `make_image_decision` no path validation | content_drafter |
| 27 | Capacity model 2.5× mismatch | capacity (new) |
| 28 | `plan_to_slide_input` ignored block order | creator |
| 29 | Phase 4 didn't enforce hard caps | content_drafter |
| 30 | No cross-phase validator | cross_phase (new) |
| 31 | No paragraph splitter | cross_phase (new) |

### Gaps deferred (architectural)

- #4 — Phase 1 multi-source intent disambiguation (SKILL.md text update;
  partly covered via #3 multi-source ContextDoc)
- #20 — Density-mode tension between skim and async-read use cases
- #32 — Density-mode toggle (skim vs send-ahead) — needs component
  schema-cap relaxation, page-builder change

## v3.13.1 (2026-05-09) — Auto-decoration logic removed (split into vti-slide-decorator skill)

Decoration is now a separate post-compose skill (`vti-slide-decorator`)
that operates on rendered deck HTML via pixel-level whitespace analysis
+ SVG overlay injection (z-index lower layer, never touches content).
The composer now produces clean content slides only.

### Removed from vti-slide-page-builder/composer_grid.py
- `auto_decorate` trigger block (sparse_by_metric, thin_rows, moderate_thin signals)
- `_build_decoration_props()` helper
- `_make_decoration_row()` helper
- `decoration-band` component registration + CSS/HTML files
- `decorated` parameter from `_compose_grid_body()` and `_validate_fill_honesty()`
- Decoration overlay HTML injection in slide template

### Removed from vti-slide-creator/slide_edits.py
- `disable_auto_decorate()` function (no longer needed — composer ignores flag)

### Kept (still useful)
- `change_decoration_label()` — vti-slide-decorator's typographic strategy may consume `slide_meta.decoration_label`
- `position: relative` on slide div — decorator skill needs it for overlay anchoring
- `stat-hero.decoration` prop ('rings'/'none') — unrelated, just visual decoration of stat component

### Verification
- Component count: 38 → 37 (decoration-band gone)
- Clean v1 deck size: 6.0MB → 3.8MB (saved 2.2MB of decoration HTML/CSS)
- All 4 decoration markers absent from clean deck output:
  - `vti-slide-decoration-overlay`: 0 occurrences
  - `vti-decor__numeral`: 0 occurrences
  - `decoration-band`: 0 occurrences
  - `class="vti-decor`: 0 occurrences
- 15 slides with stale `auto_decorate=True` flag in slide_meta still build cleanly (flag now ignored, dead weight only)

### Migration notes
- If a slide was previously relying on `auto_decorate=True` for visual fill, it will now show empty bottom area in compose output. Decoration is added at the next stage by `vti-slide-decorator`.
- For slides where decoration is unwanted: pass `strategies={slide_idx: 'none'}` at the decorator stage (see `vti-slide-decorator/SKILL.md`).

---

## v3.13 (2026-05-09) — Phase 5 wireframe protocol + slide edit primitives

**Two foundational fixes shipped after live run on Smart Retail deck (29
slides) revealed Phase 5 was being skipped (no per-slide widget review)
and Principle 5 (custom-build) was being violated (forcing content into
mismatched components causing truncation).**

### 1. Phase 5 wireframe widget — primary review checkpoint

New `preview.py` API: `render_layout_review_widget(slides) → HTML
fragment`. Batch-renders all slides as 16:9 wireframe boxes for review
BEFORE compose. Pass output to `visualize:show_widget` for inline chat
review.

Key visual signals:
- 16:9 aspect ratio matches real slide proportions → empty bottom area
  shows visible whitespace (predicted sparse)
- Each cell colored by component category (text/data/card/visual/
  structural)
- Red border = predicted char overflow (chars > capacity)
- Dashed border = predicted char sparse (<40% of capacity)
- Per-slide flags: SPARSE, OVERCROWDED, OVERFLOW×N, IMG×N-aspect-risk
- Top-bar stats: total slides, chars, sparse-flag count, overflow-flag
  count

Wireframe is a **layout intent blueprint**, NOT a render preview. Does
NOT call compose_slide_grid; reads slide_dict structure + char counts
+ component capacity metadata only.

Also added:
- `deck_stats(slides) → dict` — programmatic summary, no render. For
  scripts/CI/quick checks.
- `render_inline_preview(slide)` retained for AFTER-wireframe single-
  slide pixel-perfect verification (slow; opt-in).
- `render_grid_summary(slide)` retained for plain-text logs.

### 2. `slide_edits.py` — per-slide edit primitives

New module with PURE functions (return new dict, don't mutate). Used
during Phase 5 iteration after wireframe surfaces issues:

- Cell-level: `change_cell_props`, `change_cell_component`,
  `change_cell_span`, `add_cell`, `remove_cell`
- Row-level: `replace_row`, `add_row`, `remove_row`, `set_row_height`,
  `mark_fill_verified`
- Slide-level: `change_slide_meta`, `change_decoration_label`,
  `disable_auto_decorate`, `change_layout_class`
- Custom-build escape hatch: `replace_with_custom_html(slide, html, css)`
  for Principle 5 (when components don't fit, build custom block,
  bypass row/cell rendering, keep chrome)
- Convenience: `shorten_practice_cards`, `find_cells_by_component`

Allows fix-one-slide iteration without rebuilding deck.

### 3. SKILL.md Phase 5 protocol updated

- Phase 5.4 expanded with v3.13 API examples
- Decision table: wireframe-flag → action (overflow → shorten/widen/
  replace; sparse → add content/consolidate/escalate; etc.)
- Phase 5 sub-steps clarified: 5.4 WIREFRAME (batch review), 5.5
  COMPOSE_DECK (only after user OK)
- Decoration concern handed off to NEW skill `vti-slide-decorator`
  (split from composer auto_decorate, pending v3.13.1)

### 4. Known limitations (will fix in W3 + W4)

- Wireframe predicts char-level overflow but NOT visual issues like
  image aspect-crop, narrow-cell text truncation, decoration label
  overflow. Visual-fit checker (Playwright DOM analysis) coming in W4.
- `image-tile` aspect mismatch is flagged as IMG×N-risk but wireframe
  cannot simulate the actual crop. Real fix = set `aspect_ratio`
  matching source asset (4:3, 9:16, 1:1, 21:9) — until W4 lands.
- Decoration rendering still embedded in composer (auto_decorate=True).
  Will be extracted to `vti-slide-decorator` skill in W3 (post-compose
  layer that doesn't touch content/layout).

### 5. Verified end-to-end on Smart Retail v1 deck

Live run on 29-slide deck:
- `deck_stats(slides)` correctly identified 8 flagged slides (5 overflow
  + 3 sparse) matching what visual review of v1 thumbs found
- `render_layout_review_widget(slides)` rendered as 23KB widget,
  show_widget compatible
- `slide_edits.shorten_practice_cards` + `change_decoration_label` +
  `change_cell_props` (aspect_ratio) demonstrated end-to-end fix loop
  works (mutations compose, wireframe re-renders cleanly)

---

## v3.12 (2026-05-09) — Decoration overlay fix + planning-gap acknowledgment

**Three real problems flagged by user review of v3.11 deck:**

1. Decoration not visible on actual slides (was rendered as inline row,
   ended up squeezed at top instead of anchoring empty bottom canvas)
2. Auto-decoration only applied to 1 demo slide (others didn't opt in)
3. **(Foundational)** Planning loop never runs end-to-end — every deck
   rebuild is hand-coded, no capacity-first planner / consolidation
   logic / layout-by-content-budget mechanism

**v3.12 ships fixes for #1 and #2:**

- Decoration renders as `<div class="vti-slide-decoration-overlay">…
  </div>` positioned absolute at bottom-right of each slide (32px
  right, 72px above footer). Numeral bumped to 160px for visual weight.
  Slide div gets `position: relative` to anchor the overlay.

- `auto_decorate` defaults to `True` in the slide() helper (opt-OUT
  model now). 18 of 25 content slides on the test deck pick up
  decoration automatically.

- Three trigger signals for auto-decoration:
  - `slide_fill < 0.40` (char-based sparseness)
  - `≤2 content rows AND no _fill_verified` (true thin)
  - `≤3 rows AND no _fill_verified AND fill < 0.55` (moderate-thin —
    catches narrative+process-flow+kpi-row layouts where each row is
    full but bottom canvas is still empty)

- Slides with `_fill_verified=True` 1fr rows are exempt — the planner
  declared the layout intentional. Case-study hero-stat slides
  (s17/s19/s21) are not decorated.

**Phase 5 hint:** When laying out a slide, decide if you actually want
auto-decoration. If the layout is intentionally spaced (hero anchor,
section divider rhythm), set `_fill_verified=True` on the 1fr row to
opt out. Otherwise leave it default and the composer will anchor any
residual whitespace with a numeral overlay.

---

## ⚠ v3.13 / v4.0 — the planning loop is what's missing

The creator skill currently has SKILL.md with all the rules but **no
runnable planning pipeline**. Every deck has been hand-authored in
`build_deck_v*.py`. Through v3.0–v3.12 we built renderer-side tools
(capacity hints, layout_class, auto_decorate, decoration-band, Gap A-E
detection) but never wired a planner that USES them on real source
material.

**v3.13 needs a `creator.plan(source) → slide_dicts` pipeline:**

1. **Phase 0 (NEW) — Material audit**: parse source PPTX/brief, count
   chars per topic, list visual artifacts.
2. **Phase 1 — Deck outline**: act/section/slide count from material
   volume. Consolidation detection: thin adjacent topics in same
   section get merged into one slide.
3. **Phase 2 — Per-slide layout**: pick layout pattern + component set
   matching content budget. Apply `layout_class` here.
4. **Phase 3 — Content draft**: fill component props within capacity.
5. **Phase 4 — Bounce-back**: if Gap A-E warnings fire, revise layout
   choice in Phase 2 and re-draft.
6. **Phase 5 — Compose**: `compose_slide_grid` with all decisions
   baked in; `auto_decorate=True` handles residual whitespace.

Until this pipeline exists, the skill principles aren't actually
exercised end-to-end. v3.12 just makes the render output cleaner; the
real work is wiring the planner.

---

## v3.11 (2026-05-09) — Auto-decoration generator (P7 Loop 2 closure)

**Closes the v3.4 Principle 7 promise.** P7 said "if slide is sparse,
fix by content add OR decoration"; through v3.10 the composer only
warned about sparseness. v3.11 ships the decoration mechanism.

**New: `decoration-band` component** (38th component, renderer-side).
Three variants for visual anchoring of intentional whitespace:

| Variant | Visual | Use for |
|---|---|---|
| `numeral` | Large faded numeral + small label, top-right by default | Section anchors, hero whitespace |
| `accent-bar` | Thin gradient horizontal line | Bottom-strip closure, divider |
| `corner-chevron` | Angular chevron + label | Sub-section transition |

Schema: `variant`, `text`, `label`, `position` (`full-row`/`left`/
`right`/`center`), `tone` (`soft`/`medium`/`deep`).

**New: opt-in `slide_meta.auto_decorate: True` flag.** When set, the
composer:
1. Pre-projects slide fill before composition.
2. If projected fill < 40%, builds and appends a decoration-band row
   with sensible defaults (numeral variant, page_number as text,
   section_name as label, soft/medium tone based on sparseness).
3. Composes as normal. Validator runs with `decorated=True` flag — if
   post-injection fill is still <40%, an info line `[gap-E
   auto-decorated]` replaces the sparse warning. If decoration pushed
   fill over 40%, no warning fires.

Override defaults via `slide_meta.decoration_variant`,
`decoration_text`, `decoration_label`.

**Phase 5 hint:** When laying out a slide that's intentionally sparse
(hero-anchored case study, philosophical pause, divider transition),
add `auto_decorate: True` to slide_meta. The composer will anchor the
whitespace automatically — no need to hand-craft a decoration cell.

**Phase 4 hint:** The sparse warning text now mentions both options:
add real content OR add decoration via the new mechanism. Pick based
on whether the slide's message is fully delivered by current content.

**Validation result:** 31-slide CTO deck (v3.11) ships with 0 pre-
render warnings AND 0/31 audit violations. New s30 ("What we promise")
demonstrates auto-decoration: a single pull-quote at col 12 with low
content density triggers auto-injection of a "WHY VTI / 04" numeral
decoration on the right side, anchoring the otherwise-empty canvas.

---

## v3.10 (2026-05-09) — Layout-class calibration + callout dynamic capacity

**New: `slide_meta.layout_class` field.** Slides can declare one of three
layout classes that drive both pre-render Gap C aggregator thresholds
and post-render audit_typography.py thresholds:

| layout_class | T1 levels | Use for |
|---|---|---|
| `default` (default) | max 3 | regular slides |
| `case-study` | max 4 | hero-stat anchor layouts (hero+title+body+caption) |
| `data-dense` | max 4 | Why-VTI / TOC patterns (display+title+body+caption) |

Phase 5 layout planner should classify the slide:
- If layout uses `stat-hero` + cards/narrative → `case-study`
- If layout has 4+ structural sections (kpi-row + headline + cards + tags) → `data-dense`
- Otherwise → leave default (no tag needed)

The composer validates `layout_class` against allowed values and emits
a `data-layout-class="..."` attribute on the slide DOM root for the
audit script to read.

**Callout dynamic capacity** — extends v3.9's narrative-paragraph
pattern. Composer detects "pullout mode" automatically:
- col_span ≥ 10 AND title+body < 200 chars → capacity 30/col (was 60/col)
- otherwise → 60/col unchanged

This handles the case where a planner uses callout as a wide pull-out
emphasis bar (col 12, slim copy) vs as a sidebar (col 4-6 with full
content). No schema change needed — composer infers from props.

**Phase 4 hint:** When drafting a wide callout (col 12) as emphasis,
keep it short (under 200 chars total). For full-content sidebar
callout, use col 4-6 with detailed body — composer auto-applies main
mode.

**Validation result:** 30-slide CTO deck now ships with 0 pre-render
warnings AND 0 audit violations — the cleanest state to date.

---

## v3.9 (2026-05-09) — Component CSS fixes + dynamic capacity

Three component-layer bugs surfaced by v3.8 stress-test fixed:

- **quadrant-matrix Y-axis** — long axis labels (e.g. "CLOUD SERVER" /
  "EDGE DEVICE") no longer overlap. Y-axis layout switched from
  flex-space-between to grid 2-row.
- **before-after canvas fill** — at col 12 the component now stretches
  the full row width (was rendering ~50% width, leaving the right side
  empty).
- **timeline horizontal** — dates now visible (were `color: white` on
  white background); deliverable checkmarks visible (same fix); metric
  badges stack BELOW title in horizontal orientation as a horizontal
  mini-pill, removing collision with short titles.

**Dynamic narrative-paragraph capacity** — `_component_capacity()` now
infers usage role from props for narrative-paragraph:
- **Intro pattern** (col_span ≥ 10, ≤ 1 paragraph, < 300 chars) →
  capacity 35/col (was 80/col flat). A 200-char intro at col 12 now
  projects against 420 cap (48% fill) instead of 960 (21% fill).
- **Main body pattern** (col_span ≤ 8, multi-paragraph, or ≥ 300 chars
  total) → 80/col unchanged.

This closes 3 of 4 false-positive Gap E sparse warnings on v3.8 deck.
Last one (s13) is genuinely borderline at 39% fill — not a false
positive, just close to threshold.

**Phase 4 hint:** When drafting an intro narrative at col_span ≥ 10,
keep it to 1 paragraph and ≤ 300 chars. The composer will auto-detect
intro mode and apply lenient capacity. For richer content blocks (2+
paragraphs or 300+ chars), use col_span ≤ 8 to invoke main-body
capacity.

---

## v3.8 (2026-05-09) — Capacity recalibration + diverse-style stress test

8 free-form text components (narrative-paragraph, callout, pull-quote,
lead-paragraph, quote-block, section-header, headline, kicker) re-opt-in
to capacity check with calibrated single-number values:

| Component | per_col | Notes |
|---|---|---|
| narrative-paragraph | 80 | col 6 main = 480 (target 350-432); col 12 intro = 960 (light fill OK) |
| callout | 60 | title + body |
| pull-quote | 20 | col 12 = 240 |
| lead-paragraph | 100 | hero-style intro |
| quote-block | 30 | longer narrative quote |
| section-header | 18 | mid-slide eyebrow |
| headline | 8 | 1-2 line statement |
| kicker | 5 | small label |

**`_walk_chars` bug fix:** when image-tile renders a base64 data URI
(60K+ chars typical), the chars walker was inflating slide-fill to
14000%+. v3.8 skips strings starting with `data:` and strings ending in
image extensions.

**Before-after capacity bump:** 300 → 500 chars after stress-test
showed Scan&Go before/after slide hitting 178% with 5 items per side.
500 is now the natural cap matching the typical pattern.

**Stress test result:** 30-slide CTO deck across 20+ component types
ships with 0/30 audit_typography violations. Pre-render Gap E surfaced
4 borderline-sparse slides (29-38% fill) as planning signals; not
layout failures.

---

## v3.7 (2026-05-09) — Capacity-fill projection (Gap E)

The composer now estimates actual char count in cell props and compares
against declared component capacity. Three new warning types in the
slide-render metadata:

- `[gap-E fill-honesty]` — row uses `_fill_verified=True` but cell
  projects <70% fill → declaration was wrong; either drop verified or
  expand content
- `[gap-E slide-sparse]` — total slide fill <40% → P7 Loop 2: add
  content / decoration / restructure
- `[gap-E slide-overcrowded]` — total slide fill >115% → P6: too dense

**Creator-side impact:** `compose_slide_grid()` metadata `warnings`
list now surfaces capacity-fill issues. Phase 4 (content drafter)
should iterate Gap E warnings after build:
- `slide-sparse` → bounce back to Phase 5, change layout or add row
- `fill-honesty` → either expand content or change row to `auto`
- `slide-overcrowded` → split slide or move content to appendix

**Component capacity declarations (29/37):** Most structured components
declare `capacity_chars_per_col` (linear scaling) or
`capacity_chars_fixed` (fixed-structure). The 8 free-form text
components (narrative-paragraph, callout, pull-quote, lead-paragraph,
quote-block, section-header, headline, kicker) opted out — single-number
capacity can't model their dual-use (intro vs main body). v3.8 candidate:
context-aware dynamic capacity.

**Calibration thresholds:** sparse 40% / fill-honesty 70% / overcrowded
115%. These were tuned against the v3.6 CTO deck with visual ground-truth.

**Phase 2 hint:** When committing `Char budget` in the outline table
(per P6 v3.4), use the sum of component capacity_chars_* meta values
for the chosen layout. The composer will validate this at build.

---

## v3.6 (2026-05-09) — CSS rationalization

The page-builder CSS layer now consumes only canonical T1 sizes
(12 / 15 / 24 / 32 / 64 px) and canonical T2 weights (400 / 500 / 600).
112 hardcoded px values + 61 hardcoded weight values across 46 files
were normalized to the nearest canonical value. The 7 legacy size
tokens + 2 deprecated weight tokens in tokens.css now alias to canonical
T1 px values.

**Effect on creator side:** None — the creator skill rules are unchanged;
this is purely a renderer-layer rationalization. But the post-render
audit_typography.py result has dropped from 9/16 → 0/16 violations on
the v3.6 build of the same content, meaning the strict T1/T2/T3 budget
is now honored by the renderer at default settings.

**Gap C aggregator refined:** weight 600 is now allowed when paired with
hero or display level on the slide (T2 exception). Five false-positive
weight warnings on case-study + Why-VTI slides cleared.

---

## v3.5 (2026-05-09) — Composer code enforcement

The page-builder composer now enforces v3.4's rules with code-level
warnings instead of pure documentation:

- **Gap A** — `col_span ∉ best_col_spans` produces a warning per cell
- **Gap B** — `height="1fr"` without `_fill_verified=True` produces a
  warning per row
- **Gap C** — per-slide font_levels_used / font_weights_used aggregator
  emits warnings when slide exceeds T1/T2 budget. All 37 components
  now declare these fields.
- **Gap D** — `_esc()` detects pre-escaped HTML entity sequences in
  source strings and warns

**Creator-side impact:** The `compose_slide_grid()` metadata return now
includes a populated `warnings: list[str]` for any of the above. After
build, iterate per-slide warnings and either fix the source or flag the
exception as documented.

**Phase 5 helper update:** When constructing rows, callers should pass
`_fill_verified=True` on the row dict for any genuinely-needed `1fr`
case (e.g. case-study hero stat anchor). Without it, the composer
warns. The `make_row()` helper in `grid_helpers.py` may want to grow
a `fill_verified=False` keyword in v3.6.

**Phase 4 hint:** When using `kpi-row`, ensure the cell uses
col_span=12. Putting `kpi-row` into a 4-col cell will trigger Gap A
because internal `stat-mini` items can't fit. Use individual
`stat-mini` cells in narrow columns instead.

**Source-string hygiene (Gap D):** Schema string values must be plain
Unicode. Use `<30s`, not `&lt;30s`. Composer auto-escapes once;
pre-escaping double-escapes and renders literal `&LT;30S` after CSS
uppercase.

---

## v3.4 (2026-05-09) — Two-loop fit + capacity-first

These edits were applied during a real end-to-end build of a 16-slide
CTO deck synthesizing 4 customer-facing source PPTX (VTI Retail
Capability + Smart Planogram + 2 SKT proposals).

### Principle 6 — fully rewritten

**Old (v3.3):** "Capacity-aware content planning" — capacity computed
during draft, validated after. Effectively a hint, not a planning input.

**New (v3.4):** "Capacity-first content planning" — capacity is an
INPUT to Phase 2 (outline) and Phase 4 (content), committed in advance
as `Layout sketch + Char budget` columns on the Phase 2 outline table.
Phase 4 drafts to that budget; if it falls below 70%, BOUNCES BACK to
Phase 2 to swap to a narrower layout.

**Reason for change:** v3.3 P6 was advisory and got bypassed routinely.
The v3.4 build had 6/16 slides ship with cards stretched to ~600px
height containing ~200 chars of body text. The fix: capacity is a
commitment, not a check.

### Principle 7 — NEW

"Two-loop fit discipline." Splits the visual-fit problem into two
distinct passes:
- **Loop 1** — peer-equalization within a row via `max(natural_heights)`.
  Browser grid `auto` already does this. NEVER use `1fr` to stretch
  boxes to fill canvas.
- **Loop 2** — slide-level whitespace evaluated separately, resolved
  via content add / decoration / restructure. Bottom whitespace <25%
  is intentional breathing space; 25-50% requires action; >50% means
  redesign the layout.

**Reason:** P6 was conflating cell-level density with slide-level
density. They are two separate decisions.

### Phase 2 outline table — 2 new columns

Was:
```
| # | Section | Kind | Topic | Block kinds | Image strategy | Rationale | Need Input |
```

Now:
```
| # | Section | Kind | Topic | Block kinds | Layout sketch | Char budget | Image strategy | Rationale | Need Input |
```

`Layout sketch` is a 1-line concrete grid sketch (e.g. "narrative 7 +
kpi-strip right 5"); `Char budget` is the total chars target across
all cells, derived from the capacity reference table.

### Phase binding table — updated

Each phase now has explicit P6 v3.4 / P7 hooks. Phase 4 must bounce
back to Phase 2 (not Phase 5) if budget can't be filled.

### Phase 5 default behavior change

Default row height is now `auto`. Setting `1fr` requires explicit
content-fill verification + visual-weight justification, documented
inline.

---

## Session edits during end-to-end test (May 2026, v3.2-v3.3 era)

These edits were applied during a real end-to-end test where Claude
produced a 19-slide healthcare deck from a PDF + PPTX source pair, with
a real user driving the brainstorm checkpoints.

### Top of file — new sections

**Output scope — HTML ONLY**
- This skill produces ONE HTML file. No PDF, no PNG screenshots.
- PDF route is delegated to the separate `vti-pdf-export` skill.
- Reason: in test, Claude auto-exported PDF "as a bonus" — out of scope.

**Checkpoint enforcement — STOP and WAIT**
- After each phase output, ask specific questions, then STOP.
- Do not auto-advance phases. User "OK" gives permission for NEXT phase
  only.
- Reason: in test, Claude treated checkpoints as advisory, not blocking,
  and auto-ran through 5 phases on the first attempt.

### Phase 1 — ANALYZE

**Image extraction is mandatory**
- Extract substantive images (>5KB) from PDF (pymupdf) and PPTX
  (zipfile `ppt/media/`) during Phase 1.
- Reason: in test, Claude passed `assets=[]` and skipped 38 PDF + 67
  PPTX images on first attempt — lost most of the source visual material.

**Question methodology**
- DO ask: viewer role · usage context · customer specificity · language
- DO NOT ask: slide count · density · tone · format
- Slide count and density are OUTPUTS of Phase 1 reasoning, not inputs.
- Reason: in test, asking "how many slides do you want?" was useless —
  the user couldn't picture the answer. The right inputs are role +
  context + duration; length follows from those.

### Phase 2 — PLAN-OUTLINE (split from former Phase 2-3)

**Required 8-column markdown table format**
```
| # | Section | Kind | Topic | Block kinds | Image strategy | Rationale | Need Input |
```
- `Image strategy` is a concrete description, not a one-word strategy
  (e.g. "Lift pdf/p03-00 (VTI HQ photo)" not "lift")
- `Rationale` explains WHY for THIS slide
- `Need Input` flags items requiring user clarification
- Reason: in test, Claude defaulted to bullet lists which were "messy"
  and didn't surface decision rationale or open questions clearly.

### Phase 3 — PLAN-REVIEW (split into its own section)

- Phase 3 is its own checkpoint, distinct from Phase 2.
- Each turn must be labeled "Phase 3 — PLAN-REVIEW".
- Loop with `add_slide / remove_slide / move_slide / replace_slide`
  until user approves.
- Reason: in test, Phase 3 was bundled with Phase 2 in the skill, so
  Claude skipped naming it and the user lost track of where in the
  pipeline they were.

### Phase 4 — Content drafter

**Required output structure**
1. Per-slide content draft (concrete block content, no prose narration)
2. Narrator + framing slide props (concrete values)
3. Open items list
4. 2-4 specific brainstorm questions

- Phase 2's table already covers image strategy — Phase 4 should NOT
  repeat that. Focus on content.
- Reason: in test, Claude duplicated the image strategy table in
  Phase 4, wasting space.

### Phase 5 — Layout brainstorm loop

**Phase 5.4 — Layout wireframe widget (CRITICAL)**
- The widget is a wireframe / blueprint, NOT a rendered slide.
- Must show: 1280×720 frame with chrome zones, 12-col grid overlay,
  cells as labeled boxes, image slots clearly marked, row heights.
- MUST NOT: render real slide HTML, screenshot built slides, embed
  real component CSS.
- Render via `visualize:show_widget` for ALL content slides, then
  ask user for batch approval.
- Reason: in test, Claude built the actual deck and screenshotted it,
  treating that as a "preview". The whole point of Phase 5.4 is to let
  the user catch layout problems BEFORE composition — a screenshot of
  a built slide is too late.

## Bug fixes / minor

- Fixed `make_cell` arg confusion (col_start, col_span — not col_end)
- Fixed TOC item key (use `title`/`page` not `label`/`page`)
- Fixed special-page prop names (`deck_title` not `tagline`,
  `toc_items` not `items`, etc.) — these were undocumented in skill
- Fixed narrative row 1fr height creating visual gaps when paired
  with other rows

## Open / not yet fixed

These are gaps observed during the test that need design decisions
before fixing:

- `CONTENT_BLOCK_SCHEMAS` (8 kinds) << page-builder catalog (37
  components). Many components (process-flow, tags, timeline, table,
  charts, etc.) cannot be expressed as block kinds in Phase 4 — user
  must drop into manual Phase 5.
- Icon catalog is tech-themed (16 icons): brain, code, cloud, tools,
  shield-check, etc. No healthcare-specific icons (heart, hospital,
  pill, stethoscope). For domain-specific decks, mapping to closest
  icon is required.
- `validate_block` does not enforce per-component max-char limits.
  Errors only surface at compose time.
- `plan_to_slide_input` heuristic always uses 1fr for narrative-only
  rows, creating visual gaps when paired with other rows. Workaround
  applied at Phase 5 patch time.
- No `features_4` block kind (only `features_3`). Workaround: use
  `values` (4-6 medallions) when 4 cards are needed.
