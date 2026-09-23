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
)
errors = [
    l
    for l in text.splitlines()
    if re.search(r"\bError\b", l) and not any(b in l for b in _ERROR_BENIGN)
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
)
warnings = [
    l
    for l in text.splitlines()
    if re.search(r"\bWarning\b", l) and not any(b in l for b in _WARNING_BENIGN)
]

print(f"phases passed: {len(passes)}")
for p in passes:
    print(f"  {p}")
print(f"phases failed: {len(fails)}")
for f in fails:
    print(f"  {f}")
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

if fails or not done or errors or warnings:
    print("RESULT: FAIL")
    sys.exit(1)
print("RESULT: PASS")
