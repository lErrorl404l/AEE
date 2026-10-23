#!/usr/bin/env python3
"""Gate the independent ballistic verifier over a fixed representative set.

The verifier (tools/validation/verify_ballistics.py) recomputes the AEE
trajectory equations in Python and compares them with py-ballisticcalc.  This
suite runs it over eleven bullets that span G1 and G7 and 5.56 mm to .50 BMG,
then asserts three things:

- The run exits 0, so no compared bullet disagrees above tolerance.
- The written report names a non-zero number of compared bullets, so the run
  did not silently compare nothing.
- Both published worked examples are still reproduced within their stated
  tolerance, so the solver itself is still sound.

The screens are asserted to fire on a planted defect.  A screen that never
fires is an untested screen, and the corpus happens to be clean.

Dependency: py-ballisticcalc (pinned in tools/requirements-tooling.txt, which
the CI install step reads).  When the library is absent the suite skips, which
is the same pattern tools/tests/test_sensitivity.py uses for SALib.

The full corpus run is the `if __name__ == "__main__"` path, not the fast sweep:

    python3 tools/tests/test_ballistic_verifier.py --full
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "tools" / "validation") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "validation"))

try:
    import py_ballisticcalc  # noqa: F401

    _SOLVER = True
except ImportError:
    _SOLVER = False

# The form-factor screen and its review check touch no solver, so they are
# imported and tested even when py-ballisticcalc is absent.
import verify_ballistics as verifier  # noqa: E402


@unittest.skipUnless(
    _SOLVER,
    "py-ballisticcalc not installed (pip install -r tools/requirements-tooling.txt)",
)
class TestBallisticVerifier(unittest.TestCase):
    """The verifier agrees with an independent solver across the corpus sample."""

    @classmethod
    def setUpClass(cls) -> None:
        # The reports go to a scratch directory, so a test run never rewrites
        # the committed report, which is the full-corpus one.
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out_dir = Path(cls.tmp.name)
        cls.status = verifier.main([], out_dir=cls.out_dir)
        cls.report = json.loads(
            (cls.out_dir / "verification.json").read_text(encoding="utf-8")
        )
        cls.projectiles, cls.loads, _ = verifier.load_corpus()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_exit_status_is_zero(self):
        self.assertEqual(self.status, 0, "the verifier reported a data error")

    def test_report_names_a_nonzero_number_of_compared_bullets(self):
        self.assertGreaterEqual(self.report["counts"]["compared"], 8)
        self.assertTrue(
            (self.out_dir / "verification.json").exists(),
            "the machine-readable report was not written",
        )
        self.assertTrue(
            (self.out_dir / "VERIFICATION.md").exists(), "the report was not written"
        )

    def test_no_trajectory_disagreement_above_tolerance(self):
        self.assertEqual(self.report["counts"]["trajectory_disagreements"], 0)
        self.assertEqual(self.report["counts"]["gross_disagreements"], 0)

    def test_representative_set_spans_both_drag_models(self):
        models = {c["model"] for c in self.report["compared"]}
        self.assertEqual(models, {"G1", "G7"})

    def test_drift_bias_is_measured_and_small(self):
        bias = self.report["counts"]["mean_drift_bias"]
        self.assertLess(abs(bias), 0.01, f"drift bias {bias:+.2%} exceeds 1 percent")

    def test_published_examples_are_reproduced(self):
        for example in self.report["published_examples"]:
            self.assertTrue(example["passed"], f"{example['id']} is not reproduced")
            self.assertTrue(example["url"].startswith("https://www.lapua.com/"))
            self.assertEqual(len(example["sha256"]), 64)


@unittest.skipUnless(
    _SOLVER,
    "py-ballisticcalc not installed (pip install -r tools/requirements-tooling.txt)",
)
class TestBallisticScreens(unittest.TestCase):
    """Each data screen fires on a planted defect."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.projectiles, cls.loads, _ = verifier.load_corpus()
        cls.band = verifier.derive_form_factor_band(cls.projectiles)

    def test_form_factor_band_derivation_is_from_measured_records(self):
        self.assertGreaterEqual(self.band["measured_count"], 10)
        self.assertLess(self.band["g7_min"], self.band["g7_max"])
        self.assertGreaterEqual(len(self.band["groups"]), 3)

    def test_form_factor_screen_flags_a_decimal_shifted_coefficient(self):
        planted = {
            "projectile_id": "planted_bc_shift",
            "names": ["planted"],
            "values": {
                "mass_g": {"value": 10.0, "grade": "planted"},
                "diameter_mm": {"value": 7.82, "grade": "planted"},
                "bc_g7": {"value": 0.023, "grade": "planted"},
            },
        }
        flags = verifier.screen_form_factor([planted], self.band)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["projectile_id"], "planted_bc_shift")
        self.assertGreater(flags[0]["form_factor"], flags[0]["band"][1])

    def test_form_factor_screen_accepts_a_consistent_record(self):
        group = self.band["groups"]["0.31"]
        mass_g = 9.72
        sd = (mass_g / 0.06479891 / 7000) / (0.308**2)
        planted = {
            "projectile_id": "planted_consistent",
            "names": ["planted"],
            "values": {
                "mass_g": {"value": mass_g, "grade": "planted"},
                "diameter_mm": {"value": 7.82, "grade": "planted"},
                "bc_g7": {"value": sd / group["median"], "grade": "planted"},
            },
        }
        self.assertEqual(verifier.screen_form_factor([planted], self.band), [])

    def test_transposition_screen_flags_a_model_field_mismatch(self):
        planted = {
            "projectile_id": "planted_model_mismatch",
            "names": ["planted"],
            "values": {
                "mass_g": {"value": 10.0},
                "diameter_mm": {"value": 7.82},
                "bc_g1": {"value": 0.46, "drag_model": "G7", "grade": "planted"},
            },
        }
        flags = verifier.screen_transposition([planted], self.loads, self.band)
        self.assertIn("drag_model_field", {f["subclass"] for f in flags})

    def test_transposition_screen_flags_a_decade_shifted_ballistic_coefficient(self):
        planted = {
            "projectile_id": "planted_decade",
            "names": ["planted"],
            "values": {
                "mass_g": {"value": 10.0},
                "diameter_mm": {"value": 7.82},
                "bc_g1": {"value": 2.3, "grade": "planted"},
                "bc_g7": {"value": 0.23, "grade": "planted"},
            },
        }
        flags = verifier.screen_transposition([planted], self.loads, self.band)
        self.assertIn("bc_decimal_shift", {f["subclass"] for f in flags})

    def test_transposition_screen_flags_a_negative_drag_model_declaration(self):
        planted = {
            "projectile_id": "planted_only_g7",
            "names": ["planted"],
            "values": {
                "mass_g": {"value": 10.0},
                "diameter_mm": {"value": 7.82},
                "bc_g7": {"value": 0.23, "grade": "planted"},
                "drag_model": {"value": "G1"},
            },
        }
        flags = verifier.screen_transposition([planted], self.loads, self.band)
        self.assertIn("drag_model_field", {f["subclass"] for f in flags})


class TestFormFactorReviews(unittest.TestCase):
    """A review answers a flag without moving the band or the coefficient."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.projectiles, _loads, _weapons = verifier.load_corpus()
        cls.band = verifier.derive_form_factor_band(cls.projectiles)

    def planted(self, review=None) -> dict:
        record = {
            "projectile_id": "planted_reviewed",
            "names": ["planted"],
            "values": {
                "mass_g": {"value": 10.0, "grade": "planted"},
                "diameter_mm": {"value": 7.82, "grade": "planted"},
                "bc_g7": {"value": 0.023, "grade": "planted"},
            },
        }
        if review is not None:
            record["form_factor_review"] = review
        return record

    def review(self, decision="genuine") -> dict:
        return {
            "decision": decision,
            "reason": "Berger states this coefficient and its own form factor for the bullet.",
            "evidence": ["berger_bullets"],
            "reviewed": "2026-10-23",
        }

    def test_the_corpus_raises_no_open_form_factor_flag(self):
        flags = verifier.screen_form_factor(self.projectiles, self.band)
        open_flags, reviewed, problems = verifier.split_reviewed_flags(
            self.projectiles, flags
        )
        self.assertEqual(problems, [])
        self.assertEqual(open_flags, [])
        self.assertEqual(len(reviewed), len(flags))
        self.assertTrue(all(f["decision"] == "genuine" for f in reviewed))

    def test_a_review_closes_a_flag_without_moving_the_value(self):
        record = self.planted(self.review())
        flags = verifier.screen_form_factor([record], self.band)
        open_flags, reviewed, problems = verifier.split_reviewed_flags([record], flags)
        self.assertEqual(open_flags, [])
        self.assertEqual(problems, [])
        self.assertEqual(len(reviewed), 1)
        self.assertEqual(reviewed[0]["decision"], "genuine")
        self.assertEqual(reviewed[0]["form_factor"], flags[0]["form_factor"])

    def test_a_correction_decision_on_a_still_flagged_record_is_a_defect(self):
        record = self.planted(self.review("source_error"))
        flags = verifier.screen_form_factor([record], self.band)
        _open_flags, _reviewed, problems = verifier.split_reviewed_flags(
            [record], flags
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("still outside the band", problems[0])

    def test_a_review_on_a_record_inside_the_band_is_stale(self):
        group = self.band["groups"]["0.31"]
        mass_g = 9.72
        sd = (mass_g / 0.06479891 / 7000) / (0.308**2)
        record = self.planted(self.review())
        record["values"]["mass_g"]["value"] = mass_g
        record["values"]["bc_g7"]["value"] = sd / group["median"]
        flags = verifier.screen_form_factor([record], self.band)
        self.assertEqual(flags, [])
        _open_flags, _reviewed, problems = verifier.split_reviewed_flags(
            [record], flags
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("stale", problems[0])

    def test_an_unknown_decision_is_a_defect(self):
        record = self.planted(self.review("looks_about_right"))
        flags = verifier.screen_form_factor([record], self.band)
        _open_flags, _reviewed, problems = verifier.split_reviewed_flags(
            [record], flags
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("is not one of", problems[0])


def run_full() -> int:
    """Compare the whole corpus. This is not part of the fast sweep."""
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "validation"))
    if not _SOLVER:
        print("py-ballisticcalc is not installed, so the full run cannot start")
        return 2
    return verifier.main(["--full"])


if __name__ == "__main__":
    if "--full" in sys.argv:
        raise SystemExit(run_full())
    unittest.main()
