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


def rows(path: Path) -> list:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith('["'):
            continue
        p = re.findall(r'"([^"]*)"', s)
        if len(p) <= 6:
            continue
        out.append(
            {
                "id": p[0],
                "classes": [x for x in p[4].split("|") if x],
                "aliases": [x for x in p[5].split("|") if x],
                "keywords": [x for x in p[6].split("|") if x],
            }
        )
    return out


def munition_rows(path: Path) -> list:
    """The munition table: id, type, classes, aliases, keywords."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith('["'):
            continue
        p = re.findall(r'"([^"]*)"', s)
        if len(p) <= 4:
            continue
        out.append(
            {
                "id": p[0],
                "classes": [x for x in p[2].split("|") if x],
                "aliases": [x for x in p[3].split("|") if x],
                "keywords": [x for x in p[4].split("|") if x],
            }
        )
    return out


def matcher(table: list, ancestry=None):
    """The runtime ladder: exact class, alias, keyword, closest, then the
    inherited rung.

    `ancestry` is the engine parent chain, a callable that returns a class's
    ancestors nearest first as classnames. Only the vehicle table is given
    one, because only its runtime matcher walks the chain.
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
            return hit[0]
        hit = [r for r in table if tokens & set(r["aliases"])]
        if len(hit) == 1:
            return hit[0]
        # The runtime's keyword layer scans the aliases too, so a curated
        # alias long enough to be a substring is still a way in.
        hit = [
            r
            for r in table
            if any(
                len(w) >= SCAN_MIN and w in key for w in (r["keywords"] + r["aliases"])
            )
        ]
        if len(hit) == 1:
            return hit[0]
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
            return best
        # Nothing in the class text names an entry. The engine ancestry is
        # the last evidence there is, and it is used only when the class
        # text names the ancestor's entry (see inherited_row).
        if ancestry is not None and cls:
            row, _ancestor = inherited_row(table, cls, tokens, ancestry)
            return row
        return None

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
        if row is None:
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


def weapon_matcher(table: list):
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
            return best
        key = fold(text)
        for wid, aliases in table:
            for a in aliases:
                if len(a) >= 4 and a in key and len(a) > best_len:
                    best, best_len = wid, len(a)
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


def pct(count: dict) -> float:
    return (100.0 * count["hit"] / count["total"]) if count["total"] else 0.0


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
        table = rows(path)
        plain = matcher(table)
        match = matcher(table, ancestors) if label == "vehicles" else plain
        tables[slug(label)] = {
            "label": label,
            **score(sel, match, base),
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
        matcher(munition_rows(MUNITION_TABLE)) if MUNITION_TABLE.exists() else None
    )
    for label, sel in (
        ("small arms", small),
        ("carried launchers", carried),
        ("vehicle armament", armament),
    ):
        if not sel:
            continue
        pick = match_m if (label == "vehicle armament" and match_m) else match_w
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
            "method": (
                "A class is BASE when the PBO that declares it is in the base "
                "game's Addons directory, and MODDED otherwise. Rows come from "
                "the binarised configs only. Regenerate with "
                "tools/report_match_coverage.py --write-gaps --write-baseline."
            ),
            # The platform worker classified the gaps that survive the corpus.
            # They are expected to stay unresolved, so a future reader must
            # not read them as regression.
            "known_unresolvable": {
                "vehicle_modded": {
                    "retexture_of_an_unmapped_ancestor": 0,
                    "different_maker_than_ancestor": 1,
                    "family_label_over_a_generic_class": 1,
                    "armafpv_drone_no_published_designation": 8,
                    "note": (
                        "Seventeen modded vehicle classes closed by engine "
                        "ancestry (433/435): the seven Offroad re-uses and the "
                        "ten Project OPFOR KAMAZ retextures, which descend from "
                        "the Zamak and close on it now that the Zamak variants "
                        "are bound to kamaz_4310. Two remain. "
                        "LOP_Nissan_PKM_base names a Nissan over the ancestor's "
                        "Toyota entry, and rhsusf_fmtv_base names a family over "
                        "the engine's Car class. The rung refuses both rather "
                        "than answer a different vehicle. The eight aircraft "
                        "gaps are ArmaFPV FPV drones. None is a failure."
                    ),
                }
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
