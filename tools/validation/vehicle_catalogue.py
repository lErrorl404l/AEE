#!/usr/bin/env python3
"""Shared loader for the vehicle catalogue and the class-to-catalogue map.

The loader reads ``data/vehicle/catalogue/*.json`` and
``data/vehicle/class_map.json`` and returns typed records. The validator and
the generator share it, so the corpus has one read path. The loader stays
independent of the runtime SQF. It reads corpus data only, never a config,
and it invents no value.

Rules it enforces:

- A ``catalogue_id`` and a ``variant_id`` are unique in the corpus. The loader
  keeps the first record and drops a duplicate with an error.
- An alias and a keyword are normalised to the runtime match key: lowercase
  letters and digits only, as ``fnc_getWeaponData.sqf`` does.
- An alias claimed by two entries is not an identity signal. The loader drops
  it from the alias index and warns.
- A class map needs a real-world mapping source. A record with no mapping
  source, or with an engine source, is rejected.
- A catalogue capture keeps its retired ``sources`` array empty.

A held-source lead loads as a record with ``runtime_ready`` false. The loader
never marks a record runtime-ready.

Run: imported by ``tools/validation/validate_vehicle_data.py`` and the
generator. No command-line entry point.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

# The real-world source types. Only these can be a class-map mapping source.
# This set is the canonical source-type vocabulary: the aircraft validator
# reads it, so the two definitions cannot diverge. `poh` and `tcds` are the
# tier-2 pilot's operating handbook and type certificate data sheet classes
# from `data/vehicle/SCHEMA.md` section 4.
REAL_SOURCE_TYPES = frozenset(
    {
        "standard",
        "manual",
        "poh",
        "tcds",
        "measurement",
        "manufacturer",
        "compilation",
    }
)

# The class-map grade set per schema section 7.
CLASS_MAP_GRADES = frozenset({"documented", "claimed"})

# The vehicle families the runtime projection supports. ``wheeled`` and
# ``tracked`` are the ground families and carry the NRMM inputs. ``air`` and
# ``sea`` are the flight and maritime families and carry the identity
# geometry only: the ground couplings are land-specific and are not forced
# onto them.
VEHICLE_TYPES = frozenset({"wheeled", "tracked", "air", "sea"})

# The fixed unit of every runtime field. The wider field vocabulary lives in
# the validator; these are the projected runtime inputs.
RUNTIME_FIELD_UNITS: dict[str, str] = {
    "operating_weight_kg": "kg",
    "tyre_width_mm": "mm",
    "tyre_diameter_mm": "mm",
    "ground_clearance_mm": "mm",
    "net_power_kw": "kW",
    "transmission_type": "enum",
    "grousers_state": "enum",
    "track_shoe_width_mm": "mm",
    "track_pitch_mm": "mm",
    "length_mm": "mm",
    "width_mm": "mm",
    "height_mm": "mm",
    "rated_power_w": "W",
    "drag_area_m2": "m^2",
    "rotor_disc_area_m2": "m^2",
}

# The runtime inputs per vehicle family, in projection order. A wheeled set
# carries the two tyre fields. A tracked set carries the two track fields.
# An air or sea set carries the identity geometry only. The ground couplings
# are land-specific, so the NRMM inputs are not forced onto air or sea.
REQUIRED_RUNTIME_BY_TYPE: dict[str, tuple[str, ...]] = {
    "wheeled": (
        "operating_weight_kg",
        "tyre_width_mm",
        "tyre_diameter_mm",
        "ground_clearance_mm",
        "net_power_kw",
        "transmission_type",
        "grousers_state",
    ),
    "tracked": (
        "operating_weight_kg",
        "track_shoe_width_mm",
        "track_pitch_mm",
        "ground_clearance_mm",
        "net_power_kw",
        "transmission_type",
        "grousers_state",
    ),
    "air": (
        "operating_weight_kg",
        "length_mm",
        "width_mm",
        "height_mm",
    ),
    "sea": (
        "operating_weight_kg",
        "length_mm",
        "width_mm",
        "height_mm",
    ),
}

# The runtime fields that carry a word, not a number.
TEXT_RUNTIME_FIELDS = frozenset({"transmission_type", "grousers_state"})

# The grade vocabulary of a resolved runtime field. ``absent`` means the
# corpus holds no value and no derivation applies. The row still emits.
RESOLVED_GRADES = frozenset({"standard", "documented", "claimed", "derived", "absent"})

# The five keys a complete held value object carries beside its value.
VALUE_META_KEYS = ("unit", "source", "locator", "state", "grade")

# Named derivations. Each formula is a citation, not a guess.
HP_TO_KW = 0.745699872
INCH_TO_MM = 25.4
POWER_ROUND = 6
TYRE_ROUND = 4

# A derived value must name its formula in the state text. The marker is the
# phrase the generator writes and the validator checks.
DERIVATION_STATE_MARKERS: dict[str, str] = {
    "operating_weight_kg": "derived operating weight",
    "net_power_kw": "1 hp = 745.699872 W",
    "tyre_width_mm": "derived from the size code",
    "tyre_diameter_mm": "derived from the size code",
}
DERIVATION_FIELDS = frozenset(DERIVATION_STATE_MARKERS)

# The aircraft corpus is a sibling of the vehicle corpus. It keeps the value
# object, the grades and the resolution ladder, and changes only the type enum,
# the runtime sets and the named derivations. A jet's thrust is a force, not
# power, so the rated power is derived as
# ``thrust_kn * 1000 * reference_speed_ms`` at the reference speed.
AIRCRAFT_VEHICLE_TYPES = frozenset({"fixed_wing", "rotary_wing"})
AIRCRAFT_REQUIRED_RUNTIME_BY_TYPE: dict[str, tuple[str, ...]] = {
    "fixed_wing": ("operating_weight_kg", "rated_power_w"),
    "rotary_wing": (
        "operating_weight_kg",
        "rated_power_w",
        "rotor_disc_area_m2",
    ),
}
AIRCRAFT_DERIVATION_STATE_MARKERS: dict[str, str] = {
    "operating_weight_kg": "derived operating weight",
    "rated_power_w": "derived rated power",
    "rotor_disc_area_m2": "derived rotor disc area",
    "drag_area_m2": "derived drag area",
}
AIRCRAFT_DERIVATION_FIELDS = frozenset(AIRCRAFT_DERIVATION_STATE_MARKERS)

# The systems field registry. It is the shared contract in
# ``data/vehicle/SCHEMA.md`` section 16 together with the aircraft deltas in
# ``data/aircraft/SCHEMA.md`` section 10. Each row gives one field and its
# exact unit. The validator reads this registry, so a systems field is a known
# field. Every field here is reference only, status only or derived. None of
# the reference-only or status-only fields is a runtime calculation input, so
# a reference-only or status-only value never fills a runtime-required field.
SYSTEMS_FIELD_UNITS: dict[str, str] = {
    # Fuel.
    "fuel_capacity": "L",
    "fuel_type": "enum",
    "fuel_density_kg_l": "kg/L",
    "fuel_mass_full_kg": "kg",
    "fuel_consumption_rate": "kg/s",
    "sfc_kg_kwh": "kg/kWh",
    "fuel_burn_kg_s": "kg/s",
    "fuel_tank_count": "count",
    "fuel_tank_capacity_l": "L",
    "fuel_cg_arm_m": "m",
    "fuel_lhv_mj_kg": "MJ/kg",
    # Engine.
    "engine_model": "text",
    "engine_count": "count",
    "rated_power_w": "W",
    "engine_design_rpm": "rpm",
    "engine_max_torque_nm": "N m",
    "engine_oil_pressure_min_kpa": "kPa",
    "engine_oil_pressure_max_kpa": "kPa",
    "engine_oil_capacity_l": "L",
    "engine_oil_type": "enum",
    "transmission_torque_limit_nm": "N m",
    "transmission_gear_ratio_main": "ratio",
    # Engine turbine terms, an aircraft delta.
    "engine_idle_ng": "ratio",
    "engine_max_ng": "ratio",
    "engine_max_np": "ratio",
    "engine_max_tgt_c": "deg C",
    "engine_max_itt_c": "deg C",
    "transmission_gear_ratio_tail": "ratio",
    # Rotor geometry, an aircraft delta.
    "rotor_radius_m": "m",
    "rotor_diameter_m": "m",
    "rotor_blade_count": "count",
    "rotor_chord_m": "m",
    "rotor_twist_deg": "deg",
    "rotor_hinge_offset_m": "m",
    "rotor_design_rpm": "rpm",
    "rotor_tip_speed_ms": "m/s",
    "tail_rotor_radius_m": "m",
    "tail_rotor_blade_count": "count",
    # Mass, centre of gravity and inertia.
    "empty_weight_kg": "kg",
    "max_takeoff_weight_kg": "kg",
    "cg_empty_m": "m",
    "cg_forward_limit_m": "m",
    "cg_aft_limit_m": "m",
    "inertia_xx_kgm2": "kg m^2",
    "inertia_yy_kgm2": "kg m^2",
    "inertia_zz_kgm2": "kg m^2",
    "payload_kg": "kg",
    # V-speeds, an aircraft delta and reference only.
    "vne_kmh": "km/h",
    "vmo_kmh": "km/h",
    "vref_kmh": "km/h",
    "vstall_kmh": "km/h",
    "vy_kmh": "km/h",
    "autorotation_speed_kmh": "km/h",
    "service_ceiling_m": "m",
    # Damage.
    "hitpoint_names": "list",
    "component_count": "count",
    "crew_count": "count",
    "damage_role_map": "mapping",
    # Status systems.
    "hydraulic_system_count": "count",
    "hydraulic_pressure_kpa": "kPa",
    "generator_count": "count",
    "generator_power_kw": "kW",
    "bus_voltage_v": "V",
    "battery_capacity_ah": "Ah",
    # Pressurisation, an aircraft delta and status only.
    "cabin_pressure_max_kpa": "kPa",
    "pressurisation_ceiling_m": "m",
    "oxygen_system": "enum",
}

# The unit vocabulary the systems contract adds to the inherited vocabulary.
# ``list`` and ``mapping`` are the non-physical tokens the damage fields use.
SYSTEMS_UNITS = frozenset(
    {
        "rpm",
        "MJ/kg",
        "kg/L",
        "kg/kWh",
        "kg/s",
        "deg C",
        "Ah",
        "V",
        "kg m^2",
        "list",
        "mapping",
    }
)

# The systems fields the schema marks reference only. A reference-only value
# may carry any grade. It never fills a runtime-required field.
REFERENCE_ONLY_SYSTEMS_FIELDS = frozenset(
    {
        "fuel_type",
        "fuel_tank_count",
        "fuel_tank_capacity_l",
        "engine_model",
        "engine_count",
        "engine_design_rpm",
        "engine_oil_capacity_l",
        "engine_oil_type",
        "transmission_gear_ratio_main",
        "transmission_gear_ratio_tail",
        "rotor_radius_m",
        "rotor_blade_count",
        "rotor_chord_m",
        "rotor_twist_deg",
        "rotor_hinge_offset_m",
        "rotor_design_rpm",
        "rotor_tip_speed_ms",
        "tail_rotor_radius_m",
        "tail_rotor_blade_count",
        "cg_forward_limit_m",
        "cg_aft_limit_m",
        "inertia_xx_kgm2",
        "inertia_yy_kgm2",
        "inertia_zz_kgm2",
        "vne_kmh",
        "vmo_kmh",
        "vref_kmh",
        "vstall_kmh",
        "vy_kmh",
        "autorotation_speed_kmh",
        "service_ceiling_m",
        "crew_count",
    }
)

# The systems fields the schema marks status only. A status-only value reports
# a state. It never feeds the flight dynamics model.
STATUS_ONLY_SYSTEMS_FIELDS = frozenset(
    {
        "engine_oil_pressure_min_kpa",
        "engine_oil_pressure_max_kpa",
        "engine_max_np",
        "engine_max_tgt_c",
        "engine_max_itt_c",
        "hydraulic_system_count",
        "hydraulic_pressure_kpa",
        "generator_count",
        "generator_power_kw",
        "bus_voltage_v",
        "battery_capacity_ah",
        "cabin_pressure_max_kpa",
        "pressurisation_ceiling_m",
        "oxygen_system",
    }
)

HP_TO_W = HP_TO_KW * 1000.0


@dataclass(frozen=True)
class Profile:
    """A corpus profile: the type enum, its runtime sets and its derivations."""

    name: str
    vehicle_types: frozenset[str]
    runtime_by_type: Mapping[str, tuple[str, ...]]
    text_fields: frozenset[str]
    derivation_markers: Mapping[str, str]
    derivation_fields: frozenset[str]


GROUND_PROFILE = Profile(
    name="ground",
    vehicle_types=VEHICLE_TYPES,
    runtime_by_type=MappingProxyType(dict(REQUIRED_RUNTIME_BY_TYPE)),
    text_fields=TEXT_RUNTIME_FIELDS,
    derivation_markers=MappingProxyType(dict(DERIVATION_STATE_MARKERS)),
    derivation_fields=DERIVATION_FIELDS,
)

AIRCRAFT_PROFILE = Profile(
    name="aircraft",
    vehicle_types=AIRCRAFT_VEHICLE_TYPES,
    runtime_by_type=MappingProxyType(dict(AIRCRAFT_REQUIRED_RUNTIME_BY_TYPE)),
    text_fields=frozenset(),
    derivation_markers=MappingProxyType(dict(AIRCRAFT_DERIVATION_STATE_MARKERS)),
    derivation_fields=AIRCRAFT_DERIVATION_FIELDS,
)

# Engine identity sources. They can bind a game class only at grade
# ``claimed`` and only when the evidence names the concrete token or kind.
ENGINE_MAPPING_SOURCE_TYPES = frozenset({"engine_config", "class_table"})

_NON_KEY = re.compile(r"[^a-z0-9]+")


def normalise(text: str) -> str:
    """Return the runtime match key: lowercase letters and digits only."""
    return _NON_KEY.sub("", text.lower())


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return list(value)


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _normalised_list(
    value: object, where: str, field_name: str, errors: list[str]
) -> tuple[str, ...]:
    """Return the deduplicated match keys of an alias or keyword array."""
    items = _sequence(value)
    if items is None:
        errors.append(f"{where}: {field_name} must be an array")
        return ()
    keys: list[str] = []
    for item in items:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{where}: {field_name} holds a non-string entry")
            continue
        key = normalise(item)
        if key and key not in keys:
            keys.append(key)
    return tuple(keys)


@dataclass(frozen=True)
class CatalogueEntry:
    """One real-world catalogue entry, loaded and normalised."""

    catalogue_id: str
    canonical_name: str
    maker: str
    model: str
    variant: str
    variant_id: str
    vehicle_type: str
    class_token: str
    country: str
    era: str
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]
    runtime_ready: bool
    values: dict[str, object]
    source_file: str
    profile: Profile = GROUND_PROFILE

    def identity_aliases(self) -> tuple[str, ...]:
        """Every token that names this entry: id, variant id and aliases."""
        tokens = [normalise(self.catalogue_id), normalise(self.variant_id)]
        tokens.extend(self.aliases)
        keys: list[str] = []
        for token in tokens:
            if token and token not in keys:
                keys.append(token)
        return tuple(keys)

    def resolved_fields(
        self, profile: Profile | None = None
    ) -> dict[str, ResolvedField]:
        """Resolve the runtime fields of this entry for the projection."""
        return resolve_fields(self.vehicle_type, self.values, profile or self.profile)

    def to_mapping(self) -> dict[str, object]:
        """Return the record as a plain mapping for the contract validator.

        ``values`` holds the held value objects only. ``resolved`` holds the
        graded runtime projection: one entry per runtime field, each resolved
        to a held value, a named derivation or a labelled absent zero.
        """
        return {
            "catalogue_id": self.catalogue_id,
            "canonical_name": self.canonical_name,
            "maker": self.maker,
            "model": self.model,
            "variant": self.variant,
            "variant_id": self.variant_id,
            "vehicle_type": self.vehicle_type,
            "class_token": self.class_token,
            "country": self.country,
            "era": self.era,
            "aliases": list(self.aliases),
            "keywords": list(self.keywords),
            "runtime_ready": self.runtime_ready,
            "values": self.values,
            "resolved": {
                name: field.to_mapping()
                for name, field in self.resolved_fields().items()
            },
        }


@dataclass(frozen=True)
class ClassMapping:
    """One game-class to catalogue mapping with its real-world evidence."""

    game_class: str
    class_token: str
    catalogue_id: str
    identity_source: str
    identity_evidence: str
    grade: str
    note: str
    source_file: str

    def to_mapping(self) -> dict[str, object]:
        """Return the mapping as a plain mapping for the contract validator."""
        return {
            "game_class": self.game_class,
            "class_token": self.class_token,
            "catalogue_id": self.catalogue_id,
            "identity_source": self.identity_source,
            "identity_evidence": self.identity_evidence,
            "grade": self.grade,
            "note": self.note,
        }


@dataclass(frozen=True)
class ClassBinding:
    """One concrete game class bound to a catalogue entry.

    A class binding is finer than a class map. The class map names a class
    token; a binding names the concrete, deployed class and the entry it
    stands for. It carries the same identity evidence and grade rules.
    """

    game_class: str
    class_token: str
    catalogue_id: str
    identity_source: str
    identity_evidence: str
    grade: str
    note: str
    source_file: str

    def to_mapping(self) -> dict[str, object]:
        """Return the binding as a plain mapping for the contract validator."""
        return {
            "game_class": self.game_class,
            "class_token": self.class_token,
            "catalogue_id": self.catalogue_id,
            "identity_source": self.identity_source,
            "identity_evidence": self.identity_evidence,
            "grade": self.grade,
            "note": self.note,
        }


@dataclass(frozen=True)
class ResolvedField:
    """One runtime field after the graded resolution ladder."""

    name: str
    value: object
    unit: str
    source: str
    locator: str
    state: str
    grade: str

    def to_mapping(self) -> dict[str, object]:
        """Return the resolved field as a plain value object."""
        return {
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "locator": self.locator,
            "state": self.state,
            "grade": self.grade,
        }


def held_value(values: dict[str, object], field: str) -> dict[str, object] | None:
    """Return a complete held value object for one field, or None."""
    entry = _mapping(values.get(field))
    if entry is None:
        return None
    if entry.get("value") in (None, ""):
        return None
    for key in VALUE_META_KEYS:
        if entry.get(key) in (None, ""):
            return None
    return entry


def _from_held(field: str, entry: dict[str, object]) -> ResolvedField:
    return ResolvedField(
        name=field,
        value=entry.get("value"),
        unit=str(entry.get("unit", "")),
        source=str(entry.get("source", "")),
        locator=str(entry.get("locator", "")),
        state=str(entry.get("state", "")),
        grade=str(entry.get("grade", "")),
    )


def _absent(field: str, profile: Profile = GROUND_PROFILE) -> ResolvedField:
    """A field no held value and no derivation reaches: a labelled zero."""
    value: object = "" if field in profile.text_fields else 0
    return ResolvedField(
        name=field,
        value=value,
        unit=RUNTIME_FIELD_UNITS.get(field, ""),
        source="",
        locator="",
        state="no held value and no derivation applies",
        grade="absent",
    )


# The metric size code, radial or cross-ply: 395/85R20, 110/80-R19, 130/80-16.
# The width is the first figure in millimetres and the aspect is the second.
# The separator before the rim is required and marks radial (R) or cross-ply
# (-). It does not change the formula. A required separator stops the aspect
# from backtracking into the rim, so ``130/80`` and ``395/8520`` are rejected.
# The inch form is handled after the imperial colon is folded to a decimal
# point.
_METRIC_TYRE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)"
    r"\s*(?:-\s*)?(?:R|-)\s*(\d+(?:\.\d+)?)\s*$"
)
_INCH_TYRE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[xX\-\s]+\s*R?\s*(\d+(?:\.\d+)?)\s*$")


def parse_tyre_size(code: str) -> tuple[float, float] | None:
    """Return ``(width_mm, diameter_mm)`` from a size code, or None.

    Metric ``395/85R20`` (radial) and ``130/80-16`` (cross-ply): width is the
    first figure in millimetres, the section height is ``width * aspect / 100``
    and the diameter adds two sections to the rim. The separator before the rim
    marks radial or cross-ply. It does not change the formula.
    Inch ``14:00 x R20``, ``14.00-20`` or ``14x20``: the aspect is 100 by
    definition for a cross-ply truck tyre, so the section equals the width.
    """
    metric = _METRIC_TYRE.match(code)
    if metric is not None:
        width = float(metric.group(1))
        aspect = float(metric.group(2))
        rim = float(metric.group(3))
        section = width * aspect / 100.0
        return (
            round(width, TYRE_ROUND),
            round(rim * INCH_TO_MM + 2.0 * section, TYRE_ROUND),
        )
    inch = _INCH_TYRE.match(code.replace(":", "."))
    if inch is not None:
        width_in = float(inch.group(1))
        rim_in = float(inch.group(2))
        return (
            round(width_in * INCH_TO_MM, TYRE_ROUND),
            round((rim_in + 2.0 * width_in) * INCH_TO_MM, TYRE_ROUND),
        )
    return None


NET_POWER_STATE = (
    "brake horsepower converted by 1 hp = 745.699872 W (ISO 80000-4, "
    "mechanical horsepower); the source states brake, not net, power"
)


_OPERATING_WEIGHT_STATES: dict[str, str] = {
    "curb_weight_kg": (
        "derived operating weight from the published curb weight; no "
        "operating weight is published, so the curb weight is the basis"
    ),
    "gross_weight_kg": (
        "derived operating weight from the gross vehicle weight rating; "
        "no operating or curb weight is published, so the rating is the "
        "basis and it is a maximum, not a kerb weight"
    ),
    "empty_weight_kg": (
        "derived operating weight from the published empty weight; no "
        "operating weight is published, so the empty weight is the basis"
    ),
    "max_takeoff_weight_kg": (
        "derived operating weight from the maximum takeoff weight; no "
        "operating or empty weight is published, so the maximum is the basis"
    ),
}

_GROUND_WEIGHT_BASES = ("curb_weight_kg", "gross_weight_kg")
_AIRCRAFT_WEIGHT_BASES = ("empty_weight_kg", "max_takeoff_weight_kg")


def _derive_operating_weight(
    values: dict[str, object], bases: tuple[str, ...]
) -> ResolvedField | None:
    for basis in bases:
        base = held_value(values, basis)
        if base is None:
            continue
        return ResolvedField(
            name="operating_weight_kg",
            value=base.get("value"),
            unit="kg",
            source=str(base.get("source", "")),
            locator=str(base.get("locator", "")),
            state=_OPERATING_WEIGHT_STATES[basis],
            grade="derived",
        )
    return None


def _number(value: object) -> float | None:
    """Return a finite number, or None for a bool, a string or a non-number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _derive_net_power(values: dict[str, object]) -> ResolvedField | None:
    base = held_value(values, "published_power_hp")
    if base is None:
        return None
    hp = base.get("value")
    if not isinstance(hp, (int, float)) or isinstance(hp, bool):
        return None
    return ResolvedField(
        name="net_power_kw",
        value=round(float(hp) * HP_TO_KW, POWER_ROUND),
        unit="kW",
        source=str(base.get("source", "")),
        locator=str(base.get("locator", "")),
        state=NET_POWER_STATE,
        grade="derived",
    )


def _derive_tyre(values: dict[str, object], field: str) -> ResolvedField | None:
    base = held_value(values, "tyre_size_text")
    if base is None:
        return None
    code = base.get("value")
    if not isinstance(code, str):
        return None
    parsed = parse_tyre_size(code)
    if parsed is None:
        return None
    width, diameter = parsed
    state = (
        f"derived from the size code {code} by W mm, section = W*A/100, "
        "diameter = rim*25.4 + 2*section (inch codes assume aspect 100)"
    )
    return ResolvedField(
        name=field,
        value=width if field == "tyre_width_mm" else diameter,
        unit="mm",
        source=str(base.get("source", "")),
        locator=str(base.get("locator", "")),
        state=state,
        grade="derived",
    )


def _derive_rated_power(values: dict[str, object]) -> ResolvedField | None:
    """Rated power from thrust, then net power, then published horsepower.

    A jet publishes thrust, a force, not power. The rated power is the thrust
    converted to power at the reference speed:
    ``rated_power_w = thrust_kn * 1000 * reference_speed_ms``. The conversion
    is the plan's settled thrust branch, so the kernel stays unchanged.
    """
    thrust = held_value(values, "thrust_kn")
    reference = held_value(values, "reference_speed_ms")
    if thrust is not None and reference is not None:
        thrust_kn = _number(thrust.get("value"))
        reference_ms = _number(reference.get("value"))
        if thrust_kn is not None and reference_ms is not None:
            return ResolvedField(
                name="rated_power_w",
                value=round(thrust_kn * 1000.0 * reference_ms, POWER_ROUND),
                unit="W",
                source=str(thrust.get("source", "")),
                locator=str(thrust.get("locator", "")),
                state=(
                    "derived rated power from thrust: "
                    "rated_power_w = thrust_kn * 1000 * reference_speed_ms; "
                    f"{thrust_kn} kN at {reference_ms} m/s"
                ),
                grade="derived",
            )
    net = held_value(values, "net_power_kw")
    if net is not None:
        net_kw = _number(net.get("value"))
        if net_kw is not None:
            return ResolvedField(
                name="rated_power_w",
                value=round(net_kw * 1000.0, POWER_ROUND),
                unit="W",
                source=str(net.get("source", "")),
                locator=str(net.get("locator", "")),
                state=(
                    "derived rated power from the net power: "
                    "rated_power_w = net_power_kw * 1000"
                ),
                grade="derived",
            )
    hp = held_value(values, "published_power_hp")
    if hp is not None:
        horsepower = _number(hp.get("value"))
        if horsepower is not None:
            return ResolvedField(
                name="rated_power_w",
                value=round(horsepower * HP_TO_W, POWER_ROUND),
                unit="W",
                source=str(hp.get("source", "")),
                locator=str(hp.get("locator", "")),
                state=(
                    "derived rated power from the published power: "
                    "rated_power_w = published_power_hp * 745.699872 "
                    "(1 hp = 745.699872 W)"
                ),
                grade="derived",
            )
    return None


def _derive_rotor_disc(values: dict[str, object]) -> ResolvedField | None:
    """Rotor disc area from the rotor diameter: ``pi * (diameter / 2)^2``."""
    base = held_value(values, "rotor_diameter_m")
    if base is None:
        return None
    diameter = _number(base.get("value"))
    if diameter is None:
        return None
    return ResolvedField(
        name="rotor_disc_area_m2",
        value=round(math.pi * (diameter / 2.0) ** 2, POWER_ROUND),
        unit="m^2",
        source=str(base.get("source", "")),
        locator=str(base.get("locator", "")),
        state=(
            "derived rotor disc area from the rotor diameter "
            f"{diameter} m: rotor_disc_area_m2 = pi * (rotor_diameter_m / 2)^2"
        ),
        grade="derived",
    )


def _derive_drag_area(values: dict[str, object]) -> ResolvedField | None:
    """Drag area from the drag coefficient and the wing area."""
    coefficient = held_value(values, "drag_coefficient")
    wing_area = held_value(values, "wing_area_m2")
    if coefficient is None or wing_area is None:
        return None
    cd = _number(coefficient.get("value"))
    area = _number(wing_area.get("value"))
    if cd is None or area is None:
        return None
    return ResolvedField(
        name="drag_area_m2",
        value=round(cd * area, POWER_ROUND),
        unit="m^2",
        source=str(coefficient.get("source", "")),
        locator=str(coefficient.get("locator", "")),
        state=(
            "derived drag area from the drag coefficient and the wing area: "
            f"drag_area_m2 = drag_coefficient * wing_area_m2 = {cd} * {area}"
        ),
        grade="derived",
    )


def _derive_field(
    values: dict[str, object], field: str, profile: Profile
) -> ResolvedField | None:
    """Choose the named derivation from the profile, never from a caller hint."""
    if field not in profile.derivation_fields:
        return None
    if field == "operating_weight_kg":
        bases = (
            _AIRCRAFT_WEIGHT_BASES
            if profile.name == "aircraft"
            else _GROUND_WEIGHT_BASES
        )
        return _derive_operating_weight(values, bases)
    if field == "net_power_kw":
        return _derive_net_power(values)
    if field in ("tyre_width_mm", "tyre_diameter_mm"):
        return _derive_tyre(values, field)
    if field == "rated_power_w":
        return _derive_rated_power(values)
    if field == "rotor_disc_area_m2":
        return _derive_rotor_disc(values)
    if field == "drag_area_m2":
        return _derive_drag_area(values)
    return None


def resolve_field(
    values: dict[str, object], field: str, profile: Profile = GROUND_PROFILE
) -> ResolvedField:
    """Resolve one runtime field: held, then the named derivation, then zero."""
    held = held_value(values, field)
    if held is not None:
        return _from_held(field, held)
    derived = _derive_field(values, field, profile)
    if derived is not None:
        return derived
    return _absent(field, profile)


def resolve_fields(
    vehicle_type: str,
    values: dict[str, object],
    profile: Profile = GROUND_PROFILE,
) -> dict[str, ResolvedField]:
    """Resolve every runtime field of one type, in projection order."""
    required = profile.runtime_by_type.get(vehicle_type, ())
    return {field: resolve_field(values, field, profile) for field in required}


def is_runtime_ready(
    vehicle_type: str,
    values: dict[str, object],
    profile: Profile = GROUND_PROFILE,
) -> bool:
    """True when every runtime field resolves to a non-absent value."""
    required = profile.runtime_by_type.get(vehicle_type)
    if not required:
        return False
    resolved = resolve_fields(vehicle_type, values, profile)
    return all(field.grade != "absent" for field in resolved.values())


def source_record_id(
    vehicle_type: str,
    values: dict[str, object],
    profile: Profile = GROUND_PROFILE,
) -> str:
    """The source id of the first field that resolved via a held value or a
    named derivation, or an empty string when every field is absent."""
    for field in profile.runtime_by_type.get(vehicle_type, ()):
        resolved = resolve_field(values, field, profile)
        if resolved.grade != "absent" and resolved.source:
            return resolved.source
    return ""


@dataclass
class CatalogueLoad:
    """The result of one load. Errors and warnings are explicit."""

    entries: list[CatalogueEntry]
    mappings: list[ClassMapping]
    alias_index: dict[str, str]
    warnings: list[str]
    errors: list[str]
    bindings: list[ClassBinding] = field(default_factory=list)


def _read_json(path: Path, errors: list[str]) -> object | None:
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.name}: cannot parse JSON: {exc}")
        return None
    return loaded


def _load_entry(
    raw: object,
    source_file: str,
    seen_ids: set[str],
    seen_variants: set[str],
    errors: list[str],
    profile: Profile = GROUND_PROFILE,
) -> CatalogueEntry | None:
    record = _mapping(raw)
    if record is None:
        errors.append(f"catalogue file {source_file}: entry must be an object")
        return None
    cid = _text(record.get("catalogue_id"))
    if cid is None:
        errors.append(f"catalogue file {source_file}: entry has no catalogue_id")
        return None
    where = f"catalogue {cid}"
    if cid in seen_ids:
        errors.append(f"{where}: duplicate catalogue_id")
        return None
    seen_ids.add(cid)

    variant_id = _text(record.get("variant_id")) or ""
    if variant_id:
        if variant_id in seen_variants:
            errors.append(f"{where}: duplicate variant_id {variant_id}")
            return None
        seen_variants.add(variant_id)

    declared_ready = record.get("runtime_ready")
    if not isinstance(declared_ready, bool):
        errors.append(f"{where}: runtime_ready must be true or false")

    values = _mapping(record.get("values"))
    if values is None:
        errors.append(f"{where}: values must be an object")
        values = {}

    vehicle_type = _text(record.get("vehicle_type")) or ""
    # The reported flag means every runtime field resolved to a non-absent
    # value. It never blocks a row.
    runtime_ready = is_runtime_ready(vehicle_type, values, profile)

    aliases = _normalised_list(record.get("aliases"), where, "aliases", errors)
    keywords = _normalised_list(record.get("keywords"), where, "keywords", errors)

    return CatalogueEntry(
        catalogue_id=cid,
        canonical_name=_text(record.get("canonical_name")) or "",
        maker=_text(record.get("maker")) or "",
        model=_text(record.get("model")) or "",
        variant=_text(record.get("variant")) or "",
        variant_id=variant_id,
        vehicle_type=vehicle_type,
        class_token=_text(record.get("class_token")) or "",
        country=_text(record.get("country")) or "",
        era=_text(record.get("era")) or "",
        aliases=aliases,
        keywords=keywords,
        runtime_ready=runtime_ready,
        values=values,
        source_file=source_file,
        profile=profile,
    )


def _load_entries(
    data_dir: Path, profile: Profile, errors: list[str]
) -> list[CatalogueEntry]:
    entries: list[CatalogueEntry] = []
    seen_ids: set[str] = set()
    seen_variants: set[str] = set()
    catalogue_dir = data_dir / "catalogue"
    if not catalogue_dir.is_dir():
        return entries
    for path in sorted(catalogue_dir.glob("*.json")):
        capture = _mapping(_read_json(path, errors))
        if capture is None:
            errors.append(f"catalogue file {path.name}: must be an object")
            continue
        inline = capture.get("sources")
        if inline is not None and inline != []:
            errors.append(
                f"catalogue file {path.name}: the retired capture-level sources "
                "array must stay empty; register sources in sources.json"
            )
        raw_entries = _sequence(capture.get("entries"))
        if raw_entries is None:
            errors.append(f"catalogue file {path.name}: entries must be an array")
            continue
        for raw in raw_entries:
            entry = _load_entry(
                raw, path.name, seen_ids, seen_variants, errors, profile
            )
            if entry is not None:
                entries.append(entry)
    return entries


def _build_alias_index(
    entries: list[CatalogueEntry], warnings: list[str]
) -> dict[str, str]:
    """Index unique identity tokens. Drop a shared token and warn."""
    owners: dict[str, list[str]] = {}
    for entry in entries:
        for token in entry.identity_aliases():
            owners.setdefault(token, []).append(entry.catalogue_id)
    index: dict[str, str] = {}
    for token, claiming in sorted(owners.items()):
        unique = sorted(set(claiming))
        if len(unique) > 1:
            warnings.append(
                f"alias {token} is claimed by {len(unique)} entries "
                f"({', '.join(unique)}) and is dropped from the alias index"
            )
            continue
        index[token] = unique[0]
    return index


def _source_ids_of_types(
    data_dir: Path, types: frozenset[str], errors: list[str]
) -> set[str]:
    """Read sources.json and return the ids whose type is in ``types``."""
    path = data_dir / "sources.json"
    if not path.is_file():
        return set()
    loaded = _sequence(_read_json(path, errors))
    if loaded is None:
        return set()
    ids: set[str] = set()
    for raw in loaded:
        source = _mapping(raw)
        if source is None:
            continue
        sid = _text(source.get("source_id"))
        if sid is not None and source.get("type") in types:
            ids.add(sid)
    return ids


def _real_source_ids(data_dir: Path, errors: list[str]) -> set[str]:
    """Read sources.json and return the real-world mapping source ids."""
    return _source_ids_of_types(data_dir, REAL_SOURCE_TYPES, errors)


def _engine_source_ids(data_dir: Path, errors: list[str]) -> set[str]:
    """Read sources.json and return the engine class-table source ids."""
    return _source_ids_of_types(data_dir, ENGINE_MAPPING_SOURCE_TYPES, errors)


def _load_mapping(
    record: dict[str, object],
    catalogue_ids: set[str],
    real_source_ids: set[str],
    seen: set[str],
    errors: list[str],
) -> ClassMapping | None:
    game_class = _text(record.get("game_class"))
    where = f"class map {game_class or '<none>'}"
    ok = True

    if game_class is None:
        errors.append(
            f"{where}: game_class is required; a category guess cannot create a class map"
        )
        ok = False
    elif game_class in seen:
        errors.append(
            f"{where}: duplicate game_class; one game class maps to one catalogue entry"
        )
        return None
    else:
        seen.add(game_class)

    class_token = record.get("class_token")
    if not isinstance(class_token, str):
        errors.append(f"{where}: class_token must be a string")
        ok = False

    cid = _text(record.get("catalogue_id"))
    if cid is None:
        errors.append(f"{where}: catalogue_id is required")
        ok = False
    elif cid not in catalogue_ids:
        errors.append(f"{where}: unknown catalogue_id {cid}")
        ok = False

    grade = record.get("grade")
    grade_ok = isinstance(grade, str) and grade in CLASS_MAP_GRADES
    if not grade_ok:
        errors.append(f"{where}: grade must be one of {sorted(CLASS_MAP_GRADES)}")

    source_id = _text(record.get("identity_source"))
    if source_id is None:
        errors.append(
            f"{where}: identity_source is required; a real-world mapping source cannot be a guess"
        )
        ok = False
    elif source_id not in real_source_ids and grade != "claimed":
        # An engine class table or config can bind a class only at grade
        # claimed. A documented mapping needs a real-world source.
        errors.append(
            f"{where}: identity_source {source_id} is not a real-world mapping source"
        )
        ok = False

    evidence = _text(record.get("identity_evidence"))
    if evidence is None:
        errors.append(
            f"{where}: identity_evidence is required; name the words or locator that link the class to the entry"
        )
        ok = False

    if not grade_ok:
        ok = False

    if not ok:
        return None
    return ClassMapping(
        game_class=game_class or "",
        class_token=class_token if isinstance(class_token, str) else "",
        catalogue_id=cid or "",
        identity_source=source_id or "",
        identity_evidence=evidence or "",
        grade=grade if isinstance(grade, str) else "",
        note=_text(record.get("note")) or "",
        source_file="class_map.json",
    )


def _load_mappings(
    data_dir: Path,
    catalogue_ids: set[str],
    real_source_ids: set[str],
    errors: list[str],
) -> list[ClassMapping]:
    mappings: list[ClassMapping] = []
    path = data_dir / "class_map.json"
    if not path.is_file():
        return mappings
    loaded = _read_json(path, errors)
    records = _sequence(loaded)
    if records is None:
        if loaded is not None:
            errors.append("class_map.json: must be a top-level array")
        return mappings
    seen: set[str] = set()
    for raw in records:
        record = _mapping(raw)
        if record is None:
            errors.append("class map entry: must be an object")
            continue
        mapping = _load_mapping(record, catalogue_ids, real_source_ids, seen, errors)
        if mapping is not None:
            mappings.append(mapping)
    return mappings


def _load_binding(
    record: dict[str, object],
    catalogue_ids: set[str],
    real_source_ids: set[str],
    engine_source_ids: set[str],
    seen: set[str],
    errors: list[str],
) -> ClassBinding | None:
    game_class = _text(record.get("game_class"))
    where = f"class binding {game_class or '<none>'}"
    ok = True

    if game_class is None:
        errors.append(f"{where}: game_class is required")
        ok = False
    elif game_class in seen:
        errors.append(
            f"{where}: duplicate game_class; one game class binds to one "
            "catalogue entry"
        )
        return None
    else:
        seen.add(game_class)

    class_token = record.get("class_token")
    if not isinstance(class_token, str):
        errors.append(f"{where}: class_token must be a string")
        ok = False

    cid = _text(record.get("catalogue_id"))
    if cid is None:
        errors.append(f"{where}: catalogue_id is required")
        ok = False
    elif cid not in catalogue_ids:
        errors.append(f"{where}: unknown catalogue_id {cid}")
        ok = False

    grade = record.get("grade")
    grade_ok = isinstance(grade, str) and grade in CLASS_MAP_GRADES
    if not grade_ok:
        errors.append(f"{where}: grade must be one of {sorted(CLASS_MAP_GRADES)}")
        ok = False

    source_id = _text(record.get("identity_source"))
    if source_id is None:
        errors.append(
            f"{where}: identity_source is required; a binding needs a "
            "real-world or class-table source"
        )
        ok = False
    elif source_id in real_source_ids:
        pass
    elif source_id in engine_source_ids and grade == "claimed":
        pass
    else:
        errors.append(
            f"{where}: identity_source {source_id} is not a real-world or "
            "class-table source at grade claimed"
        )
        ok = False

    evidence = _text(record.get("identity_evidence"))
    if evidence is None:
        errors.append(f"{where}: identity_evidence is required")
        ok = False

    if not ok:
        return None
    return ClassBinding(
        game_class=game_class or "",
        class_token=class_token if isinstance(class_token, str) else "",
        catalogue_id=cid or "",
        identity_source=source_id or "",
        identity_evidence=evidence or "",
        grade=grade if isinstance(grade, str) else "",
        note=_text(record.get("note")) or "",
        source_file="class_bindings.json",
    )


def _load_bindings(
    data_dir: Path,
    catalogue_ids: set[str],
    real_source_ids: set[str],
    engine_source_ids: set[str],
    errors: list[str],
) -> list[ClassBinding]:
    bindings: list[ClassBinding] = []
    path = data_dir / "class_bindings.json"
    if not path.is_file():
        return bindings
    loaded = _read_json(path, errors)
    records = _sequence(loaded)
    if records is None:
        if loaded is not None:
            errors.append("class_bindings.json: must be a top-level array")
        return bindings
    seen: set[str] = set()
    for raw in records:
        record = _mapping(raw)
        if record is None:
            errors.append("class binding entry: must be an object")
            continue
        binding = _load_binding(
            record, catalogue_ids, real_source_ids, engine_source_ids, seen, errors
        )
        if binding is not None:
            bindings.append(binding)
    return bindings


def load(
    data_dir: Path,
    *,
    real_source_ids: Collection[str] | None = None,
    profile: Profile = GROUND_PROFILE,
) -> CatalogueLoad:
    """Load the catalogue, the class map and the class bindings.

    ``real_source_ids`` names the source ids that can act as a mapping source.
    When it is None, the loader reads ``sources.json`` and takes the real-world
    types. A missing catalogue directory, class map or bindings file loads as an
    empty list. ``profile`` selects the type enum, the runtime sets and the
    named derivations. It defaults to the ground profile, so every existing
    caller is unchanged.
    """
    errors: list[str] = []
    warnings: list[str] = []
    entries = _load_entries(data_dir, profile, errors)
    catalogue_ids = {entry.catalogue_id for entry in entries}
    if real_source_ids is None:
        real_ids = _real_source_ids(data_dir, errors)
        engine_ids = _engine_source_ids(data_dir, errors)
    else:
        real_ids = set(real_source_ids)
        engine_ids = _engine_source_ids(data_dir, errors)
    mappings = _load_mappings(data_dir, catalogue_ids, real_ids, errors)
    bindings = _load_bindings(data_dir, catalogue_ids, real_ids, engine_ids, errors)
    alias_index = _build_alias_index(entries, warnings)
    return CatalogueLoad(entries, mappings, alias_index, warnings, errors, bindings)
