#!/usr/bin/env python3
"""Measure the matchers against the game content actually installed.

Coverage is not a guess: tools/scan_game_classes.py reads what the game
and the installed mods declare, and this walks that scan through the same
ladder the runtime matcher uses, so the number is what a player would get.

Every table is reported twice: BASE, the classes the game itself ships, and
MODDED, the classes a mod declares. The base game is `<install>/Addons`, so
the split is derived from the install and never from a list of names. The
modded number is the one that must reach 100%: a mod nobody has written yet
is measured by the same rule as one that is installed.

It also prints the gap list - the real vehicles and aircraft that appear in
the content but that no catalogue entry can name - which is the worklist
for capturing new entries. `--modded` prints the same list restricted to
modded classes, as one tab-separated record per class, carrying the class,
the display name, the parent and the source PBO.

Two artefacts make the closing work a stable input rather than a fresh
derivation. Both carry their provenance:

  data/coverage/modded_gaps_<table>.txt   one file per table, tab-separated
                                          class, display, parent, source
  data/coverage/modded_baseline.json      per table: base count, modded
                                          count, and the scan, date, install
                                          and base PBO count behind them

Run:
    OUT=/tmp/all.jsonl python3 tools/scan_game_classes.py \\
        "<game>/Addons" "<workshop>/107410"
    python3 tools/report_match_coverage.py /tmp/all.jsonl \\
        --modded --gaps \\
        --write-gaps data/coverage \\
        --write-baseline data/coverage/modded_baseline.json
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation.munition_kind import (  # noqa: E402
    is_munition,
    kind_of,
    screened,
)

VEHICLE = REPO / "addons/vehicles/functions/fnc_getVehicleMatch.sqf"
AIRCRAFT = REPO / "addons/flight/functions/fnc_getAircraftMatch.sqf"
WEAPON = REPO / "addons/ballistics/functions/fnc_getWeaponData.sqf"
MUNITION_TABLE = REPO / "addons/blast/functions/munition/fnc_getMunitionMatch.sqf"
DEVICE = REPO / "addons/nightvision/functions/fnc_getDeviceMatch.sqf"
ITEM_MASS = REPO / "addons/clothing/functions/clothing/fnc_getItemMass.sqf"

# Every generated identity table this report measures. A new generated
# matcher is added here, never silently omitted: the coverage lock reads
# this tuple, so a table that stops being measured fails the suite.
MEASURED_TABLES = (
    "vehicles",
    "aircraft",
    "small_arms",
    "carried_launchers",
    "vehicle_armament",
    "night_vision_devices",
    "thermal_optics",
    "optics",
    "uniforms",
    "vests",
    "helmets",
    "rucksacks",
)

# The class a table is scored against, from the config taxonomy the engine
# itself declares. The device table's optic and thermal rows are NOT here:
# the discriminator between an optic and any other ItemCore descendant is
# CfgWeapons >> ItemInfo >> type and OpticsModes, which the scan does not
# hold, so no denominator can be derived from it.
UNIFORM_ROOT = "uniform_base"
VEST_ROOTS = {"vest_camo_base", "vest_nocamo_base"}
HELMET_ROOT = "helmetbase"
BACKPACK_ROOT = "bag_base"
NVG_ROOT = "nvgoggles"

# The device ladder accepts a designation of this length at the alias layer.
DEVICE_MIN = 4

# The ENGINE kind a type entry states, from the config chain the class
# passes. It names a kind, never a model: a tank and a tracked APC are both
# armoured vehicles, and the chain is the engine's own statement.
VEHICLE_KINDS = (
    ("armoured vehicle", {"tank"}),
    ("truck", {"truck"}),
    ("motorcycle", {"motorcycle"}),
    ("car", {"car"}),
)
AIRCRAFT_KINDS = (
    ("helicopter", {"helicopter"}),
    ("fixed-wing aircraft", {"plane"}),
    ("unmanned aerial vehicle", {"uav"}),
)
VEHICLE_FALLBACK = "vehicle"
AIRCRAFT_FALLBACK = "aircraft"


def _engine_kind(chain: list, kinds: tuple, fallback: str) -> str:
    seen = set(chain)
    for kind, roots in kinds:
        if seen & roots:
            return kind
    return fallback

# The base game is the PBOs the install ships. Everything else in a scan is
# modded. The directory name comes from the install, and the environment
# variable lets a caller point at a second install without editing this file.
BASE_ADDONS = "Addons"
INSTALL_ENV = "AEE_ARMA3_DIR"

# CfgWeapons holds every weapon the game has, not just the ones a soldier
# carries, and the weapon catalogue is a SMALL-ARMS catalogue: it holds one
# datum per weapon, the rifling twist. So the split is taken from the
# game's OWN taxonomy - the CfgWeapons inheritance root - rather than from
# a list of names, which is what makes it hold for a mod nobody has
# written yet.
#
#   RifleCore, PistolCore      a small arm, which the catalogue names
#   Launcher_Base_F            a launcher a soldier carries: it fires a
#                              rocket or a recoilless round, so a rifling
#                              twist is not a thing it has
#   LauncherCore, CannonCore,  vehicle armament
#   MGunCore, MissileLauncher,
#   RocketPods, BombCore,
#   GatlingCore
#   anything else              a store, a countermeasure or a pod: not a
#                              weapon that fires a projectile at all
SMALL_ARMS_ROOT = {"riflecore", "pistolcore"}
CARRIED_LAUNCHER_ROOT = {"launcher_base_f", "launcher_base"}
VEHICLE_ARMAMENT_ROOT = {
    "launchercore",
    "cannoncore",
    "missilelauncher",
    "rocketpods",
    "bombcore",
    "mgun",
    "mguncore",
    "autocannon",
    "gatlingcore",
    "bomblauncher",
    "rocketlauncher",
}
# A mod base class whose own parent is declared in a PBO this scan did not
# read leaves the chain short. The classname still says what it is, so the
# vanilla weapon-slot prefixes carry the fallback.
SMALL_ARMS_PREFIX = re.compile(r"\b(a|s|h|l|m)?(rifle|gun|hgun|smg|lmg|mmg)_", re.I)
# A classname ending in BASE is a base class the mod builds others from.
BASE_CLASS = re.compile(r"_base(_[a-z]{1,2})?$", re.I)

# Things that live in CfgWeapons under an armament root and are NOT a
# munition are filtered by tools/validation/munition_kind.py, which the
# runtime matcher shares.  A catalogue of real munitions is not scored
# against a cockpit switch, a targeting pod, a countermeasure discharger, a
# leaflet dispenser or an aircraft weapon bay.
MUNITION = re.compile(
    r"rocket|missile|bomb|gbu|agm|aim-|flare|dagr|apkws|crv7|torpedo|shell"
    r"|railgun|laser|cannon|pods?\b"
    # Stores and countermeasures also live in CfgWeapons and declare
    # magazines, but none of them is a small arm either.
    r"|chaff|irjam|jammer|napalm|\bsdb\b|\blgb\b|\bsraw\b|gas\b"
    r"|agent|incendiary|cluster|decoy|smoke ?(launcher|generator)"
    # The weapon corpus holds ONE datum per weapon, the rifling twist, so a
    # weapon with no rifled barrel is not something it can ever name: a
    # rocket or grenade launcher, a dazzler, a smoke or flare discharger.
    r"|\brpg[- ]?\d|\bgp-?2\d\b|\bpbg\d|dazzler|\bchf/flr\b"
    r"|^smoke\b|\baction in progress\b",
    re.I,
)
SCAN_MIN = 3

# Why the classes the measurement leaves open stay open. The count is derived
# from the gap list, so only the reason is written here.
KNOWN_UNRESOLVABLE = {
    "vehicles": (
        "Every class here is named by its own text at a layer the runtime "
        "would refuse as a tie, or names no entry at all. A tie is answered "
        "as an empty result by the engine, so the measurement reports the "
        "class as open even where a weaker layer would have guessed. Closing "
        "one needs a term the class's own text carries and no other class "
        "does."
    ),
    "aircraft": (
        "The aircraft ladder refuses a tie the same way. Ten of these are "
        "loadout configurations of an Arma 3 fictional type, and eight are "
        "ArmaFPV drones no published source designates. The rest tie above "
        "the family rung: a shared reporting name held as a curated alias of "
        "two marks (falcon, hornet, merlin, pavehawk, black hawk), a role "
        "word several entries carry (cas, gunship), the AH-64 marks' shared "
        "ah64 with ah6 as a substring of every AH-64 query, and the Mi-8MTV-3 "
        "whose mi8 ties against the Mi-8T and Mi-8AMTSh. Capturing the family "
        "word would answer a different mark in each case. Closing one needs "
        "the mark's own designation in the class or display text."
    ),
    "small_arms": (
        "The two DSA machine pistols name a chambering and a category, not a "
        "designation, and their ancestors are themselves unnamed, so there is "
        "nothing for a chain to answer."
    ),
    "vehicle_armament": (
        "A tied munition is refused. The open classes name a body, a "
        "seeker or a warhead the catalogue holds for a different store."
    ),
    "night_vision_devices": (
        "The device ladder refuses a tie at every layer above the scored "
        "one. The open classes carry no published designation, or carry "
        "one two entries share."
    ),
    "uniforms": (
        "The item-mass resolver names a family the class text carries. "
        "The open uniforms carry a pattern or a loadout description and "
        "no product family, and their band fallback needs the live config "
        "mass the scan does not hold."
    ),
    "vests": (
        "The open vests carry a variant or a maker the table holds for "
        "another slot, or no published family at all."
    ),
    "helmets": (
        "Most open helmets carry a stringtable display the scan cannot "
        "localise, so the only identity text left is a generic classname."
    ),
    "rucksacks": (
        "The open rucksacks carry a maker or a capacity description and "
        "no published pack family."
    ),
}

# A class is a vehicle when its inheritance chain passes one of these.
LAND = {
    "car",
    "tank",
    "truck",
    "motorcycle",
    "landvehicle",
    "wheeled_apc_f",
    "apc_tracked_01_base_f",
}
AIR = {"air", "helicopter", "plane", "uav"}
# A tripod gun or a mortar inherits LandVehicle without being a vehicle. The
# fleet inventory excludes it by the same rule, in
# tools/validation/gen_vehicle_bindings.py: a ground class is a LandVehicle
# that is not a StaticWeapon.
STATIC_WEAPON = "staticweapon"
STATIC_WEAPON_KIND = "static weapon emplacements"
# Things that inherit a vehicle but are not one.
# A class can inherit a vehicle and still not be one: Arma hangs seating,
# scenery and weapon emplacements off vehicle classes. None of these is a
# thing a catalogue of real vehicles should be scored against.
PROP = re.compile(
    r"towel|stool|chair|matress|mattress|seatable|parachute|wreck|ejection"
    r"|cruise missile|\bpod\b|radar|rope|dummy|spawner|helper|static"
    r"|hammock|forklift|fork ?lift|\bvls\b|satcom|\bffv\b|\bpylon\b"
    # A camera round is fired from a mortar; it is not an aircraft.
    r"|huntir"
    # Arma hangs STATIC WEAPONS and radars off vehicle classes. A tripod
    # machine gun, a recoilless gun, a towed howitzer, a MANPADS post and a
    # surveillance radar are not vehicles, and a catalogue of real vehicles
    # should not be scored against them.
    r"|\bnsv\b|\bkord\b|dshkm?\b|\bags-?\d|\bspg-?9|\bd-?30a?\b"
    r"|\b2a18m\b|\b9k3\d\b|djigit|\bp-37\b|\bprv-?\d"
    r"|anti-ship|\basm\b|missile|torpedo|\bbase class\b|\bcrate\b",
    re.I,
)


def fold(text: str) -> str:
    return "".join(c for c in text.lower() if c.isascii() and c.isalnum())


FAMILY_MARKER = "private _families = ["


def _tables(path: Path) -> tuple[str, str]:
    """Split a matcher file into its mark table text and its family text.

    A family row is identity-only, so the generated matcher keeps it in a
    separate table that no rung above the family rung reads. The measurement
    has to split the file the same way, or the family row would enter the
    mark table and every text layer with it.
    """
    text = path.read_text(encoding="utf-8")
    if FAMILY_MARKER not in text:
        return text, ""
    head, _, rest = text.partition(FAMILY_MARKER)
    family, _, _ = rest.partition("\n];")
    return head, family


def _parse(text: str, armament: bool = False) -> list:
    """Parse one generated table. Armament rows hold fewer columns."""
    classes_col, aliases_col, keywords_col = (2, 3, 4) if armament else (4, 5, 6)
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith('["'):
            continue
        p = re.findall(r'"([^"]*)"', s)
        if len(p) <= keywords_col:
            continue
        out.append(
            {
                "id": p[0],
                "classes": [x for x in p[classes_col].split("|") if x],
                "aliases": [x for x in p[aliases_col].split("|") if x],
                "keywords": [x for x in p[keywords_col].split("|") if x],
            }
        )
    return out


def rows(path: Path) -> list:
    """The mark table of a vehicle or aircraft matcher."""
    return _parse(_tables(path)[0])


def family_rows(path: Path) -> list:
    """The family table of a vehicle or aircraft matcher."""
    return _parse(_tables(path)[1])


def munition_rows(path: Path) -> list:
    """The munition table: id, type, classes, aliases, keywords."""
    return _parse(_tables(path)[0], armament=True)


def munition_family_rows(path: Path) -> list:
    """The family table of the munition matcher."""
    return _parse(_tables(path)[1], armament=True)


def device_rows(path: Path, family: str = "") -> list:
    """The device table: id, family, mapped classes, aliases, keywords.

    A row is seven columns; the value row carries its own strings, so only
    the identity columns are read. `family` selects one device family, the
    same filter the runtime applies before its ladder runs.
    """
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith('["'):
            continue
        p = re.findall(r'"([^"]*)"', s)
        if len(p) < 5 or (family and p[1] != family):
            continue
        out.append(
            {
                "id": p[0],
                "family": p[1],
                "classes": [x for x in p[2].split("|") if x],
                "aliases": [x for x in p[3].split("|") if x],
                "keywords": [x for x in p[4].split("|") if x],
            }
        )
    return out


def device_matcher(table: list, trace=None, type_entry=None, ancestry=None):
    """The device ladder: exact class, alias, keyword, then closest.

    The keyword layer answers nothing on a tie and the closest layer below
    it decides, exactly as the generated matcher does. The table arrives
    already filtered by family, so one class cannot tie across two families.
    """

    def match(cls: str = "", display: str = ""):
        text = (cls + " " + display).strip()
        key = fold(text)
        if not key:
            return None
        class_key = fold(cls) or key
        tokens = {fold(t) for t in re.split(r"[ _\-.]+", text) if fold(t)}

        hit = [r for r in table if class_key in r["classes"]]
        if len(hit) == 1:
            if trace is not None:
                trace.update(layer="exact_class", candidates=[hit[0]["id"]])
            return hit[0]
        if len(hit) > 1:
            if trace is not None:
                trace.update(layer="exact_class", candidates=[r["id"] for r in hit])
            return _type_row(type_entry, cls, trace)

        hit = [r for r in table if tokens & set(r["aliases"])]
        if len(hit) == 1:
            if trace is not None:
                trace.update(layer="alias", candidates=[hit[0]["id"]])
            return hit[0]
        if len(hit) > 1:
            if trace is not None:
                trace.update(layer="alias", candidates=[r["id"] for r in hit])
            return _type_row(type_entry, cls, trace)

        terms_of = lambda r: r["aliases"] + r["keywords"]  # noqa: E731
        hit = [
            r
            for r in table
            if any(len(w) >= DEVICE_MIN and w in key for w in terms_of(r))
        ]
        if len(hit) == 1:
            if trace is not None:
                trace.update(layer="keyword", candidates=[hit[0]["id"]])
            return hit[0]

        best = None
        best_score = runner = 0
        best_count = best_name = 0
        tie = False
        for r in table:
            terms = terms_of(r)
            score = sum(
                len(w) * (2 if any(c.isdigit() for c in w) else 1)
                for w in terms
                if len(w) >= DEVICE_MIN and w in key
            )
            count = len(terms)
            longest = max((len(w) for w in terms), default=0)
            if score > best_score:
                runner, best_score, best, best_count, best_name, tie = (
                    best_score,
                    score,
                    r,
                    count,
                    longest,
                    False,
                )
            elif score == best_score and score > 0:
                if count < best_count:
                    best, best_count, best_name, tie = r, count, longest, False
                elif count == best_count:
                    if longest < best_name:
                        best, best_name, tie = r, longest, False
                    elif longest == best_name:
                        tie = True
            if score < best_score:
                runner = max(runner, score)
        if best is not None and not tie and best_score > runner:
            if trace is not None:
                trace.update(layer="closest", candidates=[best["id"]])
            return best
        if trace is not None and best is not None and tie:
            trace.update(layer="closest", candidates=[best["id"]])

        # The inherited rung: the nearest ancestor a row maps by classname,
        # when the class text names a designation that row carries.
        if ancestry is not None and cls:
            for name in ancestry(cls):
                key_name = fold(name)
                hits = [r for r in table if key_name in r["classes"]]
                if not hits:
                    continue
                if len(hits) == 1:
                    blob = fold(
                        hits[0]["id"]
                        + "|"
                        + "|".join(hits[0]["aliases"])
                        + "|"
                        + "|".join(hits[0]["keywords"])
                    )
                    if any(len(t) >= DEVICE_MIN and t in blob for t in tokens):
                        if trace is not None:
                            trace.update(layer="inherited", candidates=[hits[0]["id"]])
                        return hits[0]
                break
        return _type_row(type_entry, cls, trace)

    return match


def equipment_rows(path: Path) -> list:
    """The item-mass table: family keyword, slot category, in table order.

    Order is the rule: the generator writes the longest family first, and
    the runtime stops at the first row whose family the identity text
    carries, so the measurement must not re-sort it.
    """
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith('["'):
            continue
        p = re.findall(r'"([^"]*)"', s)
        if len(p) < 2:
            continue
        out.append({"id": p[0].lower(), "family": p[0].lower(), "category": p[1]})
    return out


def equipment_matcher(
    table: list, category: str, trace=None, type_entry=None, ancestry=None
):
    """The item-mass resolver, restricted to the slot it is asked about.

    The runtime is handed the categories the caller accepts, and a row of
    another category is skipped rather than scored. A family is matched as
    a case-folded substring of the classname and display name, the same
    `find` the generated resolver runs.
    """

    def match(cls: str = "", display: str = ""):
        hay = (cls + " " + display).lower()
        for r in table:
            if r["category"] == category and r["family"] in hay:
                if trace is not None:
                    trace.update(layer="family", candidates=[r["id"]])
                return r
        # A variant of a named item is still that item: the ancestor's
        # classname carries the family, so its published mass answers.
        if ancestry is not None and cls:
            for name in ancestry(cls):
                hay_ancestor = str(name).lower()
                for r in table:
                    if r["category"] == category and r["family"] in hay_ancestor:
                        if trace is not None:
                            trace.update(layer="inherited", candidates=[r["id"]])
                        return r
        return _type_row(type_entry, cls, trace) if type_entry is not None else None

    return match


def _type_row(type_entry, cls: str, trace) -> dict | None:
    """The kind-of-item answer, or None when the caller states no kind."""
    if type_entry is None:
        return None
    kind = type_entry(cls) if callable(type_entry) else type_entry
    if not kind:
        return None
    if trace is not None:
        trace.update(layer="type", candidates=[kind])
    return {"id": kind, "classes": [], "aliases": [], "keywords": [], "type": True}


def matcher(table: list, ancestry=None, trace=None, families=None, type_entry=None):
    """The runtime ladder: exact class, alias, keyword, closest, then the
    inherited rung, then the family rung.

    `ancestry` is the engine parent chain, a callable that returns a class's
    ancestors nearest first as classnames. Only the vehicle table is given
    one, because only its runtime matcher walks the chain.

    `families` is the family table, read by the last rung alone. A family row
    names a family and no mark, so it never enters the table above and can
    never take an answer from a mark. Exactly one family row matching a
    designation of `SCAN_MIN` or more characters answers; two answer nothing.

    `trace`, when given, receives the layer that answered, or the layer that
    blocked the match and the candidates it tied between. It is
    instrumentation and changes no decision.

    `type_entry` is the last rung: when nothing above names the class, the
    kind of item it is answers. It is a string, or a callable that receives
    the classname and returns the kind from the engine chain. A type entry
    carries no model and no figure.
    """

    def match(cls: str = "", display: str = ""):
        text = (cls + " " + display).strip()
        key = fold(text)
        if not key:
            return None
        # The runtime's exact layer reads the CLASS alone; the display only
        # enters at the alias layer onward.
        class_key = fold(cls) or key
        # The runtime splits the identity into TOKENS for the alias layer,
        # because a curated alias is a whole designation and must match a
        # whole word of the query: "S-5" folds to "s5", which the folded
        # whole identity never equals. The mirror has to split the same
        # way or it under-reports every short alias.
        tokens = {fold(t) for t in re.split(r"[ _\-.]+", text) if fold(t)}
        hit = [r for r in table if class_key in r["classes"]]
        if len(hit) == 1:
            if trace is not None:
                trace.update(layer="exact_class", candidates=[hit[0]["id"]])
            return hit[0]
        if len(hit) > 1:
            if trace is not None:
                trace.update(layer="exact_class", candidates=[r["id"] for r in hit])
            return _type_row(type_entry, cls, trace)
        hit = [r for r in table if tokens & set(r["aliases"])]
        if len(hit) == 1:
            if trace is not None:
                trace.update(layer="alias", candidates=[hit[0]["id"]])
            return hit[0]
        if len(hit) > 1:
            if trace is not None:
                trace.update(layer="alias", candidates=[r["id"] for r in hit])
            return _type_row(type_entry, cls, trace)
        # The keyword layer scans the keywords alone, as the generated matcher
        # does. A curated alias is matched by equality at the layer above, so it
        # is not a substring key here.
        hit = [
            r
            for r in table
            if any(len(w) >= SCAN_MIN and w in key for w in r["keywords"])
        ]
        if len(hit) == 1:
            if trace is not None:
                trace.update(layer="keyword", candidates=[hit[0]["id"]])
            return hit[0]
        if len(hit) > 1:
            if trace is not None:
                trace.update(layer="keyword", candidates=[r["id"] for r in hit])
            return _type_row(type_entry, cls, trace)
        best = None
        best_score = runner = 0
        best_count = 0
        best_name = 0
        tie = False
        for r in table:
            terms = r["aliases"] + r["keywords"]
            # A type number identifies; a plain word only describes. The
            # runtime weights a digit-bearing designation double, so the
            # mirror must too.
            score = sum(
                len(w) * (2 if any(c.isdigit() for c in w) else 1)
                for w in terms
                if len(w) >= SCAN_MIN and w in key
            )
            if score < SCAN_MIN:
                continue
            count = len(terms)
            longest = max((len(w) for w in terms), default=0)
            if score > best_score:
                runner, best_score, best, best_count, best_name, tie = (
                    best_score,
                    score,
                    r,
                    count,
                    longest,
                    False,
                )
            elif score == best_score:
                if count < best_count:
                    best, best_count, best_name, tie = r, count, longest, False
                elif count == best_count:
                    if longest < best_name:
                        best, best_name, tie = r, longest, False
                    elif longest == best_name:
                        tie = True
            if score < best_score:
                runner = max(runner, score)
        if best and not tie and best_score > runner:
            if trace is not None:
                trace.update(layer="closest", candidates=[best["id"]])
            return best
        # Nothing in the class text names an entry. The engine ancestry is
        # the last evidence there is, and it is used only when the class
        # text names the ancestor's entry (see inherited_row).
        if ancestry is not None and cls:
            row, _ancestor = inherited_row(table, cls, tokens, ancestry)
            if row is not None:
                if trace is not None:
                    trace.update(layer="inherited", candidates=[row["id"]])
                return row
        # Last rung: the class text names a family and no mark. The family
        # table is separate, so no rung above could have answered from it.
        if families:
            hit = [
                r
                for r in families
                if any(len(w) >= SCAN_MIN and w in key for w in r["keywords"])
            ]
            if len(hit) == 1:
                if trace is not None:
                    trace.update(layer="family", candidates=[hit[0]["id"]])
                return hit[0]
            if len(hit) > 1 and trace is not None:
                trace.update(layer="family", candidates=[r["id"] for r in hit])
        # Last rung: the kind of item it is. It names a kind, never a model.
        return _type_row(type_entry, cls, trace)

    return match


def _named_ancestor(table: list, name: str):
    """The one entry that maps this ancestor classname, or None.

    The mapped-class test only: a mod may rewrite any ancestor's displayName,
    so the classname is the evidence and the text is not.
    """
    key = fold(name)
    if not key:
        return None
    hit = [r for r in table if key in r["classes"]]
    return hit[0] if len(hit) == 1 else None


def _blob(row: dict) -> str:
    """The identity text one entry is published under, folded."""
    return fold(
        row["id"] + "|" + "|".join(row["aliases"]) + "|" + "|".join(row["keywords"])
    )


def _claims(row: dict, tokens: set) -> bool:
    """True when a class token names something the entry is identified by.

    This is the retexture test. A class that carries the ancestor's family
    word, or a maker or a model the ancestor's entry is published under, is
    the same article in new paint. A class that carries neither describes a
    DIFFERENT article, so the rung must refuse it however short the chain.
    """
    blob = _blob(row)
    return any(len(t) >= SCAN_MIN and t in blob for t in tokens)


def inherited_row(table: list, cls: str, tokens: set, ancestry):
    """The row the ENGINE ancestry yields, and the ancestor that yielded it.

    A claim about ancestry, never about identity: the nearest ancestor the
    table names decides, and it answers only where the class's own text names
    it. A nearer ancestor that the class text does not name blocks a further
    one, so a generic engine class can never answer for a specific class.
    """
    for name in ancestry(cls):
        row = _named_ancestor(table, name)
        if row is None:
            continue
        if _claims(row, tokens):
            return row, name
        return None, name
    return None, None


def ancestry_closures(
    selected: list, table: list, plain, chained, ancestry, base
) -> list:
    """Every class the inherited rung closed, with the chain that closed it.

    A closed class has no identity of its own, so the record states what the
    answer rests on: the ancestor the table names, the config chain from the
    class to that ancestor, and the class tokens that name it. The claim is
    engine ancestry; it is not a claim that the class is that real vehicle.
    """
    out = []
    for r in selected:
        if plain(r["class"], r["display"]) is not None:
            continue
        row = chained(r["class"], r["display"])
        if row is None or row.get("type"):
            continue
        tokens = {
            fold(t)
            for t in re.split(r"[ _\-.]+", r["class"] + " " + r["display"])
            if fold(t)
        }
        chain, ancestor = [r["class"]], ""
        for name in ancestry(r["class"]):
            chain.append(name)
            if _named_ancestor(table, name) is not None:
                ancestor = name
                break
        out.append(
            {
                "group": "base" if r["source"].lower() in base else "modded",
                "class": r["class"],
                "display": r["display"],
                "source": r["source"],
                "ancestor": ancestor,
                "chain": chain,
                "catalogue_id": row["id"],
                "named": sorted(
                    t for t in tokens if len(t) >= SCAN_MIN and t in _blob(row)
                ),
            }
        )
    return out


def weapon_table() -> list:
    """The small-arms table: each row is an id and its alias keys."""
    out = []
    for line in WEAPON.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith('["'):
            continue
        p = re.findall(r'"([^"]*)"', s)
        if len(p) >= 3:
            out.append((p[0], [a for a in p[1].split("|") if a]))
    return out


def weapon_matcher(table: list, trace=None, type_entry=None):
    """The kernel's two layers: whole-token equality, then substring."""
    index: dict[str, tuple] = {}
    for wid, aliases in table:
        for a in aliases:
            index.setdefault(a, (wid, len(a)))

    def match(identity: str, display: str = ""):
        text = (identity + " " + display).strip()
        best, best_len = None, 0
        for token in re.split(r"[_\- .]+", text.lower()):
            hit = index.get(fold(token))
            if hit and hit[1] > best_len:
                best, best_len = hit[0], hit[1]
        if best:
            if trace is not None:
                trace.update(layer="alias", candidates=[best])
            return best
        key = fold(text)
        for wid, aliases in table:
            for a in aliases:
                if len(a) >= 4 and a in key and len(a) > best_len:
                    best, best_len = wid, len(a)
        if best:
            if trace is not None:
                trace.update(layer="closest", candidates=[best])
        elif type_entry is not None:
            if trace is not None:
                trace.update(layer="type", candidates=[type_entry])
            return type_entry
        return best

    return match


def install_dir(explicit: str | None) -> Path:
    """The Arma 3 install. `<install>/Addons` is the base game, by definition."""
    if explicit:
        root = Path(explicit).expanduser()
    elif os.environ.get(INSTALL_ENV):
        root = Path(os.environ[INSTALL_ENV]).expanduser()
    else:
        # The Steam library says where the game is. Ask it rather than
        # hard-code a path that holds on one machine only.
        from tools.proton import find_arma3

        found = find_arma3()
        if not found:
            raise SystemExit(
                f"no Arma 3 install found: set {INSTALL_ENV}=<dir>, pass --install, "
                "or make the Steam library readable"
            )
        root = Path(found["path"])
    if not (root / BASE_ADDONS).is_dir():
        raise SystemExit(
            f"{root} holds no {BASE_ADDONS}/ directory: the base game cannot be "
            "told from the mods, and neither can the coverage"
        )
    return root


def base_sources(install: Path) -> set[str]:
    """The PBO names the base game ships, lower case.

    Every other source in the scan is modded. The names are derived from the
    install, never listed here, and the tool records them in the baseline
    artefact so a reader without the install can still see the split.
    """
    names = {p.name.lower() for p in (install / BASE_ADDONS).glob("*.pbo")}
    if not names:
        raise SystemExit(
            f"no *.pbo under {install / BASE_ADDONS}: refusing to call every class modded"
        )
    return names


def slug(label: str) -> str:
    """The table name as an artefact slug: "small arms" -> "small_arms"."""
    return label.replace(" ", "_")


def figure_pct(res: dict) -> float:
    """The share of resolved classes sitting on an entry with a sourced figure.

    Every grade above `type` answers with a corpus entry, and every entry in
    these tables carries at least one published figure. A `type` entry names
    a kind and carries none, so the difference is the data coverage.
    """
    total = res["base"]["total"] + res["modded"]["total"]
    typed = res.get("grades", {}).get("type", 0)
    return (100.0 * (total - typed) / total) if total else 0.0


def pct(count: dict) -> float:
    return (100.0 * count["hit"] / count["total"]) if count["total"] else 0.0


def _decided(selected: list, match) -> list:
    """Every scored class and the entry the ladder reaches, or None.

    The measurement reports counts; the per-class decision is what a lock
    artefact needs, and deriving it here keeps one ladder behind both.
    """
    out = []
    for r in selected:
        row = match(r["class"], r["display"])
        # The vehicle and munition ladders return a row; the weapon kernel
        # returns the catalogue id.
        out.append(
            (
                r["class"],
                r["display"],
                (row["id"] if isinstance(row, dict) else row),
                r["source"],
            )
        )
    return sorted(out)


def grades(selected: list, factory) -> dict:
    """The grade that answered for every scored class, counted.

    `factory(trace)` returns a matcher bound to that trace, so each class
    is scored on a fresh trace and the layer that answered it is recorded
    without changing any decision.
    """
    out: dict[str, int] = {}
    for r in selected:
        trace: dict = {}
        factory(trace)(r["class"], r["display"])
        layer = trace.get("layer", "none")
        out[layer] = out.get(layer, 0) + 1
    return dict(sorted(out.items()))


def score(selected: list, match, base: set[str]) -> dict:
    """The coverage of one table, split by who DECLARES the class.

    A class the base game ships is base. Every other class is modded,
    including a mod class that inherits a base one: the catalogue still has
    to name the thing the player is looking at. The split is by the PBO that
    declares the class, so a mod nobody has written yet is measured the same
    way as one that is installed.
    """
    out = {
        "base": {"hit": 0, "total": 0},
        "modded": {"hit": 0, "total": 0},
        "unresolved": [],
    }
    for r in selected:
        group = "base" if r["source"].lower() in base else "modded"
        out[group]["total"] += 1
        if match(r["class"], r["display"]):
            out[group]["hit"] += 1
        else:
            out["unresolved"].append(
                {
                    "group": group,
                    "class": r["class"],
                    "display": r["display"],
                    "parent": r.get("parent") or "",
                    "source": r["source"],
                }
            )
    return out


def modded_gaps(res: dict) -> list:
    """The unresolved classes of one table that a MOD declares."""
    return [u for u in res["unresolved"] if u["group"] == "modded"]


def _order(row: dict) -> tuple:
    return (row["source"].lower(), row["class"].lower())


def _tidy(text: str) -> str:
    """One line per row, so a tab or a newline cannot break the record."""
    return " ".join(text.split())


def _taxonomy(scanned: list, kind: str, roots: set[str], chain) -> list:
    """The classes of one config kind whose chain passes one of `roots`.

    The root is the engine's own taxonomy, not a list of names, so a mod
    nobody has written yet is selected by the same rule as an installed
    one. Rows are deduplicated on class and display name, because several
    PBOs may declare the same class.
    """
    out, seen = [], set()
    for r in scanned:
        if r["kind"] != kind:
            continue
        key = (r["class"], r["display"])
        if key in seen:
            continue
        if not (set(chain(r["class"])) & roots):
            continue
        seen.add(key)
        out.append(r)
    return out


def _optic_rows(scanned: list, thermal_only: bool = False) -> list:
    """The CfgWeapons classes the config states are sights.

    An optic declares optics modes; a thermal sight further declares a
    thermal palette or the thermal vision mode in one of them. The scan
    holds both, so the denominator is the config's statement, not a
    classname pattern.
    """
    out, seen = [], set()
    for r in scanned:
        if r["kind"] != "CfgWeapons" or not r.get("optics_modes"):
            continue
        if thermal_only and not r.get("thermal_mode"):
            continue
        key = (r["class"], r["display"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _device_reason(cls: str, display: str, table: list) -> str:
    """Why the device ladder answers nothing for one class."""
    trace: dict = {}
    device_matcher(table, trace=trace)(cls, display)
    if trace.get("layer"):
        return f"tied at the {trace['layer']} layer"
    if display.startswith("$"):
        return "display is a stringtable key the scan cannot localise"
    return "no published device identity in the identity text"


def _clothing_reason(row: dict, category: str, table: list, chain, match) -> str:
    """Why the item-mass resolver names no family for one class.

    The shapes are the ones the corpus leaves: an identity the scan cannot
    read, a variant that only repeats a resolved parent, a family of
    another slot, or no published family at all.
    """
    display = row["display"]
    if display.startswith("$"):
        return "display is a stringtable key the scan cannot localise"
    for ancestor in list(chain(row["class"]))[1:]:
        if match(ancestor, ""):
            return "variant text of a resolved parent"
    hay = (row["class"] + " " + display).lower()
    other = [r for r in table if r["family"] in hay]
    if other:
        return f"names the {other[0]['family']!r} {other[0]['category']} family, not {category}"
    return f"no published {category} family in the identity text"


def measure(scanned: list, base: set[str]) -> dict:
    """Walk the scan through every matcher, table by table.

    Returns {"tables": {slug: {label, base, modded, unresolved, excluded}},
    "excluded", "emplacements", "other"}. `excluded` names every armament
    class dropped as equipment that is not a munition, by kind, and
    `emplacements` holds the ground classes dropped as weapon positions, so
    no exclusion is silent.
    """
    parent = {}
    for r in scanned:
        if r["kind"] == "CfgVehicles" and r["parent"] and r["class"] not in parent:
            parent[r["class"]] = r["parent"]

    def chain_of(cls: str) -> list[str]:
        seen, cur, chain = set(), cls, []
        while cur and cur not in seen:
            seen.add(cur)
            chain.append(cur.lower())
            cur = parent.get(cur)
        return chain

    def chain_orig(cls: str) -> list[str]:
        """The same chain with the case the config declares, for evidence."""
        seen, cur, chain = set(), cls, []
        while cur and cur.lower() not in seen:
            seen.add(cur.lower())
            chain.append(cur)
            cur = parent.get(cur)
        return chain

    def ancestors(cls: str) -> list[str]:
        """The class's config ancestors, nearest first."""
        return chain_orig(cls)[1:]

    def kind(chain: list[str]):
        if any(c in AIR for c in chain):
            return "air"
        if any(c in LAND for c in chain):
            return "land"
        return None

    named, seen = [], set()
    for r in scanned:
        if r["kind"] != "CfgVehicles":
            continue
        dn = r["display"]
        if not dn or dn.startswith("$") or PROP.search(dn):
            continue
        key = (r["class"], dn)
        if key in seen:
            continue
        seen.add(key)
        named.append(r)

    emplacements: list[dict] = []
    ground, air = [], []
    for r in named:
        chain = chain_of(r["class"])
        table = kind(chain)
        if table is None:
            continue
        if table == "land" and STATIC_WEAPON in chain:
            emplacements.append(r)
            continue
        (air if table == "air" else ground).append(r)

    tables: dict[str, dict] = {}
    for sel, path, label, dropped in (
        (ground, VEHICLE, "vehicles", emplacements),
        (air, AIRCRAFT, "aircraft", []),
    ):
        kinds, fallback = (
            (VEHICLE_KINDS, VEHICLE_FALLBACK)
            if label == "vehicles"
            else (AIRCRAFT_KINDS, AIRCRAFT_FALLBACK)
        )

        def engine_kind_for(cls: str, kinds=kinds, fallback=fallback) -> str:
            return _engine_kind(chain_of(cls), kinds, fallback)

        table = rows(path)
        families = family_rows(path)
        plain = matcher(table, families=families)
        match = (
            matcher(table, ancestors, families=families, type_entry=engine_kind_for)
            if label == "vehicles"
            else matcher(table, families=families, type_entry=engine_kind_for)
        )
        tables[slug(label)] = {
            "label": label,
            **score(sel, match, base),
            "decided": _decided(sel, match),
            "grades": grades(
                sel,
                lambda tr, t=table, f=families, k=engine_kind_for, a=(
                    ancestors if label == "vehicles" else None
                ): matcher(t, a, trace=tr, families=f, type_entry=k),
            ),
            "inherited": (
                ancestry_closures(sel, table, plain, match, ancestors, base)
                if label == "vehicles"
                else []
            ),
            "excluded": {STATIC_WEAPON_KIND: len(dropped)} if dropped else {},
        }

    # ── Small arms ────────────────────────────────────────────────────────
    wpar = {}
    for r in scanned:
        if r["kind"] == "CfgWeapons" and r["parent"] and r["class"] not in wpar:
            wpar[r["class"]] = r["parent"]

    def wchain(cls: str) -> list:
        seen, cur, out = set(), cls, []
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur.lower())
            cur = wpar.get(cur)
        return out

    match_w = weapon_matcher(weapon_table())
    small, carried, armament, wseen = [], [], [], set()
    excluded: dict[str, list] = defaultdict(list)
    other = 0
    for r in scanned:
        # A firearm declares what it feeds from; a uniform does not.
        if r["kind"] != "CfgWeapons" or not r.get("feeds"):
            continue
        dn = r["display"]
        if not dn or dn.startswith("$"):
            continue
        key = (r["class"], dn)
        if key in wseen:
            continue
        wseen.add(key)
        # A BASE CLASS is scaffolding, not a weapon anyone is issued: its
        # display name is whatever the mod left there, often a UI string.
        if BASE_CLASS.search(r["class"]):
            other += 1
            continue
        chain = set(wchain(r["class"]))
        if chain & SMALL_ARMS_ROOT or SMALL_ARMS_PREFIX.search(r["class"]):
            small.append(r)
        elif chain & CARRIED_LAUNCHER_ROOT:
            carried.append(r)
        elif chain & VEHICLE_ARMAMENT_ROOT:
            # The runtime screen reads a folded substring, so a classname
            # that joins its words with an underscore is caught by the
            # second test and not by the first.  The measurement and the
            # runtime then agree.
            equipment = not is_munition(dn) or screened(dn, r["class"]) != ""
            if not equipment:
                armament.append(r)
            else:
                excluded[kind_of(dn) or screened(dn, r["class"])].append(
                    (r["class"], dn)
                )
                other += 1
        else:
            # A store, a countermeasure or a pod. Not a weapon that fires
            # a projectile, so no catalogue of weapons should be scored
            # against it.
            other += 1

    # Vehicle armament is scored against the MUNITION catalogue, which is
    # the corpus written to name it; the small-arms corpus holds a rifling
    # twist and was never meant to.
    match_m = (
        matcher(
            munition_rows(MUNITION_TABLE),
            families=munition_family_rows(MUNITION_TABLE),
            type_entry="munition",
        )
        if MUNITION_TABLE.exists()
        else None
    )
    for label, sel in (
        ("small arms", small),
        ("carried launchers", carried),
        ("vehicle armament", armament),
    ):
        if not sel:
            continue
        kind = (
            "munition"
            if label == "vehicle armament"
            else ("launcher" if label == "carried launchers" else "small arm")
        )
        if label == "vehicle armament" and match_m:
            factory = lambda tr, k=kind: matcher(
                munition_rows(MUNITION_TABLE), trace=tr, type_entry=k
            )
            pick = match_m
        else:
            factory = lambda tr, k=kind: weapon_matcher(
                weapon_table(), trace=tr, type_entry=k
            )
            pick = weapon_matcher(weapon_table(), type_entry=kind)
        # The armament table's denominator is what the shared kind filter
        # left in it, so the kinds it dropped belong in its record.
        kept = (
            {kind: len(members) for kind, members in excluded.items()}
            if label == "vehicle armament"
            else {}
        )
        tables[slug(label)] = {
            "label": label,
            **score(sel, pick, base),
            "excluded": kept,
            "decided": _decided(sel, pick),
            "grades": grades(sel, factory),
        }

    # ── Night vision devices ──────────────────────────────────────────────
    # The NVG rows are scored against the engine taxonomy: a CfgWeapons
    # class whose chain passes the NVGoggles root. The optic and thermal
    # rows of the same table are NOT scored here, because the scan holds no
    # ItemInfo type and no OpticsModes, and those are the only evidence
    # that tells an optic from a compass. A denominator invented from the
    # classname would measure the name, not the item.
    for label, family, type_name, selected in (
        (
            "night vision devices",
            "nvg",
            "night-vision device",
            _taxonomy(scanned, "CfgWeapons", {NVG_ROOT}, wchain),
        ),
        ("thermal optics", "thermal", "thermal optic", _optic_rows(scanned, True)),
        ("optics", "optic", "optic", _optic_rows(scanned, False)),
    ):
        if not selected:
            continue
        dtable = device_rows(DEVICE, family)
        match_d = device_matcher(
            dtable, type_entry=type_name, ancestry=lambda c: wchain(c)[1:]
        )
        reasons = defaultdict(int)
        for r in selected:
            if match_d(r["class"], r["display"]) is None:
                reasons[_device_reason(r["class"], r["display"], dtable)] += 1
        tables[slug(label)] = {
            "label": label,
            **score(selected, match_d, base),
            "excluded": {},
            "decided": _decided(selected, match_d),
            "grades": grades(
                selected,
                lambda tr, t=dtable, n=type_name: device_matcher(
                    t, trace=tr, type_entry=n, ancestry=lambda c: wchain(c)[1:]
                ),
            ),
            "reasons": dict(reasons),
        }

    # ── Clothing and load carriage ────────────────────────────────────────
    # The item-mass resolver keys on the slot category the caller states,
    # so each table is measured with its own category, exactly as a caller
    # that holds the slot would call it. The band fallback below the family
    # table reads the live config mass, which the scan does not hold; a
    # class the family table cannot name is reported open, not guessed.
    eq_table = equipment_rows(ITEM_MASS) if ITEM_MASS.exists() else []
    for label, category, roots, kind, chain in (
        ("uniforms", "uniform", {UNIFORM_ROOT}, "CfgWeapons", wchain),
        ("vests", "vest", VEST_ROOTS, "CfgWeapons", wchain),
        ("helmets", "helmet", {HELMET_ROOT}, "CfgWeapons", wchain),
        ("rucksacks", "rucksack", {BACKPACK_ROOT}, "CfgVehicles", chain_of),
    ):
        selected = _taxonomy(scanned, kind, roots, chain)
        if not selected:
            continue
        match_e = equipment_matcher(
            eq_table, category, type_entry=category, ancestry=lambda c: chain(c)[1:]
        )
        reasons = defaultdict(int)
        for r in selected:
            if match_e(r["class"], r["display"]) is not None:
                continue
            reasons[_clothing_reason(r, category, eq_table, chain, match_e)] += 1
        tables[slug(label)] = {
            "label": label,
            **score(selected, match_e, base),
            "excluded": {},
            "decided": _decided(selected, match_e),
            "grades": grades(
                selected,
                lambda tr, c=category, ch=chain: equipment_matcher(
                    eq_table, c, trace=tr, type_entry=c,
                    ancestry=lambda x: ch(x)[1:],
                ),
            ),
            "reasons": dict(reasons),
        }

    return {
        "tables": tables,
        "excluded": excluded,
        "emplacements": emplacements,
        "other": other,
    }


def report(tables: dict) -> None:
    """Print base, modded and combined coverage for every table."""
    for res in tables.values():
        base, modded = res["base"], res["modded"]
        both = {
            "hit": base["hit"] + modded["hit"],
            "total": base["total"] + modded["total"],
        }
        print(
            f"{res['label']}: base {base['hit']}/{base['total']} ({pct(base):.1f}%), "
            f"modded {modded['hit']}/{modded['total']} ({pct(modded):.1f}%), "
            f"all {both['hit']}/{both['total']} ({pct(both):.1f}%)"
        )
        print(
            f"    data coverage {figure_pct(res):.1f}% "
            f"({res['base']['total'] + res['modded']['total'] - res.get('grades', {}).get('type', 0)}"
            f"/{res['base']['total'] + res['modded']['total']} on a sourced entry)"
        )
        for reason, count in sorted(res.get("reasons", {}).items()):
            print(f"    {count:4d} open: {reason}")


def print_evidence(result: dict) -> None:
    """Name every class the measurement drops, and why.

    Coverage must not rise by excluding a class in silence, so the excluded
    classes are listed by the KIND of equipment they are, from the shared
    filter in tools/validation/munition_kind.py.
    """
    other = result["other"]
    excluded = result["excluded"]
    emplacements = result.get("emplacements", [])
    print(f"  ({other} CfgWeapons entries are stores, countermeasures or pods)")
    if emplacements:
        named = sorted({r["class"] for r in emplacements})
        print(
            f"  {len(emplacements)} ground classes are {STATIC_WEAPON_KIND}, "
            "not vehicles:"
        )
        print(f"    {', '.join(named)}")
    if excluded:
        total = sum(len(v) for v in excluded.values())
        print(f"  {total} armament classes are equipment, not munitions:")
        for kind, members in sorted(excluded.items()):
            sample = ", ".join(sorted({c for c, _dn in members})[:4])
            print(f"    {len(members):3d}  {kind:<20} e.g. {sample}")


def print_inheritance(tables: dict) -> None:
    """Name every class the inherited rung closed, with the chain behind it.

    The closure is a claim about engine ancestry, so the evidence is the
    config chain and the ancestor's entry. A reader can check both.
    """
    for res in tables.values():
        closed = res.get("inherited") or []
        if not closed:
            continue
        print(f"  {len(closed)} {res['label']} classes resolved by engine ancestry:")
        for row in sorted(closed, key=_order):
            chain = " <- ".join(row["chain"])
            print(f"    {row['class']} = {row['catalogue_id']}  ({chain})")


def print_gaps(tables: dict) -> None:
    """The unnamed display names of every table, most-used first."""
    for res in tables.values():
        gaps: dict[str, list] = defaultdict(list)
        for row in res["unresolved"]:
            gaps[row["display"]].append(row["class"])
        if not gaps:
            continue
        print(f"{res['label']}: {len(gaps)} unnamed display names, most-used first:")
        for dn, cls in sorted(gaps.items(), key=lambda kv: -len(kv[1]))[:40]:
            print(f"    {len(cls):3d}  {dn}")


def print_modded(tables: dict) -> None:
    """Every unresolved MODDED class, as a tab-separated record.

    The closing work needs the class to fix, the name the player sees, what
    the mod inherits and the PBO that declares it, so one line carries all
    four and a consumer can read it with cut(1).
    """
    for res in tables.values():
        gaps = modded_gaps(res)
        print(f"# {res['label']}: {len(gaps)} unresolved modded classes")
        print("# class\tdisplay\tparent\tsource")
        for row in sorted(gaps, key=_order):
            print(
                f"{row['class']}\t{_tidy(row['display'])}\t"
                f"{row['parent']}\t{row['source']}"
            )


def write_gaps(directory: Path, tables: dict) -> None:
    """Write one gap file per table: data/coverage/modded_gaps_<table>.txt.

    The shape is the one `--modded` prints: a header of `#` comment lines,
    then one tab-separated record per unresolved modded class -
    class, display, parent, source. Rows are ordered by source then class, so
    a rewrite of the same content is byte-identical and a worker can diff it.
    """
    directory.mkdir(parents=True, exist_ok=True)
    for name, res in tables.items():
        gaps = modded_gaps(res)
        lines = [
            f"# modded match coverage gaps: {res['label']}",
            f"# {len(gaps)} unresolved of {res['modded']['total']} modded classes "
            f"({pct(res['modded']):.1f}% resolved)",
            "# class\tdisplay\tparent\tsource",
        ]
        for row in sorted(gaps, key=_order):
            lines.append(
                f"{row['class']}\t{_tidy(row['display'])}\t"
                f"{row['parent']}\t{row['source']}"
            )
        (directory / f"modded_gaps_{name}.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )


def write_baseline(
    path: Path,
    *,
    scan: Path,
    install: Path,
    base: set[str],
    scan_rows: int,
    measured_rows: int,
    tables: dict,
) -> None:
    """Record the modded coverage, with the provenance to reproduce it.

    The base PBO list is written here, so the split can be read - and the
    measurement reproduced - without the game install to hand.
    """
    payload = {
        "schema": "aee.match_coverage.baseline/1",
        "provenance": {
            "generated": datetime.date.today().isoformat(),
            "scan": str(scan),
            "scan_sha256": hashlib.sha256(scan.read_bytes()).hexdigest(),
            "scan_rows": scan_rows,
            "measured_rows": measured_rows,
            "install": str(install),
            "base_addons": str(install / BASE_ADDONS),
            "base_pbo_count": len(base),
            "base_pbos": sorted(base),
            "measured_tables": list(MEASURED_TABLES),
            "method": (
                "A class is BASE when the PBO that declares it is in the base "
                "game's Addons directory, and MODDED otherwise. Rows come from "
                "the binarised configs only. Regenerate with "
                "tools/report_match_coverage.py --write-gaps --write-baseline."
            ),
            # The count is derived from the measurement, so it cannot drift
            # from the gap list it describes.
            "known_unresolvable": {
                name: {
                    "unresolved": len(modded_gaps(res)),
                    "note": KNOWN_UNRESOLVABLE.get(name, ""),
                }
                for name, res in tables.items()
            },
        },
        "tables": {
            name: {
                "label": res["label"],
                "base": {**res["base"], "pct": round(pct(res["base"]), 2)},
                "modded": {**res["modded"], "pct": round(pct(res["modded"]), 2)},
                "unresolved_modded": len(modded_gaps(res)),
                "inherited": res.get("inherited", []),
                "excluded": res.get("excluded", {}),
                "grades": res.get("grades", {}),
                "figure_graded": (
                    res["base"]["total"]
                    + res["modded"]["total"]
                    - res.get("grades", {}).get("type", 0)
                ),
                "figure_pct": round(figure_pct(res), 2),
                "reasons": res.get("reasons", {}),
            }
            for name, res in tables.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scan", type=Path, help="the scan_game_classes.py JSONL scan")
    ap.add_argument(
        "--install",
        help=f"Arma 3 install directory. Default: ${INSTALL_ENV}, else the "
        "install the Steam library points at",
    )
    ap.add_argument(
        "--modded",
        action="store_true",
        help="list every unresolved modded class: class, display, parent, source",
    )
    ap.add_argument("--gaps", action="store_true", help="list unnamed display names")
    ap.add_argument(
        "--write-gaps",
        type=Path,
        metavar="DIR",
        help="write DIR/modded_gaps_<table>.txt for every table",
    )
    ap.add_argument(
        "--write-baseline",
        type=Path,
        metavar="PATH",
        help="write the modded coverage baseline and its provenance to PATH",
    )
    args = ap.parse_args()

    if not args.scan.is_file():
        raise SystemExit(
            f"no scan at {args.scan}: run tools/scan_game_classes.py first"
        )
    raw = [
        json.loads(line)
        for line in args.scan.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # A raw config.cpp is not preprocessed by the scanner, so a macro-built
    # config can mis-attach a display name. Measure on binarised configs.
    scanned = [r for r in raw if r.get("fmt") == "bin"]

    install = install_dir(args.install)
    base = base_sources(install)

    result = measure(scanned, base)
    tables = result["tables"]
    report(tables)
    print_evidence(result)
    print_inheritance(tables)
    if args.gaps:
        print_gaps(tables)
    if args.modded:
        print_modded(tables)
    if args.write_gaps:
        write_gaps(args.write_gaps, tables)
    if args.write_baseline:
        write_baseline(
            args.write_baseline,
            scan=args.scan,
            install=install,
            base=base,
            scan_rows=len(raw),
            measured_rows=len(scanned),
            tables=tables,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
