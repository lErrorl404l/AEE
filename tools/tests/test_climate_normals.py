#!/usr/bin/env python3
"""Climate normals come from real reference stations.

The runtime normals (fnc_getStationNormals) are a projection of
data/climate/station_normals.json, which transcribes each station's
published monthly normals and names the primary source.  These tests pin:

  * the generated SQF is fresh against the corpus;
  * every station's Koppen label is the class its own normals give under
    Peel, Finlayson & McMahon (2007), so a station cannot stand for a class
    it does not belong to;
  * spot values against the published tables (Met Office Heathrow
    1991-2020, NOAA Miami International 1991-2020, HNMS Lemnos);
  * the vanilla terrains bind to the station of their real location;
  * no hand-typed per-biome table remains in fnc_getClimateNormals.

Run: python3 -m unittest tools.tests.test_climate_normals
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import gen_climate_normals as gen  # noqa: E402

DATA = json.loads(gen.DATA.read_text(encoding="utf-8"))
STATIONS = {s["id"]: s for s in DATA["stations"]}


class TestCorpus(unittest.TestCase):
    def test_generated_table_is_fresh(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_every_label_matches_its_own_normals(self):
        for s in DATA["stations"]:
            tmean = [(a + b) / 2 for a, b in zip(s["mean_daily_max_c"], s["mean_daily_min_c"])]
            got = gen.koppen(tmean, s["precipitation_mm"], s["hemisphere"] == "N")
            self.assertEqual(got, s["koppen"], s["id"])

    def test_every_station_names_a_primary_source(self):
        for s in DATA["stations"]:
            self.assertTrue(s["primary_source"], s["id"])
            self.assertIn("wikipedia.org", s["retrieved_from"])

    def test_published_spot_values(self):
        # Met Office Heathrow 1991-2020: July mean max 23.5 C, annual
        # rainfall ~600 mm.  NOAA Miami Intl 1991-2020: Jan mean max 24.6 C.
        # HNMS Lemnos: August the driest month (6.3 mm).
        lhr = STATIONS["london_lhr"]
        self.assertAlmostEqual(lhr["mean_daily_max_c"][6], 23.5, delta=0.6)
        self.assertAlmostEqual(sum(lhr["precipitation_mm"]), 600, delta=60)
        self.assertAlmostEqual(STATIONS["miami"]["mean_daily_max_c"][0], 24.6, delta=0.1)
        lem = STATIONS["lemnos"]["precipitation_mm"]
        self.assertEqual(lem.index(min(lem)), 7)

    def test_vanilla_terrains_bind_to_their_real_location(self):
        w = DATA["world_bindings"]
        self.assertEqual(w["Altis"]["station"], "lemnos")
        self.assertEqual(w["Tanoa"]["station"], "nadi")
        self.assertEqual(w["Enoch"]["station"], "suwalki")
        self.assertEqual(STATIONS["nadi"]["hemisphere"], "S")


class TestRuntime(unittest.TestCase):
    def test_no_hand_typed_table_remains(self):
        src = (REPO / "addons/weather/functions/climatology/fnc_getClimateNormals.sqf").read_text(encoding="utf-8")
        self.assertNotIn("case \"Cfb\"", src)
        self.assertIn("getStationNormals", src)

    def test_southern_worlds_shift_a_koppen_station(self):
        src = gen.OUT.read_text(encoding="utf-8")
        self.assertIn("(_x select [6, 6]) + (_x select [0, 6])", src)


if __name__ == "__main__":
    unittest.main()


class TestWmoGlobalStations(unittest.TestCase):
    WMO = json.loads(gen.WMO.read_text(encoding="utf-8"))["stations"]

    def test_corpus_size(self):
        self.assertGreater(len(self.WMO), 3000)
        self.assertGreater(sum(1 for s in self.WMO if s["rh"]), 1500)

    def test_humidity_method_matches_measured_rh(self):
        # Measured monthly RH of curated stations (national services) against
        # the RH the generator derives from the same place's WMO vapour
        # pressure: within 7 points in every month.
        by_name = {s["name"]: s for s in self.WMO}
        for sid, name in (("suwalki", "Suwalki"), ("singapore", "ChangiAirport"),
                          ("niamey", "Niamey_Aero"), ("minsk", "MINSK"), ("kashgar", "KASHI")):
            measured = STATIONS[sid]["relative_humidity_pct"]
            derived = by_name[name]["rh"]
            worst = max(abs(a - b) for a, b in zip(derived, measured))
            self.assertLess(worst, 7.0, f"{sid}: {worst:.1f}")

    def test_temperatures_are_reduced_to_sea_level(self):
        # Kabul (1791 m) enters the runtime table 11.6 C warmer than measured,
        # because the temperature model applies the lapse to the terrain.
        src = gen.OUT.read_text(encoding="utf-8")
        kabul = STATIONS["kabul"]
        reduced = round(kabul["mean_daily_max_c"][6] + 0.0065 * kabul["elevation_m"], 2)
        self.assertIn(f"{reduced:g}", src)

    def test_unbound_world_uses_the_nearest_station(self):
        src = (REPO / "addons/weather/functions/climatology/fnc_getNearestClimateStation.sqf").read_text(encoding="utf-8")
        self.assertIn('configFile >> "AEE_ClimateStations"', src)
        self.assertIn("getNearestClimateStation", gen.OUT.read_text(encoding="utf-8"))
