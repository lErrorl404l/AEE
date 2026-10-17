# arma_vqa - offline visual QA for Arma 3 mods

Checks what a mod will **look like** without launching the game: post-process effects, priorities and layering,
thermal imaging, night vision, aperture, picture-in-picture, camera effects and the optics config that drives them.
It is a static analyser plus an approximate renderer. It does not replace one look in the real game; it makes
most of the trips to the game unnecessary.

Pure Python 3.9+. Needs `numpy` and `Pillow` for the render preview (`pip install numpy pillow`); the analyser itself uses only the standard library.

```
python3 -m arma_vqa scan path/to/mod                    # static checks + offline render of every effect stack found
python3 -m arma_vqa scan modA modB modC                 # several mods TOGETHER: finds cross-mod priority collisions
python3 -m arma_vqa scan mod --no-sim --min-severity warning --fail-on warning     # CI style, exit code 1 on findings
python3 -m arma_vqa scan mod --sim-out previews/        # also write before/after PNG sheets
python3 -m arma_vqa scan mod --format json -o report.json   # or --format md
python3 -m arma_vqa limits                              # every documented limit, default and priority, with provenance
python3 -m arma_vqa limits ColorCorrections             # one effect
python3 -m arma_vqa explain PP004                       # why a rule exists, with its source link  (explain all = everything)
python3 -m arma_vqa sim ColorCorrections "[1,0.4,0,[0,0,0,0],[1,1,1,0],[1,1,1,0]]"   # preview one effect, no mod needed
python3 -m arma_vqa ti --start 0.7 --width 0.3 --modes 1 2                          # preview a thermal output window
python3 -m arma_vqa calibrate --pair before.png after.png "[...]" --out calibration.json   # fit the renderer to real screenshots
python3 -m unittest discover -s tests -v                # self-tests
```

Run it on the **unpacked source** of a mod (the folder with `config.cpp` and the `.sqf` files), the same place you run
HEMTT or sqflint. It reads `.sqf`, `config.cpp`, `.hpp`, `.h` and `.ext`, follows `#include` and simple `#define`s inside the scanned
folders, and understands CBA/ACE style `GVAR(x)` / `EGVAR(c,x)` variables.

## How much to trust a finding

Every finding carries a provenance tag. This is the most important thing to read:

| Tag | Meaning |
|---|---|
| `wiki` | Stated on the Bohemia wiki. |
| `wiki-note` | From a user note on a wiki page. Less authoritative. |
| `tracker` | A bug report on the BI Feedback Tracker: the engine deviates from the documentation. |
| `inferred` | A logical consequence of the wiki text, not stated outright. |
| `heuristic` | A QA threshold chosen by this tool, **not** a Bohemia limit. Editable in `rules/post_process.json` (`thresholds`). |
| `model` | Depends on the approximate renderer. Uncalibrated until you run `calibrate`. |

Severity is capped by confidence: renderer-based findings never rise above `warning`, and numbers the wiki sources disagree on are `info`.

## What it checks (63 rules)

**Post-process effects**

| Rule | Default severity | Provenance | What it catches |
|---|---|---|---|
| PP001 | error | wiki | Unknown post-process effect name |
| PP002 | error | wiki | Wrong number of parameters for effect |
| PP003 | warning | wiki | Parameter outside documented range / wrong type |
| PP004 | warning | wiki | Priority collision |
| PP005 | error | wiki | Advanced effect cannot be created |
| PP006 | info | wiki | ppEffectCreate result not guarded against -1 |
| PP007 | warning | wiki | ppEffectAdjust never committed |
| PP008 | warning | inferred | Effect adjusted but never enabled |
| PP009 | info | inferred | Effect created but never destroyed or disabled |
| PP010 | warning | wiki-note | Timed fade is cut off by ppEffectEnable false / ppEffectDestroy |
| PP011 | info | inferred | Name-based call hits the shared default instance |
| PP012 | error | wiki | Flat colour arrays used with by-name syntax |
| PP013 | info | inferred | Priority order differs from conventional effect order |
| PP014 | info | inferred | Multiple ColorCorrections stack |
| PP015 | warning | wiki | Questionable priority value |
| PP016 | warning | inferred | Invalid commit duration |
| PP017 | info | wiki | FilmGrain monochromatic given as boolean |
| PP018 | info | wiki | Effect depends on a player video option / hardware |
| PP019 | warning | wiki-note | WetDistortion used by name |
| PP020 | info | inferred | Unresolved variable in effect arguments |

**Night vision / thermal / camera**

| Rule | Default severity | Provenance | What it catches |
|---|---|---|---|
| AP001 | info | wiki | setAperture value |
| AP002 | error | wiki | setApertureNew argument shape |
| AP003 | warning | wiki | setAperture after setApertureNew overrides it |
| AP004 | warning | wiki | Aperture set too early (resets at mission start) |
| CAM001 | warning | wiki | camSetFov outside the documented range |
| CAM002 | warning | wiki | camSetFov never committed |
| CAM003 | warning | wiki | cameraEffect uses an undocumented effect or position |
| NV001 | error | wiki | ppEffectForceInNVG needs a handle |
| NV002 | info | inferred | Effects created in a night-vision context but never forced into NVG |
| NV003 | warning | wiki | camUseNVG / setCamUseTI used without a script camera |
| NV004 | error | wiki | ppEffectForceInNVG needs a boolean |
| PIP001 | error | wiki | setPiPEffect mode invalid |
| PIP002 | error | wiki | setPiPEffect parameter count wrong |
| PIP003 | info | wiki-note | Reverting a PiP colour correction with mode 0 has no effect |
| TI001 | error | wiki | Unknown thermal parameter name |
| TI002 | warning | wiki | Thermal output range invalid |
| TI003 | info | wiki | setTIParameter is not saved in savegames |
| TI004 | warning | wiki | Thermal mode index outside documented range |
| TI005 | error | wiki | setTIParameter argument shape |
| TI006 | info | inferred | Thermal flag parameter not 0/1 |
| TI007 | warning | heuristic | Thermal output window narrow / low contrast |
| TI008 | info | tracker | Thermal output window: known engine deviation (tracker T185536) |
| TI009 | error | wiki | disableTIEquipment / disableNVGEquipment needs a boolean |
| TI010 | error | wiki | setVehicleTIPars argument invalid |
| TM001 | warning | wiki | Tone-mapping command is not present in Arma 3 |
| TPL001 | warning | wiki | Post-process template name not found |
| TPL002 | info | wiki | BIS function creates post-process effects at undocumented priorities |

**Config (optics, vision modes)**

| Rule | Default severity | Provenance | What it catches |
|---|---|---|---|
| CF001 | warning | inferred | opticsPPEffects references an unknown CfgOpticsEffect class |
| CF002 | warning | inferred | Unknown visionMode token |
| CF003 | info | inferred | thermalMode set but visionMode has no Ti |
| CF004 | warning | inferred | CfgOpticsEffect class invalid |
| CF005 | info | wiki | Weapon optics zoom values out of order |
| CF006 | warning | wiki | opticsDisablePeripherialVision outside 0..1 |

**UI layers**

| Rule | Default severity | Provenance | What it catches |
|---|---|---|---|
| UI001 | warning | wiki | Numeric layer shared by different resources |

**Offline render model**

| Rule | Default severity | Provenance | What it catches |
|---|---|---|---|
| SIM001 | warning | model | Output clips to black |
| SIM002 | warning | model | Output clips to white |
| SIM003 | warning | model | Few distinct tonal levels remain (banding risk) |
| SIM004 | warning | model | Large overall brightness shift |
| SIM005 | info | model | Saturation almost gone / over-saturated |
| SIM006 | warning | model | Contrast collapsed / harsh |
| SIM007 | info | model | Detail heavily blurred |
| SIM008 | info | model | Grain overwhelms image |
| SIM009 | info | model | Effect not simulated |

`# vqa-ignore: PP006, PP009` on the same or the previous line suppresses rules for that line; `// vqa-ignore-file: PP009` for the whole file.

## What the "does it look good" part really is

The wiki documents the **API contract** (parameter layouts, ranges, priorities, what needs a commit) but not the look.
Two things stand in for the look, and neither is the engine:

1. **Documented-limit checks.** Out-of-range values, wrong array shapes, collisions, effects that never get enabled or committed,
   a fade cut off by an immediate disable. These are reliable, because they are about the contract.
2. **The offline renderer** (`sim.py`). It pushes a synthetic day scene (sky, sun, building, figure, grey ramp, colour patches) through the effect stack in priority
   order and reports crushed blacks, clipped whites, lost tonal levels, brightness shift, saturation and contrast change.
   The Arma 3 shaders are not public, so the maths is a model. Where the wiki is silent the model follows BI's own examples:
   the wiki's "Black & White" example uses desaturation weights `[1,1,1]` with contrast `0.4`, which only produces a sane image if desaturation
   happens *before* a multiplicative contrast, and "brightness 0 = black, 2 = white" implies an additive shift. The thresholds
   (`clip_low_pct`, `levels_remaining_min`, ...) are starting points, not rules of taste.

Not simulated: SSAO, HBAO+ and light shafts (they need depth and sun data), and night vision (its look is not documented).
Thermal output follows the **documented** formula `OutputRangeStart + thermal x OutputRangeWidth`; tracker T185536 reports that the shipped engine
behaves like a levels filter instead, so rule `TI008` says so whenever the window is changed.

### Calibrating against the real game

This is how the renderer becomes trustworthy. It needs a handful of screenshots, once.

1. Pick a static scene and keep the camera still. Take a screenshot with **no** effect (`before.png`).
2. Apply a single `ColorCorrections` with known parameters, take another (`after.png`). Repeat with 2-3 *different* parameter sets
   (different contrast, brightness, colorize) so the candidate models can be told apart. Avoid other effects, HUD and motion.
3. `python3 -m arma_vqa calibrate --pair before.png after1.png "[...params...]" --pair before.png after2.png "[...]" --out calibration.json`
4. `python3 -m arma_vqa scan mod --calibration calibration.json`

`calibrate` ranks the candidate ColorCorrections models by mean absolute pixel error and **warns when none fits**, instead of
reporting a confident fit to the wrong thing. `--effect DynamicBlur` fits the blur scale the same way. Grain, chromatic aberration,
radial blur and wet distortion scales can be edited by hand in the calibration JSON (keys are in `DEFAULT_CAL` in `sim.py`).
In-game screenshots include the engine's own tone mapping, so expect some residual error even from a correct model.

## Validation

* **Real mods.** Scanned ACE3 (`b98e48d`, 2026-10-14) and CBA_A3 (`cd4361a`, 2026-10-10), 5,625 files in about 7 seconds, no crashes.
  Together: 0 errors, 0 warnings, 43 info. A first pass produced 5 + 63 findings; the false positives were fixed and each now has a regression test (`tests/test_rules.py`, labelled REAL-WORLD).
* **Seeded bugs.** Defects injected into ACE-style `GVAR()` code (priority collision, three out-of-range params, missing commit, non-boolean force flag,
  wrong array length, never enabled) are all found.
* **Calibrator.** Renders "screenshots" with a known model, then checks `calibrate` recovers it. This tests the fitting code, not the engine.
* `python3 -m unittest discover -s tests` runs all 29.

## Known limits

* **Static analysis cannot see runtime state.** Values computed at run time, handles stored in collections, and effects created by other mods are `UNKNOWN` and are skipped, never guessed.
  Handles that are returned or passed on ("escaped") do not trigger the lifecycle rules.
* **Disputed numbers.** The current wiki and an older mirrored copy of the same page disagree in places (ColorInversion range, FilmGrain defaults, base priorities,
  RadialBlur/ChromAberration upper bounds). They are listed in `rules/post_process.json` under `_meta.source_conflicts` and reported at `info` only.
  The wiki text was read through a summarising fetcher, not as raw wikitext: check anything that matters against the live page.
* **Documented ranges can be wrong in practice.** ColorCorrections radial radii are documented `-1..1`; ACE3 ships 10 and 2. Optics `opticsZoomMin/Max` follow a different convention on
  vehicle turrets than on weapon optics. Both are `info`/scoped for that reason.
* **Not covered:** UI layout and aspect ratio, textures/rvmat/models, particles and lights, `CfgPostProcessTemplates` internals (only template *names* are checked),
  the priorities used inside `BIS_fnc_setPPeffectTemplate` / `BIS_fnc_ambientPostprocess` (the wiki does not document them; rule `TPL002` says so).
* `setToneMapping` / `setToneMappingParams` are flagged because their wiki pages state "This command is not present in Arma 3". If that changes, edit rule `TM001`.

## Layout

```
arma_vqa/   sqf.py (tokenizer, constant folding, call extraction)   analyze.py (model + rules)   config_cpp.py (config reader)
            sim.py (renderer, calibration fit)   catalog.py (rule text, severity, provenance, source URL)   report.py   cli.py
rules/      post_process.json (effects, ranges, priorities, thresholds)   thermal_camera.json (TI, PiP, aperture, vision modes)
examples/   bad_mod (deliberately broken, every rule family)
tests/      test_rules.py   test_calibrate.py   fixtures/
```

Sources: the BI wiki pages for Post Process Effects, ppEffectCreate / Adjust / Commit / Committed / Enable / Enabled / Destroy / ForceInNVG,
setTIParameter, getTIParameters, setVehicleTIPars, setCamUseTI, camUseNVG, disableTIEquipment, disableNVGEquipment, setPiPEffect, setAperture, setApertureNew,
apertureParams, camSetFov, cameraEffect, cutRsc, BIS_fnc_setPPeffectTemplate, BIS_fnc_ambientPostprocess, setToneMapping(Params), CfgWeapons Config Reference;
Feedback Tracker T185536. Each rule's `url` is shown by `explain`.
