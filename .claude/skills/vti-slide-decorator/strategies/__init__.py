"""Strategy generators for vti-slide-decorator (W3.4)."""
from . import typographic, abstract_geometric, topical_motif, none

# Registry: strategy_name → generate(classified_gap, slide_meta, slide_size) → html
STRATEGIES = {
    'typographic':        typographic.generate,
    'abstract_geometric': abstract_geometric.generate,
    'topical_motif':      topical_motif.generate,
    'none':               none.generate,
}


def generate(strategy: str, classified_gap, slide_meta=None,
             slide_size=(2560, 1440)) -> str:
    """Dispatch to the right strategy generator. Returns HTML string."""
    fn = STRATEGIES.get(strategy)
    if fn is None:
        raise ValueError(f"Unknown strategy: {strategy!r}. "
                         f"Available: {sorted(STRATEGIES)}")
    return fn(classified_gap, slide_meta, slide_size)
