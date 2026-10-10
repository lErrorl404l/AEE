#!/usr/bin/env python3
"""Gate for the magazine mass corpus (ADR-003, ADR-037).

The corpus data/ballistics/sources/magazine_mass.json holds the published
magazine masses. Every source carries a tier (1 to 5) and a grade, and the
grade must agree with the tier: a tier 1 to 3 source is documented, a tier
4 to 5 source is claimed. Every magazine carries a state that names the
mass basis, empty or loaded. No mass number may change without a source.

Run:  python3 tools/validation/validate_magazine_mass.py
Exit: 0 when the corpus obeys the contract, 1 when it does not.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CORPUS = (
    Path(__file__).parents[2] / "data" / "ballistics" / "sources" / "magazine_mass.json"
)

SOURCE_COUNT = 72
MAGAZINE_COUNT = 76
CASE_COUNT = 12
LOADED_COUNT = 13
EMPTY_COUNT = 73

# The frozen digest of every (item, empty_mass_g, loaded_mass_g) triple. A
# changed mass number, a new magazine or a removed magazine changes this
# digest and fails the gate. Update it only with a held source.
MASS_DIGEST = "824c7000524b21f6f1147c074170276b9100d8986f68de3da23bbdae0fe71fd0"

STATES = ("empty", "loaded")


class MassContractError(Exception):
    """A violation of the magazine mass corpus contract."""


def _mass_digest(magazines: list[dict[str, object]]) -> str:
    triples = sorted(
        [str(row["item"]), row.get("empty_mass_g"), row.get("loaded_mass_g")]
        for row in magazines
    )
    canonical = json.dumps(triples, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate(payload: dict[str, object]) -> None:
    sources = payload.get("sources")
    magazines = payload.get("magazines")
    cases = payload.get("cases")
    if not isinstance(sources, list) or not isinstance(magazines, list):
        raise MassContractError("sources and magazines must be arrays")
    if not isinstance(cases, list):
        raise MassContractError("cases must be an array")

    if len(sources) != SOURCE_COUNT:
        raise MassContractError(
            f"expected {SOURCE_COUNT} sources, found {len(sources)}"
        )
    if len(magazines) != MAGAZINE_COUNT:
        raise MassContractError(
            f"expected {MAGAZINE_COUNT} magazines, found {len(magazines)}"
        )
    if len(cases) != CASE_COUNT:
        raise MassContractError(f"expected {CASE_COUNT} cases, found {len(cases)}")

    for raw in sources:
        if not isinstance(raw, dict):
            raise MassContractError("a source is not an object")
        source_id = raw.get("source_id")
        tier = raw.get("tier")
        grade = raw.get("grade")
        if not isinstance(tier, int) or isinstance(tier, bool) or not 1 <= tier <= 5:
            raise MassContractError(f"{source_id}: tier must be an integer 1 to 5")
        if grade not in ("documented", "claimed"):
            raise MassContractError(f"{source_id}: grade must be documented or claimed")
        expected = "documented" if tier <= 3 else "claimed"
        if grade != expected:
            raise MassContractError(
                f"{source_id}: tier {tier} must carry grade {expected}, found {grade}"
            )

    loaded = 0
    empty = 0
    for raw in magazines:
        if not isinstance(raw, dict):
            raise MassContractError("a magazine is not an object")
        item = raw.get("item")
        state = raw.get("state")
        if state not in STATES:
            raise MassContractError(f"{item}: state must be empty or loaded")
        if raw.get("loaded_mass_g") is not None:
            loaded += 1
        if raw.get("empty_mass_g") is not None:
            empty += 1
        expected_state = "loaded" if raw.get("loaded_mass_g") is not None else "empty"
        if state != expected_state:
            raise MassContractError(
                f"{item}: state {state} disagrees with the held mass basis"
            )
    if loaded != LOADED_COUNT:
        raise MassContractError(
            f"expected {LOADED_COUNT} loaded masses, found {loaded}"
        )
    if empty != EMPTY_COUNT:
        raise MassContractError(f"expected {EMPTY_COUNT} empty masses, found {empty}")

    digest = _mass_digest(magazines)
    if digest != MASS_DIGEST:
        raise MassContractError(
            "a magazine mass number changed: digest "
            f"{digest} does not match the frozen {MASS_DIGEST}"
        )


def main() -> int:
    try:
        payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"magazine mass: cannot read the corpus: {exc}")
        return 1
    if not isinstance(payload, dict):
        print("magazine mass: the corpus must be a JSON object")
        return 1
    try:
        validate(payload)
    except MassContractError as exc:
        print(f"magazine mass: {exc}")
        return 1
    print(
        f"magazine mass: {SOURCE_COUNT} sources, {MAGAZINE_COUNT} magazines, "
        f"{CASE_COUNT} cases, {LOADED_COUNT} loaded and {EMPTY_COUNT} empty (fresh)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
