"""Addon dependency guards (issue #203).

Two addons used to depend on each other: `environmental` called
`thermal.calculateStefanCoefficient` for its freeze/thaw and ice-load
models, while `thermal.updateTemperature` called four `environmental`
climate and terrain functions. Neither addon could then be built, loaded or
reasoned about independently, and a load-order change could break one of
them.

The coefficient is a soil property: it reads a surface class and a snow
depth and returns a value derived from the soil's conductivity, water
content and latent heat. It now lives in `material`, the leaf addon both
the others already depend on, so the cycle is gone.

These checks read the SOURCE. A mirror of the dependency graph would prove
nothing about the graph.

The target tree is 45 addons, recorded in `docs/architecture/addon-map.json`
and ADR-032. An addon that is present but not yet a target is listed in
PENDING_RETIREMENT while the migration retires it.

The tree is INTENTIONALLY cyclic today: EFUNC/EGVAR closes cycles through
`core` and the split addons. The tree-wide guard is therefore a RATCHET, not
an acyclicity proof. `KNOWN_COUPLINGS` pins the pre-migration strongly
connected components; a NEW coupling fails the guard, and the migration steps
may only shrink the set. Each present addon is normalized to its pre-migration
addon via the map, so a rename during a split does not read as a new coupling;
a coupling wholly inside one pre-migration addon is therefore not seen here.
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
ADDON_MAP = REPO / "docs" / "architecture" / "addon-map.json"

# Addons present on disk that the migration retires: `main` becomes `lib` at
# step 1, `environmental` splits into weather/lighting/persistence at step 5,
# and `fx` splits into particles/weatherfx/blast at step 9.
PENDING_RETIREMENT = frozenset({"main", "environmental", "fx"})

# The pre-migration monolith: one strongly connected component of twelve
# addons. The lib-kernel extraction and the splits must SHRINK this set. A
# coupling that is not within this component is a new cycle and fails the
# guard. Do not loosen this to pass a migration step.
KNOWN_COUPLINGS = frozenset({
    frozenset({
        "atmos",
        "ballistics",
        "core",
        "environmental",
        "fx",
        "maritime",
        "mobility",
        "nightvision",
        "optics",
        "physiology",
        "radio",
        "thermal",
    }),
})

# EFUNC(component,name) in a call, or EGVAR(component,name) in a variable
# name, is the cross-addon edge.
CALL = re.compile(r"EFUNC\(\s*([a-z_]+)\s*,")
VAR = re.compile(r"[QE]?EGVAR\(\s*([a-z_]+)\s*,")


def dependencies(addon):
    """Components this addon reaches into, excluding itself.

    Compat addons are excluded: they load only when their host mod is
    present, and an optional read of a compat variable is not a graph edge
    in the core addon set.
    """
    found = set()
    for path in (ADDONS / addon).rglob("*.sqf"):
        text = path.read_text(encoding="utf-8", errors="replace")
        found.update(CALL.findall(text))
        found.update(VAR.findall(text))
    found.discard(addon)
    found = {d for d in found if not d.startswith("compat_")}
    return found


def target_addons():
    """The 45 destination addon names from the canonical map."""
    return set(json.loads(ADDON_MAP.read_text(encoding="utf-8"))["target_addons"])


def present_addons():
    """Every addon directory on disk, sorted."""
    return sorted(d.name for d in ADDONS.iterdir() if d.is_dir())


def origins():
    """The pre-migration addon(s) each addon name descends from.

    A source addon maps to itself. A name a split creates maps to the addon it
    came from. The map is the source of truth, so a node survives a rename.
    """
    data = json.loads(ADDON_MAP.read_text(encoding="utf-8"))
    table = {}
    for source, record in data["addons"].items():
        table.setdefault(source, set()).add(source)
        for destination in record.get("destinations", []):
            table.setdefault(destination, set()).add(source)
    return table


def graph():
    """The cross-addon adjacency map, keyed by pre-migration addon.

    Reuses dependencies() and renames every node to its origin addon, so a
    split (which renames a node) cannot read as a new coupling. On a tree that
    has not moved, this is exactly the dependencies() graph.
    """
    table = origins()
    edges = {}
    for addon in present_addons():
        for source in table.get(addon, {addon}):
            bucket = edges.setdefault(source, set())
            for dep in dependencies(addon):
                for target in table.get(dep, {dep}):
                    if target != source:
                        bucket.add(target)
    return edges


def strongly_connected(adjacency):
    """The non-trivial strongly connected components of a dependency graph.

    A component of two or more nodes is a dependency cycle. Tarjan's
    algorithm. The result is a frozenset of frozensets, so a component is
    canonical: a pinned baseline is stable and one edge change reads as a
    membership change, not a new rotation of the same cycle.

    A node that appears only as a dependency is ignored unless it is a key: an
    edge to an addon that is not present on disk is not a coupling here.
    """
    index = {}
    low = {}
    on_stack = set()
    stack = []
    found = []
    counter = [0]

    def visit(node):
        index[node] = low[node] = counter[0]
        counter[0] += 1
        stack.append(node)
        on_stack.add(node)
        for other in sorted(adjacency.get(node) or ()):
            if other not in adjacency:
                continue
            if other not in index:
                visit(other)
                low[node] = min(low[node], low[other])
            elif other in on_stack:
                low[node] = min(low[node], index[other])
        if low[node] == index[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                found.append(frozenset(component))

    for node in sorted(adjacency):
        if node not in index:
            visit(node)
    return frozenset(found)


def new_couplings(adjacency):
    """Components that are not inside a KNOWN_COUPLINGS component."""
    return {
        component
        for component in strongly_connected(adjacency)
        if not any(component <= pinned for pinned in KNOWN_COUPLINGS)
    }


class TestNoCycle(unittest.TestCase):
    def test_environmental_does_not_depend_on_thermal(self):
        """The direction that closed the cycle must stay closed."""
        self.assertNotIn(
            "thermal",
            dependencies("environmental"),
            "environmental reaches into thermal again: the cycle is back",
        )

    def test_material_is_still_a_leaf(self):
        """The shared owner must depend on nothing but itself.

        The coefficient was moved here because both sides can depend on a
        leaf. If material ever gains a cross-addon edge, the cycle can
        return through the back door.
        """
        self.assertEqual(
            dependencies("material"),
            set(),
            "material is no longer a leaf; the cycle can return",
        )

    def test_the_coefficient_lives_in_material(self):
        self.assertTrue(
            (
                ADDONS / "material" / "functions" / "fnc_calculateStefanCoefficient.sqf"
            ).exists(),
            "the Stefan coefficient is not in material",
        )
        self.assertFalse(
            (
                ADDONS
                / "thermal"
                / "functions"
                / "ground"
                / "fnc_calculateStefanCoefficient.sqf"
            ).exists(),
            "the Stefan coefficient is still in thermal",
        )
        prep = (ADDONS / "material" / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(calculateStefanCoefficient)", prep)
        old_prep = (ADDONS / "thermal" / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertNotIn("calculateStefanCoefficient", old_prep)

    def test_callers_use_the_new_owner(self):
        """The call sites must name material, not thermal."""
        for name in ("fnc_calculateFreezeThawCycling.sqf", "fnc_calculateIceLoad.sqf"):
            text = (
                ADDONS / "environmental" / "functions" / "terrain" / name
            ).read_text(encoding="utf-8")
            self.assertIn("EFUNC(material,calculateStefanCoefficient)", text)
            self.assertNotIn("EFUNC(thermal,calculateStefanCoefficient)", text)


class TestAiWildlifeDirection(unittest.TestCase):
    """aee_wildlife consumes aee_ai, never the reverse."""

    def test_wildlife_consumes_ai_and_environmental(self):
        deps = dependencies("wildlife")
        self.assertIn("ai", deps)
        self.assertIn("environmental", deps)

    def test_ai_does_not_reach_into_wildlife(self):
        self.assertNotIn(
            "wildlife",
            dependencies("ai"),
            "aee_ai reaches into aee_wildlife: the dependency cycle is back",
        )


REQUIRED_BLOCK = re.compile(r"requiredAddons\[\]\s*=\s*\{(.*?)\}", re.DOTALL)


def required_addons(addon):
    """The addon names declared in the addon's CfgPatches requiredAddons."""
    text = (ADDONS / addon / "config.cpp").read_text(encoding="utf-8", errors="replace")
    match = REQUIRED_BLOCK.search(text)
    if not match:
        return set()
    return set(re.findall(r'"([^"]+)"', match.group(1)))


class TestRequiredAddonsComplete(unittest.TestCase):
    """Every cross-addon call is declared in CfgPatches requiredAddons.

    Scoped to the three addons the optics/combat QA named.  The repo-wide
    graph still has pre-existing gaps in other addons, so this pins the three
    that were fixed and guards them against a new undeclared call.
    """

    ADDONS_UNDER_TEST = ("optics", "ballistics", "wildlife")

    def test_every_dependency_is_declared(self):
        for addon in self.ADDONS_UNDER_TEST:
            declared = required_addons(addon)
            for dep in sorted(dependencies(addon)):
                self.assertIn(
                    f"aee_{dep}",
                    declared,
                    f"{addon} calls into {dep} but does not list "
                    f"aee_{dep} in requiredAddons",
                )


class TestTargetAddonSet(unittest.TestCase):
    """Every addon on disk has a home in the 45-addon target tree."""

    def test_present_addons_are_targets_or_retiring(self):
        unplanned = set(present_addons()) - target_addons() - PENDING_RETIREMENT
        self.assertEqual(
            unplanned,
            set(),
            f"addon(s) with no destination addon: {sorted(unplanned)}",
        )

    def test_the_target_set_holds_45_addons(self):
        self.assertEqual(len(target_addons()), 45)

    def test_a_pending_retirement_is_not_also_a_target(self):
        self.assertEqual(PENDING_RETIREMENT & target_addons(), frozenset())


class TestCycleDetector(unittest.TestCase):
    """The detector itself, on a synthetic graph."""

    def test_a_mutual_dependency_is_a_cycle(self):
        self.assertEqual(
            strongly_connected({"a": {"b"}, "b": {"a"}}),
            frozenset({frozenset({"a", "b"})}),
        )

    def test_a_dag_has_no_cycle(self):
        self.assertEqual(
            strongly_connected({"a": {"b"}, "b": {"c"}, "c": set()}),
            frozenset(),
        )


class TestNoNewCoupling(unittest.TestCase):
    """The migration may not add a dependency cycle (issue #203).

    A ratchet, not an acyclicity proof. The pre-migration monolith is pinned
    in KNOWN_COUPLINGS; a cycle between addons that were not already coupled
    fails the guard.
    """

    def test_no_new_coupling(self):
        introduced = new_couplings(graph())
        self.assertEqual(
            introduced,
            set(),
            "new dependency cycle(s): "
            + repr(sorted(sorted(component) for component in introduced)),
        )
