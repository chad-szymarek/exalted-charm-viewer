"""Low-level helpers for reading text out of the PDF's two-column page layout.

Nothing in this module knows what a "charm" is — it only understands PyMuPDF's
page -> block -> line -> span structure and how to turn it back into clean prose
(reading order, soft-hyphen rejoining, whitespace normalization).
"""
import re

SOFT_HYPHEN = "­"


def normalize_whitespace(text):
    """Collapse runs of whitespace and strip soft hyphens, for display text."""
    return re.sub(r"\s+", " ", text.replace(SOFT_HYPHEN, "")).strip()


def normalized_lookup_key(text):
    """Case-insensitive, whitespace-normalized key for name comparisons."""
    return normalize_whitespace(text).lower()


def blocks_in_reading_order(page):
    """Text blocks in two-column reading order: left column top-to-bottom,
    then right column top-to-bottom."""
    column_split_x = page.rect.width / 2
    text_blocks = [block for block in page.get_text("dict")["blocks"]
                   if "lines" in block]
    left_column = sorted((block for block in text_blocks
                          if block["bbox"][0] < column_split_x),
                         key=lambda block: block["bbox"][1])
    right_column = sorted((block for block in text_blocks
                           if block["bbox"][0] >= column_split_x),
                          key=lambda block: block["bbox"][1])
    return left_column + right_column


def spans_in_block(block):
    for line in block["lines"]:
        for span in line["spans"]:
            yield span


def first_nonempty_span(block):
    for span in spans_in_block(block):
        if span["text"].strip():
            return span
    return None


def _paragraph_text(lines):
    """Join a block's lines into one clean paragraph, rejoining words split
    across lines by a soft hyphen. Returns (text, ends_with_soft_hyphen); the
    flag lets the caller rejoin a word split across a column/page break.
    """
    joined_text = ""
    for line in lines:
        line_text = "".join(span["text"] for span in line["spans"])
        if not joined_text:
            joined_text = line_text
        elif joined_text.rstrip().endswith(SOFT_HYPHEN):
            joined_text = joined_text.rstrip()[:-1] + line_text.lstrip()
        else:
            joined_text = joined_text + " " + line_text
    ends_with_soft_hyphen = joined_text.rstrip().endswith(SOFT_HYPHEN)
    clean_text = re.sub(r"\s+", " ", joined_text.replace(SOFT_HYPHEN, "")).strip()
    return clean_text, ends_with_soft_hyphen


def join_description_paragraphs(paragraph_line_lists):
    """Assemble a charm description from its blocks, keeping true paragraph
    breaks but healing the false ones the two-column layout introduces.

    Each block is normally its own paragraph, but a paragraph that flows across
    a column or page break is split into two blocks. Two signals reveal such a
    continuation: the previous block ended a word with a soft hyphen (rejoin the
    word), or the next block starts with a lowercase letter (the sentence
    continues — real paragraphs start with a capital or a bullet).
    """
    description = ""
    previous_block_split_a_word = False
    for lines in paragraph_line_lists:
        paragraph_text, ends_with_soft_hyphen = _paragraph_text(lines)
        if not paragraph_text:
            continue
        if not description:
            description = paragraph_text
        elif previous_block_split_a_word:
            description += paragraph_text
        elif paragraph_text[:1].islower():
            description += " " + paragraph_text
        else:
            description += "\n\n" + paragraph_text
        previous_block_split_a_word = ends_with_soft_hyphen
    return description
