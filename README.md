# Exalted 3e Charm Viewer

A local tool to browse, search, filter, select, and export Exalted 3rd Edition
charms parsed from the core rulebook PDF.

> **Copyright:** Exalted 3e text is © Onyx Path Publishing. This tool is for
> personal use of a rulebook you own. The PDF and generated `charms.json` are
> git-ignored — do not commit or publicly host the extracted text.


Charm detail views are deep-linkable: `http://localhost:8000/web/#wise-arrow`.

## Setup
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r parser/requirements.txt
```

## Parse the PDF
```bash
. .venv/bin/activate
python3 parser/parse.py "source/Exalted 3e Core.pdf" -o data/charms.json
```
Prints per-category charm counts and any unresolved prerequisite references
(free-text prereqs like "any 5 Lore Charms" cannot resolve to a single charm and
are kept as raw text — this is expected).

## View
```bash
python3 -m http.server 8000
# open http://localhost:8000/web/
```
Serving over http avoids the `file://` fetch restriction on `charms.json`.

## Scope & notes
- Covers **Chapter Six** ability Charms and **Chapter Seven** Martial Arts style
  Charms (~875 charms). **Sorcery spells are excluded** — they use a different
  stat format.
- Prerequisites are resolved into a navigable graph. Both `prerequisites` and
  `children` are lists of `{name, charmId}` entries — `charmId` is a real
  charm's id (clickable) or `null` for free text like "any 5 Lore Charms".

## Charm JSON schema
```json
{
  "id": "wise-arrow",
  "name": "Wise Arrow",
  "category": "Archery",
  "cost": "1m",
  "mins": "Archery 2, Essence 1",
  "type": "Supplemental",
  "keywords": ["Uniform"],
  "duration": "Instant",
  "prerequisites": [],
  "children": [
    {"name": "Sight Without Eyes", "charmId": "sight-without-eyes"},
    {"name": "Trance of Unhesitating Speed", "charmId": "trance-of-unhesitating-speed"}
  ],
  "description": "...",
  "page": 256
}
```
