#!/usr/bin/env python3
"""AEE test runner — runs every unit suite and the physics validation harness.

Usage:
    python3 tools/run_tests.py            # full sweep
    python3 tools/run_tests.py --fast     # unit suites only (no validation harness)
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(cmd, cwd=ROOT):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    return result.returncode


def main():
    fast = "--fast" in sys.argv
    suites = [
        "tools/tests/test_physics.py",
        "tools/tests/test_mobility.py",
        "tools/tests/test_soil_strength.py",
        "tools/tests/test_terrain_limits.py",
        "tools/tests/test_terrain_drag.py",
        "tools/tests/test_vehicle_geometry.py",
        "tools/tests/test_rollover.py",
        "tools/tests/test_physiology.py",
        "tools/tests/test_radio.py",
        "tools/tests/test_environmental.py",
        "tools/tests/test_blowing_snow.py",
        "tools/tests/test_addon_dependencies.py",
        "tools/tests/test_ground_frost.py",
        "tools/tests/test_atmos.py",
        "tools/tests/test_atmospheric_refraction.py",
        "tools/tests/test_maritime.py",
        "tools/tests/test_thermal_optics.py",
        "tools/tests/test_visual_pipeline_audit.py",
        "tools/tests/test_astronomical.py",
        "tools/tests/test_biome.py",
        "tools/tests/test_biome_dynamic.py",
        "tools/tests/test_propellant_temp.py",
        "tools/tests/test_sleep_model.py",
        "tools/tests/test_shooter_stability.py",
        "tools/tests/test_cold_weather.py",
        "tools/tests/test_dynamics.py",
        "tools/tests/test_trajectories.py",
        "tools/tests/test_compat.py",
        "tools/tests/test_optics_vision.py",
        "tools/tests/test_blast.py",
        "tools/tests/test_diving.py",
        "tools/tests/test_particles.py",
        "tools/tests/test_particle_engine.py",
        "tools/tests/test_perf_counters.py",
        "tools/tests/test_barrel_thermal.py",
        "tools/tests/test_local_wind.py",
        "tools/tests/test_wet_traction.py",
        "tools/tests/test_ice_avalanche.py",
        "tools/tests/test_concealment.py",
        "tools/tests/test_gloc.py",
        "tools/tests/test_two_node.py",
        "tools/tests/test_sqf_two_node.py",
        "tools/tests/test_ground_node_stack.py",
        "tools/tests/test_water_thermal.py",
        "tools/tests/test_wet_ground.py",
        "tools/tests/test_audit_189.py",
        "tools/tests/test_frost.py",
        "tools/tests/test_geolocation.py",
        "tools/tests/test_material.py",
        "tools/tests/test_equipment_classifier.py",
        "tools/tests/test_device_values.py",
        "tools/tests/test_cbrn.py",
        "tools/tests/test_device_coverage.py",
        "tools/tests/test_device_wiring.py",
        "tools/tests/test_ammo_database.py",
        "tools/tests/test_ballistic_drag.py",
        "tools/tests/test_interior_ballistics.py",
        "tools/tests/test_ballistic_coefficient.py",
        "tools/tests/test_armour_database.py",
        "tools/tests/test_derivation.py",
        "tools/tests/test_vehicle_weapons.py",
        "tools/tests/test_engine_bridges.py",
        "tools/tests/test_vehicle_inventory.py",
        "tools/tests/test_vehicle_corpus.py",
        "tools/tests/test_vehicle_coverage.py",
        "tools/tests/test_runtime_vehicles.py",
        "tools/tests/test_vehicle_mass_model.py",
        "tools/tests/test_vehicle_mass_estimate.py",
        "tools/tests/test_vehicle_mass_separation.py",
    ]
    # Only run suites that exist (module suites are added incrementally).
    existing = [s for s in suites if os.path.exists(os.path.join(ROOT, s))]
    if not existing:
        print("No test suites found under tools/tests/")
        return 1

    # Prefer the venv when present so the optional-library checks run.
    python = os.path.join(ROOT, "tools/validation/.venv/bin/python")
    if not os.path.exists(python):
        python = "python3"

    failed = 0
    for suite in existing:
        failed += run(f"{python} -m unittest {suite} -v")
    if not fast:
        print("\n--- Physics validation harness ---")
        failed += run(
            f"{python} {os.path.join(ROOT, 'tools/validation/validate_physics.py')}"
        )
        print("\n--- Post-process effect safety audit ---")
        failed += run(f"{python} tools/validation/audit_pp_effects.py")

    if failed:
        print("\nFAILED: one or more test suites exited non-zero.")
        return 1
    print("\nALL TESTS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
