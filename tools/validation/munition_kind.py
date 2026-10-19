#!/usr/bin/env python3
"""The munition kind filter: which equipment is a munition, and which is not.

A munition catalogue must name munitions.  The coverage scan holds every
class the game and the installed mods declare, and some classes it finds
under a vehicle armament root are not munitions at all: a cockpit switch, a
targeting pod, a countermeasure discharger, an aircraft weapon bay.  The
config cannot tell them apart from a munition, because each one declares a
magazine and some hold a damaging round.  What separates them is what they
ARE, so every term below names a KIND of equipment.  No term names a mod and
no term names a class.

This is the same idiom as the vehicle-property filter PROP in
tools/report_match_coverage.py, which removes the seating, the scenery and
the weapon emplacements that inherit a vehicle but are not one.

Two consumers share this module, so the filter holds in one place:

  tools/report_match_coverage.py     drops a non-munition class from the
                                     coverage measurement, so the number
                                     counts real munitions only.
  tools/validation/gen_munition_data.py
                                     writes SCREEN_TERMS into the generated
                                     matcher, so the runtime screens a
                                     non-munition out instead of forcing
                                     the "closest" rung onto a switch.

A term that could name a REAL munition is kept out of the runtime screen.
"flare", "chaff" and "decoy" each name a countermeasure device AND a real
round, so the runtime matcher does not screen on them: a real flare or smoke
round is a munition, and the corpus must be able to name it.  The coverage
measurement still uses them, because the corpus scope is rounds and gun
barrels, and the munition suite proves that no catalogue entry carries any
screened term.

Run:  python3 -m tools.validation.munition_kind
"""

from __future__ import annotations

import re

# Phrase, kind, and whether the runtime matcher can screen on the phrase.
#
# The runtime screen is a substring test on the folded class identity.  A
# phrase that is a common word ("safe") or a common suffix ("pod") is safe
# under the coverage filter, which anchors at a word boundary and excepts a
# gun pod, but it is not safe as a plain substring.  Those phrases carry
# screen=False.
KINDS: tuple[tuple[str, str, bool], ...] = (
    # A cockpit switch: it arms or limits a store, it fires nothing.
    ("master arm", "cockpit switch", True),
    ("inhibit", "cockpit switch", True),
    ("safe", "cockpit switch", False),
    ("burst limit", "cockpit switch", True),
    ("salvo limit", "cockpit switch", True),
    # The bay the store hangs in.
    ("internal bay", "weapon bay", True),
    # A pod that carries a sensor, never a warhead.  A GUN POD is not in
    # this list: it holds a real gun, the gun is a real munition-firing
    # weapon, and the catalogue names the gun.
    ("targeting pod", "recon pod", True),
    ("recon pod", "recon pod", True),
    ("tarps", "recon pod", True),
    ("pod", "recon pod", False),
    # A countermeasure device: it launches a decoy, it is not the decoy.
    ("dircm", "countermeasure", True),
    ("irjam", "countermeasure", True),
    ("jammer", "countermeasure", True),
    # Coverage only: the MW-1 and the CBU are munitions dispensers.
    ("dispenser", "countermeasure", False),
    ("smoke generator", "countermeasure", True),
    ("smoke screen", "countermeasure", True),
    # Coverage only: a real flare, chaff or decoy round carries the word.
    ("flare", "countermeasure", False),
    ("chaff", "countermeasure", False),
    ("decoy", "countermeasure", False),
    # A leaflet dispenser.
    ("pdu-5", "leaflet dispenser", True),
    # A ship vertical launch cell.
    ("vls", "ship launcher cell", True),
    # A generic label that names no weapon at all: the slot, not the store.
    ("action in progress", "generic label", True),
    ("rocket launcher", "generic label", True),
)

# Two phrases need more than a word boundary: "pod" excepts a gun pod, and
# "safe" must not match inside a longer word.  The countermeasure words are
# plain substrings, because the device is named by a compound ("Flares",
# "CMChaffLauncher").
_SPECIAL = {
    "pod": r"(?<!gun )(?<!gun)\bpod\b",
    "safe": r"\bsafe\b",
}
_PLAIN = {"flare", "chaff", "decoy"}
_PHRASE = {
    phrase: _SPECIAL.get(
        phrase,
        re.escape(phrase) if phrase in _PLAIN else r"\b" + re.escape(phrase) + r"\b",
    )
    for phrase, _kind, _screen in KINDS
}

# The coverage filter.  A class that matches is not a munition.
NOT_A_MUNITION = re.compile("|".join(_PHRASE[p] for p, _k, _s in KINDS), re.I)

# The runtime screen: the folded substrings the generated matcher tests,
# and the kind each one names.
SCREEN_KIND: dict[str, str] = {
    phrase.lower().replace(" ", "").replace("-", ""): kind
    for phrase, kind, screen in KINDS
    if screen
}
SCREEN_TERMS: tuple[str, ...] = tuple(SCREEN_KIND)


def fold(text: str) -> str:
    """Fold identity text the way the matcher does: letters and digits only."""
    return "".join(c for c in text.lower() if c.isascii() and c.isalnum())


def screened(*texts: str) -> str:
    """The kind the runtime screen reads in a class, or "" when none.

    The runtime tests a folded substring, so a classname that joins its
    words with an underscore ("FIR_Mk41_VLS_SM") is caught here and not by
    the word-boundary coverage pattern.  The coverage tool uses this so the
    number it reports is the number the runtime delivers.
    """
    for text in texts:
        if not text:
            continue
        folded = fold(text)
        for term, kind in SCREEN_KIND.items():
            if term in folded:
                return kind
    return ""


def kind_of(*texts: str) -> str:
    """The equipment kind a class belongs to, or "" for a munition."""
    for text in texts:
        if not text:
            continue
        for phrase, kind, _screen in KINDS:
            if re.search(_PHRASE[phrase], text, re.I):
                return kind
    return ""


def is_munition(*texts: str) -> bool:
    """True when no text names a non-munition equipment kind.

    The caller passes the identity text it has: a classname, a display
    name, or both.  A non-munition in any of them makes the class a
    non-munition.
    """
    return kind_of(*texts) == ""


def main() -> int:
    print(f"munition kind filter: {len(KINDS)} kinds, {len(SCREEN_TERMS)} screened")
    for phrase, kind, screen in KINDS:
        print(f"  {phrase:<20} {kind:<20} {'screen' if screen else 'coverage only'}")
    print("screen terms: " + " ".join(SCREEN_TERMS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
