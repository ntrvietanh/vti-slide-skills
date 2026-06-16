"""ECharts-backed chart specs for the VTI deck (v4.0 / M2).

The page-builder's chart components (bar / pie / line / stacked-bar) used to
emit hand-templated flat SVG. M2 routes them through Apache ECharts (vendored
locally at ``vendor/echarts.min.js``) for richer, on-brand data-viz.

How it stays export-safe (the PPTX/PNG screenshot race the design review
flagged for any JS-charting path):

  * The chart component renders only a placeholder ``<div class="vti-echart"
    data-vti-echart="<json option>">``. No JS runs at compose time.
  * ``runtime_html()`` injects the vendored ECharts UMD bundle + a tiny boot
    script ONCE per deck (only when a chart is present — see
    creator.build_deck_html).
  * The boot script inits every chart with the **SVG renderer** and
    **animation disabled**, so ``setOption`` paints synchronously into the
    DOM — no requestAnimationFrame, no canvas async paint. After the loop it
    sets ``window.__vtiChartsReady = true``.
  * Renderers (exporter.render_slides_to_pngs, figma html_backend) wait on
    that flag before screenshotting.

Everything here is pure-Python dict construction → JSON; no JS function
formatters (those can't survive JSON), so option strings are fully portable.
"""
from __future__ import annotations

import html as _html
import json
from pathlib import Path

# --- Brand palette (stable VTI brand hexes; mirrors tokens.css) -------------
_NAVY    = "#051934"
_DEEP    = "#0844A4"
_BLUE    = "#004AAD"
_MEDIUM  = "#1B5DE6"
_BRIGHT  = "#0468E6"
_SKY     = "#0782FF"
_LIGHT   = "#DAE9F6"
_TEAL    = "#43C9B7"
_AMBER   = "#F8C379"
_ORANGE  = "#ED8B2C"
_MAGENTA = "#D33A77"
_PURPLE  = "#7E5CD9"
_GREEN   = "#1A7A4A"
_RED     = "#B02020"

_INK      = "#1F2A3A"
_INK_SOFT = "#4B5A6E"
_MUTED    = "#6B7A8D"
_BORDER   = "#C8DCF0"
_DIVIDER  = "#E4ECF5"

_FONT = "'Plus Jakarta Sans','Arial',system-ui,sans-serif"

# tone alias → hex (matches the bar-chart tone contract + tokens)
TONE_HEX: dict[str, str] = {
    "navy": _NAVY, "deep": _DEEP, "blue": _BLUE, "medium": _MEDIUM,
    "bright": _BRIGHT, "sky": _SKY, "light": _LIGHT, "teal": _TEAL,
    "amber": _AMBER, "orange": _ORANGE, "magenta": _MAGENTA,
    "purple": _PURPLE, "green": _GREEN, "red": _RED,
    "gray": "#9DB0C4",   # neutral bar tone (bar-chart contract)
    "success": _GREEN,   # gauge/progress semantic tones
    "warning": _AMBER,
}

# default series colour cycle (used when a series/item gives no colour)
PALETTE = [_DEEP, _SKY, _TEAL, _MEDIUM, _AMBER, _NAVY, _MAGENTA, _PURPLE]


# ---------------------------------------------------------------------------
# colour helpers
# ---------------------------------------------------------------------------
def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lighten(hex_color: str, ratio: float) -> str:
    """Mix a colour toward white by ``ratio`` (0 = same, 1 = white)."""
    r, g, b = _hex_rgb(hex_color)
    r = int(r + (255 - r) * ratio)
    g = int(g + (255 - g) * ratio)
    b = int(b + (255 - b) * ratio)
    return f"#{r:02X}{g:02X}{b:02X}"


def _rgba(hex_color: str, alpha: float) -> str:
    r, g, b = _hex_rgb(hex_color)
    return f"rgba({r},{g},{b},{alpha})"


def _resolve(color: str | None, fallback: str) -> str:
    """Resolve a tone alias OR a literal hex to a hex; fall back if empty."""
    if not color:
        return fallback
    if color.startswith("#"):
        return color
    return TONE_HEX.get(color, fallback)


def _vgrad(top: str, bottom: str) -> dict:
    """Vertical (top→bottom) linear gradient option for depth on fills."""
    return {
        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
        "colorStops": [
            {"offset": 0, "color": top},
            {"offset": 1, "color": bottom},
        ],
    }


# ---------------------------------------------------------------------------
# shared base option pieces
# ---------------------------------------------------------------------------
def _text_style() -> dict:
    return {"fontFamily": _FONT, "color": _INK}


def _cat_axis(data: list[str]) -> dict:
    return {
        "type": "category",
        "data": data,
        "axisLine": {"lineStyle": {"color": _BORDER}},
        "axisTick": {"show": False},
        "axisLabel": {"color": _INK_SOFT, "fontSize": 11, "fontFamily": _FONT,
                      "fontWeight": 500},
    }


def _val_axis() -> dict:
    return {
        "type": "value",
        "axisLine": {"show": False},
        "axisTick": {"show": False},
        "splitLine": {"lineStyle": {"color": _DIVIDER, "type": "dashed"}},
        "axisLabel": {"color": _MUTED, "fontSize": 10, "fontFamily": _FONT},
    }


def _grid(*, top: int = 14) -> dict:
    return {"left": "2%", "right": "4%", "top": top, "bottom": "2%",
            "containLabel": True}


# ---------------------------------------------------------------------------
# option builders (props already validated by the composer renderer)
# ---------------------------------------------------------------------------
def bar_option(props: dict) -> dict:
    items = props["items"]
    horizontal = props.get("orientation", "vertical") == "horizontal"
    show_values = bool(props.get("show_values", True))
    cats = [str(it.get("label", "")) for it in items]

    data = []
    for it in items:
        tone = _resolve(it.get("tone"), _DEEP)
        radius = [0, 0, 4, 4] if horizontal else [4, 4, 0, 0]
        data.append({
            "value": float(it.get("value", 0)),
            "itemStyle": {
                "color": _vgrad(_lighten(tone, 0.22), tone),
                "borderRadius": radius,
            },
        })

    label = {"show": show_values,
             "position": "right" if horizontal else "top",
             "color": _INK_SOFT, "fontSize": 11, "fontWeight": 500,
             "fontFamily": _FONT}

    opt = {
        "textStyle": _text_style(),
        "grid": _grid(),
        "series": [{"type": "bar", "data": data, "barWidth": "55%",
                    "label": label}],
    }
    if horizontal:
        opt["xAxis"] = _val_axis()
        opt["yAxis"] = {**_cat_axis(cats), "inverse": True}
    else:
        opt["xAxis"] = _cat_axis(cats)
        opt["yAxis"] = _val_axis()
    return opt


def line_option(props: dict) -> dict:
    items = props["items"]
    area_fill = bool(props.get("area_fill", True))
    show_dots = bool(props.get("show_dots", True))
    show_values = bool(props.get("show_values", False))
    labels = [str(it.get("label", "")) for it in items]
    values = [float(it.get("value", 0)) for it in items]

    series = {
        "type": "line",
        "data": values,
        "smooth": True,
        "symbol": "circle" if show_dots else "none",
        "symbolSize": 7,
        "lineStyle": {"width": 3, "color": _DEEP},
        "itemStyle": {"color": _DEEP, "borderColor": "#FFFFFF",
                      "borderWidth": 2},
        "label": {"show": show_values, "position": "top", "color": _INK_SOFT,
                  "fontSize": 11, "fontWeight": 500, "fontFamily": _FONT},
    }
    if area_fill:
        series["areaStyle"] = {
            "color": _vgrad(_rgba(_SKY, 0.34), _rgba(_SKY, 0.02)),
            "origin": "start",
        }
    return {
        "textStyle": _text_style(),
        "grid": _grid(),
        "xAxis": {**_cat_axis(labels), "boundaryGap": False},
        "yAxis": _val_axis(),
        "series": [series],
    }


def pie_option(props: dict) -> dict:
    items = props["items"]
    donut = bool(props.get("donut", False))
    center_value = str(props.get("center_value", ""))
    center_label = str(props.get("center_label", ""))
    legend_below = props.get("layout", "legend-right") == "legend-below"

    data = []
    for i, it in enumerate(items):
        color = _resolve(it.get("color"), PALETTE[i % len(PALETTE)])
        data.append({
            "name": str(it.get("label", "")),
            "value": float(it.get("value", 0)),
            "itemStyle": {"color": color},
        })

    if legend_below:
        center = ["50%", "44%"]
        legend = {"bottom": 4, "left": "center", "orient": "horizontal",
                  "textStyle": {"color": _INK_SOFT, "fontFamily": _FONT,
                                "fontSize": 11}}
    else:
        center = ["34%", "52%"]
        legend = {"right": "2%", "top": "middle", "orient": "vertical",
                  "textStyle": {"color": _INK_SOFT, "fontFamily": _FONT,
                                "fontSize": 11}}

    series = {
        "type": "pie",
        "radius": ["52%", "74%"] if donut else ["0%", "70%"],
        "center": center,
        "data": data,
        "label": {"show": False},
        "labelLine": {"show": False},
        "itemStyle": {"borderColor": "#FFFFFF", "borderWidth": 2},
    }
    opt = {
        "textStyle": _text_style(),
        "legend": legend,
        "series": [series],
    }
    if donut and (center_value or center_label):
        opt["title"] = {
            "text": center_value,
            "subtext": center_label,
            "left": center[0],
            "top": center[1],
            "textAlign": "center",
            "textVerticalAlign": "middle",
            "textStyle": {"color": _BLUE, "fontSize": 26, "fontWeight": 600,
                          "fontFamily": _FONT},
            "subtextStyle": {"color": _MUTED, "fontSize": 11,
                             "fontFamily": _FONT},
            "itemGap": 2,
        }
    return opt


def stacked_option(props: dict) -> dict:
    categories = props["categories"]
    series_in = props["series"]
    series = []
    for i, s in enumerate(series_in):
        color = _resolve(s.get("color"), PALETTE[i % len(PALETTE)])
        series.append({
            "name": str(s.get("name", "")),
            "type": "bar",
            "stack": "total",
            "data": [float(v) for v in s.get("values", [])],
            "itemStyle": {"color": color},
            "barWidth": "55%",
        })
    return {
        "textStyle": _text_style(),
        "legend": {"top": 2, "left": "center", "orient": "horizontal",
                   "textStyle": {"color": _INK_SOFT, "fontFamily": _FONT,
                                 "fontSize": 11}, "itemHeight": 10,
                   "itemWidth": 14},
        "grid": _grid(top=34),
        "xAxis": _cat_axis(list(categories)),
        "yAxis": _val_axis(),
        "series": series,
    }


def _fmt(n: float) -> str:
    """Terse numeric label."""
    if n == int(n):
        return f"{int(n):,}"
    return f"{n:,.1f}"


def gauge_option(props: dict) -> dict:
    """Single semicircular KPI gauge."""
    value = float(props["value"])
    max_v = float(props.get("max", 100)) or 1.0
    color = _resolve(props.get("tone"), _DEEP)
    suffix = props.get("suffix")
    if suffix is None:
        suffix = "" if max_v == 100 else f" / {int(max_v)}"
    value_text = str(props.get("value_text", _fmt(value)))
    label = str(props.get("label", ""))
    return {
        "textStyle": _text_style(),
        "series": [{
            "type": "gauge",
            "startAngle": 200, "endAngle": -20,
            "min": 0, "max": max_v,
            "radius": "94%", "center": ["50%", "60%"],
            "progress": {"show": True, "width": 16, "roundCap": True,
                         "itemStyle": {"color": color}},
            "axisLine": {"lineStyle": {"width": 16, "color": [[1, "#E4ECF5"]]}},
            "axisTick": {"show": False}, "splitLine": {"show": False},
            "axisLabel": {"show": False}, "pointer": {"show": False},
            "anchor": {"show": False},
            "title": {"show": bool(label), "offsetCenter": [0, "32%"],
                      "color": _MUTED, "fontSize": 12, "fontFamily": _FONT},
            "detail": {"valueAnimation": False, "offsetCenter": [0, "-6%"],
                       "formatter": value_text + suffix, "color": _BLUE,
                       "fontSize": 32, "fontWeight": 600, "fontFamily": _FONT},
            "data": [{"value": value, "name": label}],
        }],
    }


def progress_option(props: dict) -> dict:
    """Stack of horizontal progress bars (one per item) with a track."""
    items = props["items"]
    labels, data = [], []
    for i, it in enumerate(items):
        value = float(it.get("value", 0))
        max_v = float(it.get("max", 100)) or 1.0
        pct = max(0.0, min(100.0, value / max_v * 100.0))
        color = _resolve(it.get("tone"), PALETTE[i % len(PALETTE)])
        vtext = str(it.get("value_text") or f"{pct:.0f}%")
        labels.append(str(it.get("label", "")))
        data.append({
            "value": pct,
            "itemStyle": {"color": color, "borderRadius": 7},
            "label": {"show": True, "position": "right", "formatter": vtext,
                      "color": _INK_SOFT, "fontSize": 11, "fontWeight": 500,
                      "fontFamily": _FONT},
        })
    return {
        "textStyle": _text_style(),
        "grid": {"left": 4, "right": "10%", "top": 6, "bottom": 6,
                 "containLabel": True},
        "xAxis": {"type": "value", "max": 100, "show": False},
        "yAxis": {"type": "category", "data": labels, "inverse": True,
                  "axisLine": {"show": False}, "axisTick": {"show": False},
                  "axisLabel": {"color": _INK, "fontSize": 12, "fontWeight": 500,
                                "fontFamily": _FONT}},
        "series": [{
            "type": "bar", "data": data, "barWidth": 14,
            "showBackground": True,
            "backgroundStyle": {"color": "#E4ECF5", "borderRadius": 7},
        }],
    }


def funnel_option(props: dict) -> dict:
    """Conversion funnel (stages sorted descending)."""
    stages = props["stages"]
    show_pct = bool(props.get("show_pct_of_top", True))
    top = float(stages[0].get("value", 1)) or 1.0
    data = []
    for i, st in enumerate(stages):
        value = float(st.get("value", 0))
        color = _resolve(st.get("color"), PALETTE[i % len(PALETTE)])
        name = str(st.get("label", ""))
        pct = value / top * 100.0
        lab = (f"{name}\n{_fmt(value)}  ·  {pct:.0f}% of top"
               if show_pct else f"{name}\n{_fmt(value)}")
        data.append({
            "name": name, "value": value,
            "itemStyle": {"color": color, "borderColor": "#FFFFFF",
                          "borderWidth": 1},
            "label": {"formatter": lab},
        })
    return {
        "textStyle": _text_style(),
        "series": [{
            "type": "funnel", "top": 10, "bottom": 10, "left": "8%",
            "right": "8%", "min": 0, "max": top, "minSize": "26%",
            "maxSize": "100%", "sort": "descending", "gap": 2,
            "label": {"show": True, "position": "inside", "color": "#FFFFFF",
                      "fontFamily": _FONT, "fontSize": 12, "fontWeight": 500,
                      "lineHeight": 15},
            "data": data,
        }],
    }


# ---------------------------------------------------------------------------
# div wrapper + deck runtime
# ---------------------------------------------------------------------------
def echart_div(option: dict, *, title_html: str = "", min_h: int = 190) -> str:
    """Wrap an ECharts option as the placeholder div the boot script hydrates."""
    payload = _html.escape(json.dumps(option, ensure_ascii=False), quote=True)
    return (
        '<div class="vti-echart-wrap" '
        'style="display:flex;flex-direction:column;height:100%;width:100%">'
        f'{title_html}'
        f'<div class="vti-echart" data-vti-echart="{payload}" '
        f'style="flex:1 1 auto;width:100%;min-height:{min_h}px"></div>'
        '</div>'
    )


def chart_title_html(title: str) -> str:
    """Brand chart title sitting above the canvas (fluid caption token)."""
    if not title:
        return ""
    t = _html.escape(str(title), quote=True)
    return (
        '<div class="vti-echart-title" style="'
        'font-family:var(--vti-font-body);'
        'font-size:var(--vti-fs-caption);font-weight:500;'
        'letter-spacing:.04em;text-transform:uppercase;'
        f'color:var(--vti-blue);margin:0 0 6px 2px">{t}</div>'
    )


# The boot script: SVG renderer + animation off ⇒ synchronous paint, then a
# single readiness flag. Kept tiny and dependency-free.
BOOT_JS = """
(function(){
  function boot(){
    if (typeof echarts === 'undefined') { window.__vtiChartsReady = true; return; }
    var nodes = document.querySelectorAll('.vti-echart');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var raw = el.getAttribute('data-vti-echart');
      if (!raw) continue;
      try {
        var opt = JSON.parse(raw);
        opt.animation = false;
        var chart = echarts.init(el, null, { renderer: 'svg' });
        chart.setOption(opt);
      } catch (e) { /* bad spec → leave the cell empty, keep going */ }
    }
    window.__vtiChartsReady = true;
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
""".strip()

_VENDOR_ECHARTS = Path(__file__).resolve().parent / "vendor" / "echarts.min.js"


def runtime_html() -> str:
    """Return the <script> block (vendored ECharts + boot) to inject ONCE
    per deck, only when a chart placeholder is present. Raises if the vendor
    bundle is missing so the failure is loud, not a silently chart-less deck.
    """
    if not _VENDOR_ECHARTS.exists():
        raise FileNotFoundError(
            f"ECharts bundle not found at {_VENDOR_ECHARTS}. "
            "Re-vendor it: curl -sL "
            "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js "
            f"-o {_VENDOR_ECHARTS}"
        )
    js = _VENDOR_ECHARTS.read_text(encoding="utf-8")
    return f"<script>{js}</script>\n<script>{BOOT_JS}</script>\n"


__all__ = [
    "TONE_HEX", "PALETTE",
    "bar_option", "line_option", "pie_option", "stacked_option",
    "gauge_option", "progress_option", "funnel_option",
    "echart_div", "chart_title_html", "runtime_html", "BOOT_JS",
]
