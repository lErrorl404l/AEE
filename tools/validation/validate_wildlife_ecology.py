#!/usr/bin/env python3
"""Validation for the wildlife ecology corpus.

Checks the committed corpus under data/wildlife/:

  - the schema fields are present and typed, per family and per group
  - every source grade is in the allowed set S, S-lit, R and U
  - every media path begins with a3\\ or is a listed confirmed CfgSFX class
  - no media path begins with x\\ or z\\
  - no UNKNOWN or UNCONFIRMED recording is assigned a species
  - every species group's sound group exists in the sound map

The media rules mirror tools/tests/test_wildlife.py:67-124: the a3\\ prefix,
the allowed CfgSFX set and the allowed extensions.

Run:  python3 tools/validation/validate_wildlife_ecology.py
Exit: 0 when every check passes, 1 when any fails.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO = Path(__file__).parents[2]
DEFAULT_DATA = REPO / "data" / "wildlife"

# Grade and identity vocabularies.
ALLOWED_GRADES = {"S", "S-lit", "R", "U"}
ALLOWED_IDENTITY = {"CONFIRMED", "UNCONFIRMED", "UNKNOWN"}
ALLOWED_ACTIVITY = {"diurnal", "nocturnal", "crepuscular"}
ALLOWED_GREGARIOUSNESS = {
    "solitary",
    "territorial",
    "pair",
    "flocking",
    "chorus",
    "herd",
    "pack",
    "swarm",
    "mixed",
}

# The media rules, copied from test_wildlife.py.
ALLOWED_CFGSFX = {"Owl", "Sound_Stream"}
ALLOWED_EXTENSIONS = {".wss", ".ogg", ".wav"}

# The recordings that must never be given a species. sarance is a confirmed
# cricket set, but the species is not pinned below the order, so it carries a
# taxon and never a species.
NEVER_SPECIES = {"sarance", "chicken_grill", "hen", "dog", "seagul_1", "sheep"}

# The ranks a species anchor may carry.
ALLOWED_RANKS = {"species", "subspecies", "genus", "family", "order", "suborder"}

REQUIRED_FAMILIES = {"tropical", "arid", "temperate", "cold", "water", "settlement"}
REQUIRED_FIELDS = [
    "group_id",
    "family",
    "taxa",
    "activity",
    "season",
    "temperature_c",
    "wind",
    "rain",
    "gregariousness",
    "habitat",
    "temporal",
    "sound_group",
    "field_grades",
    "grade",
]
REQUIRED_FIELD_GRADES = [
    "taxa",
    "activity",
    "season",
    "temperature_c",
    "wind",
    "rain",
    "gregariousness",
    "habitat",
    "temporal",
    "sound_group",
]


def _load(data_dir: Path) -> tuple[dict, dict]:
    ecology = json.loads((data_dir / "ecology.json").read_text(encoding="utf-8"))
    asset_map = json.loads((data_dir / "asset_map.json").read_text(encoding="utf-8"))
    return ecology, asset_map


def check_families(ecology: dict) -> list[str]:
    errors: list[str] = []
    families = ecology.get("families")
    if not isinstance(families, list):
        return ["ecology.json: families is not a list"]
    keys = [f.get("family") for f in families if isinstance(f, dict)]
    missing = REQUIRED_FAMILIES - set(keys)
    if missing:
        errors.append(f"missing families: {sorted(missing)}")
    if len(keys) != len(set(keys)):
        errors.append("a family key is duplicated")
    return errors


def check_group(group: dict, family: str) -> list[str]:
    errors: list[str] = []
    gid = group.get("group_id", "<no id>")
    for field in REQUIRED_FIELDS:
        if field not in group:
            errors.append(f"{gid}: missing field {field}")
    if errors:
        return errors
    if not isinstance(group["group_id"], str) or not group["group_id"]:
        errors.append(f"{gid}: group_id is not a non-empty string")
    if group["family"] != family:
        errors.append(f"{gid}: family {group['family']} does not match {family}")
    if not isinstance(group["taxa"], list) or not group["taxa"]:
        errors.append(f"{gid}: taxa is not a non-empty list")
    if group["activity"] not in ALLOWED_ACTIVITY:
        errors.append(f"{gid}: bad activity {group['activity']}")
    if group["gregariousness"] not in ALLOWED_GREGARIOUSNESS:
        errors.append(f"{gid}: bad gregariousness {group['gregariousness']}")
    season = group["season"]
    if not isinstance(season, dict) or not isinstance(season.get("months"), list):
        errors.append(f"{gid}: season.months is not a list")
    else:
        for month in season["months"]:
            if not isinstance(month, int) or not 1 <= month <= 12:
                errors.append(f"{gid}: bad month {month}")
    temp = group["temperature_c"]
    if (
        not isinstance(temp, dict)
        or not isinstance(temp.get("min"), (int, float))
        or not isinstance(temp.get("max"), (int, float))
    ):
        errors.append(f"{gid}: temperature_c is not a min/max object")
    wind = group["wind"]
    if (
        not isinstance(wind, dict)
        or not isinstance(wind.get("limit_ms"), (int, float))
        or not isinstance(wind.get("suppression"), (int, float))
    ):
        errors.append(f"{gid}: wind is not a limit/suppression object")
    rain = group["rain"]
    if (
        not isinstance(rain, dict)
        or not isinstance(rain.get("limit"), (int, float))
        or not isinstance(rain.get("suppression"), (int, float))
        or not isinstance(rain.get("triggers"), bool)
    ):
        errors.append(f"{gid}: rain is not a limit/suppression/triggers object")
    habitat = group["habitat"]
    if not isinstance(habitat, dict):
        errors.append(f"{gid}: habitat is not an object")
    else:
        for key in ("foliage", "surface", "water", "structures"):
            value = habitat.get(key)
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                errors.append(f"{gid}: habitat.{key} is not 0 to 1")
    temporal = group["temporal"]
    if not isinstance(temporal, dict) or not isinstance(temporal.get("bins"), list):
        errors.append(f"{gid}: temporal.bins is not a list")
    elif len(temporal["bins"]) != 7:
        errors.append(
            f"{gid}: temporal.bins has {len(temporal['bins'])} weights, expected 7"
        )
    elif not all(isinstance(b, (int, float)) and 0 <= b <= 1 for b in temporal["bins"]):
        errors.append(f"{gid}: a temporal bin weight is not 0 to 1")
    if not isinstance(temporal.get("dolbear"), bool):
        errors.append(f"{gid}: temporal.dolbear is not a bool")
    if not isinstance(group["sound_group"], str) or not group["sound_group"]:
        errors.append(f"{gid}: sound_group is not a non-empty string")
    return errors


def check_grades(ecology: dict) -> list[str]:
    errors: list[str] = []
    for family in ecology.get("families", []):
        for group in family.get("groups", []):
            gid = group.get("group_id", "<no id>")
            grades = group.get("field_grades")
            if not isinstance(grades, dict):
                errors.append(f"{gid}: field_grades is not an object")
                continue
            for field in REQUIRED_FIELD_GRADES:
                grade = grades.get(field)
                if grade not in ALLOWED_GRADES:
                    errors.append(f"{gid}: field_grades.{field}={grade} not allowed")
            if group.get("grade") not in ALLOWED_GRADES:
                errors.append(f"{gid}: grade {group.get('grade')} not allowed")
    return errors


def check_sound_map(ecology: dict, asset_map: dict) -> list[str]:
    errors: list[str] = []
    sound_ids = {s.get("sound_group") for s in asset_map.get("sound_groups", [])}
    for family in ecology.get("families", []):
        for group in family.get("groups", []):
            sg = group.get("sound_group")
            if sg not in sound_ids:
                errors.append(
                    f"{group.get('group_id')}: sound group {sg} is not in the map"
                )
    return errors


def check_media(asset_map: dict) -> list[str]:
    errors: list[str] = []
    for entry in asset_map.get("sound_groups", []):
        sid = entry.get("sound_group", "<no id>")
        if entry.get("identity") not in ALLOWED_IDENTITY:
            errors.append(f"{sid}: bad identity {entry.get('identity')}")
        for item in entry.get("media", []):
            if not isinstance(item, dict):
                errors.append(f"{sid}: a media item is not an object")
                continue
            value = item.get("path", item.get("cfg_sfx", ""))
            if not isinstance(value, str) or not value:
                errors.append(f"{sid}: an empty media reference")
                continue
            low = value.lower()
            if low.startswith(("x\\", "z\\")):
                errors.append(f"{sid}: third-party prefix {value}")
                continue
            if "." in value:
                if not low.startswith("a3\\"):
                    errors.append(f"{sid}: non-vanilla path {value}")
                extension = value[value.rfind(".") :].lower()
                if extension not in ALLOWED_EXTENSIONS:
                    errors.append(f"{sid}: unexpected extension {extension}")
            else:
                if value not in ALLOWED_CFGSFX:
                    errors.append(f"{sid}: unlisted CfgSFX class {value}")
    for entry in asset_map.get("faunal_groups", []):
        if entry.get("identity") not in ALLOWED_IDENTITY:
            errors.append(
                f"{entry.get('fauna_group')}: bad identity {entry.get('identity')}"
            )
    return errors


def check_no_species(asset_map: dict) -> list[str]:
    errors: list[str] = []
    for entry in asset_map.get("sound_groups", []):
        sid = entry.get("sound_group", "<no id>")
        species = entry.get("species")
        assigned = isinstance(species, str) and species.strip() != ""
        if entry.get("identity") in ("UNKNOWN", "UNCONFIRMED") and assigned:
            errors.append(f"{sid}: an {entry['identity']} recording has a species")
        if sid in NEVER_SPECIES and assigned:
            errors.append(f"{sid}: must never be given a species")
    return errors


def check_anchors(asset_map: dict, sources: list) -> list[str]:
    """Every species anchor carries a graded taxon and a registered source."""
    errors: list[str] = []
    source_ids = {s.get("source_id") for s in sources if isinstance(s, dict)}
    seen: set[tuple[object, object]] = set()
    for anchor in asset_map.get("species_anchors", []):
        if not isinstance(anchor, dict):
            errors.append("a species anchor is not an object")
            continue
        cls = anchor.get("class")
        if not isinstance(cls, str) or not cls:
            errors.append("a species anchor has no class")
            continue
        key = (cls, anchor.get("variant", ""))
        if key in seen:
            errors.append(f"{cls}: duplicate species anchor")
        seen.add(key)
        if not isinstance(anchor.get("taxon"), str) or not anchor["taxon"]:
            errors.append(f"{cls}: taxon is not a non-empty string")
        if anchor.get("rank") not in ALLOWED_RANKS:
            errors.append(f"{cls}: bad rank {anchor.get('rank')}")
        if anchor.get("grade") not in ALLOWED_GRADES:
            errors.append(f"{cls}: bad grade {anchor.get('grade')}")
        if anchor.get("source") not in source_ids:
            errors.append(f"{cls}: source {anchor.get('source')} is not registered")
    return errors


def main(argv: Sequence[str]) -> int:
    data_dir = DEFAULT_DATA
    if "--data-dir" in argv:
        index = argv.index("--data-dir")
        if index + 1 < len(argv):
            data_dir = Path(argv[index + 1])

    ecology, asset_map = _load(data_dir)
    sources = json.loads((data_dir / "sources.json").read_text(encoding="utf-8"))

    checks = [
        ("families present", check_families(ecology)),
        ("source grades allowed", check_grades(ecology)),
        ("sound groups exist", check_sound_map(ecology, asset_map)),
        ("media rules", check_media(asset_map)),
        ("no species on unverified", check_no_species(asset_map)),
        ("species anchors", check_anchors(asset_map, sources)),
    ]
    group_errors: list[str] = []
    for family in ecology.get("families", []):
        for group in family.get("groups", []):
            group_errors += check_group(group, family.get("family", ""))
    checks.insert(1, ("group schema and types", group_errors))

    lines = ["AEE Wildlife Ecology Validation", "=" * 31, ""]
    failed = 0
    for name, errors in checks:
        status = "PASS" if not errors else "FAIL"
        if errors:
            failed += 1
        lines.append(f"[{status}] {name}")
        for error in errors:
            lines.append(f"    - {error}")
    lines.append("")
    lines.append(f"Checks: {len(checks) - failed} of {len(checks)} passed")
    report = "\n".join(lines)
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
