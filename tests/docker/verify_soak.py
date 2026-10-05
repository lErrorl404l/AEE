#!/usr/bin/env python3
"""Verify the AEE soak and stress log.

Reads a captured soak log and reports the [SOAK-*] results.  Exits 0 only when
the soak finished, no violation was reported, every sample stayed inside the
cap, the churn left no agent, both budgets passed, and the log holds no
un-benign Error or Warning line.

The benign lists are reused from tests/docker/verify.py.  They are copied here
so the same engine noise is ignored by both gates.
"""

import re
import sys

LOG = sys.argv[1] if len(sys.argv) > 1 else "tests/docker/run.soak.log"

# The field, sound and fauna caps.  The first two are the model constants.
AI_CELL_CAP = 256
WILDLIFE_SOUND_INSTANCE_CAP = 8
WILDLIFE_ANIMAL_CAP = 16

with open(LOG, encoding="utf-8", errors="replace") as f:
    text = f.read()

# Benign lists copied from tests/docker/verify.py.  Keep the two in step.
_ERROR_BENIGN = (
    "Warning:",
    ".wss",
    ".ogg",
    ".wav",
    "Cannot open object",
    "bison",
    "Wheel reference not initialized",
    "ammo1",
)
_WARNING_BENIGN = (
    "Warning: looped for animation",
    "is dependent on downloadable content",
    "No entry 'bin\\config.bin",
    "No entry 'bin/config.bin",
    "No entry '.",
    "'/' is not a value",
    "Size: '/' not an array",
    "No geometry and no visual shape",
    "Fresnel k must be >0",
    "Some of magazines weren't stored",
    "unknown animation source",
    "Array tex in bin",
    ".wss",
    ".ogg",
    ".wav",
    "Cannot open object",
    "bison",
    "Convex component representing",
)

errors = [
    line
    for line in text.splitlines()
    if re.search(r"\bError\b", line) and not any(b in line for b in _ERROR_BENIGN)
]
warnings = [
    line
    for line in text.splitlines()
    if re.search(r"\bWarning\b", line) and not any(b in line for b in _WARNING_BENIGN)
]

done = "[AEE-SOAK] DONE" in text
fails = re.findall(r"\[SOAK-FAIL\][^\n]*", text)
phase10 = "[PHASE10] [PASS]" in text
phase11 = "[PHASE11] [PASS]" in text

sample_count = 0
field_values = []
sound_values = []
fauna_values = []
for line in text.splitlines():
    if "[SOAK-SAMPLE]" not in line:
        continue
    sample_count += 1
    match = re.search(r"\bfield=(\d+)", line)
    if match:
        field_values.append(int(match.group(1)))
    match = re.search(r"\bsound=(\d+)", line)
    if match:
        sound_values.append(int(match.group(1)))
    match = re.search(r"\bfauna=(\d+)", line)
    if match:
        fauna_values.append(int(match.group(1)))

match = re.search(r"agents_end=(\d+)", text)
agents_end = int(match.group(1)) if match else None

field_over = [v for v in field_values if v > AI_CELL_CAP]
sound_over = [v for v in sound_values if v > WILDLIFE_SOUND_INSTANCE_CAP]
fauna_over = [v for v in fauna_values if v > WILDLIFE_ANIMAL_CAP]

print(f"soak samples: {sample_count}")
print(
    f"field samples: {len(field_values)} max={max(field_values) if field_values else 'none'}"
)
print(
    f"sound samples: {len(sound_values)} max={max(sound_values) if sound_values else 'none'}"
)
print(
    f"fauna samples: {len(fauna_values)} max={max(fauna_values) if fauna_values else 'none'}"
)
print(f"agents_end: {agents_end}")
print(f"soak fails: {len(fails)}")
for f in fails:
    print(f"  {f}")

verdict_fail = False

if not done:
    print("  soak did not reach DONE")
    verdict_fail = True
if fails:
    verdict_fail = True
if not field_values:
    print("  no field sample present")
    verdict_fail = True
if field_over:
    print(f"  field over cap {AI_CELL_CAP}: {sorted(set(field_over))}")
    verdict_fail = True
if sound_over:
    print(f"  sound over cap {WILDLIFE_SOUND_INSTANCE_CAP}: {sorted(set(sound_over))}")
    verdict_fail = True
if fauna_over:
    print(f"  fauna over cap {WILDLIFE_ANIMAL_CAP}: {sorted(set(fauna_over))}")
    verdict_fail = True
if agents_end != 0:
    print(f"  agents_end not 0: {agents_end}")
    verdict_fail = True
if not phase10:
    print("  no [PHASE10] [PASS] line")
    verdict_fail = True
if not phase11:
    print("  no [PHASE11] [PASS] line")
    verdict_fail = True
if errors:
    print(f"script errors: {len(errors)}")
    for e in errors[:10]:
        print(f"  {e}")
    verdict_fail = True
if warnings:
    print(f"warnings (treated as errors): {len(warnings)}")
    for w in warnings[:10]:
        print(f"  {w}")
    verdict_fail = True

if verdict_fail:
    print("RESULT: FAIL")
    sys.exit(1)
print("RESULT: PASS")
