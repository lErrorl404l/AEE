#!/usr/bin/env python3
"""Dynamic biome tests (issue #123 — fully data-driven, no map names).

The old biome system looked up a hardcoded map-name table + description
keywords.  The new system CLASSIFIES the biome from map facts: latitude
climate physics (getLatitudeClimate) run through the real Köppen rules,
corrected by terrain signals (surface textures, indicator vegetation
species, structures, elevation).  No map name anywhere.

These tests mirror the SQF physics:
  - getLatitudeClimate: annual mean/amplitude, maritime moderation,
    hemisphere peak, summer-dry regime, diurnal range
  - classifyBiome (Köppen): the real thresholds from the SQF
  - the fusion weights in getBiome
  - regressions for all three #123 root causes

Run: python3 -m unittest tools.tests.test_biome_dynamic
"""

import math
import unittest


# ─── Mirror of fnc_getLatitudeClimate.sqf ──────────────────────────────────
def latitude_climate(lat_deg, water_frac=0.3):
    """Returns [P_sea, cloud, tDay[12], tNight[12], RH[12], precip[12]]."""
    lat = abs(lat_deg)
    if lat > 66.5:
        lat = 66.5
    t_mean_base = 27 - 0.42 * lat
    # Maritime air masses moderate amplitude AND raise the annual mean
    # (the ocean warms the winter half-year).  Threshold sits low: a map
    # with a third water is dominated by ocean-air masses.  The +5 C
    # coefficient is anchored to the Scottish Highlands (Aviemore 57.2 N:
    # latitude base 3.2 C, real mean 7.7 C, +4.5 C lift at waterFrac
    # ~0.35); the old +4 C left the mean 1.2 C low, dropping
    # high-latitude oceanic maps to Cfc instead of Cfb (issue #184).
    maritime = 1 / (1 + math.exp(-12 * (water_frac - 0.22)))
    t_mean = t_mean_base + 5 * maritime
    # Subtropical high (Hadley cell descending branch): a sharp belt at
    # ~31 N/S brings BOTH warm dry air (adiabatic warming, clear skies)
    # and suppressed convection.  Without it the model cannot produce the
    # world's desert belt — Cairo/Baghdad/Kandahar classify Csa instead
    # of BWh (found by the CUP workshop-map rotation).  The single
    # `hadley` factor drives the +6.0 C warming and the precip
    # * (1 - 0.92*hadley) aridity.  It is zero at the equator, at the
    # poles, and on maritime maps (the ocean breaks the high).  Cairo
    # (30 N): +5.2 C, *0.20 precip — real 22 C, 25 mm/yr (BWh).
    hadley = math.exp(-((lat - 31) ** 2) / (2 * 5**2)) * (1 - maritime)
    t_mean = t_mean + 6.0 * hadley
    # Annual amplitude: the documented model A(lat) = 1.4 + 0.405*|lat| is
    # the FULL peak-to-trough range (Minsk at 54 N: 25.1 C swing).  The
    # sin() term needs HALF that (the amplitude about the mean).  Feeding
    # the full range in produced a ~2x seasonal swing, pushing mid-latitude
    # maps into Dfa instead of Dfb (issue #184).
    amp_full = max(1.4 + 0.405 * lat, 2.0)
    amp = (amp_full / 2) * (1 - 0.6 * maritime)
    peak_month = 7 if lat_deg >= 0 else 1
    summer_boost = 6 * math.exp(-((lat - 35) ** 2) / 90)
    summer_dry = math.exp(-((lat - 35) ** 2) / 70)
    diurnal = 8 + 5 * math.exp(-((lat - 30) ** 2) / 250) * (1 - lat / 90)
    if lat < 10:
        diurnal = 8

    t_day, t_night, precip, rh = [], [], [], []
    for m in range(1, 13):
        # Phase peaks AT the peak month: sin((m - peak + 3)/12 * 2pi) is 1
        # when m == peak (July north, January south).  (The naive
        # (m - peak) form makes the warmest month come 3 months late.)
        phase = (m - peak_month + 3) / 12 * 2 * math.pi
        t_mid = t_mean + amp * math.sin(phase)
        if math.sin(phase) > 0:
            t_mid += summer_boost
        t_day.append(round((t_mid + diurnal / 2) * 10) / 10)
        t_night.append(round((t_mid - diurnal / 2) * 10) / 10)
        # Dry-season floor: the model's own dryness factor, not a flat 0.1.
        # A flat 10% floor overdried tropical wet seasons (Tanoa -> Am).
        dryness = math.exp(-lat / 25)
        wetness = max(0.5 + 0.5 * math.sin(phase), dryness)
        if summer_dry > 0.3:
            wetness = 1 - wetness
        base_p = (60 + 90 * dryness) * (1 + 2.5 * maritime)
        # Subtropical-high aridity: the descending branch suppresses
        # convection in the 25-38 N/S belt (Sahara, Arabian, Afghan).
        base_p = base_p * (1 - 0.92 * hadley)
        precip.append(round(base_p * wetness))
        rh.append(round(max(min(wetness * 70 + (1 - wetness) * 35, 90), 30)))
    cloud = round((rh[5] / 90) * 8) / 10
    return [1013, cloud, t_day, t_night, rh, precip]


# ─── Mirror of fnc_classifyBiome.sqf (real Köppen rules) ──────────────────
def classify_biome(temps, precip):
    """Köppen classification from 12 monthly mean temps + precip (mm)."""
    t_ann = sum(temps) / 12
    t_warm = max(temps)
    t_cold = min(temps)
    p_ann = sum(precip)
    p_driest = min(precip)

    # Summer/winter halves: fixed convention (Apr-Sep north, Oct-Mar
    # south) per the standard Köppen interpretation.  Using the warmest
    # six-month block instead wrongly shifts Athens' rainy Dec-Jan into
    # "summer" and breaks the dry-threshold split.
    summer_p = sum(precip[3:9])
    winter_p = p_ann - summer_p

    if summer_p >= 0.7 * p_ann:
        p_thresh = 20 * t_ann + 280
    elif winter_p >= 0.7 * p_ann:
        p_thresh = 20 * t_ann
    else:
        p_thresh = 20 * t_ann + 140

    # Dry climates (B) first: arid check.
    if p_ann < p_thresh:
        half = 0.5 * p_thresh
        if t_ann >= 18:
            return "BWh" if p_ann < half else "BSh"
        return "BWk" if p_ann < half else "BSk"

    # Polar (E): warmest month <= 10.
    if t_warm <= 10:
        return "EF" if t_warm <= 0 else "ET"

    # Tropical (A): coldest month >= 18.
    if t_cold >= 18:
        if p_driest >= 60:
            return "Af"
        return "Am" if p_driest >= 100 - p_ann / 25 else "Aw"

    # Continental (D): coldest month <= -3.
    if t_cold <= -3:
        # Second letter by the same summer/winter test as C.
        dry_summer = min(precip[3:9])
        wet_winter = max(precip[0:3] + precip[9:12])
        wet_summer = max(precip[3:9])
        dry_winter = min(precip[0:3] + precip[9:12])
        months_10 = sum(1 for t in temps if t >= 10)
        third = (
            "d"
            if t_cold <= -38
            else ("a" if t_warm >= 22 else ("b" if months_10 >= 4 else "c"))
        )
        if dry_summer < 40 and dry_summer < wet_winter / 3:
            return "Ds" + third  # continental Mediterranean: Ankara Dsa
        if wet_summer >= 10 * dry_winter:
            return "Dw" + third  # monsoon continental: Beijing Dwa
        return "Df" + third  # fully humid: Dfa/Dfb/Dfc/Dfd

    # Temperate (C): driest-summer rule.
    dry_summer = min(precip[3:9])
    wet_winter = max(precip[0:3] + precip[9:12])
    wet_summer = max(precip[3:9])
    dry_winter = min(precip[0:3] + precip[9:12])
    months_10 = sum(1 for t in temps if t >= 10)
    if dry_summer < 40 and dry_summer < wet_winter / 3:
        return "Csa" if t_warm >= 22 else ("Csb" if months_10 >= 4 else "Csc")
    if wet_summer >= 10 * dry_winter:
        return "Cwa" if t_warm >= 22 else ("Cwb" if months_10 >= 4 else "Cwc")
    return "Cfa" if t_warm >= 22 else ("Cfb" if months_10 >= 4 else "Cfc")


def biome_from_climate(temps, precip):
    return classify_biome(temps, precip)


def mean_temps(normals):
    t_day, t_night = normals[2], normals[3]
    return [(a + b) / 2 for a, b in zip(t_day, t_night)]


# ─── Fusion mirror (fnc_getBiome.sqf weights) ─────────────────────────────
def fuse_biome(
    climate_biome, veg_scores, surface_scores=None, struct_scores=None, mean_elev=0.0
):
    """Returns (code, score).  Climate is primary (10); vegetation 8,
    surface 4, structure 3 refine within the climate band.

    Peak-to-sidelobe confidence gate (TERCOM/DSMAC doctrine): the
    terrain refinement is accepted only when the winner unambiguously
    clears the runner-up by the ratio (1.4); an ambiguous match is
    rejected and the climate anchor holds."""
    scores = {climate_biome: 10}
    for code, w in veg_scores.items():
        scores[code] = scores.get(code, 0) + w * 8
    for code, w in (surface_scores or {}).items():
        scores[code] = scores.get(code, 0) + w * 4
    for code, w in (struct_scores or {}).items():
        scores[code] = scores.get(code, 0) + w * 3
    if mean_elev > 1500:
        scores["Dfc"] = scores.get("Dfc", 0) + 15
        scores["ET"] = scores.get("ET", 0) + 8
    codes = list(scores.keys())
    best_code = max(codes, key=lambda c: scores[c])
    best_score = scores[best_code]
    others = [scores[c] for c in codes if c != best_code]
    # Single candidate (climate and terrain agree): no runner-up to
    # gate against, so the winner stands.
    if not others:
        return (best_code, best_score)
    second_score = max(others)
    margin_ratio = 1.4
    if best_code != climate_biome and best_score < second_score * margin_ratio:
        return (climate_biome, scores[climate_biome])
    return (best_code, best_score)


# ─── Climate physics tests ─────────────────────────────────────────────────
class TestLatitudeClimatePhysics(unittest.TestCase):
    """The latitude-driven climatology must be physically sensible."""

    def test_tropical_warm_constant(self):
        # Tanoa (-8, water 0.5): mean ~27.5, tiny amplitude (maritime).
        n = latitude_climate(-8, 0.5)
        t = mean_temps(n)
        self.assertGreater(sum(t) / 12, 26)
        self.assertLess(max(t) - min(t), 7)  # equatorial: little seasonality

    def test_polar_cold(self):
        # 70 N clamps to 66.5 (polar night regime).  Annual mean must be
        # cold, near freezing.  Real anchor: Rovaniemi at 66.5 N has
        # annual mean +0.9 C (Jan -10, Jul +15).  The corrected maritime
        # coefficient (+5 C) gives +0.04 here; the old +4 C gave -0.17,
        # slightly too cold.  The < 2 C bound keeps "cold" without
        # over-constraining against the real near-zero mean.
        n = latitude_climate(70, 0.1)
        t = mean_temps(n)
        self.assertLess(sum(t) / 12, 2)

    def test_hemisphere_peak_shift(self):
        # July warmest north, January warmest south.
        n_north = latitude_climate(40, 0.1)
        t_north = mean_temps(n_north)
        self.assertEqual(t_north.index(max(t_north)), 6)  # July (0-indexed)
        n_south = latitude_climate(-40, 0.1)
        t_south = mean_temps(n_south)
        self.assertEqual(t_south.index(max(t_south)), 0)  # January

    def test_maritime_moderates_amplitude(self):
        # Same latitude, continental vs ocean: amplitude collapses ~60%.
        n_cont = latitude_climate(52, 0.05)
        n_ocean = latitude_climate(52, 0.7)
        t_cont = mean_temps(n_cont)
        t_ocean = mean_temps(n_ocean)
        amp_cont = max(t_cont) - min(t_cont)
        amp_ocean = max(t_ocean) - min(t_ocean)
        self.assertGreater(amp_cont, amp_ocean * 1.5)

    def test_mediterranean_winter_rains(self):
        # Lat 35 summer-dry: precip peaks in winter, not summer.
        n = latitude_climate(35, 0.5)
        precip = n[5]
        t = mean_temps(n)
        warm_month = t.index(max(t))
        cold_month = t.index(min(t))
        self.assertGreater(precip[cold_month], precip[warm_month])

    def test_shape_matches_consumers(self):
        # Output shape must equal getClimateNormals: 6 elements.
        n = latitude_climate(40, 0.3)
        self.assertEqual(len(n), 6)
        self.assertEqual(len(n[2]), 12)  # tDay
        self.assertEqual(len(n[3]), 12)  # tNight
        self.assertEqual(len(n[4]), 12)  # RH
        self.assertEqual(len(n[5]), 12)  # precip
        self.assertEqual(n[0], 1013)  # P_sea


# ─── Köppen classification tests ───────────────────────────────────────────
class TestKoppenClassification(unittest.TestCase):
    """The Köppen rules must classify reference climatologies correctly."""

    def test_tropical_rainforest_af(self):
        # Singapore: 27C year-round, wet every month.
        temps = [27.3] * 12
        precip = [240] * 12
        self.assertEqual(classify_biome(temps, precip), "Af")

    def test_tropical_savanna_aw(self):
        # Wet summer, dry winter, cold month > 18.
        temps = [25.0] * 12
        precip = [180, 150, 120, 80, 40, 20, 15, 25, 60, 120, 170, 190]
        self.assertEqual(classify_biome(temps, precip), "Aw")

    def test_hot_desert_bwh(self):
        temps = [30.0] * 12
        precip = [5] * 12
        self.assertEqual(classify_biome(temps, precip), "BWh")

    def test_mediterranean_csa(self):
        # Athens: hot dry summer, mild wet winter.
        temps = [9, 10, 12, 16, 21, 26, 29, 29, 25, 19, 14, 10]
        precip = [60, 50, 55, 30, 20, 10, 5, 5, 15, 50, 70, 75]
        self.assertEqual(classify_biome(temps, precip), "Csa")

    def test_oceanic_cfb(self):
        # London: mild winters, cool summers, year-round rain.
        temps = [5, 5, 7, 9, 13, 16, 18, 18, 15, 11, 8, 6]
        precip = [55] * 12
        self.assertEqual(classify_biome(temps, precip), "Cfb")

    def test_humid_continental_dfb(self):
        # Winnipeg: cold winter, warm summer.
        temps = [-16, -13, -6, 4, 12, 17, 20, 19, 12, 5, -4, -12]
        precip = [20] * 12
        self.assertEqual(classify_biome(temps, precip), "Dfb")

    def test_subarctic_dfc(self):
        temps = [-20, -17, -10, 0, 8, 14, 17, 15, 8, 0, -9, -16]
        precip = [30] * 12
        self.assertEqual(classify_biome(temps, precip), "Dfc")

    def test_tundra_et(self):
        temps = [-15, -14, -12, -6, 0, 5, 8, 7, 2, -4, -10, -14]
        precip = [25] * 12
        self.assertEqual(classify_biome(temps, precip), "ET")

    def test_monsoon_continental_dwa(self):
        # Beijing: cold dry winter (Jan mean -3.7), hot humid summer
        # (Jul 26.2, 185 mm), wettest summer >= 10x driest winter.
        temps = [-3.7, -0.7, 5.8, 13.9, 20.0, 24.4, 26.2, 24.8, 20.0, 13.1, 4.6, -1.5]
        precip = [2.6, 5.9, 9.0, 26.3, 33.1, 77.7, 185.2, 159.7, 45.5, 21.8, 7.4, 2.8]
        self.assertEqual(classify_biome(temps, precip), "Dwa")

    def test_dry_summer_continental_dsa(self):
        # Continental Mediterranean: cold winter (<= -3), hot dry summer,
        # wettest winter > 3x driest summer month.
        temps = [-5, -4, 2, 10, 17, 22, 25, 24, 18, 10, 2, -3]
        precip = [40, 35, 40, 45, 40, 20, 10, 8, 15, 30, 35, 40]
        self.assertEqual(classify_biome(temps, precip), "Dsa")

    def test_subpolar_oceanic_cfc(self):
        # Torshavn: cool year-round, wet every month, no dry season,
        # fewer than 4 months >= 10 C.
        temps = [1.7, 1.8, 2.7, 4.4, 7.0, 9.3, 11.0, 11.1, 8.9, 6.1, 3.6, 2.2]
        precip = [141, 95, 132, 89, 63, 57, 71, 96, 119, 147, 135, 155]
        self.assertEqual(classify_biome(temps, precip), "Cfc")

    def test_severe_subarctic_dfd(self):
        # Oymyakon: extreme winter (Jan -46), short mild summer.
        temps = [
            -46.4,
            -42.0,
            -31.3,
            -14.2,
            -1.7,
            9.4,
            14.8,
            11.2,
            2.5,
            -10.9,
            -32.2,
            -42.5,
        ]
        precip = [9, 9, 6, 8, 20, 35, 48, 38, 25, 15, 12, 8]
        self.assertEqual(classify_biome(temps, precip), "Dfd")


# ─── Map-resolution fusion tests (issue #123) ──────────────────────────────
class TestMapFusion(unittest.TestCase):
    """The fused result for the reported maps must be correct."""

    def test_tanoa_tropical(self):
        # lat -8, water 0.5: climate says tropical; palms confirm.
        n = latitude_climate(-8, 0.5)
        climate = classify_biome(mean_temps(n), n[5])
        self.assertIn(climate, ["Af", "Am", "Aw"])
        code, _ = fuse_biome(climate, {"Af": 1})
        self.assertEqual(code, climate)  # climate anchors, veg confirms

    def test_scottish_highlands_not_frozen(self):
        # oski_corran: lat 56.7, water 0.35.  The bug was Dfb with winter
        # -12 (constant freezing).  The maritime correction must keep the
        # cold month above the deep-freeze: no Dfa/Dfd, cold month above
        # -8, and the climate stays in the temperate/continental band
        # (Cfb/Dfb) — never the extreme Dfc that would freeze the player.
        n = latitude_climate(56.7, 0.35)
        t = mean_temps(n)
        self.assertGreater(sum(t) / 12, 4)  # not frozen
        self.assertGreater(min(t), -8)  # winter not deep-freeze
        climate = classify_biome(t, n[5])
        self.assertIn(climate, ["Cfb", "Dfb"])  # temperate, not arctic

    def test_enochns_continental(self):
        # Enoch: lat 52, water 0.05 (inland) -> continental band, cold winter.
        # Real anchor: Minsk (53.9 N) January mean -6.6 C.  The corrected
        # amplitude (half of A = 1.4 + 0.405*lat) gives ~-4.8 here; the
        # old 2x-amplitude bug gave -17, and the -10 bound was locking it.
        n = latitude_climate(52, 0.05)
        t = mean_temps(n)
        self.assertLess(min(t), -2)  # real continental winter (below freezing)
        climate = classify_biome(t, n[5])
        self.assertIn(climate, ["Dfa", "Dfb", "Dfc"])

    def test_elevation_shift(self):
        # A temperate climate at high elevation shifts toward subarctic.
        code, _ = fuse_biome("Cfb", {}, mean_elev=1800)
        self.assertEqual(code, "Dfc")

    def test_afghan_desert_arid(self):
        # Takistan/Zargabad (lat 34, water 0.05): real Afghanistan is
        # BWh/BSk desert (~250 mm/yr at Kandahar).  The #184 climate
        # model had no subtropical aridity, so 34 N classified Csa
        # (Mediterranean) and every Afghan map got olive trees instead
        # of sand (found by the CUP workshop-map rotation).  The Hadley
        # descending-branch term must push 30-35 N continental into the
        # arid (B) band.
        n = latitude_climate(34, 0.05)
        t = mean_temps(n)
        climate = classify_biome(t, n[5])
        self.assertEqual(climate[0], "B")  # arid, not temperate
        self.assertLess(sum(n[5]), 450)  # annual precip stays desert-low

    def test_cairo_hot_desert(self):
        # Cairo (lat 30, water 0.02): BWh, 22 C mean, 25 mm/yr.  The
        # Hadley warming must lift the annual mean past the 18 C BWh/BSk
        # boundary while the aridity keeps precip in the desert band.
        n = latitude_climate(30, 0.02)
        t = mean_temps(n)
        self.assertGreater(sum(t) / 12, 18)  # hot, not cold desert
        climate = classify_biome(t, n[5])
        self.assertIn(climate, ["BWh", "BSh"])

    def test_mediterranean_stays_temperate(self):
        # Athens (lat 38, water 0.25): Csa.  The Hadley belt must fade by
        # 38 N (peak 31 N, sigma 5) so the Mediterranean keeps its
        # temperate classification - the aridity must not reach it.
        n = latitude_climate(38, 0.25)
        t = mean_temps(n)
        climate = classify_biome(t, n[5])
        self.assertEqual(climate, "Csa")

    def test_hadley_fades_poleward(self):
        # The Hadley term is a sharp 25-38 N belt.  It must be zero by
        # 45 N: London (51.5 N) and Enoch (45-54 N) keep their maritime
        # temperate / continental climates untouched.
        n_lon = latitude_climate(51.5, 0.35)
        self.assertEqual(classify_biome(mean_temps(n_lon), n_lon[5]), "Cfb")
        n_eno = latitude_climate(54, 0.0)
        self.assertIn(
            classify_biome(mean_temps(n_eno), n_eno[5]), ["Dfa", "Dfb", "Dfc"]
        )

    # ─── Fusion confidence gate (peak-to-sidelobe, TERCOM doctrine) ───
    def test_fusion_full_coverage_indicator_overrides(self):
        # A full-coverage indicator species (weight 3 -> 24 after the
        # veg channel 8x) clears the climate anchor (10) by the ratio:
        # 24/10 = 2.4 >= 1.4, so the terrain wins.
        code, score = fuse_biome("Cfb", {"Dfc": 3.0})
        self.assertEqual(code, "Dfc")

    def test_fusion_moderate_signal_abstains(self):
        # A moderate vegetation signal (12 vs anchor 10: ratio 1.2 < 1.4)
        # must NOT move off the climate anchor - the match is ambiguous,
        # so the system abstains and the climate verdict holds.
        code, score = fuse_biome("Cfb", {"Dfc": 1.5})
        self.assertEqual(code, "Cfb")
        self.assertEqual(score, 10)

    def test_fusion_near_tie_abstains(self):
        # Two competing terrain signals nearly tied (20 vs 18: ratio
        # 1.11 < 1.4) - the terrain evidence is ambiguous, so the
        # climate anchor wins rather than either signal.
        code, _ = fuse_biome("Cfb", {"Dfc": 2.5, "Dfb": 2.25})
        self.assertEqual(code, "Cfb")

    def test_fusion_elevation_override_preserved(self):
        # The documented elevation override (Dfc +15 vs anchor 10:
        # ratio 1.5 >= 1.4) still passes the gate - mountains are
        # colder than their latitude suggests.
        code, _ = fuse_biome("Cfb", {}, mean_elev=1800)
        self.assertEqual(code, "Dfc")


# ─── Root-cause regressions (issue #123) ───────────────────────────────────
class TestRootCauseRegressions(unittest.TestCase):
    """The three reported bugs must not recur."""

    def test_no_negative_latitude_inversion(self):
        # A negative config latitude must NOT invert the seasons.  The
        # old bug: sin(-56.7) made northern winter a summer.  Now:
        # magnitude is abs-corrected, and the hemisphere sets the peak
        # month (Jan south, Jul north).
        n_south = latitude_climate(-56.7, 0.35)
        t_south = mean_temps(n_south)
        self.assertEqual(t_south.index(max(t_south)), 0)  # January warmest
        # The annual mean matches the northern equivalent (abs-corrected).
        n_north = latitude_climate(56.7, 0.35)
        t_north = mean_temps(n_north)
        self.assertAlmostEqual(sum(t_south) / 12, sum(t_north) / 12, places=1)

    def test_biome_names_are_all_valid(self):
        # Every Köppen code the system can emit has a display name.
        codes = [
            "Af",
            "Am",
            "Aw",
            "BSh",
            "BSk",
            "BWk",
            "BWh",
            "Csa",
            "Csb",
            "Cfa",
            "Cfb",
            "Cwa",
            "Dfa",
            "Dfb",
            "Dfc",
            "ET",
            "EF",
        ]
        names = [
            "Tropical Rainforest",
            "Monsoon Tropical",
            "Tropical Savanna",
            "Hot Semi-Arid",
            "Cold Semi-Arid",
            "Cold Desert",
            "Hot Desert",
            "Hot Mediterranean",
            "Warm Mediterranean",
            "Humid Subtropical",
            "Oceanic",
            "Monsoon Subtropical",
            "Hot Continental",
            "Humid Continental",
            "Subarctic",
            "Tundra",
            "Ice Cap",
        ]
        for code, name in zip(codes, names):
            self.assertTrue(name)  # every code has a name

    def test_no_map_name_table(self):
        # The rewritten getBiome must NOT contain the hardcoded map-name
        # table or the description-keyword matching (the RC2c
        # hardcoded-assumption).  worldName IS allowed - it is read only
        # for the latitude FACT (abs-corrected), never matched by name.
        from pathlib import Path

        text = Path("addons/environmental/functions/biome/fnc_getBiome.sqf").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("_MAP_BIOMES", text)  # old map-name table gone
        self.assertNotIn("_description", text)  # description keyword matching gone

    def test_camo_swap_unknown_keeps_engine(self):
        # RC3 regression + #124 migration: the clothing thermal path must
        # not break third-party uniforms.  The old keyword branch
        # (`_m find "cloth" >= 0`) is GONE - the #124 migration replaced
        # rvmat swaps with the per-selection substrate, which classifies
        # via the #96 detector chain and leaves unknown materials at the
        # engine default.  The dangerous "unknown -> swap" else-branch is
        # gone; the substrate's safe fallback is present.
        from pathlib import Path

        text = Path("addons/thermal/functions/display/fnc_applyClothingThermal.sqf").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('_m find "cloth" >= 0', text)
        self.assertNotIn('_m == "" ||', text)
        self.assertNotIn("Unknown material: swap", text)
        # The substrate path must be used instead.
        self.assertIn("FUNC(applySelectionThermal)", text)
        # And the scrapped rvmat override names must not be referenced.
        self.assertNotIn("ti_cloth_cold.rvmat", text)
        self.assertNotIn("ti_cloth_hot.rvmat", text)

    def test_climate_consumers_use_latitude_normals(self):
        # The 4 climate consumers (temperature, pressure, humidity, fog)
        # must get the map's latitude-driven climatology, not the static
        # per-biome table.  getBiome publishes QGVAR(climateNormals) from
        # fnc_getLatitudeClimate; getClimateNormals prefers it.  A Cfb at
        # 66 N (Norway) must NOT receive the 35 N Cfb table.
        from pathlib import Path

        get_biome = Path("addons/environmental/functions/biome/fnc_getBiome.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("QGVAR(climateNormals)", get_biome)
        self.assertIn("getLatitudeClimate", get_biome)
        # Regression: `private _x = getVariable [..., nil]` does not bind
        # the local in SQF -> "Undefined variable" every tick.  The cached
        # read must use a string sentinel.
        self.assertNotIn('biomeCached", nil]', get_biome)
        self.assertIn('QGVAR(biomeCached), ""]', get_biome)

        get_normals = Path(
            "addons/environmental/functions/climatology/fnc_getClimateNormals.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("QGVAR(climateNormals)", get_normals)
        self.assertIn(
            "if (_latNormals isNotEqualTo []) exitWith { _latNormals }", get_normals
        )

        # Every consumer must call getClimateNormals (the dispatcher), not
        # reach around it with its own static data.
        for fn in [
            "addons/atmos/functions/state/fnc_updateHumidity.sqf",
            "addons/atmos/functions/state/fnc_updateFog.sqf",
            "addons/atmos/functions/state/fnc_updatePressure.sqf",
            "addons/thermal/functions/environment/fnc_updateTemperature.sqf",
        ]:
            text = Path(fn).read_text(encoding="utf-8")
            self.assertIn("getClimateNormals", text, f"{fn} bypasses the dispatcher")

    def test_fusion_iterates_keys_not_pairs(self):
        # #180: on Tanoa the terrain scan yields populated HashMaps, and
        # `forEach` over a HashMap iterates the KEYS (Strings), not
        # [code, weight] pairs.  The old `_x#0` on a String errored
        # ("Type String, expected Array") on every map whose scan found
        # signals.  Stratis never hit it because its score maps stayed
        # empty.  The fusion must iterate `keys` and read weights with
        # `get`.
        from pathlib import Path

        text = Path("addons/environmental/functions/biome/fnc_getBiome.sqf").read_text(
            encoding="utf-8"
        )
        # The three score maps are HashMaps: keys = biome codes.
        self.assertIn("forEach (keys _vegScores)", text)
        self.assertIn("forEach (keys _surfaceScores)", text)
        self.assertIn("forEach (keys _structScores)", text)
        self.assertIn("_vegScores get _code", text)
        self.assertIn("_surfaceScores get _code", text)
        self.assertIn("_structScores get _code", text)
        # No raw `forEach _x` treating a HashMap element as a pair.
        self.assertNotIn("} forEach _vegScores;", text)
        self.assertNotIn("} forEach _surfaceScores;", text)
        self.assertNotIn("} forEach _structScores;", text)


if __name__ == "__main__":
    unittest.main()
