"""
gap_classifier.py — W3.3 of vti-slide-decorator

Enriches Gap (output of whitespace_analyzer.detect_gaps) with brand-aware
taxonomy + strategy compatibility hints. The output feeds strategy_selector
(W3.5) which makes the final pick per slide.

Classification dimensions
-------------------------

1. **size_class** — perceptual area buckets
     xs    <100K px² → too small, skip decoration
     small  100K-300K → typographic (small numeral), small motif
     medium 300K-800K → all strategies plausible
     large  800K-2M   → abstract_geometric / large typographic / motif
     xl     >2M       → abstract_geometric (full-bleed), bold motif

2. **region** — derived from Gap.position
     corner   → top-l, top-r, bot-l, bot-r
     edge     → top-c, bot-c, mid-l, mid-r
     center   → mid-c

3. **brand_context** — composite signal driving strategy choice
     footer-merged    — gap.merged_with_footer=True; decoration spans bottom
     header-merged    — gap.merged_with_header=True (rare)
     bottom-band      — wide horizontal at bottom, NOT footer-merged
     top-band         — wide horizontal at top
     side-strip       — tall narrow on left/right edge
     corner-pocket    — small gap in a corner
     standalone-block — center/edge gap that doesn't fit above

4. **compatible_strategies** — ordered list of viable strategies, best-first
     Subset of: abstract_geometric, topical_motif, typographic, none

5. **decoration_eligible** — final gate; False = strategy=none, no overlay

Stable contract: this module READS Gap dataclass (immutable) and RETURNS
ClassifiedGap (Gap + taxonomy fields). Does NOT mutate the input Gap.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Optional

from whitespace_analyzer import Gap


# ---------------------------------------------------------------------------
# Tunable thresholds (tuned on 2560×1440 thumbnails; scale-invariant logic
# uses ratios where possible)
# ---------------------------------------------------------------------------

SIZE_THRESHOLDS_PX2 = {
    'xs':     100_000,    # < 100K
    'small':  300_000,    # 100K - 300K
    'medium': 800_000,    # 300K - 800K
    'large':  2_000_000,  # 800K - 2M
    # xl: > 2M
}

# A gap is decoration-eligible if its area >= this threshold
MIN_ELIGIBLE_AREA_PX2 = 100_000

# Aspect classification refinement
THIN_RATIO = 4.0  # w/h or h/w > 4 = thin
SQUARE_TOLERANCE = 1.3  # max(w,h)/min(w,h) <= 1.3 = square


# ---------------------------------------------------------------------------
# ClassifiedGap dataclass
# ---------------------------------------------------------------------------

@dataclass
class ClassifiedGap:
    """A Gap enriched with brand taxonomy and strategy hints."""
    gap: Gap

    # Taxonomy
    size_class: str         # 'xs' / 'small' / 'medium' / 'large' / 'xl'
    region: str             # 'corner' / 'edge' / 'center'
    brand_context: str      # see module docstring
    decoration_eligible: bool

    # Strategy hint (ordered list, best-first; selector makes final pick)
    compatible_strategies: list[str] = field(default_factory=list)

    # Reasoning trace (for debug + audit)
    reasoning: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'gap': self.gap.to_dict(),
            'size_class': self.size_class,
            'region': self.region,
            'brand_context': self.brand_context,
            'decoration_eligible': self.decoration_eligible,
            'compatible_strategies': self.compatible_strategies,
            'reasoning': self.reasoning,
        }


# ---------------------------------------------------------------------------
# Internal classifiers
# ---------------------------------------------------------------------------

def _size_class(area_px2: int) -> str:
    if area_px2 < SIZE_THRESHOLDS_PX2['xs']:
        return 'xs'
    if area_px2 < SIZE_THRESHOLDS_PX2['small']:
        return 'small'
    if area_px2 < SIZE_THRESHOLDS_PX2['medium']:
        return 'medium'
    if area_px2 < SIZE_THRESHOLDS_PX2['large']:
        return 'large'
    return 'xl'


def _region(position: str) -> str:
    """Map 3×3 position to coarse region."""
    if position in ('top-l', 'top-r', 'bot-l', 'bot-r'):
        return 'corner'
    if position == 'mid-c':
        return 'center'
    return 'edge'  # top-c, bot-c, mid-l, mid-r


def _brand_context(gap: Gap, region: str) -> str:
    """Derive composite brand-context bucket."""
    if gap.merged_with_footer:
        return 'footer-merged'
    if gap.merged_with_header:
        return 'header-merged'

    # Bottom/top horizontal bands (wide, low height, edge position)
    if gap.aspect == 'thin-h':
        if gap.position.startswith('bot-'):
            return 'bottom-band'
        if gap.position.startswith('top-'):
            return 'top-band'

    # Side strips (tall, narrow, on left/right edge)
    if gap.aspect in ('thin-v', 'portrait') and gap.position in ('mid-l', 'mid-r'):
        return 'side-strip'

    # Corner pockets — corner region with smallish area
    if region == 'corner' and gap.area < SIZE_THRESHOLDS_PX2['medium']:
        return 'corner-pocket'

    return 'standalone-block'


def _compatible_strategies(size_class: str,
                           region: str,
                           brand_context: str,
                           gap: Gap) -> tuple[list[str], list[str]]:
    """Pick ordered list of compatible strategies + reasoning trace.

    Returns (strategies, reasoning_lines).

    Strategy semantics:
      typographic        — oversized numeral / glyph; works in any size,
                           best for corners and footer-merged
      abstract_geometric — gradient blob / dot grid / mesh; best for
                           medium+ areas with breathing room
      topical_motif      — SVG primitive from slide keywords; best for
                           medium+ areas, NOT corners (motif needs space)
      none               — explicit skip; xs gaps or full slides
    """
    strategies: list[str] = []
    reasoning: list[str] = []

    # Hard skip: gap too small
    if size_class == 'xs':
        reasoning.append(
            f"size_class={size_class!r} < eligibility threshold "
            f"({MIN_ELIGIBLE_AREA_PX2:,} px²) → none")
        return ['none'], reasoning

    # Brand context drives primary strategy ordering
    if brand_context == 'footer-merged':
        # Decoration spans content + footer → typographic numeral
        # works beautifully (page number style), abstract gradient also fits
        strategies = ['typographic', 'abstract_geometric', 'topical_motif']
        reasoning.append(
            "footer-merged → typographic (numeral/page-style) preferred; "
            "abstract gradient also fits a band that crosses chrome")

    elif brand_context == 'header-merged':
        strategies = ['typographic', 'abstract_geometric']
        reasoning.append(
            "header-merged → typographic preferred (rare context)")

    elif brand_context == 'bottom-band':
        # Wide horizontal band at bottom — gradient strip works well
        strategies = ['abstract_geometric', 'typographic', 'topical_motif']
        reasoning.append(
            "bottom-band → abstract_geometric (gradient strip) preferred; "
            "typographic (oversized numeral) also good")

    elif brand_context == 'top-band':
        strategies = ['abstract_geometric', 'topical_motif']
        reasoning.append("top-band → abstract gradient or motif")

    elif brand_context == 'side-strip':
        # Tall narrow vertical strip — vertical accent or motif
        strategies = ['abstract_geometric', 'topical_motif']
        reasoning.append(
            "side-strip → abstract (vertical accent line) or motif column")

    elif brand_context == 'corner-pocket':
        # Small corner gap — typographic glyph or skip
        strategies = ['typographic', 'none']
        reasoning.append("corner-pocket → typographic glyph or skip")

    else:  # standalone-block
        # Center/edge block — full strategy choice
        if region == 'center':
            strategies = ['topical_motif', 'abstract_geometric', 'typographic']
            reasoning.append(
                "standalone-block at center → topical_motif preferred "
                "(centered motif reads as intentional)")
        else:
            strategies = ['abstract_geometric', 'topical_motif', 'typographic']
            reasoning.append(
                "standalone-block at edge → abstract_geometric or motif")

    # Size-based filtering — large+ favors geometric/motif over typographic
    if size_class in ('large', 'xl') and 'typographic' in strategies:
        # typographic in large area looks lonely; demote
        idx = strategies.index('typographic')
        if idx == 0:
            strategies = strategies[1:] + ['typographic']
            reasoning.append(
                f"size_class={size_class!r} → demote typographic "
                "(large area benefits from richer fill)")

    # Small gaps: prefer typographic over geometric (geometric needs room)
    if size_class == 'small':
        if 'typographic' in strategies and strategies[0] != 'typographic':
            strategies.remove('typographic')
            strategies.insert(0, 'typographic')
            reasoning.append(
                "size_class='small' → promote typographic "
                "(small geometric/motif looks cluttered)")

    # Aspect-based filtering — thin gaps don't suit motifs
    if gap.aspect in ('thin-h', 'thin-v'):
        if 'topical_motif' in strategies:
            strategies.remove('topical_motif')
            reasoning.append(
                f"aspect={gap.aspect!r} → drop topical_motif "
                "(motifs need square-ish space)")

    return strategies, reasoning


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_gap(gap: Gap, slide_meta: Optional[dict] = None) -> ClassifiedGap:
    """Classify a single gap.

    Args:
        gap: a Gap from whitespace_analyzer.detect_gaps
        slide_meta: optional slide_meta dict (currently unused; reserved
            for future content-aware classification e.g. section keywords
            steering topical_motif preference)

    Returns:
        ClassifiedGap with taxonomy + ordered compatible strategies.
    """
    size_class = _size_class(gap.area)
    region = _region(gap.position)
    brand_context = _brand_context(gap, region)

    decoration_eligible = (gap.area >= MIN_ELIGIBLE_AREA_PX2)
    strategies, reasoning = _compatible_strategies(
        size_class, region, brand_context, gap)

    if not decoration_eligible:
        strategies = ['none']
        reasoning = [
            f"area={gap.area:,} px² < {MIN_ELIGIBLE_AREA_PX2:,} → none"]

    return ClassifiedGap(
        gap=gap,
        size_class=size_class,
        region=region,
        brand_context=brand_context,
        decoration_eligible=decoration_eligible,
        compatible_strategies=strategies,
        reasoning=reasoning,
    )


def classify_slide_gaps(gaps: list[Gap],
                        slide_meta: Optional[dict] = None) -> list[ClassifiedGap]:
    """Classify all gaps in a single slide. Returns list in same order as input."""
    return [classify_gap(g, slide_meta) for g in gaps]


# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------

def format_classification_table(classified: list[ClassifiedGap],
                                 slide_label: str = "") -> str:
    """Pretty-print a per-gap classification table for terminal/debug."""
    if not classified:
        return f"  {slide_label}: 0 gaps (NONE)"

    lines = [f"  {slide_label}: {len(classified)} gap(s)"]
    for i, cg in enumerate(classified, 1):
        g = cg.gap
        merge = ' +F' if g.merged_with_footer else (
            ' +H' if g.merged_with_header else '')
        lines.append(
            f"    #{i}: {g.w}×{g.h} ({g.area/1000:.0f}K) "
            f"{g.position}/{g.aspect}{merge} "
            f"→ size={cg.size_class}, ctx={cg.brand_context}, "
            f"strats={cg.compatible_strategies}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from whitespace_analyzer import detect_gaps

    if len(sys.argv) < 2:
        print("Usage: python gap_classifier.py <screenshot.png>")
        sys.exit(1)

    path = sys.argv[1]
    gaps = detect_gaps(path)
    classified = classify_slide_gaps(gaps)
    print(format_classification_table(classified, slide_label=path))
    print()
    print("Reasoning per gap:")
    for i, cg in enumerate(classified, 1):
        print(f"  #{i}: {' / '.join(cg.reasoning)}")
