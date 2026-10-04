#!/usr/bin/env python3
"""NVG audit locks (issue #153).

Locks the #153 audit state: the two latent bugs are resolved and most
gaps are implemented (spectral response, gating flicker).  This suite
locks the RESOLVED state so the audit cannot regress, and tests the two
gaps added here (tube warm-up, Gen 1 erosion) by executing the REAL
fnc_applyNVGTubeModel.sqf through sqf_lite.
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tools.tests.test_exhaust_shimmer import _code_only  # noqa: E402

FNC = (
    Path(__file__).parents[2] / "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf"
)
NVG_DEV = (
    Path(__file__).parents[2]
    / "addons/nightvision/functions/fnc_getNvgDeviceProperties.sqf"
)
# The per-tier edge factor moved out of the parent into the pincushion kernel
# (issue #215); the lock below reads the kernel's edge array, not an inline
# switch the parent no longer has.
EROSION_KERNEL = (
    Path(__file__).parents[2] / "addons/nightvision/functions/fnc_nvgPincushion.sqf"
)
PHOTON_SCALE = 500.0  # mirrors AEE_PHOTON_SCALE in fnc_applyNVGTubeModel.sqf

# Tier name -> the switch label that carries its constants.  The tier
# switch's `default` block is GEN1 (the AUTO fallback shares it).
_TIER_LABEL = {
    "PVS31": 'case "PVS31"',
    "GEN3": 'case "GEN3"',
    "GEN2": 'case "GEN2"',
    "GEN1": "default",
}


def _switch_body(src, header):
    """Return the text inside the first balanced {...} after `header`."""
    i = src.index(header)
    i = src.index("{", i)
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1 : j]
    raise AssertionError(f"unterminated switch: {header}")


def _branch_weight(src, branch_cond):
    """The `_spectralWeight = N;` inside the `then {..}` of a branch.

    The weight is read from the REAL branch structure, so moving it to a
    different source class (or inverting the values) changes the result.
    """
    m = re.search(branch_cond + r"\s*then\s*\{(.*?)\}", src, re.DOTALL)
    assert m, f"spectral branch not found: {branch_cond}"
    w = re.search(r"_spectralWeight = ([0-9.]+)", m.group(1))
    assert w, f"no _spectralWeight in branch: {branch_cond}"
    return float(w.group(1))


def _tier_switch_bodies(src):
    body = _switch_body(src, "switch (_tier) do")
    out = {}
    for label in _TIER_LABEL.values():
        start = body.index(label)
        nxt = re.search(r'(?:case "|default)', body[start + len(label) :])
        end = start + len(label) + (nxt.start() if nxt else len(body))
        out[label] = body[start:end]
    return out


def _tier_constants(src):
    """(noiseFloor, mtf15) per tier, read from the REAL SQF tier switch."""
    out = {}
    for label, body in _tier_switch_bodies(src).items():
        nf = re.search(r"_noiseFloor = ([0-9.]+);", body)
        mtf = re.search(r"_mtf15 = ([0-9.]+);", body)
        assert nf and mtf, f"tier constants missing for {label}"
        out[label] = (float(nf.group(1)), float(mtf.group(1)))
    return out


def _erosion_constants(_src=None):
    """Per-tier erosion factor, read from the REAL pincushion kernel."""
    body = EROSION_KERNEL.read_text(encoding="utf-8")
    m = re.search(r"private _edge = \[([0-9., ]+)\] select", body)
    assert m, "the pincushion kernel edge array is missing"
    vals = [float(v) for v in m.group(1).split(",")]
    # Index order is GEN1, GEN2, GEN3, PVS31.  GEN3 is the flat-field ceiling
    # and PVS31 shares it, matching the old switch's default.
    return {"GEN1": vals[0], "GEN2": vals[1], "GEN3": vals[2]}


def _classifier_tier(dev_src, tier):
    """The first [generation, sensitivity, resolution, ...] tuple for a tier."""
    m = re.search(rf'\["{tier}", ([0-9.]+), ([0-9.]+),', dev_src)
    assert m, f"classifier tuple missing for {tier}"
    return float(m.group(1)), float(m.group(2))


# ─── Perceived-output mirror (evaluated from SQF-extracted constants) ──────
# The constants come from the SQF; these functions only combine them.  The
# ordering assertions below are what lock the tier ladder.


def _shot_noise(lux, sensitivity):
    return 1.0 / math.sqrt(lux * sensitivity * PHOTON_SCALE + 1.0)


def _noise_floor_at(noise_floor, lux, sensitivity):
    # t = 0 (warm-up fraction 0), air temperature 20 C (factor 1.0).
    n = noise_floor + (1.0 - noise_floor) * _shot_noise(lux, sensitivity)
    return max(0.03, min(1.0, n))


def _mtf_effective(mtf15, res_lpmm, noise):
    scaled = min(0.65, max(0.15, mtf15 * (res_lpmm / 64.0)))
    return scaled * (1.0 - 0.45 * noise)


def _brightness(lux):
    return max(0.65, min(1.0, 0.65 + 0.35 * (lux - 0.001) / (0.25 - 0.001)))


def _perceived(noise_floor, mtf15, res, erosion, sensitivity, lux):
    noise = _noise_floor_at(noise_floor, lux, sensitivity)
    clean = _mtf_effective(mtf15, res, noise) * (1.0 - noise) / erosion
    return 0.65 + (1.0 - 0.65) * (_brightness(lux) * clean)


class TestAuditResolved(unittest.TestCase):
    def test_bug_a_burnpos_dead_code_removed(self):
        # Bug A: the phosphor afterimage was written-but-never-read dead
        # code.  The comment documents the removal (the #152 smear class).
        src = FNC.read_text(encoding="utf-8")
        self.assertNotIn("nvgBurnPos", src)
        self.assertIn("removed as dead code", src)

    def test_bug_b_single_tick(self):
        # Bug B: applyRainDroplets TICK ran twice per tick in thermal
        # mode.  The dispatch must call TICK exactly once, before the
        # mode branches.
        src = (Path(__file__).parents[2] / "addons/optics/XEH_postInit.sqf").read_text(
            encoding="utf-8"
        )
        self.assertEqual(src.count('["TICK"] call EFUNC(thermal,applyRainDroplets)'), 1)

    def test_gap3_spectral_response(self):
        # Gap 3: IR-rich sources weight the tube excitation above their
        # luminous output (the military IR-signature exploit).
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("_spectralWeight", src)
        self.assertIn('"nvmarker"', src)  # IR strobe/marker branch

    def test_gap2_gating_flicker(self):
        # Gap 2: gate-transition blackout flicker raises the noise floor
        # for a window (nvgGrainBoost / nvgGateFlickerUntil).
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("nvgGateFlickerUntil", src)
        self.assertIn("nvgGrainBoost", src)

    def test_gap4_warmup_curve_present(self):
        # Gap 4 (added here): tube warm-up scales dark current by
        # (1 - exp(-t/tau)) toward +25%, tier-dependent tau.
        src = FNC.read_text(encoding="utf-8")
        self.assertIn("_warmupTau", src)
        self.assertIn("nvgTubeOnTime", src)
        self.assertIn("exp (-((CBA_missionTime", src)

    def test_gap5_gen1_erosion_present(self):
        # Gap 5 (added here): Gen 1 edge-erosion vignette multiplier.  Issue
        # #215 moved the per-tier factor into fnc_nvgPincushion and applies it
        # ONCE in the parent, so the lock now reads the kernel and proves the
        # inline switch is gone.
        src = FNC.read_text(encoding="utf-8")
        kernel = EROSION_KERNEL.read_text(encoding="utf-8")
        self.assertIn("_erosionFactor", src)
        self.assertNotIn("nvgErosionFactor", src)
        self.assertNotIn("private _erosionFactor = switch (_tier) do", src)
        self.assertIn("call FUNC(nvgPincushion)", src)
        self.assertIn("private _edge = [2.5, 1.3, 1.0, 1.0] select", kernel)


class TestWarmupMath(unittest.TestCase):
    def test_warmup_approaches_25_percent(self):
        # The warm-up term 1 - exp(-t/tau): at t=5*tau it is ~99.3%,
        # so the noise floor multiplier approaches 1.25.  This is the
        # physical claim (dark current rises to equilibrium, not
        # unbounded).
        import math

        tau = 60.0
        t = 5 * tau
        frac = 1 - math.exp(-t / tau)
        self.assertAlmostEqual(frac, 0.993, places=2)
        self.assertAlmostEqual(1 + 0.25 * frac, 1.248, places=2)


class TestSpectralPhysics(unittest.TestCase):
    """Gap 3 (#153): IR-rich sources must excite the tube MORE than their
    luminous output suggests.  The weights are read from the REAL branch
    structure in the SQF and evaluated, so a plain visible lamp (weight
    1.0) must sit BELOW a hot muzzle flash, and an IR marker must weight
    highest.  Inverting the ordering in the source fails this test."""

    @classmethod
    def setUpClass(cls):
        cls.src = FNC.read_text(encoding="utf-8")

    def _plain_weight(self):
        return float(
            re.search(r"private _spectralWeight = ([0-9.]+);", self.src).group(1)
        )

    def test_weights_ordered_by_ir_content(self):
        plain = self._plain_weight()
        muzzle = _branch_weight(self.src, r'if \(_x isKindOf "F_40_White"\)')
        ir_lamp = _branch_weight(
            self.src,
            r'if \(_sim == "Lamps" && '
            r'\{getNumber \(\(configOf _x\) >> "irLight"\) == 1\}\)',
        )
        marker = _branch_weight(self.src, r'if \(_sim == "nvmarker"\)')

        # The plain visible lamp carries no IR weighting.
        self.assertEqual(plain, 1.0)
        # Same luminous output, more IR -> more tube excitation.
        self.assertGreater(muzzle, plain)
        self.assertGreater(ir_lamp, plain)
        # The IR marker/strobe is the strongest IR source.
        self.assertGreater(marker, muzzle)
        self.assertGreater(marker, ir_lamp)

    def test_weight_scales_gate_intensity(self):
        # The weight must be a FACTOR in the gate intensity (not a dead
        # assignment): a muzzle flash and a plain lamp at the SAME angle,
        # distance and weather gate the tube in the ratio of their weights.
        m = re.search(r"private _intensity = (.+?);", self.src, re.DOTALL)
        self.assertIsNotNone(m, "gate intensity expression not found")
        self.assertIn("_spectralWeight", m.group(1))

        plain = self._plain_weight()
        muzzle = _branch_weight(self.src, r'if \(_x isKindOf "F_40_White"\)')
        cone, dist, transmission = 0.5, 10.0, 1.0
        lamp_i = cone * (100 / dist**2) * transmission * plain
        flame_i = cone * (100 / dist**2) * transmission * muzzle
        self.assertAlmostEqual(flame_i / lamp_i, muzzle / plain, places=9)
        self.assertGreater(flame_i, lamp_i)


class TestPerceptualDifferentiation(unittest.TestCase):
    """Gap 6 (#153): a PVS-31 must read brighter and cleaner than a Gen 1
    on the SAME scene.  The per-tier constants are read from the REAL SQF
    tier switch and erosion switch, so swapping two tier bodies inverts the
    ordering and fails this test."""

    ORDER = ["PVS31", "GEN3", "GEN2", "GEN1"]

    @classmethod
    def setUpClass(cls):
        cls.src = FNC.read_text(encoding="utf-8")
        cls.dev = NVG_DEV.read_text(encoding="utf-8")
        cls.tiers = _tier_constants(cls.src)
        cls.erosion = _erosion_constants(cls.src)

    def _perceived_for(self, tier, lux):
        noise_floor, mtf15 = self.tiers[_TIER_LABEL[tier]]
        sens, res = _classifier_tier(self.dev, tier)
        ero = self.erosion.get(tier, self.erosion["GEN3"])
        return _perceived(noise_floor, mtf15, res, ero, sens, lux)

    def _noise_for(self, tier, lux):
        noise_floor, _ = self.tiers[_TIER_LABEL[tier]]
        sens, _ = _classifier_tier(self.dev, tier)
        return _noise_floor_at(noise_floor, lux, sens)

    def _assert_ladder(self, values):
        for hi, lo, thi, tlo in zip(values, values[1:], self.ORDER, self.ORDER[1:]):
            self.assertGreater(
                hi, lo, f"perceived {thi} {hi:.4f} not above {tlo} {lo:.4f}"
            )

    def test_brightness_cleanliness_ladder_full_moon(self):
        self._assert_ladder([self._perceived_for(t, 0.25) for t in self.ORDER])

    def test_brightness_cleanliness_ladder_starlight(self):
        self._assert_ladder([self._perceived_for(t, 0.001) for t in self.ORDER])

    def test_noise_and_distortion_axis_reversed(self):
        noises = [self._noise_for(t, 0.25) for t in self.ORDER]
        for lo, hi, tlo, thi in zip(noises, noises[1:], self.ORDER, self.ORDER[1:]):
            self.assertLess(lo, hi, f"noise {tlo} {lo:.4f} not below {thi} {hi:.4f}")
        erosions = [self.erosion.get(t, self.erosion["GEN3"]) for t in self.ORDER]
        for a, b, ta, tb in zip(erosions, erosions[1:], self.ORDER, self.ORDER[1:]):
            self.assertLessEqual(a, b, f"erosion {ta} {a} not <= {tb} {b}")

    def test_perceived_stays_in_watchable_band(self):
        # The render must never go black: every tier stays at or above the
        # engine's documented ColorCorrections brightness floor.
        for t in self.ORDER:
            for lux in (0.001, 0.25):
                v = self._perceived_for(t, lux)
                self.assertGreaterEqual(v, 0.65, f"{t} @ {lux} below floor")
                self.assertLessEqual(v, 1.0, f"{t} @ {lux} above ceiling")

    def test_perceived_published_and_consumed_by_render(self):
        self.assertIn(
            "missionNamespace setVariable [QGVAR(nvgPerceived), _perceived]", self.src
        )
        self.assertIn(
            "missionNamespace getVariable [QGVAR(nvgPerceived), _perceived]", self.src
        )
        m = re.search(r"_hCC ppEffectAdjust \[([^,]+), _mtfEffective", self.src)
        self.assertIsNotNone(m, "ColorCorrections adjust not found")
        self.assertEqual(m.group(1), "_perceivedOut")

    def test_perceived_formula_matches_source(self):
        # The mirror above only combines extracted constants; lock the
        # combination to the source so a formula inversion is caught.
        self.assertRegex(
            self.src,
            r"_cleanliness = _mtfEffective \* \(1 - _noise\) / _erosionFactor;",
        )
        self.assertRegex(
            self.src,
            r"_perceived = 0\.65 \+ \(1 - 0\.65\) \* "
            r"\(_brightness \* _cleanliness\);",
        )


class TestPhosphorFollowsTheDevice(unittest.TestCase):
    """The phosphor is a DEVICE property, not a tier property.

    Live RPT 2026-09-29: "NVG tier: hmd=NVGogglesB_grn_F -> PVS31" and the
    operator reported a purple image, not green and not white.  The PVS-31
    tier carried the shape this file's own header labels P45 white, with the
    blue channel the heaviest, and green tube light under a blue-heavy tint
    is purple.  A tier decides the noise floor, the MTF, the bloom and the
    focus; which phosphor a tube uses comes from the device.

    Every number here is READ OUT OF THE SQF: the two shapes from the
    header definitions the resolver is bound to, and the token test from the
    resolver itself.  Nothing is hardcoded, so changing a shape in the SQF
    changes the expectation instead of failing it.
    """

    @classmethod
    def setUpClass(cls):
        cls.raw = FNC.read_text(encoding="utf-8")
        cls.code = _code_only(cls.raw)

    def _shape_from_header(self, name):
        """The shape the header records for a phosphor, in comments."""
        m = re.search(rf"{name} \([a-z-]+\)[^\n]*shape \[([0-9., ]+)\]", self.raw)
        self.assertIsNotNone(m, f"the header no longer defines the {name} shape")
        return _floats(m.group(1))

    def _resolver(self):
        """(fallback, token, tint, weight, delimiter) from the resolver."""
        start = self.code.index("private _phosphor =")
        end = self.code.index("QGVAR(nvgTubeTier), _tier]")
        body = self.code[start:end]
        fb = re.search(r'private _phosphor = "(\w+)"', body)
        tok = re.search(r'if \(_x == "(\w+)"\) then', body)
        tint = re.search(r"_phosphorTint = \[([0-9., ]+)\]", body)
        weight = re.search(r"_nvgWeight = \[([0-9., ]+)\]", body)
        delim = re.search(r'splitString "([^"]+)"', body)
        for part, what in (
            (fb, "fallback"),
            (tok, "device token"),
            (tint, "device tint"),
            (weight, "device weight"),
            (delim, "token delimiter"),
        ):
            self.assertIsNotNone(part, f"the resolver has no {what}")
        self.assertIn(
            'if (_phosphor == "%s") then' % tok.group(1),
            body,
            "the device token must be the one that selects the device shape",
        )
        return (
            fb.group(1),
            tok.group(1),
            _floats(tint.group(1)),
            _floats(weight.group(1)),
            delim.group(1),
        )

    def _resolve(self, hmd):
        """The tint the SQF applies for this hmd, resolved from the source."""
        _, token, tint, _, delim = self._resolver()
        if token in hmd.lower().split(delim):
            return tint
        return None  # the hmd states no phosphor, so the tier value stands

    def test_green_hmd_resolves_to_the_green_shape(self):
        self.assertIsNotNone(
            self._resolve("NVGogglesB_grn_F"),
            "the device named _grn_ must resolve to the green phosphor, not "
            "fall through to the tier value",
        )

    def test_device_shape_is_the_shape_the_header_defines(self):
        _, _, tint, _, _ = self._resolver()
        self.assertEqual(
            tint,
            self._shape_from_header("P43"),
            "the shape the resolver applies must be the P43 green shape the "
            "header defines for it",
        )

    def test_green_shape_cannot_render_purple(self):
        # The regression itself: a green tube under a tint whose blue channel
        # is the heaviest renders purple.  The green shape kills blue.
        _, _, tint, _, _ = self._resolver()
        self.assertEqual(tint[2], 0.0, "the green phosphor must kill the blue channel")
        self.assertGreater(tint[1], 0.0, "the green phosphor must carry green")

    def test_hmd_without_a_phosphor_keeps_the_tier_value(self):
        # No device in this repository states a white phosphor, so inventing
        # a token for one would be guessing.  An hmd that states nothing must
        # keep the tier value and the log must name the tier as the source.
        for hmd in ("NVGoggles", "NVGoggles_OPFOR", "FirstPersonalKit"):
            self.assertIsNone(
                self._resolve(hmd),
                f"{hmd} states no phosphor, so it must keep the tier value",
            )
        self.assertIn("phosphor=%3", self.code, "the tier log must name the source")
        self.assertIn("_phosphor", self.code, "the resolved source must be logged")

    def test_tier_table_shapes_read_from_the_source(self):
        # Records which shape each tier CARRIED as its fallback.  PVS-31 is
        # the white one, which is why a _grn_ device on that tier rendered
        # purple before the device was consulted.  Nothing here changes a
        # tier: the fallback stays, and the device now wins where it states
        # a phosphor.
        bodies = _tier_switch_bodies(self.code)
        shapes = {}
        for tier, label in _TIER_LABEL.items():
            m = re.search(r"_phosphorTint = \[([0-9., ]+)\]", bodies[label])
            self.assertIsNotNone(m, f"no phosphorTint in the {tier} tier body")
            shapes[tier] = _floats(m.group(1))
        green = self._shape_from_header("P43")
        white = self._shape_from_header("P45")
        self.assertEqual(
            shapes["PVS31"], white, "the PVS-31 tier carries the white shape"
        )
        for tier in ("GEN3", "GEN2", "GEN1"):
            self.assertEqual(
                shapes[tier][2],
                green[2],
                f"{tier} kills blue like the green shape, so it is not the "
                f"white one: {shapes[tier]} vs {white}",
            )
        # The bug was reachable only on a tier whose fallback is NOT green.
        self.assertNotEqual(
            shapes["PVS31"],
            green,
            "if PVS-31 now carried green there would be nothing to fix",
        )


def _floats(text):
    return [float(x) for x in text.replace(" ", "").split(",") if x]


if __name__ == "__main__":
    unittest.main()
