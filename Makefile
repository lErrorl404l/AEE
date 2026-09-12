.PHONY: check build release test lint clean

check:
	hemtt check -p -e

build:
	hemtt build

release:
	hemtt release

test:
	python3 -m unittest discover -s tools/tests

lint:
	python3 tools/sqf_validator.py addons/
	python3 tools/check_strings.py
	python3 tools/config_style_checker.py addons/

clean:
	rm -rf .hemttout/ releases/ @aee/
