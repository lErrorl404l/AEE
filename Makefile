.PHONY: data check build release test dev lint lint-parity clean

# Rebuild the verified ballistics database and its runtime projections.
# Adding a source and running this one target updates the in-game values.
data:
	tools/build_ballistics_data.sh

check:
	tools/hemtt.sh check -p -e

build:
	tools/hemtt.sh build

release:
	tools/hemtt.sh release

test:
	python3 -m unittest discover -s tools/tests

# Build the standalone dev project, then print the dev console health URL and
# the command that starts the server with the console. The dev project lives
# outside the main HEMTT project, so `make lint`, `make release` and CI never
# depend on it.
dev:
	bash tools/dev-harness/build.sh
	@echo "dev console health: http://127.0.0.1:7788/health"
	@echo "build the extension: bash tools/dev-harness/extension/build.sh linux"
	@echo "start the server with the console: AEE_DEV=1 tools/docker_test.sh --console"

# Run EVERY check CI runs, and report ALL failures: a failing line does not
# stop the sweep, so a later broken gate is visible in one run.  Generated
# from .github/workflows/ci.yml so the two cannot drift: a local gate set
# narrower than CI is not a gate, and a red build shipped because of it on
# 2026-09-23.
lint: lint-parity
	@rc=0; \
	python3 tools/sqf_validator.py || rc=1; \
	python3 tools/config_style_checker.py || rc=1; \
	python3 tools/check_strings.py || rc=1; \
	python3 tools/stringtable_validator.py || rc=1; \
	python3 tools/run_tests.py --fast || rc=1; \
	python3 tools/validation/validate_physics.py || rc=1; \
	python3 tools/validation/validate_sensors.py || rc=1; \
	python3 tools/validation/validate_illuminance.py || rc=1; \
	python3 tools/validation/validate_dof.py || rc=1; \
	python3 tools/validation/validate_astronomical.py || rc=1; \
	python3 tools/validation/validate_cba_settings.py || rc=1; \
	python3 tools/validation/validate_biome_plausible.py --self-check || rc=1; \
	python3 tools/validation/fix_current_unit_guard.py || rc=1; \
	python3 tools/validation/validate_cross_module.py || rc=1; \
	python3 tools/validation/check_macro_quoting.py || rc=1; \
	python3 tools/validation/validate_oracles.py || rc=1; \
	python3 tools/validation/validate_physics_config.py || rc=1; \
	python3 tools/validation/gen_physics_config.py --check || rc=1; \
	python3 tools/validation/gen_star_catalog.py --check || rc=1; \
	python3 tools/validation/gen_meteor_showers.py --check || rc=1; \
	python3 tools/validation/gen_vehicle_class_inventory.py --check || rc=1; \
	python3 tools/validation/gen_vehicle_data.py --check || rc=1; \
	python3 tools/validation/gen_vehicle_coverage.py --check || rc=1; \
	python3 tools/validation/validate_vehicle_data.py || rc=1; \
	python3 tools/validation/validate_ballistics_data.py || rc=1; \
	python3 tools/validation/gen_vehicle_mass_model.py --check || rc=1; \
	python3 tools/validation/validate_vehicle_mass_model.py || rc=1; \
	python3 tools/validation/validate_mass_calibration.py || rc=1; \
	python3 tools/validation/gen_aircraft_data.py --check || rc=1; \
	python3 tools/validation/gen_aircraft_coverage.py --check || rc=1; \
	python3 tools/validation/validate_aircraft_data.py || rc=1; \
	python3 tools/validation/gen_thermal_optics.py --check || rc=1; \
	python3 tools/validation/gen_engine_overrides.py --check || rc=1; \
	python3 tools/validation/validate_engine_overrides.py || rc=1; \
	python3 tools/validation/gen_debug_index.py --check || rc=1; \
	python3 tools/validation/gen_mgrs_tables.py --check || rc=1; \
	python3 tools/validation/validate_mgrs.py || rc=1; \
	python3 tools/validation/gen_symbology_tables.py --check || rc=1; \
	python3 tools/validation/validate_symbology.py || rc=1; \
	python3 tools/validation/validate_symbology_colour.py || rc=1; \
	python3 tools/gen_symbology_catalogue.py --check || rc=1; \
	python3 tools/gen_symbology_catalogue.py --verify-svg || rc=1; \
	python3 tools/validation/validate_symbology_catalogue.py || rc=1; \
	python3 tools/validation/gen_terrain_tables.py --check || rc=1; \
	python3 tools/validation/validate_terrain.py || rc=1; \
	python3 tools/gen_terrain_symbols.py --check || rc=1; \
	python3 tools/validation/validate_terrain_symbols.py || rc=1; \
	python3 tools/validation/validate_terrain_alpha.py || rc=1; \
	python3 tools/validation/validate_terrain_provenance.py || rc=1; \
	python3 tools/gen_terrain_catalogue.py --check || rc=1; \
	python3 tools/gen_app6_catalogue.py --check || rc=1; \
	python3 tools/gen_compat_directions.py --check || rc=1; \
	python3 tools/gen_ownership_sentinels.py --check || rc=1; \
	python3 tools/gen_extension_contract.py --check || rc=1; \
	python3 tools/gen_dev_console_contract.py --check || rc=1; \
	python3 tools/gen_kernel_table.py --check || rc=1; \
	python3 tools/tests/test_sim_clock_guard.py || rc=1; \
	python3 tools/tests/test_kernel_split.py || rc=1; \
	python3 tools/validation/gen_wildlife_ecology.py --check || rc=1; \
	python3 tools/validation/validate_wildlife_ecology.py || rc=1; \
	python3 tools/tests/test_suite_registration.py || rc=1; \
	python3 tools/tests/test_adr_numbers.py || rc=1; \
	python3 tools/tests/test_engine_docs.py || rc=1; \
	if [ $$rc -ne 0 ]; then echo "LINT: one or more checks FAILED"; fi; \
	exit $$rc

# Fail when the lint target and the CI workflow disagree, so a new CI check
# cannot be added without a matching local one.
lint-parity:
	python3 tools/validation/check_lint_parity.py

clean:
	rm -rf .hemttout/ releases/ @aee/
