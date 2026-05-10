# Chrome · header + footer

## 1. WHAT THIS IS
The shared top and bottom regions of every **content slide** in the deck
(content slides only — special pages like cover/closing/divider have their
own framing).

Both fragments here were derived directly from inspecting the three
reference decks (Software.pptx, GDC.pptx, Cloud.pptx). No values were copied
from any other Claude skill.

## 2. HEADER

### Components
- **Breadcrumb (top-left)** — a 3 px deep-blue vertical bar followed by a
  single-line caps title in gray. Two display patterns are supported and
  both are rendered by the composer based on what `slide_meta` carries:

  1. **Section only** — when only `section_name` is supplied. Renders as
     a single uppercase line, e.g. `ABOUT VTI GROUP`.
  2. **Section + title** — when BOTH `section_name` and `slide_title`
     are supplied. Renders as `SECTION | TITLE`, with the section in
     medium weight and the title in heavier weight (separator at 70%
     opacity). This is the canonical home for any per-slide title —
     content rows are reserved for actual content blocks. The composer
     uses the `.bc-section` / `.bc-sep` / `.bc-title` CSS classes to
     style the two parts differently.

  Sampled across GDC / Cloud / Software reference decks: both patterns
  occur in the wild. Earlier docs claimed only pattern 1 was canonical;
  that was a documentation drift, the renderer always supported both.

- **Logo (top-right)** — full VTI mark + tagline. Resolved by the
  `vti-logo` skill via the `<!-- VTI_LOGO_INJECT -->` marker.

### Placeholder
- `{{BREADCRUMB}}` → uppercase string, max ~40 chars (or the composed
  `<span class="bc-section">…</span> | <span class="bc-title">…</span>`
  fragment when the section + title pattern is used).

### Logo marker
```html
<!-- VTI_LOGO_INJECT position="top-right" variant="full-color" -->
```
The composer's `resolve_logo_markers()` replaces this with an
`<img class="logo-tr">` whose width comes from the canonical size table
`composer.CHROME_LOGO_DEFAULT_SIZES` (currently 92 px for `top-right`).
**Do NOT** add a `size="…"` attribute on layout/chrome markers — the
size is centralised so every content slide stays visually aligned.
Add an explicit `size=` only on a special page that genuinely needs
a different visual weight (e.g. cover/closing's larger display logo).

## 3. FOOTER

### Components (left → right)
1. **Chevron** — a forward-leaning parallelogram (clip-path angle ≈ -20°)
   filled `#0844A4`, holding the page number in white 22 px bold.
2. **Hairline separator** — 1 × 22 px, light gray.
3. **Doc title** — muted gray descriptor, e.g. `Corporate Profile - For
   Software Development`.

### Placeholders
- `{{PAGE_NUM}}` → zero-padded number, e.g. `03`
- `{{DOC_TITLE}}` → deck descriptor string

### Why a chevron, not a navy bar?
All three reference decks use this exact chevron pattern. The earlier
"navy footer bar" pattern that some legacy templates carried is NOT
present in the source PPTXs — it appears to be drift from a different
template family. We rebuilt to match what's actually in the decks.

## 4. SAFE ZONE
With the chrome above, content layouts get this usable area:

| edge   | offset | reason                                        |
|--------|--------|-----------------------------------------------|
| top    | 56 px  | clears the breadcrumb at y=24 + 16 line height |
| bottom | 56 px  | clears the chevron at y=22-58                 |
| left   | 60 px  | matches breadcrumb left edge                  |
| right  | 60 px  | mirrors left for symmetry                      |

Content area: **1160 × 608 px**.

## 5. INTEGRATION RULES
- Both header and footer are absolutely positioned. Content layouts must
  declare their own `<main>` region inside the safe zone — the chrome
  does not push content with margins.
- The breadcrumb text and doc title MUST be passed in by the orchestrator.
  Hard-coding them here would defeat reuse across decks.
- The logo asset bytes MUST come from `vti-logo`. Do not embed base64 in
  this skill.
