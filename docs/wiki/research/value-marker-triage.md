# Value-marker triage

Every constant in this project traces to a published source, or it carries a
marker that says it does not. The earlier sweep looked for the word
`UNSOURCED`. It missed the other four markers:

- `proxy`
- `modelling choice` and `modeling choice`
- `tuning`
- `declared default`

This document triages every hit of those markers under `addons/**/*.sqf`.

## The scan

```sh
grep -rniE 'proxy|modelling choice|modeling choice|tuning|declared default' \
  --include=*.sqf addons
```

The scan at commit `1f6c3e54` returned **111 hits in 64 files**. Line numbers
below are from that commit.

## The classes

| Class | Meaning | Count |
|---|---|---|
| HONEST LABEL | A display, engine or performance choice with no physical meaning. The marker is correct. | 63 |
| SOURCEABLE | A physical quantity with a reachable published value. | 1 |
| NO SOURCE | A physical quantity with no reachable published value. Keep the marker, record the search. | 32 |
| DEAD | Nothing consumes the value. | 0 |
| FALLBACK BEHIND A CORPUS | A default that applies only when a corpus row or a published value is absent. | 15 |

Three of the five classes carried a code change. HONEST LABEL hits carry a
new lock where the label was the only thing protecting the value.

## What changed

1. **`atmos/functions/physics/fnc_calculateAirframeIcing.sqf`** (SOURCEABLE).
   The comment claimed the FAR 25 Appendix C envelope set the liquid water
   content. The appendix states one cloud figure as a number and no rain
   figure at all. The two coefficients are now named `_cloudLwcGm3` and
   `_rainLwcGm3`, cited to the paragraph that applies, and labelled as stated
   proxies. The accretion scale `0.05` now carries its own label.
2. **`ballistics/functions/fnc_calculateAmmoTemperature.sqf`** (NO SOURCE,
   label repaired). The header stated 0.06 degC per shot for 5.56 NATO. The
   shipped default of 0.0001 degC/J yields 0.164 degC per shot for the same
   round, so the label disagreed with the value by 2.7 times. The label now
   states the arithmetic the default actually produces. The default is one
   definition, `AEE_AMMO_HEAT_PER_SHOT_DEFAULT`, that the read and the type
   guard both use. The settings registration keeps a literal because the
   taxonomy and documentation generators cannot resolve a macro, and a test
   fails when the literal and the definition drift apart.
3. **`weather/functions/dispersion/fnc_calculatePoolEvaporation.sqf`**
   (NO SOURCE). The label claimed most vapours fall in a 0.6 to 1.0 band. No
   published table was reachable, so the band is now stated as a placeholder
   rather than presented as a cited range.
4. **`tools/tests/test_value_markers.py`** (new, registered in
   `tools/run_tests.py`). 28 tests. It locks the label beside the value, the
   stated arithmetic, and the corpus-before-fallback order.

## SOURCEABLE

| File | Value | Unit | Citation | Disposition |
|---|---|---|---|---|
| `atmos/functions/physics/fnc_calculateAirframeIcing.sqf:34` | cloud LWC 0.35 | g/m3 | 14 CFR 25 App C Part I(c), takeoff maximum icing, −9 °C, 20 µm droplet | Cited in the header as the one stated cloud figure. The 0.5 coefficient stays a stated proxy because the continuous and intermittent maxima are figures, not numbers. |

The published figure cannot replace the coefficient. The engine passes
`overcast` and `rain` as 0 to 1 scalars, not as liquid water content. So the
appendix bounds the label and cannot supply the value. The header now says
exactly that.

## NO SOURCE

Each row is a physical quantity. The last column records why no published
value was applied.

| File:line | Value | Unit | Why it stays a marker |
|---|---|---|---|
| `ballistics/functions/fnc_calculateAmmoTemperature.sqf:84` | 0.0001 | degC/J | No published per-shot ammunition temperature rise was reachable. The label now states what the default yields, so the marker is true. |
| `ballistics/functions/fnc_calculateSeekerState.sqf:30` | see file | engine scale | The seeker constants are engine-scale, not physical. The label says so. |
| `flight/functions/fnc_calculateEngineNg.sqf:22` | 4 | s | No published gas-generator spool time constant for these engine classes. |
| `atmos/functions/physics/fnc_calculateWeatherFront.sqf:40,54,77` | 0.10 to 0.35 | cloud trend | The cloud-trend magnitude inside a −0.5 to 0.5 clamp. The cycle length is cited to Stull. |
| `atmos/functions/volcanic/fnc_calculateLaharRisk.sqf:13` | see file | m | Anchored on a published threshold and Bingham physics. The mapping above the threshold is a stated choice. |
| `atmos/functions/volcanic/fnc_calculateVolcanicWinter.sqf:14` | doubling per VEI | K | The doubling per VEI unit above the VEI 6 anchor has no published coefficient. |
| `hydrology/functions/erosion/fnc_calculatePeakRunoff.sqf:25` | not applicable | not applicable | The RUSLE slope length stands in for the Kirpich hydraulic length. Both models are cited, the equivalence is a stated choice. |
| `mobility/functions/fnc_calculateSoilStrength.sqf:22` | not applicable | not applicable | Engine config power and drivetrain values have no verified real-world unit, so the function refuses them. |
| `nightvision/functions/fnc_applyNVGTubeModel.sqf:161` | 500 | photons per µA/lm normaliser | One calibration constant for the photon scale, labelled as one knob and not four. |
| `nightvision/functions/fnc_nvgBlemishField.sqf:27` | see file | not applicable | The blemish field shape is a stated modelling choice. |
| `particles/functions/particle/fnc_particleEmission.sqf:38` | 0.6 | fraction | See the FALLBACK table. The value is the fallback, and the fallback lacks a source. |
| `thermal/functions/display/fnc_calculateVehicleHeat.sqf:42` | not applicable | not applicable | The config `enginePower` is a PhysX tuning value. The function refuses it. |
| `thermal_display/functions/ir/fnc_startActiveIR.sqf:8` | see file | engine light units | No photometric data for the engine light units. |
| `vehicles/functions/fnc_calculateEngineLoad.sqf:11,37,39,43` | 150000, 0.7 | W, m2 | No per-vehicle rated power or drag area exists in a verified unit. See the FALLBACK table. |
| `vehicles/functions/fnc_calculateExhaustPlume.sqf:25` | see file | not applicable | The idle and full plume endpoints are declared. |
| `vehicles/functions/fnc_calculateRoadLoad.sqf:30` | 0.7 | m2 | The same declared drag area as the engine-load kernel. |
| `vehicles/functions/fnc_estimateVehicleMass.sqf:235` | not applicable | not applicable | The config `enginePower` is a PhysX tuning value, passed as a hint only. |
| `vehicles/functions/fnc_updateFuelConsumption.sqf:30,40` | see file | L/h | The base consumption is a declared default, the surface factors are stated. |
| `weather/functions/dispersion/fnc_calculateDenseGasPooling.sqf:20` | see file | m | The default `k_pool` is a stated modelling choice. |
| `weather/functions/dispersion/fnc_calculatePoolEvaporation.sqf:24` | 0.7 | not applicable | A web search for a published molecular Schmidt-number table for vapours in air returned only secondary summaries and turbulent-Schmidt literature, which is a different quantity. The label now states the band is a placeholder. |
| `weather/functions/fnc_scentWildlifeResponse.sqf:16,18` | see file | not applicable | The detection threshold and the floor are stated choices. |
| `weather/functions/scalar/fnc_scalarFieldConfig.sqf:54` | see file | not applicable | The peak-relative field setup is a stated choice. |
| `weather/functions/warnings/fnc_calculateBlowingSnowVisibility.sqf:53` | see file | m | Mapped on the issue's visibility states. |
| `weather/functions/warnings/fnc_calculateDustVisibility.sqf:21` | 1 to 10 | mg/m3 | Mapped on the issue's visibility states. |
| `weather/functions/warnings/fnc_calculateSevereWeather.sqf:51` | 1 to 10 | mg/m3 | The airborne concentration ramp. The mod has no dust sensor. |
| `wildlife/functions/fnc_applyAnimalBehaviour.sqf:281` | see file | not applicable | The ecology defaults are stated choices. |

## DEAD

No hit is dead. The check was mechanical: every value named beside a marker is
read on the same path that reaches the marker, and every published variable in
these files has a reader. A deletion was therefore available for none of the
111 hits, and no deletion was made. Removing a value that looks unused would
have needed a reader proof the scan could not supply.

## FALLBACK BEHIND A CORPUS

Each fallback was verified by reading the order of the reads in the source,
then locked by a test that fails if the order changes.

| File:line | Fallback | Corpus or published path | Proof |
|---|---|---|---|
| `weatherfx/functions/weather/fnc_applyExhaustShimmer.sqf:135,150,152,237,320,618` | rated power 150000 W, drag area 0.7 m2, rotor disc 50 m2 | `aee_engineRatedPowerW`, `aee_engineDragAreaM2`, `aee_engineRotorDiscAreaM2`, then `getAircraftData` under `data/aircraft/` | `CorpusBeforeFallbackTest` reads the `_deriveAirPower` block and asserts override, corpus, default in that order for all three fields, and that each default is guarded by `<= 0` on the corpus value. |
| `flight/functions/fnc_calculateAirEngineLoad.sqf:64,67,75` | 150000 W, 0.7 m2, 50 m2 | the caller's per-vehicle variables and the aircraft corpus | `DeclaredDefaultLabelTest.test_air_engine_load_rated_power` reads the defaults out of the params block and asserts the header still declares them, including the note that the 0.688 m2 agreement is a coincidence. |
| `vehicles/functions/fnc_calculateEngineLoad.sqf:41,45` | 150000 W | `aee_engineRatedPowerW` from the caller | `DeclaredDefaultLabelTest.test_ground_engine_load_rated_power`. No road-vehicle corpus exists, so the value is also NO SOURCE. |
| `ballistics/XEH_postInit.sqf:45` | CfgAmmo `hit` × 0.5, then 4 g | `getProjectileData` held bullet mass | `BulletMassFallbackTest` asserts the corpus read precedes the damage-number proxy, and the 4 g baseline is last. |
| `particles/functions/particle/fnc_particleEmission.sqf:38` | 0.6 | `aee_core_dustSuppression` from `fnc_calculateDustSuppression` | Not locked by a test. The publisher writes the name and three other consumers read it the same way. Recorded here as the remaining gap. |
| `atmos/functions/physics/fnc_calculateAirframeIcing.sqf:39` | overcast as cloud LWC | `aee_core_simulCloudDensity` from `fnc_updateSimulWeather` | `IcingLiquidWaterTest.test_cloud_probe_stays_the_preferred_path` asserts the probe path is read after the proxy value it replaces. |
| `thermal/functions/solver/fnc_evaluateThermalEdge.sqf:36` | 0.004349 | the caller's derived threshold from the device NETD | The header states the caller passes the derived value. The kernel keeps the default for a bare call. Not locked, because the default is a documented derivation of published NETD. |
| `nightvision/functions/fnc_applyNVGTubeModel.sqf` (SNR floor 0.15, MTF 0.45) | generation defaults | the device row: `_devSnr`, `_devRes`, `_devHalo` | `DeviceRowPrecedenceTest` asserts each device-row override is applied after the generation default it replaces. |

## HONEST LABEL

The 63 remaining hits carry a correct marker. The ones where the marker guards
a number rather than a name also gained a lock:

| File | Value | Why it is honest |
|---|---|---|
| `atmos/functions/physics/fnc_calculateWeatherFront.sqf` | 345600 s | Four days, cited to Stull ch. 13 and Bjerknes 1919. Locked as cited. |
| `thermal/functions/solver/fnc_calculateAtmosphericTransmission.sqf:193` | 0.008 per sqrt(m) | Minkina and Klecha 2016 give the coefficient. The header states it is a single-condition calibration. Locked. |
| `thermal/functions/display/fnc_applySecondSun.sqf:76` | 13 | An engine light-brightness unit from the A3TI reference. No photometric meaning. Labelled as display tuning. Locked. |
| `nightvision/functions/fnc_applyNVGTubeModel.sqf:369,377` | see file | The vignette is derived from the lens rim. The ACE3 figures quoted beside it are their tuning for their mask geometry. |
| `weatherfx/...`, `thermal/...`, `vision/...` | see file | Engine proxy-plane and nested-selection limits, selection normals as direction proxies, shadow heuristics and post-process gaps. Each states a limit of the engine, not a value. |

The scatter of `capeProxy` hits in `atmos/` is one case worth naming. The
variable holds CAPE in J/kg, computed by a parcel model. `proxy` is a legacy
name, and it is kept because `aee_atmos_capeProxy` is a published variable
name. The `sqrt (2 * CAPE)` updraft relation beside it is the standard parcel
relation, so the arithmetic is physical and only the name is loose.

## Residual gaps

- `dustSuppression` in `fnc_particleEmission` has no precedence test.
- `fnc_evaluateThermalEdge` keeps an unlocked declared default.
- The `_lH = 190` in `fnc_getLocalWind` reuses the probe separation as a hill
  half-width. It is labelled as a proxy, and the same 190 appears twice in the
  file. A single named constant would stop the two drifting apart.
