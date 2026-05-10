"""
Whitespace analyzer — pixel-level detection of empty regions in a
rendered slide screenshot.

Algorithm (v0.1 — W3.1):
  1. Read screenshot as grayscale numpy array
  2. Tile-based variance: divide image into N×M tiles (default 40×40px)
  3. A tile is "blank" if: mean grayscale > 240 AND std < 5
  4. Connected component labeling on blank tiles → cluster regions
  5. Filter: only return clusters whose bbox > min_size (default 200×150)
  6. Return list of gaps: {x, y, w, h, area, density_score}

Limitations of v0.1 (will improve in W3.2):
  - White-only background detection (slides with bg-tokyo / dark sections
    will report different "blank" semantics)
  - Doesn't distinguish "intentional whitespace" (margins, gutters)
    from "decorate-able whitespace" (slide bottom, corner gaps)
  - No DOM context — can't tell if blank region is inside a flex
    container or genuinely free space

Public API:
  detect_gaps(image_path, **kwargs) → list[Gap]
  visualize_gaps(image_path, gaps, output_path) → None  (debug overlay)
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

import numpy as np
from PIL import Image, ImageDraw


@dataclass
class Gap:
    """A whitespace region detected in a slide."""
    x: int                # left edge (pixels)
    y: int                # top edge
    w: int                # width
    h: int                # height
    area: int             # w * h
    density_score: float  # 1.0 = pure white, lower = more variation
    aspect: str           # 'square' / 'landscape' / 'portrait' / 'thin-h' / 'thin-v'
    position: str         # 'top-l' / 'top-c' / 'top-r' / 'mid-l' / 'mid-c' / 'mid-r' / 'bot-l' / 'bot-c' / 'bot-r'
    merged_with_footer: bool = False  # gap extends across footer chrome
    merged_with_header: bool = False  # gap extends across header chrome

    @property
    def bbox(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)

    def to_dict(self):
        return asdict(self)


def _classify_aspect(w: int, h: int) -> str:
    if h == 0 or w == 0:
        return 'thin-h'
    ratio = w / h
    if ratio > 4:
        return 'thin-h'
    if ratio < 0.25:
        return 'thin-v'
    if ratio > 1.4:
        return 'landscape'
    if ratio < 0.7:
        return 'portrait'
    return 'square'


def _classify_position(cx: int, cy: int, img_w: int, img_h: int) -> str:
    """3×3 grid position by gap center."""
    col = 'l' if cx < img_w / 3 else ('r' if cx > 2 * img_w / 3 else 'c')
    row = 'top' if cy < img_h / 3 else ('bot' if cy > 2 * img_h / 3 else 'mid')
    return f'{row}-{col}'


def detect_gaps(image_path: str, *,
                tile_size: int = 40,
                whiteness_threshold: int = 240,
                std_threshold: float = 5.0,
                min_gap_w: int = 200,
                min_gap_h: int = 150,
                content_dilate_tiles: int = 2,
                top_k: int = 5,
                header_pct: float = 0.10,
                footer_pct: float = 0.08,
                merge_with_footer: bool = True,
                merge_with_header: bool = False,
                merge_threshold_pct: float = 0.08) -> list[Gap]:
    """Detect whitespace gaps in a slide screenshot using content-dilation +
    maximum-empty-rectangle, with chrome-zone awareness.

    Algorithm:
      1. Tile the image; mark each tile as content or blank
      2. **Mask chrome zones** (top header strip + bottom footer strip) as
         non-eligible — these are NEVER decoration targets
      3. Dilate content tiles by ``content_dilate_tiles`` (8-neighborhood) —
         this erodes thin gutter strips between content blocks
      4. Find the top-K largest empty rectangles by greedy max-rect search
         within the eligible (non-chrome) zone
      5. **Post-process: footer merge** — if a gap's bottom edge is within
         ``merge_threshold_pct`` of footer top, extend the gap down to
         absorb the footer zone (decoration spans content+footer for
         visual cohesion)
      6. Filter by ``min_gap_w/h``, classify aspect+position

    Args:
        image_path: path to PNG/JPG screenshot
        tile_size: detection grid resolution (smaller = more precise, slower)
        whiteness_threshold: tile mean must exceed this (0-255) to be blank
        std_threshold: tile std-dev must be below this to be blank
        min_gap_w/h: minimum cluster size to return as a gap (pixels)
        content_dilate_tiles: how many tiles to grow content by
        top_k: max number of gaps to return
        header_pct: fraction of image height excluded as top chrome (default 10%)
        footer_pct: fraction of image height excluded as bottom chrome (default 8%)
        merge_with_footer: if True, gaps adjacent to footer extend into it
        merge_with_header: if True, gaps adjacent to header extend into it
        merge_threshold_pct: max distance to chrome (in image-height fraction)
            for a gap to be considered "adjacent" and merged

    Returns:
        list of Gap objects, sorted by area (largest first). Gaps may have
        ``merged_with_footer=True`` or ``merged_with_header=True`` when
        extended into chrome zones.
    """
    img = Image.open(image_path).convert('L')
    arr = np.array(img, dtype=np.float32)
    H, W = arr.shape

    tiles_y = H // tile_size
    tiles_x = W // tile_size

    # Compute chrome zone boundaries (in pixels)
    header_y = int(H * header_pct)
    footer_y = int(H * (1 - footer_pct))

    # Step 1: classify tiles
    means = np.zeros((tiles_y, tiles_x), dtype=np.float32)
    is_blank = np.zeros((tiles_y, tiles_x), dtype=bool)
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile = arr[ty * tile_size:(ty + 1) * tile_size,
                       tx * tile_size:(tx + 1) * tile_size]
            m = float(tile.mean())
            s = float(tile.std())
            means[ty, tx] = m
            is_blank[ty, tx] = (m > whiteness_threshold and s < std_threshold)

    # Step 2: mask chrome zones as ineligible (blank=False in chrome rows)
    chrome_eligible = np.ones((tiles_y, tiles_x), dtype=bool)
    for ty in range(tiles_y):
        ty_pixel_top = ty * tile_size
        ty_pixel_bot = (ty + 1) * tile_size
        # Tile is in header zone if its bottom is below header_y? No,
        # tile is in header if its TOP is above header_y line.
        if ty_pixel_bot <= header_y:
            chrome_eligible[ty, :] = False  # fully in header
        elif ty_pixel_top >= footer_y:
            chrome_eligible[ty, :] = False  # fully in footer

    eligible_blank = is_blank & chrome_eligible

    # Step 3: dilate content (erode blank) by N tiles within eligible zone
    blank = eligible_blank.copy()
    for _ in range(content_dilate_tiles):
        new = blank.copy()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                if not blank[ty, tx]:
                    new[ty, tx] = False
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = ty + dy, tx + dx
                        if 0 <= ny < tiles_y and 0 <= nx < tiles_x:
                            # Treat chrome zones as "content" for erosion —
                            # this allows gaps to extend right up to the
                            # chrome boundary without erosion eating them
                            if not blank[ny, nx] and chrome_eligible[ny, nx]:
                                new[ty, tx] = False
                                break
                    if not new[ty, tx]:
                        break
        blank = new

    # Step 4: find top-K maximum empty rectangles within blank
    available = blank.copy()
    raw_gaps: list[tuple] = []  # (x, y, w, h, density, whiteness)
    min_w_tiles = max(1, min_gap_w // tile_size)
    min_h_tiles = max(1, min_gap_h // tile_size)

    for _ in range(top_k):
        rect = _max_rectangle_in_binary(available)
        if rect is None:
            break
        ty, tx, h_t, w_t = rect
        if w_t < min_w_tiles or h_t < min_h_tiles:
            break
        x = tx * tile_size
        y = ty * tile_size
        w = w_t * tile_size
        h = h_t * tile_size
        sub = is_blank[ty:ty + h_t, tx:tx + w_t]
        density = float(sub.mean()) if sub.size else 0.0
        sub_means = means[ty:ty + h_t, tx:tx + w_t]
        whiteness = float(sub_means.mean()) / 255 if sub_means.size else 0.0
        raw_gaps.append((x, y, w, h, density, whiteness))
        available[ty:ty + h_t, tx:tx + w_t] = False

    # Step 5: footer/header merge post-processing
    # A gap is "adjacent to footer" if its bottom edge reaches at least
    # ``footer_y - merge_threshold_px``. Same for header.
    merge_threshold_px = int(H * merge_threshold_pct)
    gaps = []
    for (x, y, w, h, density, whiteness) in raw_gaps:
        merged_footer = False
        merged_header = False
        gap_bottom = y + h
        gap_top = y
        # Footer merge: gap bottom is within threshold of footer line
        # (or already crossing into footer zone if some tile rows are
        # mixed-eligibility — be inclusive)
        if merge_with_footer and gap_bottom >= (footer_y - merge_threshold_px):
            h = H - y          # extend gap down to image bottom
            merged_footer = True
        # Header merge (rare; default off): gap top within threshold
        if merge_with_header and gap_top <= (header_y + merge_threshold_px):
            h = h + y          # extend up to top
            y = 0
            merged_header = True

        gaps.append(Gap(
            x=x, y=y, w=w, h=h, area=w * h,
            density_score=round(density * whiteness, 3),
            aspect=_classify_aspect(w, h),
            position=_classify_position(x + w // 2, y + h // 2, W, H),
            merged_with_footer=merged_footer,
            merged_with_header=merged_header,
        ))

    # Step 5b: dedupe overlapping gaps. After merge, two gaps may now
    # cover overlapping regions (e.g. a band gap + a footer-extended
    # gap directly below). Keep the larger one when overlap > 70%.
    def _bbox_overlap_ratio(a, b):
        ix1 = max(a.x, b.x)
        iy1 = max(a.y, b.y)
        ix2 = min(a.x + a.w, b.x + b.w)
        iy2 = min(a.y + a.h, b.y + b.h)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        smaller = min(a.area, b.area)
        return inter / smaller if smaller else 0.0

    gaps.sort(key=lambda g: g.area, reverse=True)
    deduped = []
    for g in gaps:
        if any(_bbox_overlap_ratio(g, kept) > 0.70 for kept in deduped):
            continue
        deduped.append(g)
    gaps = deduped

    return gaps


def _max_rectangle_in_binary(matrix: np.ndarray) -> tuple | None:
    """Find the largest rectangle of True values in a binary matrix.

    Uses the classic "largest rectangle in histogram" algorithm row by row.

    Returns:
        (top_row, left_col, height, width) or None if no True cell.
    """
    if matrix.size == 0 or not matrix.any():
        return None
    rows, cols = matrix.shape
    heights = np.zeros(cols, dtype=np.int32)
    best = (0, 0, 0, 0, 0)  # area, top, left, height, width

    for r in range(rows):
        # update histogram
        for c in range(cols):
            heights[c] = heights[c] + 1 if matrix[r, c] else 0
        # find max rect in this histogram
        stack = []
        for c in range(cols + 1):
            cur_h = heights[c] if c < cols else 0
            while stack and heights[stack[-1]] > cur_h:
                top_idx = stack.pop()
                h = int(heights[top_idx])
                left = stack[-1] + 1 if stack else 0
                w = c - left
                area = h * w
                if area > best[0]:
                    best = (area, r - h + 1, left, h, w)
            stack.append(c)

    if best[0] == 0:
        return None
    _, top, left, h, w = best
    return (top, left, h, w)


def visualize_gaps(image_path: str,
                   gaps: list[Gap],
                   output_path: str,
                   show_labels: bool = True,
                   header_pct: float = 0.10,
                   footer_pct: float = 0.08,
                   show_chrome_zones: bool = True) -> None:
    """Overlay detected gaps as semi-transparent rectangles on the
    original screenshot. For visual debugging.

    Args:
        image_path: source screenshot
        gaps: detected gaps (output of detect_gaps)
        output_path: where to save annotated PNG
        show_labels: render gap labels (size, position, density)
        header_pct/footer_pct: chrome zone fractions (must match detection)
        show_chrome_zones: if True, draw chrome boundary lines so it's
            clear which area was excluded from detection
    """
    img = Image.open(image_path).convert('RGBA')
    W, H = img.size
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Chrome zone boundaries (visualization only)
    header_y = int(H * header_pct)
    footer_y = int(H * (1 - footer_pct))

    if show_chrome_zones:
        # Tint chrome zones lightly to indicate "excluded from detection"
        chrome_color = (130, 130, 130, 30)
        draw.rectangle([0, 0, W, header_y], fill=chrome_color)
        draw.rectangle([0, footer_y, W, H], fill=chrome_color)
        # Boundary lines
        line_color = (130, 130, 130, 180)
        draw.line([0, header_y, W, header_y], fill=line_color, width=2)
        draw.line([0, footer_y, W, footer_y], fill=line_color, width=2)
        # Chrome labels
        draw.text((8, 8), "HEADER ZONE (excluded)", fill=(80, 80, 80, 230))
        draw.text((8, footer_y + 8), "FOOTER ZONE (excluded)",
                  fill=(80, 80, 80, 230))

    palette = [
        (220, 50, 50, 100),
        (220, 130, 30, 90),
        (220, 200, 30, 85),
        (50, 200, 130, 80),
        (50, 130, 220, 80),
    ]
    for i, g in enumerate(gaps):
        color = palette[min(i, len(palette) - 1)]
        # Fill
        draw.rectangle([g.x, g.y, g.x + g.w, g.y + g.h], fill=color)
        # Stroke — thicker if merged
        stroke_color = (color[0], color[1], color[2], 230)
        stroke_width = 5 if (g.merged_with_footer or g.merged_with_header) else 3
        draw.rectangle([g.x, g.y, g.x + g.w, g.y + g.h],
                       outline=stroke_color, width=stroke_width)
        # Label
        if show_labels:
            merge_tag = ''
            if g.merged_with_footer:
                merge_tag = ' +FOOTER'
            elif g.merged_with_header:
                merge_tag = ' +HEADER'
            label = (f"#{i+1}  {g.w}×{g.h}  {g.aspect}  {g.position}  "
                     f"d={g.density_score}{merge_tag}")
            tx, ty = g.x + 8, g.y + 8
            draw.rectangle([tx - 3, ty - 2, tx + 8 + len(label) * 7, ty + 16],
                           fill=(0, 0, 0, 200))
            draw.text((tx, ty), label, fill=(255, 255, 255, 255))

    out = Image.alpha_composite(img, overlay)
    out.convert('RGB').save(output_path)


def gaps_to_json(gaps: list[Gap]) -> str:
    return json.dumps([g.to_dict() for g in gaps], indent=2)


# ---------------------------------------------------------------------------
# CLI / smoke test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: whitespace_analyzer.py <slide_screenshot.png> [output_overlay.png]")
        sys.exit(1)
    img_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'gaps_debug.png'
    gaps = detect_gaps(img_path)
    print(f"Detected {len(gaps)} gaps in {img_path}:")
    for i, g in enumerate(gaps, 1):
        print(f"  #{i}: {g.w}×{g.h} at ({g.x},{g.y}) — "
              f"{g.aspect} {g.position}, d={g.density_score}")
    visualize_gaps(img_path, gaps, out_path)
    print(f"Visual debug overlay → {out_path}")
