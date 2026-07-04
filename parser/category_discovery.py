"""Discover charm categories and the charm page range from the PDF's outline.

The PDF's embedded table of contents is the authoritative source for which
ability/martial-arts-style sections exist and where the charm chapters begin
and end — this avoids hardcoding edition-specific page numbers.
"""
import sys
from collections import OrderedDict

from pdf_text_layout import normalize_whitespace


# Chapter Six level-3 outline entries that are NOT charm categories.
CHAPTER_SIX_NON_CATEGORY_SECTIONS = {
    "depicting charms",
    "using charms and charm limitations",
    "presentation format",
    "excellencies",
    "martial arts",  # stub in Chapter Six; real MA charms live in Chapter Seven
    "sorcery",       # stub in Chapter Six; sorcery spells are out of scope
}


def discover_charm_categories(document):
    """Return (category_display_names, first_page_index, end_page_index,
    chapter_seven_start_index).

    category_display_names is an ordered {lookup_key: display_name} mapping of
    Chapter Six ability categories plus Chapter Seven martial-arts styles.
    Page indexes are 0-based physical page numbers; end_page_index is exclusive
    (the start of the Chapter Seven Sorcery section).

    chapter_seven_start_index is where Chapter Seven begins. Crossing it resets
    the current category once, so the Martial Arts chapter intro is not
    attributed to the last Chapter Six charm. It is a page boundary (not a text
    match) precisely because section titles like "Sorcery" and "Martial Arts"
    recur in both chapters.
    """
    table_of_contents = document.get_toc(simple=True)

    chapter_six_start_page = None
    chapter_seven_start_page = None
    for level, title, page_number in table_of_contents:
        clean_title = normalize_whitespace(title)
        if clean_title == "Chapter Six: Charms":
            chapter_six_start_page = page_number
        elif clean_title == "Chapter Seven: Martial Arts and Sorcery":
            chapter_seven_start_page = page_number
    if chapter_six_start_page is None or chapter_seven_start_page is None:
        sys.exit("Could not locate Chapter Six / Seven in the PDF outline.")

    # lookup_key -> (display_name, first_page_index)
    categories = OrderedDict()
    sorcery_section_page_index = None
    for level, title, page_number in table_of_contents:
        display_name = normalize_whitespace(title)
        lookup_key = display_name.lower()
        in_chapter_six = chapter_six_start_page <= page_number < chapter_seven_start_page
        in_chapter_seven = page_number >= chapter_seven_start_page

        # Chapter Six ability categories are the level-3 outline entries.
        if (in_chapter_six and level == 3
                and lookup_key not in CHAPTER_SIX_NON_CATEGORY_SECTIONS):
            categories.setdefault(lookup_key, (display_name, page_number - 1))
        # Chapter Seven martial-arts styles are level-4 "... Style" entries.
        if in_chapter_seven and level == 4 and display_name.endswith("Style"):
            categories.setdefault(lookup_key, (display_name, page_number - 1))
        # Chapter Seven's Sorcery section marks the end of in-scope content.
        if in_chapter_seven and level == 3 and lookup_key == "sorcery":
            sorcery_section_page_index = page_number - 1

    first_page_index = min(page_index for _, page_index in categories.values())
    end_page_index = (sorcery_section_page_index
                      if sorcery_section_page_index is not None
                      else document.page_count)

    category_display_names = OrderedDict(
        (lookup_key, display_name)
        for lookup_key, (display_name, _) in categories.items())
    return (category_display_names, first_page_index, end_page_index,
            chapter_seven_start_page - 1)
