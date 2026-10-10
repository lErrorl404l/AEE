#!/usr/bin/env python3
"""Global sensitivity analysis of the AEE physiology models with SALib.

The mod's constants (the sleep time constants, the circadian amplitude and
phase, the shooter cold/heat/fatigue curves) were chosen from the literature.
This suite asks which of them actually drive the model output, so validation
effort can be aimed at the parameters that matter.  It screens with the cheap
Morris elementary effects first, then decomposes the variance with Sobol.

Method (grounded in the cited literature, no invented data):
- Morris 1991 elementary effects: mu_star ranks influence by magnitude, sigma
  flags non-linearity or interaction.
- Sobol 1993 variance decomposition: S1 (first order) and ST (total order).
  The difference ST - S1 is the interaction share.
- Saltelli et al. 2010, "Variance based sensitivity analysis of model output.
  Design and estimator for the total sensitivity index", Comput. Phys.
  Commun. 181:259-270.

The analysis runs the SHIPPED models: the sleep mirror in
tools/tests/test_sleep_model.py and the stability mirror in
tools/tests/test_shooter_stability.py.  The sampled sleep constants are
written into the mirror's module globals for the call, so the model under
test is the model in the repository, not a re-implementation.

Reproducibility: the fixed seed (SEED) and the committed problem definitions
(SLEEP_PROBLEM, STABILITY_PROBLEM) below fix every sample and every index.

Dependency: SALib (pinned in .github/workflows/ci.yml).  CI installs it, so
the ranking gates run there.  When SALib is absent the suite skips, matching
the optional-library pattern in tools/validation.

Run: python3 -m unittest tools.tests.test_sensitivity -v
     python3 tools/tests/test_sensitivity.py    (prints the report)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import tools.tests.test_sleep_model as _sleep
from tools.tests.test_shooter_stability import stability

try:
    from SALib.analyze import morris as _morris_analyze
    from SALib.analyze import sobol as _sobol_analyze
    from SALib.sample import morris as _morris_sample

    # `SALib.sample.sobol` is the current name for the Saltelli sampler.
    from SALib.sample import sobol as _sobol_sample

    _SALIB = True
except ImportError:  # pragma: no cover - exercised where SALib is absent
    _SALIB = False

_SEED = 42

# --- Committed screening configuration -------------------------------------
# Sleep-model constants (Morris).  Bounds bracket the nominal constants in
# test_sleep_model.py: tau_s 18.2 h, tau_d 4.2 h, amp 0.12, phi 12.0.
SLEEP_PROBLEM = {
    "num_vars": 4,
    "names": ["tau_s", "tau_d", "amp", "phi"],
    "bounds": [[12.0, 24.0], [2.0, 8.0], [0.05, 0.2], [8.0, 16.0]],
}
SLEEP_MORRIS_N = 50
SLEEP_LEVELS = 4

# Shooter-stability inputs (Sobol).  Bounds are the operational envelope:
# cold ambient -40..50 degC, WBGT 0..59 degC, 0..96 h awake.
STABILITY_PROBLEM = {
    "num_vars": 3,
    "names": ["cold", "heat", "fatigue"],
    "bounds": [[-40.0, 50.0], [0.0, 59.0], [0.0, 96.0]],
}
STABILITY_SOBOL_N = 512

# Representative operational point for the sleep screen: a 24 h watch read at
# 18:00, the end of the evening watch in the circadian wake-maintenance zone.
SLEEP_WAKE_HOURS = 24.0
SLEEP_LOCAL_HOUR = 18.0


def _sleep_output(params, index):
    """Run the shipped sleep model with the sampled constants injected.

    ``sleep_pressure`` reads the module globals TAU_S, TAU_D, AMP and PHI, so
    the sampled values are set for the call and restored after it.  Index 0 is
    process S (sleep pressure), index 2 is the sleepiness (S - C).
    """
    tau_s, tau_d, amp, phi = params
    saved = (_sleep.TAU_S, _sleep.TAU_D, _sleep.AMP, _sleep.PHI)
    _sleep.TAU_S, _sleep.TAU_D, _sleep.AMP, _sleep.PHI = tau_s, tau_d, amp, phi
    try:
        return _sleep.sleep_pressure(SLEEP_WAKE_HOURS, 0.0, SLEEP_LOCAL_HOUR, False)[
            index
        ]
    finally:
        _sleep.TAU_S, _sleep.TAU_D, _sleep.AMP, _sleep.PHI = saved


def morris_screening():
    """Morris elementary effects for the sleep model.

    One trajectory set drives both outputs: process S (sleep pressure) and the
    sleepiness S - C that feeds the fatigue factor.
    """
    X = _morris_sample.sample(
        SLEEP_PROBLEM, N=SLEEP_MORRIS_N, num_levels=SLEEP_LEVELS, seed=_SEED
    )
    y_pressure = np.array([_sleep_output(x, 0) for x in X])
    y_sleepiness = np.array([_sleep_output(x, 2) for x in X])
    return {
        "X": X,
        "pressure": _morris_analyze.analyze(
            SLEEP_PROBLEM, X, y_pressure, num_levels=SLEEP_LEVELS, seed=_SEED
        ),
        "sleepiness": _morris_analyze.analyze(
            SLEEP_PROBLEM, X, y_sleepiness, num_levels=SLEEP_LEVELS, seed=_SEED
        ),
    }


def sobol_decomposition():
    """Sobol variance decomposition of the shooter stability model."""
    X = _sobol_sample.sample(
        STABILITY_PROBLEM, STABILITY_SOBOL_N, calc_second_order=True
    )
    Y = np.array([stability(x[0], x[1], x[2]) for x in X])
    return {
        "X": X,
        "Y": Y,
        "Si": _sobol_analyze.analyze(
            STABILITY_PROBLEM, Y, calc_second_order=True, seed=_SEED
        ),
    }


@unittest.skipUnless(_SALIB, "SALib not installed (pip install SALib==1.6.0)")
class TestSleepModelMorris(unittest.TestCase):
    """Morris screening: rank the sleep-model constants by elementary effect."""

    @classmethod
    def setUpClass(cls):
        cls.result = morris_screening()

    def test_mu_star_non_negative(self):
        # mu_star is the mean absolute elementary effect, so it is never
        # negative (the issue's contract).
        self.assertTrue(np.all(self.result["pressure"]["mu_star"] >= 0.0))
        self.assertTrue(np.all(self.result["sleepiness"]["mu_star"] >= 0.0))

    def test_tau_s_ranks_first_for_sleep_pressure(self):
        # Physically plausible and the issue's acceptance: the rise constant
        # tau_s is the most sensitive parameter for sleep pressure.
        names = SLEEP_PROBLEM["names"]
        mu = self.result["pressure"]["mu_star"]
        self.assertEqual(names[int(np.argmax(mu))], "tau_s")
        self.assertGreater(mu[names.index("tau_s")], 0.0)

    def test_tau_s_ranks_first_for_sleepiness(self):
        names = SLEEP_PROBLEM["names"]
        mu = self.result["sleepiness"]["mu_star"]
        self.assertEqual(names[int(np.argmax(mu))], "tau_s")

    def test_sleep_pressure_depends_only_on_tau_s_when_awake(self):
        # Process S while awake is 1 - exp(-h / tau_s): the decay constant and
        # the circadian terms are structurally inert.  A drift lock, not a
        # tolerance.
        names = SLEEP_PROBLEM["names"]
        mu = self.result["pressure"]["mu_star"]
        for inert in ("tau_d", "amp", "phi"):
            self.assertLess(mu[names.index(inert)], 1e-9, inert)

    def test_phi_flags_interaction(self):
        # sigma > mu_star means the elementary effect changes sign or scale as
        # the other inputs move: the circadian phase interacts, the time
        # constant does not (Morris 1991; Saltelli 2010 on interaction).
        names = SLEEP_PROBLEM["names"]
        si = self.result["sleepiness"]
        i_phi = names.index("phi")
        i_tau = names.index("tau_s")
        self.assertGreater(si["sigma"][i_phi], si["mu_star"][i_phi])
        self.assertLess(si["sigma"][i_tau], si["mu_star"][i_tau])


@unittest.skipUnless(_SALIB, "SALib not installed (pip install SALib==1.6.0)")
class TestShooterStabilitySobol(unittest.TestCase):
    """Sobol variance decomposition of the shooter stability model."""

    @classmethod
    def setUpClass(cls):
        cls.result = sobol_decomposition()

    def test_total_order_at_least_first_order(self):
        # ST >= S1 always, because ST adds the interaction share (the issue's
        # contract).
        Si = self.result["Si"]
        self.assertTrue(np.all(np.array(Si["ST"]) >= np.array(Si["S1"]) - 1e-6))

    def test_indices_in_unit_interval(self):
        Si = self.result["Si"]
        for key in ("S1", "ST"):
            self.assertTrue(np.all(np.array(Si[key]) >= 0.0), key)
            self.assertTrue(np.all(np.array(Si[key]) <= 1.0), key)

    def test_first_order_sum_bounded(self):
        # For independent inputs the first-order indices sum to <= 1.
        Si = self.result["Si"]
        self.assertLessEqual(float(np.sum(Si["S1"])), 1.0 + 1e-6)

    def test_cold_is_most_influential(self):
        # Physically plausible: cold has the widest degradation band (1.0 at
        # 15 degC down to the 0.3 floor), so it carries the most variance.
        names = STABILITY_PROBLEM["names"]
        Si = self.result["Si"]
        self.assertEqual(names[int(np.argmax(Si["S1"]))], "cold")
        self.assertEqual(names[int(np.argmax(Si["ST"]))], "cold")

    def test_interactions_are_non_negative(self):
        Si = self.result["Si"]
        s2 = np.array(Si["S2"])
        finite = s2[np.isfinite(s2)]
        self.assertTrue(np.all(finite >= -1e-6))

    def test_output_bounded_by_model_clamp(self):
        # stability() clamps to [0.2, 1.0]; every sample must stay inside.
        Y = self.result["Y"]
        self.assertGreaterEqual(float(Y.min()), 0.2 - 1e-9)
        self.assertLessEqual(float(Y.max()), 1.0 + 1e-9)


def build_report():
    """Return the issue's report: rankings, interaction flags, recommendations."""
    lines = ["AEE physiology sensitivity analysis (SALib)", ""]
    if not _SALIB:
        lines.append("SALib is not installed: pip install SALib==1.6.0")
        return "\n".join(lines)

    m = morris_screening()
    names = SLEEP_PROBLEM["names"]
    lines.append(
        "Morris screening, sleep model (mu_star ranks, sigma flags interaction):"
    )
    for label, key in (
        ("sleep pressure (process S)", "pressure"),
        ("sleepiness (process S - process C)", "sleepiness"),
    ):
        si = m[key]
        lines.append(f"  {label}:")
        for i in np.argsort(si["mu_star"])[::-1]:
            lines.append(
                f"    {names[i]:6s} mu*={si['mu_star'][i]:.5f}  sigma={si['sigma'][i]:.5f}"
            )

    s = sobol_decomposition()
    sname = STABILITY_PROBLEM["names"]
    Si = s["Si"]
    lines.append("")
    lines.append(
        "Sobol decomposition, shooter stability (S1 first order, ST total order):"
    )
    for i in np.argsort(Si["ST"])[::-1]:
        lines.append(
            f"    {sname[i]:8s} S1={Si['S1'][i]:.4f}  ST={Si['ST'][i]:.4f}"
            f"  ST-S1={Si['ST'][i] - Si['S1'][i]:.4f}"
        )

    lines.append("")
    lines.append(
        "Recommendation: tighten the validation bounds on the highest-ranked "
        "parameters.  For the sleep model that is tau_s; tau_d is inert while "
        "awake and only drives recovery, so it needs the loosest awake-phase "
        "bound.  For shooter stability that is cold and fatigue; heat is the "
        "weaker driver (0.6 floor, interaction-free)."
    )
    return "\n".join(lines)


def main():
    print(build_report())
    unittest.main()


if __name__ == "__main__":
    main()
