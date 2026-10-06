#!/usr/bin/env python3
"""Generate the MGRS letter tables and resolve the world anchors.

The MGRS lettering is a small, fixed set of tables: the latitude band
letters, the 100 km column sets, the 100 km row letters, the AA row
offset, the two-character zone strings and the digit characters. This
generator reads the validated source at data/mgrs/mgrs_tables.json and
writes the runtime projection

  addons/core/data/mgrs_tables.sqf

which the kernels read as aee_core_mgrsTables.

It also resolves one geographic anchor per shipped world. It reads the
raw CfgWorlds values from data/mgrs/geo_sources.json and writes the
anchor back into the same file, computed with the same rule as the pure
builder aee_core_fnc_buildGeoAnchor.

The order is fixed, so the output is byte-stable. The `--check` mode
writes nothing and returns 1 when an on-disk file differs from a fresh
render.

Run:  python3 tools/validation/gen_mgrs_tables.py
      python3 tools/validation/gen_mgrs_tables.py --check
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]

DEFAULT_DATA = ROOT / "data" / "mgrs"
TABLES_JSON = DEFAULT_DATA / "mgrs_tables.json"
GEO_JSON = DEFAULT_DATA / "geo_sources.json"
TABLES_OUT = ROOT / "addons" / "core" / "data" / "mgrs_tables.sqf"

# The generated-file notice, in the shape of the other generated data files.
TABLES_TEMPLATE = """/*
MGRS lettering tables (generated).

This file is GENERATED. The generator tools/validation/gen_mgrs_tables.py
writes it from the validated source under data/mgrs/. Do not edit it by
hand. Edit the source and regenerate it.

The rows are, in order:

  0  band letters, C to X omitting I and O (20 letters, band 0 is 80 S)
  1  column letter sets, indexed by (zone - 1) mod 3
  2  row letters, A to V omitting I and O (20 letters, row 0 is A)
  3  even-zone row offset, the AA scheme shift (odd zones start at A)
  4  zone strings, "01" to "60"
  5  digit characters, "0" to "9"

The lettering is defined by DMA TM 8358.1, DMA TM 8358.2 and the NGA
MGRS guidance (Modified February 2009). No letter is invented: every
letter here is one of those sources.
*/
[
__ROWS__
]
"""


def _sqf(value: Any) -> str:
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


def _rows(values: list[Any]) -> str:
    return ",\n".join("    " + _sqf(v) for v in values)


def tables_rows(source: dict[str, Any]) -> list[Any]:
    """Flatten the source into the six runtime rows."""
    tables = source["tables"]
    return [
        list(tables["band_letters"]["letters"]),
        [list(s) for s in tables["column_sets"]["sets"]],
        list(tables["row_letters"]["letters"]),
        int(tables["even_zone_row_offset"]["value"]),
        list(tables["zone_strings"]["strings"]),
        list(tables["digit_characters"]["characters"]),
    ]


def render_tables(source: dict[str, Any]) -> str:
    return TABLES_TEMPLATE.replace("__ROWS__", _rows(tables_rows(source)))


def resolve_anchor(world: dict[str, Any]) -> list[Any]:
    """Resolve one world anchor. Must equal aee_core_fnc_buildGeoAnchor."""
    map_size = world.get("mapSize", 0)
    zone = world.get("mapZone", 0)
    area = world.get("mapArea", [])
    latitude = world.get("latitude", 0)
    longitude = world.get("longitude", 0)

    latitude_true = -latitude if isinstance(latitude, (int, float)) else 40
    if latitude_true == 0:
        latitude_true = 40
    longitude_val = longitude if isinstance(longitude, (int, float)) else 0

    lon_west = lat_south = lon_east = lat_north = 0
    use_map_area = False
    if (
        isinstance(area, list)
        and len(area) == 4
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in area)
    ):
        lon_west, lat_south, lon_east, lat_north = area
        if (
            lon_west < lon_east
            and lat_south < lat_north
            and -180 <= lon_west
            and lon_east <= 180
            and -90 <= lat_south
            and lat_north <= 90
        ):
            use_map_area = True

    if use_map_area:
        lat_centre = (lat_south + lat_north) / 2
        lon_centre = (lon_west + lon_east) / 2
        source = "mapArea"
    else:
        lat_centre = latitude_true
        lon_centre = longitude_val
        lon_west = lat_south = lon_east = lat_north = 0
        source = "cfgworlds"

    return [
        lat_centre,
        lon_centre,
        zone,
        map_size,
        lon_west,
        lat_south,
        lon_east,
        lat_north,
        source,
    ]


def render_geo(source: dict[str, Any]) -> str:
    """Re-render geo_sources.json with a resolved anchor per world."""
    worlds: list[dict[str, Any]] = []
    for world in source.get("worlds", []):
        anchor = resolve_anchor(world)
        record = {
            "world": world["world"],
            "config": world["config"],
            "mapSize": world["mapSize"],
            "mapZone": world["mapZone"],
            "mapArea": list(world.get("mapArea", [])),
            "latitude": world["latitude"],
            "longitude": world["longitude"],
            "anchor": anchor,
            "anchor_source": anchor[8],
        }
        worlds.append(record)
    out = {
        "retrieved": source["retrieved"],
        "note": source["note"],
        "sources": list(source.get("sources", [])),
        "worlds": worlds,
    }
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def load_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    tables = json.loads(TABLES_JSON.read_text(encoding="utf-8"))
    geo = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    return tables, geo


def write_outputs() -> tuple[int, int]:
    tables, geo = load_sources()
    TABLES_OUT.parent.mkdir(parents=True, exist_ok=True)
    TABLES_OUT.write_text(render_tables(tables), encoding="utf-8")
    GEO_JSON.write_text(render_geo(geo), encoding="utf-8")
    return len(tables_rows(tables)), len(geo.get("worlds", []))


def check_outputs() -> int:
    """Return 0 when every generated file matches a fresh render."""
    tables, geo = load_sources()
    expected = {
        TABLES_OUT: render_tables(tables),
        GEO_JSON: render_geo(geo),
    }
    stale = False
    for path, text in expected.items():
        if not path.is_file():
            print(f"mgrs tables: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"mgrs tables: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(
        f"mgrs tables: {len(tables_rows(tables))} rows and "
        f"{len(geo.get('worlds', []))} world anchors -> {TABLES_OUT.name} and "
        f"{GEO_JSON.name} (fresh)"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check_outputs()
    rows, worlds = write_outputs()
    print(
        f"mgrs tables: {rows} rows and {worlds} world anchors, wrote "
        f"{TABLES_OUT.name} and {GEO_JSON.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
