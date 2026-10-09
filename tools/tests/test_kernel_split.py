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

import re
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
        # Assert the REAL dispatcher conditions, not a Python mirror of them:
        # native only when the output is a non-empty string with errorCode 0,
        # and the SQF reference kernel is the fallback.
        self.assertIn('{_output != ""}', self.dispatch)
        self.assertIn("{_code == 0}", self.dispatch)
        self.assertIn(
            'if (_nativeOutput != "") exitWith { _nativeOutput };', self.dispatch
        )
        self.assertIn("call (missionNamespace getVariable [_sqfRef", self.dispatch)


LIB_RS = ROOT / "tools" / "dev-harness" / "extension" / "src" / "lib.rs"

# A dispatch call site: ["kernel id", <args>] call EFUNC(core,dispatchKernel).
# The args are a literal array or a variable that holds one.
DISPATCH_RE = re.compile(
    r'\["([A-Za-z0-9_]+)",\s*(\[[^\]]*\]|_[A-Za-z0-9_]+)\]\s*'
    r"call\s+EFUNC\(core,\s*dispatchKernel\)",
    re.S,
)
COMMAND_RE = re.compile(
    r'\.command\(\s*"([^"]+)"\s*,\s*([A-Za-z0-9_]+)\s*,?\s*\)', re.S
)
FN_RE = re.compile(r"fn\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)\s*->", re.S)
TABLE_RE = re.compile(r'\["([A-Za-z0-9_]+)",\s*\["([^"]+)",\s*"([^"]+)"\]\]')


def count_top_level(inner: str) -> int:
    """Count non-empty comma-separated elements at bracket depth 0.

    A trailing comma (Rust parameter lists end with one) does not add an
    element.
    """
    depth = 0
    segments: list[str] = []
    current: list[str] = []
    i = 0
    n = len(inner)
    while i < n:
        ch = inner[i]
        if ch == '"':
            current.append(ch)
            i += 1
            while i < n:
                current.append(inner[i])
                if inner[i] == "\\":
                    if i + 1 < n:
                        current.append(inner[i + 1])
                    i += 2
                    continue
                if inner[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            segments.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    segments.append("".join(current))
    return sum(1 for segment in segments if segment.strip())


def variable_array(text: str, var: str, before: int) -> str | None:
    """Return the literal array body last assigned to `var` before `before`."""
    best: str | None = None
    for match in re.finditer(rf"\bprivate\s+{re.escape(var)}\s*=\s*\[", text):
        if match.start() > before:
            continue
        start = match.end() - 1
        depth = 0
        i = start
        while i < len(text):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        best = text[start + 1 : i]
    return best


class TestDispatchCallSiteArity(unittest.TestCase):
    """Every dispatch call site passes exactly its native kernel's arity.

    arma-rs rejects a call whose argument count does not match the Rust
    handler signature, so a mismatch silently selects the SQF fallback and the
    native path never runs (the eyeTimeSkip defect).  This scan pins each
    call site to the native signature, so the two cannot drift apart again.
    """

    @classmethod
    def setUpClass(cls):
        lib = LIB_RS.read_text(encoding="utf-8")
        cls.native_arity = {
            fn: count_top_level(params) for fn, params in FN_RE.findall(lib)
        }
        cls.command_to_fn = dict(COMMAND_RE.findall(lib))
        cls.kernel_to_command = {
            kernel: command
            for kernel, _sqf, command in TABLE_RE.findall(
                gen.strip_comments(KERNEL_TABLE.read_text(encoding="utf-8"))
            )
        }

    def _call_sites(self):
        for path in sorted((ROOT / "addons").rglob("*.sqf")):
            text = gen.strip_comments(path.read_text(encoding="utf-8"))
            rel = path.relative_to(ROOT).as_posix()
            for match in DISPATCH_RE.finditer(text):
                kernel, args = match.group(1), match.group(2)
                if args.startswith("["):
                    arity = count_top_level(args[1:-1])
                else:
                    body = variable_array(text, args, match.start())
                    self.assertIsNotNone(
                        body, f"{rel}: cannot resolve {args} at the call site"
                    )
                    arity = count_top_level(body)
                yield rel, kernel, arity

    def test_every_call_site_matches_its_native_signature(self):
        checked = 0
        for rel, kernel, arity in self._call_sites():
            command = self.kernel_to_command.get(kernel)
            self.assertIsNotNone(
                command, f"{rel}: kernel {kernel} is not in the kernel table"
            )
            fn = self.command_to_fn.get(command)
            self.assertIsNotNone(
                fn, f"{rel}: native command {command} is not registered in lib.rs"
            )
            expected = self.native_arity.get(fn)
            self.assertIsNotNone(expected, f"{rel}: no Rust signature for {fn}")
            self.assertEqual(
                arity,
                expected,
                f"{rel}: {kernel} passes {arity} args, {command} takes {expected}",
            )
            checked += 1
        self.assertGreater(checked, 0, "no dispatch call sites were found")

    def test_the_scan_covers_the_fixed_defect_and_more(self):
        # Guard the scan itself against passing vacuously.
        kernels = {kernel for _rel, kernel, _arity in self._call_sites()}
        self.assertIn("eyeTimeSkip", kernels)
        self.assertGreater(len(kernels), 1)


if __name__ == "__main__":
    sys.exit(unittest.main())
