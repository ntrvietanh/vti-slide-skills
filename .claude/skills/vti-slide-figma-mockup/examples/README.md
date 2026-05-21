# Example — wiring vti-slide-figma-mockup into a Phase 3 driver

This folder is documentation-only. Mockup outputs land in
`work/mockups/`, not here.

## Minimal Phase 3 driver fragment

The orchestrator (Claude in the loop) sees one slide's
`image_decision.strategy == "mockup"` and runs the following stages:

```python
# scripts/build_phase_3.py — per-deck driver fragment
import json
from pathlib import Path

import mockup_builder
import mockup_executor

# 1. Build the task descriptor (pure Python — no MCP)
task = mockup_builder.make_screen_desktop(
    brief=(
        "B2B logistics dispatch console. Left nav with sections "
        "Dispatch / Routes / Vehicles / Drivers / Reports. Main area: "
        "map on top half showing 12 vehicles as pins, route lines in "
        "blue. Below the map: a table of 8 active jobs with columns "
        "ID, Pickup, Dropoff, Driver, ETA, Status. Top bar: search, "
        "notifications bell, user avatar."
    ),
    title="Dispatch console — operator view",
    subtitle="Slide s14",
    style="brand-vti",
)
print("Task built — passing to orchestrator")
print(task["brief"])              # what use_figma will see
print(f"hint canvas: {task['hint_w']}x{task['hint_h']}")
```

## Orchestrator turn (you, Claude — not Python)

```
1. /figma-use                              # MANDATORY before use_figma
2. mcp__claude_ai_Figma__create_new_file
     title="Dispatch console — operator view"
3. mcp__claude_ai_Figma__use_figma
     prompt=task["brief"]
4. mcp__claude_ai_Figma__get_metadata     # → bbox dims, node id
5. mcp__claude_ai_Figma__get_screenshot   # → PNG bytes
6. (optional) mcp__claude_ai_Figma__upload_assets    # if SVG export available
```

Capture the Figma URL printed by `create_new_file`, the node id
returned by `use_figma`, and the screenshot bytes.

## Land the result (back in Python)

```python
spec = mockup_executor.record_render(
    task=task,
    slide_id="s14-dispatch",
    asset_id="01",
    figma_url="https://figma.com/design/abcd1234/Dispatch-console?node-id=1:42",
    figma_file_key="abcd1234",
    figma_node_id="1:42",
    png_bytes=open("/tmp/screenshot.png", "rb").read(),   # from get_screenshot
    svg_str=None,
    natural_w=1440,        # from get_metadata.bbox
    natural_h=900,
    work_root="work",
)
print(spec["png_path"])    # work/mockups/s14-dispatch_01/render.png
print(spec["figma_url"])   # user opens this to tweak
```

## Wire into the SlideContentPlan

```python
from creator import make_slide_content_plan

# v0.1.0 stop-gap: use the 'lift' strategy with a fake resolved_image
content_plan = make_slide_content_plan(
    slide_id="s14-dispatch",
    topic="Dispatch console",
    section_name="PRODUCT WALKTHROUGH",
    blocks=blocks,
    image_decision={"strategy": "lift", "source_hint": ""},
    layout_hint="pattern-b-image-narrative-side-by-side",
)
content_plan["mockup_spec"] = spec                          # NEW field
content_plan["resolved_image"] = mockup_executor.to_resolved_image(spec)
```

The `resolved_image` adapter lets the existing Phase 4 `_image_dims`
branch pick up the PNG with correct dimensions — no creator code
change required at v0.1.0.

When creator gets a follow-up bump (`image_decision.strategy="mockup"`,
`_image_dims` reads `mockup_spec` natively), drop the `resolved_image`
line.

## Resuming after a session restart

`meta.json` is persistent. To re-bind a previously rendered mockup:

```python
spec = mockup_executor.load_meta("work", "s14-dispatch", "01")
content_plan["mockup_spec"] = spec
content_plan["resolved_image"] = mockup_executor.to_resolved_image(spec)
```

No Figma MCP call required — the PNG is still on disk and the URL is
in the sidecar.
