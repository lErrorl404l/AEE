#!/usr/bin/env python3
"""Equipment classifier exhaustiveness harness (issue #119).

Mirrors the keyword tiers in fnc_getEquipmentProperties.sqf and runs
the ENTIRE known inventory (vanilla + RHS AFRF/USAF/GREF) through them.
Reports every classname that falls through to the default tier - those
are families whose keyword signal the classifier does not yet cover.

The exhaustive principle: if the family signal exists in the classname
(helmet/vest/pack type + era + protection), the classifier must catch
it.  Only genuinely generic names (no signal) may hit default.

Run: python3 tools/tests/classify_inventory.py
"""

import re
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (
    REPO / "addons/physiology/functions/clothing/fnc_getEquipmentProperties.sqf"
).read_text(encoding="utf-8")
INV = Path("/tmp/equip_extract/inventory.txt")


# ─── Extract the keyword lists from the SQF switch cases ───────────────────
# Each case is `case (_x find "kw" >= 0 || ...): { [tier] };`
# We collect the (keywords, tier) pairs per slot so the mirror classifies
# exactly like the SQF, in the same order.
def extract_tiers(slot_var):
    """Return ordered [(keywords, tier_string)] from the switch on _<slot>."""
    # find the switch block for the slot
    m = re.search(
        rf"{slot_var} = switch \(true\) do \{{(.*?)\n    \}};",
        FNC,
        re.S,
    )
    if not m:
        raise SystemExit(f"switch block for _{slot_var} not found")
    body = m.group(1)
    tiers = []
    for case in re.finditer(r"case\s*\((.*?)\):\s*\{(\s*\[[^\]]+\]\s*)\};", body, re.S):
        cond, tier = case.group(1), case.group(2)
        kws = re.findall(r'find "([^"]+)"', cond)
        tiers.append((kws, re.sub(r"\s+", " ", tier).strip()))
    return tiers


def classify(name, tiers):
    n = name.lower()
    for kws, tier in tiers:
        if any(k in n for k in kws):
            return tier
    return "DEFAULT"


def load_inventory():
    sections, cur = {}, None
    for line in INV.read_text(encoding="utf-8").splitlines():
        if line.startswith("== "):
            cur = line.strip("= ").strip()
            sections[cur] = []
        elif cur and line.strip():
            sections[cur].append(line.strip())
    return sections


def main():
    inv = load_inventory()
    helmet_tiers = extract_tiers("helmet")
    vest_tiers = extract_tiers("vest")
    pack_tiers = extract_tiers("pack")

    print(
        f"SQF tiers: helmet={len(helmet_tiers)} vest={len(vest_tiers)} pack={len(pack_tiers)}\n"
    )

    failures = 0
    for slot, tiers in [
        ("HELMETS", helmet_tiers),
        ("VESTS", vest_tiers),
        ("PACKS", pack_tiers),
    ]:
        names = inv[slot]
        hits = {}
        defaults = []
        for n in names:
            t = classify(n, tiers)
            hits[t] = hits.get(t, 0) + 1
            if t == "DEFAULT":
                defaults.append(n)
        print(f"── {slot} ({len(names)} items) ──")
        for tier, count in sorted(hits.items(), key=lambda x: -x[1]):
            print(f"   {count:4d}  {tier[:60]}")
        if defaults:
            failures += len(defaults)
            print(f"   FALL-THROUGH ({len(defaults)}):")
            for d in sorted(defaults):
                print(f"     - {d}")
        print()
    print(f"TOTAL FALL-THROUGH: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
