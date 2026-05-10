# Test Prompt Template

Copy/paste vào Claude Code session sau khi đã chạy `source scripts/setup.sh`.

---

## Standard test (full 5-phase pipeline)

```
Tôi có file source ở `tests/inputs/sample-source.docx`.
Hãy chạy `vti-slide-creator` skill từ Phase 1 đến hết.

Yêu cầu:
- Output mỗi phase ra `work/phase_N.json` (để có thể resume nếu hết context)
- DỪNG ở mỗi checkpoint, hỏi t confirm trước khi sang phase tiếp
- Phase 5 xong → composed deck HTML ra `work/deck-composed.html`
- Sau đó chạy `vti-slide-decorator` → `work/deck-decorated.html`

Density mode: standard
Layout: default
```

---

## Resume test (khi session trước hết context giữa pipeline)

```
T đã chạy pipeline đến Phase X. Output các phase trước nằm ở `work/phase_1.json`,
`work/phase_2.json`, ... Đọc các JSON này, summary cho t status hiện tại,
rồi tiếp tục từ Phase (X+1).
```

---

## Single-skill test (test đơn lẻ một skill khi debug)

```
Đọc `work/plans_v5.json` (output của Phase 4).
Chỉ chạy `vti-slide-page-builder.compose_slide_grid` với slide đầu tiên.
In ra HTML + báo cáo bất kỳ violation nào trong fill-honesty check.
```

---

## Decorator-only test (test layer post-process)

```
Đọc `work/deck-composed.html` (đã có sẵn từ session trước).
Chạy `vti-slide-decorator.decorate()` với strategy=auto.
Output: `work/deck-decorated.html`.
Cho t xem mỗi gap được classify thế nào và strategy chọn cho mỗi gap.
```

---

## Bug repro template

```
Bug observed: [mô tả ngắn]
Slide / phase liên quan: [Phase 3 / slide 5 / etc.]
Expected: [hành vi đúng]
Actual: [hành vi sai]

File liên quan:
- Input: tests/inputs/<file>
- Phase output trước bug: work/phase_<N>.json

Hãy reproduce bug, identify file/function gây lỗi, propose fix.
KHÔNG sửa code ngay — propose trước, t confirm rồi mới sửa.
```
