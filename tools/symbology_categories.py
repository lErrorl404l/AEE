#!/usr/bin/env python3
"""The AEE marker categories (CfgMarkerClasses).

The engine marker picker is a FLAT list of CfgMarkerClasses.  AEE expresses the
hierarchy the operator asked for with two levels in the class name and the
displayName: the CATEGORY is the affiliation (Friend, Hostile, Neutral,
Unknown) and the SUBCATEGORY is the battle dimension.  The three generated
modifier groups carry their own categories.

The category names here MUST match the CfgMarkerClasses classes declared in
addons/optics/config.cpp; tools/tests/test_symbology.py pins the two together.
"""

from __future__ import annotations

AFFILIATIONS = ("Friend", "Hostile", "Neutral", "Unknown")
ROLES = ("Land", "Air", "Sea", "Subsurface", "Installation", "Equipment", "Other")

# The modifier groups, not affiliation symbols.
MODIFIER_CATEGORIES = (
    ("AEE_Mission_Tasks", "AEE Mission Tasks"),
    ("AEE_Modifiers", "AEE Modifiers"),
    ("AEE_Echelon", "AEE Echelon"),
)

_AFFIL_TOKEN = {
    "Friendly": "Friend",
    "Hostile": "Hostile",
    "Neutral": "Neutral",
    "Unknown": "Unknown",
    "Unspecified": "Unknown",
}


def _role(dim: str) -> str:
    d = dim.lower()
    if "land" in d:
        return "Land"
    if "air" in d or "space" in d:
        return "Air"
    if "sea" in d:
        return "Sea"
    if "subsurface" in d:
        return "Subsurface"
    if "installation" in d:
        return "Installation"
    if "equipment" in d:
        return "Equipment"
    return "Other"


def marker_category(affil: str, dim: str) -> str:
    """The CfgMarkerClasses class for an affiliation and a battle dimension."""
    return f"AEE_{_AFFIL_TOKEN.get(affil, 'Unknown')}_{_role(dim)}"


def modifier_category(kind: str) -> str:
    """The CfgMarkerClasses class for a generated modifier group."""
    return {
        "mission_task": "AEE_Mission_Tasks",
        "modifier": "AEE_Modifiers",
        "echelon": "AEE_Echelon",
    }[kind]


def marker_classes() -> list[tuple[str, str]]:
    """Every AEE CfgMarkerClasses class and its displayName, in picker order."""
    out: list[tuple[str, str]] = []
    for affil in AFFILIATIONS:
        for role in ROLES:
            out.append((f"AEE_{affil}_{role}", f"AEE {affil} - {role}"))
    out.extend(MODIFIER_CATEGORIES)
    return out
