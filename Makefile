.PHONY: data check build release test lint clean

# Rebuild the verified ballistics database and its runtime projections.
# Adding a source and running this one target updates the in-game values.
data:
	tools/build_ballistics_data.sh

check:
	hemtt check -p -e

build:
	hemtt build

release:
	hemtt release

test:
	python3 -m unittest discover -s tools/tests

# Run EVERY check CI runs. Generated from .github/workflows/ci.yml so the
# two cannot drift: a local gate set that is narrower than CI is not a
# gate, and a red build shipped because of it on 2026-09-23.
lint:
	python3 tools/sqf_validator.py addons/
	python3 tools/config_style_checker.py addons/
	python3 tools/check_strings.py
	python3 tools/stringtable_validator.py
	python3 tools/run_tests.py --fast
	python3 tools/validation/validate_physics.py
	python3 tools/validation/validate_sensors.py
	python3 tools/validation/validate_illuminance.py
	python3 tools/validation/validate_dof.py
	python3 tools/validation/validate_astronomical.py
	python3 tools/validation/validate_cba_settings.py
	python3 tools/validation/validate_biome_plausible.py --self-check
	python3 tools/validation/fix_current_unit_guard.py
	python3 tools/validation/validate_cross_module.py
	python3 tools/validation/validate_oracles.py
	python3 tools/validation/check_macro_quoting.py
	python3 tools/validation/gen_vehicle_class_inventory.py --check
	python3 tools/validation/gen_vehicle_data.py --check
	python3 tools/validation/gen_vehicle_coverage.py --check
	python3 tools/validation/validate_vehicle_data.py

# Fail when the lint target and the CI workflow disagree, so a new CI check
# cannot be added without a matching local one.
lint-parity:
	python3 tools/validation/check_lint_parity.py

clean:
	rm -rf .hemttout/ releases/ @aee/
