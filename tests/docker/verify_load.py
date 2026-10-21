#!/usr/bin/env python3
"""Verify the headless load gate log.

Reads the captured server log from tools/docker_test.sh --load and fails when:

- the server never reached "Game started", or the probe never printed DONE
- a matcher function was not compiled
- the log holds an Error, Script error, Undefined variable or Cannot load line
- a rung case answered weaker than the rung it is expected to answer at
- a ladder rung was never exercised, so a matcher regression could pass unseen

Exit 0 only when every check passes. The mission only reports what the
matchers returned; this file owns the verdict, so a corpus change never needs
an edit to the mission.
"""

import re
import sys

# The ladder, strongest first. A weaker answer than the expected rung is a
# regression; a stronger answer is an improvement and passes.
RANK = {
    "exact_class": 1,
    "alias": 2,
    "keyword": 3,
    "inheritance": 4,
    "closest": 5,
    "inherited": 6,
    "family": 7,
    "type": 8,
}
ABSENT = 99
TYPE_RANK = RANK["type"]

# Every rung the gate must see answered at least once.
REQUIRED_RUNGS = (
    "exact_class",
    "alias",
    "keyword",
    "closest",
    "inherited",
    "family",
    "type",
)

ERROR_PATTERN = re.compile(r"\bError\b|Script error|Undefined variable|Cannot load")
RUNG_LINE = re.compile(
    r"\[LOAD-GATE\] RUNG matcher=(\S+) want=(\S+) query=(.*?) answered=(\S+) id=(.*)$"
)
MASS_LINE = re.compile(r"\[LOAD-GATE\] MASS item=(\S+) kg=(\S+)$")

# A family item answers with a published figure. An item the research does
# not hold answers 0.
MASS_EXPECT = {
    "FirstAidKit": "positive",
    "U_B_CombatUniform_mcam": "positive",
    "AEE_Unknown_zzz_item": "zero",
}


def check(path):
    """Return a list of failure strings. An empty list means the log passed."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    lines = text.splitlines()
    failures = []

    if "Game started." not in text:
        failures.append('the server never reached "Game started."')
    if "[LOAD-GATE] DONE" not in text:
        failures.append("the load gate probe never printed DONE")
    if "[LOAD-GATE] FUNCS present=5 missing=0" not in text:
        failures.append("a matcher function was not compiled")

    for number, line in enumerate(lines, 1):
        if ERROR_PATTERN.search(line):
            failures.append(f"line {number}: {line.strip()}")

    seen_rungs = set()
    cases = 0
    for line in lines:
        match = RUNG_LINE.search(line)
        if not match:
            continue
        cases += 1
        matcher, want, query, answered, _ident = match.groups()
        if want == "none":
            if answered != "none":
                failures.append(
                    f"{matcher} q={query}: expected no answer, answered {answered}"
                )
            continue
        if answered not in RANK:
            failures.append(f"{matcher} q={query}: no answer at all (want {want})")
            continue
        seen_rungs.add(answered)
        if want == "above_type":
            if RANK[answered] >= TYPE_RANK:
                failures.append(
                    f"{matcher} q={query}: answered at {answered}, "
                    "which is not above the type grade"
                )
            continue
        if want not in RANK:
            failures.append(f"{matcher} q={query}: the case names unknown rung {want}")
        elif RANK[answered] > RANK[want]:
            failures.append(
                f"{matcher} q={query}: answered at {answered}, weaker than {want}"
            )

    if cases == 0:
        failures.append("no [LOAD-GATE] RUNG line in the log")

    for rung in REQUIRED_RUNGS:
        if rung not in seen_rungs:
            failures.append(f"the {rung} rung was never exercised")

    masses = 0
    for line in lines:
        match = MASS_LINE.search(line)
        if not match:
            continue
        masses += 1
        item, raw = match.groups()
        try:
            kg = float(raw)
        except ValueError:
            failures.append(f"item {item}: mass {raw} is not a number")
            continue
        expect = MASS_EXPECT.get(item)
        if expect == "positive" and kg <= 0:
            failures.append(f"item {item}: mass {kg} kg, expected a published figure")
        if expect == "zero" and kg != 0:
            failures.append(
                f"item {item}: mass {kg} kg, expected 0 for an unknown item"
            )
    if masses == 0:
        failures.append("no [LOAD-GATE] MASS line in the log")

    print(f"rung cases: {cases}  rungs seen: {len(seen_rungs)}  mass cases: {masses}")
    return failures


def main():
    if len(sys.argv) < 2:
        print("usage: verify_load.py <log>", file=sys.stderr)
        return 2
    failures = check(sys.argv[1])
    if failures:
        print(f"LOAD GATE FAIL ({len(failures)} finding(s))")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("LOAD GATE PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
