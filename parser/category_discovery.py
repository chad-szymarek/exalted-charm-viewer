"""Discover charm categories and the charm page range from the PDF's outline.

The PDF's embedded table of contents is the authoritative source for which
ability/martial-arts-style sections exist and where the charm chapters begin
and end — this avoids hardcoding edition-specific page numbers.
"""
import sys
from collections import OrderedDict

from charm_block_parsing import section_header_text
from pdf_text_layout import blocks_in_reading_order, normalize_whitespace


# Chapter Six level-3 outline entries that are NOT charm categories.
CHAPTER_SIX_NON_CATEGORY_SECTIONS = {
    "depicting charms",
    "using charms and charm limitations",
    "presentation format",
    "excellencies",
    "martial arts",  # stub in Chapter Six; real MA charms live in Chapter Seven
    "sorcery",       # stub in Chapter Six; sorcery spells are out of scope
}


def discover_merit_section(document):
    """Return (merit_categories, start_page_index, end_page_index) for Merits.

    merit_categories is an ordered {lookup_key: display_name} of the merit
    sub-sections ("Standard Merits", "Supernatural Merits"), discovered from the
    page headers. The region runs from the "Merits" section to "Flaws" (both from
    the outline).
    """
    table_of_contents = document.get_toc(simple=True)
    merits_page = flaws_page = None
    for level, title, page_number in table_of_contents:
        clean_title = normalize_whitespace(title)
        if clean_title == "Merits" and merits_page is None:
            merits_page = page_number
        elif clean_title == "Flaws" and flaws_page is None:
            flaws_page = page_number
    if merits_page is None or flaws_page is None:
        sys.exit("Could not locate the Merits / Flaws sections in the outline.")

    start_page_index = merits_page - 1
    end_page_index = flaws_page - 1

    merit_categories = OrderedDict()
    for page_index in range(start_page_index, end_page_index):
        for block in blocks_in_reading_order(document[page_index]):
            header_text = section_header_text(block)
            # "Standard Merits" / "Supernatural Merits" — but not the "Merits"
            # intro header itself.
            if header_text and header_text.endswith(" Merits"):
                merit_categories.setdefault(header_text.lower(), header_text)
    return merit_categories, start_page_index, end_page_index


def discover_charm_categories(document):
    """Return (category_display_names, first_page_index, end_page_index,
    chapter_seven_start_index).

    category_display_names is an ordered {lookup_key: display_name} mapping of
    Chapter Six ability categories, Chapter Seven martial-arts styles, and the
    three sorcery "... Circle Spells" sections. Page indexes are 0-based physical
    page numbers; end_page_index is exclusive (the start of Chapter Eight).

    chapter_seven_start_index is where Chapter Seven begins. From there on, any
    section header that is NOT a category (chapter intros, Sorcerous Workings,
    Thaumaturgy) resets the current category so its prose is not attributed to
    the previous section's last charm. The reset is gated by page index (not a
    text match) because section titles like "Sorcery" and "Martial Arts" recur
    in Chapter Six among real charms and must not reset there.
    """
    table_of_contents = document.get_toc(simple=True)

    chapter_six_start_page = None
    chapter_seven_start_page = None
    chapter_eight_start_page = None
    for level, title, page_number in table_of_contents:
        clean_title = normalize_whitespace(title)
        if clean_title == "Chapter Six: Charms":
            chapter_six_start_page = page_number
        elif clean_title == "Chapter Seven: Martial Arts and Sorcery":
            chapter_seven_start_page = page_number
        elif clean_title == "Chapter Eight: Antagonists":
            chapter_eight_start_page = page_number
    if (chapter_six_start_page is None or chapter_seven_start_page is None
            or chapter_eight_start_page is None):
        sys.exit("Could not locate Chapter Six/Seven/Eight in the PDF outline.")

    # lookup_key -> (display_name, first_page_index)
    categories = OrderedDict()
    for level, title, page_number in table_of_contents:
        display_name = normalize_whitespace(title)
        lookup_key = display_name.lower()
        in_chapter_six = chapter_six_start_page <= page_number < chapter_seven_start_page
        in_chapter_seven = chapter_seven_start_page <= page_number < chapter_eight_start_page

        # Chapter Six ability categories are the level-3 outline entries.
        if (in_chapter_six and level == 3
                and lookup_key not in CHAPTER_SIX_NON_CATEGORY_SECTIONS):
            categories.setdefault(lookup_key, (display_name, page_number - 1))

    # Chapter Seven categories (martial-arts styles and sorcery spell circles)
    # are discovered from the page headers, not the outline: the book's TOC omits
    # at least one real style ("Dreaming Pearl Courtesan Style").
    for page_index in range(chapter_seven_start_page - 1,
                            chapter_eight_start_page - 1):
        for block in blocks_in_reading_order(document[page_index]):
            header_text = section_header_text(block)
            if header_text and (header_text.endswith("Style")
                                or header_text.endswith("Circle Spells")):
                categories.setdefault(header_text.lower(),
                                      (header_text, page_index))

    first_page_index = min(page_index for _, page_index in categories.values())
    # The charm/spell region runs to the start of Chapter Eight. Non-category
    # sections within it (chapter intros, Sorcerous Workings, Thaumaturgy) reset
    # the category during parsing, so their prose is not collected.
    end_page_index = chapter_eight_start_page - 1

    category_display_names = OrderedDict(
        (lookup_key, display_name)
        for lookup_key, (display_name, _) in categories.items())
    return (category_display_names, first_page_index, end_page_index,
            chapter_seven_start_page - 1)
