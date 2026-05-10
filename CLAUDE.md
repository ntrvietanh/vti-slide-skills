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
PYTHONPATH=.claude/skills/vti-slide-creator-v3:.claude/skills/vti-slide-page-builder-v3:.claude/skills/vti-slide-decorator:.claude/skills/vti-slide-decorator/strategies python3 -c "..."
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

## Phases recap (vti-slide-creator-v3)

5 phases với checkpoint sau mỗi phase. Đọc `.claude/skills/vti-slide-creator-v3/SKILL.md` cho chi tiết. Ngắn gọn:

- Phase 1: source ingestion + summary
- Phase 2: deck planning (sections, slide count)
- Phase 3: per-slide content drafting
- Phase 4: component selection + grid layout
- Phase 5: HTML composition (gọi page-builder)

Sau Phase 5 → optional: chạy decorator.

## Density mode

Set `plan['density_mode']` ở Phase 4. Options: `standard` (default) | `sparse-ok` | `dense`. Cả creator và page-builder đọc cùng giá trị này.

## Reference

- Architecture + version map: `COORDINATED_BASELINE.md`
- Skill SKILL.md: `.claude/skills/<name>/SKILL.md`
- Test prompt templates: `tests/TEST_PROMPT.md`
