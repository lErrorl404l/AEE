#!/usr/bin/env python3
"""Regression tests for the class audit of 2026-09-27.

Every assertion here corresponds to a defect that was live in the repository
and that ALL of the 23 CI gates passed.  That is the reason this file exists:
the gates could not see these classes, so the classes need a named test.

The five shapes, and the real bug each one came from:

1. A restore branch that does not exit.  The four thermal EXIT branches and
   the rain-stop branch all ran a restore and then fell through into the code
   that re-applies it, so the restore was undone on the same call.
2. A restore placed below an early exit that skips it.  The second-sun EXIT
   branch sat below the `!alive` guard, so the lightpoint survived a death.
3. A client-visible write with no restore anywhere.  The fusion overlay
   swapped emissive materials onto every thermal selection within 300 m, the
   selection set includes Man, and nothing put them back.
4. A world-wide query in a 10 Hz path.  `allUnits` and `vehicles` were swept
   with no radius, and each element ran a per-selection solve.
5. An init event that registers the same handler more than once.  CBA appends
   rather than replacing, so a repeat triples the per-event work.

Comments are stripped before every search.  Three separate checks in this
session matched the prose that explains a token instead of the code, so a
search that can see comments is a check that can be satisfied by a sentence.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _code(path):
    """Return the file with line AND block comments blanked.

    A block comment naming a command sorts before the real code, so a search
    for that command finds the prose. That is how this file's own first
    version of the registry test passed a broken implementation.
    """
    import re as _re

    text = _re.sub(r"/\*.*?\*/", " ", path.read_text(encoding="utf-8"), flags=_re.S)
    out = []
    for line in text.split("\n"):
        cut = line.find("//")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


class TestRestoreBranchExits(unittest.TestCase):
    """Shape 1. A branch that restores must leave, whatever keys it."""

    _FILES = (
        REPO / "addons/thermal/functions/display/fnc_applyRainDroplets.sqf",
        REPO / "addons/thermal/functions/display/fnc_applySecondSun.sqf",
        REPO / "addons/thermal/functions/display/fnc_applyClothingThermal.sqf",
        REPO / "addons/thermal/functions/display/fnc_applyBuildingThermal.sqf",
    )

    def test_no_restore_branch_ends_in_a_discarded_value(self):
        """`then { restore; 0 };` is a fall-through, not an early return.

        The signature is the DISCARDED TAIL, not merely a branch containing a
        restore verb.  An inner `if` nested inside a correct exitWith block
        also contains a restore verb, and flagging that was a false positive
        in the first version of this test.  The audit proved the live shape
        was keyed on a WEATHER value as well as a mode value, so the test
        must not look only for mode strings.
        """
        restore = re.compile(
            r"deleteVehicle|ppEffectDestroy|setObjectTexture|setObjectMaterial|detach"
        )
        bare = re.compile(r"^(0|1|-1|true|false)$")
        for path in self._FILES:
            code = _code(path)
            lines = code.split("\n")
            for i, line in enumerate(lines):
                if not line.strip().startswith("if ") or "then {" not in line:
                    continue
                level, j, opened = 0, i, False
                while j < len(lines):
                    level += lines[j].count("{") - lines[j].count("}")
                    if "{" in lines[j]:
                        opened = True
                    if opened and level == 0:
                        break
                    j += 1
                body = lines[i + 1 : j]
                tail = [
                    b.strip()
                    for b in body
                    if b.strip() and b.strip() not in ("};", "}")
                ]
                if not tail or not bare.match(tail[-1]):
                    continue
                if (
                    "exitWith" in "\n".join(body)
                    or restore.search("\n".join(body)) is None
                ):
                    continue
                if re.search(r"\}\s*else", code[i : j + 1]):
                    continue
                self.fail(
                    f"{path.name}:{i + 1}: restore branch falls through, tail {tail[-1]!r}"
                )


class TestRestorePrecedesGuards(unittest.TestCase):
    """Shape 2. The teardown path must not be reachable past a guard."""

    def test_second_sun_exit_precedes_the_alive_guard(self):
        """A death still returns the dead unit, so a guard skips the destroy.

        The sensor teardown calls this function with EXIT when the player
        dies.  If the EXIT branch sits below `!alive _player`, the lightpoint
        is never deleted.
        """
        path = REPO / "addons/thermal/functions/display/fnc_applySecondSun.sqf"
        code = _code(path)
        exit_at = code.index('if (_mode == "EXIT")')
        alive_at = code.index("!alive _player")
        self.assertLess(
            exit_at, alive_at, "the EXIT branch sits below the guard that skips it"
        )


class TestModeStringNotBoundToObjectParameter(unittest.TestCase):
    """Shape 3. A mode string must never be bound to an object-typed argument."""

    def test_no_string_literal_is_bound_to_an_object_typed_first_parameter(self):
        """The class the fusion fault belongs to.

        Every teardown helper in thermal takes a bare mode string, except
        applyFusionOverlay, which takes the player first. A single-element
        ["EXIT"] call therefore binds a string where the parameter is declared
        [objNull], which the engine rejects at run time with an empty
        expression and no useful position. This walks the call sites instead of
        trusting one of them.
        """
        sig = {}
        for f in sorted((REPO / "addons").rglob("fnc_*.sqf")):
            body = _code(f).split("params [", 1)
            if len(body) < 2:
                continue
            head = body[1].split("];", 1)[0]
            first = re.search(r'\[[ \t]*"(\w+)"[ \t]*,.*?,[ \t]*\[([^\]]*)\]', head)
            if first and "objNull" in first.group(2) and "string" not in first.group(2):
                sig[f.stem[4:]] = (f, first.group(1))
        self.assertTrue(
            sig, "no object-typed first parameters found, the parse is wrong"
        )

        offenders = []
        for f in sorted((REPO / "addons").rglob("*.sqf")):
            for n, line in enumerate(_code(f).splitlines(), 1):
                m = re.match(
                    r'\[[ \t]*"[A-Z_]+"[ \t]*\][ \t]*call[ \t]*(?:EFUNC\(\s*\w+\s*,\s*(\w+)\s*\)|FUNC\(\s*(\w+)\s*\))',
                    line.strip(),
                )
                if not m:
                    continue
                target = m.group(1) or m.group(2)
                if target in sig:
                    offenders.append(
                        f"{f.relative_to(REPO)}:{n} binds a mode string to {target}, "
                        f"whose first parameter {sig[target][1]} is object typed"
                    )
        self.assertEqual(offenders, [], "\n".join(offenders))


class TestHighFrequencySweepsAreBounded(unittest.TestCase):
    """Shape 4. A 10 Hz path must not sweep the world with no radius."""

    def test_clothing_thermal_bounds_the_unit_sweep(self):
        code = _code(
            REPO / "addons/thermal/functions/display/fnc_applyClothingThermal.sqf"
        )
        # Anchor on the radius variable, not a fixed-width window: the unit
        # loop head sits far above the `forEach (allUnits)` closer, because
        # the per-selection loop is nested inside it.
        self.assertIn("_viewDist", code, "the unit sweep has no radius")
        self.assertIn("distance", code, "the unit sweep has no radius test")
        self.assertLess(
            code.index("_viewDist"),
            code.index("forEach (allUnits)"),
            "the radius is computed after the loop it bounds",
        )

    def test_building_thermal_bounds_the_vehicle_sweep(self):
        code = _code(
            REPO / "addons/thermal/functions/display/fnc_applyBuildingThermal.sqf"
        )
        at = code.index("(vehicles - [player])")
        self.assertIn(
            "distance", code[at : at + 220], "the vehicle sweep has no radius"
        )

    def test_the_substrate_trace_log_is_gated(self):
        """The raw log wrote to the RPT from a 10 Hz path, ungated."""
        code = _code(
            REPO / "addons/thermal/functions/display/fnc_applySelectionThermal.sqf"
        )
        at = code.index('diag_log format [\n                "[AEE][TRACE]')
        window = code[max(0, at - 400) : at]
        self.assertIn("thermalDebug", window, "the substrate trace log is ungated")


class TestInitIsIdempotent(unittest.TestCase):
    """Shape 5. A repeat init must not append the same handler again."""

    # actions binds keys, which CBA keys by mod and action, so a repeat
    # overwrites rather than stacking.  The four compat addons need host mods
    # this client does not run, and the audit ranked them LOW.  Both are
    # deliberate exemptions, recorded here so the next reader sees the reason.
    def test_every_init_file_with_a_registration_is_guarded_first(self):
        """The guard for the file's OWN event must precede its first registration.

        CBA has no re-entrancy guard for postInit (fnc_postInit.sqf:19 checks
        a marker it never sets) and CBA_fnc_addEventHandler STACKS, so a
        repeat init multiplies the per-event work.  The guard is a macro in the
        shared header so a new addon cannot get the scope wrong, and this test
        makes omitting it -- or naming the WRONG event -- a build failure.

        The wrong-event case is not hypothetical.  optics carried the single
        shared macro in BOTH init files, so preInit set the flag and postInit
        then found it set and exited, dropping the 0.1 s sensor PFH, both
        player event handlers and the hitPart handler.  The headless run logged
        it as a routine "skipping repeat init", which is exactly why the flag
        now carries the event name: a shared name cannot be told apart from a
        genuine re-entry.
        """
        offenders = []
        for path in sorted(
            list((REPO / "addons").rglob("XEH_postInit.sqf"))
            + list((REPO / "addons").rglob("XEH_preInit.sqf"))
        ):
            code = _code(path)
            lines = code.split("\n")
            regs = [
                i
                for i, line in enumerate(lines)
                if "CBA_fnc_add" in line or "call FUNC(ppEffectCreate)" in line
            ]
            if not regs:
                continue
            want = (
                "AEE_MODULE_POST_INIT"
                if path.name == "XEH_postInit.sqf"
                else "AEE_MODULE_PRE_INIT"
            )
            guard = next((i for i, line in enumerate(lines) if want in line), None)
            name = f"{path.parent.name}/{path.name}"
            if guard is None:
                offenders.append(f"{name} has no {want} for its own XEH event")
            elif guard > regs[0]:
                offenders.append(
                    f"{name} guards after registration at line {regs[0] + 1}"
                )
        self.assertEqual(offenders, [], "; ".join(offenders))

    def test_the_guard_macros_use_one_distinct_flag_per_xeh_event(self):
        """preInit and postInit need DIFFERENT flags, or the second one skips.

        One flag per event, not one flag per addon.  With a shared flag the
        later event believes the addon is already initialised, and every
        handler it owns is never registered.  Two flags make that structurally
        impossible, and the flag name carrying the event is what let the log
        prove it rather than hide it.
        """
        macros = _code(REPO / "addons/main/script_macros.hpp")

        def body(name, end_token):
            i = macros.index(f"#define {name}")
            j = macros.index(end_token) + len(end_token)
            return macros[i:j]

        pre = body(
            "AEE_MODULE_PRE_INIT",
            "missionNamespace setVariable [QGVAR(preInit), true];",
        )
        post = body(
            "AEE_MODULE_POST_INIT",
            "missionNamespace setVariable [QGVAR(postInit), true];",
        )
        self.assertIn("getVariable [QGVAR(preInit), false]", pre)
        self.assertIn("getVariable [QGVAR(postInit), false]", post)
        self.assertIn("skipping repeat preInit", pre)
        self.assertIn("skipping repeat postInit", post)
        # Neither body may mention the other event's flag.
        self.assertNotIn("QGVAR(postInit)", pre)
        self.assertNotIn("QGVAR(preInit)", post)
        # A literal aee_<component>_... would make every addon share one flag.
        self.assertNotIn("aee_", pre)
        self.assertNotIn("aee_", post)


class TestPPEffectRegistry(unittest.TestCase):
    """Shape: a registered handle is a handle that can be destroyed.

    CBA 3.19.0 has no resource registry, no RAII and no teardown manager, so
    the four optics base effects had no destroy path on any code path.
    """

    _CREATE = REPO / "addons/core/functions/fnc_createPPEffect.sqf"
    _DESTROY = REPO / "addons/core/functions/fnc_destroyPPEffect.sqf"
    _RELEASE = REPO / "addons/optics/functions/vision/fnc_destroyBasePostProcess.sqf"
    _PREP = REPO / "addons/core/XEH_PREP.hpp"
    _OPTICS_PREP = REPO / "addons/optics/XEH_PREP.hpp"
    _OPTS = REPO / "addons/optics/functions/vision/fnc_ppEffectCreate.sqf"
    _PRE = REPO / "addons/optics/XEH_preInit.sqf"

    def test_both_halves_of_the_registry_exist_and_are_prepped(self):
        for f in (self._CREATE, self._DESTROY, self._RELEASE):
            self.assertTrue(f.exists(), f"{f.name} missing")
        prep = self._PREP.read_text(encoding="utf-8")
        self.assertIn("PREP(createPPEffect);", prep)
        self.assertIn("PREP(destroyPPEffect);", prep)
        self.assertIn(
            "PREPS(vision,destroyBasePostProcess);",
            self._OPTICS_PREP.read_text(encoding="utf-8"),
        )

    def test_creation_is_idempotent_through_the_registry(self):
        """A second create for the same scope and key returns the live handle.

        This is the stacking fix. ppEffectCreate at an occupied priority bumps
        and returns a NEW handle, orphaning the old one, which is how one
        session produced handles 17,18,19,20 then 29,30,31,32.
        """
        code = _code(self._CREATE)
        self.assertIn("ppEffectCreate", code)
        # The invariant is ordering: the registry must be consulted for an
        # existing handle BEFORE any engine create happens, and must return it
        # without creating a second effect.
        lookup = code.index("getOrDefault")
        create = code.index("ppEffectCreate")
        self.assertLess(lookup, create, "creates before consulting the registry")
        guard = code[lookup:create]
        self.assertIn(
            "_existing",
            guard,
            "the pre-create check never tests the existing handle",
        )
        self.assertIn(
            "exitWith", guard, "an existing handle must short-circuit the create"
        )

    def test_the_base_effects_no_longer_bypass_the_registry(self):
        code = _code(self._OPTS)
        self.assertIn("EFUNC(core,createPPEffect)", code)
        self.assertNotIn(
            "= ppEffectCreate", code, "the base effects bypass the registry"
        )

    def test_the_registry_has_a_caller_on_mission_end(self):
        """A teardown with no caller is dead code, so it must be wired."""
        code = _code(self._PRE)
        self.assertIn('addMissionEventHandler ["Ended"', code)
        self.assertIn("destroyBasePostProcess", code)

    def test_whole_scope_release_is_supported(self):
        """Releasing by scope is what stops one name typo leaking the rest."""
        code = _code(self._DESTROY)
        self.assertIn('if (_key == "") then', code)
        self.assertIn("ppEffectDestroy", code)


class TestPPEffectCrossScopeOwnership(unittest.TestCase):
    """Two scopes must never be handed the same engine handle.

    A live log recorded the night grain and the optics base set both creating
    a FilmGrain at priority 2000 and both being handed handle 32:

      ppEffect created optics/FilmGrain      handle=32 priority=2000
      ppEffect created nightvision/FilmGrain handle=32 priority=2000

    Idempotence is keyed on scope and key, so neither request matched the
    other's entry, and ppEffectCreate returned a POSITIVE handle for the
    occupied priority, so a negative-only check never fired.  Two owners of
    one effect means the first teardown destroys the other module's effect,
    which is the damage the registry exists to prevent.
    """

    _CREATE = REPO / "addons/core/functions/fnc_createPPEffect.sqf"
    _OPTS = REPO / "addons/optics/functions/vision/fnc_ppEffectCreate.sqf"
    _MGMT = REPO / "addons/optics/functions/vision/fnc_managePostProcess.sqf"

    def test_a_candidate_is_compared_against_every_owned_handle(self):
        code = _code(self._CREATE)
        self.assertIn("keys _registry", code)
        self.assertIn("forEach _ownedIds", code)
        self.assertIn("_heldHandle == _candidate", code)

    def test_a_positive_but_owned_candidate_triggers_a_retry(self):
        """The discriminator against the old code: a positive return value
        does not mean the handle is ours."""
        code = _code(self._CREATE)
        self.assertIn("if (_candidate >= 0) then", code)
        self.assertIn('if (_collidedWith == "") then { _handle = _candidate; }', code)
        self.assertIn("_usedPriority = _usedPriority + 1", code)

    def test_a_collision_is_reported_rather_than_swallowed(self):
        code = _code(self._CREATE)
        self.assertIn("already owned by", code)
        self.assertIn("AEE_LOG_WARN", code)

    def test_the_created_line_reports_the_priority_actually_used(self):
        code = _code(self._CREATE)
        self.assertIn("priority=%5", code)
        self.assertIn("_handle, _usedPriority", code)

    def test_the_optics_base_no_longer_creates_a_film_grain(self):
        """Nobody read or destroyed it, so it is deleted rather than given a
        different priority.  Night vision owns the eye noise."""
        code = _code(self._OPTS)
        self.assertNotIn("FilmGrain", code)

    def test_the_deleted_handle_name_is_absent_from_the_addon(self):
        for path in (self._OPTS, self._MGMT):
            with self.subTest(path=path.name):
                self.assertNotIn("ppHandle_FilmGrain", _code(path))

    def test_the_false_lost_handle_warning_is_gone(self):
        """It keyed on the legacy mirror, so it fired while the registry
        still held the live handle and the very next line reported the
        effect already owned at that same handle."""
        code = _code(self._MGMT)
        self.assertNotIn("handle lost", code)
        self.assertNotIn("mirror=-1", code)

    def test_the_registry_decides_and_the_mirror_follows(self):
        code = _code(self._MGMT)
        self.assertIn("QEGVAR(core,ppHandle_%1_%2)", code)
        self.assertIn("missionNamespace setVariable [_legacy, _owner]", code)
        self.assertIn("has no registry handle", code)

    def test_the_undetectable_engine_kill_is_still_declared(self):
        """There is no engine query for a live handle, so an effect the
        engine killed cannot be seen here.  The gap must stay written down
        rather than being covered by a proxy that misreports."""
        text = self._MGMT.read_text(encoding="utf-8")
        self.assertIn("no engine query", text)
        self.assertIn("EPE manager release", text)

    def test_the_header_records_the_measured_collision(self):
        text = self._CREATE.read_text(encoding="utf-8")
        self.assertIn("A HANDLE IS NEVER SHARED ACROSS SCOPES", text)
        self.assertIn("handle=32", text)


class TestSettingMacroStringtableContract(unittest.TestCase):
    """Shape 6. A settings macro must produce the stringtable keys that exist.

    The AEE_SETTING_* macros take the bare setting name and build the title
    pair with LLSTRING(DOUBLES(h,Name)).  DOUBLES is var1##_##var2, so passing
    _Name pastes a DOUBLE underscore and silently points every setting at a key
    that does not exist.  HEMTT caught that (332 missing keys) but HEMTT is not
    one of the python gates, so nothing failed until the SQF was checked.  This
    test is the python-side guard for the same contract.
    """

    _MACROS = REPO / "addons/main/script_macros.hpp"
    _SETTINGS = sorted((REPO / "addons").glob("*/initSettings.inc.sqf"))

    def test_the_title_macro_does_not_double_the_separator(self):
        text = self._MACROS.read_text(encoding="utf-8")
        line = next(
            l for l in text.split("\n") if l.startswith("#define AEE_SETTING_TITLE")
        )
        self.assertNotIn(
            "DOUBLES(h,_",
            line,
            "DOUBLES already inserts the separator; _Name pastes a second one",
        )
        self.assertIn("DOUBLES(h,Name)", line)
        self.assertIn("DOUBLES(h,Description)", line)

    def test_every_macro_declared_setting_has_both_stringtable_keys(self):
        missing = []
        for inc in self._SETTINGS:
            addon = inc.parent.name
            table = REPO / "addons" / addon / "stringtable.xml"
            self.assertTrue(table.exists(), f"{addon}: no stringtable.xml")
            declared = {
                m.lower()
                for m in re.findall(r'ID="([^"]+)"', table.read_text(encoding="utf-8"))
            }
            code = _code(inc)
            for m in re.finditer(
                r"\bAEE_SETTING_(?:CHECKBOX|SLIDER)(?:_LOCAL)?\((\w+)\s*,", code
            ):
                name = m.group(1)
                for suffix in ("_Name", "_Description"):
                    key = f"STR_aee_{addon}_{name}{suffix}".lower()
                    if key not in declared:
                        missing.append(f"{addon}/{name}: {key}")
        self.assertEqual(missing, [], "; ".join(missing))

    def test_the_validator_can_see_settings_declared_through_a_macro(self):
        """The cross-module validator infers ownership from the settings file.

        It used to match only a literal QGVAR(name), so the macro form became
        invisible, ownership fell through to whichever module CROSS-WROTE the
        name, and the owning module's own read was reported as a scope bug.
        That is a false positive in the validator, not a defect in the setting.
        """
        validator = (REPO / "tools/validation/validate_cross_module.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("AEE_SETTING_", validator, "validator cannot see the macro form")


class TestPPEffectLifecycle(unittest.TestCase):
    """Shape 7. A handle read below a guard cannot be cleaned up on that path.

    fnc_managePostProcess returned at three early exits (optics disabled, the
    player nil or dead, the camera not on the player) while the handles and
    the cleanup sat below all three, so a live effect survived each of them.
    The isolated NVG DoF handle was destroyed by optics rather than by the
    addon that owns it, and the night grain read a handle that no code wrote.
    """

    _MANAGE = REPO / "addons/optics/functions/vision/fnc_managePostProcess.sqf"
    _OPTICS_POST = REPO / "addons/optics/XEH_postInit.sqf"
    _NIGHT_GRAIN = REPO / "addons/nightvision/functions/fnc_applyNightGrain.sqf"
    _TEARDOWN = REPO / "addons/nightvision/functions/fnc_teardownNvgDoF.sqf"
    _ALLOWLIST = REPO / "tools/validation/cba_settings_allowlist.txt"

    def test_cleanup_reaches_every_early_exit(self):
        """The handles must be read before the first guard.  A read below a
        guard leaves that path's cleanup with nothing to disable."""
        code = _code(self._MANAGE)
        first_exit = code.index("exitWith")
        for handle in ("_hChroma =", "_hBlur   =", "_hCC     ="):
            self.assertLess(
                code.index(handle),
                first_exit,
                f"{handle.strip(' =')} is read after the first exit",
            )

    def test_each_early_exit_runs_the_cleanup(self):
        code = _code(self._MANAGE)
        self.assertEqual(
            code.count("call _cleanup"),
            3,
            "an early exit does not run the cleanup",
        )

    def test_recreation_goes_through_the_registry(self):
        """A recreated handle must stay owned, so a whole-scope release
        reaches it and the WARN can name the scope and key that lost it."""
        code = _code(self._MANAGE)
        self.assertIn("EFUNC(core,createPPEffect)", code)
        self.assertNotIn(
            "= ppEffectCreate", code, "the recreation bypasses the registry"
        )
        self.assertIn("optics|%1", code, "the lost-handle WARN does not name the scope")

    def test_optics_does_not_destroy_another_modules_handle(self):
        code = _code(self._OPTICS_POST)
        self.assertIn("EFUNC(nightvision,teardownNvgDoF)", code)
        self.assertNotIn(
            "ppEffectDestroy", code, "optics destroys a nightvision handle directly"
        )
        self.assertTrue(
            self._TEARDOWN.exists(), "the owning teardown function is missing"
        )
        self.assertIn("ppEffectDestroy", _code(self._TEARDOWN))

    def test_night_grain_handle_is_created_and_destroyed(self):
        code = _code(self._NIGHT_GRAIN)
        self.assertIn(
            "EFUNC(core,createPPEffect)",
            code,
            "the night grain handle is never created",
        )
        self.assertIn(
            "EFUNC(core,destroyPPEffect)",
            code,
            "the night grain handle is never destroyed",
        )
        self.assertIn("ppHandle_FilmGrain", code)

    def test_night_grain_allowlist_reason_is_true(self):
        """The old reason claimed a create loop wrote the variable; no code
        did.  The reason must name the producer that now exists."""
        text = self._ALLOWLIST.read_text(encoding="utf-8")
        line = next(
            entry
            for entry in text.splitlines()
            if entry.startswith("aee_nightvision_ppHandle_FilmGrain")
        )
        self.assertNotIn(
            "create loop",
            line,
            "the reason still claims a create loop that does not exist",
        )
        self.assertIn("fnc_createPPEffect", line)


if __name__ == "__main__":
    unittest.main()
