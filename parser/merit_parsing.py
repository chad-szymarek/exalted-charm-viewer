"""Detect and parse Merit entries.

Merits use a different header format from Charms: a single Semibold line of the
form "Name (dot-rating)—Type", e.g. "Allies (•, •••, or •••••)—Story", with no
Cost/Mins/etc. stat block. Type is one of Story, Innate, or Purchased. The
description (including italic sub-labels like "Drawback:") follows in body text.
"""
import re

from charm_block_parsing import CHARM_NAME_FONT
from pdf_text_layout import first_nonempty_span, normalize_whitespace

# Name (rating)—Type. The dash in the book is an em dash; accept a few variants.
MERIT_HEADER_RE = re.compile(
    r"^(?P<name>.+?)\s*\((?P<rating>[^)]*)\)\s*[—–-]\s*"
    r"(?P<type>Story|Innate|Purchased)$")


def _header_line_text(block):
    """Text of the block's first line (where a merit's name/rating/type sit)."""
    if not block["lines"]:
        return ""
    return normalize_whitespace(
        "".join(span["text"] for span in block["lines"][0]["spans"]))


def block_is_merit_header(block):
    leading_span = first_nonempty_span(block)
    if not leading_span or leading_span["font"] != CHARM_NAME_FONT:
        return False
    return MERIT_HEADER_RE.match(_header_line_text(block)) is not None


def parse_merit_block(block):
    """Return (name, rating, merit_type, inline_description_lines).

    inline_description_lines are the block's lines after the header line (when
    the description shares the header's block); the rest is collected downstream.
    """
    match = MERIT_HEADER_RE.match(_header_line_text(block))
    name = normalize_whitespace(match.group("name"))
    rating = normalize_whitespace(match.group("rating"))
    merit_type = match.group("type")
    inline_description_lines = block["lines"][1:]
    return name, rating, merit_type, inline_description_lines
