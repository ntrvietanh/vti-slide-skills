# vti-slide-page-builder-v3 · component catalog

_v3.0.0_ — 37 atomic components across 8 categories.

Every component is grid-flexible: it works at any `col_span` (1-12) and `row_span` (1-N) within a slide's 12-column grid. Charts use SVG `viewBox` to scale; tables use CSS `minmax(0, 1fr)` columns; text blocks flex naturally.

Emphasis design rule: the VTI brand blue (`var(--vti-blue-deep)` or `var(--vti-navy)`) is ALWAYS used for emphasis in slides. Tints/shades for variation, grays for de-emphasis. NO yellow/amber.

## Quick reference

- **stats** (5) — `kpi-row`, `stat-hero`, `stat-mini`, `trend-stat`, `value-medallion`
- **text-paragraph** (8) — `callout`, `headline`, `kicker`, `lead-paragraph`, `narrative-paragraph`, `pull-quote`, `quote-block`, `section-header`
- **text-list** (5) — `bullet-list-checked`, `definition-list`, `icon-list`, `numbered-list`, `tags`
- **card** (2) — `catalog-column`, `practice-card`
- **visual** (2) — `image-tile`, `logo-grid`
- **table** (2) — `comparison-table`, `table`
- **chart** (6) — `bar-chart`, `gauge-dial`, `line-chart`, `pie-chart`, `progress-bar`, `stacked-bar`
- **diagram** (7) — `before-after`, `funnel`, `process-flow`, `quadrant-matrix`, `swimlane`, `timeline`, `vs-divider`

## stats

_Numeric values + labels. KPIs, hero stats, supporting numbers._

### `kpi-row`

**Role.** Horizontal strip of 2-5 stat-mini cards.

**Kind:** `data`

**Schema:** `items: list[{icon, value, label}] (2-5 items)`

**Best col_spans:** [12]  ·  **Natural height:** `auto`

**Use for:**
- supporting metrics row at bottom of slide
- quick fact strip below a hero

**Don't use for:**
- 1 single stat (use stat-hero)
- >5 items (split across 2 rows or use a different shape)

**Block kind aliases:** `supporting_stats`

### `stat-hero`

**Role.** Dominant single stat (84-128px font) — anchors a slide visually around 1 number.

**Kind:** `data`

**Schema:** `value: str≤8, label: str≤30, decoration?: 'rings'|'none'`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `1fr (centered) or auto`

**Use for:**
- headline metric / scale claim
- dominant number paired with narrative
- single-stat focal point

**Don't use for:**
- multiple stats (use kpi-row)
- supporting context number (use stat-mini)

**Block kind aliases:** `hero_stat`

### `stat-mini`

**Role.** Compact stat card (icon disc + value + label) for tight slots — typically used as a child of kpi-row.

**Kind:** `data`

**Schema:** `icon: str, value: str≤8, label: str≤30, tone?: 'default'|'white'`

**Best col_spans:** [3, 4]  ·  **Natural height:** `auto`

**Use for:**
- supporting metric (paired with hero stat or narrative)
- single cell in a kpi-row

**Don't use for:**
- primary headline number (use stat-hero)
- stand-alone hero (too small)

### `trend-stat`

**Role.** Single KPI value + delta arrow + period descriptor. Like stat-mini but with directional movement (▲ up green, ▼ down red, — flat gray).

**Kind:** `data`

**Schema:** `value: str, delta: str (e.g. '+18.3%'), trend: 'up'|'down'|'flat', period?: str, label?: str, size?: 'small'|'default'`

**Best col_spans:** [3, 4, 5, 6]  ·  **Natural height:** `auto`

**Use for:**
- QoQ / YoY KPI movements (revenue +18% vs Q3)
- scoreboard panels (3-4 trend-stats in a row)

**Don't use for:**
- single static stat (use stat-hero / stat-mini)
- category comparisons (use bar-chart)

**Block kind aliases:** `trend_stat`, `kpi_movement`

### `value-medallion`

**Role.** Vertical icon disc + title + tagline — for short labels (4-6 peers).

**Kind:** `card`

**Schema:** `icon: str, title: str≤22, tagline?: str≤60, number?: str, color_tone?: tone|hex`

**Best col_spans:** [2, 3]  ·  **Natural height:** `auto`

**Use for:**
- 4-6 values / pillars / principles
- icon-led short labels in a row

**Don't use for:**
- 1-2 items (looks empty)
- items with body paragraphs (use practice-card)

**Block kind aliases:** `values`

## text-paragraph

_Single text blocks — paragraphs, headlines, eyebrow labels, callouts, quotes._

### `callout`

**Role.** Emphasized text block (note / warn / tip / deep) with colored left border + icon + optional title.

**Kind:** `text`

**Schema:** `tone: 'info'|'warn'|'tip'|'deep' (default 'info'), text: str, title?: str, icon?: str (override default)`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- key takeaway above content
- warning / caveat in a slide
- tip / best-practice note

**Don't use for:**
- long-form prose (use narrative-paragraph)
- decoration without semantic emphasis

**Block kind aliases:** `callout`, `note`, `warning`, `tip`

### `headline`

**Role.** Big inline hero statement for content slides — distinct from the chrome breadcrumb (slide title). 26px / 36px sizes. Optional leading vertical bar accent for stronger anchor.

**Kind:** `text`

**Schema:** `text: str, size?: 'medium'|'large' (default 'medium'), color?: 'deep'|'navy'|'ink' (default 'deep'), align?: 'left'|'center' (default 'left'), show_bar?: bool (default false — leading vertical bar accent)`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- hero statement that sets the slide's main argument
- section opener inside a content slide
- punchy 1-sentence summaries

**Don't use for:**
- small section labels (use kicker)
- body-text paragraphs (use narrative-paragraph)
- data values (use stat-hero)

**Block kind aliases:** `headline`, `hero_statement`

### `kicker`

**Role.** Small uppercase eyebrow / kicker label — sits ABOVE a headline, narrative, image, or chart to label the section / topic. Optional thin underline (rule: true).

**Kind:** `text`

**Schema:** `text: str (≤40 chars), rule?: bool (default false — show underline), align?: 'left'|'center' (default 'left')`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `auto`

**Use for:**
- eyebrow above a headline ('OUR APPROACH' → big headline)
- section labels above visual content
- category / topic markers

**Don't use for:**
- regular section title (use section-header)
- main slide title (use chrome breadcrumb)
- long sentences (kicker is for 1-4 words)

**Block kind aliases:** `kicker`, `eyebrow`, `topic_label`

### `lead-paragraph`

**Role.** Opening paragraph (the 'lede') — larger and heavier than narrative-paragraph (17px / weight 500 vs 14px / weight 400). Use to introduce a content slide before the body text. Inline **emphasis** wraps in <strong> with VTI blue color.

**Kind:** `text`

**Schema:** `text: str OR paragraphs: list[str], align?: 'left'|'center' (default 'left'), tone?: 'default'|'muted' (default 'default')`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- first paragraph on a content slide
- executive summary text
- topic sentence above a chart or list

**Don't use for:**
- regular body paragraphs (use narrative-paragraph)
- single-sentence hero statement (use headline)

**Block kind aliases:** `lead_paragraph`, `lede`

### `narrative-paragraph`

**Role.** 1-4 paragraph body text with optional **emphasis** wrapping.

**Kind:** `text`

**Schema:** `paragraphs: list[str≤400] (1-4 items), align?: 'left'|'center', max_width?: str (e.g. '780px')`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `auto`

**Use for:**
- intro / framing prose under a heading
- body of explanatory slide
- callout text beside a stat or visual

**Don't use for:**
- lists (use bullet-list-checked instead)
- long-form copy (>4 paragraphs splits across slides)

**Block kind aliases:** `narrative`

### `pull-quote`

**Role.** Editorial pull-out quote — large italic text with big opening quote mark. Different from quote-block (which has structured name/role/company attribution). pull-quote is for memorable phrases pulled from prose; attribution is optional and free-form.

**Kind:** `text`

**Schema:** `text: str, attribution?: str, size?: 'default'|'large' (default 'default'), align?: 'left'|'center' (default 'left')`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- memorable phrase highlight on a content slide
- editorial / book-style quote
- key insight pulled from a longer passage

**Don't use for:**
- structured testimonial (use quote-block)
- factual statement / claim (use callout)
- long passages (pull-quote is 1-2 sentences max)

**Block kind aliases:** `pull_quote`, `editorial_quote`

### `quote-block`

**Role.** Pull quote / testimonial with optional attribution (name, role, company). Two visual styles — hero (centered) or card (pale-blue background with corner quote mark).

**Kind:** `text`

**Schema:** `quote: str≤320, attribution?: {name: str, role?: str, company?: str}, style?: 'hero'|'card' (default 'card'), accent?: 'deep'|'navy'|'sky' (default 'deep')`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- single customer testimonial
- leadership statement / mission quote
- press review pull quote

**Don't use for:**
- multiple peer quotes — they need their own slides
- long-form text (use narrative-paragraph)

**Block kind aliases:** `quote`, `testimonial`

### `section-header`

**Role.** Small bold heading for grouping content within a row or column (e.g. 'Customer Problems' above a bullet list, 'Key metrics' above a kpi-row). One step DOWN from the slide-level subhead or chrome breadcrumb.

**Kind:** `text`

**Schema:** `title: str≤40, size?: 'small'|'default'|'large' (default 'default'), rule?: bool (default false — show thin underline)`

**Best col_spans:** [3, 4, 5, 6, 7, 8, 12]  ·  **Natural height:** `auto`

**Use for:**
- labeling a section within a multi-section column
- title above bullet-list-checked / narrative-paragraph / kpi-row
- subhead inside a case-study right-column section group

**Don't use for:**
- main slide title (use the chrome breadcrumb)
- case-study slide subhead (use the layout's own subhead field)
- stat values (use stat-mini / stat-hero)

**Block kind aliases:** `section_header`, `subhead`

## text-list

_Multi-item text collections — bullets, numbered lists, key-value pairs, tags._

### `bullet-list-checked`

**Role.** Vertical list with check-icon bullets.

**Kind:** `text`

**Schema:** `items: list[str≤100] (2-8 items), density?: 'compact'|'default'|'loose'`

**Best col_spans:** [4, 5, 6, 7]  ·  **Natural height:** `auto`

**Use for:**
- feature list / capability list
- comparison panel content
- benefit highlights

**Don't use for:**
- numbered sequence (use practice-card with number instead)
- single short statement (use narrative-paragraph)

**Block kind aliases:** `list`

### `definition-list`

**Role.** Term: value pairs. horizontal layout = term on left (uppercase blue), value on right (ink). stacked layout = term above (small uppercase), value below (larger). Use for spec sheets, capability summaries, key-value pairs.

**Kind:** `text`

**Schema:** `items: list[{term, value}], layout?: 'horizontal'|'stacked' (default 'horizontal'), density?: 'compact'|'default'|'loose' (default 'default')`

**Best col_spans:** [3, 4, 5, 6, 7, 8]  ·  **Natural height:** `auto`

**Use for:**
- company spec sheet (Engineers: 1,200+; Hubs: 4)
- capability summary (Languages: VN/JP/KR/EN)
- after-image data block on a slide

**Don't use for:**
- rich tabular data (use table)
- feature comparison (use comparison-table)
- single statistic (use stat-hero / stat-mini)

**Block kind aliases:** `definition_list`, `key_value`, `spec_sheet`

### `icon-list`

**Role.** Items each with a custom icon + title + optional body text. Richer than bullet-list-checked — use when each item warrants its own visual identity.

**Kind:** `text`

**Schema:** `items: list[{icon, title, body?}], density?: 'compact'|'default'|'loose' (default 'default'), icon_style?: 'plain'|'circle' (default 'plain')`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `auto`

**Use for:**
- feature list with capability icons
- value-add bullets with thematic icons
- service catalog rows

**Don't use for:**
- homogeneous bullets (use bullet-list-checked)
- single item (use callout)

**Block kind aliases:** `icon_list`, `feature_list`

### `numbered-list`

**Role.** Items with prominent numbered anchors (01, 02, 03 …). Use when ORDERING is meaningful — vs bullet-list-checked which is for set-of-things. Items can be plain strings OR dicts with {title, body} for richer entries.

**Kind:** `text`

**Schema:** `items: list[str | {title, body?}], density?: 'compact'|'default'|'loose', number_style?: 'circle'|'block' (default 'circle')`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `auto`

**Use for:**
- ordered steps in a methodology
- ranked list (top 5 priorities)
- phased plan with descriptions

**Don't use for:**
- unordered sets (use bullet-list-checked)
- key-value pairs (use definition-list)
- process flow visualization (use process-flow / timeline)

**Block kind aliases:** `numbered_list`, `ordered_list`, `ranked_list`

### `tags`

**Role.** Inline pill chips for categorization / capability badges. 4 tones: solid (deep/medium/sky) for prominence, soft (pale blue bg + deep blue text) for many-tag scenarios. Wrap to multiple rows automatically.

**Kind:** `text`

**Schema:** `items: list[str], tone?: 'deep'|'medium'|'sky'|'soft' (default 'soft'), size?: 'default'|'small' (default 'default')`

**Best col_spans:** [4, 5, 6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- capability list under an image-tile or headline
- category markers ('AI · Cloud · Data')
- tech stack badges (Python · React · Kubernetes)

**Don't use for:**
- long phrases (tags are 1-3 words each)
- ranked / ordered lists (use numbered-list)
- single emphasis label (use kicker)

**Block kind aliases:** `tags`, `chips`, `badges`

## card

_Richer single units — number/icon/title/body composites._

### `catalog-column`

**Role.** Colored header band + chevron rows + count badge — for service catalogs.

**Kind:** `card`

**Schema:** `label: str≤24, category_icon: str, items: list[str|{text, tag?}] (2-8), count_text?: str, color_tone?: tone|hex`

**Best col_spans:** [4, 6]  ·  **Natural height:** `auto`

**Use for:**
- categorized service / feature list (2-3 categories)
- items grouped by track/phase/tier with optional tag pills

**Don't use for:**
- single uncategorized list (use bullet-list-checked)
- narrative content (no body in this component)

**Block kind aliases:** `catalog`

### `practice-card`

**Role.** Hero card with colored top half (icon + title) and white body — for 3 peer practice areas / capabilities / steps.

**Kind:** `card`

**Schema:** `title: str≤28, body: str≤220, icon: str, number?: str, color_tone?: 'deep'|'medium'|'sky'|'navy'|hex`

**Best col_spans:** [3, 4, 6]  ·  **Natural height:** `auto`

**Use for:**
- 3 peer practice areas / capabilities
- numbered step or principle (1-4)
- dominant feature card

**Don't use for:**
- 5+ peer items (cards too narrow)
- short labels alone (use value-medallion)

**Block kind aliases:** `features_3`

## visual

_Image and logo content._

### `image-tile`

**Role.** Single image inside a sized frame, with optional caption — for office photos, screenshots, illustrations, products.

**Kind:** `media`

**Schema:** `image: str (path or URL), caption?: str≤120, aspect_ratio?: 'W:H' (default '16:9'), frame?: 'rounded'|'soft'|'square', caption_position?: 'overlay'|'below'|'none'`

**Best col_spans:** [4, 5, 6, 7, 8]  ·  **Natural height:** `1fr`

**Use for:**
- single hero photo paired with text
- office building / team photo
- product or screenshot reference
- diagram or illustration

**Don't use for:**
- multiple peer logos (use logo-grid)
- icon only (use practice-card or stat-mini)

**Block kind aliases:** `image`, `photo`

### `logo-grid`

**Role.** Even N-column grid of partner / customer / award logos. Three tone modes (color, muted, monochrome) handle visual compatibility when many brands clash.

**Kind:** `media`

**Schema:** `logos: list[{image?: str, name?: str}] (>=2), cols?: int 3-6 (default 4), tone?: 'color'|'muted'|'monochrome' (default 'muted'), density?: 'loose'|'compact'`

**Best col_spans:** [12]  ·  **Natural height:** `auto`

**Use for:**
- trusted-by row (8-12 customer logos)
- strategic partners callout (4-6 logos)
- awards & certifications row

**Don't use for:**
- single hero logo (just use an image-tile)
- logos that need bullet copy each (use practice-card)

**Block kind aliases:** `logos`, `partners`, `trust_signals`

## table

_Tabular structured data._

### `comparison-table`

**Role.** Feature comparison matrix — distinct from data table. Cells render booleans as ✓ / ✕ icons, level keywords ('best'/'good'/'fair') as colored dot indicators, and strings as text. One column can be highlighted as the 'recommended' option.

**Kind:** `data`

**Schema:** `columns: list[{name, highlight?}] (Option A/B/C — first column implicitly the feature names), rows: list[{feature, values: list[bool|str|level_keyword]}]`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- vendor / option comparison
- feature matrix across product tiers
- build vs buy decision matrix

**Don't use for:**
- pure numeric tabular data (use table)
- single feature deep dive (use bullet-list)

**Block kind aliases:** `comparison_table`, `feature_matrix`

### `table`

**Role.** Generic data table — rows × columns of values with optional header row, per-column alignment, highlighted rows, and first-column emphasis. Use for revenue tables, KPI scorecards, specification matrices.

**Kind:** `data`

**Schema:** `headers: list[str], rows: list[list[str]], alignment?: list['left'|'center'|'right'], column_widths?: list[str], highlight_rows?: list[int], first_col_emphasis?: bool, density?: 'compact'|'default'|'loose'`

**Best col_spans:** [4, 5, 6, 7, 8, 9, 10, 11, 12]  ·  **Natural height:** `auto`

**Use for:**
- tabular numeric data (revenue by quarter)
- label/value pairs (config table)
- feature specifications (model x capability)

**Don't use for:**
- feature comparison with check/x (use comparison-table instead)
- single KPI display (use stat-hero / stat-mini)

**Block kind aliases:** `table`, `data_table`

## chart

_Data visualizations — bars, pies, lines, progress, gauges._

### `bar-chart`

**Role.** Categorical bar chart — vertical (column) or horizontal orientation. Renders as inline SVG with viewBox so it scales to any cell size. Single-series only — for multi-series use stacked-bar (Phase E4).

**Kind:** `data`

**Schema:** `items: list[{label, value, tone?}], orientation?: 'vertical'|'horizontal' (default vertical), title?: str, show_values?: bool (default true), y_label?: str, max_value?: number`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `1fr or auto with min ~200px`

**Use for:**
- quarterly revenue / volume comparisons
- ranked category data (top-N)
- before / after comparisons (2-3 bars)

**Don't use for:**
- share of whole (use pie-chart)
- trend over time with many points (use line-chart)
- multi-series comparison (use stacked-bar)

**Block kind aliases:** `bar_chart`, `column_chart`

### `gauge-dial`

**Role.** Semicircular gauge showing a single metric with min/max endpoints and a color-coded fill arc. Center text shows current value + suffix (e.g. '/100', '%').

**Kind:** `data`

**Schema:** `value: number, max?: number (default 100), value_text?: str (display override), suffix?: str (default '/100'), label?: str, tone?: 'deep'|'medium'|'sky'|'navy'|'success'|'warning'`

**Best col_spans:** [3, 4, 5, 6]  ·  **Natural height:** `auto (~160-200px)`

**Use for:**
- CSAT / NPS scoreboard
- single-metric headline (target progress)
- service health summary

**Don't use for:**
- multi-metric comparison (use kpi-row)
- non-bounded values (use stat-hero)

**Block kind aliases:** `gauge`, `gauge_dial`

### `line-chart`

**Role.** Single-series line chart for trend over time. Optional area fill below the line, optional dot markers + value labels at each point.

**Kind:** `data`

**Schema:** `items: list[{label, value}], area_fill?: bool (default true), show_dots?: bool (default true), show_values?: bool (default false), title?: str`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `1fr or auto with min ~200px`

**Use for:**
- trend over time (revenue, signups, traffic)
- delta-from-target tracking

**Don't use for:**
- categorical comparison (use bar-chart)
- composition (use stacked-bar)
- very few data points <3 (use trend-stat)

**Block kind aliases:** `line_chart`, `trend_chart`

### `pie-chart`

**Role.** Share-of-whole pie or donut chart with optional center label and legend on right (default) or below (for narrow cells). Auto-percentage from absolute values.

**Kind:** `data`

**Schema:** `items: list[{label, value, color?}], donut?: bool (default false), center_value?: str, center_label?: str, layout?: 'legend-right'|'legend-below' (default legend-right)`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `1fr or auto with min ~200px`

**Use for:**
- market share / customer mix
- budget allocation
- team / capability breakdown

**Don't use for:**
- trend over time (use line-chart)
- ranked comparison (use bar-chart)
- more than ~7 segments (becomes unreadable)

**Block kind aliases:** `pie_chart`, `donut_chart`, `share_chart`

### `progress-bar`

**Role.** One or more horizontal % completion bars with label + value. Multi-bar mode shows several metrics stacked.

**Kind:** `data`

**Schema:** `items: list[{label, value, max?, tone?, value_text?}], (value is 0-100 or 0-max if max specified)`

**Best col_spans:** [4, 5, 6, 7, 8, 12]  ·  **Natural height:** `auto`

**Use for:**
- migration / rollout progress dashboards
- OKR / goal tracking with multiple KRs
- capability maturity ratings

**Don't use for:**
- single static stat (use stat-mini)
- categorical comparison (use bar-chart)

**Block kind aliases:** `progress_bar`, `progress_bars`, `okr_tracker`

### `stacked-bar`

**Role.** Multi-series stacked bar chart. Each category (x-axis) shows a single bar made of stacked segments (one per series).

**Kind:** `data`

**Schema:** `categories: list[str], series: list[{name, color?, values: list[number]}], title?: str`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `1fr or auto with min ~250px`

**Use for:**
- revenue mix over quarters
- headcount composition by region over years
- any composition-over-categories pattern

**Don't use for:**
- single series (use bar-chart)
- trend over time without composition (use line-chart)

**Block kind aliases:** `stacked_bar`, `composition_chart`

## diagram

_Process flows, timelines, matrices, structural relationships._

### `before-after`

**Role.** Two-panel split with arrow between — left = before state (gray), right = after state (blue accent). Use for transformation, migration outcomes, problem→solution narratives.

**Kind:** `comparison`

**Schema:** `before: {label?, title, items: list[str]}, after:  {label?, title, items: list[str]}`

**Best col_spans:** [8, 10, 12]  ·  **Natural height:** `auto`

**Use for:**
- before/after of a transformation
- manual vs automated process comparison

**Don't use for:**
- more than 2 states (use comparison-table)
- non-temporal comparison (use side-by-side narrative)

**Block kind aliases:** `before_after`, `transformation`

### `funnel`

**Role.** Sequential reduction funnel — each stage narrower than the last based on its absolute value, with the % drop from previous (or % of top) shown alongside.

**Kind:** `diagram`

**Schema:** `stages: list[{label, value, color?}], show_pct_of_top?: bool (default true)`

**Best col_spans:** [4, 5, 6, 7, 8]  ·  **Natural height:** `1fr or auto with min ~250px`

**Use for:**
- sales / conversion funnels
- qualification pipelines
- drop-off analysis

**Don't use for:**
- non-monotonic series (some segments could go up — funnel implies decrease)
- more than 6 stages (becomes cramped)

**Block kind aliases:** `funnel`, `conversion_funnel`

### `process-flow`

**Role.** Sequence of 3-7 numbered steps with chevron connectors — for methodology, project lifecycle, customer journey explanations.

**Kind:** `structural`

**Schema:** `steps: list[{title: str≤30, body?: str≤140, number?: str, icon?: str}] (3-7 entries), direction?: 'horizontal'|'vertical' (default 'horizontal'), accent?: 'deep'|'navy'|'sky'`

**Best col_spans:** [12]  ·  **Natural height:** `auto`

**Use for:**
- 3-7 step methodology
- project lifecycle (Discover → Design → Deliver → Run)
- decision flow / customer journey

**Don't use for:**
- 2 steps (use a vs-divider or two practice-cards)
- 8+ steps (split across two slides)
- non-sequential peers (use catalog-column or practice-card)

**Block kind aliases:** `process`, `steps`, `methodology`

### `quadrant-matrix`

**Role.** 2×2 strategic positioning matrix. Each quadrant has a label and a list of items. Highlight one quadrant for emphasis (e.g. 'quick wins').

**Kind:** `diagram`

**Schema:** `x_start: str, x_end: str, y_start: str, y_end: str, quadrants: {tl: {label, items, highlight?}, tr: {...}, bl: {...}, br: {...}}`

**Best col_spans:** [6, 7, 8, 10, 12]  ·  **Natural height:** `auto (~280-320px)`

**Use for:**
- effort × impact prioritization
- BCG growth-share matrix
- feasibility × value mapping

**Don't use for:**
- more than 4 categories (use a different chart)
- continuous data (use scatter — out of scope)

**Block kind aliases:** `quadrant`, `matrix_2x2`

### `swimlane`

**Role.** Multi-actor process diagram with horizontal lanes (one per actor) × columns (one per step). Two density modes: 'compact' (default) shows title + small icon per step; 'rich' adds a body paragraph per step describing what happens. Empty steps render as hatched cells. Steps can be marked accent for the key handoff in a flow.

**Kind:** `diagram`

**Schema:** `lanes: list[{name, tone?, steps: list[{title, icon?, body?, accent?: bool} | None]}], density?: 'compact'|'rich' (default compact), step_count?: int (auto from longest lane)`

**Best col_spans:** [8, 10, 11, 12]  ·  **Natural height:** `compact: auto (~60px per lane); rich: ~110px+ per lane`

**Use for:**
- customer journey across actors (Customer / System / Support)
- release process across teams
- data pipeline showing transitions and what each stage does (rich)

**Don't use for:**
- single-track linear flow (use process-flow)
- free-form network / non-linear structures

**Block kind aliases:** `swimlane`, `process_lanes`

### `timeline`

**Role.** Card-based events on a time axis. Each event = a richer card with optional body, deliverables list (✓ bullets), and metric badge (e.g. '+28% / conversion'). Horizontal = events distributed left-to-right with track running through dots; vertical = events stacked top-to-bottom with track on left. Milestone items get an navy-accented card + larger navy dot (deeper than regular events).

**Kind:** `diagram`

**Schema:** `items: list[{date, title, body?, deliverables?: list[str], metric?: {value, label}, milestone?: bool}], orientation?: 'horizontal'|'vertical' (default horizontal)`

**Best col_spans:** [6, 8, 10, 12]  ·  **Natural height:** `auto (~150-220px horizontal depending on card content; ~80px per event vertical)`

**Use for:**
- project phases by quarter with deliverables shipped
- company milestones with KPI deltas at each step
- rollout plan over months — what was delivered when

**Don't use for:**
- non-temporal sequences (use process-flow)
- more than ~5 events horizontally (cards become cramped — use vertical)

**Block kind aliases:** `timeline`

### `vs-divider`

**Role.** VS badge with optional connecting line — sits between 2 panels.

**Kind:** `structural`

**Schema:** `label?: str≤6 (default 'VS'), has_line?: bool, line_style?: 'dashed'|'solid'`

**Best col_spans:** [1, 2]  ·  **Natural height:** `auto / 1fr`

**Use for:**
- center divider in 2-panel comparison layouts

**Don't use for:**
- general spacer (use empty cell or 1fr row)
- more than 2 panels (use a different shape)

**Block kind aliases:** `comparison_divider`

## Reverse lookup — content kind → component

When you have content of a particular kind (e.g. a chart, a quote, a callout), this index tells you which components can render it.

- `badges` → `tags`
- `bar_chart` → `bar-chart`
- `before_after` → `before-after`
- `callout` → `callout`
- `catalog` → `catalog-column`
- `chips` → `tags`
- `column_chart` → `bar-chart`
- `comparison_divider` → `vs-divider`
- `comparison_table` → `comparison-table`
- `composition_chart` → `stacked-bar`
- `conversion_funnel` → `funnel`
- `data_table` → `table`
- `definition_list` → `definition-list`
- `donut_chart` → `pie-chart`
- `editorial_quote` → `pull-quote`
- `eyebrow` → `kicker`
- `feature_list` → `icon-list`
- `feature_matrix` → `comparison-table`
- `features_3` → `practice-card`
- `funnel` → `funnel`
- `gauge` → `gauge-dial`
- `gauge_dial` → `gauge-dial`
- `headline` → `headline`
- `hero_stat` → `stat-hero`
- `hero_statement` → `headline`
- `icon_list` → `icon-list`
- `image` → `image-tile`
- `key_value` → `definition-list`
- `kicker` → `kicker`
- `kpi_movement` → `trend-stat`
- `lead_paragraph` → `lead-paragraph`
- `lede` → `lead-paragraph`
- `line_chart` → `line-chart`
- `list` → `bullet-list-checked`
- `logos` → `logo-grid`
- `matrix_2x2` → `quadrant-matrix`
- `methodology` → `process-flow`
- `narrative` → `narrative-paragraph`
- `note` → `callout`
- `numbered_list` → `numbered-list`
- `okr_tracker` → `progress-bar`
- `ordered_list` → `numbered-list`
- `partners` → `logo-grid`
- `photo` → `image-tile`
- `pie_chart` → `pie-chart`
- `process` → `process-flow`
- `process_lanes` → `swimlane`
- `progress_bar` → `progress-bar`
- `progress_bars` → `progress-bar`
- `pull_quote` → `pull-quote`
- `quadrant` → `quadrant-matrix`
- `quote` → `quote-block`
- `ranked_list` → `numbered-list`
- `section_header` → `section-header`
- `share_chart` → `pie-chart`
- `spec_sheet` → `definition-list`
- `stacked_bar` → `stacked-bar`
- `steps` → `process-flow`
- `subhead` → `section-header`
- `supporting_stats` → `kpi-row`
- `swimlane` → `swimlane`
- `table` → `table`
- `tags` → `tags`
- `testimonial` → `quote-block`
- `timeline` → `timeline`
- `tip` → `callout`
- `topic_label` → `kicker`
- `transformation` → `before-after`
- `trend_chart` → `line-chart`
- `trend_stat` → `trend-stat`
- `trust_signals` → `logo-grid`
- `values` → `value-medallion`
- `warning` → `callout`