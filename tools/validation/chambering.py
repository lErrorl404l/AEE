#!/usr/bin/env python3
"""Chambering identity: one canonical key for one cartridge.

Five generators grew their own normaliser and their own alias table, and
they disagreed. The same weapon resolved in one generator and failed in
another, which is why 353 weapon records carried no cartridge_id even
though the chambering was written on them in words.

This module is the single source. It reduces a chambering designation to
a canonical key, and every generator joins on that key.

Canonical form, in order:

  1. Fold the Unicode multiplication signs to ASCII x.
  2. NFKC normalise, then lowercase.
  3. Read a comma between two digits as a decimal point. This turns the
     continental "6,5 x 55" into "6.5 x 55". Every other comma is left,
     because it separates list items.
  4. Drop the unit and the rim marker: "mm" and a following "R" when they
     sit directly after a digit. "7.62x54mmR" and "7,62 x 54 R" and
     "7_62_x_54_r" all reduce to the same key.
  5. Fold the long word "magnum" to "mag". Only that word. No other
     collapse, because "222 Rem. Mag." must not become "222 Rem.".
  6. Drop everything that is not a letter, a digit, the x separator or a
     ratio slash.

A designation can carry alternatives. "6.8x51mm (277 Fury) / 7.62x51mm
NATO" names three things. The `keys` function emits one key per
alternative: the whole string with parentheticals removed, each
parenthetical group, and each item of a whitespace-flanked slash list. A
ratio such as "450/400" is one designation, not a list, so a slash splits
only when whitespace flanks it.

Resolution returns every cartridge_id a key reaches. Zero is unresolved,
one is resolved, and more than one is a COLLISION: two register records
claim the same key. A collision is reported by the caller and never
guessed, which is the same rule the twist data follows.
"""

import json
import re
import unicodedata
from pathlib import Path

ALIASES_PATH = (
    Path(__file__).parents[2]
    / "data"
    / "ballistics"
    / "sources"
    / "chambering_aliases.json"
)

_MULTIPLICATION_SIGNS = ("\u00d7", "\u2715", "\u2a2f")
_DECIMAL_COMMA = re.compile(r"(?<=\d),(?=\d)")
_MAGNUM = re.compile(r"\bmagnum\b")
_UNIT = re.compile(r"(?<=[0-9])mm")
_STRIP = re.compile(r"[^a-z0-9x/]+")
_PARENTHETICAL = re.compile(r"\(([^)]*)\)")
_ALT_SPLIT = re.compile(r"\s/\s")


def canonical(text):
    """The canonical key for one chambering designation.

    The separators go first, so a register id such as "7_62_x_54_r" and
    the text "7.62x54mmR" reduce to the same shape. The unit is then read
    off, and a rim marker stays in the key, because 7x57 and 7x57R are
    different cartridges. The unit is matched only after a digit, so the
    "mm" inside the word "Remington" is not touched.
    """
    if not text:
        return ""
    s = text
    for sign in _MULTIPLICATION_SIGNS:
        s = s.replace(sign, "x")
    s = unicodedata.normalize("NFKC", s).lower()
    s = _DECIMAL_COMMA.sub(".", s)
    s = _MAGNUM.sub("mag", s)
    s = _STRIP.sub("", s)
    return _UNIT.sub("", s)


def keys(text):
    """Every canonical key a designation reaches.

    A designation that names alternatives reaches more than one key. The
    caller resolves each in turn and takes the union of the hits.
    """
    out = set()
    if not text:
        return out
    candidates = [text, _PARENTHETICAL.sub(" ", text)]
    candidates.extend(_PARENTHETICAL.findall(text))
    if _ALT_SPLIT.search(text):
        candidates.extend(_ALT_SPLIT.split(text))
    for candidate in candidates:
        key = canonical(candidate)
        if key:
            out.add(key)
    return out


def load_aliases(path=ALIASES_PATH):
    """The curated alias table, keyed on the canonical key.

    Keyed on the canonical key and not on the raw text, so a register
    that renames a record does not break the alias. Every alias carries
    the source that states the equivalence, because an alias is an
    identity claim.
    """
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["key"]: row for row in data.get("aliases", [])}


def build_index(cartridges):
    """Every canonical key to the cartridge_ids that claim it."""
    index = {}
    for record in cartridges:
        cid = record["cartridge_id"]
        for name in [cid] + list(record.get("names", [])):
            for key in keys(name):
                index.setdefault(key, set()).add(cid)
    return index


def resolve(text, index, aliases=None):
    """Resolve a chambering designation.

    Returns (cartridge_id, candidates). A resolved chambering returns its
    id and a single-element list. An unresolved one returns an empty
    string and an empty list. A collision returns an empty string and
    every candidate, so the caller reports it rather than guessing.
    """
    aliases = aliases or {}
    hits = set()
    for key in keys(text):
        hits.update(index.get(key, ()))
        alias = aliases.get(key)
        if alias:
            hits.add(alias["cartridge_id"])
    if len(hits) == 1:
        return hits.pop(), []
    if not hits:
        return "", []
    return "", sorted(hits)
