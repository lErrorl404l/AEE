#!/usr/bin/env python3
"""Reference checks for the propellant-temperature muzzle-velocity model.

Validates the SQF implementation in addons/ballistics:
- fnc_calculatePropellantSensitivity.sqf  (fps/degF coefficient cascade)
- fnc_calculateMuzzleVelocityCorrection.sqf (%/degC normalised to the
  ammo's own initSpeed, 21 degC NATO EPVAT reference)

Ground truth (research-verified):
- Smokeless powders span 0.14-2.0 fps/degF; military ball (WC844-type)
  is ~1.5 fps/degF; central rule of thumb is 1.0 fps/degF
  (reloading literature; Sniper's Hide compilation; PrecisionRifleBlog
  field test; Boulkadid et al. 2016, DOI 10.22211/cejem/67229)
- 1 fps/degF = 0.5486 m/s per degC (0.3048 * 1.8)
- 21 degC reference: NATO AEP-97 / STANAG 4823 EPVAT conditioning

Run: python3 -m unittest tools/tests/test_propellant_temp.py
"""

import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BALLISTICS = _REPO_ROOT / "addons" / "ballistics" / "functions"

# fps/degF -> m/s per degC (1 degC = 1.8 degF; 1 fps = 0.3048 m/s)
MPS_PER_DEGC_PER_FPS_DEGF = 0.3048 * 1.8  # 0.5486

# Real vanilla CfgMagazines initSpeed per ammo class (verified against
# weapons_f config): the SQF reads these at runtime, the mirrors must too.
INIT_SPEED = {
    "B_556x45_Ball": 920,  # 30Rnd_556x45_Stanag
    "B_762x51_Ball": 850,  # 20Rnd_762x51_Mag
    "B_9x21_Ball": 370,  # 30Rnd_9x21_Mag
    "B_545x39_Ball": 880,  # 30Rnd_545x39
    "B_127x108_Ball": 820,  # 5Rnd_127x108_Mag
    "B_65x39_Caseless": 800,  # 30Rnd_65x39_caseless_mag
}

# Literature-anchored coefficients (fps/degF)
TEMP_STABLE = 0.3  # Hodgdon Extreme / RL16-class, match powders
SINGLE_BASE = 0.7  # extruded nitrocellulose
CENTRAL = 1.0  # rule of thumb, most smokeless powders
DOUBLE_BASE = 1.2  # NC + NG
MILITARY_BALL = 1.5  # WC844-type ball (5.56/7.62 NATO)

REF_TEMP_C = 21.0

# Cannon identity tokens. No tier 1 to 4 source holds a cannon propellant
# temperature coefficient, so a cannon ammo has no coefficient and its
# muzzle-velocity correction is a no-op.
CANNON_TOKENS = ("105mm", "120mm", "125mm", "cannon", "howitzer", "mortar")


def propellant_sensitivity(ammo):
    """Mirror of fnc_calculatePropellantSensitivity.sqf cascade.

    A cannon ammo returns 0.0: no tier 1 to 4 source held here states a
    cannon propellant temperature coefficient, so the small-arms cascade is
    not applied to a cannon charge.
    """
    if any(t in ammo.lower() for t in CANNON_TOKENS):
        return 0.0
    table = {
        "B_556x45_Ball": MILITARY_BALL,
        "B_556x45_Ball_Tracer_Red": MILITARY_BALL,
        "B_762x51_Ball": MILITARY_BALL,
        "B_762x51_Ball_Tracer_Green": MILITARY_BALL,
        "B_9x21_Ball": DOUBLE_BASE,
        "B_545x39_Ball": MILITARY_BALL,
        "B_65x39_Caseless": TEMP_STABLE,
        "B_127x108_Ball": MILITARY_BALL,
        "B_127x99_Ball": MILITARY_BALL,
    }
    if ammo in table:
        return table[ammo]
    # Caliber-family fallback
    for frag, coeff in [
        ("556x45", MILITARY_BALL),
        ("762x51", MILITARY_BALL),
        ("545x39", MILITARY_BALL),
        ("127x", MILITARY_BALL),
        ("9x21", DOUBLE_BASE),
        ("9x19", DOUBLE_BASE),
        ("338", TEMP_STABLE),
        ("6.5", TEMP_STABLE),
    ]:
        if frag in ammo:
            return coeff
    return CENTRAL


def muzzle_velocity_correction(ammo, init_speed, temp_c, ace_advbal=False):
    """Mirror of fnc_calculateMuzzleVelocityCorrection.sqf.

    Returns (correction, coeff).  ace_advbal True -> no-op (ACE3 double
    count guard returns 1.0 without setting anything).
    """
    if ace_advbal:
        return 1.0, None
    if init_speed <= 0:
        return 1.0, None
    coeff = propellant_sensitivity(ammo)
    mps_per_degc = coeff * MPS_PER_DEGC_PER_FPS_DEGF
    pct_per_degc = mps_per_degc / init_speed * 100
    correction = 1 + (pct_per_degc * (temp_c - REF_TEMP_C)) / 100
    return max(0.85, min(1.15, correction)), coeff


class TestSensitivityCascade(unittest.TestCase):
    """fps/degF coefficient resolution (fnc_calculatePropellantSensitivity)."""

    def test_military_556(self):
        # M855-family: WC844 double-base ball ~1.5 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_556x45_Ball"), 1.5, places=4)

    def test_military_762(self):
        # M80-family: same ball-powder anchor.
        self.assertAlmostEqual(propellant_sensitivity("B_762x51_Ball"), 1.5, places=4)

    def test_9mm_double_base(self):
        # 9mm Parabellum: double-base, ~1.2 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_9x21_Ball"), 1.2, places=4)

    def test_temperature_stable_match(self):
        # .338 Norma match: temp-stable powder via the CALIBER FALLBACK
        # (B_338_NM_Ball is not in the table — it is a Marksmen-DLC class,
        # not vanilla).  Coefficient assumed within the published
        # temp-stable range; not primary-data-verified per cartridge.
        self.assertAlmostEqual(propellant_sensitivity("B_338_NM_Ball"), 0.3, places=4)

    def test_unknown_ammo_central_default(self):
        # Unknown ammo: conservative central 1.0 fps/degF.
        self.assertAlmostEqual(propellant_sensitivity("B_999x999_Ball"), 1.0, places=4)

    def test_caliber_fallback(self):
        # Known caliber family, unknown exact class: family coefficient.
        self.assertAlmostEqual(
            propellant_sensitivity("B_556x45_Ball_Green"), 1.5, places=4
        )

    def test_sensitivity_span_within_literature(self):
        # All coefficients must sit in the published 0.14-2.0 fps/degF range.
        for ammo in [
            "B_556x45_Ball",
            "B_762x51_Ball",
            "B_9x21_Ball",
            "B_338_NM_Ball",
            "B_65x39_Caseless",
            "B_127x99_Ball",
        ]:
            c = propellant_sensitivity(ammo)
            self.assertGreaterEqual(c, 0.14)
            self.assertLessEqual(c, 2.0)


class TestMuzzleVelocityCorrection(unittest.TestCase):
    """%/degC normalised to the ammo's own initSpeed."""

    def test_556_reference_temp_no_change(self):
        # 5.56 at 21 degC: correction exactly 1.0.
        corr, _ = muzzle_velocity_correction(
            "B_556x45_Ball", INIT_SPEED["B_556x45_Ball"], 21.0
        )
        self.assertAlmostEqual(corr, 1.0, places=6)

    def test_556_cold_reduces_mv(self):
        # -30 degC at the real 920 m/s: ~0.954 (docker PHASE16 verifies the
        # SQF produces 0.954379 with the real config).
        corr, _ = muzzle_velocity_correction(
            "B_556x45_Ball", INIT_SPEED["B_556x45_Ball"], -30.0
        )
        mps_per_c = 1.5 * MPS_PER_DEGC_PER_FPS_DEGF
        pct = mps_per_c / INIT_SPEED["B_556x45_Ball"] * 100
        expected = 1 + (pct * (-30 - 21)) / 100
        self.assertAlmostEqual(corr, expected, places=6)
        self.assertAlmostEqual(corr, 0.9544, places=3)

    def test_556_hot_increases_mv(self):
        # +50 degC: +2.6% -> correction ~1.026.
        corr, _ = muzzle_velocity_correction(
            "B_556x45_Ball", INIT_SPEED["B_556x45_Ball"], 50.0
        )
        self.assertGreater(corr, 1.01)
        self.assertLess(corr, 1.05)

    def test_9mm_larger_relative_shift(self):
        # Same 1.2 fps/degF powder, but 370 m/s pistol: the RELATIVE shift
        # is larger than a 920 m/s rifle with the same coefficient.
        pistol = muzzle_velocity_correction(
            "B_9x21_Ball", INIT_SPEED["B_9x21_Ball"], 50.0
        )[0]
        rifle_at_12 = muzzle_velocity_correction(
            "B_9x21_Ball", INIT_SPEED["B_556x45_Ball"], 50.0
        )[0]
        self.assertGreater(abs(pistol - 1.0), abs(rifle_at_12 - 1.0))

    def test_military_ball_vs_match_at_heat(self):
        # At +50 degC the temperature-stable .338 shifts less than the
        # military ball 5.56: this is the "no bias" requirement.
        match = muzzle_velocity_correction(
            "B_338_NM_Ball", INIT_SPEED["B_556x45_Ball"], 50.0
        )[0]
        military = muzzle_velocity_correction(
            "B_556x45_Ball", INIT_SPEED["B_556x45_Ball"], 50.0
        )[0]
        self.assertLess(abs(match - 1.0), abs(military - 1.0))

    def test_clamp_upper(self):
        # Extreme heat, slow round, sensitive powder: clamp at 1.15.
        corr, _ = muzzle_velocity_correction(
            "B_9x21_Ball", INIT_SPEED["B_9x21_Ball"], 110.0
        )
        self.assertAlmostEqual(corr, 1.15, places=6)

    def test_clamp_lower(self):
        # Extreme cold, slow round: clamp at 0.85.
        corr, _ = muzzle_velocity_correction(
            "B_9x21_Ball", INIT_SPEED["B_9x21_Ball"], -70.0
        )
        self.assertAlmostEqual(corr, 0.85, places=6)

    def test_no_mv_data_no_correction(self):
        # initSpeed <= 0: no correction possible, factor 1.0.
        corr, _ = muzzle_velocity_correction("B_556x45_Ball", 0, 50.0)
        self.assertEqual(corr, 1.0)

    def test_ace_advbal_double_count_guard(self):
        # ACE3 advanced ballistics active: no-op (ACE3 applies its own
        # per-ammo table).  This prevents compounding the correction.
        corr, _ = muzzle_velocity_correction(
            "B_556x45_Ball", INIT_SPEED["B_556x45_Ball"], 50.0, ace_advbal=True
        )
        self.assertEqual(corr, 1.0)

    def test_reference_is_nato_epvat(self):
        # The zero-crossing is at 21 degC (AEP-97 / STANAG 4823).
        self.assertEqual(REF_TEMP_C, 21.0)

    def test_real_vanilla_init_speeds(self):
        # The mirror table must match the real vanilla CfgMagazines
        # initSpeed values (weapons_f config, verified at authoring time).
        # These are what the SQF reads at runtime; wrong values here would
        # make the mirror diverge from the game silently.
        self.assertEqual(INIT_SPEED["B_556x45_Ball"], 920)  # 30Rnd_556x45_Stanag
        self.assertEqual(INIT_SPEED["B_762x51_Ball"], 850)  # 20Rnd_762x51_Mag
        self.assertEqual(INIT_SPEED["B_9x21_Ball"], 370)  # 30Rnd_9x21_Mag
        self.assertEqual(INIT_SPEED["B_545x39_Ball"], 880)  # 30Rnd_545x39
        self.assertEqual(INIT_SPEED["B_127x108_Ball"], 820)  # 5Rnd_127x108_Mag
        self.assertEqual(
            INIT_SPEED["B_65x39_Caseless"], 800
        )  # 30Rnd_65x39_caseless_mag


class TestSQFSyncPropellant(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = (_BALLISTICS / filename).read_text(encoding="utf-8")
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_propellant_temp.py.",
        )

    def test_sensitivity_constants(self):
        self._assert_in_sqf(
            "fnc_calculatePropellantSensitivity.sqf",
            [
                "1.5",
                "1.2",
                "0.3",
                "AEE_Propellant",
            ],
            "propellant coefficient table and cascade",
        )

    def test_correction_constants(self):
        self._assert_in_sqf(
            "fnc_calculateMuzzleVelocityCorrection.sqf",
            [
                "0.3048",
                "1.8",
                "21",
                "0.85",
                "1.15",
                "ace_advanced_ballistics_ammoTemperatureEnabled",
            ],
            "unit conversion, reference temp, clamps, ACE3 guard",
        )


class TestCannonPropellantDeferral(unittest.TestCase):
    """The cannon charge-temperature coefficient is not held.

    No tier 1 to 4 source states the cannon muzzle-velocity change per degree
    of charge temperature. The small-arms cascade is fitted to cartridge
    powders and does not transfer, so a cannon ammo returns 0 and the
    muzzle-velocity correction is a no-op. A mission override still wins.
    """

    def test_cannon_ammo_has_no_sourced_coefficient(self):
        for ammo in (
            "Sh_120mm_APFSDS",
            "Sh_125mm_APFSDS",
            "Sh_105mm_HE",
            "cannon_120mm",
        ):
            self.assertEqual(propellant_sensitivity(ammo), 0.0, ammo)

    def test_cannon_temperature_correction_is_noop(self):
        for temp in (-40.0, 0.0, 21.0, 50.0):
            corr, coeff = muzzle_velocity_correction("Sh_120mm_APFSDS", 1670.0, temp)
            self.assertEqual(corr, 1.0)
            self.assertEqual(coeff, 0.0)

    def test_small_arms_path_unaffected(self):
        self.assertAlmostEqual(propellant_sensitivity("B_556x45_Ball"), 1.5, places=4)
        self.assertAlmostEqual(propellant_sensitivity("B_999x999_Ball"), 1.0, places=4)

    def test_sqf_documents_the_cannon_gap(self):
        text = (_BALLISTICS / "fnc_calculatePropellantSensitivity.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("_isCannon", text)
        self.assertIn("if (_isCannon) exitWith { 0 }", text)
        self.assertIn("cannon", text.lower())


# ── Drift-lock constants (issue #62) ───────────────────────────────────────
REF_TEMP_EPVAT_C = 21.0  # NATO AEP-97 / STANAG 4823 conditioning
CLAMP_LOWER = 0.85
CLAMP_UPPER = 1.15


class TestDriftLockPropellant(unittest.TestCase):
    """Pins the EPVAT reference temperature and the clamp range."""

    def test_epvat_reference_pinned(self):
        self.assertEqual(REF_TEMP_C, REF_TEMP_EPVAT_C)
        # At 21 degC the correction is exactly 1.0 for any ammo.
        for ammo in INIT_SPEED:
            corr, _ = muzzle_velocity_correction(ammo, INIT_SPEED[ammo], REF_TEMP_C)
            self.assertAlmostEqual(corr, 1.0, places=6)

    def test_clamp_range_pinned(self):
        self.assertEqual(CLAMP_LOWER, 0.85)
        self.assertEqual(CLAMP_UPPER, 1.15)

    def test_clamp_behaviour_boundaries(self):
        # Extreme inputs must clamp, never exceed the range.
        for temp in [-60, -40, 60, 80]:
            for ammo in INIT_SPEED:
                corr, _ = muzzle_velocity_correction(ammo, INIT_SPEED[ammo], temp)
                self.assertGreaterEqual(corr, CLAMP_LOWER)
                self.assertLessEqual(corr, CLAMP_UPPER)


# ─── Ammo temperature tracker (issue #94) ──────────────────────────────────
# Mirror of fnc_calculateAmmoTemperature.sqf: lazy first-order relaxation
# toward ambient (+ solar soak), with per-shot propellant heat.


def ammo_temp(
    ambient_c,
    prev_temp,
    dt_s,
    tau=600.0,
    shot_energy_j=0.0,
    heat_per_j=0.0001,
    sun_elev=0.0,
    overcast=1.0,
    fresh=False,
):
    """Mirror of the per-weapon ammo temperature tracker.

    soakAmbient = ambient + 8 * sunFactor * skyFactor
    A FRESH weapon inits at soakAmbient (already sun-warmed); a warm
    weapon relaxes toward it.
    temp = soakAmbient + (prevTemp - soakAmbient) * exp(-dt/tau)
    + shot_energy_j * heat_per_j
    """
    sun_factor = max(0.0, min(1.0, sun_elev / 45.0))
    sky_factor = max(0.1, 1.0 - overcast)
    soak = 8.0 * sun_factor * sky_factor
    soak_ambient = ambient_c + soak
    prev = soak_ambient if fresh else prev_temp
    temp = soak_ambient + (prev - soak_ambient) * math.exp(-dt_s / max(tau, 30.0))
    if shot_energy_j > 0:
        temp += shot_energy_j * heat_per_j
    return temp


class TestAmmoTemperature(unittest.TestCase):
    """Issue #94: per-weapon ammo temp tracking."""

    def test_init_at_ambient(self):
        # Fresh state: no previous temp -> ambient.
        t = ammo_temp(21.0, 21.0, 0.0)
        self.assertAlmostEqual(t, 21.0, places=4)

    def test_cold_start_decays_to_ambient(self):
        # Ammo at 50 C in a -20 C environment: relaxes down.
        t0 = ammo_temp(-20.0, 50.0, 0.0)
        t_short = ammo_temp(-20.0, 50.0, 300.0)  # 5 min
        t_long = ammo_temp(-20.0, 50.0, 3600.0)  # 1 h
        self.assertAlmostEqual(t0, 50.0, places=4)
        self.assertLess(t_short, t0)
        self.assertLess(t_long, t_short)
        # 1 h at tau 600 -> within ~0.25% of ambient.
        self.assertAlmostEqual(t_long, -20.0, delta=0.5)

    def test_relaxation_is_first_order(self):
        # After one tau (600 s) the gap closes by 63%.
        t = ammo_temp(21.0, -30.0, 600.0)
        gap = 21.0 - t
        self.assertAlmostEqual(gap / 51.0, math.exp(-1.0), places=3)

    def test_solar_soak_heats_above_ambient(self):
        # Full sun (elev 45, clear): soak ambient is +8 C.
        t_full_sun = ammo_temp(20.0, 20.0, 3600.0, sun_elev=45.0, overcast=0.0)
        self.assertAlmostEqual(t_full_sun, 28.0, places=1)
        # Night: no soak.
        t_night = ammo_temp(20.0, 20.0, 3600.0, sun_elev=-90.0, overcast=0.0)
        self.assertAlmostEqual(t_night, 20.0, places=2)

    def test_shot_heat_raises_temp(self):
        # 5.56 NATO: ~1800 J per shot * 0.0001 = +0.18 C per shot.
        t = ammo_temp(21.0, 21.0, 0.0, shot_energy_j=1800.0)
        self.assertAlmostEqual(t, 21.0 + 0.18, places=4)
        # A 30-round mag of sustained fire adds ~5.4 C.
        t_30 = ammo_temp(21.0, 21.0, 0.0, shot_energy_j=1800.0 * 30)
        self.assertAlmostEqual(t_30, 21.0 + 0.18 * 30, places=3)

    def test_no_shot_no_heat(self):
        t = ammo_temp(21.0, 21.0, 0.0, shot_energy_j=0.0)
        self.assertAlmostEqual(t, 21.0, places=6)

    def test_fresh_weapon_inits_at_soak_ambient(self):
        # A fresh weapon in full sun starts already sun-warmed (soak +8).
        t = ammo_temp(20.0, 0.0, 0.0, sun_elev=45.0, overcast=0.0, fresh=True)
        self.assertAlmostEqual(t, 28.0, places=4)
        # Fresh at night: no soak.
        t_night = ammo_temp(20.0, 0.0, 0.0, sun_elev=-90.0, overcast=0.0, fresh=True)
        self.assertAlmostEqual(t_night, 20.0, places=4)

    def test_cold_ammo_reduces_mv(self):
        # -20 C ammo via the propellant model: correction below 1.0.
        corr_cold, _ = muzzle_velocity_correction("B_556x45_Ball", 920, -20)
        corr_warm, _ = muzzle_velocity_correction("B_556x45_Ball", 920, 21)
        self.assertLess(corr_cold, corr_warm)

    def test_sustained_fire_raises_mv(self):
        # Hot ammo (sustained fire) gives a higher correction than cold.
        corr_hot, _ = muzzle_velocity_correction("B_556x45_Ball", 920, 35)
        corr_cold, _ = muzzle_velocity_correction("B_556x45_Ball", 920, 0)
        self.assertGreater(corr_hot, corr_cold)


if __name__ == "__main__":
    unittest.main()
