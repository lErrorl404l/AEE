#!/usr/bin/env python3
"""Measure the matchers against the game content actually installed.

Coverage is not a guess: tools/scan_game_classes.py reads what the game
and the installed mods declare, and this walks that scan through the same
ladder the runtime matcher uses, so the number is what a player would get.

It also prints the gap list - the real vehicles and aircraft that appear in
the content but that no catalogue entry can name - which is the worklist
for capturing new entries.

Run:
    OUT=/tmp/all.jsonl python3 tools/scan_game_classes.py \\
        "<game>/Addons" "<workshop>/107410"
    python3 tools/report_match_coverage.py /tmp/all.jsonl --gaps
"""

from __future__ import annotations

import argparse
import json
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
    "launchercore", "cannoncore", "missilelauncher", "rocketpods",
    "bombcore", "mgun", "mguncore", "autocannon", "gatlingcore",
    "bomblauncher", "rocketlauncher",
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
LAND = {"car", "tank", "truck", "motorcycle", "landvehicle", "wheeled_apc_f",
        "apc_tracked_01_base_f"}
AIR = {"air", "helicopter", "plane", "uav"}
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


def matcher(table: list):
    """The runtime ladder: exact class, alias, keyword, then closest."""

    def match(text: str):
        key = fold(text)
        if not key:
            return None
        # The runtime splits the identity into TOKENS for the alias layer,
        # because a curated alias is a whole designation and must match a
        # whole word of the query: "S-5" folds to "s5", which the folded
        # whole identity never equals. The mirror has to split the same
        # way or it under-reports every short alias.
        tokens = {fold(t) for t in re.split(r"[ _\-.]+", text) if fold(t)}
        hit = [r for r in table if key in r["classes"]]
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
                len(w) >= SCAN_MIN and w in key
                for w in (r["keywords"] + r["aliases"])
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
                    best_score, score, r, count, longest, False
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
        return None

    return match


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

    def match(identity: str):
        best, best_len = None, 0
        for token in re.split(r"[_\- .]+", identity.lower()):
            hit = index.get(fold(token))
            if hit and hit[1] > best_len:
                best, best_len = hit[0], hit[1]
        if best:
            return best
        key = fold(identity)
        for wid, aliases in table:
            for a in aliases:
                if len(a) >= 4 and a in key and len(a) > best_len:
                    best, best_len = wid, len(a)
        return best

    return match


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scan", type=Path)
    ap.add_argument("--gaps", action="store_true")
    args = ap.parse_args()

    scanned = [
        json.loads(line)
        for line in args.scan.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    # A raw config.cpp is not preprocessed by the scanner, so a macro-built
    # config can mis-attach a display name. Measure on binarised configs.
    scanned = [r for r in scanned if r.get("fmt") == "bin"]

    parent = {}
    for r in scanned:
        if r["kind"] == "CfgVehicles" and r["parent"] and r["class"] not in parent:
            parent[r["class"]] = r["parent"]

    def kind(cls: str):
        seen, cur, chain = set(), cls, []
        while cur and cur not in seen:
            seen.add(cur)
            chain.append(cur.lower())
            cur = parent.get(cur)
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

    for want, path, label in (
        ("land", VEHICLE, "vehicles"),
        ("air", AIRCRAFT, "aircraft"),
    ):
        match = matcher(rows(path))
        sel = [r for r in named if kind(r["class"]) == want]
        gaps = defaultdict(list)
        hit = 0
        for r in sel:
            if match(r["class"] + " " + r["display"]):
                hit += 1
            else:
                gaps[r["display"]].append(r["class"])
        pct = (100 * hit / len(sel)) if sel else 0
        print(f"{label}: {hit}/{len(sel)} ({pct:.1f}%) named by the catalogue")
        if args.gaps and gaps:
            print(f"  {len(gaps)} unnamed display names, most-used first:")
            for dn, cls in sorted(gaps.items(), key=lambda kv: -len(kv[1]))[:40]:
                print(f"    {len(cls):3d}  {dn}")

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

    print(f"  ({other} CfgWeapons entries are stores, countermeasures or pods)")
    if excluded:
        total = sum(len(v) for v in excluded.values())
        print(f"  {total} armament classes are equipment, not munitions:")
        for kind, members in sorted(excluded.items()):
            sample = ", ".join(sorted({c for c, _dn in members})[:4])
            print(f"    {len(members):3d}  {kind:<20} e.g. {sample}")
    # Vehicle armament is scored against the MUNITION catalogue, which is
    # the corpus written to name it; the small-arms corpus holds a rifling
    # twist and was never meant to.
    match_m = (
        matcher(munition_rows(MUNITION_TABLE))
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
        pick = match_m if (label == "vehicle armament" and match_m) else match_w
        gaps = defaultdict(list)
        hit = 0
        for r in sel:
            if pick(r["class"] + " " + r["display"]):
                hit += 1
            else:
                gaps[r["display"]].append(r["class"])
        print(f"{label}: {hit}/{len(sel)} ({100 * hit / len(sel):.1f}%) named by the catalogue")
        if args.gaps and gaps:
            print(f"  {len(gaps)} unnamed display names, most-used first:")
            for dn, cls in sorted(gaps.items(), key=lambda kv: -len(kv[1]))[:200]:
                print(f"    {len(cls):3d}  {dn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
