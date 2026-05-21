# vti-slide-figma-mockup — changelog

## v0.2.4 — 2026-05-20 — macOS Tahoe / Liquid Glass chrome + SF Pro body

`slide-hero` / `slide-mini` mac-window updated to a macOS Tahoe (26)
look so the mockup chrome matches the latest macOS aesthetic when the
slide content is itself a Mac-style UI.

**Window chrome:**
- Corner radius `11px` → `14px`
- Titlebar `30px` → `38px`; layered translucent gradient (rgba whites
  over `#F6F6F8 → #ECECEF`) with `backdrop-filter: blur(20px) saturate(180%)`
  for a Liquid Glass tone; thinner low-contrast bottom divider
- Traffic lights: solid fills replaced by radial gradients (light
  top-left highlight → mid → darker base) plus an inset bevel, for the
  Tahoe-style softer "pill" feel
- Drop shadow deepened (`0 18px 48px / 0 4px 12px`) to match the larger
  radius and Tahoe's softer-but-richer elevation; top edge gets a
  1px white inset highlight

**Body typography:**
- New CSS token `--font-mac` = `-apple-system, BlinkMacSystemFont,
  'SF Pro Text', 'SF Pro Display', 'Helvetica Neue', system-ui, sans-serif`
  exposed in all three theme blocks (brand-vti / neutral / dark-mode)
- `.mac-body` now sets `font-family: var(--font-mac); font-size: 14px;`
  with `letter-spacing: -0.005em` and antialiased smoothing —
  authentic macOS look-and-feel without affecting non-mac mockup kinds
  (browser/phone/flow still use the Plus Jakarta Sans brand stack).

Per-deck drivers should bump their inline `font-size:` values ~+2px
when targeting `slide-hero` / `slide-mini` (text reads bigger relative
to the slide canvas). The s07/s08/s09/s12 driver has already been
updated.

**Liquid Glass body wallpaper:**
- `.mac-body` background is now a VTI-tinted radial mesh
  (blue / violet / sky corners over a near-white linear base) — gives
  per-deck driver cards something to be glass over. The wallpaper is
  brand-tinted on purpose so glass cards read as VTI-tinted, not
  generic macOS.
- Driver-side card recipe for glass material (per-deck CSS):
  ```css
  .card-like {
    background: rgba(255, 255, 255, 0.62);
    backdrop-filter: blur(28px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.55);
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.80),
      0 6px 20px rgba(31, 42, 58, 0.07);
  }
  ```
  For colored panels, swap the white-translucent fill for a brand
  color at the same alpha (e.g. `rgba(234, 242, 251, 0.50)` for blue).
  The `build_mockups_v2.py` driver demonstrates the full recipe.

## v0.2.3 — 2026-05-20 — fix clipped mac-window shadow

`.mac-window` (`slide-hero` / `slide-mini`) had 14px inset against a
viewport sized to match — only 14px of transparent canvas around the
window for a drop shadow that needs ~24px above, ~48px below, and
~36px on the sides to fade naturally. The shadow was being hard-clipped
at the PNG edge, producing a visible dark strip just outside the
window (most obvious along the bottom).

**Fix:** padded both viewport and inset so the shadow has room.
- `slide-hero` viewport: (1600, 900) → (1680, 1000)
- `slide-mini` viewport: (1800, 900) → (1880, 1000)
- `.mac-window` inset: `14px` all sides → `top:50; left:40; right:40; bottom:60`

Window content area stays ≈1600×890, so downstream layout math (image
tile sizing in page-builder) is unaffected. PNG output grows ~5% per
dimension; page-builder downscales as before.

Re-render existing `slide-hero` / `slide-mini` mockups under `work/mockups/`
to pick up the fix (re-running the per-deck `build_phase_3.py` is enough).

## v0.2.0 — 2026-05-20 — HTML backend (default)

**New default backend: `html`.** Renders fully locally via Playwright +
headless Chromium, no external quota, deterministic output, editable
HTML source travels with the PNG. The Figma backend stays available
via `backend="figma"` (or `VTI_MOCKUP_BACKEND=figma` env) for when
stakeholders want to co-edit in Figma.

**Why:** the v0.1.x Figma path proved brittle in practice — Starter
plan caps at 6 MCP calls/MONTH, Plugin API has subtle gotchas
(layoutSizing requires parenting, STRETCH invalid for
counterAxisAlignItems, resize locks sizing mode), and Claude has to
hand-write JS rather than the brief itself. HTML+CSS is the natural
medium for both production and iteration.

**New modules / entry points:**

- `html_backend.py` — frame templates (browser chrome, phone bezel,
  flow strip), brand-vti / neutral / dark-mode token CSS, atom CSS
  classes (.av, .chip, .card, .sec-hdr-*, .spark, .check, etc.),
  Playwright `render_to_png()`.
- `mockup_executor.record_html_render(task, slide_id, asset_id, screens, work_root, scale)`
  — full pipeline: builds HTML doc via `html_backend.frame_html()`,
  renders PNG, writes `render.png` + `source.html` + `meta.json`,
  appends INDEX.md.
- `mockup_builder.make_*` — now accepts `backend="html"|"figma"`
  (default `"html"`); HTML tasks carry `html_brief` instead of `brief`.
- Env var: `VTI_MOCKUP_BACKEND` flips the default.

**Worked example landed:** `scripts/build_s12_mockup.py` renders the
s12 day-in-life flow-desktop (3 screens × ~600px wide) to
`work/mockups/s12-day-in-life_01/render.png` at 4000×2400 (retina @2×).
Verified end-to-end.

**Atom classes** documented in SKILL.md → "HTML backend → Atom classes
available in html_backend" — the contract for orchestrators authoring
body_html per slide.

**Spec shape additions** (v0.2.0 `mockup_spec`):
- `backend: "html" | "figma"` — discriminator
- `html_path: str | None` — path to editable HTML source (html backend)
- `scale: int` — device scale factor for the PNG
- `figma_url/figma_file_key/figma_node_id` — now optional (null when backend=html)

**Decision criteria:**
- Use **html** for: production decks, iteration speed matters, the
  user wants the source as a hand-editable file, output goes into
  page-builder image-tile.
- Use **figma** for: stakeholder co-editing, hand-off to design team,
  the deck has a budget for Figma seats + the team works there.

## v0.1.1 — 2026-05-20 (same-day patch)

**Docs only.** First real Figma render (deck `VTI_Day-to-Day-Info-Summarization-Agent`
slide s12 — flow-desktop, 3 screens) exposed two gaps in the v0.1.0
SKILL.md that misled the orchestrator. Patched the contract so future
sessions don't repeat:

1. **`use_figma` takes JS code, not a natural-language brief.** v0.1.0
   implied the brief was passed directly to `use_figma`. Updated
   "Two-step orchestration" to spell out the brief→JS translation step
   and reference the Plugin API (`figma.createFrame`, `appendChild`,
   `layoutMode`, fills, fonts).

2. **Auto-layout sizing trap.** `layoutSizingHorizontal/Vertical = 'FILL'`
   set on a frame BEFORE it's appended to an auto-layout parent
   silently no-ops. v0.1.1 SKILL.md now documents three workarounds
   (post-parent setting / `layoutAlign='STRETCH'` + `layoutGrow=1` /
   post-walk pass) and three other Plugin API gotchas (`STRETCH` not
   valid for `counterAxisAlignItems`, `resize()` locks sizing mode,
   Inter weights need a space).

3. **Rate-limit reminder.** Figma Starter plan is **6 MCP calls per
   MONTH**, not per hour. `whoami` / `generate_figma_design` /
   `add_code_connect_map` are exempt; `use_figma` and `get_screenshot`
   both count. Plan iterations carefully — the per-month cap means
   a sloppy first render can burn most of the quota.

The s12 render itself is in `work/mockups/s12-day-in-life_01/` with
`fix-layout.js` (1-call repair script) and a `KNOWN_BUG.md` analysis.
Finishing the render is blocked on quota reset (~30 days) or a plan
upgrade.

## v0.1.0 — 2026-05-20

Initial release. High-fidelity UI mockup / wireframe / demo screenshot
producer for VTI slide decks, fronted by Figma MCP.

**Public API:**

- `mockup_builder.make_screen_mobile`, `make_screen_tablet`,
  `make_screen_desktop`, `make_screen_bare`
- `mockup_builder.make_flow_mobile`, `make_flow_desktop`
- `mockup_builder.make_wireframe_mobile`, `make_wireframe_desktop`
- `mockup_builder.{list_kinds, describe_kind, call}`
- `mockup_executor.record_render` — lands Figma output to
  `work/mockups/<id>/{render.png, render.svg?, meta.json}` and appends
  `work/mockups/INDEX.md`.
- `mockup_executor.load_meta` — resume helper.
- `mockup_executor.to_resolved_image` — legacy `resolved_image` shape
  adapter (v0.1.0 stop-gap until creator reads `mockup_spec` natively).
- `figma_styles.{brand_style_block, neutral_style_block,
  dark_style_block}` — style-instruction paragraphs. Named `figma_styles`
  rather than `theme_bridge` to avoid namespace collision with
  `vti-slide-diagram-builder/theme_bridge.py` (which serves the SVG
  color-accent API).

**Pipeline integration (v0.1.0 stop-gap):** Per-deck `build_phase_3.py`
drivers wire mockups in via the existing `lift` strategy using
`to_resolved_image()`. Native `image_decision.strategy="mockup"` +
`mockup_spec` reading by `layout_designer._image_dims` is deferred to a
follow-up creator bump (no code change required to creator at v0.1.0).

**Hint canvases per kind:**

| Kind | Canvas | Frame |
|---|---|---|
| screen-mobile     | 480 × 960  | iPhone 15 Pro |
| screen-tablet     | 1024 × 768 | iPad landscape |
| screen-desktop    | 1440 × 900 | Chrome / macOS |
| screen-bare       | 1180 × 740 | (none) |
| flow-mobile       | 1440 × 960 | 3 × iPhone |
| flow-desktop      | 1620 × 540 | 3 × Browser |
| wireframe-mobile  | 480 × 960  | mono iPhone |
| wireframe-desktop | 1440 × 900 | mono browser |

**Outstanding work:**

- Creator side: add `mockup_spec` field to `make_slide_content_plan`
  and read it from `layout_designer._image_dims`. Bumps creator to
  4.7.0 + COORDINATED_BASELINE.md update.
- Decorator: confirm that mockup images don't trigger unwanted gap-fill
  decoration on hi-density slides (currently no known issue).
- Validation: a `verify-time` check that asserts every
  `image_decision.strategy=="mockup"` plan has a corresponding
  `mockup_spec` with a readable PNG.
