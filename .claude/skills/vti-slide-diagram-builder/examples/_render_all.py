"""Render all 7 primitives as standalone HTML files in this directory.

Run from anywhere with PYTHONPATH including the skill dir:

    PYTHONPATH=.claude/skills/vti-slide-diagram-builder .venv/bin/python \\
        .claude/skills/vti-slide-diagram-builder/examples/_render_all.py
"""
from __future__ import annotations

from pathlib import Path
import sys

EXAMPLES = Path(__file__).parent.resolve()
SKILL_ROOT = EXAMPLES.parent
sys.path.insert(0, str(SKILL_ROOT))

from diagram_builder import (  # noqa: E402
    make_flow_diagram,
    make_quadrant,
    make_footprint_map,
    make_layered_stack,
    make_fanout_pipeline,
    make_hybrid_swimlane,
    make_data_path,
)


def wrap(name: str, svg: str, natural_w: int, natural_h: int) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{name} — vti-slide-diagram-builder example</title>
<style>
  body {{ font-family: system-ui; max-width: 1240px; margin: 40px auto;
         padding: 0 20px; color: #1F2A3A; }}
  h1   {{ color: #0844A4; margin-bottom: 4px; }}
  .meta {{ color: #6B7785; font-size: 13px; margin-bottom: 24px; }}
  .frame {{ border: 1px solid #E4ECF5; border-radius: 8px;
            padding: 16px; background: white; }}
</style>
</head>
<body>
  <h1>{name}</h1>
  <div class="meta">natural viewBox = {natural_w} × {natural_h} px</div>
  <div class="frame">{svg}</div>
</body>
</html>
"""


def main() -> None:
    cases: list[tuple[str, dict]] = [
        ("flow", make_flow_diagram(steps=[
            {"title": "DATA", "sub": "POS · IoT · EHR"},
            {"title": "ETL", "sub": "Lambda · Step Func"},
            {"title": "STORAGE", "sub": "Aurora · OpenSearch"},
            {"title": "ORCHESTRATION", "sub": "ECS / Fargate brain"},
            {"title": "LLM", "sub": "Bedrock · 4o · Gemini"},
        ], title="7-block AWS reference",
           subtitle="Generalised from production deployments")),

        ("quadrant", make_quadrant(cells=[
            {"title": "SAFETY", "accent": "red", "items": [
                "SOS emergency call",
                "Fall detection",
                "Smart kitchen control",
                "Geofence / e-fence",
                "Smoke / fire / gas / leak",
            ]},
            {"title": "HEALTH", "accent": "teal", "items": [
                "BLE vitals (HR / BP / SpO₂)",
                "Glucose · Holter ECG",
                "Sleep belt + smart pillow",
                "Bedsore-prevention diaper",
            ]},
            {"title": "LIFE", "accent": "amber", "items": [
                "Smart lighting (elderly CRI)",
                "Smart curtains / windows",
                "Smart bathroom (heated)",
                "HVAC + smart appliances",
            ]},
            {"title": "EMOTION", "accent": "purple", "items": [
                "Family video calls",
                "Voice companion",
                "Emotional-care assistant",
            ]},
        ], title="Smart Elder Care — 4-pillar platform",
           footer="Multi-protocol gateway · >128 nodes · <120ms latency · offline OK")),

        ("footprint", make_footprint_map(cities=[
            {"name": "Hanoi",     "x": 280, "y": 245},
            {"name": "HCMC",      "x": 310, "y": 360},
            {"name": "Tokyo",     "x": 770, "y": 195},
            {"name": "Osaka",     "x": 720, "y": 230},
            {"name": "Nagoya",    "x": 740, "y": 215},
            {"name": "Fukuoka",   "x": 660, "y": 245},
            {"name": "Seoul",     "x": 640, "y": 175},
            {"name": "Singapore", "x": 365, "y": 460, "highlight": True},
        ], scale_label="4 countries · 9 offices · 1,800+ staff",
           title="VTI APAC footprint")),

        ("layered", make_layered_stack(layers=[
            {"label": "PHYSICAL",
             "items": ["Wi-Fi", "BLE Mesh", "Zigbee", "LoRa", "NB-IoT", "5G"],
             "accent": "ink"},
            {"label": "LINK",
             "items": ["Multi-proto stack"],
             "accent": "blue"},
            {"label": "CONVERGENCE",
             "items": ["Rules engine", "Edge compute", "Offline ctrl"],
             "accent": "deep"},
            {"label": "APP",
             "items": ["IoT PaaS", "Catalog", "Geo"],
             "accent": "teal"},
            {"label": "CLOUD",
             "items": ["App PaaS", "+ SaaS"],
             "accent": "navy",
             "filled": True},
        ], kpi_band=">128 nodes per gateway · <120 ms latency · <3 s onboarding · <1 s recovery",
           title="Multi-protocol IoT gateway — layered architecture")),

        ("fanout", make_fanout_pipeline(
            input_label="Ward camera (RTSP)",
            models=[
                {"name": "RetinaFace", "desc": "detect + align"},
                {"name": "ArcFace", "desc": "patient ID"},
                {"name": "OpenPose", "desc": "body pose"},
                {"name": "YOLOv7", "desc": "cup / pill"},
                {"name": "Dlib", "desc": "fine keypoints"},
            ],
            fusion_label="Fusion + verification rules — right patient · right medication · right step",
            outputs=[
                {"label": "OK → log event", "accent": "teal"},
                {"label": "Mismatch → alert nurse", "accent": "red"},
            ],
            title="Medication-monitoring AI — 5-model parallel pipeline")),

        ("swimlane", make_hybrid_swimlane(
            tiers=[
                {"label": "EDGE TIER — REAL-TIME SECURITY", "accent": "red", "stages": [
                    {"title": "Edge gateway", "sub": "ARM · Jetson"},
                    {"title": "Event filter", "sub": "intrusion · fall"},
                    {"title": "Security dash", "sub": "+ alerts", "filled": True},
                ]},
                {"label": "SERVER TIER — RETAIL ANALYTICS", "accent": "blue", "stages": [
                    {"title": "AI server", "sub": "A100 40GB"},
                    {"title": "Re-detect", "sub": "RT-DETR · ByteTrack"},
                    {"title": "Retail dash", "sub": "+ POS / ERP", "filled": True},
                ]},
            ],
            fleet_box={"label": "CCTV / NVR", "sub": "Existing fleet"},
            header="EXISTING INFRASTRUCTURE — SKT 1.6M AI CCTVs (4 yrs deployed)",
            footer="Same camera feed · two model stacks · two cadences",
            title="SKT Hybrid AI Camera — security + retail dual stack")),

        ("datapath", make_data_path(stages=[
            {"label": "PATIENT-SIDE", "accent": "teal", "items": [
                "BP / HR / SpO₂",
                "Glucose meter",
                "Smart pillow + sleep belt",
                "Holter ECG",
            ]},
            {"label": "MOBILE", "accent": "blue", "items": [
                "Patient gateway app",
            ]},
            {"label": "CLOUD (AWS)", "accent": "deep", "items": [
                "Lambda + Aurora",
                "Triage chatbot",
                "Alert routing engine",
                "Threshold rules · Escalation tree",
            ], "brain": True},
            {"label": "PROVIDER-SIDE", "accent": "magenta", "items": [
                "Caregiver dashboard",
                "Alert queue",
                "Patient cohort views",
                "Audit log",
            ]},
        ], callout={
            "title": "Abnormal-reading flow",
            "body": "Cloud rules engine matches incoming vitals against patient-specific thresholds. "
                    "Out-of-band triggers escalation: dashboard → SMS → auto-call.",
        }, title="RPM data path — device → cloud → caregiver")),
    ]

    for name, result in cases:
        html = wrap(name, result["svg"], result["natural_w"], result["natural_h"])
        path = EXAMPLES / f"{name}.html"
        path.write_text(html, encoding="utf-8")
        print(f"  → {path.name:20s}  {result['natural_w']}x{result['natural_h']}  "
              f"{len(result['svg']):,}c")


if __name__ == "__main__":
    main()
