# Gaps and Lessons Register

Defects and lessons for this project. The format matches the standards
library register: what happened, what went wrong, why, what prevents
recurrence, and the lesson.

## GAP-012: a ninth argument the engine does not accept

**What happened.** `fnc_isPositionShadowed.sqf` called
`lineIntersectsSurfaces` with a ninth argument, `true`, commented
"returnUnique (2.10+)". Every shadow raycast raised "Error Type Bool,
expected String". The session RPT held thousands of the line.

**What went wrong.** The engine's array form does not take `returnUnique`
at that index in the installed build. The other three calls in the repo
pass eight arguments and work. `returnUnique` is a documented optional
argument, and its default is already `true`, so the argument was both
invalid and redundant.

**Why.** The rule was absent. No test asserted the shape of the call, and
the docker gate does not always reach the solar-shadow path (the function
returns early when the solar radiation is low), so the fault survived a
green gate and surfaced only in a live session log.

**What prevents recurrence.** The call keeps the documented eight
arguments. `test_thermal_optics.py` asserts that `returnUnique` is absent
from the file, so the argument cannot return unnoticed. The signature is
cited from the archived biki page.

**Lesson.** An optional command argument is accepted only where the build
puts it. Keep the call shape the working call sites use, and cite the
signature before writing the call.

## GAP-013: a matching keyword with a lookalike character

**What happened.** Four capture rows under `data/equipment/sources/` carried
the family keyword `protaс`, with U+0441 CYRILLIC SMALL LETTER ES in place
of the Latin `c`. The generated resolver could never match a classname.

**What went wrong.** A family keyword exists only to match a classname. A
keyword with a non-Latin letter is dead. The generator accepted any string
and projected it.

**Why.** The rule was absent. The schema asked for lowercase and no
punctuation, but no check rejected a non-Latin character or proved that a
keyword can match.

**What prevents recurrence.** `gen_equipment_data.py` folds the common
lookalikes to Latin and counts any keyword that still holds a non-ASCII
character under `non_ascii`, so the defect is visible in the build output.
`test_inventory_load.py` fails when the projection drifts from the
captures.

**Lesson.** A keyword that cannot match looks like coverage and is worse
than none. Fold lookalikes at ingest and count what is dropped.

## GAP-014: `hmd` returns a string, not an array

**What happened.** The first draft of `fnc_getInventoryLoad.sqf` wrote
`hmd _unit + [binocular _unit]`. HEMTT reported L-S12: the left operand is
a String. The walk was wrong before it ran.

**What went wrong.** `hmd` returns one classname (an empty string when the
slot is empty), not an array. The signature was assumed, not read.

**Why.** The rule was unapplied. Truth over assumption already requires the
engine signature to be read first. The assumption was written into the call
without the read.

**What prevents recurrence.** The walk reads `hmd` and `binocular` as
single classnames and guards each with a membership test. The HEMTT type
checker is the gate that caught it, and it runs on every commit.

**Lesson.** Read the engine signature before writing the call. A type
checker that catches the call shape is cheaper than a docker run.

## GAP-016: an eager type guard evaluated a command on the wrong type

**What happened.** `fnc_readState.sqf` tested a value's type and its length
in one `&&` chain: `_neverZero && _val isEqualType [] && count _val == 0`.
The engine evaluated `count` on a number even when the type test was false.
Every weapon barrel-heat display update raised "count: Type Number,
expected Array", eight times in a short session.

**What went wrong.** The chain read as a guard but was not one. `&&`
evaluates its operands eagerly, so the length test ran regardless of the
type test.

**Why.** The rule was absent. A guard that protects a command from the
wrong type is a specific SQF idiom, and nothing in the register named it.
The docker gate never reached the weapon display path, so a green gate
hid a fault that a player would see.

**What prevents recurrence.** Each branch now tests one type, so the count
runs only on an array. Docker phase 59 drives every branch in-engine. The
register carries the lesson.

**Lesson.** `&&` is eager. Guard a command with a branch, never with a
`&&` chain, because the chain runs every operand.

## GAP-017: an engine warning passed as clean

**What happened.** Two faults emitted engine warnings and the gate passed
them. `fnc_calculateBarrelState.sqf` read a weapon's modes class without
testing it first ("'modes/' is not a class"), and `fnc_init.sqf` logged a
normal UTM zone as an AEE WARNING.

**What went wrong.** The verify gate collected `Error` lines only. A
warning was invisible to it, so the discipline "warnings are errors" was
not enforced anywhere.

**Why.** The rule was absent from the tool. The operator held the rule; the
gate did not.

**What prevents recurrence.** `tests/docker/verify.py` fails on any warning
AEE emits. Only engine noise that no AEE change can remove is allowlisted,
and every entry states why. This is the check that would have caught both
faults.

**Lesson.** A rule the gate does not hold is a rule that lapses. Put the
rule in the gate.

## GAP-018: four stale checks kept the suite red

**What happened.** Four tests failed for reasons unrelated to the code:
a parser that could not read a unary command inside parentheses, a row
pattern that matched six fields against eight, a not-built assertion for a
feature built in issue #212, and a test that read a local extraction not in
the tree.

**What went wrong.** Each check encoded a fact that later changed, and none
carried a guard against its own staleness. The suite reported eleven
failures, so a real failure would have been lost in the noise.

**Why.** The rule was unapplied. A check is maintenance, and a check that
describes a past state must be updated with the state, or it becomes a
false alarm.

**What prevents recurrence.** The suite is green: 1517 tests, no failure,
and the fourteen skips each name why. A local-fixture test skips with a
reason instead of erroring. A not-built check asserts the code and the doc
agree in either direction.

**Lesson.** A red suite hides the next real failure. Keep the floor clean.

