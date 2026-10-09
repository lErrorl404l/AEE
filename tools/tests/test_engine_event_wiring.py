"""Locks the MEASURED CBA engine-event findings and the rewiring they forced.

Every value in MEASURED was read out of a headless dedicated-server RPT
(tests/docker/run.log, probe PHASE64 loaded by execVM). None of it is
inferred from reading CBA source, because source reading got this wrong
once already: I had recorded that CBA's "FiredBIS" guard was dead code
after toLower and therefore unreachable. The run rejected it.

The three numbers that decided it:
  CLASS-INIT fired 5 times (2 retroactive + 3 created after registration),
    so CBA_fnc_addClassEventHandler DOES receive real engine events.
  BUS-INIT fired 0 times on those same real engine Init events, and fired
    exactly 1 time when CBA_fnc_localEvent was called by hand, so the CBA
    bus is sound but NOTHING emits engine event names onto it.
  RAW-HD-INSTALLED fired 8 times, so a per-object raw HandleDamage handler
    installed from a class Init handler does attach.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Return values of CBA_fnc_addClassEventHandler, measured on CBA v3.19.0.
MEASURED = {
    "FiredBIS": False,     # rejected outright
    "Fired": True,         # accepted, but legacy order: slots 5 and 6 swapped
    "Explosion": True,
    "HitPart": True,       # accepted, but see below on why it still cannot fire
    "HandleDamage": False, # absent from XEH_EVENTS
    "Init": True,
}

# Engine event names. Handing any of these to CBA's bus registers a handler
# that never fires.
ENGINE_EVENTS = ("fired", "CBA_fired", "explosion", "hitPart", "HandleDamage")

# Legitimate CBA events AEE still uses on the bus. These must NOT be rewired:
# compat_kat listens for one emitted by ACE medical, optics for a CBA player
# event, and either would break on a raw engine route.
ALLOWED_BUS_EVENTS = {"ace_medical_handleUnitVitals", "visionmode", "unit"}

BUS_FUNCS = ("CBA_fnc_addEventHandler", "CBA_fnc_addPlayerEventHandler")

# Every rewired site, and the route it must use.
# material inlines its own attach, because a shared core edge would break
# the leaf invariant that keeps the dependency graph acyclic.
INLINED_LEAF = {"addons/material/XEH_preInit.sqf"}

PLAYER_SCOPED = (
    "addons/ballistics/XEH_postInit.sqf",
    "addons/fx/XEH_postInit.sqf",
    "addons/optics/XEH_postInit.sqf",
    "addons/material/XEH_preInit.sqf",
)
OBJECT_SCOPED = (
    "addons/core/XEH_postInit.sqf",
    "addons/armour/XEH_postInit.sqf",
)


def _raw(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _code(path: pathlib.Path) -> str:
    """Source with comments and string bodies blanked.

    Braces inside comments and string literals both break a structural scan,
    and AEE's own comments name the very tokens these tests search for, so a
    raw-text scan matches prose first.
    """
    text = re.sub(r"/\*.*?\*/", "", _raw(path), flags=re.S)
    out = []
    for line in text.splitlines():
        line = re.sub(r"//.*$", "", line)
        line = re.sub(r'"[^"\n]*"', '""', line)
        out.append(line)
    return "\n".join(out)


def _bus_registrations():
    """Every [name, {...}] array that is handed to a CBA bus function."""
    for path in sorted(ROOT.glob("addons/*/XEH_*.sqf")):
        text = _raw(path)
        for fn in BUS_FUNCS:
            for match in re.finditer(re.escape(fn), text):
                window = text[max(0, match.start() - 220):match.start()]
                names = re.findall(r'\[\s*"([^"]+)"\s*,\s*\{', window)
                if names:
                    yield path.relative_to(ROOT).as_posix(), fn, names[-1]


class TestNoEngineEventOnTheDeadBus(unittest.TestCase):
    """The point of the rewiring: nothing lands on CBA's bus that matters.

    Such a registration returns an id and looks successful, and it never
    fires. That was true of 8 sites before the rewiring.
    """

    def test_no_engine_event_registered_on_the_cba_bus(self):
        offenders = [
            f"{path} via {fn}"
            for path, fn, name in _bus_registrations()
            if name in ENGINE_EVENTS
        ]
        self.assertEqual(
            offenders, [],
            "engine events on CBA's bus never fire: " + "; ".join(offenders),
        )

    def test_what_remains_on_the_bus_is_a_real_cba_event(self):
        for path, fn, name in _bus_registrations():
            self.assertIn(
                name, ALLOWED_BUS_EVENTS,
                f"{path} registers {name} on CBA's bus via {fn}, which is dead",
            )


class TestEngineHandlersUseAWorkingRoute(unittest.TestCase):
    def test_player_scoped_engines_use_the_raw_bis_installer(self):
        for rel in PLAYER_SCOPED:
            text = _raw(ROOT / rel)
            self.assertIn('"Fired"', text, rel)
            if rel in INLINED_LEAF:
                # material is a deliberate leaf: a shared core edge would let a
                # dependency cycle return, so it inlines its own attach.
                self.assertIn('addEventHandler ["Fired"', text, rel)
                continue
            self.assertIn("installPlayerEngineHandler", _code(ROOT / rel), rel)

    def test_object_scoped_damage_uses_the_per_object_installer(self):
        for rel in OBJECT_SCOPED:
            self.assertIn("installObjectEngineHandler", _code(ROOT / rel), rel)
            self.assertIn('"HandleDamage"', _raw(ROOT / rel), rel)

    def test_hit_part_is_attached_to_the_projectile_inside_fired(self):
        """HitPart cannot be a class event handler: it fires on the projectile.

        So the attach has to live where the projectile is in scope, which is
        the shooter's own Fired handler.
        """
        text = _raw(ROOT / "addons/optics/XEH_postInit.sqf")
        self.assertIn('_projectile addEventHandler ["HitPart"', text)
        self.assertIn("handleImpactHeat", text)
        self.assertNotIn('["hitPart", {', text,
                         "a class hitPart registration can never fire")

    def test_installers_are_idempotent_by_key_not_by_event(self):
        """Four addons each own a Fired handler on the same unit.

        Keying the stored handler on the event name would let one caller's
        install remove another's, so the key is the caller's own name.
        """
        for rel in ("addons/lib/functions/fnc_installPlayerEngineHandler.sqf",
                    "addons/lib/functions/fnc_installObjectEngineHandler.sqf"):
            self.assertIn('"_key"', _raw(ROOT / rel), rel)
            self.assertIn("attachObjectEngineHandler", _code(ROOT / rel), rel)
        # Replacement lives in the shared attach, because the engine stacks
        # duplicate handlers and a stack means the work runs twice per event.
        attach = _code(ROOT / "addons/lib/functions/fnc_attachObjectEngineHandler.sqf")
        self.assertIn("removeEventHandler", attach)
        self.assertIn("getVariable [_idVar, -1] >= 0", attach)

    def test_respawn_uses_the_cba_unit_event(self):
        """Re-attachment must ride a CBA event, not a per-frame poll."""
        rel = "addons/lib/functions/fnc_installPlayerEngineHandler.sqf"
        self.assertIn("CBA_fnc_addPlayerEventHandler", _code(ROOT / rel))
        self.assertIn('"unit"', _raw(ROOT / rel))

    def test_every_rewired_site_declares_a_distinct_key(self):
        """Two sites sharing a key would silently remove each other."""
        keys = []
        for rel in PLAYER_SCOPED + OBJECT_SCOPED:
            for match in re.finditer(r"QGVAR\((\w+)\)\]\s*call\s*EFUNC\(core,install", _raw(ROOT / rel)):
                keys.append(match.group(1))
        self.assertEqual(len(keys), len(set(keys)),
                         f"duplicate installer key would let one handler remove "
                         f"another: {keys}")


class TestProbeKeepsMeasuring(unittest.TestCase):
    PROBE = "tests/docker/missions/aee_test.Stratis/aee_p64_probe.sqf"

    def test_probe_still_measures_the_table(self):
        probe = ROOT / self.PROBE
        self.assertTrue(probe.exists(), "the measuring probe was deleted")
        text = _raw(probe)
        for name in MEASURED:
            self.assertIn('"%s"' % name, text, f"probe no longer measures {name}")

    def test_probe_is_loaded_with_execvm_never_exec(self):
        """exec runs SQS, so the preprocessor leaves "//" in and it is code.

        Cost one run on its own: 40 comment lines tokenised as code, and every
        statement after the first one truncated, which reads as missing phases
        rather than a syntax fault.
        """
        code = _code(ROOT / "tests/docker/missions/aee_test.Stratis/init.sqf")
        self.assertNotRegex(code, r'\[?\s*\]\s*exec\s+"',
                            "exec runs SQS; a mission probe must use execVM")
        self.assertIn('execVM "aee_p64_probe.sqf"',
                      _raw(ROOT / "tests/docker/missions/aee_test.Stratis/init.sqf"))

    def test_fired_params_stay_in_bis_order(self):
        """The arg order is right because of the ROUTE, not the event name.

        CBA's class EH only accepts legacy "Fired", and cba_xeh rebinds it as
        _this = [0,1,2,3,4,6,5], swapping the magazine and the projectile. AEE
        reads _projectile at slot 6, so a class-EH adoption would have handed
        every handler a magazine. The raw BIS route has no swap.
        """
        bis = 'params ["_unit", "_weapon", "", "", "_ammo", "_magazine", "_projectile"]'
        self.assertIn(bis, _raw(ROOT / "addons/ballistics/XEH_postInit.sqf"))
        # fx's trace renderer names only the slot it reads, so assert the
        # event name and that slot rather than the full seven-name list.
        fx = _raw(ROOT / "addons/fx/XEH_postInit.sqf")
        self.assertIn('["Fired", {', fx)
        self.assertIn('params ["_unit", "", "", "", "", "", "_projectile"]', fx)


class TestMeasuredAcceptanceTable(unittest.TestCase):
    def test_table_matches_the_run(self):
        self.assertFalse(MEASURED["FiredBIS"], "FiredBIS is rejected by CBA")
        self.assertFalse(MEASURED["HandleDamage"], "HandleDamage is not in XEH_EVENTS")
        for name in ("Fired", "Explosion", "Init"):
            self.assertTrue(MEASURED[name], f"{name} is accepted by the class EH")


if __name__ == "__main__":
    unittest.main()
