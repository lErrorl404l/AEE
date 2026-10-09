#!/usr/bin/env python3
"""Generate the wildlife ecology corpus and asset map from the data corpus.

The wildlife corpus holds one entry per real species group. An entry carries
an activity class, a season rule, a temperature band, a wind and rain rule, a
habitat rule, a temporal pattern, a sound group and a source grade per field.
This generator reads the corpus and writes two SQF files:

  addons/wildlife/data/ecology_corpus.sqf  the species-group rows
  addons/wildlife/data/asset_map.sqf       the sound and fauna identity rows

The generated files are data tables. The pure matcher
aee_wildlife_fnc_getSpeciesMatch reads the ecology corpus. The sound map
reads the asset map. CBA PREP compiles the data files; no function lives
here.

The order is by id, so the output is byte-stable. The `--check` mode writes
nothing and returns 1 when an on-disk file differs from a fresh render.

Run:  python3 tools/validation/gen_wildlife_ecology.py
      python3 tools/validation/gen_wildlife_ecology.py --data-dir PATH
      python3 tools/validation/gen_wildlife_ecology.py --check
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path

_REPO = Path(__file__).parents[2]

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "wildlife"
ECO_OUT = ROOT / "addons" / "wildlife" / "data" / "ecology_corpus.sqf"
ASSET_OUT = ROOT / "addons" / "wildlife" / "data" / "asset_map.sqf"

# The generated-file notice, copied from the shape at
# addons/vehicles/functions/fnc_getVehicleMatch.sqf:7-9.
ECO_TEMPLATE = """/*
Wildlife ecology corpus (generated).

This file is GENERATED. The generator tools/validation/gen_wildlife_ecology.py
writes it from the validated wildlife corpus under data/wildlife/. Do not
edit it by hand. Edit the corpus and regenerate it.

One row per species group, sorted by group id. A row has fourteen columns:

  0  family           string, a Koppen family or an overlay
  1  group_id         string, the stable corpus key
  2  taxa             array of strings
  3  activity         string, "diurnal", "nocturnal" or "crepuscular"
  4  season_months    array of month numbers, 1 to 12
  5  temp_band        array [min_c, max_c]
  6  wind_rule        array [limit_ms, suppression]
  7  rain_rule        array [limit, suppression, triggers]
  8  gregariousness   string
  9  habitat_weights  array [foliage, surface, water, structures], each 0 to 1
  10 temporal_bins    array of seven weights, each 0 to 1
  11 dolbear          bool, the Dolbear shortcut drives the rate
  12 sound_group      string, a key in asset_map.sqf
  13 grade            string, the group source grade

The seven temporal bins, in order, are pre_dawn, dawn, morning, midday,
afternoon, dusk and night. The pure matcher aee_wildlife_fnc_getSpeciesMatch
reads this table. The Dolbear shortcut is the only cricket rate source.
*/
[
__ROWS__
]
"""

ASSET_TEMPLATE = """/*
Wildlife asset map (generated).

This file is GENERATED. The generator tools/validation/gen_wildlife_ecology.py
writes it from the validated wildlife corpus under data/wildlife/. Do not
edit it by hand. Edit the corpus and regenerate it.

One row per sound group and per faunal group, sorted by kind then id. A row
has six columns:

  0 kind           string, "sound" or "fauna"
  1 id             string, the sound-group key or the family key
  2 identity       string, "CONFIRMED", "UNCONFIRMED" or "UNKNOWN"
  3 media          array of strings, a raw a3 path or a CfgSFX class
  4 fauna_classes  array of vanilla CfgVehicles Animals classes
  5 species        string, empty when the recording is not given a species

A media string with a dot is a raw vanilla .wss file. A media string without
a dot is a vanilla CfgSFX class. An UNKNOWN or UNCONFIRMED recording is
never given a species. The sound map aee_wildlife_fnc_speciesSound reads
this table.
*/
[
__ROWS__
]
"""


def _sqf(value: object) -> str:
    """Render one SQF literal. A string is quoted with doubled quotes."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_sqf(item) for item in value) + "]"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _row(items: Sequence[object]) -> str:
    return "    " + _sqf(list(items))


def load_corpus(data_dir: Path) -> tuple[dict[str, object], dict[str, object]]:
    ecology = json.loads((data_dir / "ecology.json").read_text(encoding="utf-8"))
    asset_map = json.loads((data_dir / "asset_map.json").read_text(encoding="utf-8"))
    return ecology, asset_map


def ecology_rows(ecology: dict[str, object]) -> list[list[object]]:
    """Flatten every species group into one fourteen-column row."""
    rows: list[list[object]] = []
    families = ecology.get("families", [])
    assert isinstance(families, list)
    for family in families:
        assert isinstance(family, dict)
        for group in family.get("groups", []):
            assert isinstance(group, dict)
            season = group["season"]
            temp = group["temperature_c"]
            wind = group["wind"]
            rain = group["rain"]
            habitat = group["habitat"]
            temporal = group["temporal"]
            rows.append(
                [
                    group["family"],
                    group["group_id"],
                    list(group["taxa"]),
                    group["activity"],
                    list(season["months"]),
                    [temp["min"], temp["max"]],
                    [wind["limit_ms"], wind["suppression"]],
                    [rain["limit"], rain["suppression"], bool(rain["triggers"])],
                    group["gregariousness"],
                    [
                        habitat["foliage"],
                        habitat["surface"],
                        habitat["water"],
                        habitat["structures"],
                    ],
                    list(temporal["bins"]),
                    bool(temporal["dolbear"]),
                    group["sound_group"],
                    group["grade"],
                ]
            )
    rows.sort(key=lambda row: str(row[1]))
    return rows


def asset_rows(asset_map: dict[str, object]) -> list[list[object]]:
    """Flatten every sound group and faunal group into a six-column row."""
    rows: list[list[object]] = []
    for entry in asset_map.get("sound_groups", []):
        assert isinstance(entry, dict)
        media: list[str] = []
        for item in entry.get("media", []):
            assert isinstance(item, dict)
            if "path" in item:
                media.append(str(item["path"]))
            elif "cfg_sfx" in item:
                media.append(str(item["cfg_sfx"]))
        species = entry.get("species")
        rows.append(
            [
                "sound",
                entry["sound_group"],
                entry["identity"],
                media,
                list(entry.get("fauna_classes", [])),
                "" if species is None else str(species),
            ]
        )
    for entry in asset_map.get("faunal_groups", []):
        assert isinstance(entry, dict)
        rows.append(
            [
                "fauna",
                entry["fauna_group"],
                entry["identity"],
                [],
                list(entry.get("classes", [])),
                "",
            ]
        )
    rows.sort(key=lambda row: (str(row[0]), str(row[1])))
    return rows


def render(rows: Sequence[Sequence[object]], template: str) -> str:
    body = ",\n".join(_row(row) for row in rows)
    return template.replace("__ROWS__", body)


def render_ecology(ecology: dict[str, object]) -> str:
    return render(ecology_rows(ecology), ECO_TEMPLATE)


def render_asset(asset_map: dict[str, object]) -> str:
    return render(asset_rows(asset_map), ASSET_TEMPLATE)


def write_outputs(data_dir: Path = DEFAULT_DATA) -> tuple[int, int]:
    """Write both generated files. Returns the two row counts."""
    ecology, asset_map = load_corpus(data_dir)
    eco = ecology_rows(ecology)
    asset = asset_rows(asset_map)
    ECO_OUT.write_text(render(eco, ECO_TEMPLATE), encoding="utf-8")
    ASSET_OUT.write_text(render(asset, ASSET_TEMPLATE), encoding="utf-8")
    return len(eco), len(asset)


def check_outputs(data_dir: Path = DEFAULT_DATA) -> int:
    """Return 0 when every generated file matches a fresh render.

    Check mode writes nothing. A missing or stale file returns 1, so a stale
    generated corpus fails the gate.
    """
    ecology, asset_map = load_corpus(data_dir)
    expected = {
        ECO_OUT: render_ecology(ecology),
        ASSET_OUT: render_asset(asset_map),
    }
    stale = False
    for path, text in expected.items():
        if not path.is_file():
            print(f"wildlife ecology: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"wildlife ecology: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(
        f"wildlife ecology: {len(ecology_rows(ecology))} species-group rows and "
        f"{len(asset_rows(asset_map))} asset rows -> {ECO_OUT.name} and "
        f"{ASSET_OUT.name} (fresh)"
    )
    return 0


def main(argv: Sequence[str]) -> int:
    data_dir = DEFAULT_DATA
    if "--data-dir" in argv:
        index = argv.index("--data-dir")
        if index + 1 < len(argv):
            data_dir = Path(argv[index + 1])
    if "--check" in argv:
        return check_outputs(data_dir)
    eco, asset = write_outputs(data_dir)
    print(
        f"wildlife ecology: {eco} species-group rows and {asset} asset rows, "
        f"wrote {ECO_OUT.name} and {ASSET_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
