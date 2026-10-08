#!/usr/bin/env python3
"""Verify the AEE docker test log.

Reads a captured server log and reports the [PHASE] results. Exits 0 only
when every phase passed and the mission finished.
"""

import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "tests/docker/run.log"

with open(LOG, encoding="utf-8", errors="replace") as f:
    text = f.read()

passes = re.findall(r"\[PHASE\d+\] \[PASS\][^\n]*", text)
fails = re.findall(r"\[PHASE\d+\] \[FAIL\][^\n]*", text)
done = "[AEE-TEST] DONE" in text

# Any "Error" line in the server log is a failure — a script error, a
# ppEffect signature error, a type mismatch, or a malformed call.  The
# previous filter matched only a few keywords (script/variable/Generic/
# position) and silently ignored everything else, which let the
# ChromAberration "6 elements provided, 3 expected" and the particle
# "Type Array, expected Number" errors pass the gate.  Exclude only the
# known-benign engine noise lines that are unrelated to AEE.
_ERROR_BENIGN = (
    "Warning:",
    ".wss",
    ".ogg",
    ".wav",  # missing sound files (vanilla)
    "Cannot open object",  # engine asset noise
    "bison",  # PBO header noise
    # The fleet probe creates every public ground vehicle. The engine emits
    # these two notes on createVehicle for vanilla classes: a wheel that has
    # not taken a simulation step, and a vanilla vehicle MFD whose condition
    # reads undefined globals. No AEE change can remove either.
    "Wheel reference not initialized",
    "ammo1",
)
errors = [
    line
    for line in text.splitlines()
    if re.search(r"\bError\b", line) and not any(b in line for b in _ERROR_BENIGN)
]

# Warnings are errors here.  A warning AEE emits fails the gate.  Only
# engine noise that no AEE change can remove is benign, and each entry
# states why.  This is the check that caught the 'modes/' class read and
# the mapZone alarm before a player saw them.
_WARNING_BENIGN = (
    "Warning: looped for animation",  # vanilla RTM loop flag
    "is dependent on downloadable content",  # server note: the base addon is installed
    "No entry 'bin\\config.bin",  # vanilla class gap in the BI config
    "No entry 'bin/config.bin",
    "No entry '.",  # engine light class gap (BI CargoLight)
    "'/' is not a value",  # BI config placeholder
    "Size: '/' not an array",  # BI config placeholder
    "No geometry and no visual shape",  # vanilla proxy models
    "Fresnel k must be >0",  # vanilla material
    "Some of magazines weren't stored",  # engine soldier loadout note
    "unknown animation source",  # vanilla vehicle animation
    "Array tex in bin",  # vanilla config
    ".wss",  # missing vanilla sound files
    ".ogg",
    ".wav",
    "Cannot open object",  # engine asset noise
    "bison",  # PBO header noise
    # The fleet probe creates every public ground vehicle; the engine prints a
    # model geometry note when a vanilla convex component is unnamed. It is a
    # vanilla asset note, not AEE output.
    "Convex component representing",
)
warnings = [
    line
    for line in text.splitlines()
    if re.search(r"\bWarning\b", line) and not any(b in line for b in _WARNING_BENIGN)
]

print(f"phases passed: {len(passes)}")
for p in passes:
    print(f"  {p}")
print(f"phases failed: {len(fails)}")
for f in fails:
    print(f"  {f}")

# The debug switch must actually gate the trace.  Phase 63 runs the traced
# path with the flag on; if the DEBUG lines are absent from the log, the
# macro is not reading the flag and the switch is decorative.  This is the
# check that a setting can be registered and still do nothing.
_debug_expected = (
    "[AEE][physiology][DEBUG] item mass:",
    "[AEE][ballistics][DEBUG] shot ",
)
_debug_missing = [m for m in _debug_expected if m not in text]
if _debug_missing:
    print(f"debug switch: {len(_debug_missing)} expected trace line(s) absent")
    for m in _debug_missing:
        print(f"  missing: {m}")

# The consolidated wildlife state line is emitted at INFO on the first tick
# even with tracing off.  Its absence means the logger is not wired into the
# tick, so the run proves the line end to end.
_state_line = "[AEE][wildlife][INFO] wildlife state |"
_state_missing = [] if _state_line in text else [_state_line]
if _state_missing:
    print(f"wildlife state line: {len(_state_missing)} expected line(s) absent")
    for m in _state_missing:
        print(f"  missing: {m}")

# The mission probes report with their own tag, not [PHASEn], because they
# run on a separate thread loaded by execVM. The fails regex above matches
# [PHASE\d+] only, so a probe failure or a probe that never ran was INVISIBLE
# to this gate: init.sqf emits its own DONE, so the run still completed. Require
# each probe's PASS line explicitly, and require the absence of its FAIL line.
_probe_expected = (
    "[P64] [PASS]",
    "[P65] [PASS]",
    "[P66] [PASS]",
    "[P68] [PASS]",
    "[P69] [PASS]",
    "[P70] [PASS]",
    "[P71] [PASS]",
    "[P72] [PASS]",
    "[P73] [PASS]",
    "[P74] [PASS]",
    "[P75] [PASS]",
    "[P76] [PASS]",
    "[P77] [PASS]",
    "[P78] [PASS]",
    "[P79] [PASS]",
    "[P80] [PASS]",
    "[P81] [PASS]",
    "[P82] [PASS]",
    "[P83] [PASS]",
    "[P84] [PASS]",
    "[P84B] [PASS]",
    "[P85] [PASS]",
    "[P86] [PASS]",
    "[P87] [PASS]",
    "[P88] [PASS]",
    "[P89] [PASS]",
    "[P91] [PASS]",
    "[P92] [PASS]",
    "[P93] [PASS]",
    "[P94] [PASS]",
    "[P95] [PASS]",
    "[P96] [PASS]",
    "[P97] [PASS]",
    "[P98] [PASS]",
    "[P99] [PASS]",
    "[P100] [PASS]",
    "[P101] [PASS]",
    "[P102] [PASS]",
    "[P103] [PASS]",
    "[P104] [PASS]",
    "[P105] [PASS]",
    "[P106] [PASS]",
    "[P107] [PASS]",
    "[P108] [PASS]",
    "[P109] [PASS]",
    "[P110] [PASS]",
    "[P111] [PASS]",
    "[P112] [PASS]",
    "[P113] [PASS]",
    "[P115] [PASS]",
    "[P116] [PASS]",
    "[P117] [PASS]",
)
_probe_missing = [m for m in _probe_expected if m not in text]
if _probe_missing:
    print(f"mission probes: {len(_probe_missing)} expected PASS line(s) absent")
    for m in _probe_missing:
        print(f"  missing: {m}")
_probe_failed = sorted(
    set(
        re.findall(
            r"\[P(?:64|65|66|68|69|70|71|72|73|74|75|76|77|78|79|80|81|82|83|84B|84|85|86|87|88|89|91|92|93|94|95|96|97|98|99|100|101|102|103|104|105|106|107|108|109|110|111|112|115|116|117)\] \[FAIL\][^\n]*",
            text,
        )
    )
)
if _probe_failed:
    print(f"mission probes: {len(_probe_failed)} failed")
    for p in _probe_failed:
        print(f"  {p}")

if not done:
    print("  mission did not reach DONE")
if errors:
    print(f"script errors: {len(errors)}")
    for e in errors[:10]:
        print(f"  {e}")
if warnings:
    print(f"warnings (treated as errors): {len(warnings)}")
    for w in warnings[:10]:
        print(f"  {w}")

if (
    fails
    or not done
    or errors
    or warnings
    or _debug_missing
    or _state_missing
    or _probe_missing
    or _probe_failed
):
    print("RESULT: FAIL")
    sys.exit(1)
print("RESULT: PASS")
