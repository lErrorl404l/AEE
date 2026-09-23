# Gaps and Lessons Register

Defects and lessons for this project. The format matches the standards
library register: what happened, what went wrong, why, what prevents
recurrence, and the lesson.

## GAP-012: a ninth argument the engine does not accept

Status: Closed

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

Status: Closed

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

Status: Closed

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

Status: Closed

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

Status: Closed

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

Status: Closed

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


## GAP-019: a model added to the value it reads

Status: Closed

**What happened.** `fnc_calculateWaterInfluence` read
`aee_core_currentTemperature` to obtain the ambient temperature. That is
the value the caller adds the returned offset to. The offset alternated
+40 and -40 C per tick and the temperature swung 80.9 C, reaching 71 C on
one tick and -8 C on the next.

**What went wrong.** Two faults met. The reader and the writer shared one
variable, so the model fed on its own output. The per-term debug prints
sampled different ticks, so each looked plausible in isolation.

**Why.** The rule was absent. Nothing forbade a model from reading the
state it contributes to, and no test sampled the same tick twice.

**What prevents recurrence.** The ambient temperature is passed in as an
argument. The docker determinism phase (PHASE5) samples one tick apart and
asserts the delta stays small, so a feedback loop fails the gate.

**Lesson.** A model that adds to state X must never read published X. Pass
the input in, and print the running total after each stage, not per term.

## GAP-020: a cross-addon read that returned nil

Status: Closed

**What happened.** `EGVAR(core,currentTemperature)` was used as a value in
72 places across 52 files. It expands to the unquoted token
`aee_core_currentTemperature`, which SQF reads as a variable, so every one
of those reads returned nil. The client RPT carried 2796 "Undefined
variable aee_core_currenttemperature" errors in a single session.

**What went wrong.** The macro was used as if it were a variable. The
correct form is `missionNamespace getVariable [QEGVAR(core,name), default]`.

**Why.** The rule was unclear. Both EGVAR and QEGVAR are documented, and
the difference is invisible in a file that only reads well-formed code.
Five call sites already used the correct form, so the pattern existed.

**What prevents recurrence.** Every cross-addon read uses QEGVAR inside
getVariable. `fnc_resolveShot.sqf` and `fnc_openAltimeter.sqf` are the
reference call sites to match.

**Lesson.** A bare macro that expands to a name is not a value. Cite a
working call site before writing a cross-addon read.

## GAP-021: a unit the setting never used

Status: Closed

**What happened.** `fnc_updatePressure` read `aee_core_tempLapseRate`,
documented as degrees Celsius per 1000 m with a default of 6.5, and used it
as kelvin per metre. The 1000-times value drove the barometric term
negative and the station pressure collapsed to 0.5 hPa. The formula's
ratio was also inverted, so pressure rose with height.

**What went wrong.** Two independent faults in one expression, and the
existing check mirrored the hardcoded constant rather than the setting, so
it passed while the real code diverged.

**Why.** The guardrail was unapplied. The check asserted the formula, not
the setting that feeds it, so a unit error was invisible.

**What prevents recurrence.** The value is divided by 1000 at the point of
use. A new check, `check_barometric_pressure`, compares the result with
the ICAO standard atmosphere table and asserts that pressure falls with
height.

**Lesson.** A setting has a unit. Convert it where it is used, and test the
setting, not a copy of the arithmetic.

## GAP-022: two classifiers sharing one variable

Status: Closed

**What happened.** `aee_core_biome` holds the map Koppen class, read by
fourteen consumers for a map-scoped purpose. A per-position sampler wrote
the same variable every tick with one tile's surface answer. On Stratis at
35 N the map-wide classifier resolved Csa, correct for an Aegean island,
and the position path replaced it with Cfb, because a man-made surface
carries no climate signal.

**What went wrong.** Two functions with different scopes owned one
variable. The weaker signal won because it wrote last.

**Why.** The guardrail was absent. No test compared the two verdicts, and
the latitude band check could not see the fault because Cfb is legal at
35 N.

**What prevents recurrence.** The position sampler publishes
`aee_environmental_localBiome` instead. PHASE8b asserts the map class does
not change when the player crosses a surface boundary. The first fix read
the anchor from the variable it wrote, a feedback loop of the GAP-019
class, and the phase caught it.

**Lesson.** One variable has one owner and one scope. When two producers
disagree, give the weaker one its own variable rather than a tie-break.

## GAP-023: a supersession that left its consumers behind

Status: Closed

**What happened.** Issue #11 asked for three things. The largest, a full
soil temperature solve, landed as a 4-node Crank-Nicolson stack (issue
#198), which replaced the single-node solver the issue had described. Two
consumers of the OLD approximation were never moved with it:
`fnc_detectGroundFrost` still computed the surface as `T_air - 2` on a
clear calm night, and `fnc_calculateFreezeThawCycling` still used
`0.05 * sqrt(FDD)`. Both were the exact shortcuts the issue named.

**What went wrong.** The replacement was declared done when the new model
landed. Nothing checked whether every consumer of the model it replaced
had been routed.

**Why.** The rule was absent. A replacement reads as complete because the
new code works, and the old call sites keep working too, on the value
they always produced. Nothing compares the two.

**What prevents recurrence.** Both consumers now read the solved values.
`test_frost_supersession.py` guards each route at source level, because
"this file uses the solved value" is a property no runtime test can see
on a headless server.

**Lesson.** A replacement is not done when the new model works. It is done
when every consumer of the old one has moved.

## GAP-024: a test that asserted a monotonicity the physics lacks

Status: Closed

**What happened.** A new test asserted that frost depth decreases as soil
water content rises, across every row of the material table. It failed on
two rows that share one water content. An earlier version of the same
table also produced a 65-metre frost depth, because a water content of
zero let the divisor collapse to the floor.

**What went wrong.** Two faults, both in my own work. Depth depends on
BOTH the frozen conductivity and the water content, so ordering by water
content alone is not guaranteed to be monotonic. And a cover over soil
(concrete, asphalt, metal) is not a soil: it takes the ground beneath it.

**Why.** The guardrail was absent at first. I wrote the test from the
intuition "more water, less depth" without checking that the function has
one controlling variable. It does not.

**What prevents recurrence.** The test holds conductivity fixed and varies
only the water content, which is the invariant that actually holds. The
table gives every cover the soil beneath it. A test asserts no material
exceeds 5 m of frost depth at 500 degree-days.

**Lesson.** A test that fails on correct code is a finding about the test.
Check which variables the function actually depends on before asserting
monotonicity in one of them.
