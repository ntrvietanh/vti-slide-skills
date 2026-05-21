# vti-slide-figma-mockup

**Version: 0.2.4**

High-fidelity UI mockups for VTI slide decks. **Dual backend**:

| Backend | Default? | Quota | Editing handle | Best for |
|---|---|---|---|---|
| `html` | ✅ (v0.2.0+) | unlimited (local) | `source.html` file | day-to-day deck production, fast iteration |
| `figma` | opt-in | Figma plan (Starter: 6/MONTH) | Figma URL | when stakeholders want to co-edit in Figma |

Pick a backend per call via `backend="html" | "figma"` or the env var
`VTI_MOCKUP_BACKEND={html|figma}`.

> **Figma backend caveats** (still true in v0.2.0):
> - `use_figma` takes Plugin API **JavaScript**, not natural-language briefs.
> - `layoutSizingHorizontal/Vertical` only work AFTER `appendChild`.
> - Starter plan is **6 calls/MONTH** — sloppy first render burns the quota.
> See *"Plugin API gotchas"* below for full list.

High-fidelity UI mockups / demo screenshots for VTI slide decks, rendered
through Figma MCP. Pairs with `vti-slide-creator` (Phase 3 caller) and
feeds image-tile cells via `vti-slide-page-builder`.

```
vti-slide-creator (Phase 3) ─┬─► vti-slide-diagram-builder  → work/diagrams/*.svg
                             └─► vti-slide-figma-mockup     → work/mockups/<id>/{render.png, render.svg?, meta.json}
                                                              ↑ this skill
```

## Why this skill exists

Before this skill, slides that needed product UI / app screenshot demos
either (a) lifted a junk PNG from the source PDF, or (b) drew an
ASCII-ish wireframe inside a diagram primitive. Neither produced
boardroom-quality "this is what the product looks like" visuals. This
skill emits a Figma render task that the orchestrator executes via
Figma MCP, then captures the result as PNG (mandatory) + SVG (optional)
+ Figma file URL (for hand-editing after the deck is composed).

Each kind carries a **canonical hint canvas** so Phase 4
(`layout_designer`) can pre-size the hosting image-tile cell to the
mockup's natural aspect ratio — guaranteeing no-crop / no-letterbox
regardless of which `image-aside` split the designer chooses.

## When to use

The orchestrator (Phase 3 in `vti-slide-creator`) invokes this skill
when `image_decision.strategy == "mockup"`. Strategy `"mockup"` should
be picked when the slide narrative needs:

- A product UI screenshot (mobile / desktop app)
- A wireframe of a proposed UX flow
- A device-framed demo (phone / tablet / browser)
- A multi-screen user journey strip

Strategy stays `"synthesize"` for diagrams, `"lift"` for source PDF
images, `"text-only"` for narrative-only slides.

## Inputs

| Input | Source | Required |
|---|---|---|
| Brief | Phase 3 author text — what UI to mock | yes |
| Kind | One of `screen-mobile / screen-tablet / screen-desktop / screen-bare / flow-mobile / flow-desktop / wireframe-mobile / wireframe-desktop` | yes |
| Title | Slide topic — used in Figma file name | yes |
| Style | `brand-vti` (default) \| `neutral` \| `dark-mode` | optional |
| Frame label | e.g. `"iPhone 15 Pro"`, `"Chrome on macOS"` | optional (kind defaults) |
| Captions | Optional list of per-screen captions for flow kinds | optional |

## Outputs

| Output | Description |
|---|---|
| `work/mockups/<slide_id>_<asset_id>/render.png` | PNG at the Figma node's natural pixel size (mandatory). |
| `work/mockups/<slide_id>_<asset_id>/render.svg` | SVG export when Figma supports it for the node (optional). |
| `work/mockups/<slide_id>_<asset_id>/meta.json` | Sidecar: `{kind, brief, figma_url, figma_file_key, figma_node_id, natural_w, natural_h, captions}`. |
| `work/mockups/INDEX.md` | Auto-appended one-line per render with the Figma URL — quick reference for the user to open + tweak. |

The orchestrator stores the resulting `mockup_spec` (shape below) in
`content_plan["mockup_spec"]` so Phase 4 can size the cell.

```python
mockup_spec = {
    "kind":           "screen-mobile",
    "brief":          str,
    "png_path":       "work/mockups/.../render.png",
    "svg_path":       "work/mockups/.../render.svg" | None,
    "figma_url":      "https://figma.com/design/<key>/...?node-id=<id>",
    "figma_file_key": str,
    "figma_node_id":  str,
    "natural_w":      int,    # actual rendered px width
    "natural_h":      int,    # actual rendered px height
    "captions":       list[str],   # optional, parallel to flow screens
}
```

## Kinds

| Kind | Hint canvas | Frame default | Typical use |
|---|---|---|---|
| `screen-mobile`     | 480 × 960  | iPhone 15 Pro     | one mobile app screen |
| `screen-tablet`     | 1024 × 768 | iPad (landscape)  | one tablet UI |
| `screen-desktop`    | 1440 × 900 | Chrome on macOS   | one desktop / web app screen |
| `screen-bare`       | 1180 × 740 | (no frame)        | screen without device chrome, for hero crops |
| `flow-mobile`       | 1440 × 960 | iPhone × 3        | 3-screen mobile journey strip |
| `flow-desktop`      | 1620 × 540 | Browser × 3       | 3-screen desktop journey strip |
| `wireframe-mobile`  | 480 × 960  | iPhone (mono)     | low-fi mobile (gray boxes + lorem) |
| `wireframe-desktop` | 1440 × 900 | Browser (mono)    | low-fi desktop |

`hint_w / hint_h` is what Phase 4 uses for the image-tile cell
aspect-ratio. After Figma renders, `mockup_executor.record_render`
re-reads the actual pixel size and overwrites `natural_w / natural_h`
in the spec.

## HTML backend (default) — end-to-end

The HTML backend renders entirely locally: no quota, deterministic,
hand-editable. The orchestrator writes per-screen `body_html` against
brand-token CSS variables provided by `html_backend`; the skill
provides the outer frame (browser chrome / phone bezel / flow strip).

### Quick start

```python
import mockup_builder
import mockup_executor

# 1. Build the task — default backend='html'
task = mockup_builder.make_screen_desktop(
    brief="B2B logistics dispatch console. Left nav. Map on top. Job table below.",
    title="Dispatch console — operator view",
    style="brand-vti",
)

# 2. Hand-author body HTML using the html_backend atoms.
#    Use CSS vars (var(--blue), var(--ink), ...) and atom classes
#    (.card, .chip, .av, .sec-hdr-amber, .spark, etc.) — see
#    html_backend.py for the full atom catalogue.
body_html = """
<div class="col-v gap-6">
  <h1 class="h1">Dispatch console</h1>
  <div class="row" style="gap:10px;">
    <div class="card col-v gap-4" style="flex:1;">
      <span class="kicker">Active vehicles</span>
      <span class="fs-18 fw-600">12</span>
    </div>
    <div class="card col-v gap-4" style="flex:1;">
      <span class="kicker">Open jobs</span>
      <span class="fs-18 fw-600">8</span>
    </div>
  </div>
  <!-- ... -->
</div>
"""

# 3. Render — Playwright headless Chromium @ 2× retina by default.
spec = mockup_executor.record_html_render(
    task=task,
    slide_id="s14-dispatch",
    asset_id="01",
    screens=[{"url": "ops.vti.ai/dispatch", "body_html": body_html}],
    work_root="work",
    scale=2,
)
print(spec["png_path"])      # work/mockups/s14-dispatch_01/render.png
print(spec["html_path"])     # work/mockups/s14-dispatch_01/source.html
```

After render: `work/mockups/s14-dispatch_01/` contains `render.png`,
`source.html` (the document the user edits to tweak), and `meta.json`.
`work/mockups/INDEX.md` gets a one-liner appended.

### Atom classes available in `html_backend`

| Class | Purpose |
|---|---|
| `.av`, `.av-sm`, `.av-md`, `.av-stack` | Circular initials avatar; `av-stack` overlaps them |
| `.chip`, `.chip-blue`, `.chip-amber`, `.chip-green`, `.chip-muted`, `.chip-white` | Pill labels |
| `.card`, `.card-sm`, `.card-row` | Card containers with auto layout |
| `.card-active` | Highlighted card (blue border + paleblue fill) |
| `.sec-hdr`, `.sec-hdr-{amber,blue,gray,green}` | Section header with leading colored bar |
| `.spark` | Inline sparkline — children `<span style="height:Npx">` |
| `.check`, `.check-done`, `.strike` | Checkbox + struck-through text |
| `.h1` / `.h2` / `.h3` / `.h4` | Heading scales (18 / 13 / 12 / 11 px) |
| `.kicker` | 11px muted label |
| `.row`, `.row-tight`, `.col-v`, `.gap-{2,4,6,8,10}` | Flex helpers |
| `.fs-{10..18}`, `.fw-600`, `.muted`, `.ink-soft` | Type modifiers |
| `.divider` | 1px horizontal hairline |

**Brand tokens (CSS vars)** mirror `vti-slide-page-builder/tokens.css`:
`--navy`, `--blue`, `--blue-deep`, `--blue-mid`, `--bright`, `--sky`,
`--light`, `--paleblue`, `--ink`, `--ink-soft`, `--muted`, `--border`,
`--divider`, `--bg`, `--white`, `--amber`, `--amber-strong`,
`--amber-pale`, `--amber-ink`, `--green`, `--green-pale`, `--red`.

For `style="neutral"` and `style="dark-mode"`, the same variable names
swap to alternate palettes — orchestrator code stays identical.

### Single-screen vs flow

```python
# Single screen:
record_html_render(task=task, ..., screens=[{"url": "...", "body_html": "..."}])

# Flow (exactly 3 screens):
record_html_render(task=flow_task, ..., screens=[s1, s2, s3])
# Captions and the wrapping flow strip come from task["captions"] + task["title"]
```

For phone kinds, pass `time` instead of `url`:
```python
screens=[{"time": "9:41", "body_html": "..."}]
```

### Worked example

See [scripts/build_s12_mockup.py](../../scripts/build_s12_mockup.py)
(per-deck) — renders the s12 day-in-life flow-desktop with 3 detailed
screens (Mail Summary / Chat Digest / Meeting Prep). Output is
`work/mockups/s12-day-in-life_01/render.png` (4000×2400 @2×).

---

## Figma backend (opt-in) — two-step orchestration

The Figma backend is split — the build step is pure Python (no MCP),
the render step is an MCP call the orchestrator drives.

### Step 1 — build a task descriptor (pure Python)

```python
import mockup_builder

task = mockup_builder.make_screen_mobile(
    brief=(
        "Healthcare patient portal mobile app. Header with patient name "
        "+ avatar. 3 KPI cards. Appointments list. Bottom tab bar."
    ),
    title="Patient portal — home screen",
    style="brand-vti",
    backend="figma",        # OPT-IN — default is "html"
)
# task["brief"] is the natural-language design brief, used to
# AUTHOR the Plugin API JS the orchestrator hands to use_figma.
```

### Step 2 — translate `brief` to Plugin API JS, render, record

`use_figma` does NOT accept the natural-language `brief` directly. It
takes JavaScript that runs against the Figma Plugin API (`figma.*`).
The orchestrator must hand-author the JS using the brief as the
spec. The brief is your design intent; the JS is your construction
recipe.

```text
1. Load /figma-use skill (MANDATORY before use_figma).
2. Call mcp__claude_ai_Figma__create_new_file with title=task["title"]
   + planKey (get via whoami first call only).
3. Translate task["brief"] into Plugin API JS:
     - figma.loadFontAsync for each Inter weight you use.
     - Build frames bottom-up with figma.createFrame, set
       layoutMode + sizing modes (see Plugin API gotchas below).
     - Set fills/strokes/cornerRadius. Use the brand-vti hex
       literals from task["brief"]'s "Visual style" block.
   Call mcp__claude_ai_Figma__use_figma with the JS as `code`,
   `fileKey` from step 2, and `description` summarizing the JS.
4. Call mcp__claude_ai_Figma__get_screenshot on the root node →
   returns a short-lived asset URL + curl instructions. Use
   `maxDimension` ≥ 2000 for a deck-quality render.
5. curl the PNG to disk (Bash).
6. Pass to mockup_executor.record_render(...).
```

#### Plugin API gotchas (codified from v0.1.1 incident)

1. **`layoutSizingHorizontal/Vertical` only work AFTER `appendChild`.**
   Setting them on a freshly-created frame silently no-ops because
   Figma's API requires an auto-layout parent. Either:
   - Use `layoutAlign='STRETCH'` (counter-axis fill) and
     `layoutGrow=1` (primary-axis fill) — these work pre-parent.
   - Or do a post-walk: build the tree first, then traverse and
     apply `layoutSizing*` to every node after the root is laid out.

2. **`counterAxisAlignItems` does NOT accept `'STRETCH'`.** Only
   `'MIN' | 'CENTER' | 'MAX' | 'BASELINE'`. To make a child stretch
   vertically inside a HORIZONTAL parent, use `layoutAlign='STRETCH'`
   on the child (not the parent's align).

3. **`resize(w, h)` on auto-layout frames locks the sizing mode.**
   After resize, the frame's `counterAxisSizingMode` becomes `FIXED`.
   If you wanted the frame to hug content vertically, set
   `primaryAxisSizingMode = 'AUTO'` *after* resize.

4. **Inter weights: use `"Semi Bold"` (with space), not `"SemiBold"`.**
   Same for "Extra Bold". Wrong spelling silently falls back to
   Regular at runtime.

5. **`figma.setCurrentPageAsync(page)` is required for page switching.**
   Plain `figma.currentPage = page` is not supported.

```python
import mockup_executor

mockup_spec = mockup_executor.record_render(
    task=task,
    slide_id="s07-product-demo",
    asset_id="01",
    figma_url="https://figma.com/design/abc123/Patient-portal?node-id=12:34",
    figma_file_key="abc123",
    figma_node_id="12:34",
    png_bytes=png_bytes,        # from get_screenshot
    svg_str=None,               # optional, if Figma exported SVG
    natural_w=480,              # from get_metadata or PIL
    natural_h=960,
    work_root="work",
)
```

`record_render` writes the files, appends to `work/mockups/INDEX.md`,
and returns the spec ready to drop into `content_plan["mockup_spec"]`.

## Phase 3 integration recipe

In your per-deck `scripts/build_phase_3.py`, after the orchestrator
decides a slide gets `image_decision.strategy = "mockup"`:

```python
from creator import make_slide_content_plan
import mockup_builder

# Author the brief (orchestrator decides this from ContextDoc)
task = mockup_builder.make_screen_desktop(
    brief="...",
    title=slide_topic,
    style="brand-vti",
)

# >>> ORCHESTRATOR PAUSE: Claude executes the Figma MCP loop here <<<
# After the render, Claude calls mockup_executor.record_render(...)
# and assigns the result to `spec` below.

# Wire into the content plan
content_plan = make_slide_content_plan(
    slide_id=slide_id,
    topic=slide_topic,
    blocks=blocks,
    image_decision={"strategy": "mockup"},
    section_name=section,
    layout_hint="pattern-b-image-narrative-side-by-side",
)
content_plan["mockup_spec"] = spec   # NEW field — parallel to diagram_spec
```

Phase 4 / layout_designer will need a follow-up patch to read
`mockup_spec` the same way it reads `diagram_spec` (see Integration
status below). Until that lands, the per-deck driver can construct a
fake `resolved_image` from the mockup_spec so the existing `lift`
branch of `_image_dims` picks it up:

```python
content_plan["image_decision"] = {"strategy": "lift", "source_hint": ""}
content_plan["resolved_image"] = {
    "path":      spec["png_path"],
    "natural_w": spec["natural_w"],
    "natural_h": spec["natural_h"],
    "kind":      "content",
    "score":     1.0,
}
```

## Style hints

`style="brand-vti"` pulls the VTI brand palette + type scale from
`vti-slide-page-builder/tokens.css` via `figma_styles`, and bakes the
following instructions into the Figma brief:

- Primary surfaces use VTI blue family
- Typography: Inter / system-ui, 14–22 px body, 24–32 px headings
- Corner radius: 8 px (cards), 14 px (buttons)
- Subtle shadows; no neon, no rainbow accents

`style="neutral"` strips brand styling — useful when the demo is of a
**third-party** product (a partner's app, a competitor's UI). The brief
uses generic "modern SaaS design system" language.

`style="dark-mode"` flips backgrounds to slate-900 / slate-800; text to
slate-100 / slate-300; accent stays brand-blue.

## Integration status — v0.1.0

| Layer | Status |
|---|---|
| `mockup_builder.make_*` (8 kinds) | ✅ Stable |
| `mockup_executor.record_render` | ✅ Stable |
| `figma_styles` (brand-vti pull) | ✅ Stable |
| Creator Phase 3 `mockup_spec` field | ⏳ Per-deck driver scaffold (creator change pending) |
| Phase 4 `_image_dims` reads `mockup_spec` | ⏳ Pending creator bump |
| Page-builder image-tile rendering | ✅ Works as-is (consumes PNG path) |

The per-deck driver workaround (lift-as-mockup) above is the supported
path until creator bumps to read `mockup_spec` natively.

## Reference

- Brand tokens source: `vti-slide-page-builder/tokens.css`
- Figma MCP server docs: `claude.ai Figma` instructions block
- Mandatory Figma skill: `/figma-use` (load before any `use_figma` call)
