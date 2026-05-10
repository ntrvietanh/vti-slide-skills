# VTI Slide Skills

Bộ 3 skill phối hợp cho VTI APAC slide deck pipeline. Phát triển và test bằng **Claude Code** chạy local.

## Architecture

```
Phase 1-5 input/source           composed deck             decorated deck
    │                                 │                          │
    ▼                                 ▼                          ▼
┌─────────────────────┐    ┌────────────────────┐    ┌────────────────────┐
│ vti-slide-creator   │ -> │vti-slide-page-     │ -> │vti-slide-decorator │
│ (orchestrator,      │    │ builder            │    │ (whitespace        │
│  5-phase pipeline)  │    │ (component         │    │  analyzer +        │
│                     │    │  renderer)         │    │  SVG/CSS overlay)  │
└─────────────────────┘    └────────────────────┘    └────────────────────┘
```

3 skills đều là Python packages, share `slide_meta` contract. Xem chi tiết: [`COORDINATED_BASELINE.md`](./COORDINATED_BASELINE.md)

## Versions (baseline 2026-05-10)

| Skill | Version |
|---|---|
| `vti-slide-creator` | 3.19.0 |
| `vti-slide-page-builder` | 3.13.1 |
| `vti-slide-decorator` | 0.5.2 |

## Repo layout

```
vti-slide-skills/
├── .claude/skills/                 ← skills (Claude Code auto-load từ đây)
│   ├── vti-slide-creator/
│   ├── vti-slide-page-builder/
│   └── vti-slide-decorator/
├── tests/
│   ├── inputs/                     ← file đầu vào để test (drop file vào đây)
│   ├── expected/                   ← reference output để so sánh
│   └── TEST_PROMPT.md              ← prompt test chuẩn
├── work/                           ← runtime workspace (gitignored)
├── scripts/
│   ├── setup.sh                    ← setup PYTHONPATH + venv
│   └── verify.sh                   ← smoke test 3 skills load được
├── COORDINATED_BASELINE.md         ← contracts + version map
├── requirements.txt                ← Python deps
├── .gitignore
└── README.md
```

## Setup local

### 1. Clone + Python env

```bash
git clone <your-repo-url> vti-slide-skills
cd vti-slide-skills

# Tạo virtualenv (khuyến nghị — tránh đụng system Python)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set PYTHONPATH

```bash
source scripts/setup.sh
# hoặc tự export:
# export PYTHONPATH=$(pwd)/.claude/skills/vti-slide-creator:\
# $(pwd)/.claude/skills/vti-slide-page-builder:\
# $(pwd)/.claude/skills/vti-slide-decorator:\
# $(pwd)/.claude/skills/vti-slide-decorator/strategies
```

### 3. Smoke test

```bash
bash scripts/verify.sh
# Expected:
# creator:      3.19.0
# page-builder: 3.13.0
# decorator:    0.5.0
```

### 4. Khởi động Claude Code

```bash
# Đảm bảo KHÔNG có ANTHROPIC_API_KEY trong env (nếu không sẽ tính tiền API thay vì dùng sub)
unset ANTHROPIC_API_KEY

claude
# trong session: gõ /status để confirm đang dùng Pro/Max subscription
```

Claude Code tự load 3 skills từ `.claude/skills/` — không cần cấu hình thêm.

## Dev loop điển hình

1. Drop file input vào `tests/inputs/` (vd `sample-source.docx`)
2. Trong Claude Code, paste prompt từ `tests/TEST_PROMPT.md`
3. Skill chạy 5-phase pipeline → output ở `work/`
4. Quan sát output, thấy bug → bảo Claude Code edit file trong `.claude/skills/<skill-name>/`
5. Gõ `/clear` trong Claude Code → reset context
6. Test lại từ bước 2 → so sánh output mới
7. Khi xong: `git add . && git commit -m "fix: ..."` → push

**Tip**: nếu pipeline hết context giữa chừng, output intermediate JSON ở `work/phase_N.json` cho mỗi phase. Phase sau đọc lại JSON, không phải re-run từ đầu.

## VS Code integration

Mở repo bằng VS Code:
- Edit code skill trong `.claude/skills/...` như Python project bình thường (Pylance, ruff, etc. work)
- Dùng integrated terminal cho `claude` session
- Có thể chia 2 tab terminal: 1 cho Claude Code, 1 cho `pytest` / manual test

Khuyến nghị `.vscode/settings.json` (auto-create khi anh muốn):
```json
{
  "python.analysis.extraPaths": [
    ".claude/skills/vti-slide-creator",
    ".claude/skills/vti-slide-page-builder",
    ".claude/skills/vti-slide-decorator",
    ".claude/skills/vti-slide-decorator/strategies"
  ]
}
```

## Contributing

Mỗi skill có `CHANGELOG.md` riêng. Khi sửa:
1. Bump version trong `SKILL.md` (header phần `## Version`)
2. Cập nhật `CHANGELOG.md` của skill đó
3. Nếu sửa cross-skill contract → cập nhật `COORDINATED_BASELINE.md` luôn
