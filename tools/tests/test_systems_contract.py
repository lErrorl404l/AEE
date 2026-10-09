#!/usr/bin/env python3
"""The systems field contract is the oracle for the field tables.

A field table is a markdown table whose header names the columns of the
contract. Every data row must carry a unit, a source class, a published
flag and an engine hook or marker. A prose stub parses to no rows and
fails this module.

The tables live in ``data/vehicle/SCHEMA.md`` (the shared contract and the
land-vehicle physics surface) and ``data/aircraft/SCHEMA.md`` (the
aircraft deltas).

Run: python3 -m unittest tools.tests.test_systems_contract -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
VEHICLE_SCHEMA = REPO / "data" / "vehicle" / "SCHEMA.md"
AIRCRAFT_SCHEMA = REPO / "data" / "aircraft" / "SCHEMA.md"

# The header signature of a systems field table. One name per column.
SYSTEMS_HEADER = ("field", "unit", "source class", "published", "engine hook or marker")

# The exact new units the shared vocabulary must carry.
NEW_UNITS = (
    "`rpm`",
    "`MJ/kg`",
    "`kg/L`",
    "`kg/kWh`",
    "`kg/s`",
    "`deg C`",
    "`Ah`",
    "`V`",
    "`kg m^2`",
)


def _cells(line: str) -> list[str]:
    """Split one pipe-table line into its trimmed cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def pipe_tables(text: str):
    """Yield (header_cells, [row_cells, ...]) for every markdown table."""
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].strip().startswith("|"):
            block: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                block.append(lines[index])
                index += 1
            if len(block) >= 2:
                header = _cells(block[0])
                body = [_cells(line) for line in block[2:]]
                yield header, body
        else:
            index += 1


def systems_rows(text: str) -> list[list[str]]:
    """Return every data row of every systems field table."""
    rows: list[list[str]] = []
    for header, body in pipe_tables(text):
        if tuple(cell.lower() for cell in header) == SYSTEMS_HEADER:
            rows.extend(body)
    return rows


def systems_errors(text: str) -> list[str]:
    """Return one message per systems row that breaks the contract."""
    errors: list[str] = []
    for row in systems_rows(text):
        if len(row) != len(SYSTEMS_HEADER):
            errors.append(f"systems row has {len(row)} columns, expected 5: {row}")
            continue
        field, unit, source, published, marker = row
        label = field or "<unknown field>"
        if not field:
            errors.append("systems row has no field name")
        if not unit:
            errors.append(f"{label}: missing unit")
        if not source:
            errors.append(f"{label}: missing source class")
        if published.lower() not in ("yes", "no"):
            errors.append(
                f"{label}: published flag must be yes or no, got {published!r}"
            )
        if not marker:
            errors.append(f"{label}: missing engine hook or marker")
    return errors


# The header signature of a land-vehicle physics table.
LAND_HEADER = ("field", "source class or derivation", "marker")
LAND_MARKERS = ("published", "derived", "engine schema")


def land_rows(text: str) -> list[list[str]]:
    """Return every data row of every land-vehicle physics table."""
    rows: list[list[str]] = []
    for header, body in pipe_tables(text):
        if tuple(cell.lower() for cell in header) == LAND_HEADER:
            rows.extend(body)
    return rows


def land_errors(text: str) -> list[str]:
    """Return one message per land row that breaks the contract."""
    errors: list[str] = []
    for row in land_rows(text):
        if len(row) != len(LAND_HEADER):
            errors.append(f"land row has {len(row)} columns, expected 3: {row}")
            continue
        field, source, marker = row
        label = field or "<unknown field>"
        if not field:
            errors.append("land row has no field name")
        if not source:
            errors.append(f"{label}: missing source class or derivation")
        if marker not in LAND_MARKERS:
            errors.append(
                f"{label}: marker must be published, derived or engine schema, got {marker!r}"
            )
        elif marker == "derived" and not source.lower().startswith("derived"):
            errors.append(f"{label}: a derived row must name its derivation")
    return errors


def _section(text: str, heading: str) -> str:
    """Return the text under a level-2 heading up to the next heading."""
    marker = f"## {heading}"
    start = text.find(marker)
    if start == -1:
        raise AssertionError(f"heading not found: {marker}")
    body = text[start + len(marker) :]
    end = body.find("\n## ")
    return body if end == -1 else body[:end]


class SharedSystemsContractTest(unittest.TestCase):
    """`data/vehicle/SCHEMA.md` section 16 defines the shared field set."""

    def setUp(self) -> None:
        self.text = VEHICLE_SCHEMA.read_text(encoding="utf-8")

    def test_the_shared_schema_holds_a_systems_table(self) -> None:
        self.assertTrue(systems_rows(self.text), "no systems field table found")

    def test_every_systems_row_is_complete(self) -> None:
        self.assertEqual([], systems_errors(self.text))

    def test_the_five_shared_groups_are_present(self) -> None:
        fields = {row[0] for row in systems_rows(self.text)}
        for name in (
            "`fuel_capacity`",
            "`rated_power_w`",
            "`cg_empty_m`",
            "`hitpoint_names`",
            "`hydraulic_system_count`",
        ):
            self.assertIn(name, fields, f"shared field missing: {name}")

    def test_the_new_units_are_in_the_vocabulary(self) -> None:
        for unit in NEW_UNITS:
            self.assertIn(unit, self.text, f"unit missing from the vocabulary: {unit}")

    def test_the_source_types_include_poh_and_tcds(self) -> None:
        section = _section(self.text, "4. Source types and hard rules")
        self.assertIn("`poh`", section)
        self.assertIn("`tcds`", section)

    def test_the_engine_ceiling_is_stated(self) -> None:
        self.assertIn("difficultyEnabledRTD", self.text)
        self.assertIn("never feeds the flight dynamics model", self.text)
        self.assertIn("engine-fixed at config load", self.text)

    def test_the_aircraft_schema_is_untouched_by_the_shared_contract(self) -> None:
        # The aircraft deltas are a separate task. This file must not hold a
        # shared table, so a systems row here is a contract error.
        aircraft = AIRCRAFT_SCHEMA.read_text(encoding="utf-8")
        self.assertEqual([], systems_errors(aircraft))


class LandPhysicsSurfaceTest(unittest.TestCase):
    """`data/vehicle/SCHEMA.md` section 17 defines the land physics surface."""

    def setUp(self) -> None:
        self.text = VEHICLE_SCHEMA.read_text(encoding="utf-8")

    def test_the_land_surface_holds_a_table(self) -> None:
        self.assertTrue(land_rows(self.text), "no land physics table found")

    def test_every_land_row_is_complete(self) -> None:
        self.assertEqual([], land_errors(self.text))

    def test_the_named_derivations_are_present(self) -> None:
        derived = {row[0] for row in land_rows(self.text) if row[-1] == "derived"}
        for name in ("`sprungMass`", "`springStrength`", "`springDamperRate`", "`MOI`"):
            self.assertIn(name, derived, f"derivation missing: {name}")

    def test_the_simulation_keys_name_the_three_solvers(self) -> None:
        sims = [row for row in land_rows(self.text) if row[0] == "`simulation`"]
        self.assertEqual(
            3, len(sims), "carx, tankx and shipx each need a simulation key"
        )
        for _, source, _ in sims:
            self.assertRegex(source, r"carx|tankx|shipx")

    def test_the_three_solvers_are_named(self) -> None:
        lowered = self.text.lower()
        for solver in ("carx", "tankx", "shipx"):
            self.assertGreaterEqual(lowered.count(solver), 1, solver)

    def test_the_no_xml_statement_is_present(self) -> None:
        self.assertIn("the engine reads no XML for it", self.text)


if __name__ == "__main__":
    _ = unittest.main()
