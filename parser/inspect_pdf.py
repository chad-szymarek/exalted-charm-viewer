#!/usr/bin/env python3
"""Calibration tool for the charm parser.

This is a *development* aid, not part of the build. Use it to discover the font
signatures the real PDF uses for ability section headers vs. individual charm
headers vs. body text, so the parser's heuristics can be tuned to this edition.

Usage:
    python inspect_pdf.py <pdf> fonts <page> [<page> ...]   # dump spans w/ font info
    python inspect_pdf.py <pdf> find "text"                 # find pages containing text
    python inspect_pdf.py <pdf> outline                     # dump the PDF bookmarks/TOC
    python inspect_pdf.py <pdf> sizes <start> <end>         # histogram of font sizes
"""
import sys
from collections import Counter

import fitz  # PyMuPDF

BOLD_FLAG_BIT = 2 ** 4
ITALIC_FLAG_BIT = 2 ** 1


def spans_on_page(page):
    page_dict = page.get_text("dict")
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                yield span


def dump_fonts(document, page_indexes):
    for page_index in page_indexes:
        page = document[page_index]
        print(f"\n===== PAGE {page_index} (0-indexed; "
              f"label {page.get_label() or '?'}) =====")
        for span in spans_on_page(page):
            span_text = span["text"].strip()
            if not span_text:
                continue
            bold_marker = "B" if span["flags"] & BOLD_FLAG_BIT else " "
            italic_marker = "I" if span["flags"] & ITALIC_FLAG_BIT else " "
            print(f"  size={span['size']:5.1f} {bold_marker}{italic_marker} "
                  f"font={span['font']:<28} | {span_text[:80]}")


def find_pages_containing(document, search_text):
    search_text_lower = search_text.lower()
    matching_page_indexes = [
        page_index for page_index in range(document.page_count)
        if search_text_lower in document[page_index].get_text().lower()]
    print(f"'{search_text}' found on {len(matching_page_indexes)} page(s) "
          f"(0-indexed): {matching_page_indexes}")


def dump_outline(document):
    table_of_contents = document.get_toc(simple=True)
    if not table_of_contents:
        print("(no embedded outline/TOC)")
        return
    for level, title, page_number in table_of_contents:
        print(f"{'  ' * (level - 1)}{title}  -> p{page_number}")


def dump_font_size_histogram(document, start_page_index, end_page_index):
    size_counts = Counter()
    font_counts = Counter()
    for page_index in range(start_page_index,
                            min(end_page_index, document.page_count)):
        for span in spans_on_page(document[page_index]):
            if span["text"].strip():
                size_counts[round(span["size"], 1)] += 1
                font_counts[span["font"]] += 1
    print("Font sizes (size: span_count), most common first:")
    for font_size, span_count in size_counts.most_common():
        print(f"  {font_size:5.1f}: {span_count}")
    print("\nFonts:")
    for font_name, span_count in font_counts.most_common():
        print(f"  {span_count:6d}  {font_name}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pdf_path, command = sys.argv[1], sys.argv[2]
    document = fitz.open(pdf_path)
    if command == "fonts":
        dump_fonts(document, [int(arg) for arg in sys.argv[3:]])
    elif command == "find":
        find_pages_containing(document, sys.argv[3])
    elif command == "outline":
        dump_outline(document)
    elif command == "sizes":
        dump_font_size_histogram(document, int(sys.argv[3]), int(sys.argv[4]))
    else:
        print(f"unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
