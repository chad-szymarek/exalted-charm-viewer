"""Resolve raw prerequisite text into a single navigable prerequisites field.

Each charm's raw prerequisite text (e.g. "Wise Arrow" or
"any 5 Lore Charms") is turned into a list of entries, each either a resolved
charm reference {name, charmId} or a free-text note {name, charmId: null}.
The reverse edges are written to each charm's `children` list in the same
{name, charmId} shape. Consecutive unresolvable tokens are kept together so
free-text clauses read naturally instead of fragmenting on their commas.
"""
import re

from charm_block_parsing import strip_trailing_parenthetical
from pdf_text_layout import normalize_whitespace, normalized_lookup_key


def make_charm_id_slug(text):
    slug = normalized_lookup_key(text)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _assign_charm_ids(charms):
    """Give every charm a unique id; return (charm_by_id, charm_id_by_name)."""
    charm_by_id = {}
    charm_id_by_name = {}
    for charm in charms:
        base_slug = make_charm_id_slug(charm["name"]) or "charm"
        charm_id = base_slug
        duplicate_counter = 2
        while charm_id in charm_by_id:
            charm_id = f"{base_slug}-{duplicate_counter}"
            duplicate_counter += 1
        charm_by_id[charm_id] = charm
        charm["id"] = charm_id
        charm_id_by_name.setdefault(normalized_lookup_key(charm["name"]), charm_id)
    return charm_by_id, charm_id_by_name


def _build_prerequisite_entries(raw_prerequisite_text, charm_id_by_name):
    """Turn raw prerequisite text into (entries, resolved_charm_ids).

    entries is a list of {name, charmId} — charmId is None for free text.
    """
    raw_prerequisite_text = normalize_whitespace(raw_prerequisite_text)
    if not raw_prerequisite_text or raw_prerequisite_text.lower() == "none":
        return [], []

    tokens = [token.strip() for token in raw_prerequisite_text.split(",")
              if token.strip()]
    entries = []
    resolved_charm_ids = []
    unresolved_run = []

    def flush_unresolved_run():
        if unresolved_run:
            entries.append({"name": ", ".join(unresolved_run), "charmId": None})
            unresolved_run.clear()

    for token in tokens:
        lookup_key = normalized_lookup_key(strip_trailing_parenthetical(token))
        charm_id = charm_id_by_name.get(lookup_key)
        if charm_id:
            flush_unresolved_run()
            entries.append({"name": token, "charmId": charm_id})
            resolved_charm_ids.append(charm_id)
        else:
            unresolved_run.append(token)
    flush_unresolved_run()
    return entries, resolved_charm_ids


def link_prerequisite_graph(charms):
    """Fill each charm's prerequisites/children lists from its raw prerequisite
    text. Returns (charm_name, free_text) pairs for references that did not
    resolve, for reporting.
    """
    charm_by_id, charm_id_by_name = _assign_charm_ids(charms)

    unresolved_references = []
    for charm in charms:
        entries, resolved_charm_ids = _build_prerequisite_entries(
            charm.pop("_prerequisites_raw"), charm_id_by_name)
        charm["prerequisites"] = entries

        for prerequisite_charm_id in resolved_charm_ids:
            if prerequisite_charm_id == charm["id"]:
                continue
            children_of_prerequisite = charm_by_id[prerequisite_charm_id]["children"]
            if not any(child["charmId"] == charm["id"]
                       for child in children_of_prerequisite):
                children_of_prerequisite.append(
                    {"name": charm["name"], "charmId": charm["id"]})

        for entry in entries:
            if entry["charmId"] is None:
                unresolved_references.append((charm["name"], entry["name"]))
    return unresolved_references
