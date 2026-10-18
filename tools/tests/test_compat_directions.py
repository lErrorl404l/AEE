#!/usr/bin/env python3
"""Contract test: every compat_ace3 function declares its direction (ADR-027).

AEE owns by declaration and load order, not by force.  A compat function that
carries no declared direction is a silent policy gap: it is not clear whether
AEE is the declared authority (the host stands down) or the host owns the
subsystem (AEE adapts).  This test fails when a compat_ace3 function has no
declared direction, and when the rendered integrations.qmd block drifts.

It also holds the host dependency contract of the two ACE3 and ACM compat
addons (issues #240, #241): a host symbol the addon calls or writes must have
its owning PBO declared in requiredAddons.  Otherwise `skipWhenMissingDependencies`
lets the addon load without that PBO and the integration no-ops, with no RPT
line to say so.

Run: python3 -m unittest tools.tests.test_compat_directions
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import gen_compat_directions as gcd  # noqa: E402

# ─── host dependency contract (issues #240, #241) ────────────────────────────
COMPAT = ROOT / "addons"
COMPAT_ADDONS = ("compat_ace3", "compat_acm")

# SQF comments.  A symbol named only in prose is not a call.
SQF_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
# A host-namespace token.  ACE3 lower-cases its symbols (ace_medical_status_*),
# ACM does not (ACM_CBRN_*), so the pattern is case-insensitive on the host
# name.  `aee_*` is AEE's own namespace (EGVAR expands to it) and is resolved
# by aee_component, not by this pattern.
HOST_TOKEN = re.compile(r"\b(?:ACE|ACM|ace|acm)_[A-Za-z0-9_]+")
# Both host mods name the owning PBO in the function prefix, so the owner of
# ace_medical_status_fnc_setCardiacArrestState is ace_medical_status and the
# owner of ACM_CBRN_fnc_updateExposureEffects is ACM_CBRN.  Verified against
# the shipped PBOs: ACE 3.21.2 puts both status functions in
# ace_medical_status.pbo, addDamageToUnit in ace_medical.pbo and
# addSpO2DutyFactor in ace_medical_vitals.pbo; ACM 1.4.8.0 puts the CBRN
# functions, ACM_CBRN_Hazards and the ACM_CBRN_* variables in ACM_cbrn.pbo.
NAMESPACED_FUNCTION = re.compile(r"^(?P<pbo>.+)_fnc_[A-Za-z0-9_]+$")
AEE_SYMBOL = re.compile(r"^aee_(?P<component>[A-Za-z0-9_]+)")
REQUIRED_BLOCK = re.compile(r"requiredAddons\[\]\s*=\s*\{(.*?)\}", re.DOTALL)

# Scanned host tokens the ownership rule does not attribute to a PBO, with the
# reason it does not.  This is fail-closed: a token the rule cannot attribute
# and that is not listed here fails the guard, so a new host surface cannot
# slip in unclassified, and an entry that is no longer scanned fails too.
# It is not a place to silence a real, undeclared dependency.
UNATTRIBUTED = {
    "compat_acm": {
        # ace_common defines it (`ACE_player = (_this select 0);`).  It is a
        # global VALUE, not a namespaced symbol of a PBO this addon may name,
        # so the rule must not invent an owner for it.
        "ACE_player": "global variable defined by ace_common",
    },
}


def required_addons(addon):
    """The addon names written in the addon's CfgPatches requiredAddons."""
    text = (COMPAT / addon / "config.cpp").read_text(encoding="utf-8", errors="replace")
    match = REQUIRED_BLOCK.search(text)
    if not match:
        raise AssertionError(f"{addon}/config.cpp declares no requiredAddons block")
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def host_symbols(addon):
    """The host symbols the addon calls or writes.

    compat_ace3 declares its host surface in directions.json (ADR-027), and the
    ADR-027 gate forces every function to declare one, so the declared list IS
    the contract.  compat_acm carries no directions.json, so its inventory is
    the host-namespace tokens in its own source.  config.cpp is deliberately
    not scanned: it holds the requiredAddons answer this guard checks, so
    reading it as input would be circular.
    """
    manifest = COMPAT / addon / "directions.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return {
            symbol
            for entry in data["functions"].values()
            for symbol in entry.get("host_api", [])
        }
    found = set()
    for path in sorted((COMPAT / addon).rglob("*")):
        if path.suffix in (".sqf", ".hpp"):
            text = SQF_COMMENT.sub(
                "", path.read_text(encoding="utf-8", errors="replace")
            )
            found.update(HOST_TOKEN.findall(text))
    return found


def declared_universe():
    """Every PBO name any compat addon declares.

    The rule needs candidate names for a plain variable symbol, and this is the
    only record of host PBO names in the tree.  It cannot hide a missing entry:
    a name removed from the universe leaves its variable symbols without a
    candidate, and an unattributed symbol fails the guard.
    """
    universe = set()
    for addon in COMPAT_ADDONS:
        universe.update(required_addons(addon))
    return universe


def known_host_pbos(symbols, universe):
    """The PBO names the rule may attribute a variable symbol to."""
    names = {
        match.group("pbo")
        for symbol in symbols
        if (match := NAMESPACED_FUNCTION.match(symbol))
    }
    return names | universe


def owner_of(symbol, candidates):
    """The PBO that owns a host symbol, or None when the rule cannot say.

    A `<pbo>_fnc_<name>` symbol names its own owner.  A plain variable is owned
    by the longest candidate PBO name that prefixes it, which is how
    ACM_CBRN_Chemical_Sarin_Buildup resolves through the ACM_CBRN_fnc_* family
    in the same inventory.  The comparison is case-insensitive: the symbols are
    ACM_CBRN_* and the CfgPatches name is ACM_cbrn.
    """
    match = NAMESPACED_FUNCTION.match(symbol)
    if match:
        return match.group("pbo")
    folded = symbol.casefold()
    # Prefer a candidate the symbol spells exactly; the ACM_cbrn entry in
    # requiredAddons and the ACM_CBRN_* symbol prefix would otherwise tie.
    exact = [
        name
        for name in sorted(candidates)
        if symbol == name or symbol.startswith(name + "_")
    ]
    if exact:
        return max(exact, key=len)
    prefixed = [
        name
        for name in sorted(candidates)
        if folded == name.casefold() or folded.startswith(name.casefold() + "_")
    ]
    return max(prefixed, key=len) if prefixed else None


def aee_component(symbol):
    """The AEE addon an `aee_*` symbol belongs to, or None.

    EGVAR(component,name) expands to `aee_<component>_<name>`, so the component
    is the longest leading segment run that names an addon on disk.  Such a
    symbol is AEE's own: a registry variable such as
    aee_physiology_massResolvers is written by the compat addon into a registry
    the physiology addon owns, and the AEE-side edge is the business of
    test_addon_dependencies.py.  This guard must not invent a host
    requiredAddons entry for it.
    """
    match = AEE_SYMBOL.match(symbol)
    if not match:
        return None
    segments = match.group("component").split("_")
    for end in range(len(segments), 0, -1):
        component = "_".join(segments[:end])
        if (COMPAT / component).is_dir():
            return component
    return None


def dependency_errors(addon, symbols, declared, candidates, unattributed=frozenset()):
    """Undocumented host dependencies: a symbol whose owner is not declared.

    The owner comparison is case-insensitive: a CfgPatches name and the symbol
    prefix differ only in case for ACM (ACM_cbrn vs ACM_CBRN).
    """
    errors = []
    declared_folded = {name.casefold() for name in declared}
    for symbol in sorted(symbols):
        if aee_component(symbol):
            continue
        owner = owner_of(symbol, candidates)
        if owner is None:
            if symbol in unattributed:
                continue
            errors.append(
                f"{addon}: cannot attribute {symbol} to an owning PBO; "
                "classify it in UNATTRIBUTED with a reason"
            )
            continue
        if owner.casefold() not in declared_folded:
            errors.append(
                f"{addon}: {symbol} is owned by {owner}, which is not in requiredAddons"
            )
    return errors


class TestRequiredAddonsCoverTheHostSurface(unittest.TestCase):
    """Every host symbol a compat addon uses has its PBO in requiredAddons.

    Issue #240: compat_ace3 called ace_medical_status_fnc_* with only
    ace_medical declared, and ACE's ace_medical does not pull
    ace_medical_status.  Issue #241: compat_acm called ACM_CBRN_fnc_* and wrote
    ACM_CBRN_* with only ACM_main declared, and ACM_main does not pull
    ACM_cbrn.
    """

    def test_every_host_symbol_has_its_pbo_declared(self):
        for addon in COMPAT_ADDONS:
            with self.subTest(addon=addon):
                symbols = host_symbols(addon)
                self.assertTrue(symbols, f"{addon}: the host inventory is empty")
                errors = dependency_errors(
                    addon,
                    symbols,
                    required_addons(addon),
                    known_host_pbos(symbols, declared_universe()),
                    UNATTRIBUTED.get(addon, frozenset()),
                )
                self.assertEqual(errors, [], "\n".join(errors))

    def test_aee_registry_variables_get_no_host_requirement(self):
        # The declared host_api of compat_ace3 contains two AEE registry
        # variables.  Their owner is an AEE addon, and the guard must resolve
        # them as such rather than demand a format entry for a host PBO.
        self.assertEqual(aee_component("aee_physiology_massResolvers"), "physiology")
        self.assertEqual(
            aee_component("aee_physiology_categoryResolvers"), "physiology"
        )
        declared = required_addons("compat_ace3")
        self.assertEqual(
            dependency_errors(
                "compat_ace3",
                {"aee_physiology_massResolvers"},
                declared,
                known_host_pbos(set(), declared_universe()),
            ),
            [],
            "an AEE registry variable must not become a host dependency",
        )

    def test_the_ace_vitals_symbols_resolve_to_ace_medical_status(self):
        symbols = host_symbols("compat_ace3")
        candidates = known_host_pbos(symbols, declared_universe())
        for symbol in (
            "ace_medical_status_fnc_addMedicationAdjustment",
            "ace_medical_status_fnc_setCardiacArrestState",
        ):
            self.assertEqual(owner_of(symbol, candidates), "ace_medical_status")
        self.assertIn("ace_medical_status", required_addons("compat_ace3"))

    def test_the_acm_cbrn_symbols_resolve_to_the_cbrn_pbo(self):
        # A variable symbol is owned by the PBO of the ACM_CBRN_fnc_* family.
        # The comparison against requiredAddons is case-insensitive: the
        # symbols are ACM_CBRN_* and the CfgPatches name is ACM_cbrn.
        symbols = host_symbols("compat_acm")
        candidates = known_host_pbos(symbols, declared_universe())
        for symbol in (
            "ACM_CBRN_fnc_updateExposureEffects",
            "ACM_CBRN_Chemical_Sarin_Buildup",
        ):
            self.assertEqual(owner_of(symbol, candidates), "ACM_CBRN")
        self.assertIn("ACM_cbrn", required_addons("compat_acm"))

    def test_the_scan_sees_code_and_not_comments(self):
        # compat_acm is the scanned addon.  A symbol named only in a comment is
        # prose, so ace_medical_vitals_spo2DutyList must not be in the
        # inventory; the called function must be.
        symbols = host_symbols("compat_acm")
        self.assertIn("ace_medical_vitals_fnc_addSpO2DutyFactor", symbols)
        self.assertNotIn("ace_medical_vitals_spo2DutyList", symbols)

    def test_the_unattributed_allowlist_is_exact(self):
        # Fail-closed in both directions: an unclassified symbol fails the test
        # above, and an entry that is no longer scanned is reported here.
        for addon, allowed in UNATTRIBUTED.items():
            symbols = host_symbols(addon)
            candidates = known_host_pbos(symbols, declared_universe())
            found = {
                symbol
                for symbol in symbols
                if not aee_component(symbol) and owner_of(symbol, candidates) is None
            }
            self.assertEqual(found, set(allowed), f"{addon}: UNATTRIBUTED is stale")
            for symbol, reason in allowed.items():
                self.assertTrue(reason, f"{addon}: {symbol} has no reason")

    def test_an_undeclared_owner_is_reported(self):
        # Negative control: the guard cannot pass vacuously.
        errors = dependency_errors(
            "compat_x",
            {"ace_medical_status_fnc_setCardiacArrestState"},
            {"ace_medical"},
            {"ace_medical_status"},
        )
        self.assertTrue(any("ace_medical_status" in error for error in errors), errors)

    def test_a_declared_owner_is_accepted_case_insensitively(self):
        self.assertEqual(
            dependency_errors(
                "compat_x",
                {"ACM_CBRN_fnc_updateExposureEffects"},
                {"ACM_CBRN"},
                {"ACM_CBRN"},
            ),
            [],
        )

    def test_an_unattributable_symbol_is_reported(self):
        errors = dependency_errors("compat_x", {"ace_unowned_thing"}, set(), set())
        self.assertTrue(any("ace_unowned_thing" in error for error in errors), errors)


class TestCompatDirections(unittest.TestCase):
    def test_every_compat_function_has_a_declared_direction(self):
        manifest = gcd.load_manifest()
        declared = manifest["functions"]
        missing = sorted(gcd.functions_on_disk() - set(declared))
        self.assertEqual(
            missing,
            [],
            f"compat_ace3 function(s) with no declared direction: {missing}",
        )

    def test_no_orphan_direction_entries(self):
        manifest = gcd.load_manifest()
        on_disk = gcd.functions_on_disk()
        orphans = sorted(set(manifest["functions"]) - on_disk)
        self.assertEqual(
            orphans, [], f"direction entries for missing functions: {orphans}"
        )

    def test_directions_are_from_the_allowed_set(self):
        manifest = gcd.load_manifest()
        for fn, entry in manifest["functions"].items():
            self.assertIn(entry["direction"], gcd.ALLOWED, f"{fn} direction")

    def test_integration_functions_declare_a_two_way_direction(self):
        # An integration function must be an ownership claim or an adaptation.
        # `diagnostics` is the only non-integration direction.
        manifest = gcd.load_manifest()
        for fn, entry in manifest["functions"].items():
            if entry["direction"] == "diagnostics":
                self.assertGreaterEqual(len(entry.get("host_api", [])), 0)
            else:
                self.assertIn(entry["direction"], gcd.INTEGRATION, fn)

    def test_audit_reports_a_function_with_no_direction(self):
        # Negative control: a function on disk that the manifest omits is
        # reported, so the audit cannot pass vacuously.
        manifest = {"functions": {"fnc_known": {"direction": "adaptation"}}}
        errors = gcd.audit({"fnc_known", "fnc_undeclared"}, manifest)
        self.assertTrue(any("fnc_undeclared" in e for e in errors), errors)

    def test_audit_reports_an_orphan_entry(self):
        manifest = {"functions": {"fnc_gone": {"direction": "adaptation"}}}
        errors = gcd.audit({"fnc_live"}, manifest)
        self.assertTrue(any("fnc_gone" in e for e in errors), errors)

    def test_audit_accepts_a_complete_manifest(self):
        manifest = {"functions": {"fnc_a": {"direction": "ownership-claim"}}}
        self.assertEqual(gcd.audit({"fnc_a"}, manifest), [])

    def test_generated_block_is_current(self):
        manifest = gcd.load_manifest()
        self.assertEqual(
            gcd.audit(gcd.functions_on_disk(), manifest),
            [],
            "manifest drift: run tools/gen_compat_directions.py",
        )
        doc = gcd.DOC.read_text(encoding="utf-8")
        present = gcd.current_block(doc)
        self.assertIsNotNone(present, "integrations.qmd is missing the direction block")
        self.assertEqual(
            present,
            gcd.build_block(manifest),
            "integrations.qmd direction block is stale: run "
            "python3 tools/gen_compat_directions.py",
        )


if __name__ == "__main__":
    unittest.main()
