"""
strategies/none.py — W3.4

Explicit no-op strategy. Returns empty string for gaps that should not
be decorated (xs gaps, full slides, hero/cover slides).
"""
from __future__ import annotations
from gap_classifier import ClassifiedGap


def generate(cg: ClassifiedGap,
             slide_meta: dict = None,
             slide_size: tuple[int, int] = (2560, 1440)) -> str:
    return ''
