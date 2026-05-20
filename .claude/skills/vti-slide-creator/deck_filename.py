"""VTI deck filename convention.

Formula:

    VTI{-Customer}_Title-Slug_vX.Y.ext

Both `-Customer` and the version segment are mandatory in the formula;
`customer=None` simply collapses the optional segment. Title and
customer get slugified to ASCII (Vietnamese diacritics stripped) so
the filename is portable across Windows/macOS/email.

Examples:

    >>> deck_filename("Day-to-Day Info Summarization Agent")
    'VTI_Day-to-Day-Info-Summarization-Agent_v1.0.html'

    >>> deck_filename("Cloud Modernization", customer="LG Magna", version="2.1")
    'VTI-LG-Magna_Cloud-Modernization_v2.1.html'

    >>> deck_filename("Báo cáo nội bộ", customer="Khách hàng A", ext="pptx")
    'VTI-Khach-hang-A_Bao-cao-noi-bo_v1.0.pptx'
"""

from __future__ import annotations

import unicodedata


def _slug(text: str) -> str:
    """Slugify a string to ASCII letters/digits/hyphens.

    - Decomposes Unicode and drops combining marks (Vietnamese diacritics
      collapse: ả→a, ô→o, đ keeps its base 'd').
    - Treats every non-alphanumeric ASCII char (except hyphen) as a
      separator that collapses to a single hyphen.
    - Preserves the original case of letters.
    """
    if not text:
        return ""

    # Vietnamese 'đ' / 'Đ' don't decompose to ASCII via NFD; handle directly.
    text = text.replace("đ", "d").replace("Đ", "D")

    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

    out: list[str] = []
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch == "-"):
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    slug = "".join(out).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug


def deck_filename(
    title: str,
    customer: str | None = None,
    version: str = "1.0",
    ext: str = "html",
) -> str:
    """Build a VTI deliverable filename per the convention.

    Args:
        title: Deck title — slugified for the middle segment.
        customer: Optional customer name. When provided, inserted as
            `-CustomerSlug` directly after `VTI`. When None/empty,
            omitted entirely.
        version: Version string, e.g. `"1.0"`, `"2.1"`. Goes into
            the `_vX.Y` suffix verbatim (no extra parsing).
        ext: File extension (without the dot). Default `"html"`.

    Returns:
        The filename string (no directory).
    """
    title_slug = _slug(title) or "Deck"
    customer_seg = ""
    if customer and customer.strip():
        customer_seg = "-" + (_slug(customer) or "Customer")
    return f"VTI{customer_seg}_{title_slug}_v{version}.{ext.lstrip('.')}"
