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
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).parents[1]
VEHICLE = REPO / "addons/vehicles/functions/fnc_getVehicleMatch.sqf"
AIRCRAFT = REPO / "addons/flight/functions/fnc_getAircraftMatch.sqf"
WEAPON = REPO / "addons/ballistics/functions/fnc_getWeaponData.sqf"

# CfgWeapons also holds vehicle armament. The weapon catalogue is a
# SMALL-ARMS catalogue, so munitions are counted apart rather than scored
# against a table that was never meant to name them.
VEHICLE_ARMAMENT_ROOT = {
    "cannoncore", "missilelauncher", "rocketpods", "bombcore", "mgun",
    "autocannon", "gatlingcore", "bomblauncher", "rocketlauncher",
}
MUNITION = re.compile(
    r"rocket|missile|bomb|gbu|agm|aim-|flare|dagr|apkws|crv7|torpedo|shell"
    r"|railgun|laser|cannon|pods?\b"
    # Stores and countermeasures also live in CfgWeapons and declare
    # magazines, but none of them is a small arm either.
    r"|chaff|irjam|jammer|napalm|\bsdb\b|\blgb\b|\bsraw\b|gas\b"
    r"|agent|incendiary|cluster|decoy|smoke ?(launcher|generator)",
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


def matcher(table: list):
    """The runtime ladder: exact class, alias, keyword, then closest."""

    def match(text: str):
        key = fold(text)
        if not key:
            return None
        hit = [r for r in table if key in r["classes"]]
        if len(hit) == 1:
            return hit[0]
        hit = [r for r in table if key in r["aliases"]]
        if len(hit) == 1:
            return hit[0]
        hit = [
            r
            for r in table
            if any(len(w) >= SCAN_MIN and w in key for w in r["keywords"])
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
    small, armament, wseen = [], [], set()
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
        is_armament = any(
            c in VEHICLE_ARMAMENT_ROOT for c in wchain(r["class"])
        ) or bool(MUNITION.search(dn))
        (armament if is_armament else small).append(r)

    for label, sel in (("small arms", small), ("vehicle armament", armament)):
        if not sel:
            continue
        gaps = defaultdict(list)
        hit = 0
        for r in sel:
            if match_w(r["class"] + " " + r["display"]):
                hit += 1
            else:
                gaps[r["display"]].append(r["class"])
        print(f"{label}: {hit}/{len(sel)} ({100 * hit / len(sel):.1f}%) named by the catalogue")
        if args.gaps and gaps:
            print(f"  {len(gaps)} unnamed display names, most-used first:")
            for dn, cls in sorted(gaps.items(), key=lambda kv: -len(kv[1]))[:20]:
                print(f"    {len(cls):3d}  {dn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
