#!/usr/bin/env python3
"""Generate the AEE pure-kernel table (Pillar 2 - the kernel/driver split).

A kernel is a pure function: it reads no engine state and writes none.  A
driver reads engine state, calls the kernel, and writes the result.  The kernel
is the unit of test and the unit of native port; the driver is the only place
that touches the engine.

This generator scans the registered kernel files across the physics addons
(atmos, thermal, ballistics, optics eye), derives each kernel's inputs from its
`params` block and its outputs from its header, checks it for an engine write,
and renders the table into the marked block of
`docs/wiki/research/kernel-table.md`.

An engine write is any of: `setVariable`, `setVelocity`, `setObjectTexture`,
`setObjectMaterial`, any `ppEffect*`, or `diag_log`.

Run:
    python3 tools/gen_kernel_table.py           # update the doc block
    python3 tools/gen_kernel_table.py --check   # fail on drift or an engine write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOC = ROOT / "docs" / "wiki" / "research" / "kernel-table.md"
VECTORS = (
    ROOT / "tools" / "dev-harness" / "extension" / "tests" / "vectors" / "kernels.json"
)

BEGIN = "<!-- BEGIN GENERATED: kernel table -->"
END = "<!-- END GENERATED: kernel table -->"

# The registered pure kernels.  Each is a genuine kernel in a physics addon:
# a pure function with no engine read or write.  A function that mixes a pure
# computation with engine writes is a driver and is not registered here.
KERNELS: tuple[str, ...] = (
    "addons/atmos/functions/physics/fnc_calculateHailEnergy.sqf",
    "addons/atmos/functions/physics/fnc_calculateStationPressure.sqf",
    "addons/atmos/functions/physics/fnc_calculateRelativeHumidity.sqf",
    "addons/ballistics/functions/fnc_calculateAirDensityKernel.sqf",
    "addons/ballistics/functions/fnc_calculateBallisticDrag.sqf",
    "addons/optics/functions/eye/fnc_eyeAdaptStep.sqf",
    "addons/optics/functions/eye/fnc_eyeMesopicWeight.sqf",
    "addons/optics/functions/eye/fnc_eyePupilSteady.sqf",
    "addons/optics/functions/eye/fnc_eyePupilStep.sqf",
    "addons/optics/functions/eye/fnc_eyeTimeSkip.sqf",
    "addons/thermal/functions/display/fnc_thermalImperfectionParams.sqf",
    "addons/thermal/functions/display/fnc_thermalWetDistortionParams.sqf",
    "addons/thermal/functions/solver/fnc_solveTwoNodeKernel.sqf",
)

# Native-kernel metadata: the side the driver runs on (server or client), and
# the generated parity vector key from tools/gen_kernel_vectors.py ("-" when the
# kernel has no generated vector).  A pure kernel is server-callable whatever
# its driver side; this column states the driver, per ADR-034.
NATIVE: dict[str, tuple[str, str]] = {
    "calculateHailEnergy": ("server", "-"),
    "calculateStationPressure": ("server", "stationPressure"),
    "calculateRelativeHumidity": ("server", "relativeHumidity"),
    "calculateAirDensityKernel": ("server", "airDensity"),
    "calculateBallisticDrag": ("server", "-"),
    "eyeAdaptStep": ("server", "-"),
    "eyeMesopicWeight": ("server", "-"),
    "eyePupilSteady": ("server", "-"),
    "eyePupilStep": ("server", "-"),
    "eyeTimeSkip": ("server", "-"),
    "thermalImperfectionParams": ("client", "-"),
    "thermalWetDistortionParams": ("client", "-"),
    "solveTwoNodeKernel": ("server", "solveTwoNode"),
}

# An engine write.  A pure kernel contains none of these.
ENGINE_WRITE_TOKENS: tuple[str, ...] = (
    "setVariable",
    "setVelocity",
    "setObjectTexture",
    "setObjectMaterial",
    "ppEffect",
    "diag_log",
)

ADDON_RE = re.compile(r"^addons/([^/]+)/")
PARAM_RE = re.compile(r'"(?P<name>_[A-Za-z0-9_]+)"')
RETURN_RE = re.compile(r"^\s*\*?\s*(?:Return Value|Returns?)\s*:\s*(?P<out>.*)$", re.I)


def strip_comments(text: str) -> str:
    """Blank out line and block comments, preserving line count."""
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
        elif text[i] == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
        else:
            i += 1
    return "".join(out)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def kernel_name(rel: str) -> str:
    return Path(rel).stem.removeprefix("fnc_")


def kernel_addon(rel: str) -> str:
    match = ADDON_RE.match(rel)
    return match.group(1) if match else "?"


def params_block(code: str) -> str:
    """Return the text inside the first top-level `params [ ... ]`."""
    match = re.search(r"\bparams\s*\[", code)
    if not match:
        return ""
    start = code.index("[", match.start())
    depth = 0
    for i in range(start, len(code)):
        if code[i] == "[":
            depth += 1
        elif code[i] == "]":
            depth -= 1
            if depth == 0:
                return code[start + 1 : i]
    return code[start + 1 :]


def kernel_inputs(code: str) -> str:
    names = PARAM_RE.findall(params_block(code))
    return ", ".join(f"`{n}`" for n in names) if names else "(none)"


def kernel_outputs(raw: str) -> str:
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        match = RETURN_RE.match(line)
        if not match:
            continue
        text = match.group("out").strip().lstrip("*").strip()
        if not text:
            # The description sits on the next non-empty header line.
            for following in lines[i + 1 :]:
                candidate = following.strip().lstrip("*").strip()
                if candidate:
                    text = candidate
                    break
        return text.rstrip(".") or "expression"
    return "expression"


def scan_kernel(path: Path) -> list[str]:
    """Return the engine-write tokens found in the kernel's code."""
    code = strip_comments(_read(path))
    return [tok for tok in ENGINE_WRITE_TOKENS if tok in code]


def row(rel: str) -> dict[str, str]:
    path = ROOT / rel
    raw = _read(path) if path.is_file() else ""
    writes = scan_kernel(path) if path.is_file() else ["<missing file>"]
    return {
        "name": f"`{kernel_name(rel)}`",
        "addon": kernel_addon(rel),
        "inputs": kernel_inputs(strip_comments(raw)),
        "outputs": kernel_outputs(raw),
        "engine_write_free": "yes" if not writes else "NO: " + ", ".join(writes),
    }


def audit() -> list[str]:
    """Return a list of defects (empty when the tree is clean)."""
    errors: list[str] = []
    for rel in KERNELS:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"{rel}: kernel file is missing")
            continue
        writes = scan_kernel(path)
        if writes:
            errors.append(
                f"{rel}: kernel contains an engine write: {', '.join(writes)}"
            )
    return errors


def parity_cell(key: str) -> str:
    """Render the parity-vector column from the generated vectors file."""
    if key == "-":
        return "-"
    if not VECTORS.is_file():
        return f"{key} (missing)"
    data = json.loads(VECTORS.read_text(encoding="utf-8"))["kernels"]
    entry = data.get(key)
    if entry is None:
        return f"{key} (missing)"
    return f"{key} ({len(entry['vectors'])})"


def build_block() -> str:
    lines = [
        BEGIN,
        "",
        "| Kernel | Addon | Side | Inputs | Outputs | Parity vector | Engine-write-free |",
        "|---|---|---|---|---|---|---|",
    ]
    for rel in KERNELS:
        r = row(rel)
        name = kernel_name(rel)
        side, parity = NATIVE.get(name, ("?", "-"))
        lines.append(
            f"| {r['name']} | {r['addon']} | {side} | {r['inputs']} | {r['outputs']} | "
            f"{parity_cell(parity)} | {r['engine_write_free']} |"
        )
    lines.append("")
    lines.append(END)
    return "\n".join(lines)


def current_block(doc: str) -> str | None:
    start = doc.find(BEGIN)
    end = doc.find(END)
    if start < 0 or end < 0 or end < start:
        return None
    return doc[start : end + len(END)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail on drift, write nothing"
    )
    args = parser.parse_args()

    errors = audit()
    if errors:
        for error in errors:
            print(f"kernel table: {error}")
        print("kernel table: FAIL")
        return 1

    block = build_block()
    if not DOC.is_file():
        print(f"kernel table: {DOC.relative_to(ROOT)} is missing")
        return 1
    doc = _read(DOC)
    present = current_block(doc)
    if present is None:
        print(f"kernel table: markers missing from {DOC.relative_to(ROOT)}")
        return 1

    if args.check:
        if present != block:
            print("kernel table: doc block is stale (run without --check)")
            return 1
        print(f"kernel table: PASS ({len(KERNELS)} kernels, all engine-write-free)")
        return 0

    DOC.write_text(doc.replace(present, block), encoding="utf-8")
    print(f"kernel table: wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
