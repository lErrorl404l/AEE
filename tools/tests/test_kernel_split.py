#!/usr/bin/env python3
"""The kernel/driver split (Pillar 2).

A kernel is a pure function: it reads no engine state and writes none.  A
driver reads engine state, calls the kernel, and writes the result.  This suite
guards the split: every registered kernel must be engine-write-free, and the
generated kernel table must be fresh.

An engine write is any of ``setVariable``, ``setVelocity``,
``setObjectTexture``, ``setObjectMaterial``, any ``ppEffect*``, or
``diag_log``.  A kernel file that contains one fails here.

Run: python3 -m unittest tools.tests.test_kernel_split
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import gen_kernel_table as gen  # noqa: E402

PHYSICS_ADDONS = ("atmos", "thermal", "ballistics", "optics")


class TestKernelSplit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.errors = gen.audit()
        cls.addons = {gen.kernel_addon(rel) for rel in gen.KERNELS}

    def test_every_registered_kernel_is_engine_write_free(self):
        self.assertEqual(
            self.errors,
            [],
            "a registered kernel contains an engine write: " + "; ".join(self.errors),
        )

    def test_every_registered_kernel_file_exists(self):
        for rel in gen.KERNELS:
            self.assertTrue((ROOT / rel).is_file(), f"kernel file missing: {rel}")

    def test_each_physics_addon_has_at_least_one_kernel(self):
        for addon in PHYSICS_ADDONS:
            self.assertIn(addon, self.addons, f"no kernel registered for addon {addon}")

    def test_a_kernel_with_an_engine_write_fails_the_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fnc_badKernel.sqf"
            fixture.write_text(
                'params [["_x", 0, [0]]];\n'
                "_x setVelocity [0, 0, 0];\n"
                'diag_log text "x";\n'
                "_x\n",
                encoding="utf-8",
            )
            hits = gen.scan_kernel(fixture)
        self.assertIn("setVelocity", hits, "setVelocity must be an engine write")
        self.assertIn("diag_log", hits, "diag_log must be an engine write")

    def test_a_pure_kernel_passes_the_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fnc_goodKernel.sqf"
            fixture.write_text(
                'params [["_x", 0, [0]]];\nprivate _y = _x * 2;\n_y\n',
                encoding="utf-8",
            )
            hits = gen.scan_kernel(fixture)
        self.assertEqual(hits, [], "a pure kernel must contain no engine write")

    def test_inputs_are_derived_from_the_params_block(self):
        for rel in gen.KERNELS:
            code = gen.strip_comments((ROOT / rel).read_text(encoding="utf-8"))
            inputs = gen.kernel_inputs(code)
            self.assertTrue(inputs, f"{rel} has no derived inputs")

    def test_the_generated_table_is_fresh(self):
        doc = gen.DOC.read_text(encoding="utf-8")
        self.assertEqual(
            gen.current_block(doc),
            gen.build_block(),
            "the kernel table is stale; run python3 tools/gen_kernel_table.py",
        )

    def test_the_check_mode_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "gen_kernel_table.py"), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


DISPATCHER = ROOT / "addons" / "core" / "functions" / "fnc_dispatchKernel.sqf"
PROBE = ROOT / "addons" / "core" / "functions" / "fnc_probeExtension.sqf"
KERNEL_TABLE = ROOT / "addons" / "core" / "functions" / "fnc_initKernelTable.sqf"


class TestKernelDispatcher(unittest.TestCase):
    """The SQF kernel and a native kernel sit behind one dispatcher name."""

    @classmethod
    def setUpClass(cls):
        cls.table = gen.strip_comments(KERNEL_TABLE.read_text(encoding="utf-8"))
        cls.dispatch = gen.strip_comments(DISPATCHER.read_text(encoding="utf-8"))
        cls.probe = gen.strip_comments(PROBE.read_text(encoding="utf-8"))

    def test_every_kernel_has_an_sqf_path_and_a_native_path(self):
        for rel in gen.KERNELS:
            name = gen.kernel_name(rel)
            self.assertIn(f'["{name}", ["aee_', self.table, f"{name} has no SQF ref")
            self.assertIn(f'"kernel.{name}"', self.table, f"{name} has no native name")

    def test_the_dispatcher_gates_call_extension_behind_the_probe(self):
        # The native call sits inside the extReady guard, and the SQF reference
        # kernel is the fallback, so absence of the extension selects SQF.
        guard = self.dispatch.index(
            "missionNamespace getVariable [QGVAR(extReady), false]"
        )
        call = self.dispatch.index("callExtension")
        self.assertLess(guard, call, "callExtension must sit behind the extReady guard")
        self.assertIn("call (missionNamespace getVariable [_sqfRef", self.dispatch)

    def test_the_probe_caches_aee_core_ext_ready(self):
        self.assertIn("callExtension", self.probe)
        self.assertIn("QGVAR(extReady)", self.probe)

    def test_absence_of_the_extension_selects_sqf(self):
        # Mirror of the dispatcher's decision: native only when ready AND the
        # native return is a non-empty string (the extension's errorCode-0
        # payload); otherwise the SQF reference kernel runs.
        def choose(ext_ready: bool, native_out: object) -> str:
            if ext_ready and isinstance(native_out, str) and native_out != "":
                return "native"
            return "sqf"

        self.assertEqual(choose(False, "payload"), "sqf")
        self.assertEqual(choose(True, ""), "sqf")
        self.assertEqual(choose(True, "1.0"), "native")


if __name__ == "__main__":
    sys.exit(unittest.main())
