#!/usr/bin/env python3
"""Contract: no two AEE post-process effects request the same priority.

The engine can return a POSITIVE handle that another effect already holds when
two AEE creators ask for the same effect type at the same priority.  The BIKI
note that ppEffectCreate "fails" (returns -1) on a collision is WRONG: a live
operator RPT shows optics/FilmGrain and nightvision/FilmGrain both handed
handle 32 at priority 2000.  Two owners of one engine effect means the first
teardown destroys the second owner's effect.

The trigger is a shared (effect type, priority).  The core registry
(fnc_createPPEffect) closes it for its own callers: it compares every candidate
handle against the handles it already owns and bumps the priority.  A creator
that calls ppEffectCreate directly bypasses that guard, so the priorities
across ALL AEE creators must be disjoint as well.

This test enumerates every AEE (effect type, priority) literal, or a file-local
variable resolved to a literal, and fails when two different addons request the
same pair.  It reads the source: a mirror would prove nothing about the
creators.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"

# The engine effect types an AEE creator may request through ppEffectCreate.
# LightShafts is excluded: ppEffectCreate cannot create it (it returns -1), so
# fnc_applySolarGlareFX drives it with the string-LHS form instead.
EFFECTS = (
    "ChromAberration",
    "DynamicBlur",
    "ColorCorrections",
    "FilmGrain",
    "RadialBlur",
    "ColorInversion",
    "WetDistortion",
    "Resolution",
    "DepthOfField",
)

PAIR_RE = re.compile(r'"(' + "|".join(EFFECTS) + r')"\s*,\s*(\d+|_[A-Za-z0-9_]+)')
ASSIGN_RE = re.compile(r"(_[A-Za-z0-9_]+)\s*=\s*(\d+)\s*;")


def strip_comments(text: str) -> str:
    """Blank ``//`` and ``/* */`` comments, preserving offsets and strings."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def scan():
    """Return {(effect, priority): {addon, ...}} over every addon source."""
    pairs: dict[tuple[str, int], set[str]] = {}
    for path in sorted(ADDONS.rglob("*.sqf")):
        code = strip_comments(path.read_text(encoding="utf-8"))
        addon = path.relative_to(ADDONS).parts[0]
        literals = {m.group(1): int(m.group(2)) for m in ASSIGN_RE.finditer(code)}
        for m in PAIR_RE.finditer(code):
            token = m.group(2)
            priority = int(token) if token.isdigit() else literals.get(token)
            if priority is None:
                continue
            pairs.setdefault((m.group(1), priority), set()).add(addon)
    return pairs


class TestPPHandleUnique(unittest.TestCase):
    def test_no_two_addons_share_an_effect_priority(self):
        collisions = {
            pair: sorted(owners) for pair, owners in scan().items() if len(owners) > 1
        }
        self.assertEqual(
            collisions,
            {},
            "two AEE addons request one effect type at one priority, so the "
            "engine can hand them one shared handle: "
            + repr({f"{e}@{p}": o for (e, p), o in collisions.items()}),
        )

    def test_the_registry_bumps_a_shared_handle(self):
        # The registry is the choke point for its own callers: it compares the
        # candidate handle against the handles it owns and bumps.  If this
        # guard is removed, registry callers can share a handle again even with
        # disjoint priorities.
        registry = (ADDONS / "core" / "functions" / "fnc_createPPEffect.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("ppEffectCreate", registry)
        self.assertIn("_collidedWith", registry)
        self.assertIn("_usedPriority = _usedPriority + 1", registry)


if __name__ == "__main__":
    unittest.main()
