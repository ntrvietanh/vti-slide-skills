# Aesthetic Redesign Proposal — "Bộ não thẩm mỹ" cho VTI slide pipeline

> Status: **PROPOSAL / research synthesis** — chưa code. Không sửa skill code nào cho tới khi Michael confirm.
> Ngày: 2026-06-17. Branch: `claude/amazing-dijkstra-y16tph`.
> Mục đích: kết tinh 4 mũi research về "tại sao layout/decoration vẫn yếu" thành một kế hoạch dùng được, bền qua nhiều session.

---

## 0. Vấn đề (lời Michael)

> "Skill build slide vẫn gặp 1 vấn đề: khả năng **tư duy thiết kế layout** và **slide decoration** vẫn rất yếu. Cần một phương án để output có **tính thẩm mỹ cao**. Sẵn sàng đập bỏ tất cả làm lại."

Kết luận của research: **KHÔNG cần đập bỏ.** Pipeline hiện tại đã ở đúng họ kiến trúc mà best-in-class (Gamma) và học thuật xác nhận là đúng (constrained selection + deterministic render + design tokens). Nó thiếu **đúng một lớp** và **sai một quy tắc**. Xem §4–§5.

---

## 1. Chẩn đoán — 4 root cause (có bằng chứng)

| # | Vấn đề trong pipeline hiện tại | Bằng chứng đối chiếu |
|---|---|---|
| **1 (gốc)** | **Phase 4 chọn layout theo waste-minimization** (`abs(waste_v)+1.5*waste_h`) + ép `fill_pct ≥ 0.70`. Tối ưu "lấp đầy" thay vì "nội dung này muốn là gì". | Gamma chọn layout theo **content-intent** (data-heavy→comparison, narrative→text, showcase→gallery). Lấp đầy chủ động giết hierarchy & whitespace → ra "stuffed/soulless". Chính `Principle 3 (whitespace intentional)` của repo **mâu thuẫn** với rule fill≥70%. |
| **2** | **Render engine không reflow thật** — dùng `BLOCK_KIND_EST_H` (ước lượng tĩnh, đo 1 lần) trên grid auto-rows. Ước sai → đẻ khoảng trắng. | Gamma/Beautiful.ai/SmartArt: card **reflow/rebalance** khi content đổi; whitespace là *byproduct được engine quản*, không phải lỗi. CSS `minmax()/fr/auto-fit` + container queries làm được điều này. |
| **3** | **Decorator vá khoảng trắng (sai layer)** — inject SVG blob ở `z-index:1` post-hoc → trông "dán thêm". | Literature: đừng *fill* khoảng trống, để *engine* quản. Decoration nên là **theme/background**, không phải gap-filler. |
| **4** | **Không có pass kiểm tra thị giác** cho lỗi tồn dư; **thiếu archetype/exemplar đẹp** để chống "generic". | Root cause học thuật: *"LLMs lack direct visual feedback and cannot accurately assess how the generated layout will appear"* (đừng để LLM tự chỉnh số pixel). VLM-judge HẸP bắt overflow/overlap/contrast. Archetype library + content-freedom chống "uncanny valley". |

**Tension phải quản:** template cứng → "generic / average-of-all-slides". Consistency ≠ đẹp. Giải: archetype đẹp thật + cho LLM tự do *nội dung* trong ràng buộc + vision-judge.

---

## 2. Research đã làm (4 mũi, đã hội tụ)

1. **Map kiến trúc hiện tại** — pipeline 6 phase, 37 component, `tokens.css`, decorator 4 strategy, diagram-builder. Đã có component layer + token layer + phần lớn beauty rules.
2. **Constraint vs free-gen + Gamma teardown** — Gamma đạt thẩm mỹ bằng **ràng buộc up-front, KHÔNG bằng critique loop**: LLM chọn layout-type theo content-intent; engine responsive lo spacing/whitespace; tách content↔theme bằng token. Học thuật hội tụ ở "constrained generation" (token = hard constraint + auto-layout solver + LLM cho content/intent + VLM-verify cho lỗi tồn dư).
3. **SlideCoder teardown** — *bất ngờ:* nó là engine **image→pptx** (sao chép design có sẵn), KHÔNG phải design-engine; "layout-aware RAG" thực ra là **API/ontology-doc RAG**. Giá trị: cho mượn **scaffold kỹ thuật** (hierarchical per-block generation, RAG-grounding theo từ vựng riêng, refine-on-error loop, SCM density metric) — KHÔNG cho mượn "bộ não thẩm mỹ".
4. **Bộ não thẩm mỹ** — taxonomy content-intent (SmartArt + Zelazny + Abela + FT Visual Vocabulary + McKinsey/Minto), thư viện archetype (Gamma/Beautiful.ai/pitch/tome/editorial), bảng mapping, beauty-rule rubric. → **Kết luận: lớp thiếu là "archetype layer".**

Caveat chung: WebFetch bị 403 mọi domain trừ github; mọi claim vendor/paper được triangulate từ WebSearch snippets (quote nguyên văn) + github raw. Ngưỡng số cụ thể (count buckets, target 16 archetype, 5% margin) là synthesis.

---

## 3. Kết luận hợp nhất — lớp thiếu là **ARCHETYPE LAYER**

Repo đã ship:
- **Component layer** — 37 atomic block + metadata (`good_for`/`best_col_spans`/`picks_content_kinds`).
- **Token layer** — `tokens.css` (color/type-scale/spacing/radii/shadow/surface).
- **Phần lớn beauty rules** — 5-level type scale, 2-weight, single-accent, 8px spacing, focal hierarchy.

Repo **thiếu**:
- **Archetype layer** — ~14–18 *layout shell* có slot, bind token, gắn metadata, **responsive thật**.
- **Content-intent → archetype mapper** — sống *giữa Phase 2 (outline) và Phase 4 (layout-design)*.
- **Vision-judge HẸP** — bắt lỗi tồn dư sau render.

Và phải **đổi** Phase 4: bỏ waste-minimization + rule fill≥70%, chuyển sang chọn archetype theo content-intent; **hạ vai** decorator từ gap-filler → theme/background.

---

## 4. Kiến trúc đích — GIỮ / ĐỔI / THÊM

**GIỮ (literature xác nhận đúng):** `tokens.css`, component registry + metadata, outline-review checkpoint (Phase 2★), phase split, contract-based skills, SCM-style capacity planning (`cell_capacity`, `BLOCK_KIND_CAPS`).

**ĐỔI:**
- **Phase 4 LAYOUT-DESIGN**: thay scoring `waste` → **chọn archetype theo content-intent** (faceted retrieval, §6.4). Bỏ rule `fill≥70%` cứng → đổi thành band 70–90% *mềm* + cho phép sparse có chủ đích ở statement/section/quote.
- **Render**: chuyển sang **reflow thật** — CSS Grid `minmax()/fr/auto-fit`, fluid type `clamp()`, **container queries** (`cqi`) cho region-aware reflow. Token = hard constraint.
- **Decorator**: hạ vai → **theme/background system** (hoặc tắt mặc định). Hết "vá trắng".

**THÊM:**
- **Archetype layer** — thư viện ~14–18 shell (§6.2), mỗi shell = layout + slot set + token binding + metadata (§6.4).
- **Content-intent classifier + mapper** — giữa Phase 2 và Phase 4 (§6.3).
- **Vision-judge HẸP** — render PNG → VLM chấm *chỉ* 8 assertion (§6.5); chỉ bắt overflow/overlap/contrast/stretch, KHÔNG redesign. Refine-on-error loop kiểu SlideCoder (max 3).
- **Component-doc RAG-grounding** (SlideCoder H-RAG mở rộng) — `components.kb` + `blocktypes.kb`, retrieve top-3 theo mô tả block, inject vào prompt để LLM luôn dùng *từ vựng của repo*.

```
Phase 1 ANALYZE
Phase 2 PLAN-OUTLINE ★
   └─► [MỚI] CONTENT-INTENT CLASSIFY  (gán 1 intent / slide, §6.1)
Phase 3 CONTENT-PLAN  (per-block, RAG-grounded)
   └─► [MỚI] ARCHETYPE MAP            (intent + signals → archetype, §6.3–6.4)
Phase 4 LAYOUT-DESIGN  (đổ content vào archetype shell; reflow; KHÔNG waste-min)
Phase 5 COMPONENT-PICK
Phase 6 REVIEW-AND-COMPOSE ★
   └─► [MỚI] VISION-JUDGE HẸP         (render→chấm 8 assertion→fix tồn dư, §6.5)
Decorator: theme/background only (no gap-fill)
```

---

## 5. Khuyến nghị triển khai (phased)

**Bước 0 — SPIKE (đề xuất làm trước):** lấy 1–2 slide đang xấu trong `work/`, dựng lại bằng lớp #1 (content-intent → archetype) + #2 (CSS reflow thật, token hard-constraint, KHÔNG decorator), đặt cạnh output cũ để **so sánh trực tiếp**. Rẻ; chứng minh thesis trước khi refactor. *Tiêu chí pass:* nhìn bằng mắt thấy đẹp hơn rõ rệt + không cần decorator vá.

**Bước 1 — Archetype library v0:** author 4–6 archetype "xương sống" (cover, statement, big-number, two-up-comparison, card-grid, split-media-text) theo §6.2, bind `tokens.css`, responsive (`minmax/clamp/cqi`). Nguồn: adapt HTML designer-made hoặc one-shot frontier model + token contract (§ research playbook).

**Bước 2 — Mapper + intent classify:** thêm bước classify sau Phase 2 + faceted mapper trước Phase 4 (§6.3–6.4). Bỏ waste-scoring trong `layout_designer.py`.

**Bước 3 — Vision-judge HẸP + RAG-grounding.** Bước 4 — mở rộng library lên ~16; hạ vai decorator.

Mỗi bước: bump version + CHANGELOG; nếu đổi cross-skill contract → update `COORDINATED_BASELINE.md` (theo CLAUDE.md).

---

## 6. Artifacts (starter kit dùng được ngay)

### 6.1 Content-intent taxonomy (14, cho corporate deck)
`explain-concept · big-number · compare-options · list-parallel-items · process-sequence · timeline-milestones · trend-over-time · part-to-whole · ranking-magnitude · quadrant-2x2 · before-after · quote-testimonial · image-showcase · assertion-cta`

3 họ trực giao cần cả ba: (a) data-message intents (Zelazny/Abela/FT), (b) conceptual-structure (SmartArt), (c) rhetorical (McKinsey: title khẳng định, body chứng minh).

### 6.2 Archetype library (14 shell) — slots · intent-tags · count · has_image · key design move

| Archetype | Slots | intent_tags | count | img | Key design move |
|---|---|---|---|---|---|
| **cover** | eyebrow?, title, subtitle, logo | (deck open) | — | opt | full-bleed + scrim; 1 title trội |
| **section-divider** | number, title, rule | (act reset) | — | opt | type to + emptiness chủ đích |
| **statement** | title, support? | explain-concept, assertion-cta | 1 | no | type-as-image; max negative space |
| **big-number** | value, label, body? | big-number, ranking-magnitude | 1–3 | no | 1 numeral ~120px vs caption; stat row baseline-aligned |
| **two-up-comparison** | title, left{h,body}, right{h,body}, vs? | compare-options, before-after | 2 | opt | mirror symmetry + 1 accent/side |
| **card-grid** | eyebrow?, title, items[2–4]{icon,head,body} | list-parallel-items, explain-concept | 2–4 | no | cell đều + gutter đều + accent chung |
| **icon-grid** | title, items[4–6]{icon,label} | list-parallel-items | 4–6 | no | 1 icon style, scale đều |
| **list-plus-visual** | eyebrow?, title, body(bullets≤5), media | explain-concept, image-showcase | 1+≤5 | yes | cap list; pair 1 visual; cột type sạch |
| **split-media-text** | title, body, media (50/50 hoặc 60/40) | image-showcase, explain-concept | 1 | yes | image bleed mép; tỉ lệ bất đối xứng |
| **full-bleed-image** | media, title, caption? (overlay) | image-showcase, assertion-cta | 1 | yes(req) | scrim + text trong negative space của ảnh |
| **timeline** | title, items[3–6]{date,label,body?} | timeline-milestones, process-sequence | 3–6 | no | spine liên tục + node đều; xen trên/dưới |
| **process-steps** | title, steps[3–5]{num,title,body?} | process-sequence | 3–5 | no | chevron + badge số |
| **quote** | quote, attribution, portrait? | quote-testimonial | 1 | opt | quote display-size, mọi thứ khác demote |
| **quadrant** | title, x-axis, y-axis, cells[4] | quadrant-2x2 | 4 | no | trục chữ thập = framework; quadrant color-coded |

(+ specials sẵn có: agenda/TOC, logo-grid wall, table, closing/CTA → tổng ~18.)

### 6.3 Mapping content-intent → archetype (tiebreak)

| Content-intent | Candidates | Tiebreak |
|---|---|---|
| big-number | big-number / KPI columns | 1 num → big-number; 2–4 → columns |
| compare-options | two-up / card-grid / table | 2→split; 3–4→grid; **5+ hoặc nhiều attr→table** |
| list-parallel-items | card-grid / icon-grid / spill | 3–4→cards; 5–6→icon-grid; **7+→spill slide** |
| process-sequence | timeline / process-steps | có date→timeline; không→process |
| explain-concept | list-plus-visual / split / statement / card-grid | có image→list-plus-visual/split; thesis thuần→statement; multi-part→card-grid |
| trend-over-time | line / column | nhiều period→line; ≤5→column/timeline |
| part-to-whole | pie-donut / stacked | ≤5 part→pie; nhiều→stacked |
| ranking-magnitude | sorted bar / column | nhấn ranking→horizontal sorted bar |
| quadrant-2x2 | quadrant | always |
| before-after | two-up / process | 2 state→two-up; 3+→process |
| quote-testimonial | quote | always full-width |
| image-showcase | full-bleed / split / gallery | 1 img→hero/split; nhiều→gallery |

**Decision signals:** item count (1/2/3–4/5–8/9+) · single dominant number · #things × #attributes · ordered vs set · time dimension · imagery present · part-to-whole vs absolute · narrative vs data-heavy.

### 6.4 Archetype metadata (faceted, để retrievable)
```json
{ "id":"split-media-text", "intent_tags":["image-showcase","explain-concept"],
  "slots":["title","body","media"], "element_count_range":[1,1], "max_items":6,
  "has_image":true, "media_required":true, "density":"standard",
  "focal_type":"media", "text_capacity":{"title_chars":60,"body_words":70} }
```
Mapper: filter `media_required` theo asset có sẵn → filter `element_count_range` theo item count thật → rank theo overlap `intent_tags` + `focal_type` → tiebreak `density` (dùng lại `density_mode` của repo: `standard|sparse-ok|dense`). Nếu count > `max_items` → trigger spill.

### 6.5 Beauty-rule rubric (8 assertion — renderer constraint + vision-judge)
1. **Focal point:** đúng 1 element ≥40% visual weight; có size-gap rõ tới element kế.
2. **Restraint:** ≤3 type size, ≤2 weight, ≤1 accent (VTI blue) + neutrals / slide.
3. **Type scale:** level kề nhau theo ratio ∈ {1.2, 1.25, 1.333} (12/15/24/32/64px của repo ≈ honor).
4. **Grid/rhythm:** mọi mép snap 12-col; spacing dọc = bội số 8px.
5. **Whitespace/fill:** content phủ **70–90%** (không <50% sparse vô ý, không >100% overflow); margin ngoài ≥ brand margin mọi phía.
6. **Image integrity:** giữ aspect (no stretch); full-bleed HOẶC framed nhất quán; text trên ảnh phải có scrim.
7. **Contrast:** mọi text ≥4.5:1 (≥3:1 large) so với nền hiệu dụng (WCAG AA — chuẩn formal duy nhất).
8. **Asymmetric balance:** không phải mọi thứ đều center-mirror; element chính lệch tâm + counterweight (trừ statement/section cố ý center).

---

## 7. Rủi ro & open question
- **"Generic" tension** — phải đầu tư archetype *đẹp thật* (không tự bịa), + cho LLM tự do nội dung. Đây là chỗ dễ thất bại nhất.
- **Nguồn archetype đẹp** — adapt HTML designer-made vs one-shot frontier model vs curate gallery. Cần quyết playbook ở Bước 1.
- **Container queries / fluid type** trong môi trường render (Playwright) — verify support trước.
- **Vision-judge** chi phí token/lượt render — giữ HẸP, chỉ chạy Phase 6.
- Canva/Figma MCP: nhánh "mượn engine" bị gate sau Canva paid plan (brand template/autofill yêu cầu Pro/Teams; account hiện chưa có brand kit). Chỉ theo nếu chấp nhận nâng cấp + dựng template VTI.

## 8. Nguồn chính
SmartArt (support.microsoft.com) · Zelazny *Saying It With Charts* · Abela Chart Chooser (extremepresentation.com) · FT Visual Vocabulary (github.com/Financial-Times/chart-doctor) · data-to-viz.com · Minto/SCQA · Gamma mapping guides (gamma.app) · Beautiful.ai smart-slides · SlideCoder (arXiv 2506.07964, github.com/vinsontang1/SlideCoder) · AutoPresent (arXiv 2501.00912) · DOC2PPT (arXiv 2101.11796) · Textual-to-Visual Iterative Self-Verification (arXiv 2502.15412) · ReLayout (arXiv 2507.05568) · W3C Design Tokens (designtokens.org) · Slidev layouts (sli.dev) · CSS auto-fit/clamp/container-queries · WCAG 2.1 AA · Williams CRAP / Presentation Zen.
