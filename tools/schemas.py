#!/usr/bin/env python3
"""Single source for every AEE artefact schema identifier.

An artefact states its own identity as ``aee.<domain>.<name>/<version>`` in
its ``schema`` field. The generator writes that field and the validator
checks it. Before this module the string was copied into every generator,
validator and test that touched the artefact, so one schema could drift
between the tool that writes it and the tool that checks it.

This module holds each identifier once. Every tool imports it. A committed
artefact keeps the emitted string as its content, but the tooling has one
definition per schema, and no other tool repeats the literal.

The version is part of the identity. A validator that must reject a foreign
version derives one with ``foreign_version`` instead of hardcoding a second
literal that could collide when the real version moves.

Run: imported by the generators, the validators and the tests. No
command-line entry point.
"""

from __future__ import annotations

# Ballistics.
BALLISTICS_MAGAZINE_MASS = "aee.ballistics.magazine_mass/1"

# Engine.
ENGINE_AMMO_BINDINGS = "aee.engine.ammo_bindings/1"
ENGINE_MAGAZINE_BINDINGS = "aee.engine.magazine_bindings/1"
ENGINE_OVERRIDES = "aee.engine.overrides/1"

# Physics.
PHYSICS_MASS_CALIBRATION = "aee.physics.mass_calibration/1"

# Vehicle.
VEHICLE_CLASS_BINDING_MAP = "aee.vehicle.class_binding_map/1"
VEHICLE_CLASS_INVENTORY = "aee.vehicle.class_inventory/1"
VEHICLE_COVERAGE = "aee.vehicle.coverage/1"
VEHICLE_MASS_ACCURACY_ABLATION = "aee.vehicle.mass_accuracy.ablation/1"
VEHICLE_MASS_ACCURACY_HOLDOUT = "aee.vehicle.mass_accuracy.holdout/1"
VEHICLE_MASS_ACCURACY_MAPPING = "aee.vehicle.mass_accuracy.mapping/1"
VEHICLE_MASS_ACCURACY_PROBE = "aee.vehicle.mass_accuracy.probe/1"
VEHICLE_MASS_MODEL = "aee.vehicle.mass_model/1"
VEHICLE_MASS_MODEL_CALIBRATION = "aee.vehicle.mass_model_calibration/1"
VEHICLE_MOD_FLEET = "aee.vehicle.mod_fleet/1"
VEHICLE_STRINGTABLE_BINDINGS = "aee.vehicle.stringtable_bindings/1"

# Aircraft.
AIRCRAFT_CLASS_INVENTORY = "aee.aircraft.class_inventory/1"
AIRCRAFT_COVERAGE = "aee.aircraft.coverage/2"

# Symbology.
SYMBOLOGY_ENGINE_MARKERS = "aee.symbology.engine_markers/1"


def foreign_version(schema: str) -> str:
    """Return a different version of ``schema`` with the same name.

    A validator proves it rejects a foreign version. The check needs a string
    of the same shape but a different version, so it derives one here. A
    hardcoded second literal would collide when the real version moves.
    """
    name, separator, version = schema.rpartition("/")
    if not separator or not version.isdigit():
        raise ValueError(f"not a versioned schema id: {schema}")
    return f"{name}/{int(version) + 1}"
