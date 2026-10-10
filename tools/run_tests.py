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

# Every external command is bounded so a hung suite fails fast instead of
# blocking the sweep forever.  Override with AEE_TEST_TIMEOUT when a suite
# legitimately needs longer than the default.
CMD_TIMEOUT_S = float(os.environ.get("AEE_TEST_TIMEOUT", "1800"))


def run(cmd, cwd=ROOT):
    print(f"$ {cmd}", flush=True)
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, timeout=CMD_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {CMD_TIMEOUT_S:.0f}s: {cmd}")
        return 124
    return result.returncode


def main():
    fast = "--fast" in sys.argv
    suites = [
        "tools/tests/test_physics.py",
        "tools/tests/test_mobility.py",
        "tools/tests/test_fuel_consumption.py",
        "tools/tests/test_soil_strength.py",
        "tools/tests/test_terrain_limits.py",
        "tools/tests/test_terrain_drag.py",
        "tools/tests/test_vehicle_geometry.py",
        "tools/tests/test_rollover.py",
        "tools/tests/test_trig_units.py",
        "tools/tests/test_physiology.py",
        "tools/tests/test_radio.py",
        "tools/tests/test_emp.py",
        "tools/tests/test_em_propagation.py",
        "tools/tests/test_radio_terrain.py",
        "tools/tests/test_acoustic_propagation.py",
        "tools/tests/test_radar.py",
        "tools/tests/test_environmental.py",
        "tools/tests/test_scalar_advection.py",
        "tools/tests/test_dense_gas.py",
        "tools/tests/test_blowing_snow.py",
        "tools/tests/test_addon_dependencies.py",
        "tools/tests/test_ground_frost.py",
        "tools/tests/test_orphan_wiring.py",
        "tools/tests/test_atmos.py",
        "tools/tests/test_weather_front.py",
        "tools/tests/test_volcanic.py",
        "tools/tests/test_atmospheric_refraction.py",
        "tools/tests/test_optical_phenomena.py",
        "tools/tests/test_maritime.py",
        "tools/tests/test_underwater_light.py",
        "tools/tests/test_internal_waves.py",
        "tools/tests/test_ship_motion.py",
        "tools/tests/test_underwater_acoustics.py",
        "tools/tests/test_thermal_optics.py",
        "tools/tests/test_thermal_optics_config.py",
        "tools/tests/test_thermal_display_mkk.py",
        "tools/tests/test_thermal_prewarm.py",
        "tools/tests/test_thermal_heat_sources.py",
        "tools/tests/test_thermal_selection_walk.py",
        "tools/tests/test_visual_pipeline_audit.py",
        "tools/tests/test_astronomical.py",
        "tools/tests/test_docker_isolation.py",
        "tools/tests/test_fd_limit_guard.py",
        "tools/tests/test_p79_probe_contract.py",
        "tools/tests/test_sim_clock.py",
        "tools/tests/test_sim_clock_guard.py",
        "tools/tests/test_kernel_split.py",
        "tools/tests/test_kernel_parity.py",
        "tools/tests/test_biome.py",
        "tools/tests/test_biome_dynamic.py",
        "tools/tests/test_propellant_temp.py",
        "tools/tests/test_sleep_model.py",
        "tools/tests/test_shooter_stability.py",
        # Global sensitivity analysis of the two models above (SALib). Skips
        # where SALib is absent; CI installs the pinned version.
        "tools/tests/test_sensitivity.py",
        "tools/tests/test_suppression_psychology.py",
        "tools/tests/test_cold_weather.py",
        "tools/tests/test_dynamics.py",
        "tools/tests/test_dynamic_stars.py",
        "tools/tests/test_eye_adaptation.py",
        "tools/tests/test_image_realism.py",
        "tools/tests/test_vision_model.py",
        "tools/tests/test_color_temperature.py",
        "tools/tests/test_star_catalog.py",
        "tools/tests/test_star_brightness.py",
        "tools/tests/test_meteors.py",
        "tools/tests/test_trajectories.py",
        "tools/tests/test_compat.py",
        "tools/tests/test_compat_directions.py",
        "tools/tests/test_ownership_sentinels.py",
        "tools/tests/test_extension_contract.py",
        "tools/tests/test_engine_overrides.py",
        "tools/tests/test_magazine_masses.py",
        "tools/tests/test_magazine_mass_engine.py",
        "tools/tests/test_physx_mass_surface.py",
        "tools/tests/test_physx_gated_surface.py",
        "tools/tests/test_aircraft_sources.py",
        "tools/tests/test_probe_numbers.py",
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
        "tools/tests/test_acoustic_masking.py",
        "tools/tests/test_gloc.py",
        "tools/tests/test_two_node.py",
        "tools/tests/test_sqf_two_node.py",
        "tools/tests/test_oxygen_delivery.py",
        "tools/tests/test_ground_node_stack.py",
        "tools/tests/test_water_thermal.py",
        "tools/tests/test_wet_ground.py",
        "tools/tests/test_audit_189.py",
        "tools/tests/test_frost.py",
        # Frost heave: the in-situ expansion and the ice-lens segregation
        # (aee-frost-heave, issue #20).
        "tools/tests/test_frost_heave.py",
        "tools/tests/test_seismic.py",
        "tools/tests/test_geolocation.py",
        "tools/tests/test_geo_positioning.py",
        "tools/tests/test_mgrs.py",
        "tools/tests/test_mgrs_map_layer.py",
        "tools/tests/test_gnss.py",
        "tools/tests/test_material.py",
        "tools/tests/test_equipment_classifier.py",
        "tools/tests/test_device_values.py",
        "tools/tests/test_cbrn.py",
        "tools/tests/test_cbrn_plume.py",
        "tools/tests/test_device_coverage.py",
        "tools/tests/test_device_wiring.py",
        "tools/tests/test_device_runtime.py",
        "tools/tests/test_wiring_orphans.py",
        "tools/tests/test_ammo_database.py",
        "tools/tests/test_ballistic_drag.py",
        "tools/tests/test_supersonic_trace.py",
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
        # Aircraft suites: test_aircraft catalogue, runtime, corpus and coverage.
        "tools/tests/test_aircraft_catalogue.py",
        "tools/tests/test_runtime_aircraft.py",
        "tools/tests/test_aircraft_corpus.py",
        "tools/tests/test_aircraft_coverage.py",
        "tools/tests/test_aircraft_roster.py",
        "tools/tests/test_aircraft_systems.py",
        "tools/tests/test_aircraft_systems_lookup.py",
        "tools/tests/test_aircraft_systems_runtime.py",
        "tools/tests/test_systems_contract.py",
        "tools/tests/test_vehicle_mass_model.py",
        "tools/tests/test_vehicle_mass_estimate.py",
        "tools/tests/test_vehicle_mass_separation.py",
        "tools/tests/test_class_bindings.py",
        "tools/tests/test_physics_config.py",
        "tools/tests/test_ship_mass_schema.py",
        "tools/tests/test_mass_gap_sources.py",
        "tools/tests/test_mass_calibration.py",
        "tools/tests/test_mass_config.py",
        "tools/tests/test_vehicle_classify.py",
        "tools/tests/test_identity_bands.py",
        "tools/tests/test_localize_guard.py",
        "tools/tests/test_config_docs.py",
        "tools/tests/test_engine_hdr_config.py",
        "tools/tests/test_world_lighting_matcher.py",
        "tools/tests/test_weather_grain.py",
        "tools/tests/test_shadow_distance.py",
        "tools/tests/test_weather_particles.py",
        "tools/tests/test_scent_dispersion.py",
        "tools/tests/test_settings_taxonomy.py",
        "tools/tests/test_ltm.py",
        "tools/tests/test_film_grain_invariant.py",
        "tools/tests/test_hud.py",
        "tools/tests/test_fusion_hud.py",
        "tools/tests/test_fusion_display_guard.py",
        "tools/tests/test_audit_regressions.py",
        "tools/tests/test_cross_module_validator.py",
        "tools/tests/test_night_sky_debug.py",
        "tools/tests/test_nvg_imperfections.py",
        "tools/tests/test_ai.py",
        "tools/tests/test_ai_hearing.py",
        "tools/tests/test_ai_survival.py",
        "tools/tests/test_wildlife.py",
        "tools/tests/test_wildlife_ecology.py",
        "tools/tests/test_rpt_regressions.py",
        "tools/tests/test_ai_wildlife_soak.py",
        "tools/tests/test_sqf_nil_reads.py",
        "tools/tests/test_pfh_contract.py",
        "tools/tests/test_flight_physics.py",
        "tools/tests/test_fixed_wing.py",
        "tools/tests/test_mobility_pfh.py",
        # Observability and perception (aee-observability-and-perception).
        "tools/tests/test_debug_index.py",
        "tools/tests/raw_diag_allowlist.py",
        "tools/tests/test_debug_guard.py",
        "tools/tests/test_per_frame_log_guard.py",
        "tools/tests/test_dump_state_contract.py",
        "tools/tests/test_invariant_table.py",
        "tools/tests/test_consistency_evaluator.py",
        "tools/tests/test_consistency_log_level.py",
        "tools/tests/test_pp_handle_unique.py",
        "tools/tests/test_camera_contract.py",
        "tools/tests/test_producer_contract.py",
        "tools/tests/test_perception_sample.py",
        "tools/tests/test_perception_adaptation.py",
        "tools/tests/test_perception_deviation.py",
        "tools/tests/test_perception_contracts.py",
        # The runner itself bounds every command (test_run_tests_timeout.py).
        "tools/tests/test_run_tests_timeout.py",
        # Terrain and map-feature symbols (aee-map-feature-overhaul).
        "tools/tests/test_terrain.py",
        # The map QA matrix and its machine checks (aee-map-realism-polish).
        "tools/tests/test_map_qa.py",
        # Map symbology: the derived engine marker mapping (ADR-029).
        "tools/tests/test_symbology.py",
        # The dynamic variation families (aee-dynamic-variation-system).
        "tools/tests/test_variation.py",
        "tools/tests/test_variation_ui.py",
        "tools/tests/test_symbology_live.py",
        "tools/tests/test_symbology_catalogue.py",
        "tools/tests/test_marker_derivation.py",
        "tools/tests/test_cba_settings.py",
        "tools/tests/test_settings_migration.py",
        # Dormant suites registered by the conformance sweep (ADR-031). Each was
        # on disk but not registered, so CI never ran it. Eight more stay on the
        # test_suite_registration allowlist with a recorded reason.
        "tools/tests/test_app6_catalogue.py",
        "tools/tests/test_armour.py",
        "tools/tests/test_biome_rotation.py",
        "tools/tests/test_capability_matrix.py",
        "tools/tests/test_chambering.py",
        "tools/tests/test_clothing.py",
        "tools/tests/test_collision_damage.py",
        "tools/tests/test_complaint_landscape.py",
        "tools/tests/test_config_inheritance.py",
        "tools/tests/test_engine_event_wiring.py",
        "tools/tests/test_equipment_values.py",
        "tools/tests/test_frost_supersession.py",
        "tools/tests/test_fx_supersonic_trace.py",
        "tools/tests/test_groundwater.py",
        "tools/tests/test_hail_damage.py",
        "tools/tests/test_hydrology.py",
        "tools/tests/test_erosion.py",
        "tools/tests/test_inventory_load.py",
        "tools/tests/test_movement_speed.py",
        "tools/tests/test_nvg_audit.py",
        "tools/tests/test_nvg_fusion.py",
        "tools/tests/test_outline_overlay.py",
        "tools/tests/test_parse_caliber.py",
        "tools/tests/test_particle_array_spec.py",
        "tools/tests/test_pm_coverage.py",
        "tools/tests/test_qa_core_stack.py",
        "tools/tests/test_read_state.py",
        "tools/tests/test_runtime_cartridges.py",
        "tools/tests/test_runtime_projectiles.py",
        "tools/tests/test_runtime_weapons.py",
        "tools/tests/test_stability.py",
        "tools/tests/test_stefan_coefficient.py",
        "tools/tests/test_surface_type_normalisation.py",
        "tools/tests/test_symbology_modifiers.py",
        "tools/tests/test_symbology_taxonomy.py",
        "tools/tests/test_terrain_catalogue.py",
        "tools/tests/test_vehicle_bindings_order.py",
        "tools/tests/test_vehicle_catalogue.py",
        "tools/tests/test_vehicle_mass_accuracy.py",
        "tools/tests/test_vehicle_sources.py",
        "tools/tests/test_wind_engine_push.py",
        "tools/tests/test_work_distribution.py",
        # Conformance meta-gates (ADR-031): suite registration and ADR numbering.
        "tools/tests/test_suite_registration.py",
        "tools/tests/test_adr_numbers.py",
        # Dynamic identifier allocation: the next free ADR number and probe
        # tag, derived so concurrent worktrees never collide.
        "tools/tests/test_next_id.py",
        # Engine reference: the docs/engine index and its portability rule.
        "tools/tests/test_engine_docs.py",
        # Interface control documents: freshness, index and grounding.
        "tools/tests/test_icd_docs.py",
        # Dev harness release exclusion, part (a). Part (b) runs in the full
        # sweep only (see RELEASE_SUITES) because it needs a release tree.
        "tools/tests/test_dev_harness_release_exclusion.py",
        "tools/tests/test_dev_harness_gate.py",
        "tools/tests/test_dev_harness_dispatch.py",
        "tools/tests/test_dev_console_contract.py",
        # The console command contract doc is generated, never hand-synced.
        "tools/tests/test_dev_console_contract_doc.py",
        # Probe batching: every probe has a run class, and every console fact
        # keeps a probe file behind it (ADR-035).
        "tools/tests/test_probe_classification.py",
        "tools/tests/test_console_fact_gating.py",
        # Visual workbench: keybinds, re-apply, screenshot and state dump.
        "tools/tests/test_dev_workbench.py",
    ]
    # Part (b) needs a `hemtt release` tree, so it runs in the full sweep only.
    release_suites = [
        "tools/tests/test_dev_harness_release_exclusion.py",
    ]
    # Only run suites that exist (module suites are added incrementally).
    existing = [s for s in suites if os.path.exists(os.path.join(ROOT, s))]
    if not fast:
        existing = [s for s in existing if s not in release_suites]
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
        print("\n--- Release-artefact proof ---")
        for suite in release_suites:
            failed += run(f"{python} -m unittest {suite} -v")
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
