#!/usr/bin/env python3
"""Parse Exalted 3e Core charms from the PDF into charms.json.

Scope: Chapter Six ability Charms + Chapter Seven Martial Arts style Charms.
Sorcery spells use a different stat format and are intentionally excluded.

Usage:
    python parse.py <pdf> [-o data/charms.json]

The parsing knowledge is split across focused modules:
    pdf_text_layout.py      page/block/span reading, column order, de-hyphenation
    category_discovery.py   charm categories + page range from the PDF outline
    charm_block_parsing.py  font-signature detection and stat-block extraction
    prerequisite_graph.py   id assignment and prerequisite/children resolution
"""
import argparse
import json
import sys
from collections import OrderedDict

import fitz  # PyMuPDF

from category_discovery import discover_charm_categories, discover_merit_section
from charm_block_parsing import (
    block_is_charm_header,
    block_is_description_body,
    extract_charm_name,
    parse_charm_stat_block,
    section_header_text,
)
from merit_parsing import block_is_merit_header, parse_merit_block
from pdf_text_layout import (
    blocks_in_reading_order,
    join_description_paragraphs,
    normalize_whitespace,
    normalized_lookup_key,
)
from prerequisite_graph import link_prerequisite_graph, make_charm_id_slug


def collect_charm_names(document, first_page_index, end_page_index):
    """First pass: gather every charm name so the main pass can tell a wrapped
    prerequisite name apart from the start of a description."""
    charm_names = set()
    for page_index in range(first_page_index, end_page_index):
        for block in blocks_in_reading_order(document[page_index]):
            if block_is_charm_header(block):
                charm_name = extract_charm_name(block)
                if charm_name:
                    charm_names.add(normalized_lookup_key(charm_name))
    return charm_names


def _match_category(category_display_names, header_text):
    """Match a section header against the known categories (full text or
    leading-substring in either direction, to tolerate outline/header drift)."""
    header_key = normalized_lookup_key(header_text)
    return next(
        (lookup_key for lookup_key in category_display_names
         if lookup_key == header_key
         or header_key.startswith(lookup_key)
         or lookup_key.startswith(header_key)),
        None)


def parse_charms_from_pdf(pdf_path):
    """Parse charms from a PDF on disk. Returns (charms, category_display_names)."""
    return parse_charms_from_document(fitz.open(pdf_path))


def parse_charms_from_bytes(pdf_bytes):
    """Parse charms from PDF bytes held in memory (nothing touches disk).

    Used by the web upload endpoint so an uploaded PDF is never stored."""
    return parse_charms_from_document(fitz.open(stream=pdf_bytes, filetype="pdf"))


def build_output(charms, category_display_names):
    """The JSON payload shape shared by the CLI and the web endpoint."""
    return {
        "categories": list(category_display_names.values()),
        "charms": charms,
    }


def parse_charms_from_document(document):
    category_display_names, first_page_index, end_page_index, \
        chapter_seven_start_index = discover_charm_categories(document)
    print(f"Charm region: pages {first_page_index + 1}..{end_page_index} "
          f"(physical). {len(category_display_names)} categories.",
          file=sys.stderr)

    known_charm_names = collect_charm_names(
        document, first_page_index, end_page_index)

    parsed_charms = []
    current_category_name = None
    charm_in_progress = None

    def finish_current_charm():
        nonlocal charm_in_progress
        if charm_in_progress is not None:
            charm_in_progress["description"] = join_description_paragraphs(
                charm_in_progress["_description_blocks"])
            del charm_in_progress["_description_blocks"]
            parsed_charms.append(charm_in_progress)
            charm_in_progress = None

    for page_index in range(first_page_index, end_page_index):
        page = document[page_index]
        for block in blocks_in_reading_order(page):
            header_text = section_header_text(block)
            if header_text is not None:
                matched_category_key = _match_category(
                    category_display_names, header_text)
                if matched_category_key:
                    finish_current_charm()
                    current_category_name = \
                        category_display_names[matched_category_key]
                elif page_index >= chapter_seven_start_index:
                    # A non-category section in Chapter Seven (chapter intros,
                    # Sorcerous Workings, Thaumaturgy): end the current category
                    # so its prose is not attributed to the previous charm.
                    finish_current_charm()
                    current_category_name = None
                continue  # header blocks never contribute to a description

            if current_category_name is None:
                continue

            if block_is_charm_header(block):
                finish_current_charm()
                charm_name, stat_fields, inline_description_lines = \
                    parse_charm_stat_block(block, known_charm_names)
                charm_in_progress = {
                    "id": "",
                    "name": charm_name,
                    "category": current_category_name,
                    "cost": stat_fields.get("cost", ""),
                    "mins": stat_fields.get("mins", ""),
                    "type": stat_fields.get("type", ""),
                    "keywords": [keyword.strip()
                                 for keyword in stat_fields.get("keywords", "").split(",")
                                 if keyword.strip()
                                 and keyword.strip().lower() != "none"],
                    "duration": stat_fields.get("duration", ""),
                    "rating": "",         # merits only; empty for charms
                    "prerequisites": [],  # filled by link_prerequisite_graph
                    "children": [],       # filled by link_prerequisite_graph
                    "description": "",
                    "page": page_index + 1,
                    "_prerequisites_raw": normalize_whitespace(
                        stat_fields.get("prerequisites_raw", "")),
                    "_description_blocks":
                        [inline_description_lines] if inline_description_lines else [],
                }
                continue

            # Any other prose/addendum block belongs to the open charm.
            if charm_in_progress is not None and block_is_description_body(block):
                charm_in_progress["_description_blocks"].append(block["lines"])

    finish_current_charm()

    unresolved_references = link_prerequisite_graph(parsed_charms)
    _report_unresolved_references(unresolved_references)

    # Merits live in their own section (Chapter Four) with a different format,
    # so they are parsed separately and appended with globally-unique ids.
    merits, merit_categories = parse_merits_from_document(document)
    used_ids = {charm["id"] for charm in parsed_charms}
    _assign_merit_ids(merits, used_ids)
    parsed_charms.extend(merits)
    category_display_names = OrderedDict(category_display_names)
    category_display_names.update(merit_categories)

    return parsed_charms, category_display_names


def _assign_merit_ids(merits, used_ids):
    for merit in merits:
        base_slug = make_charm_id_slug(merit["name"]) or "merit"
        merit_id = base_slug
        duplicate_counter = 2
        while merit_id in used_ids:
            merit_id = f"{base_slug}-{duplicate_counter}"
            duplicate_counter += 1
        used_ids.add(merit_id)
        merit["id"] = merit_id


def parse_merits_from_document(document):
    """Parse Merit entries. Returns (merits, merit_categories)."""
    merit_categories, start_page_index, end_page_index = \
        discover_merit_section(document)

    merits = []
    current_category_name = None
    merit_in_progress = None

    def finish_current_merit():
        nonlocal merit_in_progress
        if merit_in_progress is not None:
            merit_in_progress["description"] = join_description_paragraphs(
                merit_in_progress["_description_blocks"])
            del merit_in_progress["_description_blocks"]
            merits.append(merit_in_progress)
            merit_in_progress = None

    for page_index in range(start_page_index, end_page_index):
        for block in blocks_in_reading_order(document[page_index]):
            header_text = section_header_text(block)
            if header_text is not None:
                finish_current_merit()
                key = normalized_lookup_key(header_text)
                current_category_name = merit_categories.get(key)  # None for intro
                continue
            if current_category_name is None:
                continue
            if block_is_merit_header(block):
                finish_current_merit()
                name, rating, merit_type, inline_lines = parse_merit_block(block)
                merit_in_progress = {
                    "id": "",
                    "name": name,
                    "category": current_category_name,
                    "cost": "",
                    "mins": "",
                    "type": merit_type,
                    "keywords": [],
                    "duration": "",
                    "rating": rating,
                    "prerequisites": [],
                    "children": [],
                    "description": "",
                    "page": page_index + 1,
                    "_description_blocks": [inline_lines] if inline_lines else [],
                }
                continue
            if merit_in_progress is not None and block_is_description_body(block):
                merit_in_progress["_description_blocks"].append(block["lines"])

    finish_current_merit()
    return merits, merit_categories


def _report_unresolved_references(unresolved_references):
    if not unresolved_references:
        return
    print(f"\n{len(unresolved_references)} unresolved prerequisite "
          f"reference(s) (kept as raw text):", file=sys.stderr)
    for charm_name, prerequisite_text in unresolved_references[:40]:
        print(f"  {charm_name!r} -> {prerequisite_text!r}", file=sys.stderr)
    if len(unresolved_references) > 40:
        print(f"  ... and {len(unresolved_references) - 40} more",
              file=sys.stderr)


def _print_category_counts(charms, category_display_names):
    charm_count_by_category = OrderedDict(
        (display_name, 0) for display_name in category_display_names.values())
    for charm in charms:
        charm_count_by_category[charm["category"]] = \
            charm_count_by_category.get(charm["category"], 0) + 1
    print("\nCharms per category:", file=sys.stderr)
    for display_name, charm_count in charm_count_by_category.items():
        print(f"  {charm_count:4d}  {display_name}", file=sys.stderr)
    print(f"\nTOTAL: {len(charms)} charms", file=sys.stderr)


def main():
    argument_parser = argparse.ArgumentParser(
        description="Parse Exalted 3e charms to JSON.")
    argument_parser.add_argument("pdf")
    argument_parser.add_argument("-o", "--out", default="data/charms.json")
    arguments = argument_parser.parse_args()

    charms, category_display_names = parse_charms_from_pdf(arguments.pdf)
    _print_category_counts(charms, category_display_names)

    output = build_output(charms, category_display_names)
    with open(arguments.out, "w", encoding="utf-8") as output_file:
        json.dump(output, output_file, indent=2, ensure_ascii=False)
    print(f"Wrote {arguments.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
