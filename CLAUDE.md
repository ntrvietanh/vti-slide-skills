# Instructions for Claude Code

Khi anh chạy `claude` trong repo này, đọc file này trước.

## Mục đích repo

Đây là dự án dev/test bộ 3 skill VTI slide pipeline. **Đây là môi trường tuning skill** — Michael sẽ:
1. Test pipeline với file input (`tests/inputs/`)
2. Quan sát output ở `work/`
3. Khi thấy bug, bảo Claude Code edit code skill trong `.claude/skills/`
4. Test lại loop

## Trước khi chạy bất kỳ Python code nào

PYTHONPATH phải bao gồm 3 skill dirs. Nếu chưa set, chạy:

```bash
source scripts/setup.sh
```

Hoặc khi gọi Python trực tiếp, prefix bằng:

```bash
PYTHONPATH=.claude/skills/vti-slide-creator:.claude/skills/vti-slide-page-builder:.claude/skills/vti-slide-decorator:.claude/skills/vti-slide-decorator/strategies python3 -c "..."
```

## Conventions cho session này

1. **Output intermediate JSON cho mỗi phase** vào `work/phase_N.json`. Lý do: nếu context hết, session sau resume được mà không phải re-run từ đầu.

2. **Không tự ý sửa code skill khi gặp bug** — propose fix trước, đợi Michael confirm.

3. **Khi sửa code skill**:
   - Bump version trong `.claude/skills/<skill>/SKILL.md`
   - Update `.claude/skills/<skill>/CHANGELOG.md`
   - Nếu sửa cross-skill contract (slide_meta shape, density mode, etc.) → update `COORDINATED_BASELINE.md`

4. **Không xóa file trong `tests/expected/`** — đây là reference output để regression test.

5. **Final HTML deck output** đi vào `work/deck-composed.html` (sau page-builder) và `work/deck-decorated.html` (sau decorator). Đừng output vào root.

### CRITICAL — mọi tweak phải sống trong `scripts/patches/`

**Quy tắc folder `scripts/`:** tất cả `*.py` và `*.mjs` đều **per-deck** (gitignored, bị `reset.sh` wipe). Chỉ `*.sh` và `scripts/patches/README.md` là durable infra. Generic dev tools (vd renderer mermaid) thuộc về `.claude/skills/<skill>/`, không nằm trong `scripts/`.

Patches + drivers + `work/*` đều per-deck. Nhưng trong lifecycle của 1 deck, đừng chạy `reset.sh` — files vẫn ở đĩa, persist qua nhiều Claude sessions. Vì vậy:

- Mọi chỉnh sửa đã approve vào `work/phase_N.json` hoặc `work/deck-composed.html` **PHẢI** được codify thành patch trong `scripts/patches/`.
  - Phase JSON tweak → `phase{N}_{NN}_{slug}.py` (auto-run cuối `build_phase_{N}.py`)
  - HTML tweak (sau Phase 6) → `post_compose_{NN}_{slug}.py` (auto-run cuối `build_phase_6.py`)
- Patch phải **idempotent** (chạy 2 lần = chạy 1 lần, dùng sentinel marker class / comment).
- Đọc `scripts/patches/README.md` để biết contract + danh sách patch hiện có.
- Không bao giờ để 1 fix đã approve sống chỉ trong `work/` — re-run là mất.

Workflow:
1. Edit thử trực tiếp `work/...` để confirm visual với user.
2. User approve → codify ngay thành patch file (không hứa "để sau").
3. Re-run `build_phase_{N}.py` để verify patch re-apply sạch (log có ✓).
4. Tweak gốc trong `work/` bị regenerate đè — đó là chứng cứ patch hoạt động.

### MANDATORY footers cho mỗi `build_phase_{N}.py`

Drivers là per-deck, viết lại mỗi deck mới. **Mọi `build_phase_N.py` mới phải có footer auto-apply patches**, nếu không re-run trong cùng deck sẽ mất hết tweak. Template:

```python
# Cuối build_phase_5.py
import runpy
from pathlib import Path
PATCHES = Path(__file__).resolve().parent / 'patches'
for pf in sorted(PATCHES.glob('phase5_*.py')) if PATCHES.exists() else []:
    print(f'  > {pf.name}')
    runpy.run_path(str(pf), run_name='__main__')

# Cuối build_phase_6.py  (sau khi write work/deck-composed.html)
import runpy
from pathlib import Path
PATCHES = Path(__file__).resolve().parent / 'patches'
for pf in sorted(PATCHES.glob('post_compose_*.py')) if PATCHES.exists() else []:
    print(f'  > {pf.name}')
    runpy.run_path(str(pf), run_name='__main__')
```

Hiện có footer này cho phase 5 và 6. Nếu thêm patch layer mới cho phase khác (vd phase 3 content tweak) → thêm footer tương tự cho `build_phase_3.py` + naming `phase3_NN_slug.py`.

## Phases recap (vti-slide-creator ≥ 4.0)

**6 phases**, 2 mandatory checkpoints (★). Đọc `.claude/skills/vti-slide-creator/SKILL.md` cho chi tiết.

- Phase 1 ANALYZE — source ingestion → ContextDoc
- Phase 2 PLAN-OUTLINE-AND-REVIEW ★ — deck arc + slide list (merged with review)
- Phase 3 CONTENT-PLAN — per-slide blocks + diagram-draw via `vti-slide-diagram-builder` + lift filter via `classify_image_kind`
- Phase 4 LAYOUT-DESIGN — explicit row heights + cell aspect-ratio (no-crop + ≥70% fill assertions)
- Phase 5 COMPONENT-PICK — mostly mechanical; SlideLayoutPlan → slide_input descriptors
- Phase 6 REVIEW-AND-COMPOSE ★ — layout-review widget + final HTML deck

Sau Phase 6 → optional: chạy decorator (user-triggered, not auto).
Sau decorator (hoặc trực tiếp sau Phase 6) → optional: chạy
`vti-slide-pptx-exporter` để xuất `work/deck.pptx` với mỗi slide là 1 ảnh +
speaker notes (script + hints) trong notes pane. User-triggered, not auto.

## Driver scripts

```
scripts/build_phase_1.py  # ANALYZE
scripts/build_phase_2.py  # PLAN-OUTLINE-AND-REVIEW
scripts/build_phase_3.py  # CONTENT-PLAN (writes work/diagrams/*.svg)
scripts/build_phase_4.py  # LAYOUT-DESIGN
scripts/build_phase_5.py  # COMPONENT-PICK
scripts/build_phase_6.py  # REVIEW-AND-COMPOSE → work/deck-composed.html
scripts/build_pptx.py     # (optional) → work/deck.pptx + work/pptx-notes.json
```

## Density mode

Set `plan['density_mode']` ở Phase 3. Options: `standard` (default) | `sparse-ok` | `dense`. Cả creator và page-builder đọc cùng giá trị này.

## Reference

- Architecture + version map: `COORDINATED_BASELINE.md`
- Skill SKILL.md: `.claude/skills/<name>/SKILL.md`
- Test prompt templates: `tests/TEST_PROMPT.md`
