#!/usr/bin/env python3
"""Identity designations: how a matcher recognises a real thing from text.

Every AEE matcher resolves a game class - vanilla, modded or one nobody has
written yet - to a real-world catalogue entry using only the text the class
carries: its classname, its displayName and its localised stringtable text.
For that to work WITHOUT a per-mod class list, each catalogue entry has to
advertise every designation the real thing is published under.

This module derives those designations generically, from the entry's own
PUBLISHED identity. No mod is named anywhere, so a class from a mod that
does not exist yet matches on the same rules as a vanilla one.

Three forms are emitted, each matching a way a designation is written:

  whole      the folded identity string
             "M1A2 SEP v2"   -> m1a2sepv2
  type       every word carrying a digit, which is how a type number is
             written, including the stem of a suffixed one
             "BTR-70" -> btr70;  "T-72BA" -> t72ba, t72
  marque     every adjacent word pair, which is how a two-word marque is
             written
             "Land Rover" -> landrover

A CATEGORY word is never a designation. "Transport", "tracked" or "rifle"
name a kind, not a thing: as a designation one would match a large part of
the catalogue and make every query ambiguous, so the matcher would return
nothing at all. The category list is deliberately small and holds only
words that are categories in EVERY domain this module serves.

The caller decides which layer receives these. The convention across the
AEE matchers is that the curated aliases stay on the equality layer, so one
curated alias names one entry, and the derived designations go on the
substring layer, which is the one that reads an unknown classname.
"""

from __future__ import annotations

import re

# Words that name a kind, not a thing. Never a designation.
CATEGORY_WORDS = frozenset(
    {
        # ground vehicles
        "transport", "cargo", "truck", "tank", "car", "apc", "ifv", "mbt",
        "suv", "van", "offroad", "armoured", "armored", "vehicle", "utility",
        "recovery", "carrier", "sedan", "coupe", "hatchback", "tracked",
        "wheeled", "howitzer", "artillery", "selfpropelledartillery",
        # aircraft
        "aircraft", "helicopter", "plane", "jet", "fighter", "bomber",
        "transporthelicopter", "attackhelicopter", "rotary", "fixedwing",
        "drone", "uav",
        # weapons and optics
        "rifle", "carbine", "pistol", "revolver", "shotgun", "launcher",
        "machinegun", "submachinegun", "sniper", "marksman", "weapon",
        "optic", "scope", "sight", "goggles", "binocular", "nightvision",
        "thermal", "magazine", "round", "ammo", "ammunition", "cartridge",
        # generic qualifiers
        "base", "variant", "standard", "model", "type", "mark",
        "black", "green", "tan", "desert", "woodland", "winter", "camo",
    }
)


def fold(text: str) -> str:
    """Fold any text to its lookup key: ASCII letters and digits, lowered."""
    return "".join(ch for ch in text.lower() if ch.isascii() and ch.isalnum())


def _type_stems(key: str) -> list[str]:
    """A type number and the stem under which it is also published.

    A trailing letter block is a sub-mark: "t72ba" is also published as
    "t72", "m1a1fep" as "m1a1". Only ONE stem is taken, so the key never
    erodes to a fragment that names something else.
    """
    out = [key]
    stem = re.match(r"^([a-z]*\d+[a-z]*\d*)[a-z]+$", key)
    if stem and len(stem.group(1)) >= 3:
        out.append(stem.group(1))
    return out


def designations(
    *texts: object, extra_categories: frozenset[str] | None = None
) -> list[str]:
    """Every designation the real thing is published under, in order.

    Pass the entry's published identity strings - its canonical name, its
    model and its curated aliases. Internal keys (a catalogue id, a variant
    id, a capture id) are NOT identity and should not be passed: they are
    repository bookkeeping and would put repository words in the matcher.
    """
    blocked = CATEGORY_WORDS | (extra_categories or frozenset())
    out: list[str] = []

    def add(key: str, floor: int) -> None:
        # A bare number is not an identity. "130" belongs to the C-130 and
        # to the Yak-130 alike, so admitting it would let one match the
        # other. A designation must carry at least one letter.
        if not key or key.isdigit():
            return
        if len(key) >= floor and key not in blocked and key not in out:
            out.append(key)

    for text in texts:
        if not isinstance(text, str) or not text:
            continue
        # A capture id may carry its source as a prefix; that names the
        # source, not the thing.
        clean = re.sub(r"^wikipedia[_ ]", "", text, flags=re.IGNORECASE)
        # A name may list ALTERNATIVES: "T-54/T-55" is two designations,
        # not one, and each is published on its own.
        for part in re.split(r"\s*/\s*", clean):
            if not part:
                continue
            # A short type designation is still a designation: "T-54"
            # folds to three characters and names a real tank, so a
            # letters-then-digits key is admitted at three.
            part_key = fold(part)
            add(part_key, 3 if re.fullmatch(r"[a-z]{1,3}\d{1,3}", part_key) else 4)
            # Split on WHITESPACE, not on every separator: a type number
            # is written with hyphens inside it, so "UH-1H" is one
            # designation and splitting it would leave the fragments "uh"
            # and "1h", which name nothing.
            words = [w for w in re.split(r"\s+", part) if w]
            for word in words:
                key = fold(word)
                if any(ch.isdigit() for ch in key):
                    for stem in _type_stems(key):
                        add(stem, 3)
            for first, second in zip(words, words[1:]):
                add(fold(first + second), 5)
    return out
