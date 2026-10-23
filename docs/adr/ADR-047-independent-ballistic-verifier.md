# ADR-047: An independent ballistic verifier

Status: accepted. This record fixes the reference solver, its licence position,
the dependency pin, the validation of the solver against published tables, the
comparison tolerances and the data screenings.

Relates to ADR-003 (verified ballistics data), ADR-036 (native kernel parity),
ADR-037 (the grade gate).

---

## Context

The corpus in `data/ballistics/` holds 681 projectiles, 316 loads and 1643
weapons. Every ballistic coefficient in it was read from a publisher, measured
at a proving ground, or derived. Nothing in the repository re-derives a
trajectory from those numbers, so a wrong coefficient produces a plausible
drop table and no failure. The kernel tests pin the kernel's arithmetic against
its own reference, which cannot detect a bad input.

An independent check needs a second solver that was written by other people
from the same physics. It must be able to answer a drop question: given a mass,
a calibre, a ballistic coefficient, a drag model and a muzzle velocity, return
drop, wind drift, retained velocity and time of flight.

## Candidates

**py-ballisticcalc 3.1.1.** Chosen. Licence LGPL-3.0 (the metadata `License`
field carries the full GNU Lesser General Public License version 3 text).
`Requires-Python >=3.11`, and the classifiers name 3.11 to 3.15. The 3.1.1
wheel is `py_ballisticcalc-3.1.1-py3-none-any.whl`, uploaded 2026-10-16, so it
is pure Python and needs no build step. It is maintained at
https://github.com/o-murphy/py-ballisticcalc. It ships the standard drag
tables TableG1, TableG2, TableG5, TableG6, TableG7, TableG8, TableGI, TableGS
and TableRA4, an ICAO atmosphere class, a wind class and a custom drag table
interface. Every published release is LGPL-3.0. No 2.x release is MIT.

**`ballistics` 0.4.0.** Rejected. MIT, but last uploaded 2018-02-15 and it has
no standard atmosphere model. It cannot take an altitude or a temperature, so
its density is fixed and a drop table that depends on air density cannot be
answered.

**`pyBallistics` 1.2.1.** Rejected. It computes interior ballistics, so it has
no exterior trajectory, and it publishes no licence field, so its licence
cannot be shown compatible.

## Licence position

The repository is GPL-2.0-or-later with a PBO distribution exception, stated in
README and LICENSE.

py-ballisticcalc is a development-side dependency of a validation tool. It is
never vendored and never conveyed inside a PBO, so no combined-work obligation
arises for the shipped mod. LGPL-3.0 combines with GPL-3.0, and GPL-2.0-or-later
permits that upgrade. The obligation that remains is the ordinary one: the tool
names the library, its version and its licence, and a user who runs the tool
installs the library themselves.

Vendoring the library would remove that position, because a copy in the tree
would make the repository a combined work and require either the removal of the
copyleft dependency or the distribution of its source. The rule is therefore:
**pinned dependency, never vendored.**

## The pin

The repository held no dependency manifest. The de-facto manifest is the
"Install test dependencies" step of `.github/workflows/ci.yml`, which runs
python 3.12 and installs numpy, pillow and SALib 1.6.0.

`tools/requirements-tooling.txt` now pins `py-ballisticcalc==3.1.1` with a
header that states the licence and the non-vendoring rule. The CI step installs
that file.

A clean install was proved from a throwaway directory:

    $ uv venv .venv --python 3.12
    $ uv pip install -r tools/requirements-tooling.txt
    Installed 4 packages
     + deprecated==3.0.0
     + py-ballisticcalc==3.1.1
     + typing-extensions==4.16.0
     + wrapt==2.5.1
    $ .venv/bin/python -c "import importlib.metadata as md; print(md.version('py-ballisticcalc'))"
    3.1.1

The CI gate runs python 3.12. The local system python3 is 3.15.0 and does not
carry the library. The test module therefore skips cleanly when the import is
absent, with `unittest.skipUnless`, in the pattern `tools/tests/test_sensitivity.py`
already uses for SALib.

## Validation of the solver before use

A solver that cannot reproduce a published table proves nothing. Two published
worked examples were fetched and reproduced.

| Example | Source | Conditions | Worst error |
|---|---|---|---|
| .308 Win 155 gr Scenar-L, G1 0.460, 860 m/s | Lapua Catalog 2026, product 4317076 | 100 m zero, 40 mm sight, ISA sea level, 4 m/s sidewind | velocity 1.56 %, drop 1.22 %, drift 7.24 % |
| .338 Lapua Mag. 250 gr Scenar, G7 0.322, 905 m/s | Lapua Catalog 2026, product 4318017 | same | velocity 0.31 %, drop 1.28 %, drift 8.30 % |

Both tables were read from
https://www.lapua.com/wp-content/uploads/2026/06/Lapua_Catalog_2026_ENG_web.pdf
with sha256 `27b2ebed6394cfa9a762527f8188eb3e534d39c1ef75dd9524f78c7954417f64`,
which matches the hash the corpus records for that document in
`data/ballistics/sources/lapua_velocity.json`.

The drop and velocity agreement is within 1.6 %. The drift agreement is within
8.3 %, and the residual is one-sided: the publisher's drift is lower than a
three-dimensional relative-wind integration returns. Drop and velocity agreeing
to 1.6 % while drift differs by 5 to 8 % confines the difference to the wind
convention, not to the drag law or the atmosphere. The check reports the
classic `w (t - x / v0)` approximation beside both figures so a reader can see
that the solver matches the closed form to a fraction of a percent. The
published-example tolerance for drift is therefore 10 %, and the number is
stated rather than hidden.

Example one is gated to 800 m. The publisher bands the coefficient by velocity
(0.473 above 830 m/s, 0.459 from 830 to 600, 0.430 from 600 to 380), so a single
0.460 coefficient is only valid in the top band. The 1000 m row is printed and
not gated.

## Comparison contract

The AEE side is recomputed in Python from the published equations. The verifier
never runs the SQF, never shells out to it, and never imports a value generated
from it. Only the Cd(Mach) tables are shared, because a like-for-like
comparison must integrate the same published curve.

- Retardation `K (Cd(Mach) / BC) v^2 rhoRel`, `K = 0.00068418`, from
  `fnc_calculateBallisticDrag.sqf`.
- Speed of sound `20.05 sqrt(T + 273.15)`, from `constants.hpp`.
- Cd interpolated linearly on Mach and clamped at both ends.
- Integration: fixed-step RK4 at 1 ms, not the game tick.
- Gravity 9.80665 m/s^2, flat fire, no Coriolis, no spin drift.
- Zero 100 m, sight height 40 mm, wind 4 m/s from 90 degrees.
- Atmosphere ISA sea level, 15.0 C, 1013.25 hPa, 0 % relative humidity.
- Ranges 0 to 1000 m at 100 m steps, truncated below 200 m/s retained velocity.

## Tolerances

| Metric | Tolerance | Reason |
|---|---|---|
| Retained velocity | 1 % | Same drag law both sides, so only quadrature and Cd interpolation differ, both sub-0.1 % at a 1 ms step |
| Drop | `max(1 % of drop, 0.03 mrad x range)`, ramping to 2 % at 1000 m | 0.03 mrad is 9 mm at 300 m, about the resolution a published table prints. The ramp covers the growing sensitivity of drop to the drag model |
| Wind drift | `max(3 %, 5 mm)` | At short range the drift is tens of millimetres and whole-millimetre rounding is a few percent by itself |
| Time of flight | 1 %, reported only | Not a data-error signal |

A residual systematic offset is measured and printed. AEE uses
`rho0 = 1.225 kg/m3`. The solver documents `cStandardDensity` 0.076474 lb/ft3,
which is 1.2250 kg/m3, so the two constants agree. The measured mean drift bias
over the representative set is +0.2 %, which is the density model difference,
not a tolerance problem.

## The two screenings

**Form factor.** `i = SD / BC`, so `i` is unity for the drag model's standard
projectile. The band is derived per calibre group from the records whose
`bc_g7` grade is measured or corroborated, and a group is banded only when it
holds at least three such records. Groups below that are not screened. Records
that hold only a `bc_g1` are not screened either, because mapping a G1
coefficient onto the G7 scale needs a ratio whose spread the corpus puts at
1.38 to 2.58, which leaves no power to detect anything. The derivation is
printed in the report.

**Transposition.** Six checks: a drag model field that disagrees with its own
field name, a `bc_g1 / bc_g7` ratio outside the corpus's own ratio band, a
mass a decade from the median for its calibre, a coefficient identical to
another bullet's coefficient while the mass and calibre both differ, a
coefficient that is the reciprocal or a decade shift of the same bullet's
other-model coefficient, and a bullet calibre that does not match the cartridge
of its matched load. A shared coefficient only counts as a copy at four
significant figures, because manufacturer coefficients are commonly published
to three decimals and two bullets sharing 0.240 is ordinary rounding.

## Answering a flag

A flag is a question, not a verdict. The answer is written once, in
`data/ballistics/form_factor_reviews.json`, and copied onto the projectile as
`form_factor_review` by `gen_projectiles.py`. The record states the decision,
the reason and the sources that state the value, and the record's `note`
carries the same sentence, so a reader of the corpus sees the review beside the
number.

The band and the screen are not touched by a review, and no coefficient moves
because of one. A decision of `genuine` keeps the value and says why the shape
explains the form factor. `source_error`, `unit_error` and `unsupported` say
the value was corrected or withdrawn, so the record leaves the flag list, and a
review carrying one of those decisions on a record that is still outside the
band is reported as a defect. A review on a record that is inside the band is
stale and is reported the same way. The data gate requires the reason and at
least one known evidence source, so an answer without evidence cannot close a
screen.

## Outcome

The verifier reports and changes nothing. No corpus value is edited by it. A
flagged value is a follow-up item with its own citations.

First full run: 62 bullets compared out of 681 (the rest have no declared
muzzle velocity or no ballistic coefficient), 0 trajectory disagreements, 122
form factor flags, 0 transposition flags. Exit status 0.

Review of the 122 flags, 2026-10-23: every flag was settled against the held
source table, and all 122 are `genuine`. Each value equals a coefficient the
maker states for that bullet; 42 of them (Berger) also equal the maker's own
published G7 form factor, and 18 carry an independent measurement in
`conflicts.json`. Of those 19 measurements, 12 agree within 5 percent and five
agree within 13 percent. Two Sierra bullets differ by 18 and 20 percent, and
the record keeps the maker value under ADR-003. No value was corrected and
none was withdrawn. The screen is unchanged, so the open count is now 0 and
the reviewed count is 122.
