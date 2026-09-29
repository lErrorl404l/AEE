#!/usr/bin/env python3
"""Refractive shock trace renderer verification (issue #217 follow-on).

Verifies fnc_renderSupersonicTrace.sqf, its CfgCloudlets shape, its Fired
wiring, and the honesty labels.  Per the note in tools/tests/sqf_lite.py a
hand-transcribed Python mirror is NOT acceptable, because a mirror once
replicated the SQF's own bugs and drifted from the source.  So this test
PARSES the real SQF and the real config, and reads every asserted string
out of the file it tests.

The kernel is a separate, already verified unit.  This test guards the
CONSUMER: that it calls the kernel with the round's own velocity, that the
kernel keeps its own arithmetic, that the engine refract path is declared
once and consumed, that the per-tick re-read and the reap are visible, and
that the retracted condensation claim stays retracted.

Run: python3 -m unittest tools/tests/test_fx_supersonic_trace.py
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RENDERER = REPO / "addons/fx/functions/particle/fnc_renderSupersonicTrace.sqf"
FX_PREP = REPO / "addons/fx/XEH_PREP.hpp"
FX_POST = REPO / "addons/fx/XEH_postInit.sqf"
FX_CONFIG = REPO / "addons/fx/config.cpp"
KERNEL = REPO / "addons/ballistics/functions/fnc_calculateSupersonicTrace.sqf"
ANNEX_C = REPO / "docs/wiki/annexes/annex-c-variable-reference.qmd"
PHYSICS = REPO / "docs/wiki/chapters/physics.qmd"

SOURCE = RENDERER.read_text(encoding="utf-8")
POST = FX_POST.read_text(encoding="utf-8")
CONFIG = FX_CONFIG.read_text(encoding="utf-8")


def prose(path: Path) -> str:
    """Read a file and flatten its line breaks.

    Header comments wrap, so a phrase such as "does not model
    condensation" is split across two lines.  Collapsing whitespace tests
    the claim rather than the line wrapping.
    """
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


SOURCE_PROSE = prose(RENDERER).upper()


class RendererWiring(unittest.TestCase):
    """The renderer must be reached from a real event handler."""

    def test_renderer_file_exists(self) -> None:
        self.assertTrue(RENDERER.exists())

    def test_registered_in_prep(self) -> None:
        prep = FX_PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(particle,renderSupersonicTrace);", prep)

    def test_called_from_a_fired_handler(self) -> None:
        # Raw BIS "Fired" on the local unit, not a CBA bus registration, which
        # carries no engine events (measured 2026-09-29).
        self.assertIn('"Fired"', POST)
        self.assertIn("installPlayerEngineHandler", POST)
        self.assertRegex(POST, r"call FUNC\(renderSupersonicTrace\)")

    def test_handler_passes_the_projectile_and_guards_the_local_unit(self) -> None:
        fired = POST[POST.index('"Fired"') :]
        self.assertIn("call CBA_fnc_currentUnit", fired)
        self.assertIn("_projectile", fired)
        self.assertIn("isNull _projectile", fired)

    def test_renderer_refuses_without_an_interface(self) -> None:
        # A dedicated server must create no particle source at all.
        self.assertIn("if (!hasInterface) exitWith {}", SOURCE)


class KernelConsumption(unittest.TestCase):
    """The kernel is re-read each tick with the round's own velocity."""

    def test_calls_the_kernel(self) -> None:
        self.assertRegex(SOURCE, r"call EFUNC\(ballistics,calculateSupersonicTrace\)")

    def test_velocity_argument_is_the_projectile_not_a_constant(self) -> None:
        call = re.search(
            r"\[([^\]]*)\]\s*call EFUNC\(ballistics,calculateSupersonicTrace\)", SOURCE
        )
        self.assertIsNotNone(call, "kernel call not found")
        args = call.group(1)
        for bad in ("905", "343", "_initSpeed"):
            self.assertNotIn(bad, args, msg=f"hard-coded velocity {bad}")
        # The speed must be derived from the round itself.  The call may
        # pass it through a local, so assert the derivation, not the
        # literal expression inside the argument list.
        derived = re.search(
            r"_speed\s*=\s*vectorMagnitude\s*\(velocity _projectile\)", SOURCE
        )
        self.assertIsNotNone(derived, "_speed must come from the projectile velocity")
        self.assertIn("_speed", args, msg="the call must pass the derived speed")

    def test_environment_is_passed_not_assumed(self) -> None:
        # The kernel defaults to ISA sea level, which would be wrong at
        # altitude.  The renderer reads the live environment once.
        self.assertIn("getEnvironmentState", SOURCE)
        self.assertIn("_rhoRel", SOURCE)
        self.assertIn("_tempC", SOURCE)

    def test_re_read_is_inside_the_loop(self) -> None:
        loop = re.search(r"while\s*\{", SOURCE)
        self.assertIsNotNone(loop, "per-tick loop not found")
        call = re.search(r"call EFUNC\(ballistics,calculateSupersonicTrace\)", SOURCE)
        self.assertIsNotNone(call)
        self.assertGreater(
            call.start(), loop.start(), "the kernel call must sit inside the loop"
        )

    def test_reap_is_deterministic(self) -> None:
        self.assertIn("deleteVehicle _source", SOURCE)
        self.assertIn("alive _projectile", SOURCE)

    def test_does_not_read_the_muzzle_variable(self) -> None:
        # The muzzle value is superseded by the per-tick read.
        self.assertNotIn("aee_ballistics_supersonicTrace", SOURCE)
        self.assertNotIn("EGVAR(ballistics,supersonicTrace)", SOURCE)


class KernelNotScaled(unittest.TestCase):
    """The renderer is a consumer.  The kernel keeps its own arithmetic."""

    def test_kernel_scales_only_its_reporting_unit(self) -> None:
        kernel = KERNEL.read_text(encoding="utf-8")
        self.assertIn("_contrast / 0.0001", kernel)
        self.assertNotIn("settingsConfigFile", kernel)
        self.assertNotIn("missionNamespace setVariable", kernel)

    def test_kernel_does_not_know_the_renderer(self) -> None:
        self.assertNotIn("renderSupersonicTrace", KERNEL.read_text(encoding="utf-8"))

    def test_visual_mapping_stays_out_of_the_kernel(self) -> None:
        kernel = prose(KERNEL).lower()
        self.assertNotIn("legibility", kernel)
        self.assertNotIn("visual mapping", kernel)


class CfgCloudletsShape(unittest.TestCase):
    """The engine refract path is declared once, and consumed."""

    def test_class_is_declared(self) -> None:
        self.assertRegex(CONFIG, r"class\s+AEE_SupersonicTrace\s*:\s*Default")

    def test_uses_the_engine_refract_path(self) -> None:
        self.assertIn("\\A3\\data_f\\ParticleEffects\\Universal\\refract", CONFIG)

    def test_base_data_is_a_requirement(self) -> None:
        # The shape ships in the base game data_f package, so fx must
        # declare that dependency.
        self.assertRegex(CONFIG, r'"A3_Data_F"')

    def test_renderer_reads_the_shape_from_the_class(self) -> None:
        self.assertIn('"CfgCloudlets" >> "AEE_SupersonicTrace"', SOURCE)
        self.assertIn("particleShape", SOURCE)


class HonestyLabels(unittest.TestCase):
    """The retracted condensation claim must stay retracted."""

    def test_does_not_claim_condensation(self) -> None:
        for phrase in (
            "DOES NOT MODEL CONDENSATION",
            "NOT A VAPOUR TRAIL",
            "NOT A CONDENSATION TRAIL",
        ):
            self.assertIn(phrase, SOURCE_PROSE, msg=f"missing label: {phrase}")

    def test_claims_a_bound_not_an_exact_value(self) -> None:
        self.assertIn("UPPER BOUND", SOURCE_PROSE)
        self.assertIn("CEILING", SOURCE_PROSE)

    def test_visual_mapping_is_marked_not_physics(self) -> None:
        self.assertIn("VISUAL MAPPING", SOURCE_PROSE)
        self.assertIn("LEGIBILITY", SOURCE_PROSE)

    def test_docs_keep_the_same_labels(self) -> None:
        physics = prose(PHYSICS).lower()
        self.assertIn("upper bound", physics)
        self.assertIn("does not model condensation", physics)
        self.assertIn("visual mapping", physics)

    def test_annex_row_keeps_the_same_labels(self) -> None:
        row = re.search(r"`aee_fx_supersonicTrace`[^\n]*", prose(ANNEX_C))
        self.assertIsNotNone(row)
        text = row.group(0).lower()
        self.assertIn("upper bound", text)
        self.assertIn("not a vapour trail", text)


class BoundedConcurrency(unittest.TestCase):
    """Several rounds can be airborne, so the renderer caps the count."""

    def test_cap_is_declared_and_enforced(self) -> None:
        self.assertRegex(SOURCE, r"_MAX_TRACES\s*=\s*[0-9]+")
        self.assertRegex(SOURCE, r"count _traces\s*>=\s*_MAX_TRACES")
        self.assertIn("exitWith", SOURCE)

    def test_a_running_trace_is_never_evicted(self) -> None:
        # Only the cap check may refuse a new shot.  Nothing may remove a
        # live record early, or a round in flight would lose its trace.
        self.assertNotIn("deleteVehicle (_x getOrDefault", SOURCE)


class Diagnostics(unittest.TestCase):
    """A silent exit is the likeliest failure, so every refusal must log."""

    def test_debug_logging_is_gated_not_always_on(self) -> None:
        # AEE_LOG_DEBUG is gated on aee_fx_logDebug, so per-tick output
        # costs nothing until the operator ticks the box.
        self.assertIn("AEE_LOG_DEBUG", SOURCE)
        self.assertNotIn("diag_log text", SOURCE)

    def test_hard_refusals_warn(self) -> None:
        # A missing particleShape or a null projectile is a wiring fault,
        # not a normal condition, so it warns rather than stays quiet.
        self.assertIn("AEE_LOG_WARN", SOURCE)
        self.assertIn("AEE_SUPERSONICTRACE CARRIES NO PARTICLESHAPE", SOURCE_PROSE)

    def test_cap_refusal_names_the_cap(self) -> None:
        # Skipping a shot at the cap must be visible, or the operator sees
        # no trace and cannot tell why.
        self.assertIn("REFUSED", SOURCE_PROSE)
        self.assertIn("AT THE CAP OF", SOURCE_PROSE)

    def test_open_and_close_are_both_named(self) -> None:
        self.assertIn("SUPERSONIC TRACE OPEN", SOURCE_PROSE)
        self.assertIn("CLOSED AFTER", SOURCE_PROSE)

    def test_close_names_all_three_reasons(self) -> None:
        # Which branch ended a trace is the first thing anyone asks when a
        # trace vanishes in the middle of a flight.
        for reason in (
            "ROUND LEFT THE SUPERSONIC REGIME",
            "ROUND DESTROYED",
            "SPRITE LIFETIME EXPIRED",
        ):
            self.assertIn(reason, SOURCE_PROSE, msg=f"missing reap reason: {reason}")

    def test_per_tick_log_is_throttled(self) -> None:
        # An unthrottled line at 20 Hz would flood the client log.  The
        # gate is a threshold compare, not a modulo: HEMTT's SQF parser
        # fails to structure a "%" expression in this position.
        self.assertRegex(SOURCE, r"_LOG_EVERY\s*=\s*[0-9]+")
        self.assertRegex(SOURCE, r"_ticks\s*>=\s*_nextLog")
        self.assertRegex(SOURCE, r"_nextLog\s*=\s*_ticks\s*\+\s*_LOG_EVERY")
        self.assertNotRegex(SOURCE, r"_ticks\s*%")

    def test_debug_setting_exists_to_gate_it(self) -> None:
        # The setting must actually be declared, or the log never turns on.
        settings = (REPO / "addons/fx/initSettings.inc.sqf").read_text(encoding="utf-8")
        self.assertIn("QGVAR(logDebug)", settings)

    def test_diagnostics_name_the_cone_and_keep_the_labels(self) -> None:
        # The renderer now carries real geometry, so it may name the Mach
        # cone, and it must state the sign error it corrects.  It must not
        # smuggle a condensation claim back in.  "vapour" is deliberately
        # NOT banned, because the header must carry the negation "not a
        # vapour trail"; HonestyLabels requires it.
        self.assertIn("MACH CONE", SOURCE_PROSE)
        self.assertIn("SIGN ERROR", SOURCE_PROSE)
        self.assertNotIn("CONDENSATION CONE", SOURCE_PROSE)


class TestPostInitRegistrationIdempotence(unittest.TestCase):
    """A repeat postInit must not stack CBA event handlers.

    One client RPT logged "fx module initialised" three times around a
    single mission start, with every PBO loaded exactly once.  CBA's
    addEventHandler stacks rather than replacing, so each repeat re-ran the
    per-shot and per-impact work, and the trace was drawn once per
    registration.  The guard must sit before the first registration.

    The guard used to be a hand-written block pasted into each init file.
    It is now AEE_MODULE_POST_INIT, one macro in the shared header, so the
    flag and the log line live in the macro BODY and the init files carry a
    single call.  There is a SEPARATE macro for preInit with its own flag:
    sharing one flag between the two events made postInit see the flag preInit
    had set and skip every handler it owned.  The three tests below check the
    macro body for the flag and the log, and the call site for the ordering.
    """

    _POST_INITS = (
        REPO / "addons" / "fx" / "XEH_postInit.sqf",
        REPO / "addons" / "optics" / "XEH_postInit.sqf",
    )
    _MACROS = REPO / "addons" / "main" / "script_macros.hpp"

    @staticmethod
    def _code_only(text):
        """Blank out line comments so a search cannot match the prose.

        The guard comment names CBA_fnc_addEventHandler, so a raw search finds
        the explanation before the registration it is meant to be compared
        against.
        """
        out = []
        for line in text.split("\n"):
            idx = line.find("//")
            out.append(line if idx < 0 else line[:idx])
        return "\n".join(out)

    def test_guard_precedes_every_registration(self):
        for path in self._POST_INITS:
            text = self._code_only(path.read_text(encoding="utf-8"))
            guard = text.find("AEE_MODULE_POST_INIT")
            self.assertNotEqual(guard, -1, f"{path.name}: no postInit guard")
            firsts = [
                text.find(token)
                for token in (
                    "CBA_fnc_add",
                    "installPlayerEngineHandler",
                    "installObjectEngineHandler",
                )
            ]
            firsts = [f for f in firsts if f >= 0]
            self.assertTrue(firsts, f"{path.name}: registers nothing")
            first = min(firsts)
            self.assertLess(
                guard, first, f"{path.name}: the guard is after the handlers"
            )

    def test_guard_sets_and_reads_the_same_flag(self):
        # The flag is derived from the CALLING component through QGVAR, so a
        # literal aee_<component>_moduleInitDone would make every addon share
        # one flag and the guard would silence the others.  That is the whole
        # reason this is a macro and not a helper function.
        text = self._code_only(self._MACROS.read_text(encoding="utf-8"))
        body = text.split("#define AEE_MODULE_POST_INIT")[1]
        self.assertIn("getVariable [QGVAR(postInit), false]", body)
        self.assertIn("setVariable [QGVAR(postInit), true]", body)
        self.assertNotIn("aee_", body, "a literal name would not be component scoped")
        # It must NOT reuse the preInit flag, or the second event skips.
        self.assertNotIn("QGVAR(preInit)", body)

    def test_repeat_init_is_logged_not_silent(self):
        # A silent skip would hide the fact that init is running more than
        # once, which is a real fault the RPT must keep showing.
        text = self._code_only(self._MACROS.read_text(encoding="utf-8"))
        body = text.split("#define AEE_MODULE_POST_INIT")[1]
        self.assertIn("skipping repeat postInit", body)
        self.assertIn("AEE_LOG_INFO", body)


# The Fired handler's round selection is asserted in
# tools/tests/test_supersonic_trace.py::FiredHandlerScans, which owns that
# contract.  It is not duplicated here, because two tests for one contract is
# how they come to disagree.


if __name__ == "__main__":
    unittest.main()
