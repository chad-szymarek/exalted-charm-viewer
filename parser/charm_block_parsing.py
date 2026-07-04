"""Recognize and parse individual charm blocks by their font signatures.

Calibrated against "Exalted 3e Core.pdf":
  - Ability / MA-style section header: font Envision-Roman, size ~11.
  - Charm name:                        font MercuryTextG2-Semibold, size ~9.5.
  - Stat labels (Cost:, Mins:, ...):   font MercuryTextG2-Bold.
  - Body text / stat values:           font MercuryTextG2-Roman.

A charm's name and full stat block occupy a single PDF block; its description
is usually the block(s) that follow. On some pages the description shares the
stat block's own block, and the prerequisite value can wrap across lines. To
tell a wrapped prerequisite name apart from the start of the description, the
parser is given the set of all charm names up front (see parse.py's first pass).
"""
import re

from pdf_text_layout import (
    SOFT_HYPHEN,
    first_nonempty_span,
    normalize_whitespace,
    spans_in_block,
)

SECTION_HEADER_FONT = "Envision-Roman"
CHARM_NAME_FONT = "MercuryTextG2-Semibold"
STAT_LABEL_FONT = "MercuryTextG2-Bold"
BODY_TEXT_FONT = "MercuryTextG2-Roman"

# Stat labels as printed in the book, mapped to the JSON field they fill.
STAT_LABEL_TO_FIELD_KEY = {
    "Cost": "cost",
    "Mins": "mins",
    "Type": "type",
    "Keywords": "keywords",
    "Duration": "duration",
    "Prerequisite Charms": "prerequisites_raw",
}

_TRAILING_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")


def strip_trailing_parenthetical(text):
    """Remove a trailing note like ' (x2)' from a charm name for matching."""
    return _TRAILING_PARENTHETICAL.sub("", text).strip()


def _stat_label_of_span(span):
    """The stat label a span carries ('Cost', 'Mins', ...), or None."""
    if span["font"] != STAT_LABEL_FONT:
        return None
    label_text = span["text"].strip().rstrip(":").strip()
    return label_text if label_text in STAT_LABEL_TO_FIELD_KEY else None


def _join_across_line_break(existing_text, continued_text):
    """Append text from the next line, rejoining hyphenated words and adding a
    space where the previous line ended a whole word."""
    if not existing_text:
        return continued_text
    trimmed = existing_text.rstrip()
    if trimmed.endswith(SOFT_HYPHEN):
        return trimmed[:-1] + continued_text.lstrip()
    if trimmed.endswith("-"):
        return trimmed + continued_text.lstrip()
    return existing_text + " " + continued_text.lstrip()


def section_header_text(block):
    """The section title if this block is an ability/style header, else None.

    Section headers use the display font at ~11pt; page numbers use the same
    font at 12pt but are purely numeric, so they are excluded.
    """
    leading_span = first_nonempty_span(block)
    if not leading_span:
        return None
    if leading_span["font"] == SECTION_HEADER_FONT and 10.0 <= leading_span["size"] <= 11.9:
        header_text = normalize_whitespace(
            "".join(span["text"] for span in spans_in_block(block)
                    if span["font"] == SECTION_HEADER_FONT))
        if header_text and not header_text.isdigit():
            return header_text
    return None


def block_is_charm_header(block):
    """True if the block starts with a charm name and contains a Cost label."""
    leading_span = first_nonempty_span(block)
    if not leading_span or leading_span["font"] != CHARM_NAME_FONT:
        return False
    return any(span["font"] == STAT_LABEL_FONT
               and span["text"].strip().rstrip(":").strip() == "Cost"
               for span in spans_in_block(block))


# A charm's prose can start with body text, an italic lead-in word, or a bold
# in-line label like "Mastery:", "Terrestrial:", or "Special activation rules:"
# (all real charm addenda). Charm-name Semibold, section-header Envision, and
# footer DINAlternate fonts are deliberately excluded.
DESCRIPTION_BODY_FONTS = (BODY_TEXT_FONT, STAT_LABEL_FONT, "MercuryTextG2-Italic")


def block_is_description_body(block):
    leading_span = first_nonempty_span(block)
    return leading_span is not None and leading_span["font"] in DESCRIPTION_BODY_FONTS


def extract_charm_name(block):
    """The charm name (the leading name spans before the first stat label)."""
    name_parts = []
    for span in spans_in_block(block):
        if _stat_label_of_span(span) is not None:
            break
        if span["font"] == CHARM_NAME_FONT:
            name_parts.append(span["text"])
    return normalize_whitespace("".join(name_parts))


def _line_contains_stat_label(line):
    return any(_stat_label_of_span(span) for span in line["spans"])


def _line_continues_prerequisites(prerequisite_text_so_far, line, known_charm_names):
    """True if a label-less line still belongs to the prerequisite value rather
    than starting the description.

    The test: append the line, and check whether the last comma-separated token
    is (the start of) a real charm name. A wrapped prerequisite name completes a
    known name; a description sentence does not.
    """
    line_text = "".join(span["text"] for span in line["spans"])
    combined_text = normalize_whitespace(
        _join_across_line_break(prerequisite_text_so_far, line_text))
    last_token = strip_trailing_parenthetical(
        combined_text.split(",")[-1].strip().lower())
    if not last_token:
        return False
    return any(charm_name == last_token or charm_name.startswith(last_token + " ")
               for charm_name in known_charm_names)


def parse_charm_stat_block(block, known_charm_names):
    """Extract (charm_name, stat_fields, inline_description_lines) from a charm
    header block.

    known_charm_names is the set of normalized charm names, used to keep a
    wrapped prerequisite name from being mistaken for the description.
    inline_description_lines are the raw description line dicts found inside the
    stat block itself (non-empty only when the stat block and its prose share a
    single PDF block); they are joined with the following blocks downstream.
    """
    name_parts = []
    stat_fields = {}
    active_field_key = None
    description_lines = []
    stat_block_finished = False

    for line in block["lines"]:
        if stat_block_finished:
            description_lines.append(line)
            continue
        # After the prerequisite value (the last stat field), a label-less line
        # that does not continue a charm name begins the description.
        if (active_field_key == "prerequisites_raw"
                and not _line_contains_stat_label(line)):
            if not _line_continues_prerequisites(
                    stat_fields.get("prerequisites_raw", ""), line,
                    known_charm_names):
                stat_block_finished = True
                description_lines.append(line)
                continue

        is_first_span_on_line = True
        for span in line["spans"]:
            span_label = _stat_label_of_span(span)
            if span_label is not None:
                active_field_key = STAT_LABEL_TO_FIELD_KEY[span_label]
                stat_fields.setdefault(active_field_key, "")
                is_first_span_on_line = False
                continue
            if active_field_key is None:
                if span["font"] == CHARM_NAME_FONT:
                    name_parts.append(span["text"])
            elif is_first_span_on_line and stat_fields[active_field_key]:
                # Continuing a stat value onto a new line: rejoin properly.
                stat_fields[active_field_key] = _join_across_line_break(
                    stat_fields[active_field_key], span["text"])
            else:
                stat_fields[active_field_key] += span["text"]
            is_first_span_on_line = False

    charm_name = normalize_whitespace("".join(name_parts))
    for field_key in list(stat_fields):
        stat_fields[field_key] = normalize_whitespace(stat_fields[field_key])
    if "cost" in stat_fields:
        stat_fields["cost"] = stat_fields["cost"].rstrip(" ;")
    return charm_name, stat_fields, description_lines
