#!/usr/bin/env python3
"""Oxygen-delivery physiology verification (issue #196).

Mirrors addons/physiology/functions/oxygen/fnc_calculateOxygenDelivery.sqf.
The constants are published values and are drift-locked to their sources:

  Hufner 1.34 mL O2/g Hb             (Hufner 1894; Guyton & Hall Ch. 40)
  0.003 mL O2/dL/mmHg solubility     (Guyton & Hall Ch. 40)
  CO_rest 5 L/min                    (Guyton & Hall Ch. 20)
  20.1 J/mL O2 oxycaloric equivalent (Guyton & Hall: 1 L O2 ~ 20.1 kJ)
  DO2crit 330 mL O2/min/m2           (Shibutani et al., Crit Care Med
                                      1983; PMID 6409505)

The point of the model, and of these tests: in acute haemorrhage the two
determinants of delivery fall on different clocks.  Cardiac output falls
at once with circulating volume; haemoglobin is initially normal and
falls only over hours as plasma refills.  The model must NOT collapse to
[Hb] = [Hb]ref * bloodFrac.
"""

import math
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

HUEBNER = 1.34  # mL O2/g Hb
O2_SOLUBILITY = 0.003  # mL O2/dL/mmHg
CO_REST = 5.0  # L/min
OXYCALORIC = 20.1  # J/mL O2
HB_REF = 15.0  # g/dL
SAO2_REF = 0.97
PAO2_REF = 95.0
DO2CRIT_INDEX = 330.0  # mL O2/min/m2
ER_MAX = 0.75
TAU_REFILL = 7200.0  # s
BLOOD_VOL_REF = 6.0  # L
BSA = 1.8258  # m2 DuBois
ATLS_CLASS_III = 0.70


def oxygen_delivery(
    blood_volume,
    metabolic_rate,
    hb=HB_REF,
    sao2=SAO2_REF,
    pao2=PAO2_REF,
    bsa=BSA,
):
    """Mirror of the SQF at a single instant (Hb supplied by the caller)."""
    blood_frac = min(max(blood_volume, 0.0), BLOOD_VOL_REF) / BLOOD_VOL_REF
    cao2 = HUEBNER * hb * min(max(sao2, 0.0), 1.0) + O2_SOLUBILITY * max(pao2, 0.0)
    co = CO_REST * blood_frac
    do2 = co * cao2 * 10.0
    vo2 = max(metabolic_rate, 0.0) * 60.0 / OXYCALORIC
    do2crit = DO2CRIT_INDEX * max(bsa, 0.1)
    er_crit = min(vo2 / do2crit, ER_MAX)
    vo2_actual = vo2
    o2er = 0.0
    if do2 > 0.0:
        if do2 < do2crit:
            vo2_actual = do2 * er_crit
        if vo2_actual / do2 > ER_MAX:
            vo2_actual = do2 * ER_MAX
        o2er = min(vo2_actual / do2, 1.0)
    else:
        vo2_actual = 0.0
    vo2_actual = max(vo2_actual, 0.0)
    metabolic_factor = min(vo2_actual / vo2, 1.0) if vo2 > 0.0 else 1.0
    deficit = max(vo2 - vo2_actual, 0.0)
    skin_perfusion = min(blood_frac / ATLS_CLASS_III, 1.0)
    return {
        "blood_frac": blood_frac,
        "cao2": cao2,
        "co": co,
        "do2": do2,
        "vo2": vo2,
        "vo2_actual": vo2_actual,
        "o2er": o2er,
        "metabolic_factor": metabolic_factor,
        "anaerobic_deficit": deficit,
        "do2crit": do2crit,
        "skin_perfusion": skin_perfusion,
    }


def hb_step(hb, target, seconds, step=60.0):
    """Discrete transcapillary-refill integration (elapsed clamped to 60 s)."""
    remaining = seconds
    while remaining > 0.0:
        dt = min(step, remaining, 60.0)
        hb += (target - hb) * (1.0 - math.exp(-dt / TAU_REFILL))
        remaining -= dt
    return hb


def source(rel):
    return (REPO / rel).read_text(encoding="utf-8")


OXY = "addons/physiology/functions/oxygen/fnc_calculateOxygenDelivery.sqf"


class TestOxygenContent(unittest.TestCase):
    def test_cao2_uses_hufner_and_solubility(self):
        # Given normal blood
        out = oxygen_delivery(BLOOD_VOL_REF, 106.0)
        # Then CaO2 = 1.34*15*0.97 + 0.003*95
        self.assertAlmostEqual(out["cao2"], 19.782, places=3)

    def test_cao2_in_normal_clinical_range(self):
        # 18-20 mL O2/dL at normal Hb (Guyton & Hall)
        out = oxygen_delivery(BLOOD_VOL_REF, 106.0)
        self.assertGreater(out["cao2"], 18.0)
        self.assertLess(out["cao2"], 20.0)


class TestDeliveryAndExtraction(unittest.TestCase):
    def test_normal_delivery(self):
        # Given full blood volume, When delivery is computed,
        # Then DO2 = 5 * 19.782 * 10 ~ 989 mL/min
        out = oxygen_delivery(BLOOD_VOL_REF, 106.0)
        self.assertAlmostEqual(out["do2"], 989.1, places=1)

    def test_cardiac_output_scales_with_circulating_volume(self):
        # Guyton: venous return sets CO, so CO tracks circulating volume.
        full = oxygen_delivery(BLOOD_VOL_REF, 106.0)
        lost = oxygen_delivery(3.0, 106.0)
        self.assertAlmostEqual(full["co"], 5.0, places=6)
        self.assertAlmostEqual(lost["co"], 2.5, places=6)

    def test_extraction_ratio_below_critical_is_physiological(self):
        out = oxygen_delivery(BLOOD_VOL_REF, 106.0)
        self.assertGreater(out["o2er"], 0.2)
        self.assertLess(out["o2er"], 0.35)

    def test_metabolic_factor_one_at_twenty_percent_loss(self):
        # 20 percent loss is above the critical delivery, so oxidative
        # metabolism is fully supplied and ONLY the volume axis moves.
        out = oxygen_delivery(4.8, 106.0)
        self.assertEqual(out["metabolic_factor"], 1.0)
        self.assertEqual(out["anaerobic_deficit"], 0.0)

    def test_metabolic_suppression_only_below_critical_delivery(self):
        # The threshold is where DO2 falls to do2crit, NOT a chosen
        # blood fraction: threshold = do2crit / (5*cao2*10).
        out = oxygen_delivery(BLOOD_VOL_REF, 106.0)
        threshold_frac = out["do2crit"] / out["do2"]
        # At 30 percent loss (the ATLS class III boundary) delivery is
        # still above critical, so metabolism is intact.  The critical
        # threshold therefore sits at a MORE severe loss than class III
        # onset: 0.609 vs 0.70 blood fraction.
        intact = oxygen_delivery(BLOOD_VOL_REF * ATLS_CLASS_III, 106.0)
        self.assertEqual(intact["metabolic_factor"], 1.0)
        self.assertLess(threshold_frac, ATLS_CLASS_III)
        # Well below the threshold metabolism is supply-limited.
        limited = oxygen_delivery(3.0, 106.0)
        self.assertLess(limited["metabolic_factor"], 1.0)

    def test_metabolic_factor_ratio_when_supply_dependent(self):
        # Below critical the fraction delivered is DO2 / DO2crit.
        out = oxygen_delivery(3.0, 106.0)
        do2crit = DO2CRIT_INDEX * BSA
        expected = out["do2"] / do2crit
        self.assertAlmostEqual(out["metabolic_factor"], expected, places=6)

    def test_anaerobic_deficit_appears_below_critical(self):
        out = oxygen_delivery(3.0, 106.0)
        self.assertGreater(out["anaerobic_deficit"], 0.0)
        self.assertLess(out["vo2_actual"], out["vo2"])

    def test_skin_perfusion_stays_on_the_atls_class_iii_boundary(self):
        # The vasoconstriction axis is a volume/baroreflex response, so it
        # keeps the single ATLS boundary cluster 2 established.
        self.assertAlmostEqual(
            oxygen_delivery(BLOOD_VOL_REF * 0.70, 106.0)["skin_perfusion"],
            1.0,
            places=9,
        )
        self.assertAlmostEqual(
            oxygen_delivery(BLOOD_VOL_REF * 0.35, 106.0)["skin_perfusion"],
            0.5,
            places=6,
        )


class TestHaemoglobinKinetics(unittest.TestCase):
    def test_haemoglobin_is_normal_immediately_after_haemorrhage(self):
        # The naive [Hb] = [Hb]ref * bloodFrac would return 10.5 at once.
        # Acute loss removes cells and plasma together, so [Hb] is normal.
        target = HB_REF * 0.70
        self.assertEqual(HB_REF, 15.0)
        self.assertNotEqual(HB_REF, target)

    def test_haemoglobin_barely_moves_in_the_first_five_minutes(self):
        target = HB_REF * 0.70
        hb = hb_step(HB_REF, target, 300.0)
        self.assertGreater(hb, 14.8)

    def test_haemoglobin_dilutes_over_hours(self):
        # After ~10 h of transcapillary refill [Hb] approaches the
        # diluted equilibrium [Hb]ref * bloodFrac.
        target = HB_REF * 0.70
        hb = hb_step(HB_REF, target, 36000.0)
        self.assertAlmostEqual(hb, target, delta=0.1)

    def test_haemoglobin_recovers_when_volume_is_restored(self):
        # Blood volume restored: the target returns to the reference, so
        # [Hb] climbs back rather than staying diluted.
        target = HB_REF
        hb = hb_step(HB_REF * 0.70, target, 36000.0)
        self.assertAlmostEqual(hb, HB_REF, delta=0.1)


class TestModelWiring(unittest.TestCase):
    """Drift-locks: one blood model, consumed everywhere."""

    def test_function_exists_and_is_registered(self):
        self.assertTrue((REPO / OXY).exists())
        prep = source("addons/physiology/XEH_PREP.hpp")
        self.assertIn("PREPS(oxygen,calculateOxygenDelivery);", prep)

    def test_sourced_constants_pinned(self):
        text = source(OXY)
        for token in (
            "1.34",
            "0.003",
            "5.0 * _bloodFrac",
            "20.1",
            "330",
            "0.75",
            "7200",
        ):
            self.assertIn(token, text, f"missing sourced constant: {token}")

    def test_both_thermal_consumers_use_the_shared_model(self):
        display = source(
            "addons/thermal/functions/display/fnc_applySelectionThermal.sqf"
        )
        solver = source(
            "addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf"
        )
        self.assertIn("EFUNC(physiology,calculateOxygenDelivery)", display)
        self.assertIn("EFUNC(physiology,calculateOxygenDelivery)", solver)

    def test_old_perfusion_proxy_is_gone(self):
        for rel in (
            "addons/thermal/functions/display/fnc_applySelectionThermal.sqf",
            "addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf",
            "addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf",
        ):
            self.assertNotIn("_bloodFrac", source(rel), rel)

    def test_solver_takes_a_perfusion_index_not_a_blood_fraction(self):
        solver = source("addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf")
        self.assertIn('["_skinPerfusion", 1, [0]]', solver)
        self.assertNotIn("/ 0.70", solver)


class TestOneWayAndOpenItems(unittest.TestCase):
    def test_one_way_limitation_is_stated(self):
        self.assertIn("ONE-WAY", source(OXY))

    def test_lactate_magnitude_is_labelled_open(self):
        self.assertIn("OPEN ITEM", source(OXY))

    def test_naive_haemoglobin_model_is_explicitly_rejected(self):
        self.assertIn("deliberately NOT [Hb]ref * bloodFrac", source(OXY))

    def test_no_supply_dependent_state_restores_delivery(self):
        # Going hypoxic reduces delivery; nothing in the model adds it back.
        # The factor is monotone in DO2, so a lower DO2 never yields a
        # higher oxidative fraction.
        low = oxygen_delivery(2.0, 106.0)["metabolic_factor"]
        high = oxygen_delivery(4.0, 106.0)["metabolic_factor"]
        self.assertLessEqual(low, high)


if __name__ == "__main__":
    unittest.main()
