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

## Phases recap (vti-slide-creator ≥ 4.0)

**6 phases**, 2 mandatory checkpoints (★). Đọc `.claude/skills/vti-slide-creator/SKILL.md` cho chi tiết.

- Phase 1 ANALYZE — source ingestion → ContextDoc
- Phase 2 PLAN-OUTLINE-AND-REVIEW ★ — deck arc + slide list (merged with review)
- Phase 3 CONTENT-PLAN — per-slide blocks + diagram-draw via `vti-slide-diagram-builder` + lift filter via `classify_image_kind`
- Phase 4 LAYOUT-DESIGN — explicit row heights + cell aspect-ratio (no-crop + ≥70% fill assertions)
- Phase 5 COMPONENT-PICK — mostly mechanical; SlideLayoutPlan → slide_input descriptors
- Phase 6 REVIEW-AND-COMPOSE ★ — layout-review widget + final HTML deck

Sau Phase 6 → optional: chạy decorator (user-triggered, not auto).

## Driver scripts

```
scripts/build_phase_1.py  # ANALYZE
scripts/build_phase_2.py  # PLAN-OUTLINE-AND-REVIEW
scripts/build_phase_3.py  # CONTENT-PLAN (writes work/diagrams/*.svg)
scripts/build_phase_4.py  # LAYOUT-DESIGN
scripts/build_phase_5.py  # COMPONENT-PICK
scripts/build_phase_6.py  # REVIEW-AND-COMPOSE → work/deck-composed.html
```

## Density mode

Set `plan['density_mode']` ở Phase 3. Options: `standard` (default) | `sparse-ok` | `dense`. Cả creator và page-builder đọc cùng giá trị này.

## Reference

- Architecture + version map: `COORDINATED_BASELINE.md`
- Skill SKILL.md: `.claude/skills/<name>/SKILL.md`
- Test prompt templates: `tests/TEST_PROMPT.md`
